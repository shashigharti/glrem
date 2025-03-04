import os
import io
import json
import base64
import requests
from datetime import datetime

from fastapi import APIRouter, HTTPException, Depends, BackgroundTasks
from fastapi.responses import JSONResponse, StreamingResponse
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional

from src.utils.logger import logger
from src.utils.common import generate_filename
from src.database import get_db
from src.crud.task import create_task, get_tasks, update_task_status
from src.config import AWS_BUCKET_NAME, s3_client, AWS_PROCESSED_FOLDER, USGS_ENDPOINT
from src.apis.usgs.earthquake import get_data, format_data
from src.geospatial.helpers.earthquake.utils import get_daterange
from src.geospatial.helpers.earthquake.changedetection import generate_change_detection
from src.geospatial.helpers.earthquake.damageassessment import (
    generate_damage_assessment,
)
from src.geospatial.helpers.earthquake.interferogram import generate_interferogram
from src.config import OUTPUT

router = APIRouter()


@router.get("")
def get_earthquakes(
    starttime: str, endtime: str, coordinates: str, minmagnitude: float = 7.0
):
    min_lat, max_lat, min_lon, max_lon = map(float, coordinates.split(","))

    params = {
        "format": "geojson",
        "starttime": starttime,
        "endtime": endtime,
        "minlatitude": min_lat,
        "maxlatitude": max_lat,
        "minlongitude": min_lon,
        "maxlongitude": max_lon,
        "minmagnitude": minmagnitude,
    }

    response = requests.get(USGS_ENDPOINT, params=params)
    return (
        response.json()
        if response.status_code == 200
        else {"error": "Failed to fetch data"}
    )


@router.get("/tiles")
async def get_tiles_endpoint(eventid: str, z: int, x: int, y: int):
    s3_key = os.path.join(AWS_PROCESSED_FOLDER, eventid, "tiles", f"{z}/{x}/{y}.png")
    print(s3_key)

    try:
        tile_object = s3_client.get_object(Bucket=AWS_BUCKET_NAME, Key=s3_key)
        tile_data = tile_object["Body"].read()

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal Server Error: {str(e)}")

    return StreamingResponse(io.BytesIO(tile_data), media_type="image/png")


@router.get("/interferogram/files")
async def get_earthquake_interferogram_files_endpoint(
    eventid: str,
    ext: str = "png",
    responsetype: str = "url",
    db: Session = Depends(get_db),
):
    tasks = get_tasks(
        db, eventid=eventid, eventtype="earthquake", analysis="interferogram"
    )
    if not tasks:
        return JSONResponse(content={"detail": "File not found"})

    task = tasks[0]
    try:
        image_file_key = os.path.join(
            AWS_PROCESSED_FOLDER, task.eventtype, eventid, f"{task.filename}.{ext}"
        )

        meta_file_key = os.path.join(
            AWS_PROCESSED_FOLDER,
            task.eventtype,
            eventid,
            f"{task.filename}.geojson",
        )

        if responsetype == "url":
            return JSONResponse(
                content={
                    "file_name": image_file_key,
                    "geojson": meta_file_key,
                }
            )

        geojson_object = s3_client.get_object(Bucket=AWS_BUCKET_NAME, Key=meta_file_key)
        geojson_data = geojson_object["Body"].read().decode("utf-8")
        png_object = s3_client.get_object(Bucket=AWS_BUCKET_NAME, Key=image_file_key)
        png_data = png_object["Body"].read()
        png_base64 = base64.b64encode(png_data).decode("utf-8")
        content = {
            "png_base64": png_base64,
            "geojson": json.loads(geojson_data),
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal Server Error: {str(e)}")

    return JSONResponse(content=content)


@router.get("/changedetection/files")
async def get_earthquake_changedetection_files_endpoint(
    eventid: str,
    ext: str = "tif",
    db: Session = Depends(get_db),
):
    tasks = get_tasks(
        db, eventid=eventid, eventtype="earthquake", analysis="changedetection"
    )
    if not tasks:
        return JSONResponse(content={"detail": "File not found"})

    task = tasks[0]
    try:
        damaged_buildings_file_key = os.path.join(
            AWS_PROCESSED_FOLDER,
            task.eventtype,
            eventid,
            f"{task.filename}.{ext}",
        )

        s3_client.get_object(Bucket=AWS_BUCKET_NAME, Key=damaged_buildings_file_key)

        content = {
            "file_name": damaged_buildings_file_key,
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal Server Error: {str(e)}")

    return JSONResponse(content=content)


@router.get("/damageassessment/files")
async def get_earthquake_damageassessment_files_endpoint(
    eventid: str,
    ext: str = "geojson",
    assettype: str = "buildings",
    db: Session = Depends(get_db),
):
    tasks = get_tasks(
        db, eventid=eventid, eventtype="earthquake", analysis="changedetection"
    )
    if not tasks:
        return JSONResponse(content={"detail": "File not found"})

    task = tasks[0]
    try:
        damaged_buildings_file_key = os.path.join(
            AWS_PROCESSED_FOLDER,
            task.eventtype,
            eventid,
            f"{task.filename}-{assettype}.{ext}",
        )
        buildings_file_key = os.path.join(
            AWS_PROCESSED_FOLDER,
            task.eventtype,
            eventid,
            f"{assettype}-footprints.{ext}",
        )

        content = {
            f"file_name_damaged_{assettype}_footprint": damaged_buildings_file_key,
            f"file_name_{assettype}_footprint": buildings_file_key,
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal Server Error: {str(e)}")

    return JSONResponse(content=content)


class InterferogramRequest(BaseModel):
    userid: str
    eventid: str


@router.post("/interferogram")
async def generate_interferogram_endpoint(
    params: InterferogramRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
):
    params_dict = params.model_dump()
    logger.print_log("info", f"Initiated request for {params_dict}")

    eventid = params_dict["eventid"]
    event_data = get_data(params_dict["eventid"])
    eventdetails = format_data(event_data)
    logger.print_log("info", f"Event found: {eventdetails}")

    eventdate = eventdetails.get("eventdate")
    latitude = eventdetails.get("latitude")
    longitude = eventdetails.get("longitude")

    eventdetails = {**eventdetails, **params_dict}
    daterange = get_daterange(eventdate, 10, 10)
    eventdetails["startdate"] = datetime.strptime(
        daterange["startdate"], "%Y-%m-%dT%H:%M:%SZ"
    )
    eventdetails["enddate"] = datetime.strptime(
        daterange["enddate"], "%Y-%m-%dT%H:%M:%SZ"
    )
    eventdetails["status"] = "processing"

    analysis = "interferogram"
    eventtype = "earthquake"
    filename = generate_filename(eventid, eventtype, analysis)
    eventdetails["filename"] = filename
    eventdetails["analysis"] = analysis

    existing_tasks = get_tasks(
        db=db,
        latitude=latitude,
        longitude=longitude,
        eventtype=eventtype,
        analysis=analysis,
    )

    if existing_tasks:
        logger.print_log("info", f"Task already exists with ID: {existing_tasks[0].id}")
        return {
            "success": True,
            "message": "Task already exists.",
            "task_id": existing_tasks[0].id,
            "eventid": eventid,
            "filename": filename,
        }

    task = create_task(db=db, task_data=eventdetails)
    logger.print_log("info", f"Task {task.id} created successfully.")

    try:
        logger.print_log("info", f"Triggered interferogram processing.")
        background_tasks.add_task(generate_interferogram, task.id)
    except Exception as e:
        update_task_status(db=db, taskid=task.id, status="error")
        logger.print_log(
            "error", f"Error generating interferogram: {str(e)}", exc_info=True
        )
        raise HTTPException(status_code=500, detail="Error generating interferogram.")

    return {
        "success": True,
        "status": "processing",
        "task_id": task.id,
        "eventid": eventid,
        "filename": filename,
    }


class InterferogramRequest(BaseModel):
    userid: str
    eventid: str
    analysis: Optional[str] = "interferogram"


@router.post("/interferogram/regenerate")
def regenerate_task_endpoint(
    params: InterferogramRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
):
    task = get_tasks(
        db=db,
        eventid=params.eventid,
        userid=params.userid,
        analysis=params.analysis,
    )
    analysis_func = {
        "interferogram": generate_interferogram,
        "changedetection": generate_change_detection,
        "damageassessment": generate_damage_assessment,
    }

    logger.print_log("info", f"Regenerating analysis {params.analysis}")

    if task is None:
        raise HTTPException(
            status_code=404, detail="Task not found or cannot be regenerated"
        )
    task = task[0]
    try:
        update_task_status(db=db, taskid=task.id, status="processing")
        background_tasks.add_task(analysis_func[params.analysis], task.id)
    except Exception as e:
        update_task_status(db=db, taskid=task.id, status="error")
        logger.print_log("error", f"Error regenerating {params.analysis}: {str(e)}")
        raise HTTPException(
            status_code=500, detail=f"Error regenerating {params.analysis}."
        )

    return {
        "success": True,
        "status": "processing",
        "task_id": task.id,
        "eventid": params.eventid,
        "filename": task.filename,
    }


class ChangedetectionRequest(BaseModel):
    userid: str
    eventid: str


@router.post("/changedetection")
async def generate_change_detection_endpoint(
    params: ChangedetectionRequest,
    background_tasks: BackgroundTasks,
    db_session: Session = Depends(get_db),
):
    params_dict = params.model_dump()
    eventid = params_dict["eventid"]
    eventdetails = format_data(get_data(params_dict["eventid"]))

    eventdate = eventdetails.get("eventdate")
    latitude = eventdetails.get("latitude")
    longitude = eventdetails.get("longitude")

    eventdetails = {**eventdetails, **params_dict}
    daterange = get_daterange(eventdate, 10, 10)
    eventdetails["startdate"] = datetime.strptime(
        daterange["startdate"], "%Y-%m-%dT%H:%M:%SZ"
    )
    eventdetails["enddate"] = datetime.strptime(
        daterange["enddate"], "%Y-%m-%dT%H:%M:%SZ"
    )
    eventdetails["status"] = "processing"

    analysis = "changedetection"
    eventtype = "earthquake"
    eventdetails["analysis"] = analysis

    filename = generate_filename(eventid, eventtype, analysis)
    eventdetails["filename"] = filename

    existing_tasks = get_tasks(
        db=db_session,
        eventid=eventid,
        latitude=latitude,
        longitude=longitude,
        eventtype=eventtype,
        analysis=analysis,
    )

    if existing_tasks:
        logger.print_log("info", f"Task already exists with ID: {existing_tasks[0].id}")
        return {
            "success": True,
            "message": "Task already exists.",
            "task_id": existing_tasks[0].id,
            "eventid": eventid,
            "filename": filename,
        }

    task = create_task(db=db_session, task_data=eventdetails)
    logger.print_log("info", f"Task {task.id} created successfully.")

    try:
        logger.print_log("info", f"Triggered change detection processing.")
        background_tasks.add_task(generate_change_detection, task.id)
    except Exception as e:
        update_task_status(db=db_session, taskid=task.id, status="error")
        logger.print_log(
            "error", f"Error generating change detection: {str(e)}", exc_info=True
        )
        raise HTTPException(
            status_code=500, detail="Error generating change detection."
        )

    return {
        "success": True,
        "status": "processing",
        "task_id": task.id,
        "eventid": eventid,
        "filename": filename,
    }


class DamageAssessmentRequest(BaseModel):
    userid: str
    eventid: str
    area: str


@router.post("/damageassessment/buildings")
async def generate_damage_assessment_endpoint(
    params: DamageAssessmentRequest,
    background_tasks: BackgroundTasks,
    db_session: Session = Depends(get_db),
):
    params_dict = params.model_dump()
    eventid = params_dict["eventid"]
    area = params_dict["area"]
    eventdetails = format_data(get_data(eventid))
    asset = "buildings"

    changedetection_filepath = os.path.join(
        OUTPUT, "earthquake", eventid, f"earthquake-{eventid}-changedetection.tif"
    )
    logger.print_log("info", f"Checking file: {changedetection_filepath}")
    file_exists = os.path.exists(changedetection_filepath)
    if not file_exists:
        logger.print_log("info", "File doesnot exists")
        return JSONResponse(
            content={
                "detail": "Change detection file not found. Run change detection first."
            }
        )

    eventdate = eventdetails.get("eventdate")
    latitude = eventdetails.get("latitude")
    longitude = eventdetails.get("longitude")

    params_dict.pop("area", None)
    eventdetails.update(params_dict)
    daterange = get_daterange(eventdate, 10, 10)

    eventdetails["startdate"] = datetime.strptime(
        daterange["startdate"], "%Y-%m-%dT%H:%M:%SZ"
    )
    eventdetails["enddate"] = datetime.strptime(
        daterange["enddate"], "%Y-%m-%dT%H:%M:%SZ"
    )
    eventdetails["status"] = "processing"

    analysis = "damageassessment"
    eventtype = "earthquake"
    filename = generate_filename(eventid, eventtype, analysis)
    eventdetails["filename"] = filename
    eventdetails["analysis"] = analysis
    params_dict["areaofinterest"] = area
    params_dict["asset"] = asset

    existing_tasks = get_tasks(
        db=db_session,
        latitude=latitude,
        longitude=longitude,
        eventtype=eventtype,
        analysis=analysis,
        asset=asset,
    )

    if existing_tasks:
        logger.print_log("info", f"Task already exists with ID: {existing_tasks[0].id}")
        return {
            "success": True,
            "message": "Task already exists.",
            "task_id": existing_tasks[0].id,
            "eventid": eventid,
            "filename": filename,
        }

    task = create_task(db=db_session, task_data=eventdetails)
    logger.print_log("info", f"Task {task.id} created successfully.")

    try:
        logger.print_log("info", f"Triggered damage assessment processing.")
        background_tasks.add_task(generate_damage_assessment, task.id)
    except Exception as e:
        update_task_status(db=db_session, taskid=task.id, status="error")
        logger.print_log(
            "error", f"Error generating damage assessment: {str(e)}", exc_info=True
        )
        raise HTTPException(
            status_code=500, detail="Error generating damage assessment."
        )

    return {
        "success": True,
        "status": "processing",
        "task_id": task.id,
        "eventid": eventid,
        "filename": filename,
    }


@router.post("/damageassessment/roads")
async def generate_damage_assessment_endpoint(
    params: DamageAssessmentRequest,
    background_tasks: BackgroundTasks,
    db_session: Session = Depends(get_db),
):
    params_dict = params.model_dump()
    eventid = params_dict["eventid"]
    area = params_dict["area"]
    eventdetails = format_data(get_data(eventid))

    eventdate = eventdetails.get("eventdate")
    latitude = eventdetails.get("latitude")
    longitude = eventdetails.get("longitude")

    params_dict.pop("area", None)
    eventdetails.update(params_dict)
    daterange = get_daterange(eventdate, 10, 10)

    eventdetails["startdate"] = datetime.strptime(
        daterange["startdate"], "%Y-%m-%dT%H:%M:%SZ"
    )
    eventdetails["enddate"] = datetime.strptime(
        daterange["enddate"], "%Y-%m-%dT%H:%M:%SZ"
    )
    eventdetails["status"] = "processing"

    analysis = "damageassessment"
    eventtype = "earthquake"
    filename = generate_filename(eventid, eventtype, analysis)
    eventdetails["filename"] = filename
    eventdetails["analysis"] = analysis

    existing_tasks = get_tasks(
        db=db_session,
        latitude=latitude,
        longitude=longitude,
        eventtype=eventtype,
        analysis=analysis,
    )

    if existing_tasks:
        logger.print_log("info", f"Task already exists with ID: {existing_tasks[0].id}")
        return {
            "success": True,
            "message": "Task already exists.",
            "task_id": existing_tasks[0].id,
            "eventid": eventid,
            "filename": filename,
        }

    task = create_task(db=db_session, task_data=eventdetails)
    logger.print_log("info", f"Task {task.id} created successfully.")

    try:
        logger.print_log("info", f"Triggered damage assessment processing.")
        background_tasks.add_task(generate_damage_assessment, task.id, area, "roads")
    except Exception as e:
        update_task_status(db=db_session, taskid=task.id, status="error")
        logger.print_log(
            "error", f"Error generating damage assessment: {str(e)}", exc_info=True
        )
        raise HTTPException(
            status_code=500, detail="Error generating damage assessment."
        )

    return {
        "success": True,
        "status": "processing",
        "task_id": task.id,
        "eventid": eventid,
        "filename": filename,
    }
