import pytest
from unittest.mock import MagicMock, patch
from core.adapters.parsers.string import StringParser
from core.daos.llms.prompt import Prompt, ClassifierPrompt


def test_base_prompt_parsing():
    prompt = Prompt(target_str='blah blah blah', query_template=' ', voting_template=' ')
    assert prompt.parse_answer('### REASONING: <explain your reasoning>\n'
                               '### ANSWER: one\n'
                               "### COMMENTS: <any details you'd like to add about your answer. Keep this "
                               "section but leave it blank if you don't have any comments>\n") == 'one'


@pytest.fixture
def prompt_instance():
    return Prompt(
        query_template="{{ target_str }}",
    )


@pytest.fixture
def classifier_prompt():
    prompt = ClassifierPrompt(
        prompt_explanation='Classify the sample text into one of the following categories: ',
        categories_dict={'one': 'the first one', 'two': 'the second option', 'three': 'the third'})
    assert prompt.data['target_str'] == ''
    assert prompt.categories_csv == 'one,two,three,none'
    assert prompt.categories_desc == 'one - the first one\ntwo - the second option\nthree - the third\nnone - none'
    assert prompt.examples is None
    return prompt


def test_init(prompt_instance):
    assert prompt_instance.target_str == ''
    assert prompt_instance.query_template == "{{ target_str }}"


def test_template_str(prompt_instance):
    prompt_instance.data['query_template'] = "{{ target_str }}"
    expected_template = (
        "{{ intro_tuning }}\n{{ target_str }}\n\n"
        "{% if examples %}\nHere are some examples:\n{% for example in examples %}\n"
        "{{ loop.index }} - {{ example }}\n{% endfor %}\n{% else %}\n{% endif %}\n\n"
        "{{ outro_tuning }}"
    )
    assert prompt_instance.template_str == expected_template


def test_missing_vars(prompt_instance):
    pi = Prompt(query_template='{{ undeclared_var }}')
    assert 'undeclared_var' in pi.missing_vars


def test_render_query_success(prompt_instance):
    prompt_instance.query_template = "{{ target_str }}"
    prompt_instance.target_str = "Test Target"
    result = prompt_instance.render_query()
    assert "Test Target" in result


def test_render_query_failure(prompt_instance):
    prompt_instance.query_template = "{{ missing_var }}"
    with pytest.raises(ValueError):
        prompt_instance.render_query()


def test_parse_answer(prompt_instance):
    answer_str = "### ANSWER: This is an answer"
    with patch.object(StringParser, 'isolate_answer_string', return_value=answer_str):
        result = prompt_instance.parse_answer(answer_str)
        assert result == answer_str


def test_get_answer(prompt_instance):
    mock_agent = MagicMock()
    prompt_instance.agent = mock_agent
    prompt_instance.render_query = MagicMock(return_value="Test Query")
    mock_agent.get_answer = MagicMock(return_value="Parsed Answer")

    with patch.object(prompt_instance, 'parse_answer', return_value="Parsed Answer"):
        result = prompt_instance.get_answer()
        assert result == "Parsed Answer"


def test_classifier_prompt_parsing():
    prompt = ClassifierPrompt(
        target_str='Given the following text, classify it into one of the following categories: ',
        categories_dict={'one': 'the first one', 'two': 'the second option', 'three': 'the third'})
    # Ensure that the answer is tolerant of spacing and newline characters
    assert prompt.parse_answer('### REASONING: <explain your reasoning>\n'
                               '### ANSWER:    two\n\n'
                               "### COMMENTS: <any details you'd like to add about your answer. Keep this "
                               "section but leave it blank if you don't have any comments>\n") == ['two']
    # Ensure that none is returned if the answer doesn't match a class
    assert prompt.parse_answer('### REASONING: <explain your reasoning>\n'
                               '### ANSWER: xxx\n'
                               "### COMMENTS: <any details you'd like to add about your answer. Keep this "
                               "section but leave it blank if you don't have any comments>\n") is None
