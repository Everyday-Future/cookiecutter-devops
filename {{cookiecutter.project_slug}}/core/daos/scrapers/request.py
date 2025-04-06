# core/daos/scrapers/request.py
import hashlib
import os
import random
import time
from http.client import RemoteDisconnected
from pathlib import Path
from typing import Optional, Dict, List, Tuple, Callable, Any
import requests
from requests.adapters import HTTPAdapter
from urllib3 import Retry
from urllib3.exceptions import ProtocolError
from config import Config, logger


# noinspection HttpUrlsUsage
class RequestScraper:
    """
    A class to handle downloading and processing of web pages.
    :param output_dir: Directory path where HTML files will be saved
    :type output_dir: str
    :param verify_ssl: Whether to verify SSL certificates
    :type verify_ssl: bool
    :param custom_headers: Additional headers to send with requests
    :type custom_headers: Optional[Dict[str, str]]
    """
    output_dir: Path

    def __init__(self,
                 output_dir: str = None,
                 verify_ssl: bool = True,
                 custom_headers: Optional[Dict[str, str]] = None,
                 max_retries: int = 2,
                 min_wait: float = 1.0,
                 max_wait: float = 16.0):
        """
        Initialize the calendar scraper with enhanced retry configuration.
        :param output_dir: Directory path where HTML files will be saved
        :param verify_ssl: Whether to verify SSL certificates
        :param custom_headers: Additional headers to send with requests
        :param max_retries: Maximum number of retries for failed requests
        :param min_wait: Minimum wait time between retries in seconds
        :param max_wait: Maximum wait time between retries in seconds
        """
        if output_dir is None:
            output_dir = str(os.path.join(Config.TEMP_DIR))
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.verify_ssl = verify_ssl
        self.max_retries = max_retries
        self.min_wait = min_wait
        self.max_wait = max_wait
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) '
                          'Chrome/91.0.4472.124 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Accept-Encoding': 'gzip, deflate',  # Removed 'br' to avoid compression issues
            'DNT': '1',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1'
        }
        if custom_headers:
            self.headers.update(custom_headers)

    @staticmethod
    def generate_filename(url: str) -> str:
        """
        Generate a unique filename for a URL using its hash.
        :param url: The URL to generate a filename for
        :type url: str
        :return: A unique filename based on the URL's hash
        :rtype: str
        """
        return hashlib.md5(url.encode()).hexdigest() + '.html'

    def create_session(self) -> requests.Session:
        """
        Create a requests session with proper retry configuration.

        :return: Configured requests session
        """
        session = requests.Session()
        session.headers.update(self.headers)
        session.verify = self.verify_ssl
        # Configure retry strategy for the session
        retry_strategy = Retry(
            total=self.max_retries,
            backoff_factor=0.5,
            status_forcelist=[429, 500, 502, 503, 504],
            allowed_methods=["GET", "HEAD"],
            raise_on_status=False,  # Don't raise errors on status
            respect_retry_after_header=True
        )
        adapter = HTTPAdapter(max_retries=retry_strategy)
        session.mount("http://", adapter)
        session.mount("https://", adapter)
        return session

    def exponential_backoff(self, attempt: int) -> float:
        """
        Calculate backoff time with jitter.
        :param attempt: The current attempt number
        :return: Time to wait in seconds
        """
        # Calculate exponential backoff with maximum limit
        wait = min(self.max_wait, self.min_wait * (2 ** attempt))
        # Add jitter (±25% of wait time)
        jitter = wait * 0.5 * (random.random() - 0.5)
        return wait + jitter

    def download_page(self, url: str) -> Optional[str]:
        """
        Download a webpage with enhanced error handling and retry logic.
        :param url: The URL to download
        :return: The HTML content if successful, None if failed
        """
        session = self.create_session()
        attempt = 0
        last_exception = None
        while attempt < self.max_retries:
            try:
                # Make the request with a longer timeout
                response = session.get(url, timeout=30)
                if response.status_code == 403:
                    logger.warning(f"403 Forbidden error for {url}. Possibly rate-limited or blocked.")
                    return None
                if response.status_code >= 400:
                    logger.warning(f"HTTP {response.status_code} error for {url}")
                    wait_time = self.exponential_backoff(attempt)
                    time.sleep(wait_time)
                    attempt += 1
                    continue
                return response.text
            except (ProtocolError, RemoteDisconnected) as e:
                logger.warning(f"Protocol error on attempt {attempt + 1} for {url}: {str(e)}")
                last_exception = e
                # Close and recreate session on protocol errors
                session.close()
                session = self.create_session()
                wait_time = self.exponential_backoff(attempt)
                logger.debug(f"Waiting {wait_time:.2f} seconds before retry...")
                time.sleep(wait_time)
            except requests.exceptions.SSLError as e:
                logger.info(f"SSL Error for {url}: {str(e)}")
                if not self.verify_ssl:
                    return None
                # Try once without SSL verification
                try:
                    logger.debug(f"Retrying {url} without SSL verification...")
                    response = session.get(url, verify=False, timeout=30)
                    return response.text
                except Exception as e:
                    last_exception = e
            except requests.exceptions.RequestException as e:
                logger.warning(f"Request failed on attempt {attempt + 1} for {url}: {str(e)}")
                last_exception = e
            attempt += 1
        logger.warning(f"All attempts failed for {url}. Last error: {str(last_exception)}")
        return None

    def save_html(self, html_content: str, filename: str) -> bool:
        """
        Save HTML content to a file.
        :param html_content: The HTML content to save
        :type html_content: str
        :param filename: The name of the file to save to
        :type filename: str
        :return: True if save was successful, False otherwise
        :rtype: bool
        """
        try:
            file_path = self.output_dir / filename
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(html_content)
            return True
        except Exception as e:
            logger.exception(f"Failed to save {filename}: {str(e)}")
            return False

    def load_html(self, file_name):
        """
        Load the HTML content from the specified file.
        :param file_name:
        :return:
        """
        file_path = self.output_dir / file_name
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
                return content
        except Exception as e:
            print(f"Failed to read {file_path.name}: {str(e)}")

    def process_urls(self, urls: List[str]) -> List[str | None]:
        """
        Process a list of URLs, downloading and saving their content.
        :param urls: List of URLs to process
        :type urls: List[str]
        :return: Dictionary mapping URLs to their saved filenames
        :rtype: Dict[str, str]
        """
        filenames = []
        for url in urls:
            filename = self.generate_filename(url)
            time.sleep(random.random() * 5.0)
            logger.debug(f"Processing {url}")
            html_content = self.download_page(url)
            if html_content:
                if self.save_html(html_content, filename):
                    filenames.append(filename)
                    logger.debug(f"Successfully saved {url} to {filename}")
                else:
                    filenames.append(None)
                    logger.debug(f"Failed to save content for {url}")
            else:
                filenames.append(None)
                logger.error(f"Failed to download {url}")
        return filenames

    def get_html_list(self) -> List[Tuple[str, str]]:
        """
        Read all HTML files from the output directory.
        :return: List of tuples containing (filename, html_content)
        :rtype: List[Tuple[str, str]]
        """
        html_files = []
        for file_path in self.output_dir.glob('*.html'):
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                    html_files.append((file_path.name, content))
                    logger.debug(f"Successfully read {file_path.name}")
            except Exception as e:
                logger.exception(f"Failed to read {file_path.name}: {str(e)}")
        return html_files

    def get_html_str(self, file_name) -> str:
        """
        Read the HTML file from the directory
        :param file_name: Name of the file to be loaded
        :type file_name: str
        :return: HTML content string
        :rtype: str
        """
        file_path = self.output_dir / file_name
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
                logger.debug(f"Successfully read {file_path.name}")
                return content
        except Exception as e:
            logger.exception(f"Failed to read {file_path.name}: {str(e)}")

    def post_process(self, processor_func: Callable[[str], Any]) -> List[Any]:
        """
        Apply a processing function to all downloaded HTML files.
        :param processor_func: Function that takes HTML content as string and returns processed data
        :type processor_func: Callable[[str], Any]
        :return: List of results from processing each file
        :rtype: List[Any]
        """
        results = []
        html_files = self.get_html_list()
        for filename, content in html_files:
            try:
                result = processor_func(content)
                results.append(result)
                logger.debug(f"Successfully processed {filename}")
            except Exception as e:
                logger.exception(f"Failed to process {filename}: {str(e)}")
        return results
