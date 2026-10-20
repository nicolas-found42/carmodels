"""Read-only XDVDFS (Xbox/Xbox 360 game partition) directory reader.

Layout readings, checked against the Midnight Club: Los Angeles disc: the game
partition starts at a fixed image offset per disc generation; its volume
descriptor is sector 32 of the partition and carries `MICROSOFT*XBOX*MEDIA` at
both ends, then the root directory sector and size. A directory is a binary
search tree of 4-byte-aligned records: left and right subtree offsets in dwords,
start sector, size, attribute byte (0x10 = directory), name length and name.
Records never cross a sector boundary; 0xFF bytes pad the rest of a sector.
"""

from pathlib import Path
import struct

SECTOR = 2048
MAGIC = b"MICROSOFT*XBOX*MEDIA"
# Game-partition offsets by disc generation (XGD2 first: the generation of this disc).
PARTITIONS = (
    ("XGD2", 0xFD90000),
    ("XGD3", 0x2080000),
    ("XGD1", 0x18300000),
    ("plain", 0),
)
DIRECTORY = 0x10
MAX_DIRECTORY = 64 * 1024 * 1024
MAX_ENTRIES = 1_000_000


def safe_component(name):
    if (
        not name
        or name in (".", "..")
        or len(name) > 255
        or "/" in name
        or "\\" in name
        or any(ord(c) < 32 or ord(c) > 126 for c in name)
    ):
        raise ValueError("unsafe XDVDFS name")
    return name


class XdvdfsDisc:
    """Lists every file and directory; reads payloads by entry. Never writes."""

    def __init__(self, path):
        self.path = Path(path)
        if self.path.is_symlink():
            raise ValueError("linked disc input")
        self.stream = self.path.open("rb")
        self.size = self.path.stat().st_size
        try:
            if self.size % SECTOR:
                raise ValueError("truncated disc image")
            for generation, base in PARTITIONS:
                if base + 33 * SECTOR > self.size:
                    continue
                descriptor = self.read_at(base + 32 * SECTOR, SECTOR)
                if descriptor[:20] == MAGIC:
                    if descriptor[0x7EC:0x800] != MAGIC:
                        raise ValueError("XDVDFS descriptor trailer mismatch")
                    break
            else:
                raise ValueError("no XDVDFS volume descriptor")
            self.generation, self.partition = generation, base
            root_sector, root_size = struct.unpack_from("<II", descriptor, 20)
            self.root = {"sector": root_sector, "size": root_size}
            self.timestamp = struct.unpack_from("<Q", descriptor, 28)[0]
            self.entries = []
            self._walk(root_sector, root_size, "", set())
            self.entries.sort(key=lambda e: e["path"])
            files = sorted(
                (e for e in self.entries if e["kind"] == "file" and e["size"]),
                key=lambda e: e["sector"],
            )
            for previous, current in zip(files, files[1:]):
                if (
                    previous["sector"] * SECTOR + previous["size"]
                    > current["sector"] * SECTOR
                ):
                    raise ValueError("overlapping XDVDFS file extents")
        except Exception:
            self.close()
            raise

    def close(self):
        self.stream.close()

    def read_at(self, offset, size):
        if offset < 0 or size < 0 or offset + size > self.size:
            raise ValueError("read outside disc")
        self.stream.seek(offset)
        data = self.stream.read(size)
        if len(data) != size:
            raise ValueError("truncated disc read")
        return data

    def offset(self, sector):
        return self.partition + sector * SECTOR

    def region(self, entry):
        if entry["kind"] != "file":
            raise ValueError("not an XDVDFS file")
        start, size = self.offset(entry["sector"]), entry["size"]

        def read(offset, count):
            if offset < 0 or count < 0 or offset + count > size:
                raise ValueError("read outside XDVDFS file")
            return self.read_at(start + offset, count)

        return read

    def _walk(self, sector, size, parent, seen):
        if (sector, size) in seen:
            raise ValueError("XDVDFS directory cycle")
        if not 0 < size <= MAX_DIRECTORY or self.offset(sector) + size > self.size:
            raise ValueError("XDVDFS directory outside disc")
        seen.add((sector, size))
        table = self.read_at(
            self.offset(sector), (size + SECTOR - 1) // SECTOR * SECTOR
        )[:size]
        visited, names, stack = set(), set(), [0]
        while stack:
            at = stack.pop()
            if at in visited:
                raise ValueError("XDVDFS tree cycle")
            visited.add(at)
            if at + 14 > size or at // SECTOR != (at + 13) // SECTOR:
                raise ValueError("XDVDFS record outside directory")
            left, right, start, length, attributes, name_length = struct.unpack_from(
                "<HHIIBB", table, at
            )
            end = at + 14 + name_length
            if not name_length or end > size or at // SECTOR != (end - 1) // SECTOR:
                raise ValueError("XDVDFS name outside directory")
            name = safe_component(table[at + 14 : end].decode("ascii"))
            if name.casefold() in names:
                raise ValueError("duplicate XDVDFS name")
            names.add(name.casefold())
            path = parent + name
            kind = "directory" if attributes & DIRECTORY else "file"
            if kind == "file" and length and self.offset(start) + length > self.size:
                raise ValueError("XDVDFS file outside disc")
            self.entries.append(
                {
                    "path": path + ("/" if kind == "directory" else ""),
                    "kind": kind,
                    "sector": start,
                    "size": length,
                    "attributes": attributes,
                }
            )
            if len(self.entries) > MAX_ENTRIES:
                raise ValueError("XDVDFS entry limit")
            if kind == "directory" and length:
                self._walk(start, length, path + "/", seen)
            for child in (left, right):
                if child:
                    stack.append(child * 4)
