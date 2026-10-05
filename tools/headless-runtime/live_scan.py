#!/usr/bin/env python3
"""Live mark-number scan (runs INSIDE the container, headless, read-only).

Method: snapshot a focused set of EE regions over PINE, send a key to move the menu
highlight via RFB (container's own Xvfb), snapshot again, and cancel animation by also
diffing a no-input interval. Reads only; the only input is the emulator's own key.
"""
import socket, struct, sys, time

PINE = "/tmp/pcsx2.sock.28193"
VNC = ("127.0.0.1", 5900)
REGIONS = [("globals", 0x28f000, 0x291000),
           ("dat_records", 0x241b40, 0x242000),
           ("manager", 0x473d70, 0x474d70)]
WORDS = 4


class Pine:
    def __init__(self):
        self.s = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        self.s.settimeout(15); self.s.connect(PINE)
    def _r(self, n):
        b = bytearray()
        while len(b) < n:
            c = self.s.recv(n - len(b))
            if not c: raise ValueError("pine closed")
            b.extend(c)
        return bytes(b)
    def req(self, payload):
        self.s.sendall(struct.pack('<I', len(payload) + 4) + payload)
        ln, = struct.unpack('<I', self._r(4)); r = self._r(ln - 4)
        if r[0] != 0: raise ValueError("pine FAIL")
        return r[1:]
    def r32(self, a):
        return struct.unpack('<I', self.req(bytes([2]) + struct.pack('<I', a)))[0]
    def status(self):
        return struct.unpack('<I', self.req(b'\x0f'))[0]


def rfb_key(keysyms):
    s = socket.create_connection(VNC, timeout=10)
    def rn(n):
        b = bytearray()
        while len(b) < n:
            c = s.recv(n - len(b))
            if not c: raise ValueError("vnc closed")
            b.extend(c)
        return bytes(b)
    rn(12); s.sendall(b"RFB 003.008\n")
    nt = rn(1)[0]; rn(nt); s.sendall(b"\x01"); rn(4); s.sendall(b"\x01")
    h = rn(24); rn(struct.unpack(">I", h[20:24])[0])
    for ks in keysyms:
        s.sendall(struct.pack(">BBHI", 4, 1, 0, ks)); time.sleep(0.05)
        s.sendall(struct.pack(">BBHI", 4, 0, 0, ks)); time.sleep(0.15)
    s.close()


def snapshot(p):
    out = {}
    for name, lo, hi in REGIONS:
        out[name] = [(a, p.r32(a)) for a in range(lo, hi, WORDS)]
    return out


def diff(a, b):
    d = {}
    for name in a:
        d[name] = [(addr, x, y) for (addr, x), (_, y) in zip(a[name], b[name]) if x != y]
    return d


def main():
    p = Pine()
    if p.status() != 0:
        rfb_key([0x20])           # unpause (Space)
        time.sleep(2)
    print("status:", p.status())
    A = snapshot(p)
    time.sleep(0.6)
    A2 = snapshot(p)              # no input: captures animation-only changes
    print("sending L (0x6c) to move the highlight")
    rfb_key([0x6c]); time.sleep(0.4)
    B = snapshot(p)
    d_anim = diff(A, A2)
    d_key = diff(A, B)
    print("\n=== animation-only changes (A->A2, no input) ===")
    for name in d_anim:
        print(f"  {name}: {len(d_anim[name])} words")
    print("\n=== key-interval changes (A->B, after L) ===")
    for name in d_key:
        print(f"  {name}: {len(d_key[name])} words")
    anim = {name: {addr for addr, _, _ in d_anim[name]} for name in d_anim}
    print("\n=== candidates: changed after L but NOT changing without input ===")
    found = 0
    for name in d_key:
        cand = [(addr, x, y) for addr, x, y in d_key[name] if addr not in anim[name]]
        if cand:
            print(f"  [{name}] {len(cand)} candidates:")
            for addr, x, y in cand[:40]:
                print(f"    0x{addr:08x}: {x:#010x} -> {y:#010x}  ({x} -> {y})")
                found += 1
    print(f"\ntotal candidates: {found}")


if __name__ == "__main__":
    main()
