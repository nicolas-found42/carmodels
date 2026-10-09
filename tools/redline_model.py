"""Assemble retained Redline native geometry into a static, textured GLB.

The neutral showroom pose uses native car coordinates. Resource selection is
package-local then base; live global plug-in precedence is not established.
"""
import hashlib
import json
import math
from pathlib import Path
import re
import struct

from redline_mesh import decode_model, expanded_primitives
from redline_texture import decode_image, encode_png

PROFILE = 'redline-static-car-v1'
LIMITS = [
    'Static native body/interior/wheel assembly; game animation and lighting are not reproduced.',
    'Package-local resources precede base resources; global plug-in load precedence is unverified.',
    'Native preview suspension pose uses half travel; steering/spin are neutral. Paint, reflection and secondary shader composition are not reproduced.',
    'Native two-slice raw3d textures use the game\'s first-slice 2D fallback.',
    'GLB normals are normalized; zero native normals use geometric face normals, with unusable zero-area triangles omitted.',
]


def sha(data):
    return hashlib.sha256(data).hexdigest()


class MissingResource(ValueError):
    """A declared resource is absent, distinct from failed source identity."""


class NoDrawableGeometry(ValueError):
    """A native configuration has verified resources but no drawable triangles."""

    def __init__(self, name, resources, warnings):
        super().__init__('Native configuration has no drawable geometry')
        self.name, self.resources, self.warnings = name, resources, warnings


def fold(name):
    return name.translate(str.maketrans('ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'))


def export_primitive(group):
    """Make valid glTF normals while retaining native vertex and UV addresses."""
    result = {key: [] for key in ('positions', 'normals', 'uvs', 'indices')}
    derived, omitted = 0, 0
    for start in range(0, len(group['positions']), 3):
        positions = group['positions'][start:start + 3]
        normals = group['normals'][start:start + 3]
        lengths = [math.sqrt(sum(v * v for v in normal)) for normal in normals]
        face = None
        if any(not length for length in lengths):
            a = [positions[1][k] - positions[0][k] for k in range(3)]
            b = [positions[2][k] - positions[0][k] for k in range(3)]
            cross = (a[1] * b[2] - a[2] * b[1], a[2] * b[0] - a[0] * b[2], a[0] * b[1] - a[1] * b[0])
            size = math.sqrt(sum(v * v for v in cross))
            if not size:
                omitted += 1
                continue
            face = tuple(v / size for v in cross)
        for i, (normal, length) in enumerate(zip(normals, lengths)):
            result['indices'].append(len(result['positions']))
            result['positions'].append(positions[i])
            result['uvs'].append(group['uvs'][start + i])
            result['normals'].append(tuple(v / length for v in normal) if length else face)
            derived += int(not length)
    return result, derived, omitted


def safe_file(root, relative):
    root = Path(root)
    path = Path(relative)
    if path.is_absolute() or '..' in path.parts or not path.parts:
        raise ValueError('Unsafe Redline resource path')
    target = root / path
    if root.is_symlink() or any(p.is_symlink() for p in (target, *target.parents) if p == root or root in p.parents):
        raise ValueError('Symlink Redline resource path')
    if root.resolve() not in target.resolve().parents:
        raise ValueError('Redline resource escapes root')
    return target


def parse_config(data):
    if not isinstance(data, bytes) or len(data) > 2_000_000:
        raise ValueError('Invalid native configuration size')
    fields, arrays, index = {}, {}, 0
    keys = {'model', 'interiorModel', 'carName', 'numWheels', 'numAddOns',
            'customBrakeModel', 'numColors'}
    for line_number, line in enumerate(data.decode('mac_roman').splitlines(), 1):
        line = line.strip()
        directive = re.fullmatch(r'#\s*(\d+)', line)
        if directive:
            index = int(directive[1])
            if index > 4096:
                raise ValueError('Native configuration array index exceeds bounds')
            continue
        match = re.match(r'([A-Za-z][A-Za-z0-9_.]*)\s+(.+)', line)
        if not match:
            continue
        key, raw = match.groups()
        if key not in keys and not key.startswith(('wheels.', 'addOns.')):
            continue
        quoted = re.match(r'"([^"\r\n]*)"', raw)
        vector = re.match(r'\{\s*([^}]+)\}', raw)
        number = re.match(r'[-+]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][-+]?\d+)?', raw)
        if quoted:
            value = quoted[1]
        elif vector:
            value = [float(v.strip()) for v in vector[1].split(',')]
            if len(value) != 3 or not all(math.isfinite(v) for v in value):
                raise ValueError(f'Invalid configuration vector at line {line_number}')
        elif number:
            value = float(number[0])
            if not math.isfinite(value):
                raise ValueError('Nonfinite native configuration value')
        else:
            raise ValueError(f'Invalid graphics configuration value at line {line_number}')
        if '.' in key:
            arrays.setdefault(key, {})[index] = value
        else:
            fields[key] = value
    count = fields.get('numWheels', 4)
    if int(count) != count or not 0 <= count <= 64:
        raise ValueError('Native wheel count exceeds bounds')
    fields['numWheels'] = int(count)
    addons = fields.get('numAddOns', 0)
    if int(addons) != addons or not 0 <= addons <= 256:
        raise ValueError('Native addon count exceeds bounds')
    fields['numAddOns'] = int(addons)
    return fields, arrays


class Resources:
    def __init__(self, root, index, package):
        self.root, self.used = Path(root), {}
        self.scopes = []
        for identity in dict.fromkeys((package, 'shared/base')):
            rows = [p for p in index['packages'] if p['id'] == identity]
            if len(rows) != 1:
                raise ValueError('Missing or duplicate native package')
            names = {}
            for row in rows[0]['members']:
                names.setdefault(fold(row['name']), []).append(row)
            self.scopes.append(names)

    def read(self, name, texture=False):
        if not isinstance(name, str) or not name or '/' in name or '\\' in name or name in ('.', '..'):
            raise ValueError('Invalid native resource name')
        aliases = [name + '.txr', name + '.ima', name] if texture else [name]
        for scope in self.scopes:
            for alias in aliases:
                rows = scope.get(fold(alias), [])
                if not rows:
                    continue
                if len({r['sha256'] for r in rows}) != 1:
                    raise ValueError('Ambiguous native resource: ' + name)
                row = rows[0]
                data = safe_file(self.root, row['file']).read_bytes()
                if len(data) != row['bytes'] or sha(data) != row['sha256']:
                    raise ValueError('Native resource differs from extraction pin: ' + row['file'])
                self.used[row['file']] = {k: row[k] for k in ('file', 'bytes', 'sha256')}
                return data, row['name']
        raise MissingResource('Missing native resource: ' + name)


def build_glb(root, index, car, code):
    resources = Resources(root, index, car['package'])
    config_data = safe_file(root, car['file']).read_bytes()
    if len(config_data) != car['bytes'] or sha(config_data) != car['sha256']:
        raise ValueError('Native car configuration differs from extraction pin')
    fields, arrays = parse_config(config_data)
    warnings, records, blob = [], [], bytearray()
    doc = dict(asset={'version': '2.0', 'generator': 'Redline bounded native conversion'},
               scene=0, scenes=[{'nodes': []}], nodes=[], meshes=[], materials=[],
               textures=[], images=[], samplers=[], accessors=[], bufferViews=[],
               extensionsUsed=['KHR_materials_unlit'],
               extras={'car': code, 'native_car_id': car['id'], 'source_profile': PROFILE,
                       'source_variant': car['group'], 'claim_limits': LIMITS})

    def view(data, target=None):
        while len(blob) % 4:
            blob.append(0)
        row = {'buffer': 0, 'byteOffset': len(blob), 'byteLength': len(data)}
        if target:
            row['target'] = target
        doc['bufferViews'].append(row)
        blob.extend(data)
        return len(doc['bufferViews']) - 1

    def accessor(rows, width, integer=False, bounds=False):
        values = [v for row in rows for v in row] if width > 1 else rows
        row = {'bufferView': view(struct.pack('<' + ('I' if integer else 'f') * len(values), *values),
                                  34963 if integer else 34962),
               'componentType': 5125 if integer else 5126, 'count': len(values) // width,
               'type': {1: 'SCALAR', 2: 'VEC2', 3: 'VEC3'}[width]}
        if bounds:
            row['min'] = [min(p[k] for p in rows) for k in range(width)]
            row['max'] = [max(p[k] for p in rows) for k in range(width)]
        doc['accessors'].append(row)
        return len(doc['accessors']) - 1

    image_cache, texture_cache = {}, {}

    def material(native, selector=0):
        flags, name = native['flags'], native['texture']
        factor = [1, 1, 1, 1]
        row = {'name': name, 'doubleSided': bool(flags & 1),
               'extensions': {'KHR_materials_unlit': {}},
               'pbrMetallicRoughness': {'baseColorFactor': factor, 'metallicFactor': 0, 'roughnessFactor': 1},
               'extras': {'nativeFlags': flags, 'nativeValues': native['values']}}
        if flags & 16:
            row.update(alphaMode='MASK', alphaCutoff=0.5)
        elif flags & 2:
            row['alphaMode'] = 'BLEND'
        if name:
            try:
                if selector > 0 and '.' in name:
                    prefix, suffix = name.split('.', 1)
                    candidate = prefix + '#' + format(int(selector), 'x') + '.' + suffix
                    try:
                        resources.read(candidate, texture=True)
                        name = candidate
                    except MissingResource:
                        pass
                data, resolved_name = resources.read(name, texture=True)
            except MissingResource as exc:
                warnings.append({'kind': 'texture', 'resource': name, 'reason': str(exc)})
                data = None
            try:
                if data is None:
                    raise MissingResource('Missing native resource: ' + name)
                key = sha(data)
                if key not in image_cache:
                    w, h, rgba = decode_image(data, resolved_name)
                    image_cache[key] = len(doc['images'])
                    doc['images'].append({'name': name, 'bufferView': view(encode_png(w, h, rgba)), 'mimeType': 'image/png'})
                wrap_s = 33071 if flags & (8 | 64) else 10497
                wrap_t = 33071 if flags & (8 | 128) else 10497
                texture_key = (key, wrap_s, wrap_t)
                if texture_key not in texture_cache:
                    sampler = len(doc['samplers'])
                    doc['samplers'].append({'wrapS': wrap_s, 'wrapT': wrap_t, 'magFilter': 9729, 'minFilter': 9729})
                    texture_cache[texture_key] = len(doc['textures'])
                    doc['textures'].append({'source': image_cache[key], 'sampler': sampler})
                row['pbrMetallicRoughness']['baseColorTexture'] = {'index': texture_cache[texture_key]}
            except ValueError as exc:
                if data is not None:
                    warnings.append({'kind': 'texture', 'resource': name, 'reason': str(exc)})
        doc['materials'].append(row)
        return len(doc['materials']) - 1

    def mesh(name, role, translation=None, scale=None, rotation=None, optional=False, selector=0):
        try:
            data, actual = resources.read(name)
        except MissingResource as exc:
            if not optional:
                raise
            warnings.append({'kind': 'optional-mesh', 'resource': name, 'reason': str(exc)})
            return
        try:
            model = decode_model(data)
        except ValueError as exc:
            if not optional:
                raise
            warnings.append({'kind': 'optional-mesh', 'resource': name, 'reason': str(exc)})
            return
        primitives = []
        native_triangles, derived, omitted, converted_triangles = 0, 0, 0, 0
        for group in expanded_primitives(model):
            native_triangles += len(group['indices']) // 3
            converted, fallback_count, omitted_count = export_primitive(group)
            derived += fallback_count
            omitted += omitted_count
            if not converted['positions']:
                continue
            converted_triangles += len(converted['indices']) // 3
            # Both native upload and our flipY=false GLB loaders sample row0
            # at v=0. Preserve pixel addresses by retaining the native UVs.
            uv = converted['uvs']
            primitives.append({'attributes': {'POSITION': accessor(converted['positions'], 3, bounds=True),
                                             'NORMAL': accessor(converted['normals'], 3),
                                             'TEXCOORD_0': accessor(uv, 2)},
                               'indices': accessor(converted['indices'], 1, integer=True),
                               'mode': 4, 'material': material(model['materials'][group['material']], selector)})
        if derived or omitted:
            warnings.append({'kind': 'normal-derivation', 'resource': name,
                             'reason': f'{derived} zero native corner normals derived from faces; {omitted} unusable zero-area triangles omitted'})
        if not primitives:
            warnings.append({'kind': 'empty-mesh', 'resource': name, 'reason': 'Native draw materials contain no triangles'})
            return
        node = {'name': role, 'mesh': len(doc['meshes']),
                'extras': {'sourceNames': [role], 'nativeResource': actual}}
        for key, value in (('translation', translation), ('scale', scale), ('rotation', rotation)):
            if value is not None:
                node[key] = value
        doc['scenes'][0]['nodes'].append(len(doc['nodes']))
        doc['nodes'].append(node)
        doc['meshes'].append({'name': name, 'primitives': primitives})
        records.append({'role': role, 'resource': actual, 'triangles': converted_triangles,
                        'native_triangles': native_triangles, 'derived_corner_normals': derived, 'omitted_triangles': omitted,
                        'native_sha256': sha(data), 'native_bounds': model['bounds'],
                        'opaque_trailer': model['opaque_trailer'], 'dual_texture': bool(model['flags'] & 2)})

    if not fields.get('model'):
        raise ValueError('Native configuration has no body model')
    mesh(fields['model'], 'BODY')
    if fields.get('interiorModel'):
        mesh(fields['interiorModel'], 'INTERIOR', optional=True)
    for i in range(fields['numWheels']):
        def wheel(key, default=None):
            return arrays.get('wheels.' + key, {}).get(i, default)
        name, position = wheel('model'), wheel('pos')
        if not name or position is None:
            raise ValueError(f'Native wheel {i} model/position missing')
        travel = wheel('maxSuspension', 0.0)
        if not isinstance(travel, (int, float)) or not math.isfinite(travel) or travel < 0:
            raise ValueError('Native suspension travel must be finite and nonnegative')
        # Native preview initialization 0xc5a3 and render subtraction 0x519f5.
        position = [position[0], position[1] - travel * 0.5, position[2]]
        width, radius = wheel('width', 0.2), wheel('radius', 0.3)
        if min(width, radius) < 0:
            raise ValueError('Native wheel dimensions must be nonnegative')
        if not width or not radius:
            try:
                resources.read(name)
            except MissingResource as exc:
                warnings.append({'kind': 'optional-mesh', 'resource': name, 'reason': str(exc)})
            warnings.append({'kind': 'collapsed-wheel', 'resource': name,
                             'reason': (f'Wheel {i} has native zero width/radius and no drawable area' if not radius else
                                        f'Wheel {i} has native zero width; singular scales are unsupported by the static GLB profile')})
            continue
        tilt = wheel('tilt', 0.0) * (1 if position[0] < 0 else -1)
        # Native static T * Rz(tilt*sideSign) * Ry(side*pi) * S.
        angle = 0 if position[0] < 0 else math.pi
        sz, cz, sy, cy = math.sin(tilt / 2), math.cos(tilt / 2), math.sin(angle / 2), math.cos(angle / 2)
        rotation = [-sz * sy, cz * sy, sz * cy, cz * cy]
        selector = wheel('texture', 0)
        if int(selector) != selector or not 0 <= selector <= 65535:
            raise ValueError('Invalid native wheel texture selector')
        mesh(name, 'WHEEL_' + str(i), translation=position, scale=[width, radius, radius], rotation=rotation, selector=int(selector), optional=True)
        brake = wheel('customBrakeModel')
        if brake:
            sx, cx = math.sin(angle / 2), math.cos(angle / 2)
            x, y, z, w = rotation
            brake_rotation = [w * sx + x * cx, y * cx + z * sx, z * cx - y * sx, w * cx - x * sx]
            mesh(brake, 'BRAKE_' + str(i), translation=position, scale=[width, radius, radius], rotation=brake_rotation, optional=True)
    for i in range(fields['numAddOns']):
        if arrays.get('addOns.hasGraphic', {}).get(i) and arrays.get('addOns.model', {}).get(i):
            mesh(arrays['addOns.model'][i], 'ADDON_' + str(i), optional=True)
    if not doc['meshes']:
        raise NoDrawableGeometry(fields.get('carName') or car['id'], list(resources.used.values()), warnings)
    car_limits = LIMITS + [f"{w['kind']}: {w['resource']} — {w['reason']}" for w in warnings]
    doc['extras'].update(warnings=warnings, claim_limits=car_limits, nativeConfig={'file': car['file'], 'sha256': sha(config_data)},
                         nativeResources=list(resources.used.values()))
    doc['buffers'] = [{'byteLength': len(blob)}]
    header = json.dumps(doc, separators=(',', ':'), allow_nan=False).encode()
    header += b' ' * (-len(header) % 4)
    blob.extend(b'\0' * (-len(blob) % 4))
    data = struct.pack('<4sII', b'glTF', 2, 28 + len(header) + len(blob)) + struct.pack('<I4s', len(header), b'JSON') + header
    data += struct.pack('<I4s', len(blob), b'BIN\0') + blob
    name = fields.get('carName') or (car.get('declared_names') or [Path(car['file']).stem])[0]
    # Keep the declared literal name; do not infer vehicle identity from badges.
    return data, records, warnings, name
