import os
import io
import json
import base64
from datetime import datetime

from fastapi import APIRouter, HTTPException, Depends, BackgroundTasks
from fastapi.responses import JSONResponse, StreamingResponse
from sqlalchemy.orm import Session
from pydantic import BaseModel

from src.utils.logger import logger
from src.utils.common import generate_filename
from src.database import get_db
from src.crud.task import create_task, get_tasks, update_task_status
from src.config import AWS_BUCKET_NAME, s3_client, AWS_PROCESSED_FOLDER
from src.apis.usgs.earthquake import get_data, format_data
from src.geospatial.helpers.earthquake import get_daterange
from src.geospatial.helpers.inundation import generate_inundation

router = APIRouter()


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


class InterferogramRequest(BaseModel):
    userid: str
    eventid: str


@router.post("/inundation")
async def generate_interferogram_endpoint(
    params: InterferogramRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
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

    analysis = "inundation"
    eventtype = "flood"
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
        background_tasks.add_task(generate_inundation, task.id)
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


@router.get("/inundation/files")
async def get_flood_inundation_files_endpoint(
    eventid: str,
    ext: str = "png",
    responsetype: str = "url",
    db: Session = Depends(get_db),
):
    tasks = get_tasks(db, eventid=eventid, eventtype="flood", analysis="inundation")
    if not tasks:
        return JSONResponse(content={"detail": "File not found"})

    task = tasks[0]
    try:
        image_file_key = os.path.join(
            AWS_PROCESSED_FOLDER, task.eventtype, eventid, f"{task.filename}.{ext}"
        )
        meta_file_key = os.path.join(
            AWS_PROCESSED_FOLDER, task.eventtype, eventid, f"{task.filename}.geojson"
        )
        geojson_object = s3_client.get_object(Bucket=AWS_BUCKET_NAME, Key=meta_file_key)
        geojson_data = geojson_object["Body"].read().decode("utf-8")

        if responsetype == "url":

            return JSONResponse(
                content={
                    "file_name": image_file_key,
                    "geojson": meta_file_key,
                }
            )

        png_object = s3_client.get_object(Bucket=AWS_BUCKET_NAME, Key=image_file_key)
        png_data = png_object["Body"].read()
        png_base64 = base64.b64encode(png_data).decode("utf-8")

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal Server Error: {str(e)}")

    return JSONResponse(
        content={
            "png_base64": png_base64,
            "geojson": json.loads(geojson_data),
        }
    )


@router.get("/inundation/files")
async def get_flood_inundation_files_endpoint(
    eventid: str,
    ext: str = "tif",
    db: Session = Depends(get_db),
):
    tasks = get_tasks(db, eventid=eventid, eventtype="flood", analysis="inundation")
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
async def get_flood_damageassessment_files_endpoint(
    eventid: str,
    ext: str = "geojson",
    assettype: str = "buildings",
    db: Session = Depends(get_db),
):
    tasks = get_tasks(
        db, eventid=eventid, eventtype="flood", analysis="damageassessment"
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
