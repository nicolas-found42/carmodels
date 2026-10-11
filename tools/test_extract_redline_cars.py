#!/usr/bin/env python3
"""Native extraction provenance, staging integrity, coverage and preservation."""
import copy
import hashlib
import json
from pathlib import Path
import struct
import tempfile
import unittest
from unittest.mock import patch

from extract_redline_cars import (advisory_inventory, assess_inventory, check_tree,
                                 config_fields, derive, encoded_path, reference_matches,
                                 write_tree)


def package(entries):
    count = len(entries)
    header = b'R3Dl1n3\0' + struct.pack('>I', count) + bytes(12)
    table, payload = bytearray(), bytearray()
    for name, data in entries:
        packed = b'\1\0\0\0' + data
        table.extend(struct.pack('>III', 24 + 268 * count + len(payload), len(data), len(packed)))
        table.extend(name.encode('mac_roman').ljust(256, b'\0'))
        payload.extend(packed)
    return header + table + payload


def fixture(root):
    staging = root / 'stage'
    (staging / 'extracted/cars').mkdir(parents=True)
    (staging / 'unpacked').mkdir()
    original = b'Outer envelope fixture'
    carrier = staging / 'extracted/cars/control.zip'
    carrier.write_bytes(original)
    plugin = staging / 'unpacked/control.redplug'
    plugin.write_bytes(package([('custom.car', b'carName "Custom"\rmodel "local.mdl"\rinteriorModel "BASE.MDL"\r'),
                                ('local.mdl', b'Native model fixture')]))
    base = root / 'data.redplug'
    base.write_bytes(package([('stock.car', b';carName "Ignored"\rcarName "Stock"\rmodel "base.mdl"\r'),
                              ('base.mdl', b'Base native model fixture'),
                              ('paint.pct.txr', b'Native texture fixture'),
                              ('Icon\r', b'')]))
    dmg, sit = root / 'source.dmg', root / 'source.sit'
    dmg.write_bytes(b'DMG identity fixture')
    sit.write_bytes(b'SIT identity fixture')
    pin = lambda b: hashlib.sha256(b).hexdigest()
    row = {'source_outer_member': 'cars/control.zip', 'source': 'extracted/cars/control.zip',
           'source_bytes': len(original), 'source_sha256': pin(original),
           'artifacts': [{'path': 'unpacked/control.redplug', 'bytes': plugin.stat().st_size,
                          'sha256': pin(plugin.read_bytes())}],
           'native_packages': [{'path': 'unpacked/control.redplug',
                                'sha256': pin(plugin.read_bytes()), 'config_members': ['custom.car']}]}
    manifest = root / 'stage.json'
    manifest.write_text(json.dumps({'source_sha256': pin(sit.read_bytes()),
                                    'car_source_members': 1, 'entries': [row]}))
    return base, manifest, staging, dmg, sit


class ExtractionTests(unittest.TestCase):
    def test_native_assets_provenance_and_determinism(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            args = fixture(root)
            before = {p: p.read_bytes() for p in root.rglob('*') if p.is_file()}
            tree, index = derive(*args)
            self.assertEqual(index['base_configurations'], 1)
            self.assertEqual(index['addon_configurations'], 1)
            self.assertEqual([c['declared_names'] for c in index['cars']], [['Stock'], ['Custom']])
            custom = index['cars'][1]
            refs = custom['resource_references']
            self.assertTrue(any(m['scope'] == 'local' for m in refs[0]['matches']))
            self.assertTrue(any(m['scope'] == 'base' for m in refs[1]['matches']))
            self.assertEqual(tree['shared/base/assets/Icon%0D'], b'')
            self.assertEqual(tree[index['preserved_car_envelopes'][0]['file']], b'Outer envelope fixture')
            self.assertEqual(tree['shared/base/data.redplug'], args[0].read_bytes())
            output = root / 'cars'
            output.mkdir()
            write_tree(tree, output)
            check_tree(tree, output)
            repeated, _ = derive(*args)
            self.assertEqual(tree, repeated)
            with self.assertRaisesRegex(ValueError, 'absent or an empty'):
                write_tree(tree, output)
            self.assertEqual(before, {p: p.read_bytes() for p in before})

    def test_changed_missing_extra_and_linked_output_rejected(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            tree, _ = derive(*fixture(root))
            output = root / 'cars'
            write_tree(tree, output)
            target = output / 'shared/base/assets/base.mdl'
            original = target.read_bytes()
            target.write_bytes(original[:-1] + b'!')
            with self.assertRaisesRegex(ValueError, 'byte mismatch'):
                check_tree(tree, output)
            target.unlink()
            with self.assertRaisesRegex(ValueError, 'coverage mismatch'):
                check_tree(tree, output)
            target.symlink_to(root / 'data.redplug')
            with self.assertRaisesRegex(ValueError, 'linked extraction'):
                check_tree(tree, output)
            target.unlink()
            target.write_bytes(original)
            (output / 'extra').write_bytes(b'extra')
            with self.assertRaisesRegex(ValueError, 'coverage mismatch'):
                check_tree(tree, output)

    def test_staging_hash_source_and_coverage_controls(self):
        cases = [('hash mismatch', lambda m: m['entries'][0]['artifacts'][0].update(sha256='0' * 64)),
                 ('unsafe relative', lambda m: m['entries'][0]['artifacts'][0].update(path='../escape')),
                 ('plugin coverage', lambda m: m['entries'][0].update(native_packages=[])),
                 ('duplicate native package', lambda m: m['entries'][0]['native_packages'].append(
                     copy.deepcopy(m['entries'][0]['native_packages'][0]))),
                 ('configuration coverage', lambda m: m['entries'][0]['native_packages'][0].update(config_members=[])),
                 ('envelope coverage', lambda m: m.update(entries=[], car_source_members=0)),
                 ('source hash mismatch', lambda m: m.update(source_sha256='0' * 64))]
        for reason, mutate in cases:
            with self.subTest(reason=reason), tempfile.TemporaryDirectory() as temp:
                args = fixture(Path(temp))
                manifest = json.loads(args[1].read_text())
                mutate(manifest)
                args[1].write_text(json.dumps(manifest))
                with self.assertRaisesRegex(ValueError, reason if manifest['entries'] else 'invalid addon'):
                    derive(*args)

    def test_loose_native_and_authoring_asset_kept(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            args = fixture(root)
            manifest = json.loads(args[1].read_text())
            row = manifest['entries'][0]
            native = args[2] / 'unpacked/loose.car'
            native.write_bytes(b'carName "Loose"\rmodel "base.mdl"\r')
            authoring = args[2] / 'unpacked/authoring.skp'
            authoring.write_bytes(b'SketchUp fixture')
            for path in [native, authoring]:
                row['artifacts'].append({'path': path.relative_to(args[2]).as_posix(),
                                         'bytes': path.stat().st_size,
                                         'sha256': hashlib.sha256(path.read_bytes()).hexdigest()})
            member = copy.deepcopy(row['artifacts'][1])
            row['native_packages'].append({'format': 'loose_native_resource_directory',
                                          'path': 'unpacked', 'config_members': ['loose.car'], 'members': [member]})
            args[1].write_text(json.dumps(manifest))
            tree, index = derive(*args)
            self.assertEqual(index['addon_configurations'], 2)
            self.assertTrue(any(data == b'SketchUp fixture' for data in tree.values()))
            duplicate = copy.deepcopy(row['native_packages'][-1])
            duplicate['path'] = 'unpacked/second'
            row['native_packages'].append(duplicate)
            args[1].write_text(json.dumps(manifest))
            with self.assertRaisesRegex(ValueError, 'duplicate loose car ownership'):
                derive(*args)
            row['native_packages'].pop()
            row['native_packages'].pop()
            args[1].write_text(json.dumps(manifest))
            with self.assertRaisesRegex(ValueError, 'loose car configuration coverage'):
                derive(*args)

    def test_literal_fields_alias_order_ascii_folding_and_unknown(self):
        mixed = config_fields(b';comment\r\ncarName "Car"\rmodel "body.mdl"\nengineSample "idle.wav"\r\n')
        self.assertEqual([f['line'] for f in mixed], [2, 3, 4])
        self.assertEqual(encoded_path('metadata/._Icon\r'), 'metadata/._Icon%0D')
        fields = config_fields(b';model "wrong.mdl"\rmodel "BODY.MDL" ;comment\rwheels.model "missing.mdl"\r')
        self.assertEqual([f['value'] for f in fields], ['BODY.MDL', 'missing.mdl'])
        local = [{'name': 'body.mdl', 'file': 'exact', 'sha256': 'a'},
                 {'name': 'body.mdl.ima', 'file': 'ima', 'sha256': 'b'},
                 {'name': 'body.mdl.txr', 'file': 'txr', 'sha256': 'c'}]
        result = reference_matches(fields, local, [])
        self.assertEqual([m['file'] for m in result[0]['matches']], ['txr', 'ima', 'exact'])
        self.assertEqual(result[1]['matches'], [])
        self.assertEqual(encoded_path('Icon\r'), 'Icon%0D')
        self.assertEqual(encoded_path('Icon%0D'), 'Icon%250D')
        with self.assertRaisesRegex(ValueError, 'unsafe relative'):
            encoded_path('a/../bad')

    def test_advisory_sampling_screening_and_preservation(self):
        with tempfile.TemporaryDirectory() as temp:
            tree, index = derive(*fixture(Path(temp)))
            before = copy.deepcopy(tree)
            inventory = advisory_inventory(tree, index)
            self.assertEqual(len(inventory), 2)
            self.assertEqual({r['path'].split('/')[0] for r in inventory}, {'base', 'addon'})
            for action in ('review', 'block', 'skip'):
                screen = {'recommendation': {'action': action}}
                with patch('jev_mcp_call.call', return_value=screen), patch('gt_asset_judgments.live_receipt') as live:
                    self.assertEqual(assess_inventory(inventory)['status'], 'review')
                    live.assert_not_called()
            with patch('jev_mcp_call.call', return_value={'recommendation': {'action': 'pass'}}), \
                    patch('gt_asset_judgments.live_receipt', return_value={'status': 'ok', 'results': []}):
                self.assertEqual(assess_inventory(inventory)['status'], 'ok')
            self.assertEqual(tree, before)


if __name__ == '__main__':
    unittest.main()
