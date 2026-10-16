"""Source-observed MAC semantics and prediction-independent original native job."""
import copy
import hashlib
import json
import unittest

from mc3_ee_mac import FIXTURE, PINS, SOURCE, cases, job
from mc3_environment_raster import EXECUTABLE_SHA


class NativeMACControls(unittest.TestCase):
    def test_source_and_exact_native_job(self):
        proof = json.loads(FIXTURE.read_text())
        self.assertEqual(proof['source']['executable_sha256'], EXECUTABLE_SHA)
        self.assertEqual(proof['source']['observed'], [list(row) for row in SOURCE])
        self.assertEqual(proof['source']['sources'], PINS)
        rows = [{k: v for k, v in row.items() if k not in ['expected_destination', 'expected_lo', 'expected_hi']}
                for row in proof['cases']]
        self.assertEqual(rows, json.loads(json.dumps(cases())))
        self.assertEqual(hashlib.sha256(job(rows)).hexdigest(), proof['execution']['job_sha256'])
        self.assertEqual(proof['execution']['runtime']['binary_sha256'],
                         '9b935133f224d29981200272492797eee4cb16fece3357119bf90c33cd62e48a')
        self.assertEqual(len(rows), 48)
        for row in proof['cases']:
            self.assertEqual(len(row['expected_destination']), 4)
            self.assertEqual(len(row['expected_lo']), 2)
            self.assertEqual(len(row['expected_hi']), 2)

    def test_expected_values_cannot_change_native_inputs(self):
        proof = json.loads(FIXTURE.read_text());changed = copy.deepcopy(proof['cases'])
        changed[0]['expected_destination'] = [0xffffffff]*4
        changed[0]['expected_lo'] = [0]*2;changed[0]['expected_hi'] = [0]*2
        self.assertEqual(job(changed), job(proof['cases']))
        self.assertEqual({row['kind'] for row in cases()}, {'mtlo', 'madd'})
        self.assertEqual(sum(row['kind'] == 'madd' for row in cases()), 44)
        self.assertTrue(any(row['instruction'] >> 11 & 31 == 0 for row in cases() if row['kind'] == 'madd'))


if __name__ == '__main__':
    unittest.main(verbosity=2)
