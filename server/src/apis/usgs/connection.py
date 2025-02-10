import json
import requests

"""
This module provides functions to fetch earthquake data from the USGS Earthquake API.
It retrieves and prints information about earthquakes that meet certain criteria.
"""


def fetch_shakemap_data(earthquake_id):
    """
    Fetches ShakeMap data for a given earthquake from the USGS API.

    Parameters
    ----------
    earthquake_id : str
        The unique identifier for the earthquake event.

    Returns
    -------
    dict or None
        Returns the ShakeMap data in JSON format if successful, otherwise None if there is an error.
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


if __name__ == "__main__":
    fetch_shakemap_data("us6000jlqa")
