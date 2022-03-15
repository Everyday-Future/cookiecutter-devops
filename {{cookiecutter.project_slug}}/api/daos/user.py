
from api import db
from api.models import User, Address, BannedToken, BaseDAO


class UserDAO(BaseDAO):
    """
    operations against the users table
    """
    table = User

    def __init__(self, token: str = None, user: User = None):
        if token is not None:
            self.row = self.get(token=token)
        else:
            self.row = user
        self.user = self.row

    @classmethod
    def create(cls, **data):
        new_user = cls.table.create_new(**data)
        db.session.commit()
        return new_user

    @classmethod
    def get(cls, token):
        user = cls.table.check_token(token)
        if user is None:
            raise ValueError('User not found for token')
        return user

    @classmethod
    def get_by_email(cls, email):
        user = cls.table.query.filter_by()
        if user is None:
            raise ValueError('User not found for token')
        return user

    @classmethod
    def list(cls):
        return cls.table.query.all()

    def register(self, email, password):
        if User.query.filter_by(email=email).first() is not None:
            raise ValueError("cannot register user - email already exists")
        self.user.set_password(password=password)
        self.user.email = email
        db.session.commit()
        return self.user

    @staticmethod
    def login(email, password, current_user, expires_in_days=60):
        user = User.query.filter_by(email=email).first()
        if user is None:
            raise ValueError("cannot log in - this email is not registered yet")
        if user.check_password(password) is True:
            # TODO - move the current_user's products over to the registered user.
            if current_user != user and len(current_user.products.all()) > 0:
                user.absorb_user(current_user)
                db.session.commit()
            return user
        else:
            raise ValueError('invalid password for user')

    def logout(self):
        if self.user.token is not None:
            BannedToken.create_new(self.user.token)
            self.user.token = None
            db.session.commit()
        return self.user

    def get_addresses(self):
        return self.user.addresses.order_by(Address.created.desc()).all()

    def get_mailing_address(self, strict=False):
        """
        Get the most recent instance of a mailing address for the user
        """
        addr = Address.query.filter_by(user_id=self.user.id).filter_by(is_billing=False)\
            .order_by(Address.created.desc()).first()
        if addr is None and self.get_addresses() not in (None, []) and strict is False:
            addr = self.user.addresses.order_by(Address.created.desc()).first()
        return addr

    def get_billing_address(self, strict=False):
        """
        Get the most recent instance of a billing address for the user
        """
        addr = Address.query.filter_by(user_id=self.user.id).filter_by(is_billing=True)\
            .order_by(Address.created.desc()).first()
        if addr is None and self.get_addresses() not in (None, []) and strict is False:
            addr = self.user.addresses.order_by(Address.created.desc()).first()
        return addr


def user_to_dict(user):
    data = {"addresses": [addr.to_dict() for addr in user.addresses]}
    return {**user.to_dict(), **data}
