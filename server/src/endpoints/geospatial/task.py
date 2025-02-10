from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List, Optional
from pydantic import BaseModel

from src.database import get_db
from src.utils.logger import logger
from src.schemas.task import TaskResponse
from src.crud.task import get_tasks, update_task_status
from src.geospatial.helpers.interferogram import generate_interferogram

router = APIRouter()


class UpdateTaskStatusRequest(BaseModel):
    status: str


@router.get("/tasks/", response_model=List[TaskResponse])
def get_tasks_endpoint(
    userid: Optional[int] = None,
    db: Session = Depends(get_db),
):
    tasks = get_tasks(db, userid=userid)
    return tasks


@router.patch("/tasks/{task_id}/status", response_model=TaskResponse)
def update_task_status_endpoint(
    task_id: int,
    request: UpdateTaskStatusRequest,
    db: Session = Depends(get_db),
):
    task = update_task_status(db, task_id, request.status)
    if task is None:
        raise HTTPException(status_code=404, detail="Task not found")
    return task


@router.patch("/tasks/{task_id}/regenerate", response_model=TaskResponse)
def regenerate_task_endpoint(
    taskid: int,
    db: Session = Depends(get_db),
):
    task = get_tasks(db, eventid=taskid)

    if task is None:
        raise HTTPException(
            status_code=404, detail="Task not found or cannot be regenerated"
        )

    params = {
        "userid": task.userid,
        "eventid": task.eventid,
        "eventdate": task.eventdate,
        "status": task.status,
        "location": task.location,
        "filename": task.filename,
        "eventtype": task.eventtype,
        "analysis": task.analysis,
        "country": task.country,
        "latitude": task.latitude,
        "longitude": task.longitude,
        "magnitude": task.magnitude,
    }
    try:
        generate_interferogram(params)
    except Exception as e:
        logger.print_log("error", f"Error generating interferogram: {str(e)}")
        raise HTTPException(status_code=500, detail="Error generating interferogram.")

    return {"success": True, "filename": params.filename}
