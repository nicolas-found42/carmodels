"""Native shared-format dispatch and small inline PSMT4 regression controls."""

import copy
import hashlib
import struct
import unittest

from mc3_vehicle_texture import (
    fragment_fixture,
    from_executable,
    native_pck4_window,
    native_shared_format,
    palette_reference_job,
    source_contract,
    verify_fragment_source,
)


class NativeVehicleTextureTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.fixture = fragment_fixture()
        w = cls.fixture["window"]
        data = bytearray(w["source_bytes"])
        for row in w["fragments"]:
            raw = bytes.fromhex(row["hex"])
            assert hashlib.sha256(raw).hexdigest() == row["sha256"]
            data[row["offset"] : row["offset"] + len(raw)] = raw
        cls.data, cls.slot = bytes(data), w["slot"]

    def test_default_native_dispatch_and_file_profile_pairs(self):
        for kind, bits, count, image in [
            (1, 8, 256, 5),
            (14, 8, 256, 5),
            (15, 4, 16, 6),
            (16, 4, 16, 6),
        ]:
            profile = native_shared_format(kind)
            self.assertEqual(
                (
                    profile["index_bits"],
                    profile["palette_entries"],
                    profile["native_image_format"],
                ),
                (bits, count, image),
            )
            self.assertEqual(
                (profile["palette_order"], profile["alpha_conversion"], profile["tcc"]),
                ("BGRA", "floor(A*128/255)", 1),
            )
        for kind in [0, 2, 17, True, "1"]:
            with self.subTest(kind=kind), self.assertRaises(ValueError):
                native_shared_format(kind)

    def test_retained_original_shared_files_have_exact_palette_and_all_mips(self):
        self.assertEqual(len(self.fixture["shared_files"]), 3)
        for row in self.fixture["shared_files"]:
            data = bytes.fromhex(row["hex"])
            self.assertEqual(hashlib.sha256(data).hexdigest(), row["sha256"])
            width, height, kind, mips = struct.unpack_from("<4H", data)
            profile = native_shared_format(kind)
            expected = 14 + profile["palette_entries"] * 4
            for _ in range(mips):
                expected += (width * height * profile["index_bits"] + 7) // 8
                width, height = max(1, width // 2), max(1, height // 2)
            self.assertEqual(expected, len(data))
        self.assertEqual(
            struct.unpack_from(
                "<4H", bytes.fromhex(self.fixture["shared_files"][1]["hex"])
            ),
            (64, 64, 1, 2),
        )

    def test_original_interpreter_palette_controls_and_replay_job_bindings(self):
        from mc3_reference_runtime import validate_job

        ramp = bytes(
            v
            for a in range(256)
            for v in ((a * 13) & 255, (a * 7) & 255, (a * 3) & 255, a)
        )
        palettes = [ramp]
        for row in self.fixture["shared_files"]:
            raw = bytes.fromhex(row["hex"])
            count = native_shared_format(struct.unpack_from("<H", raw, 4)[0])[
                "palette_entries"
            ]
            palettes.append(raw[14 : 14 + count * 4])
        measured = source_contract()["observed_reference"]["results"]
        self.assertEqual(len(measured), 4)
        for palette, actual in zip(palettes, measured, strict=True):
            self.assertEqual(
                hashlib.sha256(palette).hexdigest(), actual["input_sha256"]
            )
            expected = bytes(
                v
                for i in range(0, len(palette), 4)
                for v in (
                    palette[i + 2],
                    palette[i + 1],
                    palette[i],
                    palette[i + 3] * 128 // 255,
                )
            )
            self.assertEqual(
                hashlib.sha256(expected).hexdigest(), actual["output_sha256"]
            )
            self.assertEqual(actual["different_bytes"], 0)
            job = palette_reference_job(palette)
            validate_job(job, "ee")
            self.assertEqual(struct.unpack_from("<I", job, 8)[0], 0x524878)
            self.assertEqual(job[-len(palette) :], palette)
        for invalid in [b"", bytes(3), bytes(1028)]:
            with self.subTest(length=len(invalid)), self.assertRaises(ValueError):
                palette_reference_job(invalid)

    def test_actual_inline_window_is_eight_by_eight_white_native_alpha128(self):
        result = native_pck4_window(self.data, self.slot)
        self.assertEqual(result["decode_status"], "decoded")
        level = result["levels"][0]
        self.assertEqual(
            (level["width"], level["height"], level["source_offset"]), (8, 8, 0x6490)
        )
        self.assertEqual(level["rgba"], bytes([255, 255, 255, 128]) * 64)
        self.assertEqual(level["source_indices"], bytes(32))
        self.assertEqual(result["source_palette"], bytes([255, 255, 255, 128]) * 16)
        self.assertEqual(result["tex0"], "0x20000004cd404000")
        self.assertEqual(result["tex1"], "0xffffffc000000120")
        self.assertEqual(
            hashlib.sha256(level["rgba"]).hexdigest(),
            self.fixture["window"]["expected_rgba_sha256"],
        )

    def test_native_packed4_order_and_full_palette_alpha_are_preserved(self):
        data = bytearray(self.data)
        result = native_pck4_window(self.data, self.slot)
        start = result["levels"][0]["source_offset"]
        data[start] = 0x21
        data[start + 32 + 4 : start + 32 + 8] = bytes([5, 7, 9, 129])
        data[start + 32 + 8 : start + 32 + 12] = bytes([19, 23, 29, 255])
        rgba = native_pck4_window(bytes(data), self.slot)["levels"][0]["rgba"]
        self.assertEqual(rgba[:8], bytes([5, 7, 9, 129, 19, 23, 29, 255]))

    def test_alternate_sizes_mips_and_gs_pixel_modes_are_not_guessed(self):
        for offset, value in [(0x86, 2), (0x80, 3), (0x85, 2)]:
            data = bytearray(self.data)
            data[self.slot + offset] = value
            with self.subTest(offset=offset), self.assertRaises(ValueError):
                native_pck4_window(bytes(data), self.slot)
        for mask in [1 << 20, 1 << 26, 1 << 34, 1 << 55, 1 << 56]:
            data = bytearray(self.data)
            original = struct.unpack_from("<Q", data, self.slot + 16)[0]
            struct.pack_into("<Q", data, self.slot + 16, original ^ mask)
            with self.subTest(mask=mask), self.assertRaises(ValueError):
                native_pck4_window(bytes(data), self.slot)

    def test_descriptor_pointer_padding_and_payload_boundaries_fail_closed(self):
        for mutation in ("pointer", "padding", "payload"):
            data = bytearray(self.data)
            if mutation == "pointer":
                struct.pack_into("<I", data, self.slot + 0x48, 1)
            elif mutation == "padding":
                data[0x641C] = 0
            else:
                data[0x64F0] = 0
            with self.subTest(mutation=mutation), self.assertRaises(ValueError):
                native_pck4_window(bytes(data), self.slot)
        with self.assertRaises(ValueError):
            native_pck4_window(self.data[:0x64FF], self.slot)

    def test_profile_delta_and_original_ppf_pointer_conversion_are_explicit(self):
        data = bytearray(self.data)
        struct.pack_into(
            "<I", data, self.slot, struct.unpack_from("<I", data, self.slot)[0] + 0x1308
        )
        with self.assertRaisesRegex(ValueError, "class"):
            native_pck4_window(bytes(data), self.slot)
        base = struct.unpack_from("<I", data)[0]
        result = native_pck4_window(
            bytes(data), self.slot, 0x1308, to_offset=lambda value: value - base + 128
        )
        self.assertEqual(result["levels"][0]["rgba"], bytes([255, 255, 255, 128]) * 64)

    def test_receipt_and_executable_mutations_are_rejected(self):
        changed = copy.deepcopy(source_contract())
        changed["contract"]["shared_formats"]["1"]["index_bits"] = 4
        with self.assertRaisesRegex(ValueError, "receipt changed"):
            source_contract(changed)
        with self.assertRaisesRegex(ValueError, "executable identity"):
            from_executable(b"not original executable")
        with self.assertRaisesRegex(ValueError, "source identity"):
            verify_fragment_source(self.data)


if __name__ == "__main__":
    unittest.main(verbosity=2)
