from fastapi.testclient import TestClient
from main import app

client = TestClient(app)


def test_get_tile_success():
    eventid = "us6000jlqa"
    z = 5
    x = 19
    y = 19

    response = client.get(f"/geospatial/tiles?eventid={eventid}&z={z}&x={x}&y={y}")
    assert response.status_code == 200
    assert response.headers["Content-Type"] == "image/png"
    assert len(response.content) > 0
