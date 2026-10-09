"""Run with Blender --background --python-exit-code 1 --python tools/test_dealership_roundtrip.py."""
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


def hashes(paths):
    return {str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest() for p in paths}


def export(path):
    bpy.ops.export_scene.gltf(filepath=str(path), export_format='GLB', use_selection=True,
                              export_extras=True, export_animations=False, export_normals=True,
                              export_image_format='AUTO', export_keep_originals=False)


def run():
    assert bpy.app.version == (4, 5, 14), 'Use pinned Blender 4.5.14'
    source = ROOT / 'dealership/dealership/models/GRAN_TORINO.glb'
    paths = list((ROOT / 'dealership/public/ford-racing-2').glob('*.glb')) + list((ROOT / 'dealership/dealership/models').glob('*.glb'))
    before = hashes(paths)
    catalog = json.loads((ROOT / 'dealership/dealership/catalog.json').read_text())
    entry = next(c for c in catalog if c['code'] == 'GRAN_TORINO')
    doc, _ = read_glb(source.read_bytes())
    original = bake_car(entry['code'], source.read_bytes(), source_mode=False)
    scene_name = doc['scenes'][doc['scene']]['name']
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.ops.import_scene.gltf(filepath=str(source), import_scene_as_collection=True)
    collection = bpy.data.collections[scene_name]
    bpy.ops.object.select_all(action='DESELECT')
    objects = list(collection.all_objects)
    meshes = [o for o in objects if o.type == 'MESH']
    assert meshes, 'Selected dealership scene contains no meshes'
    for obj in objects:
        obj.select_set(True)
    # Exercise Blender's image encoder instead of merely copying packed PNG bytes.
    for image in bpy.data.images:
        if image.has_data:
            image.pixels[0] = image.pixels[0]
            image.update()
    with tempfile.TemporaryDirectory(prefix='dealership-roundtrip-') as temp:
        work = Path(temp) / 'editable'
        (work / 'models').mkdir(parents=True)
        (work / 'catalog.json').write_text(json.dumps([entry]))
        model = work / 'models/GRAN_TORINO.glb'
        output = Path(temp) / 'compiled/cars.json'
        export(model)
        baseline = build(work, output)[0]['model']
        assert baseline['triangleCount'] == original['triangleCount'], 'Import/export lost source triangles'
        assert len(baseline['wheelHubs']) == len(original['wheelHubs']), 'Import/export lost wheel metadata'
        # Blender is Z-up: its world Y is the car's longitudinal axis.
        for obj in meshes:
            world, inverse = obj.matrix_world.copy(), obj.matrix_world.inverted()
            for vertex in obj.data.vertices:
                point = world @ vertex.co
                point.y *= 1.2
                vertex.co = inverse @ point
            obj.data.update()
        export(model)
        edited_hash = hashlib.sha256(model.read_bytes()).hexdigest()
        edited = build(work, output)[0]['model']
        length = lambda model: model['bounds'][3] - model['bounds'][0]
        assert abs(length(edited) / length(baseline) - 1.2) < 1e-5, 'Exported geometry edit did not reach display'
        assert edited['triangleCount'] == baseline['triangleCount'], 'Roundtrip lost triangles'
        assert edited['source']['sha256'] == edited_hash, 'Display provenance differs from exported GLB'
        compiled = output.read_bytes()
        check(work, output)
        build(work, output)
        assert output.read_bytes() == compiled, 'Roundtrip rebuild is not deterministic'
        assert hashlib.sha256(model.read_bytes()).hexdigest() == edited_hash, 'Build overwrote edited GLB'
    assert hashes(paths) == before, 'Roundtrip modified production/source models'
    receipt = {'blender': bpy.app.version_string, 'car': entry['code'], 'length_multiplier': 1.2,
               'triangles': edited['triangleCount'], 'model_files_preserved': len(paths),
               'claim_limits': ['One static car import/edit/export/rebuild, not all DCC exporters or animation.',
                                'No original-game shading fidelity claim.']}
    print('PASS dealership Blender roundtrip: ' + json.dumps(receipt, sort_keys=True))


if __name__ == '__main__':
    run()
