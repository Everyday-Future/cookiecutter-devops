# core/adapters/storage/network_storage.py
import os
import shutil
import hashlib
import fnmatch
import logging
import tempfile
from typing import BinaryIO, Dict, List, Optional, Union, Any
from datetime import datetime
from config import Config
from .storage_adapter import StorageAdapter

logger = logging.getLogger(__name__)


class NetworkStorageAdapter(StorageAdapter):
    """
    Storage adapter for network file systems like NFS, SMB/CIFS, etc.
    This adapter is similar to the local file system adapter but tailored for network shares.
    """

    def __init__(self):
        """
        Initialize the network storage adapter.
        """
        super().__init__()
        # Get network share configuration
        self.mount_point = Config.NETWORK_MOUNT_POINT
        self.share_type = Config.NETWORK_SHARE_TYPE
        self.timeout = Config.NETWORK_TIMEOUT
        self.retry_count = Config.NETWORK_RETRY_COUNT
        if not self.mount_point:
            raise ValueError("NETWORK_MOUNT_POINT must be specified")
        # Validate that the mount point exists
        if not os.path.exists(self.mount_point):
            raise ValueError(f"Mount point does not exist: {self.mount_point}")
        # Create base directory path
        self.base_dir = os.path.join(self.mount_point, Config.NETWORK_BASE_DIR)
        # Create the base directory if it doesn't exist
        os.makedirs(self.base_dir, exist_ok=True)
        logger.info(f"NetworkStorageAdapter initialized with base directory: {self.base_dir} ({self.share_type})")

    def normalize_path(self, path: str) -> str:
        """Normalize path separators and remove leading/trailing whitespace."""
        # First apply base normalization
        path = super().normalize_path(path)
        # Convert Windows separators to POSIX
        return path.replace('\\', '/')

    def _get_full_path(self, path: str) -> str:
        """
        Get the full path by combining the base directory and the relative path.

        Args:
            path: Relative path

        Returns:
            str: Full path
        """
        normalized_path = self.normalize_path(path)
        return os.path.join(self.base_dir, normalized_path)

    def _ensure_directory_exists(self, path: str) -> None:
        """
        Ensure the directory for the given file path exists.

        Args:
            path: Path to a file
        """
        directory = os.path.dirname(self._get_full_path(path))
        if directory and not os.path.exists(directory):
            os.makedirs(directory, exist_ok=True)

    def _retry_operation(self, operation_func, *args, **kwargs):
        """
        Retry an operation with exponential backoff.

        Args:
            operation_func: Function to retry
            *args: Arguments to pass to the function
            **kwargs: Keyword arguments to pass to the function

        Returns:
            The result of the function

        Raises:
            The last exception encountered
        """
        import time
        from functools import wraps

        @wraps(operation_func)
        def wrapper(*args, **kwargs):
            last_exception = None
            for attempt in range(self.retry_count):
                try:
                    return operation_func(*args, **kwargs)
                except (IOError, OSError) as e:
                    last_exception = e
                    # Exponential backoff with a bit of randomness
                    delay = (2 ** attempt) * 0.1 + (attempt * 0.1)
                    logger.warning(f"Network operation failed, retrying in {delay:.2f} seconds... "
                                   f"({attempt + 1}/{self.retry_count})")
                    time.sleep(delay)

            # If we get here, all retries failed
            logger.error(f"Operation failed after {self.retry_count} attempts")
            raise last_exception

        return wrapper(*args, **kwargs)

    def read_file(self, path: str) -> bytes:
        """
        Read a file and return its contents as bytes.
        """
        full_path = self._get_full_path(path)

        if not os.path.isfile(full_path):
            raise FileNotFoundError(f"File not found: {path}")

        try:
            def _read():
                with open(full_path, 'rb') as file:
                    return file.read()

            return self._retry_operation(_read)
        except Exception as e:
            logger.error(f"Error reading file {path}: {str(e)}")
            raise IOError(f"Error reading file: {str(e)}")

    def write_file(self, path: str, data: Union[bytes, str, BinaryIO], content_type: Optional[str] = None) -> bool:
        """
        Write data to a file.
        """
        full_path = self._get_full_path(path)

        # Create parent directories if they don't exist
        self._ensure_directory_exists(path)

        try:
            # Use a temporary file and then move it to the final location
            # This helps with network issues and ensures atomicity
            with tempfile.NamedTemporaryFile(delete=False) as temp_file:
                temp_path = temp_file.name

                # Handle different types of data
                if isinstance(data, bytes):
                    temp_file.write(data)
                elif isinstance(data, str):
                    temp_file.write(data.encode('utf-8'))
                elif hasattr(data, 'read'):  # File-like object
                    shutil.copyfileobj(data, temp_file)
                else:
                    os.unlink(temp_path)
                    raise TypeError(f"Unsupported data type: {type(data)}")

            # Move the temporary file to the final location
            def _move_file():
                shutil.move(temp_path, full_path)
                return True

            return self._retry_operation(_move_file)
        except Exception as e:
            # Clean up temporary file if it exists
            if 'temp_path' in locals() and os.path.exists(temp_path):
                try:
                    os.unlink(temp_path)
                except Exception:
                    pass

            logger.error(f"Error writing file {path}: {str(e)}")
            raise IOError(f"Error writing file: {str(e)}")

    def delete_file(self, path: str) -> bool:
        """
        Delete a file.
        """
        full_path = self._get_full_path(path)

        if not os.path.isfile(full_path):
            return False

        try:
            def _delete():
                os.remove(full_path)
                return True

            return self._retry_operation(_delete)
        except Exception as e:
            logger.error(f"Error deleting file {path}: {str(e)}")
            raise IOError(f"Error deleting file: {str(e)}")

    def copy_file(self, source_path: str, dest_path: str) -> bool:
        """
        Copy a file from source_path to dest_path.
        """
        full_source_path = self._get_full_path(source_path)
        full_dest_path = self._get_full_path(dest_path)

        if not os.path.isfile(full_source_path):
            raise FileNotFoundError(f"Source file not found: {source_path}")

        # Create parent directories for destination if they don't exist
        self._ensure_directory_exists(dest_path)

        try:
            def _copy():
                # Use a temporary destination file first
                temp_dest_path = f"{full_dest_path}.tmp"
                shutil.copy2(full_source_path, temp_dest_path)
                os.replace(temp_dest_path, full_dest_path)
                return True

            return self._retry_operation(_copy)
        except Exception as e:
            # Clean up temporary file if it exists
            temp_dest_path = f"{full_dest_path}.tmp"
            if os.path.exists(temp_dest_path):
                try:
                    os.unlink(temp_dest_path)
                except Exception:
                    pass

            logger.error(f"Error copying file from {source_path} to {dest_path}: {str(e)}")
            raise IOError(f"Error copying file: {str(e)}")

    def move_file(self, source_path: str, dest_path: str) -> bool:
        """
        Move a file from source_path to dest_path.
        """
        full_source_path = self._get_full_path(source_path)
        full_dest_path = self._get_full_path(dest_path)

        if not os.path.isfile(full_source_path):
            raise FileNotFoundError(f"Source file not found: {source_path}")

        # Create parent directories for destination if they don't exist
        self._ensure_directory_exists(dest_path)

        try:
            # First copy, then delete the source
            self.copy_file(source_path, dest_path)
            self.delete_file(source_path)
            return True
        except Exception as e:
            logger.error(f"Error moving file from {source_path} to {dest_path}: {str(e)}")
            raise IOError(f"Error moving file: {str(e)}")

    def file_exists(self, path: str) -> bool:
        """
        Check if a file exists.
        """
        full_path = self._get_full_path(path)

        try:
            def _check_exists():
                return os.path.isfile(full_path)

            return self._retry_operation(_check_exists)
        except Exception as e:
            logger.warning(f"Error checking if file exists {path}: {str(e)}")
            return False

    def get_file_size(self, path: str) -> int:
        """
        Get the size of a file in bytes.
        """
        full_path = self._get_full_path(path)

        if not os.path.isfile(full_path):
            raise FileNotFoundError(f"File not found: {path}")

        try:
            def _get_size():
                return os.path.getsize(full_path)

            return self._retry_operation(_get_size)
        except Exception as e:
            logger.error(f"Error getting file size {path}: {str(e)}")
            raise IOError(f"Error getting file size: {str(e)}")

    def get_file_metadata(self, path: str) -> Dict[str, Any]:
        """
        Get metadata about a file.
        """
        full_path = self._get_full_path(path)

        if not os.path.isfile(full_path):
            raise FileNotFoundError(f"File not found: {path}")

        try:
            def _get_metadata():
                stat = os.stat(full_path)

                return {
                    'path': path,
                    'full_path': full_path,
                    'size': stat.st_size,
                    'created': datetime.fromtimestamp(stat.st_ctime),
                    'modified': datetime.fromtimestamp(stat.st_mtime),
                    'accessed': datetime.fromtimestamp(stat.st_atime),
                    'is_file': True,
                    'is_directory': False,
                    'permissions': stat.st_mode
                }

            return self._retry_operation(_get_metadata)
        except Exception as e:
            logger.error(f"Error getting file metadata {path}: {str(e)}")
            raise IOError(f"Error getting file metadata: {str(e)}")

    def get_created_time(self, path: str) -> datetime:
        """
        Get the creation time of a file.

        Args:
            path: Path to the file

        Returns:
            datetime: Creation time of the file

        Raises:
            FileNotFoundError: If the file doesn't exist
        """
        full_path = self._get_full_path(path)

        if not os.path.isfile(full_path):
            raise FileNotFoundError(f"File not found: {path}")

        try:
            def _get_created_time():
                # Get the creation time (or the closest equivalent on this OS)
                stat = os.stat(full_path)
                return datetime.fromtimestamp(stat.st_ctime)

            return self._retry_operation(_get_created_time)
        except Exception as e:
            logger.error(f"Error getting file creation time {path}: {str(e)}")
            raise IOError(f"Error getting file creation time: {str(e)}")

    def get_file_checksum(self, path: str, algorithm: str = 'md5') -> str:
        """Calculate a checksum for the file."""
        full_path = self._get_full_path(path)

        if not os.path.isfile(full_path):
            raise FileNotFoundError(f"File not found: {path}")

        try:
            if algorithm.lower() == 'md5':
                hash_obj = hashlib.md5()
            elif algorithm.lower() == 'sha1':
                hash_obj = hashlib.sha1()
            elif algorithm.lower() == 'sha256':
                hash_obj = hashlib.sha256()
            else:
                raise ValueError(f"Unsupported hash algorithm: {algorithm}")

            with open(full_path, 'rb') as file:
                for chunk in iter(lambda: file.read(4096), b''):
                    hash_obj.update(chunk)

            return hash_obj.hexdigest()
        except ValueError as e:
            # Re-raise ValueError without wrapping
            raise
        except Exception as e:
            logger.error(f"Error calculating checksum for {path}: {str(e)}")
            raise IOError(f"Error calculating checksum: {str(e)}")

    def list_files(self, directory_path: str, recursive: bool = False, pattern: Optional[str] = None) -> List[str]:
        """List files in a directory."""
        full_dir_path = self._get_full_path(directory_path)

        if not os.path.exists(full_dir_path):
            raise FileNotFoundError(f"Directory not found: {directory_path}")

        if not os.path.isdir(full_dir_path):
            raise NotADirectoryError(f"Not a directory: {directory_path}")

        result = []
        try:
            if recursive:
                for root, _, files in os.walk(full_dir_path):
                    for file in files:
                        file_path = os.path.join(root, file)
                        rel_path = os.path.relpath(file_path, self.base_dir)
                        rel_path = rel_path.replace('\\', '/')

                        if pattern and not fnmatch.fnmatch(file, pattern):
                            continue

                        result.append(rel_path)
            else:
                for item in os.listdir(full_dir_path):
                    item_path = os.path.join(full_dir_path, item)
                    if os.path.isfile(item_path):
                        if pattern and not fnmatch.fnmatch(item, pattern):
                            continue

                        rel_path = os.path.relpath(item_path, self.base_dir)
                        rel_path = rel_path.replace('\\', '/')
                        result.append(rel_path)

            return result
        except Exception as e:
            logger.error(f"Error listing files in {directory_path}: {str(e)}")
            raise IOError(f"Error listing files: {str(e)}")

    def create_directory(self, path: str) -> bool:
        """
        Create a directory.
        """
        full_path = self._get_full_path(path)

        if os.path.exists(full_path):
            if os.path.isdir(full_path):
                return False  # Directory already exists
            else:
                raise IOError(f"Path exists but is not a directory: {path}")

        try:
            def _create_directory():
                os.makedirs(full_path, exist_ok=True)
                return True

            return self._retry_operation(_create_directory)
        except Exception as e:
            logger.error(f"Error creating directory {path}: {str(e)}")
            raise IOError(f"Error creating directory: {str(e)}")

    def delete_directory(self, path: str, recursive: bool = False) -> bool:
        """
        Delete a directory.
        """
        full_path = self._get_full_path(path)

        if not os.path.exists(full_path):
            return False

        if not os.path.isdir(full_path):
            raise NotADirectoryError(f"Not a directory: {path}")

        try:
            def _delete_directory():
                if recursive:
                    shutil.rmtree(full_path)
                else:
                    os.rmdir(full_path)  # Will fail if directory is not empty
                return True

            return self._retry_operation(_delete_directory)
        except OSError as e:
            if not recursive and "Directory not empty" in str(e):
                raise ValueError(f"Directory not empty: {path}. Use recursive=True to delete non-empty directories.")
            logger.error(f"Error deleting directory {path}: {str(e)}")
            raise IOError(f"Error deleting directory: {str(e)}")

    def directory_exists(self, path: str) -> bool:
        """
        Check if a directory exists.
        """
        full_path = self._get_full_path(path)

        try:
            def _check_dir_exists():
                return os.path.isdir(full_path)

            return self._retry_operation(_check_dir_exists)
        except Exception as e:
            logger.warning(f"Error checking if directory exists {path}: {str(e)}")
            return False

    def generate_signed_url(self, path: str, expiration: int = 3600) -> str:
        """
        Generate a signed URL for temporary access to a file.
        For network storage, this isn't really applicable unless there's a web server in front.
        """
        # Network shares typically don't provide web URLs directly
        # This could be implemented by setting up a web server that serves the network share
        full_path = self._get_full_path(path)

        if not os.path.isfile(full_path):
            raise FileNotFoundError(f"File not found: {path}")

        # Return a file URL (not very useful in most cases)
        url = f"file://{os.path.abspath(full_path)}"
        logger.warning(f"Network storage does not support proper signed URLs. Returning file URL: {url}")
        return url

    def make_public(self, path: str) -> bool:
        """
        Make a file publicly accessible.
        For network storage, this could be implemented with file permissions.
        """
        full_path = self._get_full_path(path)

        if not os.path.exists(full_path):
            raise FileNotFoundError(f"File not found: {path}")

        try:
            def _make_public():
                # This is a simplistic approach - in a real implementation,
                # you might set specific permissions based on your network share setup
                os.chmod(full_path, 0o644)  # rw-r--r--
                return True

            return self._retry_operation(_make_public)
        except Exception as e:
            logger.error(f"Error making file public {path}: {str(e)}")
            raise IOError(f"Error making file public: {str(e)}")

    def make_private(self, path: str) -> bool:
        """
        Make a file private.
        For network storage, this could be implemented with file permissions.
        """
        full_path = self._get_full_path(path)

        if not os.path.exists(full_path):
            raise FileNotFoundError(f"File not found: {path}")

        try:
            def _make_private():
                # This is a simplistic approach - in a real implementation,
                # you might set specific permissions based on your network share setup
                os.chmod(full_path, 0o600)  # rw-------
                return True

            return self._retry_operation(_make_private)
        except Exception as e:
            logger.error(f"Error making file private {path}: {str(e)}")
            raise IOError(f"Error making file private: {str(e)}")

    def get_storage_info(self) -> Dict[str, Any]:
        """
        Get information about the network storage system.
        """
        try:
            def _get_storage_info():
                total, used, free = shutil.disk_usage(self.base_dir)

                # Try to get additional network share info (platform-specific)
                share_info = self._get_share_info()

                info = {
                    'type': 'network',
                    'share_type': self.share_type,
                    'mount_point': self.mount_point,
                    'base_directory': self.base_dir,
                    'total_space': total,
                    'used_space': used,
                    'free_space': free,
                    'free_space_percent': (free / total) * 100 if total > 0 else 0
                }

                if share_info:
                    info.update(share_info)

                return info

            return self._retry_operation(_get_storage_info)
        except Exception as e:
            logger.error(f"Error getting storage info: {str(e)}")
            return {
                'type': 'network',
                'share_type': self.share_type,
                'mount_point': self.mount_point,
                'base_directory': self.base_dir,
                'error': str(e)
            }

    def _get_share_info(self) -> Dict[str, Any]:
        """
        Get information about the network share.
        This is a platform-specific operation.

        Returns:
            dict: Dictionary containing share information
        """
        import platform

        system = platform.system()
        info = {}

        if system == 'Linux':
            try:
                # Try to get mount info from /proc/mounts
                with open('/proc/mounts', 'r') as f:
                    for line in f:
                        parts = line.split()
                        if len(parts) >= 2 and parts[1] == self.mount_point:
                            info['device'] = parts[0]
                            info['filesystem_type'] = parts[2]
                            info['mount_options'] = parts[3]
                            break
            except Exception as e:
                logger.warning(f"Error getting Linux share info: {str(e)}")

        elif system == 'Windows':
            try:
                import win32wnet
                # Try to get share info using win32 API
                try:
                    # This will work for mapped network drives
                    info['connection'] = win32wnet.WNetGetConnection(self.mount_point)
                except Exception:
                    pass
            except ImportError:
                logger.warning("win32wnet not available for getting Windows share info")

        return info
