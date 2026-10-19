"""Native customization vectors survive the actual preview export boundary."""
import copy
import hashlib
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from bake_models import ROOT, read_glb
from mc3_model import PROFILE, build_glb, preview_vehicle
from mc3_paint import add_paint_variants, read_native_appearance
from export_mc3_models import refresh_appearance


def source_fixture(root, rgb='0.1 0.2 0.3'):
    rows = []
    for ordinal, (name, text) in enumerate([
        ('vp_test.carcfg', 'type: a\nCarCfg {\n PaintType 0\n PaintPreset 7\n Vinyl 0\n}\n'),
        ('vp_test/default.mccarcustom', 'type: a\nmcCarCustom {\n m_paintColor1 '+rgb+'\n}\n'),
        ('paintjobs/paintjoblist.txt', 'Gloss 2\n{ red blue }\n')]):
        name = f'shared/assets/{ordinal:05d}/tune/vehicle/customdata/'+name
        path = root/name
        path.parent.mkdir(parents=True, exist_ok=True)
        data = text.encode()
        path.write_bytes(data)
        rows.append({'file': name, 'bytes': len(data), 'sha256': hashlib.sha256(data).hexdigest()})
    return {'files': rows, 'vehicles': [{'id': 'vp_test'}]}


def preview_fixture():
    materials = []
    for category in ('carpaint', 'colored_glass', 'lit_textured', 'composite_material_wrapper'):
        native = {'shader_category': category, 'shader_template': 'carpaint' if category == 'composite_material_wrapper'
                  else category, 'base_color': [.65, .65, .65, 1], 'alpha_mode': 'OPAQUE'}
        if category == 'composite_material_wrapper':
            native['composite_templates'] = ['carpaint', 'carbon_fiber']
        materials.append(native)
    parts = [{'name': 'body', 'bone': 0, 'mesh': {'source': {'sha256': 'a'*64}, 'draws': [
        {'material': i, 'batches': [{'positions': [(0, 0, 0), (1, 0, 0), (0, 1, 0)],
                                    'packet_offset': 128}]} for i in range(4)]}}]
    return build_glb('vp_test', parts, materials, [])[0]


class NativePaintTests(unittest.TestCase):
    def test_exact_namespace_and_raw_preset_preservation(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp).resolve()
            index = source_fixture(root)
            # A similarly named car cannot contribute an RGB choice.
            index['files'].append({**index['files'][1], 'file': index['files'][1]['file'].replace('vp_test/', 'vp_test_2/')})
            result = read_native_appearance(root, index, 'vp_test')
            self.assertEqual(result['choices'][0]['rgb'], [.1, .2, .3])
            self.assertEqual(result['configs'][0]['fields']['PaintPreset'], '7')
            self.assertEqual(result['preset_list']['groups'], [{'category': 'Gloss', 'names': ['red', 'blue']}])
            self.assertFalse(result['preset_list']['index_base_established'])

    def test_corrupt_hash_conflicting_copy_and_linked_source_rejected(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp).resolve()
            index = source_fixture(root)
            changed = copy.deepcopy(index)
            changed['files'][1]['sha256'] = '0'*64
            with self.assertRaisesRegex(ValueError, 'paint source hash/size differs'):
                read_native_appearance(root, changed, 'vp_test')
            source = index['files'][1]
            duplicate = root/source['file'].replace('/00001/', '/00009/')
            duplicate.parent.mkdir(parents=True)
            data = (root/source['file']).read_bytes().replace(b'0.1 0.2 0.3', b'0.7 0.8 0.9')
            duplicate.write_bytes(data)
            changed = copy.deepcopy(index)
            changed['files'].append({'file': duplicate.relative_to(root).as_posix(), 'bytes': len(data),
                                     'sha256': hashlib.sha256(data).hexdigest()})
            with self.assertRaisesRegex(ValueError, 'conflicting native paint source copies'):
                read_native_appearance(root, changed, 'vp_test')
            (root/source['file']).unlink()
            (root/source['file']).symlink_to(duplicate)
            with self.assertRaisesRegex(ValueError, 'symlink'):
                read_native_appearance(root, index, 'vp_test')

    def test_bad_rgb_duplicate_paint_fields_and_preset_counts_rejected(self):
        for value in ('NaN 0 0', 'inf 0 0', '-1 0 0', '1.1 0 0', '0 0', 'red 0 0',
                      '0 0 0\n m_paintColor1 1 1 1'):
            with self.subTest(value=value), tempfile.TemporaryDirectory() as temp:
                root = Path(temp).resolve()
                index = source_fixture(root, value)
                with self.assertRaisesRegex(ValueError, 'RGB vector|duplicate native paint field'):
                    read_native_appearance(root, index, 'vp_test')
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp).resolve()
            index = source_fixture(root)
            row = index['files'][2]
            data = (root/row['file']).read_bytes().replace(b'Gloss 2', b'Gloss 3')
            (root/row['file']).write_bytes(data)
            row.update(bytes=len(data), sha256=hashlib.sha256(data).hexdigest())
            with self.assertRaisesRegex(ValueError, 'invalid native paint preset list'):
                read_native_appearance(root, index, 'vp_test')

    def test_sparse_customization_has_no_invented_paint(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp).resolve()
            index = source_fixture(root)
            row = index['files'][1]
            data = b'type: a\nmcCarCustom {\n m_hasNeonGroundEffect 0\n}\n'
            (root/row['file']).write_bytes(data)
            row.update(bytes=len(data), sha256=hashlib.sha256(data).hexdigest())
            appearance = read_native_appearance(root, index, 'vp_test')
            self.assertEqual(appearance['choices'], [])
            doc, _ = read_glb(preview_fixture())
            before = copy.deepcopy(doc)
            add_paint_variants(doc, appearance)
            self.assertEqual(doc['materials'], before['materials'])
            self.assertNotIn('extensions', doc)

    def test_variants_preserve_base_materials_geometry_and_all_other_surfaces(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp).resolve()
            appearance = read_native_appearance(root, source_fixture(root), 'vp_test')
            doc, _ = read_glb(preview_fixture())
            before = copy.deepcopy(doc)
            add_paint_variants(doc, appearance)
            self.assertEqual(doc['materials'][:4], before['materials'])
            for key in ('nodes', 'accessors', 'bufferViews', 'buffers'):
                self.assertEqual(doc[key], before[key])
            primitives = doc['meshes'][0]['primitives']
            self.assertIn('extensions', primitives[0])
            for primitive, original in zip(primitives[1:], before['meshes'][0]['primitives'][1:]):
                self.assertEqual(primitive, original)
            self.assertEqual(doc['extras']['nativeAppearance']['unresolved_composite_materials'], [3])
            game = doc['extras']['gamePaint']
            self.assertEqual(game['schema'], 1)
            self.assertEqual(game['channels'], [{'id': 'body', 'name': 'Body paint', 'materials': [0]}])
            self.assertEqual(game['colors'][0]['rgb'], [.1, .2, .3])
            self.assertEqual(game['colors'][0]['name'], 'vp_test / default')
            self.assertIn('vp_test/default.mccarcustom:m_paintColor1', game['colors'][0]['source'])
            self.assertNotIn('finishes', game['channels'][0])
            with self.assertRaisesRegex(ValueError, 'already applied'):
                add_paint_variants(doc, appearance)

    def test_channels_survive_missing_colour_but_exclude_textured_blended_and_unused_paint(self):
        doc, _ = read_glb(preview_fixture())
        appearance = {'choices': [], 'configs': [], 'customizations': []}
        add_paint_variants(doc, appearance)
        self.assertEqual(doc['extras']['gamePaint']['channels'][0]['materials'], [0])
        self.assertEqual(doc['extras']['gamePaint']['colors'], [])
        for mutation in ('textured', 'blended', 'unused'):
            with self.subTest(mutation=mutation):
                doc, _ = read_glb(preview_fixture())
                if mutation == 'textured':
                    doc['materials'][0]['pbrMetallicRoughness']['baseColorTexture'] = {'index': 0}
                elif mutation == 'blended':
                    doc['materials'][0]['alphaMode'] = 'BLEND'
                else:
                    doc['meshes'][0]['primitives'].pop(0)
                add_paint_variants(doc, appearance)
                self.assertEqual(doc['extras']['gamePaint']['channels'], [])

    def test_appearance_only_export_preserves_binary_and_rejects_tampered_reference(self):
        with tempfile.TemporaryDirectory() as temp:
            base = Path(temp).resolve()
            source, reference, output = base/'source', base/'reference', base/'output'
            index = source_fixture(source)
            (source/'index.json').write_text(json.dumps(index))
            reference.mkdir()
            data = preview_fixture()
            (reference/'vp_test.glb').write_bytes(data)
            row = {'code': 'vp_test', 'file': 'vp_test.glb', 'bytes': len(data),
                   'sha256': hashlib.sha256(data).hexdigest(), 'source_profile': PROFILE,
                   'triangle_count': 4, 'claim_limits': []}
            (reference/'index.json').write_text(json.dumps({'cars': [row]}))
            self.assertEqual(refresh_appearance(source, reference, output), 1)
            before, binary = read_glb(data)
            after, actual = read_glb((output/'vp_test.glb').read_bytes())
            self.assertEqual(actual, binary)
            self.assertEqual(after['nodes'], before['nodes'])
            for primitive, original in zip(after['meshes'][0]['primitives'], before['meshes'][0]['primitives']):
                primitive.pop('extensions', None)
                self.assertEqual(primitive, original)
            result = json.loads((output/'index.json').read_text())['cars'][0]
            self.assertFalse(result['appearance_augmentation']['geometry_rederived'])
            self.assertEqual(after['extras']['gamePaint']['colors'][0]['rgb'], [.1, .2, .3])
            self.assertEqual(result['appearance_augmentation']['reference_sha256'], row['sha256'])
            with self.assertRaisesRegex(ValueError, 'must not exist'):
                refresh_appearance(source, reference, output)
            (reference/'vp_test.glb').write_bytes(data+b'changed')
            with self.assertRaisesRegex(ValueError, 'reference hash/size differs'):
                refresh_appearance(source, reference, base/'tampered')
            self.assertFalse((base/'tampered').exists())

    def test_native_corpus_coverage_and_explicit_choices(self):
        root = ROOT/'games/midnight-club-3-remix/cars'
        index = json.loads((root/'index.json').read_text())
        rows = [read_native_appearance(root, index, row['id']) for row in index['vehicles']]
        self.assertEqual(sum(len(row['configs']) for row in rows), 94)
        self.assertEqual(sum(len(row['customizations']) for row in rows), 84)
        self.assertEqual(sum(len(row['choices']) for row in rows), 40)
        self.assertEqual(sum(bool(row['choices']) for row in rows), 39)

    def test_native_corvette_customization_paints_body_and_trim_without_affecting_other_surfaces(self):
        root = ROOT/'games/midnight-club-3-remix/cars'
        index = json.loads((root/'index.json').read_text())
        row = next(v for v in index['vehicles'] if v['id'] == 'vp_corvettez06_03')
        manifest = json.loads((root/row['manifest']).read_text())
        # Wheel sizing does not participate in paint transfer and requires the
        # private executable. Geometry, materials and appearance use real inputs.
        with patch('mc3_model.attach_wheels', return_value=([], {})):
            data, _ = preview_vehicle(root, manifest, index, b'')
        doc, _ = read_glb(data)
        variants = doc.get('extensions', {}).get('KHR_materials_variants', {}).get('variants', [])
        self.assertTrue(variants, 'native m_paintColor1 is missing from exported choices')
        self.assertEqual(variants[0]['name'], 'Native customization: default')
        mapped = set()
        for mesh in doc['meshes']:
            for primitive in mesh['primitives']:
                source = doc['materials'][primitive['material']]
                mappings = primitive.get('extensions', {}).get('KHR_materials_variants', {}).get('mappings', [])
                if source['extras']['shader_category'] not in ('carpaint', 'aa_trim'):
                    self.assertEqual(mappings, [], source['name'])
                for mapping in mappings:
                    mapped.add(primitive['material'])
                    replacement = doc['materials'][mapping['material']]
                    self.assertEqual(replacement['pbrMetallicRoughness']['baseColorFactor'],
                                     [0.299999, 0.0, 0.0, 1.0])
        self.assertEqual(len(mapped), 2)
        self.assertFalse(doc['extras']['nativeAppearance']['factory_default_established'])
        self.assertEqual(doc['extras']['gamePaint']['channels'][0]['materials'], sorted(mapped))
        self.assertEqual(doc['extras']['gamePaint']['colors'][0]['rgb'], [0.299999, 0.0, 0.0])

    def test_runtime_paint_slot_followers_join_channel_and_receive_variants(self):
        materials = [
            # 0: primary carpaint with __metalflake__
            {'shader_category': 'carpaint', 'shader_template': 'carpaint', 'base_color': [.65, .65, .65, 1],
             'alpha_mode': 'OPAQUE', 'runtime_bound_textures': ['__metalflake__', '__decal__']},
            # 1: follower aa_trim with __metalflake__, opaque, untextured, used
            {'shader_category': 'aa_trim', 'shader_template': 'aa_trim', 'base_color': [.65, .65, .65, 1],
             'alpha_mode': 'OPAQUE', 'runtime_bound_textures': ['__metalflake__']},
            # 2: non-paint slot material (car_window)
            {'shader_category': 'car_window', 'shader_template': 'car_window', 'base_color': [.65, .65, .65, 1],
             'alpha_mode': 'OPAQUE', 'runtime_bound_textures': ['__envmap__']},
            # 3: composite wrapper
            {'shader_category': 'composite_material_wrapper', 'shader_template': 'carpaint',
             'composite_templates': ['carpaint'], 'base_color': [.65, .65, .65, 1], 'alpha_mode': 'OPAQUE',
             'runtime_bound_textures': ['__metalflake__']},
            # 4: unused aa_trim
            {'shader_category': 'aa_trim', 'shader_template': 'aa_trim', 'base_color': [.65, .65, .65, 1],
             'alpha_mode': 'OPAQUE', 'runtime_bound_textures': ['__metalflake__']},
            # 5: blended material with __metalflake__
            {'shader_category': 'car_decal', 'shader_template': 'car_decal', 'base_color': [.65, .65, .65, 1],
             'alpha_mode': 'BLEND', 'runtime_bound_textures': ['__metalflake__']},
        ]
        draws = [{'material': i, 'batches': [{'positions': [(0, 0, 0), (1, 0, 0), (0, 1, 0)], 'packet_offset': 128}]}
                 for i in (0, 1, 2, 3, 5)]  # Note: 4 is unused
        parts = [{'name': 'body', 'bone': 0, 'mesh': {'source': {'sha256': 'a'*64}, 'draws': draws}}]
        data, _ = build_glb('vp_test', parts, materials, [])
        doc, _ = read_glb(data)
        appearance = {
            'choices': [{'name': 'default', 'rgb': [.1, .2, .3],
                         'source': {'sources': [{'file': 'shared/assets/0/tune/vehicle/customdata/vp_test/default.mccarcustom',
                                                 'sha256': 'b'*64}], 'name': 'default'}}],
            'configs': [], 'customizations': []
        }
        add_paint_variants(doc, appearance)
        self.assertEqual(doc['extras']['gamePaint']['channels'][0]['materials'], [0, 1])
        primitives = doc['meshes'][0]['primitives']
        # Primitives using material 0 and 1 have variant mappings
        self.assertIn('KHR_materials_variants', primitives[0].get('extensions', {}))
        self.assertIn('KHR_materials_variants', primitives[1].get('extensions', {}))
        # Other primitives do not have variant mappings
        for p in primitives[2:]:
            self.assertNotIn('KHR_materials_variants', p.get('extensions', {}))

if __name__ == '__main__':
    unittest.main(verbosity=2)
