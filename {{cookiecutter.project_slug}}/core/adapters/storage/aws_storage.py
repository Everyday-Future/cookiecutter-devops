# core/adapters/storage/aws_storage.py
import os
import logging
import hashlib
import fnmatch
from typing import BinaryIO, Dict, List, Optional, Union, Any
from datetime import datetime
from config import Config
from .storage_adapter import StorageAdapter

# Import AWS libraries
try:
    import boto3
    from botocore.exceptions import ClientError

    AWS_AVAILABLE = True
except ImportError:
    AWS_AVAILABLE = False

logger = logging.getLogger(__name__)


class S3StorageAdapter(StorageAdapter):
    """
    Storage adapter for Amazon S3.
    """

    def __init__(self):
        """
        Initialize the S3 storage adapter.
        """
        super().__init__()

        if not AWS_AVAILABLE:
            raise ImportError("AWS libraries not installed. Install with: pip install boto3")

        # Get S3 configuration from config or environment variables
        self.bucket_name = Config.S3_BUCKET_NAME
        self.region_name = Config.AWS_REGION_NAME
        self.aws_access_key_id = Config.AWS_ACCESS_KEY_ID
        self.aws_secret_access_key = Config.AWS_SECRET_ACCESS_KEY
        self.endpoint_url = Config.AWS_ENDPOINT_URL

        if not self.bucket_name:
            raise ValueError("S3_BUCKET_NAME must be specified")

        # Initialize S3 client and resource
        self.s3_client = self._initialize_client()
        self.s3_resource = self._initialize_resource()
        self.bucket = self.s3_resource.Bucket(self.bucket_name)

        # Create bucket if it doesn't exist
        self._create_bucket_if_not_exists()

        logger.info(f"S3StorageAdapter initialized with bucket: {self.bucket_name}")

    def _initialize_client(self):
        """
        Initialize the S3 client.

        Returns:
            boto3.client: S3 client
        """
        try:
            kwargs = {
                'region_name': self.region_name
            }

            # Add credentials if provided
            if self.aws_access_key_id and self.aws_secret_access_key:
                kwargs['aws_access_key_id'] = self.aws_access_key_id
                kwargs['aws_secret_access_key'] = self.aws_secret_access_key

            # Add endpoint URL if provided (useful for MinIO and other S3-compatible services)
            if self.endpoint_url:
                kwargs['endpoint_url'] = self.endpoint_url

            return boto3.client('s3', **kwargs)
        except Exception as e:
            logger.error(f"Error initializing S3 client: {str(e)}")
            raise IOError(f"Failed to initialize S3 client: {str(e)}")

    def _initialize_resource(self):
        """
        Initialize the S3 resource.

        Returns:
            boto3.resource: S3 resource
        """
        try:
            kwargs = {
                'region_name': self.region_name
            }

            # Add credentials if provided
            if self.aws_access_key_id and self.aws_secret_access_key:
                kwargs['aws_access_key_id'] = self.aws_access_key_id
                kwargs['aws_secret_access_key'] = self.aws_secret_access_key

            # Add endpoint URL if provided
            if self.endpoint_url:
                kwargs['endpoint_url'] = self.endpoint_url

            return boto3.resource('s3', **kwargs)
        except Exception as e:
            logger.error(f"Error initializing S3 resource: {str(e)}")
            raise IOError(f"Failed to initialize S3 resource: {str(e)}")

    def _create_bucket_if_not_exists(self):
        """
        Create the S3 bucket if it doesn't exist.
        """
        try:
            # Check if bucket exists
            self.s3_client.head_bucket(Bucket=self.bucket_name)
        except ClientError as e:
            error_code = e.response.get('Error', {}).get('Code')

            if error_code == '404':
                # Bucket does not exist, create it
                logger.info(f"Creating S3 bucket: {self.bucket_name}")

                if self.region_name and self.region_name != 'us-east-1':
                    # For regions other than us-east-1, we need to specify the location constraint
                    self.s3_client.create_bucket(
                        Bucket=self.bucket_name,
                        CreateBucketConfiguration={
                            'LocationConstraint': self.region_name
                        }
                    )
                else:
                    # For us-east-1, we don't specify a location constraint
                    self.s3_client.create_bucket(Bucket=self.bucket_name)
            else:
                # Some other error occurred
                raise

    def _ensure_directory_exists(self, path: str) -> None:
        """
        For S3, directories don't need to be explicitly created,
        but we can create a directory marker if needed.

        Args:
            path: Path to a file or directory
        """
        # S3 doesn't require directories to be created explicitly,
        # but we can create a directory marker object
        if path:
            dir_path = os.path.dirname(path)
            if dir_path and '/' in dir_path:
                # Create parent directories
                parts = dir_path.split('/')
                for i in range(1, len(parts) + 1):
                    part_path = '/'.join(parts[:i]) + '/'
                    if not self._object_exists(part_path):
                        try:
                            # Create an empty object with a trailing slash to represent a directory
                            self.s3_client.put_object(
                                Bucket=self.bucket_name,
                                Key=part_path,
                                Body=b'',
                                ContentType='application/x-directory'
                            )
                        except Exception as e:
                            logger.warning(f"Could not create directory marker {part_path}: {str(e)}")
                            # Continue anyway since S3 doesn't need actual directories

    def _object_exists(self, key: str) -> bool:
        """
        Check if an object exists in S3.

        Args:
            key: S3 object key

        Returns:
            bool: True if the object exists, False otherwise
        """
        try:
            self.s3_client.head_object(Bucket=self.bucket_name, Key=key)
            return True
        except ClientError as e:
            error_code = e.response.get('Error', {}).get('Code')
            if error_code == '404':
                return False
            else:
                raise

    def read_file(self, path: str) -> bytes:
        """
        Read a file and return its contents as bytes.
        """
        normalized_path = self.normalize_path(path)

        try:
            response = self.s3_client.get_object(Bucket=self.bucket_name, Key=normalized_path)
            return response['Body'].read()
        except ClientError as e:
            error_code = e.response.get('Error', {}).get('Code')

            if error_code == 'NoSuchKey':
                raise FileNotFoundError(f"File not found in S3: {path}")
            else:
                logger.error(f"Error reading file from S3 {path}: {str(e)}")
                raise IOError(f"Error reading file from S3: {str(e)}")

    def write_file(self, path: str, data: Union[bytes, str, BinaryIO], content_type: Optional[str] = None) -> bool:
        """
        Write data to a file in S3.
        """
        normalized_path = self.normalize_path(path)

        # Ensure parent directories exist (creates directory markers in S3)
        self._ensure_directory_exists(normalized_path)

        try:
            kwargs = {
                'Bucket': self.bucket_name,
                'Key': normalized_path
            }

            if content_type:
                kwargs['ContentType'] = content_type

            if isinstance(data, bytes):
                kwargs['Body'] = data
                self.s3_client.put_object(**kwargs)
            elif isinstance(data, str):
                kwargs['Body'] = data.encode('utf-8')
                if not content_type:
                    kwargs['ContentType'] = 'text/plain'
                self.s3_client.put_object(**kwargs)
            elif hasattr(data, 'read'):  # File-like object
                self.s3_client.upload_fileobj(data, self.bucket_name, normalized_path, ExtraArgs=kwargs)
            else:
                raise TypeError(f"Unsupported data type: {type(data)}")

            return True
        except Exception as e:
            logger.error(f"Error writing file to S3 {path}: {str(e)}")
            raise IOError(f"Error writing file to S3: {str(e)}")

    def delete_file(self, path: str) -> bool:
        """
        Delete a file from S3.
        """
        normalized_path = self.normalize_path(path)

        try:
            # Check if file exists
            if not self._object_exists(normalized_path):
                return False

            self.s3_client.delete_object(Bucket=self.bucket_name, Key=normalized_path)
            return True
        except Exception as e:
            logger.error(f"Error deleting file from S3 {path}: {str(e)}")
            raise IOError(f"Error deleting file from S3: {str(e)}")

    def _object_exists(self, key: str) -> bool:
        """
        Check if an object exists in S3.

        Args:
            key: S3 object key

        Returns:
            bool: True if the object exists, False otherwise
        """
        try:
            self.s3_client.head_object(Bucket=self.bucket_name, Key=key)
            return True
        except ClientError as e:
            error_code = e.response.get('Error', {}).get('Code')
            if error_code == '404':
                return False
            else:
                raise

    def copy_file(self, source_path: str, dest_path: str) -> bool:
        """
        Copy a file within S3.
        """
        source_path = self.normalize_path(source_path)
        dest_path = self.normalize_path(dest_path)

        # Check if source exists
        if not self._object_exists(source_path):
            raise FileNotFoundError(f"Source file not found in S3: {source_path}")

        # Ensure parent directories exist for destination
        self._ensure_directory_exists(dest_path)

        try:
            copy_source = {'Bucket': self.bucket_name, 'Key': source_path}
            self.s3_client.copy_object(CopySource=copy_source, Bucket=self.bucket_name, Key=dest_path)
            return True
        except Exception as e:
            logger.error(f"Error copying file in S3 from {source_path} to {dest_path}: {str(e)}")
            raise IOError(f"Error copying file in S3: {str(e)}")

    def move_file(self, source_path: str, dest_path: str) -> bool:
        """
        Move a file within S3 (copy and delete).
        """
        try:
            self.copy_file(source_path, dest_path)
            self.delete_file(source_path)
            return True
        except Exception as e:
            logger.error(f"Error moving file in S3 from {source_path} to {dest_path}: {str(e)}")
            raise IOError(f"Error moving file in S3: {str(e)}")

    def file_exists(self, path: str) -> bool:
        """
        Check if a file exists in S3.
        """
        normalized_path = self.normalize_path(path)
        return self._object_exists(normalized_path)

    def get_file_size(self, path: str) -> int:
        """
        Get the size of a file in S3.
        """
        normalized_path = self.normalize_path(path)

        try:
            response = self.s3_client.head_object(Bucket=self.bucket_name, Key=normalized_path)
            return response['ContentLength']
        except ClientError as e:
            error_code = e.response.get('Error', {}).get('Code')
            if error_code == '404':
                raise FileNotFoundError(f"File not found in S3: {path}")
            else:
                logger.error(f"Error getting file size from S3 {path}: {str(e)}")
                raise IOError(f"Error getting file size from S3: {str(e)}")

    def get_file_metadata(self, path: str) -> Dict[str, Any]:
        """
        Get metadata about a file in S3.
        """
        normalized_path = self.normalize_path(path)

        try:
            response = self.s3_client.head_object(Bucket=self.bucket_name, Key=normalized_path)

            metadata = {
                'path': path,
                'key': normalized_path,
                'bucket': self.bucket_name,
                'size': response['ContentLength'],
                'content_type': response.get('ContentType'),
                'last_modified': response['LastModified'],
                'etag': response['ETag'].strip('"'),
                'storage_class': response.get('StorageClass'),
                'metadata': response.get('Metadata', {}),
                'version_id': response.get('VersionId')
            }

            return metadata
        except ClientError as e:
            error_code = e.response.get('Error', {}).get('Code')
            if error_code == '404':
                raise FileNotFoundError(f"File not found in S3: {path}")
            else:
                logger.error(f"Error getting file metadata from S3 {path}: {str(e)}")
                raise IOError(f"Error getting file metadata from S3: {str(e)}")

    def get_created_time(self, path: str) -> datetime:
        """
        Get the creation time of a file.

        For S3 objects, the creation time is effectively the last modified time
        since S3 doesn't track creation time separately.

        Args:
            path: Path to the file

        Returns:
            datetime: Creation/last modified time of the file

        Raises:
            FileNotFoundError: If the file doesn't exist
        """
        normalized_path = self.normalize_path(path)

        try:
            response = self.s3_client.head_object(Bucket=self.bucket_name, Key=normalized_path)
            return response['LastModified']
        except ClientError as e:
            error_code = e.response.get('Error', {}).get('Code')
            if error_code == '404':
                raise FileNotFoundError(f"File not found in S3: {path}")
            else:
                logger.error(f"Error getting file creation time from S3 {path}: {str(e)}")
                raise IOError(f"Error getting file creation time from S3: {str(e)}")

    def get_file_checksum(self, path: str, algorithm: str = 'md5') -> str:
        """
        Get checksum for a file in S3.
        S3 provides ETag (usually MD5) natively. For other algorithms, download and calculate.
        """
        normalized_path = self.normalize_path(path)

        if algorithm.lower() == 'md5':
            # Try to get the ETag from S3 (usually this is the MD5 hash, unless it's a multipart upload)
            try:
                response = self.s3_client.head_object(Bucket=self.bucket_name, Key=normalized_path)
                etag = response['ETag'].strip('"')

                # If ETag doesn't contain a dash, it's an MD5 hash
                if '-' not in etag:
                    return etag
            except ClientError:
                pass  # Fall back to downloading and calculating

        # Download the file and calculate the checksum
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
        List files in a directory in S3.
        """
        normalized_path = self.normalize_path(directory_path)

        # Make sure the path ends with a slash for directory-like behavior
        if normalized_path and not normalized_path.endswith('/'):
            normalized_path += '/'

        try:
            # Set up the parameters for listing objects
            params = {
                'Bucket': self.bucket_name,
                'Prefix': normalized_path
            }

            # If not recursive, simulate directory listing with delimiter
            if not recursive:
                params['Delimiter'] = '/'

            # Get objects with the prefix
            paginator = self.s3_client.get_paginator('list_objects_v2')
            page_iterator = paginator.paginate(**params)

            result = []
            found_objects = False

            for page in page_iterator:
                # Check if any objects were found
                found_objects = found_objects or page.get('KeyCount', 0) > 0

                # Process regular objects
                if 'Contents' in page:
                    for obj in page['Contents']:
                        key = obj['Key']

                        # Skip the directory itself
                        if key == normalized_path:
                            continue

                        # Apply pattern filtering if specified
                        if pattern and not fnmatch.fnmatch(os.path.basename(key), pattern):
                            continue

                        result.append(key)

                # Process common prefixes (directories) when using delimiter
                if 'CommonPrefixes' in page:
                    for prefix in page['CommonPrefixes']:
                        key = prefix['Prefix']

                        # Skip the directory itself
                        if key == normalized_path:
                            continue

                        result.append(key)

            # If no objects were found and the path is not empty, check if the directory exists
            if not found_objects and normalized_path:
                if not self._directory_exists_check(normalized_path):
                    raise FileNotFoundError(f"Directory not found in S3: {directory_path}")

            return result
        except Exception as e:
            if isinstance(e, FileNotFoundError):
                raise
            logger.error(f"Error listing files in S3 {directory_path}: {str(e)}")
            raise IOError(f"Error listing files in S3: {str(e)}")

    def _directory_exists_check(self, prefix: str) -> bool:
        """
        Check if a directory exists in S3 by looking for any objects with the given prefix.

        Args:
            prefix: The directory prefix to check

        Returns:
            bool: True if at least one object exists with the prefix, False otherwise
        """
        try:
            response = self.s3_client.list_objects_v2(
                Bucket=self.bucket_name,
                Prefix=prefix,
                MaxKeys=1
            )
            return response.get('KeyCount', 0) > 0
        except Exception:
            return False

    def create_directory(self, path: str) -> bool:
        """
        Create a directory in S3.

        Note: S3 has no real concept of directories, but we can create a placeholder object.
        """
        normalized_path = self.normalize_path(path)
        if not normalized_path.endswith('/'):
            normalized_path += '/'

        # Check if it already exists
        if self._object_exists(normalized_path):
            return False

        try:
            # Create an empty object with a trailing slash to represent a directory
            self.s3_client.put_object(
                Bucket=self.bucket_name,
                Key=normalized_path,
                Body=b'',
                ContentType='application/x-directory'
            )
            return True
        except Exception as e:
            logger.error(f"Error creating directory in S3 {path}: {str(e)}")
            raise IOError(f"Error creating directory in S3: {str(e)}")

    def delete_directory(self, path: str, recursive: bool = False) -> bool:
        """
        Delete a directory in S3.
        """
        normalized_path = self.normalize_path(path)
        if not normalized_path.endswith('/'):
            normalized_path += '/'

        try:
            # Check if directory exists
            if not self._directory_exists_check(normalized_path):
                return False

            # List objects in the directory
            paginator = self.s3_client.get_paginator('list_objects_v2')
            page_iterator = paginator.paginate(
                Bucket=self.bucket_name,
                Prefix=normalized_path
            )

            objects_to_delete = []
            for page in page_iterator:
                if 'Contents' in page:
                    for obj in page['Contents']:
                        objects_to_delete.append(obj['Key'])

            # If not recursive, check if the directory contains more than just the directory marker
            if not recursive and len(objects_to_delete) > 1:
                # The only object should be the directory marker itself
                if not (len(objects_to_delete) == 1 and objects_to_delete[0] == normalized_path):
                    raise ValueError(
                        f"Directory not empty: {path}. Use recursive=True to delete non-empty directories.")

            # Delete objects in batches (S3 allows up to 1000 objects per delete operation)
            if objects_to_delete:
                for i in range(0, len(objects_to_delete), 1000):
                    batch = objects_to_delete[i:i + 1000]
                    self.s3_client.delete_objects(
                        Bucket=self.bucket_name,
                        Delete={
                            'Objects': [{'Key': key} for key in batch],
                            'Quiet': True
                        }
                    )

            return True
        except Exception as e:
            if isinstance(e, ValueError):
                raise  # Re-raise ValueError for non-empty directories
            logger.error(f"Error deleting directory from S3 {path}: {str(e)}")
            raise IOError(f"Error deleting directory from S3: {str(e)}")

    def directory_exists(self, path: str) -> bool:
        """
        Check if a directory exists in S3.
        """
        normalized_path = self.normalize_path(path)
        if not normalized_path.endswith('/'):
            normalized_path += '/'

        # Check for directory marker object
        if self._object_exists(normalized_path):
            return True

        # Check if any objects exist with this prefix
        return self._directory_exists_check(normalized_path)

    def generate_signed_url(self, path: str, expiration: int = 3600) -> str:
        """
        Generate a signed URL for temporary access to a file in S3.
        """
        normalized_path = self.normalize_path(path)

        # Check if file exists
        if not self._object_exists(normalized_path):
            raise FileNotFoundError(f"File not found in S3: {path}")

        try:
            # Generate a signed URL that expires after the specified time
            url = self.s3_client.generate_presigned_url(
                'get_object',
                Params={
                    'Bucket': self.bucket_name,
                    'Key': normalized_path
                },
                ExpiresIn=expiration
            )
            return url
        except Exception as e:
            logger.error(f"Error generating signed URL for S3 file {path}: {str(e)}")
            raise IOError(f"Error generating signed URL: {str(e)}")

    def make_public(self, path: str) -> bool:
        """
        Make a file publicly accessible in S3.
        """
        normalized_path = self.normalize_path(path)

        # Check if file exists
        if not self._object_exists(normalized_path):
            raise FileNotFoundError(f"File not found in S3: {path}")

        try:
            self.s3_client.put_object_acl(
                Bucket=self.bucket_name,
                Key=normalized_path,
                ACL='public-read'
            )
            return True
        except Exception as e:
            logger.error(f"Error making file public in S3 {path}: {str(e)}")
            raise IOError(f"Error making file public: {str(e)}")

    def make_private(self, path: str) -> bool:
        """
        Make a file private in S3.
        """
        normalized_path = self.normalize_path(path)

        # Check if file exists
        if not self._object_exists(normalized_path):
            raise FileNotFoundError(f"File not found in S3: {path}")

        try:
            self.s3_client.put_object_acl(
                Bucket=self.bucket_name,
                Key=normalized_path,
                ACL='private'
            )
            return True
        except Exception as e:
            logger.error(f"Error making file private in S3 {path}: {str(e)}")
            raise IOError(f"Error making file private: {str(e)}")

    def get_storage_info(self) -> Dict[str, Any]:
        """
        Get information about the S3 storage.
        """
        try:
            # Get bucket location
            location_response = self.s3_client.get_bucket_location(Bucket=self.bucket_name)
            location = location_response.get('LocationConstraint', 'us-east-1')

            # Get bucket versioning
            versioning_response = self.s3_client.get_bucket_versioning(Bucket=self.bucket_name)
            versioning_enabled = versioning_response.get('Status') == 'Enabled'

            # Get bucket lifecycle
            lifecycle = None
            try:
                lifecycle_response = self.s3_client.get_bucket_lifecycle_configuration(Bucket=self.bucket_name)
                lifecycle = lifecycle_response.get('Rules', [])
            except ClientError as e:
                error_code = e.response.get('Error', {}).get('Code')
                if error_code != 'NoSuchLifecycleConfiguration':
                    raise

            return {
                'type': 's3',
                'bucket_name': self.bucket_name,
                'region': location,
                'endpoint_url': self.endpoint_url,
                'versioning_enabled': versioning_enabled,
                'lifecycle_rules': lifecycle
            }
        except Exception as e:
            logger.error(f"Error getting S3 storage info: {str(e)}")
            return {
                'type': 's3',
                'bucket_name': self.bucket_name,
                'region': self.region_name,
                'endpoint_url': self.endpoint_url,
                'error': str(e)
            }
