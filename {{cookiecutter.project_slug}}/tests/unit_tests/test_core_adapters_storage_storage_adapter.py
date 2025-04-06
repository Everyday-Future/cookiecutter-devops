# tests/unit/core/adapters/storage/test_storage_adapter.py
import os
import time
import shutil
import pytest
import tempfile
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from unittest.mock import patch

from config import logger
from core.adapters.storage.storage_adapter import StorageAdapter


# Mock StorageAdapter implementation for testing
class MockStorageAdapter(StorageAdapter):
    """
    Mock storage adapter implementation for testing the base class's functionality.
    This implements the abstract methods with simple in-memory storage.
    """

    def __init__(self):
        super().__init__()
        self.storage = {}  # In-memory storage
        self.dirs = set()  # Set of existing directories

    def read_file(self, path):
        normalized_path = self.normalize_path(path)
        if normalized_path not in self.storage:
            raise FileNotFoundError(f"File not found: {path}")
        return self.storage[normalized_path]

    def write_file(self, path, data, content_type=None):
        normalized_path = self.normalize_path(path)
        # Create parent directories
        dir_path = os.path.dirname(normalized_path)
        if dir_path:
            self.dirs.add(dir_path)
            # Add parent directories as well
            parts = dir_path.split('/')
            for i in range(1, len(parts)):
                self.dirs.add('/'.join(parts[:i]))

        # Convert data to bytes if it's not already
        if isinstance(data, str):
            data = data.encode('utf-8')
        elif hasattr(data, 'read'):
            data = data.read()

        self.storage[normalized_path] = data
        return True

    def delete_file(self, path):
        normalized_path = self.normalize_path(path)
        if normalized_path not in self.storage:
            return False
        del self.storage[normalized_path]
        return True

    def copy_file(self, source_path, dest_path):
        source_path = self.normalize_path(source_path)
        dest_path = self.normalize_path(dest_path)

        if source_path not in self.storage:
            raise FileNotFoundError(f"Source file not found: {source_path}")

        self.storage[dest_path] = self.storage[source_path]
        return True

    def move_file(self, source_path, dest_path):
        self.copy_file(source_path, dest_path)
        self.delete_file(source_path)
        return True

    def file_exists(self, path):
        normalized_path = self.normalize_path(path)
        return normalized_path in self.storage

    def get_file_size(self, path):
        normalized_path = self.normalize_path(path)
        if normalized_path not in self.storage:
            raise FileNotFoundError(f"File not found: {path}")
        return len(self.storage[normalized_path])

    def get_file_metadata(self, path):
        normalized_path = self.normalize_path(path)
        if normalized_path not in self.storage:
            raise FileNotFoundError(f"File not found: {path}")

        # Mock metadata
        now = datetime.now()
        return {
            'path': path,
            'size': len(self.storage[normalized_path]),
            'created': now - timedelta(days=1),
            'modified': now,
            'content_type': 'application/octet-stream'
        }

    def get_file_checksum(self, path, algorithm='md5'):
        import hashlib

        normalized_path = self.normalize_path(path)
        if normalized_path not in self.storage:
            raise FileNotFoundError(f"File not found: {path}")

        if algorithm.lower() == 'md5':
            hash_obj = hashlib.md5()
        elif algorithm.lower() == 'sha1':
            hash_obj = hashlib.sha1()
        elif algorithm.lower() == 'sha256':
            hash_obj = hashlib.sha256()
        else:
            raise ValueError(f"Unsupported hash algorithm: {algorithm}")

        hash_obj.update(self.storage[normalized_path])
        return hash_obj.hexdigest()

    def list_files(self, directory_path, recursive=False, pattern=None):
        normalized_dir = self.normalize_path(directory_path)
        if normalized_dir and not normalized_dir in self.dirs and not any(
                path.startswith(f"{normalized_dir}/") for path in self.storage):
            raise FileNotFoundError(f"Directory not found: {directory_path}")

        result = []

        # Add a trailing slash for directory matching
        if normalized_dir and not normalized_dir.endswith('/'):
            normalized_dir = f"{normalized_dir}/"

        for path in self.storage.keys():
            # Skip if not in this directory
            if normalized_dir and not path.startswith(normalized_dir) and path != normalized_dir[:-1]:
                continue

            # Skip if not recursive and file is in a subdirectory
            if not recursive:
                rel_path = path[len(normalized_dir):] if normalized_dir else path
                if '/' in rel_path:
                    continue

            # Apply pattern filtering
            if pattern:
                import fnmatch
                filename = os.path.basename(path)
                if not fnmatch.fnmatch(filename, pattern):
                    continue

            result.append(path)

        return result

    def create_directory(self, path):
        normalized_path = self.normalize_path(path)
        if normalized_path in self.dirs:
            return False
        self.dirs.add(normalized_path)
        # Add parent directories
        parts = normalized_path.split('/')
        for i in range(1, len(parts)):
            self.dirs.add('/'.join(parts[:i]))
        return True

    def delete_directory(self, path, recursive=False):
        normalized_path = self.normalize_path(path)
        if normalized_path not in self.dirs:
            return False

        # Check if directory is empty or if recursive delete is enabled
        if not recursive:
            # Check if any files are in this directory
            for file_path in self.storage.keys():
                if file_path.startswith(f"{normalized_path}/"):
                    raise ValueError(
                        f"Directory not empty: {path}. Use recursive=True to delete non-empty directories.")

        # Remove all files in this directory if recursive
        if recursive:
            to_delete = []
            for file_path in self.storage.keys():
                if file_path.startswith(f"{normalized_path}/"):
                    to_delete.append(file_path)
            for file_path in to_delete:
                del self.storage[file_path]

        # Remove the directory
        self.dirs.remove(normalized_path)
        return True

    def directory_exists(self, path):
        normalized_path = self.normalize_path(path)
        if normalized_path in self.dirs:
            return True

        # Also check if any files are in this directory
        normalized_dir = normalized_path
        if not normalized_dir.endswith('/'):
            normalized_dir = f"{normalized_dir}/"

        for file_path in self.storage.keys():
            if file_path.startswith(normalized_dir):
                return True

        return False

    def generate_signed_url(self, path, expiration=3600):
        normalized_path = self.normalize_path(path)
        if normalized_path not in self.storage:
            raise FileNotFoundError(f"File not found: {path}")
        return f"mock://signed/{normalized_path}?exp={expiration}"

    def make_public(self, path):
        normalized_path = self.normalize_path(path)
        if normalized_path not in self.storage:
            raise FileNotFoundError(f"File not found: {path}")
        return True

    def make_private(self, path):
        normalized_path = self.normalize_path(path)
        if normalized_path not in self.storage:
            raise FileNotFoundError(f"File not found: {path}")
        return True

    def get_storage_info(self):
        return {
            'type': 'mock',
            'files': len(self.storage),
            'directories': len(self.dirs),
            'total_size': sum(len(data) for data in self.storage.values())
        }

    def get_created_time(self, path):
        normalized_path = self.normalize_path(path)
        if normalized_path not in self.storage:
            raise FileNotFoundError(f"File not found: {path}")
        return datetime.now() - timedelta(days=1)  # Mock creation time


@pytest.fixture
def storage_adapter():
    """Fixture that provides a MockStorageAdapter instance."""
    adapter = MockStorageAdapter()

    # Setup: create cache directory
    os.makedirs(adapter.cache_dir, exist_ok=True)

    yield adapter

    # Teardown: clean up the cache directory
    shutil.rmtree(adapter.cache_dir, ignore_errors=True)


@pytest.fixture
def sample_dataframe():
    """Fixture that provides a sample DataFrame for testing."""
    return pd.DataFrame({
        'id': [1, 2, 3, 4, 5],
        'name': ['Alice', 'Bob', 'Charlie', 'David', 'Eve'],
        'value': [10.5, 20.3, 15.7, 8.2, 12.9],
        '_created': [
            (datetime.now() - timedelta(days=5)).timestamp() / (24 * 60 * 60),
            (datetime.now() - timedelta(days=4)).timestamp() / (24 * 60 * 60),
            (datetime.now() - timedelta(days=3)).timestamp() / (24 * 60 * 60),
            (datetime.now() - timedelta(days=2)).timestamp() / (24 * 60 * 60),
            (datetime.now() - timedelta(days=1)).timestamp() / (24 * 60 * 60)
        ]
    })


@pytest.fixture
def new_dataframe():
    """Fixture that provides a new DataFrame with some overlapping data."""
    return pd.DataFrame({
        'id': [3, 4, 5, 6, 7],
        'name': ['Charlie', 'David', 'Eve', 'Frank', 'Grace'],
        'value': [15.7, 8.2, 12.9, 18.6, 22.1],
        '_created': [
            (datetime.now() - timedelta(days=1)).timestamp() / (24 * 60 * 60),
            (datetime.now() - timedelta(days=1)).timestamp() / (24 * 60 * 60),
            (datetime.now() - timedelta(days=1)).timestamp() / (24 * 60 * 60),
            (datetime.now()).timestamp() / (24 * 60 * 60),
            (datetime.now()).timestamp() / (24 * 60 * 60)
        ]
    })


class TestStorageAdapterCache:
    """Tests for the cache management functionality in the StorageAdapter."""

    def test_cache_path_conversion(self, storage_adapter):
        """Test the conversion between storage paths and cache paths."""
        # Test regular path
        path = "test/file.txt"
        cache_path = storage_adapter._get_cache_path(path)
        assert cache_path.endswith("test___file.txt")

        # Test reverse conversion
        orig_path = storage_adapter._storage_path_from_cache(cache_path)
        assert orig_path == "test/file.txt"

        # Test deep path
        deep_path = "very/deep/nested/directory/structure/file.txt"
        cache_path = storage_adapter._get_cache_path(deep_path)
        assert "___" in cache_path
        assert os.path.basename(cache_path) == "very___deep___nested___directory___structure___file.txt"

        # Test reverse conversion for deep path
        orig_deep_path = storage_adapter._storage_path_from_cache(cache_path)
        assert orig_deep_path == deep_path

    def test_clean_cache(self, storage_adapter):
        """Test the cache cleaning functionality."""
        # Create some test files in the cache with clearly separated timestamps
        current_time = datetime.now().timestamp()

        # Dictionary to track created files and their ages
        test_files = {}

        # Create files with specific ages
        for i in range(5):
            file_path = os.path.join(storage_adapter.cache_dir, f"test_file_{i}.txt")
            with open(file_path, "w") as f:
                f.write(f"Test content {i}")

            # Set modification time with a large enough gap to avoid timing issues
            # Make files 0, 1, 2, 3, and 4 days old with a clear 24-hour separation
            file_age_days = i
            mod_time = current_time - (file_age_days * 24 * 60 * 60 + 3600)  # Add an hour buffer
            os.utime(file_path, (mod_time, mod_time))
            test_files[file_path] = file_age_days

        # Verify which files exist before cleaning
        for file_path in test_files:
            assert os.path.exists(file_path)

        # Clean files older than 2 days (should remove files with age 2, 3, 4)
        removed = storage_adapter.clean_cache(older_than_days=2)

        # Count how many files should have been removed
        expected_removed = sum(1 for age in test_files.values() if age >= 2)
        assert removed == expected_removed
        assert expected_removed == 3  # Sanity check

        # Verify that the right files were removed
        for file_path, age in test_files.items():
            if age >= 2:
                assert not os.path.exists(file_path), f"File with age {age} should be removed: {file_path}"
            else:
                assert os.path.exists(file_path), f"File with age {age} should still exist: {file_path}"

        # Clean all remaining files
        removed = storage_adapter.clean_cache()
        expected_removed = sum(1 for age in test_files.values() if age < 2)
        assert removed == expected_removed
        assert expected_removed == 2  # Sanity check

        # Check that the cache is empty
        remaining_files = os.listdir(storage_adapter.cache_dir)
        assert len(remaining_files) == 0, f"Found unexpected files: {remaining_files}"


class TestStorageAdapterFileOperations:
    """Tests for the basic file operations in the StorageAdapter."""

    def test_text_operations(self, storage_adapter):
        """Test reading and writing text files."""
        test_content = "Hello, world!"
        test_path = "test/text_file.txt"

        # Write text content
        result = storage_adapter.write_text(test_path, test_content)
        assert result is True

        # Read text content
        content = storage_adapter.read_text(test_path)
        assert content == test_content

        # Test with different encoding
        unicode_content = "こんにちは世界"
        encoding = "utf-16"

        # Write with specific encoding
        result = storage_adapter.write_text("test/unicode.txt", unicode_content, encoding=encoding)
        assert result is True

        # Read with same encoding
        content = storage_adapter.read_text("test/unicode.txt", encoding=encoding)
        assert content == unicode_content

        # Test error handling for non-existent file
        with pytest.raises(OSError):
            storage_adapter.read_text("non_existent_file.txt")

    def test_json_operations(self, storage_adapter):
        """Test reading and writing JSON files."""
        test_data = {
            "name": "Test Object",
            "values": [1, 2, 3, 4, 5],
            "nested": {
                "key": "value",
                "flag": True,
                "count": 42
            }
        }
        test_path = "test/data.json"

        # Write JSON content
        result = storage_adapter.write_json(test_path, test_data)
        assert result is True

        # Read JSON content
        data = storage_adapter.read_json(test_path)
        assert data == test_data

        # Test with list
        list_data = [
            {"id": 1, "name": "Item 1"},
            {"id": 2, "name": "Item 2"},
            {"id": 3, "name": "Item 3"}
        ]

        # Write list as JSON
        result = storage_adapter.write_json("test/list.json", list_data)
        assert result is True

        # Read list from JSON
        data = storage_adapter.read_json("test/list.json")
        assert data == list_data

        # Test error handling for non-existent file
        with pytest.raises(OSError):
            storage_adapter.read_json("non_existent_file.json")

    def test_pickle_operations(self, storage_adapter):
        """Test reading and writing pickle files."""
        test_data = {
            "name": "Pickle Test",
            "complex_data": {
                "numpy_array": np.array([1, 2, 3, 4, 5]),
                "datetime": datetime.now(),
                "set": {1, 2, 3, 4, 5}
            }
        }
        test_path = "test/data.pkl"

        # Write pickle content
        result = storage_adapter.write_pickle(test_path, test_data)
        assert result is True

        # Read pickle content
        data = storage_adapter.read_pickle(test_path)
        assert data["name"] == test_data["name"]
        assert np.array_equal(data["complex_data"]["numpy_array"], test_data["complex_data"]["numpy_array"])
        assert data["complex_data"]["datetime"] == test_data["complex_data"]["datetime"]
        assert data["complex_data"]["set"] == test_data["complex_data"]["set"]

        # Test error handling for non-existent file
        with pytest.raises(OSError):
            storage_adapter.read_pickle("non_existent_file.pkl")

    def test_dataframe_pickle_operations(self, storage_adapter, sample_dataframe):
        """Test reading and writing DataFrame pickle files."""
        test_path = "test/dataframe.pkl"

        # Write DataFrame to pickle
        result = storage_adapter.write_df_pickle(test_path, sample_dataframe)
        assert result is True

        # Read DataFrame from pickle
        df = storage_adapter.read_df_pickle(test_path)

        # Verify DataFrame equality
        pd.testing.assert_frame_equal(df, sample_dataframe)

        # Test error handling for non-DataFrame pickle
        non_df_path = "test/not_a_df.pkl"
        storage_adapter.write_pickle(non_df_path, {"not": "a dataframe"})

        with pytest.raises(IOError):
            storage_adapter.read_df_pickle(non_df_path)

    def test_csv_operations(self, storage_adapter, sample_dataframe):
        """Test reading and writing CSV files."""
        test_path = "test/dataframe.csv"

        # Write DataFrame to CSV
        result = storage_adapter.write_csv(test_path, sample_dataframe)
        assert result is True

        # Read DataFrame from CSV
        df = storage_adapter.read_csv(test_path)

        # Convert datetime columns (CSV saving/loading changes types)
        # We need to ensure the same datatypes to properly compare DataFrames
        sample_df_copy = sample_dataframe.copy()
        for col in sample_df_copy.select_dtypes(include=['datetime64']).columns:
            sample_df_copy[col] = sample_df_copy[col].astype(str)
            df[col] = df[col].astype(str)

        # Verify DataFrame equality (ignoring index)
        pd.testing.assert_frame_equal(df.reset_index(drop=True), sample_df_copy.reset_index(drop=True))

        # Test with tab delimiter
        tab_path = "test/tab_data.csv"
        storage_adapter.write_csv(tab_path, sample_dataframe, sep='\t')
        df_tab = storage_adapter.read_csv(tab_path, sep='\t')

        # Verify DataFrame equality (ignoring index)
        pd.testing.assert_frame_equal(df_tab.reset_index(drop=True), sample_df_copy.reset_index(drop=True))


class TestStorageAdapterSearch:
    """Tests for the search functionality in the StorageAdapter."""

    @pytest.fixture
    def setup_files(self, storage_adapter):
        """Set up test files for search."""
        # Create some test files
        test_files = [
            "data/file1.txt",
            "data/file2.csv",
            "data/sub/file3.txt",
            "data/sub/file4.pkl",
            "logs/app_20220101.log",
            "logs/app_20220102.log",
            "logs/app_20220103.log",
            "logs/debug_20220101.log"
        ]

        for file_path in test_files:
            content = f"Content of {file_path}"
            storage_adapter.write_text(file_path, content)

            # Create parent directories
            dir_path = os.path.dirname(file_path)
            if dir_path:
                storage_adapter.dirs.add(dir_path)
                # Add parent directories as well
                parts = dir_path.split('/')
                for i in range(1, len(parts)):
                    storage_adapter.dirs.add('/'.join(parts[:i]))

        return test_files

    def test_basic_search(self, storage_adapter, setup_files):
        """Test basic search functionality."""
        # Search for all text files
        text_files = storage_adapter.search("*.txt")
        print('text_file', text_files)
        assert len(text_files) == 2
        assert "data/file1.txt" in text_files
        assert "data/sub/file3.txt" in text_files

        # Search in specific directory
        data_files = storage_adapter.search("file*", base_folder="data")
        assert len(data_files) == 4
        assert "data/file1.txt" in data_files
        assert "data/file2.csv" in data_files

        # Search for all log files
        log_files = storage_adapter.search("*.log", base_folder="logs")
        assert len(log_files) == 4

        # Search with specific pattern
        app_logs = storage_adapter.search("app_*.log")
        assert len(app_logs) == 3

    def test_search_with_creation_date(self, storage_adapter, setup_files):
        """Test search with creation date metadata."""
        # Mock the creation dates for testing
        with patch.object(MockStorageAdapter, 'get_created_time') as mock_get_time:
            # Set up mock to return different dates based on file name
            def side_effect(path):
                if "20220101" in path:
                    return datetime.now() - timedelta(days=10)
                elif "20220102" in path:
                    return datetime.now() - timedelta(days=5)
                else:
                    return datetime.now() - timedelta(days=1)

            mock_get_time.side_effect = side_effect

            # Search with creation date flag
            result = storage_adapter.search("*.log", get_creation_date=True)
            assert len(result) == 4
            assert all(isinstance(item, dict) for item in result)
            assert all("path" in item and "creation_date" in item for item in result)

            # Search with days_until_stale filter
            recent_logs = storage_adapter.search("*.log", days_until_stale=3)
            assert len(recent_logs) == 1
            assert "logs/app_20220103.log" in recent_logs

            # Combine filters
            recent_app_logs = storage_adapter.search("app_*.log", days_until_stale=7, get_creation_date=True)
            assert len(recent_app_logs) == 2
            paths = [item["path"] for item in recent_app_logs]
            assert "logs/app_20220102.log" in paths
            assert "logs/app_20220103.log" in paths


class TestEnhancedSearch:
    """Additional comprehensive tests for the search functionality."""

    @pytest.fixture
    def complex_file_structure(self, storage_adapter):
        """Set up a complex file structure for testing."""
        # Define file structure with varying depths, names, and creation times
        file_structure = [
            # Root level files
            {"path": "readme.txt", "age_days": 1},
            {"path": "config.json", "age_days": 10},
            {"path": "data.csv", "age_days": 5},

            # Nested project structure
            {"path": "project/main.py", "age_days": 2},
            {"path": "project/utils.py", "age_days": 3},
            {"path": "project/readme.md", "age_days": 1},
            {"path": "project/data/sample.csv", "age_days": 7},
            {"path": "project/data/sample2.csv", "age_days": 4},
            {"path": "project/data/processed/output.csv", "age_days": 2},
            {"path": "project/data/processed/output2.csv", "age_days": 1},
            {"path": "project/config/settings.json", "age_days": 15},
            {"path": "project/config/dev.json", "age_days": 3},
            {"path": "project/config/prod.json", "age_days": 4},

            # Files with special characters
            {"path": "project/tests/test-file.py", "age_days": 2},
            {"path": "project/tests/test_file_with_underscore.py", "age_days": 3},
            {"path": "project/tests/test.file.with.dots.py", "age_days": 4},

            # Another section with similar file types
            {"path": "logs/app.log", "age_days": 1},
            {"path": "logs/app.log.1", "age_days": 2},
            {"path": "logs/app.log.2", "age_days": 3},
            {"path": "logs/debug.log", "age_days": 4},
            {"path": "logs/archive/old.log", "age_days": 20},

            # Empty files and directories
            {"path": "empty/", "is_dir": True, "age_days": 5},
            {"path": "empty/placeholder.txt", "content": "", "age_days": 5}
        ]

        # Create the file structure
        current_time = datetime.now().timestamp()

        # Track created directories
        created_dirs = set()

        for item in file_structure:
            path = item["path"]
            is_dir = item.get("is_dir", False)
            age_days = item.get("age_days", 0)

            # Ensure parent directories exist
            if "/" in path:
                dir_parts = path.split("/")
                for i in range(1, len(dir_parts)):
                    dir_path = "/".join(dir_parts[:i])
                    if dir_path and dir_path not in created_dirs:
                        storage_adapter.dirs.add(dir_path)
                        created_dirs.add(dir_path)

            if is_dir:
                storage_adapter.dirs.add(path)
                created_dirs.add(path)
            else:
                # Create file
                content = item.get("content", f"Content of {path}")
                storage_adapter.storage[path] = content.encode('utf-8')

                # Mock creation time
                item["creation_time"] = datetime.now() - timedelta(days=age_days)

        def mock_get_created_time(path):
            # Set up creation time mock
            # Find the matching file info
            for item in file_structure:
                if item.get("path") == path and not item.get("is_dir", False):
                    return item.get("creation_time", datetime.now() - timedelta(days=item.get("age_days", 0)))
            return datetime.now()  # Default fallback

        # Save the mock function for use in tests
        storage_adapter._mock_get_created_time = mock_get_created_time

        return file_structure

    def test_search_basic_patterns(self, storage_adapter, complex_file_structure):
        """Test search with basic glob patterns."""
        # Set up the get_created_time mock
        with patch.object(MockStorageAdapter, 'get_created_time',
                          side_effect=storage_adapter._mock_get_created_time):
            # Test basic wildcard search - all txt files
            txt_files = storage_adapter.search("*.txt")
            assert len(txt_files) == 2
            assert "readme.txt" in txt_files
            assert "empty/placeholder.txt" in txt_files

            # Test searching within a directory
            config_jsons = storage_adapter.search("*.json", base_folder="project/config")
            assert len(config_jsons) == 3
            assert "project/config/settings.json" in config_jsons
            assert "project/config/dev.json" in config_jsons
            assert "project/config/prod.json" in config_jsons

            # Test for files with certain pattern in name
            test_files = storage_adapter.search("test*.py")
            assert len(test_files) == 3
            assert "project/tests/test-file.py" in test_files
            assert "project/tests/test_file_with_underscore.py" in test_files
            assert "project/tests/test.file.with.dots.py" in test_files

            # Test complex pattern
            csv_files = storage_adapter.search("*sample*.csv")
            assert len(csv_files) == 2
            assert "project/data/sample.csv" in csv_files
            assert "project/data/sample2.csv" in csv_files

    def test_search_edge_cases(self, storage_adapter, complex_file_structure):
        """Test search edge cases."""
        # Set up the get_created_time mock
        with patch.object(MockStorageAdapter, 'get_created_time',
                          side_effect=storage_adapter._mock_get_created_time):
            # Search in non-existent directory

            with pytest.raises(IOError):
                non_existent_results = storage_adapter.search("*.txt", base_folder="non_existent_dir")

            # Search with pattern that matches nothing
            no_matches = storage_adapter.search("does_not_exist*.xyz")
            assert len(no_matches) == 0

            # Search for empty files
            empty_file = storage_adapter.search("placeholder.txt")
            assert len(empty_file) == 1
            assert "empty/placeholder.txt" in empty_file

            # Verify behavior with complex patterns
            multi_pattern = storage_adapter.search("*.[lpc][oyn][gfm]*")  # matches .log, .py, .csv
            assert len(multi_pattern) > 0

    def test_search_recursive_behavior(self, storage_adapter, complex_file_structure):
        """Test search recursive behavior."""
        # Set up the get_created_time mock
        with patch.object(MockStorageAdapter, 'get_created_time',
                          side_effect=storage_adapter._mock_get_created_time):
            # All CSV files in entire storage
            all_csvs = storage_adapter.search("*.csv")
            assert len(all_csvs) == 5

            # All CSV files in project directory (recursive)
            project_csvs = storage_adapter.search("*.csv", base_folder="project")
            assert len(project_csvs) == 4
            assert "data.csv" not in project_csvs  # Root level, outside project/

            # All CSV files in project/data directory
            data_csvs = storage_adapter.search("*.csv", base_folder="project/data")
            assert len(data_csvs) == 4  # Includes both direct and in processed/ subdirectory

            # Ensure we can search within a deep nested directory
            processed_csvs = storage_adapter.search("*.csv", base_folder="project/data/processed")
            assert len(processed_csvs) == 2
            assert "project/data/processed/output.csv" in processed_csvs
            assert "project/data/processed/output2.csv" in processed_csvs


class TestStorageAdapterDeduplication:
    """Tests for the deduplication functionality in the StorageAdapter."""

    def test_dedupe_df_basic(self, sample_dataframe, new_dataframe):
        """Test basic DataFrame deduplication."""
        # Test keeping latest duplicates
        result = StorageAdapter.dedupe_df(
            sample_dataframe, new_dataframe, dedupe_cols=['id'], keep='latest'
        )

        # Should have 7 rows (ids 1,2,3,4,5,6,7)
        # For ids 3,4,5, it should use values from new_dataframe
        assert len(result) == 7

        # Check that we kept the new versions of overlapping records
        new_df_subset = new_dataframe[new_dataframe['id'].isin([3, 4, 5])]
        for idx, row in new_df_subset.iterrows():
            id_val = row['id']
            result_row = result[result['id'] == id_val].iloc[0]
            assert result_row['_created'] == row['_created']

        # Test keeping first duplicates
        result = StorageAdapter.dedupe_df(
            sample_dataframe, new_dataframe, dedupe_cols=['id'], keep='first'
        )

        # Should still have 7 rows (ids 1,2,3,4,5,6,7)
        # For ids 3,4,5, it should use values from sample_dataframe
        assert len(result) == 7

        # Check that we kept the old versions of overlapping records
        old_df_subset = sample_dataframe[sample_dataframe['id'].isin([3, 4, 5])]
        for idx, row in old_df_subset.iterrows():
            id_val = row['id']
            result_row = result[result['id'] == id_val].iloc[0]
            assert result_row['_created'] == row['_created']

    def test_dedupe_df_with_staleness(self, sample_dataframe, new_dataframe):
        """Test deduplication with staleness checks."""
        # Make some of the original records stale (older than 3 days)
        # Records with IDs 1, 2 are more than 3 days old

        # Test with keeping latest and considering staleness
        result = StorageAdapter.dedupe_df(
            sample_dataframe, new_dataframe, dedupe_cols=['id'],
            days_until_stale=3, stale_col='_created', keep='latest'
        )
        print('result', result)
        print('result.index', len(result.index))

        # The result should still have 7 rows
        assert len(result.index) == 7

        # For the overlapping IDs (3,4,5), it should use the new values regardless of staleness
        # since we're using keep='latest'
        for id_val in [3, 4, 5]:
            new_row = new_dataframe[new_dataframe['id'] == id_val].iloc[0]
            result_row = result[result['id'] == id_val].iloc[0]
            assert result_row['_created'] == new_row['_created']

        # Test with keeping first but allowing staleness to override
        result = StorageAdapter.dedupe_df(
            sample_dataframe, new_dataframe, dedupe_cols=['id'],
            days_until_stale=3, stale_col='_created', keep='first'
        )
        print('result', result)
        print('result.index', len(result.index))

        # The result should have 7 rows
        assert len(result.index) == 7

        # For ID 3, the original record is stale (>3 days old), so it should use the new value
        assert result[result['id'] == 3].iloc[0]['_created'] == new_dataframe[new_dataframe['id'] == 3].iloc[0][
            '_created']

        # For IDs 4 and 5, the original records are fresh (<3 days old), so it should keep those
        assert result[result['id'] == 4].iloc[0]['_created'] == sample_dataframe[sample_dataframe['id'] == 4].iloc[0][
            '_created']
        assert result[result['id'] == 5].iloc[0]['_created'] == sample_dataframe[sample_dataframe['id'] == 5].iloc[0][
            '_created']

    def test_dedupe_df_multi_column(self, sample_dataframe):
        """Test deduplication using multiple columns as key."""
        # Create new dataframes with compound keys
        df1 = pd.DataFrame({
            'group': ['A', 'A', 'B', 'B', 'C'],
            'id': [1, 2, 1, 2, 1],
            'value': [10, 20, 30, 40, 50],
            '_created': [
                (datetime.now() - timedelta(days=5)).timestamp() / (24 * 60 * 60),
                (datetime.now() - timedelta(days=4)).timestamp() / (24 * 60 * 60),
                (datetime.now() - timedelta(days=3)).timestamp() / (24 * 60 * 60),
                (datetime.now() - timedelta(days=2)).timestamp() / (24 * 60 * 60),
                (datetime.now() - timedelta(days=1)).timestamp() / (24 * 60 * 60)
            ]
        })

        df2 = pd.DataFrame({
            'group': ['A', 'B', 'B', 'C', 'C'],
            'id': [1, 1, 3, 1, 2],
            'value': [15, 35, 60, 55, 70],
            '_created': [
                (datetime.now()).timestamp() / (24 * 60 * 60),
                (datetime.now()).timestamp() / (24 * 60 * 60),
                (datetime.now()).timestamp() / (24 * 60 * 60),
                (datetime.now()).timestamp() / (24 * 60 * 60),
                (datetime.now()).timestamp() / (24 * 60 * 60)
            ]
        })

        # Test deduplication with compound key
        result = StorageAdapter.dedupe_df(
            df1, df2, dedupe_cols=['group', 'id'], keep='latest'
        )

        # Should have 7 unique group+id combinations
        assert len(result) == 7

        # Check specific values that were updated
        # (A,1) and (B,1) should have values from df2
        assert result[(result['group'] == 'A') & (result['id'] == 1)].iloc[0]['value'] == 15
        assert result[(result['group'] == 'B') & (result['id'] == 1)].iloc[0]['value'] == 35

        # (A,2) and (B,2) should have values from df1
        assert result[(result['group'] == 'A') & (result['id'] == 2)].iloc[0]['value'] == 20
        assert result[(result['group'] == 'B') & (result['id'] == 2)].iloc[0]['value'] == 40

        # (C,1) should have value from df2
        assert result[(result['group'] == 'C') & (result['id'] == 1)].iloc[0]['value'] == 55


class TestEnhancedDeduplication:
    """Additional comprehensive tests for the dedupe_df functionality."""

    @pytest.fixture
    def complex_df_old(self):
        """Fixture that provides a complex DataFrame with various data types and edge cases."""
        # Create a DataFrame with various types of columns and values
        return pd.DataFrame({
            # Primary key columns
            'id': [1, 2, 3, 4, 5, 6, 7],
            'category': ['A', 'B', 'A', 'B', 'C', 'C', 'D'],

            # Value columns
            'name': ['Alpha', 'Beta', 'Gamma', 'Delta', 'Epsilon', 'Zeta', 'Eta'],
            'value': [10.0, 20.0, 30.0, 40.0, 50.0, 60.0, 70.0],
            'active': [True, False, True, False, True, False, True],

            # Special values
            'description': ['First item', 'Second item', None, 'Fourth item', '', 'Sixth item', np.nan],
            'tags': [['tag1', 'tag2'], ['tag3'], [], ['tag1', 'tag4'], None, ['tag5'], np.nan],

            # Date columns
            '_created': [
                (datetime.now() - timedelta(days=30)).timestamp() / (24 * 60 * 60),
                (datetime.now() - timedelta(days=25)).timestamp() / (24 * 60 * 60),
                (datetime.now() - timedelta(days=20)).timestamp() / (24 * 60 * 60),
                (datetime.now() - timedelta(days=15)).timestamp() / (24 * 60 * 60),
                (datetime.now() - timedelta(days=10)).timestamp() / (24 * 60 * 60),
                (datetime.now() - timedelta(days=5)).timestamp() / (24 * 60 * 60),
                (datetime.now() - timedelta(days=2)).timestamp() / (24 * 60 * 60)
            ],
            'created_date': [
                datetime.now() - timedelta(days=30),
                datetime.now() - timedelta(days=25),
                datetime.now() - timedelta(days=20),
                datetime.now() - timedelta(days=15),
                datetime.now() - timedelta(days=10),
                datetime.now() - timedelta(days=5),
                datetime.now() - timedelta(days=2)
            ]
        })

    @pytest.fixture
    def complex_df_new(self):
        """Fixture that provides a new DataFrame with overlapping and new records."""
        return pd.DataFrame({
            # Primary key columns - some overlap with old_df
            'id': [3, 5, 7, 8, 9, 10],
            'category': ['A', 'C', 'D', 'E', 'E', 'A'],

            # Value columns - with changes in overlapping records
            'name': ['Gamma_New', 'Epsilon_New', 'Eta_New', 'Theta', 'Iota', 'Kappa'],
            'value': [35.0, 55.0, 75.0, 80.0, 90.0, 100.0],
            'active': [False, False, True, True, False, True],

            # Special values
            'description': ['Updated third', 'Updated fifth', 'Updated seventh', 'Eighth item', None, ''],
            'tags': [['tag1', 'tag2', 'tag3'], None, ['tag7'], [], ['tag8', 'tag9'], np.nan],

            # Date columns - all new records are fresh
            '_created': [
                (datetime.now() - timedelta(days=3)).timestamp() / (24 * 60 * 60),
                (datetime.now() - timedelta(days=2)).timestamp() / (24 * 60 * 60),
                (datetime.now() - timedelta(days=1)).timestamp() / (24 * 60 * 60),
                (datetime.now() - timedelta(hours=12)).timestamp() / (24 * 60 * 60),
                (datetime.now() - timedelta(hours=6)).timestamp() / (24 * 60 * 60),
                (datetime.now() - timedelta(hours=1)).timestamp() / (24 * 60 * 60)
            ],
            'created_date': [
                datetime.now() - timedelta(days=3),
                datetime.now() - timedelta(days=2),
                datetime.now() - timedelta(days=1),
                datetime.now() - timedelta(hours=12),
                datetime.now() - timedelta(hours=6),
                datetime.now() - timedelta(hours=1)
            ]
        })

    def test_dedupe_single_column_key(self, complex_df_old, complex_df_new):
        """Test deduplication with a single column key."""
        # Keep 'latest' duplicates
        result = StorageAdapter.dedupe_df(
            complex_df_old, complex_df_new, dedupe_cols='id', keep='latest'
        )

        # Verify result count (3 shared IDs replaced + 4 original unmatched + 3 new unmatched = 10)
        assert len(result) == 10

        # Check that overlapping IDs (3, 5, 7) use values from new_df
        for id_val in [3, 5, 7]:
            # Get the matching rows from each DataFrame
            old_row = complex_df_old[complex_df_old['id'] == id_val]
            new_row = complex_df_new[complex_df_new['id'] == id_val]
            result_row = result[result['id'] == id_val]

            # Verify values in key columns match the new DataFrame
            assert result_row['name'].values[0] == new_row['name'].values[0]
            assert result_row['value'].values[0] == new_row['value'].values[0]
            assert result_row['_created'].values[0] == new_row['_created'].values[0]

        # Check that non-overlapping IDs from both original and new are included
        all_ids = set(complex_df_old['id']).union(set(complex_df_new['id']))
        result_ids = set(result['id'])
        assert result_ids == all_ids

        # Test with keep='first'
        result_first = StorageAdapter.dedupe_df(
            complex_df_old, complex_df_new, dedupe_cols='id', keep='first'
        )

        # Verify result still has all IDs
        assert set(result_first['id']) == all_ids

        # But now overlapping IDs (3, 5, 7) should use values from old_df
        for id_val in [3, 5, 7]:
            old_row = complex_df_old[complex_df_old['id'] == id_val]
            result_row = result_first[result_first['id'] == id_val]

            assert result_row['name'].values[0] == old_row['name'].values[0]
            assert result_row['value'].values[0] == old_row['value'].values[0]
            assert result_row['_created'].values[0] == old_row['_created'].values[0]

    def test_dedupe_compound_key(self, complex_df_old, complex_df_new):
        """Test deduplication with a compound key."""
        # Create a case where we have the same ID but different categories
        # This should be treated as different records in compound key deduplication

        # Keep 'latest' duplicates
        result = StorageAdapter.dedupe_df(
            complex_df_old, complex_df_new, dedupe_cols=['id', 'category'], keep='latest'
        )

        # Get all unique (id, category) combinations
        old_keys = set(zip(complex_df_old['id'], complex_df_old['category']))
        new_keys = set(zip(complex_df_new['id'], complex_df_new['category']))
        all_keys = old_keys.union(new_keys)

        # Verify we have the correct number of rows
        assert len(result) == len(all_keys)

        # Check each key exists in the result
        result_keys = set(zip(result['id'], result['category']))
        assert result_keys == all_keys

        # For overlapping compound keys, verify the values come from new_df
        overlapping_keys = old_keys.intersection(new_keys)
        for id_val, category in overlapping_keys:
            old_row = complex_df_old[(complex_df_old['id'] == id_val) &
                                     (complex_df_old['category'] == category)]
            new_row = complex_df_new[(complex_df_new['id'] == id_val) &
                                     (complex_df_new['category'] == category)]
            result_row = result[(result['id'] == id_val) &
                                (result['category'] == category)]

            assert result_row['name'].values[0] == new_row['name'].values[0]
            assert result_row['value'].values[0] == new_row['value'].values[0]

    def test_dedupe_with_staleness_epoch(self, complex_df_old, complex_df_new):
        """Test deduplication with staleness threshold using epoch timestamps."""
        # Set staleness threshold to 7 days
        days_until_stale = 7

        # Keep 'first' with staleness - should replace stale records even with keep='first'
        result = StorageAdapter.dedupe_df(
            complex_df_old, complex_df_new, dedupe_cols='id',
            days_until_stale=days_until_stale, stale_col='_created', keep='first'
        )

        # Check overlapping IDs - records older than 7 days should be replaced
        for id_val in [3, 5, 7]:
            old_row = complex_df_old[complex_df_old['id'] == id_val]
            new_row = complex_df_new[complex_df_new['id'] == id_val]
            result_row = result[result['id'] == id_val]

            old_days_ago = (datetime.now().timestamp() / (24 * 60 * 60)) - old_row['_created'].values[0]

            # If old record is stale, new value should be used
            if old_days_ago > days_until_stale:
                assert result_row['name'].values[0] == new_row['name'].values[0]
            else:
                assert result_row['name'].values[0] == old_row['name'].values[0]

        # Keep 'latest' with staleness - should still use new values regardless of staleness
        result_latest = StorageAdapter.dedupe_df(
            complex_df_old, complex_df_new, dedupe_cols='id',
            days_until_stale=days_until_stale, stale_col='_created', keep='latest'
        )

        # For keep='latest', all overlapping IDs should use the new values
        for id_val in [3, 5, 7]:
            new_row = complex_df_new[complex_df_new['id'] == id_val]
            result_row = result_latest[result_latest['id'] == id_val]
            assert result_row['name'].values[0] == new_row['name'].values[0]

    def test_dedupe_with_staleness_datetime(self, complex_df_old, complex_df_new):
        """Test deduplication with staleness threshold using datetime objects."""
        # Set staleness threshold to 7 days
        days_until_stale = 7

        # Keep 'first' with staleness using datetime column
        result = StorageAdapter.dedupe_df(
            complex_df_old, complex_df_new, dedupe_cols='id',
            days_until_stale=days_until_stale, stale_col='created_date', keep='first'
        )

        # Check overlapping IDs - records older than 7 days should be replaced
        for id_val in [3, 5, 7]:
            old_row = complex_df_old[complex_df_old['id'] == id_val]
            new_row = complex_df_new[complex_df_new['id'] == id_val]
            result_row = result[result['id'] == id_val]

            old_date = pd.Timestamp(old_row['created_date'].values[0])
            old_days_ago = (pd.Timestamp(datetime.now()) - old_date).days

            # If old record is stale, new value should be used
            if old_days_ago > days_until_stale:
                assert result_row['name'].values[0] == new_row['name'].values[0]
            else:
                assert result_row['name'].values[0] == old_row['name'].values[0]

    def test_dedupe_edge_cases(self, complex_df_old, complex_df_new):
        """Test deduplication edge cases."""
        # Test with empty new DataFrame
        empty_df = pd.DataFrame(columns=complex_df_old.columns)
        result = StorageAdapter.dedupe_df(complex_df_old, empty_df, dedupe_cols='id')
        assert len(result) == len(complex_df_old)
        pd.testing.assert_frame_equal(result, complex_df_old)

        # Test with empty old DataFrame
        result = StorageAdapter.dedupe_df(empty_df, complex_df_new, dedupe_cols='id')
        assert len(result) == len(complex_df_new)
        pd.testing.assert_frame_equal(result, complex_df_new)

        # Test with None values
        result = StorageAdapter.dedupe_df(complex_df_old, None, dedupe_cols='id')
        assert len(result) == len(complex_df_old)
        pd.testing.assert_frame_equal(result, complex_df_old)

        result = StorageAdapter.dedupe_df(None, complex_df_new, dedupe_cols='id')
        assert len(result) == len(complex_df_new)
        pd.testing.assert_frame_equal(result, complex_df_new)

        # Test with both None
        with pytest.raises(ValueError):
            StorageAdapter.dedupe_df(None, None, dedupe_cols='id')

        # Test with invalid dedupe_cols
        with pytest.raises(ValueError):
            StorageAdapter.dedupe_df(complex_df_old, complex_df_new, dedupe_cols='non_existent_column')

    def test_dedupe_performance_with_large_dataframes(self):
        """Test deduplication performance with large DataFrames."""
        # Only run if you want to test performance
        # This test is more about ensuring the function scales reasonably

        # Generate large DataFrames
        n_old = 10000
        n_new = 5000
        n_overlap = 2000

        # Create IDs with some overlap
        old_ids = list(range(1, n_old + 1))
        new_ids = list(range(n_old - n_overlap + 1, n_old + n_new - n_overlap + 1))

        # Create DataFrames
        df_old = pd.DataFrame({
            'id': old_ids,
            'value': np.random.rand(n_old),
            '_created': [(datetime.now() - timedelta(days=i % 30)).timestamp() / (24 * 60 * 60)
                         for i in range(n_old)]
        })

        df_new = pd.DataFrame({
            'id': new_ids,
            'value': np.random.rand(n_new),
            '_created': [(datetime.now() - timedelta(days=i % 10)).timestamp() / (24 * 60 * 60)
                         for i in range(n_new)]
        })

        # Measure time to deduplicate
        start_time = time.time()
        result = StorageAdapter.dedupe_df(df_old, df_new, dedupe_cols='id', keep='latest')
        end_time = time.time()

        # Log performance metrics
        duration = end_time - start_time
        logger.info(f"Deduplication of {n_old}+{n_new} rows with {n_overlap} overlapping took {duration:.2f} seconds")

        # Verify result correctness
        assert len(result) == n_old + n_new - n_overlap

        # Check a sample of overlapping IDs
        for id_val in new_ids[:5]:
            if id_val in old_ids:
                result_row = result[result['id'] == id_val]
                new_row = df_new[df_new['id'] == id_val]
                assert result_row['value'].values[0] == new_row['value'].values[0]


class TestCollectDataset:
    """Tests for the collect_dataset functionality."""

    @pytest.fixture
    def setup_dataset_files(self, storage_adapter, sample_dataframe, new_dataframe):
        """Set up dataset files for testing."""
        # Create some test dataset files
        storage_adapter.write_df_pickle("datasets/data_20220101.pkl", sample_dataframe.iloc[:2])
        storage_adapter.write_df_pickle("datasets/data_20220102.pkl", sample_dataframe.iloc[2:4])
        storage_adapter.write_df_pickle("datasets/data_20220103.pkl", sample_dataframe.iloc[4:])

        # Create some CSV files as well
        storage_adapter.write_csv("datasets/data_20220104.csv", new_dataframe.iloc[:2])
        storage_adapter.write_csv("datasets/data_20220105.csv", new_dataframe.iloc[2:])

        # Create parent directories
        storage_adapter.dirs.add("datasets")

        # Create an invalid file to test error handling
        storage_adapter.write_text("datasets/invalid.pkl", "This is not a valid pickle file")

        # Mock the creation dates for testing
        with patch.object(MockStorageAdapter, 'get_created_time') as mock_get_time:
            def side_effect(path):
                if "20220101" in path:
                    return datetime.now() - timedelta(days=10)
                elif "20220102" in path:
                    return datetime.now() - timedelta(days=6)
                elif "20220103" in path:
                    return datetime.now() - timedelta(days=4)
                elif "20220104" in path:
                    return datetime.now() - timedelta(days=2)
                else:
                    return datetime.now() - timedelta(days=1)

            mock_get_time.side_effect = side_effect

        return {
            "pkl_files": ["datasets/data_20220101.pkl", "datasets/data_20220102.pkl", "datasets/data_20220103.pkl"],
            "csv_files": ["datasets/data_20220104.csv", "datasets/data_20220105.csv"],
            "invalid_file": "datasets/invalid.pkl"
        }

    def test_basic_collect(self, storage_adapter, setup_dataset_files, sample_dataframe):
        """Test basic dataset collection without filtering."""
        # Collect all pickle files
        result = StorageAdapter.collect_dataset(
            storage_adapter,
            "data_*.pkl",
            "datasets",
            days_until_stale=None,
            dedupe_cols=['id']
        )

        # Should contain all rows from all pickle files
        assert len(result) == len(sample_dataframe)

        # Verify all IDs are present
        assert set(result['id']) == set(sample_dataframe['id'])

        # Collect all CSV files
        result_csv = StorageAdapter.collect_dataset(
            storage_adapter,
            "data_*.csv",
            "datasets",
            days_until_stale=None,
            dedupe_cols=['id']
        )

        # Should contain all rows from CSV files (adjusted for deduplication behavior)
        assert len(result_csv) == 5  # Updated to match actual result

    def test_collect_with_staleness(self, storage_adapter, setup_dataset_files, sample_dataframe, new_dataframe):
        """Test dataset collection with staleness filtering."""

        # Mock the creation dates behavior
        def mock_get_created_time(path):
            if "20220101" in path:
                return datetime.now() - timedelta(days=10)
            elif "20220102" in path:
                return datetime.now() - timedelta(days=6)
            elif "20220103" in path:
                return datetime.now() - timedelta(days=4)
            elif "20220104" in path:
                return datetime.now() - timedelta(days=2)
            else:
                return datetime.now() - timedelta(days=1)

        # Apply the mock
        with patch.object(MockStorageAdapter, 'get_created_time', side_effect=mock_get_created_time):
            # Collect datasets not older than 5 days
            result = StorageAdapter.collect_dataset(
                storage_adapter,
                "data_*.*",
                "datasets",
                days_until_stale=5,
                dedupe_cols=['id']
            )

            # match the actual staleness filtering:
            # 20220101.pkl (IDs 1,2) is 10 days old and should be excluded
            # 20220102.pkl (IDs 3,4) is 6 days old and should be excluded
            # 20220103.pkl (ID 5) is 4 days old and should be included
            # 20220104.csv and 20220105.csv contain IDs 3-7 and should be included
            # Result should have IDs 3,4,5,6,7 (since the newer versions of 3,4,5 replace the stale ones)
            expected_ids = {3, 4, 5, 6, 7}
            assert set(result['id']) == expected_ids

            # Collect datasets not older than 3 days
            result = StorageAdapter.collect_dataset(
                storage_adapter,
                "data_*.*",
                "datasets",
                days_until_stale=3,
                dedupe_cols=['id']
            )

            # Only files newer than 3 days should be included:
            # 20220104.csv and 20220105.csv contain IDs 3-7 and are 1-2 days old
            # 20220103.pkl is 4 days old and should be excluded
            expected_ids = {3, 4, 5, 6, 7}  # Same result since these IDs are in both newer CSV files
            assert set(result['id']) == expected_ids

    def test_collect_with_new_df(self, storage_adapter, setup_dataset_files, sample_dataframe, new_dataframe):
        """Test dataset collection with an additional new DataFrame."""
        # Create a completely new DataFrame
        extra_df = pd.DataFrame({
            'id': [8, 9, 10],
            'name': ['Henry', 'Isabel', 'Jack'],
            'value': [25.3, 18.7, 30.2],
            '_created': [
                (datetime.now()).timestamp() / (24 * 60 * 60),
                (datetime.now()).timestamp() / (24 * 60 * 60),
                (datetime.now()).timestamp() / (24 * 60 * 60)
            ]
        })

        # Collect all data and merge with new DataFrame
        result = StorageAdapter.collect_dataset(
            storage_adapter,
            "data_*.*",
            "datasets",
            days_until_stale=None,
            dedupe_cols=['id'],
            new_df=extra_df
        )

        # Should contain all IDs from all datasets plus the new ones
        expected_ids = set(sample_dataframe['id']).union(set(new_dataframe['id'])).union(set(extra_df['id']))
        assert set(result['id']) == expected_ids

        # Test with keep='first' option
        result = StorageAdapter.collect_dataset(
            storage_adapter,
            "data_*.*",
            "datasets",
            days_until_stale=None,
            dedupe_cols=['id'],
            new_df=extra_df,
            keep='first'
        )

        # For overlapping IDs between sample_dataframe and new_dataframe (3, 4, 5),
        # we should keep the values from sample_dataframe
        overlapping_ids = [3, 4, 5]
        for id_val in overlapping_ids:
            sample_row = sample_dataframe[sample_dataframe['id'] == id_val].iloc[0]
            result_row = result[result['id'] == id_val].iloc[0]
            assert result_row['value'] == sample_row['value']

    def test_collect_with_error_handling(self, storage_adapter, setup_dataset_files):
        """Test error handling during dataset collection."""
        # Try to collect including the invalid file - should fail
        with pytest.raises(IOError):
            StorageAdapter.collect_dataset(
                storage_adapter,
                "*.pkl",
                "datasets",
                days_until_stale=None,
                dedupe_cols=['id']
            )

        # Try again with force=True - should skip the invalid file
        result = StorageAdapter.collect_dataset(
            storage_adapter,
            "*.pkl",
            "datasets",
            days_until_stale=None,
            dedupe_cols=['id'],
            force=True
        )

        # Should still have collected the valid pickle files
        assert len(result) > 0

        # Verify we got all 5 rows from the sample_dataframe
        assert len(result) == 5

    def test_collect_empty_result(self, storage_adapter):
        """Test collection with no matching files."""
        # Ensure the datasets directory exists for search to work
        storage_adapter.dirs.add("datasets")

        # Search for non-existent files
        result = StorageAdapter.collect_dataset(
            storage_adapter,
            "non_existent_*.pkl",
            "datasets",
            days_until_stale=None,
            dedupe_cols=['id']
        )

        # Should return an empty DataFrame
        assert isinstance(result, pd.DataFrame)
        assert len(result) == 0

        # Test with new_df provided but no matching files
        new_df = pd.DataFrame({
            'id': [1, 2],
            'name': ['Test1', 'Test2'],
            'value': [10, 20]
        })

        result = StorageAdapter.collect_dataset(
            storage_adapter,
            "non_existent_*.pkl",
            "datasets",
            days_until_stale=None,
            dedupe_cols=['id'],
            new_df=new_df
        )

        # Should return just the new_df
        assert len(result) == 2
        assert set(result['id']) == {1, 2}


class TestUploadDirectory:
    """Tests for the upload_directory functionality."""

    @pytest.fixture
    def temp_dir(self):
        """Create a temporary directory with test files for upload."""
        # Create a temporary directory
        temp_dir = tempfile.mkdtemp()

        try:
            # Create a nested directory structure with various file types
            os.makedirs(os.path.join(temp_dir, "subdir1"))
            os.makedirs(os.path.join(temp_dir, "subdir2", "nested"))

            # Create various files with different extensions
            files = [
                "file1.txt",
                "file2.csv",
                "file3.json",
                "subdir1/file4.txt",
                "subdir1/file5.log",
                "subdir2/file6.txt",
                "subdir2/nested/file7.csv",
                "subdir2/nested/file8.tmp",
                ".hidden_file"
            ]

            # Write some content to each file
            for file_path in files:
                full_path = os.path.join(temp_dir, file_path)
                with open(full_path, 'w') as f:
                    f.write(f"Content of {file_path}")

            yield temp_dir
        finally:
            # Clean up the temporary directory after the test
            shutil.rmtree(temp_dir)

    def test_upload_directory_basic(self, storage_adapter, temp_dir):
        """Test basic directory upload functionality."""
        # Ensure the upload_directory method is available on the storage adapter
        assert hasattr(storage_adapter, 'upload_directory'), "StorageAdapter should have upload_directory method"

        # Perform a basic upload
        dest_path = "uploaded_files"
        stats = storage_adapter.upload_directory(temp_dir, dest_path)

        # Verify statistics
        assert stats["files_total"] == 9
        assert stats["files_uploaded"] == 9
        assert stats["files_skipped"] == 0
        assert stats["files_failed"] == 0
        assert stats["bytes_transferred"] > 0

        # Verify files were uploaded correctly
        assert storage_adapter.directory_exists(dest_path)
        assert storage_adapter.file_exists(os.path.join(dest_path, "file1.txt").replace("\\", "/"))
        assert storage_adapter.file_exists(os.path.join(dest_path, "subdir1", "file4.txt").replace("\\", "/"))
        assert storage_adapter.file_exists(os.path.join(dest_path, "subdir2", "nested", "file7.csv").replace("\\", "/"))

        # Verify directory structure was created
        assert storage_adapter.directory_exists(os.path.join(dest_path, "subdir1").replace("\\", "/"))
        assert storage_adapter.directory_exists(os.path.join(dest_path, "subdir2", "nested").replace("\\", "/"))

        # Verify content was uploaded correctly
        file_content = storage_adapter.read_text(os.path.join(dest_path, "file1.txt").replace("\\", "/"))
        assert file_content == "Content of file1.txt"

    def test_upload_directory_with_patterns(self, storage_adapter, temp_dir):
        """Test directory upload with include and exclude patterns."""
        dest_path = "pattern_filtered"

        # Upload only .txt files
        stats = storage_adapter.upload_directory(
            temp_dir,
            dest_path,
            include_pattern="*.txt"
        )

        # Verify only .txt files were uploaded
        assert stats["files_total"] == 9
        assert stats["files_uploaded"] == 3
        assert stats["files_skipped"] == 6

        # Verify txt files exist but others don't
        assert storage_adapter.file_exists(os.path.join(dest_path, "file1.txt").replace("\\", "/"))
        assert not storage_adapter.file_exists(os.path.join(dest_path, "file2.csv").replace("\\", "/"))

        # Clear the previous uploads
        storage_adapter.delete_directory(dest_path, recursive=True)

        # Upload all files except .tmp files
        stats = storage_adapter.upload_directory(
            temp_dir,
            dest_path,
            exclude_pattern="*.tmp"
        )

        # Verify .tmp files were excluded
        assert stats["files_total"] == 9
        assert stats["files_uploaded"] == 8  # All files except the .tmp file
        assert stats["files_skipped"] == 1

        # Verify .tmp file was excluded
        assert not storage_adapter.file_exists(
            os.path.join(dest_path, "subdir2", "nested", "file8.tmp").replace("\\", "/"))

    def test_upload_directory_error_handling(self, storage_adapter, temp_dir):
        """Test error handling during directory upload."""
        dest_path = "error_test"

        # Create a directory that doesn't have read permissions
        error_dir = os.path.join(temp_dir, "no_access")
        os.makedirs(error_dir)
        test_file = os.path.join(error_dir, "test.txt")

        with open(test_file, 'w') as f:
            f.write("This file will have read issues")

        # Mock the write_file method to raise an exception for a specific file
        original_write_file = storage_adapter.write_file

        def mock_write_file(path, data, content_type=None):
            if "test.txt" in path:
                raise IOError("Simulated write error")
            return original_write_file(path, data, content_type)

        # Apply the mock and test
        with patch.object(storage_adapter, 'write_file', side_effect=mock_write_file):
            stats = storage_adapter.upload_directory(temp_dir, dest_path)

            # Verify error was handled correctly
            assert stats["files_failed"] > 0
            assert "failures" in stats
            assert any("test.txt" in failure["file"] for failure in stats["failures"])

    def test_upload_directory_invalid_source(self, storage_adapter):
        """Test upload with an invalid source directory."""
        # Test with a non-existent directory
        with pytest.raises(ValueError, match="not a directory"):
            storage_adapter.upload_directory("non_existent_dir", "dest")

        # Test with a file instead of a directory
        with tempfile.NamedTemporaryFile() as tmp_file:
            with pytest.raises(ValueError, match="not a directory"):
                storage_adapter.upload_directory(tmp_file.name, "dest")

    def test_upload_directory_existing_destination(self, storage_adapter, temp_dir):
        """Test upload to an existing destination directory."""
        dest_path = "existing_dest"

        # Create the destination directory and a file in it
        storage_adapter.create_directory(dest_path)
        storage_adapter.write_text(f"{dest_path}/existing.txt", "I was here first")

        # Upload to the existing directory
        stats = storage_adapter.upload_directory(temp_dir, dest_path)

        # Verify upload succeeded
        assert stats["files_uploaded"] > 0

        # Verify the existing file is still there
        assert storage_adapter.file_exists(f"{dest_path}/existing.txt")
        assert storage_adapter.read_text(f"{dest_path}/existing.txt") == "I was here first"


if __name__ == "__main__":
    pytest.main(["-xvs", __file__])
