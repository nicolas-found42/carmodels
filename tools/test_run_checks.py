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
        self.assertEqual(select(checks, [], full=True), checks)
        self.assertEqual([c['name'] for c in select(checks, ['mcla_resources'])], ['mcla_resources'])
        self.assertNotIn('mcla_resources', runner.SHOWCASE)
        self.assertIn('dealership_freshness', runner.SHOWCASE)
        with tempfile.TemporaryDirectory() as temp:
            green = [{'name': 'green', 'command': [sys.executable, '-c', 'pass']}]
            self.assertEqual(run_checks(green, temp, Path(temp) / 'out', not_run=['gt4_catalog']), 0)
            # Checks left out by the tier are recorded, so a showcase run is never read as a full one.
            self.assertEqual(json.loads((Path(temp) / 'out/results.json').read_text())['not_run'], ['gt4_catalog'])

    def test_fast_game_checks_exclude_bulk_rederivation(self):
        checks = registry()
        selected = {c['name'] for c in select(checks, [], games=True)}
        self.assertTrue(runner.SHOWCASE <= selected)
        self.assertIn('test_extract_gt4_cars', selected)
        self.assertIn('test_extract_mcla_cars', selected)
        self.assertIn('test_verify_mcla_resources', selected)
        self.assertFalse(selected & runner.FULL_ONLY)
        self.assertTrue(runner.FULL_ONLY <= {c['name'] for c in checks})

    def test_one_game_selects_its_tools_and_shared_showcase_checks(self):
        checks = registry()
        selected = {c['name'] for c in select(checks, [], game=['gran-turismo-4'])}
        self.assertTrue(runner.SHOWCASE <= selected)
        self.assertIn('test_gt4_volume', selected)
        self.assertIn('test_extract_gt4_cars', selected)
        self.assertNotIn('gt4_extraction', selected)
        self.assertNotIn('test_extract_mcla_cars', selected)
        full = {c['name'] for c in select(checks, [], game=['gran-turismo-4'], full=True)}
        self.assertIn('gt4_extraction', full)
        self.assertIn('gt4_catalog', full)
        self.assertNotIn('mcla_resources', full)
        with self.assertRaisesRegex(ValueError, 'Unknown game'):
            select(checks, [], game=['typo'])
        combined = {c['name'] for c in select(checks, [], game=['gran-turismo-4', 'redline'])}
        self.assertEqual(combined, selected | {c['name'] for c in select(checks, [], game=['redline'])})

    def test_every_game_check_has_an_owner_and_can_run_explicitly(self):
        checks = registry()
        covered = set(runner.SHOWCASE)
        for game in runner.GAMES:
            covered.update(c['name'] for c in select(checks, [], game=[game], full=True))
        self.assertEqual(covered, {c['name'] for c in checks})
        self.assertEqual([c['name'] for c in select(checks, ['mcla_resources'])], ['mcla_resources'])

    def test_cli_routes_game_tier_and_rejects_ambiguous_selection(self):
        with tempfile.TemporaryDirectory() as temp, patch.object(runner, 'run_checks', return_value=0) as ran, \
                patch('builtins.print'):
            with patch.object(sys, 'argv', ['run_checks', '--game', 'gran-turismo-4', '--full',
                                          '--evidence-dir', str(Path(temp) / 'out')]):
                self.assertEqual(runner.main(), 0)
            selected = {c['name'] for c in ran.call_args.args[0]}
            self.assertIn('gt4_extraction', selected)
            self.assertNotIn('mcla_extraction', selected)
            self.assertIn('mcla_extraction', ran.call_args.kwargs['not_run'])
            ran.reset_mock()
            with patch.object(sys, 'argv', ['run_checks', '--game', 'gran-turismo-4', '--list']), \
                    patch('builtins.print') as shown:
                self.assertEqual(runner.main(), 0)
            listed = set(shown.call_args.args[0].splitlines())
            self.assertIn('test_gt4_volume', listed)
            self.assertNotIn('gt4_extraction', listed)
            self.assertNotIn('test_extract_mcla_cars', listed)
            with patch.object(sys, 'argv', ['run_checks', '--list']), patch('builtins.print') as shown:
                self.assertEqual(runner.main(), 0)
            self.assertEqual(set(shown.call_args.args[0].splitlines()), {c['name'] for c in registry()})
            for flags in [['--only', 'mcla_resources', '--games'], ['--games', '--game', 'redline']]:
                with patch.object(sys, 'argv', ['run_checks', *flags]), patch.object(sys, 'stderr'), \
                        self.assertRaises(SystemExit) as error:
                    runner.main()
                self.assertEqual(error.exception.code, 2)
            ran.assert_not_called()

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
