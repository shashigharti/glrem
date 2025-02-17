from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.orm import Session
from pydantic import BaseModel
from datetime import datetime

from src.config import *
from src.utils.logger import logger
from src.database import get_db
from src.crud.task import create_task, get_tasks, update_task_status
from src.geospatial.helpers.earthquake import get_daterange
from src.geospatial.helpers.interferogram import generate_interferogram

router = APIRouter()


class InterferogramRequest(BaseModel):
    ukey: str
    eventid: str
    eventdate: str
    status: str
    location: str
    filename: str
    eventtype: str
    analysis: str
    country: str
    latitude: float
    longitude: float
    magnitude: float


@router.post("/interferogram")
def interferogram(
    params: InterferogramRequest,
    db: Session = Depends(get_db),
):
    try:
        params_dict = params.model_dump()

        eventdate = datetime.strptime(params_dict["eventdate"], "%Y-%m-%dT%H:%M:%SZ")
        params_dict["eventdate"] = eventdate

        daterange = get_daterange(eventdate, 10, 10)
        params_dict["startdate"] = datetime.strptime(
            daterange["startdate"], "%Y-%m-%dT%H:%M:%SZ"
        )
        params_dict["enddate"] = datetime.strptime(
            daterange["enddate"], "%Y-%m-%dT%H:%M:%SZ"
        )

        existing_tasks = get_tasks(
            db=db,
            latitude=params.latitude,
            longitude=params.longitude,
            eventtype=params.eventtype,
            analysis=params.analysis,
        )

        if existing_tasks:
            logger.print_log(
                "info", f"Task already exists with ID: {existing_tasks[0].id}"
            )
            return {
                "success": True,
                "message": "Task already exists.",
                "task_id": existing_tasks[0].id,
            }

        task = create_task(db=db, task_data=params_dict)
        logger.print_log("info", f"Task {task.id} created successfully.")

        logger.print_log("info", f"Triggered interferogram processing.")
        generate_interferogram(task.id)

        return {
            "success": True,
            "status": "processing",
            "task_id": task.id,
            "filename": params.filename,
        }

    except Exception as e:
        update_task_status(db=db, task_id=task.id, status="error")
        logger.print_log(
            "error", f"Error generating interferogram: {str(e)}", exc_info=True
        )
        raise HTTPException(status_code=500, detail="Error generating interferogram.")
