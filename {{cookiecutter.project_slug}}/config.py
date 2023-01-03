"""

Config

App configuration for Flask.
Can also be accessed as global_config outside the Flask context.

"""

import re
import json
import os
import datetime
import logging
from dotenv import load_dotenv


__author__ = """{{ cookiecutter.full_name.replace('\"', '\\\"') }}"""
__email__ = '{{ cookiecutter.email }}'
# noinspection SpellCheckingInspection
base_key = 'tohmgs4dsfdsgsdfghsvaefev3587tyb63876bh84drtbubet'  # Simple key to be overridden in production


def parse_env_boolean(env_var):
    """
    Get a boolean value passed by an environmental variable
    :param env_var:
    :return:
    """
    if isinstance(env_var, str):
        env_var = env_var.strip()
    if env_var in (0, '0', 'false', 'False', False):
        return False
    if env_var in (1, '1', 'true', 'True', True):
        return True


def get_logger_handler():
    log_handler = logging.StreamHandler()
    # create logging formatter
    formatter = logging.Formatter(fmt='%(asctime)s - %(levelname)s - %(message)s')
    log_handler.setFormatter(formatter)
    log_handler.setLevel(os.environ.get('LOG_LEVEL', 'DEBUG'))
    return log_handler


def get_logger():
    logger = logging.getLogger('main')
    logger.addHandler(get_logger_handler())
    logger.setLevel(os.environ.get('LOG_LEVEL', 'DEBUG'))
    return logger


class Version:
    """
    Small class to manage version numbers and history
    """
    def __init__(self):
        self.version = self.get_version()

    @staticmethod
    def get_version():
        with open('config.json', 'r') as fp:
            return json.load(fp=fp)['version']

    def set_version(self, new_version):
        self.version = new_version
        with open('config.json', 'r') as fp:
            cfg = json.load(fp=fp)
        cfg['version'] = new_version
        with open('config.json', 'w') as fp:
            json.dump(cfg, fp=fp)

    @staticmethod
    def get_version_tuple(ver_str):
        # Get just the X.X.X part of a version number if it's decorated with other information.
        ver = re.findall("([0-9]+[,.]+[0-9]+[,.]+[0-9]+)", ver_str)
        if len(ver) == 0:
            raise ValueError(f"Invalid version number for current_version={ver_str}")
        else:
            ver = ver[0]
        # Do a hierarchical comparison of the values
        major, minor, patch = ver.split('.')
        return major, minor, patch

    @staticmethod
    def bump_version_patch(ver_str):
        major, minor, patch = Version.get_version_tuple(ver_str)
        patch = str(int(patch) + 1)
        return '.'.join([major, minor, patch])

    @staticmethod
    def bump_version_minor(ver_str):
        major, minor, patch = Version.get_version_tuple(ver_str)
        minor = str(int(minor) + 1)
        return '.'.join([major, minor, '0'])

    def bump(self, how='patch'):
        """
        Bump the version number for the app
        :param how: 'minor' or 'patch' for the version number column to bump.
        """
        ver_str = self.version
        if how == 'patch':
            ver_str = self.bump_version_patch(ver_str)
        elif how == 'minor':
            ver_str = self.bump_version_minor(ver_str)
        else:
            raise ValueError(f"Version.bump(how={how}) not valid. How must be 'patch' or 'minor'")
        self.set_version(ver_str)

    @staticmethod
    def version_greater_or_equal(ver, target_ver):
        """
        Check that a version number is major.minor.patch is greater than or equal to a target version number
        """
        # Do a hierarchical comparison of the values
        major, minor, patch = Version.get_version_tuple(ver)
        target_major, target_minor, target_patch = Version.get_version_tuple(target_ver)
        if int(major) > int(target_major):
            return True
        elif int(major) >= int(target_major) and int(minor) > int(target_minor):
            return True
        elif int(major) >= int(target_major) and int(minor) >= int(target_minor) and int(patch) >= int(target_patch):
            return True
        else:
            return False

    @staticmethod
    def append_history(ver_str, message):
        """
        Add a new entry to history.rst to reflect a new tagged version
        """
        new_history = f"""
{ver_str} ({datetime.datetime.utcnow().strftime('%Y-%m-%d')})
~~~~~~~~~~~~~~~~~~

* {message}

    """
        with open('history.rst', 'r') as fp:
            history = fp.read()
        history += new_history
        with open('history.rst', 'w') as fp:
            fp.write(history)


class Config(object):
    DATE_STR_FORMAT = "%Y_%m_%d-%H_%M_%S"
    DATE_STR_PRINT = "%A %B %d, %Y"
    VERSION = Version().version
    ENV = os.environ.get("ENV", "testing")
    SERVER_MODE = os.environ.get("SERVER_MODE")
    # Default to most secure configuration
    DEBUG_MODE = ENV not in ('staging', 'production')
    DEBUG = parse_env_boolean(os.environ.get('DEBUG')) or DEBUG_MODE
    TESTING = parse_env_boolean(os.environ.get('TESTING')) or DEBUG_MODE
    DEVELOPMENT = parse_env_boolean(os.environ.get('DEVELOPMENT')) or DEBUG_MODE
    # Load dotenv credentials if specified and available
    if os.path.isfile('local.env'):
        load_dotenv('local.env')
    # Google cloud configs
    PROJECT_ID = os.environ.get('PROJECT_ID')
    SECRET_ID = os.environ.get('SECRET_ID')
    SECRET_VERSION = os.environ.get('SECRET_VERSION', 'latest')
    # host and port are set prioritized by specificity. More specific variables overwrite more general ones.
    HOST = os.environ.get('HOST') or "0.0.0.0"  # Only used in Config
    PORT = os.environ.get('PORT') or "5000"
    USE_HTTPS = parse_env_boolean(os.environ.get('USE_HTTPS', True))
    http = 'https' if USE_HTTPS is True else 'http'
    SERVER_NAME = os.environ.get('SERVER_NAME')
    if SERVER_NAME is not None:
        SERVER_URL = os.environ.get('SERVER_URL') or f"{http}://{SERVER_NAME}"
    else:
        SERVER_URL = os.environ.get('SERVER_URL') or f"{http}://{HOST}:{PORT}"
    CLIENT_HOST = os.environ.get('CLIENT_HOST') or "0.0.0.0"
    CLIENT_PORT = os.environ.get('CLIENT_PORT') or "3000"
    CLIENT_SERVER_NAME = os.environ.get('CLIENT_SERVER_NAME') or f"{CLIENT_HOST}:{CLIENT_PORT}"
    CLIENT_SERVER_URL = os.environ.get('CLIENT_SERVER_URL') or f"{http}://{CLIENT_SERVER_NAME}"
    STAGING_URL = os.environ.get('STAGING_URL')
    PROD_URL = os.environ.get('PROD_URL')
    CDN = os.environ.get("CDN")
    SERVER_DICT = {
        'HOST': HOST,
        'PORT': PORT,
        'SERVER_NAME': SERVER_NAME,
        'SERVER_URL': SERVER_URL,
        'CLIENT_HOST': CLIENT_HOST,
        'CLIENT_PORT': CLIENT_PORT,
        'CLIENT_SERVER_URL': CLIENT_SERVER_URL,
        'STAGING_URL': STAGING_URL,
        'PROD_URL': PROD_URL,
        'ENV': ENV,
        'DEBUG_MODE': DEBUG_MODE,
        'DEBUG': DEBUG,
        'TESTING': TESTING,
        'DEVELOPMENT': DEVELOPMENT
    }
    print('SERVER_DICT', SERVER_DICT)
    # Simple switches
    DO_MINIFY = parse_env_boolean(os.environ.get('DO_MINIFY', False))
    SEND_FILE_MAX_AGE_DEFAULT = os.environ.get('SEND_FILE_MAX_AGE_DEFAULT', 60*60*24)
    # Testing switches
    BASIC_TESTS = parse_env_boolean(os.environ.get('BASIC_TESTS', True))
    DO_SCREENSHOTS = parse_env_boolean(os.environ.get('DO_SCREENSHOTS', False))
    TEST_HEADLESS = parse_env_boolean(os.environ.get('TEST_HEADLESS', True))
    WEBDRIVER_URL = os.environ.get('WEBDRIVER_URL', None)
    # Secrets
    SECRET_KEY = os.environ.get('SECRET_KEY') or base_key
    UID_SECRET_KEY = os.environ.get('UID_SECRET_KEY') or base_key
    SALT = os.environ.get('SALT') or base_key
    UNSUB_SALT = os.environ.get('UNSUB_SALT') or base_key
    if ENV not in ('testing', 'development') and any([key == base_key for key in (SECRET_KEY, UID_SECRET_KEY, SALT)]):
        raise ValueError('all secrets must be overridden in production')
    WTF_CSRF_TIME_LIMIT = None
    SESSION_COOKIE_SECURE = not DEBUG_MODE
    REMEMBER_COOKIE_SECURE = not DEBUG_MODE
    SESSION_COOKIE_HTTPONLY = True
    REMEMBER_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = 'Lax'
    IP_BAN_LIST_COUNT = os.environ.get('IP_BAN_LIST_COUNT', 10)
    IP_BAN_REGEX_FILE = './static/ipban/nuisance.yaml'
    POSTS_PER_PAGE = 10
    # Logging configuration
    LOG_TO_STDOUT = os.environ.get('LOG_TO_STDOUT') or True
    # Babel Translation
    LANGUAGES = ['en', 'es']
    MS_TRANSLATOR_KEY = os.environ.get('MS_TRANSLATOR_KEY')
    # Database connections set up for Postgresql
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or "postgresql://postgres:tempdev@localhost:5432/frontend"
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    # Alerting resources
    SLACK_CLIENT_ID = os.environ.get('SLACK_CLIENT_ID')
    SLACK_TOKEN = os.environ.get('SLACK_TOKEN')
    SLACK_CHANNEL = os.environ.get('SLACK_CHANNEL') or '#engineering'
    # Project organization
    PROJECT_DIR = os.path.dirname(__file__)
    STATIC_DIR = os.environ.get('STATIC_DIR') or './static/'
    DATA_DIR = os.environ.get('DATA_DIR', os.path.join(PROJECT_DIR, 'data'))
    TEMP_DIR = os.environ.get('TEMP_DIR') or os.path.join(DATA_DIR, 'temp')
    if not os.path.isdir(TEMP_DIR):
        os.makedirs(TEMP_DIR)
    TEST_PARALLEL = parse_env_boolean(os.environ.get('TEST_PARALLEL', False))
