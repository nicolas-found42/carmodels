"""Actual Blender import/edit/export of car, shared-body and motorcycle previews."""
import hashlib
import json
from pathlib import Path
import sys
import tempfile
from unittest.mock import patch

import bpy

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
from bake_models import bake_car, read_glb
from build_dealership import build, check
from blender_gltf_compat import install
from mc3_model import build_glb


def custom_attribute_import():
    """Different widths catch ordering errors; same-width values catch swaps."""
    batch = {'positions': [(0, 0, 0), (1, 0, 0), (0, 1, 0)], 'packet_offset': 128,
             'header_words': [0x3a800000], 'scale': 1/1024,
             'position_integers': [(0, 0, 0), (1024, 0, 0), (0, 1024, 0)],
             'normals': [(1/128, 127/128, 0)] * 3,
             'color_integers': [(17, 29, 43, 128)] * 3,
             'uvs': [(0, 0), (1, 0), (0, 1)],
             'uv_integers': [(0, 0), (4096, 0), (0, 4096)]}
    part = {'name': 'attribute_probe', 'bone': 0,
            'mesh': {'source': {'sha256': 'a'*64}, 'draws': [{'material': 0, 'batches': [batch]}]}}
    material = {'shader_category': 'unmapped', 'base_color': [1]*4, 'alpha_mode': 'OPAQUE'}
    glb = build_glb('vp_probe', [part], [material], [])[0]
    with tempfile.TemporaryDirectory(prefix='mc3-attribute-import-') as temp:
        path = Path(temp) / 'probe.glb'
        path.write_bytes(glb)
        bpy.ops.wm.read_factory_settings(use_empty=True)
        bpy.ops.import_scene.gltf(filepath=str(path))
        data = next(obj.data for obj in bpy.context.scene.objects if obj.type == 'MESH')
        for name, key, field in [('_MC3_NATIVE_POSITION', 'position_integers', 'vector'),
                                 ('_MC3_NATIVE_NORMAL', 'normals', 'vector'),
                                 ('_MC3_NATIVE_COLOR', 'color_integers', 'color'),
                                 ('_MC3_NATIVE_UV', 'uv_integers', 'vector')]:
            actual = [tuple(getattr(row, field)) for row in data.attributes[name].data]
            assert sorted(actual) == sorted(batch[key]), f'Blender misassociated {name}'


def run():
    assert bpy.app.version == (4, 5, 14), 'Use pinned Blender 4.5.14'
    bpy.app.debug_value = 1  # glTF warning-level logs; keep the check's full receipt readable.
    with patch('blender_gltf_compat.inspect.getsource', return_value='unexpected importer revision'):
        try:
            install()
        except RuntimeError as error:
            assert 'Unrecognized Blender glTF importer' in str(error)
        else:
            raise AssertionError('Compatibility repair accepted an unpinned importer')
    install()
    install()  # Repeated use in an interactive Blender session is harmless.
    custom_attribute_import()
    catalog = json.loads((ROOT / 'dealership/dealership/catalog.json').read_text())
    models = list((ROOT / 'games/midnight-club-3-remix/recovered-models').glob('*.glb'))
    models += list((ROOT / 'dealership/dealership/models').glob('MC3_*.glb'))
    before = {p: hashlib.sha256(p.read_bytes()).hexdigest() for p in models}
    assert len(before) == 188, 'Expected 94 conversions and 94 independent working copies'
    receipts = []
    for code in ['vp_350z_04', 'vp_chrysler300c_05', 'vp_aprilia_mille_04']:
        entry = next(c for c in catalog if c.get('game') == 'midnight-club-3-remix' and c['sourceCode'] == code)
        source = ROOT / 'dealership/dealership/models' / (entry['code'] + '.glb')
        original = bake_car(entry['code'], source.read_bytes(), source_mode=False)
        source_doc = read_glb(source.read_bytes())[0]
        scene_index = source_doc.get('scene', 0)
        scene_name = source_doc['scenes'][scene_index].get('name') or f'Scene {scene_index}'
        bpy.ops.wm.read_factory_settings(use_empty=True)
        bpy.ops.import_scene.gltf(filepath=str(source), import_scene_as_collection=True,
                                  import_select_created_objects=False)
        collection = bpy.data.collections[scene_name] if len(source_doc['scenes']) > 1 else bpy.context.collection
        # Blender also links its excluded "Orphan Nodes" collection beneath a
        # single scene's collection. Those dormant effect meshes are not part of
        # the GLB's default scene and cannot be selected in the active view layer.
        objects = [obj for obj in collection.all_objects if obj.name in bpy.context.view_layer.objects]
        meshes = [obj for obj in objects if obj.type == 'MESH']
        assert meshes and any('whl' in obj.name for obj in meshes), 'Missing native body or attached wheels'
        bpy.ops.object.select_all(action='DESELECT')
        for obj in objects:
            obj.select_set(True)
        with tempfile.TemporaryDirectory(prefix='mc3-roundtrip-') as temporary:
            work = Path(temporary).resolve() / 'editable'
            (work / 'models').mkdir(parents=True)
            (work / 'catalog.json').write_text(json.dumps([entry]))
            # Native package provenance stays valid in the isolated working catalog.
            (work / 'assets').mkdir()
            native = Path(entry['nativePackage']['file'])
            (work / native).write_bytes((ROOT / 'dealership/dealership' / native).read_bytes())
            model = work / 'models' / (entry['code'] + '.glb')
            output = Path(temporary) / 'cars.json'

            def export():
                bpy.ops.export_scene.gltf(filepath=str(model), export_format='GLB', use_selection=True,
                                          export_extras=True, export_animations=False, export_normals=True)

            export()
            baseline = bake_car(entry['code'], model.read_bytes(), source_mode=False)
            assert baseline['triangleCount'] == original['triangleCount'], 'Blender lost native triangles'
            source_doc, exported_doc = read_glb(source.read_bytes())[0], read_glb(model.read_bytes())[0]
            # Blender exports only images that a drawn primitive's material uses.
            used = {source_doc['images'][source_doc['textures'][m['pbrMetallicRoughness']['baseColorTexture']['index']]['source']]['name']
                    for index in {p['material'] for mesh in source_doc['meshes'] for p in mesh['primitives']}
                    for m in [source_doc['materials'][index]] if 'baseColorTexture' in m['pbrMetallicRoughness']}
            exported_names = {image.get('name', '') for image in exported_doc.get('images', [])}
            assert len(used) >= 3 and used <= exported_names, 'Blender lost embedded texture images'
            assert all(image['mimeType'] == 'image/png' for image in exported_doc['images'])
            textured = [m for m in exported_doc['materials'] if 'baseColorTexture' in m['pbrMetallicRoughness']]
            assert len(textured) >= 3, 'Blender lost texture bindings'
            assert any('TEXCOORD_0' in p['attributes'] for mesh in exported_doc['meshes'] for p in mesh['primitives']), \
                'Blender lost texture coordinates'
            assert {m.get('alphaMode') for m in exported_doc['materials']} & {'MASK', 'BLEND'}, 'Blender lost alpha modes'
            for obj in meshes:
                world, inverse = obj.matrix_world.copy(), obj.matrix_world.inverted()
                for vertex in obj.data.vertices:
                    point = world @ vertex.co
                    # glTF forward Z becomes Blender world Y on import.
                    point.y *= 1.1
                    vertex.co = inverse @ point
                obj.data.update()
            export()
            edited = bake_car(entry['code'], model.read_bytes(), source_mode=False)
            length = lambda value: value['bounds'][3] - value['bounds'][0]
            assert abs(length(edited) / length(baseline) - 1.1) < 1e-5, 'Geometry edit did not reach export'
            assert edited['triangleCount'] == baseline['triangleCount']
            built = build(work, output)[0]
            assert built['model']['schema'] == 2
            assert built['model']['triangleCount'] == edited['triangleCount']
            check(work, output)
            receipts.append({'source_code': code, 'triangles': edited['triangleCount'], 'length_multiplier': 1.1})
    assert all(hashlib.sha256(p.read_bytes()).hexdigest() == h for p, h in before.items()), 'Production models changed'
    print('PASS MC3 Blender roundtrip: ' + json.dumps({'blender': bpy.app.version_string,
          'importer_compatibility': 'ordered custom attributes; VEC2/3/4 exact-value probe passed', 'cars': receipts,
          'model_files_preserved': len(models), 'claim_limits': ['Three static previews; native shaders and animation unverified.']}, sort_keys=True))


if __name__ == '__main__':
    run()
