import os
from tests.fixtures.s3_fixture import mock_s3_client
from unittest.mock import MagicMock, patch, call
from src.geospatial.io.uploader.s3_client import copy_files_to_s3, upload_file


def test_upload_file(mock_s3_client, tmp_path):
    """Test the upload_file function with a mock S3 bucket."""
    temp_file = tmp_path / "test_file.txt"
    temp_file.write_text("This is a test file.")

    s3_filename = "app-analyzed-data/test_file.txt"

    upload_file(str(temp_file), s3_filename)

    s3_objects = mock_s3_client.list_objects_v2(Bucket="glrem-space-geospatial-data")
    assert "Contents" in s3_objects

    uploaded_files = [obj["Key"] for obj in s3_objects["Contents"]]
    assert s3_filename in uploaded_files


def test_copy_files_to_s3(mock_s3_client, tmp_path):
    test_folder = tmp_path
    test_files = ["image1.tif", "image2.png", "document.pdf"]

    for file in test_files:
        file_path = os.path.join(test_folder, file)
        with open(file_path, "w") as f:
            f.write(f"This is a test file for {file}")

    mock_upload_file = MagicMock()

    with patch("src.geospatial.io.uploader.s3_client.upload_file", mock_upload_file):
        copy_files_to_s3(test_folder)

    assert mock_upload_file.call_args_list == [
        call(os.path.join(test_folder, "image2.png"), "app-analyzed-data/image2.png"),
        call(os.path.join(test_folder, "image1.tif"), "app-analyzed-data/image1.tif"),
    ]

    assert mock_upload_file.call_count == 2
