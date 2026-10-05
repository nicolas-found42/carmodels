#!/usr/bin/env python3
"""Assert that tools/vu1_decode.py agrees with the pinned VU1 disassembly on every pair of overlays 0-6.

The decoder is written from the VU1 instruction layout, the disassembly comes from a separate tool, so
agreement on all pairs is evidence for both. Needs the sibling extraction checkout (see CONTRIBUTING.md).
    python3 tools/test_vu1_decode.py
"""
import collections
import re
import struct
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import vu1_decode as vd  # noqa: E402
import verify_vu_pass_handlers as vph  # noqa: E402


def same(mine, theirs):
    if mine.startswith('loi') and theirs.startswith('loi'):
        a, b = float(mine.split()[1]), float(theirs.split()[1])
        return abs(a - b) <= 1e-6 * max(1.0, abs(b))
    return vph.normalise(mine) == vph.normalise(theirs)


def agreement(inputs):
    total, bad, mnemonics = 0, [], collections.Counter()
    for n in range(7):
        ov = inputs['overlays'][n]
        for p, (lo, up) in enumerate(vd.pairs(ov['bin'])):
            total += 1
            u, l = vd.render_pair(lo, up).split('\t')
            tu, tl = ov['asm'][p].split('\t')
            mnemonics[re.sub(r'[\[.].*', '', u.split(' ')[0]) or 'nop'] += 1
            mnemonics[re.sub(r'\..*', '', l.strip().split(' ')[0])] += 1
            if not (same(u.strip(), tu.strip()) and same(l.strip(), tl.strip())):
                bad.append((n, p, u, l, tu, tl))
    return total, bad, mnemonics


def main():
    inputs = vph.load_inputs()
    total, bad, mnemonics = agreement(inputs)
    assert total == 1558 and not bad, bad[:5]
    assert not [m for m in mnemonics if m.startswith('?')]
    assert len(mnemonics) >= 70, len(mnemonics)

    # sensitivity: flipping one bit of one word makes the pair disagree with the disassembly in the great majority of cases
    changed = escaped = 0
    for n in (0, 2):
        ov = inputs['overlays'][n]
        for p in range(0, 256, 3):
            lo, up = struct.unpack_from('<II', ov['bin'], p * 8)
            for bit in (0, 7, 13, 21):
                mlo = lo ^ (1 << bit)
                u, l = vd.render_pair(mlo, up).split('\t')
                tu, tl = ov['asm'][p].split('\t')
                if same(l.strip(), tl.strip()):
                    escaped += 1
                else:
                    changed += 1
    assert changed > 10 * escaped, (changed, escaped)  # an escape is a bit the text does not show (for example an unused field)
    print('PASS test_vu1_decode (%d pairs, %d distinct mnemonics, %d/%d bit flips visible)' % (total, len(mnemonics), changed, changed + escaped))


if __name__ == '__main__':
    main()
