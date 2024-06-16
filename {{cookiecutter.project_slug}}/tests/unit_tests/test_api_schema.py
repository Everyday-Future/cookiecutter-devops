import pytest
from marshmallow import ValidationError
from api.daos.schemas import UserSchema

user_schema = UserSchema()


def test_valid_user_data():
    valid_data = {
        'username': 'validuser',
        'password': 'Valid1234',
        'role': 'user',
        'email': 'valid@example.com'
    }
    result = user_schema.load(valid_data)
    assert result == valid_data


def test_invalid_username_length():
    invalid_data = {
        'username': '',
        'password': 'Valid1234',
        'role': 'user',
        'email': 'valid@example.com'
    }
    with pytest.raises(ValidationError) as excinfo:
        user_schema.load(invalid_data)
    assert 'username' in excinfo.value.messages


def test_invalid_password_format():
    invalid_data = {
        'username': 'validuser',
        'password': 'password',  # Invalid: no digits
        'role': 'user',
        'email': 'valid@example.com'
    }
    with pytest.raises(ValidationError) as excinfo:
        user_schema.load(invalid_data)
    assert 'password' in excinfo.value.messages


def test_invalid_email_format():
    invalid_data = {
        'username': 'validuser',
        'password': 'Valid1234',
        'role': 'user',
        'email': 'invalid-email'
    }
    with pytest.raises(ValidationError) as excinfo:
        user_schema.load(invalid_data)
    assert 'email' in excinfo.value.messages


def test_username_contains_admin():
    invalid_data = {
        'username': 'adminuser',
        'password': 'Valid1234',
        'role': 'user',
        'email': 'valid@example.com'
    }
    with pytest.raises(ValidationError) as excinfo:
        user_schema.load(invalid_data)
    assert 'username' in excinfo.value.messages
    assert excinfo.value.messages['username'][0] == 'Username cannot contain "admin"'
