#!/usr/bin/env python3
"""Three-way triangulation across slot102/103/104 EE images.
Highlights (0-based): 102->0, 103->4, 104->3. 1-based: 1,5,4.
Finds word offsets matching those tuples exactly. Read-only."""
import array

B = "/Users/Nicolas/Documents/github/hermes/projects/carmodels/research/evidence/continuation/runtime/linux/"
imgs = []
for f in ["slot102-car1-ford49-eeMemory.bin", "slot103-car5-tbirdconv-eeMemory.bin",
           "slot104-car4-fortyninec-eeMemory.bin"]:
    d = open(B + f, "rb").read()
    assert len(d) == 32 * 1024 * 1024, f
    imgs.append(array.array("I", d))
n = len(imgs[0])
print("words:", n)

for name, tup in [("zero-based (0,4,3)", (0, 4, 3)), ("one-based (1,5,4)", (1, 5, 4))]:
    hits = [i for i in range(n) if (imgs[0][i], imgs[1][i], imgs[2][i]) == tup]
    print(name, "hits:", len(hits))
    for i in hits[:40]:
        print("  0x%08x" % (i * 4))
