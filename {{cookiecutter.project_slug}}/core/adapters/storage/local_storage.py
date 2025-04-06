# core/adapters/storage/local_storage.py
import os
import shutil
import hashlib
import fnmatch
import logging
from typing import BinaryIO, Dict, List, Optional, Union, Any
from datetime import datetime
from config import Config
from .storage_adapter import StorageAdapter

logger = logging.getLogger(__name__)


class LocalStorageAdapter(StorageAdapter):
    """
    Storage adapter for the local file system.
    """

    def __init__(self):
        """
        Initialize the local storage adapter.
        """
        super().__init__()
        self.base_dir = Config.PIPELINE_DIR
        # Create the base directory if it doesn't exist
        os.makedirs(self.base_dir, exist_ok=True)
        logger.info(f"LocalStorageAdapter initialized with base directory: {self.base_dir}")

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

    def read_file(self, path: str) -> bytes:
        """
        Read a file and return its contents as bytes.
        """
        full_path = self._get_full_path(path)

        if not os.path.isfile(full_path):
            raise FileNotFoundError(f"File not found: {path}")

        try:
            with open(full_path, 'rb') as file:
                return file.read()
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
            # Handle different types of data
            if isinstance(data, bytes):
                with open(full_path, 'wb') as file:
                    file.write(data)
            elif isinstance(data, str):
                with open(full_path, 'w', encoding='utf-8') as file:
                    file.write(data)
            elif hasattr(data, 'read'):  # File-like object
                with open(full_path, 'wb') as file:
                    shutil.copyfileobj(data, file)
            else:
                raise TypeError(f"Unsupported data type: {type(data)}")

            return True
        except Exception as e:
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
            os.remove(full_path)
            return True
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
            shutil.copy2(full_source_path, full_dest_path)
            return True
        except Exception as e:
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
            shutil.move(full_source_path, full_dest_path)
            return True
        except Exception as e:
            logger.error(f"Error moving file from {source_path} to {dest_path}: {str(e)}")
            raise IOError(f"Error moving file: {str(e)}")

    def file_exists(self, path: str) -> bool:
        """
        Check if a file exists.
        """
        full_path = self._get_full_path(path)
        return os.path.isfile(full_path)

    def get_file_size(self, path: str) -> int:
        """
        Get the size of a file in bytes.
        """
        full_path = self._get_full_path(path)

        if not os.path.isfile(full_path):
            raise FileNotFoundError(f"File not found: {path}")

        return os.path.getsize(full_path)

    def get_file_metadata(self, path: str) -> Dict[str, Any]:
        """
        Get metadata about a file.
        """
        full_path = self._get_full_path(path)

        if not os.path.isfile(full_path):
            raise FileNotFoundError(f"File not found: {path}")

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

        # Get the creation time (or the closest equivalent on this OS)
        # On Unix systems, this is usually the inode change time (ctime)
        stat = os.stat(full_path)
        return datetime.fromtimestamp(stat.st_ctime)

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
            os.makedirs(full_path, exist_ok=True)
            return True
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
            if recursive:
                shutil.rmtree(full_path)
            else:
                os.rmdir(full_path)  # Will fail if directory is not empty

            return True
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
        return os.path.isdir(full_path)

    def generate_signed_url(self, path: str, expiration: int = 3600) -> str:
        """
        Generate a signed URL for temporary access to a file.
        For local storage, this isn't really applicable, so we just return the local file path.
        """
        full_path = self._get_full_path(path)

        if not os.path.isfile(full_path):
            raise FileNotFoundError(f"File not found: {path}")

        # Local storage doesn't really have signed URLs, but we can return the full path
        # In a real application, this might be a URL to a local file server
        return f"file://{os.path.abspath(full_path)}"

    def make_public(self, path: str) -> bool:
        """
        Make a file publicly accessible.
        For local storage, this isn't really applicable.
        """
        full_path = self._get_full_path(path)

        if not os.path.exists(full_path):
            raise FileNotFoundError(f"File not found: {path}")

        # Local storage doesn't have public/private access control
        logger.warning("make_public() has no effect for LocalStorageAdapter")
        return True

    def make_private(self, path: str) -> bool:
        """
        Make a file private.
        For local storage, this isn't really applicable.
        """
        full_path = self._get_full_path(path)

        if not os.path.exists(full_path):
            raise FileNotFoundError(f"File not found: {path}")

        # Local storage doesn't have public/private access control
        logger.warning("make_private() has no effect for LocalStorageAdapter")
        return True

    def get_storage_info(self) -> Dict[str, Any]:
        """
        Get information about the local storage system.
        """
        try:
            total, used, free = shutil.disk_usage(self.base_dir)

            return {
                'type': 'local',
                'base_directory': self.base_dir,
                'total_space': total,
                'used_space': used,
                'free_space': free,
                'free_space_percent': (free / total) * 100 if total > 0 else 0
            }
        except Exception as e:
            logger.error(f"Error getting storage info: {str(e)}")
            return {
                'type': 'local',
                'base_directory': self.base_dir,
                'error': str(e)
            }
