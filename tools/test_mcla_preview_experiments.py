"""MCLA experiment readiness, failure accounting and unchanged-input controls."""
from contextlib import nullcontext, redirect_stdout
import hashlib
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from mcla_preview_experiments import GAME, fixtures, main, run
from library_filter import options_for, state_for


class Tests(unittest.TestCase):
    def test_receipt_pins_the_catalog_bytes_used_before_provider_calls(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp).resolve()
            source, dealer, output = [root / name for name in ('source.json', 'dealer.json', 'receipt.json')]
            cars = [{'game': GAME, 'source_variant': 'stock', 'file': 'car.glb'}]
            initial = {source: json.dumps({'cars': cars}).encode(), dealer: json.dumps(cars).encode()}
            for path, data in initial.items():
                path.write_bytes(data)
            class Changed:
                def system_one(self, **kwargs):
                    for path in initial:
                        path.write_bytes(b'changed while provider was running')
                    raise RuntimeError('private exception')
            with patch('sys.argv', ['experiment', '--live', '--source', str(source), '--dealership', str(dealer),
                                    '--output', str(output)]), patch('mcla_preview_experiments.make_client',
                                    return_value=nullcontext(Changed())), redirect_stdout(io.StringIO()):
                self.assertEqual(main(), 1)
            record = json.loads(output.read_text())
            for path, data in initial.items():
                self.assertEqual(record['input_pins'][str(path)], hashlib.sha256(data).hexdigest())
                self.assertNotEqual(record['input_pins'][str(path)], hashlib.sha256(path.read_bytes()).hexdigest())
            self.assertEqual(record['metrics']['grounded']['attempted'], 1)
            self.assertEqual(record['metrics']['grounded']['errors'], 1)
            self.assertNotIn('private exception', str(record))

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
