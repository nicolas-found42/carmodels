#!/usr/bin/env python3
"""Verify bounded static car-packet and VU instruction anchors.

This intentionally does not execute the original program or emulate VIF/VU/GIF/GS.
It asserts that the source files still match pinned hashes, then emits the
smallest source-supported trace plus explicitly unresolved semantic joins.
"""
from __future__ import annotations

import static_inputs
import argparse
import hashlib
import glob
import json
from pathlib import Path
import shutil
import struct
import subprocess
import sys
import zipfile
import zlib

DEFAULT_INPUT_BUNDLE = static_inputs.bundle_path()
FUNCTION_DIR = Path(".scratch/mesh/codex-root/decompile-dispatch-all-3837-02/functions")
VU_DIR = Path(".scratch/evidence/vu/private-work-016dac24781c4c9ea7c99aa0fa79c310")
TYPED_EXPORT = Path(".scratch/mesh/codex-audit/frontier-3845-01/types-t2/export-5454-po")

PINS = {
    "001288b0.c": "9e7d1c5ae7b1660549e3625a206eeee600268ce3b9c1e54ba72b73db27ed8764",
    "0021bc18.c": "d5573d86b5ee41ed717d7e8532360ef6d05f8d4f810c392d16f03c1d3cc6071d",
    "00129428.c": "5663afade6ed05882a6096911877ac45eb56c70ecfc08438fd5cc240c12700e0",
    "001297b8.c": "77acbbc5c52ab64cff11113541c6423d99ad2eec578b3fc616311d4bdf071ea4",
    "00128e88.c": "db45fd58871c3e44f227855cae71c6b3e9715e394c923d830c6a0520bdb3aae6",
    "overlay-5.s": "f5e195d23ec624026e31caae2c31d7af6cce10ec36158632f8624eeb640499d5",
    "overlay-6.s": "c19e1aff3bffba716e30e59e117a6266a4049d20f3c03781d6adc0b972745940",
    "overlay-0.s": "f5ade691d5c7de71be42e79adb5981f6b6441b451dc9ca9a181f1e1bda798fec",
    "overlay-1.s": "b6213e2c175bbb515cd5bbe86da393db65156847ebd233ca48148030acd0486a",
    "overlay-5.bin": "4d9dfc5c917746997f2bf4bd95068deca7fce6c3b447dc591fa74f537798ef0c",
}


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def overlay_residency(micro: bytes, vu_dir: Path, snapshot_label: str) -> dict[str, object]:
    """Exact byte-window comparison; residency does not establish execution."""
    rows = []
    for index in range(8):
        source_path = vu_dir / f"overlay-{index}.bin"
        source = source_path.read_bytes()
        hits = [offset for offset in range(0, len(micro) - len(source) + 1, 8)
                if micro[offset:offset + len(source)] == source]
        rows.append({"overlay": index, "source_path": str(source_path), "size": len(source),
                     "sha256": hashlib.sha256(source).hexdigest(),
                     "aligned_exact_offsets": [f"0x{x:04x}" for x in hits],
                     "exact_resident": bool(hits)})
    return {"snapshot": snapshot_label, "micro_memory_bytes": len(micro),
            "alignment_bytes": 8, "overlays": rows,
            "resident_overlay_indices": [row["overlay"] for row in rows if row["exact_resident"]],
            "nonresident_exact_window_indices": [row["overlay"] for row in rows if not row["exact_resident"]],
            "claim_limit": "Exact aligned byte residency only; it does not identify the active VU PC, program dispatch, or which overlay generated a packet."}


def linear_fit(features: list[list[float]], target: list[float]) -> dict[str, object] | None:
    """Small least-squares fit via normal equations; diagnostic, no dependencies."""
    if len(features) < 5 or len(features) != len(target):
        return None
    width = len(features[0])
    if any(len(row) != width for row in features):
        return None
    matrix = [[sum(row[i] * row[j] for row in features) for j in range(width)] +
              [sum(row[i] * y for row, y in zip(features, target))]
              for i in range(width)]
    for pivot in range(width):
        best = max(range(pivot, width), key=lambda row: abs(matrix[row][pivot]))
        if abs(matrix[best][pivot]) < 1e-10:
            return None
        matrix[pivot], matrix[best] = matrix[best], matrix[pivot]
        scale = matrix[pivot][pivot]
        matrix[pivot] = [value / scale for value in matrix[pivot]]
        for row in range(width):
            if row == pivot:
                continue
            scale = matrix[row][pivot]
            matrix[row] = [a - scale * b for a, b in zip(matrix[row], matrix[pivot])]
    coefficients = [matrix[i][-1] for i in range(width)]
    mean = sum(target) / len(target)
    total = sum((y - mean) ** 2 for y in target)
    if total < 1e-10:
        return None
    residual = sum((y - sum(c * x for c, x in zip(coefficients, row))) ** 2
                   for row, y in zip(features, target))
    return {"coefficients": coefficients, "r2": max(0.0, min(1.0, 1.0 - residual / total))}


def linear_r2(features: list[list[float]], target: list[float]) -> float | None:
    fit = linear_fit(features, target)
    return float(fit["r2"]) if fit else None


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input-bundle", type=Path, default=DEFAULT_INPUT_BUNDLE)
    parser.add_argument("--output", type=Path, default=Path("research/evidence/packet-continuation/static-trace.json"))
    parser.add_argument("--runtime-directory", type=Path, default=Path("research/evidence/continuation/runtime"))
    parser.add_argument("--runtime-output", type=Path, default=Path("research/evidence/packet-continuation/runtime-trace.json"))
    parser.add_argument("--race-state", type=Path, default=Path("research/evidence/continuation/runtime/sstates/SLES-51705 (37F695CD).94.p2s"))
    parser.add_argument("--race-dump", type=Path, default=Path("research/evidence/continuation/runtime/snaps/Ford Racing 2_SLES-51705_20261004182459.gs.zst"))
    parser.add_argument("--race-output", type=Path, default=Path("research/evidence/packet-continuation/race94-trace.json"))
    args = parser.parse_args()

    refresh_identity_path = Path("research/evidence/continuation/source-refresh/refresh-identity.json")
    refresh_identity = json.loads(refresh_identity_path.read_text(encoding="utf-8"))
    inventory_path = args.input_bundle / TYPED_EXPORT / "inventory.json"
    inventory_bytes = inventory_path.read_bytes()
    inventory_sha256 = hashlib.sha256(inventory_bytes).hexdigest()
    if inventory_sha256 != refresh_identity["inventory_sha256"]:
        raise ValueError("fresh typed inventory differs from refresh identity")
    typed_inventory = json.loads(inventory_bytes)
    typed_function = next(row for row in typed_inventory["functions"] if row["entry"] == "0021c3e0")
    raw_instruction_map = {row["address"]: row for row in typed_function["instructions"]}
    expected_cpu_instructions = {
        "0021c538": "andi v0,t8,0x8",
        "0021c53c": "beq v0,zero,0x0021c5a8",
        "0021c5c0": "lui v1,0x6e00",
        "0021c5c8": "lui a3,0x47c0",
        "0021c5d8": "lui at,0x3000",
        "0021c5dc": "addu t0,at,t0",
        "0021c600": "sw a3,0x14(v0)",
        "0021c618": "sw a3,0xc(v0)",
        "0021c61c": "sw a3,0x10(v0)",
    }
    cpu_instruction_checks = {
        address: {"expected_text": expected, "actual": raw_instruction_map.get(address), "pass": raw_instruction_map.get(address, {}).get("text") == expected}
        for address, expected in expected_cpu_instructions.items()
    }
    if not all(row["pass"] for row in cpu_instruction_checks.values()):
        raise ValueError("0021c3e0 raw instruction anchors changed")
    material_inventory_function = next(row for row in typed_inventory["functions"] if row["entry"] == "0021bc18")
    material_raw_instruction_map = {row["address"]: row for row in material_inventory_function["instructions"]}
    expected_material_instructions = {
        "0021bc64": "pextlb v1,zero,a2",
        "0021bc6c": "pextlh v1,zero,v1",
        "0021bc70": "pexew v1,v1",
        "0021bc8c": "vmulx.xyz vf2,vf2,vf3",
        "0021bcb4": "vmulx.w vf2,vf2,vf3",
    }
    material_instruction_checks = {
        address: {"expected_text": expected, "actual": material_raw_instruction_map.get(address),
                  "pass": material_raw_instruction_map.get(address, {}).get("text") == expected}
        for address, expected in expected_material_instructions.items()
    }
    if not all(row["pass"] for row in material_instruction_checks.values()):
        raise ValueError("0021bc18 raw material lane/mask anchors changed")
    cpu_decomp_path = args.input_bundle / TYPED_EXPORT / "decompilation/functions/0021c3e0.c"
    cpu_decomp = cpu_decomp_path.read_text(encoding="utf-8")
    cpu_decomp_sha256 = sha256(cpu_decomp_path)
    expected_cpu_decomp = [
        "puVar2[3] = 0x30000000;",
        "puVar2[10] = 0x5000001;",
        "puVar2[6] = 0x47c00000;",
        "puVar2[8] = iVar13 + 0x30000000;",
        "puVar2[0xb] = uVar16 + 1 | uVar15 | 0x6e000000;",
        "puVar2[4] = 0x47c00000;",
        "puVar2[5] = 0x47c00000;",
    ]
    cpu_decomp_literal_checks = {needle: needle in cpu_decomp for needle in expected_cpu_decomp}
    if not all(cpu_decomp_literal_checks.values()):
        raise ValueError("0021c3e0 typed source anchors changed")

    # VIF mode 1 adds the row word as a 32-bit integer. Confirm the following
    # float-bias subtraction yields the exact signed-byte/128 value for all 256 inputs.
    normal_scale_values = []
    for signed_byte in range(-128, 128):
        biased_bits = (0x47C00000 + signed_byte) & 0xFFFFFFFF
        biased_float = struct.unpack("<f", struct.pack("<I", biased_bits))[0]
        recovered = biased_float - 98304.0
        normal_scale_values.append(recovered)
        if recovered != signed_byte / 128.0:
            raise ValueError("signed V4-8 + 0x47c00000 - 98304 failed exact /128 identity")
    vif_source_path = args.input_bundle / ".scratch/mesh/codex-root/github-raw-Vif_Unpack.cpp"
    vif_source_sha256 = sha256(vif_source_path)
    vif_source = vif_source_path.read_text(encoding="utf-8")
    vif_literals = [
        "case 1:  dest = data + vif.MaskRow._u32[offnum]; break;",
        "const int usn    = !!vif.usn;",
        "UnpackFuncSet( V4, idx, mode, s, 0 )",
        "UnpackFuncSet( V4, idx, mode, u, 0 )",
    ]
    vif_literal_checks = {needle: needle in vif_source for needle in vif_literals}
    if not all(vif_literal_checks.values()):
        raise ValueError("pinned PCSX2 VIF signed/mode-1 anchors changed")

    callgraph_literals = {
        "00127fa8": [
            "FUN_0021d180(puVar6[-4],1,0,iVar1 + 0x1c,puVar6[1]);",
            "FUN_0021d180(puVar6[-4],0,0,iVar1 + 0x1c,puVar6[1]);",
        ],
        "0021d180": [
            "uVar7 = 0x100;",
            "if (param_2 == 0) {\n    uVar7 = 0;",
            "if ((*param_4 & 0x10000) == 0) {\n    FUN_0021bdf8();",
            "uVar7 = uVar7 | 8;",
            "FUN_0021bf28(uVar4,uVar3,puVar5,uVar2,param_5);",
        ],
        "0021bf28": [
            "if (((uVar5 & 8) == 0) || ((uVar2 & 0x10) == 0)) {\n    FUN_0021c3e0(uVar3);",
            "FUN_00128218(uVar3);",
        ],
        "00128218": [
            "param_5 = param_5 & 0x100;",
            "FUN_0021c3e0(param_1,param_2,uStack_80,param_4,param_5 | 2);",
            "FUN_0021cc88(0x89,0xffffffffff000000,param_1,param_4,auVar3._0_8_,uRam0028f180,param_5);",
            "FUN_0021c3e0(param_1,param_2,uStack_80,param_4,param_5 | 0x2a);",
        ],
    }
    callgraph_source_checks = {}
    callgraph_function_hashes = {}
    callgraph_decomp = {}
    for entry, needles in callgraph_literals.items():
        decomp_path = args.input_bundle / TYPED_EXPORT / f"decompilation/functions/{entry}.c"
        source_text = decomp_path.read_text(encoding="utf-8")
        callgraph_decomp[entry] = source_text
        callgraph_function_hashes[entry] = sha256(decomp_path)
        callgraph_source_checks[entry] = {needle: needle in source_text for needle in needles}
    if not all(all(rows.values()) for rows in callgraph_source_checks.values()):
        raise ValueError("typed CPU normal/light call graph anchors changed")

    material_setup_literals = {
        "0021ba50": ["puVar1[3] = 0x4c;", "puVar1[4] = param_2;"],
        "0021bb48": ["uVar2 = 0xc;", "if ((param_5 & 2) != 0) {\n    uVar2 = 0x4c;", "if (param_7 != 0) {\n    uVar2 = uVar2 | 0x10;"],
        "0021c3e0": ["if ((param_5 & 0x10) == 0) {", "if ((param_5 & 0x20) == 0) {\n          uVar12 = 0x44;", "FUN_0021ba50(piVar5,uVar12,3,1,0xffffffffff000000);"],
        "0021bf28": ["param_1 = (uVar2 & 1) << 5 | param_1;", "if ((uVar2 & 4) != 0) {\n    param_1 = param_1 | 1;", "if ((DAT_70003560 != 1.0) && (uVar5 = param_1 | 2, iRam0028f1d8 != 0))"],
        "0021d180": ["FUN_0021bf28(uVar4,uVar3,puVar5,uVar2,param_5);"],
        "00128e88": ["lVar12 = 0x4c;\n  if (param_7 != 0) {\n    lVar12 = 0x5c;"],
    }
    material_setup_sources = {}
    for entry, needles in material_setup_literals.items():
        path = args.input_bundle / TYPED_EXPORT / f"decompilation/functions/{entry}.c"
        source_text = path.read_text(encoding="utf-8")
        material_setup_sources[entry] = {
            "decompilation_sha256": sha256(path),
            "literal_checks": {needle: needle in source_text for needle in needles},
        }
    if not all(all(row["literal_checks"].values()) for row in material_setup_sources.values()):
        raise ValueError("typed material/primitive setup source anchors changed")

    selected_raw_instruction_addresses = {
        "00127fa8": ["001280c8", "001281c4"],
        "0021d180": ["0021d1a0", "0021d1a8", "0021d1cc", "0021d1dc", "0021d254"],
        "0021bf28": ["0021c080", "0021c084", "0021c098", "0021c0b4", "0021c0c8"],
        "00128218": ["00128358", "00128378", "00128398", "0012839c"],
    }
    callgraph_raw_instructions = {}
    for entry, addresses in selected_raw_instruction_addresses.items():
        function = next(row for row in typed_inventory["functions"] if row["entry"] == entry)
        by_address = {row["address"]: row for row in function["instructions"]}
        callgraph_raw_instructions[entry] = {address: by_address.get(address) for address in addresses}
        if any(row is None for row in callgraph_raw_instructions[entry].values()):
            raise ValueError(f"missing raw CPU call-path instruction in {entry}")

    normal_bias_candidate = {
        "function": "FUN_0021c3e0",
        "typed_export_inventory_sha256": inventory_sha256,
        "refresh_identity_executable_sha256": refresh_identity["executable_sha256"],
        "typed_decompilation_sha256": cpu_decomp_sha256,
        "raw_cpu_instruction_checks": cpu_instruction_checks,
        "raw_0021bc18_material_lane_checks": material_instruction_checks,
        "0021bc18_material_lane_interpretation": {
            "source_word_byte_order": "EE PEXT/PEXEW instructions at 0x0021bc64/6c/70 permute the base-color word into vector lanes; the 0x66000000 source word decodes to RGBA [0,0,0,102].",
            "scale_mask": "The typed _vmulbc rendering hides the destination mask. Raw EE vector instructions show vmulx.xyz at 0x0021bc8c on the header-bit-0-set arm and vmulx.w at 0x0021bcb4 on the bit-0-clear arm. Thus c01a selects W-only scaling; do not infer an all-four-lane scale.",
            "dynamic_limit": "The bit-0-clear arm multiplies W by DAT_70003560*FLOAT_0028f1e8. Their runtime values and producer-to-packet call are not joined, so this pins lane selection but not the numerical opacity factor.",
        },
        "decompilation_literal_checks": cpu_decomp_literal_checks,
        "path_condition": "param_5 & 8 == 0; the alternate bit-8-set branch emits the V4-8 REF before writing STROW and does not establish this normalization.",
        "static_command_order": [
            "STROW command 0x30000000",
            "STROW row words 0x47c00000, 0x47c00000, 0x47c00000, 0",
            "V3-16 REF command",
            "STMOD command 0x05000001 (mode 1)",
            "V4-8 REF command 0x6e000000 | (count << 16) | (selected_ADDR + 1); count occupies bits 16+, so USN bit 14 is clear",
        ],
        "pcsx2_vif_source": {
            "path": str(vif_source_path),
            "sha256": vif_source_sha256,
            "literal_checks": vif_literal_checks,
            "semantic_lines": {
                "mode_1_row_add": "writeXYZW mode 1 computes dest = data + vif.MaskRow._u32[offnum]",
                "signed_v4_unpack": "UNPACK_V4 routes to signed 8-bit input when USN is clear and the V4-8 unpack code is selected",
            },
        },
        "exact_numeric_identity": {
            "expression": "float32(bitcast_u32(0x47c00000 + signed_byte)) - 98304.0 == signed_byte / 128.0",
            "signed_byte_values_checked": 256,
            "minimum_result": min(normal_scale_values),
            "maximum_result": max(normal_scale_values),
            "all_exact": True,
        },
        "call_path_branch_evidence": {
            "typed_decompilation_sha256_by_function": callgraph_function_hashes,
            "typed_decompilation_literal_checks": callgraph_source_checks,
            "raw_instruction_records": callgraph_raw_instructions,
            "static_flow": [
                "FUN_00127fa8 calls FUN_0021d180 with param_2=1 for the first loop and param_2=0 for the second; this seeds flag bit 0x100 in the first call only.",
                "FUN_0021d180 sets flag bit 0x8 when its node record word at param_4 has bit 0x10000; it then calls FUN_0021bf28 with that flag set.",
                "FUN_0021bf28 selects FUN_00128218 when bit 0x8 and source header bit 0x10 are both set; otherwise it directly calls FUN_0021c3e0.",
                "FUN_00128218 masks incoming flags to 0x100, calls FUN_0021c3e0 first with flags|0x2 (bit 0x8 clear), calls FUN_0021cc88 with selector 0x89, calls FUN_0021d090, then calls FUN_0021c3e0 with flags|0x2a (bit 0x8 set). Thus the first helper call follows the normalized STROW-before-V4-8 branch; the second follows the alternate V4-8-before-STROW branch.",
            ],
            "claim_limit": "This pins a static caller/argument path and the two distinct helper phases. The race94 wrapper pointer and node/header flags are joined separately below; the paused state's renderer count is zero and the GSDump is a separate capture, so no live call or packet identity is claimed.",
        },
        "claim_limit": "This proves a source-supported CPU-to-VIF normalization candidate for the bit-8-clear branch and the exact signed-byte/128 arithmetic under the pinned PCSX2 mode-1 semantics. It does not prove this helper branch or overlay-1 ran for the captured COBRA interval, nor that its four-byte plane is the one paired to the sampled packet RGB values.",
    }

    inputs = {}
    content: dict[str, str] = {}
    mismatches = []
    for name, expected in PINS.items():
        base = VU_DIR if name.startswith("overlay-") else FUNCTION_DIR
        path = args.input_bundle / base / name
        actual = sha256(path) if path.is_file() else None
        inputs[name] = {"path": str(path), "expected_sha256": expected, "actual_sha256": actual}
        if actual != expected:
            mismatches.append(name)
        if name.endswith(".c") or name.endswith(".s"):
            content[name] = path.read_text(encoding="utf-8", errors="strict") if path.is_file() else ""

    # These are source-literal anchors, not semantic labels inferred from values.
    required = {
        "001288b0.c": ["FUN_00129428(0xffffffffff000000)", "FUN_00128e88(uVar1,uVar9,uVar7,uVar8"],
        "0021bc18.c": ["param_2[2] != 0xffff", "(uint)param_2[2] * 4 + *(int *)(param_1 + 0xec)"],
        "00129428.c": ["0x5000000c", "0x100000000000800b", "0x4c", "0x4e"],
        "001297b8.c": ["0x50000000", "0x1000000000008000", "puVar7[1] = 0x42", "*puVar7 = 0x60", "puVar7[1] = 0x14", "puVar7[1] = 0x3f"],
        "00128e88.c": ["0x6c058000", "0x69000000", "0x6e000000", "0x65000000", "0x44400000", "0x45c00000"],
        "overlay-5.s": ["xtop vi01", "ilw.z vi03,3(vi01)z", "lq.xyzw vf15xyzw,0(vi03)", "ilw.w vi06,1(vi03)w"],
        "overlay-6.s": ["ftoi4.xyz vf16xyz,vf17xyz", "sqi.xyzw vf12xyzw,(vi07++)", "sqi.xyzw vf30xyzw,(vi07++)", "sqi.xyzw vf16xyzw,(vi07++)", "xgkick vi11"],
    }
    checks = []
    for name, needles in required.items():
        text = content.get(name, "")
        missing = [needle for needle in needles if needle not in text]
        checks.append({"source": name, "required_source_literals": needles, "missing": missing, "result": "pass" if not missing else "fail"})

    def prim_fields(value: int) -> dict[str, int]:
        return {"type": value & 0x7, "iip": (value >> 3) & 1, "tme": (value >> 4) & 1, "fge": (value >> 5) & 1, "abe": (value >> 6) & 1, "aa1": (value >> 7) & 1, "fst": (value >> 8) & 1, "ctxt": (value >> 9) & 1, "fix": (value >> 10) & 1}

    def alpha_fields(value: int) -> dict[str, int]:
        return {"a": value & 3, "b": (value >> 2) & 3, "c": (value >> 4) & 3, "d": (value >> 6) & 3, "fix_alpha": (value >> 32) & 0xFF}

    semantic_decode = {
        "cpu_vif_normal_bias_candidate": normal_bias_candidate,
        "untextured_material_prim_alpha_path": {
            "source_functions": material_setup_sources,
            "00128e88_source_prim": "Its constructed PRIM literal is 0x4c when its texture pointer param_7 is null and 0x5c otherwise; both have ABE=1, while only 0x5c has TME=1. This construction does not depend on source header bit 1 or the dynamic opacity global.",
            "0021bb48_source_prim": "This separate packet setup path starts with 0x0c and switches to 0x4c when effective param_5 bit 1 is set; it independently adds TME bit 0x10 when texture-object param_7 is nonzero.",
            "0021bf28_source_flag_map": "Source header bit 0 maps to effective flag 0x20; bit 2 maps to 0x1; bit 3 to 0x40; bit 4 to 0x80. Header bit 1 is not directly mapped to effective ABE flag 0x2 in this helper. Effective bit 0x2 can instead be introduced when DAT_70003560 != 1.0, or by the caller's param_3 path in 0021d180.",
            "0021c3e0_source_alpha": "For the direct untextured setup (effective bit 0x10 clear, texture object null), alpha argument defaults to 0x44 when effective bit 0x20 is clear; it is passed to 0021ba50, which writes its own fixed PRIM 0x4c and supplied alpha value.",
            "bounded_race94_condition": "The COBRA node record bit 0x10000 is clear, first 0021d180 call has param_3=0, race94 DAT_70003560 is 1.0, and c01a header bit 0 is clear; if this direct 0021c3e0 branch is reached with no texture pointer, these source conditions predict the 0021ba50 setup's PRIM 0x4c and ALPHA 0x44. The paused state has a zero renderer count and the GSDump is a separate capture, so this is a source-compatible candidate, not an executed producer join.",
            "claim_limit": "The raw source has two distinct PRIM construction paths. 00128e88 sets untextured ABE unconditionally; 0021bb48 ties ABE to effective bit 1 and TME to the independent texture pointer. The runtime-bound c01a flags do not by themselves establish that 0021bb48 bit, while the 0021ba50 direct setup has a static 0x4c PRIM. No claim that any one path emitted transfer 5906 is made.",
        },
        "texture_index_lookup": {
            "header_field": "ushort param_2[2] (byte offset +4 from header pointer)",
            "sentinel": "0xffff means no table lookup; otherwise pointer = *(u32 *)(car_object+0xec+4*index)",
            "consumer": "FUN_001288b0 passes selected pointer uGpffff940c and ALPHA value 0x48 into FUN_001297b8 for the second geometry group.",
            "claim_limit": "This proves a per-object texture-table index/pointer path, not the mapping from that pointer to a named texture-library record or serialized texture record ID.",
        },
        "gif_tag": {
            "gif_primitive_control": {
                "untextured_selector": {"raw": "0x4c", **prim_fields(0x4C)},
                "textured_pointer_selector": {"raw": "0x5c", **prim_fields(0x5C)},
                "decode": "Both are triangle strips (PRIM type 4), IIP=1, ABE=1; TME is 0 when param_7==0 and 1 when param_7!=0. Other listed PRIM controls are 0.",
            },
            "gif_register_descriptor": {"raw": "0x412", "nreg": 3, "descriptor_nibbles_low_to_high": [2, 1, 4], "definitions": ["ST", "RGBAQ", "XYZF2"], "output_qword_order": ["vf13", "vf14", "vf12"], "order_join": "not inferred here; needs exact XGKICK/GIF descriptor-order consumer validation against runtime output"},
            "source": "The GIFtag is built from count|EOP, PRIM<<47, and NREG=3; the next 64-bit word is the register descriptor 0x412.",
        },
        "gs_context_values": {
            "alpha_selector_definitions": {"a_b": {"0": "Cs", "1": "Cd", "2": "0"}, "c": {"0": "As", "1": "Ad", "2": "FIX"}, "d": {"0": "Cs", "1": "Cd", "2": "0"}, "formula": "(A-B)*C+D", "abe": 1},
            "first_group": {"alpha_1_raw": "0x2a", **alpha_fields(0x2A), "rgb_equation": "(0-0)*FIX+Cs = Cs (FIX field is 0)", "draw_caller": "FUN_001297b8(0,0x2a)"},
            "second_group": {"alpha_1_raw": "0x48", **alpha_fields(0x48), "rgb_equation": "(Cs-0)*As+Cd = Cs*As+Cd", "draw_caller": "FUN_001297b8(uGpffff940c,0x48)"},
            "textured_pointer_nonzero": {"tex0_1": "dynamic value assembled from selected texture-object fields", "tex1_1_raw": "0x60", "tex1_1_fields": {"lcm": 0, "mxl": 0, "mmag": 1, "mmin": 1, "mtba": 0, "l": 0, "k": 0}, "mmag_meaning": "linear", "mmin_meaning": "linear (filter selector 1)", "mxl_meaning": "0", "texflush_raw": "0x0"},
            "interpretation_limit": "These are exact constructed context writes in FUN_001297b8. Other calls or later context changes and original runtime execution are outside this trace.",
        },
    }

    result = {
        "schema": "fr2-packet-continuation-static-trace/v1",
        "scope": "Read-only source-hash and literal-anchor validation. No original routine, VIF, VU, GIF, GS, DMA, or emulator execution.",
        "inputs": inputs,
        "checks": checks,
        "semantic_decode": semantic_decode,
        "overlay5_source_input_accesses": {
            "source": "Pinned overlay-5.s",
            "sha256": inputs["overlay-5.s"]["actual_sha256"],
            "all_lines_referencing_vi03_data_memory": [
                {"line": line_number, "text": line}
                for line_number, line in enumerate(content["overlay-5.s"].splitlines(), start=1)
                if "(vi03)" in line
            ],
            "counts": {
                "explicit_vi03_memory_references": sum("(vi03)" in line for line in content["overlay-5.s"].splitlines()),
                "vector_loads_from_plus_one": sum("lq.xyzw" in line and ",1(vi03)" in line for line in content["overlay-5.s"].splitlines()),
                "integer_W_reads_from_plus_one": sum("ilw.w" in line and "1(vi03)w" in line for line in content["overlay-5.s"].splitlines()),
                "vector_stores_to_plus_one": sum("sq.xyzw" in line and ",1(vi03)" in line for line in content["overlay-5.s"].splitlines()),
            },
            "interpretation_limit": "This lists explicit assembly references to the per-vertex vi03 base in overlay-5, not all indirect register dataflow or other microprograms. At the inspected vertex loop, source +0/+2 are vector-loaded, source +1.w is integer-loaded, and source +1 is also a vector-store destination elsewhere; this is not evidence of a program-wide absence of all normal processing.",
        },
        "preceding_overlay_input_accesses": {
            "scope": "Hash-pinned overlay-0 and overlay-1 assembly; explicit references to vi03 and the adjacent qwords. These listings alone do not identify which overlay ran for the captured car tags or establish a runtime join from a particular source header to this path.",
            "overlays": {
                str(index): {
                    "source": f"overlay-{index}.s",
                    "sha256": inputs[f"overlay-{index}.s"]["actual_sha256"],
                    "vi03_data_memory_lines": [
                        {"line": line_number, "text": line}
                        for line_number, line in enumerate(content[f"overlay-{index}.s"].splitlines(), start=1)
                        if "(vi03)" in line
                    ],
                }
                for index in (0, 1)
            },
            "interpretation_limit": "Overlay-0's inspected copy path leaves qword+1 XYZ unchanged and overwrites W. Overlay-1's separate lit block first subtracts LOI 98304 from input qword+1 XYZ, conditionally BALs vi15,+459 when vi14!=0 (target/effect unresolved), and runs lighting only when vi09!=0. It uses DM[6].xyz for the dot direction, clamps at zero, scales by DM[5].xyz, adds DM[4].xyz after reloading vf08 from that ambient slot, multiplies by vf05.xyz, FTOI0 converts, and output is stored at qword vi04+1. These are source-static facts; the saved snapshots prove byte residency only, not overlay dispatch/execution for the COBRA packets, and do not bind qword input or dynamic VU constants to captured GS colors.",
            "overlay1_colorflow_static_arithmetic": {
                "overlay_sha256": inputs["overlay-1.s"]["actual_sha256"],
                "branch_context": [
                    {"line": 54, "text": content["overlay-1.s"].splitlines()[53]},
                    {"line": 74, "text": content["overlay-1.s"].splitlines()[73]}
                ],
                "instructions": [
                    {"line": 42, "text": content["overlay-1.s"].splitlines()[41]},
                    {"line": 45, "text": content["overlay-1.s"].splitlines()[44]},
                    {"line": 50, "text": content["overlay-1.s"].splitlines()[49]},
                    {"line": 54, "text": content["overlay-1.s"].splitlines()[53]},
                    {"line": 56, "text": content["overlay-1.s"].splitlines()[55]},
                    {"line": 58, "text": content["overlay-1.s"].splitlines()[57]},
                    {"line": 61, "text": content["overlay-1.s"].splitlines()[60]},
                    {"line": 62, "text": content["overlay-1.s"].splitlines()[61]},
                    {"line": 74, "text": content["overlay-1.s"].splitlines()[73]},
                    {"line": 82, "text": content["overlay-1.s"].splitlines()[81]},
                    {"line": 86, "text": content["overlay-1.s"].splitlines()[85]},
                    {"line": 90, "text": content["overlay-1.s"].splitlines()[89]},
                    {"line": 94, "text": content["overlay-1.s"].splitlines()[93]},
                    {"line": 98, "text": content["overlay-1.s"].splitlines()[97]},
                    {"line": 103, "text": content["overlay-1.s"].splitlines()[102]}
                ],
                "bounded_formula": "For each four-record batch, the VU subtracts LOI 98304 from input qword vi03+1 XYZ; if vi14!=0, it additionally BALs vi15,+459 before the dot product (the target is outside this pinned overlay-1 listing and its effect is not asserted). The lit block runs only when vi09!=0. It forms d=dot(DM[6].xyz,n'), clamps d=max(d,0), then computes color=(DM[5].xyz*d+DM[4].xyz)*vf05.xyz, converts via FTOI0 and stores the result at output qword vi04+1. DM[6] supplies the direction used for the dot; vf08 is reloaded from DM[4] before the ambient add, so those values are distinct. The branch-control values and dynamic register contents are not captured.",
                "vif_input_format": "The separate FUN_0021c3e0 path has a bit-8-clear branch that writes STROW 0x47c00000 xyz, STMOD 1, then V4-8 with USN clear. Pinned PCSX2 VIF source implements mode 1 as signed integer plus row word; subtracting the VU LOI 98304 exactly yields signed_byte/128 for all 256 byte values. This is a plausible normalization path, but no source call or live packet join ties it to the COBRA interval. FUN_00128e88's own four-byte V4-8 REF is followed by its STROW writes, so that function alone does not establish this /128 scaling.",
                "limitations": ["No live PC/dispatch link selects overlay-1 for the COBRA packet interval.", "No captured VU input qword is joined to a particular source header and packet output vertex.", "Conditional BAL vi15,+459's target/effect is outside the inspected listing.", "The static arithmetic does not prove the lit branch was taken in the captured frame or identify the runtime values in DM[4], DM[5], DM[6] or vf05."]
            },
        },
        "trace": {
            "cpu_packet_builder": {
                "function": "FUN_001288b0",
                "prior_direct_packet_call": "FUN_00129428(0xffffffffff000000)",
                "geometry_groups": "Per group the saved C calls FUN_00128e88 with count, six-byte plane pointer, four-byte plane pointer, optional plane pointer, bbox-like qword input, another qword input, selector, and byte value.",
            },
            "geometry_packet_writer": {
                "function": "FUN_00128e88",
                "inline_header_command": "0x6c058000",
                "header": "V4-32 NUM=5, TOPS-relative, command address 0; five payload qwords are appended before the CNT QWC patch.",
                "selected_unpack_destination": {"selector_zero": "0x208", "selector_nonzero": "0x2c8", "destination_expression": "V3-16 ADDR=uVar14; V4-8 ADDR=uVar14+1; optional V2-16 ADDR=uVar14+2", "correction": "These are UNPACK command ADDR values. The five-qword V4-32 header's payload lanes are copied from param_5 and param_8; uVar14 is not qword-3.Z."},
                "refs": [
                    {"format": "V4-8", "destination": "selected_base+1", "source": "param_3"},
                    {"format": "V3-16", "destination": "selected_base", "source": "param_2"},
                    {"format": "V2-16", "destination": "selected_base+2", "source": "param_4", "condition": "param_4 != 0"},
                ],
                "row_mode_words": ["STROW 0x44400000 before V3-16", "STMOD 0x05000000", "optional STROW 0x45c00000 before V2-16"],
            },
            "vu_instruction_path": {
                "overlay5": [
                    "XTOP captures TOP in vi01.",
                    "ILW reads TOP+3.z into vi03.",
                    "LQ reads vi03+0 and vi03+2; ILW also reads vi03+1.w.",
                    "The xyz pipeline uses vector operations and FTOI4 conversion in the resumed sequence.",
                ],
                "overlay6": [
                    "FTOI4.xyz converts vf17 to vf16.",
                    "The code stores vf12, vf30, and vf16 as three consecutive qwords.",
                    "A later instruction executes XGKICK vi11.",
                ],
                "conditionality": "The TOP-relative input-plane linkage remains conditional on the actual VIF TOPS/MODE/CYCLE and execution path; the GS-visible meaning of output lanes has not been proven.",
            },
            "direct_gif_gs": {
                "packet_builders": ["FUN_00129428", "FUN_001297b8"],
                "bounded_conclusion": "These functions append DIRECT packets with GIF-tag/A+D-shaped data, but this trace does not decode per-part texture binding or establish the final draw state after all intervening packets.",
            },
        },
        "semantic_status": {
            "texture_index_and_part_binding": "unresolved",
            "UV_encoding_and_texture_linkage": "unresolved",
            "normal_encoding_and_transform": "unresolved",
            "primitive_order_and_winding": "unresolved",
            "ADC_restart_and_strip_boundaries": "unresolved",
            "final_blend_and_filter_state": "unresolved",
            "runtime_DMA_VIF_VU_GIF_GS_execution": "unobserved",
        },
        "validation": {"result": "fail" if mismatches or any(c["result"] != "pass" for c in checks) else "pass", "pin_mismatches": mismatches},
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"output": str(args.output), "result": result["validation"]["result"], "anchors_passed": sum(c["result"] == "pass" for c in checks), "anchors_total": len(checks), "pin_mismatches": mismatches}, indent=2))

    runtime_dir = args.runtime_directory
    state_identity = json.loads((runtime_dir / "loading-state-identity.json").read_text(encoding="utf-8"))
    state_path = Path(state_identity["state"])
    expected_state_sha256 = "91cb6c31177e07d9c8a3e7d975e5c480d325ea9253626f9424c89c4660448e6e"
    expected_save_source_sha256 = "868f923f2044e5a27c439f8b8528c9e509d1185d9fcbefd6eacb3e6240029589"
    runtime_names = {
        "vu1MicroMem.bin": "loading-vu1MicroMem.bin",
        "vu1Memory.bin": "loading-vu1Memory.bin",
        "eeMemory.bin": "loading-eeMemory.bin",
        "GS.bin": "loading-GS.bin",
    }
    runtime_checks = []
    with zipfile.ZipFile(state_path) as archive:
        identity_entries = {entry["name"]: entry for entry in state_identity["entries"]}
        runtime_bytes = {}
        for archive_name, local_name in runtime_names.items():
            extracted = archive.read(archive_name)
            local = (runtime_dir / local_name).read_bytes()
            crc = zlib.crc32(local) & 0xFFFFFFFF
            expected_crc = identity_entries[archive_name]["crc32"]
            match = local == extracted and crc == expected_crc
            runtime_bytes[archive_name] = local
            runtime_checks.append({"name": archive_name, "local_path": str(runtime_dir / local_name), "size": len(local), "savestate_entry_exact_match": match, "crc32": f"0x{crc:08x}", "identity_crc32": f"0x{expected_crc:08x}", "result": "pass" if match else "fail"})

    micro = runtime_bytes["vu1MicroMem.bin"]
    overlay5 = (args.input_bundle / VU_DIR / "overlay-5.bin").read_bytes()
    overlay_offset = 0x2800
    overlay_match = micro[overlay_offset:overlay_offset + len(overlay5)] == overlay5
    loading_overlay_audit = overlay_residency(micro, args.input_bundle / VU_DIR, "loading baseline")
    memory = runtime_bytes["vu1Memory.bin"]
    qwords = {}
    for address in (0x208, 0x2C8):
        raw = memory[address * 16:(address + 1) * 16]
        qwords[f"0x{address:03x}"] = {"vu1_qword_address": f"0x{address:03x}", "raw_hex": raw.hex(), "all_zero": not any(raw)}
    runtime_result = {
        "schema": "fr2-packet-continuation-runtime-snapshot/v1",
        "scope": "Read-only validation of one PCSX2 save-state snapshot. The capture identity labels it a loading screen before the car scene; it is not a geometry execution capture.",
        "state": {"path": str(state_path), "expected_sha256": expected_state_sha256, "actual_sha256": sha256(state_path), "build": state_identity["build"], "phase": state_identity["phase"]},
        "pcsx2_save_state_source": {"path": str(runtime_dir / "SaveState-v2.8.2.cpp"), "expected_sha256": expected_save_source_sha256, "actual_sha256": sha256(runtime_dir / "SaveState-v2.8.2.cpp")},
        "capture_integrity_checks": runtime_checks,
        "microprogram": {"local_snapshot_path": str(runtime_dir / "loading-vu1MicroMem.bin"), "size": len(micro), "overlay5_offset": f"0x{overlay_offset:x}", "overlay5_sha256": hashlib.sha256(overlay5).hexdigest(), "snapshot_range_equals_pinned_overlay5": overlay_match, "exact_overlay_residency_audit": loading_overlay_audit},
        "data_memory_samples": {"addressing_note": "The following are raw absolute qword addresses only. TOP/TOPS register state was not decoded, so these samples are not asserted to be the dynamically selected TOP-relative input planes.", "qwords": qwords},
        "conclusion": "Overlay 5's exact 0x800-byte image is resident at VU1 micro-memory byte offset 0x2800 in this loading-screen save. The capture contains no VU data at absolute qword addresses 0x208 and 0x2c8. Because this state precedes the car scene and live TOPS/register state is not captured here, neither result proves that a car geometry packet was consumed or not consumed.",
        "validation": {"result": "pass" if all(c["result"] == "pass" for c in runtime_checks) and overlay_match and sha256(state_path) == expected_state_sha256 and sha256(runtime_dir / "SaveState-v2.8.2.cpp") == expected_save_source_sha256 else "fail", "savestate_entry_count": len(runtime_checks), "savestate_entries_equal": sum(c["result"] == "pass" for c in runtime_checks), "overlay5_match": overlay_match, "state_hash_matches_pin": sha256(state_path) == expected_state_sha256, "pcsx2_save_source_hash_matches_pin": sha256(runtime_dir / "SaveState-v2.8.2.cpp") == expected_save_source_sha256},
    }
    args.runtime_output.parent.mkdir(parents=True, exist_ok=True)
    args.runtime_output.write_text(json.dumps(runtime_result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"runtime_output": str(args.runtime_output), "runtime_result": runtime_result["validation"]["result"], "savestate_entries_equal": runtime_result["validation"]["savestate_entries_equal"], "overlay5_match": overlay_match}, indent=2))

    # Validate the supplied post-resume race state and one-frame GS dump.
    race_identity_path = args.race_state.parent.parent / "race94-state-identity.json"
    race_identity = json.loads(race_identity_path.read_text(encoding="utf-8"))
    race_dump_sha = sha256(args.race_dump)
    race_checks: dict[str, object] = {"state": {}, "texture_join": {}, "gs_dump": {}}
    expected_race_sha = race_identity["sha256"]
    with zipfile.ZipFile(args.race_state) as archive:
        race_checks["state"] = {
            "path": str(args.race_state), "sha256": sha256(args.race_state),
            "expected_sha256": expected_race_sha,
            "entries": {},
        }
        race_locals = {
            "eeMemory.bin": "race94-eeMemory.bin",
            "GS.bin": "race94-GS.bin",
            "vu1MicroMem.bin": "race94-vu1MicroMem.bin",
            "vu1Memory.bin": "race94-vu1Memory.bin",
        }
        race_bytes = {}
        identity_members = {item["member"]: item for item in race_identity["members"]}
        for member, local_name in race_locals.items():
            raw = archive.read(member)
            local_path = args.race_state.parent.parent / local_name
            local = local_path.read_bytes()
            source_member = identity_members[member]
            match = raw == local and sha256(local_path) == source_member["sha256"]
            race_bytes[member] = raw
            race_checks["state"]["entries"][member] = {
                "path": str(local_path), "bytes": len(raw), "sha256": sha256(local_path),
                "archive_entry_exact_match": raw == local,
                "identity_hash_match": sha256(local_path) == source_member["sha256"],
                "result": "pass" if match else "fail",
            }
        micro = race_bytes["vu1MicroMem.bin"]
        race_overlay_match = micro[0x2800:0x2800 + len(overlay5)] == overlay5
        race_overlay_audit = overlay_residency(micro, args.input_bundle / VU_DIR, "race94 paused state")
        ee_hw = archive.read("eeHwRegs.bin")
        vif1 = 0x3C00
        reg_offsets = {"STAT": 0, "CYCLE": 64, "MODE": 80, "BASE": 160, "OFST": 176, "TOPS": 192, "ITOP": 208, "TOP": 224}
        vif_regs = {name: int.from_bytes(ee_hw[vif1 + off:vif1 + off + (2 if name == "CYCLE" else 4)], "little") for name, off in reg_offsets.items()}
        vu_mem = race_bytes["vu1Memory.bin"]
        vu_samples = {f"0x{addr:03x}": vu_mem[addr * 16:(addr + 1) * 16].hex() for addr in (0x208, 0x2C8)}
        scratchpad = archive.read("Scratchpad.bin")
        if len(scratchpad) != 16 * 1024:
            raise ValueError("PCSX2 Scratchpad.bin is not 16 KiB")
        scratchpad_sha256 = hashlib.sha256(scratchpad).hexdigest()

        # The parent-provided object join is treated as a read-only input. The
        # per-record validation below independently checks every indexed image
        # plane against the original COBRA file and the live EE byte image.
        joins_path = args.race_state.parent.parent / "race94-car-source-joins.json"
        joins = json.loads(joins_path.read_text(encoding="utf-8"))
        cobra = next(item for item in joins["cars"] if item["car"] == "COBRA")
        cobra_obj = cobra["joins"][0]["objects"][0]
        model_path = Path("ford-racing-2/cars/COBRA/model/COBRA.PS2;1")
        model_bytes = model_path.read_bytes()
        re_tools = Path(__file__).resolve().parent
        sys.path.insert(0, str(re_tools))
        try:
            import ps2_container  # type: ignore
            import ps2_sections  # type: ignore
            parsed = ps2_sections.parse(model_bytes)
        finally:
            sys.path.pop(0)
        texture_items = parsed["textures"]["items"]
        ee_mem = race_bytes["eeMemory.bin"]
        vu_indices = sorted({h["third"] for h in parsed["geometry"]["headers"] if h["third"] != 0xFFFF})
        texture_rows = []
        texture_table = cobra_obj["texture_pointer_table"]
        # Join one source geometry range to the exact runtime wrapper node
        # record, then separately inspect the renderer scratchpad count. The
        # state was paused and the GS dump is a separate capture, so an empty
        # count prevents us from calling this an observed live dispatch.
        renderer_entry_address = 0x2342C0
        wrapper_ptr = struct.unpack_from("<I", ee_mem, renderer_entry_address + 4)[0]
        wrapper_record_address = wrapper_ptr + 0x1C
        wrapper_words = struct.unpack_from("<3I", ee_mem, wrapper_record_address)
        source_base = cobra_obj["name_base"]
        geometry_headers = parsed["geometry"]["headers"]
        source_header_start_offset = geometry_headers[0]["offset"]
        source_header_end_offset = parsed["geometry"]["payload_start"]
        source_header_start_ptr = source_base + source_header_start_offset
        source_header_end_ptr = source_base + source_header_end_offset
        source_flag_candidates = sorted({header["flags"] for header in geometry_headers})
        record_flags = wrapper_words[0]
        first_source_header = geometry_headers[0]
        runtime_source_branch_join = {
            "state_sha256": expected_race_sha,
            "renderer_entry_address": f"0x{renderer_entry_address:08x}",
            "renderer_entry_first_two_u32": [f"0x{x:08x}" for x in struct.unpack_from("<2I", ee_mem, renderer_entry_address)],
            "wrapper_pointer": f"0x{wrapper_ptr:08x}",
            "node_record_address": f"0x{wrapper_record_address:08x}",
            "node_record_words_flags_header_start_header_end": [f"0x{x:08x}" for x in wrapper_words],
            "source_model_name_base": f"0x{source_base:08x}",
            "source_header_table_offsets": [source_header_start_offset, source_header_end_offset],
            "source_header_table_bound_note": "The parsed source's payload_start is the end pointer; it includes the 8-byte zero gap after header_end and before payload_start.",
            "computed_source_header_pointers": [f"0x{source_header_start_ptr:08x}", f"0x{source_header_end_ptr:08x}"],
            "runtime_header_pointer_bounds_match_source": wrapper_words[1:] == (source_header_start_ptr, source_header_end_ptr),
            "header_count": len(geometry_headers),
            "first_source_header_flags": f"0x{first_source_header['flags']:04x}",
            "source_header_flag_values": [f"0x{x:04x}" for x in source_flag_candidates],
            "node_record_dispatch_bit_0x10000": bool(record_flags & 0x10000),
            "source_first_header_dispatch_bit_0x10": bool(first_source_header["flags"] & 0x10),
            "FUN_0021bf28_wrapper_predicate_for_first_header": bool(record_flags & 0x10000) and bool(first_source_header["flags"] & 0x10),
            "scratchpad_sha256": scratchpad_sha256,
            "scratchpad_bytes": len(scratchpad),
            "FUN_00127fa8_scratchpad_batch_count_address": "0x70003590",
            "FUN_00127fa8_scratchpad_batch_count_u32": struct.unpack_from("<I", scratchpad, 0x3590)[0],
            "static_branch_facts": {
                "00127fa8_first_loop_seeds_0x100_and_second_loop_seeds_zero": True,
                "0021d180_adds_0x8_only_if_node_record_bit_0x10000_is_set": True,
                "0021bf28_uses_00128218_only_if_effective_bit_0x8_and_header_bit_0x10_are_both_set": True,
                "00128218_first_helper_mask_0x2_has_bit_0x8_clear": True,
                "00128218_second_helper_mask_0x2a_has_bit_0x8_set": True,
            },
            "bounded_result": "The live EE wrapper range points exactly at the loaded COBRA source header table, and its node word has bit 0x10000 clear; if this record is dispatched, the two-phase FUN_00128218 path is not selected for this first header. However, the renderer batch count in this paused save-state scratchpad is zero, and the GSDump is a separate capture. Therefore this is a source-pointer/branch-condition join, not proof that this record generated the decoded packet interval.",
        }
        if not runtime_source_branch_join["runtime_header_pointer_bounds_match_source"]:
            raise ValueError("runtime wrapper header bounds no longer match source COBRA table")
        for item in texture_items:
            index = item["index"]
            runtime_obj_ptr = struct.unpack_from("<I", ee_mem, texture_table + 4 * index)[0]
            runtime_obj_valid = 0 < runtime_obj_ptr < len(ee_mem) - 0x40
            runtime_obj = ee_mem[runtime_obj_ptr:runtime_obj_ptr + 0x40] if runtime_obj_valid else b""
            level = item["levels"][0]
            source_plane = model_bytes[level["offset"]:level["offset"] + level["size"]]
            runtime_plane_hit = ee_mem.find(source_plane) if source_plane else -1
            texture_rows.append({
                "index": index, "name": item["name"], "format": item["format"],
                "dimensions": [item["width"], item["height"]],
                "source_plane_offset": level["offset"], "source_plane_bytes": len(source_plane),
                "source_plane_sha256": hashlib.sha256(source_plane).hexdigest(),
                "runtime_pointer_table_entry_address": texture_table + 4 * index,
                "runtime_texture_object_pointer": runtime_obj_ptr,
                "runtime_object_first_0x40_sha256": hashlib.sha256(runtime_obj).hexdigest() if runtime_obj else None,
                "runtime_object_first_0x40_words32": list(struct.unpack("<16I", runtime_obj)) if len(runtime_obj) == 0x40 else [],
                "runtime_object_u16_at_plus4": struct.unpack_from("<H", runtime_obj, 4)[0] if len(runtime_obj) >= 6 else None,
                "ee_exact_plane_match_address": runtime_plane_hit if runtime_plane_hit >= 0 else None,
                "runtime_object_and_plane_in_bounds": runtime_obj_valid and runtime_plane_hit >= 0,
            })

    # Decode the pinned PCSX2 GSDump container plus the standard GIFtag and
    # packed A+D encodings. Keep the raw tag bytes/digest so interpretation is
    # reviewable and repeatable without treating a screenshot as proof.
    zstd = shutil.which("zstd") or "/opt/homebrew/bin/zstd"
    decompressed = subprocess.check_output([zstd, "-d", "-c", str(args.race_dump)])
    if len(decompressed) < 8 + 36:
        raise ValueError("truncated GSDump header")
    marker, header_size = struct.unpack_from("<II", decompressed, 0)
    state_version, state_size, serial_offset, serial_size, dump_crc, sw, sh, screenshot_offset, screenshot_size = struct.unpack_from("<9I", decompressed, 8)
    if marker != 0xFFFFFFFF or 8 + header_size > len(decompressed):
        raise ValueError("unexpected GSDump header marker/size")
    body_start = 8 + header_size
    packet_start = body_start + state_size + 0x2000
    if packet_start > len(decompressed):
        raise ValueError("truncated GSDump initial GS state")
    transfers = []
    event_counts: dict[str, int] = {"transfer": 0, "registers": 0, "vsync": 0, "read_fifo2": 0}
    pos = packet_start
    while pos < len(decompressed):
        kind = decompressed[pos]
        pos += 1
        if kind == 0:
            if pos + 5 > len(decompressed):
                raise ValueError("truncated GSDump transfer header")
            path = decompressed[pos]
            size = struct.unpack_from("<I", decompressed, pos + 1)[0]
            pos += 5
            if size > len(decompressed) - pos:
                raise ValueError("truncated GSDump transfer payload")
            transfers.append((path, decompressed[pos:pos + size]))
            pos += size
            event_counts["transfer"] += 1
        elif kind == 1:
            if pos >= len(decompressed):
                raise ValueError("truncated GSDump vsync record")
            pos += 1
            event_counts["vsync"] += 1
        elif kind == 2:
            pos += 4
            event_counts["read_fifo2"] += 1
        elif kind == 3:
            pos += 0x2000
            event_counts["registers"] += 1
        else:
            raise ValueError(f"unknown GSDump record type {kind} at {pos - 1:#x}")
    gs_state: dict[int, int] = {}
    tag_stats: dict[str, int] = {}
    draw_records = []
    draw_count = 0
    draw_prim_counts: dict[str, int] = {}
    draw_tex0_counts: dict[str, int] = {}
    draw_texture_base_counts: dict[str, int] = {}
    draw_context_counts: dict[str, int] = {}
    draw_packet_events = []
    vertex_count = 0
    adc_counts = {"set": 0, "clear": 0}
    topology_triangle_counts: dict[str, int] = {"triangle_strip": 0, "triangle_fan": 0}
    xyzf2_samples = []
    ad_values: dict[int, dict[str, int]] = {0x06: {}, 0x14: {}, 0x42: {}, 0x00: {}}
    image_transfers = []
    for transfer_index, (path, data) in enumerate(transfers):
        off = 0
        while off < len(data):
            if off + 16 > len(data):
                raise ValueError(f"incomplete GIFtag at transfer {transfer_index}+{off:#x}")
            lo, hi = struct.unpack_from("<QQ", data, off)
            nloop = lo & 0x7FFF
            eop = (lo >> 15) & 1
            prim = (lo >> 47) & 0x7FF
            flg = (lo >> 58) & 3
            nreg = (lo >> 60) & 0xF or 16
            if flg == 0:
                payload = nloop * nreg * 16
                descriptors = [(hi >> (4 * i)) & 0xF for i in range(nreg)]
            elif flg == 1:
                payload = ((nloop * nreg + 1) // 2) * 16
                descriptors = []
            elif flg == 2:
                payload = nloop * 16
                descriptors = []
            else:
                payload = 0
                descriptors = []
            end = off + 16 + payload
            if end > len(data):
                raise ValueError(f"GIF payload overruns transfer {transfer_index} at {off:#x}")
            key = f"flg{flg}_nreg{nreg}_desc{hi:x}"
            tag_stats[key] = tag_stats.get(key, 0) + 1
            if flg == 0 and nreg == 1 and descriptors == [0xE]:
                for i in range(nloop):
                    at = off + 16 + i * 16
                    value, = struct.unpack_from("<Q", data, at)
                    reg = data[at + 8]
                    gs_state[reg] = value
                    if reg in ad_values:
                        ad_values[reg][hex(value)] = ad_values[reg].get(hex(value), 0) + 1
            if flg == 2:
                image_payload = data[off + 16:end]
                image_transfers.append({
                    "transfer_index": transfer_index, "transfer_path": path,
                    "offset": off, "nloop": nloop, "eop": eop,
                    "payload": image_payload,
                    "payload_bytes": len(image_payload),
                    "payload_sha256": hashlib.sha256(image_payload).hexdigest(),
                    "gs_transfer_registers": {hex(reg): f"0x{gs_state[reg]:x}" for reg in (0x50, 0x51, 0x52, 0x53) if reg in gs_state},
                })
            if flg == 0 and descriptors == [2, 1, 4]:
                draw_count += 1
                primitive_key = f"type{prim & 7}_tme{(prim >> 4) & 1}_abe{(prim >> 6) & 1}"
                draw_prim_counts[primitive_key] = draw_prim_counts.get(primitive_key, 0) + 1
                prim_type = prim & 7
                if prim_type == 4:
                    topology_triangle_counts["triangle_strip"] += max(0, nloop - 2)
                elif prim_type == 5:
                    topology_triangle_counts["triangle_fan"] += max(0, nloop - 2)
                vertex_count += nloop
                packet_xyz = []
                packet_stq = []
                packet_rgba = []
                for vertex_index in range(nloop):
                    stq_at = off + 16 + vertex_index * 3 * 16
                    s, t, q = struct.unpack_from("<3f", data, stq_at)
                    packet_stq.append({"s": s, "t": t, "q": q})
                    rgba_at = off + 16 + (vertex_index * 3 + 1) * 16
                    rgbaq = data[rgba_at:rgba_at + 16]
                    if len(rgbaq) != 16:
                        raise ValueError("truncated packed RGBAQ vertex")
                    # This is GIF packed mode (FLG=0), so RGBA is four 32-bit
                    # lanes; PCSX2's GIFPackedRegHandlerRGBA extracts each
                    # lane's low byte. Q comes from the preceding STQ packet,
                    # not from byte offset 4 of this RGBA qword.
                    rgba_lanes = struct.unpack_from("<4I", rgbaq, 0)
                    rgba = [lane & 0xFF for lane in rgba_lanes]
                    packet_rgba.append({"rgba8": rgba, "raw_qword_hex": rgbaq.hex(), "raw_lane_u32": list(rgba_lanes), "q_source": "preceding packed STQ third float"})
                    xyz_at = off + 16 + (vertex_index * 3 + 2) * 16
                    xyzq = data[xyz_at:xyz_at + 16]
                    if len(xyzq) != 16:
                        raise ValueError("truncated packed XYZF2 vertex")
                    word3, = struct.unpack_from("<I", xyzq, 12)
                    adc = (word3 >> 15) & 1
                    adc_counts["set" if adc else "clear"] += 1
                    x, = struct.unpack_from("<H", xyzq, 0)
                    y, = struct.unpack_from("<H", xyzq, 4)
                    zf, = struct.unpack_from("<I", xyzq, 8)
                    packet_xyz.append({"x_12_4": x, "y_12_4": y, "z24": zf & 0xFFFFFF, "f8": (zf >> 24) & 0xFF, "adc": adc})
                if len(xyzf2_samples) < 32:
                    xyzf2_samples.append({"transfer_index": transfer_index, "offset": off, "prim_type": prim_type, "nloop": nloop, "vertices": [{"stq": packet_stq[i], "xyzf2": packet_xyz[i]} for i in range(min(8, nloop))]})
                tex0 = gs_state.get(0x06)
                tex1 = gs_state.get(0x14)
                alpha = gs_state.get(0x42)
                tbp0 = tex0 & 0x3FFF if tex0 is not None else None
                source_uv_candidates = []
                if tbp0 == 0x36E0:
                    for header_index, source_header in enumerate(parsed["geometry"]["headers"]):
                        if source_header["third"] != 0 or source_header["count"] != nloop:
                            continue
                        uv_plane = source_header["planes"].get("third_four_byte")
                        if not uv_plane or uv_plane["size"] != nloop * 4:
                            continue
                        uv_pairs = list(struct.iter_unpack("<hh", model_bytes[uv_plane["offset"]:uv_plane["offset"] + uv_plane["size"]]))
                        errors = []
                        for sample, (u_raw, v_raw) in zip(packet_stq, uv_pairs):
                            if sample["q"] == 0.0:
                                errors.append(float("inf"))
                            else:
                                errors.append(max(abs(sample["s"] / sample["q"] - u_raw / 2048.0), abs(sample["t"] / sample["q"] - v_raw / 2048.0)))
                        max_error = max(errors, default=float("inf"))
                        four_plane = source_header["planes"].get("four_byte")
                        adc_match_count = None
                        adc_lane_bit_matches = None
                        adc_source_lane3_bit0_pairs = None
                        if four_plane and four_plane["size"] == nloop * 4:
                            source_four = model_bytes[four_plane["offset"]:four_plane["offset"] + four_plane["size"]]
                            adc_match_count = sum(
                                ((source_four[i * 4 + 3] & 1) == packet_xyz[i]["adc"])
                                for i in range(nloop)
                            )
                            adc_lane_bit_matches = {
                                f"byte{lane}_bit{bit}": sum(
                                    (((source_four[i * 4 + lane] >> bit) & 1) == packet_xyz[i]["adc"])
                                    for i in range(nloop)
                                )
                                for lane in range(4) for bit in range(8)
                            }
                            adc_source_lane3_bit0_pairs = {
                                f"source{source_bit}_adc{adc_bit}": sum(
                                    ((source_four[i * 4 + 3] & 1) == source_bit and packet_xyz[i]["adc"] == adc_bit)
                                    for i in range(nloop)
                                )
                                for source_bit in range(2) for adc_bit in range(2)
                            }
                        source_uv_candidates.append({
                            "source_header_index": header_index,
                            "source_header_offset": source_header["offset"],
                            "source_header_count": source_header["count"],
                            "source_texture_index": source_header["third"],
                            "uv_plane_offset": uv_plane["offset"],
                            "uv_plane_sha256": hashlib.sha256(model_bytes[uv_plane["offset"]:uv_plane["offset"] + uv_plane["size"]]).hexdigest(),
                            "stq_over_q_vs_signed16_div_2048_max_absolute_error": max_error,
                            "four_byte_lane3_lowbit_matches_xyzf2_ADC_vertices": adc_match_count,
                            "four_byte_lane_bit_matches_xyzf2_ADC_vertices": adc_lane_bit_matches,
                            "source_four_byte_lane3_bit0_to_xyzf2_ADC_pairs": adc_source_lane3_bit0_pairs,
                            "adc_vertex_count": nloop,
                            "uv_exact_match_at_1e-6": max_error <= 1e-6,
                        })
                draw_tex0_counts[hex(tex0) if tex0 is not None else "unset"] = draw_tex0_counts.get(hex(tex0) if tex0 is not None else "unset", 0) + 1
                draw_texture_base_counts[hex(tbp0) if tbp0 is not None else "unset"] = draw_texture_base_counts.get(hex(tbp0) if tbp0 is not None else "unset", 0) + 1
                context = f"tex0={hex(tex0) if tex0 is not None else 'unset'}|tex1={hex(tex1) if tex1 is not None else 'unset'}|alpha={hex(alpha) if alpha is not None else 'unset'}|prim={hex(prim)}"
                draw_context_counts[context] = draw_context_counts.get(context, 0) + 1
                draw_packet_events.append({
                    "transfer_index": transfer_index, "offset": off, "nloop": nloop,
                    "prim": prim, "pre": (lo >> 46) & 1,
                    "tex0_1": f"0x{tex0:x}" if tex0 is not None else None,
                    "tbp0": tbp0,
                    "tex1_1": f"0x{tex1:x}" if tex1 is not None else None,
                    "alpha_1": f"0x{alpha:x}" if alpha is not None else None,
                    "source_uv_header_candidates": source_uv_candidates,
                    "xyzf2_adc_full": [v["adc"] for v in packet_xyz] if tbp0 == 0x36E0 else None,
                    "rgbaq_full": packet_rgba if tbp0 == 0x36E0 else None,
                    "screen_xy_12_4_full": [[v["x_12_4"], v["y_12_4"]] for v in packet_xyz] if tbp0 == 0x36E0 else None,
                    "vertices_sample": [
                        {"s": packet_stq[i]["s"], "t": packet_stq[i]["t"], "q": packet_stq[i]["q"], "rgbaq": packet_rgba[i], **packet_xyz[i]}
                        for i in range(min(8, nloop))
                    ],
                })
                if len(draw_records) < 64:
                    draw_records.append({
                        "transfer_index": transfer_index, "transfer_path": path,
                        "offset": off, "nloop": nloop, "eop": eop,
                        "giftag_raw_lo64": f"0x{lo:016x}",
                        "prim_field": prim, "prim_type": prim_type,
                        "iip": (prim >> 3) & 1, "tme": (prim >> 4) & 1,
                        "abe": (prim >> 6) & 1, "descriptor": "0x412",
                        "gs_state_before_packet": {hex(k): f"0x{gs_state[k]:x}" for k in (0x00, 0x06, 0x14, 0x42) if k in gs_state},
                        "first_vertex_records_hex": data[off + 16:min(end, off + 16 + 3 * 16)].hex(),
                    })
            off = end
            if eop:
                break
    draw_signatures: dict[str, int] = {}
    for record in draw_records:
        sig = f"type{record['prim_type']}_tme{record['tme']}_abe{record['abe']}_nloop{record['nloop']}"
        draw_signatures[sig] = draw_signatures.get(sig, 0) + 1
    race_checks["texture_join"] = {
        "join_input_sha256": sha256(joins_path), "model_path": str(model_path),
        "model_sha256": sha256(model_path), "geometry_header_count": len(parsed["geometry"]["headers"]),
        "geometry_header_texture_index_counts": {str(i): sum(1 for h in parsed["geometry"]["headers"] if h["third"] == i) for i in [*vu_indices, 0xFFFF]},
        "non_sentinel_indices": vu_indices, "texture_count": len(texture_items),
        "runtime_texture_pointer_table": texture_table,
        "texture_index_equals_ordered_serialized_record_index": all(row["index"] == row["runtime_pointer_table_entry_address"] - texture_table >> 2 for row in texture_rows),
        "all_source_level_zero_planes_found_exactly_in_ee_memory": all(row["ee_exact_plane_match_address"] is not None for row in texture_rows),
        "records": texture_rows,
        "claim_limit": "Object identity and retained EE bytes are tied to COBRA by the independently supplied ten-field/name-base object join. Exact level-zero byte matches prove index-to-serialized-record ordering and residency for this captured object; they do not alone prove that a particular record was bound in the rendered draw.",
    }
    race_checks["runtime_source_branch_join"] = runtime_source_branch_join
    race_checks["vif_vu_state"] = {
        "eeHwRegs_entry_sha256": hashlib.sha256(ee_hw).hexdigest(),
        "pcsx2_register_layout_source": "PCSX2 v2.8.2 VIFregisters/VIF1Regs layout, pinned project tree commit 81526d4dc7cc70e4ae75abb35a789417456c6d43; VIF1 register block at eeHw offset 0x3c00.",
        "vif1_registers": {k: f"0x{v:x}" for k, v in vif_regs.items()},
        "vu1_micro_overlay5_match_at_0x2800": race_overlay_match,
        "exact_overlay_residency_audit": race_overlay_audit,
        "vu1_memory_samples": vu_samples,
        "claim_limit": "This paused post-resume state establishes saved register and memory contents, not that a particular packet was in flight at the pause or that these two absolute addresses are the active input spans.",
    }
    race_checks["gs_dump"] = {
        "path": str(args.race_dump), "compressed_sha256": race_dump_sha,
        "decompressed_bytes": len(decompressed), "gsdump_header": {
            "marker": f"0x{marker:08x}", "header_size": header_size,
            "state_version": state_version, "initial_gs_state_bytes": state_size,
            "serial": decompressed[8 + serial_offset:8 + serial_offset + serial_size].decode("ascii", errors="replace"),
            "disc_crc": f"0x{dump_crc:08x}", "screenshot_dimensions": [sw, sh],
            "initial_gs_private_regs_bytes": 0x2000,
        },
        "record_counts": event_counts, "transfer_path_bytes": {str(k): sum(len(d) for pth, d in transfers if pth == k) for k in sorted({pth for pth, _ in transfers})},
        "gif_tag_counts": tag_stats,
        "xyz_st_rgba_geometry_tag_count": draw_count,
        "observed_geometry_prim_counts": draw_prim_counts,
        "decoded_vertex_count": vertex_count,
        "xyzf2_adc_bit_counts": adc_counts,
        "xyzf2_adc_bit_definition": "PCSX2 GSRegs.h packed XYZF2 U32[3] bit15; script reads qword byte offset +12, bit15.",
        "topology_triangle_count_by_gif_primitive": topology_triangle_counts,
        "first_32_xyzf2_packet_samples": xyzf2_samples,
        "geometry_tags_by_TEX0_1": draw_tex0_counts,
        "geometry_tags_by_TEX0_1_TBP0": draw_texture_base_counts,
        "geometry_tags_by_material_context": draw_context_counts,
        "first_64_geometry_tags": draw_records,
        "a_d_values_seen": {hex(reg): vals for reg, vals in ad_values.items()},
        "claim_limit": "The dump records raw GS-bound GIF transfer data for a frame. Descriptor 0x412 is decoded in transfer order as STQ, RGBAQ, XYZF2. Triangle-strip/fan primitive counts and XYZF2 ADC bit values are exact frame-wide decode facts, not car-specific assignment. Vertex positions are raw 12.4 X/Y, Z24, and F8 fields; source-to-GS attribute lane identity and per-car packet selection remain open.",
    }

    # Compare every loaded candidate vehicle texture mip byte plane against
    # individual IMAGE GIF tags. These are exact byte searches only; negatives
    # mean no full plane occurs in one captured IMAGE payload and do not rule
    # out transformed, split, or non-captured uploads.
    joins_doc = json.loads(joins_path.read_text(encoding="utf-8"))
    model_rows = []
    for car in joins_doc["cars"]:
        candidates = sorted(glob.glob(f"ford-racing-2/cars/{car['car']}/model/*PS2;1"))
        if len(candidates) != 1:
            model_rows.append({"car": car["car"], "model_paths": candidates, "result": "unresolved_model_path"})
            continue
        path = Path(candidates[0])
        raw_model = path.read_bytes()
        car_obj = car["joins"][0]["objects"][0]
        car_texture_table = car_obj["texture_pointer_table"]
        sys.path.insert(0, str(re_tools))
        try:
            import ps2_container  # type: ignore
            model_textures = ps2_container.parse(raw_model)["textures"]["items"]
        finally:
            sys.path.pop(0)
        texture_planes = []
        for item in model_textures:
            runtime_ptr = struct.unpack_from("<I", ee_mem, car_texture_table + 4 * item["index"])[0]
            runtime_obj = ee_mem[runtime_ptr:runtime_ptr + 0x40] if 0 < runtime_ptr <= len(ee_mem) - 0x40 else b""
            runtime_tex_base = struct.unpack_from("<H", runtime_obj, 4)[0] if len(runtime_obj) >= 6 else None
            for level in item["levels"]:
                plane = raw_model[level["offset"]:level["offset"] + level["size"]]
                image_hits = [img for img in image_transfers if plane and plane in img["payload"]]
                texture_planes.append({
                    "texture_index": item["index"], "name": item["name"],
                    "format": item["format"], "level": level["level"],
                    "dimensions": [level["width"], level["height"]],
                    "source_plane_offset": level["offset"], "source_plane_bytes": len(plane),
                    "source_plane_sha256": hashlib.sha256(plane).hexdigest(),
                    "runtime_pointer_table_address": car_texture_table + 4 * item["index"],
                    "runtime_texture_object_pointer": runtime_ptr,
                    "runtime_object_u16_at_plus4_candidate_TBP0": runtime_tex_base,
                    "geometry_tag_count_sharing_object_plus4_TBP0": draw_texture_base_counts.get(hex(runtime_tex_base), 0) if runtime_tex_base is not None else 0,
                    "exact_raw_plane_in_image_gif_payload": bool(image_hits),
                    "matching_image_packets": [
                        {k: v for k, v in img.items() if k != "payload"}
                        for img in image_hits
                    ],
                    "negative_meaning": None if image_hits else "No complete raw source plane found inside an individual captured FLG=IMAGE payload; transformed, split, or uncaptured uploads remain possible.",
                })
        model_rows.append({
            "car": car["car"], "model_path": str(path), "model_sha256": sha256(path),
            "runtime_texture_pointer_table": car_texture_table,
            "texture_count": len(model_textures), "mip_plane_count": len(texture_planes),
            "raw_full_plane_upload_hits": sum(row["exact_raw_plane_in_image_gif_payload"] for row in texture_planes),
            "texture_planes": texture_planes,
        })
    race_checks["gs_image_uploads"] = {
        "image_tag_count": len(image_transfers),
        "total_image_payload_bytes": sum(len(img["payload"]) for img in image_transfers),
        "records": [{k: v for k, v in img.items() if k != "payload"} for img in image_transfers],
        "source_candidate_cars_from_parent_join": model_rows,
        "claim_limit": "A positive hit is exact full-plane identity within one captured GIF IMAGE payload and retains that packet's prior BITBLTBUF/TRX registers. It shows byte transfer, not final GS texture interpretation or a specific draw's TEX0 use. A negative only excludes the complete raw plane from each individual IMAGE payload; transformed/split data, mip residency at another time, and non-captured uploads remain possible.",
    }
    upload_to_draw = []
    for model_row in model_rows:
        for plane in model_row.get("texture_planes", []):
            if not plane["exact_raw_plane_in_image_gif_payload"]:
                continue
            for hit in plane["matching_image_packets"]:
                bitblt = hit["gs_transfer_registers"].get("0x50")
                if bitblt is None:
                    dbp = None
                    matching_tex0 = {}
                    draw_tags = 0
                else:
                    dbp = (int(bitblt, 16) >> 32) & 0x3FFF
                    draw_tags = draw_texture_base_counts.get(hex(dbp), 0)
                    matching_tex0 = {
                        tex0: count for tex0, count in draw_tex0_counts.items()
                        if tex0 != "unset" and (int(tex0, 16) & 0x3FFF) == dbp
                    }
                upload_to_draw.append({
                    "car": model_row["car"], "texture_index": plane["texture_index"],
                    "texture_name": plane["name"], "mip_level": plane["level"],
                    "source_plane_sha256": plane["source_plane_sha256"],
                    "image_packet_transfer_index": hit["transfer_index"],
                    "image_packet_offset": hit["offset"],
                    "image_bitbltbuf": bitblt,
                    "image_trxreg": hit["gs_transfer_registers"].get("0x52"),
                    "destination_dbp_blocks_256b": dbp,
                    "geometry_tag_count_sharing_TBP0": draw_tags,
                    "matching_TEX0_1_values": matching_tex0,
                })
    race_checks["gs_image_uploads"]["positive_upload_to_draw_TBP0_candidates"] = upload_to_draw
    lifetime_rows = []
    for relation in upload_to_draw:
        dbp = relation["destination_dbp_blocks_256b"]
        if dbp is None:
            continue
        image = next((item for item in image_transfers if item["transfer_index"] == relation["image_packet_transfer_index"] and item["offset"] == relation["image_packet_offset"]), None)
        if image is None:
            continue
        span_blocks = (image["payload_bytes"] + 255) // 256
        later_overlaps = []
        for item in image_transfers:
            if item["transfer_index"] <= relation["image_packet_transfer_index"]:
                continue
            bitblt = item["gs_transfer_registers"].get("0x50")
            if bitblt is None:
                continue
            other_dbp = (int(bitblt, 16) >> 32) & 0x3FFF
            if dbp <= other_dbp < dbp + span_blocks:
                later_overlaps.append({
                    "transfer_index": item["transfer_index"], "offset": item["offset"],
                    "destination_dbp_blocks_256b": other_dbp, "payload_bytes": item["payload_bytes"],
                    "gs_transfer_registers": item["gs_transfer_registers"],
                })
        later_overlaps.sort(key=lambda row: (row["transfer_index"], row["offset"]))
        stop_at = later_overlaps[0]["transfer_index"] if later_overlaps else None
        interval = [
            event for event in draw_packet_events
            if event["tbp0"] == dbp and event["transfer_index"] > relation["image_packet_transfer_index"] and (stop_at is None or event["transfer_index"] < stop_at)
        ]
        lifetime_rows.append({
            "car": relation["car"], "texture_index": relation["texture_index"],
            "texture_name": relation["texture_name"], "mip_level": relation["mip_level"],
            "source_plane_sha256": relation["source_plane_sha256"],
            "upload_transfer_index": relation["image_packet_transfer_index"],
            "destination_dbp_blocks_256b": dbp,
            "approx_span_blocks_from_image_payload_bytes": span_blocks,
            "first_later_image_packet_with_start_DBP_inside_approx_span": later_overlaps[0] if later_overlaps else None,
            "draw_tag_count_after_upload_until_candidate_overwrite": len(interval),
            "TEX0_1_values": dict(__import__("collections").Counter(row["tex0_1"] for row in interval)),
            "draw_packet_events": interval,
        })
    race_checks["gs_image_uploads"]["source_plane_lifetimes_before_candidate_overwrite"] = lifetime_rows
    # Compact, reproducible source-header/GS packet join. The raw per-tag
    # candidate rows above are retained; this summary adds uniqueness counts,
    # other-car negatives, and an in-memory one-unit UV corruption control.
    cobra_model = next(row for row in model_rows if row.get("car") == "COBRA")
    cobra_path = Path(cobra_model["model_path"])
    cobra_bytes = cobra_path.read_bytes()
    sys.path.insert(0, str(re_tools))
    try:
        import ps2_container  # type: ignore
        import ps2_sections  # type: ignore
        cobra_parsed = ps2_sections.parse(cobra_bytes)
        other_models = {}
        for row in model_rows:
            if row.get("car") == "COBRA" or not row.get("model_path"):
                continue
            other_bytes = Path(row["model_path"]).read_bytes()
            other_models[row["car"]] = (other_bytes, ps2_sections.parse(other_bytes))
    finally:
        sys.path.pop(0)

    cobra_lifetime = next(
        row for row in lifetime_rows
        if row["car"] == "COBRA" and row["texture_index"] == 0 and row["mip_level"] == 0
    )
    matched_tags = []
    unique_header_count = 0
    ambiguous_header_count = 0
    no_match_count = 0
    mutation_rejected = 0
    adc_lane_histograms = {f"byte{lane}_bit{bit}": {"matches": 0, "total": 0} for lane in range(4) for bit in range(8)}
    unique_adc_pair_counts = {f"source{source_bit}_adc{adc_bit}": 0 for source_bit in range(2) for adc_bit in range(2)}
    adc_projected_area_summary = {
        "unique_header_vertex_events": 0,
        "unique_header_adc_mismatches": 0,
        "mismatch_vertices_with_any_negative_incident_strip_area": 0,
        "mismatch_vertices_with_any_positive_incident_strip_area": 0,
        "mismatch_vertices_with_only_zero_incident_strip_areas": 0,
        "mismatch_categories": {"source0_adc1": 0, "source1_adc0": 0},
        "source_adc_pair_projected_signs": {
            f"source{source_bit}_adc{adc_bit}": {"vertices": 0, "any_negative": 0, "any_positive": 0, "both_signs": 0, "zero_only": 0,
                "would_be_current_strip_triangle": {"negative": 0, "zero": 0, "positive": 0, "not_enough_prior_vertices": 0},
                "source_current_strip_triangle": {"negative": 0, "zero": 0, "positive": 0, "not_enough_prior_vertices": 0}}
            for source_bit in range(2) for adc_bit in range(2)
        },
        "source_v3_16_vs_screen_xy_strip_orientation": {"comparable_triangles": 0, "same_nonzero_sign": 0, "opposite_nonzero_sign": 0, "source_zero": 0, "screen_zero": 0},
    }
    per_other_car = {}
    rgbaq_packet_summary = {
        "bounded_interval_tag_count": 0,
        "bounded_interval_vertex_count": 0,
        "distinct_decoded_rgba8_values": 0,
        "uniform_rgba8_tags": 0,
        "nonuniform_rgba8_tags": 0,
        "alpha_byte_counts": {},
        "green_nonzero_vertex_count": 0,
        "blue_nonzero_vertex_count": 0,
        "claim_limit": "These are the four low bytes of the four lanes in a packed GIF RGBA qword (FLG=0), following pinned PCSX2 GIFPackedRegHandlerRGBA behavior. Q is separately read from the third float of the preceding STQ qword. Source-generation, shading, and material derivation are not joined; raw 16-byte records and lane words are retained.",
    }
    rgbaq_colors = set()
    rgbaq_alpha_counts = {}
    source_colorflow = {
        "candidate_scope": "Bounded COBRA index-0 tags with an exact ordered UV/header match are used only when every matching header has the same four-byte source plane. Duplicate-UV headers are retained when their four-byte planes are byte-identical; no source→VU runtime dispatch is presumed.",
        "unique_header_tag_count": 0,
        "byte_equivalent_attribute_tag_count": 0,
        "ambiguous_header_tags_with_byte_equivalent_four_byte_planes": 0,
        "vertex_pair_count": 0,
        "source_attr_rgb_exactly_equals_packet_rgb_vertices": 0,
        "ambiguous_header_four_byte_plane_mismatches": [],
        "per_tag": [],
        "global_signed8_xyz_to_rgb_linear_r2": {channel: None for channel in "rgb"},
        "global_unsigned8_lane0_2_to_rgb_linear_r2": {channel: None for channel in "rgb"},
        "global_signed8_xyz_to_rgb_linear_coefficients": {},
        "per_tag_rgb_slope_direction_cosines": [],
        "claim_limit": "Statistical association tests do not establish live VU dispatch or an exact color-generation equation. Source and packet observations are joined by exact UV candidates whose four-byte planes are byte-identical, not by a runtime source→VU→packet trace.",
    }
    colorflow_signed_features: list[list[float]] = []
    colorflow_unsigned_features: list[list[float]] = []
    colorflow_targets = {channel: [] for channel in "rgb"}
    for event in cobra_lifetime["draw_packet_events"]:
        colors = [tuple(vertex["rgba8"]) for vertex in event["rgbaq_full"]]
        rgbaq_packet_summary["bounded_interval_tag_count"] += 1
        rgbaq_packet_summary["bounded_interval_vertex_count"] += len(colors)
        rgbaq_packet_summary["uniform_rgba8_tags"] += int(len(set(colors)) == 1)
        rgbaq_packet_summary["nonuniform_rgba8_tags"] += int(len(set(colors)) > 1)
        rgbaq_colors.update(colors)
        for color in colors:
            rgbaq_alpha_counts[str(color[3])] = rgbaq_alpha_counts.get(str(color[3]), 0) + 1
            rgbaq_packet_summary["green_nonzero_vertex_count"] += int(color[1] != 0)
            rgbaq_packet_summary["blue_nonzero_vertex_count"] += int(color[2] != 0)
        exact = [candidate for candidate in event["source_uv_header_candidates"] if candidate["uv_exact_match_at_1e-6"]]
        if len(exact) == 1:
            unique_header_count += 1
            source_colorflow["unique_header_tag_count"] += 1
        elif len(exact) > 1:
            ambiguous_header_count += 1
        else:
            no_match_count += 1
        if exact:
            plane_candidates = []
            for candidate in exact:
                candidate_header = cobra_parsed["geometry"]["headers"][candidate["source_header_index"]]
                candidate_plane = candidate_header["planes"].get("four_byte")
                if not candidate_plane or candidate_plane["size"] != event["nloop"] * 4:
                    plane_candidates = []
                    break
                candidate_bytes = cobra_bytes[candidate_plane["offset"]:candidate_plane["offset"] + candidate_plane["size"]]
                plane_candidates.append((candidate["source_header_index"], candidate_bytes))
            if plane_candidates and len({plane_bytes for _, plane_bytes in plane_candidates}) == 1:
                source_colorflow["byte_equivalent_attribute_tag_count"] += 1
                if len(exact) > 1:
                    source_colorflow["ambiguous_header_tags_with_byte_equivalent_four_byte_planes"] += 1
                source_four = plane_candidates[0][1]
                attrs = [list(source_four[i:i + 4]) for i in range(0, len(source_four), 4)]
                colors = [vertex["rgba8"] for vertex in event["rgbaq_full"]]
                if len(attrs) == len(colors):
                    source_colorflow["vertex_pair_count"] += len(attrs)
                    exact_rgb = sum(attr[:3] == color[:3] for attr, color in zip(attrs, colors))
                    source_colorflow["source_attr_rgb_exactly_equals_packet_rgb_vertices"] += exact_rgb
                    signed = [[1.0, *(v if v < 128 else v - 256 for v in attr[:3])] for attr in attrs]
                    unsigned = [[1.0, *attr[:3]] for attr in attrs]
                    for row, color in zip(signed, colors):
                        colorflow_signed_features.append(row)
                        for channel, value in zip("rgb", color[:3]):
                            colorflow_targets[channel].append(float(value))
                    colorflow_unsigned_features.extend(unsigned)
                    fit_signed = {channel: linear_fit(signed, [float(color[i]) for color in colors]) for i, channel in enumerate("rgb")}
                    fit_unsigned = {channel: linear_fit(unsigned, [float(color[i]) for color in colors]) for i, channel in enumerate("rgb")}
                    slope_vectors = [fit_signed[c]["coefficients"][1:] for c in "rgb" if fit_signed[c]]
                    pair_cosines = []
                    for left_index in range(len(slope_vectors)):
                        for right_index in range(left_index + 1, len(slope_vectors)):
                            left, right = slope_vectors[left_index], slope_vectors[right_index]
                            left_norm = sum(x * x for x in left) ** 0.5
                            right_norm = sum(x * x for x in right) ** 0.5
                            if left_norm > 1e-9 and right_norm > 1e-9:
                                pair_cosines.append(sum(a * b for a, b in zip(left, right)) / (left_norm * right_norm))
                    if pair_cosines:
                        source_colorflow["per_tag_rgb_slope_direction_cosines"].append({
                            "transfer_index": event["transfer_index"],
                            "rgb_channel_slope_cosines": pair_cosines,
                            "mean_cosine": sum(pair_cosines) / len(pair_cosines),
                        })
                    source_colorflow["per_tag"].append({
                        "transfer_index": event["transfer_index"],
                        "source_header_indices_with_byte_identical_four_byte_plane": [header_index for header_index, _ in plane_candidates],
                        "ordered_uv_header_candidate_cardinality": len(exact),
                        "vertices": len(attrs),
                        "source_four_byte_sha256": hashlib.sha256(source_four).hexdigest(),
                        "attribute_rgb_equals_packet_rgb_vertices": exact_rgb,
                        "signed8_xyz_linear_fit_r2": {channel: (fit_signed[channel]["r2"] if fit_signed[channel] else None) for channel in "rgb"},
                        "signed8_xyz_linear_coefficients": {channel: (fit_signed[channel]["coefficients"] if fit_signed[channel] else None) for channel in "rgb"},
                        "unsigned8_lane_xyz_linear_fit_r2": {channel: (fit_unsigned[channel]["r2"] if fit_unsigned[channel] else None) for channel in "rgb"},
                    })
            elif plane_candidates and len(exact) > 1:
                source_colorflow["ambiguous_header_four_byte_plane_mismatches"].append({
                    "transfer_index": event["transfer_index"],
                    "source_header_indices": [header_index for header_index, _ in plane_candidates],
                    "source_four_byte_sha256s": [hashlib.sha256(plane_bytes).hexdigest() for _, plane_bytes in plane_candidates],
                })
        matched_tags.append({
            "transfer_index": event["transfer_index"], "nloop": event["nloop"],
            "exact_source_header_indices": [candidate["source_header_index"] for candidate in exact],
            "exact_uv_plane_sha256s": sorted({candidate["uv_plane_sha256"] for candidate in exact}),
            "max_error_best_candidate": min(
                (candidate["stq_over_q_vs_signed16_div_2048_max_absolute_error"] for candidate in event["source_uv_header_candidates"]),
                default=None,
            ),
        })
        # Perturb a copied signed16 UV pair by +1. The unmodified packet
        # remains untouched; this control must exceed the exact-match limit.
        if exact:
            candidate = exact[0]
            header = cobra_parsed["geometry"]["headers"][candidate["source_header_index"]]
            plane = header["planes"]["third_four_byte"]
            first_u, first_v = struct.unpack_from("<hh", cobra_bytes, plane["offset"])
            mutated_u = first_u + 1 if first_u < 32767 else first_u - 1
            # Only the perturbed first source coordinate is needed to test the
            # equality gate; use packet STQ ratio from the event candidate's
            # stored sample, which is in source units after divide by Q.
            packet_stq = next(
                item for item in draw_packet_events
                if item["transfer_index"] == event["transfer_index"]
            )["vertices_sample"][0]
            packet_u = packet_stq["s"] / packet_stq["q"] if packet_stq["q"] else float("inf")
            mutated_error = abs(packet_u - mutated_u / 2048.0)
            if mutated_error > 1e-6:
                mutation_rejected += 1

        # Compare independent source candidates from each other car at the
        # same source texture index and matching vertex count. Report best
        # errors; do not treat shared TBP0 alone as a vehicle identity.
        for car_name, (other_bytes, other_parsed) in other_models.items():
            errors = []
            for header in other_parsed["geometry"]["headers"]:
                if header["third"] != 0 or header["count"] != event["nloop"]:
                    continue
                plane = header["planes"].get("third_four_byte")
                if not plane or plane["size"] != event["nloop"] * 4:
                    continue
                max_error = 0.0
                for packet_vertex, (u_raw, v_raw) in zip(
                    event["vertices_sample"] if len(event["vertices_sample"]) == event["nloop"] else [],
                    struct.iter_unpack("<hh", other_bytes[plane["offset"]:plane["offset"] + plane["size"]]),
                ):
                    q = packet_vertex["q"]
                    if q == 0.0:
                        max_error = float("inf")
                        break
                    max_error = max(max_error, abs(packet_vertex["s"] / q - u_raw / 2048.0), abs(packet_vertex["t"] / q - v_raw / 2048.0))
                if event["nloop"] > 8:
                    # The event retains only an 8-vertex sample. Score the
                    # candidate over that same ordered prefix, explicitly
                    # labelled a partial negative control.
                    max_error = 0.0
                    for packet_vertex, (u_raw, v_raw) in zip(
                        event["vertices_sample"],
                        struct.iter_unpack("<hh", other_bytes[plane["offset"]:plane["offset"] + min(plane["size"], 32)]),
                    ):
                        q = packet_vertex["q"]
                        if q == 0.0:
                            max_error = float("inf")
                            break
                        max_error = max(max_error, abs(packet_vertex["s"] / q - u_raw / 2048.0), abs(packet_vertex["t"] / q - v_raw / 2048.0))
                errors.append(max_error)
            if errors:
                item = per_other_car.setdefault(car_name, {"comparable_tag_count": 0, "prefix_exact_tag_count_at_1e-6": 0, "best_error_by_transfer": []})
                item["comparable_tag_count"] += 1
                best = min(errors)
                item["prefix_exact_tag_count_at_1e-6"] += best <= 1e-6
                item["best_error_by_transfer"].append({"transfer_index": event["transfer_index"], "max_error_over_first_eight_vertices": best})

        for candidate in exact:
            matches = candidate.get("four_byte_lane_bit_matches_xyzf2_ADC_vertices") or {}
            for bit_key, match_count in matches.items():
                histogram = adc_lane_histograms[bit_key]
                histogram["matches"] += match_count
                histogram["total"] += event["nloop"]
        if len(exact) == 1:
            candidate = exact[0]
            for key, value in (candidate.get("source_four_byte_lane3_bit0_to_xyzf2_ADC_pairs") or {}).items():
                unique_adc_pair_counts[key] += value
            source_header = cobra_parsed["geometry"]["headers"][candidate["source_header_index"]]
            four_plane = source_header["planes"].get("four_byte")
            emitted_adc = event.get("xyzf2_adc_full")
            screen_xy = event.get("screen_xy_12_4_full")
            if four_plane and emitted_adc and screen_xy and len(emitted_adc) == len(screen_xy) == event["nloop"]:
                source_four = cobra_bytes[four_plane["offset"]:four_plane["offset"] + four_plane["size"]]
                source_bits = [source_four[i * 4 + 3] & 1 for i in range(event["nloop"])]
                areas = []
                source_position_plane = source_header["planes"].get("six_byte")
                source_positions = None
                if source_position_plane and source_position_plane["size"] == event["nloop"] * 6:
                    source_positions = list(struct.iter_unpack(
                        "<hhh", cobra_bytes[source_position_plane["offset"]:source_position_plane["offset"] + source_position_plane["size"]]
                    ))
                incident_area_signs = [[] for _ in emitted_adc]
                for tri in range(event["nloop"] - 2):
                    ids = [tri, tri + 1, tri + 2] if tri % 2 == 0 else [tri + 1, tri, tri + 2]
                    (x0, y0), (x1, y1), (x2, y2) = (screen_xy[index] for index in ids)
                    area = (x1 - x0) * (y2 - y0) - (y1 - y0) * (x2 - x0)
                    sign = (area > 0) - (area < 0)
                    areas.append(area)
                    for index in ids:
                        incident_area_signs[index].append(sign)
                    if source_positions is not None:
                        (sx0, sy0, _), (sx1, sy1, _), (sx2, sy2, _) = (source_positions[index] for index in ids)
                        source_area = (sx1 - sx0) * (sy2 - sy0) - (sy1 - sy0) * (sx2 - sx0)
                        source_sign = (source_area > 0) - (source_area < 0)
                        orientation = adc_projected_area_summary["source_v3_16_vs_screen_xy_strip_orientation"]
                        orientation["comparable_triangles"] += 1
                        if source_sign == 0:
                            orientation["source_zero"] += 1
                        elif sign == 0:
                            orientation["screen_zero"] += 1
                        elif source_sign == sign:
                            orientation["same_nonzero_sign"] += 1
                        else:
                            orientation["opposite_nonzero_sign"] += 1
                adc_projected_area_summary["unique_header_vertex_events"] += event["nloop"]
                for index, (source_bit, adc_bit) in enumerate(zip(source_bits, emitted_adc)):
                    pair_summary = adc_projected_area_summary["source_adc_pair_projected_signs"][f"source{source_bit}_adc{adc_bit}"]
                    pair_summary["vertices"] += 1
                    signs = incident_area_signs[index]
                    has_negative = -1 in signs
                    has_positive = 1 in signs
                    pair_summary["any_negative"] += has_negative
                    pair_summary["any_positive"] += has_positive
                    pair_summary["both_signs"] += has_negative and has_positive
                    pair_summary["zero_only"] += bool(signs) and not has_negative and not has_positive
                    current_tri = index - 2
                    current_area = None
                    if current_tri >= 0:
                        ids = [current_tri, current_tri + 1, current_tri + 2] if current_tri % 2 == 0 else [current_tri + 1, current_tri, current_tri + 2]
                        (x0, y0), (x1, y1), (x2, y2) = (screen_xy[vertex] for vertex in ids)
                        current_area = (x1 - x0) * (y2 - y0) - (y1 - y0) * (x2 - x0)
                        area_key = "positive" if current_area > 0 else "negative" if current_area < 0 else "zero"
                        pair_summary["would_be_current_strip_triangle"][area_key] += 1
                        if source_positions is not None:
                            (sx0, sy0, _), (sx1, sy1, _), (sx2, sy2, _) = (source_positions[vertex] for vertex in ids)
                            source_current_area = (sx1 - sx0) * (sy2 - sy0) - (sy1 - sy0) * (sx2 - sx0)
                            source_area_key = "positive" if source_current_area > 0 else "negative" if source_current_area < 0 else "zero"
                            pair_summary["source_current_strip_triangle"][source_area_key] += 1
                        else:
                            source_area_key = None
                    else:
                        pair_summary["would_be_current_strip_triangle"]["not_enough_prior_vertices"] += 1
                        source_area_key = None
                    if source_bit == adc_bit:
                        continue
                    mismatch_key = f"source{source_bit}_adc{adc_bit}"
                    adc_projected_area_summary["unique_header_adc_mismatches"] += 1
                    adc_projected_area_summary["mismatch_categories"][mismatch_key] += 1
                    if current_area is not None:
                        area_key = "positive" if current_area > 0 else "negative" if current_area < 0 else "zero"
                        adc_projected_area_summary.setdefault("mismatch_current_strip_triangle_area_signs", {"source0_adc1": {"negative": 0, "zero": 0, "positive": 0}, "source1_adc0": {"negative": 0, "zero": 0, "positive": 0}})
                        adc_projected_area_summary["mismatch_current_strip_triangle_area_signs"][mismatch_key][area_key] += 1
                        if source_area_key is not None:
                            adc_projected_area_summary.setdefault("mismatch_source_strip_triangle_area_signs", {"source0_adc1": {"negative": 0, "zero": 0, "positive": 0}, "source1_adc0": {"negative": 0, "zero": 0, "positive": 0}})
                            adc_projected_area_summary["mismatch_source_strip_triangle_area_signs"][mismatch_key][source_area_key] += 1
                    if has_negative:
                        adc_projected_area_summary["mismatch_vertices_with_any_negative_incident_strip_area"] += 1
                    if has_positive:
                        adc_projected_area_summary["mismatch_vertices_with_any_positive_incident_strip_area"] += 1
                    if not signs or not has_negative and not has_positive:
                        adc_projected_area_summary["mismatch_vertices_with_only_zero_incident_strip_areas"] += 1
                adc_projected_area_summary.setdefault("strip_triangle_area_sign_counts", {"negative": 0, "zero": 0, "positive": 0})
                for area in areas:
                    sign_key = "positive" if area > 0 else "negative" if area < 0 else "zero"
                    adc_projected_area_summary["strip_triangle_area_sign_counts"][sign_key] += 1

    rgbaq_packet_summary["distinct_decoded_rgba8_values"] = len(rgbaq_colors)
    rgbaq_packet_summary["alpha_byte_counts"] = rgbaq_alpha_counts
    for channel_index, channel in enumerate("rgb"):
        global_fit = linear_fit(colorflow_signed_features, colorflow_targets[channel])
        source_colorflow["global_signed8_xyz_to_rgb_linear_r2"][channel] = global_fit["r2"] if global_fit else None
        source_colorflow["global_signed8_xyz_to_rgb_linear_coefficients"][channel] = global_fit["coefficients"] if global_fit else None
        source_colorflow["global_unsigned8_lane0_2_to_rgb_linear_r2"][channel] = linear_r2(
            colorflow_unsigned_features, colorflow_targets[channel])

    def fixed_xy_fit(source_positions: list[tuple[int, int, int]], packet_xy: list[list[int]]) -> dict[str, object]:
        if len(source_positions) != len(packet_xy) or len(source_positions) < 5:
            raise ValueError("position-fit inputs do not align")
        features = [[x / 16384.0, y / 16384.0, z / 16384.0, 1.0]
                    for x, y, z in source_positions]
        axes = {}
        for axis, name in enumerate(("x", "y")):
            fit = linear_fit(features, [point[axis] for point in packet_xy])
            if fit is None:
                raise ValueError("source-to-screen affine fit is rank deficient")
            residuals = [point[axis] - sum(a * b for a, b in zip(row, fit["coefficients"]))
                         for row, point in zip(features, packet_xy)]
            axes[name] = {
                "coefficients_for_xyz_over_16384_plus_intercept": fit["coefficients"],
                "rms_residual_gs_fixed_12_4_units": (sum(value * value for value in residuals) / len(residuals)) ** 0.5,
                "max_abs_residual_gs_fixed_12_4_units": max(abs(value) for value in residuals),
            }
        return {"axes": axes,
                "max_abs_residual_over_xy_gs_fixed_12_4_units": max(row["max_abs_residual_gs_fixed_12_4_units"] for row in axes.values()),
                "claim_limit": "An affine fit to projected screen XY is a bounded source-position relation; it is not recovery of the complete camera or model transform."}

    material_tags = [event for event in cobra_lifetime["draw_packet_events"]
                     if event["nloop"] == 7
                     and event["rgbaq_full"]
                     and all(vertex["rgba8"] == [0, 0, 0, 102] for vertex in event["rgbaq_full"])]
    if len(material_tags) != 1:
        raise ValueError(f"expected one 7-vertex constant-alpha packet, got {len(material_tags)}")
    material_event = material_tags[0]
    glass_candidates = []
    for header_index, header in enumerate(cobra_parsed["geometry"]["headers"]):
        if header["count"] != 7 or header["flags"] != 0xC01A:
            continue
        color_word, = struct.unpack_from("<I", cobra_bytes, header["offset"] + 8)
        if color_word != 0x66000000:
            continue
        position_plane = header["planes"]["six_byte"]
        position_raw = cobra_bytes[position_plane["offset"]:position_plane["offset"] + position_plane["size"]]
        positions = list(struct.iter_unpack("<hhh", position_raw))
        if len(positions) != 7:
            raise ValueError("7-vertex material source position plane has wrong size")
        fit = fixed_xy_fit(positions, material_event["screen_xy_12_4_full"])
        glass_candidates.append({
            "source_header_index": header_index,
            "source_header_offset": header["offset"],
            "header_flags": f"0x{header['flags']:04x}",
            "vertex_count": header["count"],
            "header_base_rgba_word_offset": header["offset"] + 8,
            "header_base_rgba_word_u32": f"0x{color_word:08x}",
            "header_base_rgba_decoded": [color_word & 0xff, (color_word >> 8) & 0xff,
                                          (color_word >> 16) & 0xff, (color_word >> 24) & 0xff],
            "position_plane_offset": position_plane["offset"],
            "position_plane_sha256": hashlib.sha256(position_raw).hexdigest(),
            "positions_s16_xyz": [list(point) for point in positions],
            "position_to_packet_screen_xy_fit": fit,
        })
    if not glass_candidates:
        raise ValueError("no COBRA c01a/7 source-header candidates with base color 0x66000000")
    material_prim = prim_fields(material_event["prim"])
    material_alpha = alpha_fields(int(material_event["alpha_1"], 16))
    unmatched_material_join = {
        "gs_transfer_index": material_event["transfer_index"],
        "source_uv_candidates": material_event["source_uv_header_candidates"],
        "vertex_count": material_event["nloop"],
        "gs_prim_raw": f"0x{material_event['prim']:x}",
        "gs_prim_fields": material_prim,
        "gs_tex0_raw": material_event["tex0_1"],
        "gs_texture_enabled_by_prim": bool(material_prim["tme"]),
        "gs_alpha_raw": material_event["alpha_1"],
        "gs_alpha_selectors": material_alpha,
        "gs_blend_equation": "(Cs - Cd) * As + Cd; source alpha participates in the blend",
        "rgba8_per_vertex": [vertex["rgba8"] for vertex in material_event["rgbaq_full"]],
        "projected_screen_xy_12_4": material_event["screen_xy_12_4_full"],
        "source_header_candidates": glass_candidates,
        "base_color_cpu_lane_evidence": {
            "raw_instruction_checks": material_instruction_checks,
            "candidate_headers_all_bit0_clear": all((header["flags"] & 1) == 0 for header in cobra_parsed["geometry"]["headers"] if header["count"] == 7 and header["flags"] == 0xC01A),
            "bounded_formula": "The source header word decodes as RGBA [0,0,0,102]. Raw EE PEXT/PEXEW reorder packed lanes; 0xc01a bit 0 is clear, selecting vmulx.w only. Packet alpha 102 is consistent with the unscaled source W byte, but runtime DAT_70003560*FLOAT_0028f1e8 and producer-to-packet call are not captured, so no exact alpha transfer is asserted.",
        },
        "candidate_position_plane_distinct_sha256_count": len({row["position_plane_sha256"] for row in glass_candidates}),
        "position_relation_gate_max_abs_error_0_25_fixed_units": max(
            row["position_to_packet_screen_xy_fit"]["max_abs_residual_over_xy_gs_fixed_12_4_units"]
            for row in glass_candidates) <= 0.25,
        "interpretation": "This source-to-packet join recovers the seven-vertex untextured blended material. The two source headers are duplicate position/color candidates, so the exact header ID remains ambiguous; the captured blend uses constant black RGB and alpha 102.",
        "claim_limit": "The strong projected-position fit and exact packed base-color match identify source geometry/material bytes for this GS packet. This does not identify the semantic object name (for example windshield versus window), or establish the exact perceived opacity after GS/framebuffer behavior.",
    }
    race_checks["source_packet_match_summary"] = {
        "basis": "COBRA source geometry header texture-index field 0 and ordered signed16 V2 plane divided by 2048 compared against packed STQ S/Q,T/Q in the exact COBRA index-0 source-plane upload lifetime.",
        "texture_lifetime_upload_transfer_index": cobra_lifetime["upload_transfer_index"],
        "candidate_overwrite_transfer_index": cobra_lifetime["first_later_image_packet_with_start_DBP_inside_approx_span"]["transfer_index"] if cobra_lifetime["first_later_image_packet_with_start_DBP_inside_approx_span"] else None,
        "candidate_overwrite_is_approximate": True,
        "geometry_tags_in_interval": len(cobra_lifetime["draw_packet_events"]),
        "uv_exact_tags_at_1e-6": len(cobra_lifetime["draw_packet_events"]) - no_match_count,
        "exact_tag_header_cardinality": {"one": unique_header_count, "multiple": ambiguous_header_count, "zero": no_match_count},
        "per_tag_matches": matched_tags,
        "in_memory_uv_plus_or_minus_one_source_unit_control": {"tested_exact_tags": unique_header_count + ambiguous_header_count, "rejected_by_1e-6_gate": mutation_rejected, "expected_error_floor": 1 / 2048},
        "other_car_source_index0_first_eight_uv_negative_controls": per_other_car,
        "rgbaq_output_values": rgbaq_packet_summary,
        "source_v4_8_to_packet_rgb_probe": source_colorflow,
        "unmatched_seven_vertex_blended_material_join": unmatched_material_join,
        "adc_source_lane_bit_correlations": adc_lane_histograms,
        "unique_uv_header_source_lane3_bit0_adc_pairs": unique_adc_pair_counts,
        "unique_uv_header_mismatch_vs_projected_strip_area": adc_projected_area_summary,
        "claim_limit": "Exact ordered UV equality is a strong source-header-to-GS-packet relation, but duplicate source UV planes leave some header IDs ambiguous. Other-car controls compare only the retained first eight packet vertices. Candidate overwrite is based on the first subsequent IMAGE packet whose DBP start lies in a byte-span estimate and is not a complete GS page-overlap proof. ADC/source lane correlations are diagnostic only and do not establish source ADC derivation.",
    }
    packet_summary = race_checks["source_packet_match_summary"]
    packet_controls_ok = (
        packet_summary["geometry_tags_in_interval"] == 106
        and packet_summary["uv_exact_tags_at_1e-6"] == 105
        and packet_summary["exact_tag_header_cardinality"]["one"] == 60
        and packet_summary["exact_tag_header_cardinality"]["multiple"] == 45
        and packet_summary["exact_tag_header_cardinality"]["zero"] == 1
        and packet_summary["in_memory_uv_plus_or_minus_one_source_unit_control"]["rejected_by_1e-6_gate"] == 105
        and all(row["comparable_tag_count"] > 0 and row["prefix_exact_tag_count_at_1e-6"] == 0 for row in per_other_car.values())
        and len(per_other_car) == 5
        and rgbaq_packet_summary["bounded_interval_tag_count"] == 106
        and rgbaq_packet_summary["bounded_interval_vertex_count"] == 5915
        and rgbaq_packet_summary["distinct_decoded_rgba8_values"] > 0
        and rgbaq_packet_summary["uniform_rgba8_tags"] + rgbaq_packet_summary["nonuniform_rgba8_tags"] == 106
        and source_colorflow["unique_header_tag_count"] == 60
        and source_colorflow["byte_equivalent_attribute_tag_count"] == 105
        and source_colorflow["ambiguous_header_tags_with_byte_equivalent_four_byte_planes"] == 45
        and source_colorflow["vertex_pair_count"] == 5908
        and source_colorflow["source_attr_rgb_exactly_equals_packet_rgb_vertices"] == 0
        and not source_colorflow["ambiguous_header_four_byte_plane_mismatches"]
        and all(source_colorflow["global_signed8_xyz_to_rgb_linear_r2"][channel] > source_colorflow["global_unsigned8_lane0_2_to_rgb_linear_r2"][channel] for channel in "rgb")
        and len(glass_candidates) == 2
        and unmatched_material_join["candidate_position_plane_distinct_sha256_count"] == 1
        and unmatched_material_join["position_relation_gate_max_abs_error_0_25_fixed_units"]
        and unmatched_material_join["gs_prim_fields"]["type"] == 4
        and unmatched_material_join["gs_prim_fields"]["tme"] == 0
        and unmatched_material_join["gs_prim_fields"]["abe"] == 1
        and unmatched_material_join["gs_alpha_raw"] == "0x44"
        and all(row["pass"] for row in material_instruction_checks.values())
        and unmatched_material_join["base_color_cpu_lane_evidence"]["candidate_headers_all_bit0_clear"]
        and all(row == [0, 0, 0, 102] for row in unmatched_material_join["rgba8_per_vertex"])
    )
    packet_summary["deterministic_controls_validation"] = {
        "result": "pass" if packet_controls_ok else "fail",
        "checks": {
            "interval_tag_count_106": packet_summary["geometry_tags_in_interval"] == 106,
            "uv_exact_count_105": packet_summary["uv_exact_tags_at_1e-6"] == 105,
            "header_cardinality_60_45_1": packet_summary["exact_tag_header_cardinality"] == {"one": 60, "multiple": 45, "zero": 1},
            "one_unit_mutation_rejected_all_exact_matches": packet_summary["in_memory_uv_plus_or_minus_one_source_unit_control"]["rejected_by_1e-6_gate"] == 105,
            "five_other_car_prefix_controls_reject": len(per_other_car) == 5 and all(row["comparable_tag_count"] > 0 and row["prefix_exact_tag_count_at_1e-6"] == 0 for row in per_other_car.values()),
            "rgbaq_interval_decoded_and_tag_counts": rgbaq_packet_summary["bounded_interval_tag_count"] == 106 and rgbaq_packet_summary["bounded_interval_vertex_count"] == 5915 and rgbaq_packet_summary["distinct_decoded_rgba8_values"] > 0 and rgbaq_packet_summary["uniform_rgba8_tags"] + rgbaq_packet_summary["nonuniform_rgba8_tags"] == 106,
            "all_105_uv_matched_tags_have_unambiguous_or_byte_identical_four_byte_plane": source_colorflow["byte_equivalent_attribute_tag_count"] == 105 and not source_colorflow["ambiguous_header_four_byte_plane_mismatches"],
            "5908_matched_source_attribute_and_packet_rgb_pairs": source_colorflow["vertex_pair_count"] == 5908 and source_colorflow["source_attr_rgb_exactly_equals_packet_rgb_vertices"] == 0,
            "signed8_rgb_fit_exceeds_unsigned8_control_each_channel": all(source_colorflow["global_signed8_xyz_to_rgb_linear_r2"][channel] > source_colorflow["global_unsigned8_lane0_2_to_rgb_linear_r2"][channel] for channel in "rgb"),
            "raw_header_color_lane_masks_and_packet_alpha_match": all(row["pass"] for row in material_instruction_checks.values()) and unmatched_material_join["base_color_cpu_lane_evidence"]["candidate_headers_all_bit0_clear"] and all(row == [0, 0, 0, 102] for row in unmatched_material_join["rgba8_per_vertex"]),
        },
    }
    # Verify independent static invariants for this runtime slice.
    race_state_ok = sha256(args.race_state) == expected_race_sha and all(x["result"] == "pass" for x in race_checks["state"]["entries"].values())
    texture_ok = race_checks["texture_join"]["texture_index_equals_ordered_serialized_record_index"] and race_checks["texture_join"]["all_source_level_zero_planes_found_exactly_in_ee_memory"]
    dump_ok = pos == len(decompressed) and marker == 0xFFFFFFFF and state_version == 9 and draw_count > 0 and not any(key.startswith("flg3_") for key in tag_stats)
    branch_join_ok = (runtime_source_branch_join["runtime_header_pointer_bounds_match_source"]
                      and not runtime_source_branch_join["node_record_dispatch_bit_0x10000"]
                      and runtime_source_branch_join["scratchpad_bytes"] == 16384
                      and runtime_source_branch_join["FUN_00127fa8_scratchpad_batch_count_u32"] == 0)
    race_checks["validation"] = {"result": "pass" if race_state_ok and texture_ok and dump_ok and race_overlay_match and packet_controls_ok and branch_join_ok else "fail", "race_state_hash_match": sha256(args.race_state) == expected_race_sha, "race_entries_exact": race_state_ok, "source_texture_join": texture_ok, "overlay_match": race_overlay_match, "gsdump_decode_complete": dump_ok, "source_packet_uv_and_negative_controls": packet_controls_ok, "runtime_source_pointer_and_branch_boundary": branch_join_ok, "geometry_packet_count": draw_count}
    args.race_output.parent.mkdir(parents=True, exist_ok=True)
    args.race_output.write_text(json.dumps(race_checks, indent=2) + "\n", encoding="utf-8")
    # The advanced race97 micro-memory was captured independently by the
    # parent and is used here only for exact source-image residency tests.
    race97_micro_path = args.race_state.parent.parent / "linux" / "race97-vu1MicroMem.bin"
    race97_overlay_audit = None
    if race97_micro_path.is_file():
        race97_overlay_audit = overlay_residency(race97_micro_path.read_bytes(), args.input_bundle / VU_DIR, "race97 advanced state")
    overlay_receipt = {
        "schema": "fr2-vu-overlay-residency-audit/v1",
        "method": "byte-exact source overlay search at 8-byte-aligned offsets in 16KiB VU1 micro-memory snapshots; hashes and sizes are recorded for each pinned source binary",
        "snapshots": [
            {**loading_overlay_audit, "path": str(runtime_dir / "loading-vu1MicroMem.bin"), "sha256": sha256(runtime_dir / "loading-vu1MicroMem.bin")},
            {**race_overlay_audit, "path": str(args.race_state.parent.parent / "race94-vu1MicroMem.bin"), "sha256": hashlib.sha256(micro).hexdigest()},
        ],
        "race97": {"path": str(race97_micro_path), "sha256": sha256(race97_micro_path) if race97_micro_path.is_file() else None, "audit": race97_overlay_audit},
        "semantic_boundary": "Residency is not execution. These comparisons do not capture the active VU PC or prove which overlay emitted a particular GIF tag.",
    }
    overlay_receipt_path = args.race_output.parent / "vu-overlay-residency.json"
    overlay_receipt_path.write_text(json.dumps(overlay_receipt, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"race_output": str(args.race_output), "race_result": race_checks["validation"]["result"], "texture_records_joined": len(texture_rows), "geometry_packet_count": draw_count, "race_overlay_match": race_overlay_match}, indent=2))
    return 0 if result["validation"]["result"] == "pass" and runtime_result["validation"]["result"] == "pass" and race_checks["validation"]["result"] == "pass" else 1


if __name__ == "__main__":
    sys.exit(main())
