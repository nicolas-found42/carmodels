"""Execute the original garage vehicle-light binder with explicit frame inputs.

This recovers source lighting independently of the viewer's generic lights. The
fixed fixture is a declared parked-car context, not a captured running game.
"""

import hashlib
import json
from pathlib import Path
import re
import struct

from mc3_environment_raster import EXECUTABLE_SHA, _read_elf, encode_ee_job

PROOF = (
    Path(__file__).resolve().parents[1] / "research/evidence/"
    "midnight-club-3-remix/previews/vehicle-lighting.json"
)
PROOF_SHA = "dbcd14e11e5a910e1acd78af32ae02eb6e5641b666c9012814d5ad92c1c60258"


def need(condition, message):
    if not condition:
        raise ValueError(message)


def source_contract(executable=None, receipt=None):
    proof = json.loads(PROOF.read_text()) if receipt is None else receipt
    raw = json.dumps(proof, sort_keys=True, separators=(",", ":")).encode()
    need(
        hashlib.sha256(raw).hexdigest() == PROOF_SHA, "vehicle lighting receipt changed"
    )
    need(
        proof["source_executable_sha256"] == EXECUTABLE_SHA,
        "vehicle lighting source changed",
    )
    if executable is not None:
        need(
            hashlib.sha256(executable).hexdigest() == EXECUTABLE_SHA,
            "vehicle lighting executable changed",
        )
        for row in proof["intervals"].values():
            raw = _read_elf(executable, row["start"], row["end"] - row["start"])
            need(
                hashlib.sha256(raw).hexdigest() == row["sha256"],
                "vehicle lighting source interval changed",
            )
        for name, row in proof["setting_fields"].items():
            need(
                _read_elf(executable, row["source_string"], len(name) + 1)
                == name.encode() + b"\0",
                "vehicle lighting source setting name changed",
            )
    return proof


def source_settings(data):
    proof = source_contract()
    need(
        isinstance(data, bytes)
        and hashlib.sha256(data).hexdigest() == proof["source_settings_sha256"],
        "vehicle lighting original garage settings changed",
    )
    text = data.decode("ascii")
    result = {}
    for name in proof["setting_fields"]:
        # The original serializer registers these names with spaces; the
        # retained source file uses their corresponding unspaced tokens.
        key = name.replace(" ", "")
        matches = re.findall(
            r"(?m)^\s*" + re.escape(key) + r"\s+([-+0-9.eE]+)\s*$", text
        )
        need(len(matches) == 1, "missing or ambiguous native garage light setting")
        result[key] = struct.unpack("<I", struct.pack("<f", float(matches[0])))[0]
    return result


def words3(value):
    need(
        isinstance(value, list)
        and len(value) == 3
        and all(
            type(x) is int and 0 <= x <= 0xFFFFFFFF and x & 0x7F800000 != 0x7F800000
            for x in value
        ),
        "explicit finite native frame words required",
    )
    return struct.pack("<3I", *value)


def lighting_job(settings, *, car_position_words, selected_offset_words):
    proof = source_contract()
    values = source_settings(settings)
    garage, actor, light = 0x1000000, 0x1002000, 0x1003000
    frame, selected, definition = 0x1004000, 0x1005000, 0x1006000
    g, a, f, s, d = (
        bytearray(0x1C90),
        bytearray(0x400),
        bytearray(0x80),
        bytearray(0x80),
        bytearray(0x100),
    )
    struct.pack_into("<I", g, 0xC, frame)
    struct.pack_into("<I", g, 0x714, selected)
    struct.pack_into("<3I", g, 0x93C, *proof["default_second_point_words"])
    struct.pack_into("<3I", g, 0x948, *proof["default_second_color_words"])
    struct.pack_into(
        "<3I",
        g,
        0x954,
        values["AmbientColor"],
        values["LightIntensity"],
        values["LightColor"],
    )
    struct.pack_into("<I", a, 0x2FC, light)
    struct.pack_into("<I", s, 4, definition)
    f[0x34:0x40] = words3(car_position_words)
    d[0x80:0x8C] = words3(selected_offset_words)
    return encode_ee_job(
        0x2FB008,
        {4: actor},
        [
            (garage, g),
            (actor, a),
            (frame, f),
            (selected, s),
            (definition, d),
            (0x6179B0, struct.pack("<I", garage)),
        ],
    )


def execute_reference(executable, settings, output, runner=None):
    from mc3_reference_runtime import run_job, BINARY_SHA, contract

    runner = run_job if runner is None else runner
    executable, output = Path(executable), Path(output)
    proof = source_contract(executable.read_bytes())
    need(not output.exists(), "choose a fresh vehicle lighting output")
    output.mkdir(parents=True)
    job = lighting_job(settings, **proof["reference_context"])
    need(
        hashlib.sha256(job).hexdigest() == proof["reference_job_sha256"],
        "vehicle lighting reference job changed",
    )
    path = output / "garage-light.job"
    path.write_bytes(job)
    receipt = runner(path, output / "execution", mode="ee", executable=executable)
    need(
        receipt["status"] == "executed"
        and receipt["job_sha256"] == proof["reference_job_sha256"]
        and receipt["original_mc3_executable_sha256"] == EXECUTABLE_SHA
        and receipt["runtime"]["binary_sha256"] == BINARY_SHA
        and receipt["adapter_sha256"] == contract()["adapter_source_sha256"],
        "vehicle lighting execution binding changed",
    )
    data = (output / "execution/ee-ram.bin").read_bytes()
    need(len(data) == 32 * 1024 * 1024, "vehicle lighting output extent changed")
    words = list(struct.unpack_from("<34I", data, 0x1003000))
    need(
        words == proof["reference_light_words"],
        "vehicle lighting original output changed",
    )
    result = {
        "light_words": words,
        "execution": receipt,
        "claim_limits": proof["claim_limits"],
    }
    (output / "comparison.json").write_text(json.dumps(result, indent=2) + "\n")
    return result
