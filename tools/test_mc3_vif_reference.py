from pathlib import Path
import struct
import unittest
from unittest.mock import patch

import mc3_vif_reference as reference


class VIFReferenceTests(unittest.TestCase):
    def test_original_job_inputs_are_reproducible(self):
        proof = reference.contract()
        cases = reference.reference_cases()
        self.assertEqual(len(cases), len(proof["cases"]))
        for (inputs, case), expected in zip(cases, proof["cases"]):
            self.assertEqual(inputs, {key: expected[key] for key in inputs})
            self.assertEqual(reference.sha(case), expected["case_sha256"])
        job = reference.build_job([case for _, case in cases])
        self.assertEqual(reference.validate_job(job), len(cases))
        self.assertEqual(reference.sha(job), proof["job_sha256"])

    def test_changed_native_adapter_cannot_use_prior_proof(self):
        original = Path.read_bytes

        def changed(path):
            return b"changed adapter" if path == reference.ADAPTER else original(path)

        with patch.object(Path, "read_bytes", changed):
            with self.assertRaisesRegex(ValueError, "adapter differs"):
                reference.contract()

    def test_wrong_binary_is_rejected_before_offsets_are_used(self):
        with self.assertRaisesRegex(ValueError, "binary identity"):
            reference.from_binary(b"not the original binary")

    def test_256_v3_vectors_cannot_reuse_an_eight_vector_source(self):
        job = bytearray(reference.build_job([reference.reference_cases()[0][1]]))
        struct.pack_into("<I", job, 12 + 144 + 96, 256)
        with self.assertRaisesRegex(ValueError, "source payload"):
            reference.validate_job(job)

    def test_fill_cycles_need_only_the_consumed_source_vectors(self):
        case = reference.unpack_case(
            kind=12, alignment=1, count=8, cl=1, wl=4, data=bytes(32)
        )
        reference.validate_job(reference.build_job([case]))
        case = reference.unpack_case(
            kind=12, alignment=1, count=8, cl=1, wl=4, data=bytes(16)
        )
        with self.assertRaisesRegex(ValueError, "source payload"):
            reference.build_job([case])

    def test_malformed_state_and_truncation_are_rejected(self):
        job = reference.build_job([reference.reference_cases()[0][1]])
        for offset, value in (
            (12 + 48, 0x63),
            (12 + 144 + 80, 4),
            (12 + 144 + 96, 0),
            (12 + 32, 16384),
        ):
            changed = bytearray(job)
            struct.pack_into("<I", changed, offset, value)
            with self.assertRaises(ValueError):
                reference.validate_job(changed)
        for changed in (job[:-1], job + b"extra"):
            with self.assertRaises(ValueError):
                reference.validate_job(changed)


if __name__ == "__main__":
    unittest.main(verbosity=2)
