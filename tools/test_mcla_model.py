"""Model resource decoding on a synthetic resource, with one mutation per structural rule."""
import struct
import unittest

import mcla_model
from mcla_model import MODEL_VFTS, TYPE_TABLE, ModelError, decode, dec3n, summary, vertex_format
from test_mcla_resource import Builder

STRIDE = 28  # position, normal, colour0, texcoord0, tangent
MASK = 0x4059


def pack_dec3n(x, y, z):
    return sum((round(v * 511) & 0x3FF) << shift for v, shift in ((x, 0), (y, 10), (z, 20)))


def build(vertex_sets=None, bones=None):
    """A model resource with one model of len(vertex_sets) geometries; returns (data, virtual, physical, at)."""
    vertex_sets = vertex_sets or [
        ([(0.0, 0.0, 0.0), (1.0, 0.0, 0.0), (0.0, 1.0, 0.0)], [0, 1, 2]),
        ([(0.0, 0.0, 1.0), (1.0, 0.0, 1.0), (1.0, 1.0, 1.0), (0.0, 1.0, 1.0)], [0, 1, 2, 0, 2, 3])]
    bones = bones if bones is not None else [('vroot', -1, (0.0, 0.0, 0.0), (0.0, 0.0, 0.0)),
                                             ('hd', 0, (0.0, 0.5, -1.0), (0.0, 0.0, 0.0))]
    b, at = Builder(), {}
    root = b.alloc(0x40)
    lod, models = b.alloc(16), b.alloc(4)
    model = b.alloc(0x1C)
    count = len(vertex_sets)
    geometries = b.alloc(4 * count)
    spheres = b.alloc(16 * (count + 1 if count > 1 else 1))
    shaders = b.alloc(2 * count)
    b.put(root, 'II', MODEL_VFTS[0], 0)
    b.put(root + 8, 'I', b.pointer(lod))
    b.put(lod, 'IHH', b.pointer(models), 1, 1)
    b.put(models, 'I', b.pointer(model))
    b.put(model, 'IIHH', 0x0C4B5A00, b.pointer(geometries), count, count)
    b.put(model + 0x0C, 'II', b.pointer(spheres), b.pointer(shaders))
    b.put(model + 0x14, '6BH', 0, 0, 0xCD, 0, 0, 0, count)
    b.put(spheres, '4f', 0.5, 0.5, 0.5, 2.0)
    at.update(root=root, lod=lod, model=model, spheres=spheres, geometries=[])
    for i, (points, indices) in enumerate(vertex_sets):
        g, vb, ib, fvf = b.alloc(0x50), b.alloc(0x20), b.alloc(0x10), b.alloc(16)
        vdata, idata = b.alloc(STRIDE * len(points)), b.alloc(2 * len(indices))
        b.put(geometries + 4 * i, 'I', b.pointer(g))
        b.put(spheres + 16 * (i + 1 if count > 1 else 0), '4f', 0.5, 0.5, 0.5, 1.5)
        b.put(shaders + 2 * i, 'H', 3 + i)
        b.put(g + 0x0C, 'I', b.pointer(vb))
        b.put(g + 0x1C, 'I', b.pointer(ib))
        b.put(g + 0x2C, 'IIHH', len(indices), len(indices) // 3, len(points), 3)
        b.put(g + 0x3C, 'HH', STRIDE, 0)
        b.put(vb + 4, 'HBBII', len(points), 0, 0, b.pointer(vdata), STRIDE)
        b.put(vb + 0x10, 'III', b.pointer(fvf), 0, b.pointer(vdata))
        b.put(fvf, 'IBBBBQ', MASK, STRIDE, 0, 0, 5, TYPE_TABLE)
        b.put(ib + 4, 'II', len(indices), b.pointer(idata))
        for k, point in enumerate(points):
            v = vdata + k * STRIDE
            b.put(v, '3fI4B2eI', *point, pack_dec3n(0.0, 0.0, -1.0), 10, 20, 30, 255, k * 0.25, 1 - k * 0.25,
                  pack_dec3n(1.0, 0.0, 0.0))
        b.put(idata, '%dH' % len(indices), *indices)
        at['geometries'].append({'geometry': g, 'vb': vb, 'ib': ib, 'fvf': fvf, 'vdata': vdata, 'idata': idata})
    if bones:
        skeleton, array = b.alloc(0x40), b.alloc(224 * len(bones))
        b.put(root + 0x24, 'I', b.pointer(skeleton))
        b.put(skeleton, 'I', b.pointer(array))
        b.put(skeleton + 0x14, 'H', len(bones))
        model_space = []
        for i, (name, parent, local, euler) in enumerate(bones):
            bone = array + 224 * i
            b.put(bone, 'I', b.pointer(b.text(name)))
            if parent >= 0:
                b.put(bone + 0x10, 'I', b.pointer(array + 224 * parent))
            b.put(bone + 0x14, 'HH', i, 1000 + i)
            b.put(bone + 0x20, '3f', *local)
            b.put(bone + 0x30, '3f', *euler)
            b.put(bone + 0x40, '4f', 0.0, 0.0, 0.0, 1.0)
            base = model_space[parent] if parent >= 0 else (0.0, 0.0, 0.0)
            model_space.append(tuple(p + q for p, q in zip(base, local)))
            b.put(bone + 0x60, '3f', *model_space[-1])
        binding = b.alloc(4)
        b.put(lod + 8, 'IHH', b.pointer(binding), 1, 1)
        b.put(binding, 'I', 0)
        cache = b.alloc(0x20 + 48 * len(bones))
        b.put(root + 0x30, 'I', b.pointer(cache))
        b.put(cache, 'HH', len(bones), len(bones))
        for i in range(len(bones)):
            relative = tuple(model_space[i][k] - model_space[0][k] for k in range(3))
            struct.pack_into('<12f', b.data, cache + 0x20 + 48 * i,
                             1., 0., 0., relative[0], 0., 1., 0., relative[1], 0., 0., 1., relative[2])
        at.update(skeleton=skeleton, bones=array, binding=binding, cache=cache)
    data, virtual, physical = b.segment()
    return bytearray(data), virtual, physical, at


def patched(data, at, fmt, *values):
    data = bytearray(data)
    struct.pack_into('>' + fmt, data, at, *values)
    return data


class Decoding(unittest.TestCase):
    def test_cached_draw_pose_restores_noncommuting_ancestor_bind_chain(self):
        bones = [('root', -1, (2., 3., 4.), (0., 0., 0.)),
                 ('child', 0, (1., 0., 0.), (0., 0., 0.)),
                 ('grandchild', 1, (0., 1., 0.), (0., 0., 0.)),
                 ('sibling', 0, (0., 0., 1.), (0., 0., 0.))]
        data, virtual, physical, at = build(bones=bones)
        quarter = 1.5707963267948966
        # Root Y, child Z, grandchild X are not interchangeable. Raw cached
        # rotations also differ from parent draw rotations, so neither a local
        # orient alone nor a parent draw-pose product gives the expected axes.
        orientations = ((0., quarter, 0.), (0., 0., quarter), (quarter, 0., 0.), (0., 0., 0.))
        caches = ((1., 0., 0., 10., 0., 1., 0., 20., 0., 0., 1., 30.),
                  (0., 0., 1., 11., 0., 1., 0., 22., -1., 0., 0., 33.),
                  (0., -1., 0., 14., 1., 0., 0., 25., 0., 0., 1., 36.),
                  (1., 0., 0., 17., 0., 1., 0., 28., 0., 0., 1., 39.))
        for index, (orient, cache) in enumerate(zip(orientations, caches)):
            data = patched(data, at['bones'] + index * 224 + 0x70, '3f', *orient)
            struct.pack_into('<12f', data, at['cache'] + 0x20 + index * 48, *cache)
        data = patched(data, at['binding'], 'I', 2)
        decoded = decode(bytes(data), virtual, physical)
        expected_axes = ((0., 0., -1., 0., 0., 1., 0., 0., 1., 0., 0., 0.),
                         (0., 1., 0., 0., 1., 0., 0., 0., 0., 0., -1., 0.),
                         (-1., 0., 0., 0., 0., 1., 0., 0., 0., 0., -1., 0.),
                         (0., 0., -1., 0., 0., 1., 0., 0., 1., 0., 0., 0.))
        for index, bone in enumerate(decoded['skeleton']):
            for got, want in zip(bone['matrix'][:12], expected_axes[index]):
                self.assertAlmostEqual(got, want, places=6)
            raw = tuple(caches[index][row * 4 + col] if row < 3 else float(col == 3)
                        for col in range(4) for row in range(4))
            self.assertEqual(bone['cached_matrix'], raw)
            self.assertEqual(bone['matrix'][12:15], tuple(caches[index][i * 4 + 3] - caches[0][i * 4 + 3] + bones[0][2][i] for i in range(3)))
        self.assertEqual(decoded['models'][0]['bone_index'], 2)
        self.assertEqual(summary(decoded)['vertices'], 7)

    def test_cached_bind_basis_restores_mixed_axis_preorientation_on_right(self):
        data, virtual, physical, at = build()
        # Cache is Y quarter turn; orient is Z quarter turn after Y quarter turn.
        # Order and multiplication side both matter for this native factorization.
        struct.pack_into('<12f', data, at['cache'] + 0x20,
                         0., 0., 1., 0., 0., 1., 0., 0., -1., 0., 0., 0.)
        data = patched(data, at['bones'] + 0x70, '3f', 0., 1.5707963267948966, 1.5707963267948966)
        bone = decode(bytes(data), virtual, physical)['skeleton'][0]
        expected = (-1., 0., 0., 0., 0., 0., 1., 0., 0., 1., 0., 0., 0., 0., 0., 1.)
        for got, want in zip(bone['matrix'], expected):
            self.assertAlmostEqual(got, want, places=6)
        self.assertEqual(bone['cached_matrix'][:3], (0., 0., -1.))

    def test_cached_translation_rebases_root_and_descendant_separately(self):
        bones = [('root', -1, (2., 3., 4.), (0., 0., 0.)),
                 ('child', 0, (0., .5, -1.), (0., 0., 0.))]
        data, virtual, physical, at = build(bones=bones)
        for index, xyz in enumerate(((10., 20., 30.), (11., 22., 33.))):
            struct.pack_into('<12f', data, at['cache'] + 0x20 + index * 48,
                             1., 0., 0., xyz[0], 0., 1., 0., xyz[1], 0., 0., 1., xyz[2])
        root, child = decode(bytes(data), virtual, physical)['skeleton']
        self.assertEqual(root['cached_matrix'][12:15], (10., 20., 30.))
        self.assertEqual(root['matrix'][12:15], (2., 3., 4.))
        self.assertEqual(child['cached_matrix'][12:15], (11., 22., 33.))
        self.assertEqual(child['matrix'][12:15], (3., 5., 7.))
        self.assertEqual(child['model'], (2., 3.5, 3.))

    def test_binding_and_cached_orientation_preserve_authored_translation(self):
        data, virtual, physical, at = build(bones=[('root', -1, (2., 3., 4.), (0., 1.5707963, 0.))])
        # Native row-major Y rotation: X axis goes toward -Z. Cached root T is zero.
        struct.pack_into('<12f', data, at['cache'] + 0x20,
                         0., 0., 1., 0., 0., 1., 0., 0., -1., 0., 0., 0.)
        decoded = decode(bytes(data), virtual, physical)
        self.assertEqual(decoded['models'][0]['bone_index'], 0)
        bone = decoded['skeleton'][0]
        self.assertEqual(bone['cached_matrix'][12:15], (0., 0., 0.))
        self.assertEqual(bone['matrix'], (0., 0., -1., 0., 0., 1., 0., 0., 1., 0., 0., 0., 2., 3., 4., 1.))

    def test_nonzero_binding_is_not_the_model_matrix_index(self):
        data, virtual, physical, at = build()
        data = patched(data, at['binding'], 'I', 1)
        model = decode(bytes(data), virtual, physical)['models'][0]
        self.assertEqual((model['bone_index'], model['matrix_index']), (1, 0))

    def test_optional_cache_and_binding_are_explicit(self):
        data, virtual, physical, at = build()
        data = patched(patched(data, 0x30, 'I', 0), at['lod'] + 8, 'IHH', 0, 0, 0)
        decoded = decode(bytes(data), virtual, physical)
        self.assertIsNone(decoded['models'][0]['bone_index'])
        self.assertIsNone(decoded['skeleton'][1]['cached_matrix'])
        self.assertEqual(decoded['skeleton'][1]['matrix'][12:15], (0., .5, -1.))

    def test_geometry_channels_skeleton_and_summary(self):
        data, virtual, physical, _ = build()
        decoded = decode(bytes(data), virtual, physical)
        model = decoded['models'][0]
        first, second = model['geometries']
        self.assertEqual(first['channels'], ['position', 'normal', 'colour0', 'texcoord0', 'tangent'])
        self.assertEqual(first['position'][1], (1.0, 0.0, 0.0))
        self.assertEqual(first['normal'][0], (0.0, 0.0, -1.0))
        self.assertEqual(first['colour0'][2], (10, 20, 30, 255))
        self.assertEqual(first['texcoord0'][2], (0.5, 0.5))
        self.assertEqual(second['indices'], [0, 1, 2, 0, 2, 3])
        self.assertEqual((first['shader'], second['shader']), (3, 4))
        self.assertEqual(model['sphere'], (0.5, 0.5, 0.5, 2.0))
        self.assertEqual((model['matrix_count'], model['skinned']), (0, False))
        self.assertEqual([(bone['name'], bone['parent'], bone['model']) for bone in decoded['skeleton']],
                         [('vroot', -1, (0.0, 0.0, 0.0)), ('hd', 0, (0.0, 0.5, -1.0))])
        self.assertEqual(summary(decoded), {'bones': 2, 'models': 1, 'geometries': 2, 'vertices': 7, 'triangles': 3,
                                            'bounds': [[0.0, 0.0, 0.0], [1.0, 1.0, 1.0]]})

    def test_single_geometry_uses_the_model_sphere_and_optional_tables(self):
        data, virtual, physical, at = build(vertex_sets=[([(0.0, 0.0, 0.0)] * 3, [0, 1, 2])], bones=[])
        decoded = decode(bytes(data), virtual, physical)
        self.assertEqual(decoded['skeleton'], [])
        self.assertEqual(decoded['models'][0]['geometries'][0]['sphere'], (0.5, 0.5, 0.5, 1.5))
        bare = patched(data, at['model'] + 0x0C, 'II', 0, 0)
        geometry = decode(bytes(bare), virtual, physical)['models'][0]['geometries'][0]
        self.assertEqual((geometry['sphere'], geometry['shader']), (None, None))

    def test_empty_geometry_has_no_bounds(self):
        data, virtual, physical, _ = build(vertex_sets=[([], [])], bones=[])
        self.assertIsNone(summary(decode(bytes(data), virtual, physical))['bounds'])

    def test_rotated_ancestors_skip_the_offset_chain_check(self):
        bones = [('vroot', -1, (0.0, 0.0, 0.0), (0.0, 0.0, 0.0)), ('rotator', 0, (0.0, 1.0, 0.0), (0.5, 0.0, 0.0)),
                 ('window', 1, (1.0, 0.0, 0.0), (0.0, 0.0, 0.0))]
        data, virtual, physical, at = build(bones=bones)
        moved = patched(data, at['bones'] + 2 * 224 + 0x60, '3f', 1.0, 1.2, 0.3)  # a rotated chain's stored offset
        skeleton = decode(bytes(moved), virtual, physical)['skeleton']
        self.assertEqual([bone['rotated'] for bone in skeleton], [False, False, True])
        self.assertEqual(skeleton[2]['model'], tuple(struct.unpack('>3f', struct.pack('>3f', 1.0, 1.2, 0.3))))

    def test_dec3n_signs(self):
        self.assertEqual(dec3n(pack_dec3n(-1.0, 0.5, 1.0)), (-1.0, 256 / 511, 1.0))

    def test_vertex_format_rules(self):
        self.assertEqual([c[0] for c in vertex_format(0x0001, 12, TYPE_TABLE)], ['position'])
        with self.assertRaisesRegex(ModelError, 'component table'):
            vertex_format(MASK, STRIDE, TYPE_TABLE ^ 1)
        with self.assertRaisesRegex(ModelError, 'above 16 channels'):
            vertex_format(0x10001, 12, TYPE_TABLE)
        with self.assertRaisesRegex(ModelError, 'differs from its channels'):
            vertex_format(MASK, 32, TYPE_TABLE)
        with self.assertRaisesRegex(ModelError, 'without positions'):
            vertex_format(0x0008, 4, TYPE_TABLE)


class Rejections(unittest.TestCase):
    def setUp(self):
        self.data, self.virtual, self.physical, self.at = build()
        self.g = self.at['geometries'][0]

    def rejects(self, data, reason):
        with self.assertRaisesRegex(ModelError, reason):
            decode(bytes(data), self.virtual, self.physical)

    def test_root_lod_and_model(self):
        self.rejects(patched(self.data, 0, 'I', 0x12345678), 'not a model resource')
        self.rejects(patched(self.data, 8, 'I', 0), 'without a drawable LOD')
        self.rejects(patched(self.data, self.at['lod'] + 4, 'H', 0), 'drawable LOD without models')
        self.rejects(patched(self.data, self.at['model'] + 8, 'H', 0), 'model without geometries')
        self.rejects(patched(self.data, self.at['model'] + 0x1A, 'H', 3), 'geometry count fields differ')
        self.rejects(patched(self.data, self.at['spheres'], 'f', float('nan')), 'not finite')
        self.rejects(patched(self.data, 8, 'I', 0x50FFFFF0), 'outside its segment')
        self.rejects(self.data[:-4], 'size differs')

    def test_geometry(self):
        g = self.g
        self.rejects(patched(self.data, g['geometry'] + 0x0C, 'I', 0), 'without vertex or index buffer')
        self.rejects(patched(self.data, g['geometry'] + 0x10, 'I', 0x50000000), 'second buffer set')
        self.rejects(patched(self.data, g['geometry'] + 0x36, 'H', 5), 'not a triangle list')
        self.rejects(patched(self.data, g['geometry'] + 0x30, 'I', 2), 'primitive count differs')
        self.rejects(patched(self.data, g['vb'] + 4, 'H', 4), 'vertex buffer count differs')
        self.rejects(patched(self.data, g['vb'] + 0x0C, 'I', 32), 'vertex buffer stride differs')
        self.rejects(patched(self.data, g['vb'] + 8, 'I', 0), 'locked vertex data differs')
        self.rejects(patched(self.data, g['fvf'] + 4, 'B', 24), 'differs from its channels')
        widened = patched(patched(self.data, g['geometry'] + 0x3C, 'H', 32), g['vb'] + 0x0C, 'I', 32)
        self.rejects(widened, 'vertex format size differs from the stride')
        self.rejects(patched(self.data, g['ib'] + 4, 'I', 6), 'index buffer count differs')
        self.rejects(patched(self.data, g['idata'], 'H', 3), 'index outside the vertex buffer')
        self.rejects(patched(self.data, g['vdata'], 'f', 9.0), 'outside its bounding sphere')

    def test_required_null_pointers_raise_model_errors(self):
        models = struct.unpack_from('>I', self.data, self.at['lod'])[0] & 0x0FFFFFFF
        geometries = struct.unpack_from('>I', self.data, self.at['model'] + 4)[0] & 0x0FFFFFFF
        for at in (models, geometries, self.g['vb'] + 0x10):
            with self.subTest(at=at):
                self.rejects(patched(self.data, at, 'I', 0), 'not a resource pointer')

    def test_skeleton(self):
        bones, skeleton = self.at['bones'], self.at['skeleton']
        self.rejects(patched(self.data, skeleton + 0x14, 'H', 0), 'skeleton without bones')
        self.rejects(patched(self.data, bones + 224 + 0x10, 'I', Builder.pointer(bones + 224)), 'after the bone')
        self.rejects(patched(self.data, bones + 224 + 0x10, 'I', Builder.pointer(bones + 8)), 'outside its skeleton')
        self.rejects(patched(self.data, bones + 224 + 0x14, 'H', 7), 'index field differs')
        self.rejects(patched(self.data, bones + 224 + 0x40, 'f', 0.5), 'rotation quaternion')
        self.rejects(patched(self.data, bones + 224 + 0x64, 'f', 0.75), 'differs from its parent chain')
        self.rejects(patched(self.data, bones + 0x30, 'f', float('inf')), 'transform is not finite')

    def test_binding_counts_bounds_and_indices(self):
        lod = self.at['lod']
        self.rejects(patched(self.data, lod + 6, 'H', 0), 'model count exceeds capacity')
        self.rejects(patched(self.data, lod + 14, 'H', 0), 'binding count exceeds capacity')
        self.rejects(patched(self.data, lod + 12, 'HH', 2, 2), 'binding count differs')
        self.rejects(patched(self.data, lod + 8, 'I', 0), 'binding count differs')
        self.rejects(patched(self.data, self.at['binding'], 'I', 2), 'binding outside skeleton')
        self.rejects(patched(self.data, lod + 8, 'I', Builder.pointer(self.virtual - 2)), 'outside its segment')
        self.rejects(patched(self.data, lod, 'I', Builder.pointer(self.virtual - 2)), 'outside its segment')

    def test_cache_counts_bounds_and_rotation_controls(self):
        cache = self.at['cache']
        self.rejects(patched(self.data, cache, 'H', 1), 'cache counts differ')
        self.rejects(patched(self.data, cache + 2, 'H', 1), 'cache counts differ')
        # The cache header fits; the inline matrix array does not.
        self.rejects(patched(self.data, 0x30, 'I', Builder.pointer(self.virtual - 32)), 'outside its segment')
        data = bytearray(self.data)
        for value, reason in ((float('nan'), 'not finite'), (2., 'not orthogonal'), (-1., 'not a proper rotation')):
            struct.pack_into('<f', data, cache + 0x20, value)
            self.rejects(data, reason)
        data = patched(patched(self.data, 0x30, 'I', 0), self.at['bones'] + 0x70, 'f', .5)
        self.rejects(data, 'rotated skeleton without matrix cache')
        self.rejects(patched(self.data, 0x24, 'I', 0), 'matrix cache without skeleton')

    def test_struct_errors_become_model_errors(self):
        original = mcla_model.skeleton
        mcla_model.skeleton = lambda *_: struct.unpack('>I', b'')
        try:
            self.rejects(self.data, 'unpack requires')
        finally:
            mcla_model.skeleton = original


if __name__ == '__main__':
    unittest.main(verbosity=2)
