"""Exercise preview topology with source-independent geometry and malformed inputs."""
import copy
import math
import unittest
from mc3_model import strip_triangles, build_glb, wheel_slots, native_rest_frames, rotated_point
from bake_models import read_glb


class PreviewGeometryTest(unittest.TestCase):
    def test_native_xyz_order_parent_rotation_and_invalid_frames(self):
        bones = [{'parent': None, 'local_position': [10, 0, 0], 'rotation_raw': [0, 0, math.pi/2]},
                 {'parent': 0, 'local_position': [1, 0, 0], 'rotation_raw': [math.pi/2, math.pi/2, 0]}]
        frames = native_rest_frames(bones)
        for actual, expected in zip(frames[1]['translation'], [10, 1, 0]):
            self.assertAlmostEqual(actual, expected)
        # Local Ry*Rx maps X to -Z and Y to +X; parent Rz maps that +X to +Y.
        for point, expected in [([1, 0, 0], [0, 0, -1]), ([0, 1, 0], [0, 1, 0]), ([0, 0, 1], [1, 0, 0])]:
            for actual, wanted in zip(rotated_point(frames[1]['rotation'], point), expected):
                self.assertAlmostEqual(actual, wanted)
        changed = copy.deepcopy(bones);changed[0]['parent'] = 1
        with self.assertRaisesRegex(ValueError, 'cyclic'):
            native_rest_frames(changed)
        changed = copy.deepcopy(bones);changed[1]['parent'] = 4
        with self.assertRaisesRegex(ValueError, 'outside skeleton'):
            native_rest_frames(changed)
        changed = copy.deepcopy(bones);changed[0]['rotation_raw'][0] = math.nan
        with self.assertRaisesRegex(ValueError, 'nonfinite'):
            native_rest_frames(changed)

    def test_wheel_set_and_inherited_rotation_controls(self):
        root = {'index': 0, 'name': 'root', 'parent': None, 'rotation_raw': [0, 0, 0], 'global_position': [0, 0, 0]}
        bones = [root, *[{'index': i+1, 'name': 'whl_'+str(i), 'parent': 0,
                         'rotation_raw': [0, 0, 0], 'global_position': [-1 if i%2 == 0 else 1, 1, -1 if i < 2 else 1]}
                        for i in range(4)]]
        self.assertEqual([s['axle'] for s in wheel_slots(bones)], [0, 0, 1, 1])
        changed = copy.deepcopy(bones);changed[0]['rotation_raw'][1] = 0.2
        with self.assertRaisesRegex(ValueError, 'ancestor rotation'):
            wheel_slots(changed)
        changed = [bones[0], bones[1], {**bones[3], 'index': 2}]
        with self.assertRaisesRegex(ValueError, 'two-wheel aliases'):
            wheel_slots(changed)
        changed = copy.deepcopy(bones);changed[2]['name'] = 'whl_0'
        with self.assertRaisesRegex(ValueError, 'four-wheel aliases'):
            wheel_slots(changed)

    def test_strip_winding_and_degenerate_restart(self):
        points = [(0, 0, 0), (1, 0, 0), (0, 1, 0), (1, 1, 0)]
        self.assertEqual(strip_triangles(points), [0, 1, 2, 2, 1, 3])
        self.assertEqual(strip_triangles([points[0]] * 4), [])

    def test_empty_geometry_rejected(self):
        with self.assertRaisesRegex(ValueError, 'drawable'):
            build_glb('vp_test', [], [], [])

    def test_source_identity_retained(self):
        batch = {'positions': [(0, 0, 0), (1, 0, 0), (0, 1, 0)], 'packet_offset': 128}
        parts = [{'name': 'native.mesh', 'bone': 0, 'mesh': {'source': {'sha256': 'a' * 64},
                  'draws': [{'material': 0, 'batches': [batch]}]}}]
        data, records = build_glb('vp_test', parts, [{'shader_category': 'unmapped', 'base_color': [.65]*3+[1],
                                                   'alpha_mode': 'OPAQUE'}], [])
        doc, _ = read_glb(data)
        self.assertEqual(doc['extras']['car'], 'vp_test')
        self.assertEqual(records[0]['native_sha256'], 'a' * 64)
        self.assertEqual(records[0]['triangles'], 1)


if __name__ == '__main__':
    unittest.main()
