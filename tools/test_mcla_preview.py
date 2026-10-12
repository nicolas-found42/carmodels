"""Stock assembly on synthetic native resources, with corrupt-source and geometry controls."""
import copy
import json
import struct
import tempfile
import unittest
from pathlib import Path

import mcla_model
import mcla_preview as preview
import mcla_texture
from bake_models import accessor, node_transform, read_glb
from gt4_glb import Builder
from mcla_rpf import jenkins
from test_mcla_lzx import Encoder, resource
from test_mcla_model import build as model_resource, pack_dec3n
from test_mcla_texture import build_pack
from unittest.mock import patch


def wrapped(data, kind):
    encoder = Encoder()
    # A resource can contain more than one frame.
    for start in range(0, len(data), 32768):
        encoder.stored(data[start:start + 32768])
        encoder.close()
    return resource(encoder.body(), len(data), kind)


def fixture(root, code='vp_test_car_00', bike=False, brakes=True, hashed=False, rim_root=(0., 0., 0.), rim_face=False):
    points = [(-0.25, -0.5, -0.5), (0.25, 0.5, -0.5), (0., 0., 0.5)]
    body_bones = [('vroot', -1, (0., 0., 0.), (0., 0., 0.)),
                  ('hd', 0, (0., 1., -1.), (0., 0., 0.)),
                  ('door_l', 0, (0., 0., 0.), (0., 0., 0.)),
                  ('door_l_regular_anim', 0, (-1., 1., 0.), (0., 0., 0.)),
                  ('bumr', 0, (0., .5, 2.), (0., 0., 0.))]
    axes = [('axl_front', (0., .3, -1.)), ('axl_rear', (0., .35, 1.))] if bike else [
        ('axl_0', (-.75, .3, -1.)), ('axl_1', (.75, .3, -1.)),
        ('axl_2', (-.75, .35, 1.)), ('axl_3', (.75, .35, 1.))]
    body_bones += [(name, 0, xyz, (0., 0., 0.)) for name, xyz in axes]
    files = {}

    def model(path, bones):
        is_face = rim_face and '/rims/' in path
        shape = [(-.2, -.5, 0.), (-.2, .5, 0.), (-.2, 0., .5)] if is_face else points
        data, virtual, physical, at = model_resource([(shape, [0, 1, 2])], bones)
        if is_face:
            for i in range(3):
                struct.pack_into('>I', data, at['geometries'][0]['vdata'] + i * 28 + 12, pack_dec3n(-1., 0., 0.))
        struct.pack_into('>4f', data, at['spheres'], 0., 0., 0., 2.)
        shaders_pointer = struct.unpack_from('>I', data, at['model'] + 0x10)[0] & 0xfffffff
        struct.pack_into('>H', data, shaders_pointer, 0)
        files[path] = wrapped(data, 63)

    pack_data, _, _, _ = build_pack()
    pack_bytes = wrapped(pack_data, 83)
    prefix = code + '/resources/vehicle/' + code
    model(prefix + '/body_lod_0.xrsc', body_bones)
    model(prefix + '/hood0_lod_0.xrsc', [('hd00_stk', -1, (0., 0., 0.), (0., 0., 0.))])
    model(prefix + '/door_l0_lod_0.xrsc', [('door_l_stk', -1, (0., 0., 0.), (0., 0., 0.))])
    model(prefix + '/door_l_wide0_lod_0.xrsc', [('wide', -1, (0., 0., 0.), (0., 0., 0.))])
    model(prefix + '/occluder_0_lod_0.xrsc', [])
    files[prefix + '/' + code + '.xtl'] = pack_bytes
    files[prefix + '/' + code + '.xtp'] = pack_bytes
    rim = preview.stock_rim_name(code)
    directory = '0x%08x' % jenkins(rim) if hashed else rim
    prefixes = ['shared/resources/rims/' + directory, 'shared/resources/tires/models/' + ('tir_bike' if bike else 'tir_car')]
    if brakes:
        prefixes.append('shared/resources/brakes/brk_stk_' + code.split('_', 1)[1])
    for shared in prefixes:
        origin = rim_root if '/rims/' in shared else (0., 0., 0.)
        model(shared + '/body_lod_0.xrsc', [('root', -1, origin, (0., 0., 0.))])
        files[shared + '/' + Path(shared).name + '.xtp'] = pack_bytes
    rows = []
    for path, data in files.items():
        target = root / path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(data)
        rows.append({'file': path, 'bytes': len(data), 'sha256': preview.sha(data), 'source': {'entry': len(rows)}})
    index = {'files': rows, 'vehicles': [{'id': code}]}
    (root / 'index.json').write_text(json.dumps(index))
    return index


def pose_bone(name, xyz, quarter_turn=False):
    """Independent explicit GLTF basis: a positive Y quarter turn sends +X toward -Z."""
    basis = (0., 0., -1., 0., 0., 1., 0., 0., 1., 0., 0., 0.) if quarter_turn else (
        1., 0., 0., 0., 0., 1., 0., 0., 0., 0., 1., 0.)
    return {'name': name, 'model': tuple(xyz), 'matrix': basis + tuple(xyz) + (1.,),
            'cached_matrix': basis + (0., 0., 0., 1.)}


def add_part(root, index, name):
    source = next(row for row in index['files'] if row['file'].endswith('/hood0_lod_0.xrsc'))
    path = str(Path(source['file']).with_name(name + '0_lod_0.xrsc'))
    (root / path).write_bytes((root / source['file']).read_bytes())
    index['files'].append(dict(source, file=path))
    return path


class Assembly(unittest.TestCase):
    def test_preview_cleanup_uses_verified_source_and_emits_repaired_geometry_and_receipt(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            index = fixture(root)
            source = next(r for r in index['files'] if r['file'].endswith('/body_lod_0.xrsc')
                          and r['file'].startswith('vp_test_car_00/'))
            native_bytes = (root / source['file']).read_bytes()
            calls = []

            def cleanup(g, namespace, digest, geometry_index, model_index=0):
                calls.append((namespace, digest, model_index, geometry_index))
                if namespace != source['file']:
                    return g, None
                before = copy.deepcopy(g)
                repaired = copy.deepcopy(g)
                for field in ('position', 'normal', 'texcoord0'):
                    repaired[field].append(tuple((a + b) / 2 for a, b in zip(g[field][0], g[field][1])))
                repaired['indices'] = [0, 3, 2, 3, 1, 2]
                self.assertEqual(g, before, 'Derived repair must not alter decoded source values')
                return repaired, {'source_file': namespace, 'source_sha256': digest,
                                  'model_index': model_index, 'geometry_index': geometry_index,
                                  'input_triangles': 1, 'output_triangles': 2}

            with patch.object(preview, 'cleanup_preview_geometry', cleanup):
                data, record = preview.build_car(root, 'vp_test_car_00', index)
            self.assertEqual([r for r in calls if r[0] == source['file']],
                             [(source['file'], source['sha256'], 0, 0)])
            self.assertEqual(len(record['preview_geometry_repairs']), 1)
            repair = record['preview_geometry_repairs'][0]
            self.assertEqual(repair['source_sha256'], source['sha256'])
            self.assertEqual(next(p for p in record['parts'] if p['slot'] == 'body')['triangles'], 2)
            doc, binary = read_glb(data)
            node = next(n for n in doc['nodes'] if '/body_lod_0.xrsc@' in n['name']
                        and n['name'].startswith('vp_test_car_00/'))
            primitive = doc['meshes'][node['mesh']]['primitives'][0]
            self.assertEqual(accessor(doc, binary, primitive['attributes']['POSITION'], 3, 5126)[3],
                             (0., 0., -.5))
            self.assertEqual(accessor(doc, binary, primitive['indices'], 1, 5125),
                             [(0,), (3,), (2,), (3,), (1,), (2,)])
            self.assertEqual(doc['extras']['preview_geometry_repairs'], record['preview_geometry_repairs'])
            self.assertEqual((root / source['file']).read_bytes(), native_bytes)

    def test_preview_cleanup_failure_stops_export(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            index = fixture(root)
            with patch.object(preview, 'cleanup_preview_geometry', side_effect=ValueError('geometry pin differs')):
                with self.assertRaisesRegex(ValueError, 'geometry pin differs'):
                    preview.build_car(root, 'vp_test_car_00', index)

    def test_instanced_exhaust_replaces_authoring_root_and_keeps_child_binding(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            index = fixture(root)
            add_part(root, index, 'bumper_r')
            add_part(root, index, 'exh_pipe')
            original = preview.Sources.model

            def posed(self, path):
                part = copy.deepcopy(original(self, path))
                if path.endswith('/bumper_r0_lod_0.xrsc'):
                    part['skeleton'] = [pose_bone('rear_stk', (0., 0., 0.)),
                                        pose_bone('exst0', (-.5, .1, .2), quarter_turn=True)]
                elif path.endswith('/exh_pipe0_lod_0.xrsc'):
                    part['skeleton'] = [pose_bone('pipe_root', (1., .2, .3), quarter_turn=True),
                                        pose_bone('pipe_child', (1.2, .3, .4), quarter_turn=True)]
                    part['models'][0]['bone_index'] = 1
                return part

            with patch.object(preview.Sources, 'model', posed):
                data, record = preview.build_car(root, 'vp_test_car_00', index)
            doc, binary = read_glb(data)
            pipe = next(n for n in doc['nodes'] if '/exh_pipe0_lod_0.xrsc@' in n['name'])
            # The inverse authoring root maps child displacement to (-.1,.1,.2).
            # The native anchor then maps it to (.2,.1,.1), with one quarter turn.
            self.assertEqual(pipe['matrix'][:12], [0., 0., -1., 0., 0., 1., 0., 0., 1., 0., 0., 0.])
            for actual, expected in zip(pipe['matrix'][12:15], (-.3, .7, 2.3)):
                self.assertAlmostEqual(actual, expected)
            self.assertEqual(pipe['extras']['nativeBoneIndex'], 1)
            primitive = doc['meshes'][pipe['mesh']]['primitives'][0]
            self.assertEqual(accessor(doc, binary, primitive['attributes']['POSITION'], 3, 5126),
                             [(-.25, -.5, -.5), (.25, .5, -.5), (0., 0., .5)])
            self.assertEqual(next(p for p in record['parts'] if p['slot'] == 'exh_pipe')['resource_frame'], 'root-relative')

    def test_rigid_roof_prefers_native_top_counterframe_over_matching_root(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            index = fixture(root)
            add_part(root, index, 'conv_topup')
            original = preview.Sources.model

            def posed(self, path):
                part = copy.deepcopy(original(self, path))
                if path.startswith('shared/'):
                    return part
                if path.endswith('/body_lod_0.xrsc'):
                    top = pose_bone('conv_tops', (0., 1., 0.), quarter_turn=True)
                    # Independent negative Y quarter turn, inverse of the roof.
                    top['matrix'] = (0., 0., 1., 0., 0., 1., 0., 0., -1., 0., 0., 0., 0., 1., 0., 1.)
                    part['skeleton'].append(top)
                elif path.endswith('/conv_topup0_lod_0.xrsc'):
                    part['skeleton'][0] = pose_bone('vroot', (0., 0., 0.), quarter_turn=True)
                return part

            with patch.object(preview.Sources, 'model', posed):
                data, record = preview.build_car(root, 'vp_test_car_00', index)
            doc, _ = read_glb(data)
            roof = next(n for n in doc['nodes'] if '/conv_topup0_lod_0.xrsc@' in n['name'])
            self.assertEqual(roof['matrix'], [1., 0., 0., 0., 0., 1., 0., 0., 0., 0., 1., 0., 0., 1., 0., 1.])
            self.assertEqual(next(p for p in record['parts'] if p['slot'] == 'conv_topup')['bone'], 'conv_tops')
        part = {'skeleton': [{'name': 'vroot'}]}
        body = {'vroot': pose_bone('vroot', (0., 0., 0.)), 'hardtops': pose_bone('hardtops', (0., 1., 0.))}
        self.assertEqual(preview.attachment('conv_topdown', part, body), ('hardtops', (0., 1., 0.)))

    def test_trunk_lamp_inherits_owner_rotation_before_its_root_compensation(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            index = fixture(root)
            add_part(root, index, 'trunk_swap')
            add_part(root, index, 'taillight_b')
            original = preview.Sources.model

            def posed(self, path):
                part = copy.deepcopy(original(self, path))
                if path.startswith('shared/'):
                    return part
                if path.endswith('/body_lod_0.xrsc'):
                    part['skeleton'].append(pose_bone('tk', (0., 1., 2.)))
                elif path.endswith('/trunk_swap0_lod_0.xrsc'):
                    part['skeleton'][0] = pose_bone('tk_swap', (0., 0., 0.), quarter_turn=True)
                elif path.endswith('/taillight_b0_lod_0.xrsc'):
                    part['skeleton'][0] = pose_bone('trunk_tl', (1., -.5, .25))
                return part

            with patch.object(preview.Sources, 'model', posed):
                data, _ = preview.build_car(root, 'vp_test_car_00', index)
            doc, _ = read_glb(data)
            lamp = next(n for n in doc['nodes'] if '/taillight_b0_lod_0.xrsc@' in n['name'])
            trunk = next(n for n in doc['nodes'] if '/trunk_swap0_lod_0.xrsc@' in n['name'])
            # A +Y quarter turn maps lamp's +X compensation toward -Z, and
            # +Z toward +X. Applying it twice or rotating geometry alone fails.
            self.assertEqual(lamp['matrix'][12:15], [.25, .5, 1.])
            self.assertEqual(lamp['matrix'][:12], trunk['matrix'][:12])
            self.assertEqual(trunk['matrix'][12:15], [0., 1., 2.])

    def test_normalized_shared_wheels_preserve_child_binding_offsets(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            fixture(root, rim_root=(0., 0., -1.194053))
            original = preview.Sources.model

            def child(self, path):
                part = copy.deepcopy(original(self, path))
                if '/rims/' in path:
                    rz = part['skeleton'][0]['model'][2]
                    part['skeleton'].append(pose_bone('rim_child', (.1, .2, rz + .3)))
                    part['models'][0]['bone_index'] = 1
                return part

            with patch.object(preview.Sources, 'model', child):
                data, record = preview.build_car(root, 'vp_test_car_00')
            doc, _ = read_glb(data)
            for node in [n for n in doc['nodes'] if n['name'].startswith('shared/resources/rims/')]:
                w = next(w for w in record['wheels'] if w['file'].split('/body_lod')[0] + '@' + w['bone'] + '/model0' == node['name'])
                sign = -1 if w['translation'][0] > 0 else 1
                expected = [w['translation'][0] + sign * .1 * w['scale'][0],
                            w['translation'][1] + .2 * w['scale'][1],
                            w['translation'][2] + sign * .3 * w['scale'][2]]
                for actual, target in zip(node['matrix'][12:15], expected):
                    self.assertAlmostEqual(actual, target)
                self.assertEqual(node['extras']['nativeBoneIndex'], 1)

    def test_rim_show_faces_point_outward_and_authoring_root_does_not_move_unit_wheels(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            fixture(root, rim_root=(0., 0., -1.194053), rim_face=True)
            data, record = preview.build_car(root, 'vp_test_car_00')
            doc, binary = read_glb(data)
            nodes = [n for n in doc['nodes'] if n['name'].startswith('shared/resources/rims/')]
            self.assertEqual(len(nodes), 4)
            for node in nodes:
                wheel = next(w for w in record['wheels'] if w['file'].split('/body_lod')[0] + '@' + w['bone'] + '/model0' == node['name'])
                pose = node_transform(node)
                # The native asymmetric show face is at negative X with -X normals.
                # After placement it must be outside its axle on either side, and
                # its center must not inherit the resource's unrelated authoring Z.
                self.assertEqual([pose[i][3] for i in range(3)], wheel['translation'])
                normal_x = -pose[0][0]
                self.assertGreater(normal_x * wheel['translation'][0], 0.)
                self.assertGreater((-.2 * pose[0][0]) * wheel['translation'][0], 0.)
                attrs = doc['meshes'][node['mesh']]['primitives'][0]['attributes']
                self.assertEqual(accessor(doc, binary, attrs['POSITION'], 3, 5126),
                                 [(-.20000000298023224, -.5, 0.), (-.20000000298023224, .5, 0.), (-.20000000298023224, 0., .5)])
                self.assertEqual(accessor(doc, binary, attrs['NORMAL'], 3, 5126), [(-1., 0., 0.)] * 3)

    def test_duplicate_scissor_labels_resolve_native_left_right_ancestry(self):
        bones = []
        for name, parent, x in [('vroot', -1, 0.), ('door_l', 0, 0.), ('door_l_regular', 1, -.8),
                                ('door_l_scissor', 2, -.9), ('door_r', 0, 0.), ('door_r_regular', 4, .8),
                                ('door_l_scissor', 5, .9)]:
            bones.append(dict(pose_bone(name, (x, 1., 0.)), parent=parent))
        lookup = preview.body_bones(bones)
        part = {'skeleton': [{'name': 'door_stk'}]}
        self.assertEqual(preview.attachment('door_l', part, lookup), ('door_l_scissor', (-.9, 1., 0.)))
        self.assertEqual(preview.attachment('door_r_int', part, lookup), ('door_r_scissor', (.9, 1., 0.)))
        self.assertEqual(lookup['door_l_scissor']['native_index'], 3)
        self.assertEqual(lookup['door_r_scissor']['native_index'], 6)
        bones[-1]['parent'] = 2
        with self.assertRaisesRegex(preview.PreviewError, 'ambiguous scissor-door ancestry'):
            preview.body_bones(bones)
        duplicates = preview.body_bones([dict(pose_bone('vroot', (0., 0., 0.)), parent=-1)] * 2)
        with self.assertRaisesRegex(preview.PreviewError, 'ambiguous body attachment'):
            preview.attachment('hood', {'skeleton': [{'name': 'vroot'}]}, duplicates)
        self.assertIsNone(preview.body_bones([dict(pose_bone('joint8', (0., 0., 0.)), parent=-1)] * 2)['joint8'])

    def test_front_fork_uses_steering_frame_and_other_mechanical_parts_keep_own_placement(self):
        steer = pose_bone('front_steer', (0., .9, -.4), quarter_turn=True)
        part = {'skeleton': [pose_bone('front_fork', (0., 0., 0.))]}
        name, matrix = preview.attachment_pose('armfl', part, {'front_steer': steer})
        self.assertEqual(name, 'front_steer')
        self.assertEqual(matrix, node_transform({'matrix': steer['matrix']}))
        with self.assertRaisesRegex(preview.PreviewError, 'front fork without steering'):
            preview.attachment_pose('armfl', part, {})
        part['skeleton'][0]['name'] = 'car_arm'
        self.assertEqual(preview.attachment_pose('armfl', part, {}), ('resource_root', preview.IDENTITY))

    def test_required_wide_shell_only_replaces_absent_regular_exterior(self):
        wide = ['p/body_lod_0.xrsc', 'p/widebody0_lod_0.xrsc', 'p/hood_wide0_lod_0.xrsc',
                'p/door_l_wide0_lod_0.xrsc', 'p/trunk_wide0_lod_0.xrsc', 'p/conv_top0_lod_0.xrsc']
        chosen, omitted = preview.select_parts(wide)
        self.assertEqual([slot for slot, _ in chosen], ['body', 'door_l_wide', 'hood_wide', 'trunk_wide', 'widebody'])
        self.assertEqual(omitted, ['p/conv_top0_lod_0.xrsc'])
        for exterior in ('hood', 'door_l', 'door_r', 'bumper_f', 'bumper_r'):
            with self.subTest(exterior=exterior):
                chosen, _ = preview.select_parts(wide + ['p/' + exterior + '0_lod_0.xrsc'])
                self.assertEqual([slot for slot, _ in chosen], ['body', exterior])

    def test_native_bindings_keep_separate_models_and_unmodified_attributes(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            index = fixture(root, code='va_test_car_00')
            original = preview.Sources.model

            def two_models(self, path):
                part = original(self, path)
                if path.endswith('/body_lod_0.xrsc'):
                    part['models'].append(copy.deepcopy(part['models'][0]))
                    part['models'][1]['bone_index'] = 1
                return part
            with patch.object(preview.Sources, 'model', two_models):
                data, record = preview.build_car(root, 'va_test_car_00', index)
            doc, binary = read_glb(data)
            nodes = [node for node in doc['nodes'] if '/body_lod_0.xrsc@' in node['name']]
            self.assertEqual([node['extras']['nativeBoneIndex'] for node in nodes], [0, 1])
            self.assertEqual([node['matrix'][12:15] for node in nodes], [[0., 0., 0.], [0., 1., -1.]])
            self.assertNotEqual(nodes[0]['mesh'], nodes[1]['mesh'])
            expected_positions = [(-.25, -.5, -.5), (.25, .5, -.5), (0., 0., .5)]
            for node in nodes:
                primitive = doc['meshes'][node['mesh']]['primitives'][0]
                attrs = primitive['attributes']
                self.assertEqual(accessor(doc, binary, attrs['POSITION'], 3, 5126), expected_positions)
                self.assertEqual(accessor(doc, binary, attrs['NORMAL'], 3, 5126), [(0., 0., -1.)] * 3)
                self.assertEqual(accessor(doc, binary, attrs['TEXCOORD_0'], 2, 5126), [(0., 1.), (.25, .75), (.5, .5)])
                self.assertEqual(accessor(doc, binary, primitive['indices'], 1, 5125), [(0,), (1,), (2,)])
            self.assertEqual(next(p for p in record['parts'] if p['slot'] == 'body')['vertices'], 6)
            self.assertTrue(all(row['sha256'] == preview.sha((root / row['file']).read_bytes()) for row in record['sources']))

    def test_scissor_root_compensation_and_noncommuting_attachment_order(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            fixture(root)
            original = preview.Sources.model

            def transformed(self, path):
                part = original(self, path)
                if path.endswith('/vehicle/vp_test_car_00/body_lod_0.xrsc'):
                    part['skeleton'].append(pose_bone('door_l_scissor_anim', (-1., 1.2, .3)))
                    hd = next(b for b in part['skeleton'] if b['name'] == 'hd')
                    hd.update(pose_bone('hd', (10., 2., 3.), quarter_turn=True))
                elif path.endswith('/door_l0_lod_0.xrsc'):
                    part['skeleton'][0].update(pose_bone('door_l_stk', (0., -.2, -.3)))
                elif path.endswith('/hood0_lod_0.xrsc'):
                    part['skeleton'][0].update(pose_bone('hd00_stk', (1., 0., 0.)))
                return part
            with patch.object(preview.Sources, 'model', transformed):
                data, record = preview.build_car(root, 'vp_test_car_00')
            doc, _ = read_glb(data)
            door = next(node for node in doc['nodes'] if '/door_l0_lod_0.xrsc@' in node['name'])
            self.assertEqual(door['matrix'][12:15], [-1., 1., 0.])
            self.assertEqual(next(p for p in record['parts'] if p['slot'] == 'door_l')['bone'], 'door_l_scissor_anim')
            hood = next(node for node in doc['nodes'] if '/hood0_lod_0.xrsc@' in node['name'])
            # Outer Y rotation sends local X translation toward -Z. Reversing
            # external/local composition would instead give X=11, Z=3.
            self.assertEqual(hood['matrix'][12:15], [10., 2., 2.])
            self.assertEqual(hood['matrix'][:3], [0., 0., -1.])

    def test_arm_uses_own_authored_pose_and_cached_basis(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            index = fixture(root)
            arm_path = add_part(root, index, 'armfl')
            original = preview.Sources.model

            def own_arm(self, path):
                part = original(self, path)
                if path == arm_path:
                    part['skeleton'][0].update(pose_bone('arm_native', (-.4, .6, -1.2), quarter_turn=True))
                return part
            with patch.object(preview.Sources, 'model', own_arm):
                data, record = preview.build_car(root, 'vp_test_car_00', index)
            doc, _ = read_glb(data)
            arm = next(node for node in doc['nodes'] if node['name'].startswith(arm_path + '@'))
            self.assertEqual(arm['matrix'][12:15], [-.4, .6, -1.2])
            self.assertEqual(arm['matrix'][:3], [0., 0., -1.])
            self.assertNotEqual(arm['matrix'][12:15], [-.75, .3, -1.])
            self.assertIn(arm_path, [row['file'] for row in record['sources']])

    def test_stock_selection_and_raised_roof(self):
        paths = ['p/body_lod_0.xrsc', 'p/hood0_lod_0.xrsc', 'p/hood1_lod_0.xrsc',
                 'p/door_l_wide0_lod_0.xrsc', 'p/widebody0_lod_0.xrsc',
                 'p/conv_top0_lod_0.xrsc', 'p/conv_topup0_lod_0.xrsc', 'p/conv_topdown0_lod_0.xrsc',
                 'p/occluder_0_lod_0.xrsc', 'p/hood0_lod_1.xrsc']
        chosen, omitted = preview.select_parts(paths)
        self.assertEqual([s for s, _ in chosen], ['body', 'conv_topup', 'hood'])
        self.assertEqual(len(omitted), 5)
        with self.assertRaisesRegex(preview.PreviewError, 'one LOD-0 body'):
            preview.select_parts(paths[1:])

    def test_attachment_prefers_real_body_bone_and_hinge(self):
        bones = {'hd': {'model': (1., 2., 3.)}, 'door_l': {'model': (0., 0., 0.)},
                 'door_l_regular_anim': {'model': (-1., 1., 0.)}}
        part = {'skeleton': [{'name': 'door_l_stk'}]}
        self.assertEqual(preview.attachment('door_l', part, bones), ('door_l_regular_anim', (-1., 1., 0.)))
        self.assertEqual(preview.attachment('hood', {'skeleton': []}, bones), ('hd', (1., 2., 3.)))
        # S600 DUB uses trunk_wide with a tk_wide resource root; its body
        # attachment keeps the regular tk vocabulary.
        self.assertEqual(preview.attachment('trunk_wide', {'skeleton': [{'name': 'tk_wide'}]},
                                            {'tk': {'model': (0., 1., 2.)}}), ('tk', (0., 1., 2.)))
        with self.assertRaisesRegex(preview.PreviewError, 'unmapped stock attachment'):
            preview.attachment('mystery', part, bones)

    def test_native_resources_to_glb_sources_offsets_mesh_reuse(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            fixture(root)
            data, record = preview.build_car(root, 'vp_test_car_00')
            doc, binary = read_glb(data)
            self.assertEqual(doc['asset']['generator'], preview.PROFILE)
            self.assertEqual(doc['extras']['car'], 'vp_test_car_00')
            self.assertEqual(record['triangles'], 15)
            self.assertEqual(len(record['wheels']), 12)
            self.assertEqual(len(doc['meshes']), 6)
            self.assertEqual(len(doc['nodes']), 15)
            self.assertTrue(binary)
            self.assertEqual(next(p for p in record['parts'] if p['slot'] == 'hood')['translation'], [0., 1., -1.])
            self.assertEqual(next(p for p in record['parts'] if p['slot'] == 'door_l')['translation'], [-1., 1., 0.])
            self.assertTrue(record['texture_pack'].endswith('.xtl'))
            self.assertEqual(record['glb_sha256'], preview.sha(data))
            self.assertTrue(all(row['sha256'] == preview.sha((root / row['file']).read_bytes()) for row in record['sources']))
            self.assertTrue(all('wide' not in p['file'] for p in record['parts']))
            left = next(w for w in record['wheels'] if w['bone'] == 'axl_0')
            self.assertIsNone(left['rotation'])
            self.assertEqual(next(w for w in record['wheels'] if w['bone'] == 'axl_1')['rotation'], [0., 1., 0., 0.])
            self.assertAlmostEqual(left['scale'][1], 2 ** .5 * .3, places=6)
            self.assertAlmostEqual(left['scale'][0], .39, places=6)
            second, again = preview.build_car(root, 'vp_test_car_00')
            self.assertEqual(data, second)
            self.assertEqual(record, again)

    def test_hash_named_rim_bike_and_ambient(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            fixture(root, bike=True, brakes=False, hashed=True)
            _, record = preview.build_car(root, 'vp_test_car_00')
            self.assertEqual(len(record['wheels']), 4)
            self.assertTrue(any('/0x' in w['file'] for w in record['wheels']))
            self.assertTrue(all(w['rotation'] is None for w in record['wheels']))
            self.assertEqual(preview.stock_rim_name('vpd_am_db9_08'), 'whld_stk_am_db9_08')
            self.assertEqual(preview.stock_rim_name('vp_mbz_s600_07_dub'), 'whl_stk_mbz_s600')
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            fixture(root, code='va_test_car_00')
            _, record = preview.build_car(root, 'va_test_car_00')
            self.assertEqual(record['wheels'], [])

    def test_tampered_source_duplicate_index_and_unsafe_paths(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            index = fixture(root)
            src = preview.Sources(root)
            with self.assertRaisesRegex(preview.PreviewError, 'missing from extraction'):
                src.read('unknown')
            bad = copy.deepcopy(index)
            bad['files'].append(bad['files'][0])
            with self.assertRaisesRegex(preview.PreviewError, 'duplicate extraction'):
                preview.Sources(root, bad)
            bad = {'files': [{'file': '../escape', 'bytes': 1, 'sha256': 'x'}]}
            with self.assertRaisesRegex(preview.PreviewError, 'unsafe source path'):
                preview.Sources(root, bad).read('../escape')
            target = root / index['files'][0]['file']
            target.write_bytes(target.read_bytes() + b'corrupt')
            with self.assertRaisesRegex(preview.PreviewError, 'source hash/size differs'):
                preview.build_car(root, 'vp_test_car_00')
            with self.assertRaisesRegex(preview.PreviewError, 'unsafe/unknown'):
                preview.build_car(root, '../escape')

    def test_missing_rim_and_pack_ambiguity_fail(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            index = fixture(root)
            index['files'] = [r for r in index['files'] if '/rims/' not in r['file']]
            with self.assertRaisesRegex(preview.PreviewError, 'stock rim missing'):
                preview.build_car(root, 'vp_test_car_00', index)
            src = preview.Sources(root)
            with self.assertRaisesRegex(preview.PreviewError, 'ambiguous/missing texture pack'):
                preview.pack_for(src, 'vp_test_car_00/resources/vehicle/vp_test_car_00')

    def test_geometry_shader_skinning_and_index_controls(self):
        data, virtual, physical, _ = model_resource()
        part = mcla_model.decode(data, virtual, physical)
        pdata, pv, pp, _ = build_pack()
        pack, reader = mcla_texture.decode(pdata, pv, pp, 83)
        with self.assertRaisesRegex(preview.PreviewError, 'shader outside'):
            preview.mesh(Builder(), part, pack, reader, 'bad')
        part['models'][0]['skinned'] = True
        with self.assertRaisesRegex(preview.PreviewError, 'requires skinning'):
            preview.mesh(Builder(), part, pack, reader, 'bad')
        part['models'][0]['skinned'] = False
        for g in part['models'][0]['geometries']:
            g['shader'] = 0
        part['models'][0]['geometries'][0]['indices'][0] = 999
        with self.assertRaisesRegex(preview.PreviewError, 'index outside'):
            preview.mesh(Builder(), part, pack, reader, 'bad')
        part['models'][0]['geometries'][0]['indices'] = []
        with self.assertRaisesRegex(preview.PreviewError, 'empty/non-triangular'):
            preview.mesh(Builder(), part, pack, reader, 'bad')

    def test_exhaust_anchors_selected_bumper_and_no_anchor_omission(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            index = fixture(root)
            prefix = 'vp_test_car_00/resources/vehicle/vp_test_car_00/'
            # Use a genuine synthetic source for both parts, and alter decoded bones only
            # to exercise the assembly seam rather than resource decoding again.
            src = next(r for r in index['files'] if r['file'].endswith('/hood0_lod_0.xrsc'))
            for name in ('bumper_r0_lod_0.xrsc', 'exh_pipe0_lod_0.xrsc'):
                path = prefix + name
                (root / path).write_bytes((root / src['file']).read_bytes())
                index['files'].append(dict(src, file=path))
            original = preview.Sources.model

            def with_anchors(self, path):
                part = original(self, path)
                if path.endswith('/body_lod_0.xrsc') and not path.startswith('shared/'):
                    # Body labels are a different namespace from bumper anchors.
                    # Repeated exst0 entries are irrelevant to the bumper binding.
                    part['skeleton'] += [dict(pose_bone('exst0', (9., 9., 9.)), parent=0)] * 2
                    part['skeleton'].append(dict(pose_bone('ext_secondary', (8., 8., 8.)), parent=0))
                if path.endswith('bumper_r0_lod_0.xrsc'):
                    part['skeleton'] = [pose_bone('rear_stk', (0., 0., 0.)),
                                        pose_bone('exst0', (-.5, .1, .2), quarter_turn=True),
                                        pose_bone('ext_secondary', (.5, .1, .2), quarter_turn=True)]
                return part
            with patch.object(preview.Sources, 'model', with_anchors):
                glb, record = preview.build_car(root, 'vp_test_car_00', index)
            exhaust = [p for p in record['parts'] if p['slot'] == 'exh_pipe']
            self.assertEqual([p['translation'] for p in exhaust], [[-.5, .6, 2.2], [.5, .6, 2.2]])
            self.assertEqual([p['attachment_bone_index'] for p in exhaust], [1, 2])
            self.assertEqual([p['attachment_native_name'] for p in exhaust], ['exst0', 'ext_secondary'])
            self.assertEqual([p['attachment_source'] for p in exhaust], [prefix + 'bumper_r0_lod_0.xrsc'] * 2)
            doc, _ = read_glb(glb)
            exhaust_nodes = [node for node in doc['nodes'] if '/exh_pipe0_lod_0.xrsc@' in node['name']]
            self.assertEqual(len(exhaust_nodes), 2)
            self.assertTrue(all(node['matrix'][:3] == [0., 0., -1.] for node in exhaust_nodes))
            _, record = preview.build_car(root, 'vp_test_car_00', index)
            self.assertIn(prefix + 'exh_pipe0_lod_0.xrsc', record['omitted'])
            index['files'] = [r for r in index['files'] if not r['file'].endswith('bumper_r0_lod_0.xrsc')]
            _, record = preview.build_car(root, 'vp_test_car_00', index)
            self.assertIn(prefix + 'exh_pipe0_lod_0.xrsc', record['omitted'])

    def test_axle_height_type_and_symlink_controls(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            index = fixture(root)
            original = preview.Sources.model

            def bad_axle(self, path):
                part = original(self, path)
                for bone in part['skeleton']:
                    if bone['name'] == 'axl_0':
                        bone['model'] = (0., -1., 0.)
                return part
            with patch.object(preview.Sources, 'model', bad_axle):
                with self.assertRaisesRegex(preview.PreviewError, 'invalid axle height'):
                    preview.build_car(root, 'vp_test_car_00', index)
            src = next(r for r in index['files'] if r['file'].endswith('.xtl'))
            with self.assertRaisesRegex(preview.PreviewError, 'wrong type'):
                preview.Sources(root).model(src['file'])
            link = root / 'linked'
            link.symlink_to(root.parent)
            bad = {'files': [{'file': 'linked/escape', 'bytes': 1, 'sha256': 'x'}]}
            with self.assertRaisesRegex(preview.PreviewError, 'escapes extraction'):
                preview.Sources(root, bad).read('linked/escape')

    def test_material_fallback_and_normals_without_source_channels(self):
        data, virtual, physical, _ = model_resource()
        part = mcla_model.decode(data, virtual, physical)
        pdata, pv, pp, _ = build_pack()
        pack, reader = mcla_texture.decode(pdata, pv, pp, 83)
        for g in part['models'][0]['geometries']:
            g['shader'] = 0
            del g['normal']
            del g['texcoord0']
        shader = pack['shader_group']['shaders'][0]
        shader['params'] = []
        builder = Builder()
        preview.mesh(builder, part, pack, reader, 'fallback')
        self.assertEqual(builder.doc['materials'][0]['pbrMetallicRoughness']['baseColorFactor'], [.8, .8, .8, 1.])
        self.assertNotIn('textures', builder.doc)
        self.assertIn('NORMAL', builder.doc['meshes'][0]['primitives'][0]['attributes'])
        self.assertNotIn('TEXCOORD_0', builder.doc['meshes'][0]['primitives'][0]['attributes'])
        self.assertEqual(preview.attachment('hood', {'skeleton': [{'name': 'hd'}]}, {'hd': {'model': (0., 1., 2.)}}),
                         ('hd', (0., 1., 2.)))

    def test_tire_bead_radial_extent_controls(self):
        part = {'models': [{'geometries': [{'position': [(0., .4, 0.), (0., 0., .5)]}]}]}
        self.assertAlmostEqual(preview.tire_bead_ratio(part), .8)
        part['models'][0]['geometries'][0]['position'] = [(0., 0., 0.)]
        with self.assertRaisesRegex(preview.PreviewError, 'invalid tire radial extent'):
            preview.tire_bead_ratio(part)
        part['models'][0]['geometries'][0]['position'] = [(0., .5, 0.)]
        with self.assertRaisesRegex(preview.PreviewError, 'no radial thickness'):
            preview.tire_bead_ratio(part)

    def test_player_axle_set_rejects_absent_partial_mixed_and_unknown(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            index = fixture(root)
            original = preview.Sources.model
            for mode in ('absent', 'partial', 'mixed', 'unknown'):
                def invalid_axes(self, path):
                    part = original(self, path)
                    if path.endswith('/vehicle/vp_test_car_00/body_lod_0.xrsc'):
                        if mode == 'absent':
                            part['skeleton'] = [b for b in part['skeleton'] if not b['name'].startswith('axl_')]
                        elif mode == 'partial':
                            part['skeleton'] = [b for b in part['skeleton'] if b['name'] != 'axl_3']
                        else:
                            part['skeleton'].append({'name': 'axl_front' if mode == 'mixed' else 'axl_4',
                                                     'model': (0., .3, 0.)})
                    return part
                with self.subTest(mode=mode), patch.object(preview.Sources, 'model', invalid_axes):
                    with self.assertRaisesRegex(preview.PreviewError, 'player wheel axle set incomplete, mixed or unsupported'):
                        preview.build_car(root, 'vp_test_car_00', index)

    def test_player_bus_exact_native_donor_join_and_failure_controls(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            player = fixture(root, code='vp_citybus_07')
            donor = fixture(root, code='va_citybus_07')
            files = {row['file']: row for row in player['files'] + donor['files']}
            index = {'files': list(files.values()), 'vehicles': player['vehicles'] + donor['vehicles']}
            original = preview.Sources.model
            donor_path = 'va_citybus_07/resources/vehicle/va_citybus_07/body_lod_0.xrsc'

            def native_bus(self, path):
                part = original(self, path)
                if path.endswith('/body_lod_0.xrsc') and '/vehicle/' in path:
                    wheels = [pose_bone('whl_%d' % i, (float(i), .4, float(i % 2))) for i in range(4)]
                    start = len(part['skeleton'])
                    part['skeleton'].extend(wheels)
                    if path == donor_path:
                        template = part['models'][0]
                        for i in range(8):
                            model = copy.deepcopy(template)
                            model['bone_index'] = start + i // 2
                            part['models'].append(model)
                return part

            with patch.object(preview.Sources, 'model', native_bus):
                data, record = preview.build_car(root, 'vp_citybus_07', index)
            doc, _ = read_glb(data)
            wheel_nodes = [node for node in doc['nodes'] if node['name'].startswith(donor_path + '@wheel_family')]
            self.assertEqual(len(wheel_nodes), 8)
            self.assertEqual([node['matrix'][12:15] for node in wheel_nodes],
                             [[float(i // 2), .4, float((i // 2) % 2)] for i in range(8)])
            self.assertEqual(record['wheels'], [])
            embedded = next(p for p in record['parts'] if p['slot'] == 'embedded_wheels')
            self.assertEqual((embedded['file'], embedded['triangles']), (donor_path, 8))
            self.assertIn(donor_path, [row['file'] for row in record['sources']])
            self.assertIn('va_citybus_07/resources/vehicle/va_citybus_07/va_citybus_07.xtl',
                          [row['file'] for row in record['sources']])
            for mode in ('pose', 'count'):
                def invalid_donor(self, path):
                    part = native_bus(self, path)
                    if path == donor_path:
                        if mode == 'count':
                            part['models'].pop()
                        else:
                            bone = next(b for b in part['skeleton'] if b['name'] == 'whl_0')
                            bone.update(pose_bone('whl_0', (99., .4, 0.)))
                    return part
                with self.subTest(mode=mode), patch.object(preview.Sources, 'model', invalid_donor):
                    with self.assertRaisesRegex(preview.PreviewError, 'donor wheel pose differs' if mode == 'pose'
                                                else 'donor wheel-model coverage differs'):
                        preview.build_car(root, 'vp_citybus_07', index)


if __name__ == '__main__':
    unittest.main(verbosity=2)
