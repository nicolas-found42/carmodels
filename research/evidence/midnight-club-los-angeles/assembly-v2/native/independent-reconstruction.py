import hashlib
import json
import math
import struct
import sys
from pathlib import Path

sys.path.insert(0, 'tools')
from mcla_preview import Sources
from mcla_resource import Resource
import mcla_lzx
import mcla_model

out = Path(__file__).parent
source = Sources('midnight-club-los-angeles/cars')
records = json.loads(Path('.scratch/mcla-assembly-fix/global-calibration/results.json').read_text())['records']
identity = [[1., 0., 0.], [0., 1., 0.], [0., 0., 1.]]

def mul(a, b):
    return [[sum(a[i][k] * b[k][j] for k in range(3)) for j in range(3)] for i in range(3)]

def basis(euler):
    x, y, z = euler
    cx, sx, cy, sy, cz, sz = math.cos(x), math.sin(x), math.cos(y), math.sin(y), math.cos(z), math.sin(z)
    rx = [[1., 0., 0.], [0., cx, -sx], [0., sx, cx]]
    ry = [[cy, 0., sy], [0., 1., 0.], [-sy, 0., cy]]
    rz = [[cz, -sz, 0.], [sz, cz, 0.], [0., 0., 1.]]
    return mul(mul(rz, ry), rx)

rot_error = translation_error = 0.
bones_checked = 0
for record in records:
    compressed = source.read(record['file'])
    assert hashlib.sha256(compressed).hexdigest() == record['sha256']
    data, header = mcla_lzx.decompress(compressed)
    resource = Resource(data, header['virtual'], header['physical'])
    skel = resource.pointer(0x24)
    start = resource.pointer(skel)
    count = struct.unpack_from('>H', data, skel + 0x14)[0]
    assert count == record['bones']
    decoded = mcla_model.decode(data, header['virtual'], header['physical'])['skeleton']
    expected_r, expected_t = [], []
    for index in range(count):
        at = start + index * 224
        parent_ptr = struct.unpack_from('>I', data, at + 0x10)[0]
        parent = (resource.offset(parent_ptr) - start) // 224 if parent_ptr else -1
        local_t = struct.unpack_from('>3f', data, at + 0x20)
        local_r = basis(struct.unpack_from('>3f', data, at + 0x30))
        parent_r = expected_r[parent] if parent >= 0 else identity
        parent_t = expected_t[parent] if parent >= 0 else [0., 0., 0.]
        global_r = mul(parent_r, local_r)
        global_t = [parent_t[i] + sum(parent_r[i][j] * local_t[j] for j in range(3)) for i in range(3)]
        expected_r.append(global_r)
        expected_t.append(global_t)
        actual = decoded[index]['matrix']
        rot_error = max(rot_error, max(abs(actual[i + 4*j] - global_r[i][j]) for i in range(3) for j in range(3)))
        translation_error = max(translation_error, max(abs(actual[12+i] - global_t[i]) for i in range(3)))
        bones_checked += 1
assert len(records) == 1491 and bones_checked == 7453
assert rot_error < 1e-4 and translation_error < 1e-4
result = {'resources': len(records), 'bones': bones_checked, 'maximum_rotation_error': rot_error,
          'maximum_translation_error': translation_error,
          'limits': 'Independent source-byte/global Euler reconstruction compared with current decoder draw matrices; no game consumer or physical clearance proof.'}
(out / 'result.json').write_text(json.dumps(result, indent=2) + '\n')
print(json.dumps(result))
