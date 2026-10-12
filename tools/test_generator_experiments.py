"""Selective accuracy counts uncertainty separately and derives usage from raw envelopes."""
import unittest
from generator_experiments import threshold_metrics, usage


class Tests(unittest.TestCase):
    def test_thresholds_separate_coverage_from_accuracy(self):
        rows = [{'code': 'car', 'expected_car': True}, {'code': 'bus', 'expected_car': False},
                {'code': 'unsure', 'expected_car': True}, {'code': 'wrong', 'expected_car': False}]
        labels = {code: {'car_probability': value} for code, value in
                  [('car', .95), ('bus', .05), ('unsure', .5), ('wrong', .9)]}
        result = next(r for r in threshold_metrics(rows, labels) if r['threshold'] == .85)
        self.assertEqual(result, {'threshold': .85, 'decided': 3, 'count': 4, 'accuracy': 2 / 3})
        self.assertEqual(usage([{'response': {'usage': {'input_tokens': 3, 'output_tokens': 2, 'cost': .01}},
                                'latency_seconds': .25}]),
                         {'input_tokens': 3, 'output_tokens': 2, 'cost_usd': .01, 'latency_seconds': .25})


if __name__ == '__main__':
    unittest.main()
