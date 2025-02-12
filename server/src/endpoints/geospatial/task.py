import os
import subprocess
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List, Optional
from pydantic import BaseModel

from src.database import get_db
from src.utils.logger import logger
from src.schemas.task import TaskResponse
from src.crud.task import get_tasks, update_task_status

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

    try:
        logger.print_log("info", f"Task {task.id} created successfully.")

        command = [
            "/home/ubuntu/envs/guardian/bin/python",
            "-m",
            "src.geospatial.helpers.interferogram",
            str(task.id),
        ]
        env = os.environ.copy()
        env["GMTSAR_PATH"] = "/usr/local/GMTSAR"
        env["PATH"] = f"{env['GMTSAR_PATH']}/bin:{env['PATH']}"
        process = subprocess.Popen(
            command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, env=env
        )

        logger.print_log(
            "info", f"Triggered interferogram processing with PID {process.pid}."
        )
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
