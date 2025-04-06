import unittest
from unittest.mock import patch, MagicMock
import pandas as pd
# noinspection PyProtectedMember
from core.daos.llms.agent import _ModelBase, _OllamaModel


def toy_df():
    return pd.DataFrame({
        'platform': ['OpenAI', 'Anthropic', 'Google', 'OpenAI', 'Free', 'Free'],
        'model_name': ['GPT-4', 'Claude', 'PaLM', 'GPT-3.5', 'LLAMA:8b', 'LLAMA:70b'],
        'is_coding': [True, True, False, False, False, False],
        'is_uncensored': [False, True, False, False, True, True],
        'context_length': [8000, 100000, 5000, 4000, 2000, 2000],
        'is_free': [False, False, False, False, True, True],
        'num_params': [100, 200, 50, 30, 8, 70],
        'output_cost': [0.1, 0.2, 0.05, 0.03, 0, 0]
    })


class MockModel(_ModelBase):
    LLM_OPTIONS = toy_df()

    @classmethod
    def load_model_df(cls):
        pass

    # noinspection PyMethodMayBeStatic
    def _get_answer(self, prompt, model_name=None, system_prompt=None):
        return "mocked answer"

    def _get_chat_response(self, prompt, model_name=None, system_prompt=None):
        return "mocked chat response"

    def _get_embedding(self, text, model_name=None, **kwargs):
        return "mocked embedding"


class TestAgent(unittest.TestCase):
    def setUp(self):
        self.agent = MockModel(model_name='test_model')

    @patch.object(MockModel, '_get_answer')
    def test_get_answer_with_prompt(self, mock_get_answer):
        mock_get_answer.return_value = "mocked answer"
        answer = self.agent._get_answer("test prompt")
        mock_get_answer.assert_called_once_with("test prompt")
        self.assertEqual(answer, "mocked answer")

    @patch.object(MockModel, '_get_chat_response')
    def test_get_answer_with_messages(self, mock_get_chat_response):
        messages = [{"role": "user", "content": "hello"}]


class TestLocalAgent(unittest.TestCase):
    @patch('requests.post')
    def test_get_chat_response(self, mock_post):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {'message': {'content': 'test response'}}
        mock_post.return_value = mock_response
        agent = _OllamaModel(model_name="ollama//phi3:3.8b")
        response = agent.get_chat_response(message='respond with: test "response"')
        self.assertEqual(response, 'test response')
