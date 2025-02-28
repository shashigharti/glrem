import os
import datetime
import pandas as pd
import geopandas as gpd
import asf_search as asf

from shapely.ops import unary_union
from shapely.geometry import Polygon
from sentinelsat import read_geojson, geojson_to_wkt

from src.config import (
    DATA_PLATFORM,
    PROCESSING_LEVEL,
    BEAM_MODE,
    OUTPUT,
    SCENES_FILENAME,
)
from src.utils.logger import logger
from src.geospatial.helpers.sceneselection import find_matching_scenes, generate_aoi


def get_burst_or_scene(params, eventdate, startdate, enddate, crs="EPSG:4326"):
    """
    Fetches Sentinel-1 images based on an earthquake epicenter and a specified date range.

    Parameters:
    - params (dict): ASF search parameters, including the desired satellite mode, polarization, etc.
    - eventdate (str): Date of the earthquake event in "YYYY-MM-DD" format.
    - startdate (str): Start date of the image search period in "YYYY-MM-DD" format.
    - enddate (str): End date of the image search period in "YYYY-MM-DD" format.

    Returns:
    - list: A list of scene IDs for images that intersect with the AOI, covering the earthquake event within the specified date range.
    """
    logger.print_log("info", params)

    selected_scenes = []
    aoi_path = os.path.join(OUTPUT, "aois")
    tmpscenes_path = os.path.join(OUTPUT, SCENES_FILENAME)

    # generate aoi
    aoi_path = generate_aoi(params["eventid"])

    # load aoi
    footprint = geojson_to_wkt(read_geojson(aoi_path))
    params = {**params, "intersectsWith": footprint.wkt}
    params.update({"start": startdate, "end": enddate})
    aoi_gdf = gpd.GeoDataFrame({"geometry": [footprint]}, crs)

    results = asf.search(**params)
    if not results:
        return []

    # process scenes
    scenes_df = _process_scenes(results, eventdate)

    # find post event scenes overlapping with AOI
    selected_scenes_pre_event, _ = _find_best_overlapping_scenes(
        scenes_df, aoi_gdf, eventdate, snapshot_time="post"
    )
    logger.print_log("info", f"Post event scenes: {selected_scenes_pre_event}")
    scenes_df = pd.DataFrame(
        [
            scene.properties
            for scene in results
            if scene.properties.fileId in selected_scenes_pre_event
        ]
    )
    scenes_df.to_csv(tmpscenes_path)

    # find matching scenes based on perpendicular and temporal baseline
    selected_scenes_df = find_matching_scenes(selected_scenes_pre_event)
    selected_scenes = [
        scene["MatchID"]
        for scene in selected_scenes_df.iterrows()
        if scene["ReferenceID"] in selected_scenes_pre_event
    ]
    return selected_scenes


def _find_best_overlapping_scenes(scenes_gdf, aoi_gdf, event_date, snapshot_time="pre"):
    """
    Identifies the scenes that best overlap with the Area of Interest (AOI) and returns their IDs along with the minimum rotated rectangle of the combined AOI.

    Parameters:
    - scenes_gdf (GeoDataFrame): GeoDataFrame containing the scenes with metadata and geometries.
    - aoi_gdf (GeoDataFrame): GeoDataFrame representing the Area of Interest (AOI).
    - event_date (str or datetime): The event date (in 'YYYY-MM-DD' format) used to filter scenes occurring before or after the event.
    - snapshot_time (str, optional): Specifies whether to filter for "pre" or "post" event scenes (default is "pre").

    Returns:
    - tuple: A tuple containing:
        - list: A list of scene IDs that overlap with the AOI.
        - Polygon: The minimum rotated rectangle that encloses the combined AOI of the selected scenes.
    """

    aoi = None
    remaining_aoi = aoi_gdf.geometry.iloc[0]
    used_scenes = set()

    # Filter scenes based on the snapshot_time and date before the event date
    if snapshot_time == "pre":
        condition = scenes_gdf["acquisition_date"] < event_date
    else:
        condition = scenes_gdf["acquisition_date"] > event_date

    filtered_scenes_gdf = scenes_gdf[(scenes_gdf["type"] == snapshot_time) & condition]

    selected_geometries = []

    while not remaining_aoi.is_empty:
        best_scene = None
        best_coverage = 0
        selected = False

        for _, scene in filtered_scenes_gdf.iterrows():
            if scene["scene_id"] in used_scenes:
                continue

            overlap_area = scene.geometry.intersection(remaining_aoi).area
            if overlap_area > best_coverage:
                best_coverage = overlap_area
                best_scene = scene
                selected = True
            print(
                f"Scene ID: {scene['scene_id']} overlap_area: {overlap_area} selected: {selected}"
            )

        if best_scene is None:
            break

        used_scenes.add(best_scene["scene_id"])
        selected_geometries.append(best_scene.geometry)
        remaining_aoi = remaining_aoi.difference(best_scene.geometry)

    if selected_geometries:
        combined_aoi = unary_union(selected_geometries)
        aoi = combined_aoi.minimum_rotated_rectangle

    return list(used_scenes), aoi


def _process_scenes(results, event_date):
    """
    Processes ASF search results into a GeoDataFrame with scene metadata.

    Parameters:
    - results (list): List of ASF search results.
    - event_date (str or datetime): Event date to categorize scenes.

    Returns:
    - GeoDataFrame: Processed scene data including geometry, orbit, and type (pre/post).
    """
    scenes_data = []
    # event_date = datetime.datetime.strptime(event_date, "%Y-%m-%dT%H:%M:%SZ")
    for scene in results:
        start_time = scene.properties["startTime"]
        start_date = datetime.datetime.strptime(start_time, "%Y-%m-%dT%H:%M:%SZ")

        event_type = "pre" if start_date < event_date else "post"
        scenes_data.append(
            {
                "scene_id": scene.properties["sceneName"],
                "orbit": scene.properties["orbit"],
                "acquisition_date": start_date,
                "type": event_type,
                "geometry": Polygon(scene.geometry["coordinates"][0]),
            }
        )
    logger.print_log("info", f"{len(scenes_data)} scenes found")
    return gpd.GeoDataFrame(scenes_data, geometry="geometry", crs="EPSG:4326")


def process_asf_params(params):
    startdate = params.get("startdate")
    enddate = params.get("enddate")
    params = {
        "start": startdate,
        "end": enddate,
        "dataset": "SENTINEL-1",
        "platform": DATA_PLATFORM,
        "processingLevel": PROCESSING_LEVEL,
        "beamMode": BEAM_MODE,
        "flightDirection": "Descending",
    }
    return params
