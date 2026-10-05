#!/usr/bin/env python3
"""Headless PINE probe for Job B: load a savestate, then read the live entity-manager
chain (read-only) and dump bounded regions as JSON.

Read-only: uses only PINE read opcodes; the only non-read command is LoadState (restores
an existing savestate, writes no guest memory we author).
"""
import argparse
import json
import socket
import struct
import time

READ = {32: 2}
FMT = {8: '<B', 16: '<H', 32: '<I', 64: '<Q'}


class Pine:
    def __init__(self, path):
        self.s = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        self.s.settimeout(10)
        self.s.connect(path)

    def _recv(self, n):
        b = bytearray()
        while len(b) < n:
            c = self.s.recv(n - len(b))
            if not c:
                raise ValueError('PINE closed')
            b.extend(c)
        return bytes(b)

    def req(self, payload):
        self.s.sendall(struct.pack('<I', len(payload) + 4) + payload)
        ln, = struct.unpack('<I', self._recv(4))
        if not 5 <= ln <= 450000:
            raise ValueError('bad reply size')
        r = self._recv(ln - 4)
        if r[0] != 0:
            raise ValueError('PINE FAIL')
        return r[1:]

    def r32(self, addr):
        r = self.req(bytes([READ[32]]) + struct.pack('<I', addr))
        return struct.unpack('<I', r)[0]

    def region(self, addr, count):
        return [self.r32(addr + 4 * i) for i in range(count)]

    def status(self):
        r = self.req(b'\x0f')
        return struct.unpack('<I', r)[0]

    def load(self, slot):
        self.req(bytes([10, slot]))


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--socket', default='/tmp/pcsx2.sock.28193')
    p.add_argument('--load', type=int, help='savestate slot to load first')
    p.add_argument('--walk', action='store_true', help='walk the entity list from the static global')
    a = p.parse_args()
    n = Pine(a.socket)
    out = {'status_before': n.status()}
    if a.load is not None:
        n.load(a.load)
        out['loaded'] = a.load
        for _ in range(30):
            time.sleep(0.3)
            if n.status() == 1:
                break
        out['status_after'] = n.status()
    out['globals_290270'] = n.region(0x290270, 0x20)
    out['global_290278'] = n.r32(0x290278)
    if a.walk:
        g = n.r32(0x290278)
        out['manager'] = n.region(g, 0x20) if 0x100000 <= g < 0x2000000 else None
        nodes = []
        if out['manager']:
            ptr = n.r32(g + 8)
            seen = set()
            for _ in range(24):
                if ptr in seen or not (0x100000 <= ptr < 0x2000000):
                    break
                seen.add(ptr)
                node = n.region(ptr, 8)
                ent = (ptr + 0x1f) & 0xfffffff0
                entwords = n.region(ent, 0x40) if 0x100000 <= ent < 0x2000000 else None
                typ = None
                if entwords is not None and 0x100000 <= entwords[0] < 0x2000000:
                    typ = n.r32(entwords[0]) & 0xff
                nodes.append({'node': hex(ptr), 'node_words': node, 'entity': hex(ent),
                              'entity_words': entwords, 'type_byte': typ,
                              'next': hex(n.r32(ptr + 0xc))})
                ptr = n.r32(ptr + 0xc)
        out['nodes'] = nodes
    out['cursor_241b40'] = n.region(0x241b40, 0x20)
    out['rec_type2_233070'] = n.region(0x233070 + 2 * 0x114, 0x30)
    print(json.dumps(out))


if __name__ == '__main__':
    main()
