# core/daos/llms/agent.py
"""

LLM Inference Adapters

Get generative text inference from local and remote LLMs

    _Agent

        Wrapper for an LLM with error handling, prompt / message handling, threading, and fallbacks.
        Abstracts the nuance away from different LLM sources and builds a toolkit around them.

        Gather data from local and remote LLMs and, if applicable, parse their outputs.

        AGENTS DO NOT HAVE INTERNAL MEMORY. Do not store persistent data in Agents. Agencies are stateful, Agents aren't.

        Agents should be thread-safe so that AgentManager and Agencies can manage them in parallel

    Agent Manager

        Universal and Easy-To-Use interface to all available Agents. Manages Agent lifecycles,
        threading and parallelization, randomization, and prompt management.

        Multithreading a query to a batch of Agents is the standard way to query Agents in this framework,
        so it makes sense to offer that at the Agent level to keep Agency code cleaner and neater.

        AgentManager is the main interface to Agents for the rest of the app.

"""
import copy
import time
import random
from itertools import cycle
from typing import List, Optional, Union
from abc import ABC, abstractmethod
from enum import Enum
import requests
import numpy as np
import tiktoken
import openai
from together import Together
from anthropic import Anthropic, InternalServerError
from config import Config


def mod_index(in_list, idx):
    """
    Get an index in a list but apply mod to the index by the length of the list so that it automatically wraps.
    """
    return in_list[idx % len(in_list)]


def count_tokens(text, model_name="o200k_base"):
    """
    Estimate the number of tokens for a sample text to help with model selection
    :param text:
    :param model_name:
    :return:
    """
    encoding = tiktoken.encoding_for_model(model_name)
    tokens = encoding.encode(text)
    return len(tokens)


def estimate_tokens(text):
    """
    Quick estimate of num_tokens for model selection
    :param text:
    :return:
    """
    average_chars_per_token = 3.5
    num_tokens = len(text) / average_chars_per_token
    return int(num_tokens)


def to_thread(message, system_prompt=None, chat_history=None, response=None):
    out_messages = []
    if system_prompt is not None:
        out_messages.append({'role': 'system', 'content': system_prompt})
    if chat_history is not None:
        for msg in chat_history:
            out_messages.append(msg)
    out_messages.append({'role': 'user', 'content': message})
    if response is not None:
        out_messages.append({'role': 'assistant', 'content': response})
    return out_messages


class InferenceModels(Enum):
    FAST = 'fast'
    SMALL = 'small'
    MED = 'med'
    LARGE = 'large'
    HUGE = 'huge'
    IMAGE = 'image'
    EMBEDDING = 'embedding'
    SAFETY = 'safety'
    UNCENSORED = 'uncensored'

    def __str__(self) -> str:
        """
        Convert enum to string representation.

        :return: String value of the enum
        :rtype: str
        """
        return str(self.value)

    @staticmethod
    def _get_model_list(inference_model: str) -> List[str]:
        """
        Get the list of models for a given inference model type.

        :param inference_model: The model type to get the list for
        :type inference_model: str
        :return: List of model names for the given type
        :rtype: List[str]
        """
        model_lists = {
            'fast': Config.DEFAULT_LLMS_FAST,
            'small': Config.DEFAULT_LLMS_SMALL,
            'med': Config.DEFAULT_LLMS_MED,
            'large': Config.DEFAULT_LLMS_LARGE,
            'huge': Config.DEFAULT_LLMS_HUGE,
            'image': Config.DEFAULT_LLMS_IMAGE_PARSE,
            'embedding': [Config.DEFAULT_EMBEDDING_MODEL],
            'safety': Config.DEFAULT_LLMS_SAFETY,
            'uncensored': Config.DEFAULT_LLMS_UNCENSORED,
        }
        return model_lists.get(inference_model, [])

    @property
    def default_model(self) -> Optional[str]:
        """
        Get the default model for a target_difficulty (first model in the list).

        :return: Name of the default model for the given difficulty, or None if not found
        :rtype: Optional[str]
        """
        models = self._get_model_list(self.value)
        return models[0] if models else None

    @property
    def random_model(self) -> Optional[str]:
        """
        Get a random model for a target_difficulty (first model in the list).

        :return: Name of the default model for the given difficulty, or None if not found
        :rtype: Optional[str]
        """
        models = self._get_model_list(self.value)
        if not models:
            return None
        return random.choice(models)

    @staticmethod
    def _get_difficulty_order() -> List['InferenceModels']:
        """
        Helper method to define the ordering of difficulty levels.

        :return: List of InferenceModels in order of increasing difficulty
        :rtype: List[InferenceModels]
        """
        return [
            InferenceModels.FAST,
            InferenceModels.SMALL,
            InferenceModels.MED,
            InferenceModels.LARGE,
            InferenceModels.HUGE
        ]

    @classmethod
    def _filter_models_by_difficulty(
            cls,
            min_difficulty: Optional['InferenceModels'] = None,
            max_difficulty: Optional['InferenceModels'] = None,
            target_difficulty: Optional['InferenceModels'] = None
    ) -> List['InferenceModels']:
        """
        Helper method to filter models based on difficulty constraints.

        :param min_difficulty: Minimum difficulty level to include
        :type min_difficulty: Optional[InferenceModels]
        :param max_difficulty: Maximum difficulty level to include
        :type max_difficulty: Optional[InferenceModels]
        :param target_difficulty: Specific difficulty level to target
        :type target_difficulty: Optional[InferenceModels]
        :return: List of valid InferenceModels meeting the criteria
        :rtype: List[InferenceModels]
        """
        difficulty_order = cls._get_difficulty_order()
        assert min_difficulty in difficulty_order or min_difficulty is None
        assert max_difficulty in difficulty_order or max_difficulty is None
        assert target_difficulty in difficulty_order or target_difficulty is None
        if target_difficulty is not None:
            if target_difficulty in difficulty_order:
                return [target_difficulty]
            else:
                return []
        valid_models = difficulty_order.copy()
        if min_difficulty in difficulty_order:
            min_idx = difficulty_order.index(min_difficulty)
            valid_models = valid_models[min_idx:]
        if max_difficulty in difficulty_order:
            max_idx = difficulty_order.index(max_difficulty)
            valid_models = valid_models[:max_idx + 1]
        return valid_models

    @classmethod
    def to_list(
            cls,
            min_difficulty: Optional['InferenceModels'] = None,
            max_difficulty: Optional['InferenceModels'] = None,
            target_difficulty: Optional['InferenceModels'] = None
    ) -> List[str]:
        """
        Get a flattened list of models to pull from, optionally thresholded to a minimum / maximum difficulty.

        Excludes the image and embedding models from this query, since they're for specialized tasks.
        The list is deduplicated to remove some models that may be shared between difficulty levels.

        :param min_difficulty: Smallest InferenceModels to be included
        :type min_difficulty: Optional[InferenceModels]
        :param max_difficulty: Largest InferenceModels to be included
        :type max_difficulty: Optional[InferenceModels]
        :param target_difficulty: Specific InferenceModels to be included
        :type target_difficulty: Optional[InferenceModels]
        :return: Deduplicated list of model names meeting the difficulty criteria
        :rtype: List[str]
        """
        valid_difficulties = cls._filter_models_by_difficulty(
            min_difficulty, max_difficulty, target_difficulty
        )
        all_models = []
        for difficulty in valid_difficulties:
            models = cls._get_model_list(difficulty.value)
            all_models.extend(models)
        return list(dict.fromkeys(all_models))

    @classmethod
    def select_random(
            cls,
            min_difficulty: Optional['InferenceModels'] = None,
            max_difficulty: Optional['InferenceModels'] = None,
            target_difficulty: Optional['InferenceModels'] = None
    ) -> Optional[str]:
        """
        Get a random model from the filtered list of models based on difficulty criteria.

        :param min_difficulty: Smallest InferenceModels to be included
        :type min_difficulty: Optional[InferenceModels]
        :param max_difficulty: Largest InferenceModels to be included
        :type max_difficulty: Optional[InferenceModels]
        :param target_difficulty: Specific InferenceModels to be included
        :type target_difficulty: Optional[InferenceModels]
        :return: Name of randomly selected model, or None if no models match criteria
        :rtype: Optional[str]
        """
        models = cls.to_list(min_difficulty, max_difficulty, target_difficulty)
        return random.choice(models) if models else None

    @classmethod
    def select_random_list(
            cls,
            count: int,
            min_difficulty: Optional['InferenceModels'] = None,
            max_difficulty: Optional['InferenceModels'] = None,
            target_difficulty: Optional['InferenceModels'] = None
    ) -> List[str]:
        """
        Get a list of randomly selected models with replacement based on difficulty criteria.

        :param count: Number of models to select
        :type count: int
        :param min_difficulty: Smallest InferenceModels to be included
        :type min_difficulty: Optional[InferenceModels]
        :param max_difficulty: Largest InferenceModels to be included
        :type max_difficulty: Optional[InferenceModels]
        :param target_difficulty: Specific InferenceModels to be included
        :type target_difficulty: Optional[InferenceModels]
        :return: List of randomly selected model names
        :rtype: List[str]
        :raises ValueError: If count is less than 1
        """
        if count < 1:
            raise ValueError("Count must be at least 1")
        models = cls.to_list(min_difficulty, max_difficulty, target_difficulty)
        if not models:
            return []
        return random.choices(models, k=count)


class _ModelBase(ABC):
    """
    Base class for LLM Inference model adapters
    One _Model per model, represented as a collection in Agent
    """

    def __init__(self, model_name=None, embedding_model_name=None,
                 default_num_tries=3, default_temperature=0.2, verbose=False, **kwargs):
        # Automatically unpack models and defaults based on SOURCE_NAME for the subclass
        self.model_name = model_name or InferenceModels.FAST.random_model
        if '//' in self.model_name:
            self.model_name = self.model_name.split('//')[-1]
        self.embedding_model_name = embedding_model_name or Config.DEFAULT_EMBEDDING_MODEL
        if '//' in self.embedding_model_name:
            self.embedding_model_name = self.embedding_model_name.split('//')[-1]
        if self.model_name is None and self.embedding_model_name is None:
            raise AttributeError("Either model_name or embedding_model_name must be specfied for an Agent")
        # Other helpful inference defaults
        self.default_temperature = default_temperature
        self.default_num_tries = default_num_tries
        self.request_count = 0
        self.request_limit = 9999999
        self.total_tokens = 0
        self.estimated_cost = 0.0
        self.tokens_per_second = None
        self.tokens_per_second_in = None
        self.tokens_per_second_out = None
        self.verbose = verbose

    def __str__(self):
        return (f"<Model.{self.__class__.__name__}({self.model_name}) {self.default_temperature=} {self.verbose=} "
                f"{self.tokens_per_second_in=} {self.tokens_per_second_out=} {self.tokens_per_second=} >")

    def print(self, *args):
        if self.verbose is True:
            print(*args)

    @abstractmethod
    def _get_chat_response(self, msg_thread: list[dict], model_name=None, **kwargs):
        raise NotImplementedError('each agent must implement its own _get_chat_response function')

    @abstractmethod
    def _get_embedding(self, text, model_name=None, **kwargs):
        raise NotImplementedError('each agent must implement its own _get_embedding function')

    def get_chat_response(self, message=None, system_prompt=None, chat_history=None, msg_thread=None,
                          model_name=None, **kwargs):
        """
        Get an answer from the Agent for either a prompt string or an OpenAI-style chat messages dict.
        """
        # Parse the message
        if msg_thread is None:
            if message is None:
                raise ValueError("Message must be provided as message or msg_thread")
            else:
                msg_thread = to_thread(message=message, system_prompt=system_prompt, chat_history=chat_history)
        # Submit for inference
        for idx in range(self.default_num_tries):
            answer = None
            try:
                answer = self._get_chat_response(msg_thread=msg_thread, model_name=model_name, **kwargs)
                self.request_count += 1
                if answer is not None:
                    return answer
            except (KeyError, IndexError):
                raise KeyError(f"content not returned. Instead returned: {answer}")
            except (openai.RateLimitError, openai.APIError, openai.APIConnectionError) as err:
                print(f'{err}... Waiting to restart.')
            time.sleep(2 ** idx)

    def get_embedding(self, text: Union[str, list], model_name=None, **kwargs):
        emb_list = self._get_embedding(text=text, model_name=model_name, **kwargs)
        if isinstance(emb_list, list) and len(emb_list) > 0:
            emb_list = np.array(emb_list, dtype=np.float32)
        return emb_list


class _OllamaModel(_ModelBase):
    """
    Wrapper for all LLM services that we use
    """

    def __init__(self, model_name=None, embedding_model_name=None, **kwargs):
        # Set ollama model defaults
        self.model_name = model_name
        if model_name is not None and '//' in model_name and ':' in model_name.split('//')[0]:
            self.model_name = self.model_name.split('//')[-1]
            self.base_url = model_name.split('//')[0].split(':')[1]
            # noinspection HttpUrlsUsage
            self.base_url = f"http://{self.base_url}:11434"
        else:
            self.base_url = Config.LOCAL_OLLAMA_URL
        self.tokens_per_second = None
        super().__init__(model_name=model_name,
                         embedding_model_name=embedding_model_name,
                         **kwargs)

    def pull_model(self, model_name=None):
        """
        Request that ollama pull or update the specified model

        Args:
            model_name: Name of the model to pull. If None, uses the default model name.

        Returns:
            dict: Response from the pull API if successful, None otherwise
        """
        model_name = model_name or self.model_name
        if '//' in model_name:
            model_name = model_name.split('//')[-1]
        print(f"Pulling model: {model_name}...")
        data = {"model": model_name}
        try:
            response = requests.post(f"{self.base_url}/api/pull", json=data)
            response.raise_for_status()
            print(f"Successfully pulled {model_name=}...")
            return response.json()
        except requests.exceptions.RequestException as e:
            self.print(f"Error pulling {model_name=}: {str(e)}")
            return None

    def delete_model(self, model_name=None):
        """
        Delete a model from ollama

        Args:
            model_name: Name of the model to delete. If None, uses the default model name.

        Returns:
            bool: True if deletion was successful, False otherwise
        """
        model_name = model_name or self.model_name
        if '//' in model_name:
            model_name = model_name.split('//')[-1]

        print(f"Deleting model: {model_name}...")
        data = {"name": model_name}
        try:
            response = requests.delete(f"{self.base_url}/api/delete", json=data)
            response.raise_for_status()
            print(f"Successfully deleted {model_name}")
            return True
        except requests.exceptions.RequestException as e:
            self.print(f"Error deleting {model_name}: {str(e)}")
            return False

    def _get_chat_response(self, msg_thread: list[dict], model_name=None, **kwargs):
        model = model_name or self.model_name

        def make_request():
            data = {
                "model": model,
                "messages": msg_thread,
                "options": {
                    "temperature": float(kwargs.get('temperature', self.default_temperature))
                },
                "stream": False
            }
            if kwargs.get('max_out_tokens') is not None:
                # Limit the tokens in the response for time management
                data["options"]["num_predict"] = kwargs['max_out_tokens']
            start_time = time.time()
            response = requests.post(f"{self.base_url}/api/chat", json=data)
            return response
        # First attempt
        self.print("----- standard request to local Ollama -----")
        response = make_request()
        # If model not found, try pulling it
        if response.status_code == 404 or "model not found" in response.text.lower():
            self.print(f"Model {model} not found with {response.text=}  Attempting to pull...")
            if self.pull_model(model):
                self.print(f"Model {model} pulled successfully. Retrying request...")
                time.sleep(0.1)
                response = make_request()
            else:
                self.print(f"Failed to pull model {model}")
                return None
        if response.status_code == 200:
            resp_data = response.json()
            if 'prompt_eval_count' in resp_data and 'prompt_eval_duration' in resp_data:
                self.tokens_per_second_in = (float(resp_data['prompt_eval_count']) /
                                             float(resp_data['prompt_eval_duration']) * (10.0 ** 9.0))
            if 'eval_count' in resp_data and 'eval_duration' in resp_data:
                self.tokens_per_second_out = (float(resp_data['eval_count']) /
                                              float(resp_data['eval_duration']) * (10.0 ** 9.0))
            return resp_data['message']['content']
        else:
            print(f"Error: Received status code {response.status_code} for {self.base_url}/api/chat and {model=}")
            self.print(f'{response.text=}')
            return None

    def _get_embedding(self, text: Union[str, list], model_name=None, dimensions=None, **kwargs):
        model = model_name or self.embedding_model_name

        def make_request():
            data = {
                "model": model,
                "input": text
            }
            return requests.post(f"{self.base_url}/api/embed", json=data)

        # First attempt
        response = make_request()
        # If model not found, try pulling it
        if response.status_code == 404 or "model not found" in response.text.lower():
            self.print(f"Embedding model {model} not found. Attempting to pull...")
            if self.pull_model(model):
                self.print(f"Model {model} pulled successfully. Retrying request...")
                response = make_request()
            else:
                self.print(f"Failed to pull model {model}")
                return None
        if response.status_code == 200:
            resp_data = response.json()
            # evaluate outputs for single call or batch
            if isinstance(text, str):
                embed_vec = resp_data['embeddings'][0]
                if dimensions is not None:
                    embed_vec = embed_vec[:dimensions]
            else:
                embed_vec = resp_data['embeddings']
                if dimensions is not None:
                    embed_vec = [emb[:dimensions] for emb in embed_vec]
            if 'prompt_eval_count' in resp_data and 'total_duration' in resp_data:
                self.tokens_per_second = (float(resp_data['prompt_eval_count']) /
                                          float(resp_data['total_duration']) * (10.0 ** 9.0))
            return embed_vec
        else:
            print(f"Error: Received status code {response.status_code} for {self.base_url}/api/embed and {model=}")
            self.print(f'{response.text=}')
            return None

    def list_models(self):
        response = requests.get(f"{self.base_url}/api/tags")
        if response.status_code == 200:
            return response.json()
        else:
            print(f"Error: Received status code {response.status_code} for {self.base_url}/api/tags")
            self.print(f'{response.text=}')
            return None


class _OpenAIModel(_ModelBase):
    """
    Chat interface to OpenAI models
    """

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        assert Config.OPENAI_API_KEY is not None
        self.client = openai.OpenAI(api_key=copy.deepcopy(Config.OPENAI_API_KEY))

    def _get_chat_response(self, msg_thread: list[dict], model_name=None, **kwargs):
        start_time = time.time()
        completion = self.client.chat.completions.create(
            model=model_name or self.model_name,
            messages=msg_thread,
            temperature=float(kwargs.get('temperature', self.default_temperature)),
            max_tokens=kwargs.get("max_out_tokens")

        )
        total_time = time.time() - start_time
        self.print(f"total elapsed time: {time.time() - start_time}")
        self.print('completion', completion)
        est_tok_per_sec = completion.usage.total_tokens / total_time
        self.tokens_per_second_in = est_tok_per_sec
        self.tokens_per_second_out = est_tok_per_sec
        return completion.choices[0].message.content

    def _get_embedding(self, text, model_name=None, **kwargs):
        raise NotImplementedError("embeddings not currently implemented for OpenAI, "
                                  "since they're expensive and low-quality.")


class _AnthropicModel(_ModelBase):
    """
    Chat interface to OpenAI models
    """

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        assert Config.ANTHROPIC_API_KEY is not None
        self.client = Anthropic(api_key=copy.deepcopy(Config.ANTHROPIC_API_KEY))

    def _get_chat_response(self, msg_thread: list[dict], model_name=None, **kwargs):
        start_time = time.time()
        try:
            completion = self.client.messages.create(
                max_tokens=kwargs.get("max_out_tokens", 4096),
                model=model_name or self.model_name,
                messages=msg_thread,
                temperature=float(kwargs.get('temperature', self.default_temperature))
            )
        except InternalServerError:
            time.sleep(5.0 + random.random())
            completion = self.client.messages.create(
                max_tokens=kwargs.get("max_out_tokens", 4096),
                model=model_name or self.model_name,
                messages=msg_thread,
                temperature=float(kwargs.get('temperature', self.default_temperature))
            )
        total_time = time.time() - start_time
        self.print(f"total elapsed time: {time.time() - start_time}")
        self.print('completion', completion)
        est_tok_per_sec = (completion.usage.input_tokens + completion.usage.output_tokens) / total_time
        self.tokens_per_second_in = est_tok_per_sec
        self.tokens_per_second_out = est_tok_per_sec
        return completion.content[0].text

    def _get_embedding(self, text, model_name=None, **kwargs):
        raise NotImplementedError("embeddings not currently implemented for OpenAI, "
                                  "since they're expensive and low-quality.")

    def _chat_response_batch(self, text, model_name=None, **kwargs):
        raise NotImplementedError("need to implement Batches API for discount")


class _TogetherModel(_ModelBase):
    """
    Chat interface to Together models
    """

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        assert Config.TOGETHER_API_KEY is not None
        self.client = Together(api_key=copy.deepcopy(Config.TOGETHER_API_KEY))
        self.model_name = kwargs.get('default_model_name', kwargs.get('model_name'))
        if self.model_name is not None:
            self.model_name = self.model_name.split('//')[-1]

    def _get_chat_response(self, msg_thread: list[dict], model_name=None, **kwargs):
        start_time = time.time()
        self.print(f"_get_chat_response() {model_name or self.model_name}")
        # self.print(f"_get_chat_response() {msg_thread=}")
        # self.print(f"_get_chat_response() {type(msg_thread[0]['content'])=}")
        self.print(f"_get_chat_response() {float(kwargs.get('temperature', self.default_temperature))=}")
        self.print(f"_get_chat_response() {kwargs.get('max_out_tokens')=}")
        completion = self.client.chat.completions.create(
            model=model_name or self.model_name,
            messages=msg_thread,
            temperature=float(kwargs.get('temperature', self.default_temperature)),
            max_tokens=kwargs.get("max_out_tokens")
        )
        total_time = time.time() - start_time
        self.print(f"total elapsed time: {time.time() - start_time}")
        self.print('completion', completion)
        est_tok_per_sec = completion.usage.total_tokens / total_time
        self.tokens_per_second = est_tok_per_sec
        self.tokens_per_second_in = est_tok_per_sec
        self.tokens_per_second_out = est_tok_per_sec
        return completion.choices[0].message.content

    def _get_embedding(self, text, model_name=None, **kwargs):
        start_time = time.time()
        response = self.client.embeddings.create(
            model=model_name or self.embedding_model_name,
            input=text
        )
        total_time = time.time() - start_time
        est_tok_per_sec = estimate_tokens(text) / total_time
        self.tokens_per_second = est_tok_per_sec
        self.tokens_per_second_in = est_tok_per_sec
        self.tokens_per_second_out = est_tok_per_sec
        return response.data[0].embedding


class _GroqModel(_ModelBase):
    """
    Chat interface to Groq models
    """

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        from groq import Groq
        assert Config.GROQ_API_KEY is not None
        self.client = Groq(api_key=copy.deepcopy(Config.GROQ_API_KEY))
        self.request_limit = 14000

    def _get_chat_response(self, msg_thread: list[dict], model_name=None, **kwargs):
        start_time = time.time()
        chat_completion = self.client.chat.completions.create(
            messages=msg_thread,
            model=model_name or self.model_name,
            temperature=float(kwargs.get('temperature', self.default_temperature)),
            max_tokens=kwargs.get("max_out_tokens")
        )
        self.print(f"total elapsed time: {time.time() - start_time}")
        self.print('chat_completion', chat_completion)
        self.tokens_per_second_in = chat_completion.usage.prompt_tokens / chat_completion.usage.prompt_time
        self.tokens_per_second_out = chat_completion.usage.completion_tokens / chat_completion.usage.completion_time
        return chat_completion.choices[0].message.content

    def _get_embedding(self, text, model_name=None, **kwargs):
        raise NotImplementedError("embeddings not currently implemented for Groq.")


class Agent:
    """
    Main factory for agents.
    Generate batches of agents or threaded batched queries to Agents, even mixing and matching sources.
    Design to operate in serial or parallel.
    """
    LLM_OPTIONS = None
    EMBEDDING_MODEL = Config.DEFAULT_EMBEDDING_MODEL

    def __init__(self, model_name: str, temperature: float = 0.2,
                 max_out_tokens: int = None, verbose: bool = False):
        """
        Set up and configure a new model for use in Prompts
        :param model_name: specific model name to use as platform//model
        :param temperature: (optional) default temperature for queries, adding randomness to outputs
        :param max_out_tokens: (optional) What is the length limit for the answer?
        :param verbose: (optional) print out admin information (default False)
        """
        # Get the model by name or choose one within constraints
        self.model_name = model_name
        self.model = self._get_agent_by_model_name(model_spec=self.model_name, temperature=temperature)
        self.temperature = temperature
        # configure the new model
        self.model.model_name = self.model_name.split('//')[-1]
        self.model.default_temperature = self.temperature
        self.model.verbose = verbose
        self.max_out_tokens = max_out_tokens

    def __str__(self):
        return f"<Agent {self.model_name=} {self.temperature=} {self.max_out_tokens=} {self.model.verbose=}>"

    @classmethod
    def from_model_type(cls, model_type: InferenceModels, temperature: float = 0.2,
                        max_out_tokens: int = None, verbose: bool = False):
        """
        Set up and configure a new model for use in Prompts
        :param model_type: specific InferenceModel type to pull from
        :param temperature: (optional) default temperature for queries, adding randomness to outputs
        :param max_out_tokens: (optional) What is the length limit for the answer?
        :param verbose: (optional) print out admin information (default False)
        """
        return cls(model_name=model_type.default_model, temperature=temperature,
                   max_out_tokens=max_out_tokens, verbose=verbose)

    @property
    def tokens_per_second_in(self):
        """
        Models should measure their throughput and update this value after inference
        :return:
        """
        return self.model.tokens_per_second_in

    @property
    def tokens_per_second_out(self):
        """
        Models should measure their throughput and update this value after inference
        :return:
        """
        return self.model.tokens_per_second_out

    @property
    def tokens_per_second(self):
        """
        Models should measure their throughput and update this value after inference
        :return:
        """
        return self.model.tokens_per_second

    @staticmethod
    def _get_agent_by_model_name(model_spec: str, temperature: float = 0.2):
        """
        Get the agent for the specified inference source in the model_name
        """
        platform, model_name = model_spec.split('//')
        if platform.startswith('ollama'):
            return _OllamaModel(model_name=model_spec, default_temperature=temperature)
        elif platform == 'anthropic':
            return _AnthropicModel(model_name=model_name, default_temperature=temperature)
        elif platform == 'openai':
            return _OpenAIModel(model_name=model_name, default_temperature=temperature)
        elif platform == 'groq':
            return _GroqModel(model_name=model_name, default_temperature=temperature)
        elif platform == 'together':
            return _TogetherModel(model_name=model_name, default_temperature=temperature)
        else:
            raise ValueError(f"no model found for {model_name=} and {platform=}")

    def get_answer(self, message=None, system_prompt=None, chat_history=None, msg_thread=None, **kwargs):
        """
        Get an answer from the Agent for either a prompt string or an OpenAI-style chat messages dict.
        """
        if "max_out_tokens" not in kwargs:
            kwargs["max_out_tokens"] = self.max_out_tokens
        model_name = self.model_name.split('//')[-1]
        print(f"get_answer with model_name={model_name}")
        return self.model.get_chat_response(message=message, system_prompt=system_prompt, chat_history=chat_history,
                                            model_name=model_name, msg_thread=msg_thread, **kwargs)

    def get_embedding(self, text_sample: str, dimensions=None):
        """
        Get a single embedding for an item
        """
        return self.model.get_embedding(text=text_sample, dimensions=dimensions)

    @classmethod
    def get_random_agents(
            cls,
            count: int,
            min_difficulty: Optional[InferenceModels] = None,
            max_difficulty: Optional[InferenceModels] = None,
            target_difficulty: Optional[InferenceModels] = None,
            **kwargs
    ) -> List['Agent']:
        model_list = InferenceModels.select_random_list(count=count,
                                                        min_difficulty=min_difficulty,
                                                        max_difficulty=max_difficulty,
                                                        target_difficulty=target_difficulty)
        if 'model_name' in kwargs:
            del kwargs['model_name']
        return [cls(model_name=model_name, **kwargs) for model_name in model_list]

    @classmethod
    def get_agents(cls, model_name_list: Optional[List[str]] = None, num_models: int = 3, **kwargs):
        """
        Get a batch of custom agents with all the same kwargs but different model names for Prompt.get_answers()
        :param model_name_list:
        :param num_models:
        :param kwargs:
        :return:
        """
        if model_name_list is not None:
            return [cls(model_name=model_name, **kwargs) for model_name in model_name_list]
        else:
            cycled_models = cycle(Config.DEFAULT_INFERENCE_MODELS)
            return [cls(model_name=next(cycled_models), **kwargs) for _ in range(num_models)]
