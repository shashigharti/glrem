import os
import json
import argparse

import numpy as np
import pandas as pd
import geopandas as gpd
import osmnx as ox
import rasterio

from itertools import islice
from joblib import Parallel, delayed
from rasterio.mask import mask
from shapely.geometry import box, mapping, Polygon, LineString

from shapely import wkt
from src.database import get_db
from matplotlib.patches import Rectangle
from src.crud.task import get_tasks, update_task_status

from src.utils.logger import logger
from src.config.examples import AOI
from src.config import OUTPUT, DATADIR, AWS_PROCESSED_FOLDER
from src.geospatial.io.uploader.s3_client import copy_files_to_s3


def _download_data(output_directory, aoi_polygon):
    print(f"Downloading OSM data for {aoi_polygon}...")

    roads_graph = ox.graph_from_polygon(aoi_polygon, network_type="drive")
    roads_gdf = ox.graph_to_gdfs(roads_graph, nodes=False, edges=True)
    roads_gdf.to_file(os.path.join(output_directory, "roads.geojson"), driver="GeoJSON")
    logger.print_log("info", f"Total roads: {len(roads_gdf)}")
    logger.print_log("info", f"Bounding Box of roads: {roads_gdf.total_bounds}")

    buildings_gdf = ox.features_from_polygon(aoi_polygon, tags={"building": True})
    buildings_gdf.to_file(
        os.path.join(output_directory, "buildings.geojson"), driver="GeoJSON"
    )
    logger.print_log("info", f"Total buildings: {len(buildings_gdf)}")
    logger.print_log("info", f"Bounding Box of buildings: {buildings_gdf.total_bounds}")


def batch_iterator(iterable, batch_size=1000):
    iterator = iter(iterable)
    while batch := list(islice(iterator, batch_size)):
        yield batch


def _process_damaged_roads(filepath, roads_gdf, destdir, threshold=1.5, buffer_size=5):
    """Process roads to detect damage based on raster intensity."""
    damaged_roads = []

    with rasterio.open(filepath) as src:
        for _, road in roads_gdf.iterrows():
            if not isinstance(road.geometry, LineString):
                continue

            road_buffer = road.geometry.buffer(buffer_size)
            geometry = [mapping(road_buffer)]

            try:
                out_image, _ = mask(src, geometry, crop=True)
                intensity_values = out_image.flatten()

                if np.any(intensity_values >= threshold):
                    damaged_roads.append(road)

            except Exception as e:
                print(f"Skipping road due to error: {e}")

    damaged_gdf = gpd.GeoDataFrame(damaged_roads, crs=roads_gdf.crs)
    damaged_roads_fp = os.path.join(destdir, "damaged_roads_network.geojson")
    damaged_gdf.to_file(damaged_roads_fp, driver="GeoJSON")

    if damaged_gdf.crs.is_geographic:
        damaged_gdf = damaged_gdf.to_crs(epsg=3857)  # Web Mercator (meters)

    total_damaged_roads_km = damaged_gdf.geometry.length.sum() / 1000
    return total_damaged_roads_km


def _process_damaged_buildings(filepath, buildings_footprint, destdir, threshold=1.5):
    """Process buildings in batches to detect damage."""
    damaged_buildings = []
    with rasterio.open(filepath) as src:
        for _, building in buildings_footprint.iterrows():
            bbox = building.geometry.bounds
            building_mask = Polygon(
                [
                    (bbox[0], bbox[1]),
                    (bbox[0], bbox[3]),
                    (bbox[2], bbox[3]),
                    (bbox[2], bbox[1]),
                ]
            )

            geometry = [mapping(building_mask)]
            out_image, _ = mask(src, geometry, crop=True)

            intensity_values = out_image.flatten()

            if np.any(intensity_values >= threshold):
                damaged_buildings.append(building)

    damaged_gdf = gpd.GeoDataFrame(damaged_buildings, crs=buildings_footprint.crs)
    damaged_buildings_fp = os.path.join(destdir, "damaged_buildings_footprint.geojson")
    damaged_gdf.to_file(damaged_buildings_fp, driver="GeoJSON")
    return len(damaged_buildings)


def _process_road_networks(projected_gdf, destdir):
    """Convert road geometries to GeoJSON format and save."""
    features = []

    for idx, row in projected_gdf.iterrows():
        road_geom = row["geometry"]

        if road_geom.geom_type == "LineString":
            feature = {
                "type": "Feature",
                "properties": {"id": idx},
                "geometry": {
                    "type": "LineString",
                    "coordinates": list(road_geom.coords),
                },
            }
            features.append(feature)

    geojson = {
        "type": "FeatureCollection",
        "name": "road_network",
        "crs": {
            "type": "name",
            "properties": {"name": "urn:ogc:def:crs:OGC:1.3:CRS84"},
        },
        "features": features,
    }

    filepath = os.path.join(destdir, "road_networks.geojson")
    with open(filepath, "w") as f:
        json.dump(geojson, f, indent=4)


def _process_building_footprints(projected_gdf, destdir):
    features = []
    for idx, row in projected_gdf.iterrows():
        building_geom = row["geometry"]

        if building_geom.geom_type == "Polygon":
            feature = {
                "type": "Feature",
                "properties": {"id": idx},
                "geometry": {
                    "type": "Polygon",
                    "coordinates": [list(building_geom.exterior.coords)],
                },
            }
            features.append(feature)
    geojson = {
        "type": "FeatureCollection",
        "name": "building_footprints",
        "crs": {
            "type": "name",
            "properties": {"name": "urn:ogc:def:crs:OGC:1.3:CRS84"},
        },
        "features": features,
    }

    filepath = os.path.join(destdir, "building_footprints.geojson")
    with open(filepath, "w") as f:
        json.dump(geojson, f, indent=4)
    return filepath


def _process_damage_assessment(filepath, eventtype, eventid, aoi_geom):
    """
    Process earthquake-related damage detection by downloading OSM data,
    analyzing damage from raster files, and calculating statistics for damaged
    roads and buildings.
    """
    outputdir = os.path.join(OUTPUT, eventtype, eventid)
    datadir_osm = os.path.join(DATADIR, eventtype, "osm_files")
    os.makedirs(outputdir, exist_ok=True)
    os.makedirs(datadir_osm, exist_ok=True)

    logger.print_log("info", "Downloading data")
    # _download_data(datadir_osm, aoi_geom)

    buildings = os.path.join(datadir_osm, "buildings.geojson")
    buildings_gdf = gpd.read_file(buildings)
    buildings_gdf = buildings_gdf.drop_duplicates(subset="geometry")

    buildings_footprint_filepath = _process_building_footprints(
        buildings_gdf, outputdir
    )
    building_footprints = gpd.read_file(buildings_footprint_filepath)
    total_damaged_buildings_count = _process_damaged_buildings(
        filepath, building_footprints, outputdir
    )
    logger.print_log(
        "info", f"Total damaged buildings: {total_damaged_buildings_count}"
    )

    # roads = os.path.join(datadir_osm, "roads.geojson")
    # roads_gdf = gpd.read_file(roads)
    # road_networks = _process_road_networks(roads_gdf, datadir_osm)
    # total_damaged_roads_count = _process_damaged_roads(filepath, road_networks)
    # logger.print_log("info", f"Total damaged roads: {total_damaged_roads_count}")

    logger.print_log("info", "Copying files to s3 bucket")
    dest = os.path.join(AWS_PROCESSED_FOLDER, eventid)
    copy_files_to_s3(outputdir, dest, file_types=["geojson"])

    filepath = os.path.join(outputdir, dest)
    return filepath


def damage_assessment(taskid: str):
    db_session = next(get_db())
    try:
        task = get_tasks(db_session, taskid=taskid)[0]
        logger.print_log("info", task)

        if not task:
            raise ValueError(f"Task with ID {taskid} not found.")

        aoi_geom = wkt.loads(AOI.get(task.eventid))
        outputdir = os.path.join(OUTPUT, task.eventtype, task.eventid)
        filepath = os.path.join(
            outputdir,
            f"{task.filename.replace('damageassessment', 'changedetection')}.tif",
        )
        result = _process_damage_assessment(
            filepath, task.eventtype, task.eventid, aoi_geom
        )
        logger.print_log(
            "info",
            f"Generated assessment results damaged_buildings_footprint.geojson, damaged_roads_network.geojson saved at: {result}",
        )

        update_task_status(db=db_session, taskid=task.id, status="completed")
        logger.print_log("info", "Task updated successfully.")

    except Exception as e:
        logger.print_log(
            "error", f"Error during damage assessment: {str(e)}", exc_info=True
        )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Generate damage assessment for a given task ID"
    )
    parser.add_argument("--taskid", type=str, help="Task ID to process", default="1")
    args = parser.parse_args()

    logger.print_log("info", f"Initiated damage assessment")
    damage_assessment(args.taskid)
