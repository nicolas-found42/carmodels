"""Bounded source identity, exact caller inputs and uploader refusal controls."""

import copy
import struct
import unittest

from mc3_environment_raster import encode_ee_job
from mc3_vehicle_uniforms import (
    CODE,
    DMA,
    RESULT,
    caller,
    from_executable,
    output,
    sha,
    source_contract,
)


class VehicleUniformTests(unittest.TestCase):
    def test_all_original_reference_jobs_reconstruct(self):
        proof = source_contract()
        self.assertEqual(len(proof["cases"]), 4)
        for case in proof["cases"]:
            job = encode_ee_job(CODE, {}, caller(case["context"]))
            self.assertEqual(sha(job), case["job_sha256"], case["name"])
            self.assertEqual(case["expected"]["dma_bytes"], 704)
        for first, second in zip(proof["cases"][::2], proof["cases"][1::2]):
            self.assertEqual(first["expected"], second["expected"])
            self.assertNotEqual(first["job_sha256"], second["job_sha256"])
        self.assertNotEqual(
            proof["cases"][0]["expected"]["dma_sha256"],
            proof["cases"][2]["expected"]["dma_sha256"],
        )

    def test_context_refuses_unmeasured_display_or_missing_words(self):
        context = source_contract()["cases"][0]["context"]
        for mutate in (
            lambda c: c.update(backend=2),
            lambda c: c["display_words"].__setitem__(0, 640),
            lambda c: c.update(frame_words=[0] * 11),
            lambda c: c.update(light_words=[0] * 34 + [-1]),
            lambda c: c["projection_words"].__setitem__(0, 0x7F800000),
            lambda c: c["projection_words"].__setitem__(1, 0),
            lambda c: c["pose_words"].__setitem__(15, 0),
            lambda c: c.update(clip_scale_word=0),
            lambda c: c.update(guessed_camera=True),
        ):
            bad = copy.deepcopy(context)
            mutate(bad)
            with self.assertRaisesRegex(ValueError, "vehicle uniform"):
                caller(bad)

    def test_source_and_receipt_changes_refused(self):
        with self.assertRaisesRegex(ValueError, "executable differs"):
            from_executable(b"not original executable")
        proof = source_contract()
        for mutate in (
            lambda p: p["cases"][0]["context"]["pose_words"].__setitem__(0, 0),
            lambda p: p["intervals"][0].update(start=0),
            lambda p: p["cases"][0]["expected"].update(dma_sha256="0" * 64),
        ):
            bad = copy.deepcopy(proof)
            mutate(bad)
            with self.assertRaisesRegex(ValueError, "receipt differs"):
                source_contract(bad)

    def test_dma_refuses_unallocated_end_or_changed_tag(self):
        with self.assertRaisesRegex(ValueError, "RAM extent"):
            output(bytes(16))
        ram = bytearray(0x2000000)
        for end in (0, DMA, DMA + 1, 0x1110010):
            struct.pack_into("<I", ram, RESULT, end)
            with self.assertRaisesRegex(ValueError, "DMA end"):
                output(ram)
        struct.pack_into("<I", ram, RESULT, DMA + 32)
        with self.assertRaisesRegex(ValueError, "DMA tag"):
            output(ram)
        struct.pack_into("<I", ram, DMA, 0x10000002)
        with self.assertRaisesRegex(ValueError, "DMA extent"):
            output(ram)


if __name__ == "__main__":
    unittest.main(verbosity=2)
