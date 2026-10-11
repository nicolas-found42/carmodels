"""Bounded, read-only PS1 ISO and Gran Turismo GT-ARC/GTZIP parsers.

GTZIP is a relative-distance LZ stream, not standard LZSS. Format observations
are cross-checked against pez2k/gt2tools and JeevesGB/GTExplorer; see the research
note for pinned sources. Native payload extraction does not decode geometry.
"""
import hashlib
from pathlib import Path
import re
import struct

SYNC = b'\x00' + b'\xff' * 10 + b'\x00'
ARC_MAGIC = b'@(#)GT-ARC\x00\x00'
CAR_MAGIC = b'@(#)GT-CAR\x00'
TEX_MAGIC = b'@(#)GT-CTEX\x00'
MAX_PAYLOAD = 16 * 1024 * 1024


def digest(data):
    return hashlib.sha256(data).hexdigest()


def file_digest(path):
    sha = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b''):
            sha.update(chunk)
    return sha.hexdigest()


def both_endian(data, offset, width=4):
    little = int.from_bytes(data[offset:offset + width], 'little')
    big = int.from_bytes(data[offset + width:offset + width * 2], 'big')
    if little != big or offset + width * 2 > len(data):
        raise ValueError('ISO endian copies disagree or are truncated')
    return little


class Disc:
    """Accept ISO user sectors or raw Mode 1/Mode 2 Form 1 sectors only."""

    def __init__(self, path):
        self.path = Path(path)
        self.stream = self.path.open('rb')
        try:
            self.size = self.path.stat().st_size
            self.stream.seek(16 * 2048)
            if self.stream.read(7) == b'\x01CD001\x01':
                self.stride = 2048
            else:
                self.stride = 2352
            if self.size % self.stride:
                raise ValueError('Truncated disc sector')
            self.sectors = self.size // self.stride
            pvd = self.block(16)
            if pvd[:7] != b'\x01CD001\x01':
                raise ValueError('Unsupported disc: ISO primary volume descriptor absent')
            if both_endian(pvd, 128, 2) != 2048:
                raise ValueError('Unsupported ISO logical block size')
            self.volume_sectors = both_endian(pvd, 80)
            if not 17 <= self.volume_sectors <= self.sectors:
                raise ValueError('ISO volume outside disc')
            self.volume = pvd[40:72].decode('ascii').rstrip()
            self.entries = []
            self._walk(both_endian(pvd, 158), both_endian(pvd, 166), '', set())
        except Exception:
            self.stream.close()
            raise

    def close(self):
        self.stream.close()

    def block(self, lba):
        if not 0 <= lba < self.sectors:
            raise ValueError('ISO sector outside disc')
        self.stream.seek(lba * self.stride)
        data = self.stream.read(self.stride)
        if self.stride == 2048:
            return data
        if data[:12] != SYNC:
            raise ValueError('Invalid raw CD sector sync')
        if data[15] == 1:
            return data[16:2064]
        if data[15] == 2 and data[16:20] == data[20:24] and not data[18] & 0x20:
            return data[24:2072]
        raise ValueError('Unsupported CD sector mode or Form 2 data')

    def read(self, entry, limit=MAX_PAYLOAD * 2):
        lba, size = entry['lba'], entry['size']
        if not 0 <= size <= limit:
            raise ValueError('ISO file exceeds read limit')
        count = (size + 2047) // 2048
        if lba < 0 or lba + count > self.volume_sectors:
            raise ValueError('ISO extent outside volume')
        return b''.join(self.block(lba + i) for i in range(count))[:size]

    def inventory_header(self, lba):
        """Inventory streaming members without treating Form 2 as ISO file data."""
        if self.stride == 2352:
            self.stream.seek(lba * self.stride)
            raw = self.stream.read(self.stride)
            if raw[:12] == SYNC and raw[15] == 2 and raw[16:20] == raw[20:24] and raw[18] & 0x20:
                return 'Mode 2 Form 2 streaming sector; payload not read'
        head = self.block(lba)[:32]
        return ''.join(chr(b) if 32 <= b < 127 else '.' for b in head)

    def _walk(self, lba, size, parent, visited):
        if (lba, size) in visited or len(visited) >= 32:
            raise ValueError('ISO directory cycle or directory limit')
        visited.add((lba, size))
        data = self.read({'lba': lba, 'size': size}, limit=1024 * 1024)
        pos = 0
        while pos < len(data):
            length = data[pos]
            if not length:
                pos = (pos // 2048 + 1) * 2048
                continue
            if length < 34 or pos + length > len(data) or pos % 2048 + length > 2048:
                raise ValueError('Invalid ISO directory record length')
            record = data[pos:pos + length]
            pos += length
            name_length = record[32]
            if 33 + name_length > length:
                raise ValueError('Truncated ISO filename')
            name = record[33:33 + name_length]
            if name in (b'\x00', b'\x01'):
                continue
            name = name.decode('ascii')
            if not re.fullmatch(r'[A-Za-z0-9_.-]+(?:;[0-9]+)?', name):
                raise ValueError('Unsafe or unsupported ISO filename')
            if record[26] or record[27] or record[25] & 0x80 or record[1]:
                raise ValueError('Unsupported interleaved, multi-extent or extended ISO record')
            if both_endian(record, 28, 2) != 1:
                raise ValueError('Unsupported ISO volume sequence')
            entry = {'path': parent + '/' + name, 'lba': both_endian(record, 2),
                     'size': both_endian(record, 10), 'directory': bool(record[25] & 2)}
            if entry['lba'] + (entry['size'] + 2047) // 2048 > self.volume_sectors:
                raise ValueError('ISO extent outside volume')
            if any(e['path'] == entry['path'] for e in self.entries):
                raise ValueError('Duplicate ISO path')
            self.entries.append(entry)
            if len(self.entries) > 10000:
                raise ValueError('ISO inventory limit')
            if entry['directory']:
                self._walk(entry['lba'], entry['size'], entry['path'], visited)


def decompress(data, expected=None, limit=MAX_PAYLOAD):
    """GTZIP: flags LSB first, 0=literal, 1=(length-3, distance-1)."""
    if expected is not None and not 0 < expected <= limit:
        raise ValueError('Invalid declared decompressed size')
    output = bytearray()
    pos = 0
    while pos < len(data):
        flags = data[pos]
        pos += 1
        if pos == len(data):
            raise ValueError('GTZIP dangling flag byte')
        for bit in range(8):
            if pos == len(data):
                break
            if flags & (1 << bit):
                if pos + 2 > len(data):
                    raise ValueError('GTZIP truncated match')
                length, distance = data[pos] + 3, data[pos + 1]
                pos += 2
                if distance >= 128:
                    if pos == len(data):
                        raise ValueError('GTZIP truncated extended distance')
                    distance = (distance - 128) * 256 + data[pos]
                    pos += 1
                distance += 1
                if distance > len(output):
                    raise ValueError('GTZIP back-reference before output')
                if len(output) + length > (expected if expected is not None else limit):
                    raise ValueError('GTZIP output exceeds declared size or limit')
                for _ in range(length):
                    output.append(output[-distance])
            else:
                if len(output) >= (expected if expected is not None else limit):
                    raise ValueError('GTZIP output exceeds declared size or limit')
                output.append(data[pos])
                pos += 1
    if not output or expected is not None and len(output) != expected:
        raise ValueError('GTZIP decompressed size mismatch')
    return bytes(output)


def archive_entries(data):
    if len(data) < 16 or data[:12] != ARC_MAGIC:
        raise ValueError('GT-ARC signature mismatch')
    kind, count = struct.unpack_from('<HH', data, 12)
    if kind not in (1, 0x8001) or not 0 < count <= 20000 or 16 + count * 12 > len(data):
        raise ValueError('Unsupported or truncated GT-ARC directory')
    result = []
    previous_end = 16 + count * 12
    for index in range(count):
        offset, size, decoded_size = struct.unpack_from('<III', data, 16 + index * 12)
        if offset < previous_end or offset + size > len(data) or not size:
            raise ValueError('GT-ARC entry overlaps directory, previous entry or archive end')
        if not 0 < decoded_size <= MAX_PAYLOAD:
            raise ValueError('GT-ARC declared size exceeds limit')
        packed = data[offset:offset + size]
        compressed = kind == 0x8001
        decoded = decompress(packed, decoded_size) if compressed else packed
        if len(decoded) != decoded_size:
            raise ValueError('GT-ARC uncompressed size mismatch')
        result.append({'index': index, 'offset': offset, 'stored_bytes': size,
                       'decoded_bytes': decoded_size, 'compressed': compressed,
                       'stored_sha256': digest(packed), 'sha256': digest(decoded), 'data': decoded})
        previous_end = offset + size
    return result


def car_pairs(entries):
    if len(entries) % 2:
        raise ValueError('Car archive has unpaired entries')
    pairs = []
    for i in range(0, len(entries), 2):
        texture, model = entries[i:i + 2]
        if not texture['data'].startswith(TEX_MAGIC) or not model['data'].startswith(CAR_MAGIC):
            raise ValueError('Car pair signature or order mismatch')
        pairs.append((texture, model))
    return pairs
