"""

Config

App configuration for core/api

"""
import re
import os
import json
import uuid
import datetime
import logging
from dotenv import load_dotenv
import logging.handlers
from queue import Queue
from time import time


__author__ = """{{ cookiecutter.full_name.replace('\"', '\\\"') }}"""
__email__ = '{{ cookiecutter.email }}'
_PROJECT_NAME = '{{ cookiecutter.project_slug }}'
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


class Version:
    """
    Small class to manage version numbers and history
    """
    def __init__(self):
        self.version = self.get_version()

    @staticmethod
    def get_version():
        with open(os.path.join(os.path.dirname(__file__), 'config.json'), 'r') as fp:
            return json.load(fp=fp)['version']

    def set_version(self, new_version):
        self.version = new_version
        with open(os.path.join(os.path.dirname(__file__), 'config.json'), 'r') as fp:
            cfg = json.load(fp=fp)
        cfg['version'] = new_version
        with open(os.path.join(os.path.dirname(__file__), 'config.json'), 'w') as fp:
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
    # Load dotenv credentials if specified and available
    if os.path.isfile('.env'):
        load_dotenv('.env')
    # System configs
    PROJECT_NAME = _PROJECT_NAME
    EMAIL_ADDRESS = os.environ.get('EMAIL_ADDRESS', __email__)
    LOG_LEVEL = os.environ.get("LOG_LEVEL", "DEBUG")
    DATE_STR_FORMAT = "%Y_%m_%d-%H_%M_%S"
    DATE_STR_PRINT = "%A %B %d, %Y"
    VERSION = Version().version
    ENV = os.environ.get("ENV", "testing")
    # Configured by container for logging clarity (api, host, locust, ...)
    SERVER_MODE = os.environ.get("SERVER_MODE", "debug")
    # Default to most secure configuration
    DEBUG_MODE = ENV not in ('staging', 'production')
    DEBUG = parse_env_boolean(os.environ.get('DEBUG')) or DEBUG_MODE
    TESTING = parse_env_boolean(os.environ.get('TESTING')) or DEBUG_MODE
    DEVELOPMENT = parse_env_boolean(os.environ.get('DEVELOPMENT')) or DEBUG_MODE
    # Project organization
    PROJECT_DIR = os.path.dirname(__file__)
    DATA_DIR = os.environ.get('DATA_DIR', os.path.join(PROJECT_DIR, 'data'))
    TEMP_DIR = os.environ.get('TEMP_DIR') or os.path.join(DATA_DIR, 'temp')
    TEST_ASSETS_DIR = os.environ.get('TEST_ASSETS_DIR') or os.path.join(DATA_DIR, 'test_assets')
    TEST_GALLERY_DIR = os.environ.get('TEST_GALLERY_DIR') or os.path.join(DATA_DIR, 'test_gallery')
    SCREENSHOT_DIR = os.environ.get('SCREENSHOT_DIR') or TEST_GALLERY_DIR
    RAW_DATA_DIR = os.environ.get('RAW_DATA_DIR') or os.path.join(DATA_DIR, 'raw')
    CREDS_DIR = os.environ.get('CREDS_DIR') or os.path.join(DATA_DIR, 'creds')
    INKSCAPE_DIR = os.environ.get('INKSCAPE_DIR', "inkscape.exe")
    if not os.path.isdir(TEMP_DIR):
        os.makedirs(TEMP_DIR)
    if not os.path.isdir(RAW_DATA_DIR):
        os.makedirs(RAW_DATA_DIR)
    TEST_PARALLEL = parse_env_boolean(os.environ.get('TEST_PARALLEL', False))
    # Generate a random UUID for this service/daemon
    INSTANCE_ID = str(uuid.uuid4())
    INSTANCE_WORKER = os.environ.get('INSTANCE_WORKER', '').lower()
    INSTANCE_TYPE = os.environ.get('INSTANCE_TYPE', 'cli').lower().replace(' ', '_')
    if INSTANCE_TYPE == '':
        raise ValueError("INSTANCE_TYPE must be specified for every instance of a swarm service")
    INSTANCE_START = time()
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
    SEND_FILE_MAX_AGE_DEFAULT = os.environ.get('SEND_FILE_MAX_AGE_DEFAULT', 60*60*24)
    # Testing switches
    BASIC_TESTS = parse_env_boolean(os.environ.get('BASIC_TESTS', True))
    DO_SCREENSHOTS = parse_env_boolean(os.environ.get('DO_SCREENSHOTS', False))
    TEST_HEADLESS = parse_env_boolean(os.environ.get('TEST_HEADLESS', True))
    WEBDRIVER_URL = os.environ.get('WEBDRIVER_URL', None)
    TARGET_BROWSER = os.environ.get('TARGET_BROWSER', 'chrome')
    # Secrets
    SECRET_KEY = os.environ.get('SECRET_KEY') or base_key
    UID_SECRET_KEY = os.environ.get('UID_SECRET_KEY') or base_key
    SALT = os.environ.get('SALT') or base_key
    if ENV not in ('testing', 'development') and any([key == base_key for key in (SECRET_KEY, UID_SECRET_KEY, SALT)]):
        raise ValueError('all secrets must be overridden in production')
    IP_BAN_LIST_COUNT = os.environ.get('IP_BAN_LIST_COUNT', 100)
    IP_BAN_REGEX_FILE = './data/ipban/nuisance.yaml'
    POSTS_PER_PAGE = 20
    # Logging configuration
    LOG_TO_STDOUT = os.environ.get('LOG_TO_STDOUT') or True
    # Database connections set up for Postgresql
    DEFAULT_DB = os.environ.get('DEFAULT_DB', 'postgres')
    SQLALCHEMY_DATABASE_URI = (os.environ.get('DATABASE_URL', os.environ.get('SQLALCHEMY_DATABASE_URI'))
                               or "postgresql://postgres:docker@db:5432")
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_ENGINE_OPTIONS = {
        'pool_pre_ping': True
    }
    BLOCK_WRITE_DB = os.environ.get('BLOCK_WRITE_DB', True)  # Force core.adapters.database to read-only, but not api
    # Auth credentials
    JWT_SECRET_KEY = os.getenv('JWT_SECRET_KEY')
    JWT_ACCESS_TOKEN_EXPIRES = datetime.timedelta(minutes=15)
    JWT_REFRESH_TOKEN_EXPIRES = datetime.timedelta(days=30)
    SWAGGER = {'title': 'My API', 'uiversion': 3}
    CACHE_TYPE = 'redis'
    CACHE_REDIS_URL = 'redis://localhost:6379/0'
    # Machine learning params
    MODEL_DIR = os.path.join(DATA_DIR, 'models')
    WORD2VEC_MODEL = os.environ.get('WORD2VEC_MODEL', 'glove-wiki-gigaword-300')
    SIMILARITY_MODEL = os.environ.get('SIMILARITY_MODEL', os.path.join(MODEL_DIR, WORD2VEC_MODEL))
    PCA_DIMS = int(os.environ.get('PCA_DIMS', '30'))
    PCA_MODEL = os.environ.get('PCA_MODEL', os.path.join(MODEL_DIR, f'pca_{PROJECT_NAME}_{PCA_DIMS}d.joblib'))
    # Google cloud configs
    CLOUD_PROJECT_ID = os.environ.get('PROJECT_ID', 'project_id')
    SECRET_ID = os.environ.get('SECRET_ID')
    SECRET_VERSION = os.environ.get('SECRET_VERSION', 'latest')
    # Storage resources
    AWS_ACCESS_KEY_ID = os.environ.get('AWS_ACCESS_KEY_ID')
    AWS_SECRET_ACCESS_KEY = os.environ.get('AWS_SECRET_ACCESS_KEY')
    S3_REGION = os.environ.get("S3_REGION") or "us-east-2"
    S3_BUCKET = os.environ.get("S3_BUCKET") or "develop"
    DATA_LAKEHOUSE_NAME = os.environ.get('DATA_LAKEHOUSE_NAME', 'lakehouse')
    # Redis Stack memorystore / pubsub
    REDIS_HOST = os.environ.get('REDIS_HOST', "redis-stack")
    REDIS_PORT = int(os.environ.get('REDIS_PORT', 6379))
    # Alerting resources
    SLACK_CLIENT_ID = os.environ.get('SLACK_CLIENT_ID')
    SLACK_TOKEN = os.environ.get('SLACK_TOKEN')
    SLACK_CHANNEL = os.environ.get('SLACK_CHANNEL') or '#engineering'
    # Search sources
    SERPAPI_API_KEY = os.environ.get('SERPAPI_API_KEY')
    SEMANTIC_SCHOLAR_API_KEY = os.environ.get('SEMANTIC_SCHOLAR_API_KEY')
    FACT_CHECK_API_KEY = os.environ.get('FACT_CHECK_API_KEY')
    CORE_PAPERS_API_KEY = os.environ.get('CORE_PAPERS_API_KEY')
    # Social sources
    REDDIT_CLIENT_ID = os.environ.get('REDDIT_CLIENT_ID')
    REDDIT_CLIENT_SECRET = os.environ.get('REDDIT_CLIENT_SECRET')
    REDDIT_USER_AGENT = os.environ.get('REDDIT_USER_AGENT')
    # News data sources
    MEDIASTACK_API_KEY = os.environ.get('MEDIASTACK_API_KEY')
    MEDIASTACK_API_LIMIT = os.environ.get('MEDIASTACK_API_LIMIT', 100)
    THENEWSAPI_API_KEY = os.environ.get('THENEWSAPI_API_KEY')
    THENEWSAPI_API_LIMIT = os.environ.get('THENEWSAPI_API_LIMIT', 100)
    NEWSAPI_ORG_API_KEY = os.environ.get('NEWSAPI_ORG_API_KEY')
    NEWSAPI_ORG_API_LIMIT = os.environ.get('NEWSAPI_ORG_API_LIMIT', 3)
    PROPUBLICA_API_KEY = os.environ.get('PROPUBLICA_API_KEY')
    NEWSDATA_API_KEY = os.environ.get('NEWSDATA_API_KEY')
    NEWSDATA_API_ENDPOINT = os.environ.get('NEWSDATA_API_ENDPOINT', 'https://newsdata.io/api/1/news')
    NEWSDATA_API_LIMIT = os.environ.get('NEWSDATA_API_LIMIT', 3)
    ARTICLEXTRACTOR_API_KEY = os.environ.get('ARTICLEXTRACTOR_API_KEY')
    # Finance data sources
    FRED_API_KEY = os.environ.get('FRED_API_KEY')
    POLYGON_API_KEY = os.environ.get('POLYGON_API_KEY')
    POLYGON_API_DEBUG = parse_env_boolean(os.environ.get('POLYGON_API_DEBUG', False))
    ALPHA_VANTAGE_API_KEY = os.environ.get('ALPHA_VANTAGE_API_KEY')
    # LLM Inference
    OPENAI_ORGANIZATION = os.environ.get('OPENAI_ORGANIZATION')
    OPENAI_API_KEY = os.environ.get('OPENAI_API_KEY')
    OPENAI_BASE_MODEL = os.environ.get('OPENAI_BASE_MODEL') or 'gpt-3.5-turbo'
    OPENAI_EXPERT_MODEL = os.environ.get('OPENAI_EXPERT_MODEL') or 'gpt-4-turbo-preview'
    ANTHROPIC_API_KEY = os.environ.get('ANTHROPIC_API_KEY')
    LOCAL_OLLAMA_URL = os.environ.get('LOCAL_OLLAMA_URL')  # http://localhost:11434 usually
    LOCAL_OLLAMA_IS_ACTIVE = parse_env_boolean(os.environ.get('LOCAL_OLLAMA_IS_ACTIVE', False))
    RUNPOD_API_KEY = os.environ.get('RUNPOD_API_KEY')
    ANYSCALE_API_KEY = os.environ.get('ANYSCALE_API_KEY')
    ANYSCALE_BASE_URL = os.environ.get('ANYSCALE_BASE_URL')
    DEFAULT_LLM_AGENT = os.environ.get('DEFAULT_LLM_AGENT', 'local')


class JsonFormatter(logging.Formatter):
    def format(self, record):
        log_record = {
            'timestamp': self.formatTime(record, self.datefmt),
            'level': record.levelname,
            'message': record.getMessage(),
            'user_id': getattr(record, 'user_id', 'unknown'),
            'request_id': getattr(record, 'request_id', 'unknown'),
            'module': record.module,
            'funcName': record.funcName,
            'lineno': record.lineno,
            'performance': getattr(record, 'performance', None)
        }
        return json.dumps(log_record)


def _get_logger_handler_file():
    log_handler = logging.handlers.RotatingFileHandler('app.log', maxBytes=1000000, backupCount=3)
    formatter = JsonFormatter()
    log_handler.setFormatter(formatter)
    log_handler.setLevel(os.environ.get('LOG_LEVEL', 'DEBUG'))
    return log_handler


def _get_logger_handler_stream():
    log_handler = logging.StreamHandler()
    # create logging formatter
    formatter = logging.Formatter(fmt='%(asctime)s - %(levelname)s - %(message)s')
    log_handler.setFormatter(formatter)
    log_handler.setLevel(os.environ.get('LOG_LEVEL', 'DEBUG'))
    return log_handler


def _get_logger():
    new_logger = logging.getLogger('backend')
    new_logger.setLevel(os.environ.get('LOG_LEVEL', 'DEBUG'))
    new_logger.addHandler(_get_logger_handler_file())
    new_logger.addHandler(_get_logger_handler_stream())
    return new_logger


# global logging and threading instances
logger = _get_logger()
log_queue = Queue(-1)
queue_handler = logging.handlers.QueueHandler(log_queue)
queue_listener_file = logging.handlers.QueueListener(log_queue, _get_logger_handler_file())
queue_listener_stream = logging.handlers.QueueListener(log_queue, _get_logger_handler_stream())
queue_listener_file.start()
queue_listener_stream.start()


def log_performance(func):
    def wrapper(*args, **kwargs):
        start_time = time()
        result = func(*args, **kwargs)
        duration = time() - start_time
        logger.info('Performance', extra={'performance': duration})
        return result
    return wrapper
