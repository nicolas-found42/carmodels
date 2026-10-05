#!/usr/bin/env python3
"""Recover source-named child ownership and distance-root inputs without guessing states."""
import static_inputs
import argparse
from collections import Counter
import hashlib
import json
import math
from pathlib import Path
import struct
import sys

ROOT = Path(__file__).resolve().parents[1]
SOURCE = static_inputs.bundle_path()
OUT = ROOT / 'research/evidence/continuation'


def sha(data):
    return hashlib.sha256(data).hexdigest()


def names(data):
    """Ten offset arrays read by FUN_00123908, bounded by the leading pool end."""
    end, = struct.unpack_from('<I', data)
    if not 8 <= end <= len(data):
        raise ValueError('name pool end outside input')
    tables, cursor = [], 4
    for _ in range(10):
        if cursor + 4 > end:
            raise ValueError('name count outside pool')
        count, = struct.unpack_from('<I', data, cursor)
        cursor += 4
        if count > (end - cursor) // 4:
            raise ValueError('name offsets outside pool')
        table = []
        for index in range(count):
            offset, = struct.unpack_from('<I', data, cursor + 4 * index)
            if not 0 <= offset < end:
                raise ValueError('name offset outside pool')
            stop = data.find(b'\0', offset, end)
            if stop < 0:
                raise ValueError('unterminated source name')
            value = data[offset:stop].decode('ascii')
            if not value or any(ord(c) < 32 or ord(c) > 126 for c in value):
                raise ValueError('invalid source name')
            table.append({'index': index, 'offset': offset, 'name': value})
        cursor += count * 4
        tables.append(table)
    if any(item['offset'] < cursor for table in tables for item in table):
        raise ValueError('name overlaps offset tables')
    return tables


def join(data, parsed):
    tables = names(data)
    if len(parsed['later']['records']) != len(tables[0]):
        raise ValueError('root-name and later-record counts differ')
    records = []
    for entry in parsed['later']['records']:
        nodes, stack, roots = [], [], []
        for span in entry.get('nodes_2c', []):
            identifier, flags, *values = struct.unpack_from('<2I6f', data, span['offset'])
            if not all(math.isfinite(v) for v in values):
                raise ValueError('nonfinite node transform')
            if identifier >= parsed['geometry']['table']['count']:
                raise ValueError('node geometry outside table')
            depth = span['depth']
            while len(stack) > depth:
                stack.pop()
            if len(stack) != depth:
                raise ValueError('invalid node depth')
            index = len(nodes)
            node = {'index': index, 'offset': span['offset'], 'depth': depth,
                    'parent': stack[-1] if stack else None,
                    'geometry_record': identifier, 'serialized_flags': flags,
                    'translation': values[:3], 'rotation_inputs': values[3:],
                    'children': [], 'source_names': [], 'pairs': [],
                    'runtime_mutable': False}
            if depth:
                nodes[stack[-1]]['children'].append(index)
            else:
                roots.append(index)
            nodes.append(node)
            stack.append(index)
        for node, span in zip(nodes, entry.get('nodes_2c', [])):
            if len(node['children']) != span['children']:
                raise ValueError('parsed direct child count differs')
            for index in range(span['pairs']['count']):
                offset = span['pairs']['offset'] + index * 8
                raw_name, raw_child = struct.unpack_from('<2I', data, offset)
                name_id, child_id = raw_name & 65535, raw_child & 65535
                if name_id >= len(tables[1]) or child_id >= len(node['children']):
                    raise ValueError('named pair outside name/child table')
                target = node['children'][child_id]
                label = tables[1][name_id]['name']
                node['pairs'].append({'offset': offset, 'raw_words': [raw_name, raw_child],
                                      'name_id': name_id, 'child_index': child_id,
                                      'target': target, 'name': label})
                nodes[target]['source_names'].append(label)
            # FUN_00123078 marks the first pair-count children as mutable.
            # This is distinct from the pair's target index; retain both.
            if len(node['pairs']) > len(node['children']):
                raise ValueError('mutable prefix exceeds child allocation')
            for target in node['children'][:len(node['pairs'])]:
                nodes[target]['runtime_mutable'] = True
        thresholds = list(struct.unpack_from('<' + 'f' * entry['floats']['count'],
                                             data, entry['floats']['offset']))
        if not all(math.isfinite(v) for v in thresholds):
            raise ValueError('nonfinite distance thresholds')
        records.append({'record': entry['index'], 'name': tables[0][entry['index']]['name'],
                        'thresholds': thresholds, 'roots': roots, 'nodes': nodes,
                        'options': entry['options']})
    return {'name_tables': tables, 'records': records}


def distance_root(distance, thresholds, root_count, camera_scale=1.0, bias=0, minimum=0):
    """Scalar translation of FUN_00121cd0 with explicit runtime inputs.

    This predicts only the selected root. It does not invent observed globals,
    visibility bits, animation transforms, camera distance, or a final draw.
    """
    if not 1 <= root_count <= 255:
        raise ValueError('invalid runtime root count')
    if not all(math.isfinite(v) for v in [distance, camera_scale, *thresholds]):
        raise ValueError('nonfinite runtime selector input')
    if not thresholds or len(thresholds) < 2:
        return root_count - 1
    distance *= camera_scale
    index = 1
    while thresholds[index] < distance:
        index += 1
        if index >= len(thresholds):
            return root_count - 1
    index += bias - 1
    last = root_count - 1
    if last <= index:
        return root_count - 2 if root_count >= 3 else last
    if index < minimum:
        if minimum >= last:
            return root_count - 2 if root_count >= 3 else 0
        return minimum
    return index


def source_check(source, out):
    export = source / '.scratch/evidence/static-export.json'
    elfpath = source / 'games/ford-racing-2/extracted/SLES_517.05'
    elf = elfpath.read_bytes()
    static = json.loads(export.read_text())
    if sha(elf) != static['executable_sha256']:
        raise ValueError('ELF identity differs from static export')
    phoff, = struct.unpack_from('<I', elf, 28)
    phsize, phcount = struct.unpack_from('<2H', elf, 42)
    loads = []
    for i in range(phcount):
        kind, offset, va, _, size, *_ = struct.unpack_from('<8I', elf, phoff + i * phsize)
        if kind == 1:
            loads.append((va, va + size, offset))
    targets = ['001208d0', '00123908', '00123078', '00123758', '00123820',
               '00124e98', '001231c0', '001232a8', '00123450', '001217f8',
               '00121cd0', '0019b900', '0019c680', '0019bfe0', '0019a7b8',
               '0019a1b8', '00229080', '002296c8']
    rows, tested = [], 0
    for target in targets:
        f = next(f for f in static['functions'] if f['entry'] == target)
        for ins in f['instructions']:
            address = int(ins['address'], 16)
            block = next((b for b in loads if b[0] <= address < b[1]), None)
            if block is None:
                raise ValueError('instruction outside ELF load')
            expected = bytes.fromhex(ins['bytes'])
            offset = block[2] + address - block[0]
            if elf[offset:offset + len(expected)] != expected:
                raise ValueError('static instruction differs from original ELF')
            tested += 1
        decomp = source / '.scratch/mesh/codex-root/decompile-all-02/functions' / (target + '.c')
        text = decomp.read_text()
        (out / 'source').mkdir(exist_ok=True)
        (out / 'source' / decomp.name).write_text(text)
        rows.append({'entry': target, 'instructions': len(f['instructions']),
                     'decompilation_sha256': sha(decomp.read_bytes()),
                     'instructions_sha256': sha(json.dumps(f['instructions'], sort_keys=True).encode())})
    receipt = {'elf_sha256': sha(elf), 'static_export_sha256': sha(export.read_bytes()),
               'functions': rows, 'instructions_checked': tested, 'failures': 0}
    (out / 'assembly-source-byte-check.json').write_text(json.dumps(receipt, indent=2) + '\n')
    return receipt


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', type=Path, default=SOURCE)
    parser.add_argument('--output', type=Path, default=OUT)
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)
    sys.path.insert(0, str(args.source / 'tools'))
    import ps2_sections
    from corpus_binding import Baseline
    baseline = Baseline(args.source / 'games/ford-racing-2')
    archive = {e.path.lstrip('/'): e for e in baseline.entries('.ps2;1')}
    census = json.loads((ROOT / 'research/evidence/original-recovery/car-asset-census.json').read_text())
    counts, cars = Counter(), []
    for car in census['cars']:
        data = next((ROOT / 'reference/ford/cars' / car['code'] / 'model').iterdir()).read_bytes()
        if sha(data) != car['sha256'] or data != archive[car['source']].load():
            raise ValueError('car differs from pinned archive')
        result = join(data, ps2_sections.parse(data))
        counts['cars'] += 1
        for record in result['records']:
            counts['roots'] += len(record['roots'])
            counts['nodes'] += len(record['nodes'])
            counts['named_pairs'] += sum(len(n['pairs']) for n in record['nodes'])
            counts['mutable_nodes'] += sum(n['runtime_mutable'] for n in record['nodes'])
        cars.append({'code': car['code'], 'sha256': car['sha256'], **result})
    bytecheck = source_check(args.source, args.output)
    result = {'summary': dict(counts), 'provenance': baseline.provenance,
              'source_instructions_checked': bytecheck['instructions_checked'],
              'parser_sha256': sha((args.source / 'tools/ps2_sections.py').read_bytes()),
              'status': 'Static named ownership and explicit distance-root selection; runtime visibility unobserved.',
              'limits': ['Pair names identify child ownership; they do not prove that a child is drawn.',
                         'Camera scale, bias, minimum, mutable visibility and animation remain runtime inputs.',
                         'Geometry packet, GS shading and observed runtime fidelity remain open.'],
              'cars': cars}
    (args.output / 'assembly-semantics.json').write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps(result['summary']))
    print(json.dumps({'source_instructions_checked': bytecheck['instructions_checked']}))


if __name__ == '__main__':
    main()
