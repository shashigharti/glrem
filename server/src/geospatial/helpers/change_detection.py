import os
import geopandas as gpd
import osmnx as ox
import rasterio
from rasterio.features import shapes
from shapely.geometry import shape
import pandas as pd


def change_detection(pre_event_data, post_event_data, destdir):
    # TODO: Change detection code here

    output_file = os.path.join(destdir, "change-detection.tif")


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
