from time import time
import flask
from flask import Flask, request
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_cors import CORS
from flask_talisman import Talisman
from flask_ipban import IpBan
from flask_jwt_extended import JWTManager
# manual patch since flasgger is unmaintained. All the swagger extensions are for some reason
# noinspection PyUnresolvedReferences
import core.adapters.patch_flasgger
from flasgger import Swagger
from config import Config, logger


# Extensions
sa_db = SQLAlchemy()
migrate = Migrate()
cors = CORS()
talisman = Talisman()
global_config = Config()
ip_ban = IpBan(ban_seconds=200, ban_count=global_config.IP_BAN_LIST_COUNT)
jwt = JWTManager()
swagger = Swagger()


def create_app(config_class=None):
    """
    Build a fully-configured flask app for a webserver or test
    """
    app = Flask(__name__)
    # configs
    if config_class is None:
        config_class = Config()
    app.config.from_object(config_class)
    # extensions
    sa_db.init_app(app)
    migrate.init_app(app, sa_db)
    cors.init_app(app, origins=["http://localhost:5000", "http://localhost:3000", '*'])
    jwt.init_app(app)
    swagger.init_app(app)
    if app.config["ENV"] in ("staging", "production"):
        talisman.init_app(app, content_security_policy=None)
    # routes
    from api.v1_routes import bp as api_bp
    app.register_blueprint(api_bp, url_prefix='/v1/')
    # Error handler
    from api.errors import APIError, handle_api_error
    app.register_error_handler(APIError, handle_api_error)
    # logging
    if not app.debug and not app.testing:
        for handler in logger.handlers:
            app.logger.addHandler(handler)
        app.logger.setLevel(Config.LOG_LEVEL)

    @app.before_request
    def start_timer():
        """ time all request durations in logs """
        flask.g.start_time = time()

    @app.after_request
    def log_request(response):
        """ structured logging for request information """
        user_info = {
            'user_id': flask.g.get('user_id', 'unknown'),
            'request_id': flask.g.get('request_id', 'unknown'),
            'method': request.method,
            'url': request.url,
            'status': response.status_code,
            'performance': time() - flask.g.get('start_time', time()),
            'ip': request.remote_addr,
            'user_agent': request.user_agent.string,
            'headers': {key: value for key, value in request.headers.items()
                        if key in ['User-Agent', 'X-Forwarded-For']}
        }
        logger.info('Request', extra=user_info)
        return response

    @app.errorhandler(Exception)
    def handle_exception(e):
        logger.error('Unhandled Exception', exc_info=e)
        return str(e), 500

    # JWT token blacklist check
    from core.models import BannedToken

    @jwt.token_in_blocklist_loader
    def check_if_token_in_blacklist(jwt_header, jwt_payload):
        jti = jwt_payload['jti']
        token = BannedToken.query.filter_by(jti=jti).first()
        return token is not None

    @app.teardown_appcontext
    def shutdown_session(exception=None):
        sa_db.session.remove()

    return app


# noinspection PyUnresolvedReferences
from core import models
