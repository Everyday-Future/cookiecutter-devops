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
from api import global_config


class PreloadedEnvCase(BaseCase):
    """
    Ensure the basic features of the PreloadedEnv are working correctly.
    """
    @retry(**retry_config)
    def test_js_error_handling(self):
        self.driver.get(server_url + '/index')
        time.sleep(0.5)
        errors = BrowserController.get_browser_errors()
        if len(errors) > 0:
            print('browser_errors', errors)
        self.assertFalse(len(errors) > 0)
        self.driver.get(server_url + '/error')
        time.sleep(0.5)
        self.assertTrue(self.env.has_browser_error())

    def test_login(self):
        self.register_admin()
        self.register_env()
        self.env.login(next_url='index')
        self.assertIn('index', self.driver.current_url.split('?')[0])

    def test_register(self):
        self.env.register(next_url='index')
        # Assert that browser redirects to the next url when specified
        self.assertIn('index', self.driver.current_url.split('?')[0])


class BasicCase(BaseCase):

    def test_webserver_is_up(self):
        response = requests.get(server_url)
        self.assertEqual(200, response.status_code)


class RegisterCase(BaseCase):

    @retry(**retry_config)
    def test_registration_invalid_email(self):
        """
        Test that a user cannot register using an invalid email format
        and that an appropriate error message will be displayed
        """
        # Go to the register page
        self.env.goto_register()
        # Fill in registration form
        self.driver.find_element_by_id("email").send_keys("invalid_email")
        self.driver.find_element_by_id("username").send_keys(self.username + "x")
        self.driver.find_element_by_id("password").send_keys(self.password)
        self.driver.find_element_by_id("password2").send_keys(self.password)
        self.driver.find_element_by_id("privacy").send_keys(" ")
        self.driver.find_element_by_id("submit_btn").click()
        time.sleep(2)
        # Assert error message is shown
        error_message = self.driver.find_element_by_class_name("form-error").text
        self.assertIn("Invalid email address", error_message)

    @retry(**retry_config)
    def test_registration_confirm_password(self):
        """
        Test that an appropriate error message is displayed when the password
        and confirm_password fields do not match
        """
        # Go to the register page
        self.env.goto_register()
        time.sleep(1)
        # Fill in registration form
        self.driver.find_element_by_id("email").send_keys("x" + self.email)
        self.driver.find_element_by_id("username").send_keys(self.username + "x")
        self.driver.find_element_by_id("password").send_keys(self.password)
        self.driver.find_element_by_id("password2").send_keys("password-won't-match")
        self.driver.find_element_by_id("privacy").send_keys(" ")
        self.driver.find_element_by_id("submit_btn").click()
        time.sleep(2)
        # Assert error message is shown
        error_message = self.driver.find_element_by_class_name("form-error").text
        assert "Field must be equal to password" in error_message


class LoginCase(BaseCase):

    @retry(**retry_config)
    def test_admin_login(self):
        """
        Test that an admin user can login and that they will be redirected to
        the admin homepage
        """
        self.register_admin()
        self.driver.get(server_url + "/auth/login?next=index")
        time.sleep(0.8)
        # Fill in login form
        self.driver.find_element_by_id("username").send_keys(self.admin_username)
        self.driver.find_element_by_id("password").send_keys(self.admin_password)
        self.driver.find_element_by_id("submit_btn").click()
        time.sleep(2)
        assert 'index' in self.driver.current_url

    @retry(**retry_config)
    def test_admin_login_email(self):
        """
        Test that an admin user can login and that they will be redirected to
        the admin homepage
        """
        self.driver.get(server_url + "/auth/login?next=index")
        time.sleep(0.8)
        # Fill in login form
        self.driver.find_element_by_id("username").send_keys(self.admin_email)
        self.driver.find_element_by_id("password").send_keys(self.admin_password)
        self.driver.find_element_by_id("submit_btn").click()
        time.sleep(2)
        assert 'index' in self.driver.current_url

    @retry(**retry_config)
    def test_login_invalid_email_format(self):
        """
        Test that a user cannot login using an invalid email format
        and that an appropriate error message will be displayed
        """
        self.driver.get(server_url + "/auth/login?next=index")
        time.sleep(0.8)
        # Fill in login form
        self.driver.find_element_by_id("username").send_keys("invalid")
        self.driver.find_element_by_id("password").send_keys(self.admin_password)
        self.driver.find_element_by_id("submit_btn").click()
        time.sleep(2)
        # Assert error message is shown
        error_message = self.driver.find_element_by_class_name("alert-info").text
        assert "username invalid not found" in error_message

    @retry(**retry_config)
    def test_login_wrong_username(self):
        """
        Test that a login attempt without a registration creates the right redirect
        and that an appropriate error message will be displayed
        """
        self.driver.get(server_url + "/auth/login?next=index")
        time.sleep(0.8)
        # Fill in login form
        self.driver.find_element_by_id("username").send_keys(self.username)
        self.driver.find_element_by_id("password").send_keys(self.admin_password)
        self.driver.find_element_by_id("submit_btn").click()
        time.sleep(2)
        # Assert that error message is shown
        error_message = self.driver.find_element_by_class_name("alert-info").text
        assert "register" in error_message.lower()

    @retry(**retry_config)
    def test_login_wrong_password(self):
        """
        Test that a user cannot login using the wrong password
        and that an appropriate error message will be displayed
        """
        self.register_admin()
        self.driver.get(server_url + "/auth/login?next=index")
        time.sleep(0.8)
        # Fill in login form
        self.driver.find_element_by_id("username").send_keys(self.admin_username)
        self.driver.find_element_by_id("password").send_keys("invalid")
        self.driver.find_element_by_id("submit_btn").click()
        time.sleep(2)

        # Assert that error message is shown
        error_message = self.driver.find_element_by_class_name("alert-info").text
        assert "The password entered is invalid. Please try again or reset your password." in error_message


class RoutesCase(BaseCase):

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
        self.env.register(next_url='get_started')
        time.sleep(0.3)
        # Ensure that all of these routes can load correctly and without error
        routes_list = ["index", "auth/reset_password_request"]
        self.render_routes(routes_list)
        time.sleep(0.3)
        self.render_routes(["auth/logout", "auth/register", "auth/login"])


class PasswordResetCase(BaseCase):

    def test_password_reset(self):
        """
        Test that a user can login and that they will be redirected to
        the homepage
        """
        self.driver.get(server_url + "/auth/reset_password_request")
        time.sleep(1)
        # Fill in login form
        self.driver.find_element_by_id("email").send_keys(self.admin_email)
        self.driver.find_element_by_id("submit_btn").click()
        time.sleep(2)
        assert 'unexpected error' not in self.driver.page_source


if __name__ == '__main__':
    unittest.main(verbosity=2, failfast=True)
