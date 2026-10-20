"""Source-bound arithmetic probes for original MC3 vehicle VU programs.

These jobs execute unchanged contiguous instruction pairs, with an E-bit stop
inserted after the selected interval. They isolate numerical behavior from a
whole draw. Every uniform and starting VF is explicit; no host lighting,
normalization, matrix multiplication or generated-UV arithmetic substitutes
for the native instructions.
"""

import hashlib
import json
from pathlib import Path
import struct

from mc3_environment_raster import EXECUTABLE_SHA, _read_elf
from mc3_tire_vu import unpack_microprogram

EVIDENCE = (
    Path(__file__).resolve().parents[1] / "research/evidence/"
    "midnight-club-3-remix/previews/vehicle-vu.json"
)
PROOF_SHA = "31ff92c8fd5a7366ed9be021b250e662b49c208e1f49e2ee9ae024b8a1a0c6d0"
NOP = (0x8000033C, 0x000002FF)


def need(condition, message):
    if not condition:
        raise ValueError(message)


def source_contract(executable=None, receipt=None):
    proof = json.loads(EVIDENCE.read_text()) if receipt is None else receipt
    encoded = json.dumps(proof, sort_keys=True, separators=(",", ":")).encode()
    need(hashlib.sha256(encoded).hexdigest() == PROOF_SHA, "vehicle VU receipt changed")
    need(
        proof["source_executable_sha256"] == EXECUTABLE_SHA,
        "vehicle VU source identity changed",
    )
    if executable is not None:
        need(
            hashlib.sha256(executable).hexdigest() == EXECUTABLE_SHA,
            "vehicle VU executable changed",
        )
        for row in proof["kernels"].values():
            packet = _read_elf(executable, row["address"], row["bytes"])
            need(
                hashlib.sha256(packet).hexdigest() == row["sha256"],
                "vehicle VU program changed",
            )
            pairs = unpack_microprogram(packet)
            raw = b"".join(
                struct.pack("<II", *pairs[pc])
                for pc in range(row["first_pc"], row["last_pc"] + 1)
            )
            need(
                hashlib.sha256(raw).hexdigest() == row["kernel_sha256"],
                "vehicle VU kernel changed",
            )
    return proof


def kernel_job(executable, program, memory, vf_words):
    """Return one isolated native arithmetic job and its source/input bindings.

    memory is all16KiB of explicit VU data. vf_words maps each required nonzero
    vector register to four raw u32 words, retaining signed zero/integers. The
    official adapter initializes VI registers to zero. Source lower loads,
    stores, DIV and flags execute unchanged; these selected intervals contain
    no branches or XGKICK. No original-program entrypoint claim is made.
    """
    proof = source_contract(executable)
    need(program in proof["kernels"], "unsupported vehicle VU program")
    need(
        isinstance(memory, bytes) and len(memory) == 16384, "invalid vehicle VU memory"
    )
    need(
        isinstance(vf_words, dict) and set(vf_words) == set(range(1, 32)),
        "all vehicle VF input registers must be explicit",
    )
    for register, words in vf_words.items():
        need(
            type(register) is int
            and isinstance(words, list)
            and len(words) == 4
            and all(type(x) is int and 0 <= x <= 0xFFFFFFFF for x in words),
            "invalid vehicle VF input words",
        )
    row = proof["kernels"][program]
    pairs = unpack_microprogram(_read_elf(executable, row["address"], row["bytes"]))
    micro = bytearray(16384)
    for pc, pair in pairs.items():
        struct.pack_into("<II", micro, pc * 8, *pair)
    stop = row["last_pc"] + 1
    struct.pack_into("<IIII", micro, stop * 8, NOP[0], NOP[1] | 0x40000000, *NOP)
    result = bytearray(b"MC3VU001") + micro + memory
    result += struct.pack("<I6I", 1, row["first_pc"], 0, 0, 100000, 0, len(vf_words))
    for register, words in sorted(vf_words.items()):
        result += struct.pack("<I4I", register, *words)
    result = bytes(result)
    binding = {
        "program": program,
        "first_pc": row["first_pc"],
        "last_pc": row["last_pc"],
        "kernel_sha256": row["kernel_sha256"],
        "job_sha256": hashlib.sha256(result).hexdigest(),
        "memory_sha256": hashlib.sha256(memory).hexdigest(),
        "vf_words_sha256": hashlib.sha256(
            json.dumps(vf_words, sort_keys=True).encode()
        ).hexdigest(),
        "rgba_register": row["rgba_register"],
        "claim_limits": proof["claim_limits"],
    }
    return result, binding


def read_register_words(data, register):
    """Read raw VF output from the independently executed adapter's VURegs ABI."""
    need(
        isinstance(data, bytes)
        and len(data) == 1680
        and type(register) is int
        and 0 <= register < 32,
        "invalid vehicle VU register output",
    )
    return list(struct.unpack_from("<4I", data, register * 16))


def probe_job(executable, name):
    """Reproduce a measured explicit synthetic context, never game defaults."""
    proof = source_contract(executable)
    matches = [p for p in proof["numerical_probes"] if p["name"] == name]
    need(len(matches) == 1, "unknown or ambiguous vehicle numerical probe")
    probe = matches[0]
    context = proof["synthetic_probe_context"]
    rows = context["memory_rows"] | probe["memory_overrides"]
    vf = context["vf_rows"] | probe["vf_overrides"]
    memory = bytearray(16384)
    for slot, words in rows.items():
        need(
            0 <= int(slot) < 1024 and len(words) == 4,
            "invalid vehicle probe memory row",
        )
        struct.pack_into("<4I", memory, int(slot) * 16, *words)
    job, binding = kernel_job(
        executable, probe["program"], bytes(memory), {int(k): v for k, v in vf.items()}
    )
    need(
        binding["job_sha256"] == probe["job_sha256"],
        "vehicle numerical probe job changed",
    )
    return job, probe


def execute_probes(executable, output, runner=None):
    """Reexecute and compare raw VF outputs using the independent VU runtime."""
    from mc3_reference_runtime import run_job

    runner = run_job if runner is None else runner
    proof = source_contract(executable)
    output = Path(output)
    need(not output.exists(), "choose a fresh vehicle VU probe output directory")
    output.mkdir(parents=True)
    result = []
    for probe in proof["numerical_probes"]:
        job, expected = probe_job(executable, probe["name"])
        path = output / (probe["name"] + ".job")
        path.write_bytes(job)
        directory = output / probe["name"]
        receipt = runner(path, directory)
        need(
            receipt["status"] == "executed"
            and receipt["job_sha256"] == expected["job_sha256"]
            and receipt["runtime"]["binary_sha256"] == expected["runtime_binary_sha256"]
            and receipt["adapter_sha256"] == expected["adapter_sha256"],
            "vehicle numerical probe execution binding changed",
        )
        registers = (directory / "final-vuregs.bin").read_bytes()
        for register, words in expected["register_words"].items():
            need(
                read_register_words(registers, int(register)) == words,
                "executed vehicle VU numerical output changed",
            )
        result.append(
            {
                "name": probe["name"],
                "job_sha256": expected["job_sha256"],
                "register_words": expected["register_words"],
                "execution": receipt,
            }
        )
    (output / "comparison.json").write_text(json.dumps(result, indent=2) + "\n")
    return result
