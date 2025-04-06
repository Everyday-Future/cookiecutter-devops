import pytest
from unittest.mock import patch
from core.adapters.storage.storage_adapter import StorageAdapterFactory


class TestStorageAdapterFactory:
    """Tests for the StorageAdapterFactory"""

    def test_create_local_adapter(self):
        """Test creating a local storage adapter"""
        with patch('core.adapters.storage.storage_adapter.Config') as mock_config, \
                patch('core.adapters.storage.local_storage.LocalStorageAdapter') as mock_local_adapter:
            mock_config.STORAGE_TYPE = "local"

            factory = StorageAdapterFactory.create_adapter()

            # Verify the correct adapter was created
            assert mock_local_adapter.called
            assert factory == mock_local_adapter.return_value

    def test_create_network_adapter(self):
        """Test creating a network storage adapter"""
        with patch('core.adapters.storage.storage_adapter.Config') as mock_config, \
                patch('core.adapters.storage.network_storage.NetworkStorageAdapter') as mock_network_adapter:
            mock_config.STORAGE_TYPE = "network"

            factory = StorageAdapterFactory.create_adapter("network")

            # Verify the correct adapter was created
            assert mock_network_adapter.called
            assert factory == mock_network_adapter.return_value

    def test_create_gcs_adapter(self):
        """Test creating a GCS storage adapter."""
        with patch('core.adapters.storage.storage_adapter.Config') as mock_config, \
                patch('core.adapters.storage.gcp_storage.GCSStorageAdapter') as mock_gcs_adapter:
            for storage_type in ["gcs", "google", "gcp"]:
                factory = StorageAdapterFactory.create_adapter(storage_type)
                assert mock_gcs_adapter.called
                assert factory == mock_gcs_adapter.return_value
                mock_gcs_adapter.reset_mock()

    def test_create_s3_adapter(self):
        """Test creating an S3 storage adapter."""
        with patch('core.adapters.storage.storage_adapter.Config') as mock_config, \
                patch('core.adapters.storage.aws_storage.S3StorageAdapter') as mock_s3_adapter:
            for storage_type in ["s3", "aws"]:
                factory = StorageAdapterFactory.create_adapter(storage_type)
                assert mock_s3_adapter.called
                assert factory == mock_s3_adapter.return_value
                mock_s3_adapter.reset_mock()

    def test_create_adapter_invalid_type(self):
        """Test that an invalid storage type raises ValueError"""
        with pytest.raises(ValueError, match=r"Unsupported storage type"):
            StorageAdapterFactory.create_adapter("invalid_type")


if __name__ == "__main__":
    pytest.main()