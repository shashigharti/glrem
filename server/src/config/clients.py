import boto3
from src.config.constants import AWS_ACCESS_KEY, AWS_SECRET_KEY


def get_s3_client():
    """Creates and returns an S3 client with error handling."""
    if not AWS_ACCESS_KEY or not AWS_SECRET_KEY:
        print("error", "AWS credentials are missing. Check the .env file.")
        raise ValueError("AWS credentials are missing.")

    try:
        s3_client = boto3.client(
            "s3",
            aws_access_key_id=AWS_ACCESS_KEY,
            aws_secret_access_key=AWS_SECRET_KEY,
            region_name="ap-south-1",
        )
        return s3_client
    except Exception as error:
        print("error", f"Error initializing S3 client: {error}")
        raise


s3_client = get_s3_client()
