"""Source-bound contracts for MC3's specular2_dc VU tire program.

This decodes the embedded MPG stream and checks the specific alpha/cull instruction
paths. It is not a VU emulator and does not claim observed PS2 execution.
"""

import hashlib
import json
from pathlib import Path
import struct

import vu1_decode as vu

AREA = (
    Path(__file__).resolve().parents[1]
    / "research/evidence/midnight-club-3-remix/previews/tire-alpha-native"
)
FIXTURE = AREA / "vu-reflection.json"
SELECTED_PCS = [
    140,
    141,
    146,
    150,
    154,
    162,
    163,
    164,
    165,
    166,
    167,
    168,
    169,
    170,
    171,
    174,
    176,
    177,
    179,
    181,
    185,
    191,
    796,
    799,
    807,
    830,
    840,
    960,
    964,
    968,
    969,
    974,
    982,
    987,
]
SELECTED_SHA = "584baab4bf5febaad8bb06642d2cd0071e1e55305d44f7c7d81e8a1392798273"
EXECUTABLE_SHA = "1b237ade5cafaf8ddd9fd049f40d81eb46f38f2600a8f1c7273d4f836973fe9d"
INTERVALS = {
    "tire_scale_call": (
        0x3BF124,
        0x3BF138,
        "1a690ac0266f86b5775549292b0c49c29c9ff194824e86678e31307f58db340a",
    ),
    "fov_projection_prefix": (
        0x5311F8,
        0x531270,
        "70245ff3b02a531a259ffab7cf0a46a9f68ba1d082e36ed8e9fee5bbf75d2fe8",
    ),
    "microprogram": (
        0x5FE010,
        0x600210,
        "2f66787c321a43f7325414c37a2c3a31416cb57dd76ae1e0efff4b5e7cb3bb71",
    ),
    "light_upload": (
        0x2AE224,
        0x2AE340,
        "2d770b9fc96bfbf9854edd0212c2378d47384d0ac147b4e42c2fd9a7f2c3269b",
    ),
    "cull_table": (
        0x615E30,
        0x615E33,
        "d175febefc6654f1f9d8205db93cc55f45be562bca501d893a21a86860fdf98d",
    ),
    "registration": (
        0x3B59A8,
        0x3B59BC,
        "cf001d20aa8011fe3cd754141c83691e3021b05d49509d720db3a89055501ded",
    ),
    "reflection_constants": (
        0x3BED50,
        0x3BEDB0,
        "b132d1afaf50fe9fd96f21e3aac3b4eb589590b11eedc325b61eea8c5f5e7129",
    ),
    "program_name": (
        0x65DE32,
        0x65DE3F,
        "4974f6fcbcdc1d2957e26370cfaa8e3f7c0de66149cc4cab51b515b165627964",
    ),
    "texture_transform": (
        0x2AF490,
        0x2AF7B8,
        "7c2fe4e447afc52bcdb88a9ea03a9ca4e32aa7775f5e832970df3b0a6b48b43b",
    ),
    "texture_upload": (
        0x2AE178,
        0x2AE21C,
        "7f960f538572d6bdddc442d81e3b6138e44aaee5655fe9ae138a33393b29a701",
    ),
    "tire_scale_update": (
        0x3B5FA0,
        0x3B6040,
        "50f762af9992d6a9f22569e167b3e7e084e2570ba48a02dec85efcb3c8a919cd",
    ),
    "gs_common_packet": (
        0x61C3C0,
        0x61C400,
        "277846b4cbb6f454e366c0339142557b2fefe4fd09b378ea08c61d48531f4661",
    ),
    "gs_common_enqueue": (
        0x529914,
        0x529984,
        "b3401be2708aa3236a81aba945b08b6967d1787750999bc952f950be0dd9c269",
    ),
}


def need(condition, message):
    if not condition:
        raise ValueError(message)


def unpack_microprogram(packet):
    """Decode a DMA reference payload containing NOPs and contiguous MPG uploads."""
    need(
        len(packet) >= 16 and len(packet) % 16 == 0,
        "invalid tire microprogram packet size",
    )
    qwc = struct.unpack_from("<I", packet)[0]
    need(qwc >> 28 == 6 and qwc & 0x0FFF0000 == 0, "invalid tire DMA header")
    need((qwc & 65535) * 16 + 16 == len(packet), "tire DMA QWC mismatch")
    need(packet[4:16] == bytes(12), "unexpected tire DMA header fields")
    result, offset = {}, 16
    while offset < len(packet):
        word = struct.unpack_from("<I", packet, offset)[0]
        offset += 4
        if word == 0:
            continue
        need(word >> 24 == 0x4A, "unexpected VIF command in tire microprogram")
        start, count = word & 65535, (word >> 16) & 255
        count = count or 256
        need(
            start + count <= 2048 and offset + count * 8 <= len(packet),
            "invalid MPG extent",
        )
        for pc in range(start, start + count):
            need(pc not in result, "overlapping MPG upload")
            result[pc] = struct.unpack_from("<II", packet, offset)
            offset += 8
    need(result and set(result) == set(range(len(result))), "noncontiguous MPG layout")
    return result


def source_parts():
    fixture = json.loads(FIXTURE.read_text())
    need(
        fixture["executable_sha256"] == EXECUTABLE_SHA,
        "VU fixture executable identity mismatch",
    )
    need(
        set(fixture["source_intervals"]) == set(INTERVALS),
        "VU fixture interval set mismatch",
    )
    result = {}
    for key, (start, end, pin) in INTERVALS.items():
        row = fixture["source_intervals"][key]
        need(
            (row["start"], row["end"], row["sha256"]) == (start, end, pin),
            "VU fixture interval identity mismatch",
        )
        if key == "microprogram":
            need(
                row["selected_instruction_sha256"] == SELECTED_SHA,
                "changed VU instruction proof pin",
            )
            proof = row["selected_instruction_proof"]
            need(
                len(proof) == len(SELECTED_PCS)
                and all(
                    r["address"] == 0x5FE028 + r["pc"] * 8 + (r["pc"] // 256) * 8
                    for r in proof
                ),
                "changed VU instruction proof locations",
            )
            result[key] = {r["pc"]: (r["lower"], r["upper"]) for r in proof}
            need(
                sorted(result[key]) == SELECTED_PCS,
                "changed VU instruction proof scope",
            )
        else:
            result[key] = bytes.fromhex(row["hex"])
    return result


def check_word(data, address, start, word, message):
    need(struct.unpack_from("<I", data, address - start)[0] == word, message)


def derive(parts):
    """Check native instruction paths before accepting their source interval pins."""
    need(set(parts) == set(INTERVALS), "missing VU source interval")
    pairs = (
        parts["microprogram"]
        if isinstance(parts["microprogram"], dict)
        else unpack_microprogram(parts["microprogram"])
    )
    if not isinstance(parts["microprogram"], dict):
        need(len(pairs) == 1081, "changed tire MPG layout")
    # VU28..31 directional light RGB+ambient upload: W=(0,0,0,1).
    light, start = parts["light_upload"], INTERVALS["light_upload"][0]
    for address, word in [
        (0x2AE26C, 0x3C036C04),
        (0x2AE270, 0x3463001C),
        (0x2AE2C0, 0xAC60000C),
        (0x2AE2E4, 0xACA0000C),
        (0x2AE304, 0xAC80000C),
        (0x2AE2C4, 0x3C013F80),
        (0x2AE2C8, 0x44811800),
        (0x2AE318, 0xE4C3000C),
    ]:
        check_word(light, address, start, word, "changed native light alpha upload")
    # These exact paired instructions connect loaded light W -> material W -> RGBAQ.
    base = {
        0xA3: (0x01EA001C, 0x019171BC),
        0xA4: (0x01EB001D, 0x019178BD),
        0xA5: (0x01EC001E, 0x0180844B),
        0xA6: (0x01ED001F, 0x01C0CE5C),
        0xA7: (0x01F2002A, 0x01F651BC),
        0xA8: (0x80052872, 0x01F658BD),
        0xA9: (0x800738F2, 0x01F660BE),
        0xAA: (0x80015AF4, 0x01E06D8B),
        0xAE: (0x80355BFD, 0x01E0B5D7),
        0xB3: (0x800637F2, 0x01F2BD2A),
        0xB9: (0x0265C87E, 0x01F9A17C),
        0xBF: (0x03E7C800, 0x01D739BC),
    }
    for pc, pair in base.items():
        need(pairs[pc] == pair, "changed native base alpha arithmetic")
    reflection = {
        0x3C0: (0x800106BD, 0x01E00093),
        0x3C4: (0x01860880, 0x00201087),
        0x3C8: (0x038437FE, 0x01E211AB),
        0x3C9: (0x01E10034, 0x000002FF),
        0x3CE: (0x03841FFE, 0x01E130EA),
        0x3D6: (0x5003000A, 0x01E3197C),
        0x3DB: (0x03E41FF9, 0x01E3317C),
    }
    for pc, pair in reflection.items():
        need(pairs[pc] == pair, "changed native reflection RGBA arithmetic")
    for pc, pair in {
        0x31C: (0x10030080, 0x000002FF),
        0x31F: (0x50030039, 0x000002FF),
        0x327: (0x10040040, 0x000002FF),
        0x33E: (0x800108F2, 0x0105182C),
        0x348: (0x0A260FFB, 0x0105182C),
    }.items():
        need(pairs[pc] == pair, "changed native cull arithmetic")
    need(
        parts["cull_table"] == bytes([0, 128, 192]),
        "changed native cull selector table",
    )
    for pc, pair in {
        0x8C: (0x3C000000, 0x8040295E),
        0x96: (0x01F30035, 0x01B609BC),
        0x8D: (0x01E30016, 0x00400462),
        0x92: (0x8000033C, 0x01D1CD9A),
        0x9A: (0x22000000, 0x0193A1BC),
        0xA2: (0x100728A9, 0x01E0864B),
        0xAB: (0x0385C87F, 0x01808E5C),
        0xB0: (0x8131CB3D, 0x01C031BF),
        0xB1: (0x8076CB3C, 0x01D52E69),
        0xB5: (0x80798B3D, 0x01D5C97D),
    }.items():
        need(pairs[pc] == pair, "changed native generated UV arithmetic")
    packet = parts["gs_common_packet"]
    tag, register = struct.unpack_from("<QQ", packet)
    need(
        tag == 0x1000000000008003 and register == 14, "changed native common GS packet"
    )
    need(
        struct.unpack_from("<QQ", packet, 16) == (0, 0x1A), "changed native PRMODECONT"
    )
    need(
        struct.unpack_from("<QQ", packet, 48) == (0x8000000000, 0x3B),
        "changed native TEXA expansion",
    )
    # The registry binds literal specular2_dc at 0065de32 to this DMA packet.
    for address, word in [
        (0x3B59A8, 0x3C040066),
        (0x3B59AC, 0x3C050060),
        (0x3B59B0, 0x2484DE32),
        (0x3B59B4, 0x0C0ABAB0),
        (0x3B59B8, 0x24A5E010),
    ]:
        check_word(
            parts["registration"],
            address,
            INTERVALS["registration"][0],
            word,
            "changed native specular program registration",
        )
    need(parts["program_name"] == b"specular2_dc\0", "changed native VU program name")
    for address, word in [
        (0x3BED50, 0x3C0142FE),
        (0x3BED54, 0x44810000),
        (0x3BED60, 0x3C013DCC),
        (0x3BED64, 0x3421CCCD),
        (0x3BED68, 0x44810800),
        (0x3BEDA0, 0xE4410010),
        (0x3BED6C, 0x3C046C02),
        (0x3BED70, 0x34844034),
        (0x3BED90, 0xE4A00010),
        (0x3BED98, 0xE4400008),
        (0x3BEDA8, 0xE4400004),
        (0x3BEDAC, 0xAC40000C),
    ]:
        check_word(
            parts["reflection_constants"],
            address,
            INTERVALS["reflection_constants"][0],
            word,
            "changed native reflection RGBA constants",
        )
    for address, word in [
        (0x531224, 0x46006546),
        (0x531248, 0xE615019C),
        (0x531258, 0x3C013C0E),
        (0x53125C, 0x3421FA35),
        (0x531264, 0x4600AD42),
        (0x531268, 0x0C10728E),
    ]:
        check_word(
            parts["fov_projection_prefix"],
            address,
            INTERVALS["fov_projection_prefix"][0],
            word,
            "changed native FOV projection prefix",
        )
    for address, word in [
        (0x3BF128, 0x3C013F00),
        (0x3BF12C, 0x44816000),
        (0x3BF130, 0x0C0ED7E8),
    ]:
        check_word(
            parts["tire_scale_call"],
            address,
            INTERVALS["tire_scale_call"][0],
            word,
            "changed native tire scale call",
        )
    for address, word in [
        (0x3B5FB0, 0x3C0141C8),
        (0x3B5FB8, 0xC460019C),
        (0x3B5FBC, 0x3C013EB3),
        (0x3B5FC0, 0x34213333),
        (0x3B5FCC, 0x3C014220),
        (0x3B5FD4, 0x46016042),
        (0x3B5FD8, 0x46020003),
        (0x3B5FDC, 0x46016301),
        (0x3B5FE0, 0x46006302),
        (0x3B5FE8, 0x460C0840),
    ]:
        check_word(
            parts["tire_scale_update"],
            address,
            INTERVALS["tire_scale_update"][0],
            word,
            "changed native tire FOV scale arithmetic",
        )
    proof_bytes = b"".join(struct.pack("<III", pc, *pairs[pc]) for pc in SELECTED_PCS)
    need(
        hashlib.sha256(proof_bytes).hexdigest() == SELECTED_SHA,
        "native VU instruction proof identity mismatch",
    )
    for key, data in parts.items():
        if key == "microprogram" and isinstance(data, dict):
            continue
        start, end, pin = INTERVALS[key]
        need(
            len(data) == end - start and hashlib.sha256(data).hexdigest() == pin,
            "native VU source interval identity mismatch: " + key,
        )
    return {
        "schema": 1,
        "microprogram": "specular2_dc",
        "program_pairs": 1081,
        "light_rgba_w": [0, 0, 0, 1],
        "base_rgbaq_alpha": 128,
        "base_alpha_expression": "min(0*Nx + 0*Ny + 0*Nz + 1, 1) * material_alpha(128)",
        "reflection_rgbaq": [127, 127, 127, 0],
        "reflection_rgb_modulation_divisor": 128,
        "reflection_alpha_role": "ALPHA_1=0x58 uses destination alpha; source alpha is zero and is not the RGB coefficient.",
        "PRMODECONT": 0,
        "TEXA": {"TA0": 0, "TA1": 128},
        "culling": {
            "selector_table": [0, 128, 192],
            "enable_mask": 128,
            "winding_mask": 64,
            "implementation": "VU signed screen area marks ADC suppressed triangles",
        },
        "claim_limits": [
            "Static executable arithmetic, not observed PS2 execution.",
            "Texture/TEX0/GS/framebuffer behavior and runtime specular texture generation are separate evidence.",
            "VU clipping, status flags and exact floating-point rounding are not generally emulated.",
        ],
    }


def contract():
    return derive(source_parts())


def relevant_instructions():
    pairs = source_parts()["microprogram"]
    return {
        str(pc): vu.render_pair(*pairs[pc])
        for pc in [
            0xA7,
            0xA8,
            0xA9,
            0xAA,
            0xAE,
            0xB3,
            0xB9,
            0x3C0,
            0x3C4,
            0x3C9,
            0x3CE,
            0x3D6,
            0x3DB,
        ]
    }


def from_executable(executable):
    """Rederive every retained VU/light interval from the original ELF load segment."""
    need(
        hashlib.sha256(executable).hexdigest() == EXECUTABLE_SHA,
        "native VU executable identity mismatch",
    )
    need(executable[:7] == b"\x7fELF\x01\x01\x01", "unsupported native VU ELF")
    phoff = struct.unpack_from("<I", executable, 28)[0]
    width, count = struct.unpack_from("<HH", executable, 42)
    need(
        width >= 32 and count <= 128 and phoff + width * count <= len(executable),
        "invalid native VU ELF segments",
    )
    result = {}
    for key, (start, end, _) in INTERVALS.items():
        candidates = []
        for i in range(count):
            kind, offset, address, _, size = struct.unpack_from(
                "<IIIII", executable, phoff + i * width
            )
            if kind == 1 and address <= start < end <= address + size:
                need(
                    offset + size <= len(executable), "truncated native VU ELF segment"
                )
                candidates.append(
                    executable[offset + start - address : offset + end - address]
                )
        need(len(candidates) == 1, "missing or ambiguous native VU ELF interval")
        result[key] = candidates[0]
    retained = source_parts()
    decoded = unpack_microprogram(result["microprogram"])
    need(
        {pc: decoded[pc] for pc in SELECTED_PCS} == retained["microprogram"],
        "native VU instruction fixture differs from executable",
    )
    need(
        all(result[k] == retained[k] for k in result if k != "microprogram"),
        "native VU fixture differs from executable",
    )
    wheel_culling_from_executable(executable)
    return derive(result)


TIRE_PPF_SHA = "1f7586c6ce7382fc75d13dc27d7383c60e4e4ea999955f8020ca13888dbf1e77"
CACHED_TRANSFORM = [0.5, 0, 0, 0, 0, 0.5, 0, 0, 0.5, 0.5, 1, 0, 0, 0, 0, 1]


def from_tire_ppf(data):
    """Rederive every native tire's texture mode and cached UV transform.

    Slot offsets are PF05-relative, material offsets are absolute, and serialized
    animation pointers use the model's own serialized base. Those namespaces must
    not be interchanged.
    """
    from mc3_wheels import ppf_page, read_page_model

    need(len(data) >= 8 and data[:4] == b"pf05", "invalid native tire PPF header")
    count = struct.unpack_from("<I", data, 4)[0]
    need(count == 98, "changed native tire page count")
    alpha_max, slots = 0, 0
    for index in range(count):
        page = ppf_page(data, index)
        model = read_page_model(data, page)
        need(len(model["materials"]) == 1, "changed native tire material count")
        material = model["materials"][0]["ppf_file_offset"]
        need(
            tuple(data[material + 33 : material + 35]) == (0x30, 2),
            "changed native tire texture mode",
        )
        delta = model["model_file_offset"] - model["serialized_base"]

        def pointer(address, size):
            offset = address + delta
            need(
                0 <= offset <= len(data) - size,
                "native tire animation pointer outside carrier",
            )
            return offset

        animation = pointer(struct.unpack_from("<I", data, material + 28)[0], 24)
        fields = struct.unpack_from("<6I", data, animation)
        matrix = list(struct.unpack_from("<16f", data, pointer(fields[0], 64)))
        need(matrix == CACHED_TRANSFORM, "changed native tire cached UV transform")
        need(
            fields[5] == 0 and all(fields[1:5]),
            "changed native tire transform parameter set",
        )
        values = [
            struct.unpack_from("<f", data, pointer(address, 24) + 16)[0]
            for address in fields[1:5]
        ]
        need(values == [0.5] * 4, "changed native tire transform parameter value")
        need(len(model["texture_slots"]) == 3, "changed native tire LOD texture count")
        for texture in model["texture_slots"].values():
            offset = page["offset"] + texture["slot_offset"]
            value = struct.unpack_from("<Q", data, offset + 16)[0]
            psm, tcc, tfx, cpsm = (
                (value >> 20) & 63,
                (value >> 34) & 1,
                (value >> 35) & 3,
                (value >> 51) & 15,
            )
            need(
                (psm, tcc, tfx, cpsm) == (19, 1, 0, 0),
                "changed native tire TEX0 alpha mode",
            )
            need(
                1 << ((value >> 26) & 15) == texture["width"]
                and 1 << ((value >> 30) & 15) == texture["height"],
                "native tire TEX0 dimensions mismatch",
            )
            slots += 1
            # PF05 palette decoding doubles each native 0..128 CLUT alpha byte.
            # This corpus never saturates, so the exact native maximum is recoverable.
            exported_alpha = texture["rgba"][3::4]
            need(
                all(value % 2 == 0 for value in exported_alpha),
                "unexpected saturated native tire alpha",
            )
            alpha_max = max(alpha_max, max(exported_alpha) // 2)
    need(
        hashlib.sha256(data).hexdigest() == TIRE_PPF_SHA,
        "native tire PPF identity mismatch",
    )
    need(slots == 294, "changed native tire texture count")
    return {
        "source_sha256": TIRE_PPF_SHA,
        "pages": count,
        "texture_slots": slots,
        "TEX0": {"PSM": 19, "TCC": 1, "TFX": 0, "CPSM": 0},
        "native_palette_alpha_max": alpha_max,
        "cached_uv_transform": CACHED_TRANSFORM,
        "texture_parameter_values": [0.5] * 4,
        "texture_alpha_equation": "framebuffer_alpha = (native_palette_alpha * 128) >> 7",
        "TEXA": "CPSM=PSMCT32; native CLUT RGBA alpha is used without TEXA expansion",
        "claim_limits": [
            "Source tire pages and cached default transform; runtime scale updates depend on viewport state.",
            "Framebuffer precision/GS rounding and runtime texture contents are separate evidence.",
        ],
    }


def reflection_contract():
    """Public contract for alpha/UV translation; all retained native code is pinned."""
    result = contract()
    result["generated_uv"] = {
        "normal": "native signed VIF normal XYZ divided by 128; do not normalize or remove ADC X bit",
        "position_clip": "P = MVP * vec4(position, 1)",
        "normal_clip": "N = MVP * vec4(native_normal, 0)",
        "ST": "(scale * (N.xy + 0.1 * P.xy) + vec2(0.5)) / P.w",
        "Q": "1 / P.w",
        "sample_uv": "ST / Q; preserve perspective interpolation",
        "cached_scale": 0.5,
        "runtime_scale_expression": "0.175 + 0.325 * ((vertical_fov_degrees - 25) / 40)",
        "runtime_scale_source": "Viewport +0x19c stores vertical FOV degrees before pi/360 tangent projection in 005311f8 scalar prefix.",
    }
    return result


WHEEL_PROGRAMS = {
    "builtin-normal": (
        6210800,
        13488,
        "9d30b140652bb9400499dd7e450f17618de7ca45d52237b58add56274ec11f71",
        "a6a292c429922cc9cc430966965f307ffc0c204e381d2face73e8275a292278f",
    ),
    "builtin-alternate": (
        6198800,
        12000,
        "93ede46a83bb62f1995f1e555a48bd601f29963af88603d019f66b19b140462a",
        "22555cd3c9540795d7b4ba445083f61c00aa17cf3866813541e8c6e556bfb73d",
    ),
    "texgen_fresnel_dc": (
        6291984,
        8320,
        "03f0608dcd7bb939aa19b79a544dd7a549cfc50a23b1df91895a385182d7dcf8",
        "ef55242a552f4d7bd5e82ebbd9078e59f3fd565534a692393fd088db803a13fb",
    ),
    "light_texgen_dc": (
        6351264,
        8384,
        "43519fa155ab18e218a199ad8aa30325fff6faf8e7e32aa76233abd3f6eea7fa",
        "c9912c06af9772c8e80aa9984548962a30683c44845c88c876201378c031ba36",
    ),
}
WHEEL_INTERVALS = {
    "builtin_binding": (
        2772528,
        2772796,
        "93642cbac04b97aa43b1d679fc2e2928a7bb029124dafb824c25268bec1aa7c5",
    ),
    "custom_registration": (
        3889340,
        3889596,
        "4800feb530d9d30ba755bb53c81485e43eac6c9938209d392c277f0e5a592f09",
    ),
    "vehicle_cull_caller": (
        3172980,
        3173028,
        "464e5e606556c074d00787c697ee203a12cc43ee0934e24f8637e5a82f287e30",
    ),
    "cull_state_upload": (
        2807908,
        2808144,
        "1d65b990d58cb98942d6a7a91316ffa5dcb0cd05da3e2beff6a6cdb93d1528aa",
    ),
}
WHEEL_INTERVALS["initial_registry"] = (
    0x615F98,
    0x615FA4,
    "024487326c59687f9c8de677a9eb7c5335ec5eca582bf3010f438972aa621a5c",
)
RIM_PAGES = [
    0,
    9,
    10,
    11,
    12,
    13,
    14,
    15,
    16,
    17,
    18,
    19,
    22,
    23,
    24,
    42,
    43,
    44,
    45,
    47,
    48,
    49,
    51,
    62,
    63,
    64,
    65,
    66,
    67,
    68,
    69,
    70,
    82,
    83,
    91,
    92,
    93,
    96,
    103,
    104,
    115,
    116,
    117,
    118,
    119,
    120,
    121,
    122,
    129,
    136,
    137,
    138,
    139,
    140,
    141,
    142,
    143,
    144,
    154,
    155,
    156,
    157,
    158,
    159,
    160,
    161,
    162,
    167,
    168,
    169,
    171,
    172,
    173,
    174,
    175,
    176,
    177,
    178,
    179,
    180,
    181,
    182,
    183,
    184,
    185,
    186,
    188,
    189,
    190,
    191,
    192,
]


def wheel_culling_proof(proof=None):
    """Validate bounded proof cells without retaining the private VU packets."""
    proof = json.loads(FIXTURE.read_text())["wheel_culling"] if proof is None else proof
    need(
        proof["source_executable_sha256"] == EXECUTABLE_SHA,
        "wheel cull executable identity mismatch",
    )
    need(
        set(proof["native_intervals"]) == set(WHEEL_INTERVALS),
        "wheel cull interval set mismatch",
    )
    for name, (start, end, pin) in WHEEL_INTERVALS.items():
        row = proof["native_intervals"][name]
        need(
            (row["start"], row["end"], row["sha256"]) == (start, end, pin),
            "wheel cull interval pin mismatch",
        )
    need(
        proof["custom_registration_initial_index"] == 1,
        "wheel custom registry index mismatch",
    )
    need(
        proof["caller_selector"] == 2
        and proof["selector_table"] == {"address": 0x615E30, "values": [0, 128, 192]},
        "wheel cull selector mismatch",
    )
    need(
        {r["name"] for r in proof["programs"]} == set(WHEEL_PROGRAMS)
        and len(proof["programs"]) == len(WHEEL_PROGRAMS),
        "wheel cull program set mismatch",
    )
    roles = [
        "load_flags",
        "cull_mask",
        "cull_test",
        "skip_when_disabled",
        "orientation_mask",
        "orientation_test",
        "area_product_a",
        "area_product_b",
        "signed_area",
        "sign_status",
        "adc_mask",
        "adc_merge",
        "adc_write",
    ]
    for program in proof["programs"]:
        address, size, pin, selected_pin = WHEEL_PROGRAMS[program["name"]]
        need(
            (
                program["address"],
                program["bytes"],
                program["sha256"],
                program["selected_instruction_sha256"],
            )
            == (address, size, pin, selected_pin),
            "wheel cull program pin mismatch",
        )
        expected_index = (
            0
            if program["name"].startswith("builtin-")
            else (8 if program["name"] == "texgen_fresnel_dc" else 9)
        )
        need(
            program["native_program_indices"] == [expected_index],
            "wheel cull native program index mismatch",
        )
        rows = program["selected_instruction_proof"]
        need(
            [row["role"] for row in rows] == roles,
            "wheel cull instruction role mismatch",
        )
        need(
            all(
                r["address"] == address + 24 + r["pc"] * 8 + (r["pc"] // 256) * 8
                for r in rows
            ),
            "wheel cull instruction location mismatch",
        )
        need(
            [r["lower"] for r in rows[:3]] == [0x09010022, 0x10030080, 0x800118F4],
            "changed wheel native cull gate",
        )
        for row in rows[6:8]:
            upper = vu.decode_upper(row["upper"])
            need(
                upper["op"] == "muly" and upper["dest"] == "x",
                "changed wheel signed area products",
            )
        upper = vu.decode_upper(rows[8]["upper"])
        need(
            upper["op"] == "sub" and upper["dest"] == "x" and upper["fd"] == 0,
            "changed wheel signed area test",
        )
        need(
            rows[9]["lower"] >> 25 == 0x16 and rows[9]["lower"] & 0xFFFF == 2,
            "changed wheel sign status selection",
        )
        lower = vu.decode_lower(rows[-1]["lower"])
        need(lower["op"] == "isw" and lower["dest"] == "w", "changed wheel ADC write")
        raw = b"".join(
            struct.pack("<III", r["pc"], r["lower"], r["upper"]) for r in rows
        )
        need(
            hashlib.sha256(raw).hexdigest() == selected_pin,
            "wheel cull selected instruction identity mismatch",
        )
    need(
        proof["rim_ppf"]["selected_pages"] == RIM_PAGES,
        "wheel cull rim page coverage mismatch",
    )
    return proof


def wheel_culling_from_executable(executable):
    """Reproduce default/custom rim VU culling proof from the pinned original ELF."""
    need(
        hashlib.sha256(executable).hexdigest() == EXECUTABLE_SHA,
        "wheel cull source executable identity mismatch",
    )
    proof = wheel_culling_proof()
    phoff = struct.unpack_from("<I", executable, 28)[0]
    width, count = struct.unpack_from("<HH", executable, 42)

    def read(start, end):
        rows = []
        for i in range(count):
            kind, offset, address, _, size = struct.unpack_from(
                "<IIIII", executable, phoff + i * width
            )
            if kind == 1 and address <= start < end <= address + size:
                rows.append(
                    executable[offset + start - address : offset + end - address]
                )
        need(len(rows) == 1, "wheel cull source interval missing or ambiguous")
        return rows[0]

    for name, (start, end, pin) in WHEEL_INTERVALS.items():
        need(
            hashlib.sha256(read(start, end)).hexdigest() == pin,
            "wheel cull native interval mismatch: " + name,
        )
    need(
        struct.unpack("<I", read(0x615F98, 0x615F9C))[0] == 1,
        "wheel native custom registry index mismatch",
    )
    need(
        read(0x615E30, 0x615E33) == bytes([0, 128, 192]),
        "wheel cull native selector mismatch",
    )
    need(
        read(0x306A74, 0x306A78) == bytes.fromhex("02001624"),
        "wheel cull native caller selector mismatch",
    )
    for program in proof["programs"]:
        start = program["address"]
        packet = read(start, start + program["bytes"])
        need(
            hashlib.sha256(packet).hexdigest() == program["sha256"],
            "wheel cull native program identity mismatch",
        )
        pairs = unpack_microprogram(packet)
        for row in program["selected_instruction_proof"]:
            need(
                pairs[row["pc"]] == (row["lower"], row["upper"]),
                "wheel cull source selected instruction mismatch",
            )
    return proof


def from_rim_ppf(data, selected_pages=None):
    """Check every material of every stock-selected rim page inherits native culling."""
    from mc3_tire_alpha import decode_state_commands
    from mc3_wheels import ppf_page, read_page_model

    pages = RIM_PAGES if selected_pages is None else selected_pages
    need(pages == RIM_PAGES, "native rim selected page coverage mismatch")
    need(data[:4] == b"pf05", "invalid native rim PPF header")
    count, program_indices = 0, set()
    for index in pages:
        model = read_page_model(data, ppf_page(data, index))
        delta = model["model_file_offset"] - model["serialized_base"]
        for material in model["materials"]:
            offset = material["ppf_file_offset"]
            program = data[offset + 12]
            need(program in (0, 8, 9), "unproven native rim microprogram")
            program_indices.add(program)
            start = struct.unpack_from("<I", data, offset + 8)[0] + delta
            need(0 <= start < len(data), "native rim state pointer outside carrier")
            end = start
            for _ in range(14):
                need(end < len(data), "truncated native rim state")
                header = data[end]
                end += 1
                if header == 255:
                    break
                end += 4 if header & 0xC0 else 1
            commands = decode_state_commands(data[start:end])
            need(
                all(row["command"] != 0 for row in commands), "native rim cull override"
            )
            count += 1
    need(
        hashlib.sha256(data).hexdigest()
        == "9b5b2f501696c2ca90d2bde01dc90cc8597335d18c5dabd1bd2ad941362f5da7",
        "native rim PPF identity mismatch",
    )
    need(
        count == 750 and program_indices == {0, 8, 9},
        "native rim material coverage mismatch",
    )
    return {
        "source_sha256": hashlib.sha256(data).hexdigest(),
        "selected_pages": list(pages),
        "material_states": count,
        "program_indices": sorted(program_indices),
        "cull_overrides": 0,
    }
