#!/usr/bin/env python3
"""Deterministic receipt for retained FUN_00128e88 / FUN_0021ba50 output blocks in saved EE memory.

Scope: bytes retained in a saved EE image.  A match here proves a producer-shaped buffer and its
source-plane bindings; it does not prove that a CPU/VU path executed or that GIF transfer 5906 came
from it.  The decompilation is read only to pin literals; all comparisons are done here on bytes.
"""
import static_inputs
import hashlib
import json
import struct
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RT = ROOT / 'research/evidence/continuation/runtime'
SRC = static_inputs.bundle_path()
EXPORT = SRC / '.scratch/mesh/codex-audit/frontier-3845-01/types-t2/export-5454-po/decompilation/functions'
ELF = SRC / 'games/ford-racing-2/extracted/SLES_517.05'
CENSUS = ROOT / 'research/evidence/original-recovery/car-asset-census.json'
OUT = ROOT / 'research/evidence/packet-continuation/retained-packet-blocks.json'

CAPTURES = {
    'race94': RT / 'race94-eeMemory.bin',
    'race95': RT / 'linux/race95-eeMemory.bin',
    'race97': RT / 'linux/race97-eeMemory.bin',
    'menu98': RT / 'linux/menu98-eeMemory.bin',
}
CAPTURE_PINS = {  # eeMemory.bin member hashes recorded by the capture-identity receipts
    'race95': 'eacbcb2e8304957e35e784a927c4c17206ccef363c24eea6c1f6887f00f58355',
}
MARK_A = 0x6c058000   # FUN_00128e88 first VIF word after the DMA tag
MARK_B = 0x6c048003   # FUN_0021ba50 UNPACK V4-32 num4 addr3 TOPS
U32 = struct.Struct('<I')


def sha(b):
    return hashlib.sha256(b).hexdigest()


class Bad(Exception):
    pass


def words(mem, addr, n):
    if addr < 0 or addr + 4 * n > len(mem):
        raise Bad(f'bounds {addr:#x}+{4*n:#x}')
    return struct.unpack_from(f'<{n}I', mem, addr)


def need(cond, msg):
    if not cond:
        raise Bad(msg)


# ---------------------------------------------------------------- FUN_00128e88 blocks
def parse_a(mem, marker):
    """Parse one block exactly as laid out by FUN_00128e88; raise Bad on any deviation."""
    s = marker - 0xc
    need(s % 16 == 0, 'start not qword aligned')
    w = words(mem, s, 40)
    need(w[3] == MARK_A and w[1] == 0 and w[2] == 0, 'qword0 shape')
    need(w[0] == 0x10000005, f'dma tag {w[0]:#x}')                 # CNT, 5 qwords of data
    mask = w[8:12]
    need(len(set(mask)) == 1 and mask[0] <= 0xff, 'param8 mask lanes')
    gif_lo, gif_hi, regs, gif_pad = w[12:16]
    count = gif_lo & 0x7fff
    need(gif_lo >> 15 == 1, 'EOP/FLG/NLOOP shape')                 # EOP set, upper bits clear
    prim = (gif_hi >> 15) & 0x7ff
    need(gif_hi == (0x30004000 | (prim << 15)), f'gif hi {gif_hi:#x}')   # PRE, FLG0, NREG3
    need(prim in (0x4c, 0x5c) and regs == 0x412 and gif_pad == 0, 'prim/regs')
    need(w[16] == count and w[17] == 0 and w[19] == 0, 'count qword')
    addr = w[18]
    need(addr in (0x208, 0x2c8), f'unpack addr {addr:#x}')
    ref4_tag, ptr4, stc1, unp8 = w[24:28]
    need(ref4_tag == 0x30000000 + ((count * 4 + 0xf) >> 4), 'ref4 qwc')
    need(stc1 == 0x1000103 and unp8 == (0x6e000000 | count << 16 | (addr + 1)), 'unpack V4-8')
    need(w[28:32] == (0x10000001, 0, 0x1000103, 0x30000000) and w[32:36] == (0x44400000,) * 3 + (0,), 'row0')
    ref6_tag, ptr6, stm, unp16 = w[36:40]
    need(ref6_tag == 0x30000000 + ((count * 3 + 7) >> 3), 'ref6 qwc')
    need(stm == 0x5000001 and unp16 == (0x69000000 | count << 16 | addr), 'unpack V3-16')
    pos = s + 160
    ptr2 = None
    nxt = words(mem, pos, 4)
    if nxt == (0x10000001, 0, 0x1000103, 0x30000000):
        a = words(mem, pos + 16, 8)
        need(a[0:4] == (0x45c00000, 0x45c00000, 0, 0), 'row1')
        ref2_tag, ptr2, st5, unp2 = a[4:8]
        need(ref2_tag == 0x30000000 + ((count * 2 + 7) >> 3) and st5 == 0x5000001, 'ref2 shape')
        need(unp2 == (0x65000000 | count << 16 | (addr + 2)), 'unpack V2-16')
        pos += 48
    t = words(mem, pos, 12)
    need(t[0:4] == (0x10000002, 0, 0x5000000, 0) and t[4:8] == (0, 0, 0x1000404, 0x17000000), 'tail')
    need(t[8] in (0x30003aa, 0x3000388) and t[9] == 0x2000000 and t[10] == 0 and t[11] == 0, 'base tail')
    end = pos + 48
    for name, p, n in (('ptr6', ptr6, count * 6), ('ptr4', ptr4, count * 4), ('ptr2', ptr2, count * 4)):
        if p is None:
            continue
        need(p & 0xf0000000 == 0 and p % 16 == 0 and p + n <= len(mem), f'{name} {p:#x}')
    return {'marker': marker, 'start': s, 'end': end, 'qwords': (end - s) // 16, 'count': count,
            'param8_mask': mask[0], 'prim': prim, 'unpack_addr': addr, 'base_word': t[8],
            'ptr6': ptr6, 'ptr4': ptr4, 'ptr2': ptr2,
            'prim_tme_matches_v2_plane_presence': (prim == 0x5c) == (ptr2 is not None)}


def pair_diff(mem, a, b):
    wa = words(mem, a['start'], a['qwords'] * 4)
    wb = words(mem, b['start'], b['qwords'] * 4)
    return [i for i in range(len(wa)) if wa[i] != wb[i]]


# ---------------------------------------------------------------- FUN_0021ba50 blocks
def parse_b(mem, marker, frame_consts):
    s = marker - 0xc
    w = words(mem, s, 4 + 20)
    need(w[3] == MARK_B, 'marker')
    g = w[4:24]
    need(g[0:4] == (0x8003, 0x10000000, 0xe, 0), 'gif tag 0x1000000000008003 / A+D')
    fr = (g[4], g[5]); need(g[6] == 0x4c and g[7] == 0, 'FRAME_1 address 0x4c')
    need(g[10] == 0x42 and g[11] == 0 and g[9] == 0, 'ALPHA_1 address 0x42')
    need(g[14] == 0x47 and g[15] == 0 and g[13] == 0, 'TEST_1 address 0x47')
    alpha = g[8]
    test = g[12]
    need(test in (0x30000, 0x50000), 'TEST data')
    fbp, fbw, psm = fr[0] & 0x1ff, (fr[0] >> 16) & 0x3f, (fr[0] >> 24) & 0x3f
    frame = {'raw': (fr[1] << 32) | fr[0], 'FBP': fbp, 'FBW': fbw, 'PSM': psm, 'FBMSK': fr[1],
             'equals_current_DAT_002324f4_f6_f8': (fbp, fbw, psm) == (frame_consts['FBP'], frame_consts['FBW'], frame_consts['PSM'])}
    tail = words(mem, s + 16 + 64, 4)
    vif = {0x14: 'MSCAL', 0x17: 'MSCNT', 0x03: 'BASE', 0x02: 'OFFSET', 0x00: 'NOP', 0x6c: 'UNPACK_V4_32'}
    decoded = [(vif.get(x >> 24, hex(x >> 24)) + ':' + hex(x & 0xffffff)) if x else 'zero' for x in tail]
    return {'marker': marker, 'start': s, 'frame_1': frame, 'alpha_1_data': alpha, 'test_1_data': test,
            'following_qword': list(tail), 'following_decoded_if_vif_code_words': decoded}


# ---------------------------------------------------------------- source joins
def load_sources():
    census = json.loads(CENSUS.read_text())
    cars = {}
    for c in census['cars']:
        p = next((ROOT / 'ford-racing-2/cars' / c['code'] / 'model').iterdir())
        d = p.read_bytes()
        need(sha(d) == c['sha256'], f"source identity {c['code']}")
        cars[c['code']] = (d, c['geometry']['headers'])
    return census, cars


def plane_index(cars):
    idx = {}
    for code, (d, hs) in cars.items():
        for i, h in enumerate(hs):
            pl = h['planes']
            key = (h['count'], sha(d[pl['six_byte']['offset']:pl['six_byte']['end']]),
                   sha(d[pl['four_byte']['offset']:pl['four_byte']['end']]))
            idx.setdefault(key, []).append((code, i))
    return idx


def source_join(mem, blk, cars, pidx, base):
    n = blk['count']
    six = mem[blk['ptr6']:blk['ptr6'] + 6 * n]
    four = mem[blk['ptr4']:blk['ptr4'] + 4 * n]
    key = (n, sha(six), sha(four))
    byte_cands = pidx.get(key, [])
    pos = []
    for code, (d, hs) in cars.items():
        for i, h in enumerate(hs):
            pl = h['planes']
            if code == 'COBRA' and base is not None and blk['ptr6'] - base == pl['six_byte']['offset'] \
                    and blk['ptr4'] - base == pl['four_byte']['offset'] and h['count'] == n:
                pos.append((code, i))
    out = {'byte_equal_candidates': [{'car': c, 'header': i} for c, i in byte_cands],
           'positional_candidates_at_base': [{'car': c, 'header': i} for c, i in pos]}
    if blk['ptr2'] is not None:
        two = mem[blk['ptr2']:blk['ptr2'] + 4 * n]
        out['v2_16_bytes_sha256'] = sha(two)
        refined = []
        for c, i in byte_cands:
            d, hs = cars[c]
            pl = hs[i]['planes'].get('third_four_byte')
            refined.append({'car': c, 'header': i, 'third': hs[i]['third'],
                            'third_plane_equal': bool(pl and d[pl['offset']:pl['end']] == two)})
        out['third_plane_checks'] = refined
    return out


def cobra_base(mem, cars):
    """Independent base: locate the full COBRA six-byte plane of header 0 in EE and demand uniqueness."""
    d, hs = cars['COBRA']
    pl = hs[0]['planes']['six_byte']
    probe = d[pl['offset']:pl['end']]
    hits, i = [], -1
    while True:
        i = mem.find(probe, i + 1)
        if i < 0:
            break
        hits.append(i)
    return [h - pl['offset'] for h in hits]


def frame_consts(mem):
    g = lambda a: struct.unpack_from('<H', mem, a)[0]   # DAT_002324f4/6/8 read by FUN_0021ba50
    return {'PSM': g(0x2324f4), 'FBP': g(0x2324f6), 'FBW': g(0x2324f8)}


def run_capture(name, path, cars, pidx, ctrl):
    mem = path.read_bytes()
    consts = frame_consts(mem)
    rec = {'capture': name, 'path': str(path.relative_to(ROOT)), 'bytes': len(mem), 'sha256': sha(mem),
           'frame_consts_from_this_capture': consts}
    pin = CAPTURE_PINS.get(name)
    if pin:
        rec['sha256_pin_match'] = (pin == rec['sha256'])
        need(pin == rec['sha256'], f'{name} capture hash differs from pin')
    base = cobra_base(mem, cars)
    rec['cobra_file_base_candidates'] = base
    base = base[0] if len(base) == 1 else None
    hitsA, hitsB, i = [], [], -1
    for m, out in ((MARK_A, hitsA), (MARK_B, hitsB)):
        i = -1
        pat = U32.pack(m)
        while True:
            i = mem.find(pat, i + 1)
            if i < 0:
                break
            out.append(i)
    rec['raw_marker_counts'] = {'0x6c058000': len(hitsA), '0x6c048003': len(hitsB)}
    rec['unaligned_hits'] = [hex(h) for h in hitsA + hitsB if h % 4]
    blocks, rejects = [], []
    for h in hitsA:
        try:
            b = parse_a(mem, h)
            b['join'] = source_join(mem, b, cars, pidx, base)
            blocks.append(b)
        except Bad as e:
            rejects.append({'marker': hex(h), 'reason': str(e)})
    rec['a_blocks'] = [{k: (hex(v) if k in ('marker', 'start', 'end', 'ptr6', 'ptr4', 'ptr2', 'base_word') and v is not None else v)
                        for k, v in b.items()} for b in blocks]
    rec['a_rejects'] = rejects
    # contiguity within a ring page
    gaps = []
    for x, y in zip(blocks, blocks[1:]):
        gaps.append({'from': hex(x['marker']), 'to': hex(y['marker']), 'gap_bytes': y['start'] - x['end']})
    rec['a_contiguity'] = gaps
    brs, bj = [], []
    for h in hitsB:
        try:
            brs.append(parse_b(mem, h, consts))
        except Bad as e:
            bj.append({'marker': hex(h), 'reason': str(e)})
    rec['b_blocks'] = brs
    rec['b_rejects'] = bj
    if ctrl and name == 'race95':
        rec['controls'] = controls(mem, blocks, cars, pidx, base, consts, hitsB)
    return rec, mem, blocks


def controls(mem, blocks, cars, pidx, base, consts, hitsB):
    out = {}
    m = bytearray(mem)
    first = blocks[0]
    # 1: marker/word corruption is rejected by the parser
    rej = {}
    for label, off in (('marker', first['marker']), ('dma_tag', first['start']), ('gif_hi', first['start'] + 52),
                       ('unpack_addr', first['start'] + 72), ('ref4_tag', first['start'] + 96),
                       ('row0', first['start'] + 128), ('tail_cnt', first['end'] - 48)):
        old = m[off:off + 4]
        m[off:off + 4] = U32.pack(U32.unpack(old)[0] ^ 0x1)
        try:
            parse_a(bytes(m), first['marker']); rej[label] = 'ACCEPTED'
        except Bad as e:
            rej[label] = 'rejected: ' + str(e)
        m[off:off + 4] = old
    out['word_corruption'] = rej
    # 2: one-bit change inside a referenced plane must break the byte join
    n = first['count']
    old = m[first['ptr6']]; m[first['ptr6']] ^= 1
    mut = source_join(bytes(m), first, cars, pidx, base)
    out['plane_bit_flip_six'] = {'byte_equal_candidates': len(mut['byte_equal_candidates'])}
    m[first['ptr6']] = old
    old = m[first['ptr4'] + 1]; m[first['ptr4'] + 1] ^= 1
    mut = source_join(bytes(m), first, cars, pidx, base)
    out['plane_bit_flip_four'] = {'byte_equal_candidates': len(mut['byte_equal_candidates'])}
    m[first['ptr4'] + 1] = old
    # 3: wrong source base shifts must not match positionally
    shifts = {}
    for d in (-16, 16, 0x1000):
        r = source_join(mem, first, cars, pidx, base + d if base is not None else None)
        shifts[str(d)] = len(r['positional_candidates_at_base'])
    out['base_shift_positional_matches'] = shifts
    # 4: another car's source does not reproduce the same planes
    others = {}
    for code, (d, _hs) in cars.items():
        if code == 'COBRA':
            continue
        six = mem[first['ptr6']:first['ptr6'] + 6 * n]
        others[code] = d.find(six) >= 0
    out['other_car_six_plane_contains_probe'] = {'cars_with_match': sorted(k for k, v in others.items() if v),
                                                 'cars_tested': len(others)}
    # 5: truncated memory / bad pointer
    try:
        parse_a(mem[:first['end'] - 8], first['marker']); out['truncated'] = 'ACCEPTED'
    except Bad as e:
        out['truncated'] = 'rejected: ' + str(e)
    # 6: parser sanity vs a non-marker address
    try:
        parse_a(mem, first['marker'] + 16); out['shifted_marker'] = 'ACCEPTED'
    except Bad as e:
        out['shifted_marker'] = 'rejected: ' + str(e)
    # 7: frame constant control for B
    if hitsB:
        for label, wi in (('gif_tag', 4), ('frame_addr', 10), ('alpha_addr', 14), ('test_addr', 18)):
            off = hitsB[0] - 0xc + 4 * wi
            old = m[off:off + 4]
            m[off:off + 4] = U32.pack(U32.unpack(old)[0] ^ 0x1)
            try:
                parse_b(bytes(m), hitsB[0], consts); out['B_' + label + '_corrupted'] = 'ACCEPTED'
            except Bad as e:
                out['B_' + label + '_corrupted'] = 'rejected: ' + str(e)
            m[off:off + 4] = old
    return out


def main():
    _, cars = load_sources()
    pidx = plane_index(cars)
    elf = ELF.read_bytes()
    mem95 = CAPTURES['race95'].read_bytes()
    src_pins = {}
    for fn in ('00128e88', '0021ba50', '0021c3e0'):
        t = (EXPORT / f'{fn}.c').read_bytes()
        src_pins[fn] = sha(t)
    txt = (EXPORT / '00128e88.c').read_text()
    lits = ['0x6c058000', '0x412', '0x44400000', '0x45c00000', '0x1000103', '0x5000001', '0x69000000',
            '0x6e000000', '0x65000000', '0x1000404', '0x17000000', '0x30003aa', '0x3000388', '0x2c8', '0x208', '0x10000005']
    lits = [l for l in lits if l != '0x10000005']  # derived from (end-start) arithmetic, not a literal
    missing = [l for l in lits if l not in txt]
    txt2 = (EXPORT / '0021ba50.c').read_text()
    lits2 = ['0x1000000000008003', '0xe', '0x4c', '0x42', '0x47', '0x40000', '0x48000', '0x6c000000']
    missing2 = [l for l in lits2 if l not in txt2]
    receipt = {'scope': 'Retained EE buffer receipt; no execution or GIF-transfer claim.',
               'source_head_note': 'source export bytes pinned below; checkout read-only',
               'elf_sha256': sha(elf), 'source_function_sha256': src_pins,
               'source_literal_missing_00128e88': missing, 'source_literal_missing_0021ba50': missing2,
               'census_sha256': sha(CENSUS.read_bytes()),
               'captures': []}
    need(not missing and not missing2, 'source literal pins failed')
    for name, path in CAPTURES.items():
        rec, _, _ = run_capture(name, path, cars, pidx, ctrl=True)
        receipt['captures'].append(rec)
    # race95 pair analysis
    mem = mem95
    rec95 = next(c for c in receipt['captures'] if c['capture'] == 'race95')
    blocks = [parse_a(mem, int(b['marker'], 16)) for b in rec95['a_blocks']]
    half = len(blocks) // 2
    pairs = []
    for a, b in zip(blocks[:half], blocks[half:]):
        d = pair_diff(mem, a, b)
        pairs.append({'a': hex(a['marker']), 'b': hex(b['marker']), 'same_length': a['qwords'] == b['qwords'],
                      'differing_word_indices': d, 'same_pointers': (a['ptr6'], a['ptr4'], a['ptr2']) == (b['ptr6'], b['ptr4'], b['ptr2'])})
    receipt['race95_pairs'] = pairs
    json.dump(receipt, open(OUT, 'w'), indent=1)
    print('wrote', OUT)


if __name__ == '__main__':
    main()
