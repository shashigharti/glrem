from sqlalchemy.orm import Session
from src.models.task import Task


def create_task(db: Session, task_data: dict):
    task = Task(**task_data)
    db.add(task)
    db.commit()
    db.refresh(task)
    return task


def get_tasks(
    db: Session,
    eventid: str = None,
    latitude: float = None,
    longitude: float = None,
    filename: str = None,
    eventtype: str = None,
    analysis: str = None,
):
    query = db.query(Task)
    if eventid:
        query = query.filter(Task.eventtype == eventid)
    if latitude:
        query = query.filter(Task.latitude == latitude)
    if longitude:
        query = query.filter(Task.longitude == longitude)
    if filename:
        query = query.filter(Task.filename == filename)
    if eventtype:
        query = query.filter(Task.eventtype == eventtype)
    if analysis:
        query = query.filter(Task.analysis == analysis)
    return query.all()


def update_task_status(db: Session, task_id: int, status: str):
    task = db.query(Task).filter(Task.id == task_id).first()
    if task:
        task.status = status
        db.commit()
        db.refresh(task)
    return task
