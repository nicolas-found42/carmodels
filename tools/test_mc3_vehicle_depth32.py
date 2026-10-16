"""Literal selected GS inputs and source-pinned Z32 readback controls."""
import copy
import hashlib
import json
import tempfile
import unittest
from pathlib import Path

from mc3_reference_runtime import write_gs_dump
from mc3_vehicle_depth32 import FIXTURE, READBACK_SOURCES, SOURCES, cases, fragment_packets, sprite_packets, sprites


class Depth32Tests(unittest.TestCase):
    def test_original_native_dump_inputs_and_all_full_outputs(self):
        proof = json.loads(FIXTURE.read_text())
        self.assertEqual(len(proof['records']), 5)
        self.assertEqual(len(cases()), 80)
        source = [('fragments', cases(), fragment_packets(cases()))]+[(v['name'], v, sprite_packets(v)) for v in sprites()]
        for (name, inputs, packets), row in zip(source, proof['records'], strict=True):
            self.assertEqual((name, inputs), (row['name'], row['inputs']))
            with tempfile.TemporaryDirectory() as directory:
                p = Path(directory)/'native.gs';write_gs_dump(p, packets)
                self.assertEqual(hashlib.sha256(p.read_bytes()).hexdigest(), row['execution']['dump_sha256'])
            for field in ['frames', 'depth_frames']:
                self.assertEqual(len(row[field]), 3)
                self.assertEqual(len({v['sha256'] for v in row[field]}), 1)
                for frame in row[field]:
                    self.assertEqual(frame['bytes'], frame['size'][0]*frame['size'][1]*4)
            self.assertEqual(row['execution']['runtime']['binary_sha256'],
                             '9b935133f224d29981200272492797eee4cb16fece3357119bf90c33cd62e48a')
        self.assertEqual(proof['records'][0]['frames'][0]['size'][0], 256, 'all16 columns of controls must be observable')

    def test_input_states_cover_unsigned_depth_and_do_not_depend_on_expected_outputs(self):
        rows = cases()
        self.assertEqual({v['state']['afail'] for v in rows}, {0, 1, 2, 3})
        self.assertEqual({v['state']['ztst'] for v in rows}, {0, 1, 2, 3})
        self.assertTrue(any(v['z'] == 0xffffffff for v in rows))
        self.assertTrue(any(v['z'] == 0x80000000 and v['destinationZ'] == 0x7fffffff for v in rows))
        self.assertTrue(any(v['z'] == 0x7fffffff and v['destinationZ'] == 0x80000000 for v in rows))
        self.assertTrue(any(v['state']['zmsk'] for v in rows))
        self.assertTrue(any(not v['state']['zte'] for v in rows))
        proof = json.loads(FIXTURE.read_text());changed = copy.deepcopy(proof)
        changed['records'][0]['frames'][0]['sha256'] = '0'*64
        self.assertEqual(fragment_packets(changed['records'][0]['inputs']), fragment_packets(rows))
        self.assertEqual(proof['depth_readback_sources'], READBACK_SOURCES)
        self.assertEqual(proof['sources'], SOURCES)


if __name__ == '__main__':
    unittest.main(verbosity=2)
