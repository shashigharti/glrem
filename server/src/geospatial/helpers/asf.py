import asf_search as asf
import geopandas as gpd
import pandas as pd
from shapely.geometry import Polygon, box

from src.geospatial.helpers.earthquake import get_aoi


def get_burst_or_scene(
    params,
    event_date,
    startdate,
    enddate,
    epicenter=None,
    magnitude=None,
    earthquake_id=None,
):
    """
    Fetches Sentinel-1 images based on an earthquake epicenter and date range.

    Parameters:
    - params (dict): ASF search parameters.
    - epicenter (shapely.geometry.Point): Latitude and longitude of the earthquake epicenter.
    - event_date (str): Event date in "YYYY-MM-DD" format.
    - aoi (shapely.geometry.Polygon, optional): Area of Interest (AOI). Defaults to None.

    Returns:
    - list: List of selected scene IDs covering the AOI.
    """

    if earthquake_id:
        aoi = get_aoi(earthquake_id, magnitude)
    else:
        width = 200000  # 200km
        height = 200000  # 200km
        aoi = (
            gpd.GeoSeries([epicenter], crs="EPSG:4326")
            .to_crs(epsg=3857)
            .apply(
                lambda x: box(
                    x.x - width / 2, x.y - height / 2, x.x + width / 2, x.y + height / 2
                )
            )
            .to_crs(epsg=4326)
            .iloc[0]
        )

    params = {**params, "intersectsWith": aoi.wkt}
    params.update({"start": startdate, "end": enddate})
    aoi_gdf = gpd.GeoDataFrame({"geometry": [aoi]}, crs="EPSG:4326")
    print(params)

    results = asf.search(**params)
    if not results:
        return []

    scenes_df = _process_scenes(results, event_date)
    selected_scenes_pre_event = _find_best_overlapping_scenes(scenes_df, aoi_gdf)
    print(f"{selected_scenes_pre_event} pre event scenes found")

    selected_scenes_post_event = _find_best_overlapping_scenes(
        scenes_df, aoi_gdf, snapshot_time="post"
    )
    print(f"{selected_scenes_post_event} post event scenes found")

    selected_scenes = selected_scenes_pre_event + selected_scenes_post_event
    return selected_scenes


def _find_best_overlapping_scenes(scenes_gdf, aoi_gdf, snapshot_time="pre"):
    """
    Finds the scenes that best cover the area of interest (AOI).

    Parameters:
    - scenes_df (GeoDataFrame): DataFrame containing scenes with metadata and geometry.
    - aoi (shapely.geometry.Polygon): Area of Interest (AOI).
    - snapshot_time (str): Time category ("pre" or "post") to filter scenes.

    Returns:
    - list: List of scene IDs that cover the AOI.
    """

    remaining_aoi = aoi_gdf.geometry.iloc[0]
    used_scenes = set()
    filtered_scenes_gdf = scenes_gdf[scenes_gdf["type"] == snapshot_time]
    while not remaining_aoi.is_empty:
        best_scene = None
        best_coverage = 0

        for _, scene in filtered_scenes_gdf.iterrows():
            if scene["scene_id"] in used_scenes:
                continue

            overlap_area = scene.geometry.intersection(remaining_aoi).area
            if overlap_area > best_coverage:
                best_coverage = overlap_area
                best_scene = scene

        if best_scene is None:
            break

        used_scenes.add(best_scene["scene_id"])
        remaining_aoi = remaining_aoi.difference(best_scene.geometry)

    return list(used_scenes)


def _process_scenes(results, event_date):
    """
    Processes ASF search results into a GeoDataFrame with scene metadata.

    Parameters:
    - results (list): List of ASF search results.
    - event_date (str or datetime): Event date to categorize scenes.

    Returns:
    - GeoDataFrame: Processed scene data including geometry, orbit, and type (pre/post).
    """
    event_date = pd.to_datetime(event_date)

    scenes_data = []
    for scene in results:
        start_time = pd.to_datetime(scene.properties["startTime"])

        start_date = start_time.replace(tzinfo=None).normalize()
        event_type = "pre" if start_date < event_date else "post"

        scenes_data.append(
            {
                "scene_id": scene.properties["fileID"],
                "orbit": scene.properties["orbit"],
                "acquisition_date": pd.to_datetime(scene.properties["startTime"]),
                "type": event_type,
                "geometry": Polygon(scene.geometry["coordinates"][0]),
            }
        )
    print(f"{len(results)} scenes found")

    return gpd.GeoDataFrame(scenes_data, geometry="geometry", crs="EPSG:4326")
