"""Section chain of an FR2 `.PS2` model, translated from the executable's loader.

Verified on the unchanged PAL corpus only. The loader (`FUN_0011ed90`) parses the buffer as a chain:

1. name tree: word 0 is the byte offset of the next section, rounded up to 16 (`FUN_00123908`);
2. texture library (`FUN_0022ba30`): three palette-block counts A, B, C; a 12-byte table entry per block;
   the blocks themselves (A and C blocks of 0x400 bytes, B blocks of 0x40); a count N and one extra word;
   then N items, each a flags word, a length-prefixed name, a 0x40-byte descriptor (format byte at 0x34,
   mip-level count at 0x35, a 64-bit field at 0x38 whose bits 15-18 and 19-22 are log2 width and height),
   a 0x10-byte record per mip level, and finally the image planes, each 16-byte aligned;
3. the next section starts at the 16-byte-aligned end and opens with a record count (records of 0x34 bytes).

Level-zero decoding covers format 1 (32-bit linear) and formats 3/4 under the
bounded static upload contract in ps2_texture_indices. Descriptor bit8 selects
packed upload versus direct linear indices. Mips and later geometry remain
separate, and no original rendering or hardware execution is claimed.
"""

from __future__ import annotations

from functools import lru_cache
import struct

from evidence_common import Invalid, sha256
from format_contracts import model

FORMATS = {1, 2, 3, 4}
MAX_BLOCKS = 4096
MAX_ITEMS = 4096
MAX_NAME = 256
MAX_DIM = 2048
MAX_MIPS = 8
NEXT_RECORD = 0x34


class Unsupported(ValueError):
    """The item is valid but its pixels are outside the measured decoding profile."""


def align16(n: int) -> int:
    return (n + 15) & ~15


def level_bytes(fmt: int, w: int, h: int) -> int:
    return {1: w * h * 4, 2: w * h * 2, 3: w * h, 4: w * h // 2}[fmt]


def parse(data: bytes) -> dict:
    tree = model(data)
    pool_end = tree["leading_count"]
    start = align16(pool_end)

    def need(pos: int, size: int, what: str) -> None:
        if pos < 0 or size < 0 or pos + size > len(data):
            raise Invalid(f"{what} at {pos:#x} (+{size}) exceeds the {len(data)}-byte file")

    need(start, 12, "texture section header")
    a, b, c = struct.unpack_from("<3I", data, start)
    if max(a, b, c) > MAX_BLOCKS:
        raise Invalid(f"palette block counts {(a, b, c)} exceed the bound {MAX_BLOCKS}")
    total = a + b + c
    table = start + 12
    need(table, 12 * total, "palette block table")
    palettes = align16(table + 12 * total)
    block_size = [0x400] * a + [0x40] * b + [0x400] * c
    block_at = [palettes + sum(block_size[:i]) for i in range(total)]
    pos = palettes + sum(block_size)
    need(palettes, pos - palettes, "palette blocks")
    need(pos, 8, "texture count")
    count, extra = struct.unpack_from("<2I", data, pos)
    if count > MAX_ITEMS:
        raise Invalid(f"texture count {count} exceeds the bound {MAX_ITEMS}")
    pos += 8
    items = []
    for i in range(count):
        need(pos, 8, f"texture {i} header")
        flags, length = struct.unpack_from("<2I", data, pos)
        pos += 8
        if not 1 <= length <= MAX_NAME:
            raise Invalid(f"texture {i}: name length {length} outside 1..{MAX_NAME}")
        need(pos, length, f"texture {i} name")
        raw = data[pos : pos + length]
        name = raw.split(b"\0")[0]
        if raw[-1:] != b"\0" or not name or not all(32 <= ch < 127 for ch in name):
            raise Invalid(f"texture {i}: name is not a printable NUL-terminated string")
        pos += length
        if flags & 1:
            raise Invalid(f"texture {i}: items without image data are outside the measured profile")
        pos = align16(pos)
        need(pos, 0x40, f"texture {i} descriptor")
        struct_at = pos
        palette_index = struct.unpack_from("<I", data, pos)[0]
        fmt, mips = data[pos + 0x34], data[pos + 0x35]
        (field,) = struct.unpack_from("<Q", data, pos + 0x38)
        width, height = 1 << ((field >> 15) & 0xF), 1 << ((field >> 19) & 0xF)
        if fmt not in FORMATS:
            raise Invalid(f"texture {i}: unknown format {fmt}")
        if mips > MAX_MIPS or width > MAX_DIM or height > MAX_DIM:
            raise Invalid(f"texture {i}: mips {mips} or size {width}x{height} outside the measured profile")
        if mips >= min(width, height).bit_length():
            raise Invalid(f"texture {i}: {mips} mips exceed the {min(width, height).bit_length() - 1} halvings a {width}x{height} image supports")
        if fmt in (3, 4) and palette_index >= total:
            raise Invalid(f"texture {i}: palette index {palette_index} outside the {total}-entry table")
        pos += 0x40 + 0x10 * mips
        need(struct_at, pos - struct_at, f"texture {i} descriptor and mip records")
        items.append(
            {
                "index": i,
                "name": name.decode("ascii"),
                "flags": flags,
                "descriptor_offset": struct_at,
                "format": fmt,
                "mips": mips,
                "width": width,
                "height": height,
                "palette_index": palette_index,
                "palette_offset": block_at[palette_index] if palette_index < total else None,
                "palette_bytes": block_size[palette_index] if palette_index < total else None,
                "descriptor_field": f"{field:#018x}",
                "levels": [],
            }
        )
    for it in items:
        w, h = it["width"], it["height"]
        for level in range(it["mips"] + 1):
            pos = align16(pos)
            size = level_bytes(it["format"], w, h)
            need(pos, size, f"texture {it['index']} level {level} image data")
            it["levels"].append({"level": level, "offset": pos, "size": size, "width": w, "height": h})
            pos += size
            w, h = w >> 1, h >> 1
    end = align16(pos)
    need(end, 4, "record count of the next section")
    (records,) = struct.unpack_from("<I", data, end)
    if 4 + NEXT_RECORD * records > len(data) - end:
        raise Invalid(f"next section announces {records} records of {NEXT_RECORD} bytes, which do not fit after {end:#x}")
    return {
        "tree": {"name_pool_end": pool_end, "next_section_offset": start},
        "textures": {
            "section_start": start,
            "palette_blocks": (a, b, c),
            "palette_table_sha256": sha256(data[table : table + 12 * total]),
            "palette_region": [palettes, palettes + sum(block_size)],
            "extra_word": extra,
            "image_count": count,
            "items": items,
            "section_end": end,
        },
        "next_section": {"offset": end, "record_count": records, "record_bytes": NEXT_RECORD},
    }


@lru_cache(maxsize=64)
def _block_order8(w: int, h: int) -> tuple[int, ...]:
    """Source index in the GS 8-bit block layout for each pixel of a w x h image, row-major."""
    order = []
    for y in range(h):
        for x in range(w):
            block = (y & ~0xF) * w + (x & ~0xF) * 2
            swap = (((y + 2) >> 2) & 1) * 4
            row = (((y & ~3) >> 1) + (y & 1)) & 7
            column = row * w * 2 + ((x + swap) & 7) * 4
            order.append(block + column + ((y >> 1) & 1) + ((x >> 2) & 2))
    return tuple(order)


def unswizzle8(plane: bytes, w: int, h: int) -> bytes:
    if w < 16 or h < 16 or w % 16 or h % 16:
        raise Unsupported(f"8-bit block layout needs multiples of 16; got {w}x{h}")
    order = _block_order8(w, h)
    if len(plane) < w * h or max(order) >= len(plane):
        raise Unsupported("plane is shorter than the block layout requires")
    return bytes(map(plane.__getitem__, order))


def decode_rgba(data: bytes, item: dict) -> bytes:
    """Level-0 RGBA with the stored alpha (the game's palettes use 0..0x80 as opaque)."""
    level = item["levels"][0]
    plane = data[level["offset"] : level["offset"] + level["size"]]
    if item["format"] == 1:
        return plane
    if item["format"] in (3, 4):
        from ps2_texture_indices import decode_indices
        count = 256 if item["format"] == 3 else 16
        palette_size = count * 4
        allowed_sizes = (0x400,) if item['format'] == 3 else (0x40, 0x400)
        if item["palette_bytes"] not in allowed_sizes:
            raise Unsupported(f"format {item['format']} palette block is outside the measured profile")
        pixels = decode_indices(data, item)
        palette_block = data[item["palette_offset"] : item["palette_offset"] + item['palette_bytes']]
        if len(palette_block) != item['palette_bytes']:
            raise Invalid('palette bytes are outside the input')
        # The 16x16 PSMCT32 upload of a 256-color A/C block follows the
        # loader's bit3/4 permutation; CSM0/CSA0 then restores raw indices
        # 0..15 for PSMT4, as does the unpermuted 8x2 sixteen-color upload.
        palette = palette_block[:palette_size]
        entries = [palette[4 * i : 4 * i + 4] for i in range(count)]
        return b"".join(map(entries.__getitem__, pixels))
    raise Unsupported(f"format {item['format']} pixel layout is not decoded")
