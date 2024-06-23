from pathlib import Path
from typing import Optional, Union
from retry import retry
import boto3
from botocore.client import Config as BotoConfig
from botocore.exceptions import ClientError
from boto3.s3.transfer import TransferConfig
from api import logger
from config import Config


class AwsStorage:
    """
    File in Cloud storage. In Amazon S3 for now.
    """

    def __init__(self, region_name: Optional[str] = None, bucket_name: Optional[str] = None):
        self.region_name = region_name or Config.S3_REGION
        self.bucket_name = bucket_name or Config.S3_BUCKET
        self.session = boto3.session.Session()

    def _get_s3_client(self):
        return self.session.client(
            's3',
            region_name=self.region_name,
            aws_access_key_id=Config.AWS_ACCESS_KEY_ID,
            aws_secret_access_key=Config.AWS_SECRET_ACCESS_KEY,
            config=BotoConfig(signature_version='s3v4')
        )

    @retry(ClientError, tries=3, delay=2)
    def upload(self, link: str, fpath: Union[str, Path], expires_in: int = 60 * 60 * 24 * 7) -> str:
        """
        Upload a file to Amazon S3 and get a presigned URL
        :param link: The key under which the file will be stored in S3
        :param fpath: The local path to the file to be uploaded
        :param expires_in: Expiration time in seconds for the presigned URL
        :return: The presigned URL
        """
        fpath = Path(fpath)
        s3 = self._get_s3_client()
        transfer_config = TransferConfig(use_threads=False)

        try:
            s3.upload_file(str(fpath), self.bucket_name, link, Config=transfer_config)
            url = s3.generate_presigned_url(
                ClientMethod='get_object',
                Params={'Bucket': self.bucket_name, 'Key': link},
                ExpiresIn=expires_in
            )
            logger.info({
                "message": "A file was successfully uploaded to S3.",
                "link": link,
                "fpath": str(fpath),
                "region_name": self.region_name,
                "bucket_name": self.bucket_name
            })
            return url
        except ClientError as e:
            logger.exception({
                "message": "An error occurred while uploading the file to S3.",
                "error_code": e.response['Error']['Code'],
                "link": link,
                "fpath": str(fpath),
                "region_name": self.region_name,
                "bucket_name": self.bucket_name
            })
            raise

    @retry(ClientError, tries=3, delay=2)
    def download(self, link: str, fpath: Union[str, Path]) -> Path:
        """
        Download a file from Amazon S3 into a target directory
        :param link: The key under which the file is stored in S3
        :param fpath: The local path where the file will be downloaded
        :return: The local path to the downloaded file
        """
        fpath = Path(fpath)
        s3 = boto3.resource(
            's3',
            region_name=self.region_name,
            aws_access_key_id=Config.AWS_ACCESS_KEY_ID,
            aws_secret_access_key=Config.AWS_SECRET_ACCESS_KEY
        )

        try:
            s3.Bucket(self.bucket_name).download_file(link, str(fpath))
            logger.info({
                "message": "A file was successfully downloaded from S3.",
                "link": link,
                "fpath": str(fpath),
                "region_name": self.region_name,
                "bucket_name": self.bucket_name
            })
            return fpath
        except ClientError as err:
            error_code = err.response['Error']['Code']
            if error_code == "404":
                logger.exception({
                    "message": f'No storage blob found in bucket={self.bucket_name} for link={link} err={err}',
                    "error_code": error_code,
                    "link": link,
                    "region_name": self.region_name,
                    "bucket_name": self.bucket_name
                })
                raise KeyError(f'No storage blob found in bucket={self.bucket_name} for link={link}')
            else:
                logger.exception({
                    "message": "The file specified for download does not exist in S3.",
                    "error_code": error_code,
                    "link": link,
                    "region_name": self.region_name,
                    "bucket_name": self.bucket_name
                })
                raise ValueError("An error occurred that prevented the file from downloading correctly.")

    @retry(ClientError, tries=3, delay=2)
    def multipart_upload(self, link: str, fpath: Union[str, Path], part_size: int = 5 * 1024 * 1024) -> str:
        """
        Upload large files to Amazon S3 using multipart upload
        :param link: The key under which the file will be stored in S3
        :param fpath: The local path to the file to be uploaded
        :param part_size: The size of each part in bytes
        :return: The presigned URL
        """
        fpath = Path(fpath)
        s3 = self._get_s3_client()
        transfer_config = TransferConfig(
            multipart_threshold=part_size,
            max_concurrency=10,
            multipart_chunksize=part_size,
            use_threads=True
        )

        try:
            s3.upload_file(str(fpath), self.bucket_name, link, Config=transfer_config)
            url = s3.generate_presigned_url(
                ClientMethod='get_object',
                Params={'Bucket': self.bucket_name, 'Key': link},
                ExpiresIn=60 * 60 * 24 * 7
            )
            logger.info({
                "message": "A large file was successfully uploaded to S3 using multipart upload.",
                "link": link,
                "fpath": str(fpath),
                "region_name": self.region_name,
                "bucket_name": self.bucket_name
            })
            return url
        except ClientError as e:
            logger.exception({
                "message": "An error occurred while uploading the large file to S3 using multipart upload.",
                "error_code": e.response['Error']['Code'],
                "link": link,
                "fpath": str(fpath),
                "region_name": self.region_name,
                "bucket_name": self.bucket_name
            })
            raise
