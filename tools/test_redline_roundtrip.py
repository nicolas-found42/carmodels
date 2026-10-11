"""Blender import/edit/export checks on native four-, three- and six-wheel cars."""
import hashlib
import json
from pathlib import Path
import sys
import tempfile

import bpy

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
from bake_models import bake_car
from build_dealership import build, check


def run():
    assert bpy.app.version == (4, 5, 14), 'Use pinned Blender 4.5.14'
    index = json.loads((ROOT / 'dealership/public/redline/index.json').read_text())
    catalog = json.loads((ROOT / 'dealership/dealership/catalog.json').read_text())
    models = list((ROOT / 'dealership/public/redline').rglob('*.glb')) + list((ROOT / 'dealership/dealership/models').glob('REDLINE_*.glb'))
    before = {p: hashlib.sha256(p.read_bytes()).hexdigest() for p in models}
    receipts = []
    for needle, wheels in [('500gt.car', 4), ('gcw-mog3w', 3), ('Mack', 6)]:
        row = next(c for c in index['cars'] if needle.lower() in c['native_car_id'].lower())
        entry = next(c for c in catalog if c.get('game') == 'redline' and c['sourceCode'] == row['code'])
        source = ROOT / 'dealership/dealership/models' / (entry['code'] + '.glb')
        original = bake_car(entry['code'], source.read_bytes(), source_mode=False)
        assert sum(r['role'].startswith('WHEEL_') for r in row['records']) == wheels
        bpy.ops.wm.read_factory_settings(use_empty=True)
        bpy.ops.import_scene.gltf(filepath=str(source))
        objects = list(bpy.context.scene.objects)
        meshes = [obj for obj in objects if obj.type == 'MESH']
        assert meshes and bpy.data.images, 'Missing native mesh or embedded texture'
        for image in bpy.data.images:
            assert image.size[0] > 0 and image.size[1] > 0 and len(image.pixels) > 0, 'Unreadable embedded texture'
        bpy.ops.object.select_all(action='DESELECT')
        for obj in objects:
            obj.select_set(True)
        with tempfile.TemporaryDirectory(prefix='redline-roundtrip-') as temporary:
            work = Path(temporary) / 'editable'
            (work / 'models').mkdir(parents=True)
            (work / 'catalog.json').write_text(json.dumps([entry]))
            model = work / 'models' / (entry['code'] + '.glb')
            output = Path(temporary) / 'cars.json'
            def export():
                bpy.ops.export_scene.gltf(filepath=str(model), export_format='GLB', use_selection=True,
                                          export_extras=True, export_animations=False, export_normals=True,
                                          export_image_format='AUTO', export_keep_originals=False)
            export()
            baseline = bake_car(entry['code'], model.read_bytes(), source_mode=False)
            assert baseline['triangleCount'] == original['triangleCount'], 'Blender lost native triangles'
            for obj in meshes:
                world, inverse = obj.matrix_world.copy(), obj.matrix_world.inverted()
                for vertex in obj.data.vertices:
                    point = world @ vertex.co
                    point.y *= 1.1
                    vertex.co = inverse @ point
                obj.data.update()
            export()
            edited = bake_car(entry['code'], model.read_bytes(), source_mode=False)
            length = lambda value: value['bounds'][3] - value['bounds'][0]
            assert abs(length(edited) / length(baseline) - 1.1) < 1e-5, 'Geometry edit did not reach exported model'
            assert edited['triangleCount'] == baseline['triangleCount']
            built = build(work, output)[0]
            assert built['model']['schema'] == 2
            assert built['model']['triangleCount'] == edited['triangleCount']
            check(work, output)
            receipts.append({'native_car_id': row['native_car_id'], 'wheels': wheels,
                             'triangles': edited['triangleCount'], 'length_multiplier': 1.1})
    assert all(hashlib.sha256(p.read_bytes()).hexdigest() == h for p, h in before.items()), 'Production models changed'
    print('PASS Redline Blender roundtrip: ' + json.dumps({'blender': bpy.app.version_string, 'cars': receipts,
          'model_files_preserved': len(models), 'claim_limits': ['Three static assemblies; original-game shaders and animations unverified.']}, sort_keys=True))


if __name__ == '__main__':
    run()
