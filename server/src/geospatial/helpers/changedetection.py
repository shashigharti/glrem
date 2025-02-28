import os
import time
import shutil
import argparse

import dask
import psutil
import numpy as np

from itertools import islice
from shapely.geometry import Point
from dask.distributed import Client

from src.database import get_db
from src.geospatial.lib.pygmtsar import Stack, Tiles
from src.crud.task import get_tasks, update_task_status
from src.geospatial.helpers.asf import process_asf_params
from src.geospatial.io.uploader.s3_client import copy_files_to_s3
from src.geospatial.io.downloader.asf_client import download_data
from src.geospatial.helpers.dataconversion import (
    save_npy_to_tif,
)

from src.utils.logger import logger
from src.config import (
    OUTPUT,
    DATADIR,
    WORKDIR,
    ASF_USERNAME,
    ASF_PASSWORD,
    WAVELENGTH,
    COARSEN,
    SUBSWATH,
    AWS_PROCESSED_FOLDER,
)


def _generate_change_detection(params, product="3s", coarsen=None):
    """
    Generate and process change detection using Sentinel-1 data.

    Parameters:
    - params (dict): Parameters including epicenters, resolution, orbit, polarization, and ASF-specific parameters.
    - product (str): Directory for saving outputs.

    Returns:
    - str: Path to the saved interferogram image.
    """

    eventid = params.get("eventid")
    eventtype = params.get("eventtype")
    filename = params.get("filename")

    outputdir = os.path.join(OUTPUT, eventtype, eventid)
    datadir = os.path.join(DATADIR, eventtype)
    workdir = os.path.join(WORKDIR, eventtype)

    # the downloaded data size uses lots of space so delete
    # existing data before running interferogram
    logger.print_log("info", "Emptying data directory")
    if os.path.exists(datadir):
        time.sleep(1)
        shutil.rmtree(datadir)

    if os.path.exists(workdir):
        time.sleep(1)
        shutil.rmtree(workdir)

    os.makedirs(outputdir, exist_ok=True)
    os.makedirs(datadir, exist_ok=True)
    os.makedirs(workdir, exist_ok=True)

    credentials = {
        "username": ASF_USERNAME,
        "password": ASF_PASSWORD,
    }
    asf_params = process_asf_params(params)
    flight_direction = asf_params.get("flightDirection")

    orbit = "D" if flight_direction == "Descending" else None

    dem = f"{datadir}/dem.nc"
    eventid = params.get("eventid")

    eventdate = params.get("eventdate")
    latitude = params.get("latitude")
    longitude = params.get("longitude")
    startdate = params.get("startdate")
    enddate = params.get("enddate")
    epicenter = Point(longitude, latitude)

    logger.print_log("info", "Downloading Data")
    S1, aoi_gdf = download_data(
        epicenter,
        eventdate,
        workdir,
        datadir,
        credentials,
        asf_params,
        SUBSWATH,
        startdate,
        enddate,
        eventid=eventid,
    )
    aoi = aoi_gdf.unary_union.minimum_rotated_rectangle
    print(f"aoi: {aoi} type: {type(aoi)}")

    logger.print_log("info", "Downloading Tiles")
    Tiles().download_dem(aoi, filename=dem, product=product)

    if "client" in globals():
        client.close()

    dask.config.set({"logging.distributed": "info"})

    client = Client(
        n_workers=max(1, psutil.cpu_count() // 4),
        threads_per_worker=min(4, psutil.cpu_count()),
        memory_limit=max(4e9, psutil.virtual_memory().available),
    )
    logger.print_log("info", "Dask Client dashboard: %s", client.dashboard_link)

    slc_params = {"datadir": datadir, "orbit": orbit, "subswath": SUBSWATH}
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
    sbas.compute_geocode()

    logger.print_log("info", "Processing topo")
    data = sbas.open_data()

    if not coarsen:
        coarsen = COARSEN
    intensity = sbas.multilooking(
        np.square(np.abs(data)), wavelength=WAVELENGTH, coarsen=coarsen
    )

    crs = intensity.attrs.get("crs", "EPSG:4326")
    intensity_before = 10 * np.log10(intensity[0] + 1e-10)
    intensity_after = 10 * np.log10(intensity[1] + 1e-10)
    logger.print_log("info", "Performing change detection in dB space")

    changed_intensity = intensity_before - intensity_after
    threshold_min = -2
    threshold_max = 2
    changed_intensity = np.where(
        (changed_intensity >= threshold_min) & (changed_intensity <= threshold_max),
        changed_intensity,
        0,
    )

    logger.print_log("info", "Saving change detection")
    bbox = aoi_gdf.geometry.bounds.values[0]
    filepath_changedetection_tif = os.path.join(outputdir, f"{filename}.tif")
    save_npy_to_tif(changed_intensity, bbox, filepath_changedetection_tif, crs)

    logger.print_log("info", "Copying files to s3 bucket")
    dest = os.path.join(AWS_PROCESSED_FOLDER, eventtype, eventid)
    copy_files_to_s3(outputdir, dest, file_types=["tif"])
    return filepath_changedetection_tif


def batch_iterator(iterable, batch_size=1000):
    iterator = iter(iterable)
    while batch := list(islice(iterator, batch_size)):
        yield batch


def change_detection(taskid: str):
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
            "filename": task.filename,
        }
        print(params)

        result = _generate_change_detection(params, coarsen=(3, 16))
        logger.print_log("info", f"Generated change detection map, saved at: {result}")

        update_task_status(db=db_session, taskid=task.id, status="completed")
        logger.print_log("info", "Task updated successfully.")
    except Exception as e:
        logger.print_log(
            "error", f"Error during change detection: {str(e)}", exc_info=True
        )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Generate change detection for a given task ID"
    )
    parser.add_argument("--taskid", type=str, help="Task ID to process", default="1")
    args = parser.parse_args()

    logger.print_log("info", f"Initiated change detection generation")
    filepath = change_detection(args.taskid)
