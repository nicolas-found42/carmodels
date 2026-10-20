"""Bounded original MC3 garage camera, sky and floor source contract.

This verifies static source joins and inputs, not original VU/GS execution.
"""

import hashlib
import json
import math
from pathlib import Path
import re
import struct

from mc3_pck import Pck
from mc3_specular_native import EXECUTABLE_SHA, need
from mc3_tire_vu import unpack_microprogram

EVIDENCE = (
    Path(__file__).resolve().parents[1] / "research/evidence/"
    "midnight-club-3-remix/previews/environment/native-scene.json"
)
RECEIPT_SHA = "af791353b79010b06367d5d48f835f726dc8af3029e3cd588f568c1fcdfac8a2"


def f32(value):
    return struct.unpack("<f", struct.pack("<f", value))[0]


def contract(proof=None):
    proof = json.loads(EVIDENCE.read_text()) if proof is None else proof
    encoded = json.dumps(proof, sort_keys=True, separators=(",", ":")).encode()
    need(
        hashlib.sha256(encoded).hexdigest() == RECEIPT_SHA,
        "native scene receipt changed",
    )
    need(
        proof["source_executable_sha256"] == EXECUTABLE_SHA,
        "native scene executable identity mismatch",
    )
    return {
        "camera": proof["camera_contract"],
        "floor": proof["floor_contract"],
        "sky_color": proof["sky_color"],
        "fx": proof["fx_contract"],
        "main_view_axis": proof["main_view_axis_contract"],
        "heading": proof["heading_contract"],
        "claim_limits": proof["claim_limits"],
    }


def from_executable(executable):
    """Re-derive every bounded scalar interval and selected original VU pair."""
    need(
        hashlib.sha256(executable).hexdigest() == EXECUTABLE_SHA,
        "native scene executable identity mismatch",
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
        need(len(matches) == 1, "missing native scene ELF interval")
        return matches[0]

    proof = json.loads(EVIDENCE.read_text())
    result = contract(proof)
    for interval in proof["intervals"].values():
        start, end = int(interval["start"], 16), int(interval["end"], 16)
        need(
            hashlib.sha256(read(start, end - start)).hexdigest() == interval["sha256"],
            "native scene scalar interval differs",
        )
    for pc, word in proof["selected_words"].items():
        need(
            struct.unpack("<I", read(int(pc, 16), 4))[0] == int(word, 16),
            "native scene selected instruction differs",
        )
    for program in proof["vu_programs"]:
        packet = read(int(program["address"], 16), program["bytes"])
        need(
            hashlib.sha256(packet).hexdigest() == program["sha256"],
            "native scene VU program differs",
        )
        pairs = unpack_microprogram(packet)
        for row in program["selected_pairs"]:
            need(
                pairs[int(row["pc"], 16)]
                == (int(row["lower"], 16), int(row["upper"], 16)),
                "native scene selected VU pair differs",
            )
    for table in proof["native_reset_tables"].values():
        actual = read(int(table["address_or_offset"], 16), table["bytes"])
        need(actual.hex() == table["hex"], "native scene reset table differs")
    return result


def sky_vertex_rgba(raw=(110, 110, 110, 255)):
    """Selected unlit builtin VU: raw color times float32 normalization/material."""
    factor = struct.unpack("<f", bytes.fromhex("ed7f803b"))[0]
    return [math.trunc(f32(f32(value * factor) * 128)) for value in raw]


def from_sources(city_data, props_data, garage_tune):
    """Re-read original source palette127, floor pass fields and authored pose."""
    proof = json.loads(EVIDENCE.read_text())
    contract(proof)
    for data, pin in [
        (city_data, proof["sky_source_sha256"]),
        (props_data, proof["props_source_sha256"]),
        (garage_tune, proof["source_shared_tune_sha256"]),
    ]:
        need(
            hashlib.sha256(data).hexdigest() == pin,
            "native scene source identity mismatch",
        )
    city, props = Pck(city_data), Pck(props_data)
    palette = city.pointer(city.u32(0xAC), 128 * 16)
    expected = proof["world_palette127"]
    need(
        palette == expected["palette_file_offset"],
        "native scene palette ownership differs",
    )
    entry = city_data[palette + 127 * 16 : palette + 128 * 16]
    need(entry.hex() == expected["entry"]["hex"], "native scene palette127 differs")
    rgba = [math.trunc(f32(value * 128)) for value in struct.unpack("<4f", entry)]
    need(
        rgba == expected["material128_ftoi0_rgba"],
        "native scene palette color arithmetic differs",
    )
    for item in proof["floor_passes"]:
        field = item["flags_combine_bytes"]
        start, length = int(field["address_or_offset"], 16), field["bytes"]
        need(
            props.data[start : start + length].hex() == field["hex"],
            "native scene floor pass input differs",
        )
    need(
        sky_vertex_rgba() == proof["sky_color"]["ftoi0_output_rgba"],
        "native scene sky color arithmetic differs",
    )
    text = garage_tune.decode("ascii")
    spot = re.findall(r"^\s*CarSpotsd\s+([^\r\n]+)", text, re.M)
    angle = re.findall(r"^\s*CarAnglesd\s+([^\r\n]+)", text, re.M)
    need(
        len(spot) == len(angle) == 1,
        "native scene authored car pose missing or duplicated",
    )
    position = [f32(float(value)) for value in spot[0].split()]
    need(len(position) == 3, "native scene authored car position differs")
    return {
        "palette127_material_rgba": rgba,
        "sky_vertex_rgba": sky_vertex_rgba(),
        "car_position_native": position,
        "car_angle_native": f32(float(angle[0])),
    }
