#!/usr/bin/env python3
"""Test the static-input lookup and the shared verifier helpers. Needs no static inputs.

    python3 tools/test_static_inputs.py
"""
import contextlib
import io
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import static_inputs  # noqa: E402
import verifier_common  # noqa: E402

CLEAN_ENV = {k: v for k, v in os.environ.items() if k not in static_inputs.VARIABLES.values()}


def run(*args, env=None):
    return subprocess.run([sys.executable, str(HERE / 'static_inputs.py'), *args], capture_output=True, text=True, env=env or CLEAN_ENV, check=False)


def test_lookup():
    # nothing set: availability is false, the report names every variable, and require() ends with one line
    assert run('--available').returncode == 1
    r = run()
    assert r.returncode == 1 and all(v in r.stdout for v in static_inputs.VARIABLES.values()) and r.stdout.count('MISSING') == 3
    probe = subprocess.run([sys.executable, '-c', 'import static_inputs; static_inputs.overlay_dir()'], capture_output=True, text=True, cwd=HERE, env=CLEAN_ENV, check=False)
    assert probe.returncode == 2 and probe.stderr.strip().count('\n') == 0 and 'CARMODELS_OVERLAY_DIR is not set' in probe.stderr and 'Static inputs' in probe.stderr

    # a path that does not exist is reported with its variable, and a file that differs from its pin is flagged
    with tempfile.TemporaryDirectory() as tmp:
        env = dict(CLEAN_ENV, CARMODELS_OVERLAY_DIR=tmp + '/nope', CARMODELS_TYPED_EXPORT=tmp, CARMODELS_EXECUTABLE=tmp + '/exe')
        Path(tmp, 'inventory.json').write_text('{}')
        Path(tmp, 'exe').write_bytes(b'not the executable')
        r = run(env=env)
        assert r.returncode == 1 and 'NOT FOUND' in r.stdout and r.stdout.count('DIFFERS FROM ITS PIN') == 2, r.stdout
        assert run('--available', env=env).returncode == 0  # all three set, even though they are wrong: availability is not validity
    pins = static_inputs.pins()
    assert len(pins['inventory_sha256']) == 64 and len(pins['executable_sha256']) == 64 and sorted(pins['overlays']) == list(range(7))


class Boom(ValueError):
    pass


def test_common():
    need = verifier_common.make_need(Boom)
    need(True, 'fine')
    try:
        need(False, 'bad')
    except Boom as e:
        assert str(e) == 'bad'
    else:
        raise AssertionError('need did not raise')
    assert verifier_common.normalise('lq  0x10 ,\t5') == 'lq 16 , 5' and verifier_common.normalise('vi02') == 'vi02'

    def derive(x):
        if x['n'] < 0:
            raise Boom('negative')
        return {'n': x['n']}
    controls = [('negative', lambda x: x.update(n=-1))]
    assert verifier_common.run_controls({'n': 1}, controls, derive, Boom) == [{'mutation': 'negative', 'rejected': True, 'reason': 'negative'}]
    try:  # a mutation that derives cleanly escaped
        verifier_common.run_controls({'n': 1}, [('harmless', lambda x: x.update(n=2))], derive, Boom)
    except AssertionError as e:
        assert 'harmless' in str(e)
    else:
        raise AssertionError('an escaped mutation was accepted')
    # with a baseline, a mutation that changes the receipt counts and says how it was caught
    both = verifier_common.run_controls({'n': 1}, controls + [('changed', lambda x: x.update(n=2))], derive, Boom, baseline={'n': 1})
    assert [c['by'] for c in both] == ['derivation error', 'receipt differs']
    try:
        verifier_common.run_controls({'n': 1}, [('same', lambda x: None)], derive, Boom, baseline={'n': 1})
    except AssertionError:
        pass
    else:
        raise AssertionError('an unchanged receipt was accepted as a rejection')
    # finish: --write creates the receipt, a reproduction passes, a changed receipt fails
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        path = root / 'out' / 'receipt.json'
        with contextlib.redirect_stdout(io.StringIO()) as out:
            assert verifier_common.finish({'a': 1}, path, ['--write'], root, {'ok': True}) == 0 and json.loads(path.read_text()) == {'a': 1}
            assert verifier_common.finish({'a': 1}, path, [], root, {'ok': True}) == 0
            assert verifier_common.finish({'a': 2}, path, [], root, {'ok': True}) == 1 and json.loads(path.read_text()) == {'a': 1}
            assert verifier_common.finish({'a': 1}, root / 'missing.json', [], root, {}) == 1
        assert out.getvalue().count('RECEIPT MISMATCH') == 2 and out.getvalue().count('VERIFY OK') == 2


if __name__ == '__main__':
    test_lookup()
    test_common()
    print('PASS test_static_inputs')
