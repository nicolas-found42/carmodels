"""Original MC3 local-joint initialization and hierarchical frame palette.

Only pointer relocation and caller transport occur here. The original58e470,
58e740 and58e8e8 routines construct, initialize and compose the frame palette.
"""

import hashlib
import json
import math
from pathlib import Path
import struct

from mc3_pck import Pck, read_vehicle
from mc3_environment_raster import _read_elf, encode_ee_job
from mc3_specular_native import EXECUTABLE_SHA

ROOT = Path(__file__).resolve().parents[1]
PROOF = ROOT / "research/evidence/midnight-club-3-remix/previews/vehicle-skeleton.json"
PROOF_SHA = "93165f0e192ceb4ed49b1d929d3fc07f8e189ff694ff24fcbb8daa70aa8dbb78"
CODE, CONTROLLER, LOCAL, PALETTE, PARENTS, FRAME, SOURCE = (
    0x1000000,
    0x1100000,
    0x1101000,
    0x1110000,
    0x1120000,
    0x1130000,
    0x1400000,
)


def sha(data):
    return hashlib.sha256(data).hexdigest()


def need(condition, message):
    if not condition:
        raise ValueError(message)


def source_contract(receipt=None):
    proof = json.loads(PROOF.read_text()) if receipt is None else receipt
    need(
        sha(json.dumps(proof, sort_keys=True, separators=(",", ":")).encode())
        == PROOF_SHA,
        "vehicle skeleton receipt differs",
    )
    return proof


def from_executable(executable):
    need(sha(executable) == EXECUTABLE_SHA, "vehicle skeleton executable differs")
    proof = source_contract()
    for row in proof["intervals"]:
        need(
            sha(_read_elf(executable, row["start"], row["end"] - row["start"]))
            == row["sha256"],
            "vehicle skeleton source interval differs",
        )
    need(
        list(struct.unpack("<6I", _read_elf(executable, 0x635938, 24)))
        == proof["controller_vtable"],
        "vehicle skeleton controller dispatch differs",
    )
    return proof


def native_context(path, root_words, backend):
    need(type(backend) is int and backend in (0, 1), "vehicle skeleton backend differs")
    need(
        isinstance(root_words, list)
        and len(root_words) == 12
        and all(type(v) is int and 0 <= v <= 0xFFFFFFFF for v in root_words),
        "vehicle skeleton root frame words differ",
    )
    frame = struct.pack("<12I", *root_words)
    need(
        all(math.isfinite(v) for v in struct.unpack("<12f", frame)),
        "vehicle skeleton nonfinite root frame",
    )
    path = Path(path)
    raw = path.read_bytes()
    pck, vehicle = Pck(raw), read_vehicle(path)
    skeleton = vehicle["skeleton"]
    bones = skeleton["bones"]
    need(
        1 <= len(bones) <= 512 and SOURCE + len(raw) <= 0x1FE0000,
        "vehicle skeleton explicit allocation bound exceeded",
    )
    relocated = bytearray(raw)
    # Retain all68 source bytes. Relocate only actual pointer fields: name,
    # sibling, child, parent; the native functions read parent.index(+38).
    for bone in bones:
        for relative in (12, 20, 24, 28):
            offset = bone["offset"] + relative
            pointer = pck.u32(offset)
            if pointer:
                struct.pack_into("<I", relocated, offset, SOURCE + pck.pointer(pointer))
    struct.pack_into(
        "<I", relocated, skeleton["offset"] + 8, SOURCE + skeleton["joint_array_offset"]
    )
    joins = []
    for lod, parts in vehicle["lods"].items():
        for part in parts:
            if part["mesh"] is None:
                continue
            mesh = part["mesh"]
            # The same byte is consumed by original2a7f48 at2a8060. The group
            # bone table provides an independent serialized join, not a name.
            byte = raw[mesh["offset"] + 6]
            need(
                raw[mesh["offset"] + 4] == 0 and byte == part["bone"],
                "vehicle skeleton unskinned mesh palette binding differs",
            )
            joins.append(
                {
                    "lod": lod,
                    "mesh_offset": mesh["offset"],
                    "bone": byte,
                    "packets": [
                        {
                            "offset": d["packet_offset"],
                            "bytes": d["packet_bytes"],
                            "sha256": sha(
                                raw[
                                    d["packet_offset"] : d["packet_offset"]
                                    + d["packet_bytes"]
                                ]
                            ),
                        }
                        for d in mesh["draws"]
                    ],
                }
            )
    count = len(bones)
    words = [0x03E0B82D]

    def li(register, value):
        words.extend(
            [
                0x3C000000 | register << 16 | value >> 16,
                0x34000000 | register << 21 | register << 16 | value & 65535,
            ]
        )

    def call(entry):
        words.extend([0x0C000000 | entry >> 2, 0])

    for register, value in [
        (4, CONTROLLER),
        (5, count),
        (6, 0),
        (7, LOCAL),
        (8, PALETTE),
        (9, 0),
        (10, 0),
        (11, PARENTS),
    ]:
        li(register, value)
    call(0x58E470)
    for register, value in [
        (4, CONTROLLER),
        (5, SOURCE + skeleton["offset"]),
        (6, FRAME),
        (7, 0),
    ]:
        li(register, value)
    call(0x58E740)
    # 58e740 initializes the rest palette with no root then setscontroller+c.
    # This second original update applies the explicitly supplied actor frame,
    # matching22af18's controller.vtable+10 update before near-model rendering.
    li(4, CONTROLLER)
    call(0x58E8E8)
    words.extend([0x02E00008, 0])
    patches = [
        (CODE, struct.pack("<" + "I" * len(words), *words)),
        (SOURCE, relocated),
        (FRAME, frame),
        (0x61C4C2, bytes([backend])),
    ]
    binding = {
        "source_sha256": pck.sha256,
        "source_bytes": len(raw),
        "skeleton_offset": skeleton["offset"],
        "joint_array_offset": skeleton["joint_array_offset"],
        "joint_count": count,
        "joint_bytes_sha256": sha(
            raw[
                skeleton["joint_array_offset"] : skeleton["joint_array_offset"]
                + count * 68
            ]
        ),
        "mesh_palette_joins": joins,
        "backend": backend,
        "root_words": root_words,
    }
    return patches, binding


def reference_job(executable, path, root_words, backend):
    from_executable(executable)
    patches, binding = native_context(path, root_words, backend)
    return encode_ee_job(CODE, {}, patches), binding


def output(ram, count):
    need(
        len(ram) == 0x2000000 and type(count) is int and 1 <= count <= 512,
        "vehicle skeleton output extent differs",
    )
    rows = {
        name: {
            "bytes": count * width,
            "sha256": sha(ram[address : address + count * width]),
        }
        for name, address, width in [
            ("local_frames", LOCAL, 64),
            ("world_palette", PALETTE, 48),
            ("parent_indices", PARENTS, 2),
        ]
    }
    return {"ram_sha256": sha(ram), **rows}


def browser_source_pack(executable, path, root_words, backend):
    proof = from_executable(executable)
    patches, binding = native_context(path, root_words, backend)
    offset = struct.unpack_from("<I", executable, 28)[0]
    width, count = struct.unpack_from("<HH", executable, 42)
    chunks, regions, code = [], [], []
    for i in range(count):
        kind, source, address, _, filesz, memsz, flags, _ = struct.unpack_from(
            "<8I", executable, offset + i * width
        )
        if kind == 1:
            need(
                filesz <= memsz
                and source + filesz <= len(executable)
                and address + memsz <= 0x2000000,
                "vehicle skeleton segment extent differs",
            )
            chunks.append(
                {
                    "address": address,
                    "data_hex": executable[source : source + filesz].hex(),
                }
            )
            regions.append(
                {
                    "start": address,
                    "size": memsz,
                    "read": True,
                    "write": bool(flags & 2),
                }
            )
    for address, data in patches:
        chunks.append({"address": address, "data_hex": data.hex()})
        if not any(
            r["start"] <= address and address + len(data) <= r["start"] + r["size"]
            for r in regions
        ):
            regions.append(
                {"start": address, "size": len(data), "read": True, "write": True}
            )
    n = binding["joint_count"]
    regions.extend(
        {"start": a, "size": n * w, "read": True, "write": True}
        for a, w in [(LOCAL, 64), (PALETTE, 48), (PARENTS, 2)]
    )
    regions.append({"start": CONTROLLER, "size": 44, "read": True, "write": True})
    regions.append({"start": 0x1FE0000, "size": 0x20000, "read": True, "write": True})
    for row in proof["intervals"]:
        data = _read_elf(executable, row["start"], row["end"] - row["start"])
        code.extend(
            [row["start"] + i, struct.unpack_from("<I", data, i)[0]]
            for i in range(0, len(data), 4)
        )
    code.extend(
        [CODE + i, struct.unpack_from("<I", patches[0][1], i)[0]]
        for i in range(0, len(patches[0][1]), 4)
    )
    return {
        "entry": CODE,
        "chunks": chunks,
        "regions": regions,
        "code": code,
        "source_binding": binding,
        "claim_limits": proof["claim_limits"],
    }


def execute_reference(executable, source_paths, directory, runner=None):
    from mc3_reference_runtime import run_job

    runner = run_job if runner is None else runner
    executable, directory = Path(executable), Path(directory)
    proof = from_executable(executable.read_bytes())
    need(not directory.exists(), "choose a fresh vehicle skeleton directory")
    directory.mkdir(parents=True)
    rows = []
    for case in proof["cases"]:
        job, binding = reference_job(
            executable.read_bytes(),
            source_paths[case["source"]],
            case["root_words"],
            case["backend"],
        )
        expected_binding = {
            **proof["sources"][case["source"]],
            "root_words": case["root_words"],
            "backend": case["backend"],
        }
        need(
            binding == expected_binding and sha(job) == case["job_sha256"],
            "vehicle skeleton native input differs",
        )
        path = directory / (case["name"] + ".job")
        path.write_bytes(job)
        execution = runner(
            path, directory / case["name"], mode="ee", executable=executable
        )
        actual = output(
            (directory / case["name"] / "ee-ram.bin").read_bytes(),
            binding["joint_count"],
        )
        need(actual == case["expected"], "original vehicle skeleton output differs")
        rows.append({"name": case["name"], "execution": execution, "output": actual})
    (directory / "comparison.json").write_text(json.dumps(rows, indent=2) + "\n")
    return rows
