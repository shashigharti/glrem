from datetime import datetime
import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
from main import app
from src.crud.task import get_tasks, update_task_status

client = TestClient(app)

test_task = {
    "id": 1,
    "location": "Gaziantep, Turkey",
    "status": "processing",
    "latitude": 37.0662,
    "longitude": 37.3833,
    "filename": "interferogram_gaziantep_feb2023_0.0.tif",
    "eventtype": "earthquake",
    "analysis": "interferogram",
    "date": datetime(2023, 2, 6).isoformat(),
}


def mock_get_tasks(db: Session, location: str = None, status: str = None):
    return [test_task]


def mock_update_task_status(db: Session, task_id: int, status: str):
    if task_id == 1:
        return {**test_task, "status": status}
    return None


@pytest.fixture(autouse=True)
def override_dependencies():
    app.dependency_overrides[get_tasks] = mock_get_tasks
    app.dependency_overrides[update_task_status] = mock_update_task_status
    yield
    app.dependency_overrides = {}


def test_get_tasks():
    response = client.get("/geospatial/tasks/")
    assert response.status_code == 200
    print(response.json(), test_task)
    assert response.json() == [test_task]


def test_update_task_status():
    response = client.patch("/geospatial/tasks/1/status", json={"status": "processing"})
    assert response.status_code == 200
    assert response.json() == {**test_task, "status": "processing"}
