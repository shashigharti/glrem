import os

import psutil
import shutil
import argparse

import numpy as np

import dask
from dask.distributed import Client

from shapely.geometry import Point
from pygmtsar import Stack, tqdm_dask, Tiles

from src.config import *
from src.database import get_db
from src.crud.task import get_tasks, update_task_status
from src.geospatial.io.uploader.s3_client import copy_files_to_s3
from src.utils.logger import logger
from src.geospatial.io.downloader.asf_client import (
    download_data,
)
from src.geospatial.helpers.data_conversion import save_xarray_to_png


# TODO: some of the params has to be set dynamically
def _process_asf_params(params):
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


def generate_interferogram(params, product=None):
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
    # resolution = RESOLUTION

    eventid = params.get("eventid")
    eventtype = params.get("eventtype")

    outputdir = os.path.join(OUTPUT, eventtype, eventid)
    datadir = os.path.join(DATADIR, eventtype)
    workdir = os.path.join(WORKDIR, eventtype)

    # the downloaded data size uses lots of space so delete
    # existing data before running interferogram
    logger.print_log("info", "Emptying data directory")
    if os.path.exists(datadir):
        shutil.rmtree(datadir)

    if os.path.exists(workdir):
        shutil.rmtree(workdir)

    os.makedirs(outputdir, exist_ok=True)
    os.makedirs(datadir, exist_ok=True)
    os.makedirs(workdir, exist_ok=True)

    credentials = {
        "username": ASF_USERNAME,
        "password": ASF_PASSWORD,
    }
    asf_params = _process_asf_params(params)
    flight_direction = asf_params.get("flightDirection")

    orbit = None
    if flight_direction == "Descending":
        orbit = "D"

    wavelength = 200
    coarsen = (1, 4)
    subswaths = 123

    dem = f"{datadir}/dem.nc"
    eventid = params.get("eventid")

    eventdate = params.get("eventdate")
    latitude = params.get("latitude")
    longitude = params.get("longitude")
    startdate = params.get("startdate")
    enddate = params.get("enddate")
    epicenter = Point(longitude, latitude)

    logger.print_log("info", "Downloading Data")
    S1, aoi = download_data(
        epicenter,
        eventdate,
        workdir,
        datadir,
        credentials,
        asf_params,
        subswaths,
        startdate,
        enddate,
    )

    logger.print_log("info", "Downloading Tiles")
    if product:
        Tiles().download_dem(aoi, filename=dem, product=product)
    else:
        Tiles().download_dem(aoi, filename=dem)

    if "client" in globals():
        client.close()

    client = Client(
        n_workers=max(1, psutil.cpu_count() // 4),
        threads_per_worker=min(4, psutil.cpu_count()),
        memory_limit=max(4e9, psutil.virtual_memory().available),
    )
    slc_params = {
        "datadir": datadir,
        "orbit": orbit,
        "subswath": subswaths,
    }
    slc_params = {key: value for key, value in slc_params.items() if value is not None}
    logger.print_log("info", f"slc params: {slc_params}")
    scenes = S1.scan_slc(**slc_params)

    sbas = Stack(workdir, drop_if_exists=True).set_scenes(scenes)

    logger.print_log("info", "Processing reframe")
    sbas.compute_reframe(aoi)

    logger.print_log("info", "Processing DEM")
    sbas.load_dem(dem, aoi)

    logger.print_log("info", "Processing alignment")
    sbas.compute_align()

    logger.print_log("info", "Processing geocode")
    # sbas.compute_geocode(resolution) # turkey
    sbas.compute_geocode()
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
    # decimator = sbas.decimator(resolution=resolution, grid=intf) # turkey
    decimator = sbas.decimator()

    tqdm_dask(
        result := dask.persist(decimator(corr), decimator(intf)),
        desc="Compute Phase and Correlation",
    )
    corr, intf = [grid[0] for grid in result]

    intf_ll = sbas.ra2ll(intf)
    logger.print_log("info", "Saving Interferogram")
    filepath_intf_png = os.path.join(outputdir, f"{eventid}-earthquake-intf.png")
    save_xarray_to_png(intf_ll, filepath_intf_png)

    # TODO: it will be used later.
    # unwrap_filepath = os.path.join(outputdir, f"unwrap.nc")
    # unwrap = unwrapping(intf, landmask, corr, sbas, unwrap_filepath)

    # losdis_filepath = os.path.join(outputdir, f"losdis.nc")
    # los_displacement(sbas, unwrap, losdis_filepath)

    logger.print_log("info", "Copying files to s3 bucket")
    dest = os.path.join(AWS_PROCESSED_FOLDER, eventid)
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


def main(taskid: str):
    db_session = next(get_db())
    try:
        task = get_tasks(db_session, taskid=taskid)[0]
        print(task)

        if not task:
            raise ValueError(f"Task with ID {taskid} not found.")

        params = {
            "eventid": task.eventid,
            "eventtype": task.eventtype,
            "latitude": task.latitude,
            "longitude": task.longitude,
            "startdate": task.startdate,
            "enddate": task.enddate,
            "eventdate": task.eventdate,
        }
        print(params)

        result = generate_interferogram(params)
        logger.print_log("info", f"Generated interferogram saved at: {result}")

        update_task_status(db=db_session, task_id=task.id, status="completed")
        logger.print_log("info", "Task updated successfully.")
    except Exception as e:
        logger.print_log("error", f"Error during interferogram generation: {str(e)}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Generate interferogram for a given task ID"
    )
    parser.add_argument("taskid", type=str, help="Task ID to process", default="1")
    args = parser.parse_args()

    logger.print_log("info", f"Initiated interferogram generation")
    main(args.taskid)
