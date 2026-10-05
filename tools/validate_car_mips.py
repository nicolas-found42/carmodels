#!/usr/bin/env python3
"""Independently validate archive-backed mip planes and decoded PNG pixels."""
from __future__ import annotations

import static_inputs
import hashlib
import json
from pathlib import Path
import re
import struct
import sys
import zlib

ROOT = Path(__file__).resolve().parents[1]
SOURCE = static_inputs.bundle_path()
OUT = ROOT / "research/evidence/mip-continuation"
PNG_SIG = b"\x89PNG\r\n\x1a\n"
GS_TABLES = SOURCE / ".scratch/mesh/codex-root/github-raw-GSTables.cpp"
GS_TABLES_SHA256 = "a9a226297ede32b89177d7bdb04e9d8e21728e7d55799405f6112e97fe4969e8"


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def parse_png(data: bytes) -> tuple[int, int, bytes]:
    if not data.startswith(PNG_SIG):
        raise AssertionError("invalid PNG signature")
    pos, width, height, pixels, ended = len(PNG_SIG), None, None, bytearray(), False
    compressed = bytearray()
    while pos < len(data):
        if len(data) - pos < 12:
            raise AssertionError("truncated PNG chunk")
        size = struct.unpack_from(">I", data, pos)[0]
        kind = data[pos + 4:pos + 8]
        end = pos + 12 + size
        if end > len(data):
            raise AssertionError("PNG chunk exceeds file")
        payload = data[pos + 8:pos + 8 + size]
        crc = struct.unpack_from(">I", data, pos + 8 + size)[0]
        if zlib.crc32(kind + payload) != crc:
            raise AssertionError(f"PNG CRC mismatch for {kind!r}")
        if kind == b"IHDR":
            width, height, depth, color, comp, filt, interlace = struct.unpack(">2I5B", payload)
            if (depth, color, comp, filt, interlace) != (8, 6, 0, 0, 0):
                raise AssertionError("PNG is outside RGBA8/non-interlaced profile")
        elif kind == b"IDAT":
            compressed.extend(payload)
        elif kind == b"IEND":
            ended = True
            if end != len(data):
                raise AssertionError("trailing bytes after PNG IEND")
            break
        pos = end
    if width is None or height is None or not ended:
        raise AssertionError("PNG missing IHDR or IEND")
    raw = zlib.decompress(compressed)
    stride = width * 4
    if len(raw) != height * (stride + 1):
        raise AssertionError("PNG decompressed size differs from dimensions")
    for y in range(height):
        line = raw[y * (stride + 1):(y + 1) * (stride + 1)]
        if line[0] != 0:
            raise AssertionError("unexpected PNG filter")
        pixels.extend(line[1:])
    return width, height, bytes(pixels)


def order8(width: int, height: int) -> list[int]:
    """Enumerate logical T8 byte addresses using the inverse 8-bit block map."""
    if width < 16 or height < 16 or width % 16 or height % 16:
        raise AssertionError("packed T8 logical mip dimensions are unsupported")
    out = []
    for y in range(height):
        for x in range(width):
            base = (y & ~0xF) * width + (x & ~0xF) * 2
            row_swap = (((y + 2) >> 2) & 1) * 4
            row = (((y & ~3) >> 1) + (y & 1)) & 7
            column = row * width * 2 + ((x + row_swap) & 7) * 4
            out.append(base + column + ((y >> 1) & 1) + ((x >> 2) & 2))
    if len(set(out)) != width * height or min(out) != 0 or max(out) != width * height - 1:
        raise AssertionError("packed T8 addresses are not a complete plane permutation")
    return out


def xor(value: int, basis: tuple[int, ...]) -> int:
    result = 0
    for bit, mask in enumerate(basis):
        if value & (1 << bit):
            result ^= mask
    return result


def order4(width: int, height: int, dbw: int, tbw: int) -> list[int]:
    """Independent PSMT4-to-CT16 address inversion, including profile bounds."""
    if width % 2 or height % 2 or dbw <= 0 or tbw <= 0:
        raise AssertionError("packed T4 profile has invalid dimensions/strides")
    inverse_block = {xor(x | (y << 2), (2, 8, 1, 4, 16)): (x, y)
                     for y in range(8) for x in range(4)}
    inverse_column = {xor(x | (y << 4), (2, 8, 16, 1, 4, 32, 64)): (x, y)
                      for y in range(8) for x in range(16)}
    out = []
    for y in range(height):
        for x in range(width):
            page = (y // 128) * ((tbw * 64) // 128) + x // 128
            block = xor(((x % 128) // 32) | (((y % 128) // 16) << 2),
                        (2, 8, 1, 4, 16))
            column = xor((x % 32) | ((y % 16) << 5),
                         (8, 32, 64, 2, 4, 16, 65, 192, 256))
            nibble = page * 16384 + block * 512 + column
            halfword = nibble // 4
            upload_page, in_page = divmod(halfword, 4096)
            bx, by = inverse_block[in_page // 128]
            cx, cy = inverse_column[in_page % 128]
            ux = (upload_page % dbw) * 64 + bx * 16 + cx
            uy = (upload_page // dbw) * 64 + by * 8 + cy
            if ux >= width // 2 or uy >= height // 2:
                raise AssertionError("packed T4 read address is outside the corresponding CT16 upload")
            out.append((uy * (width // 2) + ux) * 4 + (nibble & 3))
    if len(set(out)) != width * height or min(out) != 0 or max(out) != width * height - 1:
        raise AssertionError("packed T4 addresses are not a complete source nibble permutation")
    return out


def decode(item: dict, mip: dict, raw: bytes, model: bytes) -> bytes:
    width, height = mip["logical_dimensions"]
    fmt, packed = mip["format"], mip["packed_upload"]
    if fmt == 1:
        return raw
    if fmt == 3:
        if packed:
            indices = bytes(raw[i] for i in order8(width, height))
        else:
            indices = raw
        paloff, palsize = mip["palette_file_offset"], mip["palette_bytes"]
        palette = model[paloff:paloff + palsize]
        return b"".join(palette[index * 4:index * 4 + 4] for index in indices)
    if fmt == 4:
        if packed:
            source_nibbles = order4(width, height, mip["bitbltbuf_dbw_low16"],
                                    mip["miptbp_tbw_low16"])
            indices = bytes((raw[n // 2] >> ((n & 1) * 4)) & 15 for n in source_nibbles)
        else:
            indices = bytes(n for b in raw for n in (b & 15, b >> 4))
        paloff, palsize = mip["palette_file_offset"], mip["palette_bytes"]
        palette = model[paloff:paloff + palsize]
        return b"".join(palette[index * 4:index * 4 + 4] for index in indices)
    raise AssertionError(f"unsupported format {fmt}")


def read_gs_tables() -> dict:
    """Load pinned PCSX2 page/block/column tables as a distinct address oracle."""
    source = GS_TABLES.read_bytes()
    if sha(source) != GS_TABLES_SHA256:
        raise AssertionError("PCSX2 GS table source differs from the pinned evidence")
    text = source.decode("utf-8")
    shapes = {32: (8, 8, 64, 32), 16: (16, 8, 64, 64),
              8: (16, 16, 128, 64), 4: (32, 16, 128, 128)}
    tables = {}
    for bits, (bw, bh, pw, ph) in shapes.items():
        tables[bits] = []
        for name, rows, cols in ((f"_blockTable{bits}", ph // bh, pw // bw),
                                 (f"columnTable{bits}", bh, bw)):
            match = re.search(r"\b" + name + rf"\[{rows}\]\[{cols}\]\s*=\s*\{{(.*?)\}};", text, re.S)
            if not match:
                raise AssertionError(f"pinned GS table {name} is missing")
            values = list(map(int, re.findall(r"\d+", re.sub(r"//[^\n]*", "", match.group(1)))))
            if len(values) != rows * cols:
                raise AssertionError(f"pinned GS table {name} has an unexpected cell count")
            tables[bits].append([values[y * cols:(y + 1) * cols] for y in range(rows)])
    return {"shapes": shapes, "tables": tables}


def gs_address(oracle: dict, bits: int, x: int, y: int, buffer_width: int) -> int:
    bw, bh, page_w, page_h = oracle["shapes"][bits]
    blocks, columns = oracle["tables"][bits]
    page = (y // page_h) * (buffer_width * 64 // page_w) + x // page_w
    address = (page * page_w * page_h +
               blocks[(y % page_h) // bh][(x % page_w) // bw] * bw * bh +
               columns[y % bh][x % bw])
    return address * (bits // 4)


def verify_table_order(mip: dict, record: tuple[int, ...], oracle: dict) -> None:
    """Compare decoder permutation with address sets from pinned public GS tables."""
    fmt = mip["format"]
    width, height = mip["logical_dimensions"]
    upload_bits, sample_bits = (32, 8) if fmt == 3 else (16, 4)
    dbw, tbw = record[3] & 0xFFFF, record[1] & 0xFFFF
    source_nibbles: dict[int, int] = {}
    upload_width, upload_height = width // 2, height // 2
    for y in range(upload_height):
        for x in range(upload_width):
            vram_nibble = gs_address(oracle, upload_bits, x, y, dbw)
            source_nibble = (y * upload_width + x) * (upload_bits // 4)
            for i in range(upload_bits // 4):
                if vram_nibble + i in source_nibbles:
                    raise AssertionError("upload GS table addresses overlap")
                source_nibbles[vram_nibble + i] = source_nibble + i
    measured = []
    for y in range(height):
        for x in range(width):
            vram_nibble = gs_address(oracle, sample_bits, x, y, tbw)
            if fmt == 3:
                if vram_nibble not in source_nibbles or vram_nibble + 1 not in source_nibbles:
                    raise AssertionError("packed T8 read references bytes not written by the CT32 upload")
                lo, hi = source_nibbles[vram_nibble], source_nibbles[vram_nibble + 1]
                if hi != lo + 1 or lo & 1:
                    raise AssertionError("packed T8 table address does not recover one aligned source byte")
                measured.append(lo // 2)
            else:
                if vram_nibble not in source_nibbles:
                    raise AssertionError("packed T4 read references an unwritten source nibble")
                measured.append(source_nibbles[vram_nibble])
    expected = order8(width, height) if fmt == 3 else order4(width, height, dbw, tbw)
    if measured != expected:
        raise AssertionError("exported decoder permutation differs from pinned PCSX2 table address mapping")


def main() -> None:
    import argparse
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, default=OUT,
                        help="mip evidence directory containing mip-index.json and extracted levels")
    args = parser.parse_args()
    output_dir = args.output_dir
    sys.path.insert(0, str(ROOT/'tools'))
    import ps2_sections
    from corpus_binding import Baseline
    index = json.loads((output_dir / "mip-index.json").read_text())
    gs_oracle = read_gs_tables()
    baseline = Baseline(SOURCE / "games/ford-racing-2")
    archive = {entry.path.lstrip("/"): entry for entry in baseline.entries(".ps2;1")}
    checked = raw_bytes = decoded = 0
    cars = {row["car"]: row for row in index["cars"]}
    if len(cars) != 35:
        raise AssertionError(f"expected 35 car index rows, got {len(cars)}")
    for folder in sorted((ROOT / "reference/ford/cars").iterdir()):
        manifest_path = folder / "manifest.json"
        if not manifest_path.is_file():
            continue
        manifest = json.loads(manifest_path.read_text())
        model_path = next(folder.glob("model/*.PS2;1"))
        src = next(row for row in manifest["files"] if "/model/" in row["dst"])
        entry = archive[src["src"]]
        model = model_path.read_bytes()
        if model != entry.load() or sha(model) != src["sha256"]:
            raise AssertionError(f"{folder.name}: model bytes differ from manifest/archive")
        parsed = ps2_sections.parse(model)
        source_levels = []
        for item in parsed["textures"]["items"]:
            field = int(item["descriptor_field"], 16)
            for mip_no, level in enumerate(item["levels"][1:], 1):
                record_at = item["descriptor_offset"] + 0x40 + 16 * (mip_no - 1)
                words = struct.unpack_from("<4I", model, record_at)
                source_levels.append((item, field, mip_no, level, record_at, words))
        rows = cars[folder.name]["extra_mip_levels"]
        if len(rows) != len(source_levels):
            raise AssertionError(f"{folder.name}: mip inventory cardinality differs")
        for (item, field, mip_no, level, record_at, words), row in zip(source_levels, rows):
            width, height = level["width"], level["height"]
            if row["level"] != mip_no or row["logical_dimensions"] != [width, height]:
                raise AssertionError(f"{folder.name}/{item['name']} L{mip_no}: identity mismatch")
            if row["source_file_offset"] != level["offset"] or row["source_byte_count"] != level["size"]:
                raise AssertionError(f"{folder.name}/{item['name']} L{mip_no}: source span mismatch")
            if row["mip_record_file_offset"] != record_at:
                raise AssertionError(f"{folder.name}/{item['name']} L{mip_no}: record offset mismatch")
            if row["mip_record_words"] != [f"0x{x:08x}" for x in words]:
                raise AssertionError(f"{folder.name}/{item['name']} L{mip_no}: raw record mismatch")
            if bool(field & 0x100) and item["format"] in (3, 4):
                verify_table_order({"format": item["format"],
                                    "logical_dimensions": [width, height]}, words, gs_oracle)
            raw = model[level["offset"]:level["offset"] + level["size"]]
            raw_path = output_dir / row["raw_plane"]
            if raw_path.read_bytes() != raw or sha(raw) != row["source_sha256"]:
                raise AssertionError(f"{folder.name}/{item['name']} L{mip_no}: exported plane differs")
            raw_bytes += len(raw)
            if row["decode_status"] == "decoded_static_mapping":
                if bool(field & 0x100) != row["packed_upload"] or item["format"] != row["format"]:
                    raise AssertionError(f"{folder.name}/{item['name']} L{mip_no}: descriptor mapping differs")
                expected_rgba = decode(row, row, raw, model)
                png_path = output_dir / row["png"]
                png = png_path.read_bytes()
                png_width, png_height, actual_rgba = parse_png(png)
                if (png_width, png_height) != (width, height) or actual_rgba != expected_rgba:
                    raise AssertionError(f"{folder.name}/{item['name']} L{mip_no}: decoded PNG pixel mismatch")
                if sha(actual_rgba) != row["rgba_sha256"] or sha(png) != row["png_sha256"]:
                    raise AssertionError(f"{folder.name}/{item['name']} L{mip_no}: decoded hash mismatch")
                decoded += 1
            elif row["decode_status"] != "unresolved":
                raise AssertionError("unknown decoder disposition")
            checked += 1
    if checked != 94 or decoded != 94 or raw_bytes != 75_520:
        raise AssertionError(f"unexpected coverage: levels={checked}, decoded={decoded}, raw_bytes={raw_bytes}")
    result = {"schema_version": 1, "status": "pass",
              "scope": "Independent archive/manifest byte, source-span, mip-record, PNG CRC/pixel, dimension and hash checks for the 35 car subset.",
              "corpus_id": baseline.provenance["corpus_id"],
              "checked_cars": 35, "checked_extra_mip_levels": checked,
              "checked_raw_plane_bytes": raw_bytes, "independently_decoded_pngs": decoded,
              "pcsx2_gs_tables_sha256": GS_TABLES_SHA256,
              "validator_tool_sha256": sha(Path(__file__).read_bytes()),
              "independent_methods": ["archive+manifest exact bytes", "raw mip offsets from parsed source", "PNG CRC and decompression", "separately implemented packed T8/T4 address permutations compared pixel-for-pixel against pinned PCSX2 page/block/column tables", "direct format pixel conversion", "source/output hashes"],
              "limits": ["Confirms the emitted static mapping and exact bytes; does not execute game, GS, emulator, or silicon.", "The source/GS base-allocation and sampler-selector behavior remains unobserved."]}
    (output_dir / "validation.json").write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
