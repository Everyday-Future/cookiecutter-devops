from flask import Blueprint

bp = Blueprint('api', __name__)

from api.v1_routes import routes
