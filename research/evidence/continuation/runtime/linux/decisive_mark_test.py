#!/usr/bin/env python3
"""Decisive test: load slots 102/103/104 (known highlights car1/car5/car4 = positions 1/5/4)
live and read the candidate words. A real mark number must read 1/5/4 across these loads."""
import socket, struct, time

PINE = "/tmp/pcsx2.sock.28193"
CANDS = [0x241b60, 0x241e00, 0x28f0f0, 0x28f0fc, 0x28f1f8, 0x28f240, 0x28f248, 0x28fb74, 0x290690]


class Pine:
    def __init__(self):
        self.s = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM); self.s.settimeout(15); self.s.connect(PINE)
    def _r(self, n):
        b = bytearray()
        while len(b) < n:
            c = self.s.recv(n - len(b))
            if not c: raise ValueError("pine closed")
            b.extend(c)
        return bytes(b)
    def req(self, p):
        self.s.sendall(struct.pack('<I', len(p) + 4) + p); ln, = struct.unpack('<I', self._r(4)); r = self._r(ln - 4)
        if r[0]: raise ValueError("FAIL")
        return r[1:]
    def r32(self, a): return struct.unpack('<I', self.req(bytes([2]) + struct.pack('<I', a)))[0]
    def status(self): return struct.unpack('<I', self.req(b'\x0f'))[0]
    def load(self, slot): return self.req(bytes([10, slot]))


def main():
    p = Pine()
    print("status:", p.status())
    EXPECT = {102: 1, 103: 5, 104: 4}     # highlight position (1-based) per slot
    rows = {}
    for slot in (102, 103, 104):
        p.load(slot); time.sleep(3)
        time.sleep(1)
        rows[slot] = {a: p.r32(a) for a in CANDS}
    print(f"\nslot (expected)  " + "  ".join(f"0x{a:06x}" for a in CANDS))
    for slot in (102, 103, 104):
        print(f"  {slot} (h={EXPECT[slot]})        " + "  ".join(f"{rows[slot][a]:>8}" for a in CANDS))
    print("\n=== any candidate equal to (1,5,4)? ===")
    for a in CANDS:
        vals = (rows[102][a], rows[103][a], rows[104][a])
        mark = "  <-- MATCHES (1,5,4)!" if vals == (1, 5, 4) else ("  <-- (0,4,3)!" if vals == (0, 4, 3) else "")
        print(f"  0x{a:06x}: {vals}{mark}")


if __name__ == "__main__":
    main()
