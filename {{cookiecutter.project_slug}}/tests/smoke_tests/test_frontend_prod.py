"""

Acceptance Tests

Ensure that the browser behaves correctly without being able to peek into the DB.
Used to test apps deployed to GCP where the DB is no longer directly accessible.

This is the last step in the unit_tests, integration_tests, acceptance_tests chain.

"""

import os
import unittest
import time
import requests
from retry import retry
from tests.fixtures import fullpage_screenshot, server_url, retry_config, get_webdriver, PreloadedEnv
from tests.fixtures import AcceptanceBaseCase as BaseCase
from api import global_config


class PreloadedEnvCase(BaseCase):
    """
    Ensure the basic features of the PreloadedEnv are working correctly.
    """
    @retry(**retry_config)
    def test_js_error_handling(self):
        self.driver.get(server_url + '/index')
        time.sleep(0.5)
        self.assertFalse(self.env.has_browser_error())
        self.driver.get(server_url + '/error')
        time.sleep(0.5)
        self.assertTrue(self.env.has_browser_error())

    def test_planner_customizer(self):
        self.driver.get(server_url + '/customize/luminary-planner')
        time.sleep(0.5)
        self.driver.get(server_url + '/customize/luminary-planner')
        time.sleep(0.5)
        self.env.short_delay = 0.5
        self.env.fill_planner_customizer()
        self.assertIn('customize', self.driver.current_url.split('?')[0])
        # Ensure that there have been no javascript errors
        self.assertFalse(self.env.has_browser_error())


class BasicCase(BaseCase):

    @retry(**retry_config)
    def test_webserver_is_up(self):
        response = requests.get(server_url)
        self.assertEqual(200, response.status_code)


class RoutesCase(BaseCase):

    @retry(**retry_config)
    def text_exception_handling(self):
        """
        Ensure that errors are raised and handled properly.
        :return:
        """
        screenshot_dir = global_config.SCREENSHOT_DIR
        # Ensure that nonexistent pages can be detected
        self.driver.get(server_url + "/nonexistent")
        assert self.driver.page_source.contains("Page not found")
        self.driver.save_screenshot(os.path.join(screenshot_dir, '404.png'))
        self.driver.get(server_url + "/exception")
        assert self.driver.page_source.contains("An unexpected error has occurred.")
        self.driver.save_screenshot(os.path.join(screenshot_dir, '500.png'))

    def render_routes(self, routes_list):
        """
        Load a list of routes and optionally save screenshots
        :param routes_list:
        :return:
        """
        screenshot_dir = global_config.SCREENSHOT_DIR
        if not os.path.exists(screenshot_dir):
            os.makedirs(screenshot_dir, exist_ok=True)
        out_dict = {}
        for each_route in routes_list:
            self.driver.get(server_url + "/" + each_route)
            time.sleep(0.2)
            source = self.driver.page_source
            out_dict[each_route] = "Page not found" not in source and "An unexpected error has occurred." not \
                                   in source and "Privacy Policy" in source
            route_name = each_route.replace('/', '-')
            if global_config.DO_SCREENSHOTS is True:
                # Render full screenshots of every page if running advanced tests
                fullpage_screenshot(self.driver, dirname=screenshot_dir, fname=route_name + '.png')
        print('Page(s) not rendered correctly: ', [key for key, val in out_dict.items() if val is False])
        self.assertTrue(all(out_dict.values()))

    def test_all_routes(self):
        """
        Ensure that all routes are reachable and loading correctly
        :return:
        """
        self.driver.get(server_url)
        time.sleep(0.5)
        # Ensure that all of these routes can load correctly and without error
        routes_list = ["index", "auth/reset_password_request" ]
        self.render_routes(routes_list)
        time.sleep(0.3)
        self.render_routes(["auth/logout", "auth/register", "auth/login"])


@unittest.skip('These tests cant be consistently run unless recaptcha can be disabled in production temporarily')
class LoginCase(unittest.TestCase):

    def setUp(self):
        """Setup the test driver and create test users"""
        self.driver = get_webdriver(is_headless=global_config.TEST_HEADLESS, remote_url=global_config.WEBDRIVER_URL)
        self.driver.set_page_load_timeout(30)
        self.driver.get(server_url)
        self.env = PreloadedEnv(driver=self.driver, server_url=server_url)
        # Set test variables for un-registered test user
        self.username = self.env.username
        self.email = self.env.email
        self.password = self.env.password
        # Set test variables for pre-registered test admin
        self.admin_timestamp = int(time.time()*1000)
        self.admin_username = os.environ.get('ADMIN_USERNAME')
        self.admin_password = os.environ.get('ADMIN_PASSWORD')

    def tearDown(self):
        self.driver.quit()

    @retry(**retry_config)
    def test_admin_login(self):
        """
        Test that an admin user can login and that they will be redirected to
        the admin homepage
        """
        self.driver.get(server_url + "/auth/login?next=index")
        time.sleep(2.5)
        # Fill in login form
        self.driver.find_element_by_id("username").send_keys(self.admin_username)
        self.driver.find_element_by_id("password").send_keys(self.admin_password)
        self.driver.find_element_by_id("submit_btn").click()
        time.sleep(2)
        assert 'index' in self.driver.current_url


if __name__ == '__main__':
    unittest.main(verbosity=2, failfast=True)
