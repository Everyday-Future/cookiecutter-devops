"""

Parser

String parser for interpreting model answers, articles, scraped pages, and more

"""
import json
from json import JSONDecodeError
import re


class StringParser:
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
    def clean_answer(answer):
        """ Strip an answer to alphanumeric and spaces, lower, and replace spaces with underscores"""
        return re.sub(r'[^A-Za-z0-9 ]+', '', str(answer)).replace(' ', '_').lower().strip()

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
            if len(ans) != 1:
                raise ValueError(f'Multiple or no answers found in {message=}')
            else:
                return cls.normalize_newlines(ans[0])

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
            lower_answer = cls.isolate_answer_string(message=answer, **kwargs).lower()
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
            lower_answer = cls.isolate_answer_string(message=answer, **kwargs).lower()
            out_classes = []
            for idx, class_name in enumerate(class_names):
                if class_name.lower() in lower_answer:
                    out_classes.append(class_names[idx])
            if len(out_classes) > 0:
                return out_classes
            # Class name not found, so return the full answer
            print(f'class name not found for {lower_answer=} and {class_names=}')
            return None

    @classmethod
    def extract_json_from_answer(cls, answer, metadata_flag: str = '### ', answer_flag: str = 'ANSWER:', **kwargs):
        try:
            answer = cls.isolate_answer_string(message=answer, metadata_flag=metadata_flag, answer_flag=answer_flag)
            return json.loads(answer)
        except JSONDecodeError as e:
            # print(f'error {e=} decoding {answer=}')
            return None
        except ValueError as e:
            # print(f'error {e=} decoding {answer=}')
            return None

    def is_unanimous(self, answers_list: list, class_names: list[str], **kwargs):
        """
        Check that all answers in a batch of raw answers agree on the classification
        """
        answers_list = [self.classify_answer(ans, class_names=class_names, **kwargs) for ans in answers_list]
        return len(list(set(answers_list))) == 1
