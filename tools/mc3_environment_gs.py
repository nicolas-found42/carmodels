"""Source-bound MC3 environment GS state, separate from image reconstruction."""

import hashlib
import json
import struct
from pathlib import Path

from mc3_specular_native import EXECUTABLE_SHA, need


EVIDENCE = (
    Path(__file__).resolve().parents[1] / "research/evidence/"
    "midnight-club-3-remix/previews/tire-alpha-native/environment-gs.json"
)
RECEIPT_SHA = "39f7d26471a8f6444576997ac232f6b4d79b704b11186d8e4f3eac414b6de36c"
MATERIAL_ALPHA = (0x44, 0x8000000068, 0x8000000062, 0x81, 0x58, 0x80000000A8, 0x54)


def contract(receipt=None):
    """Check the bounded evidence before exposing the material-state contract."""
    proof = json.loads(EVIDENCE.read_text()) if receipt is None else receipt
    encoded = json.dumps(proof, sort_keys=True, separators=(",", ":")).encode()
    need(
        hashlib.sha256(encoded).hexdigest() == RECEIPT_SHA,
        "environment GS receipt changed",
    )
    return {
        "material_alpha_registers": list(MATERIAL_ALPHA),
        "garage_scalar_bits": "3ebf7cee",
        "prefill_native_alpha": 48,
        "prefill_destination_alpha_msb": 0,
        "prefill_write_mask": 8,
        "sky_write_mask": 15,
        "static_write_mask": 7,
        "static_material_blend": 1,
        "scope": "fixed original garage alpha prefill and material blend namespace",
    }


def from_executable(executable):
    """Re-read every original interval and selected source instruction."""
    need(
        hashlib.sha256(executable).hexdigest() == EXECUTABLE_SHA,
        "environment executable identity mismatch",
    )
    phoff = struct.unpack_from("<I", executable, 28)[0]
    width, count = struct.unpack_from("<HH", executable, 42)

    def read(address, length):
        matches = []
        for i in range(count):
            kind, offset, base, _, size = struct.unpack_from(
                "<IIIII", executable, phoff + i * width
            )
            if kind == 1 and base <= address < address + length <= base + size:
                matches.append(
                    executable[
                        offset + address - base : offset + address - base + length
                    ]
                )
        need(len(matches) == 1, "missing environment source interval")
        return matches[0]

    proof = json.loads(EVIDENCE.read_text())
    contract(proof)
    for item in proof["intervals"].values():
        start, end = int(item["start"], 16), int(item["end"], 16)
        need(
            hashlib.sha256(read(start, end - start)).hexdigest() == item["sha256"],
            "environment GS source interval changed",
        )
    for pc, word in proof["selected_words"].items():
        need(
            struct.unpack("<I", read(int(pc, 16), 4))[0] == int(word, 16),
            "environment GS source instruction changed",
        )
    return contract(proof)


def material_alpha_register(value):
    """Decode 7000006c; this is distinct from helper52ecc0's enum namespace."""
    need(
        type(value) is int and 0 <= value <= 0xFFFFFFFF, "invalid material blend state"
    )
    if value & 0x10000:
        return value & 255 | (value & 0xFF00) << 24
    return MATERIAL_ALPHA[value] if value < len(MATERIAL_ALPHA) else 0


def blend_rgb(source, destination, source_alpha, destination_alpha, register):
    """PSMCT32 clamped GS (A-B)*C/128+D, with a signed arithmetic shift.

    Alpha writes are separate: the GS blend equation only combines RGB.
    Inputs here are native byte values, including alpha's native128 unity.
    """
    need(len(source) == len(destination) == 3, "GS blend requires RGB triples")
    values = [*source, *destination, source_alpha, destination_alpha]
    need(
        all(type(v) is int and 0 <= v <= 255 for v in values), "invalid native GS color"
    )
    need(type(register) is int and 0 <= register < 1 << 64, "invalid GS ALPHA register")
    selectors = [(register >> shift) & 3 for shift in (0, 2, 4, 6)]
    need(all(x < 3 for x in selectors), "unsupported GS ALPHA selector")
    coefficient = (source_alpha, destination_alpha, (register >> 32) & 255)[
        selectors[2]
    ]
    result = []
    for s, d in zip(source, destination):
        candidates = (s, d, 0)
        value = (candidates[selectors[0]] - candidates[selectors[1]]) * coefficient >> 7
        result.append(max(0, min(255, value + candidates[selectors[3]])))
    return tuple(result)


def prefill_garage_alpha(image):
    """Write alpha48 only where native DATE finds destination-alpha MSB zero.

    Colorwrite8 preserves RGB; state88=1 selects DATE/DATM=1/0. The authored
    floor's low alpha passes, but an arbitrary destination alpha128 must not.
    """
    need(
        isinstance(image, (bytes, bytearray)) and len(image) == 256 * 256 * 4,
        "garage prefill requires native256x256 RGBA8",
    )
    result = bytearray(image)
    result[3::4] = bytes(48 if alpha < 128 else alpha for alpha in image[3::4])
    return bytes(result)
