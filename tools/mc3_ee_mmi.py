"""Original EE PCPYLD raw128 controls for reached MC3 texture upload factory code."""

import argparse
import hashlib
import json
import struct
from pathlib import Path

from mc3_environment_raster import EXECUTABLE_SHA, _read_elf, encode_ee_job
from mc3_reference_runtime import run_job

FIXTURE = (
    Path(__file__).resolve().parents[1]
    / "research/evidence/midnight-club-3-remix/previews/ee-mmi.json"
)
PINS = {
    "R5900OpcodeTables.cpp": "b96376cfff67799af5fe72bbfe4490c077f3368740dbf368d0a0e6f7be877f59",
    "MMI.cpp": "5b5a045dfbf896bc470d8aed658dfc492a07a5b74859a0d7832b2969f539159a",
}
COMMIT = "fd9d310ccbb6b8b62c976da8886a3c8fd3a10ff3"
SOURCE = [
    (2851496, 1893929865),
    (2851520, 1887771529),
    (2851572, 1893864329),
    (2851600, 1883446153),
    (2851616, 1885606793),
    (2851644, 1879251849),
    (2851692, 1883509641),
    (2851932, 1883444105),
    (2851956, 1885608841),
    (2851996, 1887576969),
    (2852016, 1883444105),
    (2852028, 1885674377),
    (2852048, 1879319433),
    (2852084, 1883444105),
    (2852232, 1885477769),
    (2852244, 1883575177),
]
START, INPUT, OUTPUT = 0x1000000, 0x1300000, 0x1400000


def instruction(rd, rs, rt):
    return 0x70000389 | rs << 21 | rt << 16 | rd << 11


def cases():
    rows = [dict(name=f"source-{a:x}", instruction=w) for a, w in SOURCE]
    for name, rd, rs, rt in [
        ("distinct", 2, 7, 3),
        ("alias-left", 7, 7, 3),
        ("alias-right", 3, 7, 3),
        ("alias-all", 7, 7, 7),
        ("zero-destination", 0, 7, 3),
        ("zero-left", 2, 0, 3),
        ("zero-right", 2, 7, 0),
        ("all-zero", 0, 0, 0),
    ]:
        rows.append(dict(name=name, instruction=instruction(rd, rs, rt)))
    for row in rows:
        w = row["instruction"]
        registers = sorted({w >> 11 & 31, w >> 21 & 31, w >> 16 & 31} - {0})
        row["registers"] = [
            [
                r,
                [
                    ((0x01234567 * (r + 1)) ^ word) & 0xFFFFFFFF
                    for word in [0xDEADBEEF, 0x89ABCDEF, 0x12345678, 0xFEDCBA98]
                ],
            ]
            for r in registers
        ]
    return rows


def job(rows):
    words, data = [], bytearray()
    for index, row in enumerate(rows):
        rd = row["instruction"] >> 11 & 31
        words += [
            0x3C0A0130,
            0x354A0000 | index * 64,
            0x3C0B0140,
            0x356B0000 | index * 16,
        ]
        inputs = bytearray(64)
        for offset, (reg, raw) in enumerate(row["registers"]):
            if reg in [10, 11, 31] or offset >= 4:
                raise ValueError("native PCPYLD control aliases wrapper context")
            words += [0x79400000 | reg << 16 | offset * 16]
            struct.pack_into("<4I", inputs, offset * 16, *raw)
        data.extend(inputs)
        words += [row["instruction"], 0x7D600000 | rd << 16]
    words += [0x03E00008, 0]
    return encode_ee_job(
        START, {}, [(START, struct.pack("<" + "I" * len(words), *words)), (INPUT, data)]
    )


def source_proof(executable, decoder, operations):
    if hashlib.sha256(executable).hexdigest() != EXECUTABLE_SHA:
        raise ValueError("original MC3 executable differs")
    for name, data in [("R5900OpcodeTables.cpp", decoder), ("MMI.cpp", operations)]:
        if hashlib.sha256(data).hexdigest() != PINS[name]:
            raise ValueError("pinned original MMI source differs: " + name)
    records = []
    for address, word in SOURCE:
        raw = _read_elf(executable, address, 4)
        if raw != struct.pack("<I", word):
            raise ValueError("original factory PCPYLD source instruction differs")
        records.append(dict(address=address, instruction=word, hex=raw.hex()))
    return dict(
        executable_sha256=EXECUTABLE_SHA,
        observed=records,
        decoder_commit=COMMIT,
        sources={
            name: dict(
                sha256=digest,
                url=f"https://raw.githubusercontent.com/PCSX2/pcsx2/{COMMIT}/pcsx2/{name}",
            )
            for name, digest in PINS.items()
        },
    )


def reference(executable, decoder, operations, output):
    executable, output = Path(executable), Path(output)
    source = source_proof(
        executable.read_bytes(),
        Path(decoder).read_bytes(),
        Path(operations).read_bytes(),
    )
    rows = cases()
    data = job(rows)
    output.mkdir(parents=True, exist_ok=False)
    (output / "control.job").write_bytes(data)
    receipt = run_job(
        output / "control.job", output / "native", mode="ee", executable=executable
    )
    ram = (output / "native/ee-ram.bin").read_bytes()
    for index, row in enumerate(rows):
        row["expected_words"] = list(
            struct.unpack_from("<4I", ram, OUTPUT + index * 16)
        )
    result = dict(
        schema=1,
        source=source,
        cases=rows,
        execution=receipt,
        claim_limits=[
            "Only source-observed PCPYLD MMI2 fn9/sa14 added; prior POR remains unchanged.",
            "Raw128 destination, aliases and register0 compared; no other MMI family enabled.",
            "No whole texture factory, gameplay rendering or instruction timing claim.",
        ],
    )
    (output / "reference.json").write_text(json.dumps(result, indent=2) + "\n")
    return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--executable", type=Path, required=True)
    parser.add_argument("--decoder-source", type=Path, required=True)
    parser.add_argument("--operation-source", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--write-fixture", action="store_true")
    args = parser.parse_args()
    proof = reference(
        args.executable, args.decoder_source, args.operation_source, args.output
    )
    if args.write_fixture:
        FIXTURE.write_text(json.dumps(proof, indent=2) + "\n")
