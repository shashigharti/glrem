import datetime
import requests

"""
This module provides functions to fetch earthquake data from the USGS Earthquake API.
It retrieves and prints information about earthquakes that meet certain criteria.
"""


def fetch_earthquake_data():
    """
    Fetches earthquake data from the USGS API for the past 5 years.
    Prints details about the latest earthquakes including magnitude, depth, and location.
    """
    endpoint = "https://earthquake.usgs.gov/fdsnws/event/1/query"
    params = {
        "format": "geojson",
        "starttime": "2019-12-16",
        "endtime": "2024-12-16",
        "orderby": "time",
        "minmagnitude": 5,
    }

    try:
        response = requests.get(endpoint, params=params, timeout=10)
        response.raise_for_status()
    except requests.exceptions.Timeout:
        print("The request timed out.")
        return
    except requests.exceptions.RequestException as e:
        print(f"An error occurred: {e}")
        return

    if response.status_code == 200:
        data = response.json()
        print("Latest Earthquakes (Past 5 Years):\n")
        for feature in data["features"][:10]:
            mag = feature["properties"]["mag"]
            place = feature["properties"]["place"]
            time = datetime.datetime.utcfromtimestamp(
                feature["properties"]["time"] / 1000
            )
            depth = feature["geometry"]["coordinates"][2]
            print(
                f"Time: {time}, Magnitude: {mag}, Depth: {depth} km, Location: {place}"
            )
    else:
        print(f"Error: {response.status_code}")


if __name__ == "__main__":
    fetch_earthquake_data()
