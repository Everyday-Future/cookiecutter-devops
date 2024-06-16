from flask import current_app
from core.models import global_config, get_all_table_demos
from api import global_config, ip_ban
from api.v1_routes import bp
from flask import request, jsonify
from flask_jwt_extended import (
    jwt_required, get_jwt_identity, get_jwt, create_access_token, create_refresh_token
)
from werkzeug.security import generate_password_hash, check_password_hash
from core.models import db, User, BannedToken
from api.auth import role_required
from api.daos.schemas import UserSchema


def is_scraping_request():
    """
    Determine if the request is from a scraper, which is assumed to be malicious.
    :return: True if bot, False if not
    """
    user_agent = request.user_agent.string.lower()
    bot_names = ['python-requests', 'ahc', 'scrapy', 'catexplorador', 'cfnetwork',
                 'go-http-client', 'masscan', 'nmap', 'curl', 'wget', 'libfetch', 'aiohttp', 'urllib', 'fasthttp']
    print('scraping', user_agent)
    is_bot_req = any([bn in user_agent for bn in bot_names])
    is_banned = ip_ban.test_pattern_blocklist(url=request.url, ip=ip_ban.get_ip())
    if is_bot_req or is_banned:
        current_app.logger.warning(f'potentially malicious bot request: is_bot_req={is_bot_req}, is_banned={is_banned},'
                                   f' user_agent={user_agent}, request_url={request.url}, ip={ip_ban.get_ip()}')
    return is_bot_req or is_banned


def is_bot_request():
    """
    Determine if the request is from a bot or not. A bot may be a scraper or a harmless crawler.
    :return: True if bot, False if not
    """
    user_agent = request.user_agent.string.lower()
    bot_names = ['bot', 'googlestackdrivermonitoring', 'twitterbot', 'facebookexternal', 'bing', 'panscient.com',
                 'crawler', 'domtestcontaineragent', 'facebookexternalhit', 'semrush', 'google', 'webtech', 'axios']
    return any([bn in user_agent for bn in bot_names]) or is_scraping_request()


@bp.route('/is_bot')
@bp.route('/is-bot')
def is_bot():
    return str(is_bot_request())


@bp.route('/debug', methods=['GET', 'POST'])
def debug():
    """ Load all the debugging data for prototyping. """
    if current_app.config['ENV'] != 'production':
        get_all_table_demos(debug_mode=True)
    return jsonify({'success': True})


@bp.route('/', methods=['GET', 'POST'])
@bp.route('/ping', methods=['GET', 'POST'])
def ping():
    """
    Update stats about page load times for the user
    :return:
    """
    return {'version': global_config.VERSION, 'success': True, **global_config.SERVER_DICT}


@bp.route('/raise-exception', methods=['GET'])
def raise_exception():
    raise Exception("This is a test exception")


user_schema = UserSchema()


@bp.route('/register', methods=['POST'])
def register():
    """
    Register a new user.
    ---
    tags:
      - Authentication
    parameters:
      - name: body
        in: body
        required: true
        schema:
          id: User
          required:
            - username
            - password
            - email
            - role
          properties:
            username:
              type: string
            password:
              type: string
            email:
              type: string
            role:
              type: string
              enum: [user, admin]
    responses:
      201:
        description: User registered successfully
      400:
        description: Invalid input
    """
    data = request.get_json()
    errors = user_schema.validate(data)
    if errors:
        return jsonify(errors), 400
    hashed_password = generate_password_hash(data['password'])
    new_user = User.create_new(username=data['username'],
                               role=data['role'],
                               password_hash=hashed_password,
                               email=data['email'])
    db.session.add(new_user)
    db.session.commit()
    return jsonify({'message': 'User registered successfully'}), 201


@bp.route('/login', methods=['POST'])
def login():
    """
    Login a user.
    ---
    tags:
      - Authentication
    parameters:
      - name: body
        in: body
        required: true
        schema:
          id: UserLogin
          required:
            - username
            - password
          properties:
            username:
              type: string
            password:
              type: string
    responses:
      200:
        description: Login successful
        schema:
          type: object
          properties:
            access_token:
              type: string
            refresh_token:
              type: string
      401:
        description: Invalid credentials
      400:
        description: Invalid input
    """
    data = request.get_json()
    errors = user_schema.validate(data, partial=('email', 'role'))
    if errors:
        return jsonify(errors), 400
    user = User.query.filter_by(username=data['username']).first()
    if not user or not check_password_hash(user.password_hash, data['password']):
        return jsonify({'message': 'Invalid credentials'}), 401
    access_token = create_access_token(identity=user.id)
    new_refresh_token = create_refresh_token(identity=user.id)
    return jsonify(access_token=access_token, refresh_token=new_refresh_token), 200


@bp.route('/admin', methods=['GET'])
@jwt_required()
@role_required('admin')
def admin_only_route():
    """
    Admin-only route.
    ---
    tags:
      - Admin
    responses:
      200:
        description: Welcome, admin
      403:
        description: You do not have access to this resource
    """
    return jsonify({'message': 'Welcome, admin'}), 200


@bp.route('/logout', methods=['POST'])
@jwt_required()
def logout():
    """
    Logout a user by blacklisting their JWT.
    ---
    tags:
      - Authentication
    responses:
      200:
        description: Successfully logged out
    """
    jti = get_jwt()['jti']
    BannedToken.create_new(jti=jti)
    return jsonify({"msg": "Successfully logged out"}), 200


@bp.route('/refresh', methods=['POST'])
@jwt_required(refresh=True)
def refresh_token():
    """
    Refresh access token using a refresh token.
    ---
    tags:
      - Authentication
    responses:
      200:
        description: Token refreshed successfully
        schema:
          type: object
          properties:
            access_token:
              type: string
    """
    user_id = get_jwt_identity()
    new_access_token = create_access_token(identity=user_id)
    return jsonify(access_token=new_access_token), 200


@bp.route('/user', methods=['GET'])
@jwt_required()
def get_user():
    user_id = get_jwt_identity()
    user = User.query.get(user_id)
    if not user:
        return jsonify({'message': 'User not found'}), 403
    user_data = {'username': user.username, 'email': user.email}
    return jsonify(user_data), 200


@bp.route('/admin/roles', methods=['POST'])
@jwt_required()
@role_required('admin')
def update_user_role():
    data = request.get_json()
    user = User.query.filter_by(username=data['username']).first()
    if user:
        user.role = data['role']
        db.session.commit()
        return jsonify({'message': 'User role updated'}), 200
    return jsonify({'message': 'User not found'}), 404
