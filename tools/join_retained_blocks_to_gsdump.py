#!/usr/bin/env python3
"""Join retained EE producer blocks (FUN_00128e88 / FUN_0021ba50 shapes) to executed GIF transfers in the race94 GSDump.

The joins are content joins between two captures of the same paused race scene (EE savestate vs a
separate GSDump).  They show that the dump's transfers carry exactly what these retained blocks request;
they do not show that the retained buffer produced those transfers in this frame.
"""
import hashlib
import json
import struct

import gsdump
import validate_retained_packet_blocks as vb

ROOT = vb.ROOT
DUMP = ROOT / 'research/evidence/continuation/runtime/snaps/Ford Racing 2_SLES-51705_20261004182459.gs.zst'
DUMP_PIN = 'fe3cad806c831b6db5577a336a1f92cfc1ac007d0004f3efb99117ae0eb77e88'
OUT = ROOT / 'research/evidence/packet-continuation/retained-blocks-gsdump-join.json'


def parse_dump():
    transfers, dsha = gsdump.load_transfers(DUMP, DUMP_PIN)
    geo, ad3 = [], []
    for ti, data in enumerate(transfers):
        for off, lo, hi, nloop, flg, nreg, _ in gsdump.iter_tags(data):
            if flg == 0 and hi == 0x412:
                v = [struct.unpack_from('<3f', data, off + 16 + i * 48) for i in range(nloop)]
                geo.append({'transfer': ti, 'nloop': nloop, 'prim': (lo >> 47) & 0x7ff,
                            'adc': [(struct.unpack_from('<I', data, off + 16 + (i * 3 + 2) * 16 + 12)[0] >> 15) & 1 for i in range(nloop)],
                            'stq': v})
            if flg == 0 and nreg == 1 and hi == 0xe and nloop == 3:
                pairs = [struct.unpack_from('<QQ', data, off + 16 + 16 * i) for i in range(3)]
                ad3.append({'transfer': ti, 'tag': lo, 'regs': [p[1] & 0xff for p in pairs], 'data': [p[0] for p in pairs]})
    return {'transfers': len(transfers), 'decompressed_sha256': dsha}, geo, ad3


def source_w(cars, code, i):
    d, hs = cars[code]; h = hs[i]; p = h['planes']['four_byte']
    return [d[p['offset'] + 4 * k + 3] for k in range(h['count'])]


def uv_error(cars, code, i, stq):
    d, hs = cars[code]; p = hs[i]['planes'].get('third_four_byte')
    if not p:
        return None
    uv = list(struct.iter_unpack('<hh', d[p['offset']:p['end']]))
    err = 0.0
    for (s, t, q), (u, v) in zip(stq, uv):
        if q == 0.0:
            return float('inf')
        err = max(err, abs(s / q - u / 2048), abs(t / q - v / 2048))
    return err


def main():
    _, cars = vb.load_sources()
    ident, geo, ad3 = parse_dump()
    mem = vb.CAPTURES['race94'].read_bytes()
    base = vb.cobra_base(mem, cars)[0]
    markers, i = [], -1
    pat = vb.U32.pack(vb.MARK_A)
    while True:
        i = mem.find(pat, i + 1)
        if i < 0: break
        markers.append(i)
    blocks = [vb.parse_a(mem, m) for m in markers]
    joined = []
    for b in blocks:
        j = vb.source_join(mem, b, cars, vb.plane_index(cars), base)
        cands = [(c['car'], c['header']) for c in j['byte_equal_candidates']]
        assert len(cands) == 1
        code, hi = cands[0]
        w = source_w(cars, code, hi)
        key_cands = [(c, k) for c, (d, hs) in cars.items() for k, h in enumerate(hs)
                     if h['count'] == b['count'] and source_w(cars, c, k) == w]
        tags = [g for g in geo if g['nloop'] == b['count'] and g['prim'] == b['prim'] and g['adc'] == w]
        rec = {'marker': hex(b['marker']), 'ring_page': 'A' if b['marker'] < 0x900000 else 'B', 'car': code, 'header': hi,
               'count': b['count'], 'prim': hex(b['prim']),
               'all_car_headers_with_same_count_and_W_sequence': len(key_cands),
               'dump_tags_matching_count_prim_ADC': [g['transfer'] for g in tags]}
        if b['ptr2'] is not None:
            rec['uv_max_abs_error_by_dump_tag'] = {str(g['transfer']): uv_error(cars, code, hi, g['stq']) for g in tags}
            other = [(c, k) for c, k in key_cands if (c, k) != (code, hi)]
            rec['uv_other_adc_candidates_matching_uv_1e-6'] = sorted({
                (c, k) for c, k in other for g in tags if (uv_error(cars, c, k, g['stq']) or 9) < 1e-6})
            rec['uv_other_adc_candidates_matching_uv_1e-6'] = [list(x) for x in rec['uv_other_adc_candidates_matching_uv_1e-6']]
            rec['uv_one_unit_mutation_rejected'] = all(
                max(abs(s / q - (u + 1) / 2048) for (s, t, q), (u, v) in zip(g['stq'], struct.iter_unpack(
                    '<hh', cars[code][0][cars[code][1][hi]['planes']['third_four_byte']['offset']:cars[code][1][hi]['planes']['third_four_byte']['end']]))) > 4e-4
                for g in tags)
        # negative control: one flipped ADC bit in the expectation must match nothing
        flip = list(w); flip[len(flip) // 2] ^= 1
        rec['control_one_ADC_bit_flipped_matches'] = len([g for g in geo if g['nloop'] == b['count'] and g['prim'] == b['prim'] and g['adc'] == flip])
        joined.append(rec)
    first = [r for r in joined if r['ring_page'] == 'A']
    seq_ok = []
    for r in first:
        seq_ok.append(r['dump_tags_matching_count_prim_ADC'])
    # B blocks (0021ba50 shape) vs A+D triples
    pat_b = vb.U32.pack(vb.MARK_B)
    bm, i = [], -1
    while True:
        i = mem.find(pat_b, i + 1)
        if i < 0: break
        bm.append(i)
    consts = vb.frame_consts(mem)
    bparsed = [vb.parse_b(mem, m, consts) for m in bm]
    key_b = sorted({(p['frame_1']['raw'], p['alpha_1_data'], p['test_1_data']) for p in bparsed})
    triples = [t for t in ad3 if t['regs'] == [0x4c, 0x42, 0x47] and t['tag'] == 0x1000000000008003]
    key_t = sorted({(t['data'][0], t['data'][1], t['data'][2]) for t in triples})
    follow = []
    for t in triples:
        nxt = next((g for g in geo if g['transfer'] > t['transfer']), None)
        follow.append({'ad_transfer': t['transfer'], 'next_geometry_transfer': nxt and nxt['transfer'],
                       'next_geometry_nloop': nxt and nxt['nloop'], 'next_geometry_prim': nxt and hex(nxt['prim'])})
    all_prim4c = [{'transfer': g['transfer'], 'nloop': g['nloop']} for g in geo if g['prim'] == 0x4c]
    receipt = {'scope': 'Content join between retained EE buffers and executed GSDump transfers; not same-frame execution proof.',
               'dump': {'path': str(DUMP.relative_to(ROOT)), 'compressed_sha256': DUMP_PIN, **ident,
                        'geometry_tags_desc_0x412': len(geo), 'ad_triples_frame_alpha_test': len(triples)},
               'retained_capture': {'path': 'research/evidence/continuation/runtime/race94-eeMemory.bin', 'sha256': vb.sha(mem)},
               'a_block_to_dump_tag': joined,
               'prim_0x4c_tags_in_dump': all_prim4c,
               'b_blocks_retained': len(bparsed), 'b_content_keys_retained': [[hex(a), b, hex(c)] for a, b, c in key_b],
               'dump_ad_triples': len(triples), 'dump_ad_content_keys': [[hex(a), b, hex(c)] for a, b, c in key_t],
               'b_key_sets_equal': key_b == key_t, 'ad_triple_following_geometry': follow}
    json.dump(receipt, open(OUT, 'w'), indent=1)
    print('wrote', OUT)


if __name__ == '__main__':
    main()
