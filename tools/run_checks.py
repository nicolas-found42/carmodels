"""Named offline checks with retained per-command logs and a machine-readable manifest."""
import argparse
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import time

ROOT = Path(__file__).resolve().parents[1]
MIN_PYTHON = (3, 12)  # CI's version; the runner and every check invoke python3 from PATH.
# The default run covers the car models and the showcase that displays them. Every other check
# exists for extracting, re-deriving or researching game data; it runs with --games or --only.
SHOWCASE = {
    'ruff', 'test_viewer_scenes', 'test_viewer_materials', 'test_model_load', 'test_viewer_loading',
    'test_dealership', 'test_editable_glb', 'test_native_catalog_ui', 'test_mc3_preview_ui', 'test_mcla_preview_ui',
    'verify_recovered_asset_index', 'test_export_materials', 'test_bake_models', 'test_model_png', 'test_model_catalog',
    'test_build_showcase', 'test_build_dealership', 'dealership_freshness', 'test_library_filter', 'test_serve_library',
    'dealership_roundtrip', 'redline_roundtrip', 'mc3_roundtrip', 'test_run_checks', 'test_review_payload',
}


def registry():
    checks = [{'name': 'ruff', 'command': ['ruff', 'check', 'tools'], 'requires': 'ruff'}]
    checks += [{'name': n, 'command': ['node', f'tools/{n}.mjs'], 'requires': 'node'} for n in
               ['test_viewer_scenes', 'test_viewer_materials', 'test_model_load', 'test_viewer_loading', 'test_dealership', 'test_editable_glb', 'test_native_catalog_ui', 'test_mc3_preview_ui', 'test_mcla_preview_ui']]
    names = ['verify_recovered_asset_index', 'test_export_materials', 'test_build_showcase', 'test_bake_models',
             'test_build_dealership', 'test_model_catalog', 'test_model_png', 'test_run_checks', 'test_review_payload',
             'test_static_inputs', 'test_recovery_inputs', 'test_gt_archive', 'test_gt_asset_judgments', 'test_gt_wheels', 'test_gt_model', 'test_import_gt_dealership',
             'test_library_filter', 'test_serve_library', 'test_redline_archive', 'test_extract_redline_cars', 'test_mc3_archive', 'test_extract_mc3_cars', 'test_import_mc3_catalogs',
             'test_mc3_pck', 'test_mc3_wheels', 'test_mc3_materials', 'test_mc3_textures', 'test_mc3_model', 'test_export_mc3_models', 'test_mc3_preview', 'test_import_mc3_previews', 'test_mc3_preview_experiments',
             'test_redline_mesh', 'test_redline_texture', 'test_redline_model', 'test_export_redline_models', 'test_import_redline_dealership',
             'test_gt4_volume', 'test_extract_gt4_cars', 'test_gt4_model', 'test_gt4_specdb', 'test_gt4_glb',
             'test_import_gt4_catalog', 'test_import_gt4_dealership',
             'test_aes_decrypt', 'test_xdvdfs', 'test_xex2', 'test_mcla_rpf', 'test_extract_mcla_cars',
             'test_mcla_lzx', 'test_mcla_resource', 'test_mcla_model', 'test_mcla_texture', 'test_mcla_tuning',
             'test_verify_mcla_resources', 'test_verify_mcla_decoding', 'test_mcla_names', 'test_mcla_preview',
             'test_mcla_preview_geometry',
             'test_import_mcla_catalog', 'test_import_mcla_dealership', 'test_mcla_preview_experiments', 'test_line_coverage']
    checks += [{'name': n, 'command': ['python3', f'tools/{n}.py']} for n in names]
    checks.append({'name': 'dealership_freshness', 'command': ['python3', 'tools/build_dealership.py', '--check']})
    # The full GT4 extraction and native ZIPs stay local; the re-derivation runs only where they exist.
    checks.append({'name': 'gt4_catalog', 'command': ['python3', 'tools/import_gt4_catalog.py', '--check'],
                   'availability': ['python3', 'tools/import_gt4_catalog.py', '--available']})
    # The disc is never committed; its re-derivation runs only where the pinned ISO is supplied.
    checks.append({'name': 'gt4_extraction', 'command': ['python3', 'tools/extract_gt4_cars.py', '--check'],
                   'availability': ['python3', '-c', "from pathlib import Path; import sys; sys.exit(0 if Path("
                                    "'gran-turismo-4/game-files/Gran Turismo 4 (axekin.com).iso').is_file() else 1)"]})
    # Line coverage of the MCLA readers and the review bundle builder under their own tests (stdlib trace).
    covered = ['aes_decrypt', 'xdvdfs', 'xex2', 'mcla_rpf', 'extract_mcla_cars', 'review_payload', 'mcla_lzx',
               'mcla_resource', 'mcla_model', 'mcla_texture', 'mcla_tuning', 'verify_mcla_resources',
               'verify_mcla_decoding', 'mcla_preview_geometry']
    checks.append({'name': 'line_coverage', 'command': ['python3', 'tools/line_coverage.py', '--minimum', '95', '--modules',
                                                        *[f'tools/{n}.py' for n in covered], '--tests',
                                                        *[f'tools/test_{n}.py' for n in covered]]})
    # The MCLA disc is never committed either; the same skip applies when it is absent.
    checks.append({'name': 'mcla_extraction', 'command': ['python3', 'tools/extract_mcla_cars.py', '--check'],
                   'availability': ['python3', '-c', "from pathlib import Path; import sys; sys.exit(0 if Path("
                                    "'midnight-club-los-angeles/game-files/Midnight Club - Los Angeles - Complete Edition "
                                    "(USA, Europe).iso').is_file() else 1)"]})
    # Every RSC5 resource of the disc decompressed to its declared size (needs the ISO), then every car model,
    # texture, tuning and streaming map of the local extraction decoded (needs the extraction).
    checks.append({'name': 'mcla_resources', 'command': ['python3', 'tools/verify_mcla_resources.py'],
                   'availability': ['python3', 'tools/verify_mcla_resources.py', '--available']})
    checks.append({'name': 'mcla_decoding', 'command': ['python3', 'tools/verify_mcla_decoding.py'],
                   'availability': ['python3', 'tools/verify_mcla_decoding.py', '--available']})
    checks.append({'name': 'mcla_names', 'command': ['python3', 'tools/mcla_names.py'],
                   'availability': next(c for c in checks if c['name'] == 'mcla_extraction')['availability']})
    checks.append({'name': 'mcla_catalog', 'command': ['python3', 'tools/import_mcla_catalog.py', '--check'],
                   'availability': ['python3', 'tools/import_mcla_catalog.py', '--available']})
    for name in ['verify_config_data_sound', 'verify_sound_bank_index', 'verify_vu_dispatch_map', 'test_vu_dispatch_map',
                 'test_vu1_decode', 'verify_vu_pass_handlers', 'test_vu_pass_handlers']:
        checks.append({'name': name, 'command': ['python3', f'tools/{name}.py'],
                       'availability': ['python3', 'tools/static_inputs.py', '--available']})
    for verifier, test in [('verify_vu_handler_dump', 'test_vu_handler_dump'),
                           ('recover_dump_reference_frame', 'test_recover_dump_reference_frame')]:
        for name in [verifier, test]:
            checks.append({'name': name, 'command': ['python3', f'tools/{name}.py'],
                           'availability': ['python3', f'tools/{verifier}.py', '--available']})
    for name in ['verify_pass_source_join','test_pass_source_join']:
        checks.append({'name':name,'command':['python3',f'tools/{name}.py'],
                       'availability':['python3','tools/verify_pass_source_join.py','--available']})
    blender = os.environ.get('CARMODELS_BLENDER') or shutil.which('blender')
    mounted = ROOT / '.scratch/blender-4.5.14/Blender.app/Contents/MacOS/Blender'
    if blender is None and mounted.is_file():
        blender = str(mounted)
    checks.append({'name': 'dealership_roundtrip', 'command': [blender or 'blender', '--background', '--python-exit-code', '1',
                                                           '--python', 'tools/test_dealership_roundtrip.py'], 'requires': blender or 'blender'})
    checks.append({'name': 'redline_roundtrip', 'command': [blender or 'blender', '--background', '--python-exit-code', '1',
                                                        '--python', 'tools/test_redline_roundtrip.py'], 'requires': blender or 'blender',
                   'availability': ['python3', '-c', "from pathlib import Path; import sys; sys.exit(0 if Path('dealership/public/redline/index.json').is_file() else 1)"]})
    checks.append({'name': 'mc3_roundtrip', 'command': [blender or 'blender', '--background', '--python-exit-code', '1',
                                                     '--python', 'tools/test_mc3_roundtrip.py'], 'requires': blender or 'blender'})
    return checks


def select(checks, names, games=False):
    """Named checks when given; otherwise the showcase checks, plus the game checks with `games`."""
    requested = set(names)
    unknown = requested - {c['name'] for c in checks}
    if unknown:
        raise ValueError('Unknown checks: ' + ', '.join(sorted(unknown)))
    if requested:
        return [c for c in checks if c['name'] in requested]
    return [c for c in checks if games or c['name'] in SHOWCASE]


def run_checks(checks, root, evidence, ci=False, not_run=()):
    root, evidence = Path(root), Path(evidence)
    evidence.mkdir(parents=True, exist_ok=True)
    if any(evidence.iterdir()):
        raise ValueError('Evidence directory must be empty; previous logs are preserved')
    rows = []
    for check in checks:
        name, command = check['name'], check['command']
        start = time.monotonic()
        row = {'name': name, 'command': command, 'status': 'pass', 'exit_code': 0, 'log': name + '.log'}
        log = evidence / row['log']
        requirement = check.get('requires')
        if requirement and not shutil.which(requirement):
            row.update(status='fail' if ci else 'skip', exit_code=127 if ci else None,
                       reason=f'Required runtime unavailable: {requirement}')
            log.write_text(row['reason'] + '\n')
        else:
            available = subprocess.run(check['availability'], cwd=root, capture_output=True, text=True) if 'availability' in check else None
            if available is not None and available.returncode:
                row.update(status='skip' if available.returncode == 1 else 'fail',
                           exit_code=None if available.returncode == 1 else available.returncode,
                           reason='Optional pinned inputs unavailable' if available.returncode == 1 else 'Input availability check failed')
                log.write_text(row['reason'] + '\n' + available.stdout + available.stderr)
            else:
                with log.open('w') as stream:
                    try:
                        result = subprocess.run(command, cwd=root, stdout=stream, stderr=subprocess.STDOUT)
                        row.update(exit_code=result.returncode, status='pass' if result.returncode == 0 else 'fail')
                    except OSError as error:
                        stream.write(str(error) + '\n')
                        row.update(status='fail', exit_code=127)
        row['elapsed_seconds'] = round(time.monotonic() - start, 3)
        rows.append(row)
        print(f"{row['status']:4}  {name}  ({row['log']})", flush=True)
        if row['status'] == 'fail':
            print('\n'.join(log.read_text(errors='replace').splitlines()[-20:]), flush=True)
        status = 1 if any(r['status'] == 'fail' for r in rows) else 0
        (evidence / 'results.json').write_text(json.dumps({'schema': 1, 'exit_code': status, 'checks': rows,
            'not_run': list(not_run),
            'claim_limits': ['Only listed checks ran; skips are not passes. Logs record execution, not shader fidelity.']}, indent=2) + '\n')
    return 1 if any(r['status'] == 'fail' for r in rows) else 0


def main():
    if sys.version_info < MIN_PYTHON:
        print('ERROR: tools/check.sh needs Python %d.%d or newer; python3 is %d.%d (%s)'
              % (*MIN_PYTHON, *sys.version_info[:2], sys.executable))
        return 2
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--only', action='append', default=[], help='Check names, comma separated; repeatable')
    parser.add_argument('--games', action='store_true',
                        help='Also run the game extraction, re-derivation and research checks')
    parser.add_argument('--list', action='store_true')
    parser.add_argument('--evidence-dir', type=Path, help='Empty directory for full logs and results.json')
    args = parser.parse_args()
    checks = registry()
    if args.list:
        print('\n'.join(c['name'] for c in checks))
        return 0
    try:
        selected = select(checks, [n for group in args.only for n in group.split(',')], args.games)
        not_run = [c['name'] for c in checks if c not in selected]
        checks = selected
        if args.evidence_dir is None:
            parent = ROOT / '.scratch/checks'
            parent.mkdir(parents=True, exist_ok=True)
            evidence = Path(tempfile.mkdtemp(prefix='run-', dir=parent))
        else:
            evidence = args.evidence_dir.resolve()
        print(f'Evidence: {evidence}', flush=True)
        if not_run and not args.only:
            print(f'{len(not_run)} game checks not run (tools/check.sh --games runs them)', flush=True)
        return run_checks(checks, ROOT, evidence, ci=bool(os.environ.get('CI')), not_run=not_run)
    except ValueError as error:
        parser.error(str(error))


if __name__ == '__main__':
    raise SystemExit(main())
