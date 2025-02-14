import os
import time
from pygmtsar import S1, Tiles

from src.config import TEST_EVENTID
from src.utils.logger import logger
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
    epicenter,
    eventdate,
    workdir,
    datadir,
    credentials,
    asf_params,
    subswaths,
    startdate,
    enddate,
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

    logger.print_log("info", "Searching Scenes")
    asf = ASF(**credentials)
    file_names = asf_helper.get_burst_or_scene(
        asf_params, eventdate, startdate, enddate, epicenter=epicenter
    )
    if TEST_EVENTID != "us6000jlqa":
        file_names = asf_helper.get_burst_or_scene(
            asf_params, eventdate, startdate, enddate, epicenter=epicenter
        )
    else:
        # TODO: it is for testing only
        file_names = [
            "S1A_IW_SLC__1SDV_20230129T033517_20230129T033544_046993_05A2FE_E089",
            "S1A_IW_SLC__1SDV_20230129T033452_20230129T033519_046993_05A2FE_BE0B",
            "S1A_IW_SLC__1SDV_20230129T033427_20230129T033455_046993_05A2FE_6FF2",
            "S1A_IW_SLC__1SDV_20230210T033426_20230210T033454_047168_05A8CD_FAA6",
            "S1A_IW_SLC__1SDV_20230210T033451_20230210T033518_047168_05A8CD_E5B0",
            "S1A_IW_SLC__1SDV_20230210T033516_20230210T033543_047168_05A8CD_D767",
        ]

    logger.print_log("info", f"Selected scenes: {len(file_names)}")
    print(f"selected scenes: {len(file_names)}", file_names)

    logger.print_log("info", f"Downloading Scenes: {file_names}")
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
