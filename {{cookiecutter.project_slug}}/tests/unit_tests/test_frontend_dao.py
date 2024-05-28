#!/usr/bin/env python

import os
import unittest
import datetime
from config import Config
from api import global_config
from tests.unit_tests import BaseCase


class ConfigCase(unittest.TestCase):
    """
    Ensure that the config works as expected
    """

    def test_init(self):
        self.assertEqual(type(Config()), type(global_config))

    def test_env(self):
        self.assertIsNotNone(global_config.VERSION)


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
        self.app.logger.debug({"message": "test", "user": "ssutton", "datetime": datetime.datetime.utcnow()})


class RoutesCase(BaseCase):
    """
    Test that all the templates and basic routes run correctly
    """

    def setUp(self):
        super(RoutesCase, self).setUp()
        self.app.config.update({
            "TESTING": True,
        })
        self.tester = self.app.test_client()

    def test_index(self):
        """Ensure that the route loads correctly"""
        response = self.tester.get('/', content_type='html/text', follow_redirects=True)
        self.assertEqual(response.status_code, 200)

    @unittest.skip("unsure of how to test this with gunicorn")
    def test_404(self):
        """Ensure that the route loads correctly"""
        response = self.tester.get("/nonexistent_route", content_type='html/text')
        self.assertEqual(response.status_code, 404)


if __name__ == "__main__":
    if os.environ.get("ENV") not in ("testing", "staging"):
        raise ValueError(f"Unit tests must be run with ENV == testing or ENV == staging "
                         f"instead of {os.environ.get('ENV')}")
    # Run the tests
    unittest.main(verbosity=2, failfast=False)
