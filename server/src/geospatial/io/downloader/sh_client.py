from sentinelhub import BBox, CRS, SentinelHubCatalog, DataCollection


def download(config, params):
    """
    Downloads Sentinel-2 Level-2A data from the Sentinel Hub catalog based on the specified parameters.

    Args:
        config (dict): Configuration dictionary containing necessary credentials and settings for accessing the Sentinel Hub.
        params (dict): Dictionary containing the parameters for the download, including:
            - epicenter_lat (float): Latitude of the epicenter of interest.
            - epicenter_lon (float): Longitude of the epicenter of interest.
            - radius_km (float): Radius (in kilometers) around the epicenter to define the area of interest.
            - time_interval_before (str): Time interval before the current date for the search (in ISO 8601 format).

    Returns:
        list: A list of search results from the Sentinel Hub catalog containing metadata about Sentinel-2 Level-2A imagery.

    Example:
        config = {...}
        params = {
            "epicenter_lat": 34.0522,
            "epicenter_lon": -118.2437,
            "radius_km": 50,
            "time_interval_before": "2022-01-01/2022-02-01"
        }
        results_before = download(config, params)
    """
    epicenter_lat = params["epicenter_lat"]
    epicenter_lon = params["epicenter_lon"]
    radius_km = params["radius_km"]
    time_interval_before = params["time_interval_before"]

    # Define the area of interest as a bounding box around the epicenter
    area_of_interest = BBox(
        bbox=[
            epicenter_lon - (radius_km / 111.32),
            epicenter_lat - (radius_km / 110.574),
            epicenter_lon + (radius_km / 111.32),
            epicenter_lat + (radius_km / 110.574),
        ],
        crs=CRS.WGS84,
    )

    # Initialize the catalog and search for Sentinel-2 L2A data
    catalog = SentinelHubCatalog(config=config)
    results_before = catalog.search(
        collection=DataCollection.SENTINEL2_L2A,
        bbox=area_of_interest,
        time=time_interval_before,
        fields={"include": ["id", "properties.datetime"]},
    )

    return results_before
