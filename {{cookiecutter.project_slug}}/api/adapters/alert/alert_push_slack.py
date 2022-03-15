"""

Send an alert message with Slack as part of the alerting stack

"""

from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError
from api import global_config, logger


class AlertSlack:
    """
    Send an alert message with slack
    """
    def __init__(self):
        self.client = WebClient(token=global_config.SLACK_TOKEN)

    def send(self, alert_name, msg, params):
        channel = params.get('channel') or global_config.SLACK_CHANNEL
        try:
            response = self.client.chat_postMessage(channel=channel, text=msg)
            assert response["message"]["text"] == msg
        except SlackApiError as e:
            # You will get a SlackApiError if "ok" is False
            assert e.response["ok"] is False
            assert e.response["error"]  # str like 'invalid_auth', 'channel_not_found'
            logger.exception(f"Got an error: {e.response['error']}")
