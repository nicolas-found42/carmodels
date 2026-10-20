"""Explicit original software-GS PSMZ32 fragments and fixed-UV sprites."""

import argparse
import copy
import hashlib
import json
from pathlib import Path

from mc3_reference_runtime import (
    DEFAULT_IMAGE,
    ad,
    command,
    run_gs,
    upload_rgba,
    write_gs_dump,
)
from mc3_vehicle_fragment import base_state, fragment_cases, registers, rectangle
from mc3_vehicle_sprite import cases as sprite_cases, SOURCES as SPRITE_SOURCES
from verify_mc3_raster_reference import rgbaq

SOURCES = {
    **SPRITE_SOURCES,
    "GSDrawScanlineCodeGenerator.all.cpp": "90730bc23e6d03338aab47d13c08758e834aff153c6418f0e50b21151c20c481",
}
READBACK_SOURCES = {
    "GSLocalMemory.cpp": "46da01086c93f3839c0c20787433f8cd0b7b89790d42f12414f9589c66fd4e51",
    "GSLocalMemory.h": "8cd6ed874f53aafde5f3d294048b2b0beed87765ab099a5f8aa93899cb988a19",
}
FIXTURE = (
    Path(__file__).resolve().parents[1]
    / "research/evidence/midnight-club-3-remix/previews/vehicle-depth32.json"
)


def state32(state):
    return {**state, "depthFormat": "PSMZ32"}


def registers32(state, tfx=4, tcc=True):
    return [
        (r, (v & ~(15 << 24)) if r == 0x4E else v)
        for r, v in registers(state, tfx, tcc)
    ]


def cases():
    result = []
    for index, original in enumerate(fragment_cases()):
        case = copy.deepcopy(original)
        case["state"] = state32(case["state"])
        case.update(z=0xFEDCBA98, destinationZ=0x81234567)
        result.append(case)
    for test in range(4):
        for name, z, destination in [
            ("low-high", 0x7FFFFFFF, 0x80000000),
            ("high-low", 0x80000000, 0x7FFFFFFF),
            ("equal-max", 0xFFFFFFFF, 0xFFFFFFFF),
        ]:
            case = copy.deepcopy(result[0])
            case["state"] = state32(base_state())
            case.update(name=f"z32-{test}-{name}", z=z, destinationZ=destination)
            case["state"]["ztst"] = test
            result.append(case)
    for fail in range(4):
        case = copy.deepcopy(result[0])
        case.update(
            name=f"z32-max-alpha-fail-{fail}", z=0xFFFFFFFF, destinationZ=0xFFFFFFFE
        )
        case["state"].update(atst=0, afail=fail)
        result.append(case)
    return result


def clear_packets():
    clear = base_state()
    clear["ztst"] = 1
    # RunGS's existing completion observer expects16S; this all-zero clear is
    # semantically neutral in initially zero GS VRAM, before the explicit32clear.
    return [
        ad(
            [
                (0x18, 0),
                (0x40, 255 << 16 | 255 << 48),
                (0x45, 0),
                (0x1A, 1),
                (8, 0),
                (0x14, 0),
                (0x3B, 0),
            ]
        ),
        ad(registers(clear, 4, True)),
        rectangle(0, 0, 256, 256, 0, [0] * 4),
        ad(registers32(clear)),
        rectangle(0, 0, 256, 256, 0, [0] * 4),
    ]


def fragment_packets(inputs):
    clear = state32(base_state())
    clear["ztst"] = 1
    result = clear_packets()
    for index, case in enumerate(inputs):
        x, y = index % 16 * 16, index // 16 * 16
        result += [
            ad(registers32(clear)),
            rectangle(x, y, 16, 16, case["destinationZ"], case["destination"]),
            upload_rgba(bytes(case["texture"]) * 16, 4, 4),
            ad([(0x3F, 0)]),
            ad(registers32(case["state"], case["tfx"], case["tcc"])),
            rectangle(x, y, 16, 16, case["z"], case["vertex"], case["tfx"] != 4),
        ]
    return result + [ad([(0, 0), (0x61, 0)])]


def sprites():
    result = []
    for index, name in enumerate(
        ["nearest", "nearest-reverse", "bilinear-max", "masked-depth"]
    ):
        case = copy.deepcopy(sprite_cases()[1])
        case["name"] = name
        case["state"] = state32(case["state"])
        case["depthBits"] = 32
        case["bilinear"] = name == "bilinear-max"
        case["vertices"][1]["z"] = 0xFFFFFFFF if case["bilinear"] else 0xFEDCBA98
        if name == "nearest-reverse":
            for axis in [0, 1]:
                case["vertices"][0]["xy"][axis], case["vertices"][1]["xy"][axis] = (
                    case["vertices"][1]["xy"][axis],
                    case["vertices"][0]["xy"][axis],
                )
        if name == "masked-depth":
            case["state"]["zmsk"] = True
        result.append(case)
    return result


def sprite_packets(case):
    clear = state32(base_state())
    clear["ztst"] = 1
    result = clear_packets() + [
        ad(registers32(clear)),
        rectangle(0, 0, 256, 256, 0, case["background"]),
        upload_rgba(bytes(case["texture"]["data"]), 8, 8),
        ad([(0x3F, 0)]),
    ]
    values = [(r, v) for r, v in registers32(case["state"], 0) if r != 0]
    values += [
        (6, 0x2000 | 1 << 14 | 3 << 26 | 3 << 30 | 1 << 34),
        (0x14, 288 if case["bilinear"] else 0),
        (8, 0),
        (0, 6 | 16 | 256),
    ]
    result.append(ad(values))
    for vertex in case["vertices"]:
        result.append(
            ad(
                [
                    (1, rgbaq(*vertex["rgba"])),
                    (3, vertex["uv"][0] | vertex["uv"][1] << 16),
                    (5, vertex["xy"][0] | vertex["xy"][1] << 16 | vertex["z"] << 32),
                ]
            )
        )
    return result + [ad([(0, 0), (0x61, 0)])]


def export_depth32(output):
    """SaveBMP/ReadPixel32Z stores low24bits in RGB and highbyte in alpha PNG."""
    script = (
        "from pathlib import Path;from PIL import Image;import json;out=[]\n"
        'for p in sorted(Path("/data/draws").glob("*_rz1_*_Z_32.png")):\n'
        ' im=Image.open(p).convert("RGB");rgb=im.tobytes();'
        'a=Image.open(p.with_name(p.stem+"_alpha.png")).convert("L").tobytes();'
        "raw=bytes(v for i in range(len(a)) for v in (*rgb[i*3:i*3+3],a[i]));"
        'f=Path("/data")/(p.stem+".z32");f.write_bytes(raw);'
        'out.append({"file":f.name,"size":im.size})\nprint(json.dumps(out))'
    )
    frames = json.loads(
        command(
            [
                "docker",
                "run",
                "--rm",
                "--network=none",
                "--platform",
                "linux/amd64",
                "--entrypoint",
                "python3",
                "-v",
                f"{output.resolve()}:/data",
                DEFAULT_IMAGE,
                "-c",
                script,
            ]
        )
    )
    final = list({v["file"].split("_")[1]: v for v in frames}.values())
    if (
        len(final) != 3
        or len(
            {
                (
                    hashlib.sha256((output / v["file"]).read_bytes()).hexdigest(),
                    tuple(v["size"]),
                )
                for v in final
            }
        )
        != 1
    ):
        raise ValueError("original Z32 frames differ or incomplete")
    for frame in final:
        raw = (output / frame["file"]).read_bytes()
        frame.update(bytes=len(raw), sha256=hashlib.sha256(raw).hexdigest())
    return final


def reference(output, source_dir, memory_source_dir):
    for name, digest in READBACK_SOURCES.items():
        if (
            hashlib.sha256((memory_source_dir / name).read_bytes()).hexdigest()
            != digest
        ):
            raise ValueError("pinned Z32 readback source changed")
    for name, digest in SOURCES.items():
        if hashlib.sha256((source_dir / name).read_bytes()).hexdigest() != digest:
            raise ValueError("pinned Z32 sampler/depth source changed")
    output.mkdir(parents=True, exist_ok=False)
    records = []
    for name, inputs, packets in [("fragments", cases(), fragment_packets(cases()))] + [
        (c["name"], c, sprite_packets(c)) for c in sprites()
    ]:
        dump = output / (name + ".gs")
        write_gs_dump(dump, packets)
        receipt = run_gs(dump, output / name, save_depth=True)
        frames = list({v["file"].split("_")[1]: v for v in receipt["frames"]}.values())
        if (
            len(frames) != 3
            or len({(v["sha256"], tuple(v["size"])) for v in frames}) != 1
        ):
            raise ValueError("original Z32 color frames differ")
        records.append(
            dict(
                name=name,
                inputs=inputs,
                execution=receipt,
                frames=frames,
                depth_frames=export_depth32(output / name),
            )
        )
        print("PASS original Z32", name, flush=True)
    return dict(
        schema=1,
        records=records,
        sources=SOURCES,
        depth_readback_sources=READBACK_SOURCES,
        claim_limits=[
            "Explicit selected officialGS PSMCT32/PSMZ32 sprite/fragment contexts, not unproven triangle Z-overflow or whole native vehicle frames."
        ],
    )


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--output", type=Path, required=True)
    p.add_argument("--source-dir", type=Path, required=True)
    p.add_argument("--memory-source-dir", type=Path, required=True)
    p.add_argument("--write-fixture", action="store_true")
    args = p.parse_args()
    result = reference(args.output, args.source_dir, args.memory_source_dir)
    encoded = json.dumps(result, separators=(",", ":")) + "\n"
    (args.output / "reference.json").write_text(encoded)
    if args.write_fixture:
        FIXTURE.write_text(encoded)


if __name__ == "__main__":
    main()
