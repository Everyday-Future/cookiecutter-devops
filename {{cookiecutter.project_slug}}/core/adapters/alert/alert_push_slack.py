import logging
from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError
from config import Config, logger


class SlackAlert:
    def __init__(self):
        self.client = WebClient(token=Config.SLACK_TOKEN)
        self.channel = Config.SLACK_CHANNEL
        self.logger = logger

    def post_alert(self, channel, message, alert_type="info"):
        """
        Post an alert message to a specified Slack channel.
        """
        try:
            response = self.client.chat_postMessage(channel=channel, text=f"[{alert_type.upper()}] {message}")
            self.logger.info(f"Alert posted to {channel} with ts: {response['ts']}")
            return response['ts']  # Return timestamp for threading
        except SlackApiError as e:
            self.logger.error(f"Error posting to Slack: {e.response['error']}")
            return None

    def continue_thread(self, channel, thread_ts, message):
        """
        Post a follow-up message in a thread to continue an ongoing issue.
        """
        try:
            self.client.chat_postMessage(channel=channel, thread_ts=thread_ts, text=message)
            self.logger.info(f"Continued thread in {channel} on ts: {thread_ts}")
        except SlackApiError as e:
            self.logger.error(f"Error continuing thread in Slack: {e.response['error']}")

    def acknowledge_post(self, channel, thread_ts, user):
        """
        Acknowledge an alert by replying in the thread.
        """
        ack_message = f"Alert acknowledged by {user}."
        self.continue_thread(channel, thread_ts, ack_message)

    def handle_query(self, channel, thread_ts, query):
        """
        Process queries or commands posted in response to an alert.
        """
        # This is a stub method for handling queries; implementation would depend on the commands supported.
        response_message = f"Received query: {query}. Processing..."
        self.continue_thread(channel, thread_ts, response_message)
        # Implement query/command processing logic here.

    # Additional methods for logging, reporting, etc., can be added here.
