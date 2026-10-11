"""Named offline checks with retained per-command logs and a machine-readable manifest."""
import argparse
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import time

ROOT = Path(__file__).resolve().parents[1]


def registry():
    checks = [{'name': 'ruff', 'command': ['ruff', 'check', 'tools'], 'requires': 'ruff'}]
    checks += [{'name': n, 'command': ['node', f'tools/{n}.mjs'], 'requires': 'node'} for n in
               ['test_viewer_scenes', 'test_viewer_materials', 'test_model_load', 'test_viewer_loading', 'test_dealership', 'test_editable_glb', 'test_native_catalog_ui', 'test_mc3_preview_ui']]
    names = ['verify_recovered_asset_index', 'test_export_materials', 'test_build_showcase', 'test_bake_models',
             'test_build_dealership', 'test_model_catalog', 'test_model_png', 'test_run_checks', 'test_review_payload',
             'test_static_inputs', 'test_recovery_inputs', 'test_gt_archive', 'test_gt_asset_judgments', 'test_gt_wheels', 'test_gt_model', 'test_import_gt_dealership',
             'test_library_filter', 'test_serve_library', 'test_redline_archive', 'test_extract_redline_cars', 'test_mc3_archive', 'test_extract_mc3_cars', 'test_import_mc3_catalogs',
             'test_mc3_pck', 'test_mc3_wheels', 'test_mc3_materials', 'test_mc3_textures', 'test_mc3_model', 'test_export_mc3_models', 'test_mc3_preview', 'test_import_mc3_previews', 'test_mc3_preview_experiments',
             'test_redline_mesh', 'test_redline_texture', 'test_redline_model', 'test_export_redline_models', 'test_import_redline_dealership']
    checks += [{'name': n, 'command': ['python3', f'tools/{n}.py']} for n in names]
    checks.append({'name': 'dealership_freshness', 'command': ['python3', 'tools/build_dealership.py', '--check']})
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


def select(checks, names):
    requested = set(names)
    unknown = requested - {c['name'] for c in checks}
    if unknown:
        raise ValueError('Unknown checks: ' + ', '.join(sorted(unknown)))
    return [c for c in checks if not requested or c['name'] in requested]


def run_checks(checks, root, evidence, ci=False):
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
            'claim_limits': ['Only listed checks ran; skips are not passes. Logs record execution, not shader fidelity.']}, indent=2) + '\n')
    return 1 if any(r['status'] == 'fail' for r in rows) else 0


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--only', action='append', default=[], help='Check names, comma separated; repeatable')
    parser.add_argument('--list', action='store_true')
    parser.add_argument('--evidence-dir', type=Path, help='Empty directory for full logs and results.json')
    args = parser.parse_args()
    checks = registry()
    if args.list:
        print('\n'.join(c['name'] for c in checks))
        return 0
    try:
        checks = select(checks, [n for group in args.only for n in group.split(',')])
        if args.evidence_dir is None:
            parent = ROOT / '.scratch/checks'
            parent.mkdir(parents=True, exist_ok=True)
            evidence = Path(tempfile.mkdtemp(prefix='run-', dir=parent))
        else:
            evidence = args.evidence_dir.resolve()
        print(f'Evidence: {evidence}', flush=True)
        return run_checks(checks, ROOT, evidence, ci=bool(os.environ.get('CI')))
    except ValueError as error:
        parser.error(str(error))


if __name__ == '__main__':
    raise SystemExit(main())
