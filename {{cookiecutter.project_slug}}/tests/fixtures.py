import os
import random
import time
import datetime
import shutil
import requests
import logging
import warnings
import unittest
import selenium.common.exceptions
import sqlalchemy.exc
from selenium import webdriver
from selenium.webdriver import DesiredCapabilities
from selenium.webdriver.chrome.options import Options
from selenium.common.exceptions import ElementNotInteractableException, ElementClickInterceptedException, \
    WebDriverException
from config import Config
from api import db, global_config, create_app, logger
from api.models import User
from api.daos.user import UserDAO


run_headless = True
server_url = global_config.SERVER_URL
publisher_url = global_config.PUBLISHER_SERVER_URL
retry_config = dict(exceptions=(selenium.common.exceptions.NoSuchElementException,
                                selenium.common.exceptions.ElementNotInteractableException,
                                selenium.common.exceptions.ElementClickInterceptedException,
                                selenium.common.exceptions.UnexpectedAlertPresentException,
                                selenium.common.exceptions.TimeoutException,
                                selenium.common.exceptions.NoAlertPresentException,
                                AssertionError,
                                IndexError,
                                TypeError),
                    tries=12, delay=0, max_delay=None, backoff=1, jitter=0, logger=logger)


def get_webdriver(is_headless=True, remote_url=None):
    """
    Get an instance of the chrome webdriver.
    :param is_headless:
    :param remote_url:
    :return:
    """
    if is_headless is True:
        chrome_options = Options()
        chrome_options.add_argument("--headless")  # Runs Chrome in headless mode.
        chrome_options.add_argument('--no-sandbox')  # Bypass OS security model
        chrome_options.add_argument('--disable-gpu')  # applicable to windows os only
        chrome_options.add_argument("--window-size=1920,1080")
        chrome_options.add_argument('--disable-infobars')
        chrome_options.add_argument("--disable-extensions")
        chrome_options.add_argument("--proxy-server='direct://'")
        chrome_options.add_argument("--proxy-bypass-list=*")
        chrome_options.add_argument("--start-maximized")
        chrome_options.add_argument("--no-default-browser-check")
        chrome_options.add_argument("--no-first-run")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument("--ignore-certificate-errors")
        capabilities = DesiredCapabilities.CHROME.copy()
        capabilities['acceptSslCerts'] = True
        capabilities['acceptInsecureCerts'] = True
        if remote_url not in (None, 'None'):
            print(f'Loading headless remote webdriver at {remote_url}')
            driver = webdriver.Remote(options=chrome_options,
                                      desired_capabilities=capabilities,
                                      command_executor=remote_url)
        else:
            print(f'Loading headless local webdriver')
            driver = webdriver.Chrome(chrome_options=chrome_options, desired_capabilities=capabilities)
    else:
        print(f'Loading full local webdriver with interface')
        driver = webdriver.Chrome()
    driver.set_page_load_timeout(90)
    driver.maximize_window()
    return driver


def get_browser_errors(driver):
    """
    Checks browser for errors, returns a list of errors
    :param driver:
    :return:
    """
    try:
        browserlogs = driver.get_log('browser')
    except (ValueError, WebDriverException) as e:
        # Some browsers does not support getting logs
        print(f"Could not get browser logs for driver {driver} due to exception: {e}")
        return []
    return [entry for entry in browserlogs if entry['level'] == 'SEVERE']


def download_file(url, test_filename):
    """
    Download a file from a url into the test_gallery
    :param url: url to download the file from
    :param test_filename: Name to save the file under. Just a filename, not a full path.
    :return:
    """
    target_file = os.path.join(Config().PROJECT_DIR, global_config.TEST_DIR + f'/{test_filename}')
    if os.path.exists(target_file):
        os.remove(target_file)
    r = requests.get(url, stream=True)
    if r.status_code == 200:
        with open(target_file, 'wb') as f:
            r.raw.decode_content = True
            shutil.copyfileobj(r.raw, f)
        return target_file


def fullpage_screenshot(driver, dirname, fname, target_width=None, height=None):
    """
    Take a screenshot of the full height of a webpage with Selenium
    :param driver:
    :param dirname: Name of the directory to save the image in
    :param fname: Name of the image to be saved
    :param target_width: Width of the screen. Auto-sizes to bootstrap breakpoints if not specified
    :param height: Window height. Auto-sizes to full height if not specified.
    :return:
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
            driver.set_window_size(width, 8000)
            time.sleep(0.3)
            element = driver.find_element_by_tag_name('body')
            height = element.size["height"]
        # Render with height + height of cookie warning
        driver.set_window_size(width, height + 64.8)
        time.sleep(0.3)
        driver.save_screenshot(os.path.join(dirname, f'{wname}--{fname}.png'))


def soft_click(element):
    """A click command that fails silently"""
    try:
        element.click()
    except:
        pass


def create_test_app():
    warnings.simplefilter("ignore")
    new_app = create_app(global_config)
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
        """Setup the test driver and create test users"""
        global_config.RECAPTCHA_ENABLED = False
        self.app = create_test_app()
        self.driver = get_webdriver(is_headless=global_config.TEST_HEADLESS and run_headless,
                                    remote_url=global_config.WEBDRIVER_URL)
        time.sleep(0.5)
        self.driver.get(server_url)
        time.sleep(0.5)
        db.session.flush()
        self.env = PreloadedEnv(driver=self.driver, server_url=server_url)
        # Set test variables for un-registered test user
        self.username = self.env.username
        self.email = self.env.email
        self.password = self.env.password
        # Set test variables for pre-registered test admin
        self.timestamp = int(time.monotonic_ns())
        self.admin_username = f"admin{self.timestamp}"
        self.admin_email = f"admin{self.timestamp}@domain.com"
        self.admin_password = "notinproduction"
        # create test admin user
        self.admin = User(email=self.admin_email)
        self.admin.set_password(self.admin_password)
        db.session.add(self.admin)
        db.session.commit()

    def tearDown(self):
        if self.env.user is None:
            users = [self.admin]
        else:
            users = [self.env.user, self.admin]
        # TODO - Populate with models that depend on User
        # for obj in (Recipe, Order, Survey, Product, Layout):
        #     for user in users:
        #         try:
        #             objs = obj.query.filter(obj.user == user.id).all()
        #         except:
        #             objs = obj.query.filter(obj.user_id == user.id).all()
        #         [db.session.delete(each_obj) for each_obj in objs]
        #         db.session.commit()
        # delete all users after dependencies are cleaned up
        for user in users:
            db.session.delete(user)
        db.session.commit()
        db.session.close()
        db.session.remove()
        db.get_engine(self.app).dispose()
        self.driver.quit()

    def register_env(self):
        """
        Associate the information in the PreloadedEnv with the already-registered admin user to skip registration.
        :return:
        """
        self.env.username = self.admin_username
        self.env.password = self.admin_password
        self.env.email = self.admin_email


class AcceptanceBaseCase(unittest.TestCase):

    def setUp(self):
        """Setup the test driver and create test users"""
        global_config.RECAPTCHA_ENABLED = False
        self.driver = get_webdriver(is_headless=global_config.TEST_HEADLESS and run_headless,
                                    remote_url=global_config.WEBDRIVER_URL)
        self.driver.set_page_load_timeout(30)
        self.driver.get(server_url)
        self.env = PreloadedEnv(driver=self.driver, server_url=server_url)
        # Set test variables for un-registered test user
        self.username = self.env.username
        self.email = self.env.email
        self.password = self.env.password
        # Set test variables for pre-registered test admin
        self.admin_timestamp = int(time.time() * 1000)
        self.admin_username = f"admin{self.admin_timestamp}"
        self.admin_email = f"admin{self.admin_timestamp}@domain.com"
        self.admin_password = f"password#{random.randint(0, 99999999)}#"

    def tearDown(self):
        self.driver.quit()

    def register_env(self):
        """
        Associate the information in the PreloadedEnv with the already-registered admin user to skip registration.
        :return:
        """
        self.env.username = self.admin_username
        self.env.password = self.admin_password
        self.env.email = self.admin_email

    def register_admin(self):
        """ Register the admin user and then logout so that login can be tested. """
        # Register the admin email instead of directly pushing it to the DB.
        self.env.register(email=self.admin_email, username=self.admin_username, password=self.admin_password)
        time.sleep(0.2)
        self.env.logout()
        time.sleep(0.2)


class PreloadedEnv:
    """
    Create a pre-loaded environment with different test users at different phases of the process.
    This allows for easy debugging and troubleshooting based on usernames for specific user stories.
    :return:
    """

    def __init__(self, driver, server_url=None):
        self.server_url = server_url or Config().SERVER_URL
        self.driver = driver
        self.timestamp = int(time.monotonic_ns())
        self.username = f"employee{self.timestamp}"
        self.email = f"misc{self.timestamp}@domain.com"
        self.password = f"password#{random.randint(0, 99999999)}#"
        self.user = None
        self.customizer_data = {}
        self.selected_layouts = []
        self.creative_packs = None
        self.use_daily = None
        self.use_prompts = None
        self.repeat_pattern = None
        self.external_pathway = None
        self.internal_pathway = None
        self.short_delay = 0.1

    def get_user(self):
        """ Try to get the currently-referenced user model if possible"""
        user = self.user
        if user is None:
            user = User.query.filter(User.username == self.username).first()
        if user is None:
            user = User.query.order_by(User.created.desc()).first()
        if user is None:
            return None, None
        user_dao = UserDAO(current_user=user)
        return user_dao.get_user()

    def has_browser_error(self):
        """ Check if the browser has thrown any javascript errors """
        errors = get_browser_errors(self.driver)
        if len(errors) > 0:
            print('browser_errors', errors)
        return len(errors) > 0

    def click_random_by_class(self, class_name, num_tries=10):
        for _ in range(num_tries):
            try:
                random.choice(self.driver.find_elements_by_class_name(class_name)).click()
                break
            except (ElementClickInterceptedException, ElementNotInteractableException):
                pass
        time.sleep(0.1)

    def goto_login(self, next_url=None):
        # Go to the login page
        if next_url is None:
            self.driver.get(self.server_url + "/auth/login")
        else:
            self.driver.get(self.server_url + f"/auth/login?next={next_url}")
        time.sleep(0.5)

    def login(self, next_url=None):
        self.goto_login(next_url=next_url)
        # Fill in login form
        if 'login' not in self.driver.current_url:
            return None
        self.driver.find_element_by_id("username").send_keys(self.username)
        self.driver.find_element_by_id("password").send_keys(self.password)
        self.driver.find_element_by_id("submit_btn").click()
        time.sleep(0.5)

    def logout(self):
        self.driver.get(self.server_url + "/auth/logout")

    def goto_register(self, next_url=None):
        # Go to the register page
        if next_url is None:
            self.driver.get(self.server_url + "/auth/register")
        else:
            self.driver.get(self.server_url + f"/auth/register?next={next_url}")
        time.sleep(0.3)

    def fill_register(self, email=None, username=None, password=None):
        time.sleep(0.5)
        if 'register' not in self.driver.current_url:
            return None
        # Fill in registration form with test variables
        self.driver.find_element_by_id("email").send_keys(email or self.email)
        self.driver.find_element_by_id("username").send_keys(username or self.username)
        self.driver.find_element_by_id("password").send_keys(password or self.password)
        self.driver.find_element_by_id("password2").send_keys(password or self.password)
        self.driver.find_element_by_id("privacy").send_keys(" ")
        self.driver.find_element_by_id("submit_btn").click()
        time.sleep(1)

    def register(self, next_url=None, email=None, username=None, password=None):
        self.goto_register(next_url=next_url)
        self.fill_register(email=email, username=username, password=password)

    def goto_get_started(self):
        self.driver.get(self.server_url + "/get-started")
        time.sleep(1)

    def scroll_to(self, target):
        self.driver.execute_script(f"window.scrollTo(0, {target});")

    def retry_click(self, element_id, num_loops=10, delay=0.5, allow_fail=True):
        """
        Try to click on an element by ID with a tolerance for retries
        """
        for _ in range(num_loops):
            try:
                self.driver.find_element_by_id(element_id).click()
                time.sleep(delay)
                return True
            except (selenium.common.exceptions.NoSuchElementException,
                    selenium.common.exceptions.ElementNotInteractableException):
                time.sleep(delay)
        if allow_fail is True:
            # Raise the exception if the element still can't be found
            self.driver.find_element_by_id(element_id).click()
