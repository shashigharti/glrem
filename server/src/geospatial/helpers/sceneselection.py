import os
import numpy as np
import pandas as pd
import asf_search as asf
import json
import requests
import math
from geopy.distance import geodesic

from src.config.constants import (
    OUTPUT,
    PERP_BASELINE_MIN,
    PERP_BASELINE_MAX,
    TEMP_BASELINE,
    SCENES_FILENAME,
    USGS_ENDPOINT,
)


def _get_shakemap_url(earthquake_id):
    """
    Fetch the ShakeMap URL for a given earthquake ID.
    """
    params = {"format": "geojson", "eventid": earthquake_id}

    response = requests.get(USGS_ENDPOINT, params=params)
    if response.status_code != 200:
        return None

    data = response.json()
    products = data.get("properties", {}).get("products", {})

    if "shakemap" in products:
        shakemap = products["shakemap"][0]  # Get the latest ShakeMap entry
        return shakemap.get("contents", {}).get("download/cont_mmi.json", {}).get("url")

    return None


def _haversine_distance(lat1, lon1, lat2, lon2):
    """Calculate the great-circle distance between two points on the Earth (in km)."""
    R = 6371  # Earth’s radius in km
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = (
        math.sin(dlat / 2) ** 2
        + math.cos(math.radians(lat1))
        * math.cos(math.radians(lat2))
        * math.sin(dlon / 2) ** 2
    )
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return R * c


def _get_bounding_box(lat, lon, half_side_km):
    """Compute a square bounding box centered at (lat, lon)."""
    min_lat = geodesic(kilometers=half_side_km).destination((lat, lon), 180).latitude
    max_lat = geodesic(kilometers=half_side_km).destination((lat, lon), 0).latitude
    min_lon = geodesic(kilometers=half_side_km).destination((lat, lon), 270).longitude
    max_lon = geodesic(kilometers=half_side_km).destination((lat, lon), 90).longitude
    return [
        (min_lon, min_lat),
        (max_lon, min_lat),
        (max_lon, max_lat),
        (min_lon, max_lat),
        (min_lon, min_lat),
    ]


def generate_aoi(earthquake_id):
    """Fetch earthquake details and compute bounding box based on MMI 5 radius."""

    event_url = f"{USGS_ENDPOINT}?format=geojson&eventid={earthquake_id}"
    event_response = requests.get(event_url)

    if event_response.status_code != 200:
        print(f"Error fetching earthquake details: HTTP {event_response.status_code}")
        return

    event_data = event_response.json()
    properties = event_data.get("properties", {})
    geometry = event_data.get("geometry", {})

    if not geometry or "coordinates" not in geometry:
        print("Invalid earthquake data.")
        return

    magnitude = properties.get("mag", None)
    longitude, latitude, _ = geometry["coordinates"]

    print(f"Earthquake ID: {earthquake_id}")
    print(f"Magnitude: {magnitude}")

    shakemap_url = _get_shakemap_url
    response = requests.get(shakemap_url)

    radius = None  # mmi 5

    if response.status_code == 200:
        intensity_contours = response.json()
        radius = 0

        if "features" in intensity_contours:
            for feature in intensity_contours["features"]:
                properties = feature.get("properties", {})
                intensity = properties.get("value", None)

                if intensity is not None and intensity >= 5:
                    if "geometry" in feature and "coordinates" in feature["geometry"]:
                        for coord_set in feature["geometry"]["coordinates"]:
                            for coord in coord_set:
                                lon, lat = coord
                                radius_km = _haversine_distance(
                                    latitude, longitude, lat, lon
                                )
                                max_radius = max(max_radius, radius_km)

                        if intensity == 5:
                            radius = max_radius
    if radius is None:
        radius = 10 ** (0.5 * magnitude - 1.5)
        print(f"MMI = 5 Radius (from empirical formula): {round(radius, 2)} km")
    else:
        print(f"MMI = 5 Radius (from USGS ShakeMap): {round(radius, 2)} km")

    half_km = radius / 2
    coords = _get_bounding_box(latitude, longitude, half_km)

    width_km = geodesic(coords[0], coords[1]).kilometers
    height_km = geodesic(coords[0], coords[3]).kilometers

    print(f"Bounding Box Width: {round(width_km, 2)} km")
    print(f"Bounding Box Height: {round(height_km, 2)} km")

    geojson_data = {
        "type": "FeatureCollection",
        "features": [
            {
                "type": "Feature",
                "properties": {
                    "earthquake_id": earthquake_id,
                    "radius_km": round(radius, 2),
                    "width_km": round(width_km, 2),
                    "height_km": round(height_km, 2),
                },
                "geometry": {"type": "Polygon", "coordinates": [coords]},
            }
        ],
    }

    geojson_filename = f"{earthquake_id}_bbox.geojson"
    with open(geojson_filename, "w") as geojson_file:
        json.dump(geojson_data, geojson_file, indent=4)

    print(f"Square bounding box saved as {geojson_filename}")
    return geojson_filename


def find_matching_scenes(scenes):
    """
    Query Sentinel-1 scenes within a given geographical region and time period.
    """

    candidates = []
    tempbaselinefilename = "tmpbaseline.csv"

    # Process each scene to find baseline matches
    for scene_id in scenes:
        print(f"Processing: {scene_id}")
        results = asf.stack_from_id(scene_id)

        if not results:
            continue

        response_df = pd.DataFrame([feature.properties for feature in results])
        tmpbaseline_filepath = os.path.join(OUTPUT, tempbaselinefilename)
        response_df.to_csv(tmpbaseline_filepath, index=False)

        baseline_df = pd.read_csv(tmpbaseline_filepath).replace("None", np.nan)
        baseline_df.dropna(
            subset=["temporalBaseline", "perpendicularBaseline"], inplace=True
        )
        baseline_df[["temporalBaseline", "perpendicularBaseline"]] = baseline_df[
            ["temporalBaseline", "perpendicularBaseline"]
        ].apply(pd.to_numeric)

        baseline_filtered = baseline_df[
            (baseline_df["temporalBaseline"].abs() <= TEMP_BASELINE)
            & (PERP_BASELINE_MIN <= baseline_df["perpendicularBaseline"].abs())
            & (baseline_df["perpendicularBaseline"].abs() <= PERP_BASELINE_MAX)
        ]

        if not baseline_filtered.empty:
            baseline_filtered.rename(
                columns={
                    "fileName": "MatchID",
                    "pathNumber": "Orbit",
                    "flightDirection": "Pass",
                },
                inplace=True,
            )
            baseline_filtered.insert(0, "ReferenceID", scene_id)
            candidates.append(baseline_filtered)

    if not candidates:
        print("No matching baseline scenes found.")
        return

    candidates_df = pd.concat(candidates, ignore_index=True)
    candidates_df["ReferenceDate"] = pd.to_datetime(
        candidates_df["ReferenceID"].str[17:25], format="%Y%m%d"
    )
    candidates_df["MatchDate"] = pd.to_datetime(
        candidates_df["MatchID"].str[17:25], format="%Y%m%d"
    )
    candidates_df["inAOInDates"] = candidates_df["MatchID"].isin(scene_id)
    candidates_df["Download"] = False
    candidates_df.sort_values(by=["inAOInDates"], ascending=False, inplace=True)

    output_filepath = os.path.join(OUTPUT, SCENES_FILENAME)
    candidates_df.to_csv(output_filepath, index=False)

    os.remove(tempbaselinefilename)
    return candidates_df


def main():
    scenes = [
        "S1A_IW_SLC__1SDV_20230217T032641_20230217T032708_047270_05AC3F_7AA7-SLC",
        "S1A_IW_SLC__1SDV_20230122T034222_20230122T034249_046891_059F84_1763-SLC",
    ]
    find_matching_scenes(scenes)


if __name__ == "__main__":
    main()
