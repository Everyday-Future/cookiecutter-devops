import pytest
from unittest.mock import Mock, patch, mock_open, PropertyMock
from pathlib import Path
import requests
from requests.exceptions import RequestException, SSLError
from http.client import RemoteDisconnected
from urllib3.exceptions import ProtocolError
from core.daos.scrapers.request import RequestScraper


@pytest.fixture
def scraper():
    """Fixture providing a scraper instance with a temporary directory."""
    with patch('pathlib.Path.mkdir') as mock_mkdir:
        scraper = RequestScraper("./test_output")
        yield scraper


@pytest.fixture
def mock_session():
    """Fixture providing a mock requests session."""
    with patch('requests.Session') as mock_session_class:
        session = Mock()
        mock_session_class.return_value = session
        yield session


@pytest.fixture
def mock_response():
    """Fixture providing a mock requests response."""
    mock = Mock()
    mock.text = "<html><body>Test Content</body></html>"
    mock.status_code = 200
    return mock


@pytest.fixture
def mock_successful_response():
    """Fixture providing a mock successful response."""
    response = Mock()
    response.status_code = 200
    # Use PropertyMock to mock the text property correctly
    type(response).text = PropertyMock(return_value="Success")
    return response


class TestRequestScraper:
    """Unit tests for RequestScraper class."""

    def test_handle_429_rate_limit(self, scraper, mock_session):
        """Test handling of rate limit (429) responses."""
        mock_response = Mock()
        mock_response.status_code = 429
        mock_session.get.side_effect = [mock_response, Mock(status_code=200, text="Success")]

        with patch('time.sleep'):
            result = scraper.download_page("http://example.com")

        assert result == "Success"
        assert mock_session.get.call_count == 2

    def test_connection_timeout(self, scraper, mock_session):
        """Test handling of connection timeouts."""
        mock_session.get.side_effect = requests.exceptions.Timeout("Connection timed out")

        with patch('time.sleep'):
            result = scraper.download_page("http://example.com")

        assert result is None
        assert mock_session.get.call_count == scraper.max_retries

    def test_get_html_str_missing_file(self, scraper):
        """Test handling of missing file in get_html_str."""
        with patch('builtins.open', side_effect=FileNotFoundError()):
            result = scraper.get_html_str("nonexistent.html")
            assert result is None

    def test_get_html_str_encoding_error(self, scraper):
        """Test handling of encoding errors in get_html_str."""
        mock_file = mock_open()
        mock_file.side_effect = UnicodeDecodeError('utf-8', b"", 0, 1, "invalid")

        with patch('builtins.open', mock_file):
            result = scraper.get_html_str("test.html")
            assert result is None

    def test_load_html_invalid_encoding(self, scraper):
        """Test loading HTML with invalid encoding."""
        mock_file = mock_open()
        mock_file.side_effect = UnicodeDecodeError('utf-8', b"", 0, 1, "invalid")

        with patch('builtins.open', mock_file):
            result = scraper.load_html("test.html")
            assert result is None

    def test_session_headers_persistence(self, scraper):
        """Test that headers persist across requests."""
        custom_headers = {'X-Custom': 'Test'}
        scraper = RequestScraper(custom_headers=custom_headers)

        with patch('requests.Session') as mock_session_class:
            session = Mock()
            mock_session_class.return_value = session

            # Create two sessions
            session1 = scraper.create_session()
            session2 = scraper.create_session()

            # Verify headers were set consistently
            assert session.headers.update.call_count == 2
            for call_args in session.headers.update.call_args_list:
                headers = call_args[0][0]
                assert 'X-Custom' in headers
                assert headers['X-Custom'] == 'Test'

    def test_request_compression(self, scraper, mock_session, mock_response):
        """Test handling of compressed responses."""
        # Mock a gzipped response
        mock_response.headers = {'Content-Encoding': 'gzip'}
        mock_session.get.return_value = mock_response

        result = scraper.download_page("http://example.com")

        assert result == mock_response.text
        # Verify correct Accept-Encoding header
        headers = mock_session.get.call_args[1].get('headers', {})
        assert 'Accept-Encoding' in scraper.headers
        assert 'gzip' in scraper.headers['Accept-Encoding']

    def test_save_html_disk_full(self, scraper):
        """Test handling of disk full error when saving HTML."""
        mock_file = mock_open()
        mock_file.side_effect = OSError(28, "No space left on device")

        with patch('builtins.open', mock_file):
            result = scraper.save_html("<html>Test</html>", "test.html")
            assert result is False

    def test_concurrent_directory_creation(self):
        """Test handling of concurrent directory creation."""
        with patch('pathlib.Path.mkdir') as mock_mkdir:
            # Only raise FileExistsError if exist_ok is False
            def mkdir_side_effect(*args, **kwargs):
                if not kwargs.get('exist_ok', False):
                    raise FileExistsError()

            mock_mkdir.side_effect = mkdir_side_effect

            # Should not raise an exception
            scraper = RequestScraper("./test_output")
            assert scraper.output_dir == Path("./test_output")


class TestPageScraper:
    """Unit tests for CalendarScraper class."""

    def test_init_creates_directory(self):
        """Test that initialization creates the output directory."""
        with patch('pathlib.Path.mkdir') as mock_mkdir:
            RequestScraper("./test_output")
            mock_mkdir.assert_called_once_with(parents=True, exist_ok=True)

    def test_generate_filename(self, scraper):
        """Test filename generation from URL."""
        url = "http://example.com/calendar"
        filename = scraper.generate_filename(url)
        assert filename.endswith('.html')
        assert len(filename) == 37  # MD5 hash (32) + '.html' (5)

    def test_download_page_success(self, scraper, mock_session, mock_response):
        """Test successful page download."""
        mock_session.get.return_value = mock_response

        result = scraper.download_page("http://example.com")

        assert result == mock_response.text
        mock_session.get.assert_called_once_with("http://example.com", timeout=30)

    def test_download_page_failure(self, scraper, mock_session):
        """Test complete download failure after retries."""
        mock_session.get.side_effect = RequestException("Connection error")

        with patch('time.sleep'), patch('random.random', return_value=0.5):
            result = scraper.download_page("http://example.com")

            assert result is None
            assert mock_session.get.call_count == scraper.max_retries

    def test_download_page_403(self, scraper, mock_session):
        """Test handling of 403 response."""
        mock_response = Mock()
        mock_response.status_code = 403
        mock_session.get.return_value = mock_response

        result = scraper.download_page("http://example.com")

        assert result is None
        mock_session.get.assert_called_once()

    def test_save_html_success(self, scraper):
        """Test successful HTML save operation."""
        html_content = "<html><body>Test</body></html>"
        filename = "test.html"

        mock_file = mock_open()
        with patch('builtins.open', mock_file):
            result = scraper.save_html(html_content, filename)

        assert result is True
        mock_file().write.assert_called_once_with(html_content)

    def test_save_html_failure(self, scraper):
        """Test HTML save operation failure."""
        html_content = "<html><body>Test</body></html>"
        filename = "test.html"
        mock_file = mock_open()
        mock_file.side_effect = IOError("Write failed")
        with patch('builtins.open', mock_file):
            result = scraper.save_html(html_content, filename)
        assert result is False

    def test_get_html_list(self, scraper):
        """Test reading HTML files from directory."""
        mock_files = {
            'file1.html': "<html>Content 1</html>",
            'file2.html': "<html>Content 2</html>"
        }

        # Mock glob to return our test files
        with patch('pathlib.Path.glob') as mock_glob:
            mock_glob.return_value = [Path(f) for f in mock_files.keys()]

            # Mock file reading
            mock_file = mock_open(read_data="<html>Content</html>")
            with patch('builtins.open', mock_file):
                result = scraper.get_html_list()

                assert len(result) == 2
                assert all(isinstance(r, tuple) for r in result)
                assert all(r[0].endswith('.html') for r in result)

    def test_post_process(self, scraper):
        """Test post-processing of HTML files."""
        mock_processor = Mock(return_value=42)
        mock_files = [('file1.html', "<html>Content 1</html>"),
                      ('file2.html', "<html>Content 2</html>")]

        with patch.object(scraper, 'get_html_list', return_value=mock_files):
            results = scraper.post_process(mock_processor)

            assert len(results) == 2
            assert all(r == 42 for r in results)
            assert mock_processor.call_count == 2

    def test_download_page_ssl_error_retry(self, scraper):
        """Test SSL error handling with retry."""
        with patch('requests.Session.get') as mock_get:
            # First call raises SSL error
            mock_get.side_effect = [
                requests.exceptions.SSLError("certificate verify failed"),
                Mock(text="<html>Success</html>")  # Second call succeeds
            ]

            result = scraper.download_page("https://example.com")
            assert result == "<html>Success</html>"
            assert mock_get.call_count == 2

            # Verify the second call was made without SSL verification
            assert mock_get.call_args_list[1][1]['verify'] is False

    def test_download_page_403_handling(self, scraper):
        """Test handling of 403 Forbidden response."""
        mock_response = Mock()
        mock_response.status_code = 403

        with patch('requests.Session.get', return_value=mock_response):
            result = scraper.download_page("https://example.com")
            assert result is None

    def test_download_page_remote_disconnected(self, scraper):
        """Test handling of RemoteDisconnected error."""
        with patch('requests.Session.get') as mock_get:
            mock_get.side_effect = requests.exceptions.ConnectionError(
                "RemoteDisconnected('Remote end closed connection without response')"
            )
            with patch('time.sleep'):  # Don't actually sleep in tests
                result = scraper.download_page("https://example.com")
                assert result is None

    def test_custom_headers(self):
        """Test custom headers are properly set."""
        custom_headers = {'X-Custom': 'Test'}
        expected_headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Accept-Encoding': 'gzip, deflate',
            'DNT': '1',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
            'X-Custom': 'Test'
        }

        with patch('requests.Session') as mock_session_class:
            # Create mock session and headers
            session = Mock()
            headers = Mock()
            session.headers = headers
            mock_session_class.return_value = session

            scraper = RequestScraper(custom_headers=custom_headers)
            test_session = scraper.create_session()

            # Verify headers were updated with expected values
            headers.update.assert_called_once()
            actual_headers = headers.update.call_args[0][0]
            assert actual_headers == expected_headers

    def test_custom_headers_alternative(self):
        """Test custom headers are properly set (alternative simpler approach)."""
        custom_headers = {'X-Custom': 'Test'}

        with patch('requests.Session') as mock_session_class:
            session = Mock()
            mock_session_class.return_value = session

            scraper = RequestScraper(custom_headers=custom_headers)
            test_session = scraper.create_session()

            # Just verify the session was created and headers were updated with our custom header
            session.headers.update.assert_called()
            assert custom_headers.items() <= session.headers.update.call_args[0][0].items()

    def test_exponential_backoff(self):
        """Test backoff calculation."""
        scraper = RequestScraper(min_wait=1.0, max_wait=16.0)

        with patch('random.random', return_value=0.5):  # Fix random for predictable results
            # Test first attempt
            wait_time = scraper.exponential_backoff(0)
            assert wait_time == 1.0  # No jitter when random is 0.5

            # Test max wait time
            wait_time = scraper.exponential_backoff(10)
            assert wait_time == 16.0  # Should be capped at max_wait

    def test_ssl_error_retry(self, scraper, mock_session, mock_response):
        """Test SSL error handling with retry without verification."""
        mock_session.get.side_effect = [
            requests.exceptions.SSLError("certificate verify failed"),
            mock_response
        ]

        result = scraper.download_page("https://example.com")

        assert result == mock_response.text
        # Verify the second request was made without SSL verification
        assert mock_session.get.call_args_list[1][1]['verify'] is False

    def test_remote_disconnected(self, scraper, mock_session, mock_response):
        """Test handling of RemoteDisconnected error."""
        mock_session.get.side_effect = [
            RemoteDisconnected("Remote end closed connection without response"),
            mock_response
        ]

        with patch('time.sleep'), patch('random.random', return_value=0.5):
            result = scraper.download_page("https://example.com")

            assert result == mock_response.text
            assert mock_session.get.call_count == 2
            mock_session.close.assert_called_once()


class TestRequestScraperIntegration:
    """Integration tests for RequestScraper."""

    def test_download_and_save_workflow(self, scraper, mock_session, mock_response):
        """Test complete workflow of downloading and saving content."""
        mock_session.get.return_value = mock_response

        with patch('builtins.open', mock_open()) as mock_file:
            # Process a URL
            url = "http://example.com"
            filenames = scraper.process_urls([url])

            assert len(filenames) == 1
            assert filenames[0] is not None
            assert filenames[0].endswith('.html')

            # Verify file was written with correct content
            mock_file().write.assert_called_once_with(mock_response.text)

    def test_post_process_with_errors(self, scraper):
        """Test post-processing with some failures."""
        mock_files = [
            ('file1.html', "<html>Valid</html>"),
            ('file2.html', "<html>Also Valid</html>"),
            ('file3.html', "Invalid Content")
        ]

        def processor_func(content):
            if "Valid" in content:
                return "Processed: " + content
            raise ValueError("Invalid content")

        with patch.object(scraper, 'get_html_list', return_value=mock_files):
            results = scraper.post_process(processor_func)

            assert len(results) == 2  # Only valid files processed
            assert all("Processed" in r for r in results)
