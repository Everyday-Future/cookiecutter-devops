import os
import time
import random
import unittest
import logging
import warnings
import sqlalchemy
from selenium import webdriver
from selenium.webdriver import DesiredCapabilities
from selenium.webdriver.chrome.options import Options as ChromeOptions
from selenium.webdriver.common.by import By
from selenium.common.exceptions import ElementNotInteractableException, ElementClickInterceptedException, \
    WebDriverException, NoSuchElementException, TimeoutException, UnexpectedAlertPresentException, \
    StaleElementReferenceException
from config import Config, logger
from core.models import db
from api import create_app


run_headless = Config.TEST_HEADLESS
server_url = Config.SERVER_URL
if server_url.endswith('/'):
    server_url = server_url[:-1]
frontend_url = Config.CLIENT_SERVER_URL
if frontend_url.endswith('/'):
    frontend_url = frontend_url[:-1]

# retry allows you to automatically retry tests a few times to ignore some common browser rendering glitches.
# implement with    @retry(**retry_config)
retry_config = dict(exceptions=(NoSuchElementException,
                                ElementNotInteractableException,
                                ElementClickInterceptedException,
                                UnexpectedAlertPresentException,
                                TimeoutException,
                                StaleElementReferenceException,
                                WebDriverException,
                                ValueError, AssertionError, IndexError, TypeError),
                    tries=3, delay=2.0, max_delay=None, backoff=2, jitter=0, logger=logger)


def get_webdriver_chrome(is_headless=True, remote_url=None, disable_cookies=False, disable_javascript=False):
    """
    Get an instance of the selenium chrome webdriver for browser automation and frontend testing.

    Parameters
    ----------
    is_headless : Whether to render "headless" without showing a browser window popup
    remote_url : The URL to navigate to on browser start-up
    disable_cookies : Whether to disable cookies being stored in the browser
    disable_javascript : Whether to disable javascript in the browser

    Returns
    -------
    Selenium webdriver for browser automation
    """
    chrome_options = ChromeOptions()
    if is_headless:
        chrome_options.add_argument("--headless=new")  # Runs in headless mode.
        chrome_options.add_argument('--no-sandbox')  # Bypass OS security model
        chrome_options.add_argument('--disable-gpu')  # Applicable to Windows OS only
        chrome_options.add_argument("--window-size=1920,1080")
        chrome_options.add_argument('--lang=en')
        chrome_options.add_argument('--disable-infobars')
        chrome_options.add_argument("--disable-extensions")
        chrome_options.add_argument("--proxy-server='direct://'")
        chrome_options.add_argument("--proxy-bypass-list=*")
        chrome_options.add_argument("--start-maximized")
        chrome_options.add_argument("--no-default-browser-check")
        chrome_options.add_argument('--allow-insecure-localhost')
        chrome_options.add_argument('--allow-running-insecure-content')
        chrome_options.add_argument('--disable-notifications')
        chrome_options.add_argument("--no-first-run")
        chrome_options.add_argument("--enable-automation")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument("--disable-browser-side-navigation")
        chrome_options.add_argument("--ignore-certificate-errors")
        chrome_options.add_argument('--mute-audio')
        chrome_options.add_argument('--force-device-scale-factor=1')
        chrome_options.add_experimental_option(
            'prefs', {
                'intl.accept_languages': 'en,en_US',
                'download.prompt_for_download': False,
                'download.default_directory': '/dev/null',
                'automatic_downloads': 2,
                'download_restrictions': 3,
                'notifications': 2,
                'media_stream': 2,
                'media_stream_mic': 2,
                'media_stream_camera': 2,
                'durable_storage': 2,
            }
        )
        if disable_cookies:
            chrome_options.add_experimental_option("prefs", {"profile.default_content_settings.cookies": 2})
        if disable_javascript:
            chrome_options.add_experimental_option("prefs", {'profile.managed_default_content_settings.javascript': 2})
        capabilities = DesiredCapabilities.CHROME.copy()
        # capabilities['acceptSslCerts'] = True
        capabilities['acceptInsecureCerts'] = True
        capabilities['goog:loggingPrefs'] = {'browser': 'ALL'}
        for key, value in capabilities.items():
            chrome_options.set_capability(key, value)
        if remote_url not in (None, 'None'):
            print(f'Loading headless remote webdriver at {remote_url}')
            driver = webdriver.Remote(command_executor=remote_url, options=chrome_options)
        else:
            print(f'Loading headless local webdriver')
            driver = webdriver.Chrome(options=chrome_options)
    else:
        print(f'Loading full local webdriver with interface')
        driver = webdriver.Chrome(options=chrome_options)
    driver.set_page_load_timeout(90)
    driver.set_script_timeout(60)
    driver.maximize_window()
    return driver


def get_webdriver(disable_cookies=False, disable_javascript=False):
    """
    Simple operation to get an instance of a browser in selenium
    Parameters
    ----------
    :param disable_cookies: Whether to disable cookies being stored in the browser
    :param disable_javascript: Whether to disable javascript in the browser

    Returns
    -------
    Selenium webdriver for browser automation
    """
    return get_webdriver_chrome(is_headless=run_headless, remote_url=Config.WEBDRIVER_URL,
                                disable_cookies=disable_cookies, disable_javascript=disable_javascript)


def create_test_app():
    warnings.simplefilter("ignore")
    new_app = create_app(Config)
    app_context = new_app.app_context()
    app_context.push()
    new_app.logger.setLevel(logging.WARNING)
    try:
        db.create_all()
    except (sqlalchemy.exc.ProgrammingError, sqlalchemy.exc.IntegrityError):
        db.session.rollback()
    db.session.commit()
    return new_app


class IntegrationBaseCase(unittest.TestCase):

    def setUp(self):
        """Set up the test driver and create test users"""
        Config.RECAPTCHA_ENABLED = False
        self.app = create_test_app()
        self.driver = get_webdriver()
        time.sleep(0.5)
        self.driver.get(server_url)
        time.sleep(0.5)
        db.session.flush()
        self.env = BrowserController(driver=self.driver, server_url=server_url)

    def tearDown(self):
        db.session.close()
        db.session.remove()
        db.get_engine(self.app).dispose()
        self.driver.quit()


class AcceptanceBaseCase(unittest.TestCase):

    def setUp(self):
        """Set up the test driver and create test users"""
        Config.RECAPTCHA_ENABLED = False
        self.driver = get_webdriver()
        self.driver.set_page_load_timeout(30)
        self.driver.get(server_url)
        self.env = BrowserController(driver=self.driver, server_url=server_url)

    def tearDown(self):
        self.driver.quit()


class BrowserController:
    """
    Wrapper for selenium webdriver for convenient automation of common tasks for this app.
    """
    def __init__(self, driver=None, server_url=None):
        self.server_url = server_url or frontend_url
        self.driver = driver or get_webdriver()
        self.driver.delete_all_cookies()
        self.timestamp = int(time.monotonic_ns())
        self.username = f"employee{self.timestamp}"
        self.email = f"misc{self.timestamp}@luminaryplanners.com"
        self.password = f"password#{random.randint(0, 99999999)}#"
        self.user = None
        self.short_delay = 0.1
        self.screenshot_errors = False

    def get(self, url):
        """
        Get a url from the target server. Specify target url same as in frontend - /route/more?param=value
        :param url: Target url to navigate to
        :type url: str
        """
        self.driver.get(self.server_url + url)
        time.sleep(1.0)

    def scroll_to(self, target):
        """ Scroll an item in the main window into view """
        self.driver.execute_script(f"window.scrollTo(0, '{target}');")

    def scroll_to_px(self, target_px=None):
        target_px = target_px or 'document.body.scrollHeight'
        self.driver.execute_script(f"window.scrollTo(0, {target_px})")

    def get_browser_logs(self):
        """ Get all the console logs from the browser """
        try:
            browser_logs = self.driver.get_log('browser')
        except (ValueError, WebDriverException) as e:
            # Some browsers does not support getting logs
            print(f"Could not get browser logs for driver {self.driver} due to exception: {e}")
            return []
        return browser_logs

    def get_screenshot(self, fname, target_width=None, height=None):
        """
        Take a screenshot of the full height of a webpage with Selenium
        Parameters
        ----------
        fname : Name of the image to be saved
        target_width : Width of the screen. Auto-sizes to bootstrap breakpoints if not specified
        height : Window height. Auto-sizes to full height if not specified.

        Returns
        -------

        """
        if fname.lower().endswith('.png'):
            fname = fname[:-4]
        if target_width is not None:
            target_widths = {str(target_width): target_width}
        else:
            target_widths = {'xs': 550, 'sm': 750, 'md': 980, 'lg': 1150, 'xl': 1920}
        for wname, width in target_widths.items():
            time.sleep(0.3)
            if height is None:
                self.driver.set_window_size(width, 8000)
                time.sleep(0.3)
                element = self.driver.find_element(By.TAG_NAME, 'body')
                height = element.size["height"]
            # Render with height + height of cookie warning
            self.driver.set_window_size(width, height + 64.8)
            time.sleep(0.3)
            self.driver.save_screenshot(os.path.join(Config.TEST_GALLERY_DIR, f'{wname}--{fname}.png'))

    def find_element_by_id(self, element_id):
        try:
            return self.driver.find_element(By.ID, element_id)
        except:
            if self.screenshot_errors is True:
                self.get_screenshot(f'find_element_failed-{time.time()}.png', target_width=1920)
            raise

    def find_elements_by_class_name(self, element_class):
        try:
            return self.driver.find_elements(By.CLASS_NAME, element_class)
        except:
            if self.screenshot_errors is True:
                self.get_screenshot(f'find_element_failed-{time.time()}.png', target_width=1920)
            raise

    def check_exists_by_id(self, element_id):
        """
        Check for an element, return True if it exists, otherwise False.
        """
        try:
            self.find_element_by_id(element_id)
        except NoSuchElementException:
            return False
        return True

    def retry_click(self, element_id, num_loops=10, delay=0.5, allow_fail=True):
        """
        Try to click on an element by ID with a tolerance for retries
        """
        for _ in range(num_loops):
            try:
                self.find_element_by_id(element_id).click()
                time.sleep(delay)
                return True
            except (NoSuchElementException,
                    ElementNotInteractableException,
                    ElementClickInterceptedException):
                time.sleep(delay)
        if allow_fail is True:
            # Raise the exception if the element still can't be found
            self.find_element_by_id(element_id).click()

    def soft_click(self, element_id, allow_fail=False):
        self.retry_click(element_id, num_loops=1, allow_fail=allow_fail)

    def get_browser_errors(self):
        """
        Checks browser for errors, returns a list of errors
        Returns
        -------
        List of log strings that represent browser-side error logs
        """
        try:
            browserlogs = self.get_browser_logs()
        except (ValueError, WebDriverException) as e:
            # Some browsers does not support getting logs
            print(f"Could not get browser logs for driver {self.driver} due to exception: {e}")
            return []
        return [entry for entry in browserlogs if entry['level'] == 'SEVERE']

    def has_browser_error(self, exception_keywords=None):
        """
        Check if the browser has thrown any javascript errors
        Parameters
        ----------
        exception_keywords : (optional) list of keyword strings to exclude from considering an error

        Returns
        -------
        True if there are any browser-side error logs, False if not
        """
        if exception_keywords is None:
            exception_keywords = ['auth0-spa-js', 'googletagmanager']
        errors = [error for error in self.get_browser_errors()
                  if not any([kwd in error['message'] for kwd in exception_keywords])]
        if len(errors) > 0:
            print('browser_errors', errors)
        return len(errors) > 0

    def login(self, next_url=None):
        # Go to the login page
        if next_url is None:
            self.driver.get(self.server_url + "/auth/login")
        else:
            self.driver.get(self.server_url + f"/auth/login?next={next_url}")
        time.sleep(0.5)
        # Fill in login form
        if 'login' not in self.driver.current_url:
            return None
        self.find_element_by_id("login-email").send_keys(self.email)
        self.find_element_by_id("login-password").send_keys(self.password)
        time.sleep(0.3)
        self.find_element_by_id("login-submit").click()
        time.sleep(1)

    def logout(self, next_url=None):
        # Go to the register page
        if next_url is None:
            self.driver.get(self.server_url + "/auth/logout")
        else:
            self.driver.get(self.server_url + f"/auth/logout?next={next_url}")
        time.sleep(0.5)
        self.find_element_by_id("logout-submit").click()
        time.sleep(1)

    def register(self, email=None, password=None, next_url=None):
        # Go to the register page
        if next_url is None:
            self.driver.get(self.server_url + "/auth/login")
        else:
            self.driver.get(self.server_url + f"/auth/login?next={next_url}")
        time.sleep(0.5)
        self.find_element_by_id('register-toggle').click()
        time.sleep(0.3)
        # Fill in registration form with test variables
        self.find_element_by_id('register-email').send_keys(self.email or email)
        self.find_element_by_id('register-password').send_keys(self.password or password)
        self.find_element_by_id('register-confirmPassword').send_keys(self.password or password)
        self.find_element_by_id('register-submit').click()
        time.sleep(1)
