#!/usr/bin/env python3
"""Verify the decoding of every Midnight Club: Los Angeles car model, texture, tuning and streaming map.

Inputs are the local extraction (`midnight-club-los-angeles/cars/`, re-derived from the disc by
`tools/extract_mcla_cars.py`); every file is pinned by the SHA-256 the committed `index.json` records.
Each RSC5 file of types 63 (models), 9 and 83 (textures), 50 (tuning) and 19 (streaming maps) is
decompressed and decoded with the repo-owned readers; texture base levels are decoded to RGBA.
The receipt records fixed facts per car (vertex, triangle, texture and texel counts, bounds, tuning
section sizes), digests of the decoded data, and the cross-file joins:

- every geometry's shader index lies inside its car's `.xtp` shader group, whose shader list the
  `.xtl` repeats;
- every tuning resource has seventeen sections whose classes, sizes and field types agree across cars.

Controls corrupt real resources and require each corruption to be rejected for its own reason.
`--write` establishes the receipt; a normal run must reproduce it. `--available` exits 0 only when the
local extraction is present.
"""
from concurrent.futures import ProcessPoolExecutor
import hashlib
import json
import os
from pathlib import Path
import struct
import sys

import mcla_lzx
import mcla_model
from mcla_resource import Resource, string_records
import mcla_texture
import mcla_tuning
import verifier_common

ROOT = Path(__file__).resolve().parents[1]
CARS = ROOT / 'midnight-club-los-angeles/cars'
RECEIPT = ROOT / 'research/evidence/midnight-club-los-angeles/decoding.json'
TYPES = {63: 'model', 9: 'texture-dictionary', 83: 'texture-pack', 50: 'tuning', 19: 'streaming-map'}
LIMITS = [
    'Structures are decoded to the fixed facts recorded here (counts, sizes, bounds, digests); a decoded value '
    'is a reading of its layout, checked for internal consistency, not against game execution.',
    'Textures: mip level 0 only; DXT1/DXT5/ARGB8888 are the only formats on the car files. Shader parameters '
    'other than textures are recorded by name hash; their meaning is not established.',
    'Tuning: field names are not on the disc; fields are typed 32-bit words by offset, so their meaning '
    '(mass, torque, grip and so on) is unknown.',
    'Shader binding (geometry shader index -> the car .xtp shader group) is a reading supported by the index '
    'range join over all cars, not by rendering in the game.',
]


class VerifyError(ValueError):
    pass


need = verifier_common.make_need(VerifyError)


def digest(*parts):
    h = hashlib.sha256()
    for part in parts:
        h.update(part if isinstance(part, bytes) else json.dumps(part, sort_keys=True).encode())
    return h.hexdigest()


def model_facts(decoded):
    h = hashlib.sha256()
    shaders = []
    for model in decoded['models']:
        for g in model['geometries']:
            for channel in g['channels']:
                values = g[channel]
                h.update(channel.encode())
                h.update(b''.join(struct.pack('>%dd' % len(v), *v) if isinstance(v[0], float) else bytes(v)
                                  for v in values) if values else b'')
            h.update(struct.pack('>%dH' % len(g['indices']), *g['indices']))
            shaders.append(g['shader'])
    facts = mcla_model.summary(decoded)
    facts.update(root_bone=decoded['skeleton'][0]['name'] if decoded['skeleton'] else None,
                 max_shader=max(shaders), sha256=h.hexdigest())
    return facts


def texture_facts(decoded, r):
    rows = []
    for tex in mcla_texture.all_textures(decoded):
        rows.append({'name': tex['name'], 'size': [tex['width'], tex['height']], 'format': tex['format'],
                     'mips': tex['mips'], 'rgba_sha256': hashlib.sha256(mcla_texture.pixels(r, tex)).hexdigest()})
    facts = {'textures': len(rows), 'texels': sum(t['size'][0] * t['size'][1] for t in rows),
             'formats': sorted({t['format'] for t in rows}), 'sha256': digest(rows)}
    group = decoded.get('shader_group')
    if group:
        facts['shaders'] = [[s['name'], s['file']] for s in group['shaders']]
    return facts


def tuning_facts(decoded):
    return {'sections': [[s['slot'], s['class'], s.get('variant'), s['bytes']] for s in decoded['sections']],
            'types': [[s['slot'], [f['type'] for f in s['fields']]] for s in decoded['sections']],
            'sha256': digest(decoded)}


def decode_file(relative, kind, cars=None):
    data = (Path(cars or CARS) / relative).read_bytes()
    out, header = mcla_lzx.decompress(data)
    virtual, physical = header['virtual'], header['physical']
    if kind == 63:
        facts = model_facts(mcla_model.decode(out, virtual, physical))
    elif kind in (9, 83):
        decoded, r = mcla_texture.decode(out, virtual, physical, kind)
        facts = texture_facts(decoded, r)
    elif kind == 50:
        facts = tuning_facts(mcla_tuning.decode(out, virtual, physical))
    else:
        names = sorted(set(string_records(out, virtual)))
        facts = {'strings': len(names), 'sha256': digest(names)}
    return relative, kind, hashlib.sha256(data).hexdigest(), facts


def _star(args):
    return decode_file(*args)


def selected(index):
    rows = []
    for row in index['files']:
        source = row.get('source') or {}
        if source.get('resource_type') in TYPES:
            rows.append(row)
    return rows


def decode_all(rows, processes):
    jobs = sorted(((row['file'], row['source']['resource_type'], str(CARS)) for row in rows), key=lambda j: j[0])
    if processes <= 1:
        return [decode_file(*job) for job in jobs]
    with ProcessPoolExecutor(processes) as pool:
        return list(pool.map(_star, jobs, chunksize=8))


def car_rows(results, index):
    cars = {v['id']: {'id': v['id']} for v in index['vehicles']}
    for relative, kind, _sha, facts in results:
        car = relative.split('/', 1)[0]
        if car not in cars:
            continue
        row = cars[car]
        package = '/resources/vehicle/%s/' % car in relative
        if kind == 63 and package:
            for key in ('geometries', 'vertices', 'triangles'):
                row[key] = row.get(key, 0) + facts[key]
            row['models'] = row.get('models', 0) + 1
            row['max_shader'] = max(row.get('max_shader', -1), facts['max_shader'])
            if relative.endswith('/body_lod_0.xrsc'):
                row['body'] = {'bones': facts['bones'], 'bounds': facts['bounds']}
        elif kind in (9, 83):
            row['textures'] = row.get('textures', 0) + facts['textures']
            row['texels'] = row.get('texels', 0) + facts['texels']
            if package and relative.endswith(('.xtp', '.xtl')):
                row.setdefault('shaders', {})[relative.rsplit('.', 1)[1]] = facts['shaders']
        elif kind == 50 and package:
            row['tuning_sections'] = [s[3] for s in facts['sections']]
        elif kind == 19 and package:
            row['streaming_map_strings'] = facts['strings']
    out = []
    for car in sorted(cars):
        row = cars[car]
        shaders = row.pop('shaders', {})
        need(set(shaders) == {'xtp', 'xtl'}, car + ': missing .xtp or .xtl shader group')
        need(shaders['xtp'] == shaders['xtl'], car + ': .xtp and .xtl shader lists differ')
        need(row['max_shader'] < len(shaders['xtp']), car + ': geometry shader index outside the .xtp shader group')
        row['shader_count'] = len(shaders['xtp'])
        need('body' in row and 'tuning_sections' in row, car + ': missing body model or tuning')
        out.append(row)
    return out


def tuning_layout(results):
    """Per tuning slot: the class, size and field types every car agrees on."""
    layout = {}
    for _relative, kind, _sha, facts in results:
        if kind != 50:
            continue
        types = dict((slot, t) for slot, t in facts['types'])
        for slot, cls, variant, size in facts['sections']:
            entry = layout.setdefault(slot, {'class': cls, 'variant': variant, 'bytes': size, 'types': None})
            need((entry['class'], entry['variant'], entry['bytes']) == (cls, variant, size),
                 'tuning slot %d differs between cars' % slot)
            merged = entry['types'] or [set() for _ in types[slot]]
            for i, t in enumerate(types[slot]):
                merged[i].add(t)
            entry['types'] = merged
    for entry in layout.values():
        counts = {}
        for observed in entry.pop('types'):
            key = '/'.join(sorted(observed - {'zero'})) or 'zero'
            counts[key] = counts.get(key, 0) + 1
        entry['field_types'] = dict(sorted(counts.items()))
    return [dict(slot=slot, **layout[slot]) for slot in sorted(layout)]


def totals(results):
    out = {}
    for _relative, kind, _sha, facts in results:
        slot = out.setdefault(TYPES[kind], {'files': 0})
        slot['files'] += 1
        for key in ('geometries', 'vertices', 'triangles', 'textures', 'texels', 'strings'):
            if key in facts:
                slot[key] = slot.get(key, 0) + facts[key]
    for kind in out:
        out[kind]['sha256'] = digest(sorted([r[0], r[3]['sha256']] for r in results if TYPES[r[1]] == kind))
    return dict(sorted(out.items()))


# Controls: each corrupts a decompressed real resource and names the error it must raise.

def _geometry_offsets(out, header):
    r = Resource(out, header['virtual'], header['physical'])
    lod = r.pointer(8)
    model = r.pointer(r.pointer(lod))
    geometry = r.pointer(r.pointer(model + 4))
    return r, model, geometry


def model_controls(data):
    out, header = mcla_lzx.decompress(data)
    r, model, geometry = _geometry_offsets(out, header)
    vb, ib = r.pointer(geometry + 0x0C), r.pointer(geometry + 0x1C)
    first_index = r.offset(r.u32(ib + 8))
    first_vertex = r.offset(r.u32(vb + 0x18))
    fvf = r.pointer(vb + 0x10)

    def put(offset, raw):
        def mutate(buffer):
            buffer[offset:offset + len(raw)] = raw
        return mutate
    return out, header, [
        ('index equal to the vertex count', put(first_index, struct.pack('>H', r.u16(geometry + 0x34))),
         'index outside the vertex buffer'),
        ('vertex moved 1 km along x', put(first_vertex, struct.pack('>f', 1000.0)), 'outside its bounding sphere'),
        ('vertex format size off by four', put(fvf + 4, bytes([r.u8(fvf + 4) + 4])), 'vertex format size'),
        ('primitive type 5 (strip)', put(geometry + 0x36, struct.pack('>H', 5)), 'not a triangle list'),
        ('model VFT replaced', put(0, b'\0\0\0\1'), 'not a model resource'),
    ]


def texture_controls(data):
    out, header = mcla_lzx.decompress(data)
    r = Resource(out, header['virtual'], header['physical'])
    tex = r.pointer(0x14)  # the zone texture of a car .xtp
    d3d = r.pointer(tex + 0x1C)

    def xor(offset, mask):
        def mutate(buffer):
            buffer[offset] ^= mask
        return mutate
    return out, header, [
        ('fetch-constant width changed', xor(d3d + 0x1C + 8 + 3, 0x01), 'fetch-constant size differs'),
        ('format code low bit flipped', xor(d3d + 0x1C + 4 + 3, 0x01), 'unsupported texture format'),
        ('tiled flag cleared', xor(d3d + 0x1C, 0x80), 'untiled texture'),
        ('texture VFT replaced', xor(tex, 0xFF), 'not a texture'),
    ]


def tuning_controls(data):
    out, header = mcla_lzx.decompress(data)
    r = Resource(out, header['virtual'], header['physical'])
    sim, gyro = r.pointer(0x50 + 4 * 6), r.pointer(0x50 + 4 * 8)

    def copy(target, source):
        def mutate(buffer):
            buffer[target:target + 4] = buffer[source:source + 4]
        return mutate
    return out, header, [
        ('vehSim slot names the vehGyro class', copy(sim + 8, gyro + 8), 'slot 6 holds vehGyro, not vehSim'),
        ('tuning root VFT replaced', copy(0, 0x50), 'not a tuning resource'),
        ('section path pointer moved to the class name', copy(sim + 12, sim + 8), 'outside $/tune/vehicle/'),
    ]


def run_controls(results):
    bodies = [r[0] for r in results if r[1] == 63 and r[0].endswith('/body_lod_0.xrsc')]
    first = sorted(b for b in bodies if '/resources/vehicle/%s/' % b.split('/', 1)[0] in b)[0]
    car = first.split('/', 1)[0]
    pack = '%s/resources/vehicle/%s/%s.xtp' % (car, car, car)
    tune = '%s/resources/vehicle/%s/%s.xct' % (car, car, car)
    outcomes = []
    for path, build, decode in (
            (first, model_controls, lambda b, h: mcla_model.decode(bytes(b), h['virtual'], h['physical'])),
            (pack, texture_controls, lambda b, h: mcla_texture.decode(bytes(b), h['virtual'], h['physical'], 83)),
            (tune, tuning_controls, lambda b, h: mcla_tuning.decode(bytes(b), h['virtual'], h['physical']))):
        out, header, controls = build((CARS / path).read_bytes())
        decode(bytearray(out), header)  # the clean resource decodes
        for label, mutate, reason in controls:
            buffer = bytearray(out)
            mutate(buffer)
            try:
                decode(buffer, header)
            except (mcla_model.ModelError, mcla_texture.TextureError, mcla_tuning.TuningError) as error:
                need(reason in str(error), 'control %r failed for another reason: %s' % (label, error))
                outcomes.append({'file': path, 'mutation': label, 'rejected': True, 'reason': str(error)})
                continue
            raise VerifyError('control escaped: ' + label)
    # A wrong untiling (row-major blocks) must change the decoded pixels of the same texture.
    out, header = mcla_lzx.decompress((CARS / pack).read_bytes())
    decoded, r = mcla_texture.decode(out, header['virtual'], header['physical'], 83)
    tex = decoded['zone']
    right = mcla_texture.pixels(r, tex)
    original = mcla_texture.tiled_offset
    try:
        mcla_texture.tiled_offset = lambda x, y, width, log: (y * ((width + 31) & ~31) + x) << log
        wrong = mcla_texture.pixels(r, tex)
    finally:
        mcla_texture.tiled_offset = original
    need(wrong != right, 'control escaped: row-major untiling')
    outcomes.append({'file': pack, 'mutation': 'row-major instead of Xenos tiled addressing', 'rejected': True,
                     'reason': 'decoded pixels differ'})
    return outcomes


def derive(processes):
    index = json.loads((CARS / 'index.json').read_text())
    rows = selected(index)
    pins = {row['file']: row['sha256'] for row in rows}
    results = decode_all(rows, processes)
    for relative, _kind, sha, _facts in results:
        need(sha == pins[relative], relative + ' differs from the committed index')
    return {'schema': 1, 'tool': 'tools/verify_mcla_decoding.py',
            'decoders': ['tools/mcla_lzx.py', 'tools/mcla_model.py', 'tools/mcla_texture.py', 'tools/mcla_tuning.py',
                         'tools/mcla_resource.py'],
            'source': {'index': 'midnight-club-los-angeles/cars/index.json', 'disc_sha256': index['source']['sha256']},
            'totals': totals(results), 'tuning_layout': tuning_layout(results), 'cars': car_rows(results, index),
            'controls': run_controls(results), 'claim_limits': LIMITS}


def main(argv):
    if '--available' in argv:
        return 0 if (CARS / 'shared').is_dir() else 1
    if not (CARS / 'shared').is_dir():
        print('MISSING INPUT: the local MCLA extraction (run python3 tools/extract_mcla_cars.py)')
        return 1
    processes = int(next((a.split('=', 1)[1] for a in argv if a.startswith('--processes=')), os.cpu_count() or 1))
    try:
        receipt = derive(processes)
    except (VerifyError, ValueError, OSError) as error:
        print('VERIFY FAILED:', error)
        return 1
    summary = {kind: {k: v for k, v in facts.items() if k != 'sha256'} for kind, facts in receipt['totals'].items()}
    summary['cars'] = len(receipt['cars'])
    summary['controls_rejected'] = len(receipt['controls'])
    return verifier_common.finish(receipt, RECEIPT, argv, ROOT, summary)


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
