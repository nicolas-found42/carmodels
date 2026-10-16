import copy
import hashlib
import json
from pathlib import Path
import struct
import tempfile
import unittest

import mc3_vehicle_gif as gif
from mc3_reference_runtime import BINARY_SHA


class VehicleGIFTests(unittest.TestCase):
    def test_native_control_inputs_and_original_output_identities(self):
        proof = json.loads(gif.FIXTURE.read_text())
        self.assertEqual([row['case'] for row in proof['records']], gif.controls())
        self.assertEqual(gif.verify_reference(proof, copy.deepcopy(proof)), dict(status='pass', controls=8, programs=13))
        for row in proof['records']:
            self.assertEqual(row['runtime']['binary_sha256'], BINARY_SHA)
            for field in ['frames', 'depth_frames']:
                self.assertEqual(len(row[field]), 3)
                self.assertEqual(len({v['sha256'] for v in row[field]}), 1)
        changed = copy.deepcopy(proof)
        changed['records'][0]['frames'][0]['sha256'] = '0'*64
        with self.assertRaisesRegex(ValueError, 'output bytes differ'):
            gif.verify_reference(changed, proof)
        changed = copy.deepcopy(proof)
        changed['native_transports'][0]['job_sha256'] = '0'*64
        with self.assertRaisesRegex(ValueError, 'transport inputs differ'):
            gif.verify_reference(changed, proof)

    def test_reglist_padding_packed_xyz_and_no_expected_pixels(self):
        vertex = dict(xy=[16, 32], z=2000, rgba=[11, 22, 33, 44], stq=[.25, .5, 1], uv=[4, 8])
        packed = gif.packed([vertex], 4)
        self.assertEqual(len(packed), 64)
        self.assertEqual(struct.unpack_from('<I', packed, 56)[0], 2000 << 4)
        xyz2 = gif.packed([vertex], 4, xyz2=True)
        self.assertEqual(struct.unpack_from('<I', xyz2, 56)[0], 2000)
        listed = gif.reglist([vertex], 3)
        self.assertEqual(len(listed), 16+24+8)
        self.assertEqual(listed[-8:], bytes(8))
        vertex['expected_rgba'] = [255]*4
        self.assertEqual(packed, gif.packed([vertex], 4))
        vertex['rgba'][0] ^= 1
        self.assertNotEqual(packed, gif.packed([vertex], 4))

    def test_original_transport_requires_receipt_job_and_complete_registry(self):
        with tempfile.TemporaryDirectory() as name:
            root = Path(name)
            with self.assertRaisesRegex(ValueError, 'all13'):
                gif.native_transports(root)
            run = root/'fake-run'
            run.mkdir()
            raw = struct.pack('<I', 16)+bytes(16)
            (run/'gif-chunks.bin').write_bytes(raw)
            (root/'fake.job').write_bytes(b'job')
            receipt = dict(status='executed', mode='vu', runtime=dict(binary_sha256=BINARY_SHA),
                           job_sha256=hashlib.sha256(b'job').hexdigest(),
                           outputs={'gif-chunks.bin': dict(sha256='0'*64)})
            (run/'receipt.json').write_text(json.dumps(receipt))
            with self.assertRaisesRegex(ValueError, 'identity differs'):
                gif.native_transports(root)


if __name__ == '__main__':
    unittest.main()
