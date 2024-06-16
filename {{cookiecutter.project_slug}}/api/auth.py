from functools import wraps
from flask import jsonify
from flask_jwt_extended import get_jwt_identity
from core.models import User


def role_required(role):
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            user_id = get_jwt_identity()
            user = User.query.get(user_id)
            if user is None:
                return jsonify({'message': 'User not found'}), 403
            if user.role != role:
                return jsonify({'message': 'You do not have access to this resource'}), 403
            return f(*args, **kwargs)
        return decorated_function
    return decorator
