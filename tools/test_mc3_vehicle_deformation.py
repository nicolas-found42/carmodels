"""Offline source/receipt/job controls; original EE/VU execution is explicit."""
import copy
import json
from pathlib import Path
import struct
import unittest
from unittest.mock import patch

import mc3_vehicle_deformation as deformation


class DeformationTests(unittest.TestCase):
    def test_exact_bias_and_selector_contract(self):
        proof = deformation.source_contract()
        self.assertEqual(proof['source_operations']['bias_instruction']['lower_word'], 0x42FF0000)
        self.assertEqual(proof['source_operations']['bias'], 127.5)
        self.assertEqual(proof['source_operations']['selector_mask'], 15)
        self.assertEqual(len(proof['probes']), 7)

    def test_receipt_tamper_rejected(self):
        for change in ('bias', 'selector_mask', 'position_offset'):
            proof = copy.deepcopy(deformation.source_contract())
            proof['source_operations'][change] = 128
            with self.assertRaisesRegex(ValueError, 'receipt changed'):
                deformation.source_contract(receipt=proof)

    def test_w_preserved_and_protected_selector(self):
        proof = deformation.source_contract()
        baseline = proof['probes'][0]['output_words']
        for probe in proof['probes']:
            self.assertTrue(all(row[3] == 0xDEADBEEF for row in probe['output_words']))
            if probe['state_byte'] != 128:
                self.assertEqual(probe['output_words'][1], baseline[1])
                self.assertEqual(probe['output_words'][3], baseline[3])
        special = next(p for p in proof['probes'] if p['state_byte'] == 128)
        self.assertNotEqual(special['output_words'][1], baseline[1])
        self.assertNotEqual(special['output_words'][3], baseline[3])

    def test_unknown_state_rejected(self):
        with patch.object(deformation, 'source_contract', return_value=deformation.source_contract()):
            with self.assertRaisesRegex(ValueError, 'unmeasured morph state'):
                deformation.deformation_job(b'', 2)

    def test_zero_state_is_scaled_original(self):
        proof = deformation.source_contract()
        scale = proof['inputs']['position_scale']
        expected = [[struct.unpack('<I', struct.pack('<f', x*scale))[0] for x in row]
                    for row in proof['inputs']['positions']]
        self.assertEqual([row[:3] for row in proof['probes'][0]['output_words']], expected)

    def test_reference_does_not_embed_outputs_in_job(self):
        source = Path(deformation.__file__).read_text()
        body = source[source.index('def deformation_job'):source.index('def execute_reference')]
        self.assertNotIn("['output_words']", body)
        self.assertIn('palette_words', body)
        self.assertEqual(json.loads(deformation.EVIDENCE.read_text()), deformation.source_contract())


if __name__ == '__main__':
    unittest.main(verbosity=2)
