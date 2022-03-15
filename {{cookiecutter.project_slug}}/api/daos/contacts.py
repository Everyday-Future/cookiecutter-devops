
import datetime
from api import db
from api.models import Contact, BaseDAO


class ContactDAO(BaseDAO):
    """
    operations against the orders table
    """
    table = Contact

    @classmethod
    def create(cls, name, email, message, rating=None, suggestion=None):
        data = {}
        for key, val in {'rating': rating, 'suggestion': suggestion}.items():
            if val is not None:
                data[key] = val
        contact = Contact.create_new(name=name, email=email, message=message, data=data)
        db.session.add(contact)
        db.session.commit()
        return contact

    @classmethod
    def list(cls, num_days=None):
        if num_days is None:
            return [contact.to_dict() for contact in Contact.query.all()]
        else:
            start_date = datetime.datetime.utcnow() - datetime.timedelta(days=num_days)
            return [contact.to_dict() for contact in Contact.query.filter(Contact.created > start_date).all()]

    @classmethod
    def get(cls, contact_id):
        return cls.table.query.get(contact_id)
