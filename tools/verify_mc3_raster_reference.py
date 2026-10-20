"""Compare the shared MC3 capture with the pinned official software GS replay.

The reference receives original emitted GIF bytes and original texture bytes,
never pixels predicted by the browser reconstruction. Physical PS2 equivalence
and a complete booted-game frame are outside this reference contract.
"""

import argparse
import base64
import json
from pathlib import Path
import shutil
import struct
import subprocess
import sys
import tempfile

from mc3_archive import CookedDisc, DaveArchive, file_digest
from mc3_environment import (
    ISO_SHA,
    NATIVE_CAPTURE,
    OUTPUT,
    encode,
    from_archive,
    normalize_capture_fixture,
)
from mc3_environment_raster import regenerate
from mc3_reference_runtime import (
    RuntimeUnavailable,
    ad,
    identity,
    run_gs,
    upload_rgba,
    write_gs_dump,
)
import verifier_common as common
from static_inputs import mc3_disc

ROOT = Path(__file__).resolve().parents[1]
RECEIPT = (
    ROOT
    / "research/evidence/midnight-club-3-remix/previews/environment/raster-reference.json"
)


def need(condition, message):
    if not condition:
        raise ValueError(message)


def texture_bytes(image):
    raw = base64.b64decode(image["rgba_base64"], validate=True)
    need(
        len(raw) == image["width"] * image["height"] * 4,
        "invalid native reference texture length",
    )
    return raw


def rgbaq(red, green, blue, alpha):
    return red | green << 8 | blue << 16 | alpha << 24 | 0x3F800000 << 32


def st(s, t):
    return struct.unpack("<Q", struct.pack("<ff", s, t))[0]


def xyz(x, y, xy_offset):
    return (x * 16 + xy_offset[0]) | (y * 16 + xy_offset[1]) << 16


def sprite(width, height, xy_offset, *, uv=None, color=(0, 0, 0, 0)):
    values = [(0x01, rgbaq(*color))]
    if uv:
        values.append((0x02, st(*uv[0])))
    values.append((0x05, xyz(0, 0, xy_offset)))
    if uv:
        values.append((0x02, st(*uv[1])))
    values.append((0x05, xyz(width, height, xy_offset)))
    return ad(values)


def tex0(base, width, height):
    need(
        width > 0
        and height > 0
        and width & (width - 1) == 0
        and height & (height - 1) == 0,
        "reference texture must have power-of-two dimensions",
    )
    return (
        base
        | ((width + 63) // 64) << 14
        | (width.bit_length() - 1) << 26
        | (height.bit_length() - 1) << 30
        | 1 << 34
    )


def capture_packets(pack, *, panorama_offset16=None, copy_specular=False):
    """Build native floor/prefill/panorama/copy packets for independent GS replay.

    Other source surfaces require a separate native visibility proof before
    this bounded floor stream can establish the fixed garage capture.
    """
    native = pack["native_gs"]
    need(
        native["schema"] == 1 and native["context"]["depth_format"] == "PSMZ16S",
        "unsupported native reference context",
    )
    xy = native["context"]["xy_offset"]
    need(
        len(xy) == 2 and all(type(v) is int and 0 <= v <= 61439 for v in xy),
        "invalid native reference XYOFFSET",
    )
    need(
        native["context"]["scissor"] == [0, 0, 256, 256],
        "invalid native reference scissor",
    )
    packets = []
    for key, base in [("floorBase", 0x2000), ("floorLightmap", 0x2400)]:
        image = pack["images"][key]
        packets.append(
            upload_rgba(texture_bytes(image), image["width"], image["height"], base)
        )
    # An explicit clear makes every replay frame independent, including depth.
    common = [
        (0x46, 1),
        (0x45, 0),
        (0x49, 0),
        (0x18, xy[0] | xy[1] << 32),
        (0x40, 255 << 16 | 255 << 48),
        (0x4C, 4 << 16),
        (0x4E, 128 | 10 << 24),
        (0x14, 1 << 5 | 1 << 6),
        (0x08, 0),
        (0x3B, 0),
    ]
    packets += [
        ad(common + [(0x1A, 1), (0x00, 6), (0x47, 0x30000)]),
        sprite(256, 256, xy),
    ]
    counts = [0, 0]
    active_index = None
    for item in native["passes"]:
        if item.get("stage", "model") == "sky":
            continue  # The complete native visibility proof is checked separately.
        need(
            item["material_index"] == 8 and item["pass_index"] in (0, 1),
            "unsupported material in bounded floor reference",
        )
        index = item["pass_index"]
        need(index >= int(counts[1] > 0), "native floor reference pass order changed")
        counts[index] += 1
        key, base = ("floorBase", 0x2000) if index == 0 else ("floorLightmap", 0x2400)
        image = pack["images"][key]
        registers = [
            (0x1A, 0),
            (0x1B, 1 << 4 | 1 << 6),
            (0x47, 0x50003),
            (0x4C, 4 << 16 | (0xFF000000 << 32 if index else 0)),
            (0x4E, 128 | 10 << 24),
            (0x42, 0x81 if index else 0x0A),
            (0x06, tex0(base, image["width"], image["height"])),
            (0x08, 0),
        ]
        if index != active_index:
            packets.append(ad(registers))
            active_index = index
        chunks = [
            base64.b64decode(value, validate=True) for value in item["gif_chunks"]
        ]
        need(
            bool(chunks) and all(len(value) % 16 == 0 for value in chunks),
            "invalid original native GIF chunk extent",
        )
        packets.append(b"".join(chunks))
    need(
        counts == [4, 4],
        "native floor reference requires both complete original passes",
    )
    # Native DATE alpha-only prefill, with color/depth writes masked.
    packets += [
        ad(
            [
                (0x1A, 1),
                (0x00, 6),
                (0x47, 0x4000),
                (0x4C, 4 << 16 | 0x00FFFFFF << 32),
                (0x4E, 128 | 10 << 24 | 1 << 32),
            ]
        ),
        sprite(256, 256, xy, color=(0, 0, 0, 48)),
    ]
    if panorama_offset16 is not None:
        need(
            type(panorama_offset16) is int and 0 <= panorama_offset16 < 512 * 16,
            "invalid native panorama offset",
        )
        image = pack["images"]["panorama"]
        need(
            (image["width"], image["height"]) == (512, 256),
            "unsupported native panorama dimensions",
        )
        packets += [
            upload_rgba(texture_bytes(image), 512, 256, 0x2800),
            ad(
                [
                    (0x1A, 1),
                    (0x00, 6 | 1 << 4 | 1 << 6),
                    (0x47, 0),
                    (0x4C, 4 << 16 | 0xFF000000 << 32),
                    (0x06, tex0(0x2800, 512, 256)),
                    (0x08, 0),
                    (0x42, 0x8000000068),
                ]
            ),
            sprite(
                256,
                256,
                xy,
                color=(127, 127, 127, 128),
                uv=((panorama_offset16 / 8192, 0), (1 + panorama_offset16 / 8192, 1)),
            ),
        ]
    if copy_specular:
        packets += [
            ad(
                [
                    (0x18, 0),
                    (0x40, 63 << 16 | 63 << 48),
                    (0x4C, 0x100 | 1 << 16),
                    (0x4E, 128 | 10 << 24 | 1 << 32),
                    (0x1A, 1),
                    (0x00, 6 | 1 << 4 | 1 << 6),
                    (0x47, 0),
                    (0x06, tex0(0, 256, 256)),
                    (0x08, 5),
                    (0x42, 0x80000000A8),
                ]
            ),
            sprite(64, 64, [0, 0], color=(127, 127, 127, 128), uv=((0, 0), (1, 1))),
        ]
    # FINISH alone need not dispatch a pending software-GS primitive batch.
    # A primitive-class barrier flushes the final draw without submitting any
    # additional vertices, before the replay's VSync/frame label advances.
    packets.append(ad([(0x00, 0), (0x61, 0)]))
    return packets


def compare_rgba(inputs):
    actual, expected = inputs["actual"], inputs["expected"]
    need(len(actual) == len(expected), "official GS reference output extent mismatch")
    different = sum(a != b for a, b in zip(actual, expected))
    need(different == 0, f"official GS reference differs in {different} RGBA bytes")
    return common.sha256(actual)


def visibility_packets(records):
    """Test emitted geometry footprint regardless of its unrecovered shading.

    FBA forces a nonzero alpha bit for every passing fragment. With untextured,
    unblended writes and ALWAYS depth, even a zero-color source vertex cannot
    hide a covered pixel. Original GIF/XYZF2/ADC bytes remain unchanged.
    """
    context = records["context"]
    xy = context["xy_offset"]
    need(context["scissor"] == [0, 0, 256, 256], "invalid visibility scissor")
    states = [
        (0x46, 1),
        (0x45, 0),
        (0x49, 0),
        (0x4A, 0),
        (0x18, xy[0] | xy[1] << 32),
        (0x40, 255 << 16 | 255 << 48),
        (0x4C, 4 << 16),
        (0x4E, 128 | 10 << 24 | 1 << 32),
        (0x3B, 0),
        (0x1A, 1),
        (0x00, 6),
        (0x47, 0x30000),
    ]
    packets = [ad(states), sprite(256, 256, xy), ad([(0x1A, 0), (0x1B, 0), (0x4A, 1)])]
    for item in records["passes"]:
        chunks = [
            base64.b64decode(value, validate=True) for value in item["gif_chunks"]
        ]
        need(
            all(len(value) % 16 == 0 for value in chunks),
            "invalid visibility GIF extent",
        )
        packets.append(b"".join(chunks))
    packets.append(ad([(0x61, 0)]))
    return packets


def visibility_positive_control(context):
    """A zero-color triangle must still expose coverage through FBA alpha."""
    xy = context["xy_offset"]
    tag = struct.pack("<QQ", 3 | 1 << 15 | 1 << 46 | 3 << 47 | 3 << 60, 0x412)
    vertices = []
    for x, y in [(0, 0), (256, 0), (0, 256)]:
        vertices.append(
            struct.pack("<4f", 0, 0, 1, 0)
            + bytes(16)
            + struct.pack("<4I", xy[0] + x * 16, xy[1] + y * 16, 0, 0)
        )
    return {
        "context": context,
        "passes": [
            {"gif_chunks": [base64.b64encode(tag + b"".join(vertices)).decode()]}
        ],
    }


def original_inputs(pack, directory):
    path = mc3_disc()
    need(file_digest(path) == ISO_SHA, "native raster source disc identity mismatch")
    disc = CookedDisc(path)
    try:
        rows = {
            name: [row for row in disc.entries if row["path"] == name]
            for name in ("SLUS_213.55;1", "ASSETS.DAT;1")
        }
        need(
            all(len(value) == 1 for value in rows.values()),
            "native raster disc member is missing or ambiguous",
        )
        executable = rows["SLUS_213.55;1"][0]
        target = directory / "SLUS_213.55"
        target.write_bytes(disc.read_at(executable["lba"] * 2048, executable["size"]))
        archive_row = rows["ASSETS.DAT;1"][0]
        archive = DaveArchive(disc.region(archive_row), archive_row["size"])
        need(
            encode(from_archive(archive)) == encode(pack),
            "native raster pack differs from original disc derivation",
        )
        city = [
            row
            for row in archive.records
            if row["name"] == "resources/city/sd_midnight_clear.pck"
        ]
        need(len(city) == 1, "native raster city input is missing or ambiguous")
        return target, archive.payload(city[0])
    finally:
        disc.close()


def comparison_controls():
    inputs = {"actual": bytes(16), "expected": bytes(16)}
    controls = [
        (
            "one reference byte changed",
            lambda value: value.update(actual=bytes([1]) + bytes(15)),
        ),
        ("reference extent changed", lambda value: value.update(actual=bytes(12))),
    ]
    return common.run_controls(inputs, controls, compare_rgba, ValueError)


def latest_target_frames(receipt, size):
    candidates = [row for row in receipt["frames"] if row["size"] == list(size)]
    need(bool(candidates), "official GS reference produced no matching output")
    # Last draw in each replay frame is the completed selected target.
    latest = {}
    for row in candidates:
        frame = row["file"].split("_f", 1)[1][:5]
        latest[frame] = row
    need(
        set(latest) == {"00000", "00001", "00002"},
        "official GS reference replay frames incomplete",
    )
    return list(latest.values())


def compare_frames(receipt, directory, expected, size):
    frames = latest_target_frames(receipt, size)
    for row in frames:
        actual = (Path(directory) / row["file"]).read_bytes()
        compare_rgba({"actual": actual, "expected": expected})
    return frames


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--available", action="store_true")
    parser.add_argument("--pack", type=Path, default=OUTPUT)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--write", action="store_true")
    args = parser.parse_args()
    try:
        identity()
        mc3_disc()
    except RuntimeUnavailable as error:
        print(str(error))
        return 1 if args.available else 3
    except FileNotFoundError as error:
        print(str(error))
        return 1
    except (ValueError, RuntimeError) as error:
        if args.available:
            print(str(error))
            return 2  # A corrupt provisioned runtime is a failure, not a skip.
        raise
    if args.available:
        return 0
    need(
        shutil.which("node") is not None,
        "native shared-renderer comparison requires Node.js",
    )
    if args.output is None:
        area = ROOT / ".scratch/mc3-raster-reference"
        area.mkdir(parents=True, exist_ok=True)
        args.output = Path(tempfile.mkdtemp(prefix="run-", dir=area))
    else:
        need(not args.output.exists(), "choose a new reference output directory")
        args.output.mkdir(parents=True)
    print("Reference evidence: " + str(args.output.resolve()), flush=True)
    pack = json.loads(args.pack.read_text())
    executable, city = original_inputs(pack, args.output)
    regenerated = regenerate(pack, executable, city, args.output / "original-execution")
    fixture = json.loads(NATIVE_CAPTURE.read_text())
    need(
        normalize_capture_fixture(regenerated) == fixture,
        "executed original EE/VU capture fixture does not reproduce",
    )
    print(
        f"Executed original EE/VU jobs: {len(regenerated['executions'])}; deterministic fixture reproduced",
        flush=True,
    )
    visibility = []
    for flag, records in regenerated["visibility_controls"].items():
        dump = args.output / ("visibility-" + flag + ".gs")
        write_gs_dump(
            dump,
            visibility_packets(
                {"context": regenerated["native_gs"]["context"], "passes": records}
            ),
        )
        directory = args.output / ("visibility-" + flag + "-reference")
        receipt = run_gs(dump, directory)
        frames = compare_frames(receipt, directory, bytes(256 * 256 * 4), (256, 256))
        visibility.append(
            {
                "cull_flags": int(flag),
                "source_batches": len(records),
                "differing_bytes": 0,
                "frames": len(frames),
            }
        )
        print(
            f"PASS hidden geometry cull={flag}: {len(records)} batches, 3 frames, zero writes",
            flush=True,
        )
    control_dump = args.output / "visibility-positive.gs"
    write_gs_dump(
        control_dump,
        visibility_packets(
            visibility_positive_control(regenerated["native_gs"]["context"])
        ),
    )
    control_dir = args.output / "visibility-positive-reference"
    control = run_gs(control_dump, control_dir)
    for row in latest_target_frames(control, (256, 256)):
        raw = (control_dir / row["file"]).read_bytes()
        need(
            sum(value != 0 for value in raw[3::4]) == 32896,
            "visibility control did not detect the complete visible triangle",
        )
    with tempfile.TemporaryDirectory(prefix="mc3-raster-prediction-") as temp:
        subprocess.run(
            [
                "node",
                str(ROOT / "tools/mc3_raster_reference.mjs"),
                str(args.pack.resolve()),
                temp,
            ],
            check=True,
            cwd=ROOT,
        )
        comparisons = []
        for name, offset, copy in [
            ("capture", None, False),
            ("panorama0", 0, False),
            ("specular0", 0, True),
            ("specular7", 7, True),
        ]:
            dump = args.output / (name + ".gs")
            write_gs_dump(
                dump,
                capture_packets(pack, panorama_offset16=offset, copy_specular=copy),
                width=64 if copy else 256,
                height=64 if copy else 256,
                display_fbp=0x100 if copy else 0,
            )
            directory = args.output / (name + "-reference")
            receipt = run_gs(dump, directory)
            expected = (Path(temp) / (name + ".rgba")).read_bytes()
            frames = compare_frames(
                receipt, directory, expected, (64, 64) if copy else (256, 256)
            )
            comparisons.append({"name": name, "differing_bytes": 0, "frames": frames})
            print(
                f"PASS {name}: 3 frames, {len(expected)} RGBA bytes each, zero differences",
                flush=True,
            )
        result = {
            "status": "executed",
            "comparisons": comparisons,
            "claim_limits": [
                "Pinned official PCSX2 software GS; no physical PS2 or booted-game frame claim."
            ],
        }
        (args.output / "comparison.json").write_text(
            json.dumps(result, indent=2) + "\n"
        )
        stable = {
            "schema": 1,
            "reference": {
                key: receipt["runtime"][key]
                for key in ("binary_sha256", "appimage_sha256")
            },
            "capture_input_sha256": regenerated["capture_input_sha256"],
            "native_execution_jobs": len(regenerated["executions"]),
            "visibility": visibility,
            "visibility_positive_control_pixels": 32896,
            "comparisons": [
                {
                    "name": row["name"],
                    "differing_bytes": 0,
                    "size": row["frames"][0]["size"],
                    "frames": len(row["frames"]),
                    "rgba_sha256": row["frames"][0]["sha256"],
                }
                for row in comparisons
            ],
            "negative_controls": comparison_controls(),
            "claim_limits": result["claim_limits"],
        }
    return common.finish(
        stable,
        RECEIPT,
        sys.argv[1:],
        ROOT,
        {"native_raster_reference": "byte-exact", "comparisons": len(comparisons)},
    )


if __name__ == "__main__":
    raise SystemExit(main())
