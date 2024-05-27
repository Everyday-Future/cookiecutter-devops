from api import db
from core.models import Address, BaseDAO
from core.daos.user import UserDAO


class AddressDAO(BaseDAO):
    """
    operations against the address table
    """
    table = Address

    @classmethod
    def create(cls, user_id, street1, street2, city, state, post_code, country_code,
               first_name=None, last_name=None, phone_number=None, organization=None, is_billing=False):
        addr = cls.table.create_new(user_id, first_name=first_name, last_name=last_name, phone_number=phone_number,
                                    street1=street1, street2=street2, city=city, state=state, post_code=post_code,
                                    country_code=country_code, organization=organization, is_billing=is_billing)
        db.session.commit()
        return addr

    @classmethod
    def get(cls, address_id):
        return cls.table.query.get(address_id)

    @classmethod
    def list(cls, user_id):
        return UserDAO(user_id).get_addresses()

    @classmethod
    def update(cls, address_id, **kwargs):
        addr = cls.get(address_id)
        [setattr(addr, key, val) for key, val in kwargs.items()]
        return addr

    @classmethod
    def delete(cls, address_id):
        addr = cls.get(address_id)
        db.session.delete(addr)
        db.session.commit()
        return True

    @staticmethod
    def from_stripe_json(address_json):
        addr = Address.create_new(first_name=address_json['first_name'], last_name='', user_id=address_json['user_id'],
                                  street1=address_json['line1'], street2=address_json.get('line2', ''),
                                  city=address_json['city'], state=address_json['state'],
                                  post_code=address_json['postal_code'], country_code=address_json['country'])
        db.session.add(addr)
        db.session.commit()
        return addr
