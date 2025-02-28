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
    userid: Optional[str] = None,
    db: Session = Depends(get_db),
):
    try:
        tasks = get_tasks(db, userid=userid)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal Server Error: {str(e)}")
    return tasks


@router.delete("/tasks/{eventid}/")
async def delete_task_endpoint(
    eventid: str,
    db: Session = Depends(get_db),
):
    try:
        delete_task(db, eventid=eventid)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error deleting task: {str(e)}")
    return {"success": True}


@router.get("/tasks/{eventid}/status")
def get_task_status_endpoint(
    eventid: str,
    db: Session = Depends(get_db),
):
    try:
        tasks = get_tasks(db, eventid=eventid)
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Error getting task status: {str(e)}"
        )

    if not tasks:
        return JSONResponse(content={"detail": "File not found"})
    return JSONResponse(status_code=200, content={"status": tasks[0].status})


@router.post("/tasks/{taskid}/regenerate", response_model=TaskResponse)
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

    except Exception as e:
        logger.print_log(
            "error", f"Error generating interferogram: {str(e)}", exc_info=True
        )
        raise HTTPException(status_code=500, detail="Error generating interferogram.")

    return {
        "success": True,
        "status": "processing",
        "task_id": task.id,
        "filename": task.filename,
    }
