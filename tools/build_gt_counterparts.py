#!/usr/bin/env python3
"""Build a conservative GT1/GT4 candidate ledger and an attributed counterpart study.

Lexical overlap proposes candidates, never compatible parts. The pilot is an
unchanged GT4 scene with added attribution, not a recovered or fitted GT1 model.
"""
import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import re
import struct

from bake_models import IDENTITY, accessor, compose, node_transform, read_glb

ROOT = Path(__file__).resolve().parents[1]
PUBLIC = ROOT / 'dealership/public'
OUTPUT = PUBLIC / 'gt4-guided'
TARGET = 'simulation/_afo7n'
DONOR = 'mazd0076'
PILOT = 'rx7-type-r-91-counterpart.glb'
# The refinement subject. Distinct from TARGET: the counterpart study uses the
# displayed-name Type-R, while the refinement trial refines the Type-RB.
REFINEMENT_SOURCE = 'simulation/_afb7n'
COMPARISON = 'dealership/public/comparisons/gt1-gt4.json'
# Displayed-name/grade/year counterparts. Lexical labels only: a title asserts a
# displayed-name match, never regional or equipment equivalence.
PAIRS = [
    ('RX-7 Type R 1991', 'simulation/_afo7n', 'mazd0076'),
    ('NSX 1993', 'simulation/_hnsrn', 'hond0074'),
    ('FTO GPX 1994', 'simulation/_mfton', 'mits0030'),
    ('Impreza STI Version III 1996', 'simulation/_sipbn', 'subr0025'),
    ('Corvette Grand Sport 1996', 'simulation/_ccrvn', 'chev0006'),
    ("Silvia K\u2019s S13 1988", 'simulation/_ns13n', 'niss0005'),
]
MATCH = 'Matching displayed model/grade/year labels; region/equipment equivalence not established.'
SCOPE = ('Six displayed-name/grade/year counterparts plus one explicitly related trim. '
         'Default scenes, all visible body/wheel/tire instances; reflections/shadows omitted '
         'by source exporters. Renderer uses shared lighting; no native-game fidelity claim.')
# Each stage's GLB and its receipt; the receipt pins the GLB this measurement describes.
EDITIONS = [
    ('rx7-fd-type-rb-enhanced.glb', 'receipt.json', 'GT1 Type-RB \u00b7 2,080-triangle refinement'),
    ('rx7-fd-type-rb-enhanced-8x.glb', 'receipt-8x.json', 'GT1 Type-RB \u00b7 16,640-triangle refinement'),
    ('rx7-fd-type-rb-enhanced-133120.glb', 'receipt-133120.json',
     'GT1 Type-RB \u00b7 133,120-triangle refinement'),
]
STOP = set('type r rs rz rbr rb gtr gt gts turbo sport sports grand edition limited '
           'version sedan coupe convertible wagon cabriolet roadster racing race car '
           'special spec tuned ii iii iv v vi vii viii ix x a b c s j k japan'.split())
LIMITS = [
    'Candidates are lexical suggestions, not verified car or part interchangeability.',
    'No regions are approved for GT1 geometry transfer; unresolved equipment remains unresolved.',
    'The pilot retains GT4 geometry, UVs, textures, materials and paint variants unchanged.',
    'The pilot is a GT4-sourced counterpart study, not recovered or reconstructed GT1 geometry.',
    'Static previews do not establish physical-car accuracy or native game-render equivalence.',
]


def digest(data):
    return hashlib.sha256(data).hexdigest()


def json_bytes(value):
    return (json.dumps(value, indent=2, allow_nan=False) + '\n').encode()


def rows(data):
    result = {}
    for row in data['cars']:
        if row['code'] in result:
            raise ValueError('Duplicate source code')
        result[row['code']] = row
    return result


def tokens(name):
    # Exact lexical operations only: remove punctuation within model tokens,
    # omit years/numbers and generic equipment words; never infer car identity.
    name = re.sub(r"['`’]\d{2}\b", '', name.lower())
    return set(re.findall(r'[a-z][a-z0-9]*', name.replace('-', ''))) - STOP


def source(row, game):
    return {'game': game, 'code': row['code'], 'name': row['display_name'],
            'file': f'public/{game}/{row["file"]}', 'sha256': row['sha256']}


def ledger(gt1, gt4, pins):
    donor_tokens = {code: tokens(row['display_name']) for code, row in gt4.items()}
    frequency = Counter(t for ts in donor_tokens.values() for t in ts)
    entries = []
    for code, row in sorted(gt1.items()):
        verified = row['native_metadata']['identity']['status'] == 'verified'
        words = tokens(row['display_name']) if verified else set()
        candidates = []
        for donor, other in sorted(gt4.items()):
            shared = words & donor_tokens[donor]
            # A token shared by >10% of the catalog is not a useful model anchor.
            shared = {t for t in shared if frequency[t] <= len(gt4) / 10}
            if not shared:
                continue
            score = sum(1 / frequency[t] for t in sorted(shared))
            candidates.append({**source(other, 'gran-turismo-4'),
                               'specLabel': other.get('spec_label'),
                               'sharedTokens': sorted(shared), 'lexicalScore': round(score, 8),
                               'status': 'unreviewed', 'approvedRegions': []})
        candidates.sort(key=lambda c: (-c['lexicalScore'], c['code']))
        entries.append({'target': source(row, 'gran-turismo'), 'identityStatus':
                        row['native_metadata']['identity']['status'],
                        'status': 'unresolved-identity' if not verified else
                        'candidates-unreviewed' if candidates else 'no-lexical-candidate',
                        'candidateCount': len(candidates), 'candidates': candidates,
                        'approvedRegions': []})
    return {'schema': 1, 'sourceIndexes': pins, 'claimLimits': LIMITS,
            'candidateRule': 'Exact normalized token overlap; generic words and tokens in >10% '
                             'of GT4 names excluded. All suggestions retained; no match approvals.',
            'counts': dict(sorted(Counter(e['status'] for e in entries).items())), 'entries': entries}


def pinned_glb(public, row, game):
    base = (public / game).resolve()
    path = (base / row['file']).resolve()
    if not path.is_relative_to(base):
        raise ValueError('Source path escapes game directory')
    data = path.read_bytes()
    if digest(data) != row['sha256']:
        raise ValueError(f'{game}/{row["code"]}: source hash mismatch')
    return data


def scene_stats(data, label, relative_file, sha256, game):
    """Measure one exported default scene. Records only what the file itself states."""
    doc, binary = read_glb(data)
    result = {'game': game, 'code': '', 'name': label, 'file': relative_file, 'sha256': sha256,
              'bytes': len(data), 'scene': doc['scene'], 'triangles': 0,
              'bodyTriangles': 0, 'wheelTriangles': 0, 'otherTriangles': 0, 'parts': [],
              'paintVariants': len(doc.get('extensions', {}).get('KHR_materials_variants', {}).get('variants', []))}
    points, materials = [], set()

    def walk(index, parent, active):
        if index in active:
            raise ValueError('Cyclic scene')
        node = doc['nodes'][index]
        world = compose(parent, node_transform(node))
        if 'mesh' in node:
            name = node.get('name', '')
            count = 0
            for primitive in doc['meshes'][node['mesh']]['primitives']:
                if primitive.get('mode', 4) != 4:
                    raise ValueError('Non-triangle primitive')
                positions = accessor(doc, binary, primitive['attributes']['POSITION'], 3, 5126)
                indices = accessor(doc, binary, primitive['indices'], 1, 5125)
                if len(indices) % 3 or any(i[0] < 0 or i[0] >= len(positions) for i in indices):
                    raise ValueError('Invalid triangle indices')
                count += len(indices) // 3
                materials.add(primitive['material'])
                for i, in indices:
                    point = positions[i] + (1.,)
                    points.append(tuple(sum(world[j][k] * point[k] for k in range(4)) for j in range(3)))
            result['triangles'] += count
            if name == 'body' or name.startswith('Native body'):
                category = 'body'
            elif name.startswith(('Native wheel', 'wheel_', 'tire_')):
                category = 'wheel'
            else:
                category = 'other'
            result[category + 'Triangles'] += count
            result['parts'].append({'name': name, 'triangles': count, 'category': category})
        for child in node.get('children', []):
            walk(child, world, active | {index})

    for node in doc['scenes'][doc['scene']]['nodes']:
        walk(node, IDENTITY, set())
    if not points:
        raise ValueError('Empty default scene')
    if result['triangles'] != sum(result[k] for k in ('bodyTriangles', 'wheelTriangles', 'otherTriangles')):
        raise ValueError('Part categories do not account for every triangle')
    images = set()
    for i in materials:
        texture = doc['materials'][i].get('pbrMetallicRoughness', {}).get('baseColorTexture')
        if texture:
            images.add(doc['textures'][texture['index']]['source'])
    result['defaultTextureImages'] = []
    for i in sorted(images):
        view = doc['bufferViews'][doc['images'][i]['bufferView']]
        start = view.get('byteOffset', 0)
        png = binary[start:start+view['byteLength']]
        if png[:8] != b'\x89PNG\r\n\x1a\n':
            raise ValueError('Expected embedded PNG')
        width, height = struct.unpack_from('>II', png, 16)
        result['defaultTextureImages'].append({'image': i, 'width': width, 'height': height})
    result['defaultMaterials'] = len(materials)
    low = [min(p[j] for p in points) for j in range(3)]
    high = [max(p[j] for p in points) for j in range(3)]
    result['boundsMetres'] = {'min': low, 'max': high, 'width': high[0]-low[0],
                              'height': high[1]-low[1], 'length': high[2]-low[2]}
    return result


def measure(data, row, game):
    """Measure a recovered source model and reconcile it with its producer record."""
    result = scene_stats(data, row['display_name'], f'public/{game}/{row["file"]}',
                         digest(data), game)
    result['code'] = row['code']
    record = row['records'][0]
    expected = record['triangles'] + (record['wheel_triangles'] if game == 'gran-turismo' else 0)
    if result['triangles'] != expected:
        raise ValueError('Default scene triangle count differs from source record')
    return result


def edition(public, model, receipt_name, label):
    """Measure a committed derivative. Its receipt pins the exact GLB measured."""
    receipt = json.loads((public / 'gran-turismo-enhanced' / receipt_name).read_bytes())
    data = (public / 'gran-turismo-enhanced' / model).read_bytes()
    if digest(data) != receipt['enhancedSha256']:
        raise ValueError(f'{model}: derived hash differs from its receipt')
    result = scene_stats(data, label, f'public/gran-turismo-enhanced/{model}',
                         receipt['enhancedSha256'], 'gran-turismo')
    result['code'] = receipt['sourceId']
    if result['triangles'] != receipt['enhancedTriangles']:
        raise ValueError(f'{model}: measured triangles differ from its receipt')
    return result


def comparison(public, indices):
    """The measured GT1/GT4 sample. Every number is rederived from a pinned source GLB."""
    pairs = []
    for title, gt1_code, gt4_code in PAIRS:
        pairs.append({'title': title, 'match': MATCH,
                      'left': [measure(pinned_glb(public, indices['gran-turismo'][gt1_code], 'gran-turismo'),
                                       indices['gran-turismo'][gt1_code], 'gran-turismo')],
                      'right': measure(pinned_glb(public, indices['gran-turismo-4'][gt4_code], 'gran-turismo-4'),
                                       indices['gran-turismo-4'][gt4_code], 'gran-turismo-4')})
    refined = indices['gran-turismo'][REFINEMENT_SOURCE]
    editions = [measure(pinned_glb(public, refined, 'gran-turismo'), refined, 'gran-turismo')]
    editions += [edition(public, model, receipt, label) for model, receipt, label in EDITIONS]
    pairs.append({'title': 'Our RX-7 Type-RB trial vs related GT4 FD',
                  'match': 'Related FD comparison only: GT1 Type-RB has no exact GT4 named counterpart; '
                           'GT4 is Type R 1991. GT1 Type-RB year is unresolved.',
                  'left': editions,
                  'right': measure(pinned_glb(public, indices['gran-turismo-4'][DONOR], 'gran-turismo-4'),
                                   indices['gran-turismo-4'][DONOR], 'gran-turismo-4')})
    return {'schema': 1, 'scope': SCOPE, 'pairs': pairs}


def pilot(target, donor, target_data, donor_data):
    if target['display_name'] != "RX-7 FD '91 Type-R" or donor['display_name'] != "Mazda RX-7 Type R (FD, J) '91":
        raise ValueError('Pilot displayed identity changed; review counterpart again')
    left = measure(target_data, target, 'gran-turismo')
    right = measure(donor_data, donor, 'gran-turismo-4')
    report = {'schema': 1, 'edition': 'GT4-sourced RX-7 Type R 1991 counterpart study',
              'target': source(target, 'gran-turismo'), 'donor': source(donor, 'gran-turismo-4'),
              'identityStatus': 'displayed-name-match; region/equipment unresolved',
              'approvedGt1TransferRegions': [], 'claimLimits': LIMITS,
              'geometryPolicy': 'Entire GT4 document and binary retained; only attribution added.',
              'targetTriangles': left['triangles'], 'studyTriangles': right['triangles']}
    doc, binary = read_glb(donor_data)
    doc.setdefault('extras', {})['gt4GuidedStudy'] = report
    header = json.dumps(doc, separators=(',', ':'), allow_nan=False).encode()
    header += b' ' * (-len(header) % 4)
    output = (struct.pack('<5I', 0x46546c67, 2, 28+len(header)+len(binary), len(header), 0x4e4f534a)
              + header + struct.pack('<2I', len(binary), 0x004e4942) + binary)
    report = {**report, 'studySha256': digest(output), 'binarySha256': digest(binary),
              'file': f'public/gt4-guided/{PILOT}'}
    right.update({'name': report['edition'], 'file': report['file'], 'sha256': report['studySha256'],
                  'bytes': len(output), 'editionLabel': 'GT4-sourced study'})
    comparison = {'schema': 1, 'pairs': [{'title': 'RX-7 Type R 1991 · counterpart study',
                  'match': 'Displayed model/grade/year match. Region and equipment equivalence unresolved. '
                           'Right side uses unchanged GT4 geometry and artwork; no GT1 part transfer approved.',
                  'left': [left], 'right': right}]}
    return output, report, comparison


def products(public=PUBLIC):
    indices, pins = {}, {}
    for game in ('gran-turismo', 'gran-turismo-4'):
        data = (public / game / 'index.json').read_bytes()
        indices[game] = rows(json.loads(data))
        pins[game] = digest(data)
    target, donor = indices['gran-turismo'][TARGET], indices['gran-turismo-4'][DONOR]
    model, receipt, comparison_study = pilot(target, donor, pinned_glb(public, target, 'gran-turismo'),
                                             pinned_glb(public, donor, 'gran-turismo-4'))
    prefix = OUTPUT.relative_to(ROOT).as_posix()
    return {
        f'{prefix}/ledger.json': json_bytes(ledger(indices['gran-turismo'], indices['gran-turismo-4'], pins)),
        f'{prefix}/{PILOT}': model,
        f'{prefix}/receipt.json': json_bytes(receipt),
        f'{prefix}/comparison.json': json_bytes(comparison_study),
        COMPARISON: json_bytes(comparison(public, indices)),
    }


def stale_artifacts(generated, root=ROOT):
    """Committed artifacts whose bytes differ from the derivation, or that are absent."""
    stale = []
    for name, data in generated.items():
        path = Path(root) / name
        if not path.exists() or path.read_bytes() != data:
            stale.append(name)
    return sorted(stale)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--check', action='store_true')
    args = parser.parse_args()
    generated = products()
    if args.check:
        stale = stale_artifacts(generated)
        if stale:
            raise SystemExit('Stale GT4-guided artifact: ' + ', '.join(stale))
    else:
        for name, data in generated.items():
            path = ROOT / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(data)
    print('PASS GT4-guided ledger, counterpart study and measured comparison: '
          'all artifacts rederived; no part approvals inferred')


if __name__ == '__main__':
    main()
