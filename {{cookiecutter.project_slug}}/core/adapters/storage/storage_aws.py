import boto3
from botocore.client import Config as BotoConfig
from botocore.exceptions import ClientError
from boto3.s3.transfer import TransferConfig
from api import global_config, logger


class AwsStorage:
    """
    File in Cloud storage. In Amazon S3 for now.
    """

    def __init__(self, region_name=None, bucket_name=None):
        self.region_name = region_name or global_config.S3_REGION
        self.bucket_name = bucket_name or global_config.S3_BUCKET

    def upload(self, link, fpath):
        """
        Upload a file to Amazon S3 and get a presigned url
        :param link:
        :type link:
        :param fpath:
        :type fpath:
        :return:
        :rtype:
        """
        # Create an S3 client
        session = boto3.session.Session()
        s3 = session.client('s3', region_name=self.region_name,
                            aws_access_key_id=global_config.AWS_ACCESS_KEY_ID,
                            aws_secret_access_key=global_config.AWS_SECRET_ACCESS_KEY,
                            config=BotoConfig(signature_version='s3v4'))
        s3.upload_file(fpath, self.bucket_name, link, Config=TransferConfig(use_threads=False))
        # Get a presigned URL to fetch the file
        url = s3.generate_presigned_url(ClientMethod='get_object',
                                        Params={'Bucket': self.bucket_name, 'Key': link},
                                        ExpiresIn=60 * 60 * 24 * 7)
        logger.info({"message": "A file was successfully uploaded to S3.",
                     "link": link,
                     "fpath": fpath,
                     "region_name": self.region_name,
                     "bucket_name": self.bucket_name})
        return url

    def download(self, link, fpath):
        """
        Download a file from Amazon S3 into a target directory
        :param link:
        :type link:
        :param fpath:
        :type fpath:
        :return:
        :rtype:
        """
        # Connect to the target S3 bucket
        s3 = boto3.resource('s3', region_name=self.region_name,
                            aws_access_key_id=global_config.AWS_ACCESS_KEY_ID,
                            aws_secret_access_key=global_config.AWS_SECRET_ACCESS_KEY)
        try:
            s3.Bucket(self.bucket_name).download_file(link, fpath)
            logger.info({"message": "A file was successfully downloaded from S3.",
                         "link": link,
                         "fpath": fpath,
                         "region_name": self.region_name,
                         "bucket_name": self.bucket_name})
            return fpath
        except ClientError as err:
            if err.response['Error']['Code'] == "404":
                logger.exception({"message": f'no storage blob found in bucket={self.bucket_name} '
                                             f'for link={link} err={err}',
                                  "error_code": err.response['Error']['Code'],
                                  "link": link,
                                  "region_name": self.region_name,
                                  "bucket_name": self.bucket_name})
                raise KeyError(f'no storage blob found in bucket={self.bucket_name} for link={link}')
            else:
                logger.exception({"message": "The file specified for download does not exist in S3.",
                                  "error_code": err.response['Error']['Code'],
                                  "link": link,
                                  "region_name": self.region_name,
                                  "bucket_name": self.bucket_name})
                raise ValueError("An error occurred that prevented the file from downloading correctly.")
