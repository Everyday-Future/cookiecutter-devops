import unittest
from config import Config
from core.adapters.llms.prompt import ClassifierPrompt
# noinspection PyProtectedMember
from core.adapters.llms.inference import _AnyscaleAgent, _OpenAIAgent, Agent, get_agent


base_msg_thread = [{"role": "user", "content": "What is the capital of France?"}]


class TestAnyscaleAgent(unittest.TestCase):
    def setUp(self):
        self.agent = _AnyscaleAgent(default_model_name="mistralai/Mistral-7B-Instruct-v0.1")

    def test_get_chat_response(self):
        response = self.agent._get_chat_response(msg_thread=base_msg_thread)
        print(f"{response=}")
        self.assertIsNotNone(response)
        self.assertIsInstance(response, str)
        # Additional assertions can be added to validate the structure of the response


class TestOpenAIAgent(unittest.TestCase):
    def setUp(self):
        self.agent = _OpenAIAgent(default_model_name=Config.OPENAI_BASE_MODEL)

    def test_get_chat_response(self):
        # Example chat message
        response = self.agent._get_chat_response(msg_thread=base_msg_thread)
        print(f"{response=}")
        self.assertIsNotNone(response)
        self.assertIsInstance(response, str)
        # Additional assertions can be added to validate the content and structure of the response


class TestAgentIntegration(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # Initialize once for all tests
        cls.manager = Agent()

    def test_get_agent_by_model_anyscale(self):
        # Example test to verify fetching an Anyscale agent works as expected
        model_name = "anyscale//mistralai/Mistral-7B-Instruct-v0.1"
        agent = get_agent(model_name)
        self.assertIsNotNone(agent)
        self.assertIsInstance(agent, _AnyscaleAgent)
        openai_model = "openai//example-model"
        self.assertIsInstance(get_agent(openai_model), _OpenAIAgent)

    def test_get_answer_from_anyscale_agent(self):
        # Integration test to check if getting an answer from an Anyscale agent works
        model_name = "mistralai/Mistral-7B-Instruct-v0.1"  # Adjust as necessary
        answer = self.manager.get_answer(message="What is the capital of France?",
                                         model_name=f"anyscale//{model_name}")
        print(f"{answer=}")
        self.assertIsNotNone(answer)
        self.assertIn("paris", answer.lower())

    def test_parallel_answer_retrieval(self):
        # Assuming all models can answer these questions. Adjust as necessary.
        model_names = ['anyscale//mistralai/Mistral-7B-Instruct-v0.1',
                       "anyscale//mistralai/Mixtral-8x7B-Instruct-v0.1",
                       "anyscale//mistralai/Mixtral-8x22B-Instruct-v0.1"]
        answers = self.manager.get_answers(message="What is the capital of France?",
                                           model_names=model_names, num_iterations=len(model_names))
        print('answers', answers)
        self.assertEqual(len(answers), len(model_names))
        for answer in answers:
            self.assertIsNotNone(answer)
            self.assertIsInstance(answer, str)
            self.assertNotEqual(answer, "")
            # Further assertions can be added based on expected content of the answers.


if __name__ == '__main__':
    unittest.main()
