#!/usr/bin/env python3
"""Bounded PINE v2.8.2 metadata/save/load controls + READ-ONLY guest memory reads.

Read-only: this helper uses only the PINE read opcodes (MsgRead8/16/32/64). It never
issues a write, cheat or patch (MsgWrite* is not implemented here by construction).
"""
import argparse
import json
import socket
import struct

READ_OPCODE = {8: 0, 16: 1, 32: 2, 64: 3}   # PCSX2 PINE.cpp IPCCommand MsgRead8/16/32/64
WIDTH_BYTES = {8: 1, 16: 2, 32: 4, 64: 8}
FMT = {8: "<B", 16: "<H", 32: "<I", 64: "<Q"}


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('command', choices=['identity', 'save', 'load', 'read'])
    p.add_argument('--slot', type=int)
    p.add_argument('--socket', default='/tmp/pcsx2.sock.28193')
    p.add_argument('--addr', type=lambda s: int(s, 0), help='guest physical address (dec or 0x hex)')
    p.add_argument('--width', type=int, choices=[8, 16, 32, 64], default=32)
    p.add_argument('--count', type=int, default=1, help='number of consecutive words to read')
    a = p.parse_args()
    with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as connection:
        connection.settimeout(10)
        connection.connect(a.socket)

        def receive(count):
            result = bytearray()
            while len(result) < count:
                block = connection.recv(count - len(result))
                if not block:
                    raise ValueError('PINE closed partial reply')
                result.extend(block)
            return bytes(result)

        def request(payload):
            connection.sendall(struct.pack('<I', len(payload) + 4) + payload)
            length, = struct.unpack('<I', receive(4))
            if not 5 <= length <= 450000:
                raise ValueError('PINE reply size outside bounds')
            reply = receive(length - 4)
            if reply[0] != 0:
                raise ValueError('PINE rejected command')
            return reply[1:]

        def text(opcode):
            reply = request(bytes([opcode]))
            if len(reply) < 5:
                raise ValueError('PINE string reply truncated')
            length, = struct.unpack_from('<I', reply)
            if len(reply) != length + 4 or reply[-1] != 0:
                raise ValueError('PINE string span invalid')
            return reply[4:-1].decode('utf8')

        status_reply = request(b'\x0f')
        if len(status_reply) != 4:
            raise ValueError('PINE status span invalid')
        status, = struct.unpack('<I', status_reply)
        if status not in [0, 1, 2]:
            raise ValueError('PINE status unknown')

        if a.command == 'identity':
            print(json.dumps({'version': text(8), 'title': text(11), 'id': text(12),
                              'uuid': text(13), 'game_version': text(14), 'status': status}))
        elif a.command == 'read':
            if a.addr is None or a.count < 1 or a.count > 4096:
                raise ValueError('read requires --addr and 1<=count<=4096')
            nb = WIDTH_BYTES[a.width]
            values = []
            for i in range(a.count):
                raw = request(bytes([READ_OPCODE[a.width]]) + struct.pack('<I', a.addr + i * nb))
                if len(raw) != nb:
                    raise ValueError('PINE read width mismatch')
                values.append(struct.unpack(FMT[a.width], raw)[0])
            print(json.dumps({'command': 'read', 'addr': hex(a.addr), 'width': a.width,
                              'count': a.count, 'status': status,
                              'values': values, 'hex': [hex(v) for v in values]}))
        else:
            if a.slot is None or not 0 <= a.slot <= 255:
                raise ValueError('save/load slot outside 0..255')
            if status != 1:
                raise ValueError('save/load requires paused emulator')
            if request(bytes([9 if a.command == 'save' else 10, a.slot])):
                raise ValueError('unexpected save/load response bytes')
            print(json.dumps({'command': a.command, 'slot': a.slot,
                              'status': status, 'queued': True,
                              'note': 'Acknowledgement queues work; inspect resulting state/file to confirm.'}))


if __name__ == '__main__':
    main()
