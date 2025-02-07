import os
import boto3
import pytest
from moto import mock_aws
from src.config import AWS_BUCKET_NAME


@pytest.fixture(scope="function")
def mock_s3_client():
    with mock_aws():
        s3 = boto3.client("s3")
        s3.create_bucket(Bucket=AWS_BUCKET_NAME)
        yield s3
