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
from tests.fixtures import BrowserController, retry_config, server_url
from tests.fixtures import AcceptanceBaseCase as BaseCase
from config import Config


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
        screenshot_dir = Config.SCREENSHOT_DIR
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
        screenshot_dir = Config.SCREENSHOT_DIR
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
            if Config.DO_SCREENSHOTS is True:
                # Render full screenshots of every page if running advanced tests
                BrowserController.get_screenshot(self.driver, fname=route_name + '.png')
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


if __name__ == '__main__':
    unittest.main(verbosity=2, failfast=True)
