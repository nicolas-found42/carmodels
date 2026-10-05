#!/usr/bin/env python3
"""Diff slot102 (car1 selected) vs slot103 (car5 selected) EE images.
Lists changed words, with focus on the six selector-record region
0x233070..0x233070+8*0x114 and the six livery-list areas. Read-only."""
import struct

B = "/Users/Nicolas/Documents/github/hermes/projects/carmodels/research/evidence/continuation/runtime/linux/"
a = open(B + "slot102-car1-ford49-eeMemory.bin", "rb").read()
b = open(B + "slot103-car5-tbirdconv-eeMemory.bin", "rb").read()
assert len(a) == len(b) == 32 * 1024 * 1024

import array
wa = array.array("I", a)
wb = array.array("I", b)
n = len(wa)
changed = [i for i in range(n) if wa[i] != wb[i]]
print("changed words:", len(changed), "of", n)

# focus windows: record structs + list areas (from scan: lists near 0x143b574..0x1a5...)
wins = [(0x233070, 0x900)]
list_bases = [0x0143b574, 0x0157e1e4, 0x016b7774, 0x017ec384, 0x0192f7d4, 0x01a5844c]
for lb in list_bases:
    wins.append((lb - 0x40, 0x400))
for (start, ln) in wins:
    print("--- window 0x%08x len 0x%x" % (start, ln))
    for off in range(start, start + ln, 4):
        i = off // 4
        if wa[i] != wb[i]:
            print("  0x%08x: 102=0x%08x (%d)  103=0x%08x (%d)" % (off, wa[i], wa[i], wb[i], wb[i]))

# small-int transitions anywhere: 102 value in 0..11 and 103 value in 0..11, both small, differ
print("--- small-int transitions (both <=11, differ), excluding windows above:")
count = 0
for i in changed:
    if wa[i] <= 11 and wb[i] <= 11:
        off = i * 4
        if not any(s <= off < s + ln for (s, ln) in wins):
            print("  0x%08x: 102=%d 103=%d" % (off, wa[i], wb[i]))
            count += 1
            if count > 60:
                print("  ... truncated"); break
print("small-int count:", count)
