"""Check exit aggregation, full logs, selections, evidence preservation and required runtimes."""
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

import run_checks as runner
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

    def test_older_python_is_refused_before_any_check(self):
        with patch.object(runner.sys, 'version_info', (3, 11, 9)), patch('builtins.print') as shown, \
                patch.object(runner, 'run_checks') as ran:
            self.assertEqual(runner.main(), 2)
        ran.assert_not_called()
        self.assertIn('needs Python 3.12 or newer; python3 is 3.11', shown.call_args[0][0])

    def test_default_run_is_the_showcase_and_games_are_opt_in(self):
        checks = registry()
        names = {c['name'] for c in checks}
        self.assertLessEqual(runner.SHOWCASE, names)  # Every showcase name is a real check.
        self.assertEqual({c['name'] for c in select(checks, [])}, runner.SHOWCASE)
        self.assertEqual(select(checks, [], games=True), checks)
        self.assertEqual([c['name'] for c in select(checks, ['mcla_resources'])], ['mcla_resources'])
        self.assertNotIn('mcla_resources', runner.SHOWCASE)
        self.assertIn('dealership_freshness', runner.SHOWCASE)
        with tempfile.TemporaryDirectory() as temp:
            green = [{'name': 'green', 'command': [sys.executable, '-c', 'pass']}]
            self.assertEqual(run_checks(green, temp, Path(temp) / 'out', not_run=['gt4_catalog']), 0)
            # Checks left out by the tier are recorded, so a showcase run is never read as a full one.
            self.assertEqual(json.loads((Path(temp) / 'out/results.json').read_text())['not_run'], ['gt4_catalog'])

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
        self.assertEqual({c['name'] for c in checks}, {
            'test_viewer_scenes', 'test_viewer_materials', 'test_model_load', 'test_viewer_loading',
            'test_dealership', 'test_editable_glb', 'test_native_catalog_ui', 'test_mc3_preview_ui',
            'test_mcla_preview_ui'})
        self.assertTrue(all(c['requires'] == 'node' for c in checks))
        with tempfile.TemporaryDirectory() as temp, patch('run_checks.shutil.which', return_value=None):
            self.assertEqual(run_checks(checks, temp, Path(temp) / 'ci', ci=True), 1)
            rows = json.loads((Path(temp) / 'ci/results.json').read_text())['checks']
            self.assertTrue(all(r['status'] == 'fail' and r['exit_code'] == 127 for r in rows))


if __name__ == '__main__':
    unittest.main()
