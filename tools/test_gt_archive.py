"""Synthetic fixtures and mutation controls for lossless GT1 extraction."""
import json
from pathlib import Path
import struct
import tempfile
import unittest
from unittest.mock import patch

import extract_gt_cars as extractor
from gt_archive import ARC_MAGIC, CAR_MAGIC, TEX_MAGIC, Disc, SYNC, archive_entries, car_pairs, decompress


def literal(data):
    return b''.join(b'\x00' + data[i:i + 8] for i in range(0, len(data), 8))


def archive(payloads, compressed=False):
    result = bytearray(ARC_MAGIC + struct.pack('<HH', 0x8001 if compressed else 1, len(payloads)))
    offset = 16 + len(payloads) * 12
    stored = [literal(p) if compressed else p for p in payloads]
    for raw, data in zip(payloads, stored):
        result += struct.pack('<III', offset, len(data), len(raw))
        offset += len(data)
    return bytes(result) + b''.join(stored)


def endian(value, width=4):
    return value.to_bytes(width, 'little') + value.to_bytes(width, 'big')


def directory_record(name, lba, size, flags=0):
    size_record = 33 + len(name) + (0 if len(name) % 2 else 1)
    record = bytearray(size_record)
    record[0] = size_record
    record[2:10] = endian(lba)
    record[10:18] = endian(size)
    record[25] = flags
    record[28:32] = endian(1, 2)
    record[32] = len(name)
    record[33:33 + len(name)] = name
    return bytes(record)


def image_bytes(raw=False):
    data = bytearray(40 * 2048)
    pvd = bytearray(2048)
    pvd[:7] = b'\x01CD001\x01'
    pvd[40:72] = b'TEST_GT'.ljust(32)
    pvd[80:88] = endian(40)
    pvd[128:132] = endian(2048, 2)
    pvd[156:190] = directory_record(b'\x00', 20, 2048, 2)
    data[16 * 2048:17 * 2048] = pvd
    files = [('CAR.DAT;1', archive([TEX_MAGIC + b'textures', CAR_MAGIC + b'model'], True)),
             ('CARCADE.DAT;1', archive([TEX_MAGIC + b'arcade', CAR_MAGIC + b'model2'], True)),
             ('CARINF.DAT;1', literal(archive([b'@(#)SPEC\x00test']))),
             ('SYSTEM.CNF;1', b'BOOT = TEST.EXE;1\r\n')]
    records = directory_record(b'\x00', 20, 2048, 2) + directory_record(b'\x01', 20, 2048, 2)
    for i, (name, payload) in enumerate(files):
        lba = 21 + i
        records += directory_record(name.encode(), lba, len(payload))
        data[lba * 2048:lba * 2048 + len(payload)] = payload
    data[20 * 2048:20 * 2048 + len(records)] = records
    if not raw:
        return bytes(data)
    return b''.join(SYNC + b'\x00\x02\x00\x02' + b'\x00\x00\x08\x00' * 2 + data[i:i + 2048] + bytes(280)
                    for i in range(0, len(data), 2048))


class GTArchiveTests(unittest.TestCase):
    def test_literals_short_extended_and_overlapping_matches(self):
        self.assertEqual(decompress(literal(b'abcdefghijk'), 11), b'abcdefghijk')
        self.assertEqual(decompress(b'\x08abc\x03\x02', 9), b'abcabcabc')
        self.assertEqual(decompress(b'\x08abc\x03\x80\x02', 9), b'abcabcabc')
        self.assertEqual(decompress(b'\x02a\x05\x00', 9), b'a' * 9)

    def test_compression_tamper_controls(self):
        controls = [(b'\x01\x00', None, 'truncated match'),
                    (b'\x01\x00\x00', None, 'before output'),
                    (b'\x02a\x00\x80', None, 'extended distance'),
                    (literal(b'ab'), 3, 'size mismatch'),
                    (literal(b'ab'), 1, 'exceeds declared'),
                    (b'\x00', None, 'dangling flag'),
                    (b'\x02a\xff\x00', 5, 'exceeds declared')]
        for data, expected, reason in controls:
            with self.subTest(reason=reason), self.assertRaisesRegex(ValueError, reason):
                decompress(data, expected)

    def test_archive_pair_order_bounds_sizes_and_type(self):
        data = archive([TEX_MAGIC, CAR_MAGIC], True)
        self.assertEqual(len(car_pairs(archive_entries(data))), 1)
        self.assertEqual(archive_entries(archive([CAR_MAGIC]))[0]['data'], CAR_MAGIC)
        # A compressed stream can have equal stored/decoded lengths: type owns routing.
        equal = b'\x08abc\x00\x02'  # Six stored, six decoded, then three literal bytes.
        equal += b'xyz'
        raw = ARC_MAGIC + struct.pack('<HHIII', 0x8001, 1, 28, len(equal), 9) + equal
        self.assertEqual(archive_entries(raw)[0]['data'], b'abcabcxyz')
        for offset, value, reason in [(16, 15, 'overlaps'), (20, len(data), 'archive end'),
                                      (24, 1, 'exceeds declared')]:
            broken = bytearray(data)
            struct.pack_into('<I', broken, offset, value)
            with self.assertRaisesRegex(ValueError, reason):
                archive_entries(broken)
        with self.assertRaisesRegex(ValueError, 'order mismatch'):
            car_pairs(archive_entries(archive([CAR_MAGIC, TEX_MAGIC])))
        with self.assertRaisesRegex(ValueError, 'unpaired'):
            car_pairs(archive_entries(archive([CAR_MAGIC])))
        with self.assertRaisesRegex(ValueError, 'directory'):
            archive_entries(ARC_MAGIC + b'\xff\xff\x01\x00' + bytes(12))

    def test_iso_cooked_and_raw_extraction_and_idempotent_checks(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            for raw in (False, True):
                image = root / f'{raw}.bin'
                image.write_bytes(image_bytes(raw))
                destination = root / str(raw)
                destination.mkdir()  # User supplied empty directory.
                index, _ = extractor.extract(image, destination)
                self.assertEqual(index['car_pairs'], 2)
                self.assertEqual(index['metadata_sections'], 1)
                extractor.extract(image, destination, check=True)
                with self.assertRaisesRegex(ValueError, 'nonempty'):
                    extractor.extract(image, destination)
                target = destination / 'simulation/pair-0000/model.car'
                target.write_bytes(CAR_MAGIC + b'altered')
                manifest = destination / 'simulation/pair-0000/manifest.json'
                value = json.loads(manifest.read_text())
                value['assets'][1]['sha256'] = 'attacker-rehashed-manifest'
                manifest.write_text(json.dumps(value))
                with self.assertRaisesRegex(ValueError, 'byte mismatch'):
                    extractor.extract(image, destination, check=True)
                with self.assertRaisesRegex(ValueError, 'Unsafe'):
                    extractor.extract(image, root)

    def test_iso_endian_form2_sync_and_truncation_controls(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / 'disc.bin'
            for raw, offset, byte, reason in [(False, 16 * 2048 + 87, 0, 'endian'),
                                              (True, 16 * 2352, 1, 'sync'),
                                              (True, 16 * 2352 + 18, 0x28, 'sector mode')]:
                damaged = bytearray(image_bytes(raw))
                damaged[offset] = byte
                path.write_bytes(damaged)
                with self.subTest(reason=reason), self.assertRaisesRegex(ValueError, reason):
                    Disc(path)
            path.write_bytes(image_bytes(True)[:-1])
            with self.assertRaisesRegex(ValueError, 'Truncated disc'):
                Disc(path)

    def test_source_mapping_is_pinned_and_bounded(self):
        self.assertEqual(len(extractor.names_for_disc(b'SCUS_941.94;1', [None] * 1376)), 1376)
        self.assertEqual(extractor.names_for_disc(b'UNKNOWN;1', [None] * 1376), {})
        with self.assertRaisesRegex(ValueError, 'coverage'):
            extractor.names_for_disc(b'SCUS_941.94;1', [None] * 2)
        with patch('extract_gt_cars.NAMES') as names:
            names.read_bytes.return_value = b'mutated-map'
            with self.assertRaisesRegex(ValueError, 'hash mismatch'):
                extractor.names_for_disc(b'SCUS_941.94;1', [None] * 1376)


if __name__ == '__main__':
    unittest.main()
