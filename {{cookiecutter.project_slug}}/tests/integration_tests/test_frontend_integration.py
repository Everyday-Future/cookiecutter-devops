"""

Integration Tests

Ensure that the browser behaves correctly and peek into the DB to ensure that the changes are effective.
Used to test apps locally before remote deployment while the DB is still accessible.

This is the second and the last locally-executed step
in the unit_tests, integration_tests, acceptance_tests chain.

"""

import os
import time
import unittest
import requests
import warnings
import logging
import sqlalchemy.exc
from retry import retry
from tests.fixtures import BrowserController, retry_config, server_url
from tests.fixtures import AcceptanceBaseCase as BaseCase
from api import global_config, create_app, db
from core.models import User


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

    def test_login(self):
        self.register_env()
        self.env.login(next_url='index')
        self.assertIn('index', self.driver.current_url.split('?')[0])

    def test_register(self):
        user_count = User.query.count()
        self.env.register(next_url='index')
        # Assert that browser redirects to the next url when specified
        self.assertIn('index', self.driver.current_url.split('?')[0])
        # Assert that the anoymous user was assigned to the current user
        if global_config.TEST_PARALLEL is False:
            self.assertEqual(User.query.count(), user_count)
        # TODO - Assert that the user has also automatically been logged in


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
        time.sleep(1)
        assert "Field must be equal to password" in error_message


class LoginCase(BaseCase):

    @retry(**retry_config)
    def test_admin_login(self):
        """
        Test that an admin user can login and that they will be redirected to
        the admin homepage
        """
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

    @retry(**retry_config)
    def test_relogin(self):
        """
        Register the user, clear cookies, do nav, log in, and preserve data
        :return:
        """
        # Register
        self.env.register()
        self.env.logout()
        # Nav to blog
        self.driver.get(server_url + '/blog')
        time.sleep(0.5)
        # log in
        self.env.login()
        # Check that nav data was merged
        user, survey = self.env.get_user_and_survey()
        survey_data = survey.get_data()
        self.assertTrue('navigation' in survey_data.keys())


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
            source = self.driver.page_source
            out_dict[each_route] = "Page not found" not in source and "An unexpected error has occurred." not \
                                   in source and "Privacy Policy" in source
            route_name = each_route.replace('/', '-').replace(str(self.admin.get_reset_password_token()), 'token')
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
        routes_list = ["index", "auth/reset_password_request",
                       f"auth/reset_password/{self.admin.get_reset_password_token()}"]
        self.render_routes(routes_list)


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
        token = User.query.filter_by(username=self.admin_username).first().get_reset_password_token()
        self.driver.get(server_url + f'/auth/reset_password/{token}')
        assert 'unexpected error' not in self.driver.page_source


if __name__ == '__main__':
    if os.environ.get("ENV") not in ("testing", "staging", "integration"):
        raise ValueError(f"Integration tests must be run with ENV == staging or integration or testing "
                         f"instead of {os.environ.get('ENV')}")
    unittest.main(verbosity=2, failfast=False)
    # Ensure that the database is configured correctly after the testing is complete
    create_test_app()
