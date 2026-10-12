"""Private Blender-side generated-model fixture; invoked by test_generator_blender.py."""
import hashlib
import json
from pathlib import Path
import sys

import bpy

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
from build_dealership import build, check
from bake_models import bake_car


def run(work):
    assert bpy.app.version == (4, 5, 14), 'Use pinned Blender 4.5.14'
    entry = json.loads((work / 'catalog.json').read_text())[0]
    model = work / 'models' / (entry['code'] + '.glb')
    output = work.parent / (work.name + '-display') / 'cars.json'
    original = bake_car(entry['code'], model.read_bytes(), source_mode=False)
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.ops.import_scene.gltf(filepath=str(model), import_scene_as_collection=True)
    meshes = [obj for obj in bpy.data.objects if obj.type == 'MESH']
    assert len(meshes) >= 5, 'Generated body or copied wheels missing'
    assert any(mesh.data.uv_layers for mesh in meshes), 'No editable UV coordinates'
    for obj in bpy.data.objects:
        obj.select_set(True)
    for obj in meshes:
        world, inverse = obj.matrix_world.copy(), obj.matrix_world.inverted()
        for vertex in obj.data.vertices:
            point = world @ vertex.co
            point.y *= 1.2  # Blender Y is native glTF longitudinal Z.
            vertex.co = inverse @ point
        obj.data.update()
    bpy.ops.export_scene.gltf(filepath=str(model), export_format='GLB', use_selection=True,
                              export_extras=True, export_animations=False, export_normals=True,
                              export_image_format='AUTO', export_keep_originals=False)
    edited_hash = hashlib.sha256(model.read_bytes()).hexdigest()
    compiled_model = build(work, output)[0]['model']
    edited = bake_car(entry['code'], model.read_bytes(), source_mode=False)
    assert edited['triangleCount'] == original['triangleCount'], 'Roundtrip lost triangles'
    # The display baker maps native longitudinal +Z to its compact +X frame.
    length = lambda value: value['bounds'][3] - value['bounds'][0]
    assert abs(length(edited) / length(original) - 1.2) < 1e-5, 'Geometry edit did not reach display'
    assert compiled_model['source']['sha256'] == edited_hash, 'Edited GLB provenance not rebuilt'
    compiled = output.read_bytes()
    check(work, output)
    build(work, output)
    assert output.read_bytes() == compiled, 'Generated rebuild not deterministic'
    assert hashlib.sha256(model.read_bytes()).hexdigest() == edited_hash, 'Build changed edited GLB'
    print('PASS generated edit/export/rebuild: ' + entry['code'])


if __name__ == '__main__':
    run(Path(sys.argv[sys.argv.index('--') + 1]))
