#!/usr/bin/env python3
"""Minimal RFB (VNC) key injector, stdlib only, runs INSIDE the container.

Connects to the container's x11vnc (localhost:5900, -nopw) and sends X key events
(KeyEvent messages). Headless: it drives the container's own Xvfb display, never the host.

Usage: rfb_key.py KEYSYM [KEYSYM ...]   (hex or decimal keysyms)
  space=0x20  j=0x6a  l=0x6c  Return=0xff0d  Escape=0xff1b
"""
import socket
import struct
import sys
import time

HOST, PORT = "127.0.0.1", 5900


def main():
    keysyms = [int(k, 0) for k in sys.argv[1:]]
    if not keysyms:
        raise SystemExit("usage: rfb_key.py KEYSYM [KEYSYM ...]")
    s = socket.create_connection((HOST, PORT), timeout=10)

    def recvn(n):
        b = bytearray()
        while len(b) < n:
            c = s.recv(n - len(b))
            if not c:
                raise ValueError("VNC closed")
            b.extend(c)
        return bytes(b)

    # 1. protocol version
    ver = recvn(12)
    s.sendall(b"RFB 003.008\n")
    # 2. security types
    ntypes = recvn(1)[0]
    types = recvn(ntypes)
    if 1 not in types:
        raise SystemExit(f"VNC requires auth (types {types}); -nopw expected")
    s.sendall(b"\x01")           # choose None
    secres = recvn(4)
    if struct.unpack(">I", secres)[0] != 0:
        raise SystemExit("VNC security result failed")
    # 3. ClientInit (shared)
    s.sendall(b"\x01")
    # 4. ServerInit
    head = recvn(24)
    namelen = struct.unpack(">I", head[20:24])[0]
    recvn(namelen)
    # 5. send KeyEvent down+up per keysym
    for ks in keysyms:
        msg = struct.pack(">BBHI", 4, 1, 0, ks)   # down
        s.sendall(msg)
        time.sleep(0.05)
        msg = struct.pack(">BBHI", 4, 0, 0, ks)   # up
        s.sendall(msg)
        time.sleep(0.2)
    s.close()
    print(f"sent {len(keysyms)} key(s): {[hex(k) for k in keysyms]}")


if __name__ == "__main__":
    main()
