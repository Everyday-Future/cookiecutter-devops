import unittest
from core.adapters.parsers.string import StringParser


class TestStringParser(unittest.TestCase):
    def setUp(self):
        self.parser = StringParser()

    def test_num_matches(self):
        self.assertEqual(self.parser.num_matches('test', 'this is a test'), 1)
        self.assertEqual(self.parser.num_matches('test1 test2', 'test1 test1 test2'), 3)

    def test_title_to_snake(self):
        self.assertEqual(self.parser.title_to_snake('Title Case String'), 'title_case_string')

    def test_clean_answer(self):
        self.assertEqual(self.parser.clean_answer('Answer! 123'), 'answer_123')

    def test_yes_no_to_bool(self):
        self.assertTrue(self.parser.yes_no_to_bool('yes'))
        self.assertFalse(self.parser.yes_no_to_bool('no'))

    def test_parse_location_coordinates(self):
        answer = "Location1 (123.456, -78.910)\nLocation2 (23.456, -8.910)"
        expected = {'Location1': [123.456, -78.910], 'Location2': [23.456, -8.910]}
        self.assertEqual(self.parser.parse_location_coordinates(answer), expected)

    def test_normalize_newlines(self):
        self.assertEqual(self.parser.normalize_newlines('Line1\n\n\nLine2'), 'Line1\nLine2')

    def test_get_first_number(self):
        self.assertEqual(self.parser.get_first_number('The number is 42 in this sentence', 50), 42)
        self.assertIsNone(self.parser.get_first_number('No number here', 50))

    def test_is_valid_answer(self):
        self.assertTrue(self.parser.is_valid_answer('This is a valid answer'))
        self.assertFalse(self.parser.is_valid_answer(''))
        self.assertFalse(self.parser.is_valid_answer('ai language model'))

    def test_isolate_answer_string(self):
        message = "### ANSWER: This is the answer\n### COMMENTS: This is a comment"
        self.assertEqual(self.parser.isolate_answer_string(message), 'This is the answer')

    def test_classify_boolean_answer(self):
        self.assertTrue(self.parser.classify_boolean_answer('### ANSWER: Yes'))

    def test_classify_answer(self):
        self.assertEqual(self.parser.classify_answer('### ANSWER: Class1', ['class1', 'class2']), 'class1')

    def test_multi_classify_answer(self):
        self.assertEqual(self.parser.multi_classify_answer('### ANSWER: Class1 and Class2', ['class1', 'class2']),
                         ['class1', 'class2'])

    def test_extract_json_from_answer(self):
        answer = "### ANSWER: {\"key\": \"value\"}"
        self.assertEqual(self.parser.extract_json_from_answer(answer), {"key": "value"})

    def test_is_unanimous(self):
        answers_list = ["### ANSWER: Yes", "### ANSWER: Yes"]
        self.assertTrue(self.parser.is_unanimous(answers_list, ['yes', 'no']))

    def test_extract_urls(self):
        text = "Visit https://www.example.com and http://test.com"
        self.assertEqual(self.parser.extract_urls(text), ['https://www.example.com', 'http://test.com'])

    def test_convert_to_camel_case(self):
        self.assertEqual(self.parser.convert_to_camel_case('snake_case_string'), 'snakeCaseString')

    def test_extract_dates(self):
        text = "Dates: 2023-06-17, 06/17/2023, 17-06-2023"
        self.assertEqual(self.parser.extract_dates(text), ['2023-06-17', '06/17/2023', '17-06-2023'])

    def test_convert_newlines_to_br(self):
        self.assertEqual(self.parser.convert_newlines_to_br('Line1\nLine2'), 'Line1<br>Line2')

    def test_remove_special_characters(self):
        self.assertEqual(self.parser.remove_special_characters('Text! with# special* characters&'),
                         'Text with special characters')

    def test_parse_location_coordinates_with_invalid_data(self):
        answer = "Invalid Location (abc, xyz)"
        self.assertIsNone(self.parser.parse_location_coordinates(answer))

    def test_isolate_answer_string_missing_metadata_flag(self):
        message = "ANSWER: This is the answer"
        with self.assertRaises(ValueError):
            self.parser.isolate_answer_string(message)

    def test_isolate_answer_string_multiple_answers(self):
        message = "### ANSWER: Answer1\n### ANSWER: Answer2"
        assert self.parser.isolate_answer_string(message) == 'Answer2'

    def test_extract_json_from_answer_invalid_json(self):
        answer = "### ANSWER: {invalid json}"
        self.assertIsNone(self.parser.extract_json_from_answer(answer))

    def test_is_valid_answer_with_alignment_failure(self):
        self.assertFalse(self.parser.is_valid_answer('This is an AI language model'))

    def test_is_valid_answer_with_target_char_num(self):
        self.assertFalse(self.parser.is_valid_answer('Short answer', target_char_num=50))

    def test_classify_answer_no_class_names(self):
        self.assertIsNone(self.parser.classify_answer('### ANSWER: Class1', []))

    def test_multi_classify_answer_no_class_names(self):
        self.assertIsNone(self.parser.multi_classify_answer('### ANSWER: Class1 and Class2', []))

    def test_is_unanimous_with_different_answers(self):
        answers_list = ["### ANSWER: Yes", "### ANSWER: No"]
        self.assertFalse(self.parser.is_unanimous(answers_list, ['yes', 'no']))
