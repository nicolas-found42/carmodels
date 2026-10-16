import copy
import hashlib
import struct
import unittest
from unittest.mock import patch

import mc3_panorama_angle as angle


def sparse_elf(proof):
    """Test-only ELF carrier of exact source intervals, never a game executable."""
    sources = proof['source_intervals']
    data = bytearray(52+32*len(sources))
    data[:7] = b'\x7fELF\x01\x01\x01'
    struct.pack_into('<I', data, 28, 52)
    struct.pack_into('<HH', data, 42, 32, len(sources))
    for i, source in enumerate(sources):
        raw = bytes.fromhex(source['hex'])
        assert hashlib.sha256(raw).hexdigest() == source['sha256']
        struct.pack_into('<8I', data, 52+i*32, 1, len(data), source['start'], source['start'], len(raw), len(raw), 5, 16)
        data.extend(raw)
    return bytes(data)


class PanoramaAngleTests(unittest.TestCase):
    def test_exact_original_jobs_and_unchanged_caller_intervals(self):
        proof = angle.source_contract()
        data = sparse_elf(proof)
        with patch.object(angle, 'EXECUTABLE_SHA', hashlib.sha256(data).hexdigest()):
            for row in proof['angles']:
                job = angle.angle_job(data, row['x_word'], row['z_word'])
                self.assertEqual(hashlib.sha256(job).hexdigest(), row['execution']['job_sha256'])
            for row in proof['callers']:
                job = angle.caller_job(data, row['x_word'], row['z_word'], row['width'])
                self.assertEqual(hashlib.sha256(job).hexdigest(), row['execution']['job_sha256'])
            self.assertEqual(len(proof['angles']), 12)
            self.assertEqual(len(proof['callers']), 16)
            changed = bytearray(data);changed[-1] ^= 1
            with patch.object(angle, 'EXECUTABLE_SHA', hashlib.sha256(changed).hexdigest()):
                with self.assertRaisesRegex(ValueError, 'interval changed'):
                    angle.source_contract(bytes(changed))

    def test_outputs_cannot_change_original_reference_inputs(self):
        proof = angle.source_contract()
        changed = copy.deepcopy(proof);changed['angles'][0]['angle_word'] ^= 1
        with self.assertRaisesRegex(ValueError, 'receipt changed'):
            angle.source_contract(receipt=changed)
        with self.assertRaisesRegex(ValueError, 'executable changed'):
            angle.source_contract(b'not original')
        data = sparse_elf(proof)
        with patch.object(angle, 'EXECUTABLE_SHA', hashlib.sha256(data).hexdigest()):
            for width in [0, 513, 2048, True]:
                with self.assertRaisesRegex(ValueError, 'width'):
                    angle.caller_job(data, 0, 0, width)
            with self.assertRaisesRegex(ValueError, 'axis word'):
                angle.angle_job(data, -1, 0)


if __name__ == '__main__':
    unittest.main(verbosity=2)
