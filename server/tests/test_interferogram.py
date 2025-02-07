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
        eventdate="06-02-2023",
        status="processing",
        startdate="2023-01-28T17:00:00Z",
        enddate="2023-02-10T16:59:59Z",
        areaofinterest="LINESTRING(35.7 36, 37 38.8, 36.7 35.8, 38.7 38.5, 38 35.5)",
    )

    params_dict = params.model_dump()
    response = client.post("/geospatial/interferogram", json=params_dict)
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
        startdate="2017-11-10T18:15:00Z",
        enddate="2017-11-17T18:14:59Z",
        areaofinterest="LINESTRING(45.1557 35.4781,46.4695 33.9852)",
    )

    params_dict = params.model_dump()
    response = client.post("/geospatial/interferogram", json=params_dict)
    print(response)

    assert response.status_code == 200
    assert response.json() == {
        "success": True,
        "filename": "earthquake-intf",
    }
