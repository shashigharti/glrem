import json
import requests
import math
from geopy.distance import geodesic


def haversine_distance(lat1, lon1, lat2, lon2):
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


def get_square_bounding_box(lat, lon, half_side_km):
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


# Define earthquake ID
earthquakes = ["us6000jlqa", "us6000jllz", "us20002926", "us2000bmcg"]
# ["us6000jlqa", "us6000jllz", "us20002926", "us2000bmcg", "us2000ar20", "ci38457511"]
# Fetch earthquake details

for earthquake_id in earthquakes:
    event_url = f"https://earthquake.usgs.gov/fdsnws/event/1/query?format=geojson&eventid={earthquake_id}"
    event_response = requests.get(event_url)

    if event_response.status_code == 200:
        event_data = event_response.json()
        properties = event_data.get("properties", {})
        geometry = event_data.get("geometry", {})

        if geometry and "coordinates" in geometry:
            magnitude = properties.get("mag", None)
            longitude, latitude, _ = geometry["coordinates"]

            print(f"Earthquake ID: {earthquake_id}")
            print(f"Magnitude: {magnitude}")

            # Fetch intensity contour data (ShakeMap)
            intensity_url = f"https://earthquake.usgs.gov/product/shakemap/{earthquake_id}/us/1681495642674/download/cont_mmi.json"
            response = requests.get(intensity_url)

            mmi_5_radius = None  # Default

            if response.status_code == 200:
                intensity_contours = response.json()
                max_radius = 0

                if "features" in intensity_contours:
                    for feature in intensity_contours["features"]:
                        properties = feature.get("properties", {})
                        intensity = properties.get("value", None)  # Extract MMI value

                        if (
                            intensity is not None and intensity >= 5
                        ):  # Consider only MMI ≥ 5
                            if (
                                "geometry" in feature
                                and "coordinates" in feature["geometry"]
                            ):
                                for coord_set in feature["geometry"]["coordinates"]:
                                    for coord in coord_set:
                                        lon, lat = coord
                                        radius_km = haversine_distance(
                                            latitude, longitude, lat, lon
                                        )
                                        max_radius = max(max_radius, radius_km)

                                if intensity == 5:
                                    mmi_5_radius = max_radius

                    if mmi_5_radius:
                        print(
                            f"MMI = 5 Radius (from USGS ShakeMap): {round(mmi_5_radius, 2)} km"
                        )

            # If no ShakeMap data, use empirical formula
            if mmi_5_radius is None:
                mmi_5_radius = 10 ** (0.5 * magnitude - 1.5)
                print(
                    f"MMI = 5 Radius (from empirical formula): {round(mmi_5_radius, 2)} km"
                )

            half_side_km = mmi_5_radius / 2  # Half-side length for square

            # Compute bounding box
            bbox_coords = get_square_bounding_box(latitude, longitude, half_side_km)

            # Calculate width & height of bounding box
            bbox_width_km = geodesic(bbox_coords[0], bbox_coords[1]).kilometers
            bbox_height_km = geodesic(bbox_coords[0], bbox_coords[3]).kilometers

            print(f"Bounding Box Width: {round(bbox_width_km, 2)} km")
            print(f"Bounding Box Height: {round(bbox_height_km, 2)} km")

            # Create GeoJSON for bounding box
            geojson_data = {
                "type": "FeatureCollection",
                "features": [
                    {
                        "type": "Feature",
                        "properties": {
                            "earthquake_id": earthquake_id,
                            "mmi_5_radius_km": round(mmi_5_radius, 2),
                            "bbox_width_km": round(bbox_width_km, 2),
                            "bbox_height_km": round(bbox_height_km, 2),
                        },
                        "geometry": {"type": "Polygon", "coordinates": [bbox_coords]},
                    }
                ],
            }

            # Save GeoJSON file
            geojson_filename = f"/home/ubuntu/GuardianSpaceGeoCopy/data/output/earthquake/aois/{earthquake_id}_bbox.geojson"
            with open(geojson_filename, "w") as geojson_file:
                json.dump(geojson_data, geojson_file, indent=4)

            print(f"Square bounding box saved as {geojson_filename}")

    else:
        print(f"Error fetching earthquake details: HTTP {event_response.status_code}")
