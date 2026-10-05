#!/usr/bin/env python3
"""Read-only FR2 car-geometry numeric probes; emits a source-pinned JSON receipt."""
from __future__ import annotations

import argparse
import hashlib
import itertools
import json
import math
import struct
import sys
from pathlib import Path
from typing import Any


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def affine_fit(pairs: list[tuple[float, float]]) -> dict[str, float]:
    xs = [x for x, _ in pairs]
    ys = [y for _, y in pairs]
    xm = sum(xs) / len(xs)
    ym = sum(ys) / len(ys)
    denom = sum((x - xm) ** 2 for x in xs)
    scale = sum((x - xm) * (y - ym) for x, y in pairs) / denom if denom else 0.0
    offset = ym - scale * xm
    resid = sum((y - (scale * x + offset)) ** 2 for x, y in pairs)
    total = sum((y - ym) ** 2 for y in ys)
    return {
        "scale": scale,
        "offset": offset,
        "r_squared": 1.0 - resid / total if total else 0.0,
        "rmse": math.sqrt(resid / len(pairs)),
    }


def f32(value: float) -> float:
    return struct.unpack("<f", struct.pack("<f", value))[0]


def run(data_root: Path, tools_root: Path) -> dict[str, Any]:
    sys.path.insert(0, str(tools_root))
    import ps2_container  # type: ignore[import-not-found]
    import ps2_sections  # type: ignore[import-not-found]

    paths = sorted(data_root.glob("*.PS2;1"))
    records: list[dict[str, Any]] = []
    files: list[dict[str, Any]] = []
    float_bit_probe = {"samples": 0, "max_abs_error_from_raw_over_16384": 0.0}
    for path in paths:
        data = path.read_bytes()
        tex = ps2_container.parse(data)
        parsed = ps2_sections.parse(data, "loader68")
        files.append({
            "name": path.name,
            "size": len(data),
            "sha256": sha256(data),
            "palette_region": tex["textures"]["palette_region"],
            "geometry_table": parsed["geometry"]["table"],
            "headers": len(parsed["geometry"]["headers"]),
            "six_byte_samples": sum(
                header["planes"]["six_byte"]["count"]
                for header in parsed["geometry"]["headers"]
            ),
        })
        table = parsed["geometry"]["table"]
        headers = parsed["geometry"]["headers"]
        header_index = 0
        for record_index in range(table["count"]):
            offset = table["offset"] + record_index * 0x34
            # The two halfword counts are separated in the 0x34 record.
            group_counts = (
                struct.unpack_from("<H", data, offset + 0x1C)[0],
                struct.unpack_from("<H", data, offset + 0x28)[0],
            )
            bbox_words = [
                struct.unpack_from("<f", data, offset + field)[0]
                for field in (4, 8, 12, 16, 20, 24)
            ]
            bbox = [(bbox_words[2 * axis], bbox_words[2 * axis + 1]) for axis in range(3)]
            axis_values: list[list[int]] = [[], [], []]
            for group_count in group_counts:
                for header in headers[header_index : header_index + group_count]:
                    plane = header["planes"]["six_byte"]
                    count = plane["count"]
                    if count:
                        values = struct.unpack_from("<" + "h" * (3 * count), data, plane["offset"])
                        for value in values:
                            bits = (0x44400000 + value) & 0xFFFFFFFF
                            decoded = struct.unpack("<f", struct.pack("<I", bits))[0] - 768.0
                            float_bit_probe["max_abs_error_from_raw_over_16384"] = max(
                                float_bit_probe["max_abs_error_from_raw_over_16384"],
                                abs(decoded - value / 16384.0),
                            )
                            float_bit_probe["samples"] += 1
                        for axis in range(3):
                            axis_values[axis].extend(values[axis::3])
                header_index += group_count
            if any(axis_values):
                # A nonempty geometry record is expected to have triplets in all lanes.
                extrema = [(min(axis), max(axis)) if axis else (0, 0) for axis in axis_values]
                records.append({
                    "file": path.name,
                    "record_index": record_index,
                    "signed_extrema": extrema,
                    "bbox": bbox,
                    "maxabs_bbox": [max(abs(lo), abs(hi)) for lo, hi in bbox],
                })

    if not paths:
        raise RuntimeError(f"no model files matched {data_root}/*.PS2;1")
    axes = [[], [], []]
    for record in records:
        for axis in range(3):
            lo, hi = record["signed_extrema"][axis]
            bblo, bbhi = record["bbox"][axis]
            axes[axis].extend(((float(lo), bblo), (float(hi), bbhi)))
    pooled_fits = [affine_fit(pairs) for pairs in axes]
    permutations = []
    for permutation in itertools.permutations(range(3)):
        fits = [affine_fit([pair for i, pair in enumerate(axes[permutation[i]])]) for i in range(3)]
        permutations.append({
            "source_axis_for_bbox_axis": list(permutation),
            "r_squared": [fit["r_squared"] for fit in fits],
        })

    # Test decoder-like per-record maps and whether they actually meet serialized bounds.
    local: dict[str, dict[str, Any]] = {}
    for label, denominator, centered in (
        ("maxabs_over_16384_no_center", 16384.0, False),
        ("maxabs_over_32767_no_center", 32767.0, False),
        ("bbox_halfextent_over_32767_centered", 32767.0, True),
        ("bbox_halfextent_over_16384_centered", 16384.0, True),
    ):
        contained = 0
        axis_contained = [0, 0, 0]
        endpoints_match = 0
        axis_endpoints_match = [0, 0, 0]
        normalized_error: list[float] = []
        endpoint_mae: list[float] = []
        for record in records:
            axis_ok = []
            axis_match = []
            for axis in range(3):
                raw_lo, raw_hi = record["signed_extrema"][axis]
                bbox_lo, bbox_hi = record["bbox"][axis]
                amplitude = record["maxabs_bbox"][axis]
                center = (bbox_lo + bbox_hi) / 2 if centered else 0.0
                if centered:
                    amplitude = (bbox_hi - bbox_lo) / 2
                mapped_lo = center + raw_lo * amplitude / denominator
                mapped_hi = center + raw_hi * amplitude / denominator
                axis_ok.append(mapped_lo >= bbox_lo - 1e-6 and mapped_hi <= bbox_hi + 1e-6)
                axis_contained[axis] += axis_ok[-1]
                span = max(abs(bbox_hi - bbox_lo), 1e-12)
                if span > 1e-10:
                    normalized_error.extend((abs(mapped_lo - bbox_lo) / span, abs(mapped_hi - bbox_hi) / span))
                endpoint_mae.extend((abs(mapped_lo - bbox_lo), abs(mapped_hi - bbox_hi)))
                quant_step = amplitude / denominator if not centered else amplitude / denominator
                axis_match.append(
                    abs(mapped_lo - bbox_lo) <= quant_step + 1e-6
                    and abs(mapped_hi - bbox_hi) <= quant_step + 1e-6
                )
                axis_endpoints_match[axis] += axis_match[-1]
            contained += all(axis_ok)
            endpoints_match += all(axis_match)
        local[label] = {
            "records_all_three_axes_inside_bbox": contained,
            "axis_inside_counts": axis_contained,
            "records_all_three_axes_endpoints_match_within_one_quantization_step": endpoints_match,
            "axis_endpoints_match_within_one_quantization_step": axis_endpoints_match,
            "normalized_endpoint_mae": sum(normalized_error) / len(normalized_error) if normalized_error else 0.0,
            "endpoint_mae": sum(endpoint_mae) / len(endpoint_mae),
        }

    fixed_candidates = []
    for scale in (1 / 32768, 1 / 16384, 1 / 8192, 1 / 4096, 1 / 65536):
        for bias in (0, -768, 768, -6144, 6144, -768 / 16, 768 / 16, -6144 / 16, 6144 / 16):
            full = 0
            for record in records:
                if all(
                    record["signed_extrema"][axis][0] * scale + bias >= record["bbox"][axis][0] - 1e-6
                    and record["signed_extrema"][axis][1] * scale + bias <= record["bbox"][axis][1] + 1e-6
                    for axis in range(3)
                ):
                    full += 1
            fixed_candidates.append({"scale": scale, "bias": bias, "all_axes_inside": full})

    bound_validation: list[dict[str, Any]] = []
    per_car: dict[str, dict[str, int]] = {}
    for record in records:
        axis_rows = []
        for axis in range(3):
            raw_lo, raw_hi = record["signed_extrema"][axis]
            bbox_lo, bbox_hi = record["bbox"][axis]
            amplitude = record["maxabs_bbox"][axis]
            step = amplitude / 16384.0
            mapped_lo = raw_lo * step
            mapped_hi = raw_hi * step
            axis_rows.append({
                "raw_extrema": [raw_lo, raw_hi],
                "bbox": [bbox_lo, bbox_hi],
                "maxabs": amplitude,
                "quantization_step": step,
                "mapped_extrema": [mapped_lo, mapped_hi],
                "endpoint_error": [mapped_lo - bbox_lo, mapped_hi - bbox_hi],
                "within_one_step": abs(mapped_lo - bbox_lo) <= step + 1e-6
                and abs(mapped_hi - bbox_hi) <= step + 1e-6,
            })
        match = all(axis["within_one_step"] for axis in axis_rows)
        bound_validation.append({
            "file": record["file"],
            "record_index": record["record_index"],
            "axes": axis_rows,
            "all_axes_within_one_step": match,
        })
        item = per_car.setdefault(record["file"], {"nonempty_records": 0, "all_axes_within_one_step": 0})
        item["nonempty_records"] += 1
        item["all_axes_within_one_step"] += int(match)

    near_extrema = {"within_1_of_negative_16384": 0, "within_1_of_positive_16384": 0,
                    "within_1_of_negative_32767": 0, "within_1_of_positive_32767": 0}
    for record in records:
        for lo, hi in record["signed_extrema"]:
            for value in (lo, hi):
                near_extrema["within_1_of_negative_16384"] += abs(value + 16384) <= 1
                near_extrema["within_1_of_positive_16384"] += abs(value - 16384) <= 1
                near_extrema["within_1_of_negative_32767"] += abs(value + 32767) <= 1
                near_extrema["within_1_of_positive_32767"] += abs(value - 32767) <= 1
    palette_claim_check = []
    old_spans = (
        ("G_TORINO.PS2;1", 1748, 6410),
        ("F100_56.PS2;1", 1876, 3930),
        ("TAURUSA.PS2;1", 2196, 4250),
    )
    by_name = {entry["name"]: entry for entry in files}
    for name, start, end in old_spans:
        region = by_name[name]["palette_region"]
        palette_claim_check.append({
            "file": name,
            "historical_span": [start, end],
            "palette_region": region,
            "fully_inside_palette_region": region[0] <= start < end <= region[1],
        })

    tool_hashes = {}
    for name in ("ps2_sections.py", "ps2_container.py"):
        data = (tools_root / name).read_bytes()
        tool_hashes[name] = sha256(data)
    return {
        "schema_version": 1,
        "status": "measured_hypothesis_probe",
        "analysis_script_sha256": sha256(Path(__file__).resolve().read_bytes()),
        "inputs": {"data_root": str(data_root), "file_count": len(files), "files": files},
        "tools": {"root": str(tools_root), "sha256": tool_hashes},
        "method": {
            "record_association": "Union of all six_byte planes in both header-count groups for each 0x34 record; this correspondence is a hypothesis.",
            "component_decode": "little-endian signed int16 triplets, because the traced packet uses V3-16 with USN clear.",
            "bbox_fields": "three low/high f32 pairs at record offsets +4/+8, +12/+16, +20/+24.",
            "map_metrics": "pooled affine endpoint fit, endpoint containment, per-record local scale hypotheses, fixed scale/bias grid, signed extrema census, float-bit addition identity.",
            "superseded_attempt": "An early exploratory pass read the second group count from adjacent offset +0x1e. Its conclusions are withdrawn; this script reads the true second field at +0x28.",
        },
        "counts": {
            "files": len(files),
            "geometry_records": sum(file["geometry_table"]["count"] for file in files),
            "headers": sum(file["headers"] for file in files),
            "six_byte_samples": sum(file["six_byte_samples"] for file in files),
            "records_with_nonempty_six_byte_data": len(records),
        },
        "global_affine_fits": pooled_fits,
        "axis_permutation_fits": permutations,
        "per_record_maps": local,
        "per_record_maxabs_scale_bound_validation": {
            "formula": "mapped = signed16_value / 16384 * max(abs(bbox_min), abs(bbox_max)) per axis",
            "records_all_three_axes_within_one_quantization_step": sum(
                row["all_axes_within_one_step"] for row in bound_validation
            ),
            "records": bound_validation,
            "per_car": per_car,
        },
        "fixed_scale_bias_grid": fixed_candidates,
        "signed_extrema_counts": near_extrema,
        "float_bit_addition": float_bit_probe,
        "historical_strip_zone_check": palette_claim_check,
        "limits": [
            "The parser establishes serialized spans and candidate source counts; it does not prove six_byte plane semantics.",
            "The 0x34 record endpoint relationship and union of its two count groups are hypotheses, not a traced producer-consumer mapping.",
            "Containment and endpoint fit are not renderer or hardware equivalence.",
            "VIF mode/row and later VU transform state are only partially statically traced; this probe is offline numeric analysis.",
        ],
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--data-root", type=Path, required=True)
    parser.add_argument("--tools-root", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    result = run(args.data_root, args.tools_root)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
    print(json.dumps({"output": str(args.output), "counts": result["counts"],
                      "per_record_maps": result["per_record_maps"],
                      "palette_zone_checks": result["historical_strip_zone_check"]}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
