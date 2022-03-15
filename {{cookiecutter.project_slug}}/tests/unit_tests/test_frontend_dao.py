#!/usr/bin/env python

import os
import time
import unittest
import datetime
from config import Config
from api import global_config, db
from api.daos.user import UserDAO, User
from tests.unit_tests import BaseCase


class ConfigCase(unittest.TestCase):
    """
    Ensure that the config works as expected
    """

    def test_init(self):
        self.assertEqual(type(Config()), type(global_config))

    def test_env(self):
        self.assertTrue(global_config.ALLOW_SALES)
        self.assertFalse(global_config.RECAPTCHA_ENABLED)


class LoggerCase(BaseCase):
    """
    Ensure that the logging performs correctly and parses JSON data correctly.
    The JSON parser should also be able to handle serializing the objects that will be passed to it.
    This requires the python-json-logger library.
    """

    def test_logging(self):
        self.app.logger.debug("blah")

    def test_dict_logging(self):
        self.app.logger.debug({"message": "test", "user": "ssutton"})

    def test_dt_logging(self):
        self.app.logger.debug({"message": "test", "user": "ssutton", "datetime": datetime.utcnow()})


class RoutesCase(BaseCase):
    """
    Test that all the templates and basic routes run correctly
    """

    def setUp(self):
        super(RoutesCase, self).setUp()
        self.tester = self.app.test_client(self)

    def login(self, client, username, password):
        """Login helper function"""
        return client.post('/auth/login', data=dict(
            username=username,
            password=password
        ), follow_redirects=True)

    def logout(self, client):
        """Logout helper function"""
        return client.get('/auth/logout', follow_redirects=True)

    @unittest.skip("does not work in Staging.")
    def test_login_logout(self):
        """Make sure login and logout works."""
        # Test login
        rv = self.login(self.tester, self.username, self.password)
        self.assertEqual(rv.status_code, 200)
        assert self.username.encode('utf-8') in rv.data
        # Test logout
        rv = self.logout(self.tester)
        self.assertEqual(rv.status_code, 200)
        assert self.username.encode('utf-8') not in rv.data
        # Ensure that login detects invalid username and redirects correctly
        rv = self.login(self.tester, self.username + 'x', self.password)
        self.assertEqual(rv.status_code, 200)
        assert b'Login' in rv.data
        # Ensure that login detects invalid password redirects correctly
        rv = self.login(self.tester, self.username, self.password + 'x')
        self.assertEqual(rv.status_code, 200)
        assert b'Login' in rv.data

    def test_index(self):
        """Ensure that the route loads correctly"""
        response = self.tester.get('/', content_type='html/text', follow_redirects=True)
        self.assertEqual(response.status_code, 200)

    def test_get_user_data(self):
        with self.app.test_request_context():
            self.assertTrue(isinstance(UserDAO().get_user_metadata(), dict))

    def test_robots(self):
        """Ensure that the route loads correctly"""
        response = self.tester.get('/robots.txt', content_type='html/text', follow_redirects=True)
        self.assertEqual(response.status_code, 200)

    # def test_sitemap(self):
    #     """Ensure that the route loads correctly"""
    #     response = self.tester.get('/sitemap.xml', content_type='html/text', follow_redirects=True)
    #     self.assertEqual(response.status_code, 200)
    #
    # def test_favicon(self):
    #     """Ensure that the route loads correctly"""
    #     response = self.tester.get('/favicon.ico', content_type='html/text', follow_redirects=True)
    #     self.assertEqual(response.status_code, 200)

    def test_register(self):
        """Ensure that the route loads correctly"""
        response = self.tester.get("/auth/register", content_type='html/text', follow_redirects=True)
        self.assertEqual(response.status_code, 200)

    def test_login(self):
        """Ensure that the route loads correctly"""
        response = self.tester.get("/auth/login", content_type='html/text', follow_redirects=True)
        self.assertEqual(response.status_code, 200)

    def test_logout(self):
        """Ensure that the route loads correctly"""
        response = self.tester.get("/auth/logout", content_type='html/text')
        self.assertEqual(response.status_code, 302)

    @unittest.skip("unsure of how to test this with gunicorn")
    def test_404(self):
        """Ensure that the route loads correctly"""
        response = self.tester.get("/nonexistent_route", content_type='html/text')
        self.assertEqual(response.status_code, 404)

    def test_reset_password_request(self):
        # Test password reset request form
        response = self.login(self.tester, self.username, self.password)
        self.assertEqual(response.status_code, 200)
        response = self.tester.get("/auth/reset_password_request", content_type='html/text', follow_redirects=True)
        self.assertEqual(response.status_code, 200)


class TranslateCase(unittest.TestCase):
    @unittest.expectedFailure
    def test_translate(self):
        assert False  # Localization isn't implemented yet


class UserModelCase(BaseCase):

    def test_is_authenticated(self):
        self.assertTrue(self.user.is_anon is False)
        self.assertTrue(self.user.is_authenticated())
        self.user.password_hash = None
        db.session.commit()
        self.assertFalse(self.user.is_authenticated())

    def test_password_hashing(self):
        u = User.create_new(email='susan@strong.com')
        u.set_password('cat')
        self.assertFalse(u.check_password('dog'))
        self.assertTrue(u.check_password('cat'))

    def test_reset_password_token(self):
        token = self.user.get_reset_password_token(expires_in=1)
        self.assertTrue(token is not None)
        self.assertTrue(self.user.verify_reset_password_token(token=token))
        time.sleep(2)
        self.assertFalse(self.user.verify_reset_password_token(token=token))


class APIRoutesCase(BaseCase):
    """
    Test the app/api/routes.py routes
    """

    def setUp(self):
        super(APIRoutesCase, self).setUp()
        self.tester = self.app.test_client(self)

    def test_update_stats(self):
        rv = self.tester.post('/api/update-stats', json={'new_stat': 'test',
                                                         'uid': self.user.encoded_id}, follow_redirects=True)
        self.assertEqual(rv.status_code, 200)
        self.assertFalse(rv.json['success'])


if __name__ == "__main__":
    if os.environ.get("ENV") not in ("testing", "staging"):
        raise ValueError(f"Unit tests must be run with ENV == testing or ENV == staging "
                         f"instead of {os.environ.get('ENV')}")
    # Run the tests
    unittest.main(verbosity=2, failfast=False)
