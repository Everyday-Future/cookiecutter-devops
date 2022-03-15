import datetime

from flask_httpauth import HTTPBasicAuth, HTTPTokenAuth
from api.models import db, User
from api.routes.errors import error_response

basic_auth = HTTPBasicAuth()
token_auth = HTTPTokenAuth()


@basic_auth.verify_password
def verify_password(username, password):
    user = User.query.filter_by(username=username).first()
    if user and user.check_password(password):
        return user


@basic_auth.error_handler
def basic_auth_error(status):
    return error_response(status)


@token_auth.verify_token
def verify_token(token):
    """ Verify a user for the request """
    user = User.check_token(token)
    if user is None and isinstance(token, str) and len(token) > 20:
        # TODO - tighten this up
        # Create a new user if the token wasn't found
        user = User.create_new()
        user.token = token
        user.token_expiration = datetime.datetime.utcnow() + datetime.timedelta(days=1000)
        db.session.commit()
    return user


@token_auth.error_handler
def token_auth_error(status):
    return error_response(status)
