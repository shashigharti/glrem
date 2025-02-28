from fastapi import APIRouter, HTTPException, Depends, BackgroundTasks
from sqlalchemy.orm import Session
from pydantic import BaseModel
from datetime import datetime
from typing import Optional

from src.config import *
from src.database import get_db
from src.utils.logger import logger
from src.utils.common import generate_filename
from src.apis.usgs.earthquake import get_data, format_data
from src.crud.task import create_task, get_tasks, update_task_status
from src.geospatial.helpers.earthquake import get_daterange

from src.geospatial.helpers.change_detection import (
    change_detection,
)

router = APIRouter()


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
        background_tasks.add_task(change_detection, task.id)
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
