"""Convert source-bound MC3 static packet geometry to an editable GLB preview."""
import hashlib
import copy
import json
import math
from pathlib import Path
import re
import struct

from mc3_pck import Pck, read_vehicle, read_mesh, read_resource_group, strip_indices
from mc3_materials import read_material_table, CLAIM_LIMITS
from mc3_textures import (bind_material_textures, encode_png, read_slot_textures,
                          read_tex, shared_texture_rows, texture_policy)
from mc3_wheels import read_default_wheels, read_vehicle_class, read_wheel_sizing
from mc3_archive import CookedDisc
from import_mc3_catalogs import ROOT, regular

PROFILE = 'mc3-ps2-static-preview-v1'
LIMITS = [
    'Static inspection preview of native PS2 geometry; animation and damage are not emulated.',
    'Triangle strips use the native normal-X ADC restart bit; runtime clipping and winding are not emulated.',
    'Default stock-named parts use native skeleton rest positions; runtime customization is not emulated.',
    'Native local XYZ Euler frames compose with parent rest transforms; runtime joint animation is not emulated.',
    'Native rims and tires use default source handles and static rest sizing; wheel rotation, camber and deformation are not emulated.',
    'Normals are derived from preview faces; native normal scales are not a rendering fidelity claim.',
    'Ground shadow quads (every draw uses the drop_shadow shader template) are omitted as effect planes, '
    'never as geometry guesses; each omission is listed in the conversion index.',
    'Textures: PCK-embedded 256x256 PSMT8 images and shared 8-bit .tex files are decoded; native shader passes, '
    'environment/specular/metal-flake layers, paint colour and runtime logo/decal textures are not emulated.',
    *CLAIM_LIMITS,
]


def sha(data):
    return hashlib.sha256(data).hexdigest()


def quaternion_product(a, b):
    ax, ay, az, aw = a
    bx, by, bz, bw = b
    return [aw*bx + ax*bw + ay*bz - az*by, aw*by - ax*bz + ay*bw + az*bx,
            aw*bz + ax*by - ay*bx + az*bw, aw*bw - ax*bx - ay*by - az*bz]


def rotated_point(q, point):
    x, y, z, w = q
    px, py, pz = point
    tx, ty, tz = 2*(y*pz-z*py), 2*(z*px-x*pz), 2*(x*py-y*px)
    return [px+w*tx+y*tz-z*ty, py+w*ty+z*tx-x*tz, pz+w*tz+x*ty-y*tx]


def native_rest_frames(bones):
    """FUN_00240090: Rz*Ry*Rx; FUN_0058e8e8: parent affine * local."""
    frames, active = {}, set()

    def frame(index):
        if index in active:
            raise ValueError('cyclic native rest frame')
        if type(index) is not int or not 0 <= index < len(bones):
            raise ValueError('native rest frame parent outside skeleton')
        if index in frames:
            return frames[index]
        active.add(index)
        bone = bones[index]
        angles, position = bone['rotation_raw'], bone['local_position']
        if len(angles) != 3 or len(position) != 3 or not all(math.isfinite(v) for v in [*angles, *position]):
            raise ValueError('nonfinite or invalid native rest frame')
        sx, sy, sz = [math.sin(a/2) for a in angles]
        cx, cy, cz = [math.cos(a/2) for a in angles]
        rotation = [sx*cy*cz-cx*sy*sz, cx*sy*cz+sx*cy*sz,
                    cx*cy*sz-sx*sy*cz, cx*cy*cz+sx*sy*sz]
        position = list(position)
        if bone['parent'] is not None:
            parent = frame(bone['parent'])
            position = [a+b for a, b in zip(rotated_point(parent['rotation'], position), parent['translation'])]
            rotation = quaternion_product(parent['rotation'], rotation)
        active.remove(index)
        frames[index] = {'translation': position, 'rotation': rotation}
        return frames[index]

    return [frame(index) for index in range(len(bones))]


def source_path(folder, name):
    """Require canonical relative source identities within the extraction root."""
    folder = Path(folder)
    if (not isinstance(name, str) or not name or '\\' in name or '\0' in name
            or Path(name).is_absolute() or '..' in name.split('/')
            or Path(name).as_posix() != name):
        raise ValueError('native source path must be canonical and relative')
    path = folder/name
    regular(path)
    if not path.resolve().is_relative_to(folder.resolve()) or not path.is_file():
        raise ValueError('native source path outside extraction or missing')
    if path.stat().st_size > 64 * 1024 * 1024:
        raise ValueError('native preview source outside size bound')
    return path


def wheel_slots(bones):
    """Bind the source corpus's explicit wheel-joint aliases and zero rest frames."""
    slots = []
    for bone in bones:
        name = bone['name'].lower()
        numeric = re.fullmatch(r'(?:whl_?0?[0-3]|wheel[0-3]|whl[fr][01])', name)
        bike = name in {'whl_front', 'whl_rear', 'wheel_front', 'wheel_rear', 'wheelf', 'wheelr'}
        plain = name == 'wheel' and bone['parent'] is not None and bones[bone['parent']]['name'].lower() in {'ax', 'ax1', 'ax2', 'ax3'}
        if not (numeric or bike or plain):
            continue
        ancestor = bone
        while ancestor is not None:
            if any(ancestor['rotation_raw']):
                raise ValueError('wheel rest frame has unsupported ancestor rotation')
            ancestor = bones[ancestor['parent']] if ancestor['parent'] is not None else None
        x, y, z = bone['global_position']
        if not y > 0 or z == 0:
            raise ValueError('wheel anchor outside verified source frame')
        slots.append({'bone': bone['index'], 'native_name': bone['name'],
                      'translation': bone['global_position'], 'axle': 0 if z < 0 else 1,
                      'side': 'left' if x < 0 else 'right'})
    if len(slots) not in {2, 4} or [sum(s['axle'] == a for s in slots) for a in (0, 1)] != [len(slots)//2]*2:
        raise ValueError('native wheel joint set missing or ambiguous')
    names = {s['native_name'].lower() for s in slots}
    if len(slots) == 2:
        pairs = [{'whl_front', 'whl_rear'}, {'wheel_front', 'wheel_rear'},
                 {'whl0', 'whl1'}, {'wheelf', 'wheelr'}]
        if names not in pairs:
            raise ValueError('native two-wheel aliases missing or ambiguous')
    else:
        indices = []
        for slot in slots:
            name = slot['native_name'].lower()
            if name == 'wheel':
                parent = bones[bones[slot['bone']]['parent']]['name'].lower()
                index = 0 if parent == 'ax' else int(parent[-1])
            elif re.fullmatch(r'whl[fr][01]', name):
                index = int(name[-1]) + (2 if name[-2] == 'r' else 0)
            else:
                index = int(name[-1])
            if slot['axle'] != index//2:
                raise ValueError('native wheel alias differs from axle source frame')
            indices.append(index)
        if sorted(indices) != [0, 1, 2, 3]:
            raise ValueError('native four-wheel aliases missing or ambiguous')
    return slots


def native_executable():
    """Read the exact executable member from the supplied source disc."""
    disc = CookedDisc(ROOT/'midnight-club-3-remix/game-files/Midnight Club 3 - DUB Edition Remix.iso')
    try:
        matches = [e for e in disc.entries if e['path'] == 'SLUS_213.55;1' and not e['directory']]
        if len(matches) != 1 or matches[0]['size'] != 5264872:
            raise ValueError('native wheel sizing executable member differs')
        return disc.region(matches[0])(0, matches[0]['size'])
    finally:
        disc.close()


def attach_wheels(folder, index, code, vehicle, executable, materials, sources, textures=None, shared_rows=None):
    bones = vehicle['skeleton']['bones']
    slots = wheel_slots(bones)
    category = read_vehicle_class(folder, code)
    native = Pck.file(Path(vehicle['source']['file']))
    wrapper = native.pointer(native.u32(128 + 8), 0xE5)
    if wrapper != 0xD0:
        raise ValueError('native vehicle wrapper profile differs')
    if native.pointer(native.u32(wrapper + 0xDC), 12) != vehicle['skeleton']['offset']:
        raise ValueError('native vehicle wrapper skeleton binding differs')
    kind_offset = wrapper + 0xE4
    flag = native.data[native.bounds(kind_offset)]
    if flag not in (0, 1) or bool(flag) != (len(slots) == 2):
        raise ValueError('native vehicle kind differs from wheel joint set')
    bike = bool(flag)
    wheels = read_default_wheels(folder, code, bike=bike)
    pins = [*category['copies'], *wheels['config']['copies']]
    for key, value in wheels['sources'].items():
        if key.endswith('_copies'):
            pins.extend(value)
    discovered = {Path(pin['file']).relative_to(folder).as_posix() for pin in pins}
    basenames = {Path(name).name for name in discovered}
    declared = {row['file'] for row in index['files'] if row['file'].startswith('shared/')
                and Path(row['file']).name in basenames}
    if discovered != declared:
        raise ValueError('shared wheel source occurrence coverage differs from extraction index')
    source_rows = {s['file']: s for s in sources}
    for pin in pins:
        name = Path(pin['file']).relative_to(folder).as_posix()
        path = source_path(folder, name)
        rows = [r for r in index['files'] if r['file'] == name]
        if (len(rows) != 1 or rows[0]['bytes'] != pin['bytes'] or rows[0]['sha256'] != pin['sha256']
                or path.stat().st_size != pin['bytes']):
            raise ValueError('shared wheel source differs from extraction index')
        # _source already read and fingerprinted these exact bytes; retain every duplicate occurrence.
        if pin['file'] not in source_rows:
            sources.append(dict(pin));source_rows[pin['file']] = pin
    parts, receipts = [], []
    components = wheels['components']
    for slot in slots:
        bone = bones[slot['bone']]
        maximum = None
        if bike:
            auxiliary = native.pointer(native.u32(bone['offset'] + 0x40), 0x28)
            maximum = struct.unpack_from('<f', native.data, auxiliary + 0x24)[0]
        sizing = read_wheel_sizing(executable, wheels['config']['fields'], axle=slot['axle'],
            bike=bike, vehicle_class=category['class'], wheel_max_x=maximum,
            wheel_rest_y=slot['translation'][1])
        receipts.append({**slot, 'sizing': sizing})
        for component in components:
            if component['axle'] is not None and component['axle'] != slot['axle']:
                continue
            model = component['model']
            if textures is not None and not model.get('textures_bound'):
                label = Path(model['lods']['high'][0]['source']['file']).relative_to(folder).as_posix()
                bind_textures(None, model['materials'], textures, shared_rows or {}, folder,
                              f"{label}#page{component['page']}", model['texture_slots'], model['texture_records'])
                model['textures_bound'] = True
            base = len(materials)
            materials.extend(component['model']['materials'])
            for ordinal, original in enumerate(component['model']['lods']['high']):
                mesh = copy.deepcopy(original)
                for draw in mesh['draws']:
                    draw['native_material_index'] = draw['material'];draw['material'] += base
                    for batch in draw['batches']:
                        batch['packet_offset'] += component['model']['model_file_offset'] - 128
                parts.append({'name': f"whl_{slot['bone']}_{component['component']}_{ordinal}",
                    'bone': slot['bone'], 'mesh': mesh, 'translation': slot['translation'],
                    'rotation_raw': [0., 0., 0.],
                    # FUN_002f85d0 applies a pi turn about Y to the opposite car side.
                    'rotation': [0., 1., 0., 0.] if not bike and slot['side'] == 'right' else [0., 0., 0., 1.],
                    'scale': sizing[component['component']+'_scale'], 'provenance': {
                        'nativeWheelJoint': slot['native_name'], 'nativeWheelComponent': component['component'],
                        'nativeResourceHandle': component['packed_handle'], 'nativePpfPage': component['page'],
                        'nativeMeshOffset': mesh['ppf_file_offset'],
                        'sourceOffsetRule': component['model']['adapter_offset_rule']}})
    return parts, {'class': category['class'], 'bike': bike, 'native_kind_offset': kind_offset, 'slots': receipts,
                   'components': [{k: v for k, v in c.items() if k != 'model'} for c in components]}


def strip_triangles(points):
    """Expand a strip, dropping its explicit repeated/zero-area restart faces."""
    indices = []
    for i in range(2, len(points)):
        tri = [i - 2, i - 1, i] if i % 2 == 0 else [i - 1, i - 2, i]
        a, b, c = (points[j] for j in tri)
        ab, ac = [b[j] - a[j] for j in range(3)], [c[j] - a[j] for j in range(3)]
        cross = [ab[1]*ac[2]-ab[2]*ac[1], ab[2]*ac[0]-ab[0]*ac[2], ab[0]*ac[1]-ab[1]*ac[0]]
        if sum(x*x for x in cross) > 1e-20:
            indices.extend(tri)
    return indices


def face_normals(points, indices):
    normals = [[0., 0., 0.] for _ in points]
    for i in range(0, len(indices), 3):
        ids = indices[i:i+3]
        a, b, c = (points[j] for j in ids)
        u, v = [b[j]-a[j] for j in range(3)], [c[j]-a[j] for j in range(3)]
        cross = [u[1]*v[2]-u[2]*v[1], u[2]*v[0]-u[0]*v[2], u[0]*v[1]-u[1]*v[0]]
        for vertex in ids:
            for k in range(3):
                normals[vertex][k] += cross[k]
    result = []
    for n in normals:
        length = math.sqrt(sum(x*x for x in n))
        result.append([x/length for x in n] if length else [0., 1., 0.])
    return result


PROFILE_DELTAS = {'original': 0, 'mercedes': 0x200, 'remix': 0x1308}


def bind_textures(data, materials, textures, shared_rows, folder, label, slots=None, records=None):
    """Attach decoded textures and display policy to materials read from ``data``.

    ``textures`` collects each accepted image once under a stable key; materials
    keep only the key and provenance, so the GLB material extras stay JSON-safe.
    A texture that the display policy rejects (runtime-logo decals, speed-driven
    effect polygons, composite wrappers) is recorded as unused, never attached.
    """
    if not materials:
        return
    delta = PROFILE_DELTAS[materials[0]['profile']]
    if slots is None:
        slots = read_slot_textures(data, delta)
    if records is None:
        base = struct.unpack_from('<I', data, 0)[0]
        records = bind_material_textures(data, materials, slots, shared_rows, delta,
                                         lambda pointer: pointer - base + 128)
    loaded = {}

    def load(ref):
        if ref['source'] == 'embedded':
            key = f"{label}:{ref['name']}"
            if key not in loaded:
                image = slots[ref['name']]
                loaded[key] = {**image, 'file': label, 'sha256': sha(image['rgba'])}
        else:
            key = f"shared:{ref['name']}"
            if key not in loaded:
                rows = shared_rows[ref['name']]
                row = min(rows, key=lambda r: r['file'])
                raw = source_path(folder, row['file']).read_bytes()
                if len(raw) != row['bytes'] or sha(raw) != row['sha256']:
                    raise ValueError('shared texture differs from extraction index')
                loaded[key] = {**read_tex(raw), 'name': ref['name'], 'file': row['file'],
                               'sha256': row['sha256'], 'occurrences': sorted(r['file'] for r in rows)}
        return key, loaded[key]

    for material, record in zip(materials, records):
        material['shader_template'] = record['shader_template']
        material['runtime_bound_textures'] = record['runtime_bound']
        if record['composite']:
            material['composite_templates'] = record['composite']
        resolved = record['resolved']
        if len(resolved) > 1:
            material['texture_candidates'] = [ref['name'] for ref in resolved]
        key = image = None
        if resolved:
            key, image = load(resolved[0])
        mode, color, note, use_texture = texture_policy(material, record, image)
        if mode is not None:
            material['alpha_mode'], material['base_color'] = mode, color
            material['display_factor_source'] = 'native-texture-policy'
            material['texture_policy_note'] = note
            material['claim_limits'] = [*material['claim_limits'], note]
        if image is not None and use_texture:
            textures.setdefault(key, image)
            material['texture_key'] = key
            material['texture_name'] = resolved[0]['name']
            material['texture_source'] = resolved[0]['source']
        elif resolved:
            material['texture_unused'] = resolved[0]['name']


def build_glb(code, parts, materials, sources, textures=None):
    blob = bytearray()
    doc = {'asset': {'version': '2.0', 'generator': PROFILE}, 'scene': 0,
           'scenes': [{'nodes': []}], 'nodes': [], 'meshes': [], 'materials': [],
           'bufferViews': [], 'accessors': [],
           'extras': {'source_profile': PROFILE, 'car': code, 'nativeResources': sources,
                      'claim_limits': LIMITS}}

    def accessor(rows, width, integer=False):
        while len(blob) % 4:
            blob.append(0)
        start = len(blob)
        flat = rows if integer else [v for row in rows for v in row]
        blob.extend(struct.pack('<' + ('I' if integer else 'f') * len(flat), *flat))
        view = len(doc['bufferViews'])
        doc['bufferViews'].append({'buffer': 0, 'byteOffset': start, 'byteLength': len(blob)-start})
        item = {'bufferView': view, 'componentType': 5125 if integer else 5126,
                'count': len(rows), 'type': 'SCALAR' if integer else {2: 'VEC2', 3: 'VEC3'}[width]}
        if not integer:
            item.update(min=[min(p[k] for p in rows) for k in range(width)],
                        max=[max(p[k] for p in rows) for k in range(width)])
        doc['accessors'].append(item)
        return len(doc['accessors'])-1

    textures = textures or {}
    image_index = {}
    for m in materials:
        pbr = {'baseColorFactor': m['base_color'], 'metallicFactor': m.get('metallic', 0),
               'roughnessFactor': m.get('roughness', .6)}
        key = m.get('texture_key')
        if key is not None:
            if key not in textures:
                raise ValueError('material texture key missing from texture table')
            if key not in image_index:
                image = textures[key]
                png = encode_png(image['width'], image['height'], image['rgba'])
                while len(blob) % 4:
                    blob.append(0)
                start = len(blob)
                blob.extend(png)
                doc['bufferViews'].append({'buffer': 0, 'byteOffset': start, 'byteLength': len(png)})
                doc.setdefault('images', []).append({'bufferView': len(doc['bufferViews'])-1,
                    'mimeType': 'image/png', 'name': image['name']})
                doc.setdefault('samplers', [{'magFilter': 9729, 'minFilter': 9729, 'wrapS': 10497, 'wrapT': 10497}])
                doc.setdefault('textures', []).append({'source': len(doc['images'])-1, 'sampler': 0})
                image_index[key] = len(doc['textures'])-1
            pbr['baseColorTexture'] = {'index': image_index[key]}
        entry = {'name': m.get('shader_template') or m['shader_category'], 'doubleSided': True,
                 'alphaMode': m['alpha_mode'], 'pbrMetallicRoughness': pbr, 'extras': m}
        if m['alpha_mode'] == 'MASK':
            entry['alphaCutoff'] = 0.5
        doc['materials'].append(entry)
    doc['extras']['nativeTextures'] = [
        {'key': k, 'name': t['name'], 'width': t['width'], 'height': t['height'], 'source': t['source'],
         'file': t['file'], 'sha256': t['sha256'], 'levels': t['levels']} for k, t in sorted(textures.items())]
    records = []
    for part in parts:
        mesh = part['mesh']
        primitives, triangles = [], 0
        for draw in mesh['draws']:
            positions, indices, packet_offsets, texcoords = [], [], [], []
            if not 0 <= draw['material'] < len(materials):
                raise ValueError('draw material outside preview table')
            textured = materials[draw['material']].get('texture_key') is not None
            for batch in draw['batches']:
                points = batch['positions']
                if any(len(p) != 3 or any(not math.isfinite(x) for x in p) for p in points):
                    raise ValueError('invalid preview position')
                local = strip_indices(batch) if 'adc' in batch else strip_triangles(points)
                indices.extend(i+len(positions) for i in local)
                positions.extend(points)
                if textured:
                    if len(batch['uvs']) != len(points) or any(len(uv) != 2 or not all(math.isfinite(x) for x in uv) for uv in batch['uvs']):
                        raise ValueError('textured draw lacks one finite UV per vertex')
                    texcoords.extend(batch['uvs'])
                packet_offsets.append(batch['packet_offset'])
            if not indices:
                continue
            triangles += len(indices)//3
            attributes = {'POSITION': accessor(positions, 3),
                          'NORMAL': accessor(face_normals(positions, indices), 3)}
            if textured:
                attributes['TEXCOORD_0'] = accessor(texcoords, 2)
            primitives.append({'mode': 4, 'material': draw['material'],
                'attributes': attributes,
                'indices': accessor(indices, 1, True), 'extras': {'packet_offsets': packet_offsets,
                    'native_material_index': draw.get('native_material_index', draw['material'])}})
        if not primitives:
            continue
        doc['scenes'][0]['nodes'].append(len(doc['nodes']))
        doc['nodes'].append({'name': part['name'], 'mesh': len(doc['meshes']),
                             'translation': part.get('translation', [0., 0., 0.]),
                             'rotation': part.get('rotation', [0., 0., 0., 1.]),
                             'scale': part.get('scale', [1., 1., 1.]),
                             'extras': {'nativeBone': part['bone'], 'sourceNames': [part['name']],
                                        **part.get('provenance', {})}})
        doc['meshes'].append({'name': part['name'], 'primitives': primitives})
        records.append({'role': part['name'], 'bone': part['bone'], 'triangles': triangles,
                        'rest_position': part.get('translation', [0., 0., 0.]),
                        'rotation_raw': part.get('rotation_raw', [0., 0., 0.]),
                        'scale': part.get('scale', [1., 1., 1.]),
                        'native_sha256': mesh['source']['sha256'],
                        **part.get('provenance', {})})
    if not records:
        raise ValueError('no drawable native preview geometry')
    doc['extras']['records'] = records
    doc['buffers'] = [{'byteLength': len(blob)}]
    payload = json.dumps(doc, separators=(',', ':'), allow_nan=False).encode()
    payload += b' ' * (-len(payload) % 4)
    blob.extend(b'\0' * (-len(blob) % 4))
    length = 12+8+len(payload)+8+len(blob)
    return (struct.pack('<4sII', b'glTF', 2, length)+struct.pack('<I4s', len(payload), b'JSON')+
            payload+struct.pack('<I4s', len(blob), b'BIN\0')+blob), records


def preview_vehicle(folder, manifest, extraction_index=None, executable=None):
    """Exact source member identities select the main model and stock-named parts."""
    folder = Path(folder)
    code = manifest['id']
    if not isinstance(code, str) or not re.fullmatch(r'vp_[a-z0-9_]+', code):
        raise ValueError('invalid native preview vehicle identity')
    if extraction_index is None:
        extraction_index = json.loads(source_path(folder, 'index.json').read_text())
    assets = []
    for row in manifest['members']:
        if not row['file'].endswith('.pck'):
            continue
        path = source_path(folder, row['file'])
        data = path.read_bytes()
        if len(data) != row['bytes'] or sha(data) != row['sha256']:
            raise ValueError('native preview member hash/size differs')
        assets.append(path)
    main = [p for p in assets if p.name == code+'.pck']
    if len(main) != 1:
        raise ValueError('main native model member missing or ambiguous')
    vehicle = read_vehicle(main[0])
    main_data = main[0].read_bytes()
    materials = read_material_table(main_data, vehicle['material_collection_offset'])
    textures, shared_rows = {}, shared_texture_rows(extraction_index)
    bind_textures(main_data, materials, textures, shared_rows, folder, main[0].relative_to(folder).as_posix())
    shadow_materials = {m['index'] for m in materials if m.get('shader_template') == 'drop_shadow'}
    effect_planes = []
    parts = []
    for part in vehicle['lods']['high']:
        if part['mesh'] is None:
            continue
        if all(draw['material'] in shadow_materials for draw in part['mesh']['draws']):
            # Ground blob-shadow quad: every draw uses the drop_shadow shader template.
            effect_planes.append({'part': part['name'], 'bone': part['bone'],
                                  'materials': sorted({draw['material'] for draw in part['mesh']['draws']}),
                                  'triangles_omitted': sum(len(strip_indices(b)) // 3 for d in part['mesh']['draws']
                                                           for b in d['batches']),
                                  'reason': 'drop_shadow shader template; ground shadow effect plane'})
            continue
        parts.append(part)
    by_name = {}
    for path in assets:
        if not path.name.endswith('.mesh.pck'):
            continue
        name = path.name.removesuffix('.pck')
        if name in by_name:
            raise ValueError('ambiguous native external mesh member')
        by_name[name] = path
    sources = [vehicle['source']]
    omitted = []
    shared, shared_material_base = None, None
    for part in vehicle['lods']['high']:
        if part['mesh'] is None and '_stk_' in part['name']:
            source = by_name.get(part['name'])
            if source is None:
                if shared is None:
                    candidates = [row for row in extraction_index['files']
                        if row['file'].startswith('shared/') and Path(row['file']).name == code+'_g.pck']
                    if not candidates:
                        raise ValueError('native shared model resource missing')
                    for row in candidates:
                        resource = source_path(folder, row['file']);data = resource.read_bytes()
                        if len(data) != row['bytes'] or sha(data) != row['sha256']:
                            raise ValueError('shared preview resource hash/size differs')
                    if len({row['sha256'] for row in candidates}) != 1:
                        raise ValueError('ambiguous native shared model resource')
                    resource = source_path(folder, min(candidates, key=lambda row: row['file'])['file'])
                    shared = read_resource_group(resource)
                    sources.append(shared['source'])
                    shared_material_base = len(materials)
                    resource_data = resource.read_bytes()
                    shared_materials = read_material_table(resource_data, shared['material_collection_offset'])
                    bind_textures(resource_data, shared_materials, textures, shared_rows, folder,
                                  resource.relative_to(folder).as_posix())
                    materials.extend(shared_materials)
                shared_part = shared['parts'].get(part['name'])
                if shared_part is None:
                    omitted.append(part['name'])
                    continue
                mesh = copy.deepcopy(shared_part['mesh'])
                for draw in mesh['draws']:
                    draw['native_material_index'] = draw['material']
                    draw['material'] += shared_material_base
                parts.append({**part, 'mesh': mesh})
                continue
            mesh = read_mesh(source)
            sources.append(mesh['source'])
            parts.append({**part, 'mesh': mesh})
    bones = vehicle['skeleton']['bones']
    posed = []
    frames = native_rest_frames(bones)
    for part in parts:
        if not 0 <= part['bone'] < len(bones):
            raise ValueError('preview mesh bone outside native skeleton')
        bone = bones[part['bone']]
        part['translation'] = frames[part['bone']]['translation']
        part['rotation_raw'] = bone['rotation_raw']
        part['rotation'] = frames[part['bone']]['rotation']
        posed.append(part)
    wheel_parts, wheel_evidence = attach_wheels(folder, extraction_index, code, vehicle,
        native_executable() if executable is None else executable, materials, sources, textures, shared_rows)
    posed.extend(wheel_parts)
    for source in sources:
        source['file'] = Path(source['file']).relative_to(folder).as_posix()
    data, records = build_glb(code, posed, materials, sources, textures)
    return data, {'records': records, 'native_resources': sources, 'omitted_stock_parts': omitted,
                  'omitted_effect_planes': effect_planes,
                  'wheels': wheel_evidence,
                  'omitted_pose_parts': [],
                  'claim_limits': [*LIMITS, *([f'Missing stock part: {p}' for p in omitted])]}
