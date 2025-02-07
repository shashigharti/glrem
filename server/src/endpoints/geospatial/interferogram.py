from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.orm import Session
from pydantic import BaseModel
from datetime import datetime

from src.utils.logger import logger
from src.crud.task import create_task, get_tasks, update_task_status
from src.database import get_db
from src.geospatial.helpers.interferogram import generate_interferogram
from src.config import *

router = APIRouter()


class InterferogramRequest(BaseModel):
    userid: int
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
    startdate: str
    enddate: str
    areaofinterest: str


@router.post("/interferogram")
async def interferogram(params: InterferogramRequest, db: Session = Depends(get_db)):
    credentials = {
        "username": ASF_USERNAME,
        "password": ASF_PASSWORD,
    }
    try:
        params_dict = params.model_dump()
        params_dict["eventdate"] = datetime.strptime(
            params_dict["eventdate"], "%d-%m-%Y"
        ).date()
        params_dict["startdate"] = datetime.strptime(
            params_dict["startdate"], "%Y-%m-%dT%H:%M:%SZ"
        )
        params_dict["enddate"] = datetime.strptime(
            params_dict["enddate"], "%Y-%m-%dT%H:%M:%SZ"
        )
        eventid = params_dict.get("eventid")
        eventtype = params_dict.get("eventtype")

        existing_tasks = get_tasks(
            db=db,
            latitude=params.latitude,
            longitude=params.longitude,
            eventtype=params.eventtype,
            analysis=params.analysis,
        )

        output = os.path.join(OUTPUT, eventtype, eventid)
        datadir = os.path.join(DATADIR, eventtype)
        workdir = os.path.join(WORKDIR, eventtype)

        if not existing_tasks:
            task = create_task(db=db, task_data=params_dict)
            logger.print_log("info", "Task created successfully.")

            logger.print_log("info", "Processing Interferogram.")
            generate_interferogram(params_dict, credentials, workdir, datadir, output)
            logger.print_log("info", "Successfully Generated Interferogram.")

            update_task_status(db=db, task_id=task.id, status="completed")
            logger.print_log("info", "Task updated successfully.")
        else:
            logger.print_log(
                "info", f"Task already exists with id: {existing_tasks[0].id}"
            )

    except Exception as e:
        logger.print_log("error", f"Error generating interferogram: {str(e)}")
        raise HTTPException(status_code=500, detail="Error generating interferogram.")

    return {"success": True, "filename": params.filename}
