import os
import boto3
from botocore.exceptions import NoCredentialsError

from src.config import AWS_ACCESS_KEY, AWS_SECRET_KEY, AWS_BUCKET_NAME
from src.utils.logger import log_data, logger


@log_data
def upload_file(filepath_src, filename_dest):
    s3 = boto3.client(
        "s3",
        aws_access_key_id=AWS_ACCESS_KEY,
        aws_secret_access_key=AWS_SECRET_KEY,
    )

    try:
        s3.upload_file(filepath_src, AWS_BUCKET_NAME, filename_dest)
        logger.print_log(
            "info",
            f"Successfully uploaded {filepath_src} to s3://{AWS_BUCKET_NAME}/{filename_dest}",
        )
    except NoCredentialsError:
        print("Credentials not available.")
        logger.print_log("error", f"Credentials not available.")
    except Exception as e:
        print(f"An error occurred: {str(e)}")
        logger.print_log("error", f"An error occurred: {str(e)}")


def copy_files_to_s3(
    folder, dest="app-analyzed-data", file_types=["tif", "png", "nc", "vtx", "geojson"]
):
    for filename in os.listdir(folder):
        ext = filename.split(".")[-1].lower()
        if ext in file_types:
            filename_dest = f"{dest}/{filename}"
            filename_src = f"{folder}/{filename}"

            logger.print_log(f"Uploading file:{filename_src} to {filename_dest}")
            upload_file(filename_src, filename_dest)
