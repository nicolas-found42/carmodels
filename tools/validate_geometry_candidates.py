#!/usr/bin/env python3
"""Independently inspect the generated GLB subset; no exporter imports.

Checks container lengths, references, embedded PNG CRCs, accessor dimensions,
finite/unit attributes, extrema, triangle index bounds and scene tree ownership.
This checks artifact integrity, not the correctness of FR2 draw semantics.
"""
import hashlib
import json
import math
from pathlib import Path
import struct
import zlib

ROOT = Path(__file__).resolve().parents[1]


def check(path, expected):
    data = path.read_bytes()
    assert hashlib.sha256(data).hexdigest() == expected['sha256']
    assert struct.unpack_from('<3I', data) == (0x46546c67, 2, len(data))
    offset = 12
    chunks = []
    while offset < len(data):
        length, kind = struct.unpack_from('<2I', data, offset)
        assert length % 4 == 0 and offset + 8 + length <= len(data)
        chunks.append((kind, data[offset + 8:offset + 8 + length]))
        offset += 8 + length
    assert offset == len(data) and [k for k, _ in chunks] == [0x4e4f534a, 0x004e4942]
    doc, binary = json.loads(chunks[0][1]), chunks[1][1]
    assert doc['asset']['version'] == '2.0'
    assert 0 <= len(binary) - doc['buffers'][0]['byteLength'] <= 3
    views = doc['bufferViews']
    for v in views:
        assert v['buffer'] == 0 and v.get('byteOffset', 0) % 4 == 0
        assert v['byteLength'] > 0 and v.get('byteOffset', 0) + v['byteLength'] <= doc['buffers'][0]['byteLength']
    arrays = []
    for a in doc['accessors']:
        v = views[a['bufferView']]
        width = {'SCALAR': 1, 'VEC2': 2, 'VEC3': 3}[a['type']]
        fmt = {5125: 'I', 5126: 'f'}[a['componentType']]
        assert a['count'] > 0 and v['byteLength'] == a['count'] * width * 4
        values = [x[0] for x in struct.iter_unpack('<' + fmt, binary[v['byteOffset']:v['byteOffset'] + v['byteLength']])]
        assert all(math.isfinite(x) for x in values)
        if 'min' in a:
            assert a['min'] == [min(values[i::width]) for i in range(width)]
            assert a['max'] == [max(values[i::width]) for i in range(width)]
        arrays.append(values)
    triangles = vertices = 0
    for mesh in doc['meshes']:
        for p in mesh['primitives']:
            assert p['mode'] == 4 and 0 <= p['material'] < len(doc['materials'])
            position = doc['accessors'][p['attributes']['POSITION']]
            n = position['count']
            assert position['type'] == 'VEC3' and 'min' in position and 'max' in position
            for semantic, index in p['attributes'].items():
                assert doc['accessors'][index]['count'] == n
                if semantic == 'NORMAL':
                    values = arrays[index]
                    assert all(abs(math.sqrt(sum(x*x for x in values[i:i+3])) - 1) < 1e-6 for i in range(0, len(values), 3))
            indices = arrays[p['indices']]
            assert len(indices) % 3 == 0 and min(indices) >= 0 and max(indices) < n
            triangles += len(indices) // 3
            vertices += n
    assert triangles == expected['stats']['triangles'] and vertices == expected['stats']['vertices']
    for image in doc['images']:
        assert image['mimeType'] == 'image/png'
        v = views[image['bufferView']]
        png = binary[v['byteOffset']:v['byteOffset'] + v['byteLength']]
        assert png[:8] == b'\x89PNG\r\n\x1a\n'
        o = 8
        while o < len(png):
            n = struct.unpack_from('>I', png, o)[0]
            assert zlib.crc32(png[o+4:o+8+n]) == struct.unpack_from('>I', png, o+8+n)[0]
            o += 12 + n
        assert o == len(png)
    for t in doc['textures']:
        assert 0 <= t['source'] < len(doc['images']) and 0 <= t['sampler'] < len(doc['samplers'])
    for m in doc['materials']:
        t = m['pbrMetallicRoughness'].get('baseColorTexture')
        if t:
            assert 0 <= t['index'] < len(doc['textures'])
    nodes = doc['nodes']
    parents = {}
    for i, node in enumerate(nodes):
        if 'mesh' in node:
            assert 0 <= node['mesh'] < len(doc['meshes'])
        assert all(math.isfinite(x) for x in node.get('translation', []))
        for child in node.get('children', []):
            assert 0 <= child < len(nodes) and child not in parents
            parents[child] = i
    for i in range(len(nodes)):
        ancestors = {i}
        while i in parents:
            i = parents[i]
            assert i not in ancestors
            ancestors.add(i)
    for scene in doc['scenes']:
        assert all(0 <= i < len(nodes) and i not in parents for i in scene['nodes'])
    assert len(doc['scenes']) == 16 and doc['scene'] == 6
    return {'car': expected['code'], 'sha256': expected['sha256'], 'meshes': len(doc['meshes']),
            'nodes': len(nodes), 'scenes': len(doc['scenes']), 'textures': len(doc['images']),
            'vertices': vertices, 'triangles': triangles, 'status': 'pass'}


def main():
    folder = ROOT / 'viewer/public/recovered'
    index = json.loads((folder / 'index.json').read_text())
    results = [check(folder / e['file'], e) for e in index['cars']]
    receipt = {'status': 'pass', 'models': len(results), 'textures': sum(r['textures'] for r in results),
               'vertices': sum(r['vertices'] for r in results), 'triangles': sum(r['triangles'] for r in results),
               'scope': 'Independent integrity checks for this exporter subset; no complete Khronos validation or runtime equivalence.',
               'validator_sha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest(), 'results': results}
    (ROOT / 'research/evidence/original-recovery/glb-validation.json').write_text(json.dumps(receipt, indent=2) + '\n')
    print(json.dumps({k: v for k, v in receipt.items() if k != 'results'}))


if __name__ == '__main__':
    main()
