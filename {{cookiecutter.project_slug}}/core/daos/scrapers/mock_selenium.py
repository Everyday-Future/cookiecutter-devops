# core/daos/scrapers/mock_selenium.py
from core.daos.scrapers.selenium import SeleniumScraper


class MockSeleniumScraper(SeleniumScraper):
    """
    Mock Selenium scraper that returns predefined HTML without actually using a browser.
    Used for testing calendar extraction with saved HTML files.
    """

    def __init__(self, output_dir=None, html_content=None):
        """
        Initialize mock scraper with optional predefined HTML.

        Args:
            output_dir: Directory for saving output
            html_content: Predefined HTML content to return (dict or string)
        """
        super().__init__(headless=True)
        # Initialize with minimal setup, without actual browser initialization
        self.output_dir = output_dir
        self.headless = True
        self.scroll_pause = 0.1
        self.timeout = 1
        self.driver = None
        self.html_responses = {}
        self.html_pages = {}  # For paginated responses
        self.current_url = None
        self.is_interactive_mode = False

        # Handle different types of html_content
        if isinstance(html_content, dict):
            self.html_pages = html_content  # Multiple pages with keys as identifiers
        elif html_content:
            self.html_pages = {"default": html_content}  # Single page
        else:
            self.html_pages = {"default": ""}  # Empty default

        # Current page being "viewed"
        self.current_page_key = "default"

        # Mock driver state
        self.mock_driver = MockDriver(self.html_pages.get("default", ""))

    def create_driver(self, recreate=False):
        """Mock browser creation without actually launching one"""
        if self.driver is None or recreate:
            self.driver = self.mock_driver
        return self.driver

    def download_page(self, url, num_scroll_attempts=0, **kwargs):
        """Return predefined HTML instead of downloading"""
        # Update mock driver with current HTML
        self.mock_driver.page_source = self.html_pages.get(self.current_page_key,
                                                           self.html_pages.get("default", ""))
        return self.mock_driver.page_source

    def scroll_page(self, num_attempts=5):
        """Mock scrolling behavior without actually scrolling"""
        return True  # Pretend scrolling succeeded

    def scroll_into_view(self, element):
        """Mock scroll into view without actually scrolling"""
        pass  # Do nothing

    def quit_driver(self):
        """Mock driver cleanup without actually quitting"""
        self.driver = None

    def set_response(self, url: str, html: str):
        """Set HTML response for a URL"""
        self.html_responses[url] = html

    def set_paginated_responses(self, url: str, html_pages: list):
        """Set paginated HTML responses"""
        self.html_pages[url] = html_pages
        self.is_interactive_mode = True

    def get_element_by_xpath(self, xpath):
        """Mock finding elements by XPath"""
        # In a real implementation, this would return elements from parsed HTML
        return None

    def get(self, url):
        """Mock browser navigation"""
        # If we have specific HTML for this URL, use it
        # This is a simplified approach - in real usage, you might want more
        # sophisticated URL matching
        for key, html in self.html_pages.items():
            if url in key:
                self.current_page_key = key
                self.mock_driver.page_source = html
                break
        # If no match, use default
        return self.mock_driver.page_source

    def set_current_page(self, page_key):
        """
        Set which predefined HTML page should be returned next.
        Useful for simulating pagination or navigation.
        """
        if page_key in self.html_pages:
            self.current_page_key = page_key
            self.mock_driver.page_source = self.html_pages[page_key]
        else:
            raise ValueError(f"No HTML content defined for key: {page_key}")


class MockDriver:
    """Mock of Selenium WebDriver"""

    def __init__(self, page_source=""):
        self.page_source = page_source
        self.current_url = "https://example.com/mock"

    def get(self, url):
        """Mock navigate to URL"""
        self.current_url = url
        # Page source would be updated by the MockSeleniumScraper

    def find_element(self, by, value):
        """Mock find element - returns a MockElement"""
        # In a real implementation, this would parse HTML and find elements
        return MockElement()

    def find_elements(self, by, value):
        """Mock find elements - returns a list of MockElements"""
        # In a real implementation, this would parse HTML and find elements
        return [MockElement()]

    def execute_script(self, script, *args):
        """Mock JavaScript execution"""
        return None

    def quit(self):
        """Mock quit driver"""
        pass


class MockElement:
    """Mock of Selenium WebElement"""

    def __init__(self, is_displayed=True, is_enabled=True):
        self.displayed = is_displayed
        self.enabled = is_enabled

    def click(self):
        """Mock click action"""
        pass

    def is_displayed(self):
        """Mock visibility check"""
        return self.displayed

    def is_enabled(self):
        """Mock enabled check"""
        return self.enabled

    def get_attribute(self, name):
        """Mock attribute access"""
        return ""

    def text(self):
        """Mock text access"""
        return ""
