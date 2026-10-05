#!/usr/bin/env python3
"""Join menu98 visible challenge-theme thumbnails to GS sprite draws, GS uploads and source CHALL PTG tiles.

Chain per tile: screenshot pixels <- GS sprite (TEX0 TBP0, UV, XY) <- last IMAGE upload to that block
<- exact 4,096-byte substring of a GRAPHICS/GAME/CHALL/*.ptg;1 file.  The screenshot mapping is fitted on
one half of the tiles and tested on the held-out half, with shifted-mapping and swapped-tile controls.
"""
import collections
import hashlib
import json
import struct
import zlib

import gsdump
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
GAME = ROOT.parents[1] / 'reverse-engineering/games/ford-racing-2/extracted/files'
DUMP = ROOT / 'research/evidence/continuation/runtime/linux/snaps/Ford Racing 2_SLES-51705_20261005010217.gs.zst'
DUMP_PIN = '126c9a909501d157d5bab5359a66c63cbb6966bf70504e3f671a9ede5ee01ae9'
SHOT = ROOT / 'research/evidence/continuation/runtime/linux/menu98-Screenshot.png'
SHOT_PIN = '30c6c73f1815f9aff40469934a4109d6e504406ed152ab577d9f33acd91da63a'
OUT = ROOT / 'research/evidence/ptg-continuation/menu98-sprite-ptg-join.json'


def sha(b):
    return hashlib.sha256(b).hexdigest()


def read_png(path):
    d = path.read_bytes()
    pos, idat, w = 8, b'', None
    while pos < len(d):
        n, kind = struct.unpack_from('>I4s', d, pos)
        body = d[pos + 8:pos + 8 + n]
        if kind == b'IHDR':
            w, h, depth, ctype, _, _, inter = struct.unpack('>IIBBBBB', body)
            assert depth == 8 and ctype == 6 and inter == 0
        elif kind == b'IDAT':
            idat += body
        pos += 12 + n
    raw = zlib.decompress(idat)
    stride = w * 4
    out = bytearray(h * stride)
    prev = bytearray(stride)
    p = 0
    for y in range(h):
        f = raw[p]; line = bytearray(raw[p + 1:p + 1 + stride]); p += 1 + stride
        for i in range(stride):
            a = line[i - 4] if i >= 4 else 0
            b = prev[i]
            c = prev[i - 4] if i >= 4 else 0
            if f == 1: line[i] = (line[i] + a) & 255
            elif f == 2: line[i] = (line[i] + b) & 255
            elif f == 3: line[i] = (line[i] + ((a + b) >> 1)) & 255
            elif f == 4:
                pa, pb, pc = abs(b - c), abs(a - c), abs(a + b - 2 * c)
                pr = a if pa <= pb and pa <= pc else (b if pb <= pc else c)
                line[i] = (line[i] + pr) & 255
        out[y * stride:(y + 1) * stride] = line; prev = line
    return w, h, bytes(out)


def parse_dump():
    tr, _ = gsdump.load_transfers(DUMP, DUMP_PIN)
    S, uploads, sprites, pend = {}, [], [], []
    for ti, data in enumerate(tr):
        for off, lo, hi, nloop, flg, nreg, pl in gsdump.iter_tags(data):
            if flg == 2:
                bb, trx = S.get(0x50, 0), S.get(0x52, 0)
                uploads.append({'transfer': ti, 'dbp': (bb >> 32) & 0x3fff, 'dbw': (bb >> 48) & 0x3f, 'psm': (bb >> 56) & 0x3f,
                                'w': trx & 0xfff, 'h': (trx >> 32) & 0xfff, 'payload': data[off + 16:off + 16 + pl]})
            if flg == 0:
                regs = [(hi >> (4 * i)) & 15 for i in range(nreg)]
                if (lo >> 46) & 1: S['prim'] = (lo >> 47) & 0x7ff
                cur = {}
                for i in range(nloop):
                    for j, r in enumerate(regs):
                        q = data[off + 16 + (i * nreg + j) * 16:off + 16 + (i * nreg + j + 1) * 16]
                        w = struct.unpack('<4I', q)
                        if r == 0xe:
                            S[q[8]] = struct.unpack('<Q', q[:8])[0]
                            if q[8] == 0: S['prim'] = S[0]
                        elif r == 0: S['prim'] = w[0] & 0x7ff
                        elif r == 3: cur['uv'] = (w[0] & 0x3fff, w[1] & 0x3fff)
                        elif r == 1: cur['rgba'] = tuple(x & 0xff for x in w)
                        elif r == 5 and not (w[3] >> 15) & 1 and (S.get('prim', 0) & 7) == 6:
                            cur['xy'] = (w[0] & 0xffff, w[1] & 0xffff)
                            pend.append(dict(cur))
                            if len(pend) == 2:
                                prim = S.get('prim', 0); c = (prim >> 9) & 1
                                sprites.append({'transfer': ti, 'tme': (prim >> 4) & 1, 'abe': (prim >> 6) & 1, 'tex0': S.get(6 + c, 0),
                                                'xyoffset': S.get(0x18 + c, 0), 'frame': S.get(0x4c + c, 0), 'alpha': S.get(0x42 + c, 0),
                                                'test': S.get(0x47 + c, 0), 'verts': pend})
                                pend = []
    return tr, uploads, sprites


def ptg_index():
    files = {}
    for f in sorted(GAME.rglob('*.ptg*')):
        files[f.relative_to(GAME).as_posix()] = f.read_bytes()
    return files


def tile_rgba_bytes(payload):
    return payload  # PSMCT32 host upload is already R,G,B,A byte order per pixel


def main():
    shot_w, shot_h, shot = read_png(SHOT)
    assert sha(SHOT.read_bytes()) == SHOT_PIN
    _, uploads, sprites = parse_dump()
    files = ptg_index()
    # latest upload before each sprite (last write wins for a DBP)
    by_dbp = collections.defaultdict(list)
    for u in uploads:
        by_dbp[u['dbp']].append(u)
    rows = []
    for si, s in enumerate(sprites):
        t0 = s['tex0']; tbp = t0 & 0x3fff; psm = (t0 >> 20) & 0x3f; tw, th = (t0 >> 26) & 15, (t0 >> 30) & 15
        if not s['tme'] or psm not in (0, 0x13) or tw != th or tw > 6:
            continue
        side = 1 << tw
        ups = [u for u in by_dbp.get(tbp, []) if u['transfer'] < s['transfer'] and u['psm'] == psm and (u['w'], u['h']) == (side, side)]
        if not ups: continue
        u = ups[-1]
        if len(u['payload']) != side * side * (4 if psm == 0 else 1): continue
        hit = [(fn, b.find(u['payload'])) for fn, b in files.items() if b.find(u['payload']) >= 0]
        if not hit: continue
        clut = None
        if psm == 0x13:
            cbp = (t0 >> 37) & 0x3fff
            cl = [c for c in by_dbp.get(cbp, []) if c['transfer'] < s['transfer'] and c['psm'] == 0 and (c['w'], c['h']) == (16, 16)]
            if not cl: continue
            clut = cl[-1]['payload']
        v0, v1 = s['verts']
        ofx, ofy = s['xyoffset'] & 0xffff, (s['xyoffset'] >> 32) & 0xffff
        tex0 = {'TBP0': tbp, 'TBW': (t0 >> 14) & 0x3f, 'PSM': psm, 'TW': tw, 'TH': th, 'TCC': (t0 >> 34) & 1, 'TFX': (t0 >> 35) & 3,
                'CBP': (t0 >> 37) & 0x3fff, 'CPSM': (t0 >> 51) & 15, 'CSM': (t0 >> 55) & 1, 'CSA': (t0 >> 56) & 31, 'CLD': (t0 >> 61) & 7}
        rows.append({'tex0_decoded': tex0, 'sprite_index': si, 'transfer': s['transfer'], 'tbp0': tbp, 'psm': psm, 'side': side, 'tbw': (t0 >> 14) & 0x3f, 'upload_dbw': u['dbw'],
                     'upload_transfer': u['transfer'], 'ptg': [(fn, off) for fn, off in hit], 'uv': [v0['uv'], v1['uv']],
                     'xy_px': [((v0['xy'][0] - ofx) / 16, (v0['xy'][1] - ofy) / 16), ((v1['xy'][0] - ofx) / 16, (v1['xy'][1] - ofy) / 16)],
                     'rgba': v0['rgba'], 'tex0': hex(t0), 'frame': hex(s['frame']), 'alpha': hex(s['alpha']), 'abe': s['abe'], 'xyoffset': hex(s['xyoffset']),
                     'clut_matches_ptg_palette': None if clut is None else any(b[576:1600] == clut for fn, b in files.items() if fn.startswith('GRAPHICS/GAME/MATRIX/') and fn == hit[0][0]),
                     '_tile': u['payload'], '_clut': clut})
    for r in rows:
        r['family'] = r['ptg'][0][0].rsplit('/', 1)[0]

    def texel(r, tx, ty):
        side = r['side']
        if r['psm'] == 0:
            o = (ty * side + tx) * 4
            return r['_tile'][o:o + 4]
        i = r['_tile'][ty * side + tx]
        sw = (i & ~24) | ((i & 8) << 1) | ((i & 16) >> 1)
        return r['_clut'][sw * 4:sw * 4 + 4]

    def sample_score(r, ax, ay, bx, by):
        (x0, y0), (x1, y1) = r['xy_px']
        (u0, v0), (u1, v1) = r['uv']
        tw, th = (u1 - u0) / 16, (v1 - v0) / 16
        err, n = 0, 0
        vr, vg, vb = r['rgba'][:3]
        for py in range(int(y0) + 1, int(y1)):
            for px in range(int(x0) + 1, int(x1)):
                tx = int(u0 / 16 + (px + 0.5 - x0) / (x1 - x0) * tw)
                ty = int(v0 / 16 + (py + 0.5 - y0) / (y1 - y0) * th)
                if not (0 <= tx < r['side'] and 0 <= ty < r['side']): continue
                t = texel(r, tx, ty)
                if t[3] != 128: continue
                sx, sy = int(px * ax + bx), int(py * ay + by)
                if not (0 <= sx < shot_w and 0 <= sy < shot_h): continue
                so = (sy * shot_w + sx) * 4
                for c, vc in zip(range(3), (vr, vg, vb)):
                    err += abs(min(255, t[c] * vc // 128) - shot[so + c]); n += 1
        return (err / n if n else None), n

    def score_set(rs, ay, bx, by, swap=False):
        tot, cnt = 0, 0
        order = rs[1:] + rs[:1] if swap else rs
        for r, other in zip(rs, order):
            q = dict(r)
            if swap:
                q['_tile'], q['_clut'], q['psm'], q['side'] = other['_tile'], other['_clut'], other['psm'], other['side']
            e, n = sample_score(q, 1.0, ay, bx, by)
            if e is not None: tot += e * n; cnt += n
        return (tot / cnt if cnt else None), cnt

    chall = [r for r in rows if r['family'].endswith('/CHALL') and r['psm'] == 0]
    fit_rows = chall[0::2]
    best = None
    for ay in (1.0, 480 / 512):
        for bx in range(-12, 13, 2):
            for by in range(-12, 13, 2):
                sc = score_set(fit_rows[:16], ay, bx, by)
                if sc[0] is not None and (best is None or sc[0] < best[0]):
                    best = (sc[0], ay, bx, by)
    for bx in range(best[2] - 2, best[2] + 3):
        for by in range(best[3] - 2, best[3] + 3):
            sc = score_set(fit_rows, best[1], bx, by)
            if sc[0] < best[0]:
                best = (sc[0], best[1], bx, by)
    ay, bx, by = best[1], best[2], best[3]
    families = {}
    for fam in sorted({r['family'] for r in rows}):
        for kind, sel in (('psmct32', [r for r in rows if r['family'] == fam and r['psm'] == 0]), ('psmt8_clut', [r for r in rows if r['family'] == fam and r['psm'] == 0x13])):
            if not sel: continue
            fitted = score_set(sel, ay, bx, by)
            ctl = {f'{dx},{dy}': score_set(sel, ay, bx + dx, by + dy)[0] for dx, dy in ((8, 0), (0, 8), (-8, 0), (0, -8))}
            families[f'{fam}|{kind}'] = {'sprites': len(sel), 'samples': fitted[1], 'mean_abs_rgb_error': fitted[0], 'shifted_controls': ctl,
                                         'swapped_tile_control': score_set(sel, ay, bx, by, swap=True)[0] if len(sel) > 1 else None,
                                         'tbw_equals_upload_dbw': all(r['tbw'] == r['upload_dbw'] for r in sel)}
    for fam_key, fam in families.items():
        sel = [r for r in rows if f"{r['family']}|{'psmct32' if r['psm'] == 0 else 'psmt8_clut'}" == fam_key]
        fam['tex0_TFX_TCC_CLAMP_values'] = sorted({(r['tex0_decoded']['TFX'], r['tex0_decoded']['TCC']) for r in sel})
        fam['frame_alpha_values'] = sorted({(r['frame'], r['alpha'], r['abe']) for r in sel})
    groups = collections.defaultdict(list)
    for r in rows:
        groups[r['ptg'][0][0]].append(r)
    gsum = {}
    for fn, rs in groups.items():
        xs = [p[0] for r in rs for p in r['xy_px']]; ys = [p[1] for r in rs for p in r['xy_px']]
        gsum[fn] = {'sprites': len(rs), 'tile_offsets_in_ptg': sorted({r['ptg'][0][1] for r in rs}),
                    'screenshot_bbox_px': [min(xs) + bx, min(ys) * ay + by, max(xs) + bx, max(ys) * ay + by], 'transfers': sorted({r['transfer'] for r in rs}),
                    'mean_abs_rgb_error': score_set(rs, ay, bx, by)[0],
                    'clut_matches_ptg_palette_all': (all(r['clut_matches_ptg_palette'] for r in rs) if rs[0]['psm'] == 0x13 and fn.startswith('GRAPHICS/GAME/MATRIX/') else None)}
    n_t32 = [u for u in uploads if (u['w'], u['h'], u['psm']) == (32, 32, 0) and len(u['payload']) == 4096]
    found = {}
    for pay in {u['payload'] for u in uploads if len(u['payload']) >= 512}:
        found[pay] = sorted({fn.rsplit('/', 1)[0] for fn, b in files.items() if b.find(pay) >= 0})
    summary = collections.defaultdict(lambda: {'uploads': 0, 'exact_ptg_substring': 0, 'directories': collections.Counter()})
    for u in uploads:
        if len(u['payload']) < 512: continue
        e = summary[f"psm{u['psm']}_{u['w']}x{u['h']}"]
        e['uploads'] += 1
        if found[u['payload']]:
            e['exact_ptg_substring'] += 1
            for dname in found[u['payload']]: e['directories'][dname] += 1
    upload_summary = {k: {'uploads': v['uploads'], 'exact_ptg_substring': v['exact_ptg_substring'], 'directories': dict(v['directories'])} for k, v in sorted(summary.items())}
    for r in rows:
        r.pop('_tile'); r.pop('_clut')
    receipt = {
        'scope': 'Join of visible menu98 UI sprites to GS uploads and source PTG tiles. Colour model: opaque texel * vertex RGB / 128, alpha test off; PSMT8 via CLUT with bit3/4-swapped index. Mapping fitted on half of the CHALL PSMCT32 sprites only.',
        'dump': {'path': str(DUMP.relative_to(ROOT)), 'compressed_sha256': DUMP_PIN, 'uploads_total': len(uploads), 'uploads_32x32_psmct32': len(n_t32), 'upload_exact_match_summary_ge_512_bytes': upload_summary,
                 'ptg_files_searched': len(files)},
        'screenshot': {'path': str(SHOT.relative_to(ROOT)), 'sha256': SHOT_PIN, 'size': [shot_w, shot_h]},
        'sprites_total': len(sprites), 'sprites_joined_to_ptg_bytes': len(rows),
        'fitted_mapping_fb_to_screenshot': {'ax': 1.0, 'ay': ay, 'bx': bx, 'by': by, 'fit_half_mean_abs_rgb_error': best[0],
                                            'fit_set': 'CHALL PSMCT32 sprites with even index'},
        'family_scores': families, 'per_ptg_groups': gsum, 'rows': rows,
    }
    json.dump(receipt, open(OUT, 'w'), indent=1, default=str)
    print(json.dumps({k: receipt[k] for k in receipt if k not in ('rows', 'per_ptg_groups')}, indent=1, default=str))
    for k, v in gsum.items(): print(k, v)


if __name__ == '__main__':
    main()
