from datetime import datetime
from src.models import Task
from src.database import SessionLocal


def add_task():
    """Add a new task to the tasks table."""
    db = SessionLocal()
    try:
        new_task = Task(
            eventid="us6000jlqa",
            location="Elbistan, Turkey",
            latitude=38.011,
            longitude=37.196,
            magnitude=7.5,
            filename="earthquake-us6000jlqa-changedetection",
            eventtype="earthquake",
            analysis="changedetection",
            country="Turkey",
            eventdate=datetime.strptime("2023-02-06T10:24:48", "%Y-%m-%dT%H:%M:%S"),
            startdate=datetime.strptime("2023-02-01T00:00:00", "%Y-%m-%dT%H:%M:%S"),
            enddate=datetime.strptime("2023-02-10T23:59:59", "%Y-%m-%dT%H:%M:%S"),
            areaofinterest="",
            status="processing",
            userid="aliraza",
        )

        db.add(new_task)
        db.commit()
        print("Task added successfully!")
    except Exception as e:
        db.rollback()
        print(f"Error adding task: {e}")
    finally:
        db.close()


if __name__ == "__main__":
    add_task()
