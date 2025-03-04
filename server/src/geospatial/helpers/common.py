import pandas as pd
import geopandas as gpd
from shapely import wkt
from shapely.ops import unary_union
from src.utils.logger import logger


def revised_aoi(aoi_gdf, eventdate):
    aoi_gdf["datetime"] = pd.to_datetime(aoi_gdf["datetime"])
    pre_event_aoi = aoi_gdf[aoi_gdf["datetime"] < pd.to_datetime(eventdate)]
    post_event_aoi = aoi_gdf[aoi_gdf["datetime"] >= pd.to_datetime(eventdate)]

    if pre_event_aoi.empty or post_event_aoi.empty:
        return None

    pre_combined = unary_union(pre_event_aoi["geometry"])
    post_combined = unary_union(post_event_aoi["geometry"])
    final_aoi = pre_combined.intersection(post_combined)

    logger.print_log("info", f"{pre_combined}, {post_combined}, {final_aoi}")

    if final_aoi.is_empty:
        return None

    return gpd.GeoDataFrame(
        {"event_stage": ["Final Overlapping AOI"]},
        geometry=[final_aoi],
        crs=aoi_gdf.crs,
    )


def select_best_overlapping_scene_from_a_day(scenes, aoi_polygon):
    scenes["geometry"] = scenes["geometry"].apply(wkt.loads)
    scenes_gdf = gpd.GeoDataFrame(scenes, geometry="geometry", crs="EPSG:4326")

    def compute_intersection_percentage(geometry):
        intersection = geometry.intersection(aoi_polygon)
        return (
            (intersection.area / geometry.area) * 100
            if not intersection.is_empty
            else 0.0
        )

    scenes_gdf["intersection_percentage"] = scenes_gdf["geometry"].apply(
        compute_intersection_percentage
    )
    scenes_gdf["date"] = pd.to_datetime(scenes_gdf["startTime"]).dt.date

    best_date = scenes_gdf.groupby("date")["intersection_percentage"].sum().idxmax()

    return scenes_gdf.loc[scenes_gdf["date"] == best_date]
