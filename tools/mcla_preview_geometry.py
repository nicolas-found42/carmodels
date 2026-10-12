"""Source-pinned S7 divider thinning for the derived static preview only."""
import hashlib
import json
import math

TARGET_FILE = 'vp_sln_s7_06/resources/vehicle/vp_sln_s7_06/skirts0_lod_0.xrsc'
TARGET_SHA256 = '299e37d98e80e2399bb4eb9cef1d2a051f1119526e7e2c1b5022b758c205de5c'
GEOMETRY_SHA256 = '0a145fd85523a0634008c4f96a0493dc7f8ee0460787641f142b9c8ebc346886'
# These triangle ranges are the ten exact-coordinate components of the pinned native mesh.
FIN_RANGES = (
    ((1930, 1968),), ((1968, 2006),),
    ((2400, 2416), (2773, 2789)), ((2416, 2432), (2789, 2805)),
    ((2432, 2448), (2805, 2821)),
    ((2612, 2650),), ((2650, 2688),),
    ((2688, 2704), (2859, 2875)), ((2704, 2720), (2875, 2891)),
    ((2720, 2736), (2891, 2907)),
)
PROFILE = 's7-source-pinned-divider-thinning-v1'
CROSS_SECTION_SCALE = .1
MAXIMUM_DISPLACEMENT = .093437
LATERAL_INSET = .01


def geometry_digest(geometry):
    """Bind all decoded attributes and metadata, rather than trusting a supplied file pin."""
    try:
        encoded = json.dumps(geometry, sort_keys=True, separators=(',', ':'), allow_nan=False)
    except (TypeError, ValueError) as exc:
        raise ValueError('Preview geometry cannot be fingerprinted') from exc
    return hashlib.sha256(encoded.encode()).hexdigest()


def _bounds(points):
    return {'min': [min(p[k] for p in points) for k in range(3)],
            'max': [max(p[k] for p in points) for k in range(3)]}


def _cross(a, b):
    return (a[1]*b[2]-a[2]*b[1], a[2]*b[0]-a[0]*b[2], a[0]*b[1]-a[1]*b[0])


def _area(points, indices, triangles):
    total = 0.
    for t in triangles:
        a, b, c = (points[i] for i in indices[t*3:t*3+3])
        n = _cross(tuple(b[k]-a[k] for k in range(3)), tuple(c[k]-a[k] for k in range(3)))
        total += math.sqrt(sum(v*v for v in n))/2
    return total


def _thin_component(points, indices, triangles, output_points, output_normals, scale):
    """Positive X/Z contraction around native X(Y), Z(Y) centerlines; Y stays exact."""
    vertices = sorted({i for t in triangles for i in indices[t*3:t*3+3]})
    unique = sorted({tuple(points[i]) for i in vertices})
    mean_y = sum(p[1] for p in unique)/len(unique)
    mean_x = sum(p[0] for p in unique)/len(unique)
    mean_z = sum(p[2] for p in unique)/len(unique)
    variance = sum((p[1]-mean_y)**2 for p in unique)
    if variance <= 0 or not 0 < scale <= 1:
        raise ValueError('Divider centerline or contraction is invalid')
    slope = sum((p[1]-mean_y)*(p[2]-mean_z) for p in unique)/variance
    slope_x = sum((p[1]-mean_y)*(p[0]-mean_x) for p in unique)/variance
    residuals = [p[2]-mean_z-slope*(p[1]-mean_y) for p in unique]
    for i in vertices:
        x, y, z = points[i]
        center_z = mean_z+slope*(y-mean_y)
        center_x = mean_x+slope_x*(y-mean_y)
        side = 1 if mean_x > 0 else -1
        output_points[i] = (center_x+scale*(x-center_x)-side*LATERAL_INSET, y,
                            center_z+scale*(z-center_z))
    # Inverse transpose of the positive affine contraction preserves native smoothing seams.
    for i in vertices:
        nx, ny, nz = output_normals[i]
        n = (nx/scale, ny-(1-scale)/scale*(slope_x*nx+slope*nz), nz/scale)
        length = math.sqrt(sum(v*v for v in n))
        if not length or not math.isfinite(length):
            raise ValueError('Thinned divider has an invalid normal')
        output_normals[i] = tuple(v/length for v in n)
    moved = [i for i in vertices if tuple(points[i]) != output_points[i]]
    return {'source_triangle_ranges': _runs(triangles), 'triangles': len(triangles),
            'vertices': len(vertices), 'moved_vertices': len(moved),
            'input_bounds': _bounds([points[i] for i in vertices]),
            'output_bounds': _bounds([output_points[i] for i in vertices]),
            'centerline': {'mean_y': mean_y, 'mean_x': mean_x, 'mean_z': mean_z,
                           'x_per_y': slope_x, 'z_per_y': slope},
            'input_residual_width': max(residuals)-min(residuals),
            'output_residual_width': scale*(max(residuals)-min(residuals)),
            'maximum_displacement': max(math.dist(points[i], output_points[i]) for i in vertices),
            'input_surface_area': _area(points, indices, triangles),
            'output_surface_area': _area(output_points, indices, triangles)}


def _runs(values):
    result = []
    for v in sorted(values):
        if result and result[-1][1] == v:
            result[-1][1] += 1
        else:
            result.append([v, v+1])
    return result


def cleanup_preview_geometry(geometry, source_file, source_sha256, geometry_index, model_index=0):
    """Return unrelated geometry by identity; validate the complete target before deriving a copy."""
    if source_file != TARGET_FILE or model_index != 0 or geometry_index != 1:
        return geometry, None
    if source_sha256 != TARGET_SHA256:
        raise ValueError('S7 preview geometry source hash differs or is missing')
    if geometry_digest(geometry) != GEOMETRY_SHA256:
        raise ValueError('S7 decoded preview geometry differs from its pin')
    result = dict(geometry)
    result['position'] = list(geometry['position'])
    result['normal'] = list(geometry['normal'])
    components = []
    for ranges in FIN_RANGES:
        triangles = [t for start, stop in ranges for t in range(start, stop)]
        component = _thin_component(geometry['position'], geometry['indices'], triangles,
                                         result['position'], result['normal'], CROSS_SECTION_SCALE)
        component['source_component'] = ranges[-1][0]
        components.append(component)
    maximum = max(c['maximum_displacement'] for c in components)
    if maximum > MAXIMUM_DISPLACEMENT:
        raise ValueError('S7 divider thinning exceeds its verified displacement bound')
    receipt = {'profile': PROFILE, 'source_file': source_file, 'source_sha256': source_sha256,
               'model_index': model_index, 'geometry_index': geometry_index,
               'input_geometry_sha256': GEOMETRY_SHA256, 'output_geometry_sha256': geometry_digest(result),
               'input_vertex_count': geometry['vertex_count'], 'output_vertex_count': result['vertex_count'],
               'input_index_count': geometry['index_count'], 'output_index_count': result['index_count'],
               'new_vertices': 0, 'removed_triangles': 0,
               'input_bounds': _bounds(geometry['position']), 'output_bounds': _bounds(result['position']),
               'cross_section_scale': CROSS_SECTION_SCALE, 'lateral_inset_m': LATERAL_INSET,
               'maximum_displacement': maximum,
               'changed_triangles': sum(c['triangles'] for c in components),
               'changed_vertices': sum(c['moved_vertices'] for c in components),
               'surviving_upper_dividers': 4, 'surviving_lower_dividers': 6,
               'components': components,
               'reading': 'Contract each native divider in X/Z around its source-fitted X(Y), Z(Y) centerlines; '
                          'inset each side 10mm; preserve Y, indices and coordinate seams; inverse-transpose only divider normals.',
               'claim_limits': ['Derived preview cleanup, not recovered game deformation or shader behavior.',
                                'Finite blade-to-shell attachment contacts remain; this does not prove zero intersections.',
                                'All other primitives and native package bytes are outside this repair.']}
    return result, receipt
