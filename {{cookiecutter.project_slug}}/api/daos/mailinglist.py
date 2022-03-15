
import datetime
from api import db
from api.models import Mailinglist, BaseDAO


class MailingListDAO(BaseDAO):
    """
    operations against the MailingList table
    """
    table = Mailinglist

    @classmethod
    def create(cls, name, email, message):
        subscriber = cls.table.create_new(name=name, email=email, message=message, subscribed=True)
        db.session.add(subscriber)
        db.session.commit()
        return subscriber

    @classmethod
    def get(cls, mailinglist_id):
        return Mailinglist.query.get(mailinglist_id)

    @classmethod
    def get_by_email(cls, email):
        return cls.table.query.filter(cls.table.email == email).all()

    @classmethod
    def list(cls, num_days=None):
        if num_days is None:
            return [subscriber.to_dict() for subscriber in cls.table.query.all()]
        else:
            start_date = datetime.datetime.utcnow() - datetime.timedelta(days=num_days)
            return [subscriber.to_dict() for subscriber in cls.table.query.filter(cls.table.created > start_date).all()]

    @classmethod
    def subscribe(cls, name, email, message):
        """ Create a new subscriber if one doesn't exist or re-subscribe an email if it already exists. """
        subscriber = cls.table.query.filter(cls.table.email == email).first()
        if subscriber is None:
            return cls.create(name, email, message)
        else:
            subscriber.subscribed = True
            db.session.commit()
            return subscriber

    @classmethod
    def unsubscribe(cls, email):
        """ Find any and all instances of an email in the mailing list and unsubscribe it. """
        emails = cls.table.query.filter(cls.table.email == email).all()
        for email in emails:
            email.subscribed = False
        db.session.commit()
