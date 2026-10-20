"""Original software-GS high unsigned32 triangle depth precision controls."""

import argparse
import copy
import json
import hashlib
from pathlib import Path

from mc3_reference_runtime import ad, run_gs, write_gs_dump
from mc3_vehicle_depth32 import (
    READBACK_SOURCES,
    clear_packets,
    export_depth32,
    registers32,
)
from mc3_vehicle_depth32 import SOURCES as RASTER_SOURCES
from mc3_vehicle_fragment import base_state
from mc3_vehicle_gif import packed
from mc3_vehicle_raster import cases as raster_cases

SOURCES = {
    **RASTER_SOURCES,
    "GSVertexTrace.cpp": "04f2b48d0b3d5fe6a012188f820352dbcce274b4cddbe852c4c0a2cae173ec6f",
    "GSVertexTraceFMM.cpp": "51f8ef8c4f55c8c3198f21f2c9a7ea52effece437789529d65beec6eb2b06b80",
}
FIXTURE = (
    Path(__file__).resolve().parents[1]
    / "research/evidence/midnight-club-3-remix/previews/vehicle-high-z.json"
)


def cases():
    rows = []
    values = [
        ("constant-max", [0xFFFFFFFF] * 3),
        ("constant-high", [0x80000001] * 3),
        ("constant-near", [0x7FFFFFFF] * 3),
        ("wide-varying", [0, 0xFFFFFFFF, 0x80000000]),
        ("near-boundary", [0x7FFFFFFE, 0x80000001, 0x80000007]),
        ("high-small-cross", [0xFFFFFFF0, 0xFFFFFFFF, 0xFFFFFFE0]),
        ("mixed-small-cross", [0x7FFFFFFF, 0x80000000, 0x7FFFFFFE]),
        ("low-control", [100, 1000, 1500]),
    ]
    for name, depths in values:
        for fractional in [False, True]:
            vertices = copy.deepcopy(raster_cases()[1]["vertices"])
            for i, vertex in enumerate(vertices):
                vertex["xy"] = [[32, 48], [1360, 96], [128, 1136]][i]
                if fractional:
                    vertex["xy"] = [vertex["xy"][0] + 7, vertex["xy"][1] + 11]
                vertex["z"] = depths[i]
                vertex["rgba"] = [17, 39, 113, 128]
            rows.append(
                dict(
                    name=name + ("-fractional" if fractional else ""),
                    vertices=vertices,
                    ztst=1,
                )
            )
    for original in list(rows):
        if original["name"].startswith(
            ("near-boundary", "high-small-cross", "mixed-small-cross", "wide-varying")
        ):
            case = copy.deepcopy(original)
            case["name"] += "-gequal"
            case["ztst"] = 2
            rows.append(case)
    for name, depths in [
        ("trace-or-subset", [0x80000002, 0x80000000, 0x80000002]),
        ("trace-and-superset", [0x80000001, 0x80000003, 0x80000001]),
    ]:
        case = copy.deepcopy(rows[0])
        case["name"] = name
        case["ztst"] = 2
        for v, z in zip(case["vertices"], depths, strict=True):
            v["z"] = z
        rows.append(case)
    return rows


def packets(case):
    state = base_state()
    state["ztst"] = case["ztst"]
    return clear_packets() + [
        ad(registers32(state)),
        packed(case["vertices"], 3, xyz2=True),
        ad([(0, 0), (0x61, 0)]),
    ]


def reference(output, source_dir, memory_source_dir):
    for name, digest in READBACK_SOURCES.items():
        if (
            hashlib.sha256((memory_source_dir / name).read_bytes()).hexdigest()
            != digest
        ):
            raise ValueError("pinned high-Z readback source changed: " + name)
    for name, digest in SOURCES.items():
        if hashlib.sha256((source_dir / name).read_bytes()).hexdigest() != digest:
            raise ValueError("pinned high-Z GS source changed: " + name)
    output.mkdir(parents=True, exist_ok=False)
    rows = []
    for case in cases():
        dump = output / (case["name"] + ".gs")
        write_gs_dump(dump, packets(case))
        receipt = run_gs(dump, output / case["name"], save_depth=True)
        frames = list({v["file"].split("_")[1]: v for v in receipt["frames"]}.values())
        rows.append(
            dict(
                case=case,
                execution=receipt,
                frames=frames,
                depth_frames=export_depth32(output / case["name"]),
            )
        )
        print("PASS originalGS high-Z32", case["name"], flush=True)
    result = dict(
        commit="fd9d310ccbb6b8b62c976da8886a3c8fd3a10ff3",
        sources=SOURCES,
        depth_readback_sources=READBACK_SOURCES,
        records=rows,
        claim_limits=[
            "Selected original GS XYZ2 triangle contexts only; no whole vehicle or physical PS2 claim.",
            "ALWAYS uses float32 min/max equality; GEQUAL invokes original bitwise AND/OR raw-depth equality correction.",
            "Single-triangle draws; shared runtime accepts explicit whole-draw zEqual/zOverflow selectors for batch integration.",
            "CorrectDepthTrace bitwise subset/superset equality behavior is retained literally, not replaced with ideal raw equality.",
        ],
    )
    (output / "reference.json").write_text(json.dumps(result, indent=2) + "\n")
    return result


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--output", type=Path, required=True)
    p.add_argument("--source-dir", type=Path, required=True)
    p.add_argument("--memory-source-dir", type=Path, required=True)
    p.add_argument("--write-fixture", action="store_true")
    args = p.parse_args()
    result = reference(args.output, args.source_dir, args.memory_source_dir)
    if args.write_fixture:
        FIXTURE.write_text(json.dumps(result, indent=2) + "\n")
