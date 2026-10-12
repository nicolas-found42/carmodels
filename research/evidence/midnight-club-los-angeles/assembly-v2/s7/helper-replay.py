"""Independent source-component and affine reconstruction replay; read-only native inputs."""
import hashlib
import json
import math
import sys
from pathlib import Path

sys.path.insert(0, str(Path('tools').resolve()))
import mcla_lzx
import mcla_model
import mcla_preview_geometry as helper

base = Path('.scratch/mcla-assembly-fix/s7-cleanup-independent')
source = Path('midnight-club-los-angeles/cars') / helper.TARGET_FILE
raw = source.read_bytes()
assert hashlib.sha256(raw).hexdigest() == helper.TARGET_SHA256
decoded, header = mcla_lzx.decompress(raw)
g = mcla_model.decode(decoded, header['virtual'], header['physical'])['models'][0]['geometries'][1]
before_digest = helper.geometry_digest(g)
out, receipt = helper.cleanup_preview_geometry(g, helper.TARGET_FILE, helper.TARGET_SHA256, 1)
assert helper.geometry_digest(g) == before_digest == helper.GEOMETRY_SHA256
prototype = json.loads(Path('.scratch/mcla-assembly-fix/s7-inner-door/fin-slim10-inverse-transpose-geometry.json').read_text())
assert json.loads(json.dumps(out)) == prototype

# Independently rediscover components by exact source coordinates, without using FIN_RANGES.
triangles = [g['indices'][i:i+3] for i in range(0, len(g['indices']), 3)]
owner = {}
neighbors = [set() for _ in triangles]
for t, row in enumerate(triangles):
    for v in row:
        p = tuple(g['position'][v])
        if p in owner:
            other = owner[p]
            neighbors[t].add(other)
            neighbors[other].add(t)
        else:
            owner[p] = t
components = []
unseen = set(range(len(triangles)))
while unseen:
    pending = [min(unseen)]
    component = set()
    while pending:
        t = pending.pop()
        if t not in unseen:
            continue
        unseen.remove(t)
        component.add(t)
        pending.extend(neighbors[t] - component)
    components.append(component)
assert sorted(map(len, components)) == [32]*6 + [38]*4 + [1633]*2
fins = [c for c in components if len(c) != 1633]
selected = [{t for a, b in ranges for t in range(a, b)} for ranges in helper.FIN_RANGES]
assert {frozenset(c) for c in fins} == {frozenset(c) for c in selected}
changed = set()
max_position_error = max_normal_error = 0.
for c in fins:
    ids = {i for t in c for i in triangles[t]}
    unique = sorted({tuple(g['position'][i]) for i in ids})
    mu = [sum(p[k] for p in unique)/len(unique) for k in range(3)]
    variance = sum((p[1]-mu[1])**2 for p in unique)
    bx = sum((p[1]-mu[1])*(p[0]-mu[0]) for p in unique)/variance
    bz = sum((p[1]-mu[1])*(p[2]-mu[2]) for p in unique)/variance
    side = math.copysign(1., mu[0])
    for i in ids:
        x, y, z = g['position'][i]
        center_x, center_z = mu[0]+bx*(y-mu[1]), mu[2]+bz*(y-mu[1])
        expected = (center_x+.1*(x-center_x)-side*.01, y, center_z+.1*(z-center_z))
        max_position_error = max(max_position_error, math.dist(expected, out['position'][i]))
        # Solve A^T n' = n directly; A has positive determinant .01.
        nx, ny, nz = g['normal'][i]
        transformed = [nx/.1, ny-.9*bx*(nx/.1)-.9*bz*(nz/.1), nz/.1]
        length = math.sqrt(sum(v*v for v in transformed))
        expected_normal = [v/length for v in transformed]
        max_normal_error = max(max_normal_error, math.dist(expected_normal, out['normal'][i]))
        assert g['position'][i][1] == out['position'][i][1]
    changed.update(ids)
assert len(changed) == 292
assert max_position_error < 1e-14 and max_normal_error < 1e-14
for i in range(len(g['position'])):
    if i not in changed:
        assert g['position'][i] == out['position'][i] and g['normal'][i] == out['normal'][i]
for k in g:
    if k not in ('position', 'normal'):
        assert g[k] == out[k]
groups = {}
for i, p in enumerate(g['position']):
    groups.setdefault(tuple(p), []).append(i)
assert all(len({out['position'][i] for i in ids}) == 1 for ids in groups.values())
evidence = {'source_sha256': helper.TARGET_SHA256, 'input_geometry_sha256': before_digest,
            'output_geometry_sha256': helper.geometry_digest(out),
            'independent_component_sizes': sorted(map(len, components)),
            'native_fin_components_equal_selected_ranges': True, 'selected_vertices': len(changed),
            'max_position_replay_error': max_position_error, 'max_normal_replay_error': max_normal_error,
            'positive_affine_determinant': .01, 'exact_prototype_geometry_equality': True,
            'unaffected_arrays_and_welds_exact': True, 'receipt': receipt,
            'limits': ['No zero-contact or native-game shader fidelity conclusion.',
                       'All106 output hashes and public dealership images require separate post-regeneration checks.']}
(base/'helper-replay.json').write_text(json.dumps(evidence, indent=2)+'\n')
print('PASS independent12 native components, ten selected fins,292 vertices, affine positions/normals, prototype and unchanged arrays; max errors', max_position_error, max_normal_error)
