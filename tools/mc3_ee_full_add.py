"""Source-observed original EE full-vector ADD in MC3 compact frame composition."""

import argparse
import hashlib
import json
import struct
from pathlib import Path

from mc3_ee_cop2 import inputs, macro, wrapper
from mc3_environment_raster import EXECUTABLE_SHA, _read_elf, encode_ee_job
from mc3_reference_runtime import run_job

FIXTURE = (
    Path(__file__).resolve().parents[1]
    / "research/evidence/midnight-club-3-remix/previews/ee-full-add.json"
)
ADDRESS, WORD = 0x23E384, 0x4A4E03E8
START, INPUT, OUTPUT = 0x1000000, 0x1100000, 0x1200000


def cases():
    rows = [dict(name="original-compact-frame", instruction=WORD)]
    for mask in range(16):
        for name, vd, vs, vt in [
            ("separate", 4, 8, 5),
            ("source-alias", 8, 8, 5),
            ("other-alias", 5, 8, 5),
            ("all-alias", 5, 5, 5),
        ]:
            rows.append(
                dict(
                    name=f"mask-{mask}-{name}", instruction=macro(40, vd, vs, vt, mask)
                )
            )
    rows += [
        dict(name="zero-destination", instruction=macro(40, 0, 8, 5)),
        dict(name="zero-left", instruction=macro(40, 4, 0, 5)),
        dict(name="zero-right", instruction=macro(40, 4, 8, 0)),
        dict(name="finite-boundary", instruction=macro(40), profile="finite-boundary"),
    ]
    return rows


def case_inputs(row):
    words = inputs()
    if row.get("profile") == "finite-boundary":
        words[8 * 4 : 8 * 4 + 4] = [0x7F7FFFFF, 0xFF7FFFFF, 0x00800000, 0x80800000]
        words[5 * 4 : 5 * 4 + 4] = [0x00800000] * 4
    return words


def job(rows):
    code = wrapper(rows)
    return encode_ee_job(
        START,
        {},
        [
            (START, struct.pack("<" + "I" * len(code), *code)),
            (INPUT, b"".join(struct.pack("<128I", *case_inputs(row)) for row in rows)),
        ],
    )


def mflo_cases():
    rows = []
    for name, a, b, destination in [
        ("source-positive", 2048, 32, 6),
        ("negative", 0xFFFFFFFF, 17, 6),
        ("maximum", 0x7FFFFFFF, 0x7FFFFFFF, 6),
        ("minimum", 0x80000000, 0xFFFFFFFF, 6),
        ("zero", 0, 0x80000000, 6),
        ("source-alias", 0x7FFFFFFF, 3, 2),
        ("separate", 0x80000000, 0x7FFFFFFF, 7),
        ("zero-destination", 17, 31, 0),
    ]:
        rows.append(
            dict(
                name=name,
                instruction=destination << 11 | 18,
                input_words=[
                    a,
                    0xDEADBEEF,
                    0x12345678,
                    0x9ABCDEF0,
                    b,
                    0x11111111,
                    0x87654321,
                    0x0FEDCBA9,
                    0,
                    0x22222222,
                    0xCAFEFEED,
                    0xFEDCBA98,
                ],
            )
        )
    return rows


def mflo_job(rows):
    words = []
    for index, row in enumerate(rows):
        rd = row["instruction"] >> 11 & 31
        words += [
            0x3C0A0130,
            0x354A0000 | index * 48,
            0x3C0B0140,
            0x356B0000 | index * 16,
            0x79420000,
            0x79460010,
        ]
        if rd not in (2, 6):
            words.append(0x79400020 | rd << 16)
        words += [0x00460018, row["instruction"], 0x7D600000 | rd << 16]
    words += [0x03E00008, 0]
    return encode_ee_job(
        START,
        {},
        [
            (START, struct.pack("<" + "I" * len(words), *words)),
            (
                0x1300000,
                b"".join(struct.pack("<12I", *row["input_words"]) for row in rows),
            ),
        ],
    )


def mflo_reference(executable, output):
    rows = mflo_cases()
    path = output / "mflo.job"
    path.write_bytes(mflo_job(rows))
    receipt = run_job(path, output / "mflo-native", mode="ee", executable=executable)
    ram = (output / "mflo-native/ee-ram.bin").read_bytes()
    for index, row in enumerate(rows):
        row["expected_words"] = list(
            struct.unpack_from("<4I", ram, 0x1400000 + index * 16)
        )
    return dict(cases=rows, execution=receipt)


def reference(executable, output):
    executable, output = Path(executable), Path(output)
    source = executable.read_bytes()
    if hashlib.sha256(source).hexdigest() != EXECUTABLE_SHA:
        raise ValueError("original MC3 executable differs")
    raw = _read_elf(source, ADDRESS, 4)
    if raw != struct.pack("<I", WORD):
        raise ValueError("original compact-frame full ADD differs")
    mflo_source = _read_elf(source, 0x2B7848, 8)
    if mflo_source != struct.pack("<II", 0x00460018, 0x00003012):
        raise ValueError("original MULT/MFLO source differs")
    rows = cases()
    data = job(rows)
    output.mkdir(parents=True, exist_ok=False)
    (output / "control.job").write_bytes(data)
    receipt = run_job(
        output / "control.job", output / "native", mode="ee", executable=executable
    )
    ram = (output / "native/ee-ram.bin").read_bytes()
    for index, row in enumerate(rows):
        row["expected_vf"] = list(
            struct.unpack_from("<128I", ram, OUTPUT + index * 512)
        )
    result = dict(
        schema=1,
        source=dict(
            executable_sha256=EXECUTABLE_SHA,
            address=ADDRESS,
            instruction=WORD,
            hex=raw.hex(),
            sha256=hashlib.sha256(raw).hexdigest(),
        ),
        mflo_source=dict(
            address=0x2B7848,
            hex=mflo_source.hex(),
            sha256=hashlib.sha256(mflo_source).hexdigest(),
        ),
        mflo=mflo_reference(executable, output),
        cases=rows,
        inputs=inputs(),
        seed_accumulator=macro(60, 6, 30, 31),
        execution=receipt,
        claim_limits=[
            "Only newly observed full-vector ADD opcode0x28, with original finite RTZ/DAZ/FTZ arithmetic.",
            "All128 VF words/masks/aliases/VF0 compared, including finite-max and subnormal boundaries.",
            "Nonfinite operands and finite overflow remain explicit failures; unrelated operations remain unsupported.",
            "Observed source MFLO copies original MULT LO into low64 destination, preserving upper128; no other HI/LO operations added.",
            "No whole native skeleton, gameplay rendering, flag or timing equivalence claim.",
        ],
    )
    (output / "reference.json").write_text(json.dumps(result, indent=2) + "\n")
    return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--executable", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--write-fixture", action="store_true")
    args = parser.parse_args()
    result = reference(args.executable, args.output)
    if args.write_fixture:
        FIXTURE.write_text(json.dumps(result, indent=2) + "\n")
