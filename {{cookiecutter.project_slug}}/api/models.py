"""

Database interface and models

The db is built with Sqlalchemy and Alembic based on the architecture of these classes.

The DataMixin class also provides lots of standard data operations for unstructured data columns
and REST queries.

All models also expose a create_new() function that builds a new record and adds it to the DB,
but doesn't do a commit operation.

"""


import os
import time
import random
import base64
import jwt
from datetime import datetime, timedelta
from werkzeug.security import generate_password_hash, check_password_hash
from sqlalchemy.orm.attributes import flag_modified
from config import Config
from api import db
from sqlalchemy.schema import DropTable
from sqlalchemy.ext.compiler import compiles


@compiles(DropTable, "postgresql")
def _compile_drop_table(element, compiler, **kwargs):
    return compiler.visit_drop_table(element) + " CASCADE"


global_config = Config()


def models_to_dict(models):
    """
    Convert all the referenced data in a table to dict, sorted by most recent first
    """
    out_list = [model.to_dict() for model in models]
    return sorted(out_list, key=lambda x: x['created'], reverse=True)


class DataMixin(object):
    """
    Add created, updated, and data columns to the tables along with helper functions for them.

    This adds easy-to-use functions for getting the latest row in a series, tracking updated,
    organizing json data, and other common data tracking patterns.
    """
    query: db.Query  # Type hint to autocomplete queries
    id = db.Column(db.BigInteger, primary_key=True, index=True, unique=True)
    created = db.Column(db.DateTime, index=True, nullable=False, default=datetime.utcnow)
    updated = db.Column(db.DateTime, onupdate=datetime.utcnow, nullable=False, default=datetime.utcnow)
    data = db.Column(db.JSON, nullable=True, default={'version': global_config.VERSION, 'data': {}})

    def bump_updated(self):
        """ Indicate a table update by setting the 'updated' time to now """
        self.updated = datetime.utcnow()

    @staticmethod
    def default_data(**kwargs):
        """
        Get the default data model that encompasses a basic data structure
        :return: dict of {"version": "0.4.6", "data": {...}, ... }
        """
        kwargs.update({'start_time': time.time(), 'is_complete': False})
        return kwargs

    def get_data(self, key_name: str = None):
        """
        Get the data from a specific field in the data column
        :param key_name: If there is a specific sub-key to retrieve within self.data["data"], specify it here.
        :return: self.data['data'] dict
        """
        if self.data is None:
            self.data = {'start_time': time.time(), 'is_complete': False, "version": global_config.VERSION}
            flag_modified(self, "data")
        if key_name is None:
            return self.data
        else:
            return self.data.get(key_name)

    def update_data(self, new_data: dict):
        """
        Updates a field in the data column under the data field or add it if it doesn't already exist.
        :param new_data: dictionary of new data to add in.
        :return: updated self.data['data'] dict
        """
        assert new_data is not None
        if self.data is None:
            self.data = self.get_data()
        self.data.update(new_data)
        flag_modified(self, "data")
        self.bump_updated()
        return self.get_data()

    def increment_counter(self, key_name: str):
        """
        Increment a counter key in the data dict
        """
        self.update_data({key_name: self.get_data().get(key_name, 0) + 1})


class Mailinglist(DataMixin, db.Model):
    """
    User entries in the mailing list form.
    """
    plural = 'mailinglists'
    __table_args__ = {'extend_existing': True}
    # Top-level fields
    name = db.Column(db.String(128), default='', nullable=False)
    email = db.Column(db.String(128), nullable=False)
    subscribed = db.Column(db.Boolean, default=True)
    message = db.Column(db.Text, nullable=False)

    def __repr__(self):
        return f'<Mailinglist id={self.id} email={self.email} name={self.name} subscribed={self.subscribed}>'

    def to_dict(self):
        return {
            'id': self.id,
            "created": self.created.timestamp(),
            "updated": self.updated.timestamp(),
            'name': self.name,
            'email': self.email,
            'subscribed': self.subscribed,
            'message': self.message
        }

    @staticmethod
    def create_new(name, email, message, subscribed=True):
        # noinspection PyArgumentList
        new_subscriber = Mailinglist(name=name, email=email, subscribed=subscribed, message=message)
        db.session.add(new_subscriber)
        db.session.commit()
        return new_subscriber


class Contact(DataMixin, db.Model):
    """
    User entries in the contact us form or feedback surveys.
    """
    plural = 'contacts'
    __table_args__ = {'extend_existing': True}
    # Top-level fields
    name = db.Column(db.String(128), nullable=False)
    email = db.Column(db.String(128), nullable=False)
    message = db.Column(db.Text, nullable=False)

    def __repr__(self):
        return f'<Contact id={self.id} email={self.email} name={self.name}>'

    def to_dict(self):
        return {
            "id": self.id,
            "created": self.created.timestamp(),
            "updated": self.updated.timestamp(),
            "name": self.name,
            "email": self.email,
            "message": self.message
        }

    @staticmethod
    def create_new(name, email, message, data=None):
        data = data or {}
        data.update(dict(name=name, email=email, message=message))
        # noinspection PyArgumentList
        new_contact = Contact(name=name, email=email, message=message)
        new_contact.update_data(data)
        db.session.add(new_contact)
        db.session.commit()
        return new_contact


class BannedToken(DataMixin, db.Model):
    """
    Token Model for storing JWT tokens
    """
    plural = 'banned_tokens'
    token = db.Column(db.String(500), unique=True, nullable=False)

    def __repr__(self):
        return f'<BannedToken id: token: {self.token}'

    @staticmethod
    def to_dict():
        return {}

    @staticmethod
    def create_new(token):
        if isinstance(token, bytes):
            token = token.decode('utf-8')
        # noinspection PyArgumentList
        b_token = BannedToken(token=token)
        db.session.add(b_token)
        db.session.commit()
        return b_token

    @staticmethod
    def check_banned(token):
        if isinstance(token, bytes):
            token = token.decode('utf-8')
        # check whether auth token has been banned
        res = BannedToken.query.filter_by(token=str(token)).first()
        if res:
            return True
        else:
            return False


class User(DataMixin, db.Model):
    """
    Representation of a User.
    Anonymous users are given fake email addresses
    Registered users are identified with is_anon=False
    """
    plural = 'users'
    __table_args__ = {'extend_existing': True}
    # Foreign key cols
    addresses = db.relationship('Address', backref=db.backref("user_addrs", cascade="all"), lazy='dynamic')
    # Top-level fields
    email = db.Column(db.String(512), index=True)
    token = db.Column(db.String(512), index=True)
    token_expiration = db.Column(db.DateTime)
    password_hash = db.Column(db.String(512))
    is_admin = db.Column(db.Boolean, default=False)
    privacy = db.Column(db.Boolean)

    def __repr__(self):
        return f'<User id:{self.id} created: {self.created} updated: {self.updated} is_anon: {self.is_anon}>'

    def to_dict(self):
        return {
            "id": self.token,
            "email": self.email,
            "is_admin": self.is_admin,
            "privacy": self.privacy,
            "addresses": models_to_dict(self.addresses),
            "orders": models_to_dict(self.orders),
            "products": models_to_dict(self.products),
            "surveys": models_to_dict(self.surveys),
            "stats": models_to_dict(self.stats),
            "created": self.created.timestamp(),
            "updated": self.updated.timestamp()
        }

    @staticmethod
    def create_new(email=None, privacy=None, is_admin=False, data=None):
        # noinspection PyArgumentList
        new_user = User(email=email, privacy=privacy, is_admin=is_admin)
        data = data or {}
        new_user.update_data(data)
        db.session.add(new_user)
        new_user.get_token()
        db.session.commit()
        new_user.set_jwt()
        return new_user

    def absorb_user(self, target_user):
        # TODO - assign a user's products + cart_ids + orders over to a registered instance
        pass

    def get_token(self, expires_in=3600*4):
        now = datetime.utcnow()
        if self.token and self.token_expiration is not None and self.token_expiration > now + timedelta(seconds=60):
            return self.token
        self.token = base64.b64encode(os.urandom(24)).decode('utf-8')
        self.token_expiration = now + timedelta(seconds=expires_in)
        db.session.add(self)
        db.session.commit()
        return self.token

    def revoke_token(self):
        self.token_expiration = datetime.utcnow() - timedelta(seconds=1)

    @staticmethod
    def check_token(token):
        user = User.query.filter_by(token=token).first()
        if user is None or user.token_expiration is None or user.token_expiration < datetime.utcnow():
            return None
        return user

    def set_jwt(self, expires_in_days=60.0):
        """
        Encode a table id as a JWT with the id as {"table_id": 0} where table_id for User == user_id
        :param expires_in_days: Number of hours for which the token is valid as a float.
        """
        prev_token = self.token
        # expires_in_seconds = expires_in_days * 60 * 60 * 24
        token = jwt.encode({'sub': str(self.id),
                            'iat': time.time(),
                            'exp': datetime.utcnow() + timedelta(days=expires_in_days),
                            'jti': base64.b64encode(os.urandom(24)).decode('utf-8')},
                           global_config.UID_SECRET_KEY, algorithm='HS256')
        self.token = token
        db.session.commit()
        if prev_token is not None:
            BannedToken.create_new(prev_token)
        return token

    @staticmethod
    def get_decoded_id(encoded_jwt):
        """
        Validates the auth token
        :param encoded_jwt:
        :return: integer|string
        """
        if isinstance(encoded_jwt, str):
            encoded_jwt = encoded_jwt.encode()
        try:
            payload = jwt.decode(encoded_jwt, global_config.UID_SECRET_KEY, algorithms=['HS256'])
            is_blacklisted_token = BannedToken.check_banned(encoded_jwt)
            if is_blacklisted_token:
                raise ValueError('Token blacklisted. Please log in again.')
            else:
                return int(payload['sub'])
        except jwt.ExpiredSignatureError:
            # Ban the expired token
            BannedToken.create_new(encoded_jwt)
            raise ValueError('Signature expired. Please log in again.')
        except jwt.InvalidTokenError as err:
            raise ValueError(f'Invalid token: {err} Please log in again.')

    @staticmethod
    def from_jwt(encoded_jwt: str):
        """ get a database row from a jwt. """
        # noinspection PyUnresolvedReferences
        return User.query.get(User.get_decoded_id(encoded_jwt))

    @property
    def is_anon(self):
        return self.password_hash in ('', None)

    def set_password(self, password):
        """
        Save a secure password for the user
        :param password:
        :return:
        """
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        """
        Hash a password and check it against the hash stored for the user
        :param password:
        :return:
        """
        return check_password_hash(self.password_hash, password)


class Address(DataMixin, db.Model):
    """
    User address information for shipping and localization
    """
    plural = 'addresses'
    __table_args__ = {'extend_existing': True}
    # Foreign key cols
    user_id = db.Column(db.BigInteger, db.ForeignKey('user.id'), nullable=False)
    # Top-level fields
    first_name = db.Column(db.String(128))
    last_name = db.Column(db.String(128))
    phone_number = db.Column(db.String(20))
    street1 = db.Column(db.String(128), nullable=False)
    street2 = db.Column(db.String(128), nullable=False)
    city = db.Column(db.String(128), nullable=False)
    state = db.Column(db.String(128), nullable=False)
    post_code = db.Column(db.String(128), nullable=False)
    country_code = db.Column(db.String(128), nullable=False)
    organization = db.Column(db.String(128))
    is_billing = db.Column(db.Boolean, default=False, nullable=False)

    def __repr__(self):
        return f"<Street Address: {self.first_name} {self.last_name}, {self.street1} {self.street2}, " \
               f"{self.city} {self.state} {self.post_code} {self.country_code}>"

    def to_dict(self):
        return {"first_name": self.first_name,
                "last_name": self.last_name,
                "phone_number": self.phone_number,
                "created": self.created.timestamp(),
                "updated": self.updated.timestamp(),
                "street1": self.street1,
                "street2": self.street2,
                "line1": self.street1,
                "line2": self.street2,
                "city": self.city,
                "state": self.state,
                "post_code": self.post_code,
                "postal_code": self.post_code,
                "country": self.country_code,
                "country_code": self.country_code,
                "organization": self.organization,
                "customer_name": self.first_name + " " + self.last_name}

    @staticmethod
    def create_new(user_id, street1, street2, city, state, post_code, country_code,
                   first_name=None, last_name=None, phone_number=None, organization=None, is_billing=False):
        # noinspection PyArgumentList
        new_address = Address(user_id=user_id, first_name=first_name, last_name=last_name, phone_number=phone_number,
                              street1=street1, street2=street2, city=city, state=state, post_code=post_code,
                              country_code=country_code, organization=organization, is_billing=is_billing)
        db.session.add(new_address)
        db.session.commit()
        return new_address

    @property
    def name(self):
        return f"{self.first_name} {self.last_name}"


def get_all_tables():
    """ Get all the table models for testing and introspection """
    return [Mailinglist, Contact, BannedToken, User, Address]


def get_all_table_demos(debug_mode=False):
    username = f"test{random.randint(0, 9999999)}"
    password = 'temppassword'
    email_address = f"{random.randint(0, 9999999)}@{{ project_slug }}.com"
    user = User.create_new(email=email_address)
    user.set_password(password)
    addr = Address.create_new(user_id=user.id, first_name="Steven", last_name="Sutton",
                              street1="898 East Summit Dr", street2="Unit 33",
                              city="Dalton", state="GA", post_code="30102", country_code="US",
                              phone_number="404-429-7444", organization="Everyday Future")
    contact = Contact.create_new(name=username, email=email_address, message="test contact form entry " * 50)
    mailinglist = Mailinglist.create_new(name=username, email=email_address, subscribed=True,
                                         message="test contact form entry " * 50)
    return {
        'user': user,
        'banned_token': BannedToken.create_new(username),
        'address': addr,
        'contact': contact,
        'mailinglist': mailinglist
    }


class BaseDAO:
    """
    Shared functions for all Data Access Objects
    """
    def get_data(self):
        """ Get the data from the instance of a row represented in a db.Model class"""
        if hasattr(self, 'row'):
            return self.row.get_data()
