import copy
import hashlib
import struct
import unittest
from unittest.mock import patch

import mc3_texture_binding as binding


class TextureBindingTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.proof = binding.fixture()
        source = cls.proof["pf05"]
        data = bytearray(source["source_bytes"])
        for row in source["fragments"]:
            raw = bytes.fromhex(row["hex"])
            assert hashlib.sha256(raw).hexdigest() == row["sha256"]
            data[row["offset"] : row["offset"] + len(raw)] = raw
        cls.pf05 = bytes(data)

    def test_whole_native_factory_jobs_and_constructor_fields(self):
        self.assertEqual(len(self.proof["factory"]), 5)
        for row in self.proof["factory"]:
            data = bytes.fromhex(row["data_hex"])
            job = binding.factory_reference_job(data, **row["context"])
            self.assertEqual(
                hashlib.sha256(job).hexdigest(), row["execution"]["job_sha256"]
            )
            self.assertEqual(
                row["execution"]["original_mc3_executable_sha256"],
                binding.EXECUTABLE_SHA,
            )
            actual = bytes.fromhex(row["result"]["constructor_hex"])
            expected = binding.native_shared_texture_state(data)
            self.assertEqual(
                [
                    f"0x{struct.unpack_from('<Q', actual, 16 + i * 16)[0]:016x}"
                    for i in range(actual[0x86])
                ],
                [v["tex0"] for v in expected["levels"]],
            )
            self.assertEqual(
                f"0x{struct.unpack_from('<Q', actual, 0x88)[0]:016x}", expected["tex1"]
            )
            self.assertEqual(actual[0x85], expected["clamp"])
            changed = copy.deepcopy(row)
            changed["result"]["registers"] = []
            self.assertEqual(
                binding.factory_reference_job(
                    bytes.fromhex(changed["data_hex"]), **changed["context"]
                ),
                job,
                "recorded native outputs never enter native input construction",
            )
        counts = [
            len(
                binding.native_shared_texture_state(bytes.fromhex(v["data_hex"]))[
                    "levels"
                ]
            )
            for v in self.proof["factory"]
        ]
        self.assertEqual(counts, [1, 2, 2, 4, 4])

    def test_source_resource_resolver_job_and_pointer(self):
        source = self.proof["resolver"]
        job = binding.resolver_reference_job(**source["context"])
        self.assertEqual(
            hashlib.sha256(job).hexdigest(), source["execution"]["job_sha256"]
        )
        self.assertEqual(
            source["pointer"],
            source["context"]["loaded_base"] + source["context"]["offset"],
        )
        for context in [
            dict(source["context"], packed_handle=0),
            dict(source["context"], offset=-1),
        ]:
            with self.assertRaises(ValueError):
                binding.resolver_reference_job(**context)

    def test_all14_original_wheel_resource_joins_and_native_texels(self):
        counts = {}
        self.assertEqual(len(self.proof["pf05"]["slots"]), 14)
        for row in self.proof["pf05"]["slots"]:
            result = binding.decode_pf05_texture(
                self.pf05, row["slot_offset"], archive_index=5
            )
            self.assertEqual(
                hashlib.sha256(result["levels"][0]["rgba"]).hexdigest(),
                row["rgba_sha256"],
            )
            self.assertEqual(result["source_page_index"], row["source_page_index"])
            self.assertEqual(
                len(result["source_slot"]),
                160,
                "TEX1/cache/mip words must not be cut at128bytes",
            )
            slot = binding.native_texture_slot(self.pf05, row["slot_offset"], 0x1308)
            counts[slot["levels"][0]["psm"]] = (
                counts.get(slot["levels"][0]["psm"], 0) + 1
            )
            self.assertEqual(int(result["tex1"], 16) >> 6 & 7, 4)
        self.assertEqual(counts, {19: 12, 20: 2})

    def test_boundaries_reject_missing_source_and_other_profiles(self):
        row = self.proof["pf05"]["slots"][0]
        offset = row["slot_offset"]
        with self.assertRaisesRegex(ValueError, "another archive"):
            binding.decode_pf05_texture(self.pf05, offset, archive_index=4)
        with self.assertRaisesRegex(ValueError, "outside source"):
            binding.native_texture_slot(self.pf05[offset : offset + 128], 0, 0x1308)
        changed = bytearray(self.pf05)
        struct.pack_into("<I", changed, offset + 0x4C, 0xFFFFFFFF)
        with self.assertRaisesRegex(ValueError, "outside selected page"):
            binding.decode_pf05_texture(bytes(changed), offset, archive_index=5)
        changed = bytearray(self.pf05)
        struct.pack_into("<H", changed, offset + 0x80, 0)
        with self.assertRaisesRegex(ValueError, "extent differs"):
            binding.decode_pf05_texture(bytes(changed), offset, archive_index=5)
        with self.assertRaisesRegex(ValueError, "RAM extent"):
            binding.decode_factory_reference(b"")

    def test14_original_native_uploads_sample_exact_original_images_and_depth(self):
        rows = self.proof["pf05_gs"]
        self.assertEqual(len(rows), 14)
        for row in rows:
            source = self.proof["pf05"]["slots"][row["slot_index"]]
            decoded = binding.decode_pf05_texture(
                self.pf05, source["slot_offset"], archive_index=5
            )
            block = decoded["source_block_offset"]
            size = struct.unpack_from("<I", self.pf05, block + 12)[0]
            job = binding.slot_reference_job(
                decoded["source_slot"],
                self.pf05[block : block + size],
                **row["context"],
            )
            self.assertEqual(hashlib.sha256(job).hexdigest(), row["ee"]["job_sha256"])
            self.assertEqual(
                row["ee"]["original_mc3_executable_sha256"], binding.EXECUTABLE_SHA
            )
            self.assertEqual(
                row["gs"]["runtime"]["binary_sha256"],
                "9b935133f224d29981200272492797eee4cb16fece3357119bf90c33cd62e48a",
            )
            level = decoded["levels"][0]
            width, height = level["width"], level["height"]
            rgba, depth = bytearray(256 * 256 * 4), bytearray(256 * 256 * 2)
            for y in range(height):
                rgba[y * 256 * 4 : y * 256 * 4 + width * 4] = level["rgba"][
                    y * width * 4 : (y + 1) * width * 4
                ]
                for x in range(width):
                    struct.pack_into("<H", depth, (y * 256 + x) * 2, 1)
            for field, pixels, stride in [
                ("frames", rgba, 4),
                ("depth_frames", depth, 2),
            ]:
                self.assertEqual(len(row[field]), 3)
                for frame in row[field]:
                    w, h = frame["size"]
                    exported = b"".join(
                        pixels[y * 256 * stride : y * 256 * stride + w * stride]
                        for y in range(h)
                    )
                    self.assertEqual(
                        hashlib.sha256(exported).hexdigest(), frame["sha256"]
                    )

    def test_original_executable_and_source_interval_pins(self):
        with self.assertRaisesRegex(ValueError, "executable changed"):
            binding.from_executable(b"changed")
        with (
            patch.object(
                binding, "EXECUTABLE_SHA", hashlib.sha256(b"fixture").hexdigest()
            ),
            patch("mc3_environment_raster._read_elf", return_value=b"changed interval"),
        ):
            with self.assertRaisesRegex(ValueError, "source interval changed"):
                binding.from_executable(b"fixture")


if __name__ == "__main__":
    unittest.main(verbosity=2)
