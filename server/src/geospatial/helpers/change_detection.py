import os
import psutil
import argparse

import numpy as np
import geopandas as gpd
import osmnx as ox
import rasterio
from rasterio.features import shapes
from shapely.geometry import shape, Point
import pandas as pd
from pygmtsar import Stack, Tiles, S1
from dask.distributed import Client

from src.database import get_db
from src.crud.task import get_tasks
from src.geospatial.helpers.asf import process_asf_params
from src.config import (
    AWS_PROCESSED_FOLDER,
    RESOLUTION,
    OUTPUT,
    DATADIR,
    WORKDIR,
    ASF_USERNAME,
    ASF_PASSWORD,
)
from src.geospatial.io.downloader.asf_client import download_data
from src.utils.logger import logger
from src.geospatial.helpers.data_conversion import save_npy_to_png, save_npy_to_tif


def change_detection(params, product="3s"):
    eventid = params.get("eventid")
    eventtype = params.get("eventtype")

    outputdir = os.path.join(OUTPUT, eventtype, eventid)
    datadir = os.path.join(DATADIR, eventtype)
    workdir = os.path.join(WORKDIR, eventtype)

    os.makedirs(outputdir, exist_ok=True)
    os.makedirs(datadir, exist_ok=True)
    os.makedirs(workdir, exist_ok=True)

    credentials = {
        "username": ASF_USERNAME,
        "password": ASF_PASSWORD,
    }
    asf_params = process_asf_params(params)
    flight_direction = asf_params.get("flightDirection")

    orbit = None
    if flight_direction == "Descending":
        orbit = "D"
    wavelength = 200
    coarsen = (1, 4)
    subswaths = 123

    dem = f"{datadir}/dem.nc"
    eventid = params.get("eventid")

    eventdate = params.get("eventdate")
    latitude = params.get("latitude")
    longitude = params.get("longitude")
    startdate = params.get("startdate")
    enddate = params.get("enddate")
    epicenter = Point(longitude, latitude)

    logger.print_log("info", "Downloading Data")
    S1, aoi = download_data(
        epicenter,
        eventdate,
        workdir,
        datadir,
        credentials,
        asf_params,
        subswaths,
        startdate,
        enddate,
    )
    aoi = S1.scan_slc(datadir)
    logger.print_log("info", f"AOI {aoi}, type: {type(aoi)}")

    logger.print_log("info", "Downloading Tiles")
    if product:
        Tiles().download_dem(aoi, filename=dem, product=product)
    else:
        Tiles().download_dem(aoi, filename=dem)

    if "client" in globals():
        client.close()

    client = Client(
        n_workers=max(1, psutil.cpu_count() // 4),
        threads_per_worker=min(4, psutil.cpu_count()),
        memory_limit=max(4e9, psutil.virtual_memory().available),
    )
    slc_params = {
        "datadir": datadir,
        # "orbit": orbit,
        "subswath": subswaths,
    }
    slc_params = {key: value for key, value in slc_params.items() if value is not None}
    logger.print_log("info", f"slc params: {slc_params}")
    scenes = S1.scan_slc(**slc_params)

    sbas = Stack(workdir, drop_if_exists=True).set_scenes(scenes)
    print(sbas.__dict__)

    logger.print_log("info", "Processing reframe")
    sbas.compute_reframe(aoi)

    logger.print_log("info", "Processing DEM")
    sbas.load_dem(dem, aoi)

    logger.print_log("info", "Processing alignment")
    sbas.compute_align()

    logger.print_log("info", "Processing geocode")
    sbas.compute_geocode(RESOLUTION)

    logger.print_log("info", "Processing topo")
    data = sbas.open_data()
    intensity = sbas.multilooking(
        np.square(np.abs(data)), wavelength=wavelength, coarsen=coarsen
    )

    intensity_dB_before = 10 * np.log10(np.abs(intensity[0]) + 1e-10)
    intensity_dB_after = 10 * np.log10(np.abs(intensity[1]) + 1e-10)

    logger.print_log("info", "Performing change detection in dB space")
    change_map_dB = np.abs(intensity_dB_before - intensity_dB_after)

    threshold_min = -2
    threshold_max = 2
    change_map_dB = np.where(
        (change_map_dB < threshold_min) | (change_map_dB > threshold_max),
        change_map_dB,
        0,
    )

    bbox = aoi.geometry.apply(lambda geom: geom.coords[:])
    logger.print_log("info", "Saving change detection")
    # filepath_cd_png = os.path.join(outputdir, f"{eventid}-earthquake-cd.png")
    # save_npy_to_png(change_map_dB, coords, filepath_cd_png)

    filepath_cd_tif = os.path.join(outputdir, f"{eventid}-earthquake-cd.tif")
    save_npy_to_tif(change_map_dB, bbox, filepath_cd_tif)

    # return filepath_cd_png


def damage_assessment(
    earthquake_folder, osm_shapefile_directory, area_name="Turkey, Gaziantep"
):
    """
    Process earthquake-related damage detection by downloading OSM data,
    analyzing damage from raster files, and calculating statistics for damaged
    roads and buildings.

    Parameters:
    - earthquake_id (str): The ID of the earthquake for folder structure.
    - osm_shapefile_directory (str): The directory path to store OSM shapefiles.
    - area_name (str): The area name for downloading OSM data (default: "Turkey, Gaziantep").

    Returns:
    - tuple: Total length of damaged roads (km) and total count of damaged buildings.
    """
    total_damaged_roads_length_km = 0.0
    total_damaged_buildings_count = 0

    roads_geodataframe = gpd.GeoDataFrame()
    buildings_geodataframe = gpd.GeoDataFrame()

    def download_osm_data(output_directory, area_name):
        print(f"Downloading OSM data for {area_name}...")

        roads_graph = ox.graph_from_place(area_name, network_type="drive")
        roads_gdf = ox.graph_to_gdfs(roads_graph, nodes=False, edges=True)
        roads_gdf.to_file(
            os.path.join(output_directory, "roads.shp"), driver="ESRI Shapefile"
        )

        buildings_gdf = ox.features_from_place(area_name, tags={"building": True})
        buildings_gdf.to_file(
            os.path.join(output_directory, "buildings.shp"), driver="ESRI Shapefile"
        )

    if not os.path.exists(osm_shapefile_directory) or not any(
        file.endswith(".shp") for file in os.listdir(osm_shapefile_directory)
    ):
        os.makedirs(osm_shapefile_directory, exist_ok=True)
        download_osm_data(osm_shapefile_directory, area_name)

    for root, _, files in os.walk(osm_shapefile_directory):
        for file in files:
            if file.endswith(".shp"):
                shapefile_path = os.path.join(root, file)
                gdf = gpd.read_file(shapefile_path)

                if "road" in file.lower():
                    roads_geodataframe = pd.concat(
                        [roads_geodataframe, gdf], ignore_index=True
                    )
                elif "building" in file.lower():
                    buildings_geodataframe = pd.concat(
                        [buildings_geodataframe, gdf], ignore_index=True
                    )

    if not roads_geodataframe.empty:
        roads_geodataframe = roads_geodataframe.to_crs(epsg=3857)
    if not buildings_geodataframe.empty:
        buildings_geodataframe = buildings_geodataframe.to_crs(epsg=3857)

    def batch_intersection(data_geodataframe, damage_geodataframe):
        damage_union = damage_geodataframe.geometry.unary_union
        spatial_index = data_geodataframe.sindex

        def filter_intersects(geometry):
            possible_matches_index = list(spatial_index.intersection(geometry.bounds))
            possible_matches = data_geodataframe.iloc[possible_matches_index]
            return possible_matches[possible_matches.intersects(geometry)]

        results = pd.concat(
            (
                [filter_intersects(geom) for geom in damage_union.geoms]
                if damage_union.geom_type == "MultiPolygon"
                else [filter_intersects(damage_union)]
            ),
            ignore_index=True,
        )
        return results.drop_duplicates()

    for file in os.listdir(earthquake_folder):
        if file.startswith("Change Detection") and file.endswith(".tif"):
            tiff_path = os.path.join(earthquake_folder, file)

            with rasterio.open(tiff_path) as src:
                damage_data = src.read(1)
                damage_transform = src.transform
                damage_crs = src.crs

                damage_shapes = [
                    {"geometry": shape(geom), "value": value}
                    for geom, value in shapes(damage_data, transform=damage_transform)
                    if value != 0
                ]

            damage_geodataframe = gpd.GeoDataFrame(
                damage_shapes, crs=damage_crs
            ).set_geometry("geometry")
            damage_geodataframe = damage_geodataframe.to_crs(epsg=3857)

            if not roads_geodataframe.empty:
                damaged_roads = batch_intersection(
                    roads_geodataframe, damage_geodataframe
                )
            else:
                damaged_roads = gpd.GeoDataFrame()

            if not buildings_geodataframe.empty:
                damaged_buildings = batch_intersection(
                    buildings_geodataframe, damage_geodataframe
                )
            else:
                damaged_buildings = gpd.GeoDataFrame()

            damaged_roads_length_km = (
                damaged_roads.geometry.length.sum() / 1000
                if not damaged_roads.empty
                else 0.0
            )
            damaged_buildings_count = (
                len(damaged_buildings) if not damaged_buildings.empty else 0
            )

            total_damaged_roads_length_km += damaged_roads_length_km
            total_damaged_buildings_count += damaged_buildings_count

            output_folder = os.path.join(earthquake_folder, "results")
            os.makedirs(output_folder, exist_ok=True)

            if not damaged_roads.empty:
                damaged_roads.to_file(
                    os.path.join(output_folder, f"{file[:-4]}_damaged_roads.geojson"),
                    driver="GeoJSON",
                )
            if not damaged_buildings.empty:
                damaged_buildings.to_file(
                    os.path.join(
                        output_folder, f"{file[:-4]}_damaged_buildings.geojson"
                    ),
                    driver="GeoJSON",
                )

    return total_damaged_roads_length_km, total_damaged_buildings_count


def main(taskid: str):
    db_session = next(get_db())
    try:
        task = get_tasks(db_session, taskid=taskid)[0]
        print(task)

        if not task:
            raise ValueError(f"Task with ID {taskid} not found.")

        params = {
            "eventid": task.eventid,
            "eventtype": task.eventtype,
            "latitude": task.latitude,
            "longitude": task.longitude,
            "startdate": task.startdate,
            "enddate": task.enddate,
            "eventdate": task.eventdate,
        }
        print(params)

        result = change_detection(params)
        logger.print_log("info", f"Generated interferogram saved at: {result}")
    except Exception as e:
        logger.print_log(
            "error", f"Error during change detection: {str(e)}", exc_info=True
        )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Generate change detection for a given task ID"
    )
    parser.add_argument("taskid", type=str, help="Task ID to process", default="1")
    args = parser.parse_args()

    logger.print_log("info", f"Initiated change detection generation")
    main(args.taskid)
