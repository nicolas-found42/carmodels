"""Original macro decoder/source identities and prediction-independent native job."""
import copy
import hashlib
import json
import struct
import unittest

from mc3_ee_mr32 import FIXTURE, INPUT, PINS, SOURCE, START, cases, inputs, mr32, source_proof, wrapper
from mc3_environment_raster import EXECUTABLE_SHA, encode_ee_job


class MacroRotateControls(unittest.TestCase):
    def test_original_source_and_job(self):
        proof = json.loads(FIXTURE.read_text())
        source = proof['source']
        self.assertEqual(source['executable_sha256'], EXECUTABLE_SHA)
        raw = bytes.fromhex(source['hex'])
        self.assertEqual(raw, struct.pack('<4I', *(w for _, w in SOURCE)))
        self.assertEqual(hashlib.sha256(raw).hexdigest(), source['sha256'])
        self.assertEqual({k: v['sha256'] for k, v in source['sources'].items()}, PINS)
        rows = cases()
        self.assertEqual([{k: v for k, v in row.items() if k != 'expected_vf'} for row in proof['cases']], rows)
        self.assertEqual(proof['inputs'], inputs())
        words = wrapper(rows)
        job = encode_ee_job(START, {}, [(START, struct.pack('<'+'I'*len(words), *words)),
                                       (INPUT, struct.pack('<128I', *inputs())*len(rows))])
        self.assertEqual(hashlib.sha256(job).hexdigest(), proof['execution']['job_sha256'])
        self.assertEqual(proof['execution']['runtime']['binary_sha256'],
                         '9b935133f224d29981200272492797eee4cb16fece3357119bf90c33cd62e48a')
        self.assertEqual(len(rows), 38)
        for row in proof['cases']:
            self.assertEqual(len(row['expected_vf']), 128)
            self.assertEqual(row['expected_vf'][:4], [0, 0, 0, 0x3f800000])

    def test_control_independence_and_source_guards(self):
        proof = json.loads(FIXTURE.read_text());changed = copy.deepcopy(proof['cases'])
        changed[0]['expected_vf'] = [0xffffffff]*128
        self.assertEqual(wrapper(changed), wrapper(proof['cases']))
        self.assertEqual(mr32(6, 6), SOURCE[0][1])
        with self.assertRaisesRegex(ValueError, 'executable differs'):
            source_proof(b'wrong executable', b'', b'')


if __name__ == '__main__':
    unittest.main(verbosity=2)
