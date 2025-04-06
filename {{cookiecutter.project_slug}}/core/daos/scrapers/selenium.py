# core/daos/scrapers/selenium.py
import os
import re
import time
import random
import warnings
from typing import List, Optional, Tuple, Dict
from dataclasses import dataclass, field
from selenium.webdriver.remote.webelement import WebElement
from selenium.webdriver.support.ui import WebDriverWait
# noinspection PyPep8Naming
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, WebDriverException, ElementClickInterceptedException
from selenium.webdriver.common.by import By
import undetected_chromedriver as uc
from config import logger
from core.adapters.parsers import DataclassSerializerMixin


@dataclass
class PageData(DataclassSerializerMixin):
    """
    Comprehensive data structure for webpage retrieval
    """
    url: str
    html_str: Optional[str] = None
    # Cloudflare and request-related metadata
    is_cloudflare_protected: bool = False
    cloudflare_detection_results: Dict[str, bool] = field(default_factory=dict)
    # Additional metadata about the page retrieval
    headers: Dict[str, str] = field(default_factory=dict)
    status_code: Optional[int] = None
    retrieval_time: Optional[float] = None
    # Additional context and diagnostics
    error_message: Optional[str] = None

    def __post_init__(self):
        """
        Initialize Cloudflare detection results with default values
        """
        if not self.cloudflare_detection_results:
            self.cloudflare_detection_results = {
                'http_headers': False,
                'html_meta_tags': False,
                'page_source_text': False,
                'javascript_checks': False
            }


class SeleniumScraper:
    """
    Extension of PageScraper that handles dynamically loaded content and bypasses Cloudflare.
    Uses undetected-chromedriver to avoid detection.
    """
    ALLOWED_BY_METHODS = {
        'ID': By.ID,
        'XPATH': By.XPATH,
        'CSS_SELECTOR': By.CSS_SELECTOR,
        'CLASS_NAME': By.CLASS_NAME,
        'LINK_TEXT': By.LINK_TEXT,
        'PARTIAL_LINK_TEXT': By.PARTIAL_LINK_TEXT,
    }

    def __init__(self,
                 output_dir: str = None,
                 headless: bool = True,
                 scroll_pause: float = 0.3,
                 timeout: int = 2):
        """
        Initialize Selenium scraper with Cloudflare-friendly configuration.

        :param output_dir: Directory for HTML output
        :param headless: Whether to run browser in headless mode
        :param scroll_pause: Time to wait between scrolls (seconds)
        """
        self.output_dir = output_dir
        self.scroll_pause = scroll_pause
        self.headless = headless
        self.logger = logger
        self.timeout = timeout
        self.driver = None

    def __del__(self):
        if self.driver is not None:
            try:
                self.quit_driver()
            except Exception as e:
                print(f"Error closing browser: {str(e)}")

    def create_driver(self) -> uc.Chrome:
        """
        Create and configure undetected-chromedriver to bypass Cloudflare.
        """
        if self.driver is not None:
            print("skipping driver creation. Run .quit_driver() to clear the driver if you want to refresh")
        with warnings.catch_warnings():
            warnings.filterwarnings("ignore", category=ResourceWarning)
            warnings.filterwarnings("ignore", category=DeprecationWarning)
            options = uc.ChromeOptions()
            # Configure to appear more like a real browser
            options.add_argument('--disable-blink-features=AutomationControlled')
            options.add_argument('--disable-infobars')
            options.add_argument('--disable-popup-blocking')
            options.add_argument('--disable-notifications')
            options.add_argument('--disable-gpu')
            options.add_argument('--no-sandbox')
            options.add_argument('--disable-dev-shm-usage')
            # Set a realistic window size
            options.add_argument('--window-size=1920,1080')
            # Add more realistic user preferences
            options.add_experimental_option("prefs", {
                "profile.default_content_setting_values.notifications": 2,
                "profile.default_content_setting_values.media_stream_mic": 2,
                "profile.default_content_setting_values.media_stream_camera": 2,
                "profile.default_content_setting_values.geolocation": 2
            })
            if self.headless:
                options.add_argument('--headless=new')  # Use new headless mode
            # Create driver with custom options
            driver = uc.Chrome(options=options)
            # Set realistic viewport size
            driver.execute_cdp_cmd('Emulation.setDeviceMetricsOverride', {
                'mobile': False,
                'width': 1920,
                'height': 1080,
                'deviceScaleFactor': 1,
            })
            self.driver = driver
            return driver

    def quit_driver(self):
        if self.driver is not None:
            self.driver.quit()
            self.driver = None

    def scroll_to_load_dynamic_content(self, driver: uc.Chrome, num_scroll_attempts: int = 20) -> Tuple[bool, int]:
        """
        Scroll the page to trigger dynamic content loading with natural behavior.

        :param driver: Selenium WebDriver instance
        :param num_scroll_attempts: How many attempts to scroll to the bottom should we take if using Selenium
        :return: Tuple of (whether reached bottom, number of elements found)
        """
        last_height = driver.execute_script("return document.body.scrollHeight")
        scroll_attempts = 0
        elements_after = None
        while scroll_attempts < num_scroll_attempts:
            # Count elements before scrolling
            elements_before = len(driver.find_elements(By.TAG_NAME, "*"))
            # Scroll with variable speed and natural behavior
            current_scroll = 0
            target_scroll = last_height
            while current_scroll < target_scroll:
                # Random scroll amount between 100 and 300 pixels
                scroll_amount = random.randint(100, 300)
                current_scroll += scroll_amount
                # Smooth scroll with random speed
                driver.execute_script(
                    f"window.scrollBy({{top: {scroll_amount}, left: 0, behavior: 'smooth'}});"
                )
                # Random pause between scroll movements
                time.sleep(random.uniform(0.1, 0.3))
            # Add random pause after reaching bottom
            actual_pause = self.scroll_pause + (random.random() * 0.5)
            time.sleep(actual_pause)
            # Calculate new height and check for new elements
            new_height = driver.execute_script("return document.body.scrollHeight")
            elements_after = len(driver.find_elements(By.TAG_NAME, "*"))
            print(f"Scroll attempt {scroll_attempts + 1}: "
                  f"Found {elements_after - elements_before} new elements")
            if new_height == last_height and elements_after == elements_before:
                return True, elements_after
            last_height = new_height
            scroll_attempts += 1
            # Occasionally scroll up a bit to appear more natural
            if random.random() < 0.2:
                up_scroll = random.randint(100, 300)
                driver.execute_script(f"window.scrollBy(0, -{up_scroll})")
                time.sleep(random.uniform(0.1, 0.3))
        return False, elements_after

    def get_headers(self) -> Dict[str, str]:
        """
        Extract HTTP headers from current page using JavaScript

        :return: Dictionary of response headers
        """
        if self.driver is None:
            return {}

        try:
            # Use JavaScript to access response headers through the Performance API
            performance_entries = self.driver.execute_script("""
                var entries = performance.getEntriesByType('navigation');
                if (entries.length > 0 && entries[0].responseHeaders) {
                    return entries[0].responseHeaders;
                } else if (performance.getEntries) {
                    var entries = performance.getEntries();
                    for (var i = 0; i < entries.length; i++) {
                        if (entries[i].responseHeaders) {
                            return entries[i].responseHeaders;
                        }
                    }
                }
                return {};
            """)

            # Convert to dictionary format
            headers = {}
            if performance_entries and isinstance(performance_entries, dict):
                headers = performance_entries

            # Try to get additional headers through document.cookie if needed
            if not headers.get('set-cookie'):
                cookies = self.driver.execute_script("return document.cookie;")
                if cookies:
                    headers['set-cookie'] = cookies

            return headers
        except Exception as e:
            self.logger.error(f"Error extracting headers: {str(e)}")
            return {}

    def detect_cloudflare_from_content(self) -> Dict[str, bool]:
        """
        Detect Cloudflare protection using content-based methods

        :return: Dictionary of detection results
        """
        if self.driver is None:
            return {
                'html_meta_tags': False,
                'page_source_text': False,
                'javascript_checks': False
            }

        detection_results = {
            'html_meta_tags': False,
            'page_source_text': False,
            'javascript_checks': False
        }

        try:
            # Method 1: Check HTML Meta Tags
            meta_tags = self.driver.find_elements(By.TAG_NAME, 'meta')
            cloudflare_meta = any(
                'cloudflare' in (tag.get_attribute('content') or '').lower()
                for tag in meta_tags
            )
            detection_results['html_meta_tags'] = cloudflare_meta

            # Method 2: Page Source Text Check
            page_source = self.driver.page_source.lower()
            cloudflare_text_markers = [
                'cloudflare' in page_source,
                'ray id:' in page_source,
                'under attack' in page_source,
                'challenge' in page_source,
                'captcha' in page_source,
                'cf-' in page_source and ('browser' in page_source or 'challenge' in page_source)
            ]
            detection_results['page_source_text'] = any(cloudflare_text_markers)

            # Method 3: JavaScript-based Detection
            cloudflare_scripts = self.driver.find_elements(
                By.XPATH,
                "//script[contains(@src, 'cloudflare') or contains(text(), 'cloudflare') or contains(@src, 'cf.') or contains(@id, 'cf-')]"
            )
            detection_results['javascript_checks'] = len(cloudflare_scripts) > 0

            return detection_results
        except Exception as e:
            self.logger.error(f"Error during Cloudflare content detection: {e}")
            return detection_results

    def detect_cloudflare_from_headers(self, headers: Dict[str, str]) -> bool:
        """
        Detect Cloudflare protection from headers

        :param headers: HTTP response headers
        :return: True if Cloudflare is detected in headers
        """
        # Convert all header keys to lowercase for case-insensitive matching
        headers_lower = {k.lower(): v for k, v in headers.items()}

        cloudflare_headers = [
            'cf-ray' in headers_lower,
            'cf-cache-status' in headers_lower,
            'cf-connecting-ip' in headers_lower,
            'cf-worker' in headers_lower,
            'cloudflare' in headers_lower.get('server', '').lower(),
            'cloudflare' in headers_lower.get('via', '').lower(),
            'cloudflare' in headers_lower.get('x-powered-by', '').lower()
        ]

        return any(cloudflare_headers)

    def download_page_data(self, url: str, num_scroll_attempts: int = 10) -> PageData:
        """
        Download a webpage and collect comprehensive metadata including Cloudflare detection.

        :param url: URL to download
        :param num_scroll_attempts: How many attempts to scroll to the bottom
        :return: PageData object with HTML content and metadata
        """
        # Initialize result object
        page_data = PageData(url=url)
        start_time = time.time()

        try:
            if self.driver is None:
                self.create_driver()

            print(f"Accessing {url}")
            # Add random delay before accessing URL
            time.sleep(random.uniform(1, 3))

            # Load the page
            self.driver.get(url)

            # Wait for initial dynamic content
            time.sleep(5.0 + random.random())

            # Get HTTP headers and status code
            page_data.headers = self.get_headers()

            # Try to get status code (may not always be available)
            try:
                page_data.status_code = self.driver.execute_script(
                    "return window.performance.getEntries()[0].responseStatus"
                ) or 200  # Default to 200 if not available
            except:
                # If we can't get the status, assume 200 (success) if we got this far
                page_data.status_code = 200

            # Detect Cloudflare from headers
            cloudflare_in_headers = self.detect_cloudflare_from_headers(page_data.headers)
            page_data.cloudflare_detection_results['http_headers'] = cloudflare_in_headers

            # Scroll to load more content
            reached_bottom, total_elements = self.scroll_to_load_dynamic_content(
                self.driver,
                num_scroll_attempts=num_scroll_attempts
            )
            print(f"{'Reached bottom' if reached_bottom else 'Max scrolls reached'}. "
                  f"Found {total_elements} total elements.")

            # Random delay before getting final HTML
            time.sleep(random.uniform(0.1, 0.5))

            # Get the final HTML
            page_data.html_str = self.driver.page_source

            # Detect Cloudflare from content
            content_detection = self.detect_cloudflare_from_content()
            page_data.cloudflare_detection_results.update(content_detection)

            # Set overall Cloudflare protection flag
            page_data.is_cloudflare_protected = any(page_data.cloudflare_detection_results.values())

        except WebDriverException as e:
            page_data.error_message = f"Selenium error: {str(e)}"
            print(f"Selenium error for {url}: {str(e)}")
        except Exception as e:
            page_data.error_message = f"Unexpected error: {str(e)}"
            print(f"Unexpected error for {url}: {str(e)}")
        finally:
            # Calculate total retrieval time
            page_data.retrieval_time = time.time() - start_time

            # Don't quit the driver here to allow for additional operations
            # self.quit_driver()

        return page_data

    def download_page(self, url: str, num_scroll_attempts: int = 10) -> Optional[str]:
        """
        Download a webpage including dynamically loaded content.
        Now implemented as a wrapper around download_page_data.

        :param url: URL to download
        :param num_scroll_attempts: How many attempts to scroll to the bottom
        :return: The complete HTML content if successful, None if failed
        """
        page_data = self.download_page_data(url, num_scroll_attempts)

        # Clean up resources if we're just getting the HTML
        self.quit_driver()

        return page_data.html_str

    def get_screenshot(self, fname, link, out_dir=None, target_width=None, height=None):
        """
        Take a screenshot of the full height of a webpage with Selenium

        fname : Name of the image to be saved
        out_dir : (optional) screenshots_directory
        target_width : Width of the screen. Auto-sizes to bootstrap breakpoints if not specified
        height : Window height. Auto-sizes to full height if not specified.
        """
        if self.driver is None:
            self.driver = self.create_driver()
            self.driver.get(link)
        if fname.lower().endswith('.png'):
            fname = fname[:-4]
        if out_dir is None:
            out_dir = self.output_dir
        if out_dir is None:
            raise ValueError('out_dir must be specified to save screenshots')
        if target_width is not None:
            target_widths = {str(target_width): target_width}
        else:
            target_widths = {'xs': 550, 'sm': 750, 'md': 980, 'lg': 1150, 'xl': 1920}
        for w_name, width in target_widths.items():
            # Initial resize to get proper height
            self.driver.set_window_size(width, 8000)
            time.sleep(0.5)
            # Force a page reflow by accessing page dimensions
            self.driver.execute_script("return document.documentElement.clientWidth;")
            if height is None:
                element = self.driver.find_element(By.TAG_NAME, 'body')
                height = element.size["height"]
            # Final resize with correct dimensions
            self.driver.set_window_size(width, height + 64.8)
            time.sleep(1)  # Increased wait time
            # Force another reflow
            self.driver.execute_script("return document.documentElement.clientWidth;")
            # Optional: wait for any animations to complete
            time.sleep(0.2)
            self.driver.save_screenshot(os.path.join(out_dir, f'{w_name}--{fname}.png'))
        self.quit_driver()

    def scroll_into_view(self, element: WebElement, margin: int = 100) -> bool:
        """
        Scroll element into view with different strategies
        margin: pixels to add above the element when scrolling
        """
        if self.driver is None:
            self.create_driver()
        try:
            # Strategy 1: Use JavaScript scrollIntoView
            self.driver.execute_script(
                "arguments[0].scrollIntoView({behavior: 'smooth', block: 'center'});",
                element
            )
            time.sleep(0.5)  # Allow smooth scroll to complete
            # Strategy 2: Scroll by offset if needed
            location = element.location_once_scrolled_into_view
            if location:
                viewport_height = self.driver.execute_script("return window.innerHeight")
                current_scroll = self.driver.execute_script("return window.pageYOffset")
                # Check if element is actually visible in viewport
                element_top = location['y']
                element_bottom = element_top + element.size['height']
                if (element_top < current_scroll or
                        element_bottom > current_scroll + viewport_height):
                    # Add margin above element
                    scroll_to = element_top - margin
                    self.driver.execute_script(f"window.scrollTo(0, {scroll_to})")
                    time.sleep(0.5)
            # Strategy 3: Try scrolling parent elements if element still not visible
            current_element = element
            max_iterations = 3  # Prevent infinite loops
            iterations = 0
            while (not element.is_displayed() and
                   iterations < max_iterations):
                parent = self.driver.execute_script(
                    "return arguments[0].parentElement;",
                    current_element
                )
                if parent:
                    self.driver.execute_script(
                        "arguments[0].scrollIntoView({behavior: 'smooth', block: 'center'});",
                        parent
                    )
                    current_element = parent
                    iterations += 1
                    time.sleep(0.5)
                else:
                    break
            # Final verification
            return element.is_displayed()
        except Exception as e:
            self.logger.error(f"Error scrolling element into view: {str(e)}")
            return False

    def _handle_click_retry(self, element: WebElement, max_retries: int = 3) -> bool:
        """
        Handle click with retries and different strategies
        """
        driver = self.driver or self.create_driver()
        for attempt in range(max_retries):
            try:
                # Try regular click
                element.click()
                return True
            except ElementClickInterceptedException:
                # If click is intercepted, try JavaScript click
                # noinspection PyBroadException
                try:
                    driver.execute_script("arguments[0].click();", element)
                    return True
                except Exception:
                    if attempt < max_retries - 1:  # Don't sleep on last attempt
                        time.sleep(1)
                        continue
            except Exception as e:
                self.logger.error(f"Click failed on attempt {attempt + 1}: {str(e)}")
                if attempt < max_retries - 1:
                    time.sleep(1)
                    continue
        return False

    def _parse_selenium_command(self, command: str) -> Optional[Tuple[str, str]]:
        """
        Parse the Selenium command to extract the locator strategy and value
        Returns: Tuple of (strategy, value) or None if invalid
        """
        try:
            # Extract the By.X and the selector value using regex
            pattern = r'By\.([A-Z_]+),\s*["\'](.+?)["\']'
            match = re.search(pattern, command)
            if not match:
                self.logger.warning(f"Could not parse command: {command}")
                return None
            strategy, value = match.groups()
            if strategy not in self.ALLOWED_BY_METHODS:
                self.logger.warning(f"Unsupported locator strategy: {strategy}")
                return None
            return strategy, value
        except Exception as e:
            self.logger.error(f"Error parsing command: {str(e)}")
            return None

    @staticmethod
    def _validate_selector(strategy: str, value: str) -> bool:
        """
        Validate that the selector is safe and well-formed
        """
        if strategy == "XPATH":
            # Check for potentially dangerous XPath injection patterns
            dangerous_patterns = [
                "//comment()",
                "//processing-instruction",
                "ancestor::",
                "following-sibling::",
                "preceding::",
                "parent::"
            ]
            return not any(pattern in value for pattern in dangerous_patterns)
        elif strategy == "CSS_SELECTOR":
            # Check for potentially dangerous CSS selector patterns
            dangerous_patterns = [
                "<script>",
                "javascript:",
                "data:",
                "vbscript:"
            ]
            return not any(pattern in value for pattern in dangerous_patterns)
        return True

    def _find_element_safely(self, strategy: str, value: str) -> Optional[WebElement]:
        """
        Safely find an element using the parsed strategy and value
        Returns: WebElement if found, None if not found or invalid
        """
        try:
            driver = self.driver or self.create_driver()
            by_method = self.ALLOWED_BY_METHODS[strategy]
            wait = WebDriverWait(driver, self.timeout)
            element = wait.until(
                EC.presence_of_element_located((by_method, value))
            )
            # Additional validation that element is clickable
            wait.until(EC.element_to_be_clickable((by_method, value)))
            return element
        except TimeoutException:
            self.logger.warning(f"Element not found or not clickable: {strategy}={value}")
            return None
        except Exception as e:
            self.logger.error(f"Error finding element: {str(e)}")
            return None

    @staticmethod
    def _verify_element_attributes(element: WebElement) -> bool:
        """
        Verify that the found element has appropriate attributes for a next/pagination button
        """
        # Get element attributes
        tag_name = element.tag_name.lower()
        text = element.text.lower()
        aria_label = element.get_attribute("aria-label")
        class_name = element.get_attribute("class")
        # Common patterns for pagination elements
        pagination_indicators = [
            'next', 'nxt', 'load more', 'show more', 'view more', 'more results',
            'page', 'pagination', 'pager', 'pages', 'forward', 'newer', 'later',
            'infinite', 'scroll', 'load', "→", ">>"
        ]
        # Check if element matches common patterns
        has_pagination_indicator = any(
            indicator in text.lower()
            or (aria_label and indicator in aria_label.lower())
            or (class_name and indicator in class_name.lower())
            for indicator in pagination_indicators
        )
        # Verify it's a clickable element type
        valid_tags = {"button", "a", "div", "span", "li"}
        return tag_name in valid_tags and has_pagination_indicator

    def execute_click(self, command: str) -> bool:
        """
        Main method to validate and execute the Selenium click command
        Returns: True if successful, False otherwise
        """
        # Parse the command
        parsed = self._parse_selenium_command(command)
        if not parsed:
            return False
        strategy, value = parsed
        # Validate the selector
        if not self._validate_selector(strategy, value):
            self.logger.warning("Invalid or potentially dangerous selector")
            return False
        # Find the element
        element = self._find_element_safely(strategy, value)
        if not element:
            return False
        # Verify it looks like a pagination element
        if not self._verify_element_attributes(element):
            self.logger.warning("Element does not appear to be a pagination button")
            return False
        try:
            # Scroll element into view before clicking
            if not self.scroll_into_view(element):
                self.logger.warning("Failed to scroll element into view")
                return False
            # Final check that element is visible and clickable
            if not element.is_displayed() or not element.is_enabled():
                return False
            # Execute the click
            self._handle_click_retry(element=element)
            return True
        except Exception as e:
            self.logger.error(f"Error clicking element: {str(e)}")
            return False

    def test_multiple_strategies(self, commands: List[str]) -> Optional[str]:
        """
        Try multiple LLM-suggested strategies and return the first working one
        """
        for command in commands:
            if self.execute_click(command):
                return command
        return None

    def is_cloudflare_protected(self, url: Optional[str] = None) -> bool:
        """
        Check if a site is protected by Cloudflare using the PageData

        :param url: Optional URL to check. If not provided, uses current driver's URL
        :return: True if Cloudflare protection is detected, False otherwise
        """
        try:
            # If URL is provided, get fresh page data
            if url:
                current_url = url
                # Get minimal data without scrolling
                page_data = self.download_page_data(url, num_scroll_attempts=0)
                return page_data.is_cloudflare_protected

            # Otherwise use current page state
            if self.driver is None:
                return False

            current_url = self.driver.current_url

            # Get headers from current page
            headers = self.get_headers()
            headers_detection = self.detect_cloudflare_from_headers(headers)

            # Get content-based detection
            content_detection = self.detect_cloudflare_from_content()

            # Combine all detection results
            return headers_detection or any(content_detection.values())

        except Exception as e:
            self.logger.error(f"Error checking Cloudflare protection for {current_url}: {e}")
            return False

    def bypass_cloudflare(self, url: str, max_wait: int = 300) -> bool:
        """
        Attempt to bypass Cloudflare protection with human intervention option

        :param url: URL to access
        :param max_wait: Maximum time to wait for Cloudflare challenge or human intervention (in seconds)
        :return: True if successfully bypassed, False otherwise
        """
        try:
            # Create driver if not exists
            if self.driver is None:
                self.create_driver()

            # Navigate to URL
            self.driver.get(url)

            # Wait and check for Cloudflare challenge
            start_time = time.time()
            while time.time() - start_time < max_wait:
                # Check if Cloudflare is no longer detected (page loaded)
                if not self.is_cloudflare_protected():
                    return True

                # Look for specific Cloudflare challenge elements
                try:
                    # Common Cloudflare challenge selectors
                    challenge_selectors = [
                        'input[name="cf_captcha_kind"]',
                        '#cf-hcaptcha-container',
                        '.challenge-form',
                        '#cf-challenge-form',
                        '[data-testid="cf-challenge-form"]'
                    ]

                    for selector in challenge_selectors:
                        try:
                            # Wait for challenge element
                            challenge_element = WebDriverWait(self.driver, 10).until(
                                EC.presence_of_element_located((By.CSS_SELECTOR, selector))
                            )

                            # If not headless, allow human intervention
                            if not self.headless:
                                self.logger.warning(f"Cloudflare challenge detected: {selector}")
                                print("\n" + "=" * 50)
                                print("CLOUDFLARE CHALLENGE DETECTED")
                                print("=" * 50)
                                print("\nInstructions for manual bypass:")
                                print("1. Solve the Cloudflare challenge manually")
                                print("2. Wait for the page to fully load")
                                print("3. When ready, press ENTER in this console to continue")
                                print("4. If unable to solve, press 'q' and ENTER to abort")
                                print("\n" + "=" * 50)

                                # Wait for user input with timeout
                                from threading import Event
                                user_continued = Event()

                                import threading
                                def wait_for_input():
                                    user_input = input().strip().lower()
                                    if user_input == 'q':
                                        user_continued.set()
                                        return False
                                    user_continued.set()
                                    return True

                                input_thread = threading.Thread(target=wait_for_input)
                                input_thread.start()

                                # Wait for user input or timeout
                                input_thread.join(timeout=max_wait)

                                if not user_continued.is_set():
                                    print("\nTimeout reached. Aborting Cloudflare bypass.")
                                    return False

                                # Give some time for page to stabilize after manual intervention
                                time.sleep(5)

                                # Check if challenge is resolved
                                if not self.is_cloudflare_protected():
                                    return True
                            else:
                                # In headless mode, we can't solve challenges
                                self.logger.error("Cloudflare challenge detected in headless mode")
                                return False

                        except TimeoutException:
                            continue

                    # Small pause between checks
                    time.sleep(2)

                except Exception as e:
                    self.logger.error(f"Error during Cloudflare challenge detection: {e}")
                    time.sleep(2)

            # Timeout reached
            self.logger.error("Failed to bypass Cloudflare after maximum wait time")
            return False

        except Exception as e:
            self.logger.error(f"Error bypassing Cloudflare: {e}")
            return False
