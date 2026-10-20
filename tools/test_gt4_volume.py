"""Synthetic RoFS 3.1 volumes: parsing, payloads and tamper controls that must each fail."""

import struct
import unittest
import zlib

from gt4_volume import (
    ENCRYPTED_MAGIC,
    OFFSET_KEY,
    PAGE_XOR,
    PS2ZIP_MAGIC,
    VERSION_3_1,
    Gt4Volume,
    ps2zip_inflate,
)
from mc3_archive import byte_reader

PAGE = 0x800


def ps2zip(data):
    deflate = zlib.compressobj(9, zlib.DEFLATED, -15)
    return (
        struct.pack(">I", PS2ZIP_MAGIC)
        + struct.pack("<i", -len(data))
        + deflate.compress(data)
        + deflate.flush()
    )


def entry_page(rows, flag=0):
    """rows: (parent, name, kind, values); the table grows backwards from the page end."""
    page, table = bytearray(PAGE), []
    position = 12
    for parent, name, kind, values in rows:
        name_bytes = struct.pack(">i", parent) + name.encode()
        page[position : position + len(name_bytes)] = name_bytes
        name_at, position = position, (position + len(name_bytes) + 3) & ~3
        layout = {0: "<i", 1: "<iIi", 2: "<iIii"}.get(kind, "<i")
        meta = bytes([kind]) + struct.pack(layout, *values)
        page[position : position + len(meta)] = meta
        table.append((name_at, len(name_bytes), position, len(meta)))
        position = (position + len(meta) + 3) & ~3
    struct.pack_into("<hHii", page, 0, flag, 2 * len(rows), -1, -1)
    for i, row in enumerate(table):
        struct.pack_into("<hhhh", page, PAGE - 8 * (i + 1), *row)
    if position > PAGE - 8 * len(table) - 4:
        raise ValueError("fixture page overflow")
    return bytes(page)


def volume_fixture(files, encrypted=True, decoy_pages=2, mutate=None):
    """files: (path, payload, compressed). Directories get node ids in path order."""
    directories, rows, blobs, data_pages = {"": 1}, [(0, ".", 0, (1,))], [], 0
    for path, payload, compressed in files:
        parts = path.split("/")
        for depth in range(1, len(parts)):
            parent, here = "/".join(parts[: depth - 1]), "/".join(parts[:depth])
            if here not in directories:
                directories[here] = len(directories) + 1
                rows.append(
                    (directories[parent], parts[depth - 1], 0, (directories[here],))
                )
        stored = ps2zip(payload) if compressed else payload
        values = (
            (data_pages, 1105701374, len(stored), len(payload))
            if compressed
            else (data_pages, 1105701374, len(payload))
        )
        rows.append(
            (
                directories["/".join(parts[:-1])],
                parts[-1],
                2 if compressed else 1,
                values,
            )
        )
        blobs.append(stored + bytes(-len(stored) % PAGE))
        data_pages += (len(stored) + PAGE - 1) // PAGE
    fixture = {"rows": rows, "index_page": True, "encrypted": encrypted, "padding": b""}
    if mutate:
        mutate(fixture)
    pages = [fixture.get("page_hook", bytes)(entry_page(fixture["rows"]))]
    if fixture["index_page"]:
        pages.insert(0, entry_page([(1, "car", 0, (2,))], flag=1))
    compressed_pages = []
    for page in pages:
        if fixture["encrypted"]:
            page = bytes(b ^ PAGE_XOR for b in page)
        deflate = zlib.compressobj(9, zlib.DEFLATED, -15)
        compressed_pages.append(
            deflate.compress(page + fixture["padding"]) + deflate.flush()
        )
    offsets = [0x40 + 4 * (len(pages) + 1)]
    for blob in compressed_pages:
        offsets.append(offsets[-1] + len(blob))
    offsets = fixture.get("offsets_hook", list)(offsets)
    table = b"".join(
        struct.pack(
            "<I",
            value ^ ((OFFSET_KEY * (i + 1)) & 0xFFFFFFFF)
            if fixture["encrypted"]
            else value,
        )
        for i, value in enumerate(offsets)
    )
    header_pages = (offsets[-1] + PAGE - 1) // PAGE
    magic = struct.pack(">I", ENCRYPTED_MAGIC) if fixture["encrypted"] else b"RoFS"
    header = magic + struct.pack(
        "<IiiHH",
        fixture.get("version", VERSION_3_1),
        offsets[-1],
        header_pages,
        PAGE,
        len(pages),
    )
    header = header.ljust(0x40, b"\0")
    if "header" in fixture:
        header = fixture["header"](header)
    toc = header + table + b"".join(compressed_pages)
    toc += bytes(header_pages * PAGE - len(toc))
    decoy = b"GT3 decoy table".ljust(decoy_pages * PAGE, b"\0")
    return decoy + toc + b"".join(blobs)


FILES = [
    ("car/lod/test0001", b"CAR4\0\0\0\0" + b"model" * 300, True),
    ("car/lod/test0001.pat", b"Pat0\0\0\0\0colours", True),
    ("car/menu/test0001", b"CAR4\0\0\0\0menu", True),
    ("wheel/lod/test0001", b"MDLS wheel", True),
    ("rtext/readme.txt", b"stored plain file", False),
]


def parse(data):
    return Gt4Volume(byte_reader(data), len(data))


class VolumeTests(unittest.TestCase):
    def test_encrypted_and_plain_tables_decode_paths_and_payloads(self):
        for encrypted in (True, False):
            with self.subTest(encrypted=encrypted):
                volume = parse(volume_fixture(FILES, encrypted=encrypted))
                self.assertEqual(volume.encrypted, encrypted)
                self.assertEqual(
                    volume.toc_offset, 2 * PAGE
                )  # The decoy table is skipped.
                self.assertEqual(volume.index_pages, 1)
                files = {
                    r["path"]: r for r in volume.records if r["kind"] != "directory"
                }
                self.assertEqual(sorted(files), sorted(p for p, _, _ in FILES))
                for path, payload, compressed in FILES:
                    self.assertEqual(volume.payload(files[path]), payload)
                    self.assertEqual(
                        files[path]["kind"], "compressed" if compressed else "file"
                    )
                self.assertIn("car/lod/", {r["path"] for r in volume.records})

    def control(self, reason, mutate=None, data=None):
        with self.subTest(reason=reason), self.assertRaisesRegex(ValueError, reason):
            volume = parse(
                data if data is not None else volume_fixture(FILES, mutate=mutate)
            )
            for record in volume.records:
                if record["kind"] != "directory":
                    volume.payload(record)

    def test_table_controls(self):
        def rows(change):
            return lambda f: f.__setitem__("rows", change(f["rows"]))

        self.control(
            "RoFS 3.1 table not found", lambda f: f.__setitem__("version", 0x00030002)
        )
        self.control(
            "unsupported RoFS table header",
            lambda f: f.__setitem__("header", lambda h: h[:0x3F] + b"\1"),
        )
        self.control(
            "page offsets",
            lambda f: f.__setitem__("offsets_hook", lambda o: [o[0], o[2], o[1]]),
        )
        self.control(
            "table page length differs", lambda f: f.__setitem__("padding", b"extra")
        )
        self.control(
            "unsupported RoFS entry type",
            rows(lambda r: r[:-1] + [(r[-1][0], r[-1][1], 7, (0,))]),
        )
        self.control("duplicate RoFS path", rows(lambda r: r + [r[-1]]))
        self.control(
            "parent node missing or cyclic",
            rows(lambda r: r[:-1] + [(99, "orphan", 1, (0, 0, 1))]),
        )
        self.control(
            "parent node missing or cyclic",
            rows(lambda r: [r[0]] + [(9, "loop", 0, (9,))] + r[1:]),
        )
        self.control(
            "unsafe archive name",
            rows(lambda r: r[:-1] + [(r[-1][0], "..", 1, (0, 0, 1))]),
        )
        self.control(
            "directory nodes are not unique",
            rows(lambda r: r + [(1, "again", 0, (2,))]),
        )
        self.control(
            "file extent outside volume",
            rows(lambda r: r[:-1] + [(r[-1][0], r[-1][1], 1, (9999, 0, 4))]),
        )

    def test_entry_outside_page_control(self):
        def overrun(page):
            page = bytearray(page)
            struct.pack_into(
                "<h", page, PAGE - 6, PAGE - 4
            )  # First entry's name runs off the page.
            return bytes(page)

        self.control(
            "entry outside page", lambda f: f.__setitem__("page_hook", overrun)
        )

    def test_ps2zip_controls(self):
        payload = b"native payload" * 10
        good = ps2zip(payload)
        self.assertEqual(ps2zip_inflate(good, len(payload)), payload)
        for reason, stored, size in [
            ("missing PS2Zip header", b"\0" + good[1:], len(payload)),
            ("size differs from table", good, len(payload) + 1),
            ("stream length differs", good + b"trailing", len(payload)),
            ("stream length differs", good[:-4], len(payload)),
        ]:
            with (
                self.subTest(reason=reason),
                self.assertRaisesRegex(ValueError, reason),
            ):
                ps2zip_inflate(stored, size)


if __name__ == "__main__":
    unittest.main()
