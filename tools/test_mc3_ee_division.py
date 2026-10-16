"""Independent input reconstruction for original observed SDK integer opcodes."""
import copy
import hashlib
import json
import unittest

from mc3_ee_division import FIXTURE, SOURCE, ACCUMULATORS, cases, job
from mc3_ee_mac import PINS


class IntegerTests(unittest.TestCase):
    def test_original_source_and_exact_native_job(self):
        proof = json.loads(FIXTURE.read_text())
        self.assertEqual(proof['source']['sources'], PINS)
        self.assertEqual(proof['source']['observed'], [list(row) for row in SOURCE])
        self.assertEqual(proof['accumulator_inputs'], ACCUMULATORS)
        rows = [{key: value for key, value in row.items() if not key.startswith('expected_')}
                for row in proof['cases']]
        self.assertEqual(rows, cases())
        self.assertEqual(hashlib.sha256(job(rows)).hexdigest(), proof['execution']['job_sha256'])
        self.assertEqual(proof['execution']['runtime']['binary_sha256'],
                         '9b935133f224d29981200272492797eee4cb16fece3357119bf90c33cd62e48a')

    def test_predictions_cannot_change_original_execution_inputs(self):
        rows = json.loads(FIXTURE.read_text())['cases']
        changed = copy.deepcopy(rows)
        for row in changed:
            row['expected_destination'] = [0]*4
            row['expected_accumulators'] = [0]*8
        self.assertEqual(job(rows), job(changed))
        self.assertEqual({row['kind'] for row in rows}, {'div', 'divu', 'mfhi', 'daddiu', 'dsubu', 'mult1'})
        self.assertTrue(any(row['name'] == 'div-minimum-overflow' for row in rows))
        self.assertTrue(any(row['name'] == 'div-zero-divisor-negative' for row in rows))
        self.assertTrue(any(row['name'] == 'daddiu-wrap64-zero' for row in rows))


if __name__ == '__main__':
    unittest.main(verbosity=2)
