#!/usr/bin/env python3
"""Join retained FUN_0021bb48 colour vectors to source material headers and to executed packet RGBA alpha lanes.

Pairs come from retained-ring-gsdump-alignment.json.  Alpha is compared lane-by-lane against the dump;
RGB is not claimed.  The seven-vertex untextured call is reported with its source-plane pointer so that
the duplicate COBRA headers 149 and 261 can be told apart in the retained state.
"""
import json
import struct

import gsdump
import join_retained_blocks_to_gsdump as gj
import validate_retained_packet_blocks as vb

ROOT = vb.ROOT
ALIGN = ROOT / 'research/evidence/packet-continuation/retained-ring-gsdump-alignment.json'
MATERIAL = ROOT / 'research/evidence/continuation/source-refresh/material-header-contract.json'
OUT = ROOT / 'research/evidence/packet-continuation/retained-material-alpha-join.json'


def f32(u):
    return struct.unpack('<f', struct.pack('<I', u))[0]


def dump_rgba():
    transfers, _ = gsdump.load_transfers(gj.DUMP, gj.DUMP_PIN)
    out = {}
    for ti, data in enumerate(transfers):
        for off, lo, hi, nloop, flg, nreg, _ in gsdump.iter_tags(data):
            if flg == 0 and hi == 0x412:
                out[ti] = [tuple(x & 255 for x in struct.unpack_from('<4I', data, off + 16 + (i * 3 + 1) * 16)) for i in range(nloop)]
    return out


def main():
    ring = json.loads(ALIGN.read_text())
    rgba = dump_rgba()
    census = json.loads(vb.CENSUS.read_text())
    hoff = {c['code']: [h['offset'] for h in c['geometry']['headers']] for c in census['cars']}
    mh = {c['car']: {h['offset']: h for h in c['headers']} for c in json.loads(MATERIAL.read_text())['cars']}
    stats = {}
    seven = []
    base_eq = {'draws': 0, 'vec4_equals_base_color_rgba': 0}
    for ai, t in ring['matched_pairs']:
        d = ring['draws'][ai]
        if not d.get('vec4_u32'):
            continue
        v = [f32(x) for x in d['vec4_u32']]
        lanes = {px[3] for px in rgba[t]}
        s = stats.setdefault(d['pass_id'], {'aligned_draws': 0, 'alpha_lanes_all_equal_vec4_w': 0, 'alpha_lane_min': 255, 'alpha_lane_max': 0})
        s['aligned_draws'] += 1
        s['alpha_lanes_all_equal_vec4_w'] += lanes == {round(v[3])} and abs(v[3] - round(v[3])) < 1e-6
        s['alpha_lane_min'] = min(s['alpha_lane_min'], min(lanes)); s['alpha_lane_max'] = max(s['alpha_lane_max'], max(lanes))
        if d['pass_id'] == 2 and len(d.get('source_headers', [])) == 1:
            car, hi = d['source_headers'][0]
            h = mh[car][hoff[car][hi]]
            base_eq['draws'] += 1
            base_eq['vec4_equals_base_color_rgba'] += [float(x) for x in h['base_color_rgba_unscaled']] == v
        if d['nloop'] == 7 and d['pass_id'] == 2 and d.get('source_headers'):
            seven.append({'retained_chain_addr': hex(d['chain_addr']), 'transfer': t, 'source_headers': d['source_headers'], 'ptr6': hex(d['ptr6']), 'ptr4': hex(d['ptr4']),
                          'effective_flags': hex(d['effective_flags']), 'vec4': v, 'dump_alpha_lanes': sorted(lanes), 'arm': d['arm']})
    # retained seven-vertex calls (any pass) with a COBRA pointer, independent of dump alignment
    seven_all = [{'chain_addr': hex(d['chain_addr']), 'pass_id': d['pass_id'], 'prim': hex(d['prim']), 'source_headers': d['source_headers'], 'ptr6': hex(d['ptr6'])}
                 for d in ring['draws'] if d['nloop'] == 7 and d.get('source_headers')]
    h149, h261 = hoff['COBRA'][149], hoff['COBRA'][261]
    cobra_planes = {149: {'six_byte_offset': None}, 261: {'six_byte_offset': None}}
    for k in (149, 261):
        for c in census['cars']:
            if c['code'] == 'COBRA':
                cobra_planes[k]['six_byte_offset'] = c['geometry']['headers'][k]['planes']['six_byte']['offset']
    receipt = {
        'scope': 'Retained colour vector and alpha-lane join over aligned retained/GSDump pairs; RGB is not claimed.',
        'by_pass_id': {str(k): v for k, v in sorted(stats.items())},
        'pass2_vec4_equals_source_base_color_rgba_unscaled': base_eq,
        'seven_vertex_aligned_pass2': seven,
        'seven_vertex_retained_calls_with_cobra_pointer': seven_all,
        'duplicate_headers': {'149_header_offset': h149, '261_header_offset': h261, 'planes': cobra_planes,
                              'material_words_equal': mh['COBRA'][h149]['raw_header_hex'] == mh['COBRA'][h261]['raw_header_hex']},
    }
    OUT.write_text(json.dumps(receipt, indent=1))
    print(json.dumps(receipt, indent=1))


if __name__ == '__main__':
    main()
