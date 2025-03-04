from datetime import timedelta
from src.apis.usgs.earthquake import fetch_shakemap_data


def get_daterange(eventdate, days_before=10, days_after=10):
    """
    Generate a date range around the event date for a given number of days before and after.

    Parameters
    ----------
    - eventdate (date) : The date of the event in "YYYY-MM-DD" format.
    - days_before (int, optional) : The number of days before the event to include in the range (default is 10).
    - days_after (int, optional) : The number of days after the event to include in the range (default is 10).

    Returns
    -------
    - dict (dict) : A dictionary with startdate and enddate in "YYYY-MM-DDTHH:MM:SSZ" format.
    """

    start_date = eventdate - timedelta(days=days_before)
    end_date = eventdate + timedelta(days=days_after)

    return {
        "startdate": start_date.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "enddate": end_date.strftime("%Y-%m-%dT%H:%M:%SZ"),
    }
