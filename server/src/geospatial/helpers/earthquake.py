import pytz

from datetime import datetime, timedelta
from src.apis.usgs.connection import fetch_shakemap_data


def get_daterange(eventdate: str, days_before=10, days_after=10):
    """
    Generate a date range around the event date for a given number of days before and after.

    Parameters
    ----------
    eventdate : str
        The date of the event in "YYYY-MM-DD" format.
    days_before : int, optional
        The number of days before the event to include in the range (default is 10).
    days_after : int, optional
        The number of days after the event to include in the range (default is 10).

    Returns
    -------
    dict
        A dictionary with two keys:
        - 'startdate': The calculated start date in "YYYY-MM-DDTHH:MM:SSZ" format.
        - 'enddate': The calculated end date in "YYYY-MM-DDTHH:MM:SSZ" format.
    """

    event_date = datetime.strptime(eventdate, "%Y-%m-%d")
    event_date = pytz.UTC.localize(event_date)

    start_date = event_date - timedelta(days=days_before)
    end_date = event_date + timedelta(days=days_after)

    return {
        "startdate": start_date.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "enddate": end_date.strftime("%Y-%m-%dT%H:%M:%SZ"),
    }


def _apply_empirical_formula(magnitude):
    """
    Apply an empirical formula to estimate the radius of influence based on earthquake magnitude.

    Parameters
    ----------
    - magnitude (float): The magnitude of the earthquake.

    Returns
    -------
    - aoi (float): Estimated radius of influence.
    """
    radius = 10 * (magnitude**1.5)
    return radius


def _calculate_aoi_from_shakemap(shakemap_data):
    mmi_data = shakemap_data.get("mmi", [])
    aoi = sum(area for mmi, area in mmi_data if mmi >= 5)
    return aoi


def get_aoi(earthquake_id, magnitude):
    shakemap_data = fetch_shakemap_data(earthquake_id)

    if shakemap_data:
        aoi = _calculate_aoi_from_shakemap(shakemap_data)
    else:
        aoi = _apply_empirical_formula(magnitude)

    return aoi


if __name__ == "__main__":
    get_aoi("us6000jlqa", 7.5)
