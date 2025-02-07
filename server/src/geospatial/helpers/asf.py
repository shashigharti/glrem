import argparse
import asf_search as asf
from datetime import datetime


def get_scenes(params):
    scenes = []
    results = asf.search(**params)

    if not results:
        print("No Scenes Found")
        return scenes

    print(f"Found {len(results)} scenes:")
    for result in results:
        file_id = result.properties.get("fileID", "file ID not available")
        scenes.append(file_id.replace("-SLC", ""))

    SCENES = [
        "S1A_IW_SLC__1SDV_20171111T150004_20171111T150032_019219_0208AF_EE89",
        "S1B_IW_SLC__1SDV_20171117T145900_20171117T145928_008323_00EBAB_B716",
        "S1B_IW_SLC__1SDV_20171117T145926_20171117T145953_008323_00EBAB_AFB8",
    ]

    selected_scenes = [scene for scene in scenes if scene in SCENES]
    return selected_scenes


def get_bursts(params):
    bursts = []
    bursts_by_date = {}
    results = asf.search(**params)

    if not results:
        print("No Bursts Found")
        return bursts

    print(f"Found {len(results)} results:")
    for result in results:
        file_id = result.properties.get("fileID", "File ID not available")
        swath = result.properties.get("burst", {}).get("subswath", None)
        date = result.properties.get("startTime", "").split("T")[0]

        if "OPERA" in file_id or not swath:
            continue

        if date not in bursts_by_date:
            bursts_by_date[date] = {"files": [], "subswaths": set()}

        bursts_by_date[date]["files"].append(file_id)
        bursts_by_date[date]["subswaths"].add(swath)

    required_subswaths = {"IW1", "IW2", "IW3"}
    for date, burst_data in bursts_by_date.items():
        if required_subswaths.issubset(burst_data["subswaths"]):
            bursts.extend(burst_data["files"])
        else:
            print(
                f"Skipping {date}: Missing swaths {required_subswaths - burst_data['subswaths']}"
            )

    return bursts


def extract_times(scene):
    parts = scene.split("_")

    start_time_str = parts[5]
    end_time_str = parts[6]

    print(start_time_str, end_time_str)

    start_time = datetime.strptime(start_time_str, "%Y%m%dT%H%M%S")
    end_time = datetime.strptime(end_time_str, "%Y%m%dT%H%M%S")

    return start_time, end_time


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Download data")

    parser.add_argument("--dtype", type=str, help="Burst or Scene")

    args = parser.parse_args()

    bursts = []
    scenes = []

    area_of_interest = "LINESTRING(35.7 36, 37 38.8, 36.7 35.8, 38.7 38.5, 38 35.5)"
    if args.dtype == "burst":
        params = {
            "start": "2023-01-28T17:00:00Z",
            "end": "2023-02-10T16:59:59Z",
            "dataset": "SLC-BURST",
            "platform": ["Sentinel-1"],
            "processingLevel": ["SLC"],
            "beamMode": "IW",
            "polarization": "VV",
            "flightDirection": "Descending",
            "intersectsWith": area_of_interest,
        }
        bursts = get_bursts(params)

    area_of_interest = "LINESTRING(45.1557 35.4781,46.4695 33.9852)"
    if args.dtype == "scene":
        params = {
            "start": "2017-11-10T18:15:00Z",
            "end": "2017-11-17T18:14:59Z",
            "dataset": "SENTINEL-1",
            "platform": ["SENTINEL-1"],
            "processingLevel": ["SLC"],
            "beamMode": "IW",
            # "polarization": "VV+HH",
            "intersectsWith": area_of_interest,
        }
        scenes = get_scenes(params)
