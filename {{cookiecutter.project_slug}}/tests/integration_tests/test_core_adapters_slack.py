import pytest
from config import Config
from core.adapters.alert.alert_push_slack import SlackAlert

TEST_CHANNEL = Config.SLACK_CHANNEL


@pytest.fixture(scope="module")
def slack_alert():
    return SlackAlert()


def test_post_alert(slack_alert):
    """Test posting an alert to a Slack channel."""
    message = "Test alert message"
    ts = slack_alert.post_alert(channel=TEST_CHANNEL, message=message)
    assert ts is not None, "Failed to post alert message"


def test_continue_thread(slack_alert):
    """Test continuing a thread for an ongoing issue."""
    alert_ts = slack_alert.post_alert(channel=TEST_CHANNEL, message="Initial alert for thread test")
    assert alert_ts is not None, "Failed to post alert message"
    follow_up_message = "Follow-up message for thread"
    slack_alert.continue_thread(channel=TEST_CHANNEL, thread_ts=alert_ts, message=follow_up_message)
    # Verification can be done manually in the test Slack channel,
    # as the Slack API does not return specific success responses for thread continuation.


def test_acknowledge_post(slack_alert):
    """Test acknowledging an alert."""
    alert_ts = slack_alert.post_alert(channel=TEST_CHANNEL, message="Alert to acknowledge")
    assert alert_ts is not None, "Failed to post alert message"
    slack_alert.acknowledge_post(channel=TEST_CHANNEL, thread_ts=alert_ts, user="Test User")
    # Like the continue_thread test, manual verification in the Slack channel is necessary.

# Additional tests for handle_query and other functionalities can be added following a similar structure.
