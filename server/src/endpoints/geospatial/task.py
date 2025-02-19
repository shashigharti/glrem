from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from typing import List, Optional
from pydantic import BaseModel

from src.database import get_db
from src.utils.logger import logger
from src.schemas.task import TaskResponse
from src.crud.task import get_tasks, delete_task
from src.geospatial.helpers.interferogram import generate_interferogram

router = APIRouter()


class UpdateTaskStatusRequest(BaseModel):
    status: str


@router.get("/tasks", response_model=List[TaskResponse])
def get_tasks_endpoint(
    ukey: Optional[str] = None,
    db: Session = Depends(get_db),
):
    try:
        tasks = get_tasks(db, ukey=ukey)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal Server Error: {str(e)}")
    return tasks


@router.delete("/tasks/{task_id}/")
async def delete_task_endpoint(
    task_id: int,
    db: Session = Depends(get_db),
):
    try:
        delete_task(db, task_id=task_id)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error deleting task: {str(e)}")
    return {"success": True}


@router.get("/tasks/{task_or_event_id}/status")
def get_task_status_endpoint(
    task_or_event_id: str,
    db: Session = Depends(get_db),
):
    try:
        tasks = get_tasks(db, taskid=task_or_event_id)
        if not tasks:
            tasks = get_tasks(db, eventid=task_or_event_id)
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Error getting task status: {str(e)}"
        )

    if not tasks:
        raise HTTPException(status_code=404, detail="Task not found")
    return JSONResponse(status_code=200, content={"detail": tasks[0].status})


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

    try:
        logger.print_log("info", f"Triggered interferogram processing.")
        generate_interferogram(task.id)

        return {
            "success": True,
            "status": "processing",
            "task_id": task.id,
            "filename": task.filename,
        }

    except Exception as e:
        logger.print_log(
            "error", f"Error generating interferogram: {str(e)}", exc_info=True
        )
        raise HTTPException(status_code=500, detail="Error generating interferogram.")
