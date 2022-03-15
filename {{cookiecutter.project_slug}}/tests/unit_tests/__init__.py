

import os
import random
import datetime
import unittest
import warnings
from api import db, create_app, logging, global_config
from api.models import User


class BaseCase(unittest.TestCase):
    """
    Starting point for all cases that need a prepped database
    """

    def setUp(self):
        # Create the testing structure
        warnings.simplefilter("ignore")
        self.app = create_app()
        self.app.config['WTF_CSRF_ENABLED'] = False
        self.app_context = self.app.app_context()
        self.app_context.push()
        self.app.logger.setLevel(logging.WARNING)
        db.create_all()
        self.username = f"test{random.randint(0, 9999999)}"
        self.password = global_config.SECRET_KEY
        rand_email = f"{random.randint(0, 9999999)}@{{cookiecutter.project_slug}}.com"
        self.user = User(username=self.username, email=rand_email, sign_up_date=datetime.datetime.utcnow())
        self.user.set_password(self.password)
        db.session.add(self.user)
        db.session.commit()

    def tearDown(self):
        db.session.remove()
        db.drop_all()
        self.app_context.pop()


class LocalTest(unittest.TestCase):
    """
    Ensure that the current module is imported and run correctly
    """
    def test_is_run(self):
        self.assertTrue(True)


if __name__ == "__main__":
    if os.environ.get("ENV") not in ("testing", "staging"):
        raise ValueError(f"Unit tests must be run with ENV == testing or ENV == staging "
                         f"instead of {os.environ.get('ENV')}")
    # Run the tests
    unittest.main(verbosity=2, failfast=False)
