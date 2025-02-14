import io
import os
import base64
import json
from fastapi import APIRouter, HTTPException
from fastapi.responses import JSONResponse, StreamingResponse
import botocore

from src.config import AWS_BUCKET_NAME, s3_client, AWS_PROCESSED_FOLDER

router = APIRouter()


@router.get("/tiles")
async def get_tile(eventid: str, z: int, x: int, y: int):
    s3_key = os.path.join(AWS_PROCESSED_FOLDER, eventid, "tiles", f"{z}/{x}/{y}.png")
    print(s3_key)

    try:
        tile_object = s3_client.get_object(Bucket=AWS_BUCKET_NAME, Key=s3_key)
        tile_data = tile_object["Body"].read()
        return StreamingResponse(io.BytesIO(tile_data), media_type="image/png")

    except s3_client.exceptions.NoSuchKey:
        raise HTTPException(status_code=404, detail="Tile not found")
    except botocore.exceptions.ClientError as e:
        raise HTTPException(status_code=500, detail=f"Connection Error: {str(e)}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal Server Error: {str(e)}")


@router.get("/get-files")
async def get_files(filename: str, eventid: str):
    try:

        image_file_key = os.path.join(AWS_PROCESSED_FOLDER, eventid, f"{filename}.png")
        meta_file_key = os.path.join(
            AWS_PROCESSED_FOLDER, eventid, f"{filename}.geojson"
        )
        print("files", image_file_key, meta_file_key)

        png_object = s3_client.get_object(Bucket=AWS_BUCKET_NAME, Key=image_file_key)
        png_data = png_object["Body"].read()
        png_base64 = base64.b64encode(png_data).decode("utf-8")

        geojson_object = s3_client.get_object(Bucket=AWS_BUCKET_NAME, Key=meta_file_key)
        geojson_data = geojson_object["Body"].read().decode("utf-8")

        return JSONResponse(
            content={
                "png_base64": png_base64,
                "geojson": json.loads(geojson_data),
            }
        )

    except s3_client.exceptions.NoSuchKey:
        raise HTTPException(status_code=404, detail="File not found")
    except botocore.exceptions.ClientError as e:
        raise HTTPException(status_code=500, detail=f"Connection Error: {str(e)}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal Server Error: {str(e)}")
