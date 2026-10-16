"""Original sampler control transport is independent of expected pixels."""
import copy
import hashlib
import json
from pathlib import Path
import tempfile
import unittest

from mc3_reference_runtime import write_gs_dump
from mc3_vehicle_variable_mip import EXTRA_SOURCES, FIXTURE, controls, packets
from mc3_vehicle_sampler import SOURCES


class VariableMipControls(unittest.TestCase):
    def test_original_transports_and_complete_records(self):
        proof = json.loads(FIXTURE.read_text())
        self.assertEqual(proof['sources'], SOURCES | EXTRA_SOURCES)
        self.assertEqual([r['case'] for r in proof['records']], controls())
        self.assertEqual(len(proof['records']), 18)
        for row in proof['records']:
            self.assertEqual(len(row['case']['levels']), 3)
            self.assertEqual(len(row['frames']), 3)
            self.assertEqual(len(row['depth_frames']), 3)
            self.assertEqual(row['execution']['runtime']['binary_sha256'],
                             '9b935133f224d29981200272492797eee4cb16fece3357119bf90c33cd62e48a')
            for level in row['case']['levels']:
                self.assertEqual(len(bytes.fromhex(level['data_hex'])), level['width']*level['height']*4)
            with tempfile.TemporaryDirectory() as directory:
                dump = Path(directory)/'control.gs'
                write_gs_dump(dump, packets(row['case']))
                self.assertEqual(hashlib.sha256(dump.read_bytes()).hexdigest(), row['execution']['dump_sha256'])

    def test_expected_output_does_not_change_input(self):
        row = json.loads(FIXTURE.read_text())['records'][0]
        bad = copy.deepcopy(row)
        bad['frames'][0]['sha256'] = '0'*64
        self.assertEqual(packets(row['case']), packets(bad['case']))
        bad['case']['tex1'] = '0'
        self.assertNotEqual(packets(row['case']), packets(bad['case']))


if __name__ == '__main__':
    unittest.main(verbosity=2)
