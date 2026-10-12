"""Read-only RPF3 reader for Midnight Club: Los Angeles (Xbox 360).

Format readings (independently written; CodeX.Games.MCLA `RPF3/Rpf3File.cs` at
dedc3156 was the format reference, no code copied), each checked by the reader:

- Header, little-endian: `RPF3`, table size, entry count, unknown, encryption flag.
  The table starts at 0x800. A nonzero flag means the table is AES-256-ECB
  encrypted sixteen times over its 16-byte-aligned prefix.
- 16-byte entries. A negative third word marks a directory: name hash, flags,
  first child index | 0x80000000, child count. Otherwise a file: name hash,
  size, offset, flag word. Flag bits 0xC0000000 both set mark an RSC resource
  whose offset carries the resource type in its low byte; otherwise bit
  0x40000000 marks raw-DEFLATE compression and the rest is the stored size.
- Names are 32-bit Jenkins one-at-a-time hashes; no names are stored.
"""
import struct
import zlib

from aes_decrypt import AesDecryptor

MAGIC = b'RPF3'
TOC_OFFSET = 0x800
ENTRY = 16
MAX_ENTRIES = 1_000_000
RESOURCE = 0xC0000000
COMPRESSED = 0x40000000
RSC5 = b'\x05CSR'  # reading of the resource magic as stored big-endian on this disc


def jenkins_partial(text, h=0):
    """Jenkins one-at-a-time mixing over lower-cased ASCII, resumable from a prefix state."""
    for byte in text.lower().encode('ascii'):
        h = (h + byte) & 0xFFFFFFFF
        h = (h + (h << 10)) & 0xFFFFFFFF
        h ^= h >> 6
    return h


def jenkins_final(h):
    h = (h + (h << 3)) & 0xFFFFFFFF
    h ^= h >> 11
    return (h + (h << 15)) & 0xFFFFFFFF


def jenkins(text):
    """The RAGE name hash: Jenkins one-at-a-time over lower-cased ASCII."""
    return jenkins_final(jenkins_partial(text))


def aes_ecb_decrypt16(data, key):
    """Sixteen AES-256-ECB decryption passes over the 16-byte-aligned prefix."""
    aligned = len(data) & ~15
    aes, body = AesDecryptor(key), data[:aligned]
    for _ in range(16):
        body = aes.ecb(body)
    return body + data[aligned:]


def virtual_size(flag):
    return (flag & 0x7FF) << (((flag >> 11) & 15) + 8)


def physical_size(flag):
    return ((flag >> 15) & 0x7FF) << (((flag >> 26) & 15) + 8)


class Rpf3Archive:
    """Lists entries of one RPF3 image held behind `read(offset, size)`."""

    def __init__(self, read, size, key=None):
        self.read, self.size = read, size
        if size < TOC_OFFSET:
            raise ValueError('RPF3 smaller than its header page')
        magic, toc_size, count, self.unknown, encrypted = struct.unpack('<4sIIIi', read(0, 20))
        if magic != MAGIC:
            raise ValueError('not an RPF3 archive')
        if not 0 < count <= MAX_ENTRIES or count * ENTRY > toc_size or TOC_OFFSET + toc_size > size:
            raise ValueError('RPF3 table outside archive')
        self.encrypted = encrypted != 0
        table = read(TOC_OFFSET, toc_size)
        if self.encrypted:
            if key is None:
                raise ValueError('encrypted RPF3 table needs the AES key')
            table = aes_ecb_decrypt16(table, key)
        self.toc_size, self.count = toc_size, count
        self.entries = [self._entry(index, table[index * ENTRY:(index + 1) * ENTRY]) for index in range(count)]
        root = self.entries[0]
        if root['kind'] != 'directory':
            raise ValueError('RPF3 root is not a directory')
        self._link()

    def _entry(self, index, raw):
        name, a, b, c = struct.unpack('<IIII', raw)
        if b & 0x80000000:
            return {'index': index, 'kind': 'directory', 'hash': name, 'flags': a,
                    'first': b & 0x7FFFFFFF, 'children': c & 0x0FFFFFFF}
        entry = {'index': index, 'kind': 'file', 'hash': name, 'size': a, 'flag': c}
        if c & RESOURCE == RESOURCE:
            entry.update(resource=True, resource_type=b & 0xFF, offset=b & 0x7FFFFF00,
                         stored=a, virtual=virtual_size(c), physical=physical_size(c))
        else:
            entry.update(resource=False, offset=b, compressed=bool(c & COMPRESSED), stored=c & 0x3FFFFFFF)
        if entry['offset'] + entry['stored'] > self.size:
            raise ValueError('RPF3 file outside archive')
        return entry

    def _link(self):
        parents = {0: None}
        stack = [0]
        while stack:
            directory = self.entries[stack.pop()]
            first, count = directory['first'], directory['children']
            if first + count > self.count or (count and first <= directory['index']):
                raise ValueError('RPF3 directory children outside table')
            for child in range(first, first + count):
                if child in parents:
                    raise ValueError('RPF3 entry has two parents')
                parents[child] = directory['index']
                if self.entries[child]['kind'] == 'directory':
                    stack.append(child)
        if len(parents) != self.count:
            raise ValueError('RPF3 entries unreachable from root')
        for entry in self.entries:
            entry['parent'] = parents[entry['index']]

    def stored(self, entry):
        return self.read(entry['offset'], entry['stored'])

    def payload(self, entry):
        """Archive-level decoding only: raw DEFLATE is inflated; RSC resources stay as stored."""
        data = self.stored(entry)
        if entry['resource']:
            if data[:4] != RSC5:
                raise ValueError('RPF3 resource without RSC5 header')
            return data
        if not entry['compressed']:
            if len(data) != entry['size']:
                raise ValueError('RPF3 stored size differs from file size')
            return data
        inflater = zlib.decompressobj(-15)
        out = inflater.decompress(data, entry['size'] + 1)
        if len(out) != entry['size'] or inflater.unconsumed_tail or not inflater.eof:
            raise ValueError('RPF3 deflate size mismatch')
        return out
