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
    def probe(self, name, code, parallel=True):
        return {'name': name, 'parallel': parallel,
                'command': [sys.executable, '-c', 'from pathlib import Path\nimport time\n' + code]}

    def test_parallel_overlap_bound_failure_and_incremental_manifest(self):
        # File rendezvous proves overlap without a speed threshold. A timeout fails the probe,
        # rather than hanging CI if scheduling becomes serial or stops after the failure.
        wait = ('deadline = time.monotonic() + 15\n'
                'while not Path({peer!r}).exists():\n'
                '    assert time.monotonic() < deadline, "peer never started"\n'
                '    time.sleep(.01)\n')
        checks = [self.probe('a', 'Path("a.start").touch()\n' + wait.format(peer='b.start') +
                             'Path("a.end").touch()\nprint("a failed")\nraise SystemExit(7)'),
                  self.probe('b', 'Path("b.start").touch()\n' + wait.format(peer='c.start') +
                             'print("b passed")'),
                  self.probe('c', 'assert Path("a.end").exists(), "more than two checks started"\n'
                             'import json\nreceipt = json.loads(Path("out/results.json").read_text())\n'
                             'assert receipt["exit_code"] == 1\n'
                             'assert [r["name"] for r in receipt["checks"]] == ["a"]\n'
                             'assert receipt["pending"] == ["b", "c"]\n'
                             'Path("c.start").touch()\nprint("c passed")')]
        with tempfile.TemporaryDirectory() as temp:
            out = Path(temp) / 'out'
            self.assertEqual(run_checks(checks, temp, out, jobs=2), 1)
            receipt = json.loads((out / 'results.json').read_text())
            self.assertEqual([r['name'] for r in receipt['checks']], ['a', 'b', 'c'])
            self.assertEqual([r['exit_code'] for r in receipt['checks']], [7, 0, 0])
            self.assertEqual(receipt['pending'], [])
            self.assertEqual(receipt['jobs'], 2)
            self.assertGreater(receipt['elapsed_seconds'], 0)
            self.assertEqual((out / 'a.log').read_text(), 'a failed\n')
            self.assertEqual((out / 'b.log').read_text(), 'b passed\n')
            self.assertEqual((out / 'c.log').read_text(), 'c passed\n')

    def test_exclusive_checks_are_barriers_in_both_directions(self):
        wait = ('deadline = time.monotonic() + 15\n'
                'while not Path({peer!r}).exists():\n'
                '    assert time.monotonic() < deadline\n    time.sleep(.01)\n')
        checks = [self.probe('before', 'Path("before.start").touch()\n' + wait.format(peer='other.start') +
                             'Path("before.end").touch()'),
                  self.probe('other', 'Path("other.start").touch()\n' + wait.format(peer='before.start') +
                             'Path("other.end").touch()'),
                  self.probe('receipt', 'assert Path("before.end").exists()\nassert Path("other.end").exists()\n'
                             'assert not Path("after.start").exists()\nPath("receipt.end").touch()', False),
                  self.probe('pool', 'assert Path("receipt.end").exists()\n'
                             'assert not Path("after.start").exists()\nPath("pool.end").touch()', False),
                  self.probe('after', 'assert Path("pool.end").exists()\nPath("after.start").touch()')]
        # Missing metadata is also exclusive, including a newly registered check.
        checks[3].pop('parallel')
        with tempfile.TemporaryDirectory() as temp:
            self.assertEqual(run_checks(checks, temp, Path(temp) / 'out', jobs=4), 0)

    def test_one_job_preserves_serial_order_even_for_parallel_checks(self):
        checks = [self.probe('first', 'Path("first.end").touch()'),
                  self.probe('second', 'assert Path("first.end").exists()')]
        with tempfile.TemporaryDirectory() as temp:
            self.assertEqual(run_checks(checks, temp, Path(temp) / 'out', jobs=1), 0)

    def test_invalid_jobs_and_duplicate_names_are_refused_before_execution(self):
        check = self.probe('same', 'raise AssertionError("must not execute")')
        with tempfile.TemporaryDirectory() as temp:
            out = Path(temp) / 'out'
            for jobs in (0, -1, 1.5, True):
                with self.assertRaisesRegex(ValueError, 'positive integer'):
                    run_checks([check], temp, out, jobs=jobs)
            with self.assertRaisesRegex(ValueError, 'unique'):
                run_checks([check, check], temp, out, jobs=2)
            self.assertFalse(out.exists())

    def test_parallel_availability_and_launch_errors_keep_skip_fail_semantics(self):
        checks = [self.probe('absent', 'raise AssertionError("must skip")'),
                  self.probe('bad_pin', 'raise AssertionError("must not execute")'),
                  self.probe('bad_probe', 'raise AssertionError("must not execute")'),
                  {'name': 'bad_command', 'parallel': True, 'command': ['carmodels-command-does-not-exist']}]
        checks[0]['availability'] = [sys.executable, '-c', 'print("missing");raise SystemExit(1)']
        checks[1]['availability'] = [sys.executable, '-c', 'print("wrong pin");raise SystemExit(2)']
        checks[2]['availability'] = ['carmodels-probe-does-not-exist']
        with tempfile.TemporaryDirectory() as temp:
            out = Path(temp) / 'out'
            self.assertEqual(run_checks(checks, temp, out, jobs=2), 1)
            rows = json.loads((out / 'results.json').read_text())['checks']
            self.assertEqual([r['status'] for r in rows], ['skip', 'fail', 'fail', 'fail'])
            self.assertEqual([r['exit_code'] for r in rows], [None, 2, 127, 127])
            self.assertIn('missing', (out / 'absent.log').read_text())
            self.assertIn('wrong pin', (out / 'bad_pin.log').read_text())

    def test_shared_receipts_existing_pools_and_bulk_checks_stay_exclusive(self):
        checks = registry()
        self.assertLessEqual(runner.PARALLEL_SAFE, {c['name'] for c in checks})
        protected = runner.FULL_ONLY | {'verify_recovered_asset_index', 'test_build_dealership',
                     'dealership_freshness', 'test_verify_mcla_resources', 'test_verify_mcla_decoding',
                     'dealership_roundtrip', 'redline_roundtrip', 'mc3_roundtrip'}
        self.assertTrue(all(not c['parallel'] for c in checks if c['name'] in protected))
        self.assertTrue(all(c['parallel'] for c in checks if c['name'] in {
            'test_import_gt4_catalog', 'test_import_gt4_dealership', 'test_mc3_preview'}))

    def test_cli_jobs_default_override_and_invalid_values(self):
        with tempfile.TemporaryDirectory() as temp, patch.object(runner, 'run_checks', return_value=0) as ran, \
                patch('builtins.print'):
            for flags, expected in (([], runner.DEFAULT_JOBS), (['--jobs', '1'], 1), (['--jobs', '3'], 3)):
                with patch.object(sys, 'argv', ['run_checks', '--evidence-dir', temp, *flags]):
                    self.assertEqual(runner.main(), 0)
                self.assertEqual(ran.call_args.kwargs['jobs'], expected)
            ran.reset_mock()
            for value in ('0', '-1', 'many'):
                with patch.object(sys, 'argv', ['run_checks', '--jobs', value]), patch.object(sys, 'stderr'), \
                        self.assertRaises(SystemExit) as error:
                    runner.main()
                self.assertEqual(error.exception.code, 2)
            ran.assert_not_called()

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

    def test_gt1_full_checks_include_exports_and_disc_rederivation(self):
        checks = registry()
        fast = {c['name'] for c in select(checks, [], game=['gran-turismo'])}
        full = {c['name'] for c in select(checks, [], game=['gran-turismo'], full=True)}
        self.assertNotIn('gt_models', fast)
        self.assertNotIn('gt_extraction', fast)
        self.assertTrue({'gt_models', 'gt_extraction', 'test_gt_model', 'test_import_gt_dealership'} <= full)

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
        'test_dealership', 'test_editable_glb', 'test_gt4_refinement', 'gt4_refinement_corpus', 'test_native_catalog_ui', 'test_mc3_preview_ui',
            'test_mcla_preview_ui', 'test_factory_colours', 'test_mc3_tire_material', 'test_mc3_vehicle_math', 'test_mc3_vehicle_resources', 'test_mc3_vu_interpreter', 'test_mc3_vehicle_bindings_js', 'test_mc3_vehicle_deformation_js', 'test_mc3_vehicle_fragment_js', 'test_mc3_vehicle_raster_js', 'test_mc3_vehicle_programs_js', 'test_mc3_vehicle_gif_js', 'test_mc3_vehicle_state_js', 'test_mc3_vif_decoder', 'test_mc3_vehicle_pipeline', 'test_mc3_vehicle_sampler_js', 'test_mc3_vehicle_sprite_js', 'test_mc3_ee', 'test_mc3_ee_division_js', 'test_mc3_vehicle_transfer_reference_js', 'test_mc3_vehicle_nearest_js', 'test_mc3_vehicle_vram_js', 'test_mc3_vehicle_depth32_js', 'test_mc3_vehicle_vram_pipeline', 'test_mc3_vehicle_mip_js', 'test_mc3_vehicle_paint_factory_js', 'test_mc3_vehicle_mip_pipeline', 'test_mc3_vehicle_paint_factory_pipeline', 'test_mc3_vehicle_high_z_js', 'test_mc3_vehicle_variable_mip_js', 'test_mc3_vehicle_initialization_js', 'test_mc3_vehicle_target_js', 'test_mc3_vehicle_high_z_pipeline', 'test_mc3_vehicle_depth_trace_js', 'test_mc3_vehicle_variable_mip_pipeline', 'test_mc3_specular', 'test_mc3_environment', 'test_mc3_gs_raster', 'test_game_paint'})
        self.assertTrue(all(c['requires'] == 'node' for c in checks))
        with tempfile.TemporaryDirectory() as temp, patch('run_checks.shutil.which', return_value=None):
            self.assertEqual(run_checks(checks, temp, Path(temp) / 'ci', ci=True), 1)
            rows = json.loads((Path(temp) / 'ci/results.json').read_text())['checks']
            self.assertTrue(all(r['status'] == 'fail' and r['exit_code'] == 127 for r in rows))


if __name__ == '__main__':
    unittest.main(verbosity=2)
