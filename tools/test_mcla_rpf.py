"""RPF3 reader controls on synthetic archives: tree, encryption, DEFLATE, resources and malformed tables."""
import struct
import unittest
import zlib

from mcla_rpf import RSC5, Rpf3Archive, jenkins
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
        stored = deflate(spec[1]) if spec[0] == 'deflate' else spec[-1]
        placed[index] = position
        data += stored + bytes((-len(stored)) % 0x800)
        position += len(stored) + (-len(stored)) % 0x800
    for index, entry in enumerate(entries):
        if entry[0] == 'directory':
            struct.pack_into('<IIII', toc, 16 * index, entry[1], 0, 0x80000000 | entry[2], entry[3])
            continue
        spec, at = entry[2], placed[index]
        if spec[0] == 'resource':
            struct.pack_into('<IIII', toc, 16 * index, entry[1], len(spec[2]), at | spec[1], 0xC0000000)
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
        orphan = bytearray(image)
        struct.pack_into('<I', orphan, 0x800 + 12, 1)  # root claims only its first child
        with self.assertRaisesRegex(ValueError, 'unreachable'):
            opened(bytes(orphan))
        twice = bytearray(image)
        struct.pack_into('<I', twice, 0x800 + 16 + 8, 0x80000000 | 1)  # a child directory re-lists entry 1
        with self.assertRaisesRegex(ValueError, 'children outside table|two parents'):
            opened(bytes(twice))
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
        body = next(e for e in archive.entries if e['hash'] == jenkins('body_lod_0.xrsc'))
        stripped = bytearray(image)
        stripped[body['offset']:body['offset'] + 4] = b'RSC7'
        with self.assertRaisesRegex(ValueError, 'without RSC5'):
            opened(bytes(stripped)).payload(body)


if __name__ == '__main__':
    unittest.main()
