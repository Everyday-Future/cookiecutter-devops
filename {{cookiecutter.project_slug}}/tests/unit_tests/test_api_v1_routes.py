import json
import unittest
from api import create_app
from api.errors import APIError
from unittest.mock import patch, Mock
from core.models import User, db
from werkzeug.security import generate_password_hash
from api.v1_routes.routes import is_bot_request, is_scraping_request


def test_sqlalchemy_pre_ping():
    app = create_app()
    with app.app_context():
        # Check if the pool_pre_ping option is set
        db.create_all()
        engine = db.get_engine()
        print('engine.pool._pre_ping', engine.pool._pre_ping)
        assert engine.pool._pre_ping, "The pool_pre_ping option should be enabled"


def test_index(test_client):
    """Ensure that the route loads correctly"""
    response = test_client.get('/v1/', content_type='html/text', follow_redirects=True)
    assert response.status_code == 200


def test_swagger_ui(test_client):
    response = test_client.get('/apidocs/')
    assert response.status_code == 200


@unittest.skip("unsure of how to test this with gunicorn")
def test_404(test_client):
    """Ensure that the route loads correctly"""
    response = test_client.get("/nonexistent_route", content_type='html/text')
    assert response.status_code == 404


def test_register(test_client):
    # register
    response = test_client.post('/v1/register', data=json.dumps({
        'username': 'testuser2',
        'password': 'TestPassword123',
        'email': 'test2@example.com',
        'role': 'user'
    }), content_type='application/json')
    assert response.status_code == 201
    assert response.json['message'] == 'User registered successfully'
    # attempt login
    response = test_client.post('/v1/login', data=json.dumps({
        'username': 'testuser2',
        'password': 'TestPassword123'
    }), content_type='application/json')
    assert response.status_code == 200
    assert 'access_token' in response.json
    assert 'refresh_token' in response.json
    access_token = response.json['access_token']
    # Try to access the admin route
    response = test_client.get('/v1/admin', headers={'Authorization': f'Bearer {access_token}'})
    assert response.status_code == 403
    assert response.json['message'] == 'You do not have access to this resource'


def test_logout(test_client, init_database):
    # register
    response = test_client.post('/v1/register', data=json.dumps({
        'username': 'testuser2',
        'password': 'TestPassword123',
        'email': 'test2@example.com',
        'role': 'user'
    }), content_type='application/json')
    assert response.status_code == 201
    assert response.json['message'] == 'User registered successfully'
    # attempt login
    response = test_client.post('/v1/login', data=json.dumps({
        'username': 'testuser2',
        'password': 'TestPassword123'
    }), content_type='application/json')
    assert response.status_code == 200
    assert 'access_token' in response.json
    assert 'refresh_token' in response.json
    access_token = response.json['access_token']
    response = test_client.post('/v1/logout', headers={
        'Authorization': f'Bearer {access_token}'
    })
    assert response.status_code == 200
    assert response.json['msg'] == 'Successfully logged out'


def test_refresh_token(test_client, init_database):
    response = test_client.post('/v1/login', data=json.dumps({
        'username': 'testuser',
        'password': 'testpassword1'
    }), content_type='application/json')
    refresh_token = response.json['refresh_token']
    response = test_client.post('/v1/refresh', headers={
        'Authorization': f'Bearer {refresh_token}'
    })
    assert response.status_code == 200
    assert 'access_token' in response.json


def test_get_user(test_client, init_database):
    response = test_client.post('/v1/login', data=json.dumps({
        'username': 'testuser',
        'password': 'testpassword1'
    }), content_type='application/json')
    access_token = response.json['access_token']
    response = test_client.get('/v1/user', headers={
        'Authorization': f'Bearer {access_token}'
    })
    assert response.status_code == 200
    assert response.json['username'] == 'testuser'
    assert response.json['email'] == 'test@example.com'


def test_get_user_not_found(test_client, init_database):
    # Create a new user and log in to get a valid token
    new_user = User.create_new(username='newuser', password='testpassword2', email='newuser@example.com', role='user')
    db.session.add(new_user)
    db.session.commit()
    response = test_client.post('/v1/login', data=json.dumps({
        'username': 'newuser',
        'password': 'testpassword2'
    }), content_type='application/json')
    access_token = response.json['access_token']
    # Delete the user to simulate "User not found"
    User.query.filter_by(username='newuser').delete()
    db.session.commit()
    # Try to get the deleted user's details
    response = test_client.get('/v1/user', headers={
        'Authorization': f'Bearer {access_token}'
    })
    assert response.status_code == 403
    assert response.json['message'] == 'User not found'
    # Try to get update the deleted user's role
    response = test_client.post('/v1/admin/roles', data=json.dumps({
        'username': 'newuser',
        'role': 'admin'
    }), headers={
        'Authorization': f'Bearer {access_token}'
    })
    assert response.status_code == 403
    assert response.json['message'] == 'User not found'


def test_update_user_role(test_client, init_database):
    # Login as admin to get token
    User.create_new(username='test_ad_user',
                    password_hash=generate_password_hash('adminpassword1'),
                    email='admin@example.com',
                    role='admin')
    response = test_client.post('/v1/login', data=json.dumps({
        'username': 'test_ad_user',
        'password': 'adminpassword1'
    }), content_type='application/json')
    access_token = response.json['access_token']
    # Update user role
    response = test_client.post('/v1/admin/roles', data=json.dumps({
        'username': 'test_ad_user',
        'role': 'admin'
    }), headers={
        'Authorization': f'Bearer {access_token}'
    }, content_type='application/json')
    assert response.status_code == 200
    assert response.json['message'] == 'User role updated'
    # Ensure that the admin-only route works
    response = test_client.get('/v1/admin', data=json.dumps({
        'username': 'test_ad_user',
        'role': 'admin'
    }), headers={
        'Authorization': f'Bearer {access_token}'
    }, content_type='application/json')
    assert response.status_code == 200
    assert response.json['message'] == 'Welcome, admin'


def test_handle_exception(test_client):
    response = test_client.get('/v1/raise-exception')
    assert response.status_code == 500
    assert "This is a test exception" in response.data.decode()


def test_api_error_initialization():
    error = APIError('Test error', 400, {'additional': 'info'})
    assert error.message == 'Test error'
    assert error.status_code == 400
    assert error.payload == {'additional': 'info'}


def test_api_error_to_dict():
    error = APIError('Test error', 400, {'additional': 'info'})
    error_dict = error.to_dict()
    assert error_dict == {'message': 'Test error', 'additional': 'info'}


@patch('api.errors.logger')
def test_handle_api_error(mock_logger, test_client):
    response = test_client.get('/test-error')
    mock_logger.error.assert_called_once_with('APIError: Test error occurred, Status Code: 500')
    assert response.status_code == 500
    assert response.json == {'message': 'Test error occurred'}


def test_handle_api_error_print_output(test_client, capsys):
    test_client.get('/test-error')
    captured = capsys.readouterr()
    assert 'error' in captured.out
    assert 'Test error occurred' in captured.out


def test_is_scraping_request(test_client):
    with test_client.application.test_request_context('/some-path'):
        with patch('api.v1_routes.routes.request', new=Mock()) as mock_request, \
                patch('api.v1_routes.routes.ip_ban', new=Mock()) as mock_ip_ban:
            mock_request.user_agent.string.lower.return_value = 'python-requests'
            mock_request.url = 'http://localhost/test'
            mock_ip_ban.get_ip.return_value = '127.0.0.1'
            mock_ip_ban.test_pattern_blocklist.return_value = False
            assert is_scraping_request() is True


def test_is_bot_request(test_client):
    with test_client.application.test_request_context('/some-path'):
        with patch('api.v1_routes.routes.request', new=Mock()) as mock_request, \
                patch('api.v1_routes.routes.is_scraping_request', new=Mock()) as mock_is_scraping_request:
            mock_request.user_agent.string.lower.return_value = 'googlebot'
            mock_is_scraping_request.return_value = False
            assert is_bot_request() is True


def test_is_bot_route(test_client):
    response = test_client.get('/v1/is_bot')
    assert response.status_code == 200
    assert response.data in [b'True', b'False']


def test_debug_route(test_client):
    with patch('api.v1_routes.routes.get_all_table_demos') as mock_get_all_table_demos:
        response = test_client.get('/v1/debug')
        assert response.status_code == 200
        assert response.json == {'success': True}
        response = test_client.post('/v1/debug')
        assert response.status_code == 200
        assert response.json == {'success': True}
