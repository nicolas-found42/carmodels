"""Bounded parser for the retained MC3 PS2 tire template, not a shader interpreter.

The shipped template encodes line endings as literal backslash-r/backslash-n.
Only its active PS2 branch is relevant; its semicolon-commented old pass is not.
"""

import re
import json
from pathlib import Path

import verifier_common as common

from verifier_common import make_need


class TireAlphaError(ValueError):
    pass


need = make_need(TireAlphaError)
# Exact expected active vocabulary. Unrecognized state is never silently ignored.
EXPECTED = [
    ("ps2microcode", "specular2_dc"),
    ("lighting", "dir"),
    ("texture", "%0"),
    ("texture", "%1"),
    ("texcombine", "modulate2x"),
    ("ps2blend", "0 0 As Cs 0"),
    ("texgen", "reflect"),
    ("scales", "constant 0.5"),
    ("scalet", "constant 0.5"),
    ("slides", "constant 0.5"),
    ("slidet", "constant 0.5"),
    ("texsrc", "0"),
    ("colorwrite", "rgba"),
    ("alphafunc", "always"),
    ("basecolor", "127 127 127 255"),
]


ROOT = Path(__file__).resolve().parents[1]
AREA = ROOT / "research/evidence/midnight-club-3-remix/previews/tire-alpha-native"
SHADER_SHA = "a5054894ed8236a356fade03730a82bde3bfc3b7fdc70e584105d4a177b0f2ad"
ISO_SHA = "de199f7e7f57b7cb603a129217f7482d50644fd66558450dfeb5612857b732f9"
STORED_SHA = "3306d6c440fdb19723b482d8182be7be34d04419ef37a690ca8b7e8798030d80"
EXECUTABLE_SHA = "1b237ade5cafaf8ddd9fd049f40d81eb46f38f2600a8f1c7273d4f836973fe9d"
PROOFS = {
    "state-consumer": (
        0x2B1F90,
        0x2B2168,
        "691b8af1197b8b89e954fc86a50677a2e204b27c69217e9effb65580798f7a08",
        "59a7964c236becbe40805630aa706fb6eb37e943431e45be04eb05f4381e3c51",
    ),
    "test-packing-scalar": (
        0x2AD3DC,
        0x2AD4A0,
        "2a96dda70e0f4f62cc32554b9de72714800659ae4f388ba5a0d525d2ea885c70",
        "cb6555cbd711a35aaea5888d0ebdc1b79d855af7279095df0f898df55acde2bb",
    ),
    "state-writer": (
        0x2B0500,
        0x2B0624,
        "955dcc5db2d8706383bb67cd90fd920f0545c9e75474d266f1472b98292ebc17",
        "4351f36ae4fbd3860e75512549dcb72ee86dbcd801f4c024e314bc2050663ecd",
    ),
    "renderer-preparation": (
        0x3BEB40,
        0x3BF04C,
        "f9e5e9722702d7094285165b8ff3079191e3149ad6fe1af4a36d8bb86d5615f6",
        "44daf29f30c9da9c98487dcf54397ccab93825141e6f4dd6d8cdabe08febf564",
    ),
    "state-finalizer": (
        0x2B0628,
        0x2B06B8,
        "6e3af01bf6a300c7c303c55cfeef0fee675807458ade8216a596db00272ce77d",
        "bb484affc744d1084c893436bd2e65f84f36bdc7255aef0c80bb6606f661976e",
    ),
}


def active_ps2_lines(data):
    """Select the explicit #if PS2 arm; reject unsupported conditional syntax."""
    try:
        text = data.decode("ascii")
    except (UnicodeDecodeError, AttributeError) as error:
        raise TireAlphaError("shader must be ASCII bytes") from error
    text = text.replace(r"\r\n", "\n")
    need("\\" not in text, "unsupported shader escape")
    result, stack = [], []
    in_inputs, saw_inputs, saw_ps2 = False, False, False
    for raw in text.splitlines():
        line = raw.split(";", 1)[0].strip()
        if not line:
            continue
        if line == "inputs":
            need(not stack and not saw_inputs, "duplicate or conditional inputs")
            in_inputs, saw_inputs = True, True
            continue
        if in_inputs:
            if line == "endinputs":
                in_inputs = False
            else:
                need(
                    bool(re.fullmatch(r"[01] TEXTURE (color|lightMap)", line)),
                    "unknown shader input",
                )
            continue
        if line.startswith("#"):
            if line == "#if PS2":
                need(not stack and not saw_ps2, "duplicate or nested PS2 branch")
                saw_ps2 = True
                stack.append(True)
            elif line == "#else":
                need(stack == [True], "unexpected or duplicate else")
                stack[0] = False
            elif line == "#endif":
                need(bool(stack), "unmatched endif")
                stack.pop()
            else:
                raise TireAlphaError("unsupported shader conditional: " + line)
            continue
        need(bool(stack), "directive outside PS2 conditional")
        if stack[0]:
            result.append(" ".join(line.split()))
    need(saw_inputs and not in_inputs, "missing or unfinished inputs")
    need(saw_ps2 and not stack, "missing or unfinished PS2 branch")
    return result


def tire_alpha_policy(data):
    """Validate the complete active template and expose its source-level state."""
    lines = active_ps2_lines(data)
    directives = [tuple(line.split(" ", 1)) for line in lines]
    for name in (
        "alphafunc",
        "ps2blend",
        "colorwrite",
        "basecolor",
        "texcombine",
        "ps2microcode",
    ):
        found = [
            args for command, *tail in directives if command == name for args in tail
        ]
        need(len(found) == 1, "missing or duplicate " + name)
        expected = next(args for command, args in EXPECTED if command == name)
        need(found[0] == expected, "changed " + name)
    need(directives == EXPECTED, "unknown, reordered or changed active tire directive")
    return {
        "platform": "PS2",
        "alpha_test": "always",
        "base_pass_blend": {"A": "0", "B": "0", "C": "As", "D": "Cs", "FIX": 0},
        "base_pass_rgb_equation": "(0 - 0) * As + Cs = Cs",
        "color_write": "rgba",
        "base_color": [127, 127, 127, 255],
        "texture_combine": "modulate2x",
        "microcode": "specular2_dc",
        "active_pass_declarations": 1,
    }


def decode_state_commands(data):
    """Decode native writer byte/u32 forms; command meanings are separate evidence."""
    need(type(data) is bytes and len(data) <= 1024, "invalid state stream")
    rows, offset, seen = [], 0, set()
    while offset < len(data):
        start, header = offset, data[offset]
        offset += 1
        if header == 255:
            need(offset == len(data), "trailing state bytes")
            return rows
        command, flags = header & 63, header & 192
        need(command <= 13, "unknown state command")
        need(command not in seen, "duplicate state command")
        seen.add(command)
        need(flags in (0, 192), "unproven state width flags")
        width = 1 if flags == 0 else 4
        need(offset + width <= len(data), "truncated state argument")
        value = int.from_bytes(data[offset : offset + width], "little")
        need(width != 4 or value >= 256, "noncanonical wide state argument")
        rows.append(
            {"offset": start, "command": command, "width": width, "value": value}
        )
        offset += width
    raise TireAlphaError("missing state terminator")


def load_proofs():
    return {name: (AREA / (name + ".json")).read_bytes() for name in PROOFS}


def validate_proofs(proofs):
    need(set(proofs) == set(PROOFS), "missing or extra encoding proof")
    result = []
    for name, (start, end, pin, byte_pin) in PROOFS.items():
        raw = proofs[name]
        need(
            common.sha256(raw) == pin,
            "native encoding proof identity mismatch: " + name,
        )
        proof = json.loads(raw)
        need(
            proof["source_sha256"] == EXECUTABLE_SHA and not proof["error"],
            "encoding proof source/completion mismatch",
        )
        if name == "test-packing-scalar":
            need(
                proof.get("analysis_scope") == "scalar_interval"
                and proof["pseudocode"] is None
                and not proof["decompilation_completed"],
                "scalar proof scope mismatch",
            )
        else:
            need(proof["decompilation_completed"], "encoding proof completion mismatch")
        data = bytearray()
        for i, row in enumerate(proof["assembly"]):
            match = re.fullmatch(r"([0-9a-f]{8}) ([0-9a-f]{8}) (.+)", row)
            need(
                match is not None and int(match[1], 16) == start + 4 * i,
                "noncontiguous proof assembly",
            )
            data.extend(bytes.fromhex(match[2]))
        need(
            len(data) == end - start and common.sha256(data) == byte_pin,
            "encoding proof instruction bytes mismatch",
        )
        result.append(
            {
                "name": name,
                "virtual_start": start,
                "virtual_end_exclusive": end,
                "bytes": len(data),
                "bytes_sha256": byte_pin,
                "analysis_sha256": pin,
                "source_executable_sha256": EXECUTABLE_SHA,
                "analysis": (
                    "ordinary Ghidra CLI, contiguous scalar interval only; enclosing function incomplete"
                    if name == "test-packing-scalar"
                    else "ordinary Ghidra CLI, complete MIPS standard-subset function; static, not execution"
                ),
            }
        )
    return result


def decode_gs_alpha(value):
    """Decode GS ALPHA selectors (PCSX2 GSRegs.h), keeping integer alpha units explicit."""
    need(
        type(value) is int and value >= 0 and value & ~0xFF000000FF == 0,
        "unknown GS ALPHA bits",
    )
    selectors = [(value >> shift) & 3 for shift in (0, 2, 4, 6)]
    need(all(selector < 3 for selector in selectors), "reserved GS ALPHA selector")
    colors, alpha = ["Cs", "Cd", "0"], ["As", "Ad", "FIX"]
    a, b, c, d = selectors
    equation = f"({colors[a]} - {colors[b]}) * {alpha[c]} + {colors[d]}"
    return {
        "register_value": value,
        "A": colors[a],
        "B": colors[b],
        "C": alpha[c],
        "D": colors[d],
        "FIX": (value >> 32) & 255,
        "rgb_equation_normalized_alpha": equation,
        "integer_alpha_divisor": 128,
    }


def native_renderer_passes(proofs):
    """Read the native packet immediates from the complete pinned preparation routine."""
    validate_proofs(proofs)
    proof = json.loads(proofs["renderer-preparation"])
    instructions = {
        int(row.split()[0], 16): bytes.fromhex(row.split()[1])
        for row in proof["assembly"]
    }

    def immediate(address, prefix):
        word = int.from_bytes(instructions[address], "little")
        need(word >> 16 == prefix, "changed native ALPHA immediate instruction")
        return word & 65535

    register = immediate(0x3BEF4C, 0x2402)
    need(register == 0x42, "native ALPHA register mismatch")
    base = decode_gs_alpha(immediate(0x3BEF38, 0x2403))
    reflection = decode_gs_alpha(immediate(0x3BEF44, 0x2403))
    return {
        "register": register,
        "register_name": "ALPHA_1",
        "scope": "Configured ALPHA registers; draw ABE and full texture-to-framebuffer alpha path are not established.",
        "base_texture_index": 0,
        "base": base,
        "reflection_texture_index": 1,
        "reflection": reflection,
        "selector_reference": {
            "url": "https://raw.githubusercontent.com/PCSX2/pcsx2/master/pcsx2/GS/GSRegs.h",
            "accessed": "2026-10-15",
            "sections": ["GS_REG_ALPHA_1", "GS_ALPHA_BITS", "REG64_(GIFReg, ALPHA)"],
            "scope": "Register identity and bit selectors, not evidence that MC3 executed.",
        },
    }


def tire_alpha_translation():
    """Source-bound alpha, VU lookup and GS blend contract used by both viewers."""
    from mc3_tire_vu import reflection_contract

    shader = (AREA / "tire.shadert").read_bytes()
    policy = tire_alpha_policy(shader)
    need(common.sha256(shader) == SHADER_SHA, "native shader identity mismatch")
    passes = native_renderer_passes(load_proofs())
    vu = reflection_contract()
    return {
        "policy": "native-ps2-tire-reflection-v2",
        "alpha_test": policy["alpha_test"],
        "base_pass_rgb_equation": "(0 - 0) * As + Cs = Cs",
        "reflection_pass_rgb_equation": passes["reflection"][
            "rgb_equation_normalized_alpha"
        ],
        "base_rgbaq_alpha": vu["base_rgbaq_alpha"],
        "reflection_rgbaq": vu["reflection_rgbaq"],
        "alpha_encoding": "ps2-clut-u8-doubled-in-png",
        "native_normal_attribute": "_MC3_NATIVE_NORMAL",
        "generated_uv": vu["generated_uv"],
        "illumination": "native-sd-midnight-garage-v1; recovered environment capture, panorama and 256-to-64 GS copy",
        "source": {
            "shader_sha256": SHADER_SHA,
            "executable_sha256": EXECUTABLE_SHA,
            "receipt": "research/evidence/midnight-club-3-remix/previews/tire-alpha-native/native-alpha.json",
            "vu_receipt": "research/evidence/midnight-club-3-remix/previews/tire-alpha-native/vu-reflection.json",
        },
        "claim_limits": [
            "Native alpha, projected-normal lookup and additive RGB arithmetic use the recovered static San Diego garage environment.",
            "Original image alpha is preserved and recovered per texel before filtering; base tire coverage stays opaque.",
            "The authored garage pipeline is translated portably; original runtime animation, cycle-exact GS rasterization and all hardware floating-point precision modes are not emulated.",
            "Static shader/executable evidence does not establish observed game execution.",
        ],
    }
