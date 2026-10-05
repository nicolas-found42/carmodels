"""Run with official Blender --background --python; checks every exported scene."""
import bpy
import hashlib
import json
from pathlib import Path
import struct

ROOT = Path(__file__).resolve().parents[1]
rows = []
for path in sorted((ROOT / 'viewer/public/recovered').glob('*.glb')):
    bpy.ops.wm.read_factory_settings(use_empty=True)
    raw = path.read_bytes()
    length, kind = struct.unpack_from('<2I', raw, 12)
    assert kind == 0x4e4f534a
    doc = json.loads(raw[20:20 + length])
    bpy.ops.import_scene.gltf(filepath=str(path), import_scene_as_collection=True)
    scene_rows = []
    for scene_index, src in enumerate(doc['scenes']):
        stack = list(src['nodes'])
        tris, mesh_objects = 0, 0
        while stack:
            node = doc['nodes'][stack.pop()]
            stack.extend(node.get('children', []))
            if 'mesh' in node:
                mesh_objects += 1
                for prim in doc['meshes'][node['mesh']]['primitives']:
                    assert prim['mode'] == 4
                    tris += doc['accessors'][prim['indices']]['count'] // 3
        # Blender imports source scenes as collections when explicitly requested.
        name = src.get('name', 'Scene ' + str(scene_index))
        collection = next((s for s in bpy.data.collections if s.name == name), None)
        assert collection is not None, (path.name, scene_index, name, list(bpy.data.collections.keys()))
        objects = [o for o in collection.all_objects if o.type == 'MESH']
        actual_tris = 0
        for obj in objects:
            obj.data.calc_loop_triangles()
            actual_tris += len(obj.data.loop_triangles)
            assert all(len(v.co) == 3 for v in obj.data.vertices)
            assert all(poly.material_index < len(obj.data.materials) for poly in obj.data.polygons)
        assert len(objects) == mesh_objects, (path.name, name, len(objects), mesh_objects)
        assert actual_tris == tris, (path.name, name, actual_tris, tris)
        scene_rows.append({'source_scene': scene_index, 'collection': collection.name,
                           'mesh_objects': len(objects), 'triangles': actual_tris})
    images = [im for im in bpy.data.images if im.name not in {'Render Result', 'Viewer Node'}]
    # Blender loads only images referenced by actual primitives, not unused alternatives.
    used_materials = {p['material'] for mesh in doc['meshes'] for p in mesh['primitives']}
    used_materials.update(mapping['material'] for mesh in doc['meshes'] for p in mesh['primitives']
                          for mapping in p.get('extensions', {}).get('KHR_materials_variants', {}).get('mappings', []))
    used_images = {doc['textures'][doc['materials'][i]['pbrMetallicRoughness']['baseColorTexture']['index']]['source']
                   for i in used_materials if 'baseColorTexture' in doc['materials'][i]['pbrMetallicRoughness']}
    assert len(images) == len(used_images), (path.name, len(images), len(used_images))
    assert all(im.size[0] > 0 and im.size[1] > 0 for im in images)
    row = {'file': path.name, 'sha256': hashlib.sha256(raw).hexdigest(),
           'images': len(images), 'scenes': scene_rows}
    rows.append(row)
    print(json.dumps({'validated': path.name, 'scenes': len(scene_rows), 'images': len(images)}), flush=True)
result = {'blender': bpy.app.version_string, 'build_hash': bpy.app.build_hash.decode(),
          'cars': len(rows), 'scene_count': sum(len(r['scenes']) for r in rows),
          'failures': 0, 'checks': 'Independent DCC import of every scene; triangle/object counts and image dimensions.',
          'limits': 'DCC interoperability does not establish original game geometry or shading fidelity.', 'results': rows}
(ROOT / 'research/evidence/continuation/blender-validation.json').write_text(json.dumps(result, indent=2) + '\n')
