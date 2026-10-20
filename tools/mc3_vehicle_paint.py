"""Source-pinned bounded original EE paint-generator control.

The declared objects are explicit source-compatible inputs, not an active game
actor. The API supplies original code and memory to the browser interpreter; it
never substitutes a paint equation or claims a generic R5900 implementation.
"""

import hashlib
import json
from pathlib import Path
import struct

from mc3_environment_raster import _read_elf
from mc3_specular_native import EXECUTABLE_SHA

PROOF = (
    Path(__file__).resolve().parents[1] / "research/evidence/"
    "midnight-club-3-remix/previews/vehicle-paint-native.json"
)
PROOF_SHA = "22dab93642c5513d23559ffca27cf5a1849546520c56cfa43479bdafe7ac7ca6"


def need(condition, message):
    if not condition:
        raise ValueError(message)


def source_contract(receipt=None):
    proof = json.loads(PROOF.read_text()) if receipt is None else receipt
    raw = json.dumps(proof, sort_keys=True, separators=(",", ":")).encode()
    need(hashlib.sha256(raw).hexdigest() == PROOF_SHA, "vehicle paint receipt changed")
    need(
        proof["source_executable_sha256"] == EXECUTABLE_SHA,
        "vehicle paint source changed",
    )
    return proof


def from_executable(executable):
    proof = source_contract()
    need(
        hashlib.sha256(executable).hexdigest() == EXECUTABLE_SHA,
        "vehicle paint executable changed",
    )
    for row in proof["intervals"]:
        data = _read_elf(executable, row["start"], row["end"] - row["start"])
        need(
            hashlib.sha256(data).hexdigest() == row["sha256"],
            "vehicle paint source interval changed",
        )
    return proof


def control_context(proof, control):
    need(control in ("flat", "positive"), "unknown bounded paint control")
    context = json.loads(json.dumps(proof["reference_context"]))
    selected = proof if control == "flat" else proof["positive_control"]
    if control == "positive":
        replacements = {row["address"]: row for row in selected["patch_replacements"]}
        context["patches"] = [
            replacements.get(row["address"], row) for row in context["patches"]
        ]
    return context, selected


def reference_job(executable, *, control="flat"):
    proof = from_executable(executable)
    context, selected = control_context(proof, control)
    result = bytearray(b"MC3EE001") + struct.pack(
        "<5I",
        context["entry"],
        100000,
        len(context["gpr"]),
        len(context["fpr"]),
        len(context["patches"]),
    )
    for register, low, high in context["gpr"]:
        result += struct.pack("<IQQ", register, int(low), int(high))
    for register, value in context["fpr"]:
        result += struct.pack("<2I", register, value)
    for patch in context["patches"]:
        data = bytes.fromhex(patch["data_hex"])
        result += struct.pack("<2I", patch["address"], len(data)) + data
    need(
        hashlib.sha256(result).hexdigest() == selected["reference_job_sha256"],
        "vehicle paint job changed",
    )
    return bytes(result)


def browser_source_pack(executable, *, control="flat"):
    """Return source chunks and allocations; caller materializes zeroed RAM/SPAD.

    Original ELF segments include their source-declared BSS allocation. Explicit
    heap objects, DMA ring and helper stack are separately bounded allocations.
    No unknown object receives a fabricated constructor or texture fallback.
    """
    proof = from_executable(executable)
    offset = struct.unpack_from("<I", executable, 28)[0]
    width, count = struct.unpack_from("<HH", executable, 42)
    chunks, regions = [], []
    for i in range(count):
        kind, source, address, _, filesz, memsz, flags, _ = struct.unpack_from(
            "<8I", executable, offset + i * width
        )
        if kind != 1:
            continue
        need(
            filesz <= memsz
            and source + filesz <= len(executable)
            and address + memsz <= 0x2000000,
            "vehicle paint segment extent changed",
        )
        chunks.append(
            {"address": address, "bytes": executable[source : source + filesz]}
        )
        regions.append(
            {"start": address, "size": memsz, "read": True, "write": bool(flags & 2)}
        )
    context, _ = control_context(proof, control)
    for patch in context["patches"]:
        data = bytes.fromhex(patch["data_hex"])
        chunks.append({"address": patch["address"], "bytes": data})
        # Source globals already belong to the ELF allocation. Only explicit
        # out-of-image caller objects introduce new memory regions.
        if not any(
            patch["address"] >= r["start"]
            and patch["address"] + len(data) <= r["start"] + r["size"]
            for r in regions
        ):
            regions.append(
                {
                    "start": patch["address"],
                    "size": len(data),
                    "read": True,
                    "write": True,
                }
            )
    regions += [
        {"start": 0x70000000, "size": 0x4000, "read": True, "write": True},
        {"start": 0x1100000, "size": 0x100000, "read": True, "write": True},
        {"start": 0x1FE0000, "size": 0x20000, "read": True, "write": True},
    ]
    code = []
    for row in proof["intervals"]:
        data = _read_elf(executable, row["start"], row["end"] - row["start"])
        code.extend(
            [row["start"] + i, struct.unpack_from("<I", data, i)[0]]
            for i in range(0, len(data), 4)
        )
    return {
        "entry": context["entry"],
        "code": code,
        "chunks": chunks,
        "regions": regions,
        "gpr": context["gpr"],
        "fpr": context["fpr"],
        "control": control,
        "claim_limits": proof["claim_limits"],
    }


def verify_reference_output(ram, *, control="flat"):
    _, proof = control_context(source_contract(), control)
    need(len(ram) == 0x2000000, "vehicle paint output extent changed")
    need(
        hashlib.sha256(ram).hexdigest() == proof["reference_final_ram_sha256"],
        "vehicle paint final RAM differs",
    )
    return {
        "ram_sha256": proof["reference_final_ram_sha256"],
        "dma_sha256": proof["reference_dma_sha256"],
    }


def execute_reference(executable, output, runner=None, *, control="flat"):
    from mc3_reference_runtime import run_job

    executable, output = Path(executable), Path(output)
    runner = run_job if runner is None else runner
    need(not output.exists(), "choose a fresh vehicle paint output")
    output.mkdir(parents=True)
    job = output / "paint.job"
    job.write_bytes(reference_job(executable.read_bytes(), control=control))
    receipt = runner(job, output / "execution", mode="ee", executable=executable)
    need(receipt["status"] == "executed", "vehicle paint reference did not execute")
    result = verify_reference_output(
        (output / "execution/ee-ram.bin").read_bytes(), control=control
    )
    result["execution"] = receipt
    result["claim_limits"] = source_contract()["claim_limits"]
    (output / "comparison.json").write_text(json.dumps(result, indent=2) + "\n")
    return result


def execute_arithmetic_reference(executable, output, runner=None):
    """Fresh independent native opcode controls, not interpreter self-tests."""
    from mc3_environment_raster import encode_ee_job
    from mc3_reference_runtime import run_job

    executable, output = Path(executable), Path(output)
    runner = run_job if runner is None else runner
    proof = from_executable(executable.read_bytes())
    need(not output.exists(), "choose a fresh EE arithmetic output")
    output.mkdir(parents=True)
    controls = proof["arithmetic_controls"]
    results = []
    for case in controls["cases"]:
        words = [
            controls["wrapper_accumulator_seed"],
            case["instruction"],
            controls["wrapper_accumulator_copy"],
        ]
        words += [0xE5000000 | (i << 16) | (i * 4) for i in range(32)]
        words += [0x03E00008, 0]
        code = struct.pack("<" + "I" * len(words), *words)
        data = encode_ee_job(
            0x1000000,
            {8: 0x1002000},
            [(0x1000000, code)],
            fprs=dict(controls["input_fpr"]),
        )
        job = output / (case["name"] + ".job")
        job.write_bytes(data)
        directory = output / case["name"]
        result = runner(job, directory, mode="ee", executable=executable)
        need(result["status"] == "executed", "EE arithmetic did not execute")
        ram = (directory / "ee-ram.bin").read_bytes()
        actual = list(struct.unpack_from("<32I", ram, 0x1002000))
        need(
            actual == case["expected_fpr"],
            "original EE arithmetic differs: " + case["name"],
        )
        results.append({"name": case["name"], "fpr_words": actual, "execution": result})
    (output / "comparison.json").write_text(json.dumps(results, indent=2) + "\n")
    return results
