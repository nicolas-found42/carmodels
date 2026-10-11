#!/usr/bin/env python3
"""Verify semantic experiment failure, cost and changing-state controls."""
import unittest

from library_filter import options_for, state_for
from mc3_preview_experiments import MC3, fixtures, run, summarize


class Tests(unittest.TestCase):
    def test_controlled_transition_preserves_inputs_and_variant(self):
        source = [{'game': MC3, 'source_variant': 'native', 'asset_kind': 'native-package', 'file': 'vp.dat'}]
        dealer = [{'game': MC3, 'sourceVariant': 'native', 'displayMode': 'native-package'}]
        rows = {row['id']: row for row in fixtures(source, dealer)}
        self.assertEqual(dealer[0]['displayMode'], 'native-package')
        for name, expected in [('source-preview', False), ('ready-preview', True), ('mixed-preview', False)]:
            row = rows[name]
            facts = state_for(row['query'], row['cars'], options_for(row['cars']), row['catalog'])['filter_facts']
            self.assertEqual(facts[MC3]['all_have_preview'], expected)
            self.assertEqual(set(options_for(row['cars'])), {'all', MC3, MC3 + ':native'})
        self.assertEqual(rows['current-dealer-preview']['expected'], ['no_match'])

    def test_operational_failure_stops_without_counting_success(self):
        class Failed:
            calls = 0
            def system_one(self, **kwargs):
                self.calls += 1
                raise RuntimeError('SECRET')
        cars = [{'game': MC3, 'source_variant': 'native'}]
        client = Failed()
        record = run(cars, cars, client)
        self.assertEqual(client.calls, 1)
        self.assertEqual(record['metrics']['grounded']['errors'], 1)
        self.assertIsNone(record['metrics']['grounded']['top_accuracy'])
        self.assertIsNone(record['metrics']['grounded']['provider_cost'])
        self.assertNotIn('SECRET', str(record))
        self.assertEqual(record['metrics']['stateful']['attempted'], 0)

    def test_metrics_distinguish_error_review_wrong_apply_and_unknown_cost(self):
        rows = [{'expected': [MC3], 'receipt': {'status': 'review', 'signals': {'choice': MC3},
                 'usage': {'input_tokens': 7}, 'latency_seconds': 1}},
                {'expected': ['no_match'], 'receipt': {'status': 'ok', 'signals': {'choice': MC3},
                 'usage': {'input_tokens': 3, 'cost': .01}, 'latency_seconds': 2}},
                {'expected': ['no_match'], 'receipt': {'status': 'error', 'latency_seconds': 3}}]
        metrics = summarize(rows)
        self.assertEqual(metrics['valid'], 2)
        self.assertEqual(metrics['top_correct'], 1)
        self.assertEqual(metrics['correct_action'], 0)
        self.assertEqual(metrics['wrongly_applied'], 1)
        self.assertIsNone(metrics['provider_cost'])
        self.assertEqual(metrics['known_partial_cost'], .01)
        self.assertEqual(metrics['usage']['input_tokens'], 10)
        self.assertEqual(metrics['latency_seconds']['total'], 6)


if __name__ == '__main__':
    unittest.main()
