from src.models import Task
from src.database import SessionLocal


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
    delete_tasks()
