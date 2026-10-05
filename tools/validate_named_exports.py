#!/usr/bin/env python3
"""Independently validate source-named GLB metadata against archived model bytes."""
import hashlib
import json
from pathlib import Path
import struct
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
import ps2_sections


def check(data, document):
    # Read the second offset table directly; do not import the join/exporter.
    cursor = 4
    count, = struct.unpack_from('<I', data, cursor)
    cursor += 4 + count * 4
    count, = struct.unpack_from('<I', data, cursor)
    labels = []
    for i in range(count):
        offset, = struct.unpack_from('<I', data, cursor + 4 + i * 4)
        labels.append(data[offset:data.index(b'\0', offset)].decode('ascii'))
    spans = ps2_sections.parse(data)['later']['records'][0]['nodes_2c']
    glb = {}
    for node in document['nodes']:
        if 'serializedNodeOffset' in node.get('extras', {}):
            glb.setdefault(node['extras']['serializedNodeOffset'], []).append(node)
    assert len(glb) == len(spans), 'source node coverage'
    expected = {s['offset']: {'names': [], 'mutable': False} for s in spans}
    count_pairs = 0
    for i, span in enumerate(spans):
        children = []
        for child in spans[i+1:]:
            if child['depth'] <= span['depth']:
                break
            if child['depth'] == span['depth'] + 1:
                children.append(child)
        assert len(children) == span['children']
        count_pairs += span['pairs']['count']
        for pair in range(span['pairs']['count']):
            a, b = struct.unpack_from('<II', data, span['pairs']['offset'] + pair * 8)
            expected[children[b & 65535]['offset']]['names'].append(labels[a & 65535])
        for child in children[:span['pairs']['count']]:
            expected[child['offset']]['mutable'] = True
    for offset, row in expected.items():
        for node in glb[offset]:
            actual = node['extras']
            assert actual['sourceNames'] == row['names'], f'names at {offset}'
            assert actual['runtimeMutable'] == row['mutable'], f'mutable at {offset}'
    return {'nodes': len(spans), 'pairs': count_pairs}


def main():
    rows = []
    for entry in json.loads((ROOT/'viewer/public/recovered/index.json').read_text())['cars']:
        blob = (ROOT/'viewer/public/recovered'/entry['file']).read_bytes()
        length, kind = struct.unpack_from('<II', blob, 12)
        assert kind == 0x4e4f534a
        document = json.loads(blob[20:20+length])
        data = next((ROOT/'reference/ford/cars'/entry['code']/'model').iterdir()).read_bytes()
        assert hashlib.sha256(data).hexdigest() == document['extras']['originalModelSha256']
        result = check(data, document)
        rows.append({'car': entry['code'], 'glb_sha256': hashlib.sha256(blob).hexdigest(), **result})
    # Corruption control uses the original parsed document and source bytes.
    named = next(n for n in document['nodes'] if n.get('extras', {}).get('sourceNames'))
    named['extras']['sourceNames'] = ['INVALID_SOURCE_NAME_CONTROL']
    try:
        check(data, document)
    except AssertionError:
        rejected = True
    else:
        raise AssertionError('corrupt name accepted')
    report = {'cars': len(rows), 'nodes': sum(r['nodes'] for r in rows),
              'pairs': sum(r['pairs'] for r in rows), 'corrupt_name_rejected': rejected,
              'failures': 0, 'results': rows,
              'limits': 'Checks source metadata; does not prove runtime visibility or rendering.'}
    (ROOT/'research/evidence/continuation/named-export-validation.json').write_text(json.dumps(report, indent=2)+'\n')
    print(json.dumps({k:v for k,v in report.items() if k != 'results'}))


if __name__ == '__main__':
    main()
