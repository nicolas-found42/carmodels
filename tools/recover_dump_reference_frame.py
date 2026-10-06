#!/usr/bin/env python3
"""Reference frames for the captured GS dumps, derived from the dumps' own headers.

PCSX2 embeds a native-resolution RGBA screenshot of the rendered frame in every
GSDump header it writes (`GSDumpBase::AddHeader`, pinned v2.8.2 GSDump.h/.cpp).
The two dumps pinned below carry that frame, so a documented command produces
the issue-20 reference PNGs without an emulator run:

    python3 tools/recover_dump_reference_frame.py --write

`--write` regenerates the receipt and writes the frame PNGs; without it the
verifier re-derives everything from the pinned dump bytes and requires the
committed receipt to reproduce byte for byte. The PNG frames themselves stay
gitignored (commercial game content); the receipt carries their hashes.

The frames are the capture-time GS output, not a fresh replay: replaying a dump
headlessly into a PNG is a separate, environment-bound route (PINE refuses
savestates during replay, the screenshot hotkey needs a GUI session, and
pcsx2-gsrunner is not shipped in the pinned builds). The replay cross-check
remains open and is recorded in `claim_limits`.
"""
from pathlib import Path
import shutil
import struct
import subprocess
import sys
import zlib

import verifier_common as common

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "research/evidence/reference-frames/dump-reference-frames.json"
FRAMES = ROOT / "research/evidence/reference-frames/frames"

MARKER = 0xFFFFFFFF
HEADER_STRUCT = "<9I"


class FrameError(ValueError):
    pass


need = common.make_need(FrameError)

# Pinned inputs: the dumps the repo's receipts already bind by compressed sha256
# (retained-ring-gsdump-alignment.json, menu98-sprite-ptg-join.json). The raw
# *-GS.bin files under runtime/ are savestate GS memory images, not GSDumps:
# they carry no header and no screenshot, so they are out of scope here.
DUMPS = [
    {
        "path": ROOT / "research/evidence/continuation/runtime/snaps/"
                       "Ford Racing 2_SLES-51705_20261004182459.gs.zst",
        "compressed_sha256": "fe3cad806c831b6db5577a336a1f92cfc1ac007d0004f3efb99117ae0eb77e88",
    },
    {
        "path": ROOT / "research/evidence/continuation/runtime/linux/snaps/"
                       "Ford Racing 2_SLES-51705_20261005010217.gs.zst",
        "compressed_sha256": "126c9a909501d157d5bab5359a66c63cbb6966bf70504e3f671a9ede5ee01ae9",
    },
]


def zstd_binary():
    return shutil.which("zstd") or "/opt/homebrew/bin/zstd"


def png_bytes(width, height, rgba):
    if len(rgba) != width * height * 4:
        raise FrameError("RGBA byte count does not match dimensions")

    def chunk(kind, payload):
        return struct.pack(">I", len(payload)) + kind + payload + struct.pack(">I", zlib.crc32(kind + payload))

    scanlines = b"".join(b"\0" + rgba[y * width * 4:(y + 1) * width * 4] for y in range(height))
    return (b"\x89PNG\r\n\x1a\n" +
            chunk(b"IHDR", struct.pack(">2I5B", width, height, 8, 6, 0, 0, 0)) +
            chunk(b"IDAT", zlib.compress(scanlines)) +
            chunk(b"IEND", b""))


def load_inputs():
    for dump in DUMPS:
        if not dump["path"].is_file():
            raise SystemExit("runtime input missing: %s (see docs/static-inputs.md)" % dump["path"].name)
    dumps = []
    for dump in DUMPS:
        raw = dump["path"].read_bytes()
        need(common.sha256(raw) == dump["compressed_sha256"],
             "dump bytes differ from the compressed pin: " + dump["path"].name)
        decompressed = subprocess.check_output([zstd_binary(), "-d", "-c", str(dump["path"])])
        dumps.append({"name": dump["path"].name, "compressed_pin": dump["compressed_sha256"],
                      "data": decompressed})
    return {"dumps": dumps}


def parse_dump(entry):
    """Parse the GSDump v9 header exactly as GSDumpBase::AddHeader writes it."""
    data = entry["data"]
    marker, header_size = struct.unpack_from("<II", data, 0)
    need(marker == MARKER, "GSDump marker differs")
    (state_version, state_size, serial_offset, serial_size, crc,
     screenshot_width, screenshot_height, screenshot_offset, screenshot_size) = struct.unpack_from(HEADER_STRUCT, data, 8)
    need(state_version == 9, "unexpected state version")
    need(state_size > 0, "state size is empty")
    serial_start = 8 + serial_offset
    serial_end = serial_start + serial_size
    need(0 < serial_size <= 64 and serial_end <= header_size, "serial size out of bounds")
    serial = data[serial_start:serial_end].decode("ascii", errors="replace")
    need(serial and serial.replace("-", "").isalnum(), "serial is not an alphanumeric product code")
    need(crc != 0, "disc CRC is zero")
    shot_start = 8 + screenshot_offset
    shot_end = shot_start + screenshot_size
    need(shot_end <= 8 + header_size, "screenshot extends past the header")
    need(screenshot_width * screenshot_height * 4 == screenshot_size,
         "screenshot size differs from width*height*4")
    screenshot = data[shot_start:shot_end]
    return {
        "dump": entry["name"],
        "compressed_sha256": entry["compressed_pin"],
        "decompressed_sha256": common.sha256(data),
        "state_version": state_version,
        "serial": serial,
        "disc_crc": "0x%08x" % crc,
        "width": screenshot_width,
        "height": screenshot_height,
        "screenshot_offset": shot_start,
        "screenshot_bytes": screenshot_size,
        "screenshot_sha256": common.sha256(screenshot),
    }


def frame_png(entry, row):
    return png_bytes(row["width"], row["height"],
                     entry["data"][row["screenshot_offset"]:row["screenshot_offset"] + row["screenshot_bytes"]])


def derive(inputs):
    rows = []
    for entry in inputs["dumps"]:
        row = parse_dump(entry)
        png = frame_png(entry, row)
        row["png_sha256"] = common.sha256(png)
        row["png_path"] = str(FRAMES.relative_to(ROOT) / (Path(row["dump"]).stem + ".png"))
        rows.append(row)
    need(len(rows) == len(DUMPS), "reference-frame population differs")
    return {
        "schema": "fr2-dump-reference-frames/v1",
        "scope": "Embedded capture-time screenshots of the two pinned GSDumps; raw *-GS.bin "
                 "savestate memory images carry no screenshot and are excluded.",
        "rows": rows,
        "render_fidelity_complete": False,
        "claim_limits": [
            "The frames are the screenshots PCSX2 embedded at dump-save time (capture-time GS "
            "output), not frames from a fresh headless replay of the dumps.",
            "Replaying a dump into a PNG is environment-bound on the pinned builds: PINE refuses "
            "savestates during replay, the screenshot hotkey needs a GUI session, and "
            "pcsx2-gsrunner is not shipped in the pinned macOS bundle or the pinned Linux image. "
            "The replay cross-check of these frames is open.",
            "One dump is a race chase frame, the other a menu frame; the receipt labels content "
            "only through the dump names and does not claim both show car renders.",
            "PNG encoding uses the stdlib zlib at its default level; determinism across zlib "
            "versions is assumed, not proven. screenshot_sha256 pins the source bytes.",
        ],
    }


def controls(inputs):
    def mutate_compressed(i):
        i["dumps"][0]["data"] = i["dumps"][0]["data"][:-1] + bytes([i["dumps"][0]["data"][-1] ^ 0xFF])

    def mutate_screenshot(i):
        row = parse_dump(i["dumps"][0])
        mutated = bytearray(i["dumps"][0]["data"])
        mutated[row["screenshot_offset"]] ^= 0x01
        i["dumps"][0]["data"] = bytes(mutated)

    def mutate_header_word(i):
        mutated = bytearray(i["dumps"][0]["data"])
        mutated[8 + 5 * 4] ^= 0x01  # screenshot_width
        i["dumps"][0]["data"] = bytes(mutated)

    def mutate_serial(i):
        mutated = bytearray(i["dumps"][0]["data"])
        serial_start = 8 + struct.calcsize(HEADER_STRUCT)
        mutated[serial_start] = ord("X") if mutated[serial_start] != ord("X") else ord("Y")
        i["dumps"][0]["data"] = bytes(mutated)

    def truncate_screenshot(i):
        row = parse_dump(i["dumps"][0])
        i["dumps"][0]["data"] = i["dumps"][0]["data"][:row["screenshot_offset"] + row["screenshot_bytes"] - 4]

    tests = [
        ("decompressed dump byte changed", mutate_compressed),
        ("embedded screenshot byte changed", mutate_screenshot),
        ("header width word changed", mutate_header_word),
        ("serial changed", mutate_serial),
        ("screenshot truncated", truncate_screenshot),
    ]
    results = common.run_controls(
        inputs, [(label, mutate) for label, mutate in tests], derive, FrameError,
        baseline=derive(inputs))
    for result in results:
        need(result["rejected"], "a mutation escaped: " + result["mutation"])
    return results


def write_frames(inputs, receipt):
    FRAMES.mkdir(parents=True, exist_ok=True)
    written = []
    for entry, row in zip(inputs["dumps"], receipt["rows"]):
        target = ROOT / row["png_path"]
        target.write_bytes(frame_png(entry, row))
        written.append(str(target.relative_to(ROOT)))
    return written


def main(argv):
    if "--available" in argv:
        return 0 if all(d["path"].is_file() for d in DUMPS) else 1
    inputs = load_inputs()
    result = derive(inputs)
    result["controls"] = controls(inputs)
    if "--write" in argv:
        written = write_frames(inputs, result)
        print("wrote frames: " + ", ".join(written))
    return common.finish(result, OUT, argv, ROOT, {"rows": len(result["rows"]), "controls": len(result["controls"])})


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
