"""Exercise preview topology with source-independent geometry and malformed inputs."""
import copy
import math
import struct
import unittest
import mc3_model
from mc3_model import strip_triangles, build_glb, wheel_slots, native_rest_frames, rotated_point
from bake_models import read_glb, accessor


class PreviewGeometryTest(unittest.TestCase):
    def test_original_vif_packet_bytes_and_ppf_coordinates_are_retained(self):
        packet = bytes(range(64))
        draw = {'material': 0, 'packet_offset': 128, 'ppf_packet_offset': 8192,
                'packet_bytes': len(packet), 'native_vif_packet': packet,
                'native_vif_batch_offsets': [16],
                'batches': [{'positions': [(0, 0, 0), (1, 0, 0), (0, 1, 0)], 'packet_offset': 144}]}
        part = {'name': 'source.mesh', 'bone': 0,
                'mesh': {'source': {'sha256': 'a'*64}, 'draws': [draw, copy.deepcopy(draw)]}}
        materials = [{'shader_category': 'unmapped', 'base_color': [1]*4, 'alpha_mode': 'OPAQUE'}]
        before = copy.deepcopy(part)
        doc, binary = read_glb(build_glb('vp_test', [part], materials, [])[0])
        self.assertEqual(doc['extras']['nativeVifPackets'], 'mc3-original-vif-packets-v1')
        first, second = [p['extras']['native_vif'] for p in doc['meshes'][0]['primitives']]
        self.assertEqual(first, second)
        self.assertEqual(first['source_carrier_sha256'], 'a'*64)
        self.assertEqual(first['source_packet_offset'], 8192)
        self.assertEqual(first['batch_offsets'], [16])
        view = doc['bufferViews'][first['packet']['bufferView']]
        self.assertEqual(binary[view['byteOffset']:view['byteOffset']+view['byteLength']], packet)
        self.assertEqual(part, before)
        rebased = mc3_model._remap_mesh(part['mesh'], 0, 8064)
        rebased_doc, _ = read_glb(build_glb('vp_test', [{**part, 'mesh': rebased}], materials, [])[0])
        self.assertEqual(rebased_doc['meshes'][0]['primitives'][0]['extras']['native_vif'], first)
        for key, value in [('packet_bytes', 63), ('native_vif_packet', b''), ('ppf_packet_offset', -1)]:
            altered = copy.deepcopy(part);altered['mesh']['draws'][0][key] = value
            with self.assertRaisesRegex(ValueError, 'VIF packet source binding'):
                build_glb('vp_test', [altered], materials, [])

    def test_native_tire_back_cap_cannot_compete_with_rim_inner_face(self):
        # Native tires and rims can share an axial plane with opposite winding.
        # Drawing both sides of the tire makes its inward cap z-fight with the
        # visible rim inner face. Keep both native surfaces; restore native cull.
        points = [(0.25, 0, 0), (0.25, 1, 0), (0.25, 0, 1)]
        parts = []
        for material, name, positions in ((0, 'rim', list(reversed(points))),
                                          (1, 'tire', points)):
            parts.append({'name': name, 'bone': 0,
                          'provenance': {'nativeWheelComponent': name},
                          'mesh': {'source': {'sha256': 'a' * 64},
                                   'draws': [{'material': material, 'batches': [
                                       {'positions': positions, 'packet_offset': 128,
                                        'normals': [(-127/128, 7/128, 0)] * 3}]}]}})
        materials = [{'shader_category': 'textured', 'shader_template': template,
                      'base_color': [1, 1, 1, 1], 'alpha_mode': 'OPAQUE'}
                     for template in ('wheel_inner', 'tire', 'wheel_inner', 'tire_extra')]
        doc, binary = read_glb(build_glb('vp_test', parts, materials, [])[0])
        self.assertFalse(doc['materials'][1].get('doubleSided', False))
        self.assertFalse(doc['materials'][0]['doubleSided'])
        # Wheel provenance, rather than a rim-looking name, selects rim cull.
        self.assertTrue(doc['materials'][2]['doubleSided'])
        self.assertTrue(doc['materials'][3]['doubleSided'])
        self.assertEqual(len(doc['meshes']), 2)
        actual = [accessor(doc, binary, mesh['primitives'][0]['attributes']['POSITION'], 3, 5126)
                  for mesh in doc['meshes']]
        self.assertEqual(actual, [list(reversed(points)), points])
        rim, tire = [mesh['primitives'][0] for mesh in doc['meshes']]
        self.assertEqual(accessor(doc, binary, rim['attributes']['_MC3_NATIVE_NORMAL'], 3, 5126),
                         [(-127/128, 7/128, 0)] * 3)
        native = accessor(doc, binary, tire['attributes']['_MC3_NATIVE_NORMAL'], 3, 5126)
        self.assertEqual(native, [(-127/128, 7/128, 0)] * 3)

    def test_native_vertex_lanes_and_batch_context_survive_untextured_export(self):
        batch = {'positions': [(0, 0, 0), (1, 0, 0), (0, 1, 0)], 'packet_offset': 128,
                 'normals': [(1/128, 127/128, 0)] * 3,
                 'uvs': [(-1, 2), (3, 4), (5, 6)],
                 'uv_integers': [(-4096, 8192, 23, -24), (12288, 16384, 25, -26), (20480, 24576, 27, -28)],
                 'color_integers': [(255, 128, 0, -1)] * 3,
                 'header_words': [0, 3], 'scale': 1/1024}
        material = {'shader_category': 'unmapped', 'base_color': [.65]*3+[1], 'alpha_mode': 'OPAQUE',
                    'native_material': {'root': {'passes': [{'program': 7, 'source_words': [1, 2]}]}}}
        part = {'name': 'body', 'bone': 0, 'mesh': {'source': {'sha256': 'a'*64},
                'draws': [{'material': 0, 'batches': [batch]}]}}
        before = copy.deepcopy(part)
        skeleton = {'source_sha256': 'b'*64, 'offset': 128, 'header_words_raw': [1, 2, 3, 4],
                    'bones': [{'parent': None, 'child': 1, 'sibling': None},
                              {'parent': 0, 'child': None, 'sibling': None}]}
        doc, binary = read_glb(build_glb('vp_test', [part], [material], [], skeleton=skeleton)[0])
        self.assertEqual(doc['extras']['nativeSkeleton'], skeleton)
        primitive = doc['meshes'][0]['primitives'][0]
        for name, key, width in [('_MC3_NATIVE_NORMAL', 'normals', 3), ('_MC3_NATIVE_COLOR', 'color_integers', 4),
                                 ('_MC3_NATIVE_UV', 'uv_integers', 4), ('TEXCOORD_0', 'uvs', 2), ('POSITION', 'positions', 3)]:
            a = doc['accessors'][primitive['attributes'][name]]
            offset = doc['bufferViews'][a['bufferView']]['byteOffset']
            self.assertEqual(a['type'], {2: 'VEC2', 3: 'VEC3', 4: 'VEC4'}[width])
            actual = [struct.unpack_from('<'+'f'*width, binary, offset+i*width*4) for i in range(a['count'])]
            self.assertEqual(actual, batch[key])
        self.assertEqual(doc['extras']['nativeVertexInputs'], 'mc3-vif-vertex-inputs-v1')
        self.assertEqual(primitive['extras']['native_batches'], [{'vertex_start': 0, 'vertex_count': 3,
            'packet_offset': 128, 'header_words': [0, 3], 'position_scale': 1/1024}])
        self.assertEqual(doc['materials'][0]['extras']['native_material'], material['native_material'])
        self.assertEqual(part, before)
        for invalid in ([[(0, 0, 0, 16777217)] * 3], [[(0, 0, 0, .5)] * 3], [[(0, 0, 0, 1)]]):
            changed = copy.deepcopy(part)
            changed['mesh']['draws'][0]['batches'][0]['color_integers'] = invalid[0]
            with self.assertRaisesRegex(ValueError, 'cannot be retained exactly'):
                build_glb('vp_test', [changed], [material], [])
        changed = copy.deepcopy(part)
        second = copy.deepcopy(batch)
        second['uv_integers'] = [row[:2] for row in second['uv_integers']]
        changed['mesh']['draws'][0]['batches'].append(second)
        with self.assertRaisesRegex(ValueError, 'UV width differs'):
            build_glb('vp_test', [changed], [material], [])
        del second['uv_integers']
        with self.assertRaisesRegex(ValueError, 'attribute coverage differs'):
            build_glb('vp_test', [changed], [material], [])

    def test_native_tire_rejects_missing_mismatched_or_nonfinite_normals(self):
        material = {'shader_category': 'textured', 'shader_template': 'tire',
                    'base_color': [1, 1, 1, 1], 'alpha_mode': 'OPAQUE'}
        for normals in (None, [(1, 0, 0)], [(math.nan, 0, 0)] * 3):
            with self.subTest(normals=normals):
                batch = {'positions': [(0, 0, 0), (1, 0, 0), (0, 1, 0)],
                         'packet_offset': 128}
                if normals is not None:
                    batch['normals'] = normals
                part = {'name': 'tire', 'bone': 0,
                        'mesh': {'source': {'sha256': 'a' * 64},
                                 'draws': [{'material': 0, 'batches': [batch]}]}}
                with self.assertRaisesRegex(ValueError, 'one finite normal per vertex'):
                    build_glb('vp_test', [part], [material], [])

    def test_native_shadow_effect_is_retained_without_changing_default_scene(self):
        batch = {'positions': [(0, 0, 0), (1, 0, 0), (0, 1, 0)], 'packet_offset': 128,
                 'position_integers': [(0, 0, 0), (1024, 0, 0), (0, 1024, 0)],
                 'normals': [(0, 0, 127/128)] * 3, 'color_integers': [(255, 128, 0, -1)] * 3,
                 'uvs': [(0, 0), (1, 0), (0, 1)], 'uv_integers': [(0, 0), (4096, 0), (0, 4096)],
                 'scale': 1/1024, 'header_words': [0x3a800000, 3]}
        part = {'name': 'body', 'bone': 0, 'mesh': {'source': {'sha256': 'a'*64},
                'draws': [{'material': 0, 'batches': [batch]}]}}
        material = {'shader_category': 'unmapped', 'base_color': [1]*4, 'alpha_mode': 'OPAQUE'}
        baseline, old_binary = read_glb(build_glb('vp_test', [part], [material], [])[0])
        effect = {**part, 'name': 'original-effect', 'translation': [1000, -10, 0],
                  'native_effect': {'kind': 'drop_shadow', 'source_materials': [0]}}
        doc, binary = read_glb(build_glb('vp_test', [part, effect], [material], [])[0])
        self.assertEqual(doc['scenes'], baseline['scenes'])
        self.assertEqual(doc['nodes'][0], baseline['nodes'][0])
        self.assertEqual(doc['extras']['records'], baseline['extras']['records'])
        dormant = doc['extras']['nativeEffects'][0]
        self.assertEqual((dormant['node'], dormant['mesh'], dormant['runtimePending']), (1, 1, True))
        self.assertEqual(doc['nodes'][1]['translation'], [1000, -10, 0])
        self.assertEqual(doc['nodes'][1]['extras']['nativeBone'], 0)
        for name in ['POSITION', 'NORMAL', '_MC3_NATIVE_NORMAL', '_MC3_NATIVE_COLOR', '_MC3_NATIVE_UV', 'TEXCOORD_0']:
            payloads = []
            for mesh in doc['meshes']:
                a = doc['accessors'][mesh['primitives'][0]['attributes'][name]]
                view = doc['bufferViews'][a['bufferView']]
                payloads.append(binary[view['byteOffset']:view['byteOffset']+view['byteLength']])
            self.assertEqual(payloads[0], payloads[1], name)
        self.assertEqual(doc['meshes'][1]['primitives'][0]['extras']['native_batches'][0]['position_integers'],
                         [list(row) for row in batch['position_integers']])
        self.assertEqual(accessor(doc, binary, doc['meshes'][0]['primitives'][0]['attributes']['POSITION'], 3, 5126),
                         accessor(baseline, old_binary, baseline['meshes'][0]['primitives'][0]['attributes']['POSITION'], 3, 5126))
        invalid = copy.deepcopy(effect)
        del invalid['mesh']['draws'][0]['batches'][0]['position_integers']
        with self.assertRaisesRegex(ValueError, 'original integer position lanes'):
            build_glb('vp_test', [part, invalid], [material], [])

    def test_raw_position_lanes_do_not_replace_edited_display_rest(self):
        raw = [(127, -3, 4), (2048, 17, -15), (-4096, 31, 7)]
        display = [(0., 0., 0.), (2., 0., 0.), (0., 2., 0.)]
        batch = {'positions': display, 'position_integers': raw, 'packet_offset': 128,
                 'normals': [(0, 127/128, 0)]*3, 'color_integers': [(128, 128, 128, -1)]*3,
                 'uvs': [(0, 0)]*3, 'uv_integers': [(0, 0)]*3,
                 'header_words': [0x39800000, 3], 'scale': 1/4096}
        part = {'name': 'body', 'bone': 0, 'mesh': {'source': {'sha256': 'a'*64},
                'draws': [{'material': 0, 'batches': [batch]}]}}
        material = {'shader_category': 'unmapped', 'base_color': [1]*4, 'alpha_mode': 'OPAQUE'}
        doc, binary = read_glb(build_glb('vp_test', [part], [material], [])[0])
        primitive = doc['meshes'][0]['primitives'][0]
        self.assertEqual(accessor(doc, binary, primitive['attributes']['POSITION'], 3, 5126), display)
        self.assertEqual(accessor(doc, binary, primitive['attributes']['_MC3_NATIVE_POSITION'], 3, 5126), raw)
        self.assertEqual(doc['extras']['nativePositionInputs'], 'mc3-vif-integer-position-v1')
        self.assertEqual(primitive['extras']['native_batches'][0]['position_scale_word'], 0x39800000)
        for key, value, error in [('position_integers', [(16777217, 0, 0)]*3, 'cannot be retained exactly'),
                                  ('position_integers', [(0, 0, 0)], 'cannot be retained exactly'),
                                  ('header_words', [0, 3], 'scale word differs')]:
            invalid = copy.deepcopy(part)
            invalid['mesh']['draws'][0]['batches'][0][key] = value
            with self.assertRaisesRegex(ValueError, error):
                build_glb('vp_test', [invalid], [material], [])

    def test_remapped_mesh_metadata_is_independent_and_geometry_is_read_only(self):
        batch = {'positions': [(0, 0, 0), (1, 0, 0), (0, 1, 0)],
                 'uvs': [(0, 0), (1, 0), (0, 1)], 'adc': [False] * 3, 'packet_offset': 128}
        mesh = {'source': {'sha256': 'a' * 64}, 'draws': [{'material': 2, 'batches': [batch]}]}
        before = copy.deepcopy(mesh)
        first = mc3_model._remap_mesh(mesh, 3, 4096)
        second = mc3_model._remap_mesh(mesh, 7, 8192)
        stock = mc3_model._remap_mesh(mesh, 5)
        for remapped, material, offset in ((first, 5, 4224), (second, 9, 8320), (stock, 7, 128)):
            draw = remapped['draws'][0]
            self.assertEqual((draw['material'], draw['native_material_index']), (material, 2))
            self.assertEqual(draw['batches'][0]['packet_offset'], offset)
            materials = [{'shader_category': 'unmapped', 'base_color': [.65]*3+[1],
                          'alpha_mode': 'OPAQUE'} for _ in range(material + 1)]
            reference = copy.deepcopy(mesh)
            reference['draws'][0].update(material=material, native_material_index=2)
            reference['draws'][0]['batches'][0]['packet_offset'] = offset
            part = {'name': 'wheel', 'bone': 0}
            self.assertEqual(build_glb('vp_test', [{**part, 'mesh': remapped}], materials, []),
                             build_glb('vp_test', [{**part, 'mesh': reference}], materials, []))
        self.assertEqual(mesh, before)  # Both metadata rebasing and GLB building leave the input intact.
        first['draws'][0]['material'] = 100
        first['draws'][0]['batches'][0]['packet_offset'] = 100
        self.assertEqual(mesh, before)
        self.assertEqual(second['draws'][0]['batches'][0]['packet_offset'], 8320)

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

    def test_native_material_tables_are_deduplicated_and_preserve_original_words(self):
        table = {'schema': 1, 'source_carrier_sha256': 'b'*64, 'collection_offset': 160,
                 'inputs': [{'index': 0, 'name': 'raw-input', 'word': 0xffffffff,
                             'source_offset': 256, 'name_offset': 272}], 'claim_limits': ['source defaults only']}
        material = {'shader_category': 'unmapped', 'base_color': [1]*4, 'alpha_mode': 'OPAQUE',
                    'native_input_table': table}
        batch = {'positions': [(0, 0, 0), (1, 0, 0), (0, 1, 0)], 'packet_offset': 128}
        part = {'name': 'native.mesh', 'bone': 0, 'mesh': {'source': {'sha256': 'a'*64},
                'draws': [{'material': 0, 'batches': [batch]}]}}
        before = copy.deepcopy(material)
        doc, _ = read_glb(build_glb('vp_test', [part], [material, copy.deepcopy(material)], [])[0])
        key = 'b'*64+':160'
        self.assertEqual(doc['extras']['nativeMaterialInputs'], {key: table})
        self.assertEqual([m['extras']['native_input_key'] for m in doc['materials']], [key, key])
        self.assertTrue(all('native_input_table' not in m['extras'] for m in doc['materials']))
        self.assertEqual(material, before)
        invalid = copy.deepcopy(material)
        invalid['native_input_table']['inputs'][0]['word'] = 0
        with self.assertRaisesRegex(ValueError, 'table identity conflicts'):
            build_glb('vp_test', [part], [material, invalid], [])


if __name__ == '__main__':
    unittest.main(verbosity=2)
