"""Sparse original instruction/data closure for two explicit native MC3 paint factories."""

import argparse
import hashlib
import json
import struct
import subprocess
from pathlib import Path

from mc3_environment_raster import EXECUTABLE_SHA, _read_elf, encode_ee_job
from mc3_reference_runtime import run_job, validate_job

ROOT = Path(__file__).resolve().parents[1]
FIXTURE = (
    ROOT / "research/evidence/midnight-club-3-remix/previews/vehicle-paint-factory.json"
)
HELPER = ROOT / "tools/mc3_vehicle_paint_factory.mjs"
ENTRY = 0x100A000
PROOF_SHA = "4974ebb537eb3c91f3892e32c7aa5cc4d540f0d4af9a658d89f2492179cb227f"


def sha(data):
    return hashlib.sha256(data).hexdigest()


def wrapper(control):
    if control not in ["flat", "positive"]:
        raise ValueError("unsupported factory context")
    words = []

    def li(reg, value):
        words.extend(
            [
                0x3C000000 | reg << 16 | value >> 16 & 65535,
                0x34000000 | reg << 21 | reg << 16 | value & 65535,
            ]
        )

    def call(address):
        words.extend([0x0C000000 | address >> 2, 0])

    def move(dst, src):
        words.append(src << 21 | dst << 11 | 0x2D)

    def sw(src, base, offset):
        words.append(0xAC000000 | base << 21 | src << 16 | offset)

    li(4, 0x1008000)
    call(0x530D40)
    li(4, 0x1000000)
    call(0x2CD050)
    li(4, 0x1002000)
    call(0x2CBA80)
    for reg, value in [(4, 64), (5, 64), (6, 5), (7, 0)]:
        li(reg, value)
    call(0x523140)
    move(16, 2)
    words.append(0x8E040010)
    li(5, 255)
    li(6, 1024)
    call(0x4329B0)
    li(4, 0)
    move(5, 16)
    call(0x2B9CE0)
    move(17, 2)
    li(8, 0x1000000)
    sw(17, 8, 20)
    li(9, 0x1001000)
    sw(9, 8, 4)
    li(4, 0)
    move(5, 17)
    call(0x2CD3B0)
    li(4, 0)
    move(5, 17)
    li(6, 0x1002000)
    call(0x2CD360)
    li(4, 0x1006000)
    li(5, 0x647D52)
    call(0x2B7088)
    if control == "flat":
        li(8, 0x1000000)
        words.append(0xA1000000)
    for reg, value in [(4, 0x1000000), (5, 0x1002000), (6, 0x1003000), (7, 1)]:
        li(reg, value)
    call(0x2CE880)
    li(8, 0x1009000)
    sw(17, 8, 0)
    sw(16, 8, 4)
    li(9, 0x70000000)
    words.append(0x8D2A05AC)
    sw(10, 8, 8)
    li(31, 0x10000)
    words.extend([0x03E00008, 0])
    return struct.pack("<" + "I" * len(words), *words)


def parse_context(data, control):
    validate_job(data, "ee")
    entry, limit, ng, nf, count = struct.unpack_from("<5I", data, 8)
    if (entry, limit, ng, nf) != (ENTRY, 10000000, 0, 0):
        raise ValueError("factory context execution header differs")
    at, patches = 28, []
    for _ in range(count):
        address, size = struct.unpack_from("<II", data, at)
        at += 8
        patches.append(dict(address=address, data_hex=data[at : at + size].hex()))
        at += size
    if (
        at != len(data)
        or bytes.fromhex(patches[-1]["data_hex"]) != wrapper(control)
        or patches[-1]["address"] != ENTRY
    ):
        raise ValueError("factory native-call wrapper differs")
    return dict(
        entry=entry,
        maxSteps=limit,
        gpr=[],
        fpr=[],
        chunks=patches,
        reference_job_sha256=sha(data),
    )


def factory_job(context, control):
    chunks = context["chunks"]
    if (
        bytes.fromhex(chunks[-1]["data_hex"]) != wrapper(control)
        or chunks[-1]["address"] != ENTRY
    ):
        raise ValueError("factory source-compatible wrapper changed")
    result = b"MC3EE001" + struct.pack("<5I", ENTRY, 10000000, 0, 0, len(chunks))
    result += b"".join(
        struct.pack("<II", c["address"], len(bytes.fromhex(c["data_hex"])))
        + bytes.fromhex(c["data_hex"])
        for c in chunks
    )
    if sha(result) != context["reference_job_sha256"]:
        raise ValueError("factory initialized context changed")
    validate_job(result, "ee")
    return result


def initializer_job():
    stack = bytearray(32)
    struct.pack_into("<I", stack, 24, 0x10000)
    return encode_ee_job(0x2CBB5C, {16: 0x1000000, 24: 0x1001000}, [(0x1FF0000, stack)])


def intervals(values):
    values = sorted(set(values))
    result = []
    for value in values:
        if result and result[-1][0] + result[-1][1] == value:
            result[-1][1] += 1
        else:
            result.append([value, 1])
    return result


def ranges_mask(rows, size=0x2000000):
    result = bytearray(size)
    for start, count in rows:
        if not 0 <= start <= start + count <= size:
            raise ValueError("factory source footprint outside memory")
        result[start : start + count] = b"\1" * count
    return result


def source_chunks(executable, rows):
    result = []
    for start, count in rows:
        data = _read_elf(executable, start, count)
        result.append(dict(address=start, data_hex=data.hex(), sha256=sha(data)))
    return result


def project_ram(native, file_ranges, retained, written, context):
    if len(native) != 0x2000000:
        raise ValueError("factory native RAM extent differs")
    keep = ranges_mask(retained + written)
    for patch in context["chunks"]:
        if patch["address"] < len(native):
            size = len(bytes.fromhex(patch["data_hex"]))
            keep[patch["address"] : patch["address"] + size] = b"\1" * size
    result = bytearray(native)
    for address, count, _ in file_ranges:
        for at in range(address, address + count):
            if not keep[at]:
                result[at] = 0
    return bytes(result)


def load_receipt(data=None):
    raw = FIXTURE.read_bytes() if data is None else data
    if sha(raw) != PROOF_SHA:
        raise ValueError("factory source receipt changed")
    return json.loads(raw)


def verify_source(executable, proof):
    if sha(executable) != EXECUTABLE_SHA:
        raise ValueError("original factory executable differs")
    for name in ["source_code", "source_data"]:
        for chunk in proof[name]:
            data = bytes.fromhex(chunk["data_hex"])
            if (
                sha(data) != chunk["sha256"]
                or _read_elf(executable, chunk["address"], len(data)) != data
            ):
                raise ValueError("factory original source chunk differs")
    table = proof["table_initializer"]
    if (
        _read_elf(executable, table["entry"], table["end"] - table["entry"]).hex()
        != table["source_hex"]
    ):
        raise ValueError("factory original initializer source differs")
    return True


def pack_for_context(receipt, control):
    if control not in receipt["contexts"]:
        raise ValueError("unknown factory context")
    context = receipt["contexts"][control]
    code = [
        (c["address"] + i, struct.unpack_from("<I", bytes.fromhex(c["data_hex"]), i)[0])
        for c in receipt["source_code"]
        for i in range(0, len(bytes.fromhex(c["data_hex"])), 4)
    ]
    raw = wrapper(control)
    code += [
        (ENTRY + i, struct.unpack_from("<I", raw, i)[0]) for i in range(0, len(raw), 4)
    ]
    regions = []
    for access in receipt["access"]:
        for permission in ["read", "write"]:
            regions += [
                dict(
                    start=access["start"] + start,
                    size=size,
                    read=permission == "read",
                    write=permission == "write",
                )
                for start, size in access[permission]
            ]
    chunks = [
        dict(c, sha256=sha(bytes.fromhex(c["data_hex"])))
        for c in receipt["source_data"] + context["chunks"]
    ]
    code_digest = sha(b"".join(struct.pack("<II", a, w) for a, w in code))
    return dict(
        entry=ENTRY,
        maxSteps=10000000,
        gpr=[],
        fpr=[],
        code=code,
        code_sha256=code_digest,
        chunks=chunks,
        regions=regions,
        expected=receipt["results"][control],
        control=control,
    )


def derive(executable, contexts, discoveries, native_rams, table_proof):
    if sha(executable) != EXECUTABLE_SHA:
        raise ValueError("original factory executable differs")
    code, initial = {}, set()
    for control, d in discoveries.items():
        factory_job(contexts[control], control)
        for address, word in d["code"]:
            if address < 0x1000000:
                if _read_elf(executable, address, 4) != struct.pack("<I", word):
                    raise ValueError(
                        "factory observed instruction differs from original"
                    )
                code[address] = word
        source = ranges_mask(d["access"][0]["initial"])
        for start, count, _ in d["fileRanges"]:
            initial.update(at for at in range(start, start + count) if source[at])
    code_bytes = [a + i for a in code for i in range(4)]
    data_rows, code_rows = intervals(initial), intervals(code_bytes)
    access = []
    for i in range(2):
        row = dict(start=discoveries["positive"]["access"][i]["start"])
        for permission in ["read", "write"]:
            values = [
                a + j
                for d in discoveries.values()
                for a, n in d["access"][i][permission]
                for j in range(n)
            ]
            row[permission] = intervals(values)
        access.append(row)
    result = dict(
        schema="mc3-native-paint-factory-v1",
        executable_sha256=EXECUTABLE_SHA,
        source_file_ranges=discoveries["positive"]["fileRanges"],
        source_code=source_chunks(executable, code_rows),
        source_data=source_chunks(executable, data_rows),
        access=access,
        contexts=contexts,
        results={},
        table_initializer=table_proof,
        claim_limits=[
            "Two explicit source-compatible isolated factories, not an active actor/garage/gameplay state.",
            "Original constructors/default recipe, radial/palette/none/texture/paint generators execute unchanged.",
            "Paint-type table is recomputed by pinned original constructor tail, retained as initialized input.",
            "Sparse source closure is the union of both observed contexts; unknown instructions/accesses fail closed.",
            "Native full32MiB equality is checked before projection; sparse execution compares full32MiB after explicit omission of untouched unretained original ELF bytes.",
            "All stores including identical-value stores and aligned/unaligned read-modify-write footprints are retained.",
            "Ordered CNT/REF DMA prefix stops before first main FRAME restore after native RT256 capture; final VIF/VU/GS execution is separate.",
        ],
    )
    for control, d in discoveries.items():
        projected = project_ram(
            native_rams[control],
            d["fileRanges"],
            data_rows,
            d["access"][0]["write"],
            contexts[control],
        )
        result["results"][control] = dict(
            native_ram_sha256=sha(native_rams[control]),
            projected_ram_sha256=sha(projected),
            steps=d["steps"],
            projection_written=d["access"][0]["write"],
            dma=d["dma"],
        )
    return result


def execute_reference(executable, output, contexts):
    executable, output = Path(executable), Path(output)
    source = executable.read_bytes()
    if sha(source) != EXECUTABLE_SHA:
        raise ValueError("original factory executable differs")
    output.mkdir(parents=True, exist_ok=False)
    init = output / "initializer.job"
    init.write_bytes(initializer_job())
    init_receipt = run_job(
        init, output / "initializer", mode="ee", executable=executable
    )
    init_ram = (output / "initializer/ee-ram.bin").read_bytes()
    table = init_ram[0x6BE8E0 : 0x6BE8E0 + 192]
    table_raw = _read_elf(source, 0x2CBB5C, 0x178)
    table_proof = dict(
        entry=0x2CBB5C,
        end=0x2CBCD4,
        source_sha256=sha(table_raw),
        source_hex=table_raw.hex(),
        job_sha256=sha(init.read_bytes()),
        bytes=192,
        data_hex=table.hex(),
        sha256=sha(table),
        execution=init_receipt,
        limits=[
            "Original constructor tail after allocation; explicit source-compatible s0/t8 and return stack, not full allocation lifecycle."
        ],
    )
    discoveries, native_rams = {}, {}
    for control, context in contexts.items():
        data = factory_job(context, control)
        job_path = output / (control + ".job")
        job_path.write_bytes(data)
        table_patch = [c for c in context["chunks"] if c["address"] == 0x6BE8E0]
        if len(table_patch) != 1 or bytes.fromhex(table_patch[0]["data_hex"]) != table:
            raise ValueError("factory paint table differs from original initializer")
        run_job(job_path, output / control, mode="ee", executable=executable)
        native_rams[control] = (output / control / "ee-ram.bin").read_bytes()
        discovery = output / (control + "-discovery.json")
        subprocess.run(
            [
                "node",
                str(HELPER),
                "discover",
                str(executable),
                str(job_path),
                str(output / control / "ee-ram.bin"),
                str(discovery),
            ],
            check=True,
        )
        discoveries[control] = json.loads(discovery.read_text())
    proof = derive(source, contexts, discoveries, native_rams, table_proof)
    for control in contexts:
        (output / (control + "-pack.json")).write_text(
            json.dumps(pack_for_context(proof, control), separators=(",", ":")) + "\n"
        )
    (output / "reference.json").write_text(
        json.dumps(proof, separators=(",", ":")) + "\n"
    )
    return proof


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--executable", type=Path)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--emit-pack", choices=["positive", "flat"])
    parser.add_argument("--bootstrap-contexts", type=Path)
    parser.add_argument("--write-fixture", action="store_true")
    args = parser.parse_args()
    if args.emit_pack:
        print(
            json.dumps(
                pack_for_context(load_receipt(), args.emit_pack), separators=(",", ":")
            )
        )
        raise SystemExit(0)
    if not args.executable or not args.output:
        parser.error("--executable and --output are required for original execution")
    if args.bootstrap_contexts:
        contexts = {
            name: parse_context(
                (
                    args.bootstrap_contexts / f"paint-factory-whole-{name}.job"
                ).read_bytes(),
                name,
            )
            for name in ["positive", "flat"]
        }
    else:
        contexts = load_receipt()["contexts"]
    proof = execute_reference(args.executable, args.output, contexts)
    if args.write_fixture:
        FIXTURE.write_text(json.dumps(proof, separators=(",", ":")) + "\n")
    print(
        "PASS original table initializer and both factory jobs; native RAM equality, sparse closure and ordered DMA receipts written"
    )
