#!/usr/bin/env python3
"""Scan slot102 EE image for livery-name tables, car label strings, and selector records.
Read-only analysis; prints addresses and words. Uses hermes python3.14 (zstd not needed here)."""
import struct

EE = "/Users/Nicolas/Documents/github/hermes/projects/carmodels/research/evidence/continuation/runtime/linux/slot102-car1-ford49-eeMemory.bin"
mem = open(EE, "rb").read()
print("EE bytes:", len(mem))
assert len(mem) == 32 * 1024 * 1024

# 1. livery-name tables: DEFAULT\0A\0B\0A2\0A1\0C\0C1\0C2\0B1\0B2\0D2\0D1\0
pat = b"DEFAULT\x00A\x00B\x00A2\x00A1\x00C\x00C1\x00C2\x00B1\x00B2\x00D2\x00D1\x00"
idx = []
off = 0
while True:
    i = mem.find(pat, off)
    if i < 0:
        break
    idx.append(i)
    off = i + 1
print("livery-table hits:", ["0x%08x" % i for i in idx])

# 2. car label strings
for s in [b"FORD '49", b"FORD \x279", b"FORD\xe2\x80\x9949", b"ROUTE 50", b"DRIVING SKILLS",
          b"TXT_CARS_COUPE_1949", b"TXT_CARS_FORTYNINE", b"LIVING LEGENDS", b"49COUPED", b"FORTYD",
          b"SELECT A CHALLENGE"]:
    hits = []
    off = 0
    while True:
        i = mem.find(s, off)
        if i < 0 or len(hits) > 12:
            break
        hits.append(i)
        off = i + 1
    print(repr(s), "->", ["0x%08x" % h for h in hits][:12])

# 3. record_base candidates: 0x233070 + type*0x114 for types 0..7; dump words at +0x74,+0x90,+0xbc
for t in range(8):
    base = 0x233070 + t * 0x114
    w74, w90, wbc = struct.unpack_from("<III", mem, base + 0x74), struct.unpack_from("<I", mem, base + 0x90), struct.unpack_from("<I", mem, base + 0xBC)
    print("type %d base=0x%08x +0x74=0x%08x +0x90=0x%08x +0xbc=%d" % (t, base, w74[0], w90[0], wbc[0]))
