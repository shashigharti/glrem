import json
import requests
from datetime import datetime
from geopy.geocoders import Nominatim

"""
This module provides functions to fetch and process earthquake event data from the USGS API.
"""


def fetch_shakemap_data(earthquake_id):
    """
    Fetches ShakeMap data for a given earthquake from the USGS API.

    Parameters
    ----------
    - earthquake_id (str): The unique identifier for the earthquake event.

    Returns
    -------
    - dict : Returns the ShakeMap data in JSON format if successful, otherwise None if there is an error.
    """
    url = f"https://earthquake.usgs.gov/earthquakes/eventpage/{earthquake_id}/shakemap"
    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
    except requests.exceptions.Timeout:
        print("The request timed out.")
        return
    except requests.exceptions.RequestException as e:
        print(f"An error occurred: {e}")
        return None

    if not response.status_code == 200:
        return None

    return json.loads(response.text)


def get_data(event_id):
    """
    Fetch earthquake event data from the USGS API based on the given event ID.

    Parameters
    ----------
    - event_id (str) : The USGS event ID of the earthquake.

    Returns
    -------
    - dict (dict) : JSON response with event details if successful, otherwise None.
    """
    url = f"https://earthquake.usgs.gov/fdsnws/event/1/query?format=geojson&eventid={event_id}"
    response = requests.get(url)

    if response.status_code == 200:
        return response.json()

    print(
        f"Failed to fetch data for event ID {event_id}. Status code: {response.status_code}"
    )
    return None


def format_data(event):
    """
    Extract relevant earthquake event details including latitude and longitude.

    Parameters
    ----------
    - event (dict) : JSON response from the USGS API.

    Returns
    -------
    - dict (dict) : Formatted event data including event date, location, magnitude, latitude, and longitude.
    """
    properties = event.get("properties", {})
    geometry = event.get("geometry", {})
    coordinates = geometry.get("coordinates", [None, None])
    latitude = coordinates[0]
    longitude = coordinates[1]
    event_time = properties.get("time")
    geolocator = Nominatim(user_agent="earthquake_country")

    location = geolocator.reverse(
        (latitude, longitude), language="en", exactly_one=True
    )
    address = location.address if location else "Unknown location"
    country = address.split(",")[-1].strip()

    if event_time:
        event_time = datetime.utcfromtimestamp(event_time / 1000)

    return {
        "eventdate": event_time,
        "location": properties.get("place"),
        "magnitude": properties.get("mag"),
        "longitude": latitude,
        "latitude": longitude,
        "country": country.lower(),
        "eventtype": "earthquake",
    }


if __name__ == "__main__":
    event_data = get_data("us6000jlqa")
    print(format_data(event_data))
