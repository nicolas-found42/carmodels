#!/usr/bin/env python3
"""Build one bounded, artistic GT1 refinement; never replace recovered models.

One interpolating split makes four children per triangle. Only manifold edges
within one material/UV/colour/smooth-normal region may curve. Native wheel rings
have a separate axial midpoint rule. This is not recovered game geometry.
"""
import argparse
from collections import defaultdict
import copy
import hashlib
import json
import math
from pathlib import Path
import struct

from bake_models import accessor, bake_car, read_glb

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / 'dealership/public/gran-turismo/simulation/_afb7n.glb'
SOURCE_SHA256 = '0b5ad759fb3cceac7c671dbbeb5074de7352d0b1c85adc13d52fb7598ade16fc'
OUTPUT = ROOT / 'dealership/public/gran-turismo-enhanced'
MODEL = 'rx7-fd-type-rb-enhanced.glb'
FURTHER_MODEL = 'rx7-fd-type-rb-enhanced-8x.glb'
NEXT_MODEL = 'rx7-fd-type-rb-enhanced-133120.glb'
CREASE = math.cos(math.radians(35))


def sub(a, b):
    return tuple(x-y for x, y in zip(a, b))


def dot(a, b):
    return sum(x*y for x, y in zip(a, b))


def unit(v):
    length = math.sqrt(dot(v, v))
    if length < 1e-12:
        raise ValueError('Degenerate refinement normal')
    return tuple(x/length for x in v)


def face_normal(a, b, c):
    x, y = sub(b, a), sub(c, a)
    cross = (x[1]*y[2]-x[2]*y[1], x[2]*y[0]-x[0]*y[2], x[0]*y[1]-x[1]*y[0])
    return unit(cross) if dot(cross, cross) > 1e-24 else None


def roundoff_winding(positions, source_positions, indices, source_indices):
    """Orient float32 slivers, without accepting a resolvable inverted parent."""
    repairs = 0
    for i in range(0, len(source_indices), 3):
        parent = [source_positions[v] for v in source_indices[i:i+3]]
        normal = face_normal(*parent)
        if normal is None:
            continue
        a, b = sub(parent[1], parent[0]), sub(parent[2], parent[0])
        cross = (a[1]*b[2]-a[2]*b[1], a[2]*b[0]-a[0]*b[2], a[0]*b[1]-a[1]*b[0])
        ulp = max(1e-6, *(abs(v) for p in parent for v in p))*2**-23
        bound = 16*ulp*max(dot(a, a)**.5, dot(b, b)**.5)
        for j in range(i*8, i*8+24, 3):
            child = face_normal(*(positions[v] for v in indices[j:j+3]))
            if child is None:
                raise ValueError('Float32 refinement collapsed a nondegenerate child')
            if dot(child, normal) <= 0:
                if dot(cross, cross)**.5 > bound:
                    raise ValueError('Refinement inversion exceeds float32 roundoff bound')
                indices[j+1], indices[j+2] = indices[j+2], indices[j+1]
                repairs += 1
    return repairs


def encode(doc, binary):
    binary = bytes(binary) + b'\0' * (-len(binary) % 4)
    doc['buffers'] = [{'byteLength': len(binary)}]
    header = json.dumps(doc, separators=(',', ':'), allow_nan=False).encode()
    header += b' ' * (-len(header) % 4)
    return (struct.pack('<5I', 0x46546c67, 2, 28+len(header)+len(binary), len(header), 0x4e4f534a)
            + header + struct.pack('<2I', len(binary), 0x004e4942) + binary)


def append_accessor(doc, binary, values, width, integer=False, bounds=False):
    binary.extend(b'\0' * (-len(binary) % 4))
    flat = [v for row in values for v in row]
    payload = struct.pack('<' + ('I' if integer else 'f')*len(flat), *flat)
    view = len(doc['bufferViews'])
    doc['bufferViews'].append({'buffer': 0, 'byteOffset': len(binary), 'byteLength': len(payload),
                               'target': 34963 if integer else 34962})
    binary.extend(payload)
    row = {'bufferView': view, 'componentType': 5125 if integer else 5126,
           'count': len(values), 'type': {1: 'SCALAR', 2: 'VEC2', 3: 'VEC3'}[width]}
    if bounds:
        floats = list(struct.iter_unpack('<' + 'f'*width, payload))
        row.update(min=[min(v[j] for v in floats) for j in range(width)],
                   max=[max(v[j] for v in floats) for j in range(width)])
    doc['accessors'].append(row)
    return len(doc['accessors'])-1


def smooth_edge(rows, uses):
    """Return compatible directed edge endpoints, or preserve the boundary."""
    if len(uses) != 2 or uses[0][0] != uses[1][0]:
        return None
    pi, ta, a, b = uses[0]
    _, tb, c, d = uses[1]
    row = rows[pi]
    attrs = row['attrs']
    if attrs['POSITION'][a] != attrs['POSITION'][d] or attrs['POSITION'][b] != attrs['POSITION'][c]:
        return None
    if (row['normals'][ta] is None or row['normals'][tb] is None
            or dot(row['normals'][ta], row['normals'][tb]) < CREASE):
        return None
    pairs = ((a, d), (b, c))
    if any(dot(unit(attrs['NORMAL'][x]), unit(attrs['NORMAL'][y])) < CREASE for x, y in pairs):
        return None
    if any(attrs[k][x] != attrs[k][y] for k in ('TEXCOORD_0', 'COLOR_0') if k in attrs for x, y in pairs):
        return None
    if row['native'] and any(row['native'].get(x) != row['native'].get(y) for x, y in pairs):
        return None
    return pi, a, b, pairs


def lineage_id(values, compact=False):
    encoded = json.dumps(sorted(values), separators=(',', ':'))
    return 'sha256:'+hashlib.sha256(encoded.encode()).hexdigest() if compact else encoded


def refine_mesh(mesh, doc, binary, pivot=None, references=None, source_ids=None, protected_edges=(), compact=False):
    """Keep original samples; interpolate new edge samples with bounded curvature.

    Positions determine incidence, not welding. Attribute seams remain independent
    and frozen. Geometrically identical edges share a single midpoint decision.
    """
    rows, edges = [], defaultdict(list)
    for pi, primitive in enumerate(mesh['primitives']):
        if primitive.get('mode', 4) != 4 or set(primitive['attributes']) - {'POSITION', 'NORMAL', 'TEXCOORD_0', 'COLOR_0'}:
            raise ValueError('Unsupported refinement primitive')
        attrs = {key: accessor(doc, binary, index, 2 if key == 'TEXCOORD_0' else 3, 5126)
                 for key, index in primitive['attributes'].items()}
        positions = attrs['POSITION']
        if any(len(v) != len(positions) for v in attrs.values()):
            raise ValueError('Refinement attribute count mismatch')
        indices = [v[0] for v in accessor(doc, binary, primitive['indices'], 1, 5125)]
        if len(indices) % 3 or any(v >= len(positions) for v in indices):
            raise ValueError('Refinement triangle indices outside bounds')
        triangles = [indices[i:i+3] for i in range(0, len(indices), 3)]
        normals = [face_normal(*(positions[i] for i in tri)) for tri in triangles]
        native_ids = {}
        for record in primitive.get('extras', {}).get('nativeFaces', []):
            for j, native in enumerate(record['vertexIndices']):
                native_ids[record['firstVertex']+j] = native
        if source_ids is not None:
            native_ids = dict(enumerate(source_ids[pi])) if source_ids[pi] else {}
        reference = references[pi] if references is not None else positions
        if len(reference) != len(positions):
            raise ValueError('Refinement reference count mismatch')
        rows.append({'attrs': attrs, 'triangles': triangles, 'normals': normals, 'native': native_ids,
                     'reference': reference})
        for ti, tri in enumerate(triangles):
            for a, b in zip(tri, tri[1:] + tri[:1]):
                key = tuple(sorted((positions[a], positions[b])))
                edges[key].append((pi, ti, a, b))
    all_positions = [v for row in rows for v in row['attrs']['POSITION']]
    low = tuple(min(v[j] for v in all_positions) for j in range(3))
    high = tuple(max(v[j] for v in all_positions) for j in range(3))
    # At most 0.2% of this mesh's longest dimension; original bounds also fixed.
    limit = max(sub(high, low)) * .002
    smooth = {}
    fans = [list(range(len(row['attrs']['POSITION']))) for row in rows]

    def root(pi, v):
        while fans[pi][v] != v:
            v = fans[pi][v]
        return v

    for key, uses in edges.items():
        eligible = smooth_edge(rows, uses)
        if key in protected_edges or eligible is None:
            continue
        pi, a, b, pairs = eligible
        smooth[key] = (pi, a, b)
        for x, y in pairs:
            fans[pi][root(pi, y)] = root(pi, x)
    averaged = []
    for pi, row in enumerate(rows):
        sums = defaultdict(lambda: [0., 0., 0.])
        for tri, normal in zip(row['triangles'], row['normals']):
            if normal is None:
                continue
            for k, v in enumerate(tri):
                pos = row['attrs']['POSITION']
                a = unit(sub(pos[tri[(k+1) % 3]], pos[v]))
                b = unit(sub(pos[tri[(k+2) % 3]], pos[v]))
                angle = math.acos(max(-1., min(1., dot(a, b))))
                total = sums[root(pi, v)]
                for j in range(3):
                    total[j] += normal[j] * angle
        averaged.append({v: unit(sums[root(pi, v)]) if dot(sums[root(pi, v)], sums[root(pi, v)]) > 1e-24
                         else unit(row['attrs']['NORMAL'][v]) for tri in row['triangles'] for v in tri})
    midpoints, moved, max_offset = {}, 0, 0.
    for key in edges:
        a, b = key
        midpoint = tuple((x+y)/2 for x, y in zip(a, b))
        target = midpoint
        if key in smooth:
            pi, x, y = smooth[key]
            na, nb = averaged[pi][x], averaged[pi][y]
            # key order may differ from this triangle's direction.
            if rows[pi]['attrs']['POSITION'][x] != a:
                na, nb = nb, na
            e = sub(b, a)
            target = tuple(midpoint[j] + (dot(e, nb)*nb[j]-dot(e, na)*na[j])/8 for j in range(3))
        if pivot is not None and all(rows[pi]['normals'][ti] is not None for pi, ti, _, _ in edges[key]):
            ra, rb = sub(a[1:], pivot[1:]), sub(b[1:], pivot[1:])
            la, lb = math.sqrt(dot(ra, ra)), math.sqrt(dot(rb, rb))
            # Neutral native wheels rotate about X. Only short, constant-X,
            # equal-radius ring segments curve; axle/spoke edges stay as they are.
            if (abs(a[0]-b[0]) < 1e-7 and min(la, lb) > 1e-5
                    and abs(la-lb) < max(la, lb)*.005
                    and CREASE < dot(ra, rb)/(la*lb) < 1-1e-8):
                direction = unit(tuple((x+y)/2 for x, y in zip(ra, rb)))
                target = (midpoint[0], *(pivot[j+1]+direction[j]*(la+lb)/2 for j in range(2)))
        anchors = [tuple((x+y)/2 for x, y in zip(rows[pi]['reference'][a], rows[pi]['reference'][b]))
                   for pi, _, a, b in edges[key]]
        anchor = anchors[0] if references is not None else midpoint
        if any(v != anchor for v in anchors) and references is not None:
            # Coincident geometry with different source supports must not acquire
            # a common curved interpretation. Its arithmetic midpoint is safe
            # for each support because prior samples already obey the envelope.
            target = midpoint
        delta = sub(target, anchor)
        distance = math.sqrt(dot(delta, delta))
        if distance > limit:
            target = tuple(anchor[j]+delta[j]*limit/distance for j in range(3))
        target = tuple(max(low[j], min(high[j], target[j])) for j in range(3))
        distance = math.sqrt(dot(sub(target, anchor), sub(target, anchor)))
        moved += math.sqrt(dot(sub(target, midpoint), sub(target, midpoint))) > 1e-10
        max_offset = max(max_offset, distance)
        midpoints[key] = target
    result = copy.deepcopy(mesh)
    triangle_count = normal_fallbacks = 0
    for pi, (row, primitive) in enumerate(zip(rows, result['primitives'])):
        attrs = copy.deepcopy(row['attrs'])
        reference = list(row['reference'])
        lineage = list(source_ids[pi]) if source_ids is not None and source_ids[pi] else []
        # Keep every original position/UV/color sample, including duplicated seams.
        attrs['NORMAL'] = [averaged[pi].get(i, unit(n)) for i, n in enumerate(attrs['NORMAL'])]
        lookup, indices = {}, []
        for ti, tri in enumerate(row['triangles']):
            mids = []
            for a, b in zip(tri, tri[1:] + tri[:1]):
                edge = tuple(sorted((a, b)))
                if edge not in lookup:
                    lookup[edge] = len(attrs['POSITION'])
                    reference.append(tuple((x+y)/2 for x, y in zip(reference[a], reference[b])))
                    if lineage:
                        lineage.append(lineage_id((lineage[a], lineage[b]), compact))
                    key = tuple(sorted((attrs['POSITION'][a], attrs['POSITION'][b])))
                    for kind, values in attrs.items():
                        if kind == 'POSITION':
                            value = midpoints[key]
                        else:
                            value = tuple((x+y)/2 for x, y in zip(values[a], values[b]))
                            if kind == 'NORMAL':
                                if compact and dot(value, value) < 1e-24:
                                    value = row['normals'][ti] or row['attrs']['NORMAL'][a]
                                    normal_fallbacks += 1
                                value = unit(value)
                        values.append(value)
                mids.append(lookup[edge])
            a, b, c = tri
            ab, bc, ca = mids
            for child in ((a, ab, ca), (ab, b, bc), (ca, bc, c), (ab, bc, ca)):
                normal = face_normal(*(attrs['POSITION'][v] for v in child))
                source_normal = row['normals'][len(indices)//12]
                if source_normal is not None and (normal is None or dot(normal, source_normal) <= 0):
                    raise ValueError('Refinement inverted a triangle')
                indices.extend(child)
        for kind, values in attrs.items():
            primitive['attributes'][kind] = append_accessor(doc, binary, values, 2 if kind == 'TEXCOORD_0' else 3,
                                                          bounds=kind == 'POSITION')
        primitive['indices'] = append_accessor(doc, binary, [(i,) for i in indices], 1, integer=True)
        extras = primitive.setdefault('extras', {})
        extras['enhancement'] = {'method': 'bounded-interpolating-edges-v1',
                                 'originalAttributes': mesh['primitives'][pi]['attributes'],
                                 'originalIndices': mesh['primitives'][pi]['indices'],
                                 'originalVertexCount': len(row['attrs']['POSITION']),
                                 'childrenPerSourceTriangle': 4,
                                 'nativeNormalIndicesDescribe': 'Retained source data, not derived display normals.'}
        if references is not None:
            extras['enhancement']['referencePositions'] = append_accessor(doc, binary, reference, 3)
            extras['enhancement']['vertexSourceIds'] = lineage
        for record in extras.get('nativeFaces', []):
            record['firstTriangle'] *= 4
            record['triangleCount'] *= 4
        triangle_count += len(indices)//3
    report = {'originalTriangles': triangle_count//4, 'enhancedTriangles': triangle_count,
                    'originalDegenerateTriangles': sum(n is None for row in rows for n in row['normals']),
                    'curvedEdges': moved, 'uniqueEdges': len(edges),
                    ('maxReferenceDisplacementMetres' if references is not None else
                     'maxMidpointDisplacementMetres'): max_offset, 'displacementLimitMetres': limit}
    if compact:
        report['normalInterpolationFallbacks'] = normal_fallbacks
    return result, report


def pilot_references(mesh, doc, binary):
    """Recover linear source support and native lineage for the first 4x pilot.

    Reconstruct its deterministic edge insertion order from retained original
    accessors. Never treat generated vertex indices as native vertex identities.
    """
    if all('referencePositions' in p['extras']['enhancement'] for p in mesh['primitives']):
        # Earlier scenes retain the exact attribute/index references of each
        # generation, so ancestry is an exact structural join, not a name guess.
        parents = [m for m in doc['meshes'] if len(m['primitives']) == len(mesh['primitives'])
                   and all(a['attributes'] == b['extras']['enhancement']['originalAttributes']
                           and a['indices'] == b['extras']['enhancement']['originalIndices']
                           for a, b in zip(m['primitives'], mesh['primitives']))]
        if len(parents) != 1:
            raise ValueError('Refinement ancestry is missing or ambiguous')
        parent = parents[0]
        _, parent_lineages, inherited = pilot_references(parent, doc, binary)
        references, lineages, rows, edges, inserted, actual = [], [], [], defaultdict(list), [], []
        for pi, (old, current) in enumerate(zip(parent['primitives'], mesh['primitives'])):
            info = current['extras']['enhancement']
            references.append(accessor(doc, binary, info['referencePositions'], 3, 5126))
            lineages.append(info['vertexSourceIds'])
            attrs = {k: accessor(doc, binary, v, 2 if k == 'TEXCOORD_0' else 3, 5126)
                     for k, v in old['attributes'].items()}
            positions = attrs['POSITION']
            indices = [v[0] for v in accessor(doc, binary, old['indices'], 1, 5125)]
            triangles = [indices[i:i+3] for i in range(0, len(indices), 3)]
            rows.append({'attrs': attrs, 'native': dict(enumerate(parent_lineages[pi])),
                         'normals': [face_normal(*(positions[v] for v in tri)) for tri in triangles]})
            lookup = {}
            for ti, tri in enumerate(triangles):
                for a, b in zip(tri, tri[1:]+tri[:1]):
                    edge = tuple(sorted((a, b)))
                    if edge not in lookup:
                        lookup[edge] = len(positions)+len(lookup)
                    edges[tuple(sorted((positions[a], positions[b])))].append((pi, ti, a, b))
            inserted.append(lookup)
            actual.append(accessor(doc, binary, current['attributes']['POSITION'], 3, 5126))
            if len(references[-1]) != len(actual[-1]) or lineages[-1] and len(lineages[-1]) != len(actual[-1]):
                raise ValueError('Stored refinement support count differs')
        protected = set()
        for key, uses in edges.items():
            if key not in inherited and smooth_edge(rows, uses) is not None:
                continue
            for pi, _, a, b in uses:
                mid = inserted[pi][tuple(sorted((a, b)))]
                for x, y in ((a, mid), (mid, b)):
                    protected.add(tuple(sorted((actual[pi][x], actual[pi][y]))))
        return references, lineages, protected
    references, lineages, roots, original_edges, inserted = [], [], [], defaultdict(list), []
    for pi, primitive in enumerate(mesh['primitives']):
        info = primitive['extras']['enhancement']
        if info['childrenPerSourceTriangle'] != 4 or 'referencePositions' in info:
            raise ValueError('Expected first-stage fourfold pilot')
        positions = accessor(doc, binary, info['originalAttributes']['POSITION'], 3, 5126)
        indices = [v[0] for v in accessor(doc, binary, info['originalIndices'], 1, 5125)]
        native = {}
        for face in primitive.get('extras', {}).get('nativeFaces', []):
            for i, value in enumerate(face['vertexIndices']):
                native[face['firstVertex']+i] = str(value)
        lineage = [native[i] for i in range(len(positions))] if native else []
        attrs = {key: accessor(doc, binary, index, 2 if key == 'TEXCOORD_0' else 3, 5126)
                 for key, index in info['originalAttributes'].items()}
        triangles = [indices[i:i+3] for i in range(0, len(indices), 3)]
        roots.append({'attrs': attrs, 'native': native,
                      'normals': [face_normal(*(positions[v] for v in tri)) for tri in triangles]})
        seen = {}
        for i in range(0, len(indices), 3):
            tri = indices[i:i+3]
            for a, b in zip(tri, tri[1:]+tri[:1]):
                edge = tuple(sorted((a, b)))
                key = tuple(sorted((positions[a], positions[b])))
                original_edges[key].append((pi, i//3, a, b))
                if edge in seen:
                    continue
                seen[edge] = len(positions)
                positions.append(tuple((x+y)/2 for x, y in zip(positions[a], positions[b])))
                if lineage:
                    lineage.append(json.dumps(sorted((lineage[a], lineage[b])), separators=(',', ':')))
        if len(positions) != doc['accessors'][primitive['attributes']['POSITION']]['count']:
            raise ValueError('Pilot reference reconstruction differs')
        references.append(positions)
        lineages.append(lineage)
        inserted.append(seen)
    protected = set()
    for uses in original_edges.values():
        if smooth_edge(roots, uses) is not None:
            continue
        for pi, _, a, b in uses:
            actual = accessor(doc, binary, mesh['primitives'][pi]['attributes']['POSITION'], 3, 5126)
            mid = inserted[pi][tuple(sorted((a, b)))]
            for x, y in ((a, mid), (mid, b)):
                protected.add(tuple(sorted((actual[x], actual[y]))))
    return references, lineages, protected


def refine_eight(mesh, doc, binary, pivot=None):
    """Conforming 8x refinement, globally bounded against recovered geometry.

    Split all edges once (four children), then split two children internally
    at their centroids (three each). No additional boundary splits are needed.
    """
    compact = 'referencePositions' in mesh['primitives'][0]['extras']['enhancement']
    references, lineages, protected = pilot_references(mesh, doc, binary)
    result, report = refine_mesh(mesh, doc, binary, pivot, references, lineages, protected, compact)
    report['inheritedProtectedEdgeSegments'] = len(protected)
    if compact:
        report['float32WindingRepairs'] = 0
    for pi, primitive in enumerate(result['primitives']):
        info = primitive['extras']['enhancement']
        attrs = {key: accessor(doc, binary, index, 2 if key == 'TEXCOORD_0' else 3, 5126)
                 for key, index in primitive['attributes'].items()}
        refs = accessor(doc, binary, info['referencePositions'], 3, 5126)
        lineage = info['vertexSourceIds']
        indices = [v[0] for v in accessor(doc, binary, primitive['indices'], 1, 5125)]
        positions = attrs['POSITION']
        low = tuple(min(v[j] for row in references for v in row) for j in range(3))
        high = tuple(max(v[j] for row in references for v in row) for j in range(3))
        output = []
        for i in range(0, len(indices), 12):
            for child in range(4):
                tri = indices[i+child*3:i+child*3+3]
                if child not in (0, 3):
                    output.extend(tri)
                    continue
                centre = tuple(sum(positions[v][j] for v in tri)/3 for j in range(3))
                reference = tuple(sum(refs[v][j] for v in tri)/3 for j in range(3))
                normal = face_normal(*(positions[v] for v in tri))
                target = centre
                if normal is not None:
                    # Average the three tangent-plane projections. This may
                    # round the interior; all shared boundaries remain fixed.
                    delta = [0., 0., 0.]
                    for v in tri:
                        n = attrs['NORMAL'][v]
                        d = dot(sub(centre, positions[v]), n)
                        for j in range(3):
                            delta[j] -= d*n[j]/3
                    target = tuple(centre[j]+delta[j] for j in range(3))
                delta = sub(target, reference)
                length = math.sqrt(dot(delta, delta))
                limit = report['displacementLimitMetres']
                if length > limit:
                    target = tuple(reference[j]+delta[j]*limit/length for j in range(3))
                target = tuple(max(low[j], min(high[j], target[j])) for j in range(3))
                # A slender source triangle may not safely accept interior
                # curvature. Its planar centroid still adds conforming density.
                normals = [face_normal(positions[tri[j]], positions[tri[(j+1) % 3]], target) for j in range(3)]
                if normal is None or any(n is None or dot(n, normal) <= 0 for n in normals):
                    target = centre
                new = len(positions)
                for key, values in attrs.items():
                    value = target if key == 'POSITION' else tuple(sum(values[v][j] for v in tri)/3 for j in range(len(values[0])))
                    if compact and key == 'NORMAL' and dot(value, value) < 1e-24:
                        value = normal or values[tri[0]]
                        report['normalInterpolationFallbacks'] += 1
                    values.append(unit(value) if key == 'NORMAL' else value)
                refs.append(reference)
                if lineage:
                    lineage.append(lineage_id((lineage[v] for v in tri), compact))
                for j in range(3):
                    output.extend((tri[j], tri[(j+1) % 3], new))
                displacement = math.sqrt(dot(sub(target, reference), sub(target, reference)))
                report['maxReferenceDisplacementMetres'] = max(report['maxReferenceDisplacementMetres'], displacement)
        for key, values in attrs.items():
            primitive['attributes'][key] = append_accessor(doc, binary, values, 2 if key == 'TEXCOORD_0' else 3,
                                                          bounds=key == 'POSITION')
        if compact:
            actual = accessor(doc, binary, primitive['attributes']['POSITION'], 3, 5126)
            source = mesh['primitives'][pi]
            source_positions = accessor(doc, binary, source['attributes']['POSITION'], 3, 5126)
            source_indices = [v[0] for v in accessor(doc, binary, source['indices'], 1, 5125)]
            report['float32WindingRepairs'] += roundoff_winding(actual, source_positions, output, source_indices)
        primitive['indices'] = append_accessor(doc, binary, [(v,) for v in output], 1, integer=True)
        info.update(method='bounded-eightfold-v1', childrenPerSourceTriangle=8,
                    referencePositions=append_accessor(doc, binary, refs, 3))
        for face in primitive.get('extras', {}).get('nativeFaces', []):
            face['firstTriangle'] *= 2
            face['triangleCount'] *= 2
        actual = accessor(doc, binary, primitive['attributes']['POSITION'], 3, 5126)
        for position, reference in zip(actual, refs):
            delta = sub(position, reference)
            report['maxReferenceDisplacementMetres'] = max(report['maxReferenceDisplacementMetres'], math.sqrt(dot(delta, delta)))
    report['enhancedTriangles'] *= 2
    return result, report


def enhance(data):
    doc, original = read_glb(data)
    if doc.get('extras', {}).get('sourceProfile') != 'gran-turismo-native-candidate':
        raise ValueError('Expected canonical GT1 GLB')
    binary = bytearray(original)
    scene = copy.deepcopy(doc['scenes'][doc['scene']])
    scene['name'] = 'Enhanced LOD0 — artistic refinement'
    scene['nodes'] = list(scene['nodes'])
    reports = []
    for i, index in enumerate(scene['nodes']):
        node = copy.deepcopy(doc['nodes'][index])
        if 'children' in node or 'mesh' not in node or any(k in node for k in ('matrix', 'rotation', 'scale', 'translation')):
            raise ValueError('Expected flat native GT1 scene')
        mesh = doc['meshes'][node['mesh']]
        pivot = node.get('extras', {}).get('nativePivotPositionMetres')
        refined, report = refine_mesh(mesh, doc, binary, pivot)
        report['name'] = node['name']
        reports.append(report)
        node['mesh'] = len(doc['meshes'])
        doc['meshes'].append(refined)
        scene['nodes'][i] = len(doc['nodes'])
        doc['nodes'].append(node)
    doc['scene'] = len(doc['scenes'])
    doc['scenes'].append(scene)
    report = {'schema': 1, 'sourceSha256': hashlib.sha256(data).hexdigest(),
              'sourceId': doc['extras']['sourceId'], 'originalScene': 0,
              'enhancedScene': doc['scene'], 'meshes': reports,
              'originalTriangles': sum(r['originalTriangles'] for r in reports),
              'enhancedTriangles': sum(r['enhancedTriangles'] for r in reports),
              'claimLimits': ['Artistic derived geometry, not recovered GT1 or real-car detail.',
                              'Original vertices and bounds fixed; intermediate silhouette may change.',
                              'Original scenes, native payloads, artwork and paint variants retained.',
                              'Fourfold triangles does not imply fourfold recovered detail.',
                              'One-car trial; broader rollout requires visual acceptance.']}
    doc['extras']['enhancement'] = report
    doc['extras']['sourceProfile'] = 'gran-turismo-enhanced-v1'
    doc['extras']['claim_limits'] = doc['extras'].get('claim_limits', []) + report['claimLimits']
    output = encode(doc, binary)
    # Exercise the production static decoder/baker before publishing a derivative.
    bake_car('GT_ENHANCED_RX7', output, source_mode=False)
    report = copy.deepcopy(report)
    report['enhancedSha256'] = hashlib.sha256(output).hexdigest()
    return output, report


def enhance_further(data, iteration=1):
    """Append an 8x-further scene; retain the exact previous scenes and binary."""
    doc, original = read_glb(data)
    if iteration not in (1, 2):
        raise ValueError('Unsupported refinement iteration')
    profile = 'gran-turismo-enhanced-v1' if iteration == 1 else 'gran-turismo-enhanced-8x-v1'
    if doc.get('extras', {}).get('sourceProfile') != profile:
        raise ValueError('Expected first-stage enhanced GT1 pilot')
    previous = doc['extras']['enhancement']
    pin = previous['sourceSha256'] if iteration == 1 else previous['recoveredSourceSha256']
    if previous['enhancedTriangles'] != 2080*8**(iteration-1) or pin != SOURCE_SHA256:
        raise ValueError('Unexpected first-stage pilot identity')
    binary = bytearray(original)
    old_scene = doc['scene']
    scene = copy.deepcopy(doc['scenes'][old_scene])
    scene['name'] = ('Enhanced LOD0 — 8x further artistic refinement' if iteration == 1 else
                     'Enhanced LOD0 — 133120 triangles artistic refinement')
    reports = []
    for i, index in enumerate(scene['nodes']):
        node = copy.deepcopy(doc['nodes'][index])
        pivot = node.get('extras', {}).get('nativePivotPositionMetres')
        refined, report = refine_eight(doc['meshes'][node['mesh']], doc, binary, pivot)
        report['name'] = node['name']
        reports.append(report)
        node['mesh'] = len(doc['meshes'])
        doc['meshes'].append(refined)
        scene['nodes'][i] = len(doc['nodes'])
        doc['nodes'].append(node)
    doc['scene'] = len(doc['scenes'])
    doc['scenes'].append(scene)
    report = {'schema': iteration+1, 'sourceSha256': hashlib.sha256(data).hexdigest(),
              'recoveredSourceSha256': SOURCE_SHA256, 'sourceId': previous['sourceId'],
              'originalScene': old_scene, 'enhancedScene': doc['scene'], 'meshes': reports,
              'recoveredTriangles': previous['originalTriangles'] if iteration == 1 else previous['recoveredTriangles'],
              'originalTriangles': sum(r['originalTriangles'] for r in reports),
              'enhancedTriangles': sum(r['enhancedTriangles'] for r in reports),
              'claimLimits': ['Artistic derived geometry, not recovered GT1 or real-car detail.',
                              'All earlier position samples and original part bounds fixed.',
                              'New samples stay within the original 0.2% per-part reference envelope; float32 rounding applies.',
                              'Original and earlier enhanced scenes, native payloads, artwork and paint variants retained.',
                              'Eightfold further triangles does not imply eightfold recovered detail.',
                              'One-car trial; broader rollout requires visual acceptance.']}
    doc['extras']['enhancementHistory'] = doc['extras'].get('enhancementHistory', [])+[previous]
    doc['extras']['enhancement'] = report
    doc['extras']['sourceProfile'] = 'gran-turismo-enhanced-8x-v1' if iteration == 1 else 'gran-turismo-enhanced-64x-v1'
    doc['extras']['claim_limits'] += report['claimLimits']
    output = encode(doc, binary)
    bake_car('GT_ENHANCED_8X_RX7', output, source_mode=False)
    report = copy.deepcopy(report)
    report['enhancedSha256'] = hashlib.sha256(output).hexdigest()
    return output, report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output-dir', type=Path, default=OUTPUT)
    parser.add_argument('--check', action='store_true', help='Compare deterministic pilot outputs without writing')
    args = parser.parse_args()
    data = SOURCE.read_bytes()
    if hashlib.sha256(data).hexdigest() != SOURCE_SHA256:
        raise ValueError('Pilot source changed; review the pinned input before regenerating')
    output, report = enhance(data)
    further, further_report = enhance_further(output)
    newest, newest_report = enhance_further(further, iteration=2)
    files = {MODEL: output, 'receipt.json': (json.dumps(report, indent=2, allow_nan=False)+'\n').encode(),
             FURTHER_MODEL: further, 'receipt-8x.json': (json.dumps(further_report, indent=2, allow_nan=False)+'\n').encode(),
             NEXT_MODEL: newest, 'receipt-133120.json': (json.dumps(newest_report, indent=2, allow_nan=False)+'\n').encode()}
    for name, payload in files.items():
        path = args.output_dir / name
        if args.check:
            if not path.is_file() or path.read_bytes() != payload:
                raise ValueError(f'Enhanced pilot is stale: {path}')
        else:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(payload)
    print(f'PASS GT1 enhanced pilot: {report["originalTriangles"]} -> {report["enhancedTriangles"]} triangles')
    print(f'PASS GT1 8x further: {further_report["originalTriangles"]} -> {further_report["enhancedTriangles"]} triangles')
    print(f'PASS GT1 8x again: {newest_report["originalTriangles"]} -> {newest_report["enhancedTriangles"]} triangles')


if __name__ == '__main__':
    main()
