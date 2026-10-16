import copy
import hashlib
import json
import struct
import unittest
from unittest.mock import patch

import mc3_vehicle_fragment as fragment


class VehicleFragmentTests(unittest.TestCase):
    def test_source_identity_refuses_changed_inputs(self):
        with self.assertRaisesRegex(ValueError, 'source differs'):
            fragment.verify_sources({fragment.SOURCES[0]['path']: b'changed source'})
        # A full-file digest is checked, not a substring or a source title.
        with patch.object(fragment, 'SOURCES', [dict(path='test', sha256=hashlib.sha256(b'original').hexdigest())]):
            self.assertEqual(fragment.verify_sources({'test': b'original'})['reference_commit'], fragment.COMMIT)
            with self.assertRaisesRegex(ValueError, 'source differs'):
                fragment.verify_sources({'test': b'original\0'})

    def test_original_reference_identity_and_cases(self):
        proof = json.loads(fragment.FIXTURE.read_text())
        self.assertEqual(proof['reference_commit'], fragment.COMMIT)
        self.assertEqual(proof['cases'], fragment.fragment_cases())
        self.assertEqual(proof['sources'], fragment.SOURCES)
        self.assertEqual(len(proof['cases']), 64)
        self.assertEqual(len(proof['final_frames']), 3)
        self.assertEqual({v['sha256'] for v in proof['final_frames']}, {proof['rgba_sha256']})
        self.assertEqual(proof['runtime']['runtime']['binary_sha256'],
                         '9b935133f224d29981200272492797eee4cb16fece3357119bf90c33cd62e48a')
        raw = b''.join(fragment.packets(proof['cases']))
        self.assertTrue(raw)
        self.assertEqual(len(raw) % 16, 0)
        self.assertEqual(fragment.verify_reference(proof, copy.deepcopy(proof))['status'], 'pass')
        changed = copy.deepcopy(proof)
        changed['case_rgba'][0][0] ^= 1
        with self.assertRaisesRegex(ValueError, 'case_rgba'):
            fragment.verify_reference(changed, proof)

    def test_expected_pixels_do_not_enter_reference_packets(self):
        cases = fragment.fragment_cases()
        expected = b''.join(fragment.packets(cases))
        # Extra model predictions are ignored; only explicit native inputs form
        # registers/vertices. Changing a real input must change the carrier.
        decorated = copy.deepcopy(cases)
        for row in decorated:
            row['expected_rgba'] = [255, 255, 255, 255]
        self.assertEqual(expected, b''.join(fragment.packets(decorated)))
        decorated[0]['vertex'][3] ^= 1
        self.assertNotEqual(hashlib.sha256(expected).digest(),
                            hashlib.sha256(b''.join(fragment.packets(decorated))).digest())

    def test_register_transport_preserves_alpha_masks_and_depth(self):
        state = fragment.base_state()
        state.update(ate=True, atst=6, aref=231, afail=3, date=True, datm=1,
                     fbmask=0xaabbccdd, zmsk=True, abe=True, pabe=True, fba=True,
                     blend=[0, 2, 1, 1, 255])
        registers = dict(fragment.registers(state, 2, True))
        self.assertEqual(registers[0x47], 1 | 6 << 1 | 231 << 4 | 3 << 12 | 3 << 14 | 5 << 16)
        self.assertEqual(registers[0x4c], 4 << 16 | 0xaabbccdd << 32)
        self.assertEqual(registers[0x4e], 128 | 10 << 24 | 1 << 32)
        self.assertEqual(registers[0x42], 0x58 | 255 << 32)
        packet = fragment.rectangle(2, 3, 4, 5, 65536, [1, 2, 3, 255])
        # AD packet entries store literal RGBAQ/XYZ2, not predicted colors.
        value, register = struct.unpack_from('<QQ', packet, 16)
        self.assertEqual((register, value), (1, 0x3f800000ff030201))


if __name__ == '__main__':
    unittest.main()
