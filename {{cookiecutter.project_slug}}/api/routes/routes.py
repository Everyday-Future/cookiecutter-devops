
import datetime
import traceback
from flask import jsonify
from flask import current_app, request, _request_ctx_stack, abort
from core.db.models import db, global_config, get_all_table_demos, User
from core.daos.user import UserDAO
from core.daos.addresses import AddressDAO
from core.daos.contacts import ContactDAO
from core.daos.mailinglist import MailingListDAO
from api.routes.auth import token_auth
from api import global_config, logger, ip_ban
from api.routes import bp
from api.routes.errors import error_response


def is_scraping_request():
    """
    Determine if the request is from a scraper, which is assumed to be malicious.
    :return: True if bot, False if not
    """
    user_agent = _request_ctx_stack.top.request.user_agent.string.lower()
    bot_names = ('python-requests', 'ahc', 'scrapy', 'catexplorador', 'cfnetwork',
                 'go-http-client', 'masscan', 'nmap', 'curl', 'wget', 'libfetch', 'aiohttp', 'urllib', 'fasthttp')
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
    user_agent = _request_ctx_stack.top.request.user_agent.string.lower()
    bot_names = ('bot', 'googlestackdrivermonitoring', 'twitterbot', 'facebookexternal', 'bing', 'panscient.com',
                 'crawler', 'domtestcontaineragent', 'facebookexternalhit', 'semrush', 'google', 'webtech', 'axios')
    return any([bn in user_agent for bn in bot_names]) or is_scraping_request()


def get_entrypoint(request_path):
    """ Get the entrypoint url from a request path, splitting off sub-indexes and query strings """
    entrypoint = request_path.replace('/index', '').split('?')[0]
    if entrypoint == '':
        entrypoint = '/index'
    return entrypoint


def get_user_from_token(token):
    """ Process a token and find/create the User it belongs to. """
    try:
        current_user = UserDAO(token=token).user
    except ValueError:
        current_user = UserDAO.create()
        current_user.token = token
    return current_user


@bp.before_app_request
def before_request():
    """ Make the session permanent or else it will expire when the user closes their browser. """
    # Update the survey with relevant info about the user's experience
    if 'Authorization' not in request.headers:
        return None
    current_user = get_user_from_token(token=request.headers.get('Authorization').split(' ')[1])
    if isinstance(current_user, User) and is_bot_request() is False:
        current_user.updated = datetime.datetime.utcnow()
        # --- Add other user tracking data here
        db.session.commit()


@bp.route('/is_bot')
@bp.route('/is-bot')
def is_bot():
    return str(is_bot_request())


@bp.route('/debug', methods=['GET', 'POST'])
def debug():
    """ Load all of the debugging data for prototyping. """
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


@bp.route('/test_500/<error>')
def internal_error(error):
    db.session.rollback()
    logger.info(f'500 error on route={request.path}')
    tb_msg = traceback.format_exc().replace(' File "/', ' \nFile "/')
    logger.error(tb_msg)
    return error_response(500, tb_msg)


@bp.route('/users/<int:idx>', methods=['GET'])
@token_auth.login_required
def get_user(idx):
    if token_auth.current_user().id != idx:
        abort(403)
    return jsonify(token_auth.current_user().to_dict())


@bp.route('/users', methods=['GET'])
def create_user():
    if not is_bot_request():
        user = UserDAO.create()
        return jsonify({'token': user.get_token(), 'success': True})
    else:
        # TODO - return the standard bot token
        return jsonify({'token': '', 'success': True})


@bp.route('/addresses/<int:idx>', methods=['GET'])
@token_auth.login_required
def get_address(idx):
    addr = AddressDAO.get(address_id=idx)
    if token_auth.current_user().id != addr.user_id:
        abort(403)
    return jsonify(addr.to_dict())


@bp.route('/addresses', methods=['GET'])
@token_auth.login_required
def get_addresses():
    return jsonify([addr.to_dict() for addr in UserDAO(user=token_auth.current_user()).get_addresses()])


@bp.route('/addresses', methods=['POST'])
@token_auth.login_required
def create_address():
    return jsonify(AddressDAO.create(**request.get_json(force=True)).to_dict())


@bp.route('/addresses/<int:idx>', methods=['PUT'])
@token_auth.login_required
def update_address(idx):
    addr = AddressDAO.get(address_id=idx)
    if token_auth.current_user().id != addr.user_id:
        abort(403)
    addr = AddressDAO.update(address_id=idx, **request.get_json(force=True))
    return jsonify(addr.to_dict())


@bp.route('/register', methods=['POST'])
@token_auth.login_required
def register():
    """
    Register a new user
    """
    data = request.get_json(force=True)
    # If the email or password aren't specified
    if 'email' not in data.keys() or 'password' not in data.keys():
        return abort(403, 'Must specify email and password to register')
    try:
        user = UserDAO(user=token_auth.current_user()).register(email=data['email'], password=data['password'])
    except ValueError as err:
        return abort(403, err)
    return jsonify({'token': user.get_token()})


@bp.route('/login', methods=['POST'])
@token_auth.login_required
def login():
    """
    Log the user in
    """
    data = request.get_json(force=True)
    # If the email or password aren't specified
    if 'email' not in data.keys() or 'password' not in data.keys():
        return abort(403, 'Must specify email and password to register')
    try:
        user = UserDAO.login(email=data['email'], password=data['password'], current_user=token_auth.current_user())
    except ValueError as err:
        return abort(403, err)
    return jsonify({'token': user.get_token()})


@bp.route('/logout', methods=['GET', 'POST'])
@token_auth.login_required
def logout():
    """
    Log the user out
    """
    UserDAO(user=token_auth.current_user()).logout()
    return jsonify({'success': True})


@bp.route('/contact', methods=['POST'])
@token_auth.login_required
def create_contact():
    """
    Get a contact form submission
    """
    data = request.get_json(force=True)
    contact = ContactDAO.create(**data)
    return jsonify(contact.to_dict())


@bp.route('/subscribe', methods=['POST'])
@token_auth.login_required
def create_subscriber():
    """
    Sign up a new user to the mailing list
    """
    data = request.get_json(force=True)
    subscriber = MailingListDAO.subscribe(name=data['name'], email=data['email'], message=data['message'])
    return jsonify(subscriber.to_dict())


@bp.route('/unsubscribe', methods=['PUT'])
@token_auth.login_required
def unsubscribe_user():
    """
    Update a user's mailing list subscriber status
    """
    data = request.get_json(force=True)
    MailingListDAO.unsubscribe(data['email'])
    return jsonify({'success': True})
