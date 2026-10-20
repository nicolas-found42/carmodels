"""Source-pinned original radial/paint-palette helper contexts.

The browser EE interpreter executes the original arithmetic. No duplicated
radial curve, gradient formula, CLUT permutation or alpha approximation lives
in this producer. Contexts declare actual64square native image getters and
six native paint-type paths, including an explicit type2 three-key control.
"""

import hashlib
import json
from pathlib import Path
import struct

from mc3_environment_raster import _read_elf
from mc3_specular_native import EXECUTABLE_SHA

PROOF = (
    Path(__file__).resolve().parents[1] / "research/evidence/"
    "midnight-club-3-remix/previews/vehicle-paint-components.json"
)
PROOF_SHA = "96e7deb491bceb5b6139217593dc0a8aaf09dc35a346635dccff12a561fb03f7"


def need(condition, message):
    if not condition:
        raise ValueError(message)


def source_contract(receipt=None):
    proof = json.loads(PROOF.read_text()) if receipt is None else receipt
    raw = json.dumps(proof, sort_keys=True, separators=(",", ":")).encode()
    need(
        hashlib.sha256(raw).hexdigest() == PROOF_SHA, "paint component receipt changed"
    )
    need(
        proof["source_executable_sha256"] == EXECUTABLE_SHA,
        "paint component source changed",
    )
    return proof


def from_executable(executable):
    proof = source_contract()
    need(
        hashlib.sha256(executable).hexdigest() == EXECUTABLE_SHA,
        "paint component executable changed",
    )
    for row in proof["intervals"]:
        raw = _read_elf(executable, row["start"], row["end"] - row["start"])
        need(
            hashlib.sha256(raw).hexdigest() == row["sha256"],
            "paint component interval changed",
        )
    return proof


def selected_case(proof, name):
    found = [row for row in proof["cases"] if row["name"] == name]
    need(len(found) == 1, "unknown native paint component control")
    return found[0]


def reference_job(executable, name):
    case = selected_case(from_executable(executable), name)
    data = bytearray(b"MC3EE001") + struct.pack(
        "<5I",
        case["entry"],
        case["max_steps"],
        len(case["gpr"]),
        len(case["fpr"]),
        len(case["patches"]),
    )
    for register, low, high in case["gpr"]:
        data += struct.pack("<IQQ", register, int(low), int(high))
    for register, word in case["fpr"]:
        data += struct.pack("<2I", register, word)
    for patch in case["patches"]:
        raw = bytes.fromhex(patch["data_hex"])
        data += struct.pack("<2I", patch["address"], len(raw)) + raw
    need(
        hashlib.sha256(data).hexdigest() == case["job_sha256"],
        "paint component job changed",
    )
    return bytes(data)


def browser_source_pack(executable, name):
    proof = from_executable(executable)
    case = selected_case(proof, name)
    offset = struct.unpack_from("<I", executable, 28)[0]
    width, count = struct.unpack_from("<HH", executable, 42)
    chunks, regions = [], []
    for i in range(count):
        kind, source, address, _, filesz, memsz, flags, _ = struct.unpack_from(
            "<8I", executable, offset + i * width
        )
        if kind == 1:
            need(
                filesz <= memsz
                and source + filesz <= len(executable)
                and address + memsz <= 0x2000000,
                "paint component segment extent changed",
            )
            chunks.append(
                {"address": address, "bytes": executable[source : source + filesz]}
            )
            regions.append(
                {
                    "start": address,
                    "size": memsz,
                    "read": True,
                    "write": bool(flags & 2),
                }
            )
    for patch in case["patches"]:
        raw = bytes.fromhex(patch["data_hex"])
        chunks.append({"address": patch["address"], "bytes": raw})
        regions.append(
            {"start": patch["address"], "size": len(raw), "read": True, "write": True}
        )
    # Native image's explicit writable descriptor/pixel/CLUT backing allocation.
    # The unallocated rest of the synthetic heap is never silently readable.
    regions += [
        {"start": 0x1001000, "size": 8192, "read": True, "write": True},
        {"start": 0x1FE0000, "size": 0x20000, "read": True, "write": True},
    ]
    code = []
    for row in proof["intervals"]:
        raw = _read_elf(executable, row["start"], row["end"] - row["start"])
        code.extend(
            [row["start"] + i, struct.unpack_from("<I", raw, i)[0]]
            for i in range(0, len(raw), 4)
        )
    return {
        "entry": case["entry"],
        "gpr": case["gpr"],
        "fpr": case["fpr"],
        "chunks": chunks,
        "regions": regions,
        "code": code,
        "control": name,
        "image": proof["image"],
        "claim_limits": proof["claim_limits"],
    }


def verify_reference_output(ram, name):
    case = selected_case(source_contract(), name)
    need(len(ram) == 0x2000000, "paint component RAM extent changed")
    need(
        hashlib.sha256(ram).hexdigest() == case["ram_sha256"],
        "paint component full RAM differs",
    )
    raw = ram[case["output_address"] : case["output_address"] + case["output_bytes"]]
    need(
        hashlib.sha256(raw).hexdigest() == case["output_sha256"],
        "paint component native output differs",
    )
    return raw


def execute_reference(executable, output, runner=None):
    from mc3_reference_runtime import run_job

    executable, output = Path(executable), Path(output)
    runner = run_job if runner is None else runner
    proof = from_executable(executable.read_bytes())
    need(not output.exists(), "choose a fresh paint component output")
    output.mkdir(parents=True)
    results = []
    for case in proof["cases"]:
        job = output / (case["name"] + ".job")
        job.write_bytes(reference_job(executable.read_bytes(), case["name"]))
        execution = runner(job, output / case["name"], mode="ee", executable=executable)
        need(
            execution["status"] == "executed",
            "paint component reference did not execute",
        )
        raw = verify_reference_output(
            (output / case["name"] / "ee-ram.bin").read_bytes(), case["name"]
        )
        results.append(
            {
                "name": case["name"],
                "output_sha256": hashlib.sha256(raw).hexdigest(),
                "ram_sha256": case["ram_sha256"],
                "execution": execution,
            }
        )
    (output / "comparison.json").write_text(json.dumps(results, indent=2) + "\n")
    return results


def write_browser_source_packs(executable, output):
    """Private regression transport, not a public whole-ELF distribution asset."""
    output = Path(output)
    need(not output.exists(), "choose a fresh private paint source-pack output")
    output.mkdir(parents=True)
    for case in source_contract()["cases"]:
        pack = browser_source_pack(executable, case["name"])
        for chunk in pack["chunks"]:
            chunk["data_hex"] = chunk.pop("bytes").hex()
        (output / (case["name"] + ".json")).write_text(
            json.dumps(pack, separators=(",", ":")) + "\n"
        )
    return output
