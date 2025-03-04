import os
import datetime
import pandas as pd
import geopandas as gpd
import asf_search as asf

from shapely import wkt
from shapely.wkt import dumps
from shapely.geometry import Polygon, shape
from sentinelsat import read_geojson, geojson_to_wkt

from src.config import (
    DATA_PLATFORM,
    PROCESSING_LEVEL,
    BEAM_MODE,
    DATADIR,
    SCENES_FILENAME,
)
from src.utils.logger import logger
from src.geospatial.helpers.sceneselection import find_matching_scenes, generate_aoi
from src.geospatial.helpers.common import select_best_overlapping_scene_from_a_day


def get_burst_or_scene(
    params, eventid, eventtype, eventdate, startdate, enddate, crs="EPSG:4326"
):
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

    tmpscenes_path = os.path.join(DATADIR, eventtype, eventid)
    tmpscenes_filepath = os.path.join(tmpscenes_path, SCENES_FILENAME)
    os.makedirs(tmpscenes_path, exist_ok=True)

    # generate aoi
    aoi_path = generate_aoi(eventid)
    logger.print_log("info", aoi_path)

    # load aoi
    footprint = geojson_to_wkt(read_geojson(aoi_path))
    aoi_geometry = wkt.loads(footprint)
    aoi_polygon = next(
        (geom for geom in aoi_geometry.geoms if geom.geom_type == "Polygon"), None
    )
    logger.print_log("info", aoi_polygon.wkt)

    params = {**params, "intersectsWith": aoi_polygon.wkt}
    params.update({"start": startdate, "end": enddate})
    aoi_gdf = gpd.GeoDataFrame({"geometry": [aoi_polygon]}, crs=crs)

    results = asf.search(**params)
    if not results:
        return []

    # process scenes
    scenes_df = _process_scenes(results, eventdate)

    # find post event scenes overlapping with AOI
    selected_candidates_pre_event, _ = _find_best_overlapping_scenes(
        scenes_df, aoi_gdf, eventdate, snapshot_time="post"
    )

    logger.print_log("info", f"Post event scenes: {selected_candidates_pre_event}")
    scenes_list = []
    for scene in results:
        if scene.properties["fileID"] in selected_candidates_pre_event:
            properties = scene.properties
            properties["geometry"] = dumps(shape(scene.geometry))
            scenes_list.append(properties)

    logger.print_log("info", f"Scenes: {scenes_list}")
    scenes_df = pd.DataFrame(scenes_list)
    scenes_df = select_best_overlapping_scene_from_a_day(scenes_df, aoi_polygon)
    scenes_df.to_csv(tmpscenes_filepath)

    logger.print_log("info", f"{tmpscenes_filepath}")

    selected_scenes_pre_event = [scene["fileID"] for _, scene in scenes_df.iterrows()]

    # find matching scenes based on perpendicular and temporal baseline
    selected_scenes_df = find_matching_scenes(
        selected_scenes_pre_event, eventdate, eventtype, eventid
    )
    selected_scenes = []
    for _, scene in selected_scenes_df.iterrows():
        for item in (scene["fileID"], scene["ReferenceID"]):
            if item not in selected_scenes:
                selected_scenes.append(item.replace("-SLC", ""))
    return list(set(selected_scenes))


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

    if snapshot_time == "pre":
        condition = scenes_gdf["acquisition_date"] < event_date
    else:  # "post"
        condition = scenes_gdf["acquisition_date"] > event_date

    filtered_scenes_gdf = scenes_gdf[
        (scenes_gdf["type"] == snapshot_time) & condition
    ].to_crs(aoi_gdf.crs)

    overlapping_scenes = filtered_scenes_gdf[
        filtered_scenes_gdf.intersects(aoi_gdf.unary_union)
    ].drop_duplicates(subset="geometry")
    logger.print_log("info", f"type(aoi_gdf) {type(aoi_gdf)}")

    aoi = aoi_gdf.unary_union
    aoi_area = aoi.area

    overlapping_scenes["intersection_area"] = overlapping_scenes.geometry.apply(
        lambda geom: geom.intersection(aoi).area
    )
    overlapping_scenes = overlapping_scenes.sort_values(
        by="intersection_area", ascending=False
    )
    selected_scenes = []
    covered_area = 0

    for _, scene in overlapping_scenes.iterrows():
        selected_scenes.append(scene["file_id"])
        covered_area += scene["intersection_area"]
        coverage = covered_area / aoi_area
        if coverage > 0.90:
            break
        logger.print_log(
            "info",
            f"Total Covered Area: {scene["intersection_area"]:.2f}, Coverage: {scene["intersection_area"] / aoi_area:.2%}",
            scene["file_id"],
        )
        logger.print_log("info", f"Total Coverage:  {coverage:.2%}")
    logger.print_log("info", "Selected Overlapping Scenes:", selected_scenes)
    logger.print_log(
        "info",
        f"Total Covered Area: {covered_area:.2f}, Coverage: {covered_area / aoi_area:.2%}",
    )

    return selected_scenes, aoi


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
                "file_id": scene.properties["fileID"],
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
