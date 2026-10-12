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
from bake_models import read_glb
from gt4_glb import Builder
from mcla_rpf import jenkins
from test_mcla_lzx import Encoder, resource
from test_mcla_model import build as model_resource
from test_mcla_texture import build_pack
from unittest.mock import patch


def wrapped(data, kind):
    encoder = Encoder()
    # A resource can contain more than one frame.
    for start in range(0, len(data), 32768):
        encoder.stored(data[start:start + 32768])
        encoder.close()
    return resource(encoder.body(), len(data), kind)


def fixture(root, code='vp_test_car_00', bike=False, brakes=True, hashed=False):
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
        data, virtual, physical, at = model_resource([(points, [0, 1, 2])], bones)
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
        model(shared + '/body_lod_0.xrsc', [('root', -1, (0., 0., 0.), (0., 0., 0.))])
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


class Assembly(unittest.TestCase):
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
            self.assertEqual(left['rotation'], [0., 1., 0., 0.])
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
                if path.endswith('bumper_r0_lod_0.xrsc'):
                    part['skeleton'] = [{'name': 'rear_stk', 'model': (0., 0., 0.)},
                                        {'name': 'exstPrimary', 'model': (-.5, .1, .2)},
                                        {'name': 'exstSecondary', 'model': (.5, .1, .2)}]
                return part
            with patch.object(preview.Sources, 'model', with_anchors):
                _, record = preview.build_car(root, 'vp_test_car_00', index)
            exhaust = [p for p in record['parts'] if p['slot'] == 'exh_pipe']
            self.assertEqual([p['translation'] for p in exhaust], [[-.5, .6, 2.2], [.5, .6, 2.2]])
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
        # The player bus owns embedded wheels and is an explicit exception, like ambient cars.
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            fixture(root, code='vp_citybus_07')
            _, record = preview.build_car(root, 'vp_citybus_07')
            self.assertEqual(record['wheels'], [])


if __name__ == '__main__':
    unittest.main(verbosity=2)
