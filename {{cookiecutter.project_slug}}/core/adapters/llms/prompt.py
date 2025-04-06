# core/daos/llms/prompt.py
"""

Prompts

Prompts use Jinja2 to render complex strings from templates
Tuning variables can be injected into the template to improve performance.
Default templates are provided for classifiers, boolean classifiers, and summarization.

TODOs -
# scraping - use fine-tuned LLMs to extract data from scraped pages
# python - write python code, paying attention to add feedback hooks so that the outputs can be evaluated.
# python_is_error - TRUE if a block of text contains a python stacktrace somewhere in it.
# python_feedback - gather feedback on stdout to keep developing or return the finished code.

Applications -
# headline - rewrite the headline based on the fact sheet of the stories
# cause-effect - What are the cause-effect relationships in this article and the evidence presented for them?
# source-id - Identify the source of the claims of the article
# log line - a concise 15-20 word summary of the speech
# main themes - identify the main themes of the answers to help draw connecting dots.
# character profile - build a profile of the subject of the speech as seen through the eyes of the speaker
# harsh criticism - the worst thing a critic could say about your speech


StringParser
String parser for interpreting model answers, articles, scraped pages, and more

"""
import os
import re
import copy
import json
import time
from dataclasses import dataclass
import statistics
from numbers import Number
from abc import ABC
from json import JSONDecodeError
from typing import List, Optional, Any, Dict, Tuple
from jinja2 import Template, StrictUndefined, UndefinedError, Environment, meta
import pandas as pd
from config import logger, Config
from core.adapters.parsers.string import StringParser
from core.adapters.parsers import HtmlParser, DataclassSerializerMixin
from core.daos.llms.agent import Agent, to_thread
from core.daos.mab.bandit import Bandit

default_formatting_examples = """
{% if examples %}
Here are some examples:
{% for example in examples %}
{{ loop.index }} - {{ example }}
{% endfor %}
{% else %}
{% endif %}
"""


@dataclass
class PromptAnswers(DataclassSerializerMixin):
    """
    Results container for batch prompt execution.

    Stores both parsed and raw answers, with metadata about the execution.
    """
    parsed: List[Any]  # Parsed answers (could be any type depending on the parser)
    raw: List[str]  # Raw text responses from the agents
    model_names: List[str] = None  # List of names of the agents
    best_idx: Optional[int] = None  # Index of the best answer if determined
    num_errors: int = 0  # Number of errors encountered during execution
    avg_time_ms: float = 0.0  # Average response time in milliseconds
    msg_thread: Dict[str, Any] = None
    target_str: Optional[str] = None  # The target string used in the query
    trial_id: str = None  # (optional) MAB trial ID for .auto_get_answers()
    scenario_name: str = None  # (optional) name of the MAB scenario for .auto_get_answers()

    @property
    def best_answer_parsed(self) -> Optional[Any]:
        """Get the parsed version of the best answer."""
        # If there's only one answer and it's working, that's the best
        if len(self.parsed) == 1 and self.parsed[0] is not None:
            return self.parsed[0]
        # Otherwise, there needs to be a valid best_idx specified
        if self.best_idx is not None and 0 <= self.best_idx < len(self.parsed):
            return self.parsed[self.best_idx]
        return None

    @property
    def best_answer_raw(self) -> Optional[str]:
        """Get the raw version of the best answer."""
        # If there's only one answer and it's working, that's the best (still need to confirm correct parsing tho)
        if len(self.parsed) == 1 and self.parsed[0] is not None:
            return self.raw[0]
        # Otherwise, there needs to be a valid best_idx specified
        if self.best_idx is not None and 0 <= self.best_idx < len(self.raw):
            return self.raw[self.best_idx]
        return None

    @property
    def mean(self) -> Optional[float]:
        """
        Calculate the mean of parsed answers based on their type.
        - For lists of numbers (int/float): arithmetic mean
        - For lists of booleans: proportion of True values (treated as 1.0)
        - For other types: None (not calculable)
        Ignores None values and empty lists.
        Used for BooleanPrompt probability thresholding
        """
        # Filter out None values
        valid_values = [v for v in self.parsed if v is not None]
        if not valid_values:
            return None
        # Check if all elements are numeric
        if all(isinstance(val, Number) for val in valid_values):
            return statistics.mean(valid_values)
        # Check if all elements are boolean
        elif all(isinstance(val, bool) for val in valid_values):
            # Convert booleans to 1.0 and 0.0 and calculate mean
            return statistics.mean(1.0 if val else 0.0 for val in valid_values)
        # Not a calculable type
        return None

    @property
    def answers(self) -> List[Any]:
        """ Correctly-parsed answers with None ignored """
        return [v for v in self.parsed if v is not None]

    @property
    def unanimous(self) -> bool:
        """
        Check if all parsed answers have the same string representation. We can skip pick_best if so.

        Returns:
            bool: True if all answers have the same string representation or if there's only one answer,
                  False if string representations differ or if there are no valid answers.
        """
        # Get valid answers (filtering out None values)
        valid_answers = self.answers
        # If there are no valid answers or only one, return appropriate result
        if not valid_answers:
            return False  # No valid answers to compare
        if len(valid_answers) == 1:
            return True  # Only one answer, so it's the same as itself
        # Convert first answer to string representation
        first_answer_str = str(valid_answers[0])
        # Compare string representations of all answers to the first one
        return all(str(ans) == first_answer_str for ans in valid_answers[1:])

    def consensus(self) -> Tuple[Any, float]:
        """
        Find the most common answer and calculate its percentage occurrence.
        Used for ClassifierPrompts as a pick_best strategy

        Returns:
            Tuple[Any, float]: The most common answer and its percentage (0-100) of occurrence.
                               Returns (None, 0.0) if there are no valid answers.
        """
        valid_answers = self.answers
        if not valid_answers:
            return None, 0.0
        # If there's only one answer, it's 100% consensus
        if len(valid_answers) == 1:
            return valid_answers[0], 100.0
        # Count occurrences of each answer based on equality
        answer_counts = {}
        for answer in valid_answers:
            # Use string representation as dictionary key for counting
            answer_str = str(answer)
            if answer_str not in answer_counts:
                answer_counts[answer_str] = {"count": 1, "original": answer}
            else:
                answer_counts[answer_str]["count"] += 1
        # Find the most common answer
        most_common_str = max(answer_counts.keys(), key=lambda k: answer_counts[k]["count"])
        most_common_answer = answer_counts[most_common_str]["original"]
        most_common_count = answer_counts[most_common_str]["count"]
        # Calculate percentage
        percentage = (most_common_count / len(valid_answers)) * 100.0
        return most_common_answer, percentage

    def reward_bandit(self,
                      correct_value: Optional[Any] = None,
                      model_names: Optional[List[str]] = None,
                      model_idxs: Optional[List[int]] = None) -> Bandit:
        """
        Reward the multi-armed bandit that picked the agents, if applicable.
        If target models are unspecified, reward best_idx or whichever parsed correctly.

        Args:
            correct_value: (optional) benchmark value that the models should hit
            model_names: (optional) list of model names to reward
            model_idxs: (optional) list of the index of teh model name to reward

        Returns:

        """
        bandit = Bandit.load_or_new(name=self.scenario_name)
        # reward by value
        if correct_value is not None:
            model_names = [model for idx, model in enumerate(self.model_names) if self.parsed[idx] == correct_value]
        # reward by names
        if model_names is not None:
            bandit.update(trial_uuid=self.trial_id, rewarded_arms=model_names, strict=False)
        # reward by idx
        if model_idxs is not None:
            bandit.update(trial_uuid=self.trial_id,
                          rewarded_arms=[self.model_names[idx] for idx in model_idxs],
                          strict=False)
        # reward with best_idx
        if self.best_idx is not None:
            bandit.update(trial_uuid=self.trial_id, rewarded_arms=[self.model_names[self.best_idx]], strict=False)
        # Just reward the ones that parsed correctly
        bandit.update(trial_uuid=self.trial_id,
                      rewarded_arms=[name for idx, name in enumerate(self.model_names) if self.parsed[idx] is not None])
        return bandit

    def __len__(self) -> int:
        """Return the number of answers collected."""
        return len(self.answers)


class Prompt(ABC):
    """
    Template renderer to build a prompt from a template.
    Accepts tuning params at instantiation or run-time to allow for prompt engineering
    """
    all_agents = None

    def __init__(self, target_str=None, scenario_name: str = 'general', examples: list = None,
                 agent: Agent = None, system_prompt: str = None, query_template: str = None,
                 intro_tuning: str = '', outro_tuning: str = '',
                 temperature: float = 0.2, verbose: bool = False, max_out_tokens: int = None,
                 **kwargs):
        """
        Build out a custom prompt and get answers from Config and param specified models

        :param target_str: the main question, example, focus, or sample to be analyzed
        :param examples: (optional): list of examples to demonstrate the desired output
        :param agent: (optional): instantiated Agent model to be used for inference
        :param scenario_name: (optional) name of the applied task to track reward signals.
        :param system_prompt: (optional) override instructions for the response
        :param query_template: (optional) how the target_str is decorated in its presentation to the model
        :param intro_tuning: (optional) tuning str to set up the start of the query
        :param outro_tuning: (optional) tuning str to close out the query
        :param temperature: (optional) what default temperature should we use for agents?
        :param verbose: (optional) print admin text for agents and parsing
        :param max_out_tokens: (optional) limit to the number of output tokens in the response
        :param kwargs: (optional)
        """
        self.target_str = target_str or ''
        self.system_prompt = system_prompt
        self.application_name = scenario_name
        # query
        self.query_template = query_template or '{{ target_str }}'
        # examples
        self.formatting_examples = kwargs.get('formatting_examples', default_formatting_examples)
        self.examples = examples
        # tuning
        self.intro_tuning = intro_tuning
        self.outro_tuning = outro_tuning
        # model criteria
        self.temperature = temperature
        self.verbose = verbose
        self.max_out_tokens = max_out_tokens
        self.agent = agent
        if self.agent is not None:
            self.agent.verbose = self.verbose
            if self.max_out_tokens is not None:
                self.agent.max_out_tokens = self.max_out_tokens
        # Leave kwargs open to be injected into the .render() functions from children
        # Allows children to add their own variables into the jinja template
        self.kwargs = kwargs

    @property
    def data(self):
        return {
            **self.kwargs,
            'target_str': self.target_str,
            'query_template': self.query_template,
            'intro_tuning': self.intro_tuning,
            'outro_tuning': self.outro_tuning,
            'examples': self.examples,
            'temperature': self.temperature,
            'max_out_tokens': self.max_out_tokens
        }

    @property
    def template_str(self):
        template_str = "{{ intro_tuning }}\n"
        template_str += self.data['query_template']
        template_str += "\n" + self.formatting_examples
        template_str += "\n{{ outro_tuning }}"
        return StringParser.remove_extra_newlines(template_str)

    @property
    def missing_vars(self):
        """
        Get the variables that are required for the Prompt but haven't yet been specified
        """
        env = Environment()
        ast = env.parse(self.template_str)
        var_names = meta.find_undeclared_variables(ast)
        var_names = [vn for vn in var_names]
        return var_names

    def render_query(self, update_data: dict = None, target_str: str = None, template_str: str = None):
        """
        Inject the tuning variables into the template and render to build the full text prompt

        :param update_data: (optional) dict of data to add before rendering
        :param target_str: (optional) str for the target_str in the query template
        :param template_str: (optional) the template_str to render. Falls back to template_str property if unspecified
        :return:
        """
        # Initialize the template with StrictUndefined to ensure all variables must be defined
        template = Template(template_str or self.template_str, undefined=StrictUndefined)
        # render or error
        data = copy.deepcopy(self.data)
        if update_data is not None:
            data.update(update_data)
        if target_str is not None:
            data['target_str'] = target_str
        try:
            return StringParser.remove_extra_newlines(template.render(**data))
        except UndefinedError:
            # If an undefined variable is encountered, raise an error
            raise ValueError(f"query rendering failed due to an UndefinedError with {self.missing_vars=}")

    def _parse_answer(self, answer_str: str):
        """
        Base answer parsing method to be overridden by child classes when a custom parser is required

        :param answer_str:
        :return:
        """
        return StringParser.isolate_answer_string(message=answer_str)

    def parse_answer(self, answer_str: str, suppress_errors: bool = False):
        """
        Universal parsing interface for Prompts, which accepts strings or full Conversations for convenience

        :param answer_str:
        :param suppress_errors: Should parsing errors be suppressed and the full answer strings
        :return:
        """
        if suppress_errors is True:
            try:
                return self._parse_answer(answer_str=answer_str)
            except ValueError:
                logger.debug(f"WARNING - error parsing {answer_str=} so we're gonna return the full answer_str")
                return answer_str
        else:
            return self._parse_answer(answer_str=answer_str)

    def get_answer(self, max_retries: int = 1) -> Optional[Any]:
        """
        Get the parsed answer for the prompt from the perfect agent for the job

        :param max_retries: (optional) how many times to attempt the prompt and check for errors in the response
        :return:
        """
        msg_thread = to_thread(message=self.render_query(target_str=self.target_str), system_prompt=self.system_prompt)
        for _ in range(max_retries):
            answer_str = self.agent.get_answer(msg_thread=msg_thread,
                                               max_out_tokens=self.max_out_tokens,
                                               temperature=self.temperature)
            # Return the answer if it parses correctly, else retry
            parsed_str = self.parse_answer(answer_str)
            if answer_str not in (None, '', ' '):
                # We still want a valid string even if we don't want the parsed results
                return parsed_str
        # If no parseable answer is found, return None explicitly
        return None

    @staticmethod
    def pick_best_answer_with_agent(
            original_prompt: str, prompt_answers: PromptAnswers, agent: Agent, num_attempts: int = 3
    ) -> Optional[int]:
        voting_prompt = f"""
=== SYSTEM INSTRUCTIONS ===
You are a helpful assistant that reviews possible answers to a prompt and picks the best one.
The best answer should be the clearest, most comprehensive, and most accurate answer to the prompt.

Here is the prompt:

=== PROMPT ===
<<<prompt>>>
{original_prompt}
<<</prompt>>>

=== ANSWERS ===
And here are the {len(prompt_answers.parsed)} different answers. 
Please evaluate them and return the index (0-based) of the best answer 
which is in xml-style tags like <answer_idx>0</answer_idx>

<<<answer_list>>>
{'\n\n'.join([f"<answer_idx>{i}</answer_idx> <answer_str>{answer}</answer_str>" for i, answer in enumerate(prompt_answers.parsed)])}
<<</answer_list>>>

=== QUESTION ===
Please respond with the index of the best answer and then explain your choice
        """
        # Get the best answer index
        if prompt_answers.unanimous:
            # If answers agree, get the first that is not None
            for idx, item in enumerate(prompt_answers.parsed):
                if item is not None:
                    prompt_answers.best_idx = idx
                    return idx
        else:
            for _ in range(num_attempts):
                best_answer_response = agent.get_answer(message=voting_prompt,
                                                        max_out_tokens=20,
                                                        temperature=0.02)  # Low temperature for consistency
                # Parse the index
                try:
                    best_idx = StringParser.get_first_number(best_answer_response,
                                                             max_value=len(prompt_answers.answers))
                    if best_idx is not None:
                        prompt_answers.best_idx = best_idx
                        return best_idx
                except (ValueError, TypeError):
                    print(f"Warning: Failed to parse best answer index from: {best_answer_response}")

    def get_answers(self, answer_agents=None, pick_best_agent=None, target_count=5, max_failures=3):
        """
        Get multiple answers from a list of agents, with failure handling and optionally selecting the best answer.

        This method will attempt to get 'target_count' valid answers, but will stop after 'max_failures'
        consecutive failures. It wraps around the list of agents in a circular manner to utilize all provided agents.

        :param target_count: Number of valid answers to aim for
        :param max_failures: Maximum number of consecutive failures before giving up
        :param answer_agents: List of Agent objects to use for generating answers
        :param pick_best_agent: Optional Agent to select the best answer from the results
        :return: Dictionary with parsed and raw results, best index, error count, and average time
        """
        if answer_agents is None or len(answer_agents) == 0:
            if self.agent is None:
                raise ValueError("You must provide either answer_agents or set self.agent")
            answer_agents = [self.agent]
        # Prepare the message thread
        msg_thread = to_thread(message=self.render_query(target_str=self.target_str), system_prompt=self.system_prompt)
        # Initialize tracking variables
        parsed_answers = []
        raw_answers = []
        answer_model_name = []
        failures = 0
        total_time_ms = 0
        agent_index = 0
        # Attempt to get target_count valid answers
        while len(parsed_answers) < target_count and failures < max_failures:
            # Get the next agent in a circular manner
            agent = answer_agents[agent_index % len(answer_agents)]
            agent_index += 1
            # Track time for this attempt
            start_time = time.time()
            try:
                # Get answer from the agent
                raw_answer = agent.get_answer(msg_thread=msg_thread,
                                              max_out_tokens=self.max_out_tokens,
                                              temperature=self.temperature)
                # Calculate time taken
                elapsed_ms = (time.time() - start_time) * 1000
                total_time_ms += elapsed_ms
                # Try to parse the answer
                try:
                    parsed_answer = self.parse_answer(StringParser.parse_escaped_string(raw_answer),
                                                      suppress_errors=True)
                    # If we got a valid answer, add it to our lists
                    if parsed_answer is not None:
                        parsed_answers.append(parsed_answer)
                        raw_answers.append(raw_answer)
                        answer_model_name.append(agent.model_name)
                        consecutive_failures = 0  # Reset consecutive failures counter
                    else:
                        # Invalid parsed answer
                        raw_answers.append(raw_answer)
                        parsed_answers.append(None)
                        answer_model_name.append(agent.model_name)
                        failures += 1
                        # TODO - change back to logging warning
                        print(f"Warning: Failed to parse answer: {raw_answer}")
                except (ValueError, TypeError) as e:
                    # Parsing error
                    raw_answers.append(raw_answer)
                    parsed_answers.append(None)
                    answer_model_name.append(agent.model_name)
                    failures += 1
                    logger.warning(f"Warning: Error parsing answer: {e}")
            except Exception as e:
                # Agent error
                failures += 1
                logger.warning(f"Error getting answer from agent: {e}")
        # Calculate average time
        avg_time_ms = total_time_ms / max(1, len(raw_answers))
        # Create result object
        result = PromptAnswers(
            msg_thread=copy.deepcopy(msg_thread),
            target_str=self.target_str,
            parsed=parsed_answers,
            raw=raw_answers,
            model_names=answer_model_name,
            num_errors=failures,
            avg_time_ms=avg_time_ms
        )
        # If pick_best_agent is provided and we have at least one valid answer, find the best one
        if pick_best_agent is not None and len(raw_answers) > 1:
            # Create a voting prompt and pick the best answer
            original_prompt = self.render_query(target_str=self.target_str)
            original_prompt = StringParser.remove_extra_newlines(original_prompt).strip()
            best_idx = self.pick_best_answer_with_agent(original_prompt=original_prompt,
                                                        prompt_answers=result,
                                                        agent=pick_best_agent)
            if best_idx is not None:
                result.best_idx = best_idx
        return result

    def auto_get_answers(self, scenario_name: str, target_count=5, max_failures=3, pick_best_agent=None):
        """
        Alternative to .get_answers() that pick among the agents to find the optimal agent for the task
        based on the scenario_name

        Args:
            scenario_name:
            target_count:
            max_failures:
            pick_best_agent:

        Returns:

        """
        # Get agents to choose from, where applicable.
        if self.all_agents is None:
            df = pd.read_csv(os.path.join(Config.PIPELINE_DIR, 'bandits', 'agent_names.csv'))
            self.all_agents = df.iloc[:, 0].tolist()
        bandit = Bandit.load_or_new(name=scenario_name)
        agent_names, trial_id = bandit.pull(num_arms=target_count, include_names=self.all_agents)
        agents = Agent.get_agents(model_name_list=agent_names)
        answers = self.get_answers(target_count=target_count,
                                   max_failures=max_failures,
                                   answer_agents=agents,
                                   pick_best_agent=pick_best_agent)
        answers.trial_id = trial_id
        answers.scenario_name = scenario_name
        return answers


class BlankPrompt(Prompt):
    """
    Blank template example for testing and documentation
    No formatting or parsing, which may confuse smaller models.
    """

    def __init__(self, target_str, query_template=None, **kwargs):
        query_template = '{{ target_str }}'
        super().__init__(target_str, query_template=query_template, **kwargs)

    def _parse_answer(self, answer_str: str):
        """
        Base answer parsing method to be overridden by child classes when a custom parser is required

        :param answer_str:
        :return:
        """
        return str(answer_str)


class ClassifierPrompt(Prompt):
    def __init__(self, categories_dict: dict, examples: List[str] = None, is_multilabel: bool = True, **kwargs):
        """
        Build out a prompt to tag text passages with category labels

        :param categories_dict: dict of {label: description} for the categories
        :param examples: (optional) list of examples to demonstrate the desired output
        :param is_multilabel: if yes, choose all that fits. Otherwise, choose only one best fit label for the passage
        :param kwargs:
        """
        # unpack categories
        self.categories_dict = categories_dict
        self.categories_dict['none'] = 'none'
        self.categories_csv = ','.join(self.categories_dict.keys()).lower()
        self.categories_desc_list = [f"{label.lower()} - {desc}" for label, desc in self.categories_dict.items()]
        self.categories_desc = '\n'.join(self.categories_desc_list)
        # Assign a single class / category / label / tag to a story
        query_template = f"""
=== SYSTEM INSTRUCTIONS ===
You are a helpful assistant that reviews text passages and assigns them a category classification.
Read the following text and then the categories to choose from, then assign it a category from the list.

Here is the text:

=== TEXT ===
<<<text>>>
((((target_str))))
<<</text>>>

=== CATEGORIES ===
And here are the {len(self.categories_dict)} different categories. 
Please evaluate them and return the index (0-based) of the best category description for the text 
which is in xml-style tags like <category_idx>0</category_idx>

<<<category_list>>>
{'\n\n'.join([f"<category_idx>{i}</category_idx> <category_str>{answer}</category_str>" for i, answer in enumerate(self.categories_desc_list)])}
<<</category_list>>>

=== QUESTION ===
"""
        # configure multilabel features
        self.is_multilabel = is_multilabel
        if is_multilabel is True:
            query_template += """
Please respond with the all the indexes of categories that apply to the text as a single, comma-delimited list or 'none' like:
1,2,5,9
"""
        else:
            query_template += """
Please respond with the index of the best category to describe the text passage and then explain your choice in detail
"""
        # render the specialized query template to reduce Prompt complexity
        template = Template(query_template, undefined=StrictUndefined)
        query_template = template.render(dict(categories_csv=self.categories_csv,
                                              categories_desc=self.categories_desc))
        query_template.replace('((((target_str))))', '{{target_str}}')
        # init Prompt
        kwargs['temperature'] = kwargs.get('temperature') or 0.1
        super().__init__(query_template=query_template, examples=examples, **kwargs)

    @staticmethod
    def _validate_classifier_answer(answer_str) -> Optional[List[str]]:
        """
        Parse, clean, and validate the answers to build a dataset

        :param answer_str:
        :return: None or the parse set of strings for matching classes
        """
        print('answer_str', answer_str)
        answer_str = answer_str.copy().lower()
        # Check for suspicious punctuation
        if any([kwd in answer_str for kwd in ('\n', ':', '=', '- ', ' -', '.')]):
            return None
        answer_list = [ans.strip().replace(' ', '_') for ans in answer_str.split(',')]
        # Check for suspiciously long category names
        if any([len(ans) > 30 for ans in answer_list]):
            return None
        else:
            return answer_list

    def _parse_answer(self, answer_str):
        """
        Parse the answer string to extract only valid labels

        :param answer_str:
        :return:
        """
        # match with class_name and drop non-matches
        class_names = [name.strip() for name in self.categories_csv.split(',')]
        if self.is_multilabel is True:
            return StringParser.multi_classify_answer(answer_str, class_names=class_names)
        else:
            return StringParser.classify_answer(answer_str, class_names=class_names)

    def unstack_columns(self, class_col_name):
        """
        TODO - parse a column of class tags in a pandas DF into columns of each class
        with boolean values for whether the class category is active.
        :return:
        """


class BooleanPrompt(Prompt):
    def __init__(self, target_str, prompt_question, **kwargs):
        query_template = """
{{ prompt_question }} Answer TRUE or FALSE and explain your reasoning.

Here is the text that we'll be analyzing:
{{ target_str }}

{{ prompt_question }} 
Answer **TRUE** or **FALSE** and explain your reasoning. 
"""
        super().__init__(target_str, query_template=query_template, prompt_question=prompt_question, **kwargs)

    # noinspection PyMethodMayBeStatic
    def _parse_answer(self, answer_str):
        """
        Find the first answer in the response that is either True or False (case insensitive)
        :param answer_str:
        :return:
        """
        text_lower = answer_str.lower()
        true_index = text_lower.find("true")
        false_index = text_lower.find("false")
        # If neither is found
        if true_index == -1 and false_index == -1:
            return None
        # If only one is found
        if true_index == -1:
            return False
        if false_index == -1:
            return True
        # If both are found, return based on which comes first
        return true_index < false_index

    @staticmethod
    def get_probability(
            html_str: str,
            prompt_question: str,
            agents: Optional[List[Agent]],
            target_attempts: int = None,
            max_out_tokens: int = 20,
            **kwargs
    ) -> Optional[float]:
        """
        Determine if this is an error page

        Args:
            html_str: HTML content to analyze
            prompt_question: Prompt that requests a True or False answer. This function adds formatting so skip that.
            agents: (optional) List of LLM agents to use for detection
            target_attempts: (optional) number of agent passes to make on the analysis
            max_out_tokens: (optional) limit the number of output tokens for efficiency

        Returns:
            Boolean indicating if this is an error page
        """
        if agents is None:
            agents = Agent.get_agents(num_models=target_attempts or 3)
        if target_attempts is not None:
            target_attempts = len(agents)
        # Extract text-only version of the HTML for analysis
        text_content = HtmlParser.find_text_only(html_str)
        # Limit content to reasonable size for LLM
        if len(text_content) > 10000:
            text_content = text_content[:10000]
        logger.debug(f"Analyzing {len(text_content)} characters of text for error page detection")
        # Create boolean prompt for error page detection
        bp = BooleanPrompt(
            prompt_question=prompt_question,
            target_str=text_content,
            max_out_tokens=max_out_tokens,
            **kwargs
        )
        # Get multiple answers and use consensus approach
        results = bp.get_answers(
            target_count=target_attempts or 3,
            max_failures=2,
            answer_agents=agents
        )
        logger.debug(f"BooleanPrompt.get_probability() detection results: {results.parsed}")
        return results.mean


class HealthCheckPrompt(BlankPrompt):
    """
    Simple boolean check to ensure against memory corruption
    """

    def __init__(self, **kwargs):
        super().__init__(target_str="Simply respond 'yes' to prove that you're listening and working correctly",
                         **kwargs)

    # noinspection PyMethodMayBeStatic
    def _parse_answer(self, answer_str):
        answer = answer_str.lower()
        if len(answer) > 30:
            return None
        return 'yes' in answer or 'true' in answer


class InstructionPrompt(Prompt):
    """
    Write a prompt with custom instructions
    """

    def __init__(self, target_str, instruction_str, instruction_reminder_str='', **kwargs):
        query_template = """
INSTRUCTIONS: 
{{ instruction_str }}

{{ target_str }}

{{ instruction_reminder_str }}
"""
        # Clear formatting, since it should be included in the instruction_str
        super().__init__(target_str,
                         query_template=query_template,
                         instruction_str=instruction_str,
                         instruction_reminder_str=instruction_reminder_str,
                         **kwargs)

    def _parse_answer(self, answer_str: str):
        """
        Base answer parsing method to be overridden by child classes when a custom parser is required

        :param answer_str:
        :return:
        """
        # look for data between **double asterisks** and isolate if possible
        pattern = r"\*\*(.*?)\*\*"
        matches = re.findall(pattern, answer_str)
        if len(matches) >= 1:
            return matches[0].strip()

        # look for data between ```triple backticks``` and isolate if possible
        pattern = r"```(?:.*?)\n([\s\S]*?)```"
        matches = re.findall(pattern, answer_str, re.DOTALL)
        if len(matches) >= 1:
            return matches[0].strip()

        return answer_str


class DriverClickPrompt(InstructionPrompt):

    def _parse_answer(self, answer_str: str):
        """
        Extract a driver.find_element(...).click() phrase from an answer

        :param answer_str:
        :return:
        """
        # First try to extract the Selenium command directly (most reliable approach)
        command_pattern = r"driver\.find_element\(.*?\)\.click\(\)"
        command_match = re.search(command_pattern, answer_str)
        if command_match:
            return command_match.group(0)

        # Look for data between **double asterisks**
        pattern = r"\*\*(.*?)\*\*"
        matches = re.findall(pattern, answer_str)
        if matches:
            return matches[0]

        # Look for code blocks with triple backticks (markdown)
        triple_pattern = r"```(?:.*?)\n([\s\S]*?)```"
        triple_match = re.search(triple_pattern, answer_str, re.DOTALL)
        if triple_match:
            # Check if the content has our command pattern
            code_content = triple_match.group(1).strip()
            command_in_code = re.search(command_pattern, code_content)
            return command_in_code.group(0) if command_in_code else code_content

        # Look for code with single backticks
        single_pattern = r"`([\s\S]*?)`"
        single_match = re.search(single_pattern, answer_str, re.DOTALL)
        if single_match:
            # Check if the content has our command pattern
            code_content = single_match.group(1).strip()
            command_in_code = re.search(command_pattern, code_content)
            return command_in_code.group(0) if command_in_code else code_content

        return answer_str


class SoupFindAllPrompt(InstructionPrompt):

    def _parse_answer(self, answer_str: str):
        """
        Extract a BeautifulSoup find_all call from an answer

        :param answer_str:
        :return: Tuple of (tag_name, attrs_dict) or None if parsing fails
        """
        # Convert single quotes to double quotes for JSON compatibility
        # but store original for later reference
        original_html = answer_str
        element_html = answer_str.replace("'", '"')

        # Different patterns to match various soup.find_all formats
        patterns = [
            # Pattern 1: Match soup.find_all("tag", attrs={"attr": "value"})
            r'soup\.find_all\s*\(\s*"([^"]+)"\s*,\s*attrs\s*=\s*(\{(?:[^{}]|{[^{}]*})*\})',
            # Pattern 2: Match soup.find_all("tag", {"attr": "value"})
            r'soup\.find_all\s*\(\s*"([^"]+)"\s*,\s*(\{(?:[^{}]|{[^{}]*})*\})',
            # Pattern 3: Match soup.find_all('tag', {'attr': 'value'}) with single quotes
            r'soup\.find_all\s*\(\s*\'([^\']+)\'\s*,\s*(\{(?:[^{}]|{[^{}]*})*\})',
            # Pattern 4: Match soup.find('tag', {'attr': 'value'}) - for find instead of find_all
            r'soup\.find\s*\(\s*[\'"]([^\'"]+)[\'"]\s*,\s*(\{(?:[^{}]|{[^{}]*})*\})',
            # NEW Pattern 5: Match soup.find_all('tag', class_='value')
            r'soup\.find_all\s*\(\s*[\'"]([^\'"]+)[\'"]\s*,\s*class_\s*=\s*[\'"]([^\'"]+)[\'"]',
            # NEW Pattern 6: Match soup.find('tag', class_='value')
            r'soup\.find\s*\(\s*[\'"]([^\'"]+)[\'"]\s*,\s*class_\s*=\s*[\'"]([^\'"]+)[\'"]'
        ]

        all_matches = []

        # Try all patterns on both original and converted string
        for i, pattern in enumerate(patterns):
            # For the new patterns with class_
            if i >= 4:  # Check if it's one of our new patterns (5 or 6)
                matches = re.findall(pattern, original_html)
                for match in matches:
                    tag_name, class_value = match
                    # Create a tuple that mimics the format of the other patterns
                    all_matches.append((tag_name, f'{{"class": "{class_value}"}}'))
            else:
                all_matches.extend(re.findall(pattern, element_html))
                # Also try on original string for patterns with single quotes
                if "'" in original_html:
                    all_matches.extend(re.findall(pattern.replace('"', "'"), original_html))

        # Handle other keyword arguments
        # Match soup.find_all('tag', attr='value')
        kw_pattern = r'soup\.(?:find_all|find)\s*\(\s*[\'"]([^\'"]+)[\'"]\s*,\s*([a-zA-Z_]+)\s*=\s*[\'"]([^\'"]+)[\'"]'
        kw_matches = re.findall(kw_pattern, original_html)
        for match in kw_matches:
            tag_name, attr_name, attr_value = match
            # For class_ convert to class in the dictionary
            if attr_name == 'class_':
                attr_name = 'class'
            # Create a tuple that mimics the format of the other patterns
            all_matches.append((tag_name, f'{{"{attr_name}": "{attr_value}"}}'))

        if not all_matches:
            return None

        try:
            # Find the longest match based on the total string length
            longest_match = max(all_matches, key=lambda m: len(m[0]) + len(m[1]))
            tag_name, attrs_str = longest_match

            # Handle both single and double quotes in the attributes
            if "'" in original_html and '"' not in attrs_str:
                # If original had single quotes, convert attrs_str back to using single quotes
                # before attempting JSON parsing with double quotes
                attrs_str = attrs_str.replace("'", '"')

            # Handle potential nested JSON by proper parsing
            attrs_str = re.sub(r'"\s*:\s*"', '": "', attrs_str)  # Normalize spacing around colons
            attrs_str = re.sub(r'"\s*,\s*"', '", "', attrs_str)  # Normalize spacing around commas

            # Try to parse the JSON
            try:
                attrs_dict = json.loads(attrs_str)
            except json.JSONDecodeError:
                # If JSON parsing fails, try a more lenient approach by manually parsing the dict
                attrs_dict = {}
                # Simple key-value pair extraction
                key_val_pattern = r'"([^"]+)"\s*:\s*"([^"]+)"'
                for key, value in re.findall(key_val_pattern, attrs_str):
                    attrs_dict[key] = value

                # Handle non-string values (like numbers, booleans)
                key_nonstr_val_pattern = r'"([^"]+)"\s*:\s*([^,}]+)'
                for key, value in re.findall(key_nonstr_val_pattern, attrs_str):
                    if key not in attrs_dict:  # Only add if not already added
                        value = value.strip()
                        if value.lower() == 'true':
                            attrs_dict[key] = True
                        elif value.lower() == 'false':
                            attrs_dict[key] = False
                        elif value.isdigit():
                            attrs_dict[key] = int(value)
                        else:
                            try:
                                attrs_dict[key] = float(value)
                            except ValueError:
                                attrs_dict[key] = value

            return tag_name, attrs_dict
        except Exception as e:
            print(f"Failed to parse soup parameters: {str(e)}")
            return None


class UneditedInstructionPrompt(InstructionPrompt):

    def _parse_answer(self, answer_str: str):
        return answer_str


class JSONPrompt(Prompt):
    """
    Format data in a block of text into a JSON data structure.
    """

    def __init__(self, target_str, json_structure: str, json_example: str = None, **kwargs):
        query_template = """
INSTRUCTIONS: 
We're going to be reviewing a block of HTML/text and organizing the data into a JSON data structure.

Here is the JSON structure that we'd like to fill out:
{{ json_structure }}
"""
        if json_example is not None:
            query_template += f"""
Here is a data structure for an example passage, delimited by three single-quotes:
'''
{json_example}
'''

Your results should look something like that, though there may be sections missing if some of the data isn't present in the text.
            """
        query_template += """
Here is the sample that we'll be selecting from, delimited by three single-quotes:
'''
{{ target_str }}
'''

"""
        formatting_examples = ""
        outro_tuning = ("Format your answer in the form of a JSON data structure. "
                        "Enclose the JSON part of your answer in curly braces. ")
        super().__init__(target_str, query_template=query_template,
                         formatting_examples=formatting_examples, outro_tuning=outro_tuning,
                         json_structure=json_structure, **kwargs)

    def _parse_answer(self, answer_str, strict=True):
        """
        Parse the JSON answer string and ensure that it includes all the requested attributes
        """
        start = answer_str.find("{")
        end = answer_str.rfind("}") + 1
        if 0 <= start < end:
            answer = answer_str[start:end]
        else:
            logger.warning(f"no brackets found in {answer_str=}")
            return None
        answer = StringParser.remove_json_comments(answer)
        answer = answer.replace('\n', '')
        if strict is True:
            try:
                return json.loads(answer)
            except JSONDecodeError:
                logger.warning(f"JSONDecodeError for {answer_str=}")
                return None
        else:
            return answer


class CategoryRatingsPrompt(Prompt):
    def __init__(self, categories_dict: dict, examples: List[str] = None, is_difficult: bool = False,
                 is_expedited: bool = False, **kwargs):
        """
        Measure from 0-9 across a variety of categories to make complex measurements of text passages

        :param categories_dict: dict of {label: description} for the categories
        :param examples: (optional) list of examples to demonstrate the desired output
        :param is_difficult: (optional) what strength of models are we gonna need for this one?
        :param is_expedited: (optional) is time a factor?
        :param kwargs:
        """
        # unpack categories
        self.categories_dict = categories_dict
        self.categories_csv = ','.join(self.categories_dict.keys()).lower()
        self.categories_desc = '\n* '.join(
            [f"{label.lower()} - {desc}" for label, desc in self.categories_dict.items()])
        # Assign a single class / category / label / tag to a story
        query_template = """
INSTRUCTIONS:
We're going to apply a series of ratings to a text passage in order to measure and rate it. 

RATINGS:
Here are the ratings that we are going to apply to the article from 0 to 9:
{{ categories_desc }}

SAMPLE:
Here is the text sample that we'll be analyzing:
{{ target_str }}


FORMATTING GUIDE:
Format your response like this (make sure that the sections are in all caps like '### REASONING:' instead of '### Reasoning:'):

### REASONING: <use this section to think over the main ideas of the article and the elements of it that might be important. If we can understand what the article is trying to say, we can more accurately measure it>
### ANSWER: <a list of ratings for the article, each line starting with * to indicate a rating and then a hyphen - to a description>
### COMMENTS: <any broader context that you'd like to give for the headline or the article.>

for example:

### REASONING: The main idea of this article is that a series of safety failures with Boeing planes has caused a drop in consumer confidence and a halting of orders.
### ANSWER: 
* seriousness: 8 - safety incidents in planes are very serious and loss of customer trust can be a huge problem
* objectivity: 7 - mostly factual article with very little editorializing or speculation
* sentiment: 2 - the sentiment was very negative and didn't offer hope at the end. This is an ongoing bad situation.
* conclusiveness: 2 - the cancellation of orders was a one-off, but the rest of this situation is ongoing.
* urgency: 4 - this isn't a very urgent situation from the audience perspective, but there are safety concerns
* source_credibility: 7 - the source was a company announcement of bad news, so we can expect some 'softening' of the news
* clarity: 9 - the article was clear and factual. There was very little deception or distraction
* value: 9 - this is a valuable and factual article that gives important information about the ongoing safety issues and their impact
### COMMENTS: Overall, the article was clear, serious, and credible. We'll have to research the statements made to validate everything but it looks good so far.

and another example:

### REASONING: This article was mostly an opinion piece about the author's feelings about Kamala Harris with lots of opinion and very few facts. 
### ANSWER: 
* seriousness: 6 - Kamala Harris is a presidential candidate so it's important to learn what people think, but this article seems to have a biased agenda.
* objectivity: 2 - lot's of exaggeration, inflammatory rhetoric, and directly quoting different "hot takes" instead of facts
* sentiment: 2 - the sentiment was very negative, though the author tried to be funny at times.
* conclusiveness: 4 - the presidential campaign that the article references is ongoing, though the article itself will not be relevant for very long
* urgency: 2 - there is no call to action that the audience can take or really much they can do about it.
* source_credibility: 2 - this was an editorial by a political commentator, but was an opinion piece and doesn't present any credible facts.
* clarity: 3 - the article seemed to misrepresent and mis-state information and hedged with "some people say..." statements
* value: 2 - not much in the way of value here, other than maybe some context about the opinions of the author and the audience they claim to represent.
### COMMENTS: Overall, the article was an opinion piece with little substance to offer and not much value.

Now apply that style of analysis to this article:
{{ target_str }}
"""
        # init Prompt
        super().__init__(query_template=query_template,
                         examples=examples,
                         is_difficult=is_difficult,
                         is_expedited=is_expedited,
                         temperature=0.0,
                         categories_desc=self.categories_desc,
                         **kwargs)

    def _parse_answer(self, answer_str):
        """
        Parse the answer string to extract only valid labels

        :param answer_str:
        :return:
        """
        answer_str = StringParser.isolate_answer_string(message=answer_str)
        assert '*' in answer_str
        answers = [ans.replace('\n', '').strip() for ans in answer_str.split('*')]
        answers = [ans for ans in answers if ans not in ('', None)]
        return answers
