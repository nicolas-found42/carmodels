"""Fail-closed source table and literal upload regression controls."""
import hashlib
import json
import unittest

from mc3_vehicle_vram import FIXTURE, SOURCE_SHA, controls, verify_tables


class NativeVRAMTests(unittest.TestCase):
    def test_fixture(self):
        proof = json.loads(FIXTURE.read_text())
        self.assertEqual(proof['source']['commit'], 'fd9d310ccbb6b8b62c976da8886a3c8fd3a10ff3')
        self.assertEqual(proof['source']['exhaustive_columns'], {'32': 64, '8': 256, '4': 512})
        self.assertEqual([r['case'] for r in proof['controls']], controls())
        for row in proof['controls']:
            self.assertEqual(row['execution']['runtime']['binary_sha256'], '9b935133f224d29981200272492797eee4cb16fece3357119bf90c33cd62e48a')
            for name in ['frames', 'depth_frames']:
                frames = row['execution'][name]
                self.assertEqual(len(frames), 3)
                self.assertEqual(len({f['sha256'] for f in frames}), 1)

    def test_every_original_column(self):
        proof = json.loads(FIXTURE.read_text())
        source = bytes.fromhex(proof['source']['table_source_hex'])
        self.assertEqual(hashlib.sha256(source).hexdigest(), SOURCE_SHA)
        self.assertEqual(proof['source']['gstables_sha256'], SOURCE_SHA)
        self.assertEqual(verify_tables(source.decode()), {'32': 64, '8': 256, '4': 512})
        with self.assertRaises(ValueError):
            verify_tables(source.decode().replace('{  0,  1,  4,  5,  8,  9, 12, 13 }', '{  1,  0,  4,  5,  8,  9, 12, 13 }', 1))


if __name__ == '__main__':
    unittest.main(verbosity=2)
