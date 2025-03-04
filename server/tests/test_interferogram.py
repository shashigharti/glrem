from fastapi.testclient import TestClient
from src.endpoints.geospatial.interferogram import InterferogramRequest
from main import app

client = TestClient(app)


def test_interferogram_turkey():
    params = InterferogramRequest(
        userid=1,
        latitude=37.1962,
        longitude=38.0106,
        eventid="us6000jlqa",
        country="turkey",
        location="Elbistan earthquake, Kahramanmaras earthquake sequence",
        filename="earthquake-intf",
        eventtype="earthquake",
        analysis="Interferogram",
        eventdate="2023-02-06",
        status="processing",
        magnitude=5.0,
    )

    params_dict = params.model_dump()
    response = client.post("/earthquakes/interferogram", json=params_dict)
    print(response)

    assert response.status_code == 200
    assert response.json() == {
        "success": True,
        "filename": "earthquake-intf",
    }


def test_interferogram_iraq():
    params = InterferogramRequest(
        userid=1,
        eventid="us7000jlqa",
        latitude=35,
        longitude=46,
        country="iraq",
        location="Iraq, near Halabja (2017 November 12 Earthquake)",
        filename="iraq_intf",
        eventtype="earthquake",
        analysis="Interferogram",
        eventdate="12-11-2017",
        status="processing",
        magnitude=5.0,
    )

    params_dict = params.model_dump()
    response = client.post("/earthquakes/interferogram", json=params_dict)
    print(response)

    assert response.status_code == 200
    assert response.json() == {
        "success": True,
        "filename": "earthquake-intf",
    }
