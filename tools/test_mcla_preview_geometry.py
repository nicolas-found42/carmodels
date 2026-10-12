"""Bounded preview cleanup invariants, source qualification and tamper controls."""
import copy
import hashlib
import math
from pathlib import Path
import unittest
from unittest.mock import patch

import mcla_preview_geometry as repair

ROOT = Path(__file__).resolve().parents[1]


def fixture():
    """Ten disconnected canted divider quads and a separate shell triangle."""
    positions, normals, indices = [], [], []
    for blade in range(10):
        side = 1 if blade < 5 else -1
        base = len(positions)
        for y, z in [(0, -.05), (1, .45), (1, .55), (0, .05)]:
            positions.append((side*(1+blade*.1), y, z))
            normals.append((side, 0., 0.))
        order = [0, 1, 2, 0, 2, 3] if side > 0 else [0, 2, 1, 0, 3, 2]
        indices.extend(base+i for i in order)
    base = len(positions)
    positions.extend([(0., 0., 0.), (.2, 0., 0.), (0., .2, 0.)])
    normals.extend([(0., 0., 1.)]*3)
    indices.extend([base, base+1, base+2])
    return {'position': positions, 'normal': normals, 'indices': indices,
            'vertex_count': len(positions), 'index_count': len(indices),
            'texcoord0': [(0., 0.)]*len(positions), 'colour0': [(1, 2, 3, 4)]*len(positions),
            'tangent': [(1., 0., 0., 1.)]*len(positions), 'shader': 26}


class PreviewGeometryTests(unittest.TestCase):
    def setUp(self):
        self.geometry = fixture()
        self.pin = repair.geometry_digest(self.geometry)
        self.pins = patch.multiple(repair, GEOMETRY_SHA256=self.pin,
                                   FIN_RANGES=tuple(((i*2, i*2+2),) for i in range(10)))
        self.pins.start()
        self.addCleanup(self.pins.stop)

    def derive(self, geometry=None):
        return repair.cleanup_preview_geometry(self.geometry if geometry is None else geometry,
                                               repair.TARGET_FILE, repair.TARGET_SHA256, 1)

    def test_unrelated_source_model_and_primitive_keep_identity(self):
        for file, model, primitive in [('other.xrsc', 0, 1), (repair.TARGET_FILE, 1, 1),
                                       (repair.TARGET_FILE, 0, 0)]:
            with self.subTest(file=file, model=model, primitive=primitive):
                result, receipt = repair.cleanup_preview_geometry(self.geometry, file, None,
                                                                   primitive, model_index=model)
                self.assertIs(result, self.geometry)
                self.assertIsNone(receipt)

    def test_target_requires_exact_source_pin(self):
        for pin in [None, '', '0'*64, repair.TARGET_SHA256.upper()]:
            with self.subTest(pin=pin):
                with self.assertRaisesRegex(ValueError, 'source hash'):
                    repair.cleanup_preview_geometry(self.geometry, repair.TARGET_FILE, pin, 1)

    def test_every_decoded_field_is_bound_to_geometry_pin(self):
        for field in self.geometry:
            with self.subTest(field=field):
                changed = copy.deepcopy(self.geometry)
                if isinstance(changed[field], list):
                    changed[field] = changed[field][1:]
                else:
                    changed[field] += 1
                with self.assertRaisesRegex(ValueError, 'decoded preview geometry differs'):
                    self.derive(changed)
        changed = copy.deepcopy(self.geometry)
        changed['unexpected'] = 'new'
        with self.assertRaisesRegex(ValueError, 'decoded preview geometry differs'):
            self.derive(changed)

    def test_native_input_and_all_unaffected_attributes_stay_exact(self):
        original = copy.deepcopy(self.geometry)
        result, receipt = self.derive()
        self.assertEqual(self.geometry, original)
        self.assertEqual(result['position'][40:], original['position'][40:])
        self.assertEqual(result['normal'][40:], original['normal'][40:])
        for key in original:
            if key not in ('position', 'normal'):
                self.assertEqual(result[key], original[key])
        self.assertEqual(receipt['changed_vertices'], 40)
        self.assertEqual(receipt['changed_triangles'], 20)
        self.assertEqual(receipt['input_vertex_count'], receipt['output_vertex_count'])
        self.assertEqual(receipt['input_index_count'], receipt['output_index_count'])
        self.assertEqual(receipt['new_vertices'], 0)
        self.assertEqual(receipt['removed_triangles'], 0)

    def test_centerline_height_winding_and_normal_plane_are_preserved(self):
        result, receipt = self.derive()
        for blade in range(10):
            ids = range(blade*4, blade*4+4)
            old = [self.geometry['position'][i] for i in ids]
            new = [result['position'][i] for i in ids]
            self.assertEqual([p[1] for p in old], [p[1] for p in new])
            side = 1 if blade < 5 else -1
            for a, b in zip(old, new):
                self.assertAlmostEqual(b[0], a[0]-side*.01)
            self.assertAlmostEqual(new[3][2]-new[0][2], .01)
            self.assertAlmostEqual((new[3][2]+new[0][2])/2, 0.)
            self.assertAlmostEqual((new[2][2]+new[1][2])/2, .5)
            normal = result['normal'][blade*4]
            edge = tuple(new[1][k]-new[0][k] for k in range(3))
            self.assertAlmostEqual(sum(normal[k]*edge[k] for k in range(3)), 0.)
            self.assertAlmostEqual(math.sqrt(sum(x*x for x in normal)), 1.)
            self.assertGreater(normal[0]*side, 0.)
            self.assertAlmostEqual(receipt['components'][blade]['output_surface_area'] /
                                   receipt['components'][blade]['input_surface_area'], .1)

    def test_inverse_transpose_keeps_a_nontrivial_transformed_face_normal_perpendicular(self):
        points = [(1., 0., 0.), (2., 0., 0.), (1., 1., 0.),
                  (1., 2., 2.), (2., 2., 2.), (1., 3., 2.)]
        out = list(points)
        normals = [(0., 0., 1.)]*6
        repair._thin_component(points, [0, 1, 2, 3, 4, 5], [0, 1], out, normals, .1)
        self.assertNotEqual(normals[0], (0., 0., 1.))
        for j in [1, 2]:
            edge = [out[j][k]-out[0][k] for k in range(3)]
            self.assertAlmostEqual(sum(normals[0][k]*edge[k] for k in range(3)), 0.)

    def test_coordinate_seam_copies_move_together(self):
        points = [(1., 0., -.05), (1., 1., .45), (1., 1., .55), (1., 0., -.05)]
        indices = [0, 1, 2, 3, 1, 2]
        out = list(points)
        normals = [(1., 0., 0.)]*4
        repair._thin_component(points, indices, [0, 1], out, normals, .1)
        self.assertEqual(out[0], out[3])

    def test_double_application_and_unbounded_reconstruction_fail_closed(self):
        result, _ = self.derive()
        with self.assertRaisesRegex(ValueError, 'decoded preview geometry differs'):
            self.derive(result)
        with patch.object(repair, 'MAXIMUM_DISPLACEMENT', .001):
            with self.assertRaisesRegex(ValueError, 'displacement bound'):
                self.derive()

    def test_invalid_centerline_scale_normals_and_fingerprint_are_rejected(self):
        for scale in [0, -1, 2]:
            with self.assertRaisesRegex(ValueError, 'centerline or contraction'):
                repair._thin_component(self.geometry['position'], self.geometry['indices'], [0, 1],
                                       list(self.geometry['position']), list(self.geometry['normal']), scale)
        for points, normals, expected in [([(1., 0., 0.)]*3, [(1., 0., 0.)]*3, 'centerline'),
                                         ([(1., 0., 0.), (1., 1., 0.), (1., 0., 1.)],
                                          [(0., 0., 0.)]*3, 'invalid normal')]:
            with self.assertRaisesRegex(ValueError, expected):
                repair._thin_component(points, [0, 1, 2], [0], list(points), list(normals), .1)
        for invalid in [{'x': float('nan')}, {'x': object()}]:
            with self.assertRaisesRegex(ValueError, 'cannot be fingerprinted'):
                repair.geometry_digest(invalid)


class NativePreviewGeometryTests(unittest.TestCase):
    def test_pinned_native_cleanup_scope_and_determinism(self):
        path = ROOT/'midnight-club-los-angeles/cars'/repair.TARGET_FILE
        if not path.exists():
            self.skipTest('Private native S7 extraction absent; synthetic controls still run')
        import mcla_lzx
        import mcla_model
        raw = path.read_bytes()
        self.assertEqual(hashlib.sha256(raw).hexdigest(), repair.TARGET_SHA256)
        data, header = mcla_lzx.decompress(raw)
        native = mcla_model.decode(data, header['virtual'], header['physical'])['models'][0]['geometries'][1]
        before = copy.deepcopy(native)
        result, receipt = repair.cleanup_preview_geometry(native, repair.TARGET_FILE, repair.TARGET_SHA256, 1)
        self.assertEqual(native, before)
        self.assertEqual(receipt['changed_vertices'], 292)
        self.assertEqual(receipt['changed_triangles'], 344)
        self.assertEqual((receipt['surviving_upper_dividers'], receipt['surviving_lower_dividers']), (4, 6))
        self.assertAlmostEqual(receipt['maximum_displacement'], .09343684844388069)
        fin_vertices = {i for ranges in repair.FIN_RANGES for a, b in ranges
                        for t in range(a, b) for i in native['indices'][t*3:t*3+3]}
        groups = {}
        for i, point in enumerate(native['position']):
            if i not in fin_vertices:
                self.assertEqual(result['position'][i], point)
                self.assertEqual(result['normal'][i], native['normal'][i])
            else:
                self.assertEqual(result['position'][i][1], point[1])
            groups.setdefault(point, []).append(i)
        for ids in groups.values():
            self.assertEqual(len({result['position'][i] for i in ids}), 1)
        for key in native:
            if key not in ('position', 'normal'):
                self.assertEqual(native[key], result[key])
        for c in receipt['components']:
            self.assertGreater(c['output_surface_area']/c['input_surface_area'], .099)
            self.assertLess(c['output_surface_area']/c['input_surface_area'], .101)
        self.assertEqual((result, receipt), repair.cleanup_preview_geometry(native, repair.TARGET_FILE,
                                                                          repair.TARGET_SHA256, 1))
        self.assertEqual(hashlib.sha256(path.read_bytes()).hexdigest(), repair.TARGET_SHA256)


if __name__ == '__main__':
    unittest.main(verbosity=2)
