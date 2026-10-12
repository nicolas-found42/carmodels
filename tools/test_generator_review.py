"""Blind-review results are derived only from complete human marks."""
import unittest
from generator_review import summarize


class Tests(unittest.TestCase):
    def test_requires_all_seventy_marks_and_derives_method_rates(self):
        items = [{'id': str(i), 'method': 'shape space' if i < 30 else 'network' if i < 60 else 'control',
                  'novelty': .35, 'automatic': True} for i in range(70)]
        marks = {str(i): 'car' if i < 65 else 'not a car' for i in range(70)}
        result = summarize(items, marks)
        self.assertEqual(result['methods']['shape space']['car_rate'], 1)
        self.assertEqual(result['methods']['network']['car_rate'], 1)
        self.assertEqual(result['methods']['control']['car_rate'], .5)
        self.assertEqual(result['automatic_agreement'], 65 / 70)
        self.assertEqual(result['novelty_default'], .35)
        del marks['0']
        with self.assertRaisesRegex(ValueError, '70'):
            summarize(items, marks)


if __name__ == '__main__':
    unittest.main()
