import pytest
from google.cloud.exceptions import NotFound
import unittest
from unittest.mock import patch
from config import Config
from core.adapters.storage.storage_gcp import GcpStorage


@pytest.fixture
def gcs_credentials():
    """Mocked GCS Credentials for google-cloud-storage."""
    Config.GCS_BUCKET = "my-test-bucket"


@pytest.fixture
def gcs_bucket(gcs_credentials):
    """Mock GCS bucket."""
    with patch('google.cloud.storage.Client') as mock_client:
        mock_client_instance = mock_client.return_value
        mock_bucket = mock_client_instance.bucket.return_value
        yield mock_bucket


@pytest.fixture
def gcs_storage(gcs_bucket):
    """Fixture for the GoogleCloudStorage instance."""
    return GcpStorage()


def test_upload_file(gcs_storage, tmp_path):
    # Arrange
    file_path = tmp_path / "test_upload.txt"
    file_path.write_text("This is a test file.")
    gcs_key = "test_upload.txt"

    # Act
    with patch.object(gcs_storage.bucket, 'blob') as mock_blob:
        mock_blob_instance = mock_blob.return_value
        mock_blob_instance.upload_from_filename.return_value = None
        mock_blob_instance.generate_signed_url.return_value = "https://signed_url"

        # Assert
        presigned_url = gcs_storage.upload(link=gcs_key, fpath=file_path)
        assert presigned_url == "https://signed_url"


def test_download_file(gcs_storage, tmp_path):
    # Arrange
    gcs_key = "test_download.txt"
    download_path = tmp_path / "test_download.txt"

    # Act
    with patch.object(gcs_storage.bucket, 'blob') as mock_blob:
        mock_blob_instance = mock_blob.return_value
        mock_blob_instance.download_to_filename.return_value = None

        # Assert
        result_path = gcs_storage.download(link=gcs_key, fpath=download_path)
        assert result_path == download_path


@unittest.skipIf(Config.BASIC_TESTS is True, "takes 4s just to check exception handling")
def test_upload_file_exception_handling(gcs_storage, tmp_path):
    # Arrange
    file_path = tmp_path / "test_upload.txt"
    file_path.write_text("This is a test file.")
    gcs_key = "test_upload.txt"

    # Act
    with patch.object(gcs_storage.bucket, 'blob') as mock_blob:
        mock_blob_instance = mock_blob.return_value
        mock_blob_instance.upload_from_filename.side_effect = Exception("Upload error")

        # Assert
        with pytest.raises(Exception, match="Upload error"):
            gcs_storage.upload(link=gcs_key, fpath=file_path)


@unittest.skipIf(Config.BASIC_TESTS is True, "takes 4s just to check exception handling")
def test_download_file_not_found_exception(gcs_storage, tmp_path):
    # Arrange
    gcs_key = "test_nonexistent_file.txt"
    download_path = tmp_path / "test_nonexistent_file.txt"

    # Act
    with patch.object(gcs_storage.bucket, 'blob') as mock_blob:
        mock_blob_instance = mock_blob.return_value
        mock_blob_instance.download_to_filename.side_effect = NotFound("File not found")

        # Assert
        with pytest.raises(KeyError):
            gcs_storage.download(link=gcs_key, fpath=download_path)


@unittest.skipIf(Config.BASIC_TESTS is True, "takes 4s just to check exception handling")
def test_download_file_exception_handling(gcs_storage, tmp_path):
    # Arrange
    gcs_key = "test_file.txt"
    download_path = tmp_path / "test_file.txt"

    with patch.object(gcs_storage.bucket, 'blob') as mock_blob:
        mock_blob_instance = mock_blob.return_value
        mock_blob_instance.download_to_filename.side_effect = Exception("Download error")

        # Act & Assert
        with pytest.raises(ValueError, match="An error occurred that prevented the file from downloading correctly."):
            gcs_storage.download(link=gcs_key, fpath=download_path)


def test_multipart_upload_file(gcs_storage, tmp_path):
    # Arrange
    file_path = tmp_path / "test_multipart_upload.txt"
    file_content = "This is a large test file." * 1024 * 1024  # 22MB
    file_path.write_text(file_content)
    gcs_key = "test_multipart_upload.txt"

    # Act
    with patch.object(gcs_storage.bucket, 'blob') as mock_blob:
        mock_blob_instance = mock_blob.return_value
        mock_blob_instance.upload_from_filename.return_value = None
        mock_blob_instance.generate_signed_url.return_value = "https://signed_url"

        # Assert
        presigned_url = gcs_storage.multipart_upload(link=gcs_key, fpath=file_path)
        assert presigned_url == "https://signed_url"


@unittest.skipIf(Config.BASIC_TESTS is True, "takes 4s just to check exception handling")
def test_multipart_upload_exception_handling(gcs_storage, tmp_path):
    # Arrange
    file_path = tmp_path / "test_multipart_upload.txt"
    file_content = "This is a large test file." * 1024 * 1024  # 22MB
    file_path.write_text(file_content)
    gcs_key = "test_multipart_upload.txt"

    # Act
    with patch.object(gcs_storage.bucket, 'blob') as mock_blob:
        mock_blob_instance = mock_blob.return_value
        mock_blob_instance.upload_from_filename.side_effect = Exception("Upload error")

        # Assert
        with pytest.raises(Exception, match="Upload error"):
            gcs_storage.multipart_upload(link=gcs_key, fpath=file_path)
