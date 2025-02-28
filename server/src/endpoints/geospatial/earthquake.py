from fastapi import APIRouter
import requests

from src.config import USGS_ENDPOINT

router = APIRouter()


@router.get("/earthquakes")
def get_earthquakes(
    starttime: str, endtime: str, coordinates: str, minmagnitude: float = 7.0
):
    min_lat, max_lat, min_lon, max_lon = map(float, coordinates.split(","))

    params = {
        "format": "geojson",
        "starttime": starttime,
        "endtime": endtime,
        "minlatitude": min_lat,
        "maxlatitude": max_lat,
        "minlongitude": min_lon,
        "maxlongitude": max_lon,
        "minmagnitude": minmagnitude,
    }

    response = requests.get(USGS_ENDPOINT, params=params)
    return (
        response.json()
        if response.status_code == 200
        else {"error": "Failed to fetch data"}
    )
