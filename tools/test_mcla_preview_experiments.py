"""MCLA experiment readiness, failure accounting and unchanged-input controls."""
import unittest
from mcla_preview_experiments import GAME, fixtures, run
from library_filter import options_for, state_for


class Tests(unittest.TestCase):
    def test_ready_and_partial_states(self):
        source = [{'game': GAME, 'source_variant': 'stock', 'file': 'car.glb'}]
        dealer = [{'game': GAME, 'sourceVariant': 'stock', 'displayMode': 'textured-glb',
                   'model': {'schema': 2, 'triangleCount': 1, 'source': {'glb': 'car.glb'}}}]
        rows = {r['id']: r for r in fixtures(source, dealer)}
        for catalog in ('source', 'dealership'):
            self.assertNotEqual(rows[catalog + '-preview']['expected'], ['no_match'])
            mixed = rows[catalog + '-mixed-preview']
            self.assertFalse(state_for('', mixed['cars'], options_for(mixed['cars']), catalog)['filter_facts'][GAME]['all_have_preview'])
        self.assertEqual(source[0]['file'], 'car.glb')
        self.assertEqual(dealer[0]['displayMode'], 'textured-glb')

    def test_failure_stops_and_never_counts_success(self):
        class Failed:
            calls = 0
            def system_one(self, **kwargs):
                self.calls += 1
                raise RuntimeError('private exception')
        cars = [{'game': GAME, 'source_variant': 'stock'}]
        client = Failed(); record = run(cars, cars, client)
        self.assertEqual(client.calls, 1)
        self.assertEqual(record['metrics']['grounded']['errors'], 1)
        self.assertIsNone(record['metrics']['grounded']['top_accuracy'])
        self.assertEqual(record['metrics']['stateful']['attempted'], 0)
        self.assertNotIn('private exception', str(record))


if __name__ == '__main__':
    unittest.main(verbosity=2)
