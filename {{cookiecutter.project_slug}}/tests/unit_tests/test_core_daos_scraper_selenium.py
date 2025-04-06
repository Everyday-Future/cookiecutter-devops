import pytest
from unittest.mock import Mock, patch, call
from selenium.common.exceptions import (
    TimeoutException,
    ElementClickInterceptedException,
    WebDriverException
)
from selenium.webdriver.common.by import By
from core.daos.scrapers.selenium import SeleniumScraper


@pytest.fixture
def selenium_scraper():
    """Fixture providing a selenium scraper instance with a temporary directory."""
    with patch('pathlib.Path.mkdir'):
        scraper = SeleniumScraper(
            "./test_output",
            headless=True,
            scroll_pause=0.1
        )
        yield scraper


@pytest.fixture
def mock_driver():
    """Fixture providing a mock Selenium driver."""
    driver = Mock()
    driver.page_source = "<html><body>Test Content</body></html>"
    driver.execute_script.return_value = 1000  # Default scroll height
    mock_elements = [Mock() for _ in range(10)]
    driver.find_elements.return_value = mock_elements
    return driver


@pytest.fixture
def mock_element():
    """Fixture providing a mock WebElement."""
    element = Mock()
    element.tag_name = "button"
    element.text = "Next Page"
    element.is_displayed.return_value = True
    element.is_enabled.return_value = True
    element.location_once_scrolled_into_view = {'x': 0, 'y': 100}
    element.size = {'height': 30, 'width': 100}
    return element


class TestSeleniumScraper:
    """Unit tests for SeleniumScraper class."""

    def test_scroll_into_view_success(self, selenium_scraper, mock_driver, mock_element):
        """Test successful scrolling element into view."""
        selenium_scraper.driver = mock_driver

        result = selenium_scraper.scroll_into_view(mock_element)

        assert result is True
        assert mock_driver.execute_script.call_count >= 1
        mock_element.is_displayed.assert_called()

    def test_scroll_into_view_hidden_element(self, selenium_scraper, mock_driver, mock_element):
        """Test scrolling with hidden element."""
        mock_element.is_displayed.return_value = False
        selenium_scraper.driver = mock_driver

        result = selenium_scraper.scroll_into_view(mock_element)

        assert result is False
        assert mock_driver.execute_script.call_count >= 1

    def test_verify_element_attributes_valid(self, selenium_scraper):
        """Test verification of valid pagination element attributes."""
        element = Mock()
        element.tag_name = "button"
        element.text = "Next Page"
        element.get_attribute.side_effect = lambda attr: {
            "aria-label": "Go to next page",
            "class": "pagination-next"
        }.get(attr)

        result = selenium_scraper._verify_element_attributes(element)
        assert result is True

    def test_verify_element_attributes_invalid(self, selenium_scraper):
        """Test verification of invalid element attributes."""
        element = Mock()
        element.tag_name = "div"
        element.text = "Random Text"
        element.get_attribute.side_effect = lambda attr: {
            "aria-label": None,
            "class": "random-class"
        }.get(attr)

        result = selenium_scraper._verify_element_attributes(element)
        assert result is False

    def test_handle_click_retry_success(self, selenium_scraper, mock_element, mock_driver):
        """Test successful click with retry."""
        selenium_scraper.driver = mock_driver
        # First attempt raises exception, second succeeds
        mock_element.click.side_effect = [ElementClickInterceptedException(), None]
        # Mock the JavaScript click to fail so we retry with regular click
        mock_driver.execute_script.side_effect = Exception("JS Click failed")

        result = selenium_scraper._handle_click_retry(mock_element)

        assert result is True
        # Verify that click was attempted twice
        assert mock_element.click.call_count == 2
        # Verify JS click was attempted
        mock_driver.execute_script.assert_called_once_with("arguments[0].click();", mock_element)

    def test_handle_click_retry_failure(self, selenium_scraper, mock_element, mock_driver):
        """Test failed click after max retries."""
        selenium_scraper.driver = mock_driver
        # Make both regular click and JS click fail
        mock_element.click.side_effect = ElementClickInterceptedException("Click intercepted")
        mock_driver.execute_script.side_effect = Exception("JS Click failed")

        with patch('time.sleep'):  # Don't actually sleep in tests
            result = selenium_scraper._handle_click_retry(mock_element, max_retries=2)

        assert result is False
        # Verify exactly two attempts were made
        assert mock_element.click.call_count == 2
        # Verify JS click was attempted for each failure
        assert mock_driver.execute_script.call_count == 2
        assert mock_element.click.call_count == 2

    def test_execute_click_invalid_command(self, selenium_scraper):
        """Test execution of invalid click command."""
        invalid_command = "Invalid.COMMAND, 'selector'"
        result = selenium_scraper.execute_click(invalid_command)
        assert result is False

    def test_execute_click_dangerous_selector(self, selenium_scraper):
        """Test execution with dangerous selector."""
        dangerous_command = "By.XPATH, '//comment()'"
        result = selenium_scraper.execute_click(dangerous_command)
        assert result is False

    def test_test_multiple_strategies_success(self, selenium_scraper, mock_element, mock_driver):
        """Test multiple click strategies with success."""
        selenium_scraper.driver = mock_driver
        mock_driver.find_element.return_value = mock_element

        commands = [
            "By.XPATH, '//button[text()=\"Next\"]'",
            "By.CSS_SELECTOR, '.pagination-next'"
        ]

        with patch.object(selenium_scraper, 'execute_click', side_effect=[False, True]):
            result = selenium_scraper.test_multiple_strategies(commands)
            assert result == commands[1]

    def test_test_multiple_strategies_all_fail(self, selenium_scraper):
        """Test multiple click strategies with all failures."""
        commands = [
            "By.XPATH, '//button[text()=\"Next\"]'",
            "By.CSS_SELECTOR, '.pagination-next'"
        ]

        with patch.object(selenium_scraper, 'execute_click', return_value=False):
            result = selenium_scraper.test_multiple_strategies(commands)
            assert result is None

    def test_parse_selenium_command_valid(self, selenium_scraper):
        """Test parsing valid Selenium command."""
        command = "By.CSS_SELECTOR, '.next-button'"
        result = selenium_scraper._parse_selenium_command(command)
        assert result == ("CSS_SELECTOR", ".next-button")

    def test_parse_selenium_command_invalid(self, selenium_scraper):
        """Test parsing invalid Selenium command."""
        command = "Invalid command format"
        result = selenium_scraper._parse_selenium_command(command)
        assert result is None

    def test_validate_selector_safe(self, selenium_scraper):
        """Test validation of safe selector."""
        assert selenium_scraper._validate_selector("CSS_SELECTOR", ".pagination-next") is True
        assert selenium_scraper._validate_selector("XPATH", "//button[@class='next']") is True

    def test_validate_selector_unsafe(self, selenium_scraper):
        """Test validation of unsafe selector."""
        assert selenium_scraper._validate_selector("XPATH", "//comment()") is False
        assert selenium_scraper._validate_selector("CSS_SELECTOR", "javascript:alert(1)") is False


class TestSeleniumCalendarScraper:
    """Unit tests for SeleniumCalendarScraper class."""

    def test_init(self):
        """Test initialization with custom parameters."""
        scraper = SeleniumScraper(
            output_dir="./test_output",
            headless=False,
            scroll_pause=2.0
        )

        assert scraper.scroll_pause == 2.0
        assert scraper.headless is False

    def test_create_driver(self, selenium_scraper):
        """Test driver creation with proper options."""
        with patch('undetected_chromedriver.Chrome') as mock_chrome:
            driver = selenium_scraper.create_driver()

            # Verify Chrome was initialized with options
            assert mock_chrome.called

            # Verify CDP command for viewport
            driver.execute_cdp_cmd.assert_called_once_with(
                'Emulation.setDeviceMetricsOverride',
                {
                    'mobile': False,
                    'width': 1920,
                    'height': 1080,
                    'deviceScaleFactor': 1,
                }
            )

    def test_scroll_to_load_dynamic_content(self, selenium_scraper, mock_driver):
        """Test scrolling behavior and element detection."""

        # Setup mock driver behavior for all possible execute_script calls
        def mock_execute_script(script):
            if "return document.body.scrollHeight" in script:
                return mock_execute_script.heights[mock_execute_script.call_count]
            return None  # For other script calls (scrollBy, etc)

        mock_execute_script.heights = [1000, 1000, 1500, 1500]
        mock_execute_script.call_count = 0
        mock_driver.execute_script = Mock(side_effect=mock_execute_script)

        # Mock find_elements to simulate new content being loaded
        mock_driver.find_elements.side_effect = [
            [Mock() for _ in range(10)],  # Initial elements
            [Mock() for _ in range(15)],  # After first scroll
            [Mock() for _ in range(20)],  # After second scroll
            [Mock() for _ in range(20)]  # No new elements
        ]

        with patch('time.sleep'), patch('random.random', return_value=0.5):
            reached_bottom, total_elements = selenium_scraper.scroll_to_load_dynamic_content(mock_driver)

            assert reached_bottom is True
            assert total_elements == 20
            assert mock_driver.execute_script.call_count > 0

    def test_download_page_success(self, selenium_scraper):
        """Test successful page download with dynamic content."""
        mock_driver = Mock()
        mock_driver.page_source = "<html><body>Dynamic Content</body></html>"
        # Set the mock driver directly on the scraper instance
        selenium_scraper.driver = mock_driver
        # Now patch the necessary methods
        with patch.object(selenium_scraper, 'create_driver', return_value=mock_driver) as mock_create:
            with patch.object(selenium_scraper, 'scroll_to_load_dynamic_content',
                              return_value=(True, 20)) as mock_scroll:
                with patch('time.sleep') as mock_sleep:
                    result = selenium_scraper.download_page("http://example.com")
                    # Assertions
                    assert result == mock_driver.page_source
                    mock_driver.get.assert_called_once_with("http://example.com")
                    # Verify create_driver wasn't called since we pre-set the driver
                    mock_create.assert_not_called()

    def test_download_page_failure(self, selenium_scraper):
        """Test page download failure handling."""
        mock_driver = Mock()
        mock_driver.get.side_effect = WebDriverException("Failed to load page")
        selenium_scraper.driver = mock_driver

        with patch.object(selenium_scraper, 'create_driver', return_value=mock_driver) as mock_create:
            with patch('time.sleep'):
                result = selenium_scraper.download_page("http://example.com")
                assert result is None
                # Verify create_driver wasn't called since we pre-set the driver
                mock_create.assert_not_called()


class TestSeleniumScraperIntegration:
    """Integration tests for SeleniumScraper."""

    def test_scroll_and_screenshot(self, selenium_scraper, mock_driver):
        """Test scrolling and taking screenshot together."""
        selenium_scraper.driver = mock_driver

        # Setup mock element for scrolling
        mock_element = Mock()
        mock_element.size = {"height": 1000}
        mock_driver.find_element.return_value = mock_element

        with patch('time.sleep'), patch('os.path.join', return_value='test.png'):
            # First scroll
            selenium_scraper.scroll_to_load_dynamic_content(mock_driver)
            # Then screenshot with specific target_width to avoid multiple width screenshots
            selenium_scraper.get_screenshot(
                'test.png',
                'http://example.com',
                target_width=1920,  # Specific width to avoid multiple screenshots
                height=1000  # Specific height
            )

        assert mock_driver.execute_script.call_count > 0
        mock_driver.save_screenshot.assert_called_once_with('test.png')
