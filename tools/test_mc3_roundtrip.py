"""Actual Blender import/edit/export of car, shared-body and motorcycle previews."""
import hashlib
import json
from pathlib import Path
import sys
import tempfile

import bpy

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
from bake_models import bake_car, read_glb
from build_dealership import build, check


def run():
    assert bpy.app.version == (4, 5, 14), 'Use pinned Blender 4.5.14'
    catalog = json.loads((ROOT / 'dealership/dealership/catalog.json').read_text())
    models = list((ROOT / 'midnight-club-3-remix/recovered-models').glob('*.glb'))
    models += list((ROOT / 'dealership/dealership/models').glob('MC3_*.glb'))
    before = {p: hashlib.sha256(p.read_bytes()).hexdigest() for p in models}
    assert len(before) == 188, 'Expected 94 conversions and 94 independent working copies'
    receipts = []
    for code in ['vp_350z_04', 'vp_chrysler300c_05', 'vp_aprilia_mille_04']:
        entry = next(c for c in catalog if c.get('game') == 'midnight-club-3-remix' and c['sourceCode'] == code)
        source = ROOT / 'dealership/dealership/models' / (entry['code'] + '.glb')
        original = bake_car(entry['code'], source.read_bytes(), source_mode=False)
        bpy.ops.wm.read_factory_settings(use_empty=True)
        bpy.ops.import_scene.gltf(filepath=str(source))
        objects = list(bpy.context.scene.objects)
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
    print('PASS MC3 Blender roundtrip: ' + json.dumps({'blender': bpy.app.version_string, 'cars': receipts,
          'model_files_preserved': len(models), 'claim_limits': ['Three static previews; native shaders and animation unverified.']}, sort_keys=True))


if __name__ == '__main__':
    run()
