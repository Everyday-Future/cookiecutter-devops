from flask import Blueprint

bp = Blueprint('api', __name__)

from api.routes import errors, routes
