import pytest
from werkzeug.security import generate_password_hash
from api.errors import APIError, handle_api_error
from api import create_app
from core.models import db, User


@pytest.fixture(scope='module')
def test_client():
    app = create_app()
    # register test context

    @app.route('/test-error')
    def test_error_route():
        raise APIError('Test error occurred', 500)
    app.register_error_handler(APIError, handle_api_error)
    # Build app context
    with app.app_context():
        db.create_all()
        yield app.test_client()
        db.drop_all()


@pytest.fixture(scope='module')
def new_user():
    user = User(username='testuser',
                password_hash=generate_password_hash('testpassword1'),
                email='test@example.com',
                role='user')
    return user


@pytest.fixture(scope='module')
def init_database(test_client, new_user):
    db.session.add(new_user)
    db.session.commit()
    yield db
    db.session.remove()
    db.drop_all()
