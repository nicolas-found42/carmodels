"""Check exit aggregation, full logs, selections, evidence preservation and required runtimes."""
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

from run_checks import registry, run_checks, select


class CheckRunnerTests(unittest.TestCase):
    def test_failure_cannot_be_masked_by_later_success(self):
        checks = [{'name': 'broken', 'command': [sys.executable, '-c', 'print("first line");print("last line");raise SystemExit(7)']},
                  {'name': 'green', 'command': [sys.executable, '-c', 'print("success")']}]
        with tempfile.TemporaryDirectory() as temp:
            out = Path(temp) / 'evidence'
            self.assertEqual(run_checks(checks, Path(temp), out), 1)
            receipt = json.loads((out / 'results.json').read_text())
            self.assertEqual([r['exit_code'] for r in receipt['checks']], [7, 0])
            self.assertEqual(receipt['exit_code'], 1)
            self.assertEqual((out / 'broken.log').read_text(), 'first line\nlast line\n')
            with self.assertRaisesRegex(ValueError, 'must be empty'):
                run_checks(checks, Path(temp), out)

    def test_selection_and_missing_node_in_ci(self):
        checks = [{'name': 'node', 'command': ['missing-runtime'], 'requires': 'carmodels-runtime-does-not-exist'}]
        self.assertEqual(select(checks, ['node']), checks)
        with self.assertRaisesRegex(ValueError, 'Unknown'):
            select(checks, ['typo'])
        with tempfile.TemporaryDirectory() as temp:
            for ci in [False, True]:
                out = Path(temp) / str(ci)
                self.assertEqual(run_checks(checks, temp, out, ci=ci), int(ci))
                row = json.loads((out / 'results.json').read_text())['checks'][0]
                self.assertEqual(row['status'], 'fail' if ci else 'skip')
                self.assertEqual(row['exit_code'], 127 if ci else None)

    def test_actual_javascript_registry_requires_node(self):
        checks = [c for c in registry() if c['command'][0] == 'node']
        self.assertEqual(len(checks), 8)
        self.assertIn('test_native_catalog_ui', {c['name'] for c in checks})
        self.assertTrue(all(c['requires'] == 'node' for c in checks))
        with tempfile.TemporaryDirectory() as temp, patch('run_checks.shutil.which', return_value=None):
            self.assertEqual(run_checks(checks, temp, Path(temp) / 'ci', ci=True), 1)
            rows = json.loads((Path(temp) / 'ci/results.json').read_text())['checks']
            self.assertTrue(all(r['status'] == 'fail' and r['exit_code'] == 127 for r in rows))


if __name__ == '__main__':
    unittest.main()
