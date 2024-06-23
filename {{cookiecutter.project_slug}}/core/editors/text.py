def get_title_case_exceptions():
    """
    Get the words that shouldn't be capitalized in titles
    :return:
    :rtype:
    """
    return ['and', 'as', 'but', 'for', 'if', 'nor', 'or', 'so', 'yet', 'a', 'an', 'the',
            'as', 'at', 'by', 'for', 'in', 'of', 'off', 'on', 'per', 'to', 'up', 'via']


def titleize(text, exceptions=None):
    """
    Convert a title to proper title case, ignoring standard exceptions to title casing in english
    :param text: single sentence input text
    :type text: str
    :param exceptions: (optional) list of words that shouldn't be capitalized. Uses default list if not specified.
    :type exceptions: list[str]
    :return: Properly title cased sentence
    :rtype: str
    """
    if exceptions is None:
        exceptions = get_title_case_exceptions()
    return ' '.join([word if word in exceptions else word.title()
                     for word in text.lower().split()]).capitalize()


def remove_empty_strings_from_list(str_list):
    """
    Remove empty or blank values from a list
    :param str_list:
    :type str_list:
    :return:
    :rtype:
    """
    return [item for item in str_list if item.strip() not in (None, '', 'None', 'null', 'undefined', -1)]
