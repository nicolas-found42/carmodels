"""Read-only before/after attribute and native-pose comparison; one explicit repair address."""
import hashlib
import json
import math
import struct
import sys
from pathlib import Path

sys.path.insert(0, str(Path('tools').resolve()))
from bake_models import read_glb

BASE = Path('.scratch/mcla-assembly-fix/s7-cleanup-independent')
TARGET_CODE = 'vp_sln_s7_06'
TARGET_SOURCE = 'vp_sln_s7_06/resources/vehicle/vp_sln_s7_06/skirts0_lod_0.xrsc'
TARGET_NODE = TARGET_SOURCE + '@ss/model0'
TARGET_MODEL = 0
TARGET_GEOMETRY = 1
TARGET_SOURCE_HASH = '299e37d98e80e2399bb4eb9cef1d2a051f1119526e7e2c1b5022b758c205de5c'


def digest(data):
    return hashlib.sha256(data).hexdigest()


def array(doc, binary, at):
    entry = doc['accessors'][at]
    count = entry['count']
    assert count > 0 and not entry.get('sparse')
    width = {'SCALAR': 1, 'VEC2': 2, 'VEC3': 3, 'VEC4': 4}[entry['type']]
    size = {5121: 1, 5123: 2, 5125: 4, 5126: 4}[entry['componentType']] * width
    view = doc['bufferViews'][entry['bufferView']]
    assert view['buffer'] == 0
    step = view.get('byteStride', size)
    begin = view.get('byteOffset', 0) + entry.get('byteOffset', 0)
    assert step >= size and begin + (count - 1) * step + size <= view.get('byteOffset', 0) + view['byteLength'] <= len(binary)
    value = (binary[begin:begin + count * size] if step == size else
             b''.join(binary[begin + i * step:begin + i * step + size] for i in range(count)))
    if entry['componentType'] == 5126:
        assert all(math.isfinite(v) for (v,) in struct.iter_unpack('<f', value))
    return {'type': entry['type'], 'componentType': entry['componentType'], 'count': count,
            'normalized': entry.get('normalized', False), 'sha256': digest(value)}, value


def primitive(doc, binary, value):
    result = {'mode': value.get('mode', 4), 'material': value['material'], 'arrays': {}}
    raw = {}
    for key, at in dict(value['attributes'], indices=value['indices']).items():
        result['arrays'][key], raw[key] = array(doc, binary, at)
    assert result['arrays']['indices']['componentType'] == 5125, 'preview triangle indices must be UInt32 (componentType 5125)'
    vertex_count = result['arrays']['POSITION']['count']
    assert result['arrays']['indices']['count'] % 3 == 0
    assert all(index < vertex_count for (index,) in struct.iter_unpack('<I', raw['indices']))
    assert all(a['count'] == vertex_count for key, a in result['arrays'].items() if key != 'indices')
    return result


def compare(after_dir, write_receipt=True):
    baseline = json.loads((BASE / 'before-manifest.json').read_text())['records']
    records = []
    changed = []
    for row in baseline:
        code = row['code']
        before_bytes = Path(row['file']).read_bytes()
        assert digest(before_bytes) == row['before_glb_sha256']
        after_bytes = (after_dir / (code + '.glb')).read_bytes()
        if code != TARGET_CODE:
            assert before_bytes == after_bytes, ('unrelated model bytes changed', code)
        before, bb = read_glb(before_bytes)
        after, ab = read_glb(after_bytes)
        before_nodes = before['nodes']
        after_nodes = after['nodes']
        assert len(before_nodes) == len(after_nodes), code
        assert before['scenes'] == after['scenes'], code
        assert before['materials'] == after['materials'], code
        assert before.get('textures') == after.get('textures') and before.get('samplers') == after.get('samplers'), code
        assert len(before.get('images', [])) == len(after.get('images', [])), code
        for old, new in zip(before.get('images', []), after.get('images', [])):
            ov, nv = before['bufferViews'][old['bufferView']], after['bufferViews'][new['bufferView']]
            assert old.get('mimeType') == new.get('mimeType') and old.get('name') == new.get('name'), code
            assert bb[ov['byteOffset']:ov['byteOffset'] + ov['byteLength']] == ab[nv['byteOffset']:nv['byteOffset'] + nv['byteLength']], code
        geometry_count = 0
        for old, new in zip(before_nodes, after_nodes):
            assert old['name'] == new['name'] and old['matrix'] == new['matrix'], (code, old['name'])
            assert old['extras']['nativeModel'] == new['extras']['nativeModel'] and old['extras']['nativeBoneIndex'] == new['extras']['nativeBoneIndex'], (code, old['name'])
            old_mesh, new_mesh = before['meshes'][old['mesh']], after['meshes'][new['mesh']]
            assert old_mesh['name'] == new_mesh['name'] and len(old_mesh['primitives']) == len(new_mesh['primitives']), code
            for index, (op, np) in enumerate(zip(old_mesh['primitives'], new_mesh['primitives'])):
                a, b = primitive(before, bb, op), primitive(after, ab, np)
                geometry_count += 1
                if a == b:
                    continue
                assert code == TARGET_CODE and old['name'] == TARGET_NODE and index == TARGET_GEOMETRY, (code, old['name'], index)
                assert old['extras']['nativeModel'] == TARGET_MODEL
                assert a['material'] == b['material'] and a['mode'] == b['mode']
                assert set(a['arrays']) == set(b['arrays'])
                for field in a['arrays']:
                    old_array, new_array = a['arrays'][field], b['arrays'][field]
                    assert {k: v for k, v in old_array.items() if k != 'sha256'} == {k: v for k, v in new_array.items() if k != 'sha256'}
                    if field not in ('POSITION', 'NORMAL'):
                        assert old_array == new_array, ('non-position/normal target array changed', field)
                assert a['arrays']['POSITION']['sha256'] != b['arrays']['POSITION']['sha256']
                assert a['arrays']['NORMAL']['sha256'] != b['arrays']['NORMAL']['sha256']
                changed.append({'code': code, 'source': TARGET_SOURCE, 'source_sha256': TARGET_SOURCE_HASH,
                                'model': TARGET_MODEL, 'geometry': TARGET_GEOMETRY,
                                'node': old['name'], 'before': a, 'after': b,
                                'primitive_extras': np.get('extras'), 'record_extras': after['extras']})
        records.append({'code': code, 'before_sha256': digest(before_bytes), 'after_sha256': digest(after_bytes),
                        'node_matrices_bindings_unchanged': len(before_nodes), 'geometries_checked': geometry_count})
    assert len(records) == 106 and len(changed) == 1, (len(records), len(changed))
    source = Path('midnight-club-los-angeles/cars') / TARGET_SOURCE
    assert digest(source.read_bytes()) == TARGET_SOURCE_HASH
    repairs = changed[0]['record_extras'].get('preview_geometry_repairs')
    assert isinstance(repairs, list) and len(repairs) == 1
    receipt = repairs[0]
    assert receipt['source_file'] == TARGET_SOURCE, 'S7 repair receipt source file differs from the qualified native source'
    assert receipt['source_sha256'] == TARGET_SOURCE_HASH, 'S7 repair receipt source SHA256 differs from the qualified native source hash'
    assert receipt['model_index'] == TARGET_MODEL and receipt['geometry_index'] == TARGET_GEOMETRY
    assert receipt['input_vertex_count'] == receipt['output_vertex_count'] == 2376
    assert receipt['input_index_count'] == receipt['output_index_count'] == 10830
    assert receipt['new_vertices'] == receipt['removed_triangles'] == 0
    assert receipt['changed_vertices'] == 292 and receipt['changed_triangles'] == 344
    assert receipt['surviving_upper_dividers'] == 4 and receipt['surviving_lower_dividers'] == 6
    output = {'records': records, 'changed_geometry': changed, 'only_explicit_target_changed': True,
              'limits': ['Allowed repair is only S7 skirts0 source model0 geometry1; correctness of fin selection/cleanup must be reviewed independently.',
                         'Exact attribute-byte equality outside target, node matrices/bindings, embedded images/materials and UInt32 indices checked; no original game execution claimed.']}
    if write_receipt:
        (BASE / 'corpus-comparison.json').write_text(json.dumps(output, indent=2))
    print('PASS', len(records), 'models', sum(r['node_matrices_bindings_unchanged'] for r in records), 'unchanged poses/bindings',
          sum(r['geometries_checked'] for r in records), 'geometries; one explicitly addressed primitive changed')


if __name__ == '__main__':
    assert len(sys.argv) == 2, 'pass accepted after GLB directory'
    compare(Path(sys.argv[1]))
