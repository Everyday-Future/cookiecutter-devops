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
import requests
from abc import ABC, abstractmethod
from concurrent.futures import ThreadPoolExecutor, as_completed
import openai
from langchain_community.llms import Ollama
from config import Config


def mod_index(in_list, idx):
    """
    Get an index in a list but apply mod to the index by the length of the list so that it automatically wraps.
    """
    return in_list[idx % len(in_list)]


class _Agent(ABC):
    """
    Base class for LLM Inference Adapters
    """
    BASE_MODEL_NAMES = {
        # source//model: $/Mtok
        "openai//gpt-4o": 10.0,
        "anyscale//mistralai/Mistral-7B-Instruct-v0.1": 0.15,
        "anyscale//mistralai/Mixtral-8x7B-Instruct-v0.1": 0.5,
        "anyscale//mistralai/Mixtral-8x22B-Instruct-v0.1": 1.0,
        "groq//mistralai/Mixtral-8x7B-Instruct-v0.1": 0.27,
        'local//mistral:instruct': 0.0,
        'local//zephyr': 0.0,
        'local//openhermes': 0.0
    }
    BASE_EMBEDDING_MODEL_NAMES = {
        # source//model: $/Mtok
        'openai//text-embedding-3-small': 0.0,
        'openai//text-embedding-3-large': 0.0,
        'anyscale//BAAI/bge-large-en-v1.5': 0.0,
        'anyscale//thenlper/gte-large': 0.0,
        "local//nomic-embed-text": 0.0,
    }
    SOURCE_NAME = 'unspecified'

    def __init__(self, default_model_name=None, default_embedding_model_name=None,
                 default_num_tries=3, default_temperature=0.5, **kwargs):
        # Automatically unpack models and defaults based on SOURCE_NAME for the subclass
        self.model_names = {key: val for key, val in self.BASE_MODEL_NAMES.items()
                            if key.startswith(self.SOURCE_NAME)}
        self.default_model_name = default_model_name or list(self.model_names.keys())[0]
        self.embedding_model_names = {key: val for key, val in self.BASE_EMBEDDING_MODEL_NAMES.items()
                                      if key.startswith(self.SOURCE_NAME)}
        if len(self.embedding_model_names.keys()) > 0:
            self.default_embedding_model_name = (default_embedding_model_name or
                                                 list(self.embedding_model_names.keys())[0])
        else:
            self.default_embedding_model_name = default_embedding_model_name
        # Other helpful inference defaults
        self.default_temperature = default_temperature
        self.default_num_tries = default_num_tries
        self.total_tokens = 0
        self.estimated_cost = 0.0

    @staticmethod
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

    @abstractmethod
    def _get_chat_response(self, msg_thread: list[dict], model_name=None, **kwargs):
        raise NotImplementedError('each agent must implement its own _get_chat_response function')

    @abstractmethod
    def _get_embedding(self, text, model_name=None):
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
                msg_thread = self.to_thread(message=message, system_prompt=system_prompt, chat_history=chat_history)
        # Submit for inference
        for idx in range(self.default_num_tries):
            answer = None
            try:
                answer = self._get_chat_response(msg_thread=msg_thread, model_name=model_name, **kwargs)
                if answer is not None:
                    return answer
            except (KeyError, IndexError):
                raise KeyError(f"content not returned. Instead returned: {answer}")
            except (openai.RateLimitError, openai.APIError, openai.APIConnectionError) as err:
                print(f'{err}... Waiting to restart.')
            time.sleep(2 ** idx)

    def get_embedding(self, text, model_name=None):
        return self._get_embedding(text=text, model_name=model_name)


class _LocalAgent(_Agent):
    """
    Wrapper for all LLM services that we use
    """
    SOURCE_NAME = 'local'
    # Assuming your local server does not require an API key but adjust as necessary
    base_url = Config.LOCAL_OLLAMA_URL

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.ollama = Ollama(base_url='http://localhost:11434', model=self.default_model_name, mirostat=2)

    def _get_chat_response(self, msg_thread: list[dict], model_name=None, **kwargs):
        print("----- standard request to local Ollama -----")
        model = model_name or self.default_model_name
        data = {
            "model": model,
            "messages": msg_thread,
            "options": {
                "temperature": float(kwargs.get('temperature', self.default_temperature))
            }
        }
        # Assuming the endpoint is '/chat/completions' on your local server
        response = requests.post(f"{self.base_url}/chat/completions", json=data)
        if response.status_code == 200:
            # Adjust the response parsing based on your local server's response structure
            return response.json()['choices'][0]['message']['content']
        else:
            print(f"Error: Received status code {response.status_code}")
            return None

    def _get_embedding(self, text: str, model_name=None, **kwargs):
        # print("----- standard request to local Ollama -----")
        model = model_name or "nomic-embed-text"
        data = {
            "model": model,
            "prompt": text,
        }
        # Assuming the endpoint is '/chat/completions' on your local server
        response = requests.post(f"{self.base_url}/api/embeddings", json=data)
        if response.status_code == 200:
            # Adjust the response parsing based on your local server's response structure
            return response.json()['embedding']
        else:
            print(f"Error: Received status code {response.status_code}")
            return None


class _AnyscaleAgent(_Agent):
    """
    Connect to models in anyscale

    Here are the context length for the base models
                                    context   $/MM tok
    Mistral-7B-Instruct-v0.1	    16384     0.15
    HuggingFaceH4/zephyr-7b-beta    16384     0.15
    NeuralHermes-2.5-Mistral-7B     16384     0.15
    Open-Orca/Mistral-7B-OpenOrca   8192      0.15
    Llama-2-7b-chat-hf	            4096      0.15
    Llama-2-13b-chat-hf	            4096      0.25
    Mixtral-8x7B-Instruct-v0.1	    32768     0.50
    Llama-2-70b-chat-hf	            4096      1.0
    CodeLlama-34b-Instruct-hf	    16384     1.0
    CodeLlama-70b-Instruct-hf       4096      1.0

    """
    SOURCE_NAME = 'anyscale'

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.client = openai.OpenAI(
            base_url=Config.ANYSCALE_BASE_URL,
            api_key=Config.ANYSCALE_API_KEY
        )

    def _get_chat_response(self, msg_thread: list[dict], model_name=None, **kwargs):
        """
        Pass a chat message session to the remote model in order to gather its response.
        """
        model_name = model_name or self.default_model_name
        # Note: not all arguments are currently supported and will be ignored by the backend.
        chat_completion = self.client.chat.completions.create(
            model=model_name,
            messages=msg_thread,
            temperature=float(kwargs.get('temperature', self.default_temperature))
        )
        out_data = chat_completion.model_dump()
        # print(f"{out_data['usage']=}")
        if 'choices' in out_data and len(out_data['choices']) > 0:
            choice = out_data['choices'][-1]
            if 'message' in choice and 'content' in choice['message']:
                return choice['message']['content']

    def _get_embedding(self, text: str, model_name=None, **kwargs):
        model = model_name or "thenlper/gte-large"
        embedding = self.client.embeddings.create(
            model=model,
            input="Your text string goes here",
        )
        response = embedding.model_dump()
        if response:
            # Adjust the response parsing based on your local server's response structure
            return response['data']['embedding']
        else:
            print(f"Error: Received {response=}")
            return None


class _OpenAIAgent(_Agent):
    """
    Chat interface to OpenAI models
    """
    SOURCE_NAME = 'openai'

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.client = openai.OpenAI(api_key=Config.OPENAI_API_KEY)

    def _get_chat_response(self, msg_thread: list[dict], model_name=None, **kwargs):
        completion = self.client.chat.completions.create(
            model=model_name or self.default_model_name,
            messages=msg_thread,
            temperature=float(kwargs.get('temperature', self.default_temperature))
        )
        return completion.choices[0].message.content

    def _get_embedding(self, text, model_name=None):
        raise NotImplementedError("embeddings not currently implemented for OpenAI, "
                                  "since they're expensive and low-quality.")


class _AnthropicAgent(_Agent):
    """
    Chat interface to OpenAI models
    """
    SOURCE_NAME = 'anthropic'

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.client = openai.OpenAI(api_key=Config.OPENAI_API_KEY)

    def _get_chat_response(self, msg_thread: list[dict], model_name=None, **kwargs):
        completion = self.client.chat.completions.create(
            model=model_name or self.default_model_name,
            messages=msg_thread,
            temperature=float(kwargs.get('temperature', self.default_temperature))
        )
        return completion.choices[0].message.content

    def _get_embedding(self, text, model_name=None):
        raise NotImplementedError("embeddings not currently implemented for OpenAI, "
                                  "since they're expensive and low-quality.")


def get_model_list():
    """
    Get the lists of available models for the specified inference sources in Config as source//model_name
    """
    excl = (None, '', ' ')
    model_list = []
    if Config.LOCAL_OLLAMA_URL not in excl and Config.LOCAL_OLLAMA_IS_ACTIVE:
        model_list.extend(_LocalAgent().model_names)
    if Config.OPENAI_API_KEY not in excl:
        model_list.extend(_OpenAIAgent().model_names)
    if Config.ANYSCALE_API_KEY not in excl:
        model_list.extend(_AnyscaleAgent().model_names)
    if Config.ANTHROPIC_API_KEY not in excl:
        model_list.extend(_AnthropicAgent().model_names)
    return copy.deepcopy(model_list)


def get_agent(model_name):
    """
    Get the agent for the specified inference source in the model_name
    """
    assert '//' in model_name, f"Model {model_name} does not contain a '//' source prefix"
    if model_name.startswith('local'):
        return _LocalAgent(model_name=model_name)
    elif model_name.startswith('anthropic'):
        return _AnthropicAgent(model_name=model_name)
    elif model_name.startswith('openai'):
        return _OpenAIAgent(model_name=model_name)
    elif model_name.startswith('anyscale'):
        return _AnyscaleAgent(model_name=model_name)


class Agent:
    """
    Main factory for agents.
    Generate batches of agents or threaded batched queries to Agents, even mixing and matching sources.
    Design to operate in serial or parallel.
    """

    def __init__(self, model_names=None):
        # Filter models to domain and get Agents from them
        if model_names is None:
            model_names = get_model_list()
        if not isinstance(model_names, list):
            model_names = [model_names]
        self.model_names = model_names

    @staticmethod
    def to_thread(message, system_prompt=None, chat_history=None, response=None):
        return _Agent.to_thread(message, system_prompt, chat_history, response)

    def _build_plan_for_answers(self, msg_thread_list, model_names, num_iterations: int = None, **kwargs):
        """
        Build a list of inference data for threaded inference
        """
        if model_names is None:
            model_names = copy.deepcopy(self.model_names)
        elif not isinstance(model_names, list):
            model_names = [model_names]
        if not isinstance(msg_thread_list[0], list):
            msg_thread_list = [msg_thread_list]
        num_iterations = max(len(msg_thread_list or []), num_iterations or 1)
        return [{'model': random.choice(model_names), 'msg_thread': mod_index(msg_thread_list, idx)}
                for idx in range(num_iterations)]

    @classmethod
    def process_plan_item(cls, plan_item: dict):
        """
        Process a single item in a plan item list, like a worker on a queue
        """
        agent = get_agent(plan_item['model'])
        return agent.get_chat_response(msg_thread=plan_item.get('msg_thread').copy(),
                                       model_name=plan_item['model'].split('//')[1])

    def _execute_plan_for_answers(self, answer_plan: list[dict], do_threaded=True):
        """
        Get inference in parallel for a specific inference source.
        """
        # Define how many workers you want in the ThreadPool. This could be based on the number of available cores,
        # the nature of the tasks, or any other criteria relevant to your application's performance and API rate limits.
        # For API calls, the optimal number might be lower than the number of cores, considering rate limits.
        num_workers = min(8, len(answer_plan))
        responses = []  # This will store the results.
        if len(answer_plan) > 1 and do_threaded is True:
            # Using ThreadPoolExecutor to execute each plan item in parallel
            with ThreadPoolExecutor(max_workers=num_workers) as executor:
                # Create a dictionary to hold future-to-plan item mapping
                future_to_plan = {executor.submit(self.process_plan_item, plan): plan for plan in answer_plan}
                for future in as_completed(future_to_plan):
                    plan_item = future_to_plan[future]
                    try:
                        result = future.result()
                    except Exception as exc:
                        print(f'{plan_item} generated an exception: {exc}')
                    else:
                        responses.append(result)
            return responses
        else:
            return [self.process_plan_item(plan) for plan in answer_plan]

    def get_answer(self, message=None, system_prompt=None, chat_history=None, msg_thread=None,
                   model_name=None, **kwargs):
        """
        Get an answer from the Agent for either a prompt string or an OpenAI-style chat messages dict.
        """
        model_name = model_name or random.choice(self.model_names)
        rand_agent = get_agent(model_name=model_name)
        return rand_agent.get_chat_response(message=message, system_prompt=system_prompt, chat_history=chat_history,
                                            msg_thread=msg_thread, model_name=model_name.split('//')[-1], **kwargs)

    def get_answers(self, message=None, system_prompt=None, chat_history=None, msg_thread=None,
                    model_names=None, num_iterations: int = 3, **kwargs):
        """
        Get multiple candidate answers for a message or msg_thread
        """
        # Parse the message
        if msg_thread is None:
            if message is None:
                raise ValueError("Message must be provided as message or msg_thread")
            else:
                msg_thread = _Agent.to_thread(message=message, system_prompt=system_prompt, chat_history=chat_history)
        # Build the list for inference
        answer_plan = self._build_plan_for_answers(msg_thread_list=[msg_thread],
                                                   model_names=model_names,
                                                   num_iterations=num_iterations, **kwargs)
        # Get candidate answers
        return self._execute_plan_for_answers(answer_plan=answer_plan, do_threaded=num_iterations != 1)
