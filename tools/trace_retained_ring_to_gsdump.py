#!/usr/bin/env python3
"""Walk the retained EE DMA chain (ring page A) and align its draw descriptors with the race94 GSDump.

Evidence level: a deterministic content alignment between a saved EE display list and an executed GIF
transfer sequence from a separate capture of the same paused scene.  Nothing here executes game code.
"""
import difflib
import hashlib
import json
import random
import struct

import join_retained_blocks_to_gsdump as gj
import validate_retained_packet_blocks as vb

ROOT = vb.ROOT
OUT = ROOT / 'research/evidence/packet-continuation/retained-ring-gsdump-alignment.json'
CHAIN_START = {'A': 0x814880}
MEM_PIN = vb.CAPTURE_PINS['race95']


def walk_chain(mem, a):
    els = []
    while True:
        lo, hi, v0, v1 = struct.unpack_from('<4I', mem, a)
        idv, qwc = (lo >> 28) & 7, lo & 0xffff
        el = {'addr': a, 'id': idv, 'qwc': qwc, 'hi': hi, 'v0': v0, 'v1': v1}
        if idv == 1:
            el['data'] = [struct.unpack_from('<4I', mem, a + 16 + 16 * i) for i in range(qwc)]
            els.append(el); a += 16 + 16 * qwc
        elif idv == 3:
            els.append(el); a += 16
        elif idv == 7:
            els.append(el); return els, 'END', a + 16 + 16 * qwc
        else:
            return els, 'BAD', a


def car_bases(mem, cars):
    out = {}
    for code, (d, hs) in cars.items():
        for h in hs[:3]:
            p = h['planes']['six_byte']
            probe = d[p['offset']:p['end']]
            if len(probe) < 48:
                continue
            hits, i = [], -1
            while True:
                i = mem.find(probe, i + 1)
                if i < 0: break
                hits.append(i - p['offset'])
            if len(set(hits)) == 1:
                out[code] = hits[0]; break
    return out


def header_for(cars, bases, ptr6, ptr4, count):
    r = []
    for code, base in bases.items():
        for k, h in enumerate(cars[code][1]):
            if h['count'] == count and base + h['planes']['six_byte']['offset'] == ptr6 and base + h['planes']['four_byte']['offset'] == ptr4:
                r.append((code, k))
    return r


def parse_calls(els):
    """Group chain elements into FUN_00128e88 blocks and FUN_0021c3e0 calls; return draw descriptors in chain order."""
    draws, i = [], 0
    pend = None
    def ref_info(e):
        u = e['v1']
        return {'ptr': e['hi'], 'kind': {0x69: 'V3_16', 0x65: 'V2_16', 0x6e: 'V4_8'}.get(u >> 24), 'count': (u >> 16) & 0xff, 'addr': u & 0x3ff}
    while i < len(els):
        e = els[i]
        # C head: CNT(STCYCL,STROW)+row 0x44400000 then REF V3_16
        if e['id'] == 1 and e['qwc'] == 1 and (e['v0'], e['v1']) == (0x1000103, 0x30000000) and e['data'][0] == (0x44400000,) * 3 + (0,) \
                and i + 1 < len(els) and els[i + 1]['id'] == 3 and els[i + 1]['v0'] == 0x5000001 and els[i + 1]['v1'] >> 24 == 0x69:
            r6 = ref_info(els[i + 1]); j = i + 2; r2 = None; r4 = None; arm = None; row = None
            if els[j]['id'] == 1 and els[j]['qwc'] == 1 and els[j]['data'][0][0] == 0x45c00000 and els[j + 1]['v1'] >> 24 == 0x65:
                r2 = ref_info(els[j + 1]); j += 2
            if els[j]['id'] == 1 and els[j]['qwc'] == 1 and els[j]['v1'] == 0x30000000 and els[j]['data'][0][0] == 0x47c00000 and els[j + 1]['v1'] >> 24 == 0x6e:
                arm, row, r4 = 'bit8_clear_row_0x47c00000', 0x47c00000, ref_info(els[j + 1]); j += 2
            elif els[j]['id'] == 3 and els[j]['v0'] == 0x5000000 and els[j]['v1'] >> 24 == 0x6e:
                arm, r4 = 'bit8_set_direct_ref', ref_info(els[j]); j += 1
            if r4 is None or r4['count'] != r6['count']:
                i += 1; continue
            pend = {'head_addr': e['addr'], 'arm': arm, 'ptr6': r6['ptr'] & 0xfffffff, 'ptr4': r4['ptr'] & 0xfffffff,
                    'ptr2': r2 and r2['ptr'] & 0xfffffff, 'count': r6['count'], 'addr': r6['addr']}
            # bb48 passes live in the next CNT element(s) until the next head/A block
            k = j
            while k < len(els) and els[k]['id'] == 1:
                if k > j and els[k]['qwc'] == 1 and (els[k]['v0'], els[k]['v1']) == (0x1000103, 0x30000000):
                    break
                dq = els[k]['data']
                for qi in range(len(dq) - 3):
                    if dq[qi][3] & 0xffffff0f == 0x6c038000 and dq[qi + 3][2] == 0x412 and dq[qi + 3][3] == 0:
                        gl, gh = dq[qi + 3][0], dq[qi + 3][1]
                        draws.append({'kind': 'FUN_0021c3e0+0021bb48', 'chain_addr': els[k]['addr'] + 16 * (qi + 1), **pend,
                                      'pass_id': dq[qi + 1][0], 'nloop': gl & 0x7fff, 'prim': (gh >> 15) & 0x7ff,
                                      'effective_flags': dq[qi + 1][3], 'vec4_u32': list(dq[qi + 2])})
                k += 1
            i = j; continue
        # A block (FUN_00128e88): CNT qwc5 with marker 0x6c058000 in tag v1
        if e['id'] == 1 and e['qwc'] == 5 and e['v1'] == vb.MARK_A:
            g = e['data'][2]
            draws.append({'kind': 'FUN_00128e88', 'chain_addr': e['addr'], 'nloop': g[0] & 0x7fff, 'prim': (g[1] >> 15) & 0x7ff,
                          'a_block_marker': e['addr'] + 12, 'count': e['data'][3][0]})
        i += 1
    return draws


def gif_addr(d):
    return d['a_block_marker'] - 12 + 16 * 3 if d['kind'] == 'FUN_00128e88' else d['chain_addr'] + 16 * 3


def add_variant_draws(els, draws, cars, bases, mem):
    """Add draw tags not produced by a recognised FUN_00128e88/0021c3e0 head (texture-pass variants)."""
    seen = {gif_addr(d) for d in draws}
    out = list(draws)
    for idx, e in enumerate(els):
        if e['id'] != 1:
            continue
        for q, (lo, hi, w2, w3) in enumerate(e['data']):
            qa = e['addr'] + 16 * (q + 1)
            if w2 == 0x412 and w3 == 0 and (hi & 0xf0000000) == 0x30000000 and lo & 0x8000 and qa not in seen:
                n = lo & 0x7fff
                ptr2 = None
                for back in range(idx, max(idx - 14, 0), -1):
                    b = els[back]
                    if b['id'] == 3 and b['v1'] >> 24 == 0x65 and ((b['v1'] >> 16) & 0xff) == n:
                        ptr2 = b['hi'] & 0xfffffff; break
                hdr = []
                if ptr2 is not None:
                    for code, base in bases.items():
                        for k, h in enumerate(cars[code][1]):
                            pl = h['planes'].get('third_four_byte')
                            if pl and h['count'] == n and base + pl['offset'] == ptr2:
                                hdr.append((code, k))
                out.append({'kind': 'texture_pass_variant', 'chain_addr': qa - 16 * 3, 'nloop': n, 'prim': (hi >> 15) & 0x7ff,
                            'ptr2': ptr2, 'ptr6': None, 'ptr4': None, 'source_headers_via_v2_16_plane': hdr})
    out.sort(key=gif_addr)
    return out


def main():
    _, cars = vb.load_sources()
    mem = vb.CAPTURES['race95'].read_bytes()
    assert hashlib.sha256(mem).hexdigest() == MEM_PIN
    bases = car_bases(mem, cars)
    els, status, end = walk_chain(mem, CHAIN_START['A'])
    draws = parse_calls(els)
    draws = add_variant_draws(els, draws, cars, bases, mem)
    # source join per draw
    for d in draws:
        if d['kind'] == 'FUN_00128e88':
            b = vb.parse_a(mem, d['a_block_marker'])
            d.update({'ptr6': b['ptr6'], 'ptr4': b['ptr4'], 'ptr2': b['ptr2']})
        if d['ptr6'] is None:
            d['source_headers'] = []
            d['expected_w'] = None
            continue
        d['source_headers'] = header_for(cars, bases, d['ptr6'], d['ptr4'], d['nloop'])
        n = d['nloop']
        d['expected_w'] = list(mem[d['ptr4'] + 3:d['ptr4'] + 4 * n:4])
    _, geo, _ = gj.parse_dump()
    ra = [(d['nloop'], d['prim']) for d in draws]
    da = [(g['nloop'], g['prim']) for g in geo]
    sm = difflib.SequenceMatcher(None, ra, da, autojunk=False)
    blocks = [b for b in sm.get_matching_blocks() if b.size]
    matched = sum(b.size for b in blocks)
    pairs = []
    for b in blocks:
        for k in range(b.size):
            pairs.append((b.a + k, b.b + k))
    wpairs = [(ai, bi) for ai, bi in pairs if draws[ai]['expected_w'] is not None]
    adc_equal = sum(1 for ai, bi in wpairs if draws[ai]['expected_w'] == geo[bi]['adc'])
    adc_superset = sum(1 for ai, bi in wpairs if all(x <= y for x, y in zip(draws[ai]['expected_w'], geo[bi]['adc'])))
    violations = [[ai, geo[bi]['transfer']] for ai, bi in wpairs if not all(x <= y for x, y in zip(draws[ai]['expected_w'], geo[bi]['adc']))]
    long_blocks = [b for b in blocks if b.size >= 8]
    rng = random.Random(5)
    shuffled = list(da); rng.shuffle(shuffled)
    controls = {}
    for label, seq in (('reversed_dump_sequence', da[::-1]), ('shuffled_dump_sequence', shuffled)):
        m = difflib.SequenceMatcher(None, ra, seq, autojunk=False).get_matching_blocks()
        controls[label] = {'matched_tags': sum(b.size for b in m), 'longest_block': max(b.size for b in m)}
    rotated = sum(1 for ai, bi in wpairs if all(x <= y for x, y in zip(draws[ai]['expected_w'], geo[bi]['adc'][1:] + geo[bi]['adc'][:1])))
    controls['adc_rotated_one_vertex_superset_pairs'] = rotated
    controls['adc_rotated_one_vertex_note'] = 'same pairs and W planes, dumped ADC bits rotated by one vertex; the subset property should mostly fail'
    # alpha: vec4 w float vs dump RGBAQ alpha is checked separately by the caller; record vec4 for later joins
    receipt = {
        'scope': 'Content alignment of a saved EE DMA chain with an executed GSDump transfer sequence; not same-frame execution proof.',
        'capture': {'path': 'research/evidence/continuation/runtime/linux/race95-eeMemory.bin', 'sha256': MEM_PIN},
        'dump': {'path': str(gj.DUMP.relative_to(ROOT)), 'compressed_sha256': gj.DUMP_PIN, 'geometry_tags': len(geo)},
        'chain': {'start': hex(CHAIN_START['A']), 'status': status, 'end': hex(end), 'elements': len(els)},
        'car_bases_in_ee': {k: hex(v) for k, v in bases.items()},
        'retained_draw_descriptors': len(draws),
        'kinds': {k: sum(1 for d in draws if d['kind'] == k) for k in sorted({d['kind'] for d in draws})},
        'draws_with_unique_source_header': sum(1 for d in draws if len(d.get('source_headers', [])) == 1),
        'draws_without_positional_header': sum(1 for d in draws if not d.get('source_headers')),
        'alignment': {'matched_tags': matched, 'blocks': len(blocks), 'blocks_ge8': len(long_blocks),
                      'longest_block': max(b.size for b in blocks), 'retained_unmatched': len(draws) - matched,
                      'controls': controls, 'pairs_with_source_W_plane': len(wpairs), 'adc_equals_source_W': adc_equal,
                      'adc_superset_of_source_W': adc_superset, 'adc_subset_violations_retained_idx_transfer': violations},
        'draws': [{k: (list(v) if isinstance(v, tuple) else v) for k, v in d.items()} for d in draws],
        'matched_pairs': [[ai, geo[bi]['transfer']] for ai, bi in pairs],
    }
    json.dump(receipt, open(OUT, 'w'), indent=1)
    print({k: receipt[k] for k in ('chain', 'car_bases_in_ee', 'retained_draw_descriptors', 'kinds', 'draws_with_unique_source_header', 'draws_without_positional_header', 'alignment')})


if __name__ == '__main__':
    main()
