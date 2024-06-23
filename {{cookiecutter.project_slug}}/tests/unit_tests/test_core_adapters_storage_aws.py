import unittest

import pytest
from unittest.mock import patch
from moto import mock_aws
import boto3
from botocore.exceptions import ClientError
from config import Config
from core.adapters.storage.storage_aws import AwsStorage


@pytest.fixture
def aws_credentials():
    """Mocked AWS Credentials for moto."""
    Config.AWS_ACCESS_KEY_ID = "testing"
    Config.AWS_SECRET_ACCESS_KEY = "testing"
    Config.S3_REGION = "us-east-1"
    Config.S3_BUCKET = "my-test-bucket"


@pytest.fixture
def s3_bucket(aws_credentials):
    """Mock S3 bucket."""
    with mock_aws():
        s3 = boto3.client('s3', region_name=Config.S3_REGION)
        s3.create_bucket(Bucket=Config.S3_BUCKET)
        yield


@pytest.fixture
def aws_storage(s3_bucket):
    """Fixture for the AwsStorage instance."""
    return AwsStorage()


def test_upload_file(aws_storage, tmp_path):
    # Arrange
    file_path = tmp_path / "test_upload.txt"
    file_path.write_text("This is a test file.")
    s3_key = "test_upload.txt"

    # Act
    presigned_url = aws_storage.upload(link=s3_key, fpath=file_path)

    # Assert
    assert presigned_url is not None
    s3 = boto3.client('s3', region_name=Config.S3_REGION)
    response = s3.get_object(Bucket=Config.S3_BUCKET, Key=s3_key)
    assert response['Body'].read().decode() == "This is a test file."


def test_download_file(aws_storage, tmp_path):
    # Arrange
    s3 = boto3.client('s3', region_name=Config.S3_REGION)
    file_content = "This is a test file."
    s3_key = "test_download.txt"
    s3.put_object(Bucket=Config.S3_BUCKET, Key=s3_key, Body=file_content)
    download_path = tmp_path / "test_download.txt"

    # Act
    result_path = aws_storage.download(link=s3_key, fpath=download_path)

    # Assert
    assert result_path == download_path
    assert download_path.read_text() == file_content


def test_multipart_upload_file(aws_storage, tmp_path):
    # Arrange
    file_path = tmp_path / "test_multipart_upload.txt"
    file_content = "This is a large test file." * 1024 * 1024  # 22MB
    file_path.write_text(file_content)
    s3_key = "test_multipart_upload.txt"

    # Act
    presigned_url = aws_storage.multipart_upload(link=s3_key, fpath=file_path)

    # Assert
    assert presigned_url is not None
    s3 = boto3.client('s3', region_name=Config.S3_REGION)
    response = s3.get_object(Bucket=Config.S3_BUCKET, Key=s3_key)
    assert response['Body'].read().decode() == file_content


@unittest.skipIf(Config.BASIC_TESTS is True, "takes 4s just to check exception handling")
def test_upload_file_exception_handling(aws_storage, tmp_path):
    # Arrange
    file_path = tmp_path / "test_upload.txt"
    file_path.write_text("This is a test file.")
    s3_key = "test_upload.txt"

    # Act
    with patch('boto3.session.Session.client') as mock_client:
        mock_s3 = mock_client.return_value
        mock_s3.upload_file.side_effect = ClientError(
            {"Error": {"Code": "500", "Message": "Internal Server Error"}},
            "UploadFile"
        )

        # Assert
        with pytest.raises(ClientError):
            aws_storage.upload(link=s3_key, fpath=file_path)


def test_download_file_not_found_exception(aws_storage, tmp_path):
    # Arrange
    s3_key = "test_nonexistent_file.txt"
    download_path = tmp_path / "test_nonexistent_file.txt"

    # Act & Assert
    with pytest.raises(KeyError):
        aws_storage.download(link=s3_key, fpath=download_path)


def test_download_file_exception_handling(aws_storage, tmp_path):
    # Arrange
    s3_key = "test_file.txt"
    download_path = tmp_path / "test_file.txt"

    with patch('boto3.resource') as mock_resource:
        mock_s3 = mock_resource.return_value
        mock_bucket = mock_s3.Bucket.return_value
        mock_bucket.download_file.side_effect = ClientError(
            {"Error": {"Code": "500", "Message": "Internal Server Error"}},
            "DownloadFile"
        )

        # Act & Assert
        with pytest.raises(ValueError):
            aws_storage.download(link=s3_key, fpath=download_path)


@unittest.skipIf(Config.BASIC_TESTS is True, "takes 4s just to check exception handling")
def test_multipart_upload_exception_handling(aws_storage, tmp_path):
    # Arrange
    file_path = tmp_path / "test_multipart_upload.txt"
    file_content = "This is a large test file." * 1024 * 1024  # 22MB
    file_path.write_text(file_content)
    s3_key = "test_multipart_upload.txt"

    # Act
    with patch('boto3.session.Session.client') as mock_client:
        mock_s3 = mock_client.return_value
        mock_s3.upload_file.side_effect = ClientError(
            {"Error": {"Code": "500", "Message": "Internal Server Error"}},
            "UploadFile"
        )

        # Assert
        with pytest.raises(ClientError):
            aws_storage.multipart_upload(link=s3_key, fpath=file_path)