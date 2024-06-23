"""

Prompts

Prompts use Jinja2 to render complex strings from templates
Tuning variables can be injected into the template to improve performance.
Default templates are provided for classifiers, boolean classifiers, and summarization.

TODOs -
# ideation - make a list of a bunch of ideas
# ideation_more - used for follow-up chat sessions to get more ideation results
# ideation_voting - consolidate and rank the lists. Used to roll up other listicles too.
# ideation_best_n - get a listicle and choose to do the top n choices
# scraping - use fine-tuned LLMs to extract data from scraped pages
# python - write python code, paying attention to add feedback hooks so that the outputs can be evaluated.
# python_is_error - TRUE if a block of text contains a python stacktrace somewhere in it.
# python_feedback - gather feedback on stdout to keep developing or return the finished code.
"""
import copy
import random
from abc import ABC
from jinja2 import Template, StrictUndefined, UndefinedError
from core.adapters.parser import StringParser
from jinja2 import Environment, meta
from core.adapters.llms.inference import Agent


def get_jinja2_variables(template_string):
    env = Environment()
    ast = env.parse(template_string)
    return meta.find_undeclared_variables(ast)


class JsonPromptAttribute:
    """
    Single attribute for a json prompt, used to build descriptions and verify results
    """

    def __init__(self, name, description, options: list = None):
        self.name = name
        self.description = description
        self.options = ''
        if self.options is not None:
            self.options = f"[{','.join(self.options)}]"

    def __str__(self):
        return f"{self.name=}"

    def instructions(self):
        return f"{self.name} - {self.options} {self.description}"


class Prompt(ABC):
    """
    Template renderer to build a prompt from a template.
    Accepts tuning params at instantiation or run-time to allow for prompt engineering
    """

    def __init__(self, target_str=None, chat_history: list[dict] = None, **kwargs):
        self.target_str = target_str or ''
        self.chat_history = chat_history
        self.system_prompt = kwargs.get('system_prompt')
        # Inject the tuning variables. Guided should be added somewhere in template_str if applicable
        self.query_template = kwargs['query_template']
        self.query_formatting = kwargs.get('query_formatting') or """
FORMATTING GUIDE:
Format your response like this (make sure that the sections are in all caps like '### REASONING:' instead of '### Reasoning:'):

### REASONING: <explain your reasoning>
### ANSWER: <just the answer itself, so that our computer system can evaluate it>
### COMMENTS: <any details you'd like to add about your answer. Keep this section but leave it blank if you don't have any comments>
"""
        self.formatting_examples = """
{% if examples %}
Here are some examples:
{% for example in examples %}
{{ loop.index }} - {{ example }}
{% endfor %}
{% else %}
{% endif %}

{{ outro_tuning }}
"""
        self.voting_template = kwargs.get('voting_template') or """
We asked a group of users this question and collected up their answers. Look through the original prompt and what the users said and decide on the best answer.

Here is the original prompt that we gave the users:
{{ original_prompt }}

And here are the {{ answer_list|length }} different answers that the users gave. The section is delimited by triple-backticks:
```
{% for answer in answer_list %}
USER {{ loop.index }} - {{ answer }}
{% endfor %}
```

Build the best possible answer that you can for the original prompt based on the supplied example answers
"""
        self.voting_formatting = kwargs.get('voting_formatting') or """
FORMATTING GUIDE:
Format your response like this (make sure that the sections are in all caps like '### REASONING:' instead of '### Reasoning:'):

### REASONING: <reason about what was good or bad about the answers provided. Put your commentary about other answers here.>
### ANSWER: <just the answer itself, so that our computer system can evaluate it>
### EXPLANATION: <how the answers disagreed, if at all>
"""
        # Build the data dict for template rendering from target_str + subclass variables and optional kwargs
        tuned_data = copy.deepcopy(kwargs)
        tuned_data.update({
            'target_str': self.target_str,
            'query_formatting': self.query_formatting,
            'voting_formatting': self.voting_formatting,
            'intro_tuning': kwargs.get('intro_tuning', ''),
            'guided_tuning': kwargs.get('guided_tuning', ''),
            'outro_tuning': kwargs.get('outro_tuning', ''),
            'examples': kwargs.get('examples')
        })
        self.data = tuned_data
        self.agent = Agent()
        self.query_models = kwargs.get('query_models', Agent().model_names)
        self.voting_model = kwargs.get('voting_model', Agent().model_names[0])

    def update(self, data):
        """
        Update the data object with new data
        """
        self.data.update(data)
        return self.data

    @staticmethod
    def build_target_str_from_headline(title, description):
        return f"title: {title}\ndescription:{description}\n"

    @property
    def template_str(self):
        template_str = "{{ intro_tuning }}\n"
        template_str += self.data['query_template']
        template_str += "\n{{ guided_tuning }}\n"
        template_str += self.data['query_formatting']
        template_str += "\n" + self.formatting_examples
        template_str += "\n{{ outro_tuning }}"
        return template_str

    @property
    def missing_vars(self):
        """
        Get the variables that are required for the Prompt but haven't yet been specified
        """
        env = Environment()
        ast = env.parse(self.template_str)
        var_names = meta.find_undeclared_variables(ast)
        var_names = [vn for vn in var_names if vn not in self.data.keys()]
        return var_names

    def render_query(self):
        """
        Inject the tuning variables into the template and render to build the full text prompt
        """
        # Initialize the template with StrictUndefined to ensure all variables must be defined
        template = Template(self.template_str, undefined=StrictUndefined)
        # render or error
        try:
            return template.render(self.data)
        except UndefinedError:
            # If an undefined variable is encountered, raise an error
            raise ValueError(f"query rendering failed due to an UndefinedError with {self.missing_vars=}")

    def render_voting(self, answer_list: list[str]):
        """
        Render the answers into the finished voting template
        """
        # Initialize the template with StrictUndefined to ensure all variables must be defined
        template = Template(self.voting_template + self.voting_formatting, undefined=StrictUndefined)
        try:
            vote_prompt = template.render({**self.data,
                                           'answer_list': answer_list,
                                           'original_prompt': self.render_query()})
        except UndefinedError as e:
            # If an undefined variable is encountered, raise an error
            raise ValueError(f"query rendering failed due to an UndefinedError {e=} with {self.missing_vars=}")
        return vote_prompt

    def _parse_answer(self, answer_str: str):
        """
        Base answer parsing method to be overridden by child classes when a custom parser is required
        :param answer_str:
        :return:
        """
        return StringParser.isolate_answer_string(message=answer_str)

    def parse_answer(self, answer_str: str):
        """
        Universal parsing interface for Prompts, which accepts strings or full Conversations for convenience
        :param answer_str:
        :return:
        """
        return self._parse_answer(answer_str=answer_str)

    def get_answer(self, model_name=None, num_retries: int = 3):
        for _ in range(num_retries):
            msg_thread = self.agent.to_thread(message=self.render_query(),
                                              system_prompt=self.system_prompt,
                                              chat_history=self.chat_history)
            answer_str = self.agent.get_answer(msg_thread=msg_thread,
                                               model_name=model_name or random.choice(self.query_models))
            # Return the answer if it parses correctly, else retry
            answer_str = self.parse_answer(answer_str)
            if answer_str not in (None, '', ' '):
                return answer_str
        # If no parseable answer is found, return None explicitly
        return None

    def _get_answers(self, model_names=None, num_iterations: int = 3, num_retries: int = 3):
        msg_thread = self.agent.to_thread(message=self.render_query(),
                                          system_prompt=self.system_prompt,
                                          chat_history=self.chat_history)
        answer_list = self.agent.get_answers(msg_thread=msg_thread,
                                             model_names=model_names or self.query_models)
        # Return the answer if it parses correctly, else retry
        answer_list = [self.parse_answer(ans) for ans in answer_list if ans not in (None, '', ' ')]
        if len(answer_list) < num_iterations:
            for _ in range(num_retries):
                ans = self.agent.get_answer(msg_thread=msg_thread,
                                            model_name=random.choice(model_names or self.query_models))
                if self.parse_answer(ans) not in (None, '', ' '):
                    answer_list.append(ans)
                if len(answer_list) == num_iterations:
                    return answer_list
        # Return whatever you can manage
        if len(answer_list) == 0:
            return None
        else:
            return answer_list

    def get_voted_answer_custom(self, model_names=None, voting_model_name=None,
                                num_iterations: int = 3, num_retries: int = 3, do_return_parsed=True):
        """
        Get a batch of answers and then use the voting prompt to deliver a high-quality final answer.
        """
        # Get candidate answers
        answers = self._get_answers(model_names=model_names, num_iterations=num_iterations, num_retries=num_retries)
        if answers is None:
            print(f'WARNING: answers are not parsing correctly for {num_iterations=} {num_retries=} and '
                  f'{self.render_query()}')
            return None, None
        answer_str = None
        # Vote to roll up the results
        for _ in range(num_retries):
            msg_thread = self.agent.to_thread(message=self.render_query(),
                                              system_prompt=self.system_prompt,
                                              chat_history=self.chat_history)
            answer_str = self.agent.get_answer(msg_thread=msg_thread,
                                               model_name=voting_model_name or random.choice(self.query_models))
            # Return the answer if it parses correctly, else retry
            try:
                answer_parsed = self.parse_answer(answer_str)
                if answer_parsed is not None and do_return_parsed:
                    return answers, answer_parsed
                elif answer_parsed is None and not do_return_parsed:
                    return answers, answer_str
                else:
                    raise ValueError(f'answer_str not parsed correctly when {do_return_parsed=}')
            except (ValueError, TypeError) as e:
                print(f"WARNING: {e=} while parsing {answer_str=}")
        return answers, answer_str

    def get_voted_answer(self, num_iterations: int = 3, num_retries: int = 3):
        """
        Simplified interface to get the best possible answer from the prompt in the clearest way possible
        """
        return self.get_voted_answer_custom(num_iterations=num_iterations,
                                            num_retries=num_retries,
                                            do_return_parsed=True)[1]


class BlankPrompt(Prompt):
    """
    Blank template example for testing and documentation
    """

    def __init__(self, target_str, **kwargs):
        query_template = """"""
        voting_template = """"""
        super().__init__(target_str, query_template=query_template, voting_template=voting_template, **kwargs)


class ClassifierPrompt(Prompt):
    def __init__(self, target_str, categories_csv, categories_desc=None, examples=None, **kwargs):
        if isinstance(categories_csv, (list, tuple)):
            categories_csv = ', '.join(categories_csv)
        # Assign a single class / category / label / tag to a story
        query_template = """
Given the following text, classify it into one of the following categories: {{ categories_csv }}

Here is the text that we'll be analyzing:

{{ target_str }}

Choose the category / label that best fits the article and explain your reasoning without mentioning any of the categories that you didn't choose.
The categories you can choose between are: {{ categories_csv }}
{% if categories_desc %}
Here are some details about the categories to guide your analysis:
{{ categories_desc }}
{% else %}      
{% endif %}
"""
        # TOT compiler for the best answers to a classifier prompt
        voting_template = """
We asked a group of users this question and collected up their answers. Look through the original prompt and what the users said and decide on the best answer.

Here is the original prompt that we gave the users:
{{ original_prompt }}

And here are the {{ answer_list|length }} different answers that the users gave. The section is delimited by triple-backticks:
```
{% for answer in answer_list %}
USER {{ loop.index }} - {{ answer }}
{% endfor %}
```

Pick the answer or answers that you agree with, but only if their answers are included in the provided category options. If you agree with many answers, pick one with correct formatting and the best reasoning. If several still fit this criteria, list them in your answer. Just use the categories provided in the prompt for your answer. If you list the categories, make it a comma-delimited list.
"""
        super().__init__(target_str, query_template=query_template, voting_template=voting_template,
                         categories_csv=categories_csv, categories_desc=categories_desc, examples=examples, **kwargs)

    def _parse_answer(self, answer_str):
        class_names = [name.strip() for name in self.data['categories_csv'].split(',')]
        return StringParser.classify_answer(answer_str, class_names=class_names)


class BooleanPrompt(Prompt):
    def __init__(self, target_str, **kwargs):
        query_template = """
{{ prompt_question }} Answer Yes or No and explain your reasoning.

Here is the text that we'll be analyzing:
{{ target_str }}

{{ prompt_question }} Answer "yes" or "no" and explain your reasoning. Give your answer in the following format (make sure that the sections are in all caps like 'REASONING:' instead of 'Reasoning:') - 
"""
        voting_template = """
Given the following prompt, choose the answer from the list provided that gives the best answer.

Here is the prompt:
{{original_prompt}}

And here are the {{ answer_list|length }} answers to choose from:
{% for answer in answer_list %}
USER {{ loop.index }} - {{ answer }}
{% endfor %}

Pick the answer or answers that you agree with, but only if their answers are included in the provided category options. If you agree with many answers, pick one with correct formatting and the best reasoning.

Give your answer in the following format (make sure that the sections are in all caps like 'REASONING:' instead of 'Reasoning:') - 
"""
        super().__init__(target_str, query_template=query_template, voting_template=voting_template, **kwargs)

    # noinspection PyMethodMayBeStatic
    def _parse_answer(self, answer_str):
        answer = StringParser.isolate_answer_string(message=answer_str).lower()
        return 'yes' in answer or 'true' in answer


class ShortAnswerPrompt(Prompt):
    """
    Blank template example for testing and documentation
    """

    def __init__(self, target_str, **kwargs):
        query_template = """
We're going to have a look at some text that we've gathered and try to extract whatever information we can from it.

Here's what we'd like to know:
{{ prompt_question }}

Here is the text that we'll be extracting the information from:
{{ target_str }}

And, just to remind you, here's what we'd like to know:
{{ prompt_question }}
"""
        query_formatting = """
Format your response like this (make sure that the sections are in all caps like '### REASONING:' instead of '### Reasoning:'):
### REASONING: <walk through your reasoning as you choose the right things to say>
### ANSWER: <the direct answer without any commentary>
### COMMENTS: <add any comments you have about the answer here to leave them out of the answer>
"""
        voting_template = """
We gave the following prompt to different people to answer. Use their answers to build your own best answer. Here is the prompt that they were given:
{{ original_prompt }}

And here are the {{ answer_list|length }} different answers people gave. The section is delimited by triple backticks:
```
{% for answer in answer_list %}
USER {{ loop.index }} - {{ answer }}
{% endfor %}
```

Pick the aspects that you like or agree with from those answers and combine them up into the best answer to the prompt. First, give your reasoning about what aspects you liked or didn't like from the answers, then give your own optimal answer. Do not use the word 'answer' in your answer. Finally, give an explanation of how, if at all, the answers disagreed with each other.
"""
        voting_formatting = """
Format your response like this (make sure that the sections are in all caps like '### REASONING:' instead of '### Reasoning:'):

### REASONING: <reason about what was good or bad about the answers provided. Put your commentary about other answers here.>
### ANSWER: <your own best answer in the formatting specified>
### EXPLANATION: <how the answers disagreed, if at all>
"""
        super().__init__(target_str, query_template=query_template, voting_template=voting_template,
                         query_formatting=query_formatting, voting_formatting=voting_formatting, **kwargs)


class JSONPrompt(Prompt):
    """
    Blank template example for testing and documentation
    """

    def __init__(self, target_str, attributes: list[JsonPromptAttribute], **kwargs):
        self.attributes = attributes
        self.instructions = [f" - {att.instructions()}" for att in self.attributes]
        attributes_str = '\n'.join(self.instructions)
        query_template = """
Read the JSON markdown about this article carefully and define its major attributes in a JSON string. The article data will be valid JSON.

Here is the data article:
{{article_text}}

The attributes we're looking for from the data are defined below. The multiple-choice attributes have their options specified in [brackets]:
{{ attributes_str }}

Here is the article data again:
{{article_text}}
"""
        query_formatting = """
We'll feed your answers into a computer to be graded, so it's important that they're formatted as neatly as possible. Format them like:

### REASONING: <take this space to reason about what you know about the article to help fill out these answers>
### ANSWER: <fill out the answers here in pure json like {
    "example": "example answer",
    "example2": "example answer number 2",
}>
### COMMENTS: <add whatever comments you have about the answer here so that the answer stays as clean and easy to parse as possible>

Your answer MUST include sections for REASONING, ANSWER, and COMMENTS in order to be given a passing grade.
"""
        voting_template = """
We gave the following prompt to different people to answer. Use their answers to build your own best answer. Here is the prompt that they were given, delimited by triple backticks:
```{{original_prompt}}```

And here are the {{ answer_list|length }} different answers people gave:
{% for answer in answer_list %}
### USER {{ loop.index }} - {{ answer }}
{% endfor %}

Pick the aspects that you like or agree with from those answers and roll them up into the best answer to the prompt. Don't list them if they disagree, just pick the best answer. First, give your reasoning about what aspects you liked or didn't like from the answers, then give your own optimal answer. Do not use the word 'answer' in your answer. Finally, give an explanation of how, if at all, the answers disagreed with each other.
"""
        voting_formatting = """
Format your response like this (make sure that the sections are in all caps like 'REASONING:' instead of 'Reasoning:'):

### REASONING: <reason about what was good or bad about the answers provided. Put your commentary about other answers here.>
### ANSWER: <your own best answer in valid json formatting>
### EXPLANATION: <how the answers disagreed, if at all>"""
        super().__init__(target_str, query_template=query_template, query_formatting=query_formatting,
                         voting_template=voting_template, voting_formatting=voting_formatting,
                         attributes_str=attributes_str, **kwargs)

    def _parse_answer(self, answer_str):
        """
        Parse the JSON answer string and ensure that it includes all the requested attributes
        """
        answer = StringParser.extract_json_from_answer(answer=answer_str)
        if answer is None:
            raise ValueError(f"cannot parse {answer=}")
        elif any([att.name not in answer for att in self.attributes]):
            raise ValueError(f"{answer=} does not include all of the {self.attributes=}")
        else:
            return answer


class NumberedListPrompt(Prompt):
    """
    Create a numbered list and then parse the results into an array of strings

    Used to create:
    step-by-step plans to accomplish a task (COT)
    lists of possible options for the next step in a process (TOT)
    lists of items found in documents, like date-times, ideas, statements, etc...
    """

    def __init__(self, target_str, **kwargs):
        """
        Build out a numbered list for a prompt. Useful for making a plan, selecting options, or listing ideas.
        :param target_str:
        :param kwargs:
        """
        query_template = """
{{ target_str }}

Please make sure to list your ideas as a numbered list, where each list item starts with the number a dash, and then the idea. You can format the idea itself however your want though. Create one single simple list, rather than creating sections or groups of ideas.

        """
        query_formatting = """
Format your response like this (make sure that the sections are in all caps like '### ANSWER:' instead of '### Answer:'):

### ANSWER: <your full numbered list. Make sure to use the correct numbering format.>
"""
        voting_template = """
We asked a group of users do do the following:
{{original_prompt}}

And here are the {{ answer_list|length }} different answers that the users gave. This section is delimited by triple backticks:
```
{% for answer in answer_list %}
USER {{ loop.index }} - {{ answer }}
{% endfor %}
```

Create your own list based on these lists. Pull together the best ideas from these lists, combining similar ideas together. Your list can be longer than the original prompt asked for, since we want to make sure to capture all these good ideas and can shorten the list again later.
"""
        examples = ["""
List 5 names for a pet dog

### ANSWER:
1 - Spot
2 - Bandit
3 - Shadow
4 - Goldie
5 - Shaggy
"""]
        super().__init__(target_str=target_str, query_template=query_template, voting_template=voting_template,
                         query_formatting=query_formatting, examples=examples, **kwargs)

    # noinspection PyMethodMayBeStatic
    def _parse_answer(self, answer_str):
        answer = StringParser.isolate_answer_string(message=answer_str).lower()
        return StringParser.extract_numbered_list_from_answer(answer=answer)


class BreakingPrompt(Prompt):
    """
    Blank template example for testing and documentation
    """

    def __init__(self, previous_stories: list[str], new_story: str, company_name: str, **kwargs):
        query_template = """
We are comparing a news headline to a list of previous headlines to see if it is new.

Here is a list of previous headlines and description snippets for stories about {{ company_name }}:
{% for story in previous_stories %}
Story {{ loop.index }} - 
{{ story }}
{% endfor %}

And here is the story that we're evaluating to see if it's different from the ones listed above:
{{ new_story }}

Please classify this story in one of the following categories:
BREAKING - this is a new news item that is completely unrelated to the previous items listed. You must be able to explain what the new unique information that this headline introduces actually is, otherwise just call it a repost.
DEVELOPMENT - this is a significant new development in a story that has already been mentioned above. For example, an article about consequences or downstream effects for breaking news stories.
REPOST - this is the same news story as one or many already mentioned, even if some of the details are different. This also includes 'news of the day' or 'news of the week' or 'top stories' kinds of articles that are rolling up multiple previous stories. Or it is just a rephrasing of a story already listed with no new details.
"""
        # TOT compiler for the best answers to a classifier prompt
        voting_template = """We are comparing a news headline to a list of previous headlines to see if it is new.

Here is a list of previous headlines and description snippets for stories about {{ company_name }}:
{% for story in previous_stories %}
Story {{ loop.index }} - 
{{ story }}
{% endfor %}

And here is the story that we're evaluating to see if it's different from the ones listed above:
{{ new_story }}

We asked a group of users to classify this story in one of the following categories:
BREAKING - this is a new news item that is completely unrelated to the previous items listed. You must be able to explain what the new unique information that this headline introduces actually is, otherwise just call it a repost.
DEVELOPMENT - this is a significant new development in a story that has already been mentioned above. For example, an article about consequences or downstream effects for breaking news stories.
REPOST - this is the same news story as one or many already mentioned, even if some of the details are different. This also includes 'news of the day' or 'news of the week' or 'top stories' kinds of articles that are rolling up multiple previous stories. Or it is just a rephrasing of a story already listed with no new details.

And here are the {{ answer_list|length }} different answers people gave:
{% for answer in answer_list %}
### USER {{ loop.index }} - {{ answer }}
{% endfor %}

Based on the previous story, the story we're evaluating, and the answers that other users gave, classify this story into one of the following categories:
BREAKING - this is a new news item that is completely unrelated to the previous items listed. You must be able to explain what the new unique information that this headline introduces actually is, otherwise just call it a repost.
DEVELOPMENT - this is a significant new development in a story that has already been mentioned above. For example, an article about consequences or downstream effects for breaking news stories.
REPOST - this is the same news story as one or many already mentioned, even if some of the details are different. This also includes 'news of the day' or 'news of the week' or 'top stories' kinds of articles that are rolling up multiple previous stories. Or it is just a rephrasing of a story already listed with no new details.

Once again, here is the story we're evaluating - 
{{ new_story }}
"""
        super().__init__(target_str=' ', query_template=query_template, voting_template=voting_template,
                         previous_stories=previous_stories, new_story=new_story, company_name=company_name, **kwargs)

    def _parse_answer(self, answer_str):
        return StringParser.classify_answer(answer_str, class_names=['breaking', 'development', 'repost'])


class NewsAttributesPrompt(JSONPrompt):
    """
    Blank template example for testing and documentation
    """

    def __init__(self, target_str, **kwargs):
        attributes = [
            JsonPromptAttribute(name='is_confusing',
                                description="Is the title or the summary of this article confusing? "
                                            "Does it fail to clearly convey what it's trying to say?",
                                options=['confusing', 'clear']),
            JsonPromptAttribute(name='is_confusing',
                                description="Is the title or the summary of this article confusing? "
                                            "Does it fail to clearly convey what it's trying to say?",
                                options=['confusing', 'clear']),
            JsonPromptAttribute(name='is_confusing',
                                description="Is the title or the summary of this article confusing? "
                                            "Does it fail to clearly convey what it's trying to say?",
                                options=['confusing', 'clear']),
        ]
        attribute_TODO = """
 - is_confusing - ["confusing", "clear"] Is the title or the summary of this article confusing? Does it fail to clearly convey what it's trying to say?
 - is_earnings - [true, false] Is this about an Earnings Call, company financials update and/or a Shareholder's meeting? If any of these are true, answer true.
 - is_promotion - [true, false] Is this a sales or discount promotion, sponsored content, product list, and/or affiliate marketing? If any of these are true, is_promotion is true.
 - is_review - [true, false] Is this a product review?
 - is_trailer - [true, false] Is this a link to a video, trailer, or podcast? If any are true, answer true.
 - is_advice - [true, false] Is this an advice column, recommendation and/or a tutorial? Answer true if any of these are true.
 - is_compilation - [true, false] Is this a compilation of several different new stories, like a daily summary or newsletter?
 - is_criticism - [true, false] Is this article a criticism of how a new story was handled by a different outlet?
 - is_expert_author - [true, false, "unknown"] Is the author an expert in this subject area?
 - is_unsettled_debate - [true, false] Is there an unsettled debate around this topic? Are there two sides to this argument?
 - is_controversial - [true, false] Is the content of the article controversial?
 - implications - ["Broader Implications", "Anecdotal", "Sports", "Lifestyle"] "Anecdotal" stories are stories about crimes happening to average people, criminal convictions of people that aren't powerful or significant, celebrity gossip, opinion pieces, car accidents, traffic jams, and other events that impact a very small number of people without broader implications. "Broader implications" stories have wider effects, like new laws, business news, world events, technology, health, economics, and more. An "Anecdotal" story can become a "Broader Implications" story if the public reaction to the original story creates backlash with Broader Implications, but only if that backlash or conversation is mentioned. The potential for it isn't enough. If you're unsure which of the two to pick, then just pick "Broader Implications". "Lifestyle" stories are food blogs, game and movie reviews, travel stories, advertisements, promotions, local news without broader implication, etc... and "Sports" stories are about amy kind of sport or athletes or record breaking sports events. 
 - location - ["EU", "Asia-Pacific", "Russia", "China", "South and Central America", "Africa", "New Zealand", "US", "Canada", "Unclear", "Unspecified"] Specify the region of the world that the events of the article take place in.
 - news_type - ["Politics", "Economics and Finance", "War", "Entertainment", "Business", "Science", "Technology", "Lifestyle", "Human Interest", "Forum Post", "Listicle", "Tutorial", "Health", "Civil Rights", "Cryptocurrency", "Stock or Commodities Markets"] What kind of news story is this? Reason about the content, context, and affected parties and what section of a news site they would make sense in. What section should this be in so that someone looking for it can find it?
 - timing - ["More than a month ago", "Less than a month ago", "Yesterday", "Today", "Tomorrow", "Less than a month from now", "More than a month from now", "Unclear", "No specific event mentioned"] Choose when the events in the article took place, not when the article was written or the events were commented on. This is specifically with reference to the start time of the events referenced in the article. If the article is about a new development in an ongoing event, then the start time is the start of the development, not the broader event that it is changing.
 - fact_or_opinion - ["Fact", "Opinion", "Mixed"] Is the content of the article primarily facts, opinions, or mixed facts and opinions?
 - positivity - ["Very Positive", "Somewhat Positive", "Neutral", "Somewhat Negative", "Very Negative"] How positive is the attitude of this article?
 - political_polarity - ["Far Left", "Left", "Moderate", "Far Right", "Right", "Unknown"] Choose where on the political spectrum that the article falls, if applicable.
 - perspective - ["First-Hand", "Second-Hand", "Third-Hand", "Rumor", "Unclear"] From what perspective is the article written?
 - aggression - ["Compassionate", "Neutral", "Aggressive"] How aggressive is the tone of the article?
 - seriousness - ["Serious", "Humorous", "Satirical", "Sarcastic"] How serious is the tone of the article?
 - debate - Is there an unsettled debate around this topic? Explain the two sides, if they exist, in less than 50 words each.
 - log_line - What is the key subject of this article in 5-7 words? Make sure to include the specific parties involved, where applicable.
 - company - Does this article impact a company or companies other than the publisher? Make a comma-delimited list of companies affected, but hold your analysis on them for a follow-up question.
 - industry - ["Agriculture, Forestry, and Fishing", "Mining and Energy", "Manufacturing", "Construction and Real Estate", "Wholesale and Retail Trade", "Transportation and Logistics", "Information Technology", "Finance and Insurance", "Professional and Business Services", "Health Care", "Arts, Entertainment, and Recreation", "Food Services", "Government and Defense", "Education", "Other"] Does this article impact an industry or industries other than the publisher? Make a comma-delimited list of companies affected, but hold your analysis on them for a follow-up question.
 - important_dates - Isolate any important dates in this article and format them YYYY-MM-DD like 2024-03-05. List the dates and why they are important. If dates are relative, assume that they are relative to the publish date. So it it says that something happened on Wednesday and the article was published today which is 2024-03-08 and a Friday, the it is most likely referencing Wednesday 2024-03-06, two days ago.
 - hedge_manager_importance - ["Very Important", "Somewhat Important", "Worth Noting", "Irrelevant"] As a hedge fund manager, how important is the information in this article to you? Rank its importance with "Very Important" being absolutely critically urgent. Consider the impact on companies, industries, supply chains, regulations, or financial instruments we might be invested in and err on the side of caution.
 - hedge_manager_comments - As a hedge fund manager, what do you project to be the potential impact of this new development on companies, industries, supply chains, regulations, or financial instruments in both the near term and the long term? List out all possible impacts in order of importance.
"""
        example = """Example response for an article about a shuttle's deorbit:

### REASONING:
The article is not about earnings, as there is no mention of financial results or calls. The author's name is listed, but no further information is provided about their expertise or background. The article's focus is on astronaut Charles Bolden preparing for the shuttle's deorbit. The article's title and description also indicate that the article is clear and concise in explaining the topic.
### ANSWER:
{
"is_confusing": "clear",
"is_earnings": false,
"is_promotion": false,
"is_review": false,
"is_trailer": false,
"is_advice": false,
"is_compilation": false,
"is_criticism": false,
"is_expert_author": false,
"is_unsettled_debate": false,
"is_controversial": false,
"implications": "Broader Implications",
"location": "Unspecified",
"news_type": "Human Interest",
"timing": "Today",
"fact_or_opinion": "Fact",
"positivity": "Neutral",
"political_polarity": "Unknown",
"perspective": "First-Hand",
"aggression": "Neutral",
"seriousness": "Serious",
"log_line": "Astronaut Charles Bolden Preps for Deorbit",
"company": "NASA, SpaceX",
"industry": "Aerospace",
"important_dates": "2024-02-17 - next update, 2024-02-19 - date of planned deorbit",
"hedge_manager_importance": "Worth Noting",
"hedge_manager_comments": "As a Hedge Fund Manager, I might ask for more information about the participating companies, their partners, and their competitors. Spacex is privately owned, but there may be implications for their publicly-traded competitors. I'd like to review the data we have on programs at leading aerospace companies so that we can make some future projections for them."
}
### COMMENTS:
As there is no debate or controversy mentioned in the article, those answers were omitted. The implications and hedge_mgr answers were based on the article's focus on an important event for the astronaut and NASA, rather than broader societal implications or financial ramifications. The news_type was chosen because it is about a person and their actions, rather than politics, economics, or other topics. The location was left unspecified as the article does not mention a specific location for the event.

Format your answer like this, but for the article given.

"""
        super().__init__(target_str, attributes=attributes, examples=[example], **kwargs)


class RAGIngestPrompt(ShortAnswerPrompt):
    """
    Clean up information to be entered into the RAG, fixing parsing and formatting errors and deleting fragments.
    This should make retrieval more efficient and accurate.
    """

    def __init__(self, target_str, **kwargs):
        query_template = """
We're going to have a look at some text that we've gathered and try to extract whatever information we can from it. Please clean up formatting issues, fix character encoding errors, remove accidentally collected HTML or navigation information (some of this data comes from html web pages).

Wherever possible, try to reduce redundancy and improve clarity in the text. We want our summary to be as brief and matter-of-fact as possible, without missing any facts or details.

Here is the text that we'll be extracting the information from:
{{ target_str }}
"""
        query_formatting = """
Format your response like this (make sure that the sections are in all caps like '### ANSWER:' instead of '### Answer:'):
### ANSWER: <the optimized text passage>
### COMMENTS: <information that you think should be added or open questions that the text passage raised but didn't answer>
"""
        super().__init__(target_str, query_template=query_template, query_formatting=query_formatting, **kwargs)


class RankLikelihoodPrompt(Prompt):
    """
    Given a numbered list of text samples rank them from X to Y.
    Used to select the most likely choice in a list of options and provide alternative branches to follow
    should the most likely branch dead-end.
    Used for:
     - Choosing alternatives while planning
     - Choosing pages to crawl from Google searches
     - Choosing RAG results to include in an answer
    """

    def __init__(self, target_strs: list, **kwargs):
        target_str = [f"{idx} - {target}" for idx, target in enumerate(target_strs)]
        target_str = '\n'.join(target_str)
        query_template = """
We're going to have a look at some numbered text samples that we've gathered and try rank them in order.

Here's what we'd like to know:
{{ prompt_question }}

Here are the text samples:
{{ target_str }}

And, just to remind you, here's the order that we'd like you to put the numbered samples in:
{{ prompt_question }}
"""
        query_formatting = """
Format your response like this (make sure that the sections are in all caps like '### REASONING:' instead of '### Reasoning:'):
### REASONING: <walk through your reasoning as you choose the right things to say>
### ANSWER: <a comma-delimited list of the of numbers in the order you think is best. Example: 3,2,4,5,1>
### COMMENTS: <add any comments you have about the answer here to leave them out of the answer>
"""
        voting_template = """
We gave the following prompt to different people to answer. Use their answers to build your own best answer. Here is the prompt that they were given:
{{ original_prompt }}

And here are the {{ answer_list|length }} different answers people gave. The section is delimited by triple backticks:
```
{% for answer in answer_list %}
USER {{ loop.index }} - {{ answer }}
{% endfor %}
```

Based on what you've seen, what order do you think we should put these numbered text samples in?
"""
        voting_formatting = """
Format your response like this (make sure that the sections are in all caps like '### REASONING:' instead of '### Reasoning:'):

### REASONING: <reason about what was good or bad about the answers provided. Put your commentary about other answers here.>
### ANSWER: <a comma-delimited list of the of numbers in the order you think is best. Example: "3,2,4,5,1" >
### EXPLANATION: <how the answers disagreed, if at all>
"""
        super().__init__(target_str, query_template=query_template, voting_template=voting_template,
                         query_formatting=query_formatting, voting_formatting=voting_formatting, **kwargs)

    # noinspection PyMethodMayBeStatic
    def _parse_answer(self, answer_str):
        answer_str = StringParser.isolate_answer_string(message=answer_str)
        answer = [ans.strip() for ans in answer_str.replace('"', '').split(',')]
        out_answer = []
        for ans in answer:
            if ans.isnumeric():
                out_answer.append(int(ans))
        if out_answer:
            return out_answer
        else:
            return None


class ConsolidateChatPrompt(Prompt):
    """
    Given a long chat thread, a snowball prompt chain for example, simplify the thread as if it were a single user
    question and response.
    """

    def __init__(self, target_str, **kwargs):
        query_template = """
We're going to have a look at a chat session between a user and an assistant. This session is a bit long and complicated. Can you summarize the session so that it looks like it's just one user request and the response contains all the information from the series?

Here's the chat session:
{{ prompt_question }}

When consolidating this chat so that it appears to be just one user request and one response, compile all the details that the user provided throughout the series to the original request so their request is as thorough as possible.

When summarizing the assistant's response, make sure to include all the details in their response as if they intuitively understood everything about the prompt and gave all the detail in their first response.

Remove all formatting instructions, prompt engineering, and markdown. We just want to keep all the important facts of the conversation as if the user asked as clearly as possible and the assistant responded with all important details.

We won't have access to the original chat thread when evaluating your response, so make sure to include all details without placeholders. If you reference the original chat series in your response, we won't be able to find the information that you are referencing. So make sure to be as thorough as possible in your summary and include every detail we will need to make it make sense.
"""
        query_formatting = """
Format your response like this (make sure that the sections are in all caps like '### REASONING:' instead of '### Reasoning:'):
### REASONING: <walk through your reasoning as you choose the right things to say>
### ANSWER: <a chat session with exactly one USER: and one ASSISTANT: section summarizing the chat>
USER: <the consolidated user prompt>
ASSISTANT: <the consolidated assistant response>
### COMMENTS: <add any comments you have about the answer here to leave them out of the answer>
"""
        voting_template = """
We gave the following prompt to different people to answer. Use their answers to build your own best answer. Here is the prompt that they were given:
{{ original_prompt }}

And here are the {{ answer_list|length }} different answers people gave. The section is delimited by triple backticks:
```
{% for answer in answer_list %}
USER {{ loop.index }} - {{ answer }}
{% endfor %}
```

Based on what you've seen, what is the best possible way that we could summarize this chat?
"""
        voting_formatting = """
Format your response like this (make sure that the sections are in all caps like '### REASONING:' instead of '### Reasoning:'):

### REASONING: <reason about what was good or bad about the answers provided. Put your commentary about other answers here.>
### ANSWER: <a chat session with exactly one USER: and one ASSISTANT: section summarizing the chat>
USER: <the consolidated user prompt>
ASSISTANT: <the consolidated assistant response>
### EXPLANATION: <how the answers disagreed, if at all>
"""
        super().__init__(target_str, query_template=query_template, voting_template=voting_template,
                         query_formatting=query_formatting, voting_formatting=voting_formatting, **kwargs)

    # noinspection PyMethodMayBeStatic
    def _parse_answer(self, answer_str):
        """
        Separate the consolidated user prompt from the consolidated response prompt
        :param answer_str:
        :return:
        """
        answer_str = StringParser.isolate_answer_string(message=answer_str)
        if 'ASSISTANT:' not in answer_str or 'USER:' not in answer_str:
            print(f"WARNING: answer_str missing ASSISTANT: or USER: for {answer_str=}")
            return None
        else:
            user_str = answer_str.split('ASSISTANT:')[0].split('USER:')[-1].strip()
            assistant_str = answer_str.split('ASSISTANT:')[-1].strip()
            return [user_str, answer_str]


class PromptGeneratorPrompt(NumberedListPrompt):
    """
    Generate a list of follow-up prompts in ranked order based on the current chat session
    """

    def __init__(self, target_str, **kwargs):
        target_str = """
Based on the following chat conversation, write some follow-up prompts for the user. The prompts should be clear, specific, and listed in order of importance.
""" + target_str
        super().__init__(target_str, **kwargs)


class ToolSelectorPrompt(ClassifierPrompt):
    """
    Choose the next action to take from a collection of possible choices. For example, do the next step in the plan,
    ask for user clarification, or generate a list of options.
    """

    def __init__(self, target_str, **kwargs):
        # TODO - build out prompt choices
        target_str = """
Based on the following chat conversation, write some follow-up prompts for the user. The prompts should be clear, specific, and listed in order of importance.
""" + target_str
        super().__init__(target_str, **kwargs)
