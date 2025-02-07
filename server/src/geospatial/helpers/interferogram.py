import os
import psutil

import numpy as np

import dask
from dask.distributed import Client

from pygmtsar import Stack, tqdm_dask, Tiles

from src.geospatial.io.uploader.s3_client import copy_files_to_s3
from src.utils.logger import logger
from src.geospatial.io.downloader.asf_client import (
    benchmark,
    download_dem,
    download_data,
)
from src.geospatial.helpers.data_conversion import save_xarray_to_png
from src.config import *


# TODO: some of the params has to set dynamically
def process_params(params):
    start = params.get("startdate")
    end = params.get("enddate")
    aoi = params.get("areaofinterest")
    country = params.get("country")
    print(country)

    if country.lower() == "turkey":
        asf = {
            "start": start,
            "end": end,
            "dataset": "SLC-BURST",
            "platform": DATA_PLATFORM,
            "processingLevel": PROCESSING_LEVEL,
            "beamMode": BEAM_MODE,
            "polarization": "VV",
            "flightDirection": "Descending",
            "intersectsWith": aoi,
        }
        return {
            "asf": asf,
            "custom": {
                "wavelength": "200",
                "coarsen": "(1, 4)",
                "product": "3s",
                "use_burst": True,
            },
        }

    asf = {
        "start": start,
        "end": end,
        "dataset": "SENTINEL-1",
        "platform": DATA_PLATFORM,
        "processingLevel": PROCESSING_LEVEL,
        "beamMode": BEAM_MODE,
        "polarization": "VV+HH",
        "intersectsWith": aoi,
    }
    return {
        "asf": asf,
        "custom": {"wavelength": "400", "coarsen": "(4, 16)", "use_burst": False},
    }


def compute_reframe(sbas, aoi, country="iraq"):
    if country == "iraq":
        sbas.compute_reframe(aoi)
    return sbas


def generate_interferogram(params, credentials, workdir, datadir, outputdir):
    """
    Generate and process an interferogram using Sentinel-1 data.

    Parameters:
    - params (dict): Parameters including epicenters, resolution, orbit, polarization, and ASF-specific parameters.
    - credentials (dict): Authentication credentials for data access.
    - workdir (str): Working directory for intermediate files.
    - datadir (str): Directory for downloaded data.
    - outputdir (str): Directory for saving outputs.

    Returns:
    - str: Path to the saved interferogram image.
    """
    resolution = RESOLUTION
    subswath = SUBSWATH

    processed_params = process_params(params)
    asf_params = processed_params.get("asf")
    custom_params = processed_params.get("custom")

    orbit = asf_params.get("orbit")
    polarization = asf_params.get("polarization")
    wavelength = custom_params.get("wavelength")
    coarsen = custom_params.get("coarsen")
    use_burst = custom_params.get("use_burst", USE_BURST)

    os.makedirs(outputdir, exist_ok=True)

    dem = f"{datadir}/dem.nc"
    event_id = params["eventid"]
    print(asf_params, use_burst)

    S1, aoi = download_data(
        workdir, datadir, credentials, asf_params, use_burst, subswaths=subswath
    )

    if custom_params.get("product"):
        Tiles().download_dem(aoi, filename=dem, product=custom_params["product"])
    else:
        Tiles().download_dem(aoi, filename=dem)

    if "client" in globals():
        client.close()

    client = Client(
        n_workers=max(1, psutil.cpu_count() // 4),
        threads_per_worker=min(4, psutil.cpu_count()),
        memory_limit=max(4e9, psutil.virtual_memory().available),
    )

    if orbit:
        scenes = S1.scan_slc(datadir, polarization=polarization, orbit=orbit)
    else:
        if subswath:
            scenes = S1.scan_slc(datadir, polarization=polarization, subswath=subswath)

    sbas = Stack(workdir, drop_if_exists=True).set_scenes(scenes)

    logger.print_log("info", "Processing reframe")
    sbas = compute_reframe(sbas, aoi, "iraq")

    logger.print_log("info", "Processing DEM")
    sbas.load_dem(dem, aoi)

    logger.print_log("info", "Processing alignment")
    sbas.compute_align()

    logger.print_log("info", "Processing geocode")
    sbas.compute_geocode(resolution)
    pairs = [sbas.to_dataframe().index.unique()]

    logger.print_log("info", "Processing topo")
    topo = sbas.get_topo()
    data = sbas.open_data()
    intensity = sbas.multilooking(
        np.square(np.abs(data)), wavelength=wavelength, coarsen=coarsen
    )

    logger.print_log("info", "Processing phasediff")
    phase = sbas.phasediff(pairs, data, topo)

    logger.print_log("info", "Processing multilooking")
    phase = sbas.multilooking(phase, wavelength=wavelength, coarsen=coarsen)

    logger.print_log("info", "Processing correlation")
    corr = sbas.correlation(phase, intensity)

    logger.print_log("info", "Processing goldstein")
    phase_goldstein = sbas.goldstein(phase, corr, 32)

    logger.print_log("info", "Processing interferogram")
    intf = sbas.interferogram(phase_goldstein)

    logger.print_log("info", "Processing decimator")
    decimator = sbas.decimator(resolution=resolution, grid=intf)

    tqdm_dask(
        result := dask.persist(decimator(corr), decimator(intf)),
        desc="Compute Phase and Correlation",
    )
    corr, intf = [grid[0] for grid in result]

    intf_ll = sbas.ra2ll(intf)
    logger.print_log("info", "Saving Interferogram")
    filepath_intf_png = os.path.join(outputdir, f"intf.png")
    save_xarray_to_png(intf_ll, filepath_intf_png)

    # TODO: it will be used later.
    # unwrap_filepath = os.path.join(outputdir, f"unwrap.nc")
    # unwrap = unwrapping(intf, landmask, corr, sbas, unwrap_filepath)

    # losdis_filepath = os.path.join(outputdir, f"losdis.nc")
    # los_displacement(sbas, unwrap, losdis_filepath)

    logger.print_log("info", "Copying files to s3 bucket")
    dest = os.path.join("app-analyzed-data", event_id)
    copy_files_to_s3(outputdir, dest)

    return filepath_intf_png


def unwrapping(intf, landmask, corr, sbas, unwrap_filepath):
    # SNAPHU unwrapper allows to split large scene to tiles for parallel processing and accurately enough merge
    # the tiles to a single image. That's especially helpful to unwrap a single interferogram using all
    # the processor cores and save RAM consumption drastically.

    # Low-coherence phases can be masked using a threshold value. Offshore areas in the phase are masked.
    # The masked phase is internally interpolated using the phases of the nearest pixels with good coherence.
    # Pixels located far from well-coherent regions are set to zero phase during the unwrapping processing.
    # small tiles unwrapping is faster but some details can be missed
    conf = sbas.snaphu_config(
        defomax=None, NTILEROW=2, NTILECOL=2, ROWOVRLP=100, COLOVRLP=100
    )

    print("SNAPHU custom config generated:")
    print(conf)

    tqdm_dask(
        unwrap := sbas.unwrap_snaphu(intf.where(landmask), corr, conf=conf).persist(),
        desc="SNAPHU Unwrapping",
    )

    unwrap_ll = sbas.ra2ll(unwrap.phase)
    unwrap_ll.to_netcdf(unwrap_filepath, engine="netcdf4")
    return unwrap


def los_displacement(sbas, unwrap, losdis_filepath):
    tqdm_dask(
        detrend := (
            unwrap.phase - sbas.gaussian(unwrap.phase, wavelength=300000)
        ).persist(),
        desc="Detrending",
    )
    los_disp_mm_ll = sbas.ra2ll(sbas.los_displacement_mm(detrend))
    los_disp_mm_ll.to_netcdf(losdis_filepath, engine="netcdf4")
