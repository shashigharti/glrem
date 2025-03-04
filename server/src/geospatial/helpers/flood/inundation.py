import os
import time
import json
import psutil
import shutil
import argparse

import numpy as np
import dask
from dask.distributed import Client
from shapely.geometry import Point
from src.geospatial.lib.pygmtsar import Stack, tqdm_dask, Tiles

from src.config import (
    AWS_PROCESSED_FOLDER,
    OUTPUT,
    DATADIR,
    WORKDIR,
    ASF_USERNAME,
    ASF_PASSWORD,
    WAVELENGTH,
    COARSEN,
    SUBSWATH,
)
import geopandas as gpd
from src.database import get_db
from src.crud.task import get_tasks, update_task_status
from src.geospatial.io.uploader.s3_client import copy_files_to_s3
from src.utils.logger import logger
from src.geospatial.io.downloader.asf_client import download_data
from src.geospatial.helpers.dataconversion import (
    save_xarray_to_png,
)
from src.geospatial.helpers.asf import process_asf_params

WAVELENGTH = 400
COARSEN = (3, 12)
SUBSWATH = 2


def _generate_inundation(params, product="3s"):
    """
    Generate and process an interferogram using Sentinel-1 data.

    Parameters:
    - params (dict): Parameters including epicenters, resolution, orbit, polarization, and ASF-specific parameters.
    - product (str): Directory for saving outputs.

    Returns:
    - str: Path to the saved interferogram image.
    """

    eventid = params.get("eventid")
    eventtype = params.get("eventtype")

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

    S1, _ = download_data(
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
    geojson = """
    {
    "type": "Feature",
    "geometry": {
        "type": "Point",
        "coordinates": [130.8314, -17.44634]
    },
    "properties": {}
    }
    """
    AOI = gpd.GeoDataFrame.from_features([json.loads(geojson)])
    aoi = AOI.buffer(0.08)
    logger.print_log("info", f"AOI : {aoi}")
    print("AOI", type(aoi))

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
    logger.print_log("info", f"Dask Client dashboard: {client.dashboard_link}")

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
    sbas.compute_geocode(45.0)
    pairs = np.asarray([sbas.to_dataframe().index[:-1], sbas.to_dataframe().index[1:]])
    logger.print_log("info", f"Pairs: {pairs}")

    logger.print_log("info", "Processing topo")
    topo = sbas.get_topo()
    data = sbas.open_data()
    intensity = sbas.multilooking(
        np.square(np.abs(data)), wavelength=WAVELENGTH, coarsen=COARSEN
    )

    logger.print_log("info", "Processing phasediff")
    phase = sbas.phasediff(pairs, data, topo)

    logger.print_log("info", "Processing multilooking")
    phase = sbas.multilooking(phase, wavelength=WAVELENGTH, coarsen=COARSEN)

    logger.print_log("info", "Processing correlation")
    corr = sbas.correlation(phase, intensity)

    logger.print_log("info", "Processing correlation")
    tqdm_dask(corr := dask.persist(corr)[0], desc="Compute Correlation")
    corr_ll = sbas.ra2ll(corr)
    corr_ll = corr_ll.where(corr_ll < 0.2)
    # sbas.plot_correlations(corr_ll.where(corr_ll<0.2), cols=2, cmap='turbo', caption='Correlation Lost: Indicates Flooding')
    # logger.print_log("info", f"corr: {len(corr_ll)}")
    print(len(corr_ll))
    print(type(corr_ll[0]))

    logger.print_log("info", "Saving correlation")
    filepath_intf_png = os.path.join(outputdir, f"{eventid}-flood-inun-1.png")
    save_xarray_to_png(corr_ll[0], filepath_intf_png, colormap="turbo")

    filepath_intf_png = os.path.join(outputdir, f"{eventid}-flood-inun.png")
    save_xarray_to_png(corr_ll[1], filepath_intf_png, colormap="turbo")

    # filepath_intf_png = os.path.join(outputdir, f"{eventid}-flood-inun.tif")
    # save_xarray_to_tif(corr_ll, filepath_intf_png)

    logger.print_log("info", "Copying files to s3 bucket")
    dest = os.path.join(AWS_PROCESSED_FOLDER, eventid)
    copy_files_to_s3(outputdir, dest)

    return filepath_intf_png


def generate_inundation(taskid: str):
    db_session = next(get_db())
    try:
        task = get_tasks(db_session, taskid=taskid)[0]

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
        logger.print_log("info", f"params: {params}")

        result = _generate_inundation(params)
        logger.print_log("info", f"Generated inundation saved at: {result}")

        update_task_status(db=db_session, task_id=task.id, status="completed")
        logger.print_log("info", "Task updated successfully.")
    except Exception as e:
        update_task_status(db=db_session, task_id=task.id, status="error")
        logger.print_log(
            "error", f"Error generating inundation: {str(e)}", exc_info=True
        )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Generate inundation for a given task ID"
    )
    parser.add_argument("taskid", type=str, help="Task ID to process", default="1")
    args = parser.parse_args()

    logger.print_log("info", f"Initiated inundation generation")
    generate_inundation(args.taskid)
