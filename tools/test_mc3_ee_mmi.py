"""Pinned source PCPYLD and original prediction-independent input controls."""
import copy
import hashlib
import json
import struct
import unittest

from mc3_ee_mmi import FIXTURE, PINS, SOURCE, cases, instruction, job, source_proof
from mc3_environment_raster import EXECUTABLE_SHA


class PackedCopyControls(unittest.TestCase):
    def test_source_words_and_exact_native_job(self):
        proof = json.loads(FIXTURE.read_text())
        self.assertEqual(proof['source']['executable_sha256'], EXECUTABLE_SHA)
        self.assertEqual([(r['address'], r['instruction']) for r in proof['source']['observed']], SOURCE)
        for row in proof['source']['observed']:
            self.assertEqual(bytes.fromhex(row['hex']), struct.pack('<I', row['instruction']))
            w = row['instruction']
            self.assertEqual((w >> 26, w & 63, w >> 6 & 31), (28, 9, 14))
        self.assertEqual({k: v['sha256'] for k, v in proof['source']['sources'].items()}, PINS)
        self.assertEqual([{k: v for k, v in row.items() if k != 'expected_words'} for row in proof['cases']], cases())
        self.assertEqual(hashlib.sha256(job(cases())).hexdigest(), proof['execution']['job_sha256'])
        self.assertEqual(proof['execution']['runtime']['binary_sha256'],
                         '9b935133f224d29981200272492797eee4cb16fece3357119bf90c33cd62e48a')
        self.assertEqual(len(cases()), 24)

    def test_controls_are_independent_and_bounded(self):
        proof = json.loads(FIXTURE.read_text());changed = copy.deepcopy(proof['cases'])
        changed[0]['expected_words'] = [0xffffffff]*4
        self.assertEqual(job(changed), job(proof['cases']))
        changed[0]['registers'][0][0] = 10
        with self.assertRaisesRegex(ValueError, 'aliases wrapper context'):
            job(changed)
        with self.assertRaisesRegex(ValueError, 'executable differs'):
            source_proof(b'wrong executable', b'', b'')
        self.assertEqual(instruction(2, 7, 3), 0x70e31389)


if __name__ == '__main__':
    unittest.main(verbosity=2)
