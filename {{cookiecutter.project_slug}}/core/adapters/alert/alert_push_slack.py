import logging
import os
from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError
from config import Config, logger


class SlackAlert:
    def __init__(self):
        self.client = WebClient(token=os.getenv('SLACK_TOKEN', Config.SLACK_TOKEN))
        self.channel = os.getenv('SLACK_CHANNEL', Config.SLACK_CHANNEL)
        self.logger = logger

        # Configure logging dynamically
        log_level = os.getenv('LOG_LEVEL', 'INFO').upper()
        logging.basicConfig(level=log_level)
        self.logger.setLevel(log_level)

    def post_alert(self, channel: str, message: str, alert_type: str = "info") -> str:
        """
        Post an alert message to a specified Slack channel.

        :param channel: The Slack channel to post the message to.
        :param message: The message content to post.
        :param alert_type: The type of alert (default is "info").
        :return: The timestamp of the posted message if successful, otherwise None.
        """
        try:
            response = self.client.chat_postMessage(channel=channel, text=f"[{alert_type.upper()}] {message}")
            self.logger.info(f"Alert posted to {channel} with ts: {response['ts']}")
            return response['ts']  # Return timestamp for threading
        except SlackApiError as e:
            error_message = f"Error posting to Slack: {e.response['error']}"
            self.logger.error(error_message)
            raise RuntimeError(error_message) from e

    def continue_thread(self, channel: str, thread_ts: str, message: str) -> None:
        """
        Post a follow-up message in a thread to continue an ongoing issue.

        :param channel: The Slack channel to post the message to.
        :param thread_ts: The timestamp of the thread to continue.
        :param message: The message content to post in the thread.
        """
        try:
            self.client.chat_postMessage(channel=channel, thread_ts=thread_ts, text=message)
            self.logger.info(f"Continued thread in {channel} on ts: {thread_ts}")
        except SlackApiError as e:
            error_message = f"Error continuing thread in Slack: {e.response['error']}"
            self.logger.error(error_message)
            raise RuntimeError(error_message) from e

    def acknowledge_post(self, channel: str, thread_ts: str, user: str) -> None:
        """
        Acknowledge an alert by replying in the thread.

        :param channel: The Slack channel to post the message to.
        :param thread_ts: The timestamp of the thread to continue.
        :param user: The user acknowledging the alert.
        """
        ack_message = f"Alert acknowledged by {user}."
        self.continue_thread(channel, thread_ts, ack_message)

    def handle_query(self, channel: str, thread_ts: str, query: str) -> None:
        """
        Process queries or commands posted in response to an alert.

        :param channel: The Slack channel to post the message to.
        :param thread_ts: The timestamp of the thread to continue.
        :param query: The query or command to process.
        """
        # This is a stub method for handling queries; implementation would depend on the commands supported.
        response_message = f"Received query: {query}. Processing..."
        self.continue_thread(channel, thread_ts, response_message)
        # Implement query/command processing logic here.
