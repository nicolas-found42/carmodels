"""Source/component identity and targeted refusal tests."""
import copy
import unittest

from mc3_vehicle_paint_components import (browser_source_pack, from_executable, selected_case,
                                          source_contract, verify_reference_output)


class PaintComponentTests(unittest.TestCase):
    def test_pinned_receipt_and_source_refusals(self):
        proof = source_contract()
        for mutate in (lambda p: p['intervals'][0].update(start=0),
                       lambda p: p['cases'][0].update(output_sha256='0'*64),
                       lambda p: p['cases'][1]['patches'][0].update(data_hex='00')):
            changed = copy.deepcopy(proof)
            mutate(changed)
            with self.assertRaisesRegex(ValueError, 'receipt changed'):
                source_contract(changed)
        for function in (from_executable, lambda e: browser_source_pack(e, 'radial64')):
            with self.assertRaisesRegex(ValueError, 'executable changed'):
                function(b'not the original MC3 executable')

    def test_case_and_ram_refusals(self):
        proof = source_contract()
        with self.assertRaisesRegex(ValueError, 'unknown native paint component'):
            selected_case(proof, 'invented preset')
        with self.assertRaisesRegex(ValueError, 'RAM extent changed'):
            verify_reference_output(b'not RAM', 'radial64')
        with self.assertRaisesRegex(ValueError, 'full RAM differs'):
            verify_reference_output(bytes(0x2000000), 'palette0')

    def test_exact_native_scope_and_output_layout(self):
        proof = source_contract()
        self.assertEqual([c['name'] for c in proof['cases']], ['radial64']+[f'palette{i}' for i in range(6)])
        self.assertEqual(proof['image']['width'], 64)
        self.assertEqual(proof['image']['height'], 64)
        self.assertEqual(proof['cases'][0]['output_bytes'], 4096)
        self.assertTrue(all(c['output_bytes'] == 1024 for c in proof['cases'][1:]))
        self.assertTrue(any('not an active actor' in text for text in proof['claim_limits']))


if __name__ == '__main__':
    unittest.main(verbosity=2)
