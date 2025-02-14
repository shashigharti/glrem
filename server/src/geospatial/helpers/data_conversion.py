import os
import json
import numpy as np
from PIL import Image
from osgeo import gdal
import geojson
import matplotlib.pyplot as plt
import rasterio
from rasterio.transform import from_origin, from_bounds


def save_xarray_to_tif(data_array, tif_filepath):
    """
    Save an xarray.DataArray to a GeoTIFF file.

    Parameters:
    - data_array: xarray.DataArray containing the data and coordinates.
    - tif_filepath: Path to save the GeoTIFF file.
    """
    data = data_array.values
    lat = data_array["lat"].values
    lon = data_array["lon"].values

    transform = from_origin(
        west=lon.min(),
        north=lat.max(),
        xsize=(lon.max() - lon.min()) / data.shape[1],
        ysize=(lat.max() - lat.min()) / data.shape[0],
    )

    profile = {
        "driver": "GTiff",
        "dtype": str(data.dtype),
        "nodata": None,
        "width": data.shape[1],
        "height": data.shape[0],
        "count": 1,
        "crs": "EPSG:4326",
        "transform": transform,
    }

    with rasterio.open(tif_filepath, "w", **profile) as dst:
        dst.write(data, 1)

    return tif_filepath


def save_xarray_to_png(data_array, filepath, colormap="viridis", black_threshold=30):
    """
    Save an xarray.DataArray to a PNG image and metadata in GeoJSON file.

    Parameters:
    - data_array (xarray.DataArray): The data array containing the data and coordinates.
    - filepath (str): Path to save the PNG file (GeoJSON will use the same base name).
    - colormap (str, optional): Color map for the image. Defaults to "viridis"
    - black_threshold (int, optional):  The threshold below which pixels are considered black.
    Defaults to 30.

    Returns:
    - filename_png (str): Filename of saved PNG file.
    - filename_geojson (str): Filename of saved GEOJson file.
    """

    def normalize_data(data):
        return (data - np.nanmin(data)) / (np.nanmax(data) - np.nanmin(data))

    data_normalized = normalize_data(data_array.values)
    cmap = plt.get_cmap(colormap)
    data_colored = cmap(data_normalized)
    image_colored = (data_colored[:, :, :4] * 255).astype(np.uint8)

    black_mask = (image_colored[..., :3] < black_threshold).all(axis=-1)
    image_colored[black_mask, 3] = 0

    image = Image.fromarray(image_colored)
    image.save(filepath)

    filepath_geojson = {}
    lat = data_array["lat"].values
    lon = data_array["lon"].values

    bbox = {
        "type": "FeatureCollection",
        "features": [
            {
                "type": "Feature",
                "geometry": {
                    "type": "Polygon",
                    "coordinates": [
                        [
                            [lon.min(), lat.min()],
                            [lon.min(), lat.max()],
                            [lon.max(), lat.max()],
                            [lon.max(), lat.min()],
                            [lon.min(), lat.min()],
                        ]
                    ],
                },
                "properties": {"orbit": "D"},
            }
        ],
    }

    filepath_geojson = filepath.replace(".png", ".geojson")
    with open(filepath_geojson, "w") as f:
        geojson.dump(bbox, f)

    return filepath, filepath_geojson


def save_npy_to_png(
    data,
    coords,
    filepath,
    cmap="viridis",
    black_threshold=10,
):

    def normalize_data(data):
        return (data - np.nanmin(data)) / (np.nanmax(data) - np.nanmin(data))

    data_normalized = normalize_data(data)
    cmap = plt.get_cmap(cmap)
    data_colored = cmap(data_normalized)

    image_colored = (data_colored[:, :, :4] * 255).astype(np.uint8)
    black_mask = (image_colored[..., :3] < black_threshold).all(axis=-1)
    image_colored[black_mask, 3] = 0

    image = Image.fromarray(image_colored)
    image.save(filepath)

    bbox = {
        "type": "FeatureCollection",
        "features": [
            {
                "type": "Feature",
                "geometry": {
                    "type": "Polygon",
                    "coordinates": coords,
                },
                "properties": {"orbit": "D"},
            }
        ],
    }

    filepath_geojson = filepath.replace(".png", ".geojson")
    with open(filepath_geojson, "w") as f:
        geojson.dump(bbox, f)

    return filepath, filepath_geojson


def save_npy_to_tif(npy_file, bbox, tif_file, crs="EPSG:4326"):
    data = np.load(npy_file)
    height, width = data.shape
    transform = from_bounds(*bbox, width, height)

    with rasterio.open(
        tif_file,
        "w",
        driver="GTiff",
        height=height,
        width=width,
        count=1,
        dtype=data.dtype,
        crs=crs,
        transform=transform,
    ) as dst:
        dst.write(data, 1)
    return tif_file


def save_tif_to_png(filepath, dest):
    """
    Save tif to png and image metadata to GeoJSON file.

    Parameters:
    - filepath(str) : File path of TIFF file.
    - dest(str): Destination directory where PNG file and meta data(GeoJSON file) will be saved.

    Returns:
    - filepath_png: File path of saved PNG image.
    - filepath_geojson: File path of saved GeoJSON metadata file.
    """

    def translate_and_save_to_png(filepath_png):
        dataset = gdal.Open(filepath)

        geotransform = dataset.GetGeoTransform()
        projection = dataset.GetProjection()

        xmin = geotransform[0]
        ymax = geotransform[3]
        xmax = xmin + geotransform[1] * dataset.RasterXSize
        ymin = ymax + geotransform[5] * dataset.RasterYSize
        bounds = (xmin, ymin, xmax, ymax)

        gdal.Translate(filepath_png, dataset, format="PNG")
        return bounds, projection

    filename_tif = os.path.basename(filepath)
    filepath_png = os.path.join(dest, filename_tif.replace(".tif", ".png"))
    coordinates, projection = translate_and_save_to_png(filepath_png)
    filepath_geojson = os.path.join(dest, filename_tif.replace(".tif", ".json"))

    geojson_data = {
        "type": "FeatureCollection",
        "features": [
            {
                "type": "Feature",
                "geometry": {
                    "type": "Polygon",
                    "coordinates": [
                        [
                            [coordinates[0], coordinates[1]],
                            [coordinates[0], coordinates[3]],
                            [coordinates[2], coordinates[3]],
                            [coordinates[2], coordinates[1]],
                            [coordinates[0], coordinates[1]],
                        ]
                    ],
                },
                "properties": {"projection": projection},
            }
        ],
    }
    with open(filepath_geojson, "w") as f:
        json.dump(geojson_data, f)

    return filepath_png, filepath_geojson
