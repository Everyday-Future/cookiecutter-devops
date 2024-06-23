from pathlib import Path
from typing import Optional, Union
import logging
from retry import retry
from google.cloud import storage
from google.cloud.exceptions import NotFound
from config import Config

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


class GcpStorage:
    """
    File in Cloud storage. In Google Cloud Storage for now.
    """

    def __init__(self, bucket_name: Optional[str] = None):
        self.bucket_name = bucket_name or Config.GCS_BUCKET
        self.client = storage.Client()
        self.bucket = self.client.bucket(self.bucket_name)

    @retry(Exception, tries=3, delay=2)
    def upload(self, link: str, fpath: Union[str, Path], expires_in: int = 60 * 60 * 24 * 7) -> str:
        """
        Upload a file to Google Cloud Storage and get a presigned URL
        :param link: The key under which the file will be stored in GCS
        :param fpath: The local path to the file to be uploaded
        :param expires_in: Expiration time in seconds for the presigned URL
        :return: The presigned URL
        """
        fpath = Path(fpath)
        blob = self.bucket.blob(link)

        try:
            blob.upload_from_filename(str(fpath))
            url = blob.generate_signed_url(expiration=expires_in)
            logger.info({
                "message": "A file was successfully uploaded to GCS.",
                "link": link,
                "fpath": str(fpath),
                "bucket_name": self.bucket_name
            })
            return url
        except Exception as e:
            logger.exception({
                "message": "An error occurred while uploading the file to GCS.",
                "link": link,
                "fpath": str(fpath),
                "bucket_name": self.bucket_name
            })
            raise

    @retry(Exception, tries=3, delay=2)
    def download(self, link: str, fpath: Union[str, Path]) -> Path:
        """
        Download a file from Google Cloud Storage into a target directory
        :param link: The key under which the file is stored in GCS
        :param fpath: The local path where the file will be downloaded
        :return: The local path to the downloaded file
        """
        fpath = Path(fpath)
        blob = self.bucket.blob(link)

        try:
            blob.download_to_filename(str(fpath))
            logger.info({
                "message": "A file was successfully downloaded from GCS.",
                "link": link,
                "fpath": str(fpath),
                "bucket_name": self.bucket_name
            })
            return fpath
        except NotFound as e:
            logger.exception({
                "message": f'No storage blob found in bucket={self.bucket_name} for link={link} err={e}',
                "link": link,
                "bucket_name": self.bucket_name
            })
            raise KeyError(f'No storage blob found in bucket={self.bucket_name} for link={link}')
        except Exception as e:
            logger.exception({
                "message": "The file specified for download does not exist in GCS.",
                "link": link,
                "bucket_name": self.bucket_name
            })
            raise ValueError("An error occurred that prevented the file from downloading correctly.")

    @retry(Exception, tries=3, delay=2)
    def multipart_upload(self, link: str, fpath: Union[str, Path]) -> str:
        """
        Upload large files to Google Cloud Storage
        :param link: The key under which the file will be stored in GCS
        :param fpath: The local path to the file to be uploaded
        :return: The presigned URL
        """
        fpath = Path(fpath)
        blob = self.bucket.blob(link)

        try:
            blob.upload_from_filename(str(fpath))
            url = blob.generate_signed_url(expiration=60 * 60 * 24 * 7)
            logger.info({
                "message": "A large file was successfully uploaded to GCS.",
                "link": link,
                "fpath": str(fpath),
                "bucket_name": self.bucket_name
            })
            return url
        except Exception as e:
            logger.exception({
                "message": "An error occurred while uploading the large file to GCS.",
                "link": link,
                "fpath": str(fpath),
                "bucket_name": self.bucket_name
            })
            raise
