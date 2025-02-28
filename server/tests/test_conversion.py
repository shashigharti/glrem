import os
import numpy as np
import xarray as xr
import pytest
from PIL import Image
from tempfile import TemporaryDirectory
from server.src.geospatial.helpers.dataconversion import save_xarray_to_png
import geojson


@pytest.fixture
def create_test_xarray():
    data = np.random.rand(10, 10)
    lat = np.linspace(-90, 90, 10)
    lon = np.linspace(-180, 180, 10)
    return xr.DataArray(
        data,
        coords={"lat": lat, "lon": lon},
        dims=["lat", "lon"],
        attrs={"crs": "EPSG:4326"},
    )


def test_save_xarray_to_png(create_test_xarray):
    test_xarray = create_test_xarray

    with TemporaryDirectory() as tempdir:
        png_filepath = os.path.join(tempdir, "test_output.png")
        geojson_filepath = png_filepath.replace(".png", ".geojson")
        save_xarray_to_png(test_xarray, png_filepath)

        assert os.path.exists(png_filepath), "PNG file was not created."
        assert os.path.exists(geojson_filepath), "GeoJSON file was not created."

        with Image.open(png_filepath) as img:
            assert img.size == (10, 10), "PNG image dimensions are incorrect."

        with open(geojson_filepath, "r") as f:
            geojson_data = geojson.load(f)
            assert (
                geojson_data["type"] == "FeatureCollection"
            ), "Invalid GeoJSON format."
            assert (
                len(geojson_data["features"]) == 1
            ), "GeoJSON should contain one feature."
            assert (
                geojson_data["features"][0]["geometry"]["type"] == "Polygon"
            ), "Invalid GeoJSON geometry type."

        data = test_xarray.values
        normalized_data = (
            (data - np.nanmin(data)) / (np.nanmax(data) - np.nanmin(data)) * 255
        ).astype(np.uint8)

        with Image.open(png_filepath) as img:
            img_data = np.array(img)
            np.testing.assert_array_equal(
                img_data,
                normalized_data,
                err_msg="PNG image data does not match expected normalized data.",
            )
