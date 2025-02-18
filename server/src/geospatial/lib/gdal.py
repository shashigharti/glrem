import xarray as xr
import rasterio
import numpy as np
import pyvista as pv
from osgeo import gdal, osr
from ...helpers import logger
from argparse import ArgumentParser
from rasterio.transform import from_origin

logger = logger.CustomLogger(__name__)


def intf_nc_to_tif(input_nc_file, output_tif_file):
    try:
        logger.print_log("info", f"Opening NetCDF file: {input_nc_file}")
        ds = xr.open_dataset(input_nc_file)

        logger.print_log("info", "Extracting 'phase' variable from the NetCDF file")
        phase = ds["phase"].values

        nodata_value = 0
        logger.print_log("info", "Replacing NaN values with nodata value")
        phase_no_nan = np.nan_to_num(phase, nan=nodata_value)

        latitudes = ds["lat"].values
        longitudes = ds["lon"].values

        lat_spacing = abs(latitudes[1] - latitudes[0])
        lon_spacing = abs(longitudes[1] - longitudes[0])

        logger.print_log("info", "Creating geotransform for GeoTIFF")
        transform = from_origin(
            west=longitudes.min(),
            north=latitudes.max(),
            xsize=lon_spacing,
            ysize=lat_spacing,
        )

        logger.print_log("info", f"Writing data to GeoTIFF: {output_tif_file}")
        with rasterio.open(
            output_tif_file,
            "w",
            driver="GTiff",
            count=1,
            dtype="float32",
            height=phase_no_nan.shape[0],
            width=phase_no_nan.shape[1],
            crs="EPSG:4326",
            transform=transform,
            nodata=nodata_value,
        ) as dst:
            dst.write(phase_no_nan.astype("float32"), 1)

        logger.print_log(
            "info", f"Converted intf.nc and file saved to {output_tif_file}"
        )
    except Exception as e:
        logger.print_log("error", f"Error in intf_to_tif: {e}")
        raise RuntimeError(f"Error in intf_to_tif: {e}")


def corr_nc_to_tif(input_nc_file, output_tif_file):
    try:
        logger.print_log("info", f"Opening NetCDF file: {input_nc_file}")
        ds = xr.open_dataset(input_nc_file)

        logger.print_log("info", "Extracting 'lat', 'lon', and 'correlation' variables")
        lat = ds["lat"].values
        lon = ds["lon"].values
        correlation = ds["correlation"].values

        driver = gdal.GetDriverByName("GTiff")

        rows, cols = correlation.shape
        logger.print_log("info", "Creating GeoTIFF file for correlation data")
        output_ds = driver.Create(output_tif_file, cols, rows, 1, gdal.GDT_Float32)

        srs = osr.SpatialReference()
        srs.ImportFromEPSG(4326)

        x_min = lon.min()
        y_max = lat.max()
        pixel_size = (lon[1] - lon[0], lat[1] - lat[0])

        geotransform = (x_min, pixel_size[0], 0, y_max, 0, -pixel_size[1])
        output_ds.SetGeoTransform(geotransform)

        output_ds.SetProjection(srs.ExportToWkt())

        logger.print_log("info", "Writing correlation data to GeoTIFF")
        output_ds.GetRasterBand(1).WriteArray(correlation)

        output_ds.GetRasterBand(1).SetNoDataValue(np.nan)
        output_ds = None

        logger.print_log(
            "info", f"Converted corr.nc and file saved to {output_tif_file}"
        )
    except Exception as e:
        logger.print_log("error", f"Error in corr_to_tif: {e}")
        raise RuntimeError(f"Error in corr_to_tif: {e}")


def vtk_to_tif(src_file_path, dest_file_path):
    """
    Converts a VTK file to a GeoTIFF format, extracting 'los' scalar data.

    Parameters:
    src_file_path (str): Path to the source VTK file.
    dest_file_path (str): Path to the output GeoTIFF file.

    This function reads the VTK file, extracts the 'los' scalar data, and maps it
    onto a 2D grid. It then creates a GeoTIFF file using the extracted data,
    applying appropriate geotransform and projection (WGS84 by default).
    """
    try:
        mesh = pv.read(src_file_path)
    except Exception as e:
        raise ValueError(f"Error reading VTK file '{src_file_path}': {e}")

    print("Point data keys:", mesh.point_data.keys())
    print("Cell data keys:", mesh.cell_data.keys())

    if "los" not in mesh.point_data:
        raise ValueError("Scalar data 'los' not found in point data.")

    values = mesh.point_data["los"]
    x = mesh.points[:, 0]
    y = mesh.points[:, 1]

    grid_x, grid_y = np.meshgrid(np.unique(x), np.unique(y))
    grid_values = values.reshape(grid_x.shape)

    driver = gdal.GetDriverByName("GTiff")
    output_ds = driver.Create(
        dest_file_path, grid_x.shape[1], grid_y.shape[0], 1, gdal.GDT_Float32
    )

    if not output_ds:
        raise RuntimeError(f"Failed to create GeoTIFF file at '{dest_file_path}'.")

    pixel_size_x = (max(x) - min(x)) / (grid_x.shape[1] - 1)
    pixel_size_y = (max(y) - min(y)) / (grid_y.shape[0] - 1)

    geo_transform = (
        min(x),
        pixel_size_x,
        0,
        max(y),
        0,
        -pixel_size_y,
    )

    output_ds.SetGeoTransform(geo_transform)
    output_ds.SetProjection("EPSG:4326")

    output_ds.GetRasterBand(1).WriteArray(grid_values)
    output_ds = None
    print(f"GeoTIFF '{dest_file_path}' created successfully.")


def get_parser() -> ArgumentParser:
    """Get parser.

    Returns:
        ArgumentParser: The parser object.
    """
    parser = ArgumentParser(description="Generate GeoTIFF from VTK file")
    parser.add_argument("--input", type=str, required=True, help="Source file path")
    parser.add_argument(
        "--output", type=str, required=True, help="Destination file path"
    )
    parser.add_argument(
        "--type",
        type=str,
        required=True,
        help="Conversion type (intf or corr)",
        default="intf",
    )
    return parser


if __name__ == "__main__":
    args = get_parser().parse_args()

    input_nc_file = args.input
    output_tif_file = args.output
    type = args.type

    if type == "intf":
        logger.print_log(
            "info", f"Starting conversion of {input_nc_file} to {output_tif_file}"
        )
        intf_nc_to_tif(input_nc_file, output_tif_file)

    if type == "corr":
        logger.print_log(
            "info", f"Starting conversion of {input_nc_file} to {output_tif_file}"
        )
        corr_nc_to_tif(input_nc_file, output_tif_file)
