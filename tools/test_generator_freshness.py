"""Artifact corruption fails; changed dealership inputs produce a retrain warning."""
import contextlib
import hashlib
import io
import json
from pathlib import Path
import tempfile
import unittest

from generator_runtime import freshness


class Tests(unittest.TestCase):
    def test_reproduces_controls_and_warns_without_failing_on_changed_models(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder).resolve()
            assets = root / 'dealership/generator'
            assets.mkdir(parents=True)
            dealer = root / 'dealership/dealership'
            (dealer / 'models').mkdir(parents=True)
            model = dealer / 'models/REAL_A.glb'
            model.write_bytes(b'original model')
            (dealer / 'catalog.json').write_text('[{"code":"REAL_A"}]')
            (assets / 'manifest.json').write_text(json.dumps({'entries': [{'code': 'REAL_A',
                'glb_sha256': hashlib.sha256(model.read_bytes()).hexdigest()}], 'excluded': [], 'review': []}))
            for file in ['labels.json', 'basis.npz', 'network.pt', 'wheels.npz', 'calibration.json', 'template-labels.json']:
                (assets / file).write_bytes(file.encode())
            metadata = {pin: hashlib.sha256((assets / file).read_bytes()).hexdigest() for file, pin in [
                ('manifest.json', 'manifest_sha256'), ('labels.json', 'labels_sha256'),
                ('basis.npz', 'basis_sha256'), ('network.pt', 'network_sha256'), ('wheels.npz', 'wheels_sha256'),
                ('calibration.json', 'calibration_sha256'), ('template-labels.json', 'template_labels_sha256')]}
            (assets / 'training.json').write_text(json.dumps(metadata))
            freshness(root, write=True)
            receipt = root / 'research/evidence/car-generator/freshness.json'
            original = receipt.read_bytes()
            controls = json.loads(original)['controls']
            self.assertEqual(len(controls), 7)
            self.assertTrue(all(c['rejected'] and c['mutation'] in c['reason'] for c in controls))
            model.write_bytes(b'edited model')
            with contextlib.redirect_stdout(io.StringIO()) as stream:
                self.assertEqual(freshness(root), ['REAL_A'])
            self.assertIn('WARNING stale generator weights', stream.getvalue())
            self.assertIn('prepare --live then train', stream.getvalue())
            self.assertEqual(receipt.read_bytes(), original)
            (assets / 'basis.npz').write_bytes(b'corrupt basis')
            with self.assertRaisesRegex(ValueError, 'basis.npz'):
                freshness(root)


if __name__ == '__main__':
    unittest.main()
