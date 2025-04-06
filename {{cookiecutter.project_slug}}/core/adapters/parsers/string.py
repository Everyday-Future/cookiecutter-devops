# core/adapters/parsers/string.py
import re
import json
import uuid
import string
import base64
import random
import codecs
from json import JSONDecodeError
from config import logger


class StringParser:

    @staticmethod
    def generate_short_uuid():
        """
        Generate a 22-character "short" unique ID for string IDs
        """
        # Generate a random UUID
        uuid_bytes = uuid.uuid4().bytes
        # Encode the UUID using base64 and remove the padding
        short_uuid = base64.urlsafe_b64encode(uuid_bytes).rstrip(b'=').decode('utf-8')
        return short_uuid

    @staticmethod
    def remove_extra_newlines(text):
        """
        Use regular expressions to replace sequences of 3 or more newlines with exactly two newlines

        :param text:
        :return:
        """
        cleaned_text = re.sub(r'\n{3,}', '\n\n', text)
        return cleaned_text

    @staticmethod
    def num_matches(query, body):
        """
        Count the number of occurrences of a keyword in a string
        """
        return sum([body.count(each_word) for each_word in query.split(' ')])

    @staticmethod
    def title_to_snake(target_str):
        """
        Turns a Title Case String into a snake_case_string

        :param target_str:
        :type target_str:
        :return:
        :rtype:
        """
        return '_'.join(str(target_str).lower().split(' '))

    @staticmethod
    def camel_to_snake(text: str) -> str:
        """
        Convert a camelCase string to snake_case.
        """
        pattern = re.compile(r'(?<!^)(?=[A-Z])')
        return pattern.sub('_', text).lower()

    @staticmethod
    def snake_to_camel(text: str) -> str:
        """
        Convert a snake_case string to camelCase.
        """
        components = text.split('_')
        return components[0] + ''.join(x.title() for x in components[1:])

    @staticmethod
    def snake_to_pascal(text: str) -> str:
        """
        Convert a snake_case string to PascalCase.
        """
        return ''.join(x.title() for x in text.split('_'))

    @staticmethod
    def get_string_within_max_chars(target_str: str, max_chars: int = 8000, mode: str = 'middle') -> str:
        """
        Some of these functions are limited by the length of string that they can consume.
        So we have to cut it off at a specific character count. But often the content that we want is
        in the middle of the string and not at the beginning or end.

        So this is a quick function to sample up to a threshold number of characters from the middle of the string.
        :param target_str:
        :param max_chars:
        :param mode: Where the string will be cut off in overflow 'start' 'end' 'middle' (default) and 'random'
        :return:
        """
        if len(target_str) > max_chars:
            if mode == 'start':
                return target_str[:max_chars]
            elif mode == 'end':
                return target_str[-max_chars:]
            elif mode == 'middle':
                # Calculate the start index to get the middle_chars
                start_index = (len(target_str) - max_chars) // 2
                return target_str[start_index:start_index + max_chars]
            elif mode == 'random':
                # Calculate the maximum start index to get a random window within max_chars
                start_index = random.randint(0, len(target_str) - max_chars - 1)
                return target_str[start_index:start_index + max_chars]
        else:
            return target_str

    @staticmethod
    def clean_answer(answer):
        """ Strip an answer to alphanumeric and spaces, lower, and replace spaces with underscores"""
        return re.sub(r'[^A-Za-z0-9 ]+', '', str(answer)).replace(' ', '_').lower().strip()

    @staticmethod
    def parse_escaped_string(input_string):
        # Pattern to detect common escape sequences
        escaped_pattern = re.compile(r'\\u[0-9a-fA-F]{4}|\\x[0-9a-fA-F]{2}|\\[\\\'\"nrtbf]')

        # Check if the string contains escape sequences
        if escaped_pattern.search(input_string):
            # Safe method to decode escape sequences
            return codecs.decode(input_string, 'unicode_escape')
        else:
            # No escape sequences detected, return original
            return input_string

    @staticmethod
    def remove_json_comments(json_str):
        """Match C-style comments (// to end of line) and remove them"""
        result = ""
        in_string = False
        escape_char = False
        i = 0
        while i < len(json_str):
            # Handle string boundaries
            if json_str[i] == '"' and not escape_char:
                in_string = not in_string
                result += json_str[i]
            # Handle escape characters
            elif json_str[i] == '\\' and in_string:
                escape_char = not escape_char
                result += json_str[i]
            # Handle comments
            elif json_str[i:i+2] == '//' and not in_string:
                # Skip to the end of the line
                while i < len(json_str) and json_str[i] != '\n':
                    i += 1
                if i < len(json_str):
                    result += json_str[i]  # Keep the newline
            else:
                # Reset escape character flag if not escaping
                if escape_char:
                    escape_char = False
                result += json_str[i]
            i += 1
        return result

    @classmethod
    def yes_no_to_bool(cls, answer):
        """ Coerce a yes/no answer into a bool True/False column """
        return cls.clean_answer(answer) in ('y', 'yes', 't', 'true')

    @staticmethod
    def parse_location_coordinates(answer):
        """Get a dict of lists of coordinates from a \n separated string """
        lines = [loc.strip() for loc in answer.split('\n') if len(loc) > 10]
        out_dict = {}
        for line in lines:
            try:
                location = line.split('(')[0].strip()
                coord = line.split('(')[-1].split(')')[0].strip()
                if len(location) > 5 and len(coord) > 5 and '°' not in coord and ',' in coord:
                    out_dict[location] = [float(crd.strip()) for crd in coord.split(',')]
            except (ValueError, UnicodeDecodeError):
                try:
                    print(f'error parsing coordinates from answer_line={line}')
                except UnicodeDecodeError:
                    print('unicode decode error when parsing coordinates')
                return None
        if len(out_dict.values()) == 0:
            print(f'error parsing coordinates from answer={answer}')
            return None
        else:
            return out_dict

    @staticmethod
    def normalize_newlines(text):
        """
        Turn blocks of newlines into a single newline character to simplify printing and logging.
        """
        text = re.sub(r'\n+', '\n', text)
        if text.startswith('\n'):
            text = text[1:]
        if text.endswith('\n'):
            text = text[:-1]
        return text.strip()

    @staticmethod
    def get_first_number(sentence, max_value):
        """
        Get the first number in a string, used by voting agents
        """
        match = re.search(r'\b\d+', sentence)
        if match:
            return int(match.group(0)) if int(match.group(0)) < max_value else None
        else:
            return None

    @staticmethod
    def is_valid_answer(answer, target_char_num=None):
        """
        Check if an answer is valid against "ai language model" messages ond (optionally) a target character count.

        :param answer: Answer to be validated
        :type answer: str
        :param target_char_num: (optional) Target number of characters in an answer
        :type target_char_num: int
        :return:
        :rtype:
        """
        if answer is None or answer == '':
            return False
        if target_char_num is not None and len(answer) != target_char_num:
            print(f'invalid answer: answer={len(answer)} != target={target_char_num} for {answer}')
            return False
        if 'ai language model' in answer.lower() or 'ai_language_model' in answer.lower():
            print(f'invalid answer: alignment failure for {answer}')
            return False
        return True

    @classmethod
    def isolate_answer_string(cls, message: str, metadata_flag: str = '### ', answer_flag: str = 'ANSWER:', **kwargs):
        """
        Extract just the answer from a message.
        Expect message metadata chunks to be in the form of "### ANSWER: " or "### COMMENTS: " etc...
        A custom metadata flag can be passed to search for it instead.
        """
        if metadata_flag not in message or answer_flag not in message:
            raise ValueError(f"parseable messages must use the {metadata_flag=} and contain {answer_flag=}")
        chunks = message.split(metadata_flag)
        if len(chunks) == 1 and chunks[0].startswith(answer_flag):
            return cls.normalize_newlines(chunks[0].replace(answer_flag, ''))
        else:
            ans = [chunk.replace(answer_flag, '') for chunk in chunks if chunk.startswith(answer_flag)]
            return cls.normalize_newlines(ans[-1])

    @classmethod
    def classify_boolean_answer(cls, answer, **kwargs):
        """
        Act as a classifier and match the first value in a prioritized list that appears in the text.
        Returns fixed, known values to make it easier to bootstrap classifiers with LLMs
        """
        for class_name in ('yes', 'true'):
            if class_name in cls.isolate_answer_string(answer, **kwargs).lower():
                return True
            else:
                return False

    @classmethod
    def classify_answer(cls, answer, class_names: list[str], **kwargs):
        """
        Act as a classifier and match the first value in a prioritized list that appears in the text.
        Returns fixed, known values to make it easier to bootstrap classifiers with LLMs
        """
        if class_names is None or len(class_names) == 0:
            return None
        else:
            # lower_answer = cls.isolate_answer_string(message=answer, **kwargs).lower()
            lower_answer = answer.lower()
            for idx, class_name in enumerate(class_names):
                if class_name.lower() in lower_answer:
                    return class_names[idx]
            # Class name not found, so return the full answer
            print(f'class name not found for {lower_answer=} and {class_names=}')
            return None

    @classmethod
    def multi_classify_answer(cls, answer, class_names: list[str], **kwargs):
        """
        Get the answer with a multi-class classifier that can have multiple valid values.
        """
        if class_names is None or len(class_names) == 0:
            return None
        else:
            # lower_answer = cls.isolate_answer_string(message=answer, **kwargs).lower()
            lower_answer = answer.lower()
            out_classes = []
            for idx, class_name in enumerate(class_names):
                if class_name.lower() in lower_answer:
                    out_classes.append(class_names[idx])
            if len(out_classes) > 0:
                return out_classes
            # Class name not found, so return the full answer
            logger.debug(f'class name not found for {lower_answer=} and {class_names=}')
            return None

    @classmethod
    def extract_json_from_answer(cls, answer, metadata_flag: str = '### ', answer_flag: str = 'ANSWER:', **kwargs):
        try:
            answer = cls.isolate_answer_string(message=answer, metadata_flag=metadata_flag, answer_flag=answer_flag)
            return json.loads(answer)
        except JSONDecodeError as e:
            logger.debug(f'error {e=} decoding {answer=}')
            return None
        except ValueError as e:
            logger.debug(f'error {e=} decoding {answer=}')
            return None

    def is_unanimous(self, answers_list: list, class_names: list[str], **kwargs):
        """
        Check that all answers in a batch of raw answers agree on the classification
        """
        answers_list = [self.classify_answer(ans, class_names=class_names, **kwargs) for ans in answers_list]
        return len(list(set(answers_list))) == 1

    @staticmethod
    def extract_urls(text):
        """
        Extract all URLs from a string.

        :param text: Input text containing URLs
        :type text: str
        :return: List of URLs found in the text
        :rtype: list
        """
        # noinspection RegExpSimplifiable,RegExpDuplicateCharacterInClass
        url_pattern = re.compile(r'http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\\(\\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+')
        return url_pattern.findall(text)

    @staticmethod
    def convert_to_camel_case(snake_str):
        """
        Convert a snake_case_string to a camelCaseString.

        :param snake_str: Input string in snake_case
        :type snake_str: str
        :return: String converted to camelCase
        :rtype: str
        """
        components = snake_str.split('_')
        return components[0] + ''.join(x.title() for x in components[1:])

    @staticmethod
    def extract_dates(text):
        """
        Extract all date formats from a string.

        :param text: Input text containing dates
        :type text: str
        :return: List of dates found in the text
        :rtype: list
        """
        date_pattern = re.compile(r'(\d{4}-\d{2}-\d{2}|\d{2}/\d{2}/\d{4}|\d{2}-\d{2}-\d{4})')
        return date_pattern.findall(text)

    @staticmethod
    def convert_newlines_to_br(text):
        """
        Convert newline characters to HTML <br> tags.

        :param text: Input text with newline characters
        :type text: str
        :return: Text with newline characters replaced by <br> tags
        :rtype: str
        """
        return text.replace('\n', '<br>')

    @staticmethod
    def remove_special_characters(text):
        """
        Remove all special characters from a string.

        :param text: Input text with special characters
        :type text: str
        :return: Text with special characters removed
        :rtype: str
        """
        return re.sub(r'[^A-Za-z0-9\s]', '', text)

    @staticmethod
    def remove_currency_symbols(text):
        """
        Removes common currency symbols from a string.
        """
        currency_symbols = ['$', '€', '£', '¥', '₹', '₽', '₣', '₤', '₦', '₩', '₫', '₴', '₪', '฿', '₺', '₼', '₸']
        result = text
        for symbol in currency_symbols:
            result = result.replace(symbol, '')
        return result

    @staticmethod
    def replace_currency_symbol_with_iso_codes(text):
        """
        Replaces common currency symbols with their ISO 4217 codes.
        """
        currency_map = {
            '$': 'USD',
            '€': 'EUR',
            '£': 'GBP',
            # '¥': 'JPY',  # Also used for Chinese Yuan (CNY)
            '₹': 'INR',
            '₽': 'RUB',
            '₣': 'CHF',
            '₤': 'GBP',
            '₦': 'NGN',
            '₩': 'KRW',
            '₫': 'VND',
            '₴': 'UAH',
            '₪': 'ILS',
            '฿': 'THB',
            '₺': 'TRY',
            '₼': 'AZN',
            '₸': 'KZT'
        }
        result = text
        for symbol, code in currency_map.items():
            result = result.replace(symbol, code)
        return result

    @staticmethod
    def preprocess_text(text: str) -> str:
        """
        Preprocess text by converting to lowercase and handling special characters.
        URLs are preserved but normalized.

        Args:
            text: The text to preprocess

        Returns:
            Preprocessed text
        """
        if not isinstance(text, str):
            return ""
        # Convert to lowercase
        text = text.lower()
        # Normalize URLs (preserve but standardize)
        text = re.sub(r'https?://\S+|www\.\S+', lambda m: m.group(0).replace('/', ' slash ').replace('.', ' dot '),
                      text)
        # Remove HTML tags
        text = re.sub(r'<.*?>', '', text)
        # Replace punctuation with spaces (to separate words properly)
        text = text.translate(str.maketrans(string.punctuation, ' ' * len(string.punctuation)))
        # Remove extra whitespace
        text = re.sub(r'\s+', ' ', text).strip()
        return text
