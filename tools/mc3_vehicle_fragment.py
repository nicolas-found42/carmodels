"""Explicit-state fragment probes for the pinned official software GS.

This constructs native GIF inputs only. Expected pixels never enter the dump.
The carrier tests PSMCT32/PSMZ16S, without fog, AA or dithering.
"""

import argparse
import hashlib
import json
from pathlib import Path

from mc3_reference_runtime import ad, run_gs, upload_rgba, write_gs_dump
from verify_mc3_raster_reference import rgbaq

COMMIT = "fd9d310ccbb6b8b62c976da8886a3c8fd3a10ff3"
FIXTURE = (
    Path(__file__).resolve().parents[1]
    / "research/evidence/midnight-club-3-remix/previews/vehicle-fragment.json"
)
SOURCES = [
    dict(
        path="pcsx2/GS/Renderers/SW/GSDrawScanlineCodeGenerator.all.cpp",
        sha256="90730bc23e6d03338aab47d13c08758e834aff153c6418f0e50b21151c20c481",
    ),
    dict(
        path="pcsx2/GS/Renderers/SW/GSRendererSW.cpp",
        sha256="0382633722f2cb1b042cfa2fb4919deb2cb754ecdbdd46356731e76ceec2bae3",
    ),
    dict(
        path="pcsx2/GS/GSRegs.h",
        sha256="96fe06845d942b91229f10e2b3297036ff2571fd7c2319ba52a7a06e64c425d1",
    ),
    dict(
        path="pcsx2/GS/GSVector4i.h",
        sha256="f469fab789fd335e9544149eccd00bb20ab4e39566d1ca1df573fa2cdf049992",
    ),
]


def compact_reference(value, artifact):
    """Retain actual runtime output identities without duplicating every draw."""
    result = {key: val for key, val in value.items() if key != "runtime"}
    result["runtime"] = {
        key: val for key, val in value["runtime"].items() if key != "frames"
    }
    result["runtime"]["selected_output"] = value["final_frames"][-1]
    result["reference_artifact_sha256"] = hashlib.sha256(artifact).hexdigest()
    result["sources"] = SOURCES
    return result


def verify_sources(files):
    """Validate original pinned source bytes before using a new source export."""
    for source in SOURCES:
        raw = files[source["path"]]
        if hashlib.sha256(raw).hexdigest() != source["sha256"]:
            raise ValueError(f"official fragment source differs: {source['path']}")
    return dict(reference_commit=COMMIT, sources=SOURCES)


def verify_reference(actual, expected):
    for field in [
        "reference_commit",
        "cases",
        "rgba_sha256",
        "case_rgba",
        "case_depth_probe_rgba",
    ]:
        if actual[field] != expected[field]:
            raise ValueError(f"official fragment reference differs: {field}")
    return dict(
        status="pass", cases=len(actual["cases"]), rgba_sha256=actual["rgba_sha256"]
    )


def base_state():
    return dict(
        framebuffer="PSMCT32",
        depthFormat="PSMZ16S",
        fbmask=0,
        ate=False,
        atst=1,
        aref=128,
        afail=0,
        date=False,
        datm=0,
        zte=True,
        ztst=2,
        zmsk=False,
        abe=False,
        pabe=False,
        fba=False,
        colclamp=True,
        aa1=False,
        fge=False,
        dthe=False,
        blend=[0, 1, 0, 1, 128],
    )


def fragment_cases():
    result = []

    def add(name, **changes):
        state = base_state()
        inputs = dict(
            vertex=[193, 79, 231, 113],
            texture=[187, 219, 73, 151],
            tfx=4,
            tcc=True,
            destination=[93, 143, 213, 155],
            z=2000,
            destinationZ=1000,
        )
        for key, value in changes.items():
            if key in state:
                state[key] = value
            else:
                inputs[key] = value
        result.append(dict(name=name, state=state, **inputs))

    for test in range(8):
        for fail in range(4):
            add(f"alpha-test-{test}-fail-{fail}", ate=True, atst=test, afail=fail)
    for tfx in range(4):
        for tcc in (False, True):
            add(f"tfx-{tfx}-tcc-{int(tcc)}", tfx=tfx, tcc=tcc)
    add("glass-blend", abe=True)
    add("reflection-Ad-add", abe=True, blend=[0, 2, 1, 1, 0], vertex=[127, 127, 127, 0])
    add("negative-subtract", abe=True, blend=[1, 0, 0, 2, 0])
    add("fixed-factor", abe=True, blend=[0, 1, 2, 1, 211])
    add("overflow-wrap", abe=True, blend=[0, 2, 2, 0, 255], colclamp=False)
    add("overflow-clamp", abe=True, blend=[0, 2, 2, 0, 255])
    add("pabe-low", abe=True, pabe=True)
    add("pabe-high", abe=True, pabe=True, vertex=[193, 79, 231, 197])
    add("fba", fba=True)
    add("partial-bit-mask", fbmask=0x55AA1234, fba=True)
    add("date-reject", date=True, datm=0)
    add("date-pass", date=True, datm=1)
    add("depth-never", ztst=0)
    add("depth-always", ztst=1, z=500)
    add("depth-gequal-equal", z=1000)
    add("depth-greater-equal", ztst=3, z=1000)
    add("depth-clamp", z=65536)
    add("depth-mask", zmsk=True)
    add("depth-disabled", zte=False)
    add("rgb-only-plus-fba", ate=True, atst=0, afail=3, fba=True)
    add("alpha-equal", ate=True, atst=4, aref=113)
    add("alpha-notequal", ate=True, atst=7, aref=113)
    add("tfx-alpha-fail", tfx=0, ate=True, atst=6, aref=150, afail=3, abe=True)
    add("all-frame-masked", fbmask=0xFFFFFFFF)
    return result


def rectangle(x, y, w, h, z, color, textured=False):
    values = [(0x01, rgbaq(*color))]
    if textured:
        values.append(
            (0x03, 0)
        )  # FST UV zero: constant texel, independent of interpolation.
    values += [
        (0x05, x * 16 | (y * 16) << 16 | z << 32),
        (0x05, (x + w) * 16 | ((y + h) * 16) << 16 | z << 32),
    ]
    return ad(values)


def registers(state, tfx, tcc):
    blend = state["blend"]
    alpha = blend[0] | blend[1] << 2 | blend[2] << 4 | blend[3] << 6 | blend[4] << 32
    test = (
        int(state["ate"])
        | state["atst"] << 1
        | state["aref"] << 4
        | state["afail"] << 12
        | int(state["date"]) << 14
        | state["datm"] << 15
        | int(state["zte"]) << 16
        | state["ztst"] << 17
    )
    tex0 = 0x2000 | 1 << 14 | 2 << 26 | 2 << 30 | int(tcc) << 34 | min(tfx, 3) << 35
    prim = 6 | int(tfx != 4) << 4 | int(state["abe"]) << 6 | 1 << 8
    return [
        (0x00, prim),
        (0x47, test),
        (0x42, alpha),
        (0x06, tex0),
        (0x4C, 4 << 16 | state["fbmask"] << 32),
        (0x4E, 128 | 10 << 24 | int(state["zmsk"]) << 32),
        (0x49, int(state["pabe"])),
        (0x4A, int(state["fba"])),
        (0x46, int(state["colclamp"])),
    ]


def packets(cases):
    result = [
        ad(
            [
                (0x18, 0),
                (0x40, 255 << 16 | 255 << 48),
                (0x45, 0),
                (0x1A, 1),
                (0x08, 5),
                (0x14, 0),
                (0x3B, 0),
            ]
        )
    ]
    # Clear every framebuffer/depth pixel before the explicit per-case draws.
    clear = base_state()
    clear["ztst"] = 1
    result += [
        ad(registers(clear, 4, True)),
        rectangle(0, 0, 256, 256, 0, [0, 0, 0, 0]),
    ]
    for index, case in enumerate(cases):
        x, y = index % 16 * 16, index // 16 * 16
        result += [
            ad(registers(clear, 4, True)),
            rectangle(x, y, 16, 16, case["destinationZ"], case["destination"]),
            upload_rgba(bytes(case["texture"]) * 16, 4, 4),
            ad([(0x3F, 0)]),
            ad(registers(case["state"], case["tfx"], case["tcc"])),
            rectangle(x, y, 16, 16, case["z"], case["vertex"], case["tfx"] != 4),
        ]
        # Independent depth observation: GEQUAL1500 passes exactly when the
        # source did not store2000 (or clamped65535). No expected pixels supplied.
        result += [
            ad(registers(base_state(), 4, True)),
            rectangle(x, y + 8, 16, 8, 1500, [11, 239, 37, 91]),
        ]
    result.append(ad([(0x00, 0), (0x61, 0)]))
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--write-fixture", action="store_true")
    parser.add_argument("--verify-fixture", action="store_true")
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)
    cases = fragment_cases()
    dump = args.output / "fragment.gs"
    write_gs_dump(dump, packets(cases))
    receipt = run_gs(dump, args.output / "runtime")
    value = dict(
        schema=1,
        reference_commit=COMMIT,
        cases=cases,
        runtime=receipt,
        claim_limits=[
            "Selected explicit software-GS fragment probes; not whole vehicle frames or physical PS2."
        ],
    )
    frames = receipt["frames"]
    if not frames:
        raise ValueError("native fragment reference did not produce framebuffer output")
    raw = (args.output / "runtime" / frames[-1]["file"]).read_bytes()
    final_frames = {}
    for row in frames:
        final_frames[row["file"].split("_")[1]] = row
    if len(final_frames) != 3 or any(
        (args.output / "runtime" / row["file"]).read_bytes() != raw
        for row in final_frames.values()
    ):
        raise ValueError("three official reference frames differ")
    value["final_frames"] = list(final_frames.values())
    value["rgba_sha256"] = hashlib.sha256(raw).hexdigest()
    value["case_rgba"] = [
        list(raw[((i // 16 * 16) * 256 + i % 16 * 16) * 4 :][:4])
        for i in range(len(cases))
    ]
    value["case_depth_probe_rgba"] = [
        list(raw[(((i // 16 * 16) + 8) * 256 + i % 16 * 16) * 4 :][:4])
        for i in range(len(cases))
    ]
    artifact = (json.dumps(value, indent=2) + "\n").encode()
    (args.output / "reference.json").write_bytes(artifact)
    if args.write_fixture:
        FIXTURE.write_text(
            json.dumps(compact_reference(value, artifact), separators=(",", ":")) + "\n"
        )
    if args.verify_fixture:
        verify_reference(value, json.loads(FIXTURE.read_text()))
    print(json.dumps(dict(cases=len(cases), sha256=value["rgba_sha256"])))


if __name__ == "__main__":
    main()
