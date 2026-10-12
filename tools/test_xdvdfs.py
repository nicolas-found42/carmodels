"""XDVDFS reader controls on synthetic images: tree walk, payload reads and malformed tables."""
from pathlib import Path
import struct
import tempfile
import unittest

from xdvdfs import MAGIC, SECTOR, XdvdfsDisc


def directory_table(records):
    """records: (name, sector, size, attributes). A right-leaning tree: each record links the next."""
    table, offsets = bytearray(), []
    for name, *_ in records:
        length = (14 + len(name) + 3) & ~3
        if len(table) // SECTOR != (len(table) + length - 1) // SECTOR:
            table += b'\xff' * (SECTOR - len(table) % SECTOR)
        offsets.append(len(table))
        table += bytes(length)
    for i, (name, sector, size, attributes) in enumerate(records):
        right = offsets[i + 1] // 4 if i + 1 < len(records) else 0
        struct.pack_into('<HHIIBB', table, offsets[i], 0, right, sector, size, attributes, len(name))
        table[offsets[i] + 14:offsets[i] + 14 + len(name)] = name.encode()
    return bytes(table)


def disc_fixture(files, directories=None):
    """files: [(name, payload)] in the root; directories: {name: [(name, payload)]} one level deep."""
    directories = directories or {}
    sector = 34
    blobs, root = {}, []

    def place(data):
        nonlocal sector
        at = sector
        blobs[at] = data
        sector += max(1, (len(data) + SECTOR - 1) // SECTOR)
        return at
    for name, children in directories.items():
        entries = [(child, place(data), len(data), 0x20) for child, data in children]
        table = directory_table(entries)
        root.append((name, place(table), len(table), 0x10))
    root += [(name, place(data), len(data), 0x20) for name, data in files]
    table = directory_table(root)
    root_sector = place(table)
    image = bytearray(sector * SECTOR)
    descriptor = MAGIC + struct.pack('<IIQ', root_sector, len(table), 0)
    image[32 * SECTOR:32 * SECTOR + len(descriptor)] = descriptor
    image[32 * SECTOR + 0x7EC:33 * SECTOR] = MAGIC
    for at, data in blobs.items():
        image[at * SECTOR:at * SECTOR + len(data)] = data
    return bytes(image)


class XdvdfsTests(unittest.TestCase):
    def open(self, image):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        path = Path(temp.name) / 'disc.iso'
        path.write_bytes(image)
        disc = XdvdfsDisc(path)
        self.addCleanup(disc.close)
        return disc

    def test_lists_tree_and_reads_payloads(self):
        disc = self.open(disc_fixture([('default.xex', b'XEX2 body'), ('b.bin', b'')],
                                      {'media': [('movie.bik', b'BIK' * 1000)]}))
        self.assertEqual(disc.generation, 'plain')
        paths = {e['path']: e for e in disc.entries}
        self.assertEqual(sorted(paths), ['b.bin', 'default.xex', 'media/', 'media/movie.bik'])
        self.assertEqual(disc.region(paths['media/movie.bik'])(0, 3000), b'BIK' * 1000)
        with self.assertRaisesRegex(ValueError, 'outside XDVDFS file'):
            disc.region(paths['default.xex'])(5, 5)

    def test_rejects_malformed_images(self):
        good = disc_fixture([('a.bin', b'abc')])
        with self.assertRaisesRegex(ValueError, 'no XDVDFS volume descriptor'):
            self.open(bytes(len(good)))
        trailer = bytearray(good)
        trailer[33 * SECTOR - 1] ^= 1
        with self.assertRaisesRegex(ValueError, 'trailer mismatch'):
            self.open(bytes(trailer))
        with self.assertRaisesRegex(ValueError, 'truncated'):
            self.open(good[:-1])
        root = struct.unpack_from('<I', good, 32 * SECTOR + 20)[0] * SECTOR
        cyclic = bytearray(disc_fixture([('a.bin', b'abc'), ('b.bin', b'def')]))
        croot = struct.unpack_from('<I', cyclic, 32 * SECTOR + 20)[0] * SECTOR
        second = struct.unpack_from('<H', cyclic, croot + 2)[0] * 4
        struct.pack_into('<H', cyclic, croot + second + 2, second // 4)  # second record links itself
        with self.assertRaisesRegex(ValueError, 'tree cycle'):
            self.open(bytes(cyclic))
        outside = bytearray(good)
        struct.pack_into('<I', outside, root + 8, 10 ** 6)
        with self.assertRaisesRegex(ValueError, 'file outside disc'):
            self.open(bytes(outside))
        unsafe = bytearray(good)
        struct.pack_into('B', unsafe, root + 13, 2)
        unsafe[root + 14:root + 16] = b'..'
        with self.assertRaisesRegex(ValueError, 'unsafe XDVDFS name'):
            self.open(bytes(unsafe))

    def test_rejects_overlapping_extents(self):
        image = bytearray(disc_fixture([('a.bin', b'a' * 3000), ('b.bin', b'b' * 10)]))
        root = struct.unpack_from('<I', image, 32 * SECTOR + 20)[0] * SECTOR
        second = struct.unpack_from('<H', image, root + 2)[0] * 4
        first_sector = struct.unpack_from('<I', image, root + 4)[0]
        struct.pack_into('<I', image, root + second + 4, first_sector + 1)
        with self.assertRaisesRegex(ValueError, 'overlapping'):
            self.open(bytes(image))


if __name__ == '__main__':
    unittest.main()
