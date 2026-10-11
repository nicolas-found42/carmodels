"""Format controls for ISO tables, packed names and raw DEFLATE."""
import struct
from pathlib import Path
import tempfile
import unittest
import zlib

from mc3_archive import CHARS, CookedDisc, DaveArchive, byte_reader, packed_name
from test_gt_archive import directory_record, endian


def symbol_bytes(symbols):
    symbols = symbols + [0] * ((-len(symbols)) % 4)
    return b''.join(sum(v << (6 * j) for j, v in enumerate(symbols[i:i + 4])).to_bytes(3, 'little')
                    for i in range(0, len(symbols), 4))


def archive_fixture(entries, packed=False, compressed=False):
    """Construct native records independently, preserving duplicate names."""
    names, table, payload = bytearray(), bytearray(), bytearray()
    info = ((len(entries) * 16 + 2047) // 2048) * 2048
    offsets = []
    previous = ''
    for name, _ in entries:
        offsets.append(len(names))
        if packed:
            prefix = 0
            while prefix < min(len(previous), len(name)) and previous[prefix] == name[prefix]:
                prefix += 1
            symbols = ([56 + prefix % 8, 32 + prefix // 8] if prefix else [])
            symbols += [CHARS.index(c) for c in name[prefix:]] + [0]
            names.extend(symbol_bytes(symbols))
        else:
            names.extend(name.encode('ascii') + b'\0')
        previous = name
    names.extend(bytes((-len(names)) % 2048))
    start = 2048 + info + len(names)
    for (name, data), no in zip(entries, offsets):
        if compressed and data:
            compressor = zlib.compressobj(wbits=-15)
            encoded = compressor.compress(data) + compressor.flush()
        else:
            encoded = data
        table.extend(struct.pack('<4I', no, start + len(payload), len(data), len(encoded)))
        payload.extend(encoded)
    table.extend(bytes(info - len(table)))
    return (struct.pack('<4sIII', b'Dave' if packed else b'DAVE', len(entries), info, len(names))
            + bytes(2032) + table + names + payload)


def iso_fixture(files):
    lba, rows = 21, []
    for name, payload in files:
        rows.append((name, payload, lba))
        lba += (len(payload) + 2047) // 2048
    data = bytearray(lba * 2048)
    pvd = bytearray(2048)
    pvd[:7] = b'\x01CD001\x01'
    pvd[40:72] = b'MC3_TEST'.ljust(32)
    pvd[80:88] = endian(lba)
    pvd[128:132] = endian(2048, 2)
    pvd[156:190] = directory_record(b'\0', 20, 2048, 2)
    data[16 * 2048:17 * 2048] = pvd
    records = directory_record(b'\0', 20, 2048, 2) + directory_record(b'\1', 20, 2048, 2)
    for name, payload, address in rows:
        records += directory_record(name.encode(), address, len(payload))
        data[address * 2048:address * 2048 + len(payload)] = payload
    data[20 * 2048:20 * 2048 + len(records)] = records
    return bytes(data)


class ArchiveTests(unittest.TestCase):
    def test_plain_packed_prefix_duplicate_and_directory(self):
        entries = [('vehicle/', b''), ('vehicle/a.mesh', b'abc' * 80),
                   ('vehicle/a.mesh', b'second distinct payload'), ('vehicle/b.tex', b'xyz' * 80)]
        for packed in (False, True):
            for compressed in (False, True):
                with self.subTest(packed=packed, compressed=compressed):
                    data = archive_fixture(entries, packed, compressed)
                    arc = DaveArchive(byte_reader(data), len(data))
                    self.assertEqual([r['name'] for r in arc.records], [e[0] for e in entries])
                    self.assertEqual([arc.payload(r) for r in arc.records], [e[1] for e in entries])
                    self.assertEqual(arc.records[2]['ordinal'], 2)

    def test_packed_name_failures(self):
        cases = [(symbol_bytes([56, 33, 0]), '', 'invalid name prefix'),
                 (symbol_bytes([49, 0]), '', 'invalid packed name symbol'),
                 (b'\xff', '', 'truncated packed name'),
                 (symbol_bytes([1] * 340), '', 'unterminated packed name')]
        for data, previous, reason in cases:
            with self.subTest(reason=reason), self.assertRaisesRegex(ValueError, reason):
                packed_name(data, 0, previous)

    def test_table_path_extent_size_controls(self):
        original = archive_fixture([('vehicle/a.mesh', b'abc')])
        cases = [('unsupported DAVE magic', 0, b'FAIL'),
                 ('invalid DAVE table sizes', 8, struct.pack('<I', 1)),
                 ('name offset outside block', 2048, struct.pack('<I', 2048)),
                 ('member outside archive', 2052, struct.pack('<I', 1)),
                 ('invalid member sizes', 2056, struct.pack('<I', 0xFFFFFFFF))]
        for reason, offset, value in cases:
            changed = bytearray(original); changed[offset:offset + len(value)] = value
            with self.subTest(reason=reason), self.assertRaisesRegex(ValueError, reason):
                DaveArchive(byte_reader(changed), len(changed))
        for name in ('../a', '/a', 'vehicle//a', 'a\\b', 'C:/a', 'a\x7f'):
            data = archive_fixture([(name, b'abc')])
            with self.subTest(name=name), self.assertRaisesRegex(ValueError, 'unsafe archive name'):
                DaveArchive(byte_reader(data), len(data))

    def test_deflate_truncation_trailing_and_declared_size(self):
        original = archive_fixture([('vehicle/a.mesh', b'abc' * 100)], compressed=True)
        for change in ('truncated', 'trailing', 'wrong_size', 'bomb'):
            data = bytearray(original)
            if change == 'trailing':
                data.extend(b'!'); struct.pack_into('<I', data, 2060, struct.unpack_from('<I', data, 2060)[0] + 1)
            elif change == 'truncated':
                data[-1] = 255
            else:
                struct.pack_into('<I', data, 2056, 299 if change == 'wrong_size' else 2)
            arc = DaveArchive(byte_reader(data), len(data))
            with self.subTest(change=change), self.assertRaisesRegex(ValueError, 'DEFLATE'):
                arc.payload(arc.records[0])

    def test_iso_tilde_endian_extent_and_preservation(self):
        original = iso_fixture([('EUROPE~1.PF;1', b'hello')])
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / 'input.iso'; path.write_bytes(original)
            disc = CookedDisc(path)
            self.assertEqual(disc.entries[0]['path'], 'EUROPE~1.PF;1')
            self.assertEqual(disc.region(disc.entries[0])(0, 5), b'hello')
            with self.assertRaisesRegex(ValueError, 'outside ISO member'):
                disc.region(disc.entries[0])(4, 2)
            disc.close()
            self.assertEqual(path.read_bytes(), original)
            changed = bytearray(original); changed[16 * 2048 + 84] ^= 1; path.write_bytes(changed)
            with self.assertRaisesRegex(ValueError, 'endian copies'):
                CookedDisc(path)
            path.write_bytes(original[:-1])
            with self.assertRaisesRegex(ValueError, 'truncated cooked disc'):
                CookedDisc(path)


if __name__ == '__main__':
    unittest.main()
