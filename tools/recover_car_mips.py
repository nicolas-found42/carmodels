#!/usr/bin/env python3
"""Export the stored extra mip planes from the archive-matched 35-car subset.

Decoded PNGs are emitted only when the existing loader-derived source/GS
address mapping gives a complete pixel permutation. Original plane bytes are
always retained with their exact offsets and hashes.
"""
from __future__ import annotations

import static_inputs
from collections import Counter
import hashlib
import json
from pathlib import Path
import re
import struct
import sys
import zlib

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SOURCE = static_inputs.bundle_path()
OUT = ROOT / "research/evidence/mip-continuation"


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def png_bytes(width: int, height: int, rgba: bytes) -> bytes:
    if len(rgba) != width * height * 4:
        raise ValueError("RGBA byte count does not match dimensions")

    def chunk(kind: bytes, payload: bytes) -> bytes:
        return struct.pack(">I", len(payload)) + kind + payload + struct.pack(">I", zlib.crc32(kind + payload))

    scanlines = b"".join(b"\0" + rgba[y * width * 4:(y + 1) * width * 4] for y in range(height))
    return (b"\x89PNG\r\n\x1a\n" +
            chunk(b"IHDR", struct.pack(">2I5B", width, height, 8, 6, 0, 0, 0)) +
            chunk(b"IDAT", zlib.compress(scanlines)) + chunk(b"IEND", b""))


def decode_level(data: bytes, item: dict, level_no: int, mip_record: tuple[int, ...],
                 ps2_container, ps2_texture_indices) -> tuple[bytes, str]:
    level = item["levels"][level_no]
    width, height = level["width"], level["height"]
    plane = data[level["offset"]:level["offset"] + level["size"]]
    fmt = item["format"]
    if len(plane) != level["size"]:
        raise ValueError("truncated mip plane")
    if fmt == 1:
        rgba = plane
        method = "format1-direct-rgba"
    elif fmt == 3:
        if item["packed"]:
            # The format-3 packed route uploads CT32 at half dimensions and
            # samples PSMT8; this is the same GS-table permutation as L0.
            indices = ps2_container.unswizzle8(plane, width, height)
            method = "format3-packed-ct32-to-t8"
        else:
            indices = plane
            method = "format3-direct-t8"
        palette = data[item["palette_offset"]:item["palette_offset"] + item["palette_bytes"]]
        entries = [palette[i:i + 4] for i in range(0, 256 * 4, 4)]
        if len(indices) != width * height or len(entries) != 256:
            raise ValueError("format-3 pixel or CLUT count differs from the measured profile")
        rgba = b"".join(entries[index] for index in indices)
    elif fmt == 4:
        if item["packed"]:
            dbw, tbw = mip_record[3] & 0xFFFF, mip_record[1] & 0xFFFF
            order = ps2_texture_indices._packed4_order(width, height, width // 2,
                                                       height // 2, dbw, tbw)
            indices = bytes((plane[n // 2] >> ((n & 1) * 4)) & 15 for n in order)
            method = "format4-packed-ct16-to-t4"
        else:
            indices = bytes(n for byte in plane for n in (byte & 15, byte >> 4))
            method = "format4-direct-t4"
        palette = data[item["palette_offset"]:item["palette_offset"] + item["palette_bytes"]]
        entries = [palette[i:i + 4] for i in range(0, 16 * 4, 4)]
        if len(indices) != width * height or len(entries) != 16:
            raise ValueError("format-4 pixel or CLUT count differs from the measured profile")
        rgba = b"".join(entries[index] for index in indices)
    else:
        raise ps2_container.Unsupported(f"format {fmt} has no measured extra-mip decoder")
    if len(rgba) != width * height * 4:
        raise ValueError("decoded RGBA byte count differs from logical dimensions")
    return rgba, method


def main() -> None:
    import argparse
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, default=DEFAULT_SOURCE)
    parser.add_argument("--output", type=Path, default=OUT)
    args = parser.parse_args()
    sys.path.insert(0, str(ROOT/'tools'))
    import ps2_container
    import ps2_sections
    import ps2_texture_indices
    from corpus_binding import Baseline

    baseline = Baseline(args.source / "games/ford-racing-2")
    archive = {entry.path.lstrip("/"): entry for entry in baseline.entries(".ps2;1")}
    args.output.mkdir(parents=True, exist_ok=True)
    (args.output / "levels").mkdir(exist_ok=True)
    code_names = ["ps2_container.py", "ps2_texture_indices.py", "ps2_sections.py",
                  "format_contracts.py", "corpus_binding.py"]
    pins = {name: sha((ROOT/'tools' / name).read_bytes()) for name in code_names}
    cars = []
    outcomes = Counter()
    profiles = Counter()
    level_rows = []
    for folder in sorted((ROOT / "reference/ford/cars").iterdir()):
        manifest_path = folder / "manifest.json"
        if not manifest_path.is_file():
            continue
        manifest = json.loads(manifest_path.read_text())
        model_file = next(folder.glob("model/*.PS2;1"))
        src = next(file for file in manifest["files"] if "/model/" in file["dst"])
        entry = archive[src["src"]]
        data = model_file.read_bytes()
        if sha(data) != src["sha256"] or data != entry.load():
            raise ValueError(f"{folder.name}: reference model differs from archive/manifest")
        parsed = ps2_sections.parse(data)
        car_item_rows = []
        for item in parsed["textures"]["items"]:
            field = int(item["descriptor_field"], 16)
            packed = bool(field & 0x100)
            item["packed"] = packed
            tex_stem = f"{item['index']:03d}-" + re.sub(r"[^A-Za-z0-9_.-]", "_", item["name"])
            for level_no, level in enumerate(item["levels"][1:], 1):
                rec_offset = item["descriptor_offset"] + 0x40 + 16 * (level_no - 1)
                record = struct.unpack_from("<4I", data, rec_offset)
                raw = data[level["offset"]:level["offset"] + level["size"]]
                if len(raw) != level["size"]:
                    raise ValueError(f"{folder.name}/{item['name']} L{level_no}: truncated source plane")
                base = f"{folder.name}/{tex_stem}.L{level_no}"
                raw_rel = Path("levels") / (base + ".plane.bin")
                raw_path = args.output / raw_rel
                raw_path.parent.mkdir(parents=True, exist_ok=True)
                raw_path.write_bytes(raw)
                row = {
                    "car": folder.name, "archive_path": entry.path,
                    "model_sha256": sha(data), "texture_index": item["index"],
                    "texture_name": item["name"], "format": item["format"],
                    "packed_upload": packed, "level": level_no,
                    "logical_dimensions": [level["width"], level["height"]],
                    "source_file_offset": level["offset"], "source_byte_count": level["size"],
                    "source_sha256": sha(raw), "raw_plane": raw_rel.as_posix(),
                    "mip_record_file_offset": rec_offset,
                    "mip_record_words": [f"0x{x:08x}" for x in record],
                    "allocation_bytes_high16": record[0] >> 16,
                    "miptbp_tbw_low16": record[1] & 0xFFFF,
                    "serialized_source_pointer_word": f"0x{record[2]:08x}",
                    "bitbltbuf_dbw_low16": record[3] & 0xFFFF,
                    "palette_file_offset": item["palette_offset"],
                    "palette_bytes": item["palette_bytes"],
                    "decode_status": "unresolved",
                    "decoder": None,
                }
                profiles[(item["format"], packed, level["width"], level["height"],
                          record[1] & 0xFFFF, record[3] & 0xFFFF)] += 1
                try:
                    rgba, method = decode_level(data, item, level_no, record,
                                                ps2_container, ps2_texture_indices)
                    png_rel = Path("levels") / (base + ".rgba.png")
                    png_path = args.output / png_rel
                    png_path.write_bytes(png_bytes(level["width"], level["height"], rgba))
                    row.update({"decode_status": "decoded_static_mapping",
                                "decoder": method, "rgba_sha256": sha(rgba),
                                "png": png_rel.as_posix(), "png_sha256": sha(png_path.read_bytes()),
                                "alpha_policy": "stored palette/texel alpha retained verbatim"})
                    outcomes["decoded_static_mapping"] += 1
                except ps2_container.Unsupported as exc:
                    row["blocker"] = str(exc)
                    outcomes["raw_plane_only_unsupported_profile"] += 1
                car_item_rows.append(row)
                level_rows.append(row)
        cars.append({"car": folder.name, "archive_path": entry.path,
                     "model_sha256": sha(data), "model_bytes": len(data),
                     "extra_mip_levels": car_item_rows})
        print(json.dumps({"car": folder.name, "extra_mip_levels": len(car_item_rows)}), flush=True)

    profile_rows = [{"format": k[0], "packed_upload": k[1], "logical_dimensions": [k[2], k[3]],
                     "MIPTBP_TBW": k[4], "BITBLTBUF_DBW": k[5], "count": n}
                    for k, n in sorted(profiles.items())]
    index = {
        "schema_version": 1,
        "status": "exported_with_per_level_disposition",
        "scope": "Archive-bound 35-car .PS2;1 model containers only; PTG menu icons/liveries excluded.",
        "provenance": baseline.provenance,
        "source_code_sha256": pins,
        "recovery_tool_sha256": sha(Path(__file__).read_bytes()),
        "validator_tool_sha256": sha((ROOT / "tools/validate_car_mips.py").read_bytes()),
        "summary": {"cars": len(cars), "extra_mip_levels": len(level_rows),
                    "decoded_pngs": outcomes["decoded_static_mapping"],
                    "raw_only_levels": outcomes["raw_plane_only_unsupported_profile"]},
        "profile_counts": profile_rows,
        "limits": [
            "Decoded images implement the traced static source/GS table address mapping; no original game draw, dynamic GS base allocation, emulator render, or PS2 hardware output was observed.",
            "Serialized mip records contain zero source-pointer words; the loader fills those at runtime. MIPTBP/DBW values are retained exactly and not treated as runtime addresses.",
            "Stored palette alpha is preserved. GS blend/test state, filtering, CLUT timing and material use are outside these PNGs.",
            "Every raw source plane is exported whether or not a PNG decoder profile is supported."
        ],
        "cars": cars,
    }
    (args.output / "mip-index.json").write_text(json.dumps(index, indent=2) + "\n")
    print(json.dumps({"summary": index["summary"], "profiles": profile_rows}, indent=2))


if __name__ == "__main__":
    main()
