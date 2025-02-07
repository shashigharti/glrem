from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from src.database import get_db
from src.schemas.task import TaskResponse
from src.crud.task import get_tasks, update_task_status
from pydantic import BaseModel

router = APIRouter()


class UpdateTaskStatusRequest(BaseModel):
    status: str


@router.get("/tasks/", response_model=List[TaskResponse])
def get_tasks_endpoint(
    db: Session = Depends(get_db),
):
    tasks = get_tasks(db)
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
