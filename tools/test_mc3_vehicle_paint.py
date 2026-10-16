"""Bounded original paint control source/output refusal tests."""
import copy
import unittest

from mc3_vehicle_paint import browser_source_pack, control_context, from_executable, source_contract, verify_reference_output


class VehiclePaintTests(unittest.TestCase):
    def test_receipt_mutations_are_refused(self):
        proof = source_contract()
        for field in ('reference_job_sha256', 'reference_final_ram_sha256', 'reference_dma_sha256'):
            changed = copy.deepcopy(proof)
            changed[field] = '0'*64
            with self.subTest(field=field), self.assertRaisesRegex(ValueError, 'receipt changed'):
                source_contract(changed)
        changed = copy.deepcopy(proof)
        changed['intervals'][0]['start'] += 4
        with self.assertRaisesRegex(ValueError, 'receipt changed'):
            source_contract(changed)

    def test_wrong_executable_is_refused_before_parsing(self):
        for function in (from_executable, browser_source_pack):
            with self.subTest(function=function), self.assertRaisesRegex(ValueError, 'executable changed'):
                function(b'not the original executable')

    def test_invalid_or_changed_ram_is_refused(self):
        with self.assertRaisesRegex(ValueError, 'extent changed'):
            verify_reference_output(b'not RAM')
        with self.assertRaisesRegex(ValueError, 'final RAM differs'):
            verify_reference_output(bytes(0x2000000))

    def test_controls_do_not_mutate_shared_proof_or_invent_unknown_context(self):
        proof = source_contract()
        original = copy.deepcopy(proof)
        context, selected = control_context(proof, 'positive')
        self.assertEqual(proof, original)
        self.assertNotEqual(context['patches'], proof['reference_context']['patches'])
        self.assertEqual(selected['reference_browser_instructions'], 12012)
        with self.assertRaisesRegex(ValueError, 'unknown bounded paint control'):
            control_context(proof, 'unknown')

    def test_scope_stays_bounded(self):
        proof = source_contract()
        self.assertEqual(proof['reference_context']['entry'], 0x2ce880)
        self.assertEqual(len(proof['intervals']), 141)
        self.assertTrue(any('not a positive highlight' in value for value in proof['claim_limits']))
        self.assertTrue(any('not an original active garage' in value for value in proof['claim_limits']))


if __name__ == '__main__':
    unittest.main(verbosity=2)
