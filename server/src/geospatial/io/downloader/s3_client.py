import boto3
import os
import xml.etree.ElementTree as ET
from io import BytesIO
from geopy.geocoders import Nominatim


def download(
    config,
    bucket_name="sentinel-s1-l1c",
    output_folder="data/output",
    target_date=None,
    region_filter=None,
):
    """
    Reads metadata from Sentinel-1 manifest.safe files in an S3 bucket for a specific region
    and before a target date. Optionally extracts country details from geolocation data.

    Parameters:
        config (dict): AWS credentials {"AWS_ACCESS_KEY": ..., "AWS_SECRET_KEY": ...}.
        bucket_name (str): Name of the S3 bucket (default is Sentinel-1 bucket).
        output_folder (str): Directory to store downloaded data.
        target_date (str): The target date in "YYYY-MM-DD" format.
        region_filter (str): Optional region keyword to filter file paths.
    """
    if not target_date:
        raise ValueError("Please provide a target date in 'YYYY-MM-DD' format.")

    # Ensure the output folder exists
    os.makedirs(output_folder, exist_ok=True)

    # Initialize S3 client
    s3 = boto3.client(
        "s3",
        aws_access_key_id=config["AWS_ACCESS_KEY"],
        aws_secret_access_key=config["AWS_SECRET_KEY"],
    )

    # List objects in the bucket
    paginator = s3.get_paginator("list_objects_v2")
    response_iterator = paginator.paginate(Bucket=bucket_name)

    for response in response_iterator:
        if "Contents" in response:
            for obj in response["Contents"]:
                key = obj["Key"]
                last_modified = obj["LastModified"]

                if key.endswith("manifest.safe") and (
                    region_filter is None or region_filter in key
                ):
                    print(f"Reading metadata from: {key}")

                    # Fetch and parse the manifest.safe file
                    manifest_data = s3.get_object(Bucket=bucket_name, Key=key)[
                        "Body"
                    ].read()
                    metadata = parse_manifest_safe(manifest_data)

                    # Print metadata
                    print(f"Metadata for {key}:\n{metadata}\n")

                    # Extract geolocation and country details
                    geolocation_data = extract_geolocation_from_manifest(manifest_data)
                    country = reverse_geocode_geolocation(geolocation_data)
                    print(f"Country for {key}: {country}\n")


def parse_manifest_safe(manifest_data):
    """
    Parses a manifest.safe file and extracts key metadata.

    Parameters:
        manifest_data (bytes): XML content of the manifest.safe file.

    Returns:
        dict: A dictionary containing extracted metadata.
    """
    try:
        root = ET.parse(BytesIO(manifest_data)).getroot()
        namespaces = {"safe": "http://www.esa.int/safe/sentinel-1.0"}

        # Extract metadata
        product_type = root.find(".//safe:productType", namespaces)
        processing_level = root.find(".//safe:processingLevel", namespaces)
        start_time = root.find(".//safe:startTime", namespaces)
        stop_time = root.find(".//safe:stopTime", namespaces)

        return {
            "Product Type": product_type.text if product_type is not None else "N/A",
            "Processing Level": (
                processing_level.text if processing_level is not None else "N/A"
            ),
            "Start Time": start_time.text if start_time is not None else "N/A",
            "Stop Time": stop_time.text if stop_time is not None else "N/A",
        }
    except Exception as e:
        print(f"Error parsing manifest.safe: {e}")
        return {}


def extract_geolocation_from_manifest(manifest_data):
    """
    Extracts geolocation data from a manifest.safe file.

    Parameters:
        manifest_data (bytes): XML content of the manifest.safe file.

    Returns:
        dict: A dictionary containing bounding box coordinates (min/max lat/lon).
    """
    try:
        root = ET.parse(BytesIO(manifest_data)).getroot()
        namespaces = {"safe": "http://www.esa.int/safe/sentinel-1.0"}

        latitudes = []
        longitudes = []

        for point in root.findall(".//geolocationGridPoint"):
            lat = point.find("latitude")
            lon = point.find("longitude")
            if lat is not None and lon is not None:
                latitudes.append(float(lat.text))
                longitudes.append(float(lon.text))

        return {
            "min_latitude": min(latitudes),
            "max_latitude": max(latitudes),
            "min_longitude": min(longitudes),
            "max_longitude": max(longitudes),
        }
    except Exception as e:
        print(f"Error extracting geolocation: {e}")
        return None


def reverse_geocode_geolocation(geolocation_data):
    """
    Determines the country from geolocation data using reverse geocoding.

    Parameters:
        geolocation_data (dict): Bounding box coordinates (min/max lat/lon).

    Returns:
        str: Country name.
    """
    try:
        geolocator = Nominatim(user_agent="geoapiExercises")

        # Use the center of the bounding box for reverse geocoding
        center_lat = (
            geolocation_data["min_latitude"] + geolocation_data["max_latitude"]
        ) / 2
        center_lon = (
            geolocation_data["min_longitude"] + geolocation_data["max_longitude"]
        ) / 2
        location = geolocator.reverse((center_lat, center_lon), language="en")

        if location and "country" in location.raw["address"]:
            return location.raw["address"]["country"]
        return "Unknown country"
    except Exception as e:
        print(f"Error during reverse geocoding: {e}")
        return "Error"
