#!/usr/bin/env python3
"""Bake compact display meshes from source seeds or independent dealership GLBs.

Source mode enforces the pinned first-tree low-speed scene; dealership mode uses
the working GLB's own selected scene and static affine transforms.
Discard driver helmets and baked shadow planes, not alternative states by guesswork.
Weld identical position/normal/tone tuples without moving vertices or decimating faces.
Texture-derived tones are an illustration heuristic, not semantic part segmentation.
Original triangle/normal/UV interpretations and full game-render fidelity remain open.
"""
import base64
import hashlib
import json
import math
from pathlib import Path
import struct

from validate_car_mips import parse_png
from model_png import decode_png

ROOT = Path(__file__).resolve().parents[1]
VERTEX = struct.Struct('<6fB')


def read_glb(data):
    if len(data) < 28 or struct.unpack_from('<3I', data) != (0x46546C67, 2, len(data)):
        raise ValueError('Invalid model source GLB container')
    size, kind = struct.unpack_from('<2I', data, 12)
    end = 20 + size
    if kind != 0x4E4F534A or end + 8 > len(data):
        raise ValueError('Invalid model source JSON chunk')
    doc = json.loads(data[20:end])
    size, kind = struct.unpack_from('<2I', data, end)
    if kind != 0x004E4942 or end + 8 + size != len(data):
        raise ValueError('Invalid model source binary chunk')
    return doc, data[end + 8:]


def accessor(doc, binary, index, width, component):
    a = doc['accessors'][index]
    allowed = (5121, 5123, 5125) if component == 5125 else (component,)
    if a['type'] != {1: 'SCALAR', 2: 'VEC2', 3: 'VEC3'}[width] or a['componentType'] not in allowed:
        raise ValueError('Unsupported model accessor type')
    if a.get('sparse') or a.get('normalized'):
        raise ValueError('Unsupported model accessor encoding')
    view = doc['bufferViews'][a['bufferView']]
    if view['buffer'] != 0:
        raise ValueError('Model accessor is not in the embedded buffer')
    fmt = {5126: 'f', 5125: 'I', 5123: 'H', 5121: 'B'}[a['componentType']]
    step = width * struct.calcsize(fmt)
    stride = view.get('byteStride', step)
    start = view.get('byteOffset', 0) + a.get('byteOffset', 0)
    end = start + (a['count'] - 1) * stride + step
    if a['count'] <= 0 or stride < step or end > view.get('byteOffset', 0) + view['byteLength'] or end > len(binary):
        raise ValueError('Model accessor exceeds its buffer')
    values = [struct.unpack_from('<' + fmt * width, binary, start + i * stride) for i in range(a['count'])]
    if not all(math.isfinite(v) for row in values for v in row):
        raise ValueError('Non-finite model source attribute')
    return values


def texture_tone(rgb, wheel=False):
    """Desaturate texture details; strong chroma becomes body tone, not a livery.

    Retain dark texture features at vertices. This approximates windows, grille and
    tyre detail without shipping texture maps. It cannot remove every decal.
    """
    r, g, b = rgb
    light = 0.2126 * r + 0.7152 * g + 0.0722 * b
    if not wheel and max(rgb) - min(rgb) > 40 and max(rgb) > 72:
        light = 230
    return round((0.06 + 0.94 * (light / 255) ** 0.85) * 255)


IDENTITY = ((1, 0, 0, 0), (0, 1, 0, 0), (0, 0, 1, 0), (0, 0, 0, 1))


def node_transform(node):
    if 'matrix' in node:
        m = node['matrix']
        if len(m) != 16:
            raise ValueError('Invalid dealership node matrix')
        matrix = tuple(tuple(m[j * 4 + i] for j in range(4)) for i in range(4))
    else:
        translation = node.get('translation', [0, 0, 0])
        scale = node.get('scale', [1, 1, 1])
        rotation = node.get('rotation', [0, 0, 0, 1])
        if len(translation) != 3 or len(scale) != 3 or len(rotation) != 4:
            raise ValueError('Invalid dealership node transform')
        x, y, z, w = rotation
        if abs(x*x + y*y + z*z + w*w - 1) > 1e-5:
            raise ValueError('Dealership node quaternion must be unit length')
        rows = [[1-2*(y*y+z*z), 2*(x*y-z*w), 2*(x*z+y*w)],
                [2*(x*y+z*w), 1-2*(x*x+z*z), 2*(y*z-x*w)],
                [2*(x*z-y*w), 2*(y*z+x*w), 1-2*(x*x+y*y)]]
        matrix = tuple(tuple(rows[i][j] * scale[j] for j in range(3)) + (translation[i],) for i in range(3)) + ((0, 0, 0, 1),)
    if not all(math.isfinite(v) for row in matrix for v in row) or matrix[3] != (0, 0, 0, 1):
        raise ValueError('Invalid dealership affine transform')
    return matrix


def compose(a, b):
    return tuple(tuple(sum(a[i][k] * b[k][j] for k in range(4)) for j in range(4)) for i in range(4))


def normal_transform(matrix):
    (a, b, c, _), (d, e, f, _), (g, h, i, _), _ = matrix
    cofactors = ((e*i-f*h, f*g-d*i, d*h-e*g),
                 (c*h-b*i, a*i-c*g, b*g-a*h), (b*f-c*e, c*d-a*f, a*e-b*d))
    determinant = a*cofactors[0][0] + b*cofactors[0][1] + c*cofactors[0][2]
    if abs(determinant) < 1e-12:
        raise ValueError('Dealership model has a singular transform')
    return tuple(tuple(v / determinant for v in row) for row in cofactors), determinant


def bake_car(code, data, expected_sha256=None, *, source_mode=True):
    source_sha = hashlib.sha256(data).hexdigest()
    if expected_sha256 is not None and source_sha != expected_sha256:
        raise ValueError(f'{code}: model GLB differs from manifest pin')
    doc, binary = read_glb(data)
    if source_mode and doc.get('extras', {}).get('car') != code:
        raise ValueError(f'{code}: model source car identity differs')
    scene_index = doc['scene']
    scene = doc['scenes'][scene_index]
    if source_mode and (scene.get('extras', {}).get('visibilityPreset') != 'low_speed' or scene['extras'].get('sourceTree') != 0):
        raise ValueError(f'{code}: expected first-tree low-speed model scene')
    images = {}

    def image(index):
        if index not in images:
            v = doc['bufferViews'][doc['images'][index]['bufferView']]
            start = v.get('byteOffset', 0)
            images[index] = (parse_png if source_mode else decode_png)(binary[start:start + v['byteLength']])
        return images[index]

    parts = {kind: {'vertices': [], 'indices': [], 'lookup': {}} for kind in ['body', 'wheel', 'detail']}
    sources, hubs = [], []
    active = set()

    def walk(index, parent=IDENTITY, wheel=False):
        if index in active:
            raise ValueError('Cyclic model source scene')
        active.add(index)
        node = doc['nodes'][index]
        if source_mode and any(k in node for k in ['matrix', 'rotation', 'scale']):
            raise ValueError('Model source transform is outside translation-only profile')
        if 'skin' in node:
            raise ValueError('Dealership model must be static, not skinned')
        transform = compose(parent, node_transform(node))
        normal_matrix, determinant = normal_transform(transform)
        pos = tuple(transform[i][3] for i in range(3))
        names = node.get('extras', {}).get('sourceNames', [])
        if 'HELMET' in names:
            active.remove(index)
            return
        wheel = wheel or any(n.startswith('WHEEL_') or n.startswith('HUB_') for n in names)
        if any(n.startswith('HUB_') for n in names):
            hubs.append({'name': names[0], 'position': [pos[2], pos[1], -pos[0]]})
        if 'mesh' in node:
            sources.append({'node': index, 'record': node.get('extras', {}).get('geometryRecord'), 'names': names})
            for primitive in doc['meshes'][node['mesh']]['primitives']:
                material = doc['materials'][primitive['material']] if 'material' in primitive else {}
                if material.get('name') == 'UNDER_SHADOW':
                    continue
                if primitive.get('mode', 4) != 4:
                    raise ValueError('Model requires source triangles')
                attrs = primitive['attributes']
                positions = accessor(doc, binary, attrs['POSITION'], 3, 5126)
                normals = accessor(doc, binary, attrs['NORMAL'], 3, 5126)
                uv = accessor(doc, binary, attrs['TEXCOORD_0'], 2, 5126) if 'TEXCOORD_0' in attrs else None
                if len(normals) != len(positions) or (uv is not None and len(uv) != len(positions)):
                    raise ValueError('Model source attribute counts differ')
                indices = [v[0] for v in accessor(doc, binary, primitive['indices'], 1, 5125)]
                if len(indices) % 3 or max(indices) >= len(positions):
                    raise ValueError('Model source triangle index exceeds vertices')
                pbr = material.get('pbrMetallicRoughness', {})
                texture = pbr.get('baseColorTexture')
                kind = 'wheel' if wheel else 'body' if texture or (not source_mode and not names) else 'detail'
                part = parts[kind]
                pixels = image(doc['textures'][texture['index']]['source']) if texture else None
                remap = {}
                for i in sorted(set(indices)):
                    x, y, z = (sum(transform[j][k] * positions[i][k] for k in range(3)) + transform[j][3] for j in range(3))
                    normal = [sum(normal_matrix[j][k] * normals[i][k] for k in range(3)) for j in range(3)]
                    length = math.sqrt(sum(v*v for v in normal))
                    if not length:
                        raise ValueError('Model source normal is zero')
                    nx, ny, nz = [v / length for v in normal]
                    if pixels:
                        if uv is None:
                            raise ValueError('Model textured source has no UVs')
                        w, h, rgba = pixels
                        u, v = uv[i]
                        # glTF UV origin and repeat sampling, same as the recovered viewer.
                        # Tiny negative native UVs can round modulo to exactly
                        # 1.0 in double precision; keep sampling inside the image.
                        px, py = min(w - 1, math.floor((u % 1) * w)), min(h - 1, math.floor((v % 1) * h))
                        offset = (py * w + px) * 4
                        tone = texture_tone(rgba[offset:offset + 3], wheel)
                    else:
                        factor = pbr.get('baseColorFactor', [1, 1, 1, 1])
                        tone = round(max(0.06, min(1, sum(factor[:3]) / 3)) * 255)
                    vertex = VERTEX.pack(z, y, -x, nz, ny, -nx, tone)
                    if vertex not in part['lookup']:
                        part['lookup'][vertex] = len(part['vertices'])
                        part['vertices'].append(vertex)
                    remap[i] = part['lookup'][vertex]
                if determinant < 0:
                    indices = [v for i in range(0, len(indices), 3) for v in [indices[i], indices[i+2], indices[i+1]]]
                part['indices'].extend(remap[i] for i in indices)
        for child in node.get('children', []):
            walk(child, transform, wheel)
        active.remove(index)

    for index in scene['nodes']:
        walk(index)
    all_vertices = [VERTEX.unpack(v) for part in parts.values() for v in part['vertices']]
    if not all_vertices or (source_mode and len(hubs) != 4):
        raise ValueError(f'{code}: model requires geometry and four source wheel hubs')
    low = [min(v[i] for v in all_vertices) for i in range(3)]
    high = [max(v[i] for v in all_vertices) for i in range(3)]
    origin = [(low[0] + high[0]) / 2, low[1], (low[2] + high[2]) / 2]
    output = []
    for kind, part in parts.items():
        if not part['indices']:
            continue
        if len(part['vertices']) > 65535:
            raise ValueError('Model exceeds compact index capacity')
        vertices = bytearray()
        for raw in part['vertices']:
            x, y, z, nx, ny, nz, tone = VERTEX.unpack(raw)
            vertices.extend(VERTEX.pack(x - origin[0], y - origin[1], z - origin[2], nx, ny, nz, tone))
        output.append({'kind': kind, 'vertexCount': len(part['vertices']),
                       'vertices': base64.b64encode(vertices).decode(),
                       'indices': base64.b64encode(struct.pack('<' + 'H' * len(part['indices']), *part['indices'])).decode()})
    for hub in hubs:
        hub['position'] = [v - o for v, o in zip(hub['position'], origin)]
    return {'schema': 1, 'parts': output, 'bounds': [0 if i == 1 else low[i] - origin[i] for i in range(3)] + [high[i] - origin[i] for i in range(3)],
            'wheelHubs': hubs, 'triangleCount': sum(len(p['indices']) // 3 for p in parts.values()),
            'source': {'glb': f'recovered/{code}.glb', 'sha256': source_sha,
                       'originalModelSha256': doc.get('extras', {}).get('originalModelSha256'),
                       'scene': scene_index, 'preset': 'low_speed', 'nodes': sources},
            'claimLimits': ['Recovered triangle, normal and UV interpretations remain candidates.',
                            'Texture-derived vertex tones and icon tint are illustrative; no original paint or shader fidelity.',
                            'Driver helmets and baked shadow planes omitted; no geometry decimation or stat-based stretching.']}


def load_source_model(code):
    manifest = json.loads((ROOT / 'ford-racing-2/recovered/cars' / code / 'manifest.json').read_text())
    entry = next(a for a in manifest['assets'] if a['kind'] == 'glb')
    if entry['path'] != f'dealership/public/ford-racing-2/{code}.glb':
        raise ValueError(f'{code}: unexpected model source path')
    return bake_car(code, (ROOT / entry['path']).read_bytes(), entry['sha256'])
