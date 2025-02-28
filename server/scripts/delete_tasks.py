from src.models import Task
from src.database import SessionLocal


def delete_task_by_eventid(id):
    """Delete a task from the tasks table by event ID."""
    db = SessionLocal()
    try:
        deleted_rows = db.query(Task).filter(Task.id == id).delete()
        db.commit()
        if deleted_rows:
            print(f"Task with event ID '{id}' has been deleted successfully!")
        else:
            print(f"No task found with event ID '{id}'.")
    except Exception as e:
        db.rollback()
        print(f"Error during task deletion: {e}")
    finally:
        db.close()


def delete_tasks():
    """Delete all rows from the tasks table."""
    db = SessionLocal()
    try:
        db.query(Task).delete()
        db.commit()
        print("All tasks have been deleted successfully!")
    except Exception as e:
        db.rollback()
        print(f"Error during task deletion: {e}")
    finally:
        db.close()


if __name__ == "__main__":
    # delete_tasks()
    delete_task_by_eventid(2)
