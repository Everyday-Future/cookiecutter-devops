import pytest
from core.adapters.llms.prompt import Prompt, ClassifierPrompt


def test_prompt_init():
    prompt = Prompt(target_str='blah blah blah',
                    query_template='test: {{ target_str }}',
                    voting_template='voting {{ original_prompt }}')
    assert prompt.data == {'examples': None,
                           'guided_tuning': '',
                           'intro_tuning': '',
                           'outro_tuning': '',
                           'query_formatting': '\n'
                                               'FORMATTING GUIDE:\n'
                                               'Format your response like this (make sure that the '
                                               "sections are in all caps like '### REASONING:' instead "
                                               "of '### Reasoning:'):\n"
                                               '\n'
                                               '### REASONING: <explain your reasoning>\n'
                                               '### ANSWER: <just the answer itself, so that our '
                                               'computer system can evaluate it>\n'
                                               "### COMMENTS: <any details you'd like to add about your "
                                               'answer. Keep this section but leave it blank if you '
                                               "don't have any comments>\n",
                           'query_template': 'test: {{ target_str }}',
                           'target_str': 'blah blah blah',
                           'voting_formatting': '\n'
                                                'FORMATTING GUIDE:\n'
                                                'Format your response like this (make sure that the '
                                                "sections are in all caps like '### REASONING:' instead "
                                                "of '### Reasoning:'):\n"
                                                '\n'
                                                '### REASONING: <reason about what was good or bad about '
                                                'the answers provided. Put your commentary about other '
                                                'answers here.>\n'
                                                '### ANSWER: <just the answer itself, so that our '
                                                'computer system can evaluate it>\n'
                                                '### EXPLANATION: <how the answers disagreed, if at '
                                                'all>\n',
                           'voting_template': 'voting {{ original_prompt }}'}
    assert prompt.query_template == 'test: {{ target_str }}'
    assert prompt.query_formatting == ('\n'
                                       'FORMATTING GUIDE:\n'
                                       'Format your response like this (make sure that the sections are in all caps '
                                       "like '### REASONING:' instead of '### Reasoning:'):\n"
                                       '\n'
                                       '### REASONING: <explain your reasoning>\n'
                                       '### ANSWER: <just the answer itself, so that our computer system can '
                                       'evaluate it>\n'
                                       "### COMMENTS: <any details you'd like to add about your answer. Keep this "
                                       "section but leave it blank if you don't have any comments>\n")
    assert prompt.voting_template == 'voting {{ original_prompt }}'
    assert prompt.voting_formatting == (
        '\n'
        'FORMATTING GUIDE:\n'
        'Format your response like this (make sure that the sections are in all caps '
        "like '### REASONING:' instead of '### Reasoning:'):\n"
        '\n'
        '### REASONING: <reason about what was good or bad about the answers '
        'provided. Put your commentary about other answers here.>\n'
        '### ANSWER: <just the answer itself, so that our computer system can '
        'evaluate it>\n'
        '### EXPLANATION: <how the answers disagreed, if at all>\n')
    prompt.query_template = 'test: {{ target_str }}'
    assert prompt.render_query() == (
        '\n'
        'test: blah blah blah\n'
        '\n'
        '\n'
        'FORMATTING GUIDE:\n'
        'Format your response like this (make sure that the sections are in all caps '
        "like '### REASONING:' instead of '### Reasoning:'):\n"
        '\n'
        '### REASONING: <explain your reasoning>\n'
        '### ANSWER: <just the answer itself, so that our computer system can '
        'evaluate it>\n'
        "### COMMENTS: <any details you'd like to add about your answer. Keep this "
        "section but leave it blank if you don't have any comments>\n"
        '\n'
        '\n'
        '\n'
        '\n'
        '\n'
        '\n'
        '\n')
    prompt.voting_template = '''test: {{ target_str }}
And here are the answers to choose from:
{% for answer in answer_list %}
USER {{ loop.index }} - {{ answer }}
{% endfor %}
'''
    answer_list = ['one', 'two', 'three']
    assert prompt.render_voting(answer_list=answer_list) == (
        'test: blah blah blah\n'
        'And here are the answers to choose from:\n'
        '\n'
        'USER 1 - one\n'
        '\n'
        'USER 2 - two\n'
        '\n'
        'USER 3 - three\n'
        '\n'
        '\n'
        'FORMATTING GUIDE:\n'
        'Format your response like this (make sure that the sections are in all caps '
        "like '### REASONING:' instead of '### Reasoning:'):\n"
        '\n'
        '### REASONING: <reason about what was good or bad about the answers '
        'provided. Put your commentary about other answers here.>\n'
        '### ANSWER: <just the answer itself, so that our computer system can '
        'evaluate it>\n'
        '### EXPLANATION: <how the answers disagreed, if at all>'
    )


def test_base_prompt_parsing():
    prompt = Prompt(target_str='blah blah blah', query_template=' ', voting_template=' ')
    assert prompt.parse_answer('### REASONING: <explain your reasoning>\n'
                               '### ANSWER: one\n'
                               "### COMMENTS: <any details you'd like to add about your answer. Keep this "
                               "section but leave it blank if you don't have any comments>\n") == 'one'


def test_classifier_prompt():
    prompt = ClassifierPrompt(target_str='blah', categories_csv='one,two,three',
                              query_formatting=' ', voting_formatting=' ')
    assert prompt.data['target_str'] == 'blah'
    assert prompt.data['categories_csv'] == 'one,two,three'
    assert prompt.data['categories_desc'] is None
    assert prompt.data['examples'] is None
    assert prompt.query_template == ('\n'
                                     'Given the following text, classify it into one of the following categories: '
                                     '{{ categories_csv }}\n'
                                     '\n'
                                     "Here is the text that we'll be analyzing:\n"
                                     '\n'
                                     '{{ target_str }}\n'
                                     '\n'
                                     'Choose the category / label that best fits the article and explain your '
                                     "reasoning without mentioning any of the categories that you didn't choose.\n"
                                     'The categories you can choose between are: {{ categories_csv }}\n'
                                     '{% if categories_desc %}\n'
                                     'Here are some details about the categories to guide your analysis:\n'
                                     '{{ categories_desc }}\n'
                                     '{% else %}      \n'
                                     '{% endif %}\n')
    assert prompt.voting_template == (
        '\n'
        'We asked a group of users this question and collected up their answers. Look '
        'through the original prompt and what the users said and decide on the best '
        'answer.\n'
        '\n'
        'Here is the original prompt that we gave the users:\n'
        '{{ original_prompt }}\n'
        '\n'
        'And here are the {{ answer_list|length }} different answers that the users '
        'gave. The section is delimited by triple-backticks:\n'
        '```\n'
        '{% for answer in answer_list %}\n'
        'USER {{ loop.index }} - {{ answer }}\n'
        '{% endfor %}\n'
        '```\n'
        '\n'
        'Pick the answer or answers that you agree with, but only if their answers '
        'are included in the provided category options. If you agree with many '
        'answers, pick one with correct formatting and the best reasoning. If several '
        'still fit this criteria, list them in your answer. Just use the categories '
        'provided in the prompt for your answer. If you list the categories, make it '
        'a comma-delimited list.\n')
    assert prompt.render_query() == ('\n'
                                     '\n'
                                     'Given the following text, classify it into one of the following categories: '
                                     'one,two,three\n'
                                     '\n'
                                     "Here is the text that we'll be analyzing:\n"
                                     '\n'
                                     'blah\n'
                                     '\n'
                                     'Choose the category / label that best fits the article and explain your '
                                     "reasoning without mentioning any of the categories that you didn't choose.\n"
                                     'The categories you can choose between are: one,two,three\n'
                                     '      \n'
                                     '\n'
                                     '\n'
                                     '\n'
                                     ' \n'
                                     '\n'
                                     '\n'
                                     '\n'
                                     '\n'
                                     '\n'
                                     '\n')
    answer_list = ['one', 'two', 'three', ]
    assert prompt.render_voting(answer_list=answer_list) == (
        '\n'
        'We asked a group of users this question and collected up their answers. Look '
        'through the original prompt and what the users said and decide on the best '
        'answer.\n'
        '\n'
        'Here is the original prompt that we gave the users:\n'
        '\n'
        '\n'
        'Given the following text, classify it into one of the following categories: '
        'one,two,three\n'
        '\n'
        "Here is the text that we'll be analyzing:\n"
        '\n'
        'blah\n'
        '\n'
        'Choose the category / label that best fits the article and explain your '
        "reasoning without mentioning any of the categories that you didn't choose.\n"
        'The categories you can choose between are: one,two,three\n'
        '      \n'
        '\n'
        '\n'
        '\n'
        ' \n'
        '\n'
        '\n'
        '\n'
        '\n'
        '\n'
        '\n'
        '\n'
        '\n'
        'And here are the 3 different answers that the users gave. The section is '
        'delimited by triple-backticks:\n'
        '```\n'
        '\n'
        'USER 1 - one\n'
        '\n'
        'USER 2 - two\n'
        '\n'
        'USER 3 - three\n'
        '\n'
        '```\n'
        '\n'
        'Pick the answer or answers that you agree with, but only if their answers '
        'are included in the provided category options. If you agree with many '
        'answers, pick one with correct formatting and the best reasoning. If several '
        'still fit this criteria, list them in your answer. Just use the categories '
        'provided in the prompt for your answer. If you list the categories, make it '
        'a comma-delimited list.\n'
        ' ')


def test_classifier_prompt_parsing():
    prompt = ClassifierPrompt(target_str='blah', categories_csv='one,two,three',
                              query_formatting=' ', voting_formatting=' ')
    # Ensure that the answer is tolerant of spacing and newline characters
    assert prompt.parse_answer('### REASONING: <explain your reasoning>\n'
                               '### ANSWER:    two\n\n'
                               "### COMMENTS: <any details you'd like to add about your answer. Keep this "
                               "section but leave it blank if you don't have any comments>\n") == 'two'
    # Ensure that none is returned if the answer doesn't match a class
    assert prompt.parse_answer('### REASONING: <explain your reasoning>\n'
                               '### ANSWER: xxx\n'
                               "### COMMENTS: <any details you'd like to add about your answer. Keep this "
                               "section but leave it blank if you don't have any comments>\n") is None
