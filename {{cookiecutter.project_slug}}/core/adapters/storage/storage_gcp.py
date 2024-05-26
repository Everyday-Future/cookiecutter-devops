from google.cloud import storage
from google.cloud.exceptions import NotFound
from api import global_config, logger


class GcpStorage:
    """
    File in Cloud storage. In Amazon S3 for now.
    """

    def __init__(self, bucket_name=None):
        """
        Connect to a cloud storage bucket by name
        :param bucket_name: Name of GCP bucket to connect to
        :type bucket_name: str
        """
        self.bucket_name = bucket_name or global_config.GCP_BUCKET
        self.client = storage.Client(credentials=global_config.GCP_STORAGE_CREDS_FILE)
        # https://console.cloud.google.com/storage/browser/[bucket-id]/
        self.bucket = self.client.get_bucket(self.bucket_name)

    def download(self, link, fpath):
        """
        Download a file from a cloud storage bucket to a specified path
        :param link: Link to the asset it the cloud storage bucket
        :type link: str
        :param fpath: Path that the downloaded file will be saved to
        :type fpath: str
        :return: Path that the downloaded file will be saved to
        :rtype: str
        """
        blob = self.bucket.get_blob(link)
        try:
            blob.download_to_filename(fpath)
        except NotFound as err:
            logger.exception({"message": f'no storage blob found in bucket={self.bucket_name} '
                                         f'for link={link} err={err}',
                              "error_code": err.response['Error']['Code'],
                              "link": link,
                              "bucket_name": self.bucket_name})
            raise KeyError(f'no storage blob found in bucket={self.bucket_name} for link={link}')
        logger.info({"message": "A file was successfully downloaded from GCP Storage.",
                     "link": link,
                     "fpath": fpath,
                     "bucket_name": self.bucket_name})
        return fpath

    def upload(self, link, fpath):
        """
        Upload a file from a specified path to a cloud storage bucket.
        :param link: Link to the asset that will be created in the cloud storage bucket
        :type link: str
        :param fpath: Path to the file to be uploaded
        :type fpath: str
        :return: Link to the asset that was created in the cloud storage bucket
        :rtype: str
        """
        blob = self.bucket.blob(link)
        blob.upload_from_filename(filename=fpath)
        logger.info({"message": "A file was successfully uploaded to GCP Storage.",
                     "link": link,
                     "fpath": fpath,
                     "bucket_name": self.bucket_name})
        return blob.public_url
