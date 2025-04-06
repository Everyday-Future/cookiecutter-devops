# core/adapters/storage/gcp_storage.py
import os
import json
import logging
import hashlib
from typing import BinaryIO, Dict, List, Optional, Union, Any
from datetime import datetime, timedelta
from config import Config
from .storage_adapter import StorageAdapter

# Import Google Cloud Storage libraries
try:
    from google.cloud import storage
    from google.cloud.exceptions import NotFound, Forbidden, BadRequest
    from google.oauth2 import service_account

    GCS_AVAILABLE = True
except ImportError:
    GCS_AVAILABLE = False

logger = logging.getLogger(__name__)


class GCSStorageAdapter(StorageAdapter):
    """
    Storage adapter for Google Cloud Storage.
    """

    def __init__(self):
        """Initialize the GCS storage adapter."""
        super().__init__()

        if not GCS_AVAILABLE:
            raise ImportError("Google Cloud Storage libraries not installed. "
                              "Install with: pip install google-cloud-storage")

        self.project_id = Config.GCS_PROJECT_ID
        self.bucket_name = Config.GCS_BUCKET_NAME
        self.credentials_json = Config.GCS_CREDENTIALS_JSON

        if not self.bucket_name:
            raise ValueError("GCS_BUCKET_NAME must be specified")

        self.client = self._initialize_client()
        self.bucket = self.client.bucket(self.bucket_name)
        logger.info(f"GCSStorageAdapter initialized with bucket: {self.bucket_name}")

    def _initialize_client(self):
        try:
            if self.credentials_json:
                if isinstance(self.credentials_json, str) and self.credentials_json.startswith('{'):
                    credentials_info = json.loads(self.credentials_json)
                    credentials = service_account.Credentials.from_service_account_info(credentials_info)
                else:
                    credentials = service_account.Credentials.from_service_account_file(self.credentials_json)
                return storage.Client(project=self.project_id, credentials=credentials)
            return storage.Client(project=self.project_id)
        except Exception as e:
            logger.error(f"Error initializing GCS client: {str(e)}")
            raise IOError(f"Failed to initialize GCS client: {str(e)}")

    def _get_blob(self, path: str, must_exist: bool = False):
        normalized_path = self.normalize_path(path)
        blob = self.bucket.blob(normalized_path)

        if must_exist:
            try:
                blob.reload()
                if not blob.exists():
                    raise FileNotFoundError(f"File not found in GCS: {path}")
            except NotFound:
                raise FileNotFoundError(f"File not found in GCS: {path}")
            except Forbidden:
                logger.warning(f"Limited permissions to access GCS blob: {path}")

        return blob

    def _list_blobs_with_prefix(self, prefix: str, delimiter: Optional[str] = None) -> List[storage.Blob]:
        """List blobs with a given prefix."""
        normalized_prefix = self.normalize_path(prefix)
        return list(self.bucket.list_blobs(prefix=normalized_prefix, delimiter=delimiter))

    def _check_is_public(self, blob) -> bool:
        """Check if a blob is publicly accessible."""
        try:
            policy = self.bucket.get_iam_policy()
            for binding in policy.bindings:
                if binding["role"] == "roles/storage.objectViewer":
                    if "allUsers" in binding["members"]:
                        return True
            return False
        except Exception:
            return False

    def _ensure_directory_exists(self, path: str) -> None:
        """
        Ensure the directory for the given file path exists.
        In GCS, directories are virtual, but we still create a placeholder object.

        Args:
            path: Path to a file
        """
        directory_path = os.path.dirname(self.normalize_path(path))
        if directory_path:
            # Create each directory in the path if it doesn't exist
            parts = directory_path.split('/')
            current_path = ""

            for part in parts:
                if part:
                    current_path = f"{current_path}/{part}" if current_path else part
                    # Only create if it doesn't exist
                    if not self.directory_exists(current_path):
                        self.create_directory(current_path)

    def read_file(self, path: str) -> bytes:
        """
        Read a file and return its contents as bytes.
        """
        blob = self._get_blob(path, must_exist=True)

        try:
            return blob.download_as_bytes()
        except Exception as e:
            logger.error(f"Error reading file from GCS {path}: {str(e)}")
            raise IOError(f"Error reading file from GCS: {str(e)}")

    def write_file(self, path: str, data: Union[bytes, str, BinaryIO], content_type: Optional[str] = None) -> bool:
        """
        Write data to a file in GCS.
        """
        # Ensure directory exists
        self._ensure_directory_exists(path)

        blob = self._get_blob(path)

        try:
            if isinstance(data, bytes):
                blob.upload_from_string(data, content_type=content_type)
            elif isinstance(data, str):
                blob.upload_from_string(data, content_type=content_type or 'text/plain')
            elif hasattr(data, 'read'):  # File-like object
                blob.upload_from_file(data, content_type=content_type)
            else:
                raise TypeError(f"Unsupported data type: {type(data)}")

            return True
        except Exception as e:
            logger.error(f"Error writing file to GCS {path}: {str(e)}")
            raise IOError(f"Error writing file to GCS: {str(e)}")

    def delete_file(self, path: str) -> bool:
        """
        Delete a file from GCS.
        """
        blob = self._get_blob(path)

        try:
            if not blob.exists():
                return False

            blob.delete()
            return True
        except Exception as e:
            logger.error(f"Error deleting file from GCS {path}: {str(e)}")
            raise IOError(f"Error deleting file from GCS: {str(e)}")

    def copy_file(self, source_path: str, dest_path: str) -> bool:
        """
        Copy a file within GCS.
        """
        source_blob = self._get_blob(source_path, must_exist=True)

        # Ensure destination directory exists
        self._ensure_directory_exists(dest_path)

        dest_blob = self._get_blob(dest_path)

        try:
            self.bucket.copy_blob(source_blob, self.bucket, dest_blob.name)
            return True
        except Exception as e:
            logger.error(f"Error copying file in GCS from {source_path} to {dest_path}: {str(e)}")
            raise IOError(f"Error copying file in GCS: {str(e)}")

    def move_file(self, source_path: str, dest_path: str) -> bool:
        """
        Move a file within GCS (copy and delete).
        """
        try:
            self.copy_file(source_path, dest_path)
            self.delete_file(source_path)
            return True
        except Exception as e:
            logger.error(f"Error moving file in GCS from {source_path} to {dest_path}: {str(e)}")
            raise IOError(f"Error moving file in GCS: {str(e)}")

    def file_exists(self, path: str) -> bool:
        """
        Check if a file exists in GCS.
        """
        blob = self._get_blob(path)
        return blob.exists()

    def get_file_size(self, path: str) -> int:
        """
        Get the size of a file in GCS.
        """
        blob = self._get_blob(path, must_exist=True)
        return blob.size

    def get_file_metadata(self, path: str) -> Dict[str, Any]:
        """Get metadata about a file in GCS."""
        blob = self._get_blob(path, must_exist=True)
        blob.reload()

        is_public = self._check_is_public(blob)

        return {
            'path': path,
            'name': blob.name,
            'bucket': blob.bucket.name,
            'size': blob.size,
            'content_type': blob.content_type,
            'created': blob.time_created,
            'updated': blob.updated,
            'md5_hash': blob.md5_hash,
            'etag': blob.etag,
            'generation': blob.generation,
            'metageneration': blob.metageneration,
            'storage_class': blob.storage_class,
            'public_url': blob.public_url if is_public else None,
            'is_public': is_public
        }

    def get_created_time(self, path: str) -> datetime:
        """
        Get the creation time of a file in GCS.

        Args:
            path: Path to the file

        Returns:
            datetime: Creation time of the file

        Raises:
            FileNotFoundError: If the file doesn't exist
        """
        blob = self._get_blob(path, must_exist=True)
        blob.reload()
        return blob.time_created

    def get_file_checksum(self, path: str, algorithm: str = 'md5') -> str:
        """
        Get checksum for a file in GCS.
        For MD5, GCS provides this natively. For other algorithms, download and calculate.
        """
        blob = self._get_blob(path, must_exist=True)

        if algorithm.lower() == 'md5':
            # GCS provides MD5 hashes natively
            blob.reload()  # Make sure we have the latest metadata
            if blob.md5_hash:
                return blob.md5_hash

        # For other algorithms or if MD5 isn't available, download and calculate
        data = self.read_file(path)

        if algorithm.lower() == 'md5':
            hash_obj = hashlib.md5()
        elif algorithm.lower() == 'sha1':
            hash_obj = hashlib.sha1()
        elif algorithm.lower() == 'sha256':
            hash_obj = hashlib.sha256()
        else:
            raise ValueError(f"Unsupported hash algorithm: {algorithm}")

        hash_obj.update(data)
        return hash_obj.hexdigest()

    def list_files(self, directory_path: str, recursive: bool = False, pattern: Optional[str] = None) -> List[str]:
        """
        List files in a directory in GCS.
        """
        import fnmatch

        normalized_path = self.normalize_path(directory_path)
        # Make sure the path ends with a slash for directory-like behavior
        if normalized_path and not normalized_path.endswith('/'):
            normalized_path += '/'

        try:
            # Get blobs with the prefix
            blobs = list(self.bucket.list_blobs(prefix=normalized_path))

            # If no blobs found, check if the directory exists
            if not blobs and normalized_path:
                # Check if any blob exists with this prefix
                test_blobs = list(self.bucket.list_blobs(prefix=normalized_path, max_results=1))
                if not test_blobs:
                    err_msg = f"Directory not found in GCS: {directory_path}"
                    logger.error(err_msg)
                    raise FileNotFoundError(err_msg)

            result = []
            for blob in blobs:
                # Skip the directory itself
                if blob.name == normalized_path:
                    continue

                # If not recursive, only include files directly in this directory
                if not recursive:
                    relative_name = blob.name[len(normalized_path):]
                    if '/' in relative_name:
                        continue

                # Apply pattern filtering if specified
                if pattern and not fnmatch.fnmatch(os.path.basename(blob.name), pattern):
                    continue

                result.append(blob.name)

            return result
        except FileNotFoundError:
            raise
        except Exception as e:
            logger.error(f"Error listing files in GCS {directory_path}: {str(e)}")
            raise IOError(f"Error listing files in GCS: {str(e)}")

    def create_directory(self, path: str) -> bool:
        """Create a directory marker object in GCS."""
        normalized_path = self.normalize_path(path)
        if not normalized_path.endswith('/'):
            normalized_path += '/'

        try:
            # Check if directory already exists
            if self.directory_exists(normalized_path):
                return False

            # Create an empty blob with a trailing slash to represent the directory
            blob = self.bucket.blob(normalized_path)
            blob.upload_from_string('', content_type='application/x-directory')

            # Double check creation
            return self.directory_exists(normalized_path)
        except Exception as e:
            logger.error(f"Error creating directory in GCS {path}: {str(e)}")
            raise IOError(f"Error creating directory in GCS: {str(e)}")

    def delete_directory(self, path: str, recursive: bool = False) -> bool:
        """Delete a directory and its contents from GCS."""
        normalized_path = self.normalize_path(path)
        if not normalized_path.endswith('/'):
            normalized_path += '/'

        try:
            # List all blobs in the directory
            blobs = self._list_blobs_with_prefix(normalized_path)
            if not blobs:
                return False

            # Filter out the directory marker itself
            content_blobs = [b for b in blobs if b.name != normalized_path]

            # Check if directory is empty when recursive=False
            if not recursive and content_blobs:
                raise ValueError(f"Directory not empty: {path}. Use recursive=True to delete non-empty directories.")

            # Delete all blobs
            for blob in blobs:
                try:
                    blob.delete()
                except NotFound:
                    pass  # Ignore if blob was already deleted

            # Verify deletion
            remaining_blobs = self._list_blobs_with_prefix(normalized_path)
            return len(remaining_blobs) == 0

        except ValueError:
            raise
        except Exception as e:
            logger.error(f"Error deleting directory from GCS {path}: {str(e)}")
            raise IOError(f"Error deleting directory from GCS: {str(e)}")

    def directory_exists(self, path: str) -> bool:
        """Check if a directory exists in GCS."""
        normalized_path = self.normalize_path(path)
        if not normalized_path.endswith('/'):
            normalized_path += '/'

        # Get a single blob with this prefix to check existence
        blobs = list(self.bucket.list_blobs(prefix=normalized_path, max_results=1))
        return len(blobs) > 0

    def generate_signed_url(self, path: str, expiration: int = 3600) -> str:
        """
        Generate a signed URL for temporary access to a file in GCS.
        """
        blob = self._get_blob(path, must_exist=True)

        try:
            # Generate a signed URL that expires after the specified time
            url = blob.generate_signed_url(
                version="v4",
                expiration=timedelta(seconds=expiration),
                method="GET"
            )
            return url
        except Exception as e:
            logger.error(f"Error generating signed URL for GCS file {path}: {str(e)}")
            raise IOError(f"Error generating signed URL: {str(e)}")

    def make_public(self, path: str) -> bool:
        """Make a file publicly accessible in GCS."""
        blob = self._get_blob(path, must_exist=True)

        try:
            # Try to modify bucket IAM policy
            policy = self.bucket.get_iam_policy(requested_policy_version=3)

            # Initialize policy if needed
            if not hasattr(policy, 'version'):
                policy.version = 3

            # Create new binding for public access
            binding_found = False
            for binding in policy.bindings:
                if binding["role"] == "roles/storage.objectViewer":
                    if "allUsers" not in binding["members"]:
                        binding["members"].append("allUsers")
                    binding_found = True
                    break

            if not binding_found:
                policy.bindings.append({
                    "role": "roles/storage.objectViewer",
                    "members": ["allUsers"]
                })

            # Set the updated policy
            self.bucket.set_iam_policy(policy)

            # Verify public access was set
            if self._check_is_public(blob):
                return True

            # If IAM update succeeded but verification failed, try legacy ACL
            try:
                blob.make_public()
                return True
            except BadRequest as be:
                if "uniform bucket-level access" in str(be).lower():
                    logger.warning(
                        "Bucket has uniform bucket-level access enabled. Individual object ACLs not supported.")
                return False

        except Exception as e:
            logger.error(f"Error making file public in GCS {path}: {str(e)}")
            return False

    def make_private(self, path: str) -> bool:
        """Make a file private in GCS."""
        blob = self._get_blob(path, must_exist=True)

        try:
            # Try uniform bucket-level access first
            policy = self.bucket.get_iam_policy()
            new_bindings = []
            for binding in policy.bindings:
                if binding["role"] == "roles/storage.objectViewer":
                    if "allUsers" in binding["members"]:
                        binding["members"].remove("allUsers")
                    if binding["members"]:  # Only keep if there are other members
                        new_bindings.append(binding)
                else:
                    new_bindings.append(binding)
            policy.bindings = new_bindings
            self.bucket.set_iam_policy(policy)
            return True
        except Exception as e:
            try:
                # Fall back to legacy ACL if available
                blob.make_private()
                return True
            except BadRequest as be:
                if "uniform bucket-level access" in str(be).lower():
                    logger.warning(
                        "Bucket has uniform bucket-level access enabled. Individual object ACLs not supported.")
                    return False
                raise
            except Exception as e:
                logger.error(f"Error making file private in GCS {path}: {str(e)}")
                raise IOError(f"Error making file private: {str(e)}")

    def get_storage_info(self) -> Dict[str, Any]:
        """
        Get information about the GCS storage.
        """
        try:
            return {
                'type': 'gcs',
                'project_id': self.project_id,
                'bucket_name': self.bucket_name,
                'bucket_location': self.bucket.location,
                'bucket_storage_class': self.bucket.storage_class,
                'bucket_creation_time': self.bucket.time_created,
                'bucket_labels': self.bucket.labels,
                'bucket_lifecycle_rules': self.bucket.lifecycle_rules,
                'bucket_versioning_enabled': self.bucket.versioning_enabled
            }
        except Exception as e:
            logger.error(f"Error getting GCS storage info: {str(e)}")
            return {
                'type': 'gcs',
                'project_id': self.project_id,
                'bucket_name': self.bucket_name,
                'error': str(e)
            }
