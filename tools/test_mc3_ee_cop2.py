"""Literal original EE macro source and complete native job controls."""
import copy
import hashlib
import json
import struct
import unittest

from mc3_ee_cop2 import ADDI_SOURCE, FIXTURE, INPUT, INTERVAL_SHA, OUTPUT, SOURCE, START, addi_cases, addi_wrapper, cases, inputs, macro, native_inputs, source_proof, wrapper
from mc3_environment_raster import EXECUTABLE_SHA, encode_ee_job


class MacroControls(unittest.TestCase):
    def test_original_source_and_native_job(self):
        proof = json.loads(FIXTURE.read_text())
        source = proof['source']
        self.assertEqual(source['executable_sha256'], EXECUTABLE_SHA)
        raw = bytes.fromhex(source['hex'])
        self.assertEqual(hashlib.sha256(raw).hexdigest(), INTERVAL_SHA)
        self.assertEqual(source['sha256'], INTERVAL_SHA)
        for address, instruction in SOURCE+ADDI_SOURCE:
            self.assertEqual(struct.unpack_from('<I', raw, address-source['address'])[0], instruction)
        expected = cases()
        actual = [{k: v for k, v in row.items() if k != 'expected_vf'} for row in proof['cases']]
        self.assertEqual(actual, expected)
        self.assertEqual(proof['inputs'], inputs())
        code = struct.pack('<'+'I'*len(wrapper(expected)), *wrapper(expected))
        input_data = native_inputs(expected)
        job = encode_ee_job(START, {}, [(START, code), (INPUT, input_data)])
        self.assertEqual(hashlib.sha256(job).hexdigest(), proof['execution']['job_sha256'])
        self.assertEqual(proof['execution']['runtime']['binary_sha256'],
                         '9b935133f224d29981200272492797eee4cb16fece3357119bf90c33cd62e48a')
        self.assertEqual(len(expected), 135)
        for row in proof['cases']:
            self.assertEqual(len(row['expected_vf']), 128)
            self.assertEqual(row['expected_vf'][:4], [0, 0, 0, 0x3f800000])
        self.assertLess(OUTPUT+len(expected)*512, 0x2000000)

    def test_addi_original_job_and_source_boundaries(self):
        proof = json.loads(FIXTURE.read_text())['addi']
        rows = addi_cases()
        self.assertEqual([{k: v for k, v in row.items() if k != 'expected_words'} for row in proof['cases']], rows)
        code = addi_wrapper(rows)
        job = encode_ee_job(START, {}, [(START, struct.pack('<'+'I'*len(code), *code)),
                                       (0x1300000, b''.join(struct.pack('<8I', *v['input_words']) for v in rows))])
        self.assertEqual(hashlib.sha256(job).hexdigest(), proof['execution']['job_sha256'])
        changed = copy.deepcopy(proof['cases'])
        changed[0]['expected_words'] = [0]*4
        self.assertEqual(addi_wrapper(changed), addi_wrapper(rows))
        self.assertEqual(len(rows), 11)

    def test_expected_values_cannot_affect_native_inputs(self):
        proof = json.loads(FIXTURE.read_text())
        changed = copy.deepcopy(proof['cases'])
        changed[0]['expected_vf'] = [0xffffffff]*128
        self.assertEqual(wrapper(changed), wrapper(proof['cases']))
        with self.assertRaisesRegex(ValueError, 'executable differs'):
            source_proof(b'wrong original source')
        self.assertEqual(macro(42, 4, 8, 8), 0x4be8412a)


if __name__ == '__main__':
    unittest.main(verbosity=2)
