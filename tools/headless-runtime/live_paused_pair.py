#!/usr/bin/env python3
"""Paused-pair capture: pause via RFB Space before each savestate so animation is frozen.
A0,A1 = paused pair before move; unpause, move with L, re-pause; B0,B1 = paused pair after.
"""
import socket, struct, time

PINE = "/tmp/pcsx2.sock.28193"
VNC = ("127.0.0.1", 5900)


class Pine:
    def __init__(self):
        self.s = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM); self.s.settimeout(20); self.s.connect(PINE)
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
    def status(self): return struct.unpack('<I', self.req(b'\x0f'))[0]
    def save(self, slot): return self.req(bytes([9, slot]))


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


def ensure_paused(p, want):
    for _ in range(20):
        st = p.status()
        if st == want:
            return st
        rfb_key([0x20]); time.sleep(1.0)
    raise ValueError(f"could not reach status {want}, at {p.status()}")


def main():
    p = Pine()
    ensure_paused(p, 1)
    print("paused; saving 114,115")
    p.save(114); time.sleep(2.0)
    p.save(115); time.sleep(2.0)
    ensure_paused(p, 0)
    print("running; moving highlight with L")
    rfb_key([0x6c]); time.sleep(2.5)
    ensure_paused(p, 1)
    print("paused; saving 116,117")
    p.save(116); time.sleep(2.0)
    p.save(117); time.sleep(2.0)
    print("done; status:", p.status())


if __name__ == "__main__":
    main()
