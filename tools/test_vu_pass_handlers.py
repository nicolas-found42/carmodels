#!/usr/bin/env python3
"""Assert the VU1 pass-4/5 handler decode, the executor's instruction semantics and the negative controls.

Needs configured overlays (see CONTRIBUTING.md). Run from the repo root:
    python3 tools/test_vu_pass_handlers.py
"""
import json
import random
import re
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path.insert(0, str(HERE))
import verify_vu_pass_handlers as vph  # noqa: E402
import vu1_decode as vd  # noqa: E402
import vu1_exec as vx  # noqa: E402


def find_run(words, ops):
    for a in range(len(words) - len(ops)):
        if all(vd.decode_pair(*words[a + k])[0]['op'] == op for k, op in enumerate(ops)):
            return a
    raise AssertionError('instruction run not found: %r' % (ops,))


def test_executor(words):
    num = vx.NumDomain()
    # a four-pair mulax / madday / maddaz / maddw chain is a 4x4 matrix times a vector, rounded to binary32 at each step
    a = find_run(words, ['mulax', 'madday', 'maddaz', 'maddw'])
    u0 = vd.decode_pair(*words[a])[0]
    rng = random.Random(7)
    m = vx.Machine(num)
    rows = {}
    for reg in (u0['fs'], vd.decode_pair(*words[a + 1])[0]['fs'], vd.decode_pair(*words[a + 2])[0]['fs'], vd.decode_pair(*words[a + 3])[0]['fs']):
        rows[reg] = [vx.f32(rng.uniform(-3, 3)) for _ in range(4)]
        m.vf[reg] = list(rows[reg])
    vec_reg = u0['ft']
    m.vf[vec_reg] = [vx.f32(rng.uniform(-3, 3)) for _ in range(4)]
    vx.run_pairs(m, words[a:a + 4])
    regs = [u0['fs'], vd.decode_pair(*words[a + 1])[0]['fs'], vd.decode_pair(*words[a + 2])[0]['fs'], vd.decode_pair(*words[a + 3])[0]['fs']]
    out = vd.decode_pair(*words[a + 3])[0]['fd']
    for k in range(4):
        acc = vx.f32(rows[regs[0]][k] * m.vf[vec_reg][0])
        acc = vx.f32(acc + vx.f32(rows[regs[1]][k] * m.vf[vec_reg][1]))
        acc = vx.f32(acc + vx.f32(rows[regs[2]][k] * m.vf[vec_reg][2]))
        acc = vx.f32(acc + vx.f32(rows[regs[3]][k] * m.vf[vec_reg][3]))
        assert m.vf[out][k] == acc, (k, m.vf[out][k], acc)
    # integer conversion truncates toward zero and saturates; floats flush denormals and clamp
    assert [num.ftoi(x, 0) for x in (3.9, -3.9, 0.5, -0.5)] == [3, -3, 0, 0]
    assert num.ftoi(1e20, 0) == 2 ** 31 - 1 and num.ftoi(-1e20, 0) == -2 ** 31
    assert num.ftoi(1.5, 4) == 24 and num.itof(24, 4) == 1.5
    assert vx.f32(1e-40) == 0.0 and vx.f32(1e39) == vx.F32_MAX and vx.f32(float('nan')) == 0.0
    # division: 1/x, and a zero divisor clamps instead of producing infinity
    assert num.div(1.0, 4.0) == 0.25 and num.div(1.0, 0.0) == vx.F32_MAX
    # the shared-binding printer reuses a repeated subexpression and the symbolic domain folds constants
    sym = vx.SymDomain()
    a_, b_ = sym.sym('a'), sym.sym('b')
    shared = sym.add(sym.mul(a_, b_), 1.5)
    bindings, rendered = vx.ssa([sym.mul(shared, shared), sym.add(shared, a_)], min_len=4)
    assert bindings and len(bindings) == 1 and rendered[0] == 't1*t1' and rendered[1] == 't1 + a', (bindings, rendered)
    assert sym.mul(a_, 1.0) is a_ and sym.add(a_, 0.0) is a_ and sym.mul(a_, 0.0) == 0.0 and sym.sub(0.0, a_).s == '-a'
    assert vx.evaluate(shared, {'a': 2.0, 'b': 3.0}) == 7.5
    # an instruction form the executor does not implement fails loudly; an undecodable word renders as '?'
    clip = find_run(words, ['clipw'])
    try:
        vx.Machine(num).step(*words[clip])
    except NotImplementedError:
        pass
    else:
        raise AssertionError('clipw executed without an implementation')
    assert vd.render_upper(vd.decode_upper(0x7FFFFFFF)).startswith('?') and vd.render_lower(vd.decode_lower(0x7FFFFFFF)).startswith('?')


def main():
    inputs = vph.load_inputs()
    words, _ = vph.program(inputs)
    test_executor(words)

    r = vph.derive(inputs)
    h4, h5 = r['handlers']['4'], r['handlers']['5']
    assert r['matrix_prologue']['dm_inputs']['5'] == ['TOP[21].%s' % c for c in 'xyzw']
    assert (h4['entry_address'], h4['overlay'], h4['local_pair']) == (558, 2, 46) and (h5['entry_address'], h5['overlay'], h5['local_pair']) == (469, 1, 213)
    assert h4['pairs'] == {'loop_start': 575, 'loop_branch': 687, 'loop_delay_slot': 688, 'tail_kick': 690, 'tail_branch': 691, 'entry': 558}
    assert h5['pairs'] == {'loop_start': 484, 'loop_branch': 552, 'loop_delay_slot': 553, 'tail_kick': 555, 'tail_branch': 556, 'entry': 469}
    for h in (h4, h5):
        assert h['loop']['vertices_per_iteration'] == 4 and h['loop']['pointer_step_qwords'] == 12 and h['loop']['counter_step'] == -4
        assert h['vertices_identical_after_shift'] and h['exit_target'] == 758 and h['dm59_y_write'] == 'DM[59].y = DM[59].y | 1'
        assert h['vertex0']['xyzf'] == ['B1[3].x', 'B1[3].y', 'B1[3].z', 'B1[3].w']  # copied from the previous output buffer
        assert h['vertex0']['stq'][2:] == ['B1[1].z', 'B1[1].w']
    assert (h4['static_kick']['dm_address'], h5['static_kick']['dm_address']) == (37, 28)
    # pass 4: colour factor, unconverted w lane, reflection coordinates
    v4 = h4['vertex0']
    bind4 = dict(v4['bindings'])
    assert v4['rgba'] == ['ftoi0(TOP[1].x*t11)', 'ftoi0(TOP[1].y*t11)', 'ftoi0(TOP[1].z*t11)', 't11']
    assert bind4['t11'] == 'min(1 - t4*-0.949999988, 1)' and bind4['t4'] == '(t1*P[1].x + t2*P[1].y) + t3*P[1].z'
    assert bind4['t10'].startswith('div(1, -1 - abs(')
    assert v4['stq'][0].endswith('*t10*0.5 + 0.5)*B1[1].z') and v4['stq'][1].startswith('(-((TOP[12].y*t7')
    # pass 5: one RGBA for the whole draw, constant t coordinate
    v5 = h5['vertex0']
    assert v5['rgba'] == ['ftoi0(min(DM[5].x*TOP[1].x, 128))', 'ftoi0(min(DM[5].y*TOP[1].y, 128))', 'ftoi0(min(DM[5].z*TOP[1].z, 128))', 'ftoi0(min(DM[5].w, 128))']
    assert v5['stq'][1] == 'TOP[1].w*B1[1].z' and v5['stq'][0].startswith('max(') and not any(re.search(r'\bP\[', x) for x in v5['rgba'])
    e = r['epilogue']
    assert (e['first_pair'], e['flag_mask_tested_on_vi13'], e['kick_register'], e['e_bit_pair'], e['branch_back_target']) == (758, 0x100, 'vi11', 766, 60)
    assert e['next_entry_store'] == {'address': 'DM[59].w', 'value': 0x2fe} and e['flag_set_branch'] == {'pair': 763, 'target': 797}
    assert r['numeric_cross_check_values'] == {'4': 1920, '5': 1920}

    # negative controls and the committed receipt
    controls = vph.run_controls(inputs, r)
    assert [c['mutation'] for c in controls] == [label for label, _ in vph.CONTROLS] and len(controls) == 9 and all(c['rejected'] for c in controls)
    assert {c['by'] for c in controls} == {'derivation error', 'receipt differs'}
    committed = json.loads((ROOT / 'research/evidence/vu-dispatch/handlers-pass4-pass5.json').read_text())
    assert committed.pop('controls') == json.loads(json.dumps(controls)) and committed == json.loads(json.dumps(r))
    run = subprocess.run([sys.executable, str(HERE / 'verify_vu_pass_handlers.py')], capture_output=True, text=True, cwd=ROOT)
    assert run.returncode == 0 and 'VERIFY OK' in run.stdout, run.stdout[-1500:] + run.stderr[-1500:]
    print('PASS test_vu_pass_handlers')


if __name__ == '__main__':
    main()
