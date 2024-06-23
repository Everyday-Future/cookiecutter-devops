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
from datetime import datetime, timedelta
from sqlalchemy.orm.attributes import flag_modified
from sqlalchemy.schema import DropTable
from sqlalchemy.ext.compiler import compiles
from werkzeug.security import generate_password_hash, check_password_hash
from config import Config
from api import sa_db as db


@compiles(DropTable, "postgresql")
def _compile_drop_table(element, compiler, **kwargs):
    return compiler.visit_drop_table(element) + " CASCADE"


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
    slug = db.Column(db.String(64), index=True)
    created = db.Column(db.DateTime, index=True, nullable=False, default=datetime.utcnow)
    updated = db.Column(db.DateTime, onupdate=datetime.utcnow, nullable=False, default=datetime.utcnow)
    data = db.Column(db.JSON, nullable=True, default={'version': Config.VERSION, 'data': {}})

    def bump_updated(self):
        """ Indicate a table update by setting the 'updated' time to now """
        self.updated = datetime.utcnow()

    @classmethod
    def get_by_slug(cls, slug):
        return cls.query.filter_by(slug=slug).first()

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
            self.data = {'start_time': time.time(), 'is_complete': False, "version": Config.VERSION}
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

    def to_dict(self):
        # Returns a dictionary with all attributes of the object that are not methods or dunders
        return {k: v for k, v in self.__dict__.items() if not k.startswith("__") and not callable(v)}


class BannedToken(DataMixin, db.Model):
    """
    Token Model for storing JWT tokens
    """
    plural = 'banned_tokens'
    jti = db.Column(db.String(36), nullable=False)

    def __repr__(self):
        return f'<BannedToken id: token: {self.token}'

    def to_dict(self):
        return {'token': self.token}

    @staticmethod
    def create_new(jti):
        if isinstance(jti, bytes):
            jti = jti.decode('utf-8')
        # noinspection PyArgumentList
        b_token = BannedToken(jti=jti)
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
    username = db.Column(db.String(512), index=True, nullable=True)
    role = db.Column(db.String(64), index=True, nullable=False, default='user')  # or publisher or admin
    email = db.Column(db.String(512), index=True)
    token = db.Column(db.String(512), index=True)
    token_expiration = db.Column(db.DateTime)
    password_hash = db.Column(db.String(512), nullable=True)
    is_admin = db.Column(db.Boolean, default=False)
    privacy = db.Column(db.Boolean)

    def __repr__(self):
        return (f'<User id:{self.id} created: {self.created} updated: {self.updated} is_anon: {self.is_anon} '
                f'role: {self.role} username: {self.username} email: {self.email}>')

    def to_dict(self):
        return {
            "id": self.token,
            "username": self.username,
            "role": self.role,
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
    def create_new(username, role, password_hash=None, password=None,
                   email=None, privacy=None, is_admin=False, data=None):
        if password_hash is None and password is not None:
            password_hash = generate_password_hash(password)
        # noinspection PyArgumentList
        new_user = User(username=username, role=role, password_hash=password_hash,
                        email=email, privacy=privacy, is_admin=is_admin)
        data = data or {}
        new_user.update_data(data)
        db.session.add(new_user)
        new_user.get_token()
        db.session.commit()
        return new_user

    def absorb_user(self, target_user):
        # TODO - assign a user's products + cart_ids + orders over to a registered instance
        pass

    def get_token(self, expires_in=3600 * 4):
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


class Event(DataMixin, db.Model):
    """
    Event within an experiment.

    This is a sequential log of records for experiments to track data over time and allow rebuilding
    of the main experiment in the event of data corruption.
    """
    plural = 'events'
    __table_args__ = {'extend_existing': True}
    # Foreign key cols
    user_id = db.Column(db.BigInteger, db.ForeignKey('user.id'), nullable=False, index=True)
    # Name of the referenced experiment
    name = db.Column(db.String(64), index=True)
    # Choice represented in this event. So this represents which MAB arm was pulled.
    choice_key = db.Column(db.String(256))
    # Some experiments are broken into subsets of users, which can be specified here.
    subset_key = db.Column(db.String(256), index=True, default='default')
    # Value of the pull and reward for the event
    pull_event = db.Column(db.Boolean, default=True, nullable=False)
    reward_event = db.Column(db.Boolean, default=False, nullable=False)
    bonus_event = db.Column(db.Boolean, default=False, nullable=False)

    def __repr__(self):
        return f"<Event: id={self.id} name={self.name} created={self.created} choice_key={self.choice_key} " \
               f"subset_key={self.subset_key} pull_event={self.pull_event} reward_event={self.reward_event} >"

    def to_dict(self):
        data = {
            'id': self.id,
            "created": self.created.timestamp(),
            "updated": self.updated.timestamp(),
            "name": self.name,
            "choice_key": self.choice_key,
            "subset_key": self.subset_key,
            "pull_event": self.pull_event,
            "reward_event": self.reward_event,
        }
        return data

    @staticmethod
    def create_new(user_id: int, name: str, choice_key: str, subset_key: str):
        """
        Create a new record of an event as part of an experiment
        :param user_id: The user that triggered the event
        :param name: Name of the referenced experiment
        :param choice_key: Choice represented in this event. So this represents which MAB arm was pulled.
        :param subset_key: Some experiments are broken into subsets of users, which can be specified here.
        :return:
        """
        # noinspection PyArgumentList
        new_event = Event(user_id=user_id, name=name, choice_key=choice_key, subset_key=subset_key or 'default')
        db.session.add(new_event)
        db.session.commit()
        return new_event

    @staticmethod
    def get_by_user_and_experiment(user: User, experiment_name):
        """
        Get an event for a user and an experiment.
        Typically used to find out what choice was made on the pull to create a reward.
        :param user:
        :type user:
        :param experiment_name:
        :type experiment_name:
        :return:
        :rtype:
        """
        return Event.query.filter_by(user_id=user.id).filter_by(name=experiment_name).first()

    @classmethod
    def get_all_events_for_experiment(cls, experiment_name, subset_key=None):
        """
        Search through all events for an experiment, filtered by subset if specified.
        :param experiment_name:
        :type experiment_name:
        :param subset_key:
        :type subset_key:
        :return:
        :rtype:
        """
        if subset_key is not None:
            return cls.query.filter_by(name=experiment_name).filter_by(subset_key=subset_key).all()
        else:
            return cls.query.filter_by(name=experiment_name).all()

    @classmethod
    def get_scores(cls, experiment_name, choices: list[str], subset_key=None):
        """
        Total up the pulls and rewards for the events in the specified choices list
        and, if specified, filtered to the designated subset.
        :param experiment_name:
        :type experiment_name:
        :param choices:
        :type choices:
        :param subset_key:
        :type subset_key:
        :return:
        :rtype:
        """
        events = cls.get_all_events_for_experiment(experiment_name=experiment_name, subset_key=subset_key)
        # Start with 1 pull 1 reward to aggressively try out new additions to the choices
        out_dict = {choice: {'pulls': 1, 'rewards': 1, 'bonus': 1} for choice in choices}
        for each_event in events:
            # If the choice is still active, add the pull and reward to the choice subtotal
            if each_event.choice_key in choices:
                out_dict[each_event.choice_key]['pulls'] += 1
                if each_event.reward_event is True:
                    out_dict[each_event.choice_key]['rewards'] += 1
                if each_event.bonus_event is True:
                    out_dict[each_event.choice_key]['bonus'] += 1
        return out_dict

    @classmethod
    def reward_recent(cls, user: User, thresh_min=180.0, is_bonus=False):
        """
        Reward all the Events for the specified user for the last n minutes
        This allows for a long-term memory for the app,
        where bandit pulls are rewarded for the most important conversions
        rather that superficial landing page click-through numbers.
        This is represented by the bonus_event column added in the latest migration.
        :param thresh_min:
        :type thresh_min:
        :return:
        :rtype:
        """
        events = Event.query.filter_by(user_id=user.id).all()
        events = [event for event in events
                  if datetime.utcnow() <= (event.updated + timedelta(seconds=thresh_min * 60.0))]
        for event in events:
            if is_bonus is True:
                event.bonus_event = True
            else:
                event.reward_event = True
        db.session.commit()


class Experiment(DataMixin, db.Model):
    """
    Model for an Experiment.

    This is a records table, where if an experiment is updated a new instance is created so that the history
    of the table is preserved.

    data structure should follow:

    {
        "name": string
        "version": string
        "choices": list[string]
    }
    """
    plural = 'experiments'
    __tablename__ = 'experiment'
    __table_args__ = {'extend_existing': True}
    # Name of the experiment
    name = db.Column(db.String(64), index=True)

    def __repr__(self):
        return f"<Experiment: id={self.id} name={self.name} created={self.created} >"

    def to_dict(self):
        data = {
            'id': self.id,
            "created": self.created.timestamp(),
            "updated": self.updated.timestamp(),
            "name": self.name
        }
        return {**self.get_data(), **data}

    @staticmethod
    def create_new(experiment_name, choices: list[str]):
        # noinspection PyArgumentList
        new_model = Experiment(name=experiment_name,
                               updated=datetime.utcnow())
        new_model.update_data({'choices': choices})
        db.session.add(new_model)
        db.session.commit()
        return new_model

    @property
    def choices(self):
        """ Get the selection of choices for the experiment from the data column. """
        return self.data.get('choices', [])

    def choices_list_is_updated(self, new_choices):
        """ Compare a new list of choices to the currently-available choices. """
        return set(self.choices) != set(new_choices)

    @classmethod
    def get_by_name(cls, name):
        """
        Get the Experiment by name or return None if not found.
        If multiple records are found, get the latest
        """
        return Experiment.query.filter_by(name=name).order_by(cls.updated.desc()).first()


def get_all_tables():
    """ Get all the table models for testing and introspection """
    return [BannedToken, User, Address]


def get_all_table_demos(debug_mode=False):
    username = f"test{random.randint(0, 9999999)}"
    password = 'temppassword'
    email_address = f"{random.randint(0, 9999999)}@{{ project_slug }}.com"
    user = User.create_new(email=email_address)
    user.set_password(password)
    addr = Address.create_new(user_id=user.id, first_name="Steven", last_name="Sutton",
                              street1="895 East Summit Dr", street2="Unit 893",
                              city="Dalton", state="GA", post_code="30102", country_code="US",
                              phone_number="404-429-7444", organization="Everyday Future")
    return {
        'user': user,
        'banned_token': BannedToken.create_new(username),
        'address': addr
    }
