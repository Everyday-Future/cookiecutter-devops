import pytest
import io
import hashlib
from unittest.mock import patch, Mock
from datetime import datetime, timedelta
from core.adapters.storage.gcp_storage import GCSStorageAdapter


@pytest.fixture
def gcs_blob_mock():
    """Mock for GCS blob."""
    mock = Mock()
    # Setup default properties
    mock.name = "test/file.txt"
    mock.bucket = Mock(name="test-bucket")
    mock.size = 100
    mock.content_type = "text/plain"
    mock.time_created = datetime(2023, 1, 1)
    mock.updated = datetime(2023, 1, 2)
    mock.md5_hash = "abc123"
    mock.etag = "def456"
    mock.generation = "123"
    mock.metageneration = "456"
    mock.storage_class = "STANDARD"
    mock.public = False
    mock.public_url = "https://storage.googleapis.com/test-bucket/test/file.txt"

    # Setup default methods
    mock.exists.return_value = True
    mock.download_as_bytes.return_value = b"test content"
    return mock


@pytest.fixture
def gcs_client_mock(gcs_blob_mock):
    """Mock for Google Cloud Storage client."""
    mock = Mock()

    # Setup bucket mock
    bucket_mock = Mock()
    bucket_mock.name = "test-bucket"
    bucket_mock.exists.return_value = True
    bucket_mock.blob.return_value = gcs_blob_mock

    # Setup default list_blobs method
    bucket_mock.list_blobs.return_value = [
        gcs_blob_mock,
        Mock(name="test/file2.txt")
    ]

    mock.bucket.return_value = bucket_mock

    return mock


@pytest.fixture
def gcs_adapter(gcs_client_mock):
    """Create a GCSStorageAdapter instance with mocked GCS client."""
    with patch('core.adapters.storage.gcp_storage.storage.Client') as mock_client_cls, \
            patch('core.adapters.storage.gcp_storage.service_account.Credentials') as mock_creds, \
            patch('core.adapters.storage.gcp_storage.Config') as mock_config, \
            patch('core.adapters.storage.gcp_storage.GCS_AVAILABLE', True):
        # Configure mocks
        mock_client_cls.return_value = gcs_client_mock

        # Config settings
        mock_config.GCS_PROJECT_ID = "test-project"
        mock_config.GCS_BUCKET_NAME = "test-bucket"
        mock_config.GCS_CREDENTIALS_JSON = None  # No credentials for simplicity

        adapter = GCSStorageAdapter()
        adapter.client = gcs_client_mock
        adapter.bucket = gcs_client_mock.bucket.return_value

        yield adapter


class TestGCSStorageAdapter:
    """Unit tests for GCSStorageAdapter."""

    def test_initialization(self):
        """Test adapter initialization."""
        with patch('core.adapters.storage.gcp_storage.storage.Client') as mock_client_cls, \
                patch('core.adapters.storage.gcp_storage.Config') as mock_config, \
                patch('core.adapters.storage.gcp_storage.GCS_AVAILABLE', True):
            # Config settings
            mock_config.GCS_PROJECT_ID = "test-project"
            mock_config.GCS_BUCKET_NAME = "test-bucket"
            mock_config.GCS_CREDENTIALS_JSON = None

            # Mock client
            mock_client = Mock()
            mock_client_cls.return_value = mock_client

            # Mock bucket
            mock_bucket = Mock()
            mock_bucket.exists.return_value = True
            mock_client.bucket.return_value = mock_bucket

            adapter = GCSStorageAdapter()

            # Verify client was initialized correctly
            mock_client_cls.assert_called_with(project="test-project")
            mock_client.bucket.assert_called_with("test-bucket")

            assert adapter.project_id == "test-project"
            assert adapter.bucket_name == "test-bucket"

    def test_initialization_with_json_credentials_string(self):
        """Test initialization with credentials JSON string."""
        with patch('core.adapters.storage.gcp_storage.storage.Client') as mock_client_cls, \
                patch('core.adapters.storage.gcp_storage.service_account.Credentials') as mock_creds, \
                patch('core.adapters.storage.gcp_storage.Config') as mock_config, \
                patch('core.adapters.storage.gcp_storage.json') as mock_json, \
                patch('core.adapters.storage.gcp_storage.GCS_AVAILABLE', True):
            # Config settings
            mock_config.GCS_PROJECT_ID = "test-project"
            mock_config.GCS_BUCKET_NAME = "test-bucket"
            mock_config.GCS_CREDENTIALS_JSON = '{"type": "service_account"}'

            # Mock JSON parsing
            mock_creds_dict = {"type": "service_account"}
            mock_json.loads.return_value = mock_creds_dict

            # Mock credentials
            mock_credentials = Mock()
            mock_creds.from_service_account_info.return_value = mock_credentials

            # Mock client
            mock_client = Mock()
            mock_client_cls.return_value = mock_client

            # Mock bucket
            mock_bucket = Mock()
            mock_bucket.exists.return_value = True
            mock_client.bucket.return_value = mock_bucket

            adapter = GCSStorageAdapter()

            # Verify credentials were loaded correctly
            mock_json.loads.assert_called_with('{"type": "service_account"}')
            mock_creds.from_service_account_info.assert_called_with(mock_creds_dict)
            mock_client_cls.assert_called_with(project="test-project", credentials=mock_credentials)

    def test_initialization_with_json_credentials_file(self):
        """Test initialization with credentials JSON file path."""
        with patch('core.adapters.storage.gcp_storage.storage.Client') as mock_client_cls, \
                patch('core.adapters.storage.gcp_storage.service_account.Credentials') as mock_creds, \
                patch('core.adapters.storage.gcp_storage.Config') as mock_config, \
                patch('core.adapters.storage.gcp_storage.GCS_AVAILABLE', True):
            # Config settings
            mock_config.GCS_PROJECT_ID = "test-project"
            mock_config.GCS_BUCKET_NAME = "test-bucket"
            mock_config.GCS_CREDENTIALS_JSON = "/path/to/credentials.json"  # A file path

            # Mock credentials
            mock_credentials = Mock()
            mock_creds.from_service_account_file.return_value = mock_credentials

            # Mock client
            mock_client = Mock()
            mock_client_cls.return_value = mock_client

            # Mock bucket
            mock_bucket = Mock()
            mock_bucket.exists.return_value = True
            mock_client.bucket.return_value = mock_bucket

            adapter = GCSStorageAdapter()

            # Verify credentials were loaded correctly
            mock_creds.from_service_account_file.assert_called_with("/path/to/credentials.json")
            mock_client_cls.assert_called_with(project="test-project", credentials=mock_credentials)

    def test_initialization_without_bucket_name(self):
        """Test that initialization without bucket name raises ValueError."""
        with patch('core.adapters.storage.gcp_storage.storage.Client'), \
                patch('core.adapters.storage.gcp_storage.Config') as mock_config, \
                patch('core.adapters.storage.gcp_storage.GCS_AVAILABLE', True):
            # Config settings without bucket name
            mock_config.GCS_PROJECT_ID = "test-project"
            mock_config.GCS_BUCKET_NAME = None

            with pytest.raises(ValueError, match="GCS_BUCKET_NAME must be specified"):
                GCSStorageAdapter()

    def test_get_blob(self, gcs_adapter, gcs_blob_mock):
        """Test _get_blob method."""
        # Test getting blob
        blob = gcs_adapter._get_blob("test/file.txt")

        # Assertions
        assert blob == gcs_blob_mock
        gcs_adapter.bucket.blob.assert_called_with("test/file.txt")

    def test_get_blob_must_exist(self, gcs_adapter, gcs_blob_mock):
        """Test _get_blob method with must_exist=True."""
        # Setup blob to not exist
        gcs_blob_mock.exists.return_value = False

        # Test getting blob with must_exist=True
        with pytest.raises(FileNotFoundError, match="File not found in GCS"):
            gcs_adapter._get_blob("test/file.txt", must_exist=True)

    def test_read_file(self, gcs_adapter, gcs_blob_mock):
        """Test reading a file from GCS."""
        # Test reading file
        content = gcs_adapter.read_file("test/file.txt")

        # Assertions
        assert content == b"test content"
        gcs_blob_mock.download_as_bytes.assert_called_once()

    def test_write_file_bytes(self, gcs_adapter, gcs_blob_mock):
        """Test writing bytes to a file in GCS."""
        # Test data
        test_data = b"test binary content"

        # Test writing file
        result = gcs_adapter.write_file("test/binary.bin", test_data)

        # Assertions
        gcs_blob_mock.upload_from_string.assert_called_with(test_data, content_type=None)
        assert result is True

    def test_write_file_string(self, gcs_adapter, gcs_blob_mock):
        """Test writing string to a file in GCS."""
        # Test data
        test_data = "test string content"

        # Test writing file
        result = gcs_adapter.write_file("test/string.txt", test_data)

        # Assertions
        gcs_blob_mock.upload_from_string.assert_called_with(test_data, content_type="text/plain")
        assert result is True

    def test_write_file_fileobj(self, gcs_adapter, gcs_blob_mock):
        """Test writing file-like object to a file in GCS."""
        # Test data
        test_fileobj = io.BytesIO(b"test file object content")

        # Test writing file
        result = gcs_adapter.write_file("test/fileobj.txt", test_fileobj)

        # Assertions
        gcs_blob_mock.upload_from_file.assert_called_with(test_fileobj, content_type=None)
        assert result is True

    def test_write_file_with_content_type(self, gcs_adapter, gcs_blob_mock):
        """Test writing file with specified content type."""
        # Test data
        test_data = b"test content with type"
        content_type = "application/json"

        # Test writing file
        result = gcs_adapter.write_file("test/typed.json", test_data, content_type=content_type)

        # Assertions
        gcs_blob_mock.upload_from_string.assert_called_with(test_data, content_type=content_type)
        assert result is True

    def test_delete_file(self, gcs_adapter, gcs_blob_mock):
        """Test deleting a file from GCS."""
        # Test deleting file
        result = gcs_adapter.delete_file("test/delete.txt")

        # Assertions
        gcs_blob_mock.delete.assert_called_once()
        assert result is True

    def test_delete_file_not_found(self, gcs_adapter, gcs_blob_mock):
        """Test deleting a non-existent file returns False."""
        # Setup blob to not exist
        gcs_blob_mock.exists.return_value = False

        # Test deleting non-existent file
        result = gcs_adapter.delete_file("non-existent/file.txt")

        # Assertions
        gcs_blob_mock.delete.assert_not_called()
        assert result is False

    def test_copy_file(self, gcs_adapter, gcs_blob_mock):
        """Test copying a file within GCS."""
        # Setup source and destination blobs
        source_blob = gcs_blob_mock
        dest_blob = Mock(name="dest_blob")
        gcs_adapter.bucket.blob.side_effect = [source_blob, dest_blob]

        # Test copying file
        result = gcs_adapter.copy_file("test/source.txt", "test/dest.txt")

        # Assertions
        gcs_adapter.bucket.copy_blob.assert_called_with(source_blob, gcs_adapter.bucket, dest_blob.name)
        assert result is True

    def test_copy_file_source_not_found(self, gcs_adapter, gcs_blob_mock):
        """Test copying a non-existent source file raises FileNotFoundError."""
        # Setup source blob to not exist
        gcs_blob_mock.exists.return_value = False

        # Test copying non-existent file
        with pytest.raises(FileNotFoundError, match="File not found in GCS"):
            gcs_adapter.copy_file("non-existent/file.txt", "test/dest.txt")

    def test_move_file(self, gcs_adapter):
        """Test moving a file within GCS."""
        # Setup mocks for copy and delete operations
        with patch.object(gcs_adapter, 'copy_file', return_value=True) as mock_copy:
            with patch.object(gcs_adapter, 'delete_file', return_value=True) as mock_delete:
                # Test moving file
                result = gcs_adapter.move_file("test/source.txt", "test/dest.txt")

                # Assertions
                mock_copy.assert_called_with("test/source.txt", "test/dest.txt")
                mock_delete.assert_called_with("test/source.txt")
                assert result is True

    def test_file_exists(self, gcs_adapter, gcs_blob_mock):
        """Test checking if a file exists in GCS."""
        # Test file exists
        assert gcs_adapter.file_exists("test/exists.txt") is True

        # Test file doesn't exist
        gcs_blob_mock.exists.return_value = False
        assert gcs_adapter.file_exists("non-existent/file.txt") is False

    def test_get_file_size(self, gcs_adapter, gcs_blob_mock):
        """Test getting file size from GCS."""
        # Setup blob size
        gcs_blob_mock.size = 12345

        # Test getting file size
        size = gcs_adapter.get_file_size("test/file.txt")

        # Assertions
        assert size == 12345

    def test_get_file_size_not_found(self, gcs_adapter, gcs_blob_mock):
        """Test getting size of a non-existent file raises FileNotFoundError."""
        # Setup blob to not exist
        gcs_blob_mock.exists.return_value = False

        # Test getting size of non-existent file
        with pytest.raises(FileNotFoundError, match="File not found in GCS"):
            gcs_adapter.get_file_size("non-existent/file.txt")

    def test_get_file_metadata(self, gcs_adapter, gcs_blob_mock):
        """Test getting file metadata from GCS."""
        # Setup blob properties
        gcs_blob_mock.name = "test/metadata.txt"
        gcs_blob_mock.bucket.name = "test-bucket"
        gcs_blob_mock.size = 12345
        gcs_blob_mock.content_type = "text/plain"
        gcs_blob_mock.time_created = datetime(2023, 1, 1)
        gcs_blob_mock.updated = datetime(2023, 1, 2)
        gcs_blob_mock.md5_hash = "abc123"
        gcs_blob_mock.etag = "def456"
        gcs_blob_mock.generation = "123"
        gcs_blob_mock.metageneration = "456"
        gcs_blob_mock.storage_class = "STANDARD"
        gcs_blob_mock.exists.return_value = True  # Important for _get_blob check

        # Setup IAM policy mock
        policy_mock = Mock()
        policy_mock.bindings = []
        gcs_adapter.bucket.get_iam_policy.return_value = policy_mock

        # Test getting metadata
        metadata = gcs_adapter.get_file_metadata("test/metadata.txt")

        # Don't assert reload count since it's called in multiple places
        assert gcs_blob_mock.reload.call_count > 0
        assert metadata["path"] == "test/metadata.txt"
        assert metadata["name"] == "test/metadata.txt"
        assert metadata["bucket"] == "test-bucket"
        assert metadata["size"] == 12345
        assert metadata["content_type"] == "text/plain"
        assert metadata["created"] == datetime(2023, 1, 1)
        assert metadata["updated"] == datetime(2023, 1, 2)
        assert metadata["md5_hash"] == "abc123"
        assert metadata["etag"] == "def456"
        assert metadata["generation"] == "123"
        assert metadata["metageneration"] == "456"
        assert metadata["storage_class"] == "STANDARD"
        assert metadata["is_public"] is False
        assert metadata["public_url"] is None

    def test_get_file_metadata_not_found(self, gcs_adapter, gcs_blob_mock):
        """Test getting metadata of a non-existent file raises FileNotFoundError."""
        # Setup blob to not exist
        gcs_blob_mock.exists.return_value = False

        # Test getting metadata of non-existent file
        with pytest.raises(FileNotFoundError, match="File not found in GCS"):
            gcs_adapter.get_file_metadata("non-existent/file.txt")

    def test_get_file_checksum_md5_from_blob(self, gcs_adapter, gcs_blob_mock):
        """Test getting MD5 checksum from blob metadata."""
        # Setup blob MD5 hash
        gcs_blob_mock.md5_hash = "abc123"
        gcs_blob_mock.exists.return_value = True

        # Test getting MD5 checksum
        checksum = gcs_adapter.get_file_checksum("test/file.txt", "md5")

        # Don't assert reload count since it's called in multiple places
        assert gcs_blob_mock.reload.call_count > 0
        assert checksum == "abc123"

    def test_get_file_checksum_md5_calculated(self, gcs_adapter, gcs_blob_mock):
        """Test calculating MD5 checksum when not available in blob metadata."""
        # Setup blob with no MD5 hash
        gcs_blob_mock.md5_hash = None
        gcs_blob_mock.reload.return_value = None  # No-op for reload
        gcs_blob_mock.download_as_bytes.return_value = b"test content"

        # Expected MD5
        expected_md5 = hashlib.md5(b"test content").hexdigest()

        # Test getting MD5 checksum
        checksum = gcs_adapter.get_file_checksum("test/file.txt", "md5")

        # Assertions
        assert checksum == expected_md5

    def test_get_file_checksum_sha256(self, gcs_adapter, gcs_blob_mock):
        """Test calculating SHA-256 checksum."""
        # Setup blob
        gcs_blob_mock.download_as_bytes.return_value = b"test content"

        # Expected SHA-256
        expected_sha256 = hashlib.sha256(b"test content").hexdigest()

        # Test getting SHA-256 checksum
        checksum = gcs_adapter.get_file_checksum("test/file.txt", "sha256")

        # Assertions
        assert checksum == expected_sha256

    def test_get_file_checksum_invalid_algorithm(self, gcs_adapter):
        """Test that invalid hash algorithm raises ValueError."""
        with pytest.raises(ValueError, match="Unsupported hash algorithm"):
            gcs_adapter.get_file_checksum("test/file.txt", "invalid_algo")

    def test_list_files(self, gcs_adapter):
        """Test listing files in GCS."""
        # Setup blobs for list_blobs
        blob1 = Mock()
        blob1.name = "test/file1.txt"
        blob2 = Mock()
        blob2.name = "test/file2.txt"
        blob3 = Mock()
        blob3.name = "test/subfolder/file3.txt"

        gcs_adapter.bucket.list_blobs.return_value = [blob1, blob2, blob3]

        # Test listing files (non-recursive by default)
        file_list = gcs_adapter.list_files("test")

        # Assertions
        gcs_adapter.bucket.list_blobs.assert_called_with(prefix="test/")
        assert "test/file1.txt" in file_list
        assert "test/file2.txt" in file_list
        assert "test/subfolder/file3.txt" not in file_list  # Should be excluded in non-recursive mode

    def test_list_files_recursive(self, gcs_adapter):
        """Test listing files recursively."""
        # Setup blobs for list_blobs
        blob1 = Mock()
        blob1.name = "test/file1.txt"
        blob2 = Mock()
        blob2.name = "test/file2.txt"
        blob3 = Mock()
        blob3.name = "test/subfolder/file3.txt"

        gcs_adapter.bucket.list_blobs.return_value = [blob1, blob2, blob3]

        # Test listing files recursively
        file_list = gcs_adapter.list_files("test", recursive=True)

        # Assertions
        assert "test/file1.txt" in file_list
        assert "test/file2.txt" in file_list
        assert "test/subfolder/file3.txt" in file_list  # Should be included in recursive mode

    def test_list_files_with_pattern(self, gcs_adapter):
        """Test listing files with pattern filter."""
        # Setup blobs with different file types
        blob1 = Mock()
        blob1.name = "test/file1.txt"
        blob2 = Mock()
        blob2.name = "test/file2.jpg"
        blob3 = Mock()
        blob3.name = "test/file3.txt"

        gcs_adapter.bucket.list_blobs.return_value = [blob1, blob2, blob3]

        # Test listing files with pattern
        file_list = gcs_adapter.list_files("test", pattern="*.txt")

        # Assertions
        assert "test/file1.txt" in file_list
        assert "test/file2.jpg" not in file_list  # Should be excluded by pattern
        assert "test/file3.txt" in file_list

    def test_list_files_not_found(self, gcs_adapter):
        """Test listing files in a non-existent directory."""
        # Setup mock to return empty lists for both calls
        gcs_adapter.bucket.list_blobs.side_effect = [[], []]

        # Test listing files in non-existent directory
        with pytest.raises(FileNotFoundError, match="Directory not found in GCS"):
            gcs_adapter.list_files("non-existent")

        # Verify both list_blobs calls were made
        assert gcs_adapter.bucket.list_blobs.call_count == 2
        assert gcs_adapter.bucket.list_blobs.call_args_list[0][1] == {'prefix': 'non-existent/'}
        assert gcs_adapter.bucket.list_blobs.call_args_list[1][1] == {'prefix': 'non-existent/', 'max_results': 1}

    def test_create_directory(self, gcs_adapter, gcs_blob_mock):
        """Test creating a directory in GCS."""
        # Setup initial state
        gcs_blob_mock.exists.return_value = False
        gcs_adapter.bucket.list_blobs.side_effect = [
            [],  # First check - directory doesn't exist
            [gcs_blob_mock],  # Second check - directory exists after creation
        ]

        # Test creating directory
        with patch.object(gcs_adapter, 'directory_exists', side_effect=[False, True]):
            result = gcs_adapter.create_directory("test/new_dir")

            # Assertions
            gcs_blob_mock.upload_from_string.assert_called_with('', content_type='application/x-directory')
            assert result is True

    def test_create_directory_already_exists(self, gcs_adapter, gcs_blob_mock):
        """Test creating a directory that already exists returns False."""
        # Setup blob to exist
        gcs_blob_mock.exists.return_value = True

        # Test creating existing directory
        result = gcs_adapter.create_directory("test/existing_dir")

        # Assertions
        gcs_blob_mock.upload_from_string.assert_not_called()
        assert result is False

    def test_delete_directory(self, gcs_adapter):
        """Test deleting a directory in GCS."""
        # Setup directory marker blob
        dir_blob = Mock(name="test/dir/")
        dir_blob.name = "test/dir/"  # Important: match the normalized path

        # Setup directory to appear empty (only contains directory marker)
        gcs_adapter.bucket.list_blobs.side_effect = [
            [dir_blob],  # First call returns only directory marker
            []  # Second call to verify deletion
        ]

        # Mock _list_blobs_with_prefix to return our test data
        with patch.object(gcs_adapter, '_list_blobs_with_prefix', side_effect=[
            [dir_blob],  # First call for initial check
            []  # Second call for verification
        ]):
            # Test deleting directory
            result = gcs_adapter.delete_directory("test/dir")

            # Assertions
            dir_blob.delete.assert_called_once()
            assert result is True

    def test_delete_directory_not_empty_no_recursive(self, gcs_adapter):
        """Test deleting a non-empty directory without recursive flag raises ValueError."""
        # Setup directory with contents
        dir_blob = Mock(name="test/dir/")
        file_blob = Mock(name="test/dir/file.txt")

        gcs_adapter.bucket.list_blobs.return_value = [dir_blob, file_blob]

        # Test deleting non-empty directory without recursive
        with pytest.raises(ValueError, match="Directory not empty"):
            gcs_adapter.delete_directory("test/dir", recursive=False)

    def test_delete_directory_not_found(self, gcs_adapter):
        """Test deleting a non-existent directory returns False."""
        # Setup mock to return no blobs
        gcs_adapter.bucket.list_blobs.return_value = []

        # Test deleting non-existent directory
        result = gcs_adapter.delete_directory("test/non_existent_dir")

        # Assertions
        assert result is False

    def test_directory_exists(self, gcs_adapter, gcs_blob_mock):
        """Test checking if a directory exists in GCS."""
        # Test directory exists as marker object
        gcs_blob_mock.exists.return_value = True
        assert gcs_adapter.directory_exists("test/dir") is True

        # Test directory exists because it has contents
        gcs_blob_mock.exists.return_value = False
        gcs_adapter.bucket.list_blobs.return_value = [Mock()]
        assert gcs_adapter.directory_exists("test/dir") is True

        # Test directory doesn't exist
        gcs_blob_mock.exists.return_value = False
        gcs_adapter.bucket.list_blobs.return_value = []
        assert gcs_adapter.directory_exists("test/non_existent_dir") is False

    def test_generate_signed_url(self, gcs_adapter, gcs_blob_mock):
        """Test generating a signed URL for GCS."""
        # Setup mock to return a signed URL
        expected_url = "https://signed-url.example.com"
        gcs_blob_mock.generate_signed_url.return_value = expected_url
        expiration = 3600

        # Test generating signed URL
        url = gcs_adapter.generate_signed_url("test/file.txt", expiration=expiration)
        assert url == expected_url

        # Verify generate_signed_url was called with expected args
        gcs_blob_mock.generate_signed_url.assert_called_once()
        call_args = gcs_blob_mock.generate_signed_url.call_args[1]
        assert call_args["version"] == "v4"
        assert isinstance(call_args["expiration"], timedelta)
        assert call_args["method"] == "GET"

    def test_generate_signed_url_not_found(self, gcs_adapter, gcs_blob_mock):
        """Test generating a signed URL for a non-existent file raises FileNotFoundError."""
        # Setup blob to not exist
        gcs_blob_mock.exists.return_value = False

        # Test generating signed URL for non-existent file
        with pytest.raises(FileNotFoundError, match="File not found in GCS"):
            gcs_adapter.generate_signed_url("non-existent/file.txt")

    def test_make_public(self, gcs_adapter, gcs_blob_mock):
        """Test making a file public in GCS."""
        # Setup IAM policy mock
        policy_mock = Mock()
        policy_mock.bindings = []
        policy_mock.version = 3
        gcs_adapter.bucket.get_iam_policy.return_value = policy_mock

        # Setup _check_is_public to return True after making public
        def check_is_public_side_effect():
            return True

        gcs_adapter._check_is_public = Mock(side_effect=[False, True])

        # Test making file public
        result = gcs_adapter.make_public("test/file.txt")

        # Assertions
        gcs_adapter.bucket.get_iam_policy.assert_called_once()
        gcs_adapter.bucket.set_iam_policy.assert_called_once()
        assert result is True

    def test_make_public_not_found(self, gcs_adapter, gcs_blob_mock):
        """Test making a non-existent file public raises FileNotFoundError."""
        # Setup blob to not exist
        gcs_blob_mock.exists.return_value = False

        # Test making non-existent file public
        with pytest.raises(FileNotFoundError, match="File not found in GCS"):
            gcs_adapter.make_public("non-existent/file.txt")

    def test_make_private(self, gcs_adapter, gcs_blob_mock):
        """Test making a file private in GCS."""
        # Test making file private
        result = gcs_adapter.make_private("test/file.txt")

        # Assertions
        gcs_blob_mock.make_private.assert_called_once()
        assert result is True