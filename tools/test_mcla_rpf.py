"""RPF3 reader controls on synthetic archives: tree, encryption, DEFLATE, resources and malformed tables."""
import struct
import unittest
import zlib

from mcla_rpf import RSC5, Rpf3Archive, jenkins, physical_size, virtual_size
from test_aes_decrypt import AesEncryptor

KEY = bytes(range(32))


def deflate(data):
    packer = zlib.compressobj(9, zlib.DEFLATED, -15)
    return packer.compress(data) + packer.flush()


def encrypt16(table, key):
    aes = AesEncryptor(key)
    for _ in range(16):
        table = aes.ecb(table)
    return table


def rpf_fixture(tree, key=None):
    """tree: {name: subtree-dict | ('loose', bytes) | ('deflate', bytes) | ('resource', type, bytes)}."""
    entries, blobs = [None], []
    queue = [(0, tree)]
    while queue:
        index, children = queue.pop(0)
        first = len(entries)
        names = sorted(children)
        entries.extend([None] * len(names))
        entries[index] = ('directory', 0 if index == 0 else entries[index][1], first, len(names))
        for offset, name in enumerate(names):
            child = children[name]
            if isinstance(child, dict):
                entries[first + offset] = ('directory', jenkins(name), None, None)
                queue.append((first + offset, child))
            else:
                entries[first + offset] = ('file', jenkins(name), child)
                blobs.append(first + offset)
    toc = bytearray(16 * len(entries))
    data, position = bytearray(), (0x800 + len(toc) + 0x7FF) & ~0x7FF
    placed = {}
    for index in blobs:
        _, _, spec = entries[index]
        stored = deflate(spec[1]) if spec[0] == 'deflate' else spec[2] if spec[0] == 'resource' else spec[1]
        placed[index] = position
        data += stored + bytes((-len(stored)) % 0x800)
        position += len(stored) + (-len(stored)) % 0x800
    for index, entry in enumerate(entries):
        if entry[0] == 'directory':
            struct.pack_into('<IIII', toc, 16 * index, entry[1], 0, 0x80000000 | entry[2], entry[3])
            continue
        spec, at = entry[2], placed[index]
        if spec[0] == 'resource':
            flag = 0xC0000000 | (spec[3] if len(spec) > 3 else 0)
            struct.pack_into('<IIII', toc, 16 * index, entry[1], len(spec[2]), at | spec[1], flag)
        elif spec[0] == 'deflate':
            struct.pack_into('<IIII', toc, 16 * index, entry[1], len(spec[1]), at, 0x40000000 | len(deflate(spec[1])))
        else:
            struct.pack_into('<IIII', toc, 16 * index, entry[1], len(spec[1]), at, len(spec[1]))
    table = encrypt16(bytes(toc), key) if key else bytes(toc)
    header = struct.pack('<4sIIIi', b'RPF3', len(table), len(entries), 0, -1 if key else 0)
    image = bytearray(header + bytes(0x800 - len(header)) + table)
    image += bytes((-len(image)) % 0x800)
    image += data
    return bytes(image)


TREE = {'resources': {'vehicle': {'vp_test_car_01': {'body_lod_0.xrsc': ('resource', 63, RSC5 + b'\0\0\0\x3f model'),
                                                     'vp_test_car_01.xct': ('resource', 50, RSC5 + b' tune')}},
                      'notes.xml': ('deflate', b'<names>vp_test_car_01</names>' * 20)},
        'readme.txt': ('loose', b'plain')}


def opened(image, key=None):
    return Rpf3Archive(lambda o, s: image[o:o + s], len(image), key)


class Rpf3Tests(unittest.TestCase):
    def test_jenkins_one_at_a_time_vectors(self):
        self.assertEqual(jenkins('a'), 0xCA2E9442)
        self.assertEqual(jenkins('VP_Test'), jenkins('vp_test'))

    def test_reads_tree_payloads_and_encrypted_tables(self):
        for key in (None, KEY):
            archive = opened(rpf_fixture(TREE, key), key)
            self.assertEqual(archive.encrypted, key is not None)
            by_hash = {e['hash']: e for e in archive.entries}
            notes = by_hash[jenkins('notes.xml')]
            self.assertTrue(notes['compressed'])
            self.assertEqual(archive.payload(notes), TREE['resources']['notes.xml'][1])
            body = by_hash[jenkins('body_lod_0.xrsc')]
            self.assertEqual((body['resource'], body['resource_type']), (True, 63))
            self.assertEqual(archive.payload(body), archive.stored(body))
            car = by_hash[jenkins('vp_test_car_01')]
            self.assertEqual(body['parent'], car['index'])
            self.assertEqual(archive.payload(by_hash[jenkins('readme.txt')]), b'plain')

    def test_resource_size_words(self):
        # 3 << (2 + 8) virtual and 5 << (1 + 8) physical bytes.
        sizes = 3 | (2 << 11) | (5 << 15) | (1 << 26)
        self.assertEqual((virtual_size(sizes), physical_size(sizes)), (3072, 2560))
        self.assertEqual((virtual_size(0x7FF | (15 << 11)), physical_size(0x7FF << 15)), (0x7FF << 23, 0x7FF << 8))
        image = rpf_fixture({'a': {'b': {'deep.xrsc': ('resource', 63, RSC5 + b'x', sizes)}}})
        archive = opened(image)
        deep = archive.entries[-1]
        self.assertEqual((deep['virtual'], deep['physical'], deep['resource_type']), (3072, 2560, 63))
        chain = []
        while deep['parent'] is not None:
            chain.append(deep['hash'])
            deep = archive.entries[deep['parent']]
        self.assertEqual(chain, [jenkins('deep.xrsc'), jenkins('b'), jenkins('a')])

    def test_rejects_wrong_key_and_missing_key(self):
        image = rpf_fixture(TREE, KEY)
        with self.assertRaisesRegex(ValueError, 'needs the AES key'):
            opened(image)
        with self.assertRaisesRegex(ValueError, 'root is not a directory|outside|unreachable|two parents'):
            opened(image, bytes(32))

    def test_rejects_malformed_tables_and_payloads(self):
        image = bytearray(rpf_fixture(TREE))
        with self.assertRaisesRegex(ValueError, 'not an RPF3'):
            opened(b'RPF2' + bytes(image[4:]))
        with self.assertRaisesRegex(ValueError, 'smaller than its header page'):
            opened(bytes(image[:0x7FF]))
        rootless = bytearray(image)
        struct.pack_into('<I', rootless, 0x800 + 8, 0)  # entry 0 decodes as a file
        with self.assertRaisesRegex(ValueError, 'root is not a directory'):
            opened(bytes(rootless))
        short = bytearray(image)
        struct.pack_into('<I', short, 4, 16)  # table smaller than its entry count
        with self.assertRaisesRegex(ValueError, 'table outside archive'):
            opened(bytes(short))
        orphan = bytearray(image)
        struct.pack_into('<I', orphan, 0x800 + 12, 1)  # root claims only its first child
        with self.assertRaisesRegex(ValueError, 'unreachable'):
            opened(bytes(orphan))
        archive = opened(bytes(image))
        vehicle = next(e for e in archive.entries if e['hash'] == jenkins('vehicle'))
        twice = bytearray(image)
        # 'vehicle' claims one entry more, which is the first child of its own sub-directory.
        struct.pack_into('<I', twice, 0x800 + 16 * vehicle['index'] + 12, vehicle['children'] + 1)
        with self.assertRaisesRegex(ValueError, 'two parents'):
            opened(bytes(twice))
        overrun = bytearray(image)
        struct.pack_into('<I', overrun, 0x800 + 16 * vehicle['index'] + 12, 1000)  # more children than entries
        with self.assertRaisesRegex(ValueError, 'children outside table'):
            opened(bytes(overrun))
        archive = opened(bytes(image))
        notes = next(e for e in archive.entries if e['hash'] == jenkins('notes.xml'))
        outside = bytearray(image)
        struct.pack_into('<I', outside, 0x800 + 16 * notes['index'] + 8, len(image))
        with self.assertRaisesRegex(ValueError, 'file outside archive'):
            opened(bytes(outside))
        resized = bytearray(image)
        struct.pack_into('<I', resized, 0x800 + 16 * notes['index'] + 4, notes['size'] + 1)
        reopened = opened(bytes(resized))
        with self.assertRaisesRegex(ValueError, 'deflate size mismatch'):
            reopened.payload(reopened.entries[notes['index']])
        readme = next(e for e in archive.entries if e['hash'] == jenkins('readme.txt'))
        longer = bytearray(image)
        struct.pack_into('<I', longer, 0x800 + 16 * readme['index'] + 4, readme['size'] + 1)
        reopened = opened(bytes(longer))
        with self.assertRaisesRegex(ValueError, 'stored size differs from file size'):
            reopened.payload(reopened.entries[readme['index']])
        body = next(e for e in archive.entries if e['hash'] == jenkins('body_lod_0.xrsc'))
        stripped = bytearray(image)
        stripped[body['offset']:body['offset'] + 4] = b'RSC7'
        with self.assertRaisesRegex(ValueError, 'without RSC5'):
            opened(bytes(stripped)).payload(body)


if __name__ == '__main__':
    unittest.main(verbosity=2)
