"""Original MC3 registry-to-program join and browser execution-data pack.

Names and indices come from the original registration instructions, never a
material template/category guess. Builtin selection remains explicit caller
state, matching original2a4e30's zero/nonzero selector with null override.
"""

import base64
import hashlib
import struct

from mc3_environment_raster import EXECUTABLE_SHA, _read_elf
from mc3_tire_vu import WHEEL_INTERVALS, WHEEL_PROGRAMS, unpack_microprogram
from mc3_vehicle_draw_reference import source_contract


def need(value, message):
    if not value:
        raise ValueError(message)


def native_registry(executable):
    """Derive the twelve constant registration calls, including delay slots."""
    need(
        hashlib.sha256(executable).hexdigest() == EXECUTABLE_SHA,
        "vehicle registry executable identity changed",
    )
    for name in ("builtin_binding", "custom_registration"):
        start, end, pin = WHEEL_INTERVALS[name]
        need(
            hashlib.sha256(_read_elf(executable, start, end - start)).hexdigest()
            == pin,
            "vehicle registry instruction interval changed",
        )
    need(
        struct.unpack("<I", _read_elf(executable, 0x615F98, 4))[0] == 1,
        "vehicle registry initial index changed",
    )
    proven = source_contract(executable)["programs"]
    registers, result, pc = {}, [], 0x3B58CC

    def constant(word):
        opcode, source, target, immediate = (
            word >> 26,
            word >> 21 & 31,
            word >> 16 & 31,
            word & 65535,
        )
        need(target in (4, 5), "registry constant writes unexpected argument")
        if opcode == 15:
            registers[target] = immediate << 16
        else:
            need(
                opcode == 9 and source in registers,
                "unsupported registry argument instruction",
            )
            registers[target] = (
                registers[source]
                + (immediate if immediate < 32768 else immediate - 65536)
            ) & 0xFFFFFFFF

    while pc < 0x3B59BC:
        word = struct.unpack("<I", _read_elf(executable, pc, 4))[0]
        if word >> 26 in (15, 9):
            constant(word)
        else:
            need(
                word >> 26 == 3 and (word & 0x3FFFFFF) * 4 == 0x2AEAC0,
                "unexpected vehicle registration call",
            )
            constant(struct.unpack("<I", _read_elf(executable, pc + 4, 4))[0])
            raw_name = _read_elf(executable, registers[4], 64)
            need(b"\0" in raw_name, "unterminated vehicle program name")
            name = raw_name.split(b"\0", 1)[0].decode("ascii")
            need(
                name in proven and proven[name]["address"] == registers[5],
                "vehicle program registration differs from whole-program source proof",
            )
            need(
                proven[name]["index"] == len(result) + 1,
                "vehicle program index differs",
            )
            result.append(
                dict(
                    index=len(result) + 1,
                    name=name,
                    registration_pc=pc,
                    name_address=registers[4],
                    **{
                        key: proven[name][key] for key in ("address", "bytes", "sha256")
                    },
                )
            )
            pc += 4
        pc += 4
    need(
        len(result) == 12 and len({row["name"] for row in result}) == 12,
        "vehicle program registration count changed",
    )
    return result


def build_program_pack(executable):
    """Retain the original VU instruction input, with separate source digests.

    This is execution data for the CPU interpreter. It does not synthesize
    uniforms, select an actor state or replace native material pass dispatch.
    """
    custom = native_registry(executable)
    builtins = []
    for variant in ("normal", "alternate"):
        address, size, pin, _ = WHEEL_PROGRAMS["builtin-" + variant]
        builtins.append(
            dict(
                index=0,
                variant=variant,
                name="builtin-" + variant,
                address=address,
                bytes=size,
                sha256=pin,
            )
        )
    programs = []
    for source in builtins + custom:
        packet = _read_elf(executable, source["address"], source["bytes"])
        need(
            hashlib.sha256(packet).hexdigest() == source["sha256"],
            "vehicle program packet changed",
        )
        pairs = unpack_microprogram(packet)
        code = b"".join(struct.pack("<II", *pairs[pc]) for pc in range(len(pairs)))
        programs.append(
            {
                **source,
                "instructions": len(pairs),
                "microcode_sha256": hashlib.sha256(code).hexdigest(),
                "microcode_base64": base64.b64encode(code).decode("ascii"),
            }
        )
    return dict(
        schema=1,
        source_executable_sha256=EXECUTABLE_SHA,
        programs=programs,
        claim_limits=[
            "Original instruction input and registry identities; complete material uniforms and actor state are supplied separately.",
            "Builtin null-override binding uses normal for selector0, alternate for any nonzero selector; explicit override programs are not substituted.",
            "Execution fidelity requires independent whole-program interpreter comparisons; this pack alone is not rendering evidence.",
        ],
    )
