import unittest
from . import prediction


class PredictionTest(unittest.TestCase):
    def test_values_ignore_layout_but_preserve_order_type_and_precision(self):
        for answer in (' True, FALSE, 1.0, 1e2 ', 'true\n\nfalse\t1\r\n100'):
            self.assertTrue(prediction.matches(answer, 'true\nfalse\n1\n100\n'))
        for answer in ('false true 1 100', '1 0 1 100', 'true false 1', 'true false 1 100 0'):
            self.assertFalse(prediction.matches(answer, 'true\nfalse\n1\n100'))
        self.assertFalse(prediction.matches('9007199254740992', '9007199254740993'))
        self.assertFalse(prediction.matches('"true"', 'true'))
        self.assertTrue(prediction.matches('None undefined NaN Infinity', 'null\nundefined\nNaN\nInfinity'))

    def test_strings_keep_meaning_and_legacy_text_remains_usable(self):
        self.assertTrue(prediction.matches('"hello world", "a,b"', '"hello world"\n"a,b"'))
        self.assertFalse(prediction.matches('"hello  world"', '"hello world"'))
        self.assertFalse(prediction.matches('"Hello"', '"hello"'))
        self.assertTrue(prediction.matches(' bark\nmeow ', 'bark meow'))
        self.assertFalse(prediction.matches('changed', 'no change'))

    def test_generated_output_rejects_headings_prose_and_compound_values(self):
        for output in ('', '--- 시나리오 1 ---\ntrue', '참조가 변경되었습니다. (changed)',
                       'result: true', '[1, 2]', '{"a": 1}', 'true false garbage',
                       '1e999999999999999999999999999999'):
            self.assertIsNone(prediction.values(output), output)
        self.assertIsNotNone(prediction.values('true\nfalse\n99\n"hello"'))
