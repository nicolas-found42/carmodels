#!/usr/bin/env python3
"""Independent source-scene/triangle checks and corruption controls for all 35 bakes."""
import base64
import copy
import hashlib
import json
from pathlib import Path
import struct
import unittest

from bake_models import bake_car, texture_tone, load_source_model

ROOT = Path(__file__).resolve().parents[1]


def source_scene(code):
    data = (ROOT / f'dealership/public/ford-racing-2/{code}.glb').read_bytes()
    size = struct.unpack_from('<I', data, 12)[0]
    doc = json.loads(data[20:20 + size])
    binary = data[28 + size:]

    def array(index, width, fmt):
        a = doc['accessors'][index]
        v = doc['bufferViews'][a['bufferView']]
        start = v.get('byteOffset', 0) + a.get('byteOffset', 0)
        stride = v.get('byteStride', width * 4)
        return [struct.unpack_from('<' + fmt * width, binary, start + i * stride) for i in range(a['count'])]

    triangles = {'body': [], 'wheel': [], 'detail': []}
    normals = {'body': [], 'wheel': [], 'detail': []}
    hubs, nodes = [], []

    def visit(index, parent=(0, 0, 0), wheel=False):
        node = doc['nodes'][index]
        names = node.get('extras', {}).get('sourceNames', [])
        if 'HELMET' in names:
            return
        location = tuple(a + b for a, b in zip(parent, node.get('translation', (0, 0, 0))))
        wheel = wheel or any(n.startswith(('WHEEL_', 'HUB_')) for n in names)
        if any(n.startswith('HUB_') for n in names):
            hubs.append((location[2], location[1], -location[0]))
        if 'mesh' in node:
            nodes.append(index)
            for primitive in doc['meshes'][node['mesh']]['primitives']:
                material = doc['materials'][primitive['material']]
                if material['name'] == 'UNDER_SHADOW':
                    continue
                kind = 'wheel' if wheel else 'body' if 'baseColorTexture' in material.get('pbrMetallicRoughness', {}) else 'detail'
                xyz = array(primitive['attributes']['POSITION'], 3, 'f')
                normal = array(primitive['attributes']['NORMAL'], 3, 'f')
                indices = array(primitive['indices'], 1, 'I')
                for (i,) in indices:
                    x, y, z = (v + t for v, t in zip(xyz[i], location))
                    triangles[kind].append((z, y, -x))
                    nx, ny, nz = normal[i]
                    normals[kind].append((nz, ny, -nx))
        for child in node.get('children', []):
            visit(child, location, wheel)

    scene = doc['scenes'][doc['scene']]
    assert scene['extras']['visibilityPreset'] == 'low_speed'
    for index in scene['nodes']:
        visit(index)
    points = [v for rows in triangles.values() for v in rows]
    low = [min(v[i] for v in points) for i in range(3)]
    high = [max(v[i] for v in points) for i in range(3)]
    origin = [(low[0] + high[0]) / 2, low[1], (low[2] + high[2]) / 2]
    return {'triangles': triangles, 'normals': normals, 'hubs': hubs, 'origin': origin,
            'dimensions': [b - a for a, b in zip(low, high)], 'nodes': nodes, 'sha': hashlib.sha256(data).hexdigest()}, doc, binary


def check_bake(code, model):
    expected, _, _ = source_scene(code)
    if model['source']['sha256'] != expected['sha']:
        raise AssertionError('source pin differs')
    if [n['node'] for n in model['source']['nodes']] != expected['nodes']:
        raise AssertionError('visible source nodes differ')
    if len(model['wheelHubs']) != 4:
        raise AssertionError('source wheel hub count differs')
    for actual, source in zip(model['wheelHubs'], expected['hubs']):
        if any(abs(a - (v - o)) > 1e-6 for a, v, o in zip(actual['position'], source, expected['origin'])):
            raise AssertionError('source wheel placement differs')
    triangle_count = 0
    for part in model['parts']:
        vertices = list(struct.iter_unpack('<6fB', base64.b64decode(part['vertices'], validate=True)))
        indices = [v[0] for v in struct.iter_unpack('<H', base64.b64decode(part['indices'], validate=True))]
        triangle_count += len(indices) // 3
        rows = expected['triangles'][part['kind']]
        if len(rows) != len(indices):
            raise AssertionError('source triangle count differs')
        for j, i in enumerate(indices):
            actual = vertices[i]
            if any(abs(a - (v - o)) > 1e-6 for a, v, o in zip(actual[:3], rows[j], expected['origin'])):
                raise AssertionError('source triangle coordinates differ')
            if any(abs(a - n) > 1e-6 for a, n in zip(actual[3:6], expected['normals'][part['kind']][j])):
                raise AssertionError('source triangle normals differ')
    if triangle_count != model['triangleCount']:
        raise AssertionError('declared triangle count differs')
    dimensions = [b - a for a, b in zip(model['bounds'][:3], model['bounds'][3:])]
    if any(abs(a - b) > 1e-6 for a, b in zip(dimensions, expected['dimensions'])):
        raise AssertionError('source bounds differ')


class ModelBakeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.cars = [{'code':p.stem,'model':load_source_model(p.stem)} for p in sorted((ROOT / 'dealership/public/ford-racing-2').glob('*.glb'))]

    def test_all_source_triangles_transforms_normals_and_hubs(self):
        self.assertEqual(len(self.cars), 35)
        for car in self.cars:
            with self.subTest(car=car['code']):
                check_bake(car['code'], car['model'])

    def test_in_bounds_position_and_in_range_index_controls(self):
        code, source = self.cars[0]['code'], self.cars[0]['model']
        changed = copy.deepcopy(source)
        raw = bytearray(base64.b64decode(changed['parts'][0]['vertices']))
        x = struct.unpack_from('<f', raw)[0]
        struct.pack_into('<f', raw, 0, x + 0.01)
        changed['parts'][0]['vertices'] = base64.b64encode(raw).decode()
        with self.assertRaisesRegex(AssertionError, 'source triangle coordinates differ'):
            check_bake(code, changed)
        changed = copy.deepcopy(source)
        raw = bytearray(base64.b64decode(changed['parts'][0]['indices']))
        i = struct.unpack_from('<H', raw)[0]
        struct.pack_into('<H', raw, 0, (i + 1) % changed['parts'][0]['vertexCount'])
        changed['parts'][0]['indices'] = base64.b64encode(raw).decode()
        with self.assertRaisesRegex(AssertionError, 'source triangle coordinates differ'):
            check_bake(code, changed)

    def test_pin_identity_and_wrong_scene_controls(self):
        code = self.cars[0]['code']
        data = (ROOT / f'dealership/public/ford-racing-2/{code}.glb').read_bytes()
        pin = hashlib.sha256(data).hexdigest()
        with self.assertRaisesRegex(ValueError, 'differs from manifest pin'):
            bake_car(code, data[:-1], pin)
        with self.assertRaisesRegex(ValueError, 'car identity differs'):
            bake_car('OTHER', data, pin)
        _, doc, binary = source_scene(code)
        doc['scene'] = 1  # All alternative wheel/light states: must not become a model.
        encoded = json.dumps(doc).encode()
        encoded += b' ' * (-len(encoded) % 4)
        mutated = struct.pack('<3I', 0x46546C67, 2, 28 + len(encoded) + len(binary))
        mutated += struct.pack('<2I', len(encoded), 0x4E4F534A) + encoded
        mutated += struct.pack('<2I', len(binary), 0x004E4942) + binary
        with self.assertRaisesRegex(ValueError, 'first-tree low-speed model scene'):
            bake_car(code, mutated, hashlib.sha256(mutated).hexdigest())

    def test_tone_is_illustrative_and_bounded(self):
        self.assertLess(texture_tone((0, 0, 0)), texture_tone((220, 220, 220)))
        self.assertEqual(texture_tone((255, 0, 0)), texture_tone((0, 255, 0)))
        self.assertNotEqual(texture_tone((255, 0, 0), wheel=True), texture_tone((0, 255, 0), wheel=True))


if __name__ == '__main__':
    unittest.main()
