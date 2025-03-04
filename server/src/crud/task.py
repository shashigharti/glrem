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
    taskid: int = None,
    userid: int = None,
    eventid: str = None,
    latitude: float = None,
    longitude: float = None,
    filename: str = None,
    eventtype: str = None,
    analysis: str = None,
    asset: str = None,
):
    query = db.query(Task)
    if taskid:
        query = query.filter(Task.id == taskid)
    if userid:
        query = query.filter(Task.userid == userid)
    if eventid:
        query = query.filter(Task.eventid == eventid)
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
    if analysis:
        query = query.filter(Task.asset == asset)
    return query.all()


def update_task_status(db: Session, taskid: int, status: str):
    task = db.query(Task).filter(Task.id == taskid).first()
    if task:
        task.status = status
        db.commit()
        db.refresh(task)
    return task


def delete_task(db: Session, eventid: str):
    task = db.query(Task).filter(Task.eventid == eventid).first()
    if task:
        db.delete(task)
        db.commit()
