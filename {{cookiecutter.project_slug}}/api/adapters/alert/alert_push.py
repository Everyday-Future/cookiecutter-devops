"""

Unified alerting infrastructure

Push alerts to whatever services have been configured, including logging, email, zapier, and slack.

"""

import json
import datetime
from api import global_config, logger
from api.models import User, Address, Contact
from api.adapters.alert.alert_push_slack import AlertSlack
from api.adapters.alert.alert_push_zapier import AlertZapier


class AlertLogger:
    """
    Consume alert messages and log them
    """

    @staticmethod
    def send(alert_name, msg, params):
        """
        Log an alert message with diagnostic info that is easy to find in the logs
        :param alert_name: Standardized name for the alert (ex. "order_confirmation")
        :type alert_name: str
        :param msg: Message string for the alert
        :type msg: str
        :param params: Parameter dictionary for the alert. Contains metadata for complex services like zapier
        :type params:
        :return:
        :rtype:
        """
        level = params.get('level', 'INFO')
        logger.log(level=level, msg='alert_msg=' + alert_name + ' - ' + msg)
        logger.log(level=level, msg='alert_msg_params=' + alert_name + ' - ' + json.dumps(params))


class AlertStack:
    """
    Rollup of all of the configured alerts for the instance.
    Contains simple logic for common events that require alerts,
    then distributes the messages using those configured services.
    """

    def __init__(self, agents=None):
        self.agents = agents
        if self.agents is None:
            # Logging
            self.agents = {'logger': AlertLogger()}
            # Slack
            if global_config.SLACK_TOKEN is not None:
                self.agents['slack'] = AlertSlack()
            # Zapier
            if global_config.ZAP_ORDER_CONF is not None:
                self.agents['zapier'] = AlertZapier()

    def send_all(self, alert_name, msg, params):
        params['msg'] = msg
        [agent.send(alert_name, msg, params) for agent in self.agents.values()]
        return msg, params

    def order_confirmation_prep(self, order_id, user_id, user_email, product_ids: list[int]):
        """
        Initial alert before rendering an order,
        to capture as much information as possible in case something goes wrong.
        :param order_id:
        :type order_id:
        :param user_id:
        :type user_id:
        :param user_email:
        :type user_email:
        :param product_ids:
        :type product_ids:
        :return:
        :rtype:
        """
        msg = f"""
        {datetime.datetime.utcnow().isoformat()}
        Incoming order {order_id} for user {user_id} at {user_email}
        Product ids: {product_ids}
        Stand by for download links and shipping details when rendering is complete...
        """
        params = {'email': user_email, 'user_id': user_id, 'order_id': order_id, 'products': product_ids}
        self.send_all(alert_name='order_confirmation', msg=msg, params=params)
        return msg, params

    def order_confirmation(self, user: User, address: Address, stripe_id: str, order_id: int,
                           subtotal: float, product_links: dict = None):
        """
        Confirm the user's order with all of the information needed to fulfill it.
        To be sent once without the download links and later with the links after rendering.
        :param user: User that just completed an order
        :type user: str
        :param address: The full address model for the user
        :type address: Address
        :param stripe_id:
        :type stripe_id:
        :param order_id: ID for the entry in the order table
        :type order_id:
        :param subtotal: Dollar subtotal for the user's order
        :type subtotal: float
        :param product_links: (optional) Dict of download links for the rendered books from the order as {name: link}
        :type product_links: dict
        :return:
        :rtype:
        """
        msg = f"""
        {address.created.isoformat()}
        User {user.id} at {user.email} spent {subtotal:.2f} on order {stripe_id}
        Ship to:
        {address.first_name} {address.last_name}
        {address.street1} {address.street2}
        {address.city} {address.state} {address.post_code}

        stripe link:
        https://dashboard.stripe.com/payments/{stripe_id}

        order_id = {order_id}

        download links:
        """
        for product_name, link in product_links.items():
            msg += f"{product_name} - {link}\n"
        addr_str = f" {address.street1} {address.street2} {address.city} {address.state} {address.post_code}"
        params = {'email': user.email, 'stripe_id': stripe_id, 'address': addr_str,
                  'name': f'{address.first_name} {address.last_name}', 'user_id': user.id,
                  'products': product_links, 'order_id': order_id}
        self.send_all(alert_name='order_confirmation', msg=msg, params=params)
        return msg, params

    def ux_tester_order(self, email, coupon_code, address: Address, product_links: dict = None):
        """
        Confirm a UX tester's order
        :param email:
        :type email:
        :param coupon_code:
        :type coupon_code:
        :param address:
        :type address:
        :param product_links:
        :type product_links:
        :return:
        :rtype:
        """
        msg = f"""
        {address.created.isoformat()}
        User {email} redeemed a UX Tester coupon code "{coupon_code}"
        Ship to:
        {address.first_name} {address.last_name}
        {address.street1} {address.street2}
        {address.city} {address.state} {address.post_code}

        download links:
        """
        for product_name, link in product_links.items():
            msg += f"{product_name} - {link}\n"
        addr_str = f" {address.street1} {address.street2} {address.city} {address.state} {address.post_code}"
        params = {'email': email, 'address': addr_str, 'name': f'{address.first_name} {address.last_name}',
                  'products': product_links}
        self.send_all(alert_name='free_order_confirmation', msg=msg, params=params)
        return msg, params

    def order_shipped(self, user: User, tracking_number, order_id):
        """
        Confirm that the order was shipped
        """
        pass

    def order_delivered(self):
        """
        Confirm that the order was delivered
        """
        pass

    def order_error(self):
        """
        Alert that there was an error with the order
        """
        pass

    def contact_form_fill(self, contact: Contact):
        """
        Contact Us form fill
        User is reaching out to us through either the contact page, a help section, or a suggestion box.
        :param contact:
        :type contact:
        :return:
        :rtype:
        """
        msg = f"""
        {contact.created.isoformat()}
        {contact.name} at {contact.email} had this to say:
        {contact.message}
        """
        params = {'name': contact.name, 'email': contact.email, 'message': contact.message}
        self.send_all(alert_name='contact_form', msg=msg, params=params)
        return msg, params

    def daily_update(self):
        """
        Post an update about the daily activity to keep everyone in the loop and act as a heartbeat
        """
        yesterday = datetime.datetime.utcnow() - datetime.timedelta(days=1)
        num_visitors = User.query.filter(User.created > yesterday).count()
        # TODO - implement feedback form
        avg_rating = 'unknown'
        feedback_list = []
        # Compile the body of the message
        msg = f"""
        {datetime.datetime.utcnow().isoformat()}
        Daily Update!
        num visitors: {num_visitors}
        avg rating: {avg_rating}
        """
        # Add feedback messages if we have any
        if len(feedback_list) > 0:
            msg += f"\n\nfeedback messages:\n"
            for feedback_msg in feedback_list:
                msg += f"{feedback_msg}\n"
        params = {'num_visitors': num_visitors, 'avg_rating': avg_rating, 'feedback_list': feedback_list}
        self.send_all(alert_name='daily_update', msg=msg, params=params)
        return msg, params
