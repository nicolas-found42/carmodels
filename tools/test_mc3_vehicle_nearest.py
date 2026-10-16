"""Source reconstruction checks; original GS jobs execute via the separate reference CLI."""
import copy
import hashlib
import json
import tempfile
import unittest
from pathlib import Path
from mc3_vehicle_nearest import FIXTURE, controls, packets
from mc3_reference_runtime import write_gs_dump


class NearestTests(unittest.TestCase):
    def test_original_contexts_and_literal_native_transport(self):
        proof = json.loads(FIXTURE.read_text())
        self.assertEqual(len(proof['records']), 4)
        for case, row in zip(controls(), proof['records'], strict=True):
            self.assertEqual(case, row['case'])
            with tempfile.TemporaryDirectory() as directory:
                path = Path(directory)/'probe.gs'
                write_gs_dump(path, packets(case))
                self.assertEqual(hashlib.sha256(path.read_bytes()).hexdigest(), row['execution']['dump_sha256'])
            self.assertEqual(row['execution']['runtime']['binary_sha256'],
                             '9b935133f224d29981200272492797eee4cb16fece3357119bf90c33cd62e48a')
            for field in ['frames', 'depth_frames']:
                self.assertEqual(len(row[field]), 3)
                self.assertEqual(len({v['sha256'] for v in row[field]}), 1)
            changed = copy.deepcopy(row)
            changed['frames'][0]['sha256'] = '0'*64
            self.assertEqual(packets(case), packets(changed['case']), 'expected frames never feed native jobs')
        self.assertEqual([v['constantQ'] for v in controls()], [True, True, False, True])


if __name__ == '__main__':
    unittest.main(verbosity=2)
