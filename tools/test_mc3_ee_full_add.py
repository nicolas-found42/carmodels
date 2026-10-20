"""Full ADD original source and native input reconstruction controls."""

import copy
import hashlib
import json
import struct
import unittest

from mc3_ee_full_add import (
    ADDRESS,
    FIXTURE,
    WORD,
    cases,
    inputs,
    job,
    mflo_cases,
    mflo_job,
)
from mc3_environment_raster import EXECUTABLE_SHA


class FullAddControls(unittest.TestCase):
    def test_original_source_job_and_complete_vf(self):
        proof = json.loads(FIXTURE.read_text())
        source = proof["source"]
        raw = struct.pack("<I", WORD)
        self.assertEqual(
            source,
            dict(
                executable_sha256=EXECUTABLE_SHA,
                address=ADDRESS,
                instruction=WORD,
                hex=raw.hex(),
                sha256=hashlib.sha256(raw).hexdigest(),
            ),
        )
        self.assertEqual(
            [
                {k: v for k, v in row.items() if k != "expected_vf"}
                for row in proof["cases"]
            ],
            cases(),
        )
        self.assertEqual(proof["inputs"], inputs())
        self.assertEqual(
            hashlib.sha256(job(cases())).hexdigest(), proof["execution"]["job_sha256"]
        )
        self.assertEqual(
            proof["execution"]["runtime"]["binary_sha256"],
            "9b935133f224d29981200272492797eee4cb16fece3357119bf90c33cd62e48a",
        )
        self.assertEqual(len(cases()), 69)
        for row in proof["cases"]:
            self.assertEqual(len(row["expected_vf"]), 128)
            self.assertEqual(row["expected_vf"][:4], [0, 0, 0, 0x3F800000])

    def test_source_mflo_job_and_upper128(self):
        proof = json.loads(FIXTURE.read_text())
        raw = struct.pack("<II", 0x00460018, 0x00003012)
        self.assertEqual(
            proof["mflo_source"],
            dict(
                address=0x2B7848, hex=raw.hex(), sha256=hashlib.sha256(raw).hexdigest()
            ),
        )
        rows = proof["mflo"]["cases"]
        self.assertEqual(
            [{k: v for k, v in row.items() if k != "expected_words"} for row in rows],
            mflo_cases(),
        )
        self.assertEqual(
            hashlib.sha256(mflo_job(rows)).hexdigest(),
            proof["mflo"]["execution"]["job_sha256"],
        )
        changed = copy.deepcopy(rows)
        changed[0]["expected_words"] = [0] * 4
        self.assertEqual(mflo_job(changed), mflo_job(rows))
        self.assertEqual(len(rows), 8)

    def test_expected_outputs_cannot_affect_original_job(self):
        proof = json.loads(FIXTURE.read_text())
        changed = copy.deepcopy(proof["cases"])
        changed[0]["expected_vf"] = [0xFFFFFFFF] * 128
        self.assertEqual(job(changed), job(proof["cases"]))
        self.assertEqual((WORD & 63, WORD >> 21 & 15), (40, 2))


if __name__ == "__main__":
    unittest.main(verbosity=2)
