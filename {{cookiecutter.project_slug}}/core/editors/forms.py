import re
import json


def sanitize_input_basic(in_str):
    """
    Only remove " ' ; < and > from strings
    :param in_str:
    :type in_str:
    :return:
    :rtype:
    """
    return in_str.replace('"', '').replace("'", '').replace(';', '.').replace('<', '.').replace('>', '.').strip()


def sanitize_input(in_str):
    """
    Replace all chars that aren't alpha or space or @ , . with .
    :param in_str:
    :type in_str:
    :return:
    :rtype:
    """
    return re.sub(r'[^A-Za-z0-9áéíóúñü@ ,_-]+', '.', in_str).strip()


def sanitize_json(data):
    """
    Remove special characters from json data
    :param data:
    :type data:
    :return:
    :rtype:
    """
    return json.loads(json.dumps(data).replace(';', '.').replace('<', '').replace('>', ''))
