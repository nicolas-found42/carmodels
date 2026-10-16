import struct
import unittest
from pathlib import Path
from unittest.mock import patch

import mc3_vehicle_transfer_reference as reference


class TransferReferenceTests(unittest.TestCase):
    def test_self_authored_control_inputs_reproduce_original_job(self):
        job = reference.synthetic_job()
        reference.validate_job(job)
        self.assertEqual(reference.sha(job), reference.contract()['synthetic_control']['job_sha256'])

    def test_malformed_transfers_cannot_enter_native_dispatch(self):
        job = reference.synthetic_job()
        for offset, value in ((0, 0), (33304, 3), (33304, 10485764), (32776, 1)):
            changed = bytearray(job)
            struct.pack_into('<I', changed, offset, value)
            with self.assertRaises(ValueError):
                reference.validate_job(changed)
        for changed in (job[:-1], job+b'extra'):
            with self.assertRaises(ValueError):
                reference.validate_job(changed)

    def test_changed_adapter_cannot_reuse_original_outputs(self):
        original = Path.read_bytes
        def changed(path):
            return b'changed transfer adapter' if path == reference.ADAPTER else original(path)
        with patch.object(Path, 'read_bytes', changed):
            with self.assertRaisesRegex(ValueError, 'adapter differs'):
                reference.contract()

    def test_wrong_game_executable_cannot_claim_source_inputs(self):
        with self.assertRaises(ValueError):
            reference.source_jobs(b'changed executable', {})


if __name__ == '__main__':
    unittest.main(verbosity=2)
