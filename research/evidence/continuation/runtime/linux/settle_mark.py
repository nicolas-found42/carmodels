#!/usr/bin/env python3
"""Settle-then-read: confirm 0x241b60 tracks the menu highlight once animation stops."""
import socket, struct, time

PINE = "/tmp/pcsx2.sock.28193"; VNC = ("127.0.0.1", 5900)
CAND = [0x241b60, 0x241e00]


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
        s.sendall(struct.pack(">BBHI", 4, 0, 0, k)); time.sleep(0.1)
    s.close()


def settle(p, timeout=4.0):
    """Wait until both candidates stop changing; return the settled tuple."""
    prev = None; t0 = time.time()
    while time.time() - t0 < timeout:
        cur = tuple(p.r32(a) for a in CAND)
        if cur == prev:
            return cur
        prev = cur; time.sleep(0.25)
    return prev


def main():
    p = Pine(); print("status:", p.status())
    print("\nstep  action        settled (0x241b60, 0x241e00)")
    for i in range(10):
        act = "L" if i == 0 else ("L" if i <= 6 else "J")
        if i: rfb_key([0x6c if act == "L" else 0x6a])
        s = settle(p)
        print(f"  {i}   {act:<12}  {s}")
        time.sleep(0.3)


if __name__ == "__main__":
    main()
