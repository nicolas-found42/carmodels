#!/usr/bin/env python3
"""Full-EE live adjacent scan (runs INSIDE the container, headless, read-only).

Unpauses via RFB, takes live savestates (PINE MsgSaveState works while running), and
captures a pair before a highlight move and a pair after, so animation can be cancelled:
  A0,A1 = before move        (A0->A1 = animation-only)
  B0,B1 = after move         (B0->B1 = animation-only)
A word is a mark candidate if it is stable within a pair and differs across the move:
  A0==A1 AND B0==B1 AND A1 != B0.
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


def main():
    p = Pine()
    if p.status() != 0:
        rfb_key([0x20]); time.sleep(3)
    print("status:", p.status())
    for slot in (110, 111, 112, 113):
        pass
    # before-move pair
    p.save(110); time.sleep(2.0)
    p.save(111); time.sleep(2.0)
    # move the highlight, settle
    rfb_key([0x6c]); time.sleep(2.5)
    p.save(112); time.sleep(2.0)
    p.save(113); time.sleep(2.0)
    print("saved slots 110,111 (before) and 112,113 (after L)")


if __name__ == "__main__":
    main()
