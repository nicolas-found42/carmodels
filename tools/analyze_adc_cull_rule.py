#!/usr/bin/env python3
"""Test whether ADC bits beyond the source W lane track screen-space strip orientation in the executed GIF packets.

Input pairs come from retained-ring-gsdump-alignment.json (retained draw descriptor <-> GSDump transfer).  For
strip vertex i the GS skips the triangle (i-2,i-1,i) when XYZF2.ADC is set.  The rule tested here is
ADC[i] = W[i] OR cull[i], with cull[i] derived only from the emitted screen XY.  The orientation sign
convention is fitted on even-indexed pairs and scored on odd-indexed held-out pairs; shuffled-sign and
mirrored-sign controls are reported.  This is a measurement of the packets, not a VU1 program recovery.
"""
import json
import random
import struct

import gsdump
import join_retained_blocks_to_gsdump as gj
import validate_retained_packet_blocks as vb

ROOT = vb.ROOT
ALIGN = ROOT / 'research/evidence/packet-continuation/retained-ring-gsdump-alignment.json'
OUT = ROOT / 'research/evidence/packet-continuation/adc-cull-rule-test.json'


def dump_geometry():
    transfers, _ = gsdump.load_transfers(gj.DUMP, gj.DUMP_PIN)
    geo = {}
    for ti, data in enumerate(transfers):
        for off, lo, hi, nloop, flg, nreg, _ in gsdump.iter_tags(data):
            if flg == 0 and hi == 0x412:
                xy, adc = [], []
                for i in range(nloop):
                    q = struct.unpack_from('<4I', data, off + 16 + (i * 3 + 2) * 16)
                    xy.append((q[0] & 0xffff, q[1] & 0xffff)); adc.append((q[3] >> 15) & 1)
                geo[ti] = {'xy': xy, 'adc': adc}
    return geo


def tri_signs(xy):
    """Signed area (12.4 units) of strip triangle ending at each vertex index; None for the first two."""
    out = [None, None]
    for i in range(2, len(xy)):
        a, b, c = (xy[i - 2], xy[i - 1], xy[i]) if i % 2 == 0 else (xy[i - 1], xy[i - 2], xy[i])
        out.append((b[0] - a[0]) * (c[1] - a[1]) - (b[1] - a[1]) * (c[0] - a[0]))
    return out


def tally(pairs, geo, align, sign, shuffle=None):
    """Counts of (W, ADC, orientation) over vertices where the strip triangle exists."""
    c = {'w1_adc1': 0, 'w0_adc0_front': 0, 'w0_adc0_back': 0, 'w0_adc1_front': 0, 'w0_adc1_back': 0, 'w1_adc0': 0, 'w0_adc1_zero_area': 0, 'w0_adc0_zero_area': 0}
    rng = random.Random(7)
    for ai, t in pairs:
        d = align['draws'][ai]; g = geo[t]
        sg = tri_signs(g['xy'])
        if shuffle:
            sg = [None, None] + rng.sample(sg[2:], len(sg) - 2)
        for i in range(2, len(g['adc'])):
            w, a = d['expected_w'][i], g['adc'][i]
            if w:
                c['w1_adc1' if a else 'w1_adc0'] += 1; continue
            s = sg[i] * sign
            if s == 0:
                c['w0_adc1_zero_area' if a else 'w0_adc0_zero_area'] += 1; continue
            key = ('w0_adc1_' if a else 'w0_adc0_') + ('back' if s < 0 else 'front')
            c[key] += 1
    return c


def rates(c):
    back = c['w0_adc1_back'] + c['w0_adc0_back']
    front = c['w0_adc1_front'] + c['w0_adc0_front']
    return {'P(ADC=1 | W=0, back-facing)': c['w0_adc1_back'] / back if back else None,
            'P(ADC=1 | W=0, front-facing)': c['w0_adc1_front'] / front if front else None,
            'counts': c}


def rule_confusion(pairs, geo, align, sign, gate=True, shuffle=False):
    """Predict ADC = W | (cull_enabled & screen back-facing) and score it against the dumped ADC bits."""
    rng = random.Random(11)
    c = {'tp_extra': 0, 'fp_extra': 0, 'fn_extra': 0, 'tn_extra': 0, 'vertices': 0, 'exact_pair_matches': 0}
    for ai, t in pairs:
        d = align['draws'][ai]; g = geo[t]
        sg = tri_signs(g['xy'])
        if shuffle:
            sg = [None, None] + rng.sample(sg[2:], len(sg) - 2)
        enabled = (d.get('pass_id') not in (None, 1)) if gate else True
        exact = True
        for i in range(2, len(g['adc'])):
            w, a = d['expected_w'][i], g['adc'][i]
            if w:
                continue
            pred = 1 if enabled and sg[i] * sign < 0 else 0
            c['vertices'] += 1
            if pred and a: c['tp_extra'] += 1
            elif pred and not a: c['fp_extra'] += 1; exact = False
            elif not pred and a: c['fn_extra'] += 1; exact = False
            else: c['tn_extra'] += 1
        c['exact_pair_matches'] += exact
    c['pairs'] = len(pairs)
    n = c['vertices']
    c['accuracy_over_W0_vertices'] = (c['tp_extra'] + c['tn_extra']) / n if n else None
    return c


def main():
    align = json.loads(ALIGN.read_text())
    geo = dump_geometry()
    pairs = [(ai, t) for ai, t in align['matched_pairs'] if align['draws'][ai].get('expected_w') is not None]
    bad = {tuple(x) for x in align['alignment']['adc_subset_violations_retained_idx_transfer']}
    pairs = [(ai, t) for ai, t in pairs if (ai, t) not in bad]
    train, test = pairs[0::2], pairs[1::2]
    conv = {}
    for sign in (1, -1):
        r = rates(tally(train, geo, align, sign))
        conv[sign] = (r['P(ADC=1 | W=0, back-facing)'] or 0) - (r['P(ADC=1 | W=0, front-facing)'] or 0)
    sign = max(conv, key=lambda k: conv[k])
    held = rates(tally(test, geo, align, sign))
    receipt = {
        'scope': 'Measurement on aligned retained-descriptor/GSDump pairs; not a VU1 microprogram recovery and not a game-exact culling equation.',
        'pairs_used': len(pairs), 'train_pairs': len(train), 'test_pairs': len(test),
        'orientation_sign_fitted_on_train': sign, 'train_separation_by_sign': {str(k): v for k, v in conv.items()},
        'held_out': held,
        'control_mirrored_sign': rates(tally(test, geo, align, -sign)),
        'control_shuffled_orientation': rates(tally(test, geo, align, sign, shuffle=True)),
        'source_W_plane_rule': 'W=1 implies ADC=1 on every aligned vertex except the retained-index/transfer pairs listed as violations in the alignment receipt.',
        'subsets': {},
    }
    for label, sel in (('textured_prim_0x5c_or_0x1d', [p for p in test if align['draws'][p[0]]['prim'] & 0x10]),
                       ('untextured', [p for p in test if not align['draws'][p[0]]['prim'] & 0x10])):
        receipt['subsets'][label] = {'pairs': len(sel), **rates(tally(sel, geo, align, sign))}
    receipt['rule_gated_by_pass_id'] = {
        'statement': 'ADC = W OR (pass_id != 1 AND strip triangle signed area * sign < 0); pass_id is the second word of the FUN_0021bb48 header (2 when effective bit 0x200 is set); FUN_00128e88 blocks have no such word and are treated as not culling.',
        'held_out': rule_confusion(test, geo, align, sign),
        'control_without_pass_gate': rule_confusion(test, geo, align, sign, gate=False),
        'control_mirrored_sign': rule_confusion(test, geo, align, -sign),
        'control_shuffled_orientation': rule_confusion(test, geo, align, sign, shuffle=True),
    }
    by = {}
    for ai, t in test:
        d = align['draws'][ai]
        k = f"{d['kind']}|pass={d.get('pass_id')}|flags={hex(d['effective_flags']) if d.get('effective_flags') is not None else None}"
        by.setdefault(k, []).append((ai, t))
    receipt['rule_by_effective_flags'] = {k: rule_confusion(v, geo, align, sign) for k, v in sorted(by.items())}
    OUT.write_text(json.dumps(receipt, indent=1))
    print(json.dumps(receipt['rule_gated_by_pass_id'], indent=1))


if __name__ == '__main__':
    main()
