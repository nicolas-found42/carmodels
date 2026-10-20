"""Explicit variable-Q LOD controls for the pinned original software GS.

Synthetic original GS events isolate sampler behavior; no authored vehicle
material selection or running-game frame is asserted.
"""

import argparse
import hashlib
import json
from pathlib import Path

from mc3_reference_runtime import run_gs, write_gs_dump
from mc3_vehicle_mip import packets
from mc3_vehicle_sampler import SOURCES, verify_sources

FIXTURE = (
    Path(__file__).resolve().parents[1]
    / "research/evidence/midnight-club-3-remix/previews/vehicle-variable-mip.json"
)
EXTRA_SOURCES = {
    "GSVector4.h": "d1bbb95e6a3a43344467c70651e982fe9d4ee2b09717637edc698a7cd8d725c1",
    "GSVertexTrace.cpp": "04f2b48d0b3d5fe6a012188f820352dbcce274b4cddbe852c4c0a2cae173ec6f",
    "GSScanlineEnvironment.h": "b9972ac00b97f66a2084f1269ce3ea4493d3135f4f258c8de45eb7efa4ac282d",
    "GSVector4i.h": "f469fab789fd335e9544149eccd00bb20ab4e39566d1ca1df573fa2cdf049992",
}


def controls():
    levels = []
    for level, size in enumerate([8, 4, 2]):
        raw = bytes(
            (x * 37 + y * 19 + channel * 53 + level * 41) & 255
            for y in range(size)
            for x in range(size)
            for channel in range(4)
        )
        levels.append(dict(width=size, height=size, data_hex=raw.hex()))
    rows = []
    profiles = [(m, 0, 8, [1.1, 0.15, 0.57], 0, 1) for m in range(2, 6)]
    profiles += [(m, 1, -4, [1.7, 0.25, 0.7], 3, 0) for m in range(2, 6)]
    profiles += [(m, 2, 0, [1.4, 0.3, 0.8], 1, 1) for m in [3, 5]]
    profiles += [
        (3, 0, 0, [0.125, 0.0625, 0.09], 0, 1),
        (5, 0, 0, [0.8, 0.55, 0.65], 2, 1),
    ]
    profiles += [(m, 0, 0, [0.707107, 0.70709, 0.70712], 5, 0) for m in range(2, 6)]
    profiles += [(3, 3, -8, [1.1, 0.5, 0.8], 4, 0), (5, 3, 2047, [1.1, 0.5, 0.8], 6, 1)]
    for mmin, scale, k, qs, start, mag in profiles:
        vertices = [
            dict(xy=[x * 16, y * 16], z=10, stq=[s, t, q], rgba=[128] * 4)
            for (x, y, s, t), q in zip(
                [
                    (start, 0, -0.23, 1.2),
                    (start + 24, 0, 1.7, -0.31),
                    (start, 20, 0.27, 0.83),
                ],
                qs,
                strict=True,
            )
        ]
        rows.append(
            dict(
                name=f"mmin{mmin}-l{scale}-k{k}-x{start}",
                tex1=str(
                    2 << 2 | mag << 5 | mmin << 6 | scale << 19 | (k & 4095) << 32
                ),
                clamp="0",
                levels=levels,
                vertices=vertices,
            )
        )
    return rows


def reference(output, source_dir):
    files = {name: (source_dir / name).read_bytes() for name in SOURCES | EXTRA_SOURCES}
    source = verify_sources(files)
    for name, digest in EXTRA_SOURCES.items():
        if hashlib.sha256(files[name]).hexdigest() != digest:
            raise ValueError("pinned mip source changed: " + name)
    source["sources"] = dict(source["sources"]) | EXTRA_SOURCES
    output.mkdir(parents=True, exist_ok=False)
    rows = []
    for case in controls():
        dump = output / (case["name"] + ".gs")
        write_gs_dump(dump, packets(case))
        execution = run_gs(dump, output / case["name"], save_depth=True)
        row = dict(case=case, execution=execution)
        for name in ["frames", "depth_frames"]:
            final = {v["file"].split("_")[1]: v for v in execution[name]}
            if (
                len(final) != 3
                or len({(v["sha256"], tuple(v["size"])) for v in final.values()}) != 1
            ):
                raise ValueError("original mip frames differ")
            row[name] = list(final.values())
        rows.append(row)
        print("PASS original variable mip", case["name"], flush=True)
    result = dict(
        schema=1,
        **source,
        records=rows,
        claim_limits=[
            "Controlled LCM0/MXL2, normal positive varying Q, L0..3, signed K and MMIN2..5.",
            "Three controlled CT32 levels and nonzero alpha differences expose lane behavior.",
            "Pinned AVX2/FMA software GS, not physical PS2 or a booted MC3 frame.",
            "No vehicle shader binding, texture residency or showcase activation claim.",
        ],
    )
    (output / "reference.json").write_text(json.dumps(result, indent=2) + "\n")
    return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--source-dir", type=Path, required=True)
    parser.add_argument("--write-fixture", action="store_true")
    args = parser.parse_args()
    proof = reference(args.output, args.source_dir)
    if args.write_fixture:
        FIXTURE.write_text(json.dumps(proof, indent=2) + "\n")
