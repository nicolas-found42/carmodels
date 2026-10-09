#!/usr/bin/env python3
"""Validate and export original multi-tile car icon/livery PTG images.

The parser is pinned to the archive baseline and refuses unsupported layouts.
Each source file is checked against the archive, the car manifest, and its
bounded tile record/descriptor spans before its 32-bit tile data is assembled.
PNG files preserve one copy of the source alpha bytes and provide a second
copy scaled from the PS2 0..128 alpha range to conventional 0..255 display
alpha. The raw archive remains the authoritative source.
"""

from __future__ import annotations

import static_inputs
import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import struct
import sys
import zlib

ROOT = Path(__file__).resolve().parents[1]
INPUT_BUNDLE = static_inputs.bundle_path()
REFERENCE = ROOT / "ford-racing-2" / "cars"
DEFAULT_OUTPUT = ROOT / "research" / "evidence" / "ptg-continuation" / "assets"
HEADER_SIZE = 32
PREFIX_END = 80
RECORD_SIZE = 16
DESCRIPTOR_SIZE = 64
CELL = 32
PIXEL_BYTES = CELL * CELL * 4
DD = 0xDDDDDDDD
DESCRIPTOR_PADDING = (2, 3, 4, 5, 6, 7, 8, 9, 11, 15)
SOURCE_FORMAT_BPP = {1: 32}
EXPECTED_CAR_ASSETS = 171
U64_MASK = (1 << 64) - 1


class InvalidPTG(ValueError):
    pass


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def png_bytes(width: int, height: int, rgba: bytes) -> bytes:
    if len(rgba) != width * height * 4:
        raise InvalidPTG("decoded RGBA byte count does not match image dimensions")

    def chunk(kind: bytes, payload: bytes) -> bytes:
        return struct.pack(">I", len(payload)) + kind + payload + struct.pack(">I", zlib.crc32(kind + payload))

    scanlines = b"".join(b"\0" + rgba[y * width * 4 : (y + 1) * width * 4] for y in range(height))
    return (
        b"\x89PNG\r\n\x1a\n"
        + chunk(b"IHDR", struct.pack(">2I5B", width, height, 8, 6, 0, 0, 0))
        + chunk(b"IDAT", zlib.compress(scanlines, 9))
        + chunk(b"IEND", b"")
    )


def manifest_assets() -> dict[str, dict]:
    assets: dict[str, dict] = {}
    for car_dir in sorted(p for p in REFERENCE.iterdir() if p.is_dir()):
        manifest_path = car_dir / "manifest.json"
        if not manifest_path.is_file():
            continue
        manifest = json.loads(manifest_path.read_text())
        for record in manifest.get("files", []):
            src = record.get("src", "")
            if src.startswith("GRAPHICS/GAME/CARS/"):
                role = "icon"
            elif src.startswith("GRAPHICS/GAME/LIVERY/"):
                role = "livery"
            else:
                continue
            if not src.lower().endswith(".ptg;1"):
                raise InvalidPTG(f"manifest PTG source has an unexpected suffix: {src}")
            key = src.lower()
            if key in assets:
                raise InvalidPTG(f"duplicate manifest source path: {src}")
            assets[key] = {
                "car_code": manifest["car_code"],
                "display_name": manifest["display_name"],
                "role": role,
                "manifest_path": manifest_path.relative_to(ROOT).as_posix(),
                "manifest_sha256": sha256(manifest_path.read_bytes()),
                "source_path": src,
                "destination": record["dst"],
                "bytes": record["bytes"],
                "sha256": record["sha256"],
                "reference_path": (ROOT / "ford-racing-2" / record["dst"]).relative_to(ROOT).as_posix(),
            }
    return assets


def decode_file(data: bytes, name: str) -> tuple[dict, bytes, bytes]:
    if len(data) < HEADER_SIZE:
        raise InvalidPTG(f"{name}: truncated header")
    count, columns, rows, stride, cell, width, height, last = struct.unpack_from("<8I", data)
    if cell != CELL or stride != CELL:
        raise InvalidPTG(f"{name}: expected 32-pixel cells/stride, got {cell}/{stride}")
    if count != columns * rows or columns != (width + CELL - 1) // CELL or rows != (height + CELL - 1) // CELL:
        raise InvalidPTG(f"{name}: tile grid disagrees with image dimensions")
    if (count, columns, rows, width, height, last) not in ((24, 6, 4, 165, 98, 1), (24, 8, 3, 227, 85, 1)):
        raise InvalidPTG(f"{name}: unsupported car PTG header profile")

    records_start = PREFIX_END
    descriptors_start = records_start + RECORD_SIZE * count
    pixels_start = descriptors_start + DESCRIPTOR_SIZE * count

    record_rows = []
    for index in range(count):
        extent_u, extent_v, pointer, sentinel = struct.unpack_from("<4I", data, records_start + index * RECORD_SIZE)
        want_u = min(CELL, width - (index % columns) * CELL) / CELL
        want_v = min(CELL, height - (index // columns) * CELL) / CELL
        want_u_bits = struct.unpack("<I", struct.pack("<f", want_u))[0]
        want_v_bits = struct.unpack("<I", struct.pack("<f", want_v))[0]
        if (extent_u, extent_v, sentinel) != (want_u_bits, want_v_bits, DD):
            raise InvalidPTG(f"{name}: tile record {index} has unexpected row-major extents/sentinel")
        record_rows.append({"index": index, "extent_u_bits": f"0x{extent_u:08x}", "extent_v_bits": f"0x{extent_v:08x}", "pointer_word": f"0x{pointer:08x}"})

    descriptor_first = None
    descriptor_rows = []
    tile_spans = []
    body_cursor = pixels_start
    for index in range(count):
        descriptor_at = descriptors_start + index * DESCRIPTOR_SIZE
        words = struct.unpack_from("<16I", data, descriptor_at)
        if any(words[field] != DD for field in DESCRIPTOR_PADDING):
            raise InvalidPTG(f"{name}: descriptor {index} differs at a measured 0xdd padding word")
        if descriptor_first is None:
            descriptor_first = words
        elif tuple(words[i] for i in DESCRIPTOR_PADDING) != tuple(descriptor_first[i] for i in DESCRIPTOR_PADDING):
            raise InvalidPTG(f"{name}: descriptor padding pattern varies at tile {index}")

        # Mirror FUN_0022acc8: normalize the packed +0x38 word, extract its
        # dimension exponents, look up bpp by format code, and advance the
        # payload pointer by width * height * bpp / 8.
        packed = struct.unpack_from("<Q", data, descriptor_at + 0x38)[0]
        normalized = (packed & 0xFFFFFFFFFFFF87FF) | 0x800
        exponent_x = (((normalized << 0x11) & U64_MASK) >> 32) & 0xF
        exponent_y = (((normalized << 0x0D) & U64_MASK) >> 32) & 0xF
        tile_width, tile_height = 1 << exponent_x, 1 << exponent_y
        format_code = data[descriptor_at + 0x34]
        serialized_mip_pointer = struct.unpack_from("<I", data, descriptor_at + 0x2C)[0]
        serialized_mip_count = data[descriptor_at + 0x35]
        if serialized_mip_pointer != DD or serialized_mip_count != 0xDD:
            raise InvalidPTG(
                f"{name}: descriptor {index} mip fields differ from the measured serialized sentinel profile"
            )
        bits_per_pixel = SOURCE_FORMAT_BPP.get(format_code)
        if bits_per_pixel is None:
            raise InvalidPTG(f"{name}: unsupported source format code {format_code} at descriptor {index}")
        payload_bytes = (tile_width * tile_height * bits_per_pixel) >> 3
        if (tile_width, tile_height, bits_per_pixel, payload_bytes) != (CELL, CELL, 32, PIXEL_BYTES):
            raise InvalidPTG(
                f"{name}: descriptor {index} source-computed body is "
                f"{tile_width}x{tile_height}x{bits_per_pixel}bpp ({payload_bytes} bytes)"
            )
        tile_spans.append((body_cursor, body_cursor + payload_bytes))
        descriptor_rows.append({
            "index": index,
            "format_code": format_code,
            "bits_per_pixel": bits_per_pixel,
            "dimension_exponents": [exponent_x, exponent_y],
            "dimensions": [tile_width, tile_height],
            "serialized_mip_pointer_word": f"0x{serialized_mip_pointer:08x}",
            "serialized_mip_count_byte": serialized_mip_count,
            "mip_fields_consumer_note": "serialized sentinels; FUN_00222358 treats runtime +0x2c/+0x35 as additional-mip pointer/count, so direct descriptor identity is not asserted",
            "body_span": [body_cursor, body_cursor + payload_bytes],
            "packed_dimension_word": f"0x{packed:016x}",
        })
        body_cursor += payload_bytes

    if body_cursor != len(data):
        raise InvalidPTG(f"{name}: parser-computed body span ends at 0x{body_cursor:x}, file size is 0x{len(data):x}")
    pixels_end = body_cursor

    rgba = bytearray(width * height * 4)
    for tile in range(count):
        tile_x, tile_y = tile % columns, tile // columns
        tile_start = tile_spans[tile][0]
        for y in range(CELL):
            image_y = tile_y * CELL + y
            if image_y >= height:
                continue
            for x in range(CELL):
                image_x = tile_x * CELL + x
                if image_x >= width:
                    continue
                source_at = tile_start + (y * CELL + x) * 4
                target_at = (image_y * width + image_x) * 4
                rgba[target_at : target_at + 4] = data[source_at : source_at + 4]

    alpha = rgba[3::4]
    nontransparent = [v for v in alpha if v != 0]
    if nontransparent and max(nontransparent) > 128:
        raise InvalidPTG(f"{name}: alpha byte {max(nontransparent)} exceeds the measured PS2 0..128 range")
    display = bytearray(rgba)
    display[3::4] = bytes(min(255, value * 2) for value in alpha)

    metadata = {
        "header": {"count": count, "columns": columns, "rows": rows, "stride": stride, "cell": cell, "width": width, "height": height, "last": last},
        "spans": {"header": [0, HEADER_SIZE], "prefix": [HEADER_SIZE, PREFIX_END], "records": [records_start, descriptors_start], "descriptors": [descriptors_start, pixels_start], "tile_pixels": [pixels_start, pixels_end], "pixel_bytes_per_tile": PIXEL_BYTES},
        "record_rows": record_rows,
        "descriptor_first_words": [f"0x{word:08x}" for word in (descriptor_first or ())],
        "descriptor_runtime_fields": descriptor_rows,
        "descriptor_body_span_source": "FUN_0022acc8 dimension exponent and format-table bpp calculation",
        "tile_order": "descriptor index pairs with the same-index 16-byte record in FUN_0022acc8; record U/V extents place each cell in row-major image coordinates; edge cells are clipped to header width/height",
        "pixel_profile": "format 1 selects 32 bits per pixel and PSMCT32 code 0 in the PAL table; PCSX2 reads PSMCT32 words as 0x00AA00BB00GG00RR, corresponding to little-endian RGBA source bytes",
        "source_rgba_sha256": sha256(bytes(rgba)),
        "rgba_bytes": len(rgba),
        "alpha_value_counts": {str(k): v for k, v in sorted(Counter(alpha).items())},
        "display_alpha_mapping": "min(255, 2 * source_alpha_byte) for a conventional PNG preview; source bytes are retained in the raw-alpha companion; game-menu alpha behavior still awaits observed output",
    }
    return metadata, bytes(rgba), bytes(display)


def verify_png(path: Path, width: int, height: int, expected: bytes) -> None:
    data = path.read_bytes()
    if not data.startswith(b"\x89PNG\r\n\x1a\n"):
        raise InvalidPTG(f"{path}: missing PNG signature")
    cursor = 8
    image_header = None
    compressed = bytearray()
    ended = False
    while cursor < len(data):
        if cursor + 12 > len(data):
            raise InvalidPTG(f"{path}: truncated PNG chunk header")
        length = struct.unpack_from(">I", data, cursor)[0]
        kind = data[cursor + 4 : cursor + 8]
        start = cursor + 8
        end = start + length
        if end + 4 > len(data):
            raise InvalidPTG(f"{path}: truncated PNG chunk payload")
        payload = data[start:end]
        recorded_crc = struct.unpack_from(">I", data, end)[0]
        if zlib.crc32(kind + payload) != recorded_crc:
            raise InvalidPTG(f"{path}: PNG chunk CRC mismatch")
        if kind == b"IHDR":
            image_header = payload
        elif kind == b"IDAT":
            compressed.extend(payload)
        elif kind == b"IEND":
            ended = True
            if end + 4 != len(data):
                raise InvalidPTG(f"{path}: trailing data after IEND")
        cursor = end + 4
    if not ended or image_header is None:
        raise InvalidPTG(f"{path}: missing IHDR or IEND")
    header = struct.unpack(">2I5B", image_header)
    if header != (width, height, 8, 6, 0, 0, 0):
        raise InvalidPTG(f"{path}: PNG dimensions/encoding differ from expected RGBA8")
    scanlines = zlib.decompress(compressed)
    row_bytes = width * 4
    if len(scanlines) != height * (row_bytes + 1):
        raise InvalidPTG(f"{path}: PNG decompressed length differs from expected dimensions")
    decoded = bytearray()
    for y in range(height):
        start = y * (row_bytes + 1)
        if scanlines[start] != 0:
            raise InvalidPTG(f"{path}: unsupported PNG filter at row {y}")
        decoded.extend(scanlines[start + 1 : start + 1 + row_bytes])
    if bytes(decoded) != expected:
        raise InvalidPTG(f"{path}: independent PNG readback bytes differ from decoded source")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, default=INPUT_BUNDLE / "games" / "ford-racing-2")
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--verify-only", action="store_true", help="verify all archive/manifest/input bounds without writing images")
    args = parser.parse_args()

    sys.path.insert(0, str(ROOT/'tools'))
    from corpus_binding import Baseline

    baseline = Baseline(args.source)
    manifests = manifest_assets()
    archive_car_graphics = {
        entry.path.lstrip("/").lower(): entry
        for entry in baseline.entries(".ptg;1")
        if entry.path.lstrip("/").upper().startswith(("GRAPHICS/GAME/CARS/", "GRAPHICS/GAME/LIVERY/"))
    }
    missing_archive = sorted(set(manifests) - set(archive_car_graphics))
    if missing_archive:
        raise InvalidPTG(f"{len(missing_archive)} manifest assets absent from archive: {missing_archive[:4]}")
    corpus_entries = {key: archive_car_graphics[key] for key in manifests}
    if len(corpus_entries) != EXPECTED_CAR_ASSETS:
        raise InvalidPTG(f"expected {EXPECTED_CAR_ASSETS} car icon/livery PTGs, found {len(corpus_entries)}")

    output_entries = []
    failures = []
    if not args.verify_only:
        args.output.mkdir(parents=True, exist_ok=True)
    for key, entry in sorted(corpus_entries.items()):
        item = manifests[key]
        try:
            raw_file = entry.load()
            ref_path = ROOT / item["reference_path"]
            ref_bytes = ref_path.read_bytes()
            if len(raw_file) != item["bytes"] or sha256(raw_file) != item["sha256"] or raw_file != ref_bytes:
                raise InvalidPTG("archive, manifest, and checked-in reference bytes disagree")
            metadata, rgba, display = decode_file(raw_file, entry.path)
            item_result = {
                **item,
                "archive_sha256": entry.sha256,
                "archive_bytes": entry.bytes,
                "role": item["role"],
                "metadata": metadata,
            }
            if not args.verify_only:
                stem = Path(item["source_path"]).name.removesuffix(".ptg;1")
                relative_dir = Path(item["car_code"]) / item["role"]
                raw_path = args.output / relative_dir / f"{stem}.raw-alpha.png"
                display_path = args.output / relative_dir / f"{stem}.png"
                raw_path.parent.mkdir(parents=True, exist_ok=True)
                raw_png = png_bytes(metadata["header"]["width"], metadata["header"]["height"], rgba)
                display_png = png_bytes(metadata["header"]["width"], metadata["header"]["height"], display)
                raw_path.write_bytes(raw_png)
                display_path.write_bytes(display_png)
                verify_png(raw_path, metadata["header"]["width"], metadata["header"]["height"], rgba)
                verify_png(display_path, metadata["header"]["width"], metadata["header"]["height"], display)
                item_result["outputs"] = {
                    "raw_alpha_png": {"path": raw_path.relative_to(ROOT).as_posix(), "bytes": len(raw_png), "sha256": sha256(raw_png)},
                    "display_png": {"path": display_path.relative_to(ROOT).as_posix(), "bytes": len(display_png), "sha256": sha256(display_png)},
                }
            output_entries.append(item_result)
        except (OSError, ValueError) as exc:
            failures.append({"source": entry.path, "error": str(exc)})
    result = {
        "schema": "fr2-car-ptg-recovery/v1",
        "provenance": baseline.provenance,
        "corpus": {"expected_assets": EXPECTED_CAR_ASSETS, "manifest_assets": len(manifests), "archive_car_graphics_entries": len(archive_car_graphics), "associated_archive_entries": len(corpus_entries), "verified_assets": len(output_entries), "failures": failures},
        "source_code_sha256": {
            "recover_car_ptg.py": sha256(Path(__file__).read_bytes()),
            "corpus_binding.py": sha256((ROOT/'tools' / "corpus_binding.py").read_bytes()),
        },
        "pixel_interpretation_status": "channel byte order and record-to-descriptor raster placement are source-supported; source alpha bytes are preserved and a 2x preview is emitted; direct PTG descriptor-to-upload consumer identity and observed game-menu composition remain unresolved",
        "claim_limits": ["A recognizable preview is visual corroboration, not proof of channel order or runtime texture sampling.", "The image outputs are separate menu icon/livery images and do not replace model texture maps.", "No model mesh, UV/material binding, or in-game vehicle assembly claim is made here."],
        "assets": output_entries,
    }
    receipt_dir = ROOT / "research" / "evidence" / "ptg-continuation"
    receipt_dir.mkdir(parents=True, exist_ok=True)
    receipt_path = receipt_dir / ("archive-layout-validation.json" if args.verify_only else "recovered-car-ptgs.json")
    receipt_path.write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps({"receipt": receipt_path.relative_to(ROOT).as_posix(), "corpus": result["corpus"], "outputs_written": not args.verify_only}, sort_keys=True))
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
