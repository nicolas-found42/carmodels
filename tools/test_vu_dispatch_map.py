#!/usr/bin/env python3
"""Assert the VU1 dispatch-map derivation and its negative controls (deterministic; no model calls).

Needs the static inputs (see CONTRIBUTING.md, Static inputs). Run from the repo root:
    python3 tools/test_vu_dispatch_map.py
"""
import importlib.util
import json
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent

spec = importlib.util.spec_from_file_location('verify_vu_dispatch_map', HERE / 'verify_vu_dispatch_map.py')
assert spec and spec.loader
vdm = importlib.util.module_from_spec(spec)
spec.loader.exec_module(vdm)


def main():
    inputs = vdm.load_inputs()
    r = vdm.derive(inputs)

    # jump table: seven VU instruction addresses written by overlay 0 pairs 0-14 to data words 0..6 at 0x14
    t = r['jump_table']
    assert t['data_memory_base'] == 0x14 and t['written_by_overlay0_pairs'] == [0, 14]
    assert [e['target_address'] for e in t['entries']] == [0x2fe, 0x4d, 0xa3, 0x1ac, 0x22e, 0x1d5, 0x2b5]
    assert [(e['overlay'], e['local_pair']) for e in t['entries']] == [(2, 254), (0, 77), (0, 163), (1, 172), (2, 46), (1, 213), (2, 181)]
    assert t['entries'][0]['target_text'] == 'nop[e] \tnop' or 'nop[e]' in t['entries'][0]['target_text']

    # the table writer is a separate program that ends (E bit) before MSCAL entry 0x1a
    assert r['init_program'] == {'first_pair': 0, 'last_pair_with_e_bit': 24, 'delay_slot_pair': 25, 'next_entry_address': 0x1a}

    # entry 0x1a: matrix prologue, then a second xtop and the table dispatch
    d = r['dispatch_at_entry_0x1a']
    assert d['entry_address'] == 0x1a and d['overlay'] == 0 and d['prologue_pairs'] == [26, 59]
    assert d['dispatch_pairs'] == {'xtop': 60, 'ilwr_index_x': 61, 'table_base_iaddiu': 64, 'iadd_index': 65, 'ilwr_handler_w': 66, 'jr': 73}
    assert d['index_lane'] == {'qword_offset_from_top': 0, 'lane': 'x'}

    # MSCAL immediates derived from FUN_0022fda8 and where they are emitted
    m = {e['name']: e for e in r['mscal_entries']}
    assert m['mscal0']['value'] == 0 and m['main_car_path']['value'] == 0x1a and m['overlay5_path']['value'] == 0x5cc
    assert m['main_car_path']['emitters'] == ['0021c3e0'] and m['overlay5_path']['emitters'] == ['00128ca0'] and m['mscal0']['emitters'] == ['001124c0']
    assert m['main_car_path']['overlay'] == 0 and m['overlay5_path']['overlay'] == 5 and m['overlay5_path']['local_pair'] == 204

    # 0021bb48 payload qword 0: x=pass word (arg 2), y=arg 3, z=arg 4, w=arg 5
    p = r['pass_word_header']
    assert p['unpack_code_without_param8'] == 0x6c038000 and p['payload_qword0_lanes'] == {'x': 'param_2', 'y': 'param_3', 'z': 'param_4', 'w': 'param_5'}
    assert p['static_pass_words'] == [1, 2, 3, 4, 5, 6] and p['table_indices_without_stop'] == [1, 2, 3, 4, 5, 6]
    assert p['pass_words_outside_table'] == [] and p['table_index_0_is_stop'] is True

    # call graph: the two packet emitters are siblings under a lowest common ancestor, not a direct chain
    g = r['call_graph']
    assert g['direct_callers'] == {'00128e88': ['001288b0'], '0021ba50': ['0021c3e0']}
    assert g['lowest_common_ancestors'] == ['001cf848'] and not g['direct_chain_either_way']
    assert g['paths']['00128e88'] == ['001cf848', '001ce288', '001288b0', '00128e88']
    assert g['paths']['0021ba50'] == ['001cf848', '0021d8c8', '00127fa8', '0021d180', '0021bf28', '0021c3e0', '0021ba50']

    assert r['claim_limits'] and 'execution' in ' '.join(r['claim_limits']).lower()

    # negative controls: each mutated copy of the inputs must be rejected by the same derivation
    controls = vdm.run_controls(inputs)
    assert [c['mutation'] for c in controls] == [label for label, _ in vdm.CONTROLS] and len(controls) == 14 and all(c['rejected'] for c in controls)

    # the micro-memory snapshot cross-check: a snapshot laid out as the receipt says reproduces the receipt; a moved window is rejected
    layout = vdm.clone_inputs(inputs)
    snapshot = bytearray(16384)
    for n, off in layout['residency_offsets'].items():
        snapshot[off:off + len(layout['overlays'][n]['bin'])] = layout['overlays'][n]['bin']
    layout['snapshot'] = bytes(snapshot)
    assert vdm.derive(layout) == r
    moved = vdm.clone_inputs(layout)
    moved_snapshot = bytearray(layout['snapshot'])
    moved_snapshot[0x0800:0x1000] = bytes(0x800)
    moved_snapshot[0x3800:0x3800 + 0x800] = layout['overlays'][1]['bin']
    moved['snapshot'] = bytes(moved_snapshot)
    try:
        vdm.derive(moved)
    except vdm.DispatchError as e:
        assert 'micro-memory snapshot' in str(e)
    else:
        raise AssertionError('a moved overlay window in the snapshot escaped')

    # the committed receipt reproduces from the pinned sources
    r2 = subprocess.run([sys.executable, str(HERE / 'verify_vu_dispatch_map.py')], capture_output=True, text=True, cwd=ROOT)
    assert r2.returncode == 0 and 'VERIFY OK' in r2.stdout, r2.stdout[-1500:] + r2.stderr[-1500:]
    committed = json.loads((ROOT / 'research/evidence/vu-dispatch/dispatch-map.json').read_text())
    assert committed.pop('controls') == json.loads(json.dumps(controls)) and committed == json.loads(json.dumps(r))
    print('PASS test_vu_dispatch_map')


if __name__ == '__main__':
    main()
