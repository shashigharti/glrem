import os
import io
import json
import base64
import botocore

from fastapi import APIRouter, HTTPException, Depends
from fastapi.responses import JSONResponse, StreamingResponse
from sqlalchemy.orm import Session

from src.database import get_db
from src.crud.task import get_tasks
from src.config import AWS_BUCKET_NAME, s3_client, AWS_PROCESSED_FOLDER
from src.geospatial.helpers.interferogram import generate_filename

router = APIRouter()


@router.get("/tiles")
async def get_tiles_endpoint(eventid: str, z: int, x: int, y: int):
    s3_key = os.path.join(AWS_PROCESSED_FOLDER, eventid, "tiles", f"{z}/{x}/{y}.png")
    print(s3_key)

    try:
        tile_object = s3_client.get_object(Bucket=AWS_BUCKET_NAME, Key=s3_key)
        tile_data = tile_object["Body"].read()

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal Server Error: {str(e)}")

    return StreamingResponse(io.BytesIO(tile_data), media_type="image/png")


@router.get("/files")
async def get_files_endpoint(
    eventid: str,
    ext: str = "png",
    responsetype: str = "url",
    db: Session = Depends(get_db),
):
    tasks = get_tasks(db, eventid=eventid)
    if not tasks:
        return JSONResponse(content={"detail": "File not found"})

    task = tasks[0]
    try:
        image_file_key = os.path.join(
            AWS_PROCESSED_FOLDER, eventid, f"{task.filename}.{ext}"
        )
        meta_file_key = os.path.join(
            AWS_PROCESSED_FOLDER, eventid, f"{task.filename}.geojson"
        )
        geojson_object = s3_client.get_object(Bucket=AWS_BUCKET_NAME, Key=meta_file_key)
        geojson_data = geojson_object["Body"].read().decode("utf-8")

        if responsetype == "url":

            return JSONResponse(
                content={
                    "base_url": "https://guardian-space-geospatial-data.s3.ap-south-1.amazonaws.com/",
                    "file_name": image_file_key,
                    "geojson": meta_file_key,
                }
            )

        png_object = s3_client.get_object(Bucket=AWS_BUCKET_NAME, Key=image_file_key)
        png_data = png_object["Body"].read()
        png_base64 = base64.b64encode(png_data).decode("utf-8")

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal Server Error: {str(e)}")

    return JSONResponse(
        content={
            "png_base64": png_base64,
            "geojson": json.loads(geojson_data),
        }
    )
