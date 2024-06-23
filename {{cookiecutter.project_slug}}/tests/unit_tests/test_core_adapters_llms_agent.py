import unittest
from unittest.mock import patch, MagicMock
from core.adapters.llms.inference import _Agent, _LocalAgent


class MockAgent(_Agent):
    def _get_answer(self, prompt, model_name=None, system_prompt=None):
        return "mocked answer"

    def _get_chat_response(self, prompt, model_name=None, system_prompt=None):
        return "mocked chat response"

    def _get_embedding(self, text):
        return "mocked embedding"


class TestAgent(unittest.TestCase):
    def setUp(self):
        self.agent = MockAgent(default_model_name='test_model')

    @patch.object(MockAgent, '_get_answer')
    def test_get_answer_with_prompt(self, mock_get_answer):
        mock_get_answer.return_value = "mocked answer"
        answer = self.agent._get_answer("test prompt")
        mock_get_answer.assert_called_once_with("test prompt")
        self.assertEqual(answer, "mocked answer")

    @patch.object(MockAgent, '_get_chat_response')
    def test_get_answer_with_messages(self, mock_get_chat_response):
        messages = [{"role": "user", "content": "hello"}]


class TestLocalAgent(unittest.TestCase):
    @patch('requests.post')
    def test_get_chat_response(self, mock_post):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'choices': [{'message': {'content': 'test response'}}]
        }
        mock_post.return_value = mock_response
        agent = _LocalAgent()
        response = agent.get_chat_response(message='respond with: test "response"')
        self.assertEqual(response, 'test response')
