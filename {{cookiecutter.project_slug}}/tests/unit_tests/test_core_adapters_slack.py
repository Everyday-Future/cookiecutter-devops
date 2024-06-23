
import unittest
from unittest.mock import patch, MagicMock
from slack_sdk.errors import SlackApiError
from core.adapters.alert.alert_push_slack import SlackAlert


class TestSlackAlert(unittest.TestCase):

    @patch.dict('os.environ', {'SLACK_TOKEN': 'fake-token', 'SLACK_CHANNEL': '#general'})
    @patch('core.adapters.alert.alert_push_slack.WebClient')
    def setUp(self, MockWebClient):
        self.mock_client = MockWebClient.return_value
        self.slack_alert = SlackAlert()

    def test_post_alert_success(self):
        self.mock_client.chat_postMessage.return_value = {'ts': '1234567890.123456'}
        ts = self.slack_alert.post_alert('#general', 'Test message')
        self.assertEqual(ts, '1234567890.123456')
        self.mock_client.chat_postMessage.assert_called_once_with(channel='#general', text='[INFO] Test message')

    def test_post_alert_failure(self):
        self.mock_client.chat_postMessage.side_effect = SlackApiError('Error', MagicMock())
        with self.assertRaises(RuntimeError):
            self.slack_alert.post_alert('#general', 'Test message')

    def test_continue_thread_success(self):
        self.slack_alert.continue_thread('#general', '1234567890.123456', 'Continued message')
        self.mock_client.chat_postMessage.assert_called_once_with(channel='#general', thread_ts='1234567890.123456',
                                                                  text='Continued message')

    def test_continue_thread_failure(self):
        self.mock_client.chat_postMessage.side_effect = SlackApiError('Error', MagicMock())
        with self.assertRaises(RuntimeError):
            self.slack_alert.continue_thread('#general', '1234567890.123456', 'Continued message')

    def test_acknowledge_post(self):
        with patch.object(self.slack_alert, 'continue_thread') as mock_continue_thread:
            self.slack_alert.acknowledge_post('#general', '1234567890.123456', 'test_user')
            mock_continue_thread.assert_called_once_with('#general', '1234567890.123456',
                                                         'Alert acknowledged by test_user.')

    def test_handle_query(self):
        with patch.object(self.slack_alert, 'continue_thread') as mock_continue_thread:
            self.slack_alert.handle_query('#general', '1234567890.123456', 'Test query')
            mock_continue_thread.assert_called_once_with('#general', '1234567890.123456',
                                                         'Received query: Test query. Processing...')


if __name__ == "__main__":
    unittest.main()
