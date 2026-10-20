"""Independent explicit triangle GIF probes for the pinned software GS."""

import argparse
import copy
import hashlib
import json
from pathlib import Path
import struct

from mc3_reference_runtime import ad, run_gs, upload_rgba, write_gs_dump
from mc3_vehicle_fragment import base_state, registers, rectangle
from verify_mc3_raster_reference import rgbaq, st

FIXTURE = (
    Path(__file__).resolve().parents[1]
    / "research/evidence/midnight-club-3-remix/previews/vehicle-raster.json"
)


def cases():
    vertices = [
        dict(xy=[197, 275], z=900, stq=[0.09375, 0.15625, 1.0], rgba=[17, 241, 73, 33]),
        dict(
            xy=[3709, 709],
            z=31000,
            stq=[0.90625, 0.21875, 1.0],
            rgba=[229, 41, 189, 213],
        ),
        dict(
            xy=[1170, 3870],
            z=55000,
            stq=[0.28125, 0.96875, 1.0],
            rgba=[89, 167, 11, 127],
        ),
    ]
    texture = [
        v
        for y in range(8)
        for x in range(8)
        for v in [
            (x * 29 + y * 13 + 17) % 256,
            (x * 11 + y * 31 + 29) % 256,
            (x * 23 + y * 19 + 7) % 256,
            80 + (x + y) * 9,
        ]
    ]
    result = []
    for name, gouraud, textured, projective, reverse in [
        ("flat", False, False, False, False),
        ("gouraud", True, False, False, False),
        ("gouraud-textured", True, True, False, False),
        ("gouraud-projective-reverse", True, True, True, True),
        ("gouraud-scissor", True, False, False, False),
    ]:
        vs = copy.deepcopy(vertices)
        if not gouraud:
            vs = [vs[2], vs[0], vs[1]]  # Provoking vertex is not last in Y-sort.
        if projective:
            for v, q in zip(vs, [0.5, 1.75, 0.875]):
                v["stq"] = [v["stq"][0] * q, v["stq"][1] * q, q]
        if reverse:
            vs[0], vs[1] = vs[1], vs[0]
        result.append(
            dict(
                name=name,
                gouraud=gouraud,
                textured=textured,
                vertices=vs,
                texture=dict(width=8, height=8, data=texture),
                xyOffset=[0, 0],
                scissor=[31, 29, 201, 219]
                if name.endswith("scissor")
                else [0, 0, 256, 256],
            )
        )
    return result


def packets(case, depth_probe=False):
    state = base_state()
    state["ztst"] = 1
    result = [
        ad(
            [
                (0x18, 0),
                (0x40, 255 << 16 | 255 << 48),
                (0x45, 0),
                (0x1A, 1),
                (0x08, 0),
                (0x14, 96),
                (0x3B, 0),
            ]
        ),
        ad(registers(state, 4, True)),
        rectangle(0, 0, 256, 256, 0, [0, 0, 0, 0]),
        upload_rgba(bytes(case["texture"]["data"]), 8, 8),
        ad([(0x3F, 0)]),
    ]
    state["ztst"] = 2
    draw = registers(state, 0 if case["textured"] else 4, True)
    draw = [(r, v) for r, v in draw if r not in (0x00, 0x06)]
    draw += [
        (0x06, 0x2000 | 1 << 14 | 3 << 26 | 3 << 30 | 1 << 34),
        (
            0x40,
            case["scissor"][0]
            | (case["scissor"][2] - 1) << 16
            | case["scissor"][1] << 32
            | (case["scissor"][3] - 1) << 48,
        ),
        (0x00, 3 | int(case["gouraud"]) << 3 | int(case["textured"]) << 4),
    ]
    result.append(ad(draw))
    # Literal GS AD transport: independently constructed native inputs only.
    for vertex in case["vertices"]:
        z = vertex["z"]
        result.append(
            ad(
                [
                    (0x02, st(*vertex["stq"][:2])),
                    (
                        0x01,
                        (rgbaq(*vertex["rgba"]) & 0xFFFFFFFF)
                        | struct.unpack("<I", struct.pack("<f", vertex["stq"][2]))[0]
                        << 32,
                    ),
                    (0x05, vertex["xy"][0] | vertex["xy"][1] << 16 | z << 32),
                ]
            )
        )
    if depth_probe:
        result += [
            ad([(0x40, 255 << 16 | 255 << 48)] + registers(state, 4, True)),
            rectangle(0, 0, 256, 256, 24000, [31, 227, 59, 173]),
        ]
    result.append(ad([(0x00, 0), (0x61, 0)]))
    return result


def reference(output):
    records = []
    for case in cases():
        for mode in ["color", "depth"]:
            name = case["name"] + "-" + mode
            dump = output / (name + ".gs")
            write_gs_dump(dump, packets(case, mode == "depth"))
            receipt = run_gs(dump, output / name, save_depth=True)
            final = {}
            for row in receipt["frames"]:
                final[row["file"].split("_")[1]] = row
            rows = list(final.values())
            if (
                len(rows) != 3
                or len({(row["sha256"], tuple(row["size"])) for row in rows}) != 1
            ):
                raise ValueError("official triangle reference frames differ")
            raw = (output / name / rows[-1]["file"]).read_bytes()
            if hashlib.sha256(raw).hexdigest() != rows[-1]["sha256"]:
                raise ValueError("official triangle raw output identity differs")
            depth_final = {}
            for row in receipt["depth_frames"]:
                depth_final[row["file"].split("_")[1]] = row
            depths = list(depth_final.values())
            if (
                len(depths) != 3
                or len({(row["sha256"], tuple(row["size"])) for row in depths}) != 1
            ):
                raise ValueError("official triangle depth frames differ")
            records.append(
                dict(
                    name=name,
                    case=case,
                    mode=mode,
                    frames=rows,
                    depth_frames=depths,
                    runtime=receipt["runtime"],
                    dump_sha256=receipt["dump_sha256"],
                )
            )
            print(
                name,
                "frames=" + str(len(rows)),
                "bytes=" + str(len(raw)),
                rows[-1]["sha256"],
                "z16=" + depths[-1]["sha256"],
                flush=True,
            )
    return dict(
        schema=1,
        records=records,
        depth_export=dict(
            reference_commit="fd9d310ccbb6b8b62c976da8886a3c8fd3a10ff3",
            encoding="raw-u16-little-endian",
            source="GSLocalMemory::SaveBMP / ReadPixel16SZ / ReadPixel16",
            source_sha256={
                "GSLocalMemory.cpp": "46da01086c93f3839c0c20787433f8cd0b7b89790d42f12414f9589c66fd4e51",
                "GSLocalMemory.h": "8cd6ed874f53aafde5f3d294048b2b0beed87765ab099a5f8aa93899cb988a19",
            },
        ),
        claim_limits=[
            "Explicit selected official software-GS triangle contexts, not physical PS2 or whole vehicle frames."
        ],
    )


def verify_reference(actual, expected):
    if len(actual["records"]) != len(expected["records"]):
        raise ValueError("official triangle record count differs")
    for row, saved in zip(actual["records"], expected["records"]):
        for field in ["name", "case", "mode", "dump_sha256"]:
            if row[field] != saved[field]:
                raise ValueError(f"official triangle reference differs: {field}")
        if [(r["sha256"], r["size"]) for r in row["frames"]] != [
            (r["sha256"], r["size"]) for r in saved["frames"]
        ]:
            raise ValueError("official triangle framebuffer bytes differ")
        if [(r["sha256"], r["size"]) for r in row["depth_frames"]] != [
            (r["sha256"], r["size"]) for r in saved["depth_frames"]
        ]:
            raise ValueError("official triangle depth bytes differ")
    return dict(status="pass", contexts=len(actual["records"]))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--write-fixture", action="store_true")
    mode.add_argument("--verify-fixture", action="store_true")
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)
    value = reference(args.output)
    encoded = json.dumps(value, separators=(",", ":")) + "\n"
    (args.output / "reference.json").write_text(encoded)
    if args.write_fixture:
        FIXTURE.write_text(encoded)
    if args.verify_fixture:
        verify_reference(value, json.loads(FIXTURE.read_text()))


if __name__ == "__main__":
    main()
