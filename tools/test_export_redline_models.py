"""Transactional conversion and repeat verification with tamper controls."""
import json
from pathlib import Path
import tempfile
import unittest
import struct
from unittest.mock import patch

from export_redline_models import export
from test_redline_model import source_fixture
from redline_model import sha


class ExportTests(unittest.TestCase):
    def test_non_drawable_configuration_retains_verified_native_identity(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source, output = root / 'native', root / 'output'
            source.mkdir()
            index, _ = source_fixture(source)
            config = b'carName "Invisible native configuration"\rmodel "empty.mdl"\rnumWheels 0\r'
            model = struct.pack('>6If', 0, 0, 0, 0, 0, 0, 0)
            (source / 'empty.car').write_bytes(config)
            (source / 'empty.mdl').write_bytes(model)
            index['cars'].append({'id': 'shared/base/empty.car', 'package': 'shared/base', 'file': 'empty.car',
                                  'bytes': len(config), 'sha256': sha(config), 'group': 'base'})
            index['packages'][0]['members'].append({'name': 'empty.mdl', 'file': 'empty.mdl', 'bytes': len(model), 'sha256': sha(model)})
            (source / 'index.json').write_text(json.dumps(index))
            result = export(source, output)
            self.assertEqual((result['configurations'], result['models'], result['non_drawable_configurations']), (2, 1, 1))
            row = json.loads((output / 'index.json').read_text())['non_drawable_configurations'][0]
            self.assertEqual(row['native_config_sha256'], sha(config))
            self.assertEqual(row['native_resources'][0]['sha256'], sha(model))
            self.assertEqual(export(source, output, True), result)

    def test_publication_failure_restores_entire_prior_directory(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source, output = root / 'native', root / 'output'
            source.mkdir()
            index, _ = source_fixture(source)
            (source / 'index.json').write_text(json.dumps(index))
            export(source, output)
            before = {p.relative_to(output).as_posix(): p.read_bytes() for p in output.rglob('*') if p.is_file()}
            original = Path.replace
            def fail_publication(path, destination):
                if path.name == 'next':
                    raise OSError('simulated directory publication failure')
                return original(path, destination)
            with patch.object(Path, 'replace', fail_publication):
                with self.assertRaisesRegex(OSError, 'simulated directory'):
                    export(source, output)
            self.assertEqual(before, {p.relative_to(output).as_posix(): p.read_bytes() for p in output.rglob('*') if p.is_file()})

    def test_repeat_and_tamper(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source, output = root / 'native', root / 'output'
            source.mkdir()
            index, _ = source_fixture(source)
            (source / 'index.json').write_text(json.dumps(index))
            result = export(source, output)
            self.assertEqual(result['models'], 1)
            self.assertEqual(export(source, output, True), result)
            model = next(output.rglob('*.glb'))
            original = model.read_bytes()
            model.write_bytes(original + b'bad')
            with self.assertRaisesRegex(ValueError, 'bytes differ'):
                export(source, output, True)
            model.write_bytes(original)
            (source / 'wheel.mdl').write_bytes(b'bad')
            with self.assertRaisesRegex(ValueError, 'extraction pin'):
                export(source, output)
            self.assertEqual(model.read_bytes(), original)

    def test_unrelated_outputs_and_overlap(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            index, _ = source_fixture(root)
            (root / 'index.json').write_text(json.dumps(index))
            with self.assertRaisesRegex(ValueError, 'overlaps'):
                export(root, root / 'output')
            # The output is owned by this fixture and removed by its own context.
            with tempfile.TemporaryDirectory() as destination:
                output = Path(destination)
                (output / 'unrelated.txt').write_text('preserve')
                with self.assertRaisesRegex(ValueError, 'unrelated'):
                    export(root, output)
                self.assertEqual((output / 'unrelated.txt').read_text(), 'preserve')


if __name__ == '__main__':
    unittest.main()
