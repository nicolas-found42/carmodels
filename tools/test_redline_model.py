"""Static assembly controls: source identity, wheel pose, UVs and texture provenance."""
import json
from pathlib import Path
import tempfile
import unittest

from bake_models import read_glb, accessor
from redline_model import NoDrawableGeometry, Resources, build_glb, export_primitive, fold, parse_config, sha
from redline_texture import encode_png
from test_redline_mesh import fixture


def source_fixture(root):
    assets = {'body.mdl': fixture(), 'wheel.mdl': fixture(),
              'paint.pct': encode_png(1, 1, b'\xff\x00\x00\xff'),
              'paint#4.pct': encode_png(1, 1, b'\x00\xff\x00\xff')}
    config = b'carName "Literal test"\rmodel "body.mdl"\rnumWheels 2\r# 0\rwheels.model "wheel.mdl"\rwheels.pos {-1,1,2}\rwheels.width 0.2\rwheels.radius 0.4\rwheels.texture 4\r# 1\rwheels.model "wheel.mdl"\rwheels.pos {1,1,2}\rwheels.width 0.2\rwheels.radius 0.4\r'
    rows = []
    for name, data in assets.items():
        (root / name).write_bytes(data)
        rows.append({'name': name, 'file': name, 'bytes': len(data), 'sha256': sha(data)})
    (root / 'test.car').write_bytes(config)
    car = {'id': 'shared/base/test.car', 'package': 'shared/base', 'file': 'test.car',
           'bytes': len(config), 'sha256': sha(config), 'group': 'base'}
    return {'game': 'redline', 'cars': [car], 'packages': [{'id': 'shared/base', 'members': rows}]}, car


class AssemblyTests(unittest.TestCase):
    def test_zero_normals_and_zero_area_controls(self):
        group = {'positions': [(0, 0, 0), (1, 0, 0), (0, 1, 0)],
                 'normals': [(0, 0, 0), (0, 0, 2), (0, 0, 0)], 'uvs': [(0, 0), (1, 0), (0, 1)]}
        result, derived, omitted = export_primitive(group)
        self.assertEqual((derived, omitted), (2, 0))
        self.assertEqual(result['normals'], [(0, 0, 1)] * 3)
        self.assertEqual(result['positions'], group['positions'])
        self.assertEqual(result['uvs'], group['uvs'])
        group['positions'] = [(0, 0, 0)] * 3
        result, derived, omitted = export_primitive(group)
        self.assertEqual((derived, omitted), (0, 1))
        self.assertFalse(result['indices'])

    def test_custom_brake_and_missing_mesh_notes(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            index, car = source_fixture(root)
            config = (root / 'test.car').read_bytes() + b'# 1\rwheels.customBrakeModel "body.mdl"\r'
            (root / 'test.car').write_bytes(config)
            car.update(bytes=len(config), sha256=sha(config))
            data, records, warnings, _ = build_glb(root, index, car, 'base/test')
            doc, _ = read_glb(data)
            self.assertFalse(warnings)
            self.assertEqual(records[-1]['role'], 'BRAKE_1')
            self.assertAlmostEqual(abs(doc['nodes'][-1]['rotation'][2]), 1)
            config += b'# 0\rwheels.model "absent.mdl"\r'
            (root / 'test.car').write_bytes(config)
            car.update(bytes=len(config), sha256=sha(config))
            data, _, warnings, _ = build_glb(root, index, car, 'base/test')
            doc, _ = read_glb(data)
            self.assertEqual(warnings[0]['resource'], 'absent.mdl')
            self.assertTrue(any('absent.mdl' in s for s in doc['extras']['claim_limits']))
            config += b'# 1\rwheels.width 0\rwheels.radius 0\r'
            (root / 'test.car').write_bytes(config)
            car.update(bytes=len(config), sha256=sha(config))
            _, records, warnings, _ = build_glb(root, index, car, 'base/test')
            self.assertFalse(any(r['role'] == 'WHEEL_1' for r in records))
            self.assertTrue(any(w['kind'] == 'collapsed-wheel' for w in warnings))

    def test_native_preview_suspension_clears_arch_pose(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            index, car = source_fixture(root)
            config = (root / 'test.car').read_bytes() + b'# 0\rwheels.maxSuspension 0.2\r# 1\rwheels.maxSuspension 0.3\rwheels.customBrakeModel "body.mdl"\r'
            (root / 'test.car').write_bytes(config)
            car.update(bytes=len(config), sha256=sha(config))
            data, _, _, _ = build_glb(root, index, car, 'base/test')
            doc, _ = read_glb(data)
            left, right, brake = doc['nodes'][1:]
            self.assertEqual(left['translation'], [-1, 0.9, 2])
            self.assertEqual(right['translation'], [1, 0.85, 2])
            self.assertEqual(brake['translation'], right['translation'])
            config += b'# 0\rwheels.maxSuspension -0.1\r'
            (root / 'test.car').write_bytes(config)
            car.update(bytes=len(config), sha256=sha(config))
            with self.assertRaisesRegex(ValueError, 'suspension travel'):
                build_glb(root, index, car, 'base/test')

    def test_native_empty_geometry_is_explicit(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            index, car = source_fixture(root)
            import struct
            empty = struct.pack('>6If', 0, 0, 0, 0, 0, 0, 0)
            for name in ('body.mdl', 'wheel.mdl'):
                (root / name).write_bytes(empty)
                row = next(r for r in index['packages'][0]['members'] if r['name'] == name)
                row.update(bytes=len(empty), sha256=sha(empty))
            with self.assertRaises(NoDrawableGeometry) as captured:
                build_glb(root, index, car, 'base/test')
            self.assertEqual(captured.exception.name, 'Literal test')
            self.assertEqual(len(captured.exception.resources), 2)

    def test_carriage_return_arrays_and_literal_name(self):
        fields, arrays = parse_config(b'carName "Name"\rnumWheels 3\r# 2\rwheels.pos {1,2,3}\r')
        self.assertEqual(fields['numWheels'], 3)
        self.assertEqual(arrays['wheels.pos'][2], [1, 2, 3])
        self.assertEqual(fold('A\xc4Z'), 'a\xc4z')
        for value in (b'numWheels 3.5', b'numWheels 1000', b'# 5000', b'wheels.pos {1,2}'):
            with self.assertRaises(ValueError):
                parse_config(value)

    def test_native_pose_selector_and_embedded_pixels(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            index, car = source_fixture(root)
            data, records, warnings, name = build_glb(root, index, car, 'base/test')
            doc, blob = read_glb(data)
            self.assertEqual(name, 'Literal test')
            self.assertFalse(warnings)
            self.assertEqual([r['role'] for r in records], ['BODY', 'WHEEL_0', 'WHEEL_1'])
            left, right = doc['nodes'][1:]
            self.assertEqual(left['scale'], [0.2, 0.4, 0.4])
            self.assertEqual(left['translation'], [-1, 1, 2])
            self.assertAlmostEqual(right['rotation'][1], 1)
            self.assertEqual(left['rotation'], [0, 0, 0, 1])
            uv = accessor(doc, blob, doc['meshes'][0]['primitives'][0]['attributes']['TEXCOORD_0'], 2, 5126)
            self.assertEqual(uv, [(0, 0), (1, 0), (0, 1)])
            self.assertEqual(len(doc['images']), 2)
            self.assertTrue(any(r['file'] == 'paint#4.pct' for r in doc['extras']['nativeResources']))

    def test_pinned_optional_and_texture_corruption_fail(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            index, car = source_fixture(root)
            (root / 'paint.pct').write_bytes(b'corruption')
            with self.assertRaisesRegex(ValueError, 'extraction pin'):
                build_glb(root, index, car, 'base/test')
            index, car = source_fixture(root)
            interior = fixture()
            (root / 'interior.mdl').write_bytes(interior)
            index['packages'][0]['members'].append({'name': 'interior.mdl', 'file': 'interior.mdl',
                                                    'bytes': len(interior), 'sha256': sha(interior)})
            config = (root / 'test.car').read_bytes() + b'interiorModel "interior.mdl"\r'
            (root / 'test.car').write_bytes(config)
            car.update(bytes=len(config), sha256=sha(config))
            (root / 'interior.mdl').write_bytes(b'corruption')
            with self.assertRaisesRegex(ValueError, 'extraction pin'):
                build_glb(root, index, car, 'base/test')

    def test_resource_scope_alias_and_path_controls(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            index, _ = source_fixture(root)
            resource = Resources(root, index, 'shared/base')
            self.assertEqual(resource.read('PAINT.PCT', True)[1], 'paint.pct')
            with self.assertRaisesRegex(ValueError, 'Invalid native resource'):
                resource.read('../paint.pct')
            row = index['packages'][0]['members'][0]
            row['file'] = '../escape'
            with self.assertRaisesRegex(ValueError, 'Unsafe'):
                resource.read(row['name'])
            json.dumps(index)


if __name__ == '__main__':
    unittest.main()
