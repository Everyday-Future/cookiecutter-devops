import os
import datetime
import unittest
from unittest.mock import patch, MagicMock
from config import Config
from api import global_config, create_app
from config import _get_logger_handler_file, _get_logger_handler_stream, _get_logger


def test_init():
    assert type(Config()) == type(global_config)


def test_env():
    assert global_config.VERSION is not None


def test_logging():
    app = create_app()
    app.logger.debug("blah")


def test_logging_prod():
    Config.TESTING = False
    Config.DEBUG = False
    prev_env = Config.ENV
    Config.ENV = 'production'
    app = create_app()
    app.logger.debug("blah")
    Config.TESTING = True
    Config.DEBUG = True
    Config.ENV = prev_env


def test_dict_logging():
    app = create_app()
    app.logger.debug({"message": "test", "user": "ssutton"})


def test_dt_logging():
    app = create_app()
    app.logger.debug({"message": "test", "user": "ssutton", "datetime": datetime.datetime.utcnow()})


class TestLoggingSetup(unittest.TestCase):

    @patch('config.logging.handlers.RotatingFileHandler')
    def test_get_logger_handler(self, MockHandler):
        handler = _get_logger_handler_file()
        self.assertIsInstance(handler, MagicMock)

    @patch('config.logging.getLogger')
    def test_get_logger(self, MockGetLogger):
        mock_logger = MagicMock()
        MockGetLogger.return_value = mock_logger
        logger = _get_logger()
        self.assertEqual(logger, mock_logger)
        self.assertTrue(mock_logger.addHandler.called)


if __name__ == "__main__":
    if os.environ.get("ENV") not in ("testing", "staging"):
        raise ValueError(f"Unit tests must be run with ENV == testing or ENV == staging "
                         f"instead of {os.environ.get('ENV')}")
    # Run the tests
    unittest.main(verbosity=2, failfast=False)
