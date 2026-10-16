"""Native initialization identity, original EE job and payload controls."""
import base64
import hashlib
import json
import unittest

from mc3_vehicle_initialization import DMA, FIXTURE, INTERVALS, build_pack, initialization_job


class InitializationTests(unittest.TestCase):
    def test_original_job_and_carriers(self):
        proof = json.loads(FIXTURE.read_text())
        pack = proof['pack']
        self.assertEqual(pack['special_dma_hex'], DMA.hex())
        self.assertEqual(pack['source_intervals'],
                         [dict(address=a, bytes=n, sha256=h) for a, n, h in INTERVALS])
        self.assertEqual(hashlib.sha256(initialization_job()).hexdigest(), proof['ee']['job_sha256'])
        raw = base64.b64decode(pack['vif_base64'], validate=True)
        self.assertEqual(len(raw), pack['vif_bytes'])
        self.assertEqual(hashlib.sha256(raw).hexdigest(), pack['vif_sha256'])
        self.assertEqual(raw[:8], DMA[8:16])
        self.assertEqual(raw[8104:8112], DMA[24:32])
        self.assertEqual(proof['coupled']['gif_bytes'], 0)

    def test_wrong_executable_rejected(self):
        with self.assertRaisesRegex(ValueError, 'executable differs'):
            build_pack(bytes(128))


if __name__ == '__main__':
    unittest.main(verbosity=2)
