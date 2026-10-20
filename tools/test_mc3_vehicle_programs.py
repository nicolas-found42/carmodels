"""Registry argument/delay-slot and execution-data preservation controls."""

import base64
from contextlib import ExitStack
import hashlib
import struct
import unittest
from unittest.mock import patch

import mc3_vehicle_programs as programs


def fixture():
    packet = struct.pack(
        "<8I", 0x60000001, 0, 0, 0, 0x4A010000, 0x8000033C, 0x400002FF, 0
    )
    packet_sha = hashlib.sha256(packet).hexdigest()
    code, rows, regions = (
        bytearray(),
        {},
        {0x615F98: struct.pack("<I", 1), 0x2A4E30: bytes(268)},
    )
    for index in range(12):
        name, name_at, packet_at = (
            "source" + str(index),
            0x650000 + index * 64,
            0x600000 + index * 64,
        )
        # Original registration argument forms; ADDIU a1 is the JAL delay slot.
        code += struct.pack(
            "<5I",
            0x3C040065,
            0x3C050060,
            0x24840000 | (name_at & 65535),
            0x0C000000 | (0x2AEAC0 >> 2),
            0x24A50000 | (packet_at & 65535),
        )
        regions[name_at], regions[packet_at] = (
            name.encode() + bytes(64 - len(name)),
            packet,
        )
        rows[name] = dict(
            index=index + 1, address=packet_at, bytes=len(packet), sha256=packet_sha
        )
    regions[0x3B58CC] = bytes(code)
    intervals = {
        "builtin_binding": (0x2A4E30, 0x2A4F3C, hashlib.sha256(bytes(268)).hexdigest()),
        "custom_registration": (0x3B58CC, 0x3B59BC, hashlib.sha256(code).hexdigest()),
    }
    return regions, rows, intervals, packet_sha


class ProgramsTests(unittest.TestCase):
    def environment(self, regions, rows, intervals, packet_sha):
        def read(_source, address, length):
            for base, raw in regions.items():
                if base <= address and address + length <= base + len(raw):
                    return raw[address - base : address - base + length]
            raise ValueError("synthetic region extent")

        stack = ExitStack()
        stack.enter_context(
            patch.object(
                programs, "EXECUTABLE_SHA", hashlib.sha256(b"fixture").hexdigest()
            )
        )
        stack.enter_context(patch.object(programs, "_read_elf", side_effect=read))
        stack.enter_context(
            patch.object(programs, "source_contract", return_value={"programs": rows})
        )
        stack.enter_context(patch.object(programs, "WHEEL_INTERVALS", intervals))
        stack.enter_context(
            patch.object(
                programs,
                "WHEEL_PROGRAMS",
                {
                    "builtin-normal": (0x600000, 32, packet_sha, ""),
                    "builtin-alternate": (0x600040, 32, packet_sha, ""),
                },
            )
        )
        return stack

    def test_registry_is_ordered_from_calls_and_delay_slot_arguments(self):
        regions, rows, intervals, pin = fixture()
        with self.environment(regions, rows, intervals, pin):
            result = programs.native_registry(b"fixture")
            self.assertEqual([row["index"] for row in result], list(range(1, 13)))
            self.assertEqual(
                [row["name"] for row in result], ["source" + str(i) for i in range(12)]
            )
            self.assertEqual(result[-1]["address"], 0x600000 + 11 * 64)
            pack = programs.build_program_pack(b"fixture")
            self.assertEqual(len(pack["programs"]), 14)
            self.assertEqual(
                [row["variant"] for row in pack["programs"][:2]],
                ["normal", "alternate"],
            )
            for row in pack["programs"]:
                code = base64.b64decode(row["microcode_base64"])
                self.assertEqual(code, struct.pack("<2I", 0x8000033C, 0x400002FF))
                self.assertEqual(
                    hashlib.sha256(code).hexdigest(), row["microcode_sha256"]
                )

    def test_registry_rejects_wrong_identity_instruction_index_and_program(self):
        regions, rows, intervals, pin = fixture()
        with self.environment(regions, rows, intervals, pin):
            with self.assertRaisesRegex(ValueError, "executable identity"):
                programs.native_registry(b"wrong")
            rows["source0"]["index"] = 2
            with self.assertRaisesRegex(ValueError, "index differs"):
                programs.native_registry(b"fixture")
            rows["source0"]["index"] = 1
            rows["source0"]["address"] += 4
            with self.assertRaisesRegex(ValueError, "registration differs"):
                programs.native_registry(b"fixture")
        regions, rows, intervals, pin = fixture()
        corrupted = bytearray(regions[0x3B58CC])
        struct.pack_into("<I", corrupted, 12, 0)
        regions[0x3B58CC] = bytes(corrupted)
        with self.environment(regions, rows, intervals, pin):
            with self.assertRaisesRegex(ValueError, "instruction interval"):
                programs.native_registry(b"fixture")
        intervals["custom_registration"] = (
            0x3B58CC,
            0x3B59BC,
            hashlib.sha256(corrupted).hexdigest(),
        )
        with self.environment(regions, rows, intervals, pin):
            with self.assertRaisesRegex(ValueError, "registration call"):
                programs.native_registry(b"fixture")

    def test_changed_packet_cannot_receive_source_program_identity(self):
        regions, rows, intervals, pin = fixture()
        regions[0x600000] = bytes(32)
        with self.environment(regions, rows, intervals, pin):
            with self.assertRaisesRegex(ValueError, "packet changed"):
                programs.build_program_pack(b"fixture")


if __name__ == "__main__":
    unittest.main(verbosity=2)
