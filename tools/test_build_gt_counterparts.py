"""Source-preservation, identity and corruption controls for GT4-guided studies."""
import copy
import json
from pathlib import Path
import tempfile
import unittest

from bake_models import read_glb
import build_gt_counterparts as subject

LEDGER = 'dealership/public/gt4-guided/ledger.json'
RECEIPT = 'dealership/public/gt4-guided/receipt.json'
STUDY = 'dealership/public/gt4-guided/comparison.json'
PILOT = f'dealership/public/gt4-guided/{subject.PILOT}'
MEASURED = subject.COMPARISON


class CounterpartTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.gt1 = subject.rows(json.loads((subject.PUBLIC / 'gran-turismo/index.json').read_bytes()))
        cls.gt4 = subject.rows(json.loads((subject.PUBLIC / 'gran-turismo-4/index.json').read_bytes()))
        cls.target = cls.gt1[subject.TARGET]
        cls.donor = cls.gt4[subject.DONOR]
        cls.target_data = subject.pinned_glb(subject.PUBLIC, cls.target, 'gran-turismo')
        cls.donor_data = subject.pinned_glb(subject.PUBLIC, cls.donor, 'gran-turismo-4')
        cls.outputs = subject.products()

    def test_all_targets_accounted_for_without_approvals(self):
        ledger = json.loads(self.outputs[LEDGER])
        self.assertEqual({e['target']['code'] for e in ledger['entries']}, set(self.gt1))
        self.assertEqual(len(ledger['entries']), 342)
        self.assertEqual(sum(ledger['counts'].values()), 342)
        for entry in ledger['entries']:
            self.assertEqual(entry['approvedRegions'], [])
            if entry['identityStatus'] != 'verified':
                self.assertEqual(entry['candidates'], [])
                self.assertEqual(entry['status'], 'unresolved-identity')
            for candidate in entry['candidates']:
                self.assertEqual(candidate['status'], 'unreviewed')
                self.assertEqual(candidate['approvedRegions'], [])
                self.assertEqual(candidate['sha256'], self.gt4[candidate['code']]['sha256'])

    def test_rb_does_not_acquire_an_exact_counterpart(self):
        ledger = json.loads(self.outputs[LEDGER])
        entry = next(e for e in ledger['entries'] if e['target']['code'] == 'simulation/_afb7n')
        self.assertTrue(entry['candidates'])
        self.assertTrue(all(c['status'] == 'unreviewed' for c in entry['candidates']))
        self.assertFalse(any('Type-RB' in c['name'] for c in entry['candidates']))
        self.assertEqual(entry['approvedRegions'], [])

    def test_gt4_document_and_entire_binary_preserved(self):
        before, original_binary = read_glb(self.donor_data)
        after, binary = read_glb(self.outputs[PILOT])
        report = after['extras'].pop('gt4GuidedStudy')
        self.assertEqual(after, before)
        self.assertEqual(binary, original_binary)
        self.assertEqual(report['approvedGt1TransferRegions'], [])
        self.assertEqual(report['target']['code'], subject.TARGET)
        self.assertEqual(report['donor']['code'], subject.DONOR)
        # Tests source buffers and every UV/material/paint variant, not only visible mesh totals.
        self.assertEqual(subject.pinned_glb(subject.PUBLIC, self.target, 'gran-turismo'), self.target_data)
        self.assertEqual(subject.pinned_glb(subject.PUBLIC, self.donor, 'gran-turismo-4'), self.donor_data)

    def test_pilot_counts_and_attribution_are_derived(self):
        receipt = json.loads(self.outputs[RECEIPT])
        self.assertEqual((receipt['targetTriangles'], receipt['studyTriangles']), (530, 7830))
        self.assertEqual(receipt['studySha256'], subject.digest(self.outputs[PILOT]))
        pair = json.loads(self.outputs[STUDY])['pairs'][0]
        self.assertEqual(pair['right']['sha256'], receipt['studySha256'])
        self.assertEqual(pair['left'][0]['sha256'], subject.digest(self.target_data))
        self.assertIn('unresolved', pair['match'])

    def test_wrong_trim_and_changed_name_rejected(self):
        for target, donor in [(self.gt1['simulation/_afb7n'], self.donor),
                              (self.target, {**self.donor, 'display_name': 'RX-7 Spirit R'})]:
            with self.assertRaisesRegex(ValueError, 'identity changed'):
                subject.pilot(target, donor, self.target_data, self.donor_data)

    def test_rehashed_wrong_count_rejected(self):
        changed = copy.deepcopy(self.target)
        changed['records'][0]['triangles'] += 1
        with self.assertRaisesRegex(ValueError, 'triangle count differs'):
            subject.pilot(changed, self.donor, self.target_data, self.donor_data)

    def test_source_corruption_and_escape_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            public = Path(directory)
            game = public / 'gran-turismo'
            (game / 'simulation').mkdir(parents=True)
            (game / self.target['file']).write_bytes(self.target_data[:-1] + b'!')
            with self.assertRaisesRegex(ValueError, 'hash mismatch'):
                subject.pinned_glb(public, self.target, 'gran-turismo')
            with self.assertRaisesRegex(ValueError, 'escapes'):
                subject.pinned_glb(public, {**self.target, 'file': '../outside.glb'}, 'gran-turismo')

    def test_duplicate_id_rejected(self):
        with self.assertRaisesRegex(ValueError, 'Duplicate source code'):
            subject.rows({'cars': [self.target, self.target]})

    def test_every_committed_artifact_is_current(self):
        stale = subject.stale_artifacts(self.outputs)
        self.assertEqual(stale, [], f'committed artifacts differ from the derivation: {stale}')

    def test_changed_measurement_is_rejected(self):
        # A committed measurement that no longer follows from the pinned sources must be
        # reported stale, so the comparison page cannot silently display drifted numbers.
        measured = json.loads(self.outputs[MEASURED])
        self.assertEqual(len(measured['pairs']), 7)
        self.assertEqual(len(measured['pairs'][-1]['left']), 4)
        self.assertEqual(measured['pairs'][-1]['left'][0]['code'], subject.REFINEMENT_SOURCE)
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            path = root / MEASURED
            path.parent.mkdir(parents=True)
            path.write_bytes(self.outputs[MEASURED])
            self.assertNotIn(MEASURED, subject.stale_artifacts(self.outputs, root))
            measured['pairs'][0]['right']['triangles'] += 1
            path.write_bytes(subject.json_bytes(measured))
            self.assertIn(MEASURED, subject.stale_artifacts(self.outputs, root))

    def test_missing_artifact_is_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            self.assertIn(MEASURED, subject.stale_artifacts(self.outputs, Path(directory)))


if __name__ == '__main__':
    unittest.main(verbosity=2)
