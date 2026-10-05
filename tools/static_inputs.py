#!/usr/bin/env python3
"""Locate the executable-derived static inputs that some verifiers read.

These inputs are never committed; the committed receipts carry their SHA-256 pins. Three environment
variables name them, there is no default path, and a missing input ends the tool with one line:

    CARMODELS_OVERLAY_DIR    directory with overlay-N.bin (VU1 microcode) and overlay-N.s (its disassembly), N = 0..6
    CARMODELS_TYPED_EXPORT   directory with inventory.json and decompilation/functions/<entry>.c
    CARMODELS_EXECUTABLE     the PAL executable (SLES_517.05)

    python3 tools/static_inputs.py              # report each input and check it against its pin
    python3 tools/static_inputs.py --available  # exit 0 when all three are set, 1 otherwise (used by tools/check.sh)
"""
import hashlib
import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REFRESH = ROOT / 'research/evidence/continuation/source-refresh/refresh-identity.json'
RESIDENCY = ROOT / 'research/evidence/packet-continuation/vu-overlay-residency.json'
VARIABLES = {'overlays': 'CARMODELS_OVERLAY_DIR', 'typed_export': 'CARMODELS_TYPED_EXPORT', 'executable': 'CARMODELS_EXECUTABLE'}
CONFIG = ROOT / '.scratch/input-paths.json'


def configuration():
    """Read explicitly provisioned local paths; environment variables take precedence."""
    path = Path(os.environ.get('CARMODELS_INPUT_CONFIG', str(CONFIG))).expanduser()
    if not path.is_file():
        return {}
    values = json.loads(path.read_text())
    if not isinstance(values, dict) or any(not isinstance(v, str) for v in values.values()):
        missing('input-paths.json must map variable names to paths')
    return values


def configured(variable):
    return os.environ.get(variable) or configuration().get(variable)


def bundle_path():
    """Legacy data layout in a private local bundle, with no source checkout dependency."""
    return Path(configured('CARMODELS_BUNDLE') or ROOT / '.scratch/inputs').expanduser()


def sha256(data):
    return hashlib.sha256(data).hexdigest()


def missing(message):
    print('static input missing: %s (see CONTRIBUTING.md, Static inputs)' % message, file=sys.stderr)
    sys.exit(2)


def available():
    return all(configured(v) for v in VARIABLES.values())


def require(kind):
    """Path of one input; exits with a one-line message when it is not configured or not there."""
    variable = VARIABLES[kind]
    value = configured(variable)
    if not value:
        missing('%s is not set' % variable)
    path = Path(value).expanduser()
    if not path.exists():
        missing('%s=%s does not exist' % (variable, value))
    return path


def overlay_dir():
    return require('overlays')


def typed_export():
    return require('typed_export')


def executable():
    return require('executable')


def pins():
    refresh = json.loads(REFRESH.read_text())
    residency = json.loads(RESIDENCY.read_text())
    return {'inventory_sha256': refresh['inventory_sha256'], 'executable_sha256': refresh['executable_sha256'],
            'overlays': {n: residency['snapshots'][0]['overlays'][n]['sha256'] for n in range(7)}}


def report():
    """One line per input: found or not, and whether it equals its pin. Returns the number of problems."""
    expected, problems = pins(), 0
    rows = []
    for kind, variable in VARIABLES.items():
        value = configured(variable)
        if not value or not Path(value).expanduser().exists():
            rows.append((kind, variable, 'MISSING' if not value else 'NOT FOUND: ' + value))
            problems += 1
            continue
        path = Path(value).expanduser()
        if kind == 'executable':
            ok = sha256(path.read_bytes()) == expected['executable_sha256']
        elif kind == 'typed_export':
            ok = sha256((path / 'inventory.json').read_bytes()) == expected['inventory_sha256']
        else:
            ok = all((path / ('overlay-%d.bin' % n)).is_file() and sha256((path / ('overlay-%d.bin' % n)).read_bytes()) == h
                     for n, h in expected['overlays'].items()) and all((path / ('overlay-%d.s' % n)).is_file() for n in range(7))
        rows.append((kind, variable, 'ok (matches its pin)' if ok else 'DIFFERS FROM ITS PIN'))
        problems += not ok
    for kind, variable, state in rows:
        print('%-12s %-24s %s' % (kind, variable, state))
    return problems


if __name__ == '__main__':
    if '--available' in sys.argv[1:]:
        sys.exit(0 if available() else 1)
    sys.exit(1 if report() else 0)
