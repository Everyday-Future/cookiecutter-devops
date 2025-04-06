# core/adapters/storage/storage_adapter.py
import os
import abc
import json
import glob
import pickle
import logging
from typing import BinaryIO, Dict, List, Optional, Union, Any
from datetime import datetime
import fnmatch
import pandas as pd
from config import Config

logger = logging.getLogger(__name__)


class StorageAdapter(abc.ABC):
    """
    Abstract base class for storage adapters.
    Defines the interface that all storage adapters must implement.
    """

    def __init__(self):
        """
        Initialize the storage adapter
        """
        self.name = self.__class__.__name__
        logger.debug(f"Initializing {self.name}")

        # Initialize cache directory
        self.cache_dir = os.path.join(Config.PIPELINE_DIR, 'cache', 'storage')
        os.makedirs(self.cache_dir, exist_ok=True)
        logger.debug(f"Cache directory initialized: {self.cache_dir}")

    def _get_cache_path(self, path: str) -> str:
        """
        Get the local cache path for a storage path.

        Args:
            path: Storage path

        Returns:
            str: Local cache path
        """
        normalized_path = self.normalize_path(path)
        # Replace slashes with triple underscores to create a flat cache structure
        cache_filename = normalized_path.replace("/", "___")
        return os.path.join(self.cache_dir, cache_filename)

    def _storage_path_from_cache(self, cache_path: str) -> str:
        """
        Convert a cache path back to a storage path.

        Args:
            cache_path: Local cache path

        Returns:
            str: Original storage path
        """
        filename = os.path.basename(cache_path)
        return filename.replace("___", "/")

    def clean_cache(self, older_than_days: Optional[float] = None) -> int:
        """
        Clean the cache directory, removing files older than the specified number of days.

        Args:
            older_than_days: Remove files older than this many days, or all if None

        Returns:
            int: Number of files removed
        """
        files_removed = 0
        try:
            # Get all files in the cache directory
            cache_files = glob.glob(os.path.join(self.cache_dir, "*"))

            current_time = datetime.now().timestamp()
            for file_path in cache_files:
                if not os.path.isfile(file_path):
                    continue

                # If older_than_days is specified, check file age
                if older_than_days is not None:
                    file_time = os.path.getmtime(file_path)
                    age_in_days = (current_time - file_time) / (24 * 60 * 60)
                    if age_in_days <= older_than_days:
                        continue

                # Remove the file
                os.remove(file_path)
                files_removed += 1

            return files_removed
        except Exception as e:
            logger.error(f"Error cleaning cache: {str(e)}")
            raise IOError(f"Error cleaning cache: {str(e)}")

    @abc.abstractmethod
    def read_file(self, path: str) -> bytes:
        """
        Read a file and return its contents as bytes.

        Args:
            path: Path to the file

        Returns:
            bytes: File contents

        Raises:
            FileNotFoundError: If the file doesn't exist
            IOError: If there's an error reading the file
        """
        pass

    @abc.abstractmethod
    def write_file(self, path: str, data: Union[bytes, str, BinaryIO], content_type: Optional[str] = None) -> bool:
        """
        Write data to a file.

        Args:
            path: Path where the file should be written
            data: Data to write (bytes, string, or file-like object)
            content_type: MIME type of the content (optional)

        Returns:
            bool: True if successful

        Raises:
            IOError: If there's an error writing the file
        """
        pass

    @abc.abstractmethod
    def delete_file(self, path: str) -> bool:
        """
        Delete a file.

        Args:
            path: Path to the file to delete

        Returns:
            bool: True if the file was deleted, False if it didn't exist

        Raises:
            IOError: If there's an error deleting the file
        """
        pass

    @abc.abstractmethod
    def copy_file(self, source_path: str, dest_path: str) -> bool:
        """
        Copy a file from source_path to dest_path.

        Args:
            source_path: Source file path
            dest_path: Destination file path

        Returns:
            bool: True if successful

        Raises:
            FileNotFoundError: If the source file doesn't exist
            IOError: If there's an error copying the file
        """
        pass

    @abc.abstractmethod
    def move_file(self, source_path: str, dest_path: str) -> bool:
        """
        Move a file from source_path to dest_path.

        Args:
            source_path: Source file path
            dest_path: Destination file path

        Returns:
            bool: True if successful

        Raises:
            FileNotFoundError: If the source file doesn't exist
            IOError: If there's an error moving the file
        """
        pass

    @abc.abstractmethod
    def file_exists(self, path: str) -> bool:
        """
        Check if a file exists.

        Args:
            path: Path to the file

        Returns:
            bool: True if the file exists, False otherwise
        """
        pass

    @abc.abstractmethod
    def get_file_size(self, path: str) -> int:
        """
        Get the size of a file in bytes.

        Args:
            path: Path to the file

        Returns:
            int: Size of the file in bytes

        Raises:
            FileNotFoundError: If the file doesn't exist
        """
        pass

    @abc.abstractmethod
    def get_file_metadata(self, path: str) -> Dict[str, Any]:
        """
        Get metadata about a file.

        Args:
            path: Path to the file

        Returns:
            dict: Dictionary containing metadata (created, modified, size, etc.)

        Raises:
            FileNotFoundError: If the file doesn't exist
        """
        pass

    @abc.abstractmethod
    def get_file_checksum(self, path: str, algorithm: str = 'md5') -> str:
        """
        Calculate a checksum for the file.

        Args:
            path: Path to the file
            algorithm: Hash algorithm to use (default: md5)

        Returns:
            str: Hex digest of the checksum

        Raises:
            FileNotFoundError: If the file doesn't exist
            ValueError: If the algorithm is not supported
        """
        pass

    @abc.abstractmethod
    def list_files(self, directory_path: str, recursive: bool = False, pattern: Optional[str] = None) -> List[str]:
        """
        List files in a directory.

        Args:
            directory_path: Directory path to list
            recursive: Whether to list files recursively
            pattern: Optional glob pattern to filter files

        Returns:
            list: List of file paths

        Raises:
            NotADirectoryError: If the path is not a directory
            FileNotFoundError: If the directory doesn't exist
        """
        pass

    @abc.abstractmethod
    def create_directory(self, path: str) -> bool:
        """
        Create a directory.

        Args:
            path: Directory path to create

        Returns:
            bool: True if the directory was created, False if it already existed

        Raises:
            IOError: If there's an error creating the directory
        """
        pass

    @abc.abstractmethod
    def delete_directory(self, path: str, recursive: bool = False) -> bool:
        """
        Delete a directory.

        Args:
            path: Directory path to delete
            recursive: Whether to delete recursively

        Returns:
            bool: True if the directory was deleted, False if it didn't exist

        Raises:
            IOError: If there's an error deleting the directory
            ValueError: If recursive is False and the directory is not empty
        """
        pass

    @abc.abstractmethod
    def directory_exists(self, path: str) -> bool:
        """
        Check if a directory exists.

        Args:
            path: Directory path

        Returns:
            bool: True if the directory exists, False otherwise
        """
        pass

    @abc.abstractmethod
    def generate_signed_url(self, path: str, expiration: int = 3600) -> str:
        """
        Generate a signed URL for temporary access to a file.

        Args:
            path: Path to the file
            expiration: Expiration time in seconds (default: 1 hour)

        Returns:
            str: Signed URL

        Raises:
            FileNotFoundError: If the file doesn't exist
            NotImplementedError: If signed URLs are not supported
        """
        pass

    @abc.abstractmethod
    def make_public(self, path: str) -> bool:
        """
        Make a file publicly accessible.

        Args:
            path: Path to the file

        Returns:
            bool: True if successful

        Raises:
            FileNotFoundError: If the file doesn't exist
            NotImplementedError: If public access is not supported
        """
        pass

    @abc.abstractmethod
    def make_private(self, path: str) -> bool:
        """
        Make a file private (not publicly accessible).

        Args:
            path: Path to the file

        Returns:
            bool: True if successful

        Raises:
            FileNotFoundError: If the file doesn't exist
            NotImplementedError: If access control is not supported
        """
        pass

    @abc.abstractmethod
    def get_storage_info(self) -> Dict[str, Any]:
        """
        Get information about the storage system.

        Returns:
            dict: Dictionary containing storage information
        """
        pass

    @abc.abstractmethod
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
        pass

    def read_pickle(self, path: str) -> Any:
        """
        Read and deserialize a pickled object from a file.

        Args:
            path: Path to the file

        Returns:
            Any: Deserialized Python object

        Raises:
            FileNotFoundError: If the file doesn't exist
            IOError: If there's an error reading the file
        """
        try:
            # Get file contents as bytes
            data = self.read_file(path)

            # Deserialize the pickle data
            return pickle.loads(data)
        except Exception as e:
            logger.error(f"Error reading pickle from {path}: {str(e)}")
            raise IOError(f"Error reading pickle from {path}: {str(e)}")

    def write_pickle(self, path: str, target_obj: Any) -> bool:
        """
        Serialize and write a Python object to a file.

        Args:
            path: Path where the file should be written
            target_obj: Python object to serialize and write

        Returns:
            bool: True if successful

        Raises:
            IOError: If there's an error writing the file
        """
        try:
            # Serialize the object
            data = pickle.dumps(target_obj)

            # Write to storage
            return self.write_file(path, data)
        except Exception as e:
            logger.error(f"Error writing pickle to {path}: {str(e)}")
            raise IOError(f"Error writing pickle to {path}: {str(e)}")

    def read_df_pickle(self, path: str) -> pd.DataFrame:
        """
        Read a pandas DataFrame from a pickled file.

        Args:
            path: Path to the file

        Returns:
            pandas.DataFrame: Deserialized DataFrame

        Raises:
            FileNotFoundError: If the file doesn't exist
            IOError: If there's an error reading the file or the file doesn't contain a DataFrame
        """
        try:
            obj = self.read_pickle(path)
            if not isinstance(obj, pd.DataFrame):
                raise ValueError(f"File {path} does not contain a pandas DataFrame")
            return obj
        except Exception as e:
            logger.error(f"Error reading DataFrame from pickle {path}: {str(e)}")
            raise IOError(f"Error reading DataFrame from pickle {path}: {str(e)}")

    def write_df_pickle(self, path: str, target_df: pd.DataFrame) -> bool:
        """
        Serialize and write a pandas DataFrame to a pickled file.

        Args:
            path: Path where the file should be written
            target_df: DataFrame to serialize and write

        Returns:
            bool: True if successful

        Raises:
            IOError: If there's an error writing the file
        """
        if not isinstance(target_df, pd.DataFrame):
            raise ValueError("target_df must be a pandas DataFrame")
        return self.write_pickle(path, target_df)

    def read_csv(self, path: str, sep: str = '\t', **kwargs) -> pd.DataFrame:
        """
        Read a CSV file into a pandas DataFrame.

        Args:
            path: Path to the file
            sep: Delimiter to use (default: tab)
            **kwargs: Additional arguments to pass to pandas.read_csv

        Returns:
            pandas.DataFrame: Parsed DataFrame

        Raises:
            FileNotFoundError: If the file doesn't exist
            IOError: If there's an error reading the file
        """
        # Cache the file locally
        cache_path = self._get_cache_path(path)
        try:
            with open(cache_path, 'wb') as f:
                f.write(self.read_file(path))

            # Read the CSV into a DataFrame
            return pd.read_csv(cache_path, sep=sep, **kwargs)
        except Exception as e:
            logger.error(f"Error reading CSV from {path}: {str(e)}")
            raise IOError(f"Error reading CSV from {path}: {str(e)}")
        finally:
            # Clean up the cached file
            if 'cache_path' in locals() and os.path.exists(cache_path):
                try:
                    os.remove(cache_path)
                except Exception:
                    pass

    def write_csv(self, path: str, target_df: pd.DataFrame, sep: str = '\t', **kwargs) -> bool:
        """
        Write a pandas DataFrame to a CSV file.

        Args:
            path: Path where the file should be written
            target_df: DataFrame to write
            sep: Delimiter to use (default: tab)
            **kwargs: Additional arguments to pass to DataFrame.to_csv

        Returns:
            bool: True if successful

        Raises:
            IOError: If there's an error writing the file
        """
        cache_path = None
        try:
            if not isinstance(target_df, pd.DataFrame):
                raise ValueError("target_df must be a pandas DataFrame")

            # Default arguments
            default_kwargs = {
                'index': False,
                'encoding': 'utf-8'
            }
            # Override defaults with any provided kwargs
            for key, value in default_kwargs.items():
                if key not in kwargs:
                    kwargs[key] = value

            # Create a temporary file and write the DataFrame to it
            cache_path = self._get_cache_path(path)
            target_df.to_csv(cache_path, sep=sep, **kwargs)

            # Upload the file to storage
            with open(cache_path, 'rb') as f:
                result = self.write_file(path, f)

            return result
        except Exception as e:
            logger.error(f"Error writing CSV to {path}: {str(e)}")
            raise IOError(f"Error writing CSV to {path}: {str(e)}")
        finally:
            # Clean up the cached file
            if 'cache_path' in locals() and os.path.exists(cache_path):
                try:
                    os.remove(cache_path)
                except Exception:
                    pass

    def read_json(self, path: str) -> Union[Dict, List]:
        """
        Read a JSON file and parse its contents.

        Args:
            path: Path to the file

        Returns:
            Union[Dict, List]: Parsed JSON data

        Raises:
            FileNotFoundError: If the file doesn't exist
            IOError: If there's an error reading or parsing the file
        """
        try:
            # Get file contents as text
            data = self.read_file(path).decode('utf-8')

            # Parse JSON
            return json.loads(data)
        except Exception as e:
            logger.error(f"Error reading JSON from {path}: {str(e)}")
            raise IOError(f"Error reading JSON from {path}: {str(e)}")

    def write_json(self, path: str, target_obj: Union[Dict, List], indent: int = 2) -> bool:
        """
        Serialize and write data to a JSON file.

        Args:
            path: Path where the file should be written
            target_obj: Python object to serialize and write (must be JSON-serializable)
            indent: Number of spaces for indentation (default: 2)

        Returns:
            bool: True if successful

        Raises:
            IOError: If there's an error writing the file
        """
        try:
            # Convert to JSON string
            json_str = json.dumps(target_obj, indent=indent)

            # Write to storage
            return self.write_file(path, json_str, content_type='application/json')
        except Exception as e:
            logger.error(f"Error writing JSON to {path}: {str(e)}")
            raise IOError(f"Error writing JSON to {path}: {str(e)}")

    def read_text(self, path: str, encoding: str = "utf-8") -> str:
        """
        Read a text file and return its contents as a string.

        Args:
            path: Path to the file
            encoding: Text encoding (default: utf-8)

        Returns:
            str: File contents

        Raises:
            FileNotFoundError: If the file doesn't exist
            IOError: If there's an error reading the file
        """
        try:
            # Get file contents as bytes
            data = self.read_file(path)

            # Decode to string
            return data.decode(encoding)
        except Exception as e:
            logger.error(f"Error reading text from {path}: {str(e)}")
            raise IOError(f"Error reading text from {path}: {str(e)}")

    def write_text(self, path: str, target_str: str, encoding: str = "utf-8") -> bool:
        """
        Write a string to a text file.

        Args:
            path: Path where the file should be written
            target_str: String to write
            encoding: Text encoding (default: utf-8)

        Returns:
            bool: True if successful

        Raises:
            IOError: If there's an error writing the file
        """
        try:
            # Write to storage
            return self.write_file(path, target_str.encode(encoding), content_type='text/plain')
        except Exception as e:
            logger.error(f"Error writing text to {path}: {str(e)}")
            raise IOError(f"Error writing text to {path}: {str(e)}")

    def search(self, search_str: str, base_folder: Optional[str] = None,
               days_until_stale: Optional[float] = None,
               get_creation_date: bool = False) -> Union[List[str], List[Dict[str, Any]]]:
        """
        Search for files matching a pattern.

        Args:
            search_str: Search pattern (glob-style)
            base_folder: Base folder to search in (or all storage if None)
            days_until_stale: Only include files created within this many days (None for all)
            get_creation_date: Whether to include creation dates in results

        Returns:
            Union[List[str], List[Dict[str, Any]]]: List of matching file paths or dicts with metadata

        Raises:
            IOError: If there's an error during search
        """
        try:
            # Determine the directory to search
            search_dir = base_folder if base_folder else ""

            # Get all files in the directory
            all_files = self.list_files(search_dir, recursive=True)

            # Filter by search pattern
            matched_files = []

            for file_path in all_files:
                # Get just the basename for pattern matching
                basename = os.path.basename(file_path)

                # Check if the file matches the pattern
                if fnmatch.fnmatch(basename, search_str):
                    # If we need to filter by creation date
                    if days_until_stale is not None:
                        try:
                            creation_time = self.get_created_time(file_path)
                            age_in_days = (datetime.now() - creation_time).total_seconds() / (24 * 60 * 60)

                            if age_in_days > days_until_stale:
                                continue  # Skip files older than the stale threshold
                        except Exception as e:
                            logger.warning(f"Error getting creation time for {file_path}: {str(e)}")
                            continue

                    # Add to results based on requested format
                    if get_creation_date:
                        try:
                            creation_time = self.get_created_time(file_path)
                            matched_files.append({
                                "path": file_path,
                                "creation_date": creation_time
                            })
                        except Exception as e:
                            logger.warning(f"Error getting creation time for {file_path}: {str(e)}")
                            matched_files.append({
                                "path": file_path,
                                "creation_date": None
                            })
                    else:
                        matched_files.append(file_path)

            return matched_files
        except Exception as e:
            logger.error(f"Error searching for files: {str(e)}")
            raise IOError(f"Error searching for files: {str(e)}")

    @staticmethod
    def normalize_path(path: str) -> str:
        """
        Normalize a path for the storage system.

        Args:
            path: Path to normalize

        Returns:
            str: Normalized path
        """
        # Base implementation just removes leading/trailing whitespace and slash
        path = path.strip().strip('/')
        return path

    @staticmethod
    def dedupe_df(old_df: pd.DataFrame, new_df: pd.DataFrame,
                  dedupe_cols: Union[str, List[str]],
                  days_until_stale: Optional[float] = None,
                  stale_col: str = '_created',
                  keep: str = 'latest') -> pd.DataFrame:
        """
        Merge two DataFrames, removing duplicates based on specified criteria.

        Args:
            old_df: Existing DataFrame
            new_df: New DataFrame to merge
            dedupe_cols: Column(s) to use for deduplication
            days_until_stale: Number of days after which records are considered stale (None for never)
            stale_col: Column containing the timestamp for staleness check
            keep: Which duplicate to keep: 'first' (from old_df) or 'latest' (prefer new_df)

        Returns:
            pandas.DataFrame: Merged DataFrame with duplicates removed

        Raises:
            ValueError: If input parameters are invalid
        """
        # Input validation
        if old_df is None and new_df is None:
            raise ValueError("Both DataFrames cannot be None")

        if old_df is None:
            return new_df.copy()

        if new_df is None or len(new_df) == 0:
            return old_df.copy()

        if isinstance(dedupe_cols, str):
            dedupe_cols = [dedupe_cols]

        # Validate that dedupe columns exist in both DataFrames
        for col in dedupe_cols:
            if col not in old_df.columns:
                raise ValueError(f"Column {col} not found in old_df")
            if col not in new_df.columns:
                raise ValueError(f"Column {col} not found in new_df")

        if days_until_stale is not None and stale_col not in old_df.columns:
            raise ValueError(f"Stale column {stale_col} not found in old_df")

        if keep not in ['first', 'latest']:
            raise ValueError("'keep' must be either 'first' or 'latest'")

        # Create key lists for both datasets
        old_keys = [tuple(row) for row in old_df[dedupe_cols].values]
        new_keys = [tuple(row) for row in new_df[dedupe_cols].values]

        # Identify stale records in old_df if applicable
        if days_until_stale is not None:
            current_time = datetime.now().timestamp() / (24 * 60 * 60)  # Convert to days

            # Create a mask for fresh records
            if isinstance(old_df[stale_col].iloc[0], (int, float)):
                # Assuming stale_col contains epoch time in days
                fresh_mask = [(current_time - val) <= days_until_stale for val in old_df[stale_col]]
            else:
                # Assuming stale_col contains datetime objects
                fresh_mask = [
                    (current_time - pd.Timestamp(dt).timestamp() / (24 * 60 * 60)) <= days_until_stale
                    for dt in old_df[stale_col]
                ]

            # Mark which keys are fresh vs. stale
            fresh_keys = {key: is_fresh for key, is_fresh in zip(old_keys, fresh_mask)}
        else:
            # Without staleness check, all old records are considered "fresh"
            fresh_keys = {key: True for key in old_keys}

        # Handle the merging strategy based on 'keep' parameter
        if keep == 'first':
            # Strategy for keep='first':
            # 1. Keep all records from old_df that don't have duplicates in new_df
            # 2. For each stale record in old_df that has a duplicate in new_df, use the new record
            # 3. For each fresh record in old_df that has a duplicate in new_df, keep the old record

            # Start with all records from old_df
            result = old_df.copy()
            result_keys = set(old_keys)

            # Add new records that don't exist in old_df or replace stale records
            rows_to_add = []
            for i, key in enumerate(new_keys):
                if key not in result_keys:  # New record, not in old_df
                    rows_to_add.append(i)
                elif key in fresh_keys and not fresh_keys[key]:  # Stale record in old_df
                    # Remove the old record
                    old_idx = old_keys.index(key)
                    result = result.drop(old_idx)
                    result_keys.remove(key)
                    # Add the new record
                    rows_to_add.append(i)

            # Add the selected rows from new_df
            if rows_to_add:
                result = pd.concat([result, new_df.iloc[rows_to_add]], ignore_index=True)

        else:  # keep == 'latest'
            # Strategy for keep='latest':
            # 1. Start with all records from old_df that don't have duplicates in new_df
            # 2. Add all records from new_df

            # Get records from old_df that don't have duplicates in new_df
            rows_to_keep = []
            for i, key in enumerate(old_keys):
                if key not in new_keys:
                    rows_to_keep.append(i)

            # Combine filtered old records with all new records
            if rows_to_keep:
                result = pd.concat([old_df.iloc[rows_to_keep], new_df], ignore_index=True)
            else:
                result = new_df.copy()

        return result

    @staticmethod
    def collect_dataset(storage_adapter, search_str: str, base_folder: str,
                        days_until_stale: Optional[float], dedupe_cols: Union[str, List[str]],
                        new_df: Optional[pd.DataFrame] = None, keep: str = 'latest',
                        stale_col: str = '_created', force: bool = False) -> pd.DataFrame:
        """
        Search for DataFrames, load them, and merge with deduplication.

        Args:
            storage_adapter: Storage adapter instance to use for searching and loading
            search_str: Search pattern for files
            base_folder: Base folder to search in
            days_until_stale: Only include files created within this many days
            dedupe_cols: Column(s) to use for deduplication
            new_df: Optional new DataFrame to include in the merge
            keep: Which duplicate to keep: 'first' or 'latest'
            stale_col: Column containing the timestamp for staleness check
            force: If True, skip files that can't be read instead of failing

        Returns:
            pandas.DataFrame: Merged DataFrame with duplicates removed

        Raises:
            IOError: If there's an error loading files and force is False
        """
        # Search for matching files
        matching_files = storage_adapter.search(
            search_str,
            base_folder=base_folder,
            days_until_stale=days_until_stale,
            get_creation_date=False
        )

        if not matching_files and new_df is None:
            # No files found and no new data
            return pd.DataFrame()

        # Load each file and merge
        combined_df = None

        for file_path in matching_files:
            try:
                if file_path.endswith('.pkl'):
                    df = storage_adapter.read_df_pickle(file_path)
                elif file_path.endswith('.csv'):
                    df = storage_adapter.read_csv(file_path)
                else:
                    logger.warning(f"Unknown file type for {file_path}, skipping")
                    continue

                if combined_df is None:
                    combined_df = df
                else:
                    combined_df = StorageAdapter.dedupe_df(
                        combined_df, df, dedupe_cols,
                        days_until_stale=days_until_stale,
                        stale_col=stale_col, keep=keep
                    )
            except Exception as e:
                if force:
                    logger.warning(f"Error reading {file_path}, skipping: {str(e)}")
                    continue
                else:
                    logger.error(f"Error reading {file_path}: {str(e)}")
                    raise IOError(f"Error reading {file_path}: {str(e)}")

        # Merge with new_df if provided
        if new_df is not None:
            if combined_df is None:
                combined_df = new_df
            else:
                combined_df = StorageAdapter.dedupe_df(
                    combined_df, new_df, dedupe_cols,
                    days_until_stale=days_until_stale,
                    stale_col=stale_col, keep=keep
                )

        return combined_df if combined_df is not None else pd.DataFrame()

    def upload_directory(self, local_path: str, dest_path: str,
                         include_pattern: Optional[str] = None,
                         exclude_pattern: Optional[str] = None) -> Dict[str, int]:
        """
        Upload a local directory to the storage system.

        Args:
            local_path: Path to the local directory to upload
            dest_path: Destination path in the storage system
            include_pattern: Optional glob pattern to include files (e.g., "*.txt")
            exclude_pattern: Optional glob pattern to exclude files (e.g., "*.tmp")

        Returns:
            dict: Statistics about the upload operation (files uploaded, skipped, failed)

        Raises:
            ValueError: If local_path is not a directory
            IOError: If there's an error during upload
        """
        if not os.path.isdir(local_path):
            raise ValueError(f"Local path is not a directory: {local_path}")

        # Normalize destination path
        dest_path = self.normalize_path(dest_path)

        # Ensure destination directory exists
        if not self.directory_exists(dest_path):
            self.create_directory(dest_path)

        stats = {
            "files_total": 0,
            "files_uploaded": 0,
            "files_skipped": 0,
            "files_failed": 0,
            "bytes_transferred": 0
        }

        # Track failures for reporting
        failures = []

        # Recursively walk through the local directory
        try:
            for root, dirs, files in os.walk(local_path):
                # Calculate the relative path from local_path
                rel_path = os.path.relpath(root, local_path)
                if rel_path == '.':
                    rel_path = ''

                # Create the corresponding subdirectory in the storage system if needed
                if rel_path:
                    storage_dir = os.path.join(dest_path, rel_path).replace('\\', '/')
                    if not self.directory_exists(storage_dir):
                        self.create_directory(storage_dir)

                # Process each file in the current directory
                for file in files:
                    stats["files_total"] += 1

                    # Check include/exclude patterns
                    if include_pattern and not fnmatch.fnmatch(file, include_pattern):
                        stats["files_skipped"] += 1
                        continue

                    if exclude_pattern and fnmatch.fnmatch(file, exclude_pattern):
                        stats["files_skipped"] += 1
                        continue

                    # Construct local and storage paths
                    local_file_path = os.path.join(root, file)
                    if rel_path:
                        storage_file_path = os.path.join(dest_path, rel_path, file).replace('\\', '/')
                    else:
                        storage_file_path = os.path.join(dest_path, file).replace('\\', '/')

                    try:
                        # Open and upload the file
                        with open(local_file_path, 'rb') as f:
                            self.write_file(storage_file_path, f)

                        # Update statistics
                        stats["files_uploaded"] += 1
                        stats["bytes_transferred"] += os.path.getsize(local_file_path)

                    except Exception as e:
                        stats["files_failed"] += 1
                        failures.append({
                            "file": local_file_path,
                            "error": str(e)
                        })
                        logger.error(f"Error uploading file {local_file_path} to {storage_file_path}: {str(e)}")

            # Add failures to the stats if any occurred
            if failures:
                stats["failures"] = failures

            return stats

        except Exception as e:
            logger.error(f"Error during directory upload from {local_path} to {dest_path}: {str(e)}")
            raise IOError(f"Error during directory upload: {str(e)}")


class StorageAdapterFactory:
    """
    Factory class for creating storage adapters based on configuration.
    """

    @staticmethod
    def create_adapter(storage_type=None) -> StorageAdapter:
        """
        Create and return a storage adapter based on configuration.

        Returns:
            StorageAdapter: Configured storage adapter instance

        Raises:
            ValueError: If the storage type is invalid or not supported
        """

        # Determine which adapter to use based on config
        storage_type = storage_type or Config.STORAGE_TYPE
        if storage_type == 'local':
            from core.adapters.storage.local_storage import LocalStorageAdapter
            return LocalStorageAdapter()
        elif storage_type == 'network':
            from core.adapters.storage.network_storage import NetworkStorageAdapter
            return NetworkStorageAdapter()
        elif storage_type == 'gcs' or storage_type == 'google' or storage_type == 'gcp':
            from core.adapters.storage.gcp_storage import GCSStorageAdapter
            return GCSStorageAdapter()
        elif storage_type == 's3' or storage_type == 'aws':
            from core.adapters.storage.aws_storage import S3StorageAdapter
            return S3StorageAdapter()
        else:
            raise ValueError(f"Unsupported storage type: {storage_type}")
