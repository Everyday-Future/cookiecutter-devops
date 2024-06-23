"""

Universal Storage Adapter

Upload and download files to cloud storage in a platform-independent way.

Specify type_name as 'aws' or 'gcp' to create a new storage instance.

"""
import os.path

from core.adapters.storage.storage_gcp import GcpStorage
from core.adapters.storage.storage_aws import AwsStorage


class Storage:
    """
    Abstraction of storage layers to simplify exposing CDN resources to the rest of the app
    """
    def __init__(self, type_name='gcp'):
        # Load storage adapter type with credentials supplied by Config
        if type_name == 'aws':
            self.storage = AwsStorage()
        elif type_name == 'gcp':
            self.storage = GcpStorage()

    def upload(self, link, fpath):
        """
        Upload a file from fpath to cloud storage, returning the link to the cloud resource
        :param link: link to cloud resource
        :type link: str
        :param fpath: fpath to store downloaded file
        :type fpath: str
        :return: link to resulting cloud resource
        :rtype: str
        """
        return self.storage.upload(link=link, fpath=fpath)

    def download(self, link, fpath):
        """
        Download a file from cloud storage to the fpath, returning the specified fpath
        :param link: link to cloud resource
        :type link: str
        :param fpath: fpath to store downloaded file
        :type fpath: str
        :return: fpath to downloaded file
        :rtype: str
        """
        return self.storage.download(link=link, fpath=fpath)

    def get_or_download(self, link, fpath):
        """
        If a file doesn't exist, download it. Otherwise, return the fpath.
        :param link:
        :type link:
        :param fpath:
        :type fpath:
        :return:
        :rtype:
        """
        if os.path.isfile(fpath):
            return fpath
        else:
            self.download(link=link, fpath=fpath)
            return fpath
