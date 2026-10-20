"""Original MC3 texture bytes in explicit pinned software-GS sampler controls."""

import argparse
import copy
import hashlib
import json
from pathlib import Path

from mc3_reference_runtime import ad, run_gs, upload_rgba, write_gs_dump
from mc3_textures import native_shared_levels
from mc3_vehicle_fragment import base_state, registers, rectangle
from mc3_vehicle_gif import initial_registers, packed
from mc3_vehicle_raster import cases as raster_cases
from mc3_vehicle_texture import fragment_fixture, native_pck4_window

FIXTURE = (
    Path(__file__).resolve().parents[1]
    / "research/evidence/midnight-club-3-remix/previews/vehicle-sampler.json"
)
COMMIT = "fd9d310ccbb6b8b62c976da8886a3c8fd3a10ff3"
SOURCES = {
    "GSVertexTrace.cpp": "04f2b48d0b3d5fe6a012188f820352dbcce274b4cddbe852c4c0a2cae173ec6f",
    "GSState.cpp": "ceb0e05484e7ee3e2dc7130c794019f99a6bb04a8548116a08aa29f8916ed20e",
    "GSRendererSW.cpp": "0382633722f2cb1b042cfa2fb4919deb2cb754ecdbdd46356731e76ceec2bae3",
    # Retained concatenation of the pinned scanline generator architecture files.
    "GSDrawScanlineCodeGenerator.all.cpp": "90730bc23e6d03338aab47d13c08758e834aff153c6418f0e50b21151c20c481",
}


def verify_sources(files):
    for name, digest in SOURCES.items():
        if name not in files or hashlib.sha256(files[name]).hexdigest() != digest:
            raise ValueError("pinned sampler source changed: " + name)
    return dict(reference_commit=COMMIT, sources=SOURCES)


def images():
    source = fragment_fixture()
    window = source["window"]
    carrier = bytearray(window["source_bytes"])
    for row in window["fragments"]:
        raw = bytes.fromhex(row["hex"])
        if hashlib.sha256(raw).hexdigest() != row["sha256"]:
            raise ValueError("original window fragment changed")
        carrier[row["offset"] : row["offset"] + len(raw)] = raw
    decoded = native_pck4_window(bytes(carrier), window["slot"])
    carbon = source["shared_files"][0]
    raw = bytes.fromhex(carbon["hex"])
    if hashlib.sha256(raw).hexdigest() != carbon["sha256"]:
        raise ValueError("original carbon texture changed")
    output = {}
    for name, level, digest in [
        ("window", decoded["levels"][0], window["sha256"]),
        ("carbon", native_shared_levels(raw)["levels"][0], carbon["sha256"]),
    ]:
        output[name] = dict(
            width=level["width"],
            height=level["height"],
            data=list(level["rgba"]),
            source_sha256=digest,
            rgba_sha256=hashlib.sha256(level["rgba"]).hexdigest(),
        )
    return output


def controls():
    result = []
    source = images()
    for name, image, tex1, clamp in [
        ("window-native-repeat", "window", 0xFFFFFFC000000120, 0),
        ("window-native-clamp", "window", 0xFFFFFFC000000120, 5),
        ("carbon-mmin0", "carbon", 32, 0),
        ("carbon-mmin1", "carbon", 96, 0),
        ("carbon-mmin4", "carbon", 288, 0),
        ("carbon-mmin7", "carbon", 480, 0),
        (
            "carbon-region-clamp",
            "carbon",
            288,
            2 | 2 << 2 | 3 << 4 | 21 << 14 | 5 << 24 | 25 << 34,
        ),
        (
            "carbon-region-repeat",
            "carbon",
            288,
            3 | 3 << 2 | 7 << 4 | 16 << 14 | 15 << 24 | 32 << 34,
        ),
        ("carbon-mixed-clamp", "carbon", 288, 1),
    ]:
        vertices = copy.deepcopy(raster_cases()[1]["vertices"])
        for vertex, uv in zip(
            vertices, [[-0.25, 1.25], [2.2, -0.6], [0.6, 0.8]], strict=True
        ):
            vertex["stq"] = [*uv, 1]
            vertex["rgba"] = [128] * 4
        result.append(
            dict(
                name=name,
                image=image,
                tex1=f"0x{tex1:016x}",
                clamp=f"0x{clamp:016x}",
                vertices=vertices,
                texture=source[image],
            )
        )
    return result


def reference(output, source_dir):
    source_proof = verify_sources(
        {name: (source_dir / name).read_bytes() for name in SOURCES}
    )
    output.mkdir(parents=True, exist_ok=False)
    rows = []
    for case in controls():
        image = case["texture"]
        tex0 = (
            0x2000
            | 1 << 14
            | (image["width"].bit_length() - 1) << 26
            | (image["height"].bit_length() - 1) << 30
            | 1 << 34
        )
        initial = initial_registers()
        initial = [
            (address, tex0 if address == 6 else value) for address, value in initial
        ]
        initial += [(0x14, int(case["tex1"], 16)), (8, int(case["clamp"], 16))]
        source = base_state()
        source["ztst"] = 1
        packets = [
            ad(initial + registers(source, 4, True)),
            rectangle(0, 0, 256, 256, 0, [0] * 4),
            upload_rgba(bytes(image["data"]), image["width"], image["height"], 0x2000),
            ad(initial),
            packed(case["vertices"], 3 | 16),
            ad([(0, 0), (0x61, 0)]),
        ]
        dump = output / (case["name"] + ".gs")
        write_gs_dump(dump, packets)
        receipt = run_gs(dump, output / case["name"], save_depth=True)
        row = dict(case=case, execution=receipt)
        for field in ["frames", "depth_frames"]:
            frames = {v["file"].split("_")[1]: v for v in receipt[field]}
            if (
                len(frames) != 3
                or len({(v["sha256"], tuple(v["size"])) for v in frames.values()}) != 1
            ):
                raise ValueError("original sampler frames differ")
            row[field] = list(frames.values())
        rows.append(row)
        print(
            "PASS original",
            case["name"],
            "three RGBA/Z16 frames",
            row["frames"][0]["sha256"],
            flush=True,
        )
    return dict(
        schema=1,
        records=rows,
        **source_proof,
        claim_limits=[
            "MXL0 MMAG1 explicit RGBA views; not mip LOD, nearest or physical PS2."
        ],
    )


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--source-dir", type=Path, required=True)
    parser.add_argument("--write-fixture", action="store_true")
    args = parser.parse_args()
    result = reference(args.output, args.source_dir)
    encoded = json.dumps(result, separators=(",", ":")) + "\n"
    (args.output / "reference.json").write_text(encoded)
    if args.write_fixture:
        FIXTURE.write_text(encoded)


if __name__ == "__main__":
    main()
