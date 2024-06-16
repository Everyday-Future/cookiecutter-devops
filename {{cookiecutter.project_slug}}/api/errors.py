from flask import jsonify
from config import logger


class APIError(Exception):
    def __init__(self, message, status_code, payload=None):
        super().__init__()
        self.message = message
        self.status_code = status_code
        self.payload = payload

    def to_dict(self):
        rv = dict(self.payload or ())
        rv['message'] = self.message
        return rv


def handle_api_error(error):
    logger.error(f"APIError: {error.message}, Status Code: {error.status_code}")
    print('error', error.to_dict())
    response = jsonify(error.to_dict())
    response.status_code = error.status_code
    return response
