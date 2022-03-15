
import requests
from api import global_config


class AlertZapier:

    def send(self, alert_name, msg, params):
        webhook_url = ''
        if alert_name == 'order_confirmation':
            webhook_url = global_config.ZAP_ORDER_CONF
        elif alert_name == 'free_order_confirmation':
            webhook_url = global_config.ZAP_UXTESTER
        # Send the alert if one exists
        if webhook_url not in (None, '', ' '):
            requests.post(webhook_url, json=params)

