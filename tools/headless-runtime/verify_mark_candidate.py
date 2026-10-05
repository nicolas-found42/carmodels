#!/usr/bin/env python3
"""Verify the mark-number candidate (0x241b60 / 0x241e00) tracks the menu highlight.

Runs INSIDE the container, headless, read-only. Presses Move (L / J) and reads the
candidate words to see whether they step with the highlight.
"""
import socket, struct, time

PINE = "/tmp/pcsx2.sock.28193"
VNC = ("127.0.0.1", 5900)
CAND = [0x241b60, 0x241e00, 0x241cb0, 0x241f50, 0x2420a0]


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


def rfb_key(ks):
    s = socket.create_connection(VNC, timeout=10)
    def rn(n):
        b = bytearray()
        while len(b) < n:
            c = s.recv(n - len(b))
            if not c: raise ValueError("vnc closed")
            b.extend(c)
        return bytes(b)
    rn(12); s.sendall(b"RFB 003.008\n"); nt = rn(1)[0]; rn(nt); s.sendall(b"\x01"); rn(4); s.sendall(b"\x01")
    h = rn(24); rn(struct.unpack(">I", h[20:24])[0])
    for k in ks:
        s.sendall(struct.pack(">BBHI", 4, 1, 0, k)); time.sleep(0.05)
        s.sendall(struct.pack(">BBHI", 4, 0, 0, k)); time.sleep(0.15)
    s.close()


def read(p):
    return {a: p.r32(a) for a in CAND}


def main():
    p = Pine()
    print("status:", p.status())
    print("\nstep  action          " + "  ".join(f"0x{a:06x}" for a in CAND))
    print("----  --------------  " + "  ".join("--------" for _ in CAND))
    print("  0   (start)         " + "  ".join(f"{read(p)[a]:>8}" for a in CAND))
    for i, (key, name) in enumerate([(0x6c, "L (move +1)"), (0x6c, "L (move +1)"),
                                     (0x6c, "L (move +1)"), (0x6a, "J (move -1)"),
                                     (0x6a, "J (move -1)"), (0x6c, "L (move +1)")], start=1):
        rfb_key([key]); time.sleep(0.5)
        r = read(p)
        print(f"  {i}   {name:<14}" + "  ".join(f"{r[a]:>8}" for a in CAND) + f"   ({[hex(r[a]) for a in CAND]})")


if __name__ == "__main__":
    main()
