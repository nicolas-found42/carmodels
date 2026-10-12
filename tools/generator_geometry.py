"""Private canonical geometry, shared-template and embedded-GLB implementation."""
import hashlib
import io
import json
from pathlib import Path
import re
import struct

import numpy as np
from PIL import Image
from scipy import ndimage
from scipy.spatial import cKDTree
from skimage.measure import marching_cubes
import trimesh

from bake_models import IDENTITY, accessor, bake_car, compose, node_transform, read_glb
from generator_judge import LABEL_THRESHOLD

ROOT = Path(__file__).resolve().parents[1]
LOW = np.array([-3., 0., -1.5])
HIGH = np.array([3., 3., 1.5])
GRID = 64
LIMITS = ['Learned static geometry, not recovered source geometry or original-game rendering.',
          'Labels are probabilistic; performance, animation, interiors and damage are not inferred.']


def digest(data):
    return hashlib.sha256(data).hexdigest()


def json_bytes(value):
    return (json.dumps(value, sort_keys=True, indent=2, allow_nan=False) + '\n').encode()


def write_json(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix('.tmp')
    temporary.write_bytes(json_bytes(value))
    temporary.replace(path)


def read_parts(path, game):
    """Read only the default scene, with world transforms and separate material primitives."""
    doc, binary = read_glb(Path(path).read_bytes())
    if doc.get('animations') or doc.get('skins') or doc.get('extensionsRequired'):
        raise ValueError('unsupported static profile')
    parts, active = [], set()
    sign = -1 if game == 'midnight-club-3-remix' else 1
    frame = np.array([[0, 0, sign], [0, 1, 0], [-sign, 0, 0.]])

    def walk(index, parent=IDENTITY, group=None):
        if index in active:
            raise ValueError('cyclic scene')
        active.add(index)
        node = doc['nodes'][index]
        transform = compose(parent, node_transform(node))
        matrix = np.asarray(transform)
        names = [node.get('name', ''), *node.get('extras', {}).get('sourceNames', [])]
        if any('HELMET' in n for n in names):
            active.remove(index)
            return
        if game != 'ford-racing-2':
            if game == 'gran-turismo' and 'nativeWheelIndex' in node.get('extras', {}):
                group = str(node['extras']['nativeWheelIndex'])
            elif game == 'redline' and any(re.fullmatch(r'(WHEEL|BRAKE)_\d+', n) for n in names):
                group = next(n.split('_')[-1] for n in names if re.fullmatch(r'(WHEEL|BRAKE)_\d+', n))
            elif game == 'midnight-club-3-remix':
                group = node.get('extras', {}).get('nativeWheelJoint', group)
        if group is None and 'mesh' in node and matrix[2, 2] < 0 and np.linalg.det(matrix[:3, :3]) < 0:
            raise ValueError('front/back-reversed transform')
        if 'mesh' in node:
            for primitive in doc['meshes'][node['mesh']]['primitives']:
                material = doc.get('materials', [{}])[primitive.get('material', 0)]
                if 'shadow' in material.get('name', '').lower():
                    continue
                attrs = primitive['attributes']
                vertices = np.array(accessor(doc, binary, attrs['POSITION'], 3, 5126))
                vertices = np.einsum('ij,kj->ik', vertices, matrix[:3, :3]) + matrix[:3, 3]
                vertices = np.einsum('ij,kj->ik', vertices, frame)
                faces = np.array(accessor(doc, binary, primitive['indices'], 1, 5125)).reshape(-1, 3)
                if primitive.get('mode', 4) != 4 or np.max(faces) >= len(vertices):
                    raise ValueError('invalid triangles')
                texture = material.get('pbrMetallicRoughness', {}).get('baseColorTexture')
                image = None
                if texture:
                    source = doc['images'][doc['textures'][texture['index']]['source']]
                    if source.get('mimeType') != 'image/png':
                        raise ValueError('texture must be embedded PNG')
                    view = doc['bufferViews'][source['bufferView']]
                    start = view.get('byteOffset', 0)
                    image = binary[start:start + view['byteLength']]
                uv = np.array(accessor(doc, binary, attrs['TEXCOORD_0'], 2, 5126)) if 'TEXCOORD_0' in attrs else None
                parts.append({'vertices': vertices, 'faces': faces, 'uv': uv, 'image': image,
                              'factor': material.get('pbrMetallicRoughness', {}).get('baseColorFactor', [1, 1, 1, 1]),
                              'wheel': group, 'name': node.get('name', '')})
        for child in node.get('children', []):
            walk(child, transform, group)
        active.remove(index)

    for index in doc['scenes'][doc.get('scene', 0)]['nodes']:
        walk(index)
    if not parts:
        raise ValueError('empty body')
    if game == 'ford-racing-2':
        # Geometry rather than record names: circular longitudinal/up extents,
        # a thin lateral axis, low and outboard. Cluster material pieces by centre.
        candidates = []
        all_points = np.concatenate([p['vertices'] for p in parts])
        bottom = all_points[:, 1].min()
        for part in parts:
            v = part['vertices']
            extent = np.ptp(v, axis=0)
            centre = (v.max(0) + v.min(0)) / 2
            if (.22 < extent[0] < 1.2 and .22 < extent[1] < 1.2 and
                    .7 < extent[0] / extent[1] < 1.3 and extent[2] < .65 * extent[1] and
                    centre[1] - bottom < .8 and abs(centre[2]) > .4):
                candidates.append((part, centre))
        centres = []
        for part, centre in candidates:
            nearby = next((i for i, other in enumerate(centres) if np.linalg.norm(centre - other) < .15), None)
            if nearby is None:
                nearby = len(centres)
                centres.append(centre)
            part['wheel'] = str(nearby)
    return parts


def aligned_parts(path, game):
    parts = read_parts(path, game)
    groups = sorted({p['wheel'] for p in parts if p['wheel'] is not None})
    if len(groups) != 4:
        raise ValueError(f'failed wheel-count check: {len(groups)} detected')
    wheels = [[p for p in parts if p['wheel'] == group] for group in groups]
    centres = []
    for wheel in wheels:
        points = np.concatenate([p['vertices'] for p in wheel])
        centres.append((points.min(0) + points.max(0)) / 2)
    centres = np.array(centres)
    wheelbase = np.ptp(centres[:, 0])
    track = np.ptp(centres[:, 2])
    if wheelbase < track or track <= 0:
        raise ValueError('invalid wheel layout')
    scale = 2.5 / wheelbase
    origin = centres.mean(0)
    origin[1] = min(p['vertices'][:, 1].min() for wheel in wheels for p in wheel)
    for part in parts:
        part['vertices'] = (part['vertices'] - origin) * scale
    body = [p for p in parts if p['wheel'] is None]
    if not body:
        raise ValueError('empty body')
    points = np.concatenate([p['vertices'] for p in body])
    if np.any(points.min(0) < LOW - .05) or np.any(points.max(0) > HIGH + .05):
        raise ValueError('body outside aligned grid')
    radii = [np.ptp(np.concatenate([p['vertices'] for p in w]), axis=0)[1] / 2 for w in wheels]
    areas, flat_areas = 0., 0.
    meshes = []
    for part in body:
        mesh = trimesh.Trimesh(vertices=part['vertices'], faces=part['faces'], process=False)
        meshes.append(mesh)
        areas += float(mesh.area_faces.sum())
        flat_areas += float(mesh.area_faces[np.max(np.abs(mesh.face_normals), axis=1) > .96].sum())
    rays = []
    for wheel in wheels:
        vertices = np.concatenate([part['vertices'] for part in wheel])
        centre = (vertices.max(0) + vertices.min(0)) / 2
        centre[1] = vertices[:, 1].max() + .02
        rays.append(centre)
    covered = trimesh.util.concatenate(meshes).ray.intersects_any(np.array(rays), np.tile([0, 1, 0], (4, 1)))
    params = {'wheelbase': 2.5, 'track_width': float(track * scale), 'wheel_radius': float(np.mean(radii)),
              'wheel_count': 4, 'proportions': (np.ptp(points, axis=0) / [6, 3, 3]).tolist(),
              'boxiness': flat_areas / max(areas, 1e-12),
              'wheel_coverage': float(np.mean(covered)),
              'frame': 'front +X, up +Y, lateral +Z; ground Y=0; wheelbase 2.5',
              'wheel_detection': 'geometry' if game == 'ford-racing-2' else 'part names'}
    return body, wheels, params


def body_grid(body):
    vertices, faces, offset = [], [], 0
    for part in body:
        vertices.extend((part['vertices'] - LOW) / (HIGH - LOW) * (GRID - 1))
        faces.extend(part['faces'] + offset)
        offset += len(part['vertices'])
    mesh = trimesh.Trimesh(vertices=vertices, faces=faces, process=False)
    voxels = mesh.voxelized(pitch=1).fill()
    occupancy = np.zeros((GRID, GRID, GRID), dtype=bool)
    indices = np.rint(voxels.points).astype(int)
    indices = indices[np.all((indices >= 0) & (indices < GRID), axis=1)]
    occupancy[tuple(indices.T)] = True
    occupancy = ndimage.binary_fill_holes(occupancy)
    # The learned representation is bilaterally symmetric, including asymmetric
    # source triangulation. Wheels never enter voxelization.
    occupancy |= occupancy[:, :, ::-1]
    if not occupancy.any():
        raise ValueError('empty body grid')
    return ((ndimage.distance_transform_edt(~occupancy) -
             ndimage.distance_transform_edt(occupancy)) / GRID).astype(np.float16)


def surface(grid):
    vertices, faces, _, _ = marching_cubes(grid, level=0)
    vertices = vertices / (GRID - 1) * (HIGH - LOW) + LOW
    return trimesh.Trimesh(vertices=vertices, faces=faces, process=False)


def fit_template(grid, reconstructed):
    """Fit a shared UV template by sampling the outer zero crossing of each body section."""
    points = reconstructed.vertices
    xs = np.linspace(points[:, 0].min() + .01, points[:, 0].max() - .01, 100)
    angles = np.linspace(0, 2 * np.pi, 101)
    radius = np.linspace(0, 2.5, 256)
    rings = []
    for x in xs:
        near = points[np.abs(points[:, 0] - x) < .12]
        if not len(near):
            near = points[np.argsort(np.abs(points[:, 0] - x))[:32]]
        centre_y = (near[:, 1].min() + near[:, 1].max()) / 2 if len(near) else points[:, 1].mean()
        section_x = np.clip(int(round((x - LOW[0]) / (HIGH[0] - LOW[0]) * (GRID - 1))), 0, GRID - 1)
        occupied_y = np.flatnonzero(grid[section_x, :, GRID // 2] < 0)
        if len(occupied_y):
            centre_y = LOW[1] + occupied_y[len(occupied_y) // 2] / (GRID - 1) * (HIGH[1] - LOW[1])
        rays = np.empty((101, 256, 3))
        rays[:, :, 0] = x
        rays[:, :, 1] = centre_y + np.cos(angles[:, None]) * radius
        rays[:, :, 2] = np.sin(angles[:, None]) * radius
        coordinates = (rays - LOW) / (HIGH - LOW) * (GRID - 1)
        values = ndimage.map_coordinates(grid, coordinates.reshape(-1, 3).T, order=1,
                                         mode='constant', cval=1).reshape(101, 256)
        inside = values <= 0
        last = np.max(np.where(inside, np.arange(256), -1), axis=1)
        gaps = last < 0
        fallback = np.zeros(101)
        if np.any(gaps):
            # Open source surfaces can leave gaps in a section. Fit the enclosing
            # polar surface from measured marching-cubes points across those gaps.
            delta = near[:, [1, 2]] - [centre_y, 0]
            polar = np.mod(np.arctan2(delta[:, 1], delta[:, 0]), 2 * np.pi)
            lengths = np.linalg.norm(delta, axis=1)
            angular = cKDTree(np.column_stack([np.cos(polar), np.sin(polar)]))
            nearest = angular.query(np.column_stack([np.cos(angles), np.sin(angles)]))[1]
            fallback = lengths[nearest]
            last = np.where(gaps, 0, last)
        upper = np.minimum(last + 1, 255)
        lower_value = values[np.arange(101), last]
        upper_value = values[np.arange(101), upper]
        fraction = np.clip(-lower_value / np.maximum(upper_value - lower_value, 1e-8), 0, 1)
        crossing = radius[last] + (radius[upper] - radius[last]) * fraction
        crossing = np.where(gaps, fallback, crossing)
        # Polar fallback can choose different tied marching-cubes vertices on
        # opposing rays. Average mirror pairs before fitting the symmetric body.
        crossing = (crossing + crossing[::-1]) / 2
        ring = np.column_stack([np.full(101, x), centre_y + np.cos(angles) * crossing,
                                np.sin(angles) * crossing])
        ring[-1] = ring[0]  # Separate UVs, exactly coincident geometric seam.
        rings.append(ring)
    vertices = np.concatenate(rings)
    uv = np.array([(i / 99, j / 100) for i in range(100) for j in range(101)])
    faces = []
    for i in range(99):
        for j in range(100):
            a = i * 101 + j
            faces.extend([[a, a + 1, a + 101], [a + 1, a + 102, a + 101]])
    # Caps close the geometric surface; validation welds its duplicated UV seam.
    vertices = np.vstack([vertices, rings[0].mean(0), rings[-1].mean(0)])
    uv = np.vstack([uv, [0, .5], [1, .5]])
    for j in range(100):
        faces.extend([[10100, j + 1, j], [10101, 9999 + j, 10000 + j]])
    mesh = trimesh.Trimesh(vertices=vertices, faces=faces, process=False)
    error = float(np.mean(cKDTree(points).query(vertices)[0]))
    return mesh, uv, error


def png_bytes(pixels):
    stream = io.BytesIO()
    Image.fromarray(np.asarray(pixels, dtype=np.uint8)).save(stream, format='PNG', optimize=False)
    return stream.getvalue()


def projected_texture(mesh, uv, parts, paint, regions):
    """Project nearest source triangles with barycentric UVs onto a shared 256-square atlas."""
    size = 256
    atlas = np.broadcast_to(np.array([*paint, 255], dtype=np.uint8), (size, size, 4)).copy()
    if parts:
        source_vertices, faces, face_parts, offset = [], [], [], 0
        for i, part in enumerate(parts):
            source_vertices.extend(part['vertices'])
            faces.extend(part['faces'] + offset)
            face_parts.extend([i] * len(part['faces']))
            offset += len(part['vertices'])
        source = trimesh.Trimesh(vertices=source_vertices, faces=faces, process=False)
        usable = source.area_faces > 1e-10
        source.update_faces(usable)
        face_parts = np.asarray(face_parts)[usable]
        original_faces = np.flatnonzero(usable)
        nearest, _, triangle = trimesh.proximity.closest_point(source, mesh.vertices)
        barycentric = trimesh.triangles.points_to_barycentric(source.triangles[triangle], nearest)
        colours = np.empty((len(mesh.vertices), 4), dtype=np.uint8)
        for i, part in enumerate(parts):
            mask = face_parts[triangle] == i
            if not np.any(mask):
                continue
            if part['image'] is not None and part['uv'] is not None:
                pixels = np.asarray(Image.open(io.BytesIO(part['image'])).convert('RGBA'))
                local_faces = original_faces[triangle[mask]] - sum(len(p['faces']) for p in parts[:i])
                projected_uv = np.sum(part['uv'][part['faces'][local_faces]] * barycentric[mask, :, None], axis=1)
                xy = (projected_uv % 1 * [pixels.shape[1], pixels.shape[0]]).astype(int)
                colours[mask] = pixels[xy[:, 1], xy[:, 0]]
            else:
                colours[mask] = np.array(part['factor']) * 255
        # Rasterize the regular shared atlas by interpolation from template UVs.
        pixels_uv = np.indices((size, size)).transpose(1, 2, 0)[:, :, ::-1] / (size - 1)
        indices = cKDTree(uv).query(pixels_uv.reshape(-1, 2))[1]
        atlas = colours[indices].reshape(size, size, 4)
    else:
        x, angle = np.indices((size, size))[::-1] / (size - 1)
        for region in regions:
            if region['probability'] < LABEL_THRESHOLD:
                continue
            mask = (x >= region['u'][0]) & (x <= region['u'][1]) & (angle >= region['v'][0]) & (angle <= region['v'][1])
            if region['category'] == 'glass':
                atlas[mask] = [30, 40, 48, 255]
            elif region['category'] == 'lights':
                atlas[mask] = [220, 215, 184, 255]
    return png_bytes(atlas)


def glb_bytes(body, uv, texture, wheel_parts, recipe, paint=None):
    """Deterministic embedded static GLB; shared template and original wheel UVs."""
    binary = bytearray()
    doc = {'asset': {'version': '2.0', 'generator': 'carmodels learned generator'}, 'scene': 0,
           'scenes': [{'name': 'Generated model', 'nodes': []}], 'nodes': [], 'meshes': [],
           'accessors': [], 'bufferViews': [], 'materials': [], 'textures': [], 'images': [],
           'buffers': [], 'extras': {'generated': True, 'recipe': recipe, 'claim_limits': LIMITS}}

    def view(data):
        binary.extend(b'\0' * (-len(binary) % 4))
        index = len(doc['bufferViews'])
        doc['bufferViews'].append({'buffer': 0, 'byteOffset': len(binary), 'byteLength': len(data)})
        binary.extend(data)
        return index

    def attribute(values, width, integer=False):
        values = np.asarray(values, dtype='<u4' if integer else '<f4').reshape(-1, width)
        index = len(doc['accessors'])
        record = {'bufferView': view(values.tobytes()), 'componentType': 5125 if integer else 5126,
                  'count': len(values), 'type': {1: 'SCALAR', 2: 'VEC2', 3: 'VEC3'}[width]}
        if width == 3:
            record.update(min=values.min(0).tolist(), max=values.max(0).tolist())
        doc['accessors'].append(record)
        return index

    def material(image, factor):
        pbr = {'baseColorFactor': factor, 'metallicFactor': .15, 'roughnessFactor': .65}
        if image:
            source = len(doc['images'])
            doc['images'].append({'bufferView': view(image), 'mimeType': 'image/png'})
            pbr['baseColorTexture'] = {'index': len(doc['textures'])}
            doc['textures'].append({'source': source})
        index = len(doc['materials'])
        doc['materials'].append({'pbrMetallicRoughness': pbr, 'doubleSided': True})
        return index

    def add_mesh(mesh, coords, mat, name, extras):
        # Material primitives can retain vertices that none of their triangles
        # reference. Geometric normals are undefined there, and the viewer rightly
        # rejects zero normals. Compact every attribute with the same index map.
        used = np.unique(mesh.faces)
        mapping = np.full(len(mesh.vertices), -1, dtype=int)
        mapping[used] = np.arange(len(used))
        mesh = trimesh.Trimesh(vertices=mesh.vertices[used], faces=mapping[mesh.faces], process=False)
        coords = coords[used] if coords is not None else None
        # Canonical +X front becomes native +Z front for the static GLB route.
        vertices = np.column_stack([-mesh.vertices[:, 2], mesh.vertices[:, 1], mesh.vertices[:, 0]])
        normals = np.column_stack([-mesh.vertex_normals[:, 2], mesh.vertex_normals[:, 1], mesh.vertex_normals[:, 0]])
        attrs = {'POSITION': attribute(vertices, 3), 'NORMAL': attribute(normals, 3)}
        if coords is not None:
            attrs['TEXCOORD_0'] = attribute(coords, 2)
        primitive = {'attributes': attrs, 'indices': attribute(mesh.faces, 1, True), 'material': mat}
        node = len(doc['nodes'])
        doc['scenes'][0]['nodes'].append(node)
        doc['nodes'].append({'name': name, 'mesh': len(doc['meshes']), 'extras': extras})
        doc['meshes'].append({'name': name, 'primitives': [primitive]})

    colour = [v / 255 for v in paint] + [1] if paint is not None else [1, 1, 1, 1]
    add_mesh(body, uv, material(texture, colour), 'Generated body', {})
    for i, wheel in enumerate(wheel_parts):
        for part in wheel:
            mesh = trimesh.Trimesh(vertices=part['vertices'], faces=part['faces'], process=False)
            add_mesh(mesh, part['uv'], material(None, [.12, .12, .13, 1]), f'WHEEL_{i}', {'sourceNames': [f'WHEEL_{i}']})
    binary.extend(b'\0' * (-len(binary) % 4))
    doc['buffers'] = [{'byteLength': len(binary)}]
    text = json.dumps(doc, sort_keys=True, separators=(',', ':'), allow_nan=False).encode()
    text += b' ' * (-len(text) % 4)
    length = 12 + 8 + len(text) + 8 + len(binary)
    return struct.pack('<5I', 0x46546C67, 2, length, len(text), 0x4E4F534A) + text + struct.pack('<2I', len(binary), 0x004E4942) + binary


def validate_output(body, wheels, glb):
    points = np.asarray(body.vertices)
    mirrored = points.copy()
    mirrored[:, 2] *= -1
    symmetry = float(np.max(cKDTree(points).query(mirrored)[0]))
    contact = [float(abs(min(p['vertices'][:, 1].min() for p in wheel))) for wheel in wheels]
    profile = bake_car('GENERATED', glb, source_mode=False)
    welded = body.copy()
    welded.merge_vertices(merge_tex=True, merge_norm=True)
    closed = bool(welded.is_watertight)
    winding = bool(welded.is_winding_consistent)
    passed = symmetry <= .025 and len(contact) == 4 and max(contact) <= .001 and closed and winding
    return {'passed': passed, 'symmetry_error': symmetry, 'wheel_contact_errors': contact,
            'watertight_after_uv_weld': closed, 'consistent_winding': winding,
            'static_profile': bool(profile['triangleCount']), 'claim_limits': LIMITS}
