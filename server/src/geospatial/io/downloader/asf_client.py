import os
import time
from pygmtsar import S1, Tiles

from src.geospatial.lib.asf import ASF
from src.geospatial.helpers import asf as asf_helper
from src.geospatial.helpers.visualization import ExtendedStack as Stack


def benchmark(func, *args, **kwargs):
    start_time = time.time()
    result = func(*args, **kwargs)
    end_time = time.time()

    elapsed_time = end_time - start_time
    print(f"Time taken for {func.__name__}: {elapsed_time:.2f} seconds")
    return result


def download_data(
    epicenter, eventdate, workdir, datadir, credentials, asf_params, subswaths
):
    """
    Downloads bursts and orbits from ASF based on the provided parameters and saves them to the specified directories.

    Parameters:
    - workdir (str): The directory where the processed work will be stored.
    - datadir (str): The directory where the data (bursts and orbits) will be downloaded.
    - credentials (dict): A dictionary containing the ASF username and password for authentication.
    - asf_params (dict, optional): Parameters for fetching bursts. If not provided, `asf_helper.get_bursts` will be used to generate bursts.
    - bursts (list, optional): A list of bursts to download. If not provided, bursts will be fetched using `asf_helper.get_bursts`.
    - limit_records (int, optional): The number of bursts to download. If provided, limits the bursts to the specified count.

    Returns:
    - tuple: A tuple containing:
        - S1 : The Sentinel-1 data object
        - aoi : The area of interest (AOI)
    """
    os.makedirs(workdir, exist_ok=True)
    os.makedirs(datadir, exist_ok=True)

    asf = ASF(**credentials)
    file_names = asf_helper.get_burst_or_scene(asf_params, eventdate, epicenter)
    print(f"selected scenes: {len(file_names)}", file_names)
    print(f"subswaths: {subswaths}")

    for swath in str(subswaths):
        asf.download_scenes(datadir, file_names, swath)

    S1.download_orbits(datadir, S1.scan_slc(datadir))
    aoi = S1.scan_slc(datadir)

    return S1, aoi


def download_dem(area_of_interest, filename_nc):
    """
    Downloads a Digital Elevation Model (DEM) for the specified area of interest and saves it to a NetCDF file.

    Args:
        area_of_interest (BBox): The bounding box representing the area of interest.
        filename_nc (str): The filename to save the downloaded DEM data in NetCDF format.

    Returns:
        None

    Example:
        download_dem(area_of_interest, "dem.nc")
    """
    Tiles().download_dem(area_of_interest, filename=filename_nc, product="3s")


def download_landmask(area_of_interest, filename_nc):

    Tiles().download_landmask(area_of_interest, filename=filename_nc, product="3s")


def get_sbas(workdir, scenes):
    """
    Retrieves the Small BAseline Subset (SBAS) from the specified scenes and processes them.

    Args:
        workdir (str): The directory where the work will be stored.
        scenes (list): A list of scenes to include in the SBAS processing.

    Returns:
        Stack: A processed stack object containing the SBAS data.

    Example:
        sbas = get_sbas("/path/to/workdir", scenes)
    """
    sbas = Stack(workdir, drop_if_exists=True).set_scenes(scenes)
    return sbas
