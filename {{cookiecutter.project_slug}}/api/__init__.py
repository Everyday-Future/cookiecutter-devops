
import logging
from flask import Flask
from flask_sqlalchemy import SQLAlchemy as _BaseSQLAlchemy
from flask_migrate import Migrate
from flask_cors import CORS
from flask_talisman import Talisman
from flask_ipban import IpBan
from config import Config, get_logger_handler


# database
class SQLAlchemy(_BaseSQLAlchemy):
    def apply_pool_defaults(self, app, options):
        super(SQLAlchemy, self).apply_pool_defaults(app, options)
        options["pool_pre_ping"] = True
db = SQLAlchemy()
migrate = Migrate()
cors = CORS()
talisman = Talisman()
global_config = Config()
ip_ban = IpBan(ban_seconds=200, ban_count=global_config.IP_BAN_LIST_COUNT)
# logging
logger = logging.getLogger('frontend')


def create_app(config_class=None):
    app = Flask(__name__)
    if config_class is None:
        config_class = Config()
    app.config.from_object(config_class)
    db.init_app(app)
    migrate.init_app(app, db)
    # TODO - Refine and update when build pipeline is stable. Get from global_config
    cors.init_app(app, origins=["http://localhost:5000", "http://localhost:3000", '*'])
    if app.config["ENV"] in ("staging", "production"):
        # Secure the application and implement best practice https redirects and a content security policy
        talisman.init_app(app, content_security_policy=None)
        # ip_ban.init_app(app)
        # ip_ban.load_nuisances(global_config.IP_BAN_REGEX_FILE)
    from api.routes import bp as api_bp
    app.register_blueprint(api_bp)
    if not app.debug and not app.testing:
        app.logger.addHandler(get_logger_handler())

    @app.teardown_appcontext
    def shutdown_session(exception=None):
        db.session.remove()

    return app

from api import models
