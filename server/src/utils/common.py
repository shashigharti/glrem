import boto3
from src.config import AWS_ACCESS_KEY, AWS_SECRET_KEY


def generate_filename(eventid, eventtype, analysis):
    return f"{eventtype}-{eventid}-{analysis}"


def check_file_exists(bucket_name, file_key):
    s3 = boto3.client(
        "s3",
        aws_access_key_id=AWS_ACCESS_KEY,
        aws_secret_access_key=AWS_SECRET_KEY,
    )
    try:
        s3.head_object(Bucket=bucket_name, Key=file_key)
    except s3.exceptions.ClientError as e:
        return False
    return True
