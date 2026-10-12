"""Rebuild every GT native pair under three winding policies and measure body/wheel orientation.

Usage: python3 -I winding_variants.py <repo> <out.json> [<glb out dir>]
Optionally writes the per-variant GLBs for the dealership day cars to <glb out dir>/<variant>/.
"""
import importlib.util
import json
import math
import pathlib
import statistics as st
import struct
import sys

repo = pathlib.Path(sys.argv[1])
sys.path.insert(0, str(repo / 'tools'))
src = (repo / 'tools/gt_model.py').read_text()
OLD = """                indices.extend([base,base+2,base+1])
                if face['quad']:
                    indices.extend([base,base+3,base+2])"""
assert OLD in src
NEW = {
    'current': OLD,
    'no_swap': """                indices.extend([base,base+1,base+2])
                if face['quad']:
                    indices.extend([base,base+2,base+3])""",
    'per_triangle': """                for tri in ([0,1,2],[0,2,3]) if face['quad'] else ([0,1,2],):
                    a,b,c = (positions[3*(base+k):3*(base+k)+3] for k in tri)
                    u=[b[i]-a[i] for i in range(3)]; w=[c[i]-a[i] for i in range(3)]
                    g=[u[1]*w[2]-u[2]*w[1],u[2]*w[0]-u[0]*w[2],u[0]*w[1]-u[1]*w[0]]
                    n=[sum(normals[3*(base+k)+i] for k in tri) for i in range(3)]
                    t=[base+k for k in tri]
                    indices.extend(t if sum(g[i]*n[i] for i in range(3)) >= 0 else [t[0],t[2],t[1]])""",
}
mods = {}
for name, body in NEW.items():
    spec = importlib.util.spec_from_loader('gt_model_' + name, loader=None)
    m = importlib.util.module_from_spec(spec)
    exec(compile(src.replace(OLD, body), 'gt_model_' + name, 'exec'), m.__dict__)
    mods[name] = m


def load(d):
    n = struct.unpack_from('<I', d, 12)[0]
    doc = json.loads(d[20:20 + n])
    o = 20 + n
    bl = struct.unpack_from('<I', d, o)[0]
    return doc, d[o + 8:o + 8 + bl]


def acc(doc, b, i):
    a = doc['accessors'][i]
    v = doc['bufferViews'][a['bufferView']]
    w = {'SCALAR': 1, 'VEC2': 2, 'VEC3': 3}[a['type']]
    f = {5126: 'f', 5125: 'I'}[a['componentType']]
    flat = struct.unpack_from('<%d%s' % (a['count'] * w, f), b, v.get('byteOffset', 0))
    return [flat[k * w:(k + 1) * w] for k in range(a['count'])] if w > 1 else list(flat)


def measure(glb):
    doc, b = load(glb)
    body, wheel, body_out = [0, 0], [0, 0], [0, 0]
    body_pts = []
    prims = []
    for i in doc['scenes'][0]['nodes']:
        nd = doc['nodes'][i]
        is_wheel = 'wheel' in nd['name'].lower()
        for pr in doc['meshes'][nd['mesh']]['primitives']:
            P = acc(doc, b, pr['attributes']['POSITION'])
            prims.append((is_wheel, P, acc(doc, b, pr['attributes']['NORMAL']), acc(doc, b, pr['indices'])))
            if not is_wheel:
                body_pts += P
    car_c = [sum(p[k] for p in body_pts) / len(body_pts) for k in range(3)]
    for is_wheel, P, N, I in prims:
        cen = [sum(p[k] for p in P) / len(P) for k in range(3)]
        for t in range(0, len(I), 3):
            a, bb, c = P[I[t]], P[I[t + 1]], P[I[t + 2]]
            u = [bb[k] - a[k] for k in range(3)]
            v = [c[k] - a[k] for k in range(3)]
            g = [u[1] * v[2] - u[2] * v[1], u[2] * v[0] - u[0] * v[2], u[0] * v[1] - u[1] * v[0]]
            area = math.sqrt(sum(x * x for x in g)) / 2
            m = [(a[k] + bb[k] + c[k]) / 3 - (cen if is_wheel else car_c)[k] for k in range(3)]
            out = sum(g[k] * m[k] for k in range(3)) > 0
            if is_wheel:
                wheel[1] += area
                wheel[0] += area if out else 0
            else:
                n = [sum(N[I[t + j]][k] for j in range(3)) for k in range(3)]
                body[1] += area
                body[0] += area if sum(g[k] * n[k] for k in range(3)) > 0 else 0
                body_out[1] += area
                body_out[0] += area if out else 0
    return body[0] / body[1], body_out[0] / body_out[1], (wheel[0] / wheel[1] if wheel[1] else None)


index = json.loads((repo / 'gran-turismo/cars/index.json').read_text())
glb_dir = pathlib.Path(sys.argv[3]) if len(sys.argv) > 3 else None
res = {k: {'body': [], 'outward': [], 'wheel': []} for k in NEW}
by_variant = {}
for car in index['cars']:
    files = {pathlib.Path(a['file']).suffix: (repo / 'gran-turismo/cars' / a['file']).read_bytes() for a in car['assets']}
    for name, m in mods.items():
        glb, _ = m.build_glb(files['.car'], files['.tex'], car['id'])
        bo, ou, wh = measure(glb)
        res[name]['body'].append(bo)
        res[name]['outward'].append(ou)
        if wh is not None:
            res[name]['wheel'].append(wh)
        by_variant.setdefault('%s/%s/%s' % (name, car['mode'], car.get('variant')), []).append(bo)
        if glb_dir and car['mode'] == 'simulation' and car.get('variant') == 'day':
            code = 'GT_' + '_'.join(car['id'].split('/')).upper().replace('-', '_')
            (glb_dir / name).mkdir(parents=True, exist_ok=True)
            (glb_dir / name / (code + '.glb')).write_bytes(glb)


def q(s):
    s = sorted(s)
    return dict(n=len(s), min=round(s[0], 3), p10=round(s[len(s) // 10], 3), median=round(st.median(s), 3),
                max=round(s[-1], 3), below_half=sum(x < .5 for x in s), at_least_099=sum(x >= .99 for x in s))


summary = {k: {'body_ccw_agrees_with_stored_normal': q(v['body']),
               'body_ccw_points_away_from_car_centroid': q(v['outward']),
               'wheel_ccw_points_away_from_wheel_centroid': q(v['wheel']) if v['wheel'] else None}
           for k, v in res.items()}
summary['median_body_agreement_by_variant'] = {k: round(st.median(v), 3) for k, v in by_variant.items()}
pathlib.Path(sys.argv[2]).write_text(json.dumps(summary, indent=1) + '\n')
print(json.dumps(summary, indent=1))
