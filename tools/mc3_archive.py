"""Read-only cooked ISO and DAVE/Dave archive parsers for MC3 Remix.

Layout cross-checked against EdnessP/scripts midnight-club/dave.py. Packed
names depend on the preceding table entry. Duplicate names remain distinct.
"""
from pathlib import Path
import struct
import zlib

from gt_archive import both_endian, file_digest

CHARS = '\x00 #$()-./?0123456789_abcdefghijklmnopqrstuvwxyz~\x7f'
MAX_MEMBER = 256 * 1024 * 1024


def safe_name(name, directory=False):
    path = name[:-1] if directory and name.endswith('/') else name
    if (not path or len(path) > 240 or '\\' in path
            or any(ord(c) < 32 or ord(c) > 126 for c in path)
            or any(p in ('', '.', '..') or ':' in p for p in path.split('/'))):
        raise ValueError('unsafe archive name')
    return path


class CookedDisc:
    """ISO9660 user sectors only; no raw-sector or UDF interpretation."""

    def __init__(self, path):
        self.path = Path(path)
        if self.path.is_symlink():
            raise ValueError('linked disc input')
        self.stream = self.path.open('rb')
        self.size = self.path.stat().st_size
        try:
            if self.size % 2048:
                raise ValueError('truncated cooked disc')
            pvd = self.read_at(16 * 2048, 2048)
            if pvd[:7] != b'\x01CD001\x01' or both_endian(pvd, 128, 2) != 2048:
                raise ValueError('unsupported ISO descriptor')
            self.volume_sectors = both_endian(pvd, 80)
            if not 17 <= self.volume_sectors <= self.size // 2048:
                raise ValueError('ISO volume outside disc')
            self.volume = pvd[40:72].decode('ascii').rstrip()
            self.entries = []
            self._walk(both_endian(pvd, 158), both_endian(pvd, 166), '', set())
        except Exception:
            self.close()
            raise

    def close(self):
        self.stream.close()

    def read_at(self, offset, size):
        if offset < 0 or size < 0 or offset + size > self.size:
            raise ValueError('read outside disc')
        self.stream.seek(offset)
        data = self.stream.read(size)
        if len(data) != size:
            raise ValueError('truncated disc read')
        return data

    def region(self, entry):
        start, size = entry['lba'] * 2048, entry['size']

        def read(offset, count):
            if offset < 0 or count < 0 or offset + count > size:
                raise ValueError('read outside ISO member')
            return self.read_at(start + offset, count)
        return read

    def _walk(self, lba, size, parent, seen):
        if (lba, size) in seen or len(seen) >= 128 or size > 1024 * 1024:
            raise ValueError('ISO directory cycle or limit')
        seen.add((lba, size))
        if lba + (size + 2047) // 2048 > self.volume_sectors:
            raise ValueError('ISO directory outside volume')
        data = self.read_at(lba * 2048, size)
        pos = 0
        while pos < len(data):
            length = data[pos]
            if not length:
                pos = (pos // 2048 + 1) * 2048
                continue
            if length < 34 or pos + length > len(data) or pos % 2048 + length > 2048:
                raise ValueError('invalid ISO directory record')
            record = data[pos:pos + length]
            pos += length
            n = record[32]
            if n == 0 or n + 33 > length:
                raise ValueError('invalid ISO filename length')
            name = record[33:33 + n]
            if name in (b'\0', b'\1'):
                continue
            name = name.decode('ascii')
            safe_name(name)
            if record[1] or record[26] or record[27] or record[25] & ~3:
                raise ValueError('unsupported ISO extent flags')
            if both_endian(record, 28, 2) != 1:
                raise ValueError('unsupported ISO volume sequence')
            entry = {'path': parent + name, 'lba': both_endian(record, 2),
                     'size': both_endian(record, 10), 'directory': bool(record[25] & 2)}
            if entry['lba'] + (entry['size'] + 2047) // 2048 > self.volume_sectors:
                raise ValueError('ISO extent outside volume')
            if any(e['path'].casefold() == entry['path'].casefold() for e in self.entries):
                raise ValueError('duplicate ISO path')
            self.entries.append(entry)
            if len(self.entries) > 10000:
                raise ValueError('ISO inventory limit')
            if entry['directory']:
                self._walk(entry['lba'], entry['size'], entry['path'] + '/', seen)


def byte_reader(data):
    def read(offset, size):
        if offset < 0 or size < 0 or offset + size > len(data):
            raise ValueError('read outside archive')
        return data[offset:offset + size]
    return read


def packed_name(data, offset, previous):
    """Four six-bit symbols per three-byte word, bounded by the name block."""
    symbols = []
    while len(symbols) < 340:
        if offset + 3 > len(data):
            raise ValueError('truncated packed name')
        word = int.from_bytes(data[offset:offset + 3], 'little')
        offset += 3
        symbols.extend((word >> (6 * i)) & 63 for i in range(4))
        if 0 in symbols:
            break
    else:
        raise ValueError('unterminated packed name')
    name = ''
    if symbols[0] >= 56:
        prefix = (symbols[1] - 32) * 8 + symbols[0] - 56
        if not 0 <= prefix <= len(previous):
            raise ValueError('invalid name prefix')
        name = previous[:prefix]
        symbols = symbols[2:]
    for symbol in symbols:
        if symbol == 0:
            return name
        if symbol >= len(CHARS):
            raise ValueError('invalid packed name symbol')
        name += CHARS[symbol]
    raise ValueError('unterminated packed name')


class DaveArchive:
    def __init__(self, read, size):
        self.read, self.size = read, size
        head = read(0, 16)
        self.magic, count, info_size, name_size = struct.unpack('<4sIII', head)
        if self.magic not in (b'DAVE', b'Dave'):
            raise ValueError('unsupported DAVE magic')
        if (not 1 <= count <= 100000 or info_size < count * 16
                or info_size % 2048 or name_size % 2048
                or not 0 < name_size <= 4 * 1024 * 1024
                or info_size > 2 * 1024 * 1024):
            raise ValueError('invalid DAVE table sizes')
        self.payload_start = 2048 + info_size + name_size
        if self.payload_start > size:
            raise ValueError('DAVE tables outside archive')
        table = read(2048, count * 16)
        names = read(2048 + info_size, name_size)
        self.records, previous = [], ''
        for i in range(count):
            no, offset, full, stored = struct.unpack_from('<4I', table, i * 16)
            if no >= len(names):
                raise ValueError('name offset outside block')
            if self.magic == b'DAVE':
                end = names.find(b'\0', no)
                if end < 0 or end - no > 240:
                    raise ValueError('unterminated ASCII name')
                name = names[no:end].decode('ascii')
            else:
                name = packed_name(names, no, previous)
            previous = name
            directory = name.endswith('/')
            safe_name(name, directory)
            if full > MAX_MEMBER or stored > MAX_MEMBER or (full == 0) != (stored == 0):
                raise ValueError('invalid member sizes')
            if offset < self.payload_start or offset + stored > size:
                raise ValueError('member outside archive payload')
            if directory and (full or stored):
                raise ValueError('directory has payload')
            self.records.append({'ordinal': i, 'name': name, 'name_offset': no,
                                 'offset': offset, 'size': full, 'stored': stored,
                                 'directory': directory})

    def payload(self, record):
        data = self.read(record['offset'], record['stored'])
        if record['size'] == record['stored']:
            return data
        try:
            decoder = zlib.decompressobj(-15)
            result = decoder.decompress(data, record['size'] + 1)
        except zlib.error as error:
            raise ValueError('invalid DEFLATE stream') from error
        if (len(result) != record['size'] or not decoder.eof
                or decoder.unused_data or decoder.unconsumed_tail):
            raise ValueError('DEFLATE length, termination or trailing data mismatch')
        return result


__all__ = ['CookedDisc', 'DaveArchive', 'byte_reader', 'file_digest', 'safe_name']
