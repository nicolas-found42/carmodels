"""Read-only Gran Turismo 4 GT4.VOL (RoFS 3.1) parser.

Layout follows the published GT Modding Hub volume page and the GT4FS reader
(see research/gran-turismo-4-extraction.md for pinned sources). The volume begins
with a decoy GT3-style table; the real table is found by its RoFS 3.1 header.
Every table page and payload is bounds-checked; nothing here decodes models.
"""
import struct
import zlib

from mc3_archive import safe_name

ENCRYPTED_MAGIC = 0xAD90B9AC  # Bitwise NOT of 'RoFS', read big-endian.
PLAIN_MAGIC = 0x526F4653
VERSION_3_1 = 0x00030001
OFFSET_KEY = 0x14AC327A
PAGE_XOR = 0x55
PS2ZIP_MAGIC = 0xC5EEF7FF
SCAN_PAGES = 10000
MAX_PAYLOAD = 64 * 1024 * 1024
KINDS = {0: 'directory', 1: 'file', 2: 'compressed'}


def ps2zip_inflate(stored, size):
    """PS2Zip: magic, negated decoded size, then one raw DEFLATE stream."""
    if len(stored) < 8 or struct.unpack_from('>I', stored)[0] != PS2ZIP_MAGIC:
        raise ValueError('missing PS2Zip header')
    if -struct.unpack_from('<i', stored, 4)[0] != size or not 0 <= size <= MAX_PAYLOAD:
        raise ValueError('PS2Zip size differs from table')
    inflater = zlib.decompressobj(-15)
    data = inflater.decompress(stored[8:], size + 1)
    if len(data) != size or not inflater.eof or inflater.unconsumed_tail or inflater.unused_data:
        raise ValueError('PS2Zip stream length differs')
    return data


class Gt4Volume:
    def __init__(self, read, size):
        self.read, self.size = read, size
        self.toc_offset = self._find_table()
        header = read(self.toc_offset, 0x40)
        self.encrypted = struct.unpack_from('>I', header)[0] == ENCRYPTED_MAGIC
        (version, self.compressed_toc, self.header_pages, self.page_length,
         self.table_pages) = struct.unpack_from('<IiiHH', header, 4)
        if (version != VERSION_3_1 or self.page_length != 0x800 or not 0 < self.table_pages <= 4096
                or not 0 < self.compressed_toc <= 64 * 1024 * 1024 or self.header_pages <= 0
                or any(header[0x14:0x40])):
            raise ValueError('unsupported RoFS table header')
        self.data_offset = self.toc_offset + self.header_pages * self.page_length
        offsets = self._page_offsets()
        if (offsets[0] != 0x40 + 4 * (self.table_pages + 1) or offsets[-1] != self.compressed_toc
                or any(b <= a for a, b in zip(offsets, offsets[1:]))
                or self.toc_offset + offsets[-1] > self.data_offset):
            raise ValueError('RoFS page offsets out of order or bounds')
        self.index_pages, records = 0, []
        for page_index, (start, end) in enumerate(zip(offsets, offsets[1:])):
            page = self._page(start, end)
            flag, count = struct.unpack_from('<hH', page)
            if flag:
                self.index_pages += 1
                continue
            records.extend(self._records(page, count, page_index))
        self.records = self._paths(records)

    def _find_table(self):
        for page in range(min(self.size // 0x800, SCAN_PAGES)):
            head = self.read(page * 0x800, 8)
            magic, version = struct.unpack_from('>I', head)[0], struct.unpack_from('<I', head, 4)[0]
            if magic in (ENCRYPTED_MAGIC, PLAIN_MAGIC) and version == VERSION_3_1:
                return page * 0x800
        raise ValueError('RoFS 3.1 table not found')

    def _page_offsets(self):
        raw = self.read(self.toc_offset + 0x40, 4 * (self.table_pages + 1))
        offsets = []
        for i in range(self.table_pages + 1):
            value = struct.unpack_from('<I', raw, 4 * i)[0]
            if self.encrypted:
                value ^= (OFFSET_KEY * (i + 1)) & 0xFFFFFFFF
            offsets.append(value)
        return offsets

    def _page(self, start, end):
        inflater = zlib.decompressobj(-15)
        page = inflater.decompress(self.read(self.toc_offset + start, end - start), self.page_length + 1)
        # Pages are stored as one non-final DEFLATE block; exactly one page must result.
        if len(page) != self.page_length or inflater.unconsumed_tail or inflater.unused_data:
            raise ValueError('RoFS table page length differs')
        return bytes(b ^ PAGE_XOR for b in page) if self.encrypted else page

    def _records(self, page, count, page_index):
        if count % 2 or 12 + 8 * (count // 2) + 4 > len(page):
            raise ValueError('RoFS entry count exceeds page')
        rows = []
        for i in range(count // 2):
            name_at, name_len, meta_at, meta_len = struct.unpack_from('<hhhh', page, len(page) - 8 * (i + 1))
            if not (12 <= name_at and name_len > 4 and name_at + name_len <= len(page)
                    and 12 <= meta_at and meta_len >= 5 and meta_at + meta_len <= len(page)):
                raise ValueError('RoFS entry outside page')
            parent = struct.unpack_from('>i', page, name_at)[0]
            name = page[name_at + 4:name_at + name_len].decode('ascii')
            kind = KINDS.get(page[meta_at], '')
            layout = {'directory': '<i', 'file': '<iIi', 'compressed': '<iIii'}.get(kind)
            if layout is None or 1 + struct.calcsize(layout) > meta_len:
                raise ValueError('unsupported RoFS entry type')
            values = struct.unpack_from(layout, page, meta_at + 1)
            row = {'parent': parent, 'name': name, 'kind': kind, 'table_page': page_index}
            if kind == 'directory':
                row['node'] = values[0]
            else:
                row['page'], row['modified'] = values[0], values[1]
                row['stored'] = values[2]
                row['size'] = values[-1]
                if not (0 <= row['page'] and 0 < row['stored'] <= MAX_PAYLOAD
                        and 0 <= row['size'] <= MAX_PAYLOAD
                        and (kind == 'compressed' or row['stored'] == row['size'])
                        and self.data_offset + row['page'] * self.page_length + row['stored'] <= self.size):
                    raise ValueError('RoFS file extent outside volume')
                row['offset'] = self.data_offset + row['page'] * self.page_length
            rows.append(row)
        return rows

    def _paths(self, rows):
        directories = {r['node']: r for r in rows if r['kind'] == 'directory'}
        roots = [r for r in rows if r['kind'] == 'directory' and r['name'] == '.' and r['parent'] == 0]
        if len(roots) != 1 or len(directories) != sum(r['kind'] == 'directory' for r in rows):
            raise ValueError('RoFS directory nodes are not unique')
        root, paths, result = roots[0]['node'], {}, []

        def resolve(node, depth=0):
            if node == root:
                return ''
            if node in paths:
                return paths[node]
            entry = directories.get(node)
            if entry is None or depth > 64:
                raise ValueError('RoFS parent node missing or cyclic')
            base = resolve(entry['parent'], depth + 1)
            paths[node] = base + safe_name(entry['name']) + '/'
            return paths[node]
        seen = set()
        for row in rows:
            if row is roots[0]:
                continue
            path = resolve(row['parent']) + safe_name(row['name'])
            if path.casefold() in seen:
                raise ValueError('duplicate RoFS path')
            seen.add(path.casefold())
            result.append({**row, 'path': path + ('/' if row['kind'] == 'directory' else '')})
        return result

    def stored(self, record):
        return self.read(record['offset'], record['stored'])

    def payload(self, record):
        stored = self.stored(record)
        if record['kind'] == 'compressed':
            return ps2zip_inflate(stored, record['size'])
        if record['kind'] != 'file':
            raise ValueError('directory has no payload')
        return stored
