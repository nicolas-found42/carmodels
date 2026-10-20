"""Bounded MC3 __specular__ render-target copy evidence and byte arithmetic.

This stage consumes the original 256-square environment render target. It does
not reconstruct that target's garage/city draws or supply an invented image.
"""

import hashlib
import json
import struct
from pathlib import Path


EVIDENCE = (
    Path(__file__).resolve().parents[1] / "research/evidence/"
    "midnight-club-3-remix/previews/tire-alpha-native/specular-generation.json"
)
EXECUTABLE_SHA = "1b237ade5cafaf8ddd9fd049f40d81eb46f38f2600a8f1c7273d4f836973fe9d"
WORDS_SHA = "0538a6f7946c0e5752b48895889964c6a24d3ae9286ea408d5eb9513e09d9172"
PINS_SHA = "1a3c575300734c766733b0d8d22d9da717966aa04579c8cf92bb235e14a0a487"


def need(condition, message):
    if not condition:
        raise ValueError(message)


def contract(receipt=None):
    """Validate the bounded source receipt and expose only the copy contract."""
    proof = json.loads(EVIDENCE.read_text()) if receipt is None else receipt
    need(
        proof["source_sha256"] == EXECUTABLE_SHA,
        "specular executable identity mismatch",
    )
    pins = json.dumps(
        proof["intervals"], sort_keys=True, separators=(",", ":")
    ).encode()
    need(hashlib.sha256(pins).hexdigest() == PINS_SHA, "specular source pins changed")
    encoded = json.dumps(
        proof["selected_words"], sort_keys=True, separators=(",", ":")
    ).encode()
    need(
        hashlib.sha256(encoded).hexdigest() == WORDS_SHA,
        "specular selected instructions changed",
    )
    need(
        proof["selected_words_sha256"] == WORDS_SHA,
        "specular instruction receipt changed",
    )
    copy = proof["derived_contract"]
    need(
        copy["target_size"] == [64, 64] and copy["target_psm"] == "PSMCT32",
        "specular target layout changed",
    )
    need(
        copy["color_tint_native"] == [127, 127, 127, 128], "specular modulation changed"
    )
    need(
        copy["blend"] == "(Cs-0)*128/128+0" and copy["clear_needed"] is False,
        "specular replacement blend changed",
    )
    need(
        copy["destination_rectangle"] == [0, 0, 64, 64], "specular destination changed"
    )
    need(
        copy["source_clamp"] == 5 and copy["target_clamp"] == 0,
        "specular source/target sampler separation changed",
    )
    return {
        "schema": 1,
        "source_size": [256, 256],
        "target_size": [64, 64],
        "target_psm": "PSMCT32",
        "source_uv_step": 4,
        "source_uv_origin": 0,
        "linear_half_texel": -0.5,
        "wrap": "clamp-to-edge",
        "filter_fraction_bits": 4,
        "filter_order": "floor horizontal, floor vertical",
        "native_modulate_rgba": [127, 127, 127, 128],
        "native_blend_alpha": "0x80000000a8",
        "blend_equation": "(Cs-0)*128/128+0",
        "input_scope": "original environment render target, not reconstructed by this copy stage",
    }


def from_executable(executable):
    """Check the private original ELF against every bounded interval and word."""
    need(
        hashlib.sha256(executable).hexdigest() == EXECUTABLE_SHA,
        "specular executable identity mismatch",
    )
    need(executable[:7] == b"\x7fELF\x01\x01\x01", "unsupported specular ELF")
    phoff = struct.unpack_from("<I", executable, 28)[0]
    width, count = struct.unpack_from("<HH", executable, 42)
    need(
        width >= 32 and phoff + width * count <= len(executable),
        "invalid specular ELF segments",
    )

    def read(start, size):
        matches = []
        for i in range(count):
            kind, offset, address, _, length = struct.unpack_from(
                "<IIIII", executable, phoff + i * width
            )
            if kind == 1 and address <= start < start + size <= address + length:
                need(
                    offset + length <= len(executable), "truncated specular ELF segment"
                )
                matches.append(
                    executable[
                        offset + start - address : offset + start - address + size
                    ]
                )
        need(len(matches) == 1, "missing or ambiguous specular source interval")
        return matches[0]

    receipt = json.loads(EVIDENCE.read_text())
    for item in receipt["intervals"].values():
        start, end = int(item["start"], 16), int(item["end"], 16)
        need(
            hashlib.sha256(read(start, end - start)).hexdigest() == item["sha256"],
            "specular source interval changed",
        )
    for pc, word in receipt["selected_words"].items():
        need(
            struct.unpack("<I", read(int(pc, 16), 4))[0] == int(word, 16),
            "specular source instruction changed",
        )
    return contract(receipt)


def copy_environment_rgba(source):
    """Copy native RGBA8 256x256 to native RGBA8 64x64 using the GS sprite.

    GS samples integer screen coordinates. UVs are 4*i, shifted by -0.5
    for linear filtering, hence neighbors max(0,4*i-1) and 4*i with equal weights.
    The source EnvMapColor sampler clamps both axes; the output sampler is separate.
    Integer filtering truncates horizontally before vertically. RGB is then
    modulated by 127/128; alpha by 128/128. This is not a box resize.
    """
    need(
        isinstance(source, (bytes, bytearray, memoryview))
        and len(source) == 256 * 256 * 4
        and memoryview(source).format == "B"
        and memoryview(source).ndim == 1,
        "specular copy requires native 256x256 RGBA8",
    )
    output = bytearray(64 * 64 * 4)
    for y in range(64):
        y0, y1 = max(0, 4 * y - 1), 4 * y
        for x in range(64):
            x0, x1 = max(0, 4 * x - 1), 4 * x
            offsets = [
                (y0 * 256 + x0) * 4,
                (y0 * 256 + x1) * 4,
                (y1 * 256 + x0) * 4,
                (y1 * 256 + x1) * 4,
            ]
            for channel in range(4):
                top = (source[offsets[0] + channel] + source[offsets[1] + channel]) // 2
                bottom = (
                    source[offsets[2] + channel] + source[offsets[3] + channel]
                ) // 2
                filtered = (top + bottom) // 2
                output[(y * 64 + x) * 4 + channel] = (
                    filtered * (128 if channel == 3 else 127) // 128
                )
    return bytes(output)


def prop_reflection_masks(definition_flags, instance_flags):
    """Native 00396df8 selection for garage capture masks 2 and 0x20.

    The flags word starts at definition+0x94; instance flags at instance+8.
    Geometry availability and the global reflection setting are separate gates.
    """
    need(
        isinstance(definition_flags, int) and 0 <= definition_flags <= 0xFFFFFFFF,
        "invalid native prop definition flags",
    )
    need(
        isinstance(instance_flags, int) and 0 <= instance_flags <= 0xFFFFFFFF,
        "invalid native prop instance flags",
    )
    if instance_flags & 0x40 and definition_flags >> 24 == 0:
        return []
    result = []
    if definition_flags & 0xFF0000:
        result.append(2)
    if definition_flags & 0xFFFFFF == 0:
        result.append(0x20)
    return result
