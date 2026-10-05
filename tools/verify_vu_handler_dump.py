#!/usr/bin/env python3
"""Compare decoded pass-4/5 properties with pinned retained DMA and GSDump bytes.

Content alignment is not an execution trace. Full pass-4 UV and pass-5 S need
per-vertex working-plane reconstruction. T is measured against host binary32
arithmetic, with a one-ULP bound and exact mismatches retained in the receipt.
"""
import copy
import json
import math
from pathlib import Path
import struct
import sys

import gsdump
import join_retained_blocks_to_gsdump as gj
import trace_retained_ring_to_gsdump as ring_tools
import verifier_common as common

ROOT = Path(__file__).resolve().parents[1]
ALIGN = ROOT / 'research/evidence/packet-continuation/retained-ring-gsdump-alignment.json'
HANDLERS = ROOT / 'research/evidence/vu-dispatch/handlers-pass4-pass5.json'
OUT = ROOT / 'research/evidence/vu-dispatch/handler-dump-comparison.json'


class ComparisonError(ValueError):
    pass


need = common.make_need(ComparisonError)


def real(word):
    value = struct.unpack('<f', struct.pack('<I', word))[0]
    need(math.isfinite(value), 'non-finite float input')
    return value


def f32(value):
    return struct.unpack('<f', struct.pack('<f', value))[0]


def bits(value):
    return struct.unpack('<I', struct.pack('<f', value))[0]


def reference_rgba(dm5, colour):
    return tuple(int(min(f32(dm5[k] * colour[k]), 128)) & 0xffffffff
                 for k in range(3)) + (int(min(dm5[3], 128)) & 0xffffffff,)


def geometry_key(draw):
    return draw.get('ptr6'), draw.get('ptr4'), draw.get('count')


def load_inputs():
    if not gj.DUMP.is_file() or not ring_tools.vb.CAPTURES['race95'].is_file():
        raise SystemExit('runtime input missing: race94 GSDump or race95 EE memory (see docs/static-inputs.md)')
    raw_align, raw_handlers = ALIGN.read_bytes(), HANDLERS.read_bytes()
    align, handlers = json.loads(raw_align), json.loads(raw_handlers)
    target_indices = [ai for ai, _ in align['matched_pairs'] if align['draws'][ai].get('pass_id') in (4, 5)]
    needed_transfers = {t for ai, t in align['matched_pairs'] if ai <= max(target_indices)}
    transfers, decompressed_sha = gsdump.load_transfers(gj.DUMP, gj.DUMP_PIN)
    geometry = {}
    for transfer in sorted(needed_transfers):
        data = transfers[transfer]
        for off, lo, hi, nloop, flg, nreg, _ in gsdump.iter_tags(data):
            if flg == 0 and hi == 0x412:
                need(nreg == 3 and transfer not in geometry, 'ambiguous geometry tag in transfer')
                geometry[transfer] = [tuple(struct.unpack_from('<4I', data, off + 16 + (i * 3 + j) * 16)
                                             for j in range(3)) for i in range(nloop)]
    mem_path = ring_tools.vb.CAPTURES['race95']
    mem = mem_path.read_bytes()
    need(common.sha256(mem) == ring_tools.MEM_PIN, 'retained EE memory differs from capture pin')
    elements, status, _ = ring_tools.walk_chain(mem, ring_tools.CHAIN_START['A'])
    need(status == 'END', 'retained DMA chain does not terminate')
    raw_draws = {d['chain_addr']: d for d in ring_tools.parse_calls(elements)
                 if d['kind'] == 'FUN_0021c3e0+0021bb48'}
    uploads = [{'address': e['addr'], 'qwords': e['data']} for e in elements
               if e['id'] == 1 and e['qwc'] == 14 and e['v0'] == 0 and e['v1'] == 0x6c0e800c]
    # The paused VU image is a negative-context comparison, not the per-draw input.
    state = ROOT / 'research/evidence/continuation/runtime/linux/race95-state-identity.json'
    identity = json.loads(state.read_text())
    vu_pin = next(m['sha256'] for m in identity['members'] if m['member'] == 'vu1Memory.bin')
    vu_path = state.parent / 'race95-vu1Memory.bin'
    vu = vu_path.read_bytes()
    need(common.sha256(vu) == vu_pin, 'paused VU memory differs from capture pin')
    return {'align': align, 'raw_draws': raw_draws, 'handlers': handlers, 'geometry': geometry, 'uploads': uploads,
            'paused_dm5': list(struct.unpack_from('<4I', vu, 5 * 16)),
            'pins': {'alignment_sha256': common.sha256(raw_align), 'handler_receipt_sha256': common.sha256(raw_handlers),
                     'retained_ee_sha256': ring_tools.MEM_PIN, 'dump_compressed_sha256': gj.DUMP_PIN,
                     'dump_decompressed_sha256': decompressed_sha, 'paused_vu_memory_sha256': vu_pin}}


def derive(inputs):
    align, handlers, geo, uploads = (inputs[k] for k in ('align', 'handlers', 'geometry', 'uploads'))
    for p in ('4', '5'):
        vertex = handlers['handlers'][p]['vertex0']
        need(vertex['xyzf'] == ['B1[3].%s' % lane for lane in 'xyzw'], 'handler XYZF copy formula differs')
        need(vertex['stq'][2:] == ['B1[1].z', 'B1[1].w'], 'handler Q/w copy formula differs')
    need(handlers['handlers']['5']['vertex0']['rgba'] ==
         ['ftoi0(min(DM[5].%s*TOP[1].%s, 128))' % (c, c) for c in 'xyz'] + ['ftoi0(min(DM[5].w, 128))'],
         'pass5 RGBA formula differs')
    need(handlers['handlers']['5']['vertex0']['stq'][1] == 'TOP[1].w*B1[1].z', 'pass5 T formula differs')
    vertex4 = handlers['handlers']['4']['vertex0']
    need(vertex4['rgba'] == ['ftoi0(TOP[1].%s*t11)' % c for c in 'xyz'] + ['t11'], 'pass4 RGB/alpha relation differs')
    need(handlers['matrix_prologue']['dm_inputs']['5'] == ['TOP[21].%s' % c for c in 'xyzw'],
         'static matrix prologue DM5 mapping differs')
    draws = align['draws']
    seen = {}
    stats = {str(p): {'draws': 0, 'vertices': 0, 'xyzf_equal_draws': 0, 'qw_equal_draws': 0} for p in (4, 5)}
    stats['4'].update(rgb_from_raw_float_alpha_draws=0, finite_unit_alpha_draws=0)
    stats['5'].update(uniform_rgba_draws=0, rgba_from_retained_dm5_draws=0, t_exact_draws=0,
                      t_exact_vertices=0, t_one_ulp_vertices=0, t_max_ulp=0,
                      paused_dm5_mismatching_draws=0, t_without_colour_factor_failing_vertices=0)
    rows = []
    for index, transfer in align['matched_pairs']:
        d = draws[index]
        if d['kind'] == 'FUN_0021c3e0+0021bb48':
            raw = inputs['raw_draws'].get(d['chain_addr'])
            fields = ('pass_id', 'head_addr', 'ptr6', 'ptr4', 'count', 'nloop', 'effective_flags', 'vec4_u32')
            need(raw is not None and all(raw[f] == d[f] for f in fields),
                 'retained descriptor fields differ from EE packet bytes')
        key = geometry_key(d)
        previous = seen.get(key)
        if d.get('pass_id') not in (4, 5):
            if all(x is not None for x in key):
                seen[key] = (index, transfer)
            continue
        p, out = str(d['pass_id']), geo[transfer]
        need(previous is not None, 'missing previous output for pass ' + p)
        old_index, old_transfer = previous
        base = geo[old_transfer]
        need(len(out) == len(base) == d['count'] == d['nloop'], 'vertex count differs across aligned buffers')
        need(d['effective_flags'] & 0x100 == 0, 'clip path is outside the decoded comparison scope')
        need([q[2] for q in out] == [q[2] for q in base], 'inherited XYZF including ADC differs')
        need([q[0][2:] for q in out] == [q[0][2:] for q in base], 'inherited Q/w differs')
        candidates = [u for u in uploads if u['address'] < d['head_addr']]
        need(bool(candidates), 'retained matrix upload missing')
        upload = max(candidates, key=lambda u: u['address'])
        need(len(upload['qwords']) == 14 and all(len(q) == 4 for q in upload['qwords']), 'matrix upload shape differs')
        colour = tuple(real(u) for u in d['vec4_u32'])
        st = stats[p]
        st['draws'] += 1
        st['vertices'] += len(out)
        st['xyzf_equal_draws'] += 1
        st['qw_equal_draws'] += 1
        row = {'retained_index': index, 'transfer': transfer, 'pass_word': int(p), 'vertices': len(out),
               'previous_index': old_index, 'previous_transfer': old_transfer,
               'previous_pass_word': draws[old_index].get('pass_id'), 'matrix_upload_address': upload['address'],
               'retained_top12_14_u32': [list(q) for q in upload['qwords'][:3]],
               'retained_dm6_source_top22_u32': list(upload['qwords'][10]),
               'retained_dm7_source_top23_u32': list(upload['qwords'][11])}
        if p == '4':
            factors = [real(q[1][3]) for q in out]
            need(all(0 <= f <= 1 for f in factors), 'pass4 raw float alpha outside unit interval')
            need(all(tuple(int(f32(colour[k] * factor)) & 0xffffffff for k in range(3)) == q[1][:3]
                     for factor, q in zip(factors, out)), 'pass4 RGB differs from raw float alpha relation')
            st['rgb_from_raw_float_alpha_draws'] += 1
            st['finite_unit_alpha_draws'] += 1
        else:
            dm5 = tuple(real(u) for u in upload['qwords'][9])  # TOP[21] -> DM[5], overlay-0 prologue
            expected = reference_rgba(dm5, colour)
            need(all(q[1] == expected for q in out), 'pass5 RGBA differs from retained DM5 formula')
            st['uniform_rgba_draws'] += 1
            st['rgba_from_retained_dm5_draws'] += 1
            errors = []
            for q in out:
                qvalue = real(q[0][2])
                need(qvalue > 0 and real(q[0][1]) >= 0, 'T comparison requires positive Q and nonnegative T')
                error = abs(bits(f32(colour[3] * qvalue)) - q[0][1])
                need(error <= 1, 'pass5 T exceeds one binary32 ULP')
                errors.append(error)
                st['t_without_colour_factor_failing_vertices'] += abs(q[0][2] - q[0][1]) > 1
            st['t_exact_vertices'] += errors.count(0)
            st['t_one_ulp_vertices'] += errors.count(1)
            st['t_exact_draws'] += max(errors) == 0
            st['t_max_ulp'] = max(st['t_max_ulp'], max(errors))
            paused = reference_rgba(tuple(real(u) for u in inputs['paused_dm5']), colour)
            st['paused_dm5_mismatching_draws'] += any(q[1] != paused for q in out)
            row.update(retained_dm5_u32=list(upload['qwords'][9]), predicted_rgba=list(expected), t_max_ulp=max(errors))
        rows.append(row)
        seen[key] = (index, transfer)
    need(stats['4']['draws'] == 37 and stats['5']['draws'] == 63, 'pass4/5 comparison population differs')
    return {'schema': 'fr2-vu-handler-dump-comparison/v1', 'pins': inputs['pins'], 'by_pass_word': stats,
            'matrix_input_contract': {'unpack': '0x6c0e800c', 'qwords': 14, 'top_base': 12,
                                      'dm5_source_top_offset': 21, 'dm6_source_top_offset_negated': 22,
                                      'dm7_source_top_offset': 23,
                                      'pass4_matrix_top_offsets': [12, 13, 14],
                                      'selection': 'nearest preceding retained matrix upload before the draw head'},
            'rows': rows, 'render_fidelity_complete': False,
            'claim_limits': ['Retained EE/GSDump content alignment between separate captures; not same-frame execution proof.',
                             'Per-draw DM5 and matrix inputs are retained packet values, not arbitrary paused VU memory.',
                             'Pass4 checks inherited lanes and RGB/raw-float-alpha relation, not the full view/normal factor or UV calculation.',
                             'Pass5 checks inherited lanes, RGBA and T; S and its working-plane/view inputs remain unverified.',
                             '279 T values differ by one ULP from host binary32 multiplication; bit-exact VU arithmetic is not claimed.',
                             'Clip flag is clear on the compared draws; flag-set clip execution and static-kick packet origin remain open.']}


def mutate_vertex(inputs, pass_word, qword, lane, delta):
    index, transfer = next((i, t) for i, t in inputs['align']['matched_pairs'] if inputs['align']['draws'][i].get('pass_id') == pass_word)
    out = inputs['geometry'][transfer]
    vertex = [list(q) for q in out[0]]
    vertex[qword][lane] ^= delta
    out[0] = tuple(tuple(q) for q in vertex)


def controls(inputs):
    first5 = next(d for i, _ in inputs['align']['matched_pairs'] if (d := inputs['align']['draws'][i]).get('pass_id') == 5)
    def corrupt_dm5(i):
        upload = max((u for u in i['uploads'] if u['address'] < first5['head_addr']), key=lambda u: u['address'])
        upload['qwords'][9] = (0, 0, 0, 0)
    def corrupt_descriptor(i):
        d = next(i['align']['draws'][k] for k, _ in i['align']['matched_pairs']
                 if i['align']['draws'][k].get('pass_id') == 4)
        d['vec4_u32'][0] ^= 1
    tests = [('retained descriptor changed', corrupt_descriptor),
             ('XYZF ADC changed', lambda i: mutate_vertex(i, 4, 2, 3, 0x8000)),
             ('Q changed', lambda i: mutate_vertex(i, 5, 0, 2, 0x10)),
             ('pass4 RGB changed', lambda i: mutate_vertex(i, 4, 1, 0, 1)),
             ('pass4 alpha changed', lambda i: mutate_vertex(i, 4, 1, 3, 0x00800000)),
             ('pass5 RGBA changed', lambda i: mutate_vertex(i, 5, 1, 3, 1)),
             ('pass5 T changed beyond tolerance', lambda i: mutate_vertex(i, 5, 0, 1, 0x10)),
             ('retained DM5 replaced', corrupt_dm5)]
    expected = ['retained descriptor fields', 'inherited XYZF', 'inherited Q/w', 'pass4 RGB', 'pass4', 'pass5 RGBA', 'one binary32 ULP', 'retained DM5']
    results = common.run_controls(inputs, tests, derive, ComparisonError, clone=copy.deepcopy)
    for result, reason in zip(results, expected):
        need(reason in result['reason'], 'control failed for an unrelated reason: ' + result['mutation'])
    return results


def main(argv):
    if '--available' in argv:
        paths = [gj.DUMP, ring_tools.vb.CAPTURES['race95'],
                 ROOT / 'research/evidence/continuation/runtime/linux/race95-vu1Memory.bin',
                 ROOT / 'research/evidence/continuation/runtime/linux/race95-state-identity.json']
        return 0 if all(p.is_file() for p in paths) else 1
    inputs = load_inputs()
    result = derive(inputs)
    result['controls'] = controls(inputs)
    return common.finish(result, OUT, argv, ROOT, {'by_pass_word': result['by_pass_word'], 'controls': len(result['controls'])})


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
