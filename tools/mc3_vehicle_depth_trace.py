"""Original GS whole-draw depth trace controls for culling and ADC vertex history."""

import argparse
import json
import hashlib
from pathlib import Path

from mc3_reference_runtime import ad, run_gs, upload_rgba, write_gs_dump
from mc3_vehicle_depth32 import (
    READBACK_SOURCES,
    clear_packets,
    export_depth32,
    registers32,
)
from mc3_vehicle_depth32 import SOURCES as RASTER_SOURCES
from mc3_vehicle_fragment import base_state
from mc3_vehicle_gif import packed

SOURCES = {
    **RASTER_SOURCES,
    "GSState.cpp": "ceb0e05484e7ee3e2dc7130c794019f99a6bb04a8548116a08aa29f8916ed20e",
    "GSVertexTrace.cpp": "04f2b48d0b3d5fe6a012188f820352dbcce274b4cddbe852c4c0a2cae173ec6f",
    "GSVertexTraceFMM.cpp": "51f8ef8c4f55c8c3198f21f2c9a7ea52effece437789529d65beec6eb2b06b80",
}
FIXTURE = (
    Path(__file__).resolve().parents[1]
    / "research/evidence/midnight-club-3-remix/previews/vehicle-depth-trace.json"
)


def cases():
    def vertex(x, y, z, adc=False):
        return dict(
            xy=[x * 16, y * 16], z=z, adc=adc, stq=[0, 0, 1], rgba=[17, 39, 113, 128]
        )

    a, b, c = [
        vertex(x, y, z)
        for x, y, z in [(2, 3, 0x80000002), (85, 6, 0x80000000), (8, 71, 0x80000002)]
    ]
    body = [a, b, c]
    culled = [vertex(x, y, 1) for x, y in [(300, 300), (340, 300), (300, 340)]]
    rows = [
        dict(name="list-culled-prefix", vertices=culled + body, primitive=3),
        dict(name="list-culled-suffix", vertices=body + culled, primitive=3),
        dict(
            name="list-degenerate-prefix",
            vertices=[vertex(2, 3, 1)] * 3 + body,
            primitive=3,
        ),
        dict(
            name="list-shared-overflow",
            vertices=[
                vertex(x, y, z)
                for x, y, z in [
                    (2, 3, 100),
                    (85, 6, 1000),
                    (8, 71, 1500),
                    (100, 3, 0xFFFFFFF0),
                    (183, 6, 0xFFFFFFFF),
                    (106, 71, 0xFFFFFFE0),
                ]
            ],
            primitive=3,
        ),
    ]
    prefix = [vertex(90, 90, 1), a, dict(b, adc=True), c]
    rows += [
        dict(name="strip-adc-prefix", vertices=prefix, primitive=4),
        dict(
            name="fan-adc-prefix-retained",
            vertices=[a, vertex(90, 90, 1), dict(b, adc=True), c],
            primitive=5,
        ),
        dict(
            name="strip-adc-suffix-trimmed",
            vertices=body + [vertex(90, 90, 1, True)],
            primitive=4,
        ),
        dict(
            name="strip-adc-suffix-finish",
            vertices=body + [vertex(90, 90, 1, True)],
            primitive=4,
            finish_only=True,
        ),
    ]
    rows += [
        dict(
            name="strip-adc-middle-compacted",
            primitive=4,
            vertices=body
            + [
                vertex(90, 90, 1, True),
                vertex(100, 3, 0x80000002, True),
                vertex(183, 6, 0x80000000, True),
                vertex(106, 71, 0x80000002),
            ],
        ),
        dict(
            name="strip-test-change-before-adc",
            primitive=4,
            split_test=True,
            vertices=body + [vertex(90, 90, 1, True), vertex(120, 80, 0x80000002)],
        ),
    ]
    image = dict(
        width=8,
        height=8,
        data=[
            (x * 37 + y * 19 + ch * 53) & 255
            for y in range(8)
            for x in range(8)
            for ch in range(4)
        ],
    )
    for name, ztst in [
        ("textured-float-equal-always", 1),
        ("textured-bitwise-equal-gequal", 2),
        ("textured-corrected-unequal-gequal", 2),
    ]:
        vertices = [
            dict(v, stq=stq)
            for v, stq in zip(
                body,
                [
                    [123.412345, -234.523456, 0.7],
                    [178.2678, -31.1234, 1.1],
                    [27.127, 0.837, 0.15],
                ],
                strict=True,
            )
        ]
        if "unequal" in name:
            vertices[1]["z"] = 0x80000003
        rows.append(
            dict(name=name, primitive=3, vertices=vertices, image=image, ztst=ztst)
        )
    for row in rows:
        row.setdefault("ztst", 2)
    return rows


def draw_packets(case, upload=True):
    state = base_state()
    state["ztst"] = case["ztst"]
    geometry = [
        packed(
            case["vertices"],
            case["primitive"] | (16 if "image" in case else 0),
            xyz2=True,
        )
    ]
    if case.get("split_test"):
        changed = dict(state, ztst=1)
        geometry = [
            packed(case["vertices"][:3], case["primitive"], xyz2=True),
            ad(registers32(changed)),
            packed(case["vertices"][3:], xyz2=True),
        ]
    prefix = []
    if "image" in case:
        image = case["image"]
        if upload:
            prefix.append(
                upload_rgba(bytes(image["data"]), image["width"], image["height"])
            )
        prefix.append(
            ad(
                [
                    (6, 0x2000 | 1 << 14 | 3 << 26 | 3 << 30 | 1 << 34),
                    (8, 0),
                    (0x14, 96),
                    (0x3B, 0),
                ]
            )
        )
    return [
        ad(registers32(state, 0 if "image" in case else 4)),
        *prefix,
        *geometry,
        ad([(0x61, 0)] if case.get("finish_only") else [(0, 0), (0x61, 0)]),
    ]


def packets(case):
    return clear_packets() + draw_packets(case)


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
        print("PASS originalGS depth-trace", case["name"], flush=True)
    result = dict(
        commit="fd9d310ccbb6b8b62c976da8886a3c8fd3a10ff3",
        sources=SOURCES,
        depth_readback_sources=READBACK_SOURCES,
        records=rows,
        claim_limits=[
            "Selected original GS XYZ2 triangle contexts only; no whole vehicle or physical PS2 claim.",
            "ALWAYS uses float32 min/max equality; GEQUAL invokes original bitwise AND/OR raw-depth equality correction.",
            "Multi-triangle and ADC/culling controls isolate native source-buffer and indexed minmax differences; no bound vehicle claim.",
            "CorrectDepthTrace bitwise subset/superset equality behavior is retained literally, not replaced with ideal raw equality.",
        ],
    )
    (output / "reference.json").write_text(json.dumps(result, indent=2) + "\n")
    return result


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--output", type=Path)
    p.add_argument("--source-dir", type=Path)
    p.add_argument("--memory-source-dir", type=Path)
    p.add_argument("--write-fixture", action="store_true")
    p.add_argument("--emit-controls", action="store_true")
    args = p.parse_args()
    if args.emit_controls:
        print(
            json.dumps(
                [
                    dict(
                        name=c["name"],
                        chunks_hex=[
                            v.hex()
                            for v in [
                                clear_packets()[0],
                                *draw_packets(c, upload=False),
                            ]
                        ],
                    )
                    for c in cases()
                ]
            )
        )
    else:
        if not all([args.output, args.source_dir, args.memory_source_dir]):
            p.error(
                "original reference output and both pinned source directories are required"
            )
        result = reference(args.output, args.source_dir, args.memory_source_dir)
        if args.write_fixture:
            FIXTURE.write_text(json.dumps(result, indent=2) + "\n")
