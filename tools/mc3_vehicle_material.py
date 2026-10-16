"""Retain original MC3 vehicle material graphs without choosing a display shader.

The graph is serialized native data, not an assertion that all specialized
binders or gameplay state have been emulated. Pass blocks retain source state
commands in order, including absent commands which inherit caller state.
"""

import hashlib
import json
from pathlib import Path
import struct

from mc3_tire_alpha import decode_state_commands
from mc3_textures import PARAMETER_CLASS, SLOT_CLASS, SLOT_NAME_POINTER



EVIDENCE = (Path(__file__).resolve().parents[1] / 'research/evidence/'
            'midnight-club-3-remix/previews/vehicle-material-native.json')
PROOF_SHA = 'd4b9cb2d70f505eb4ebce2b9812767f661d3cd38b57e142dae718b645dabf82e'
FRAGMENT_SHA = 'e58eacc793300f1fcc0d24c6efd9e0cf72509a50adac8615feaf97be12638e5d'
DECAL_FRAGMENT_SHA = '0967c3e00bc4290d987cdeb1e9ace29a1c52617a1e863ebc0b60551a51100b28'


def fragment_fixture():
    data = EVIDENCE.with_name('vehicle-material-fragments.json').read_bytes()
    need(hashlib.sha256(data).hexdigest() == FRAGMENT_SHA, 'vehicle material fragments changed')
    fixture = json.loads(data)
    extra = EVIDENCE.with_name('vehicle-material-decal-fragments.json').read_bytes()
    need(hashlib.sha256(extra).hexdigest() == DECAL_FRAGMENT_SHA, 'decal material fragments changed')
    delta = json.loads(extra)
    need(delta['source_sha256'] == fixture['source_sha256'] and
         delta['source_bytes'] == fixture['source_bytes'], 'decal material source mismatch')
    fixture['fragments'].extend(delta['fragments'])
    values = {row['offset'] - 48: list(struct.unpack('<4I', bytes.fromhex(row['hex'])))
              for row in delta['fragments']}
    def update(node):
        if node['class_id'] in (6, 7):
            need(node['source_offset'] in values, 'decal material child fragment missing')
            node['parameter_words'] = values[node['source_offset']]
        for child in node.get('children', []):
            update(child)
    for row in fixture['roots']:
        update(row['expected_root'])
    return fixture


def verify_fragment_source(data):
    """Rebind every retained test fragment and graph to the original PCK."""
    fixture = fragment_fixture()
    need(len(data) == fixture['source_bytes'] and
         hashlib.sha256(data).hexdigest() == fixture['source_sha256'],
         'vehicle material fixture source identity changed')
    for row in fixture['fragments']:
        raw = bytes.fromhex(row['hex'])
        need(data[row['offset']:row['offset'] + len(raw)] == raw,
             'vehicle material fragment differs from source')
    for row in fixture['roots']:
        actual = native_material(data, {'file_offset': row['offset']})['root']
        need(actual == row['expected_root'], 'vehicle material source graph changed')
    return {'fragments': len(fixture['fragments']), 'material_roots': len(fixture['roots'])}


def source_contract(executable=None, receipt=None):
    """Validate the bounded class/graph contract, optionally from original ELF."""
    proof = json.loads(EVIDENCE.read_text()) if receipt is None else receipt
    encoded = json.dumps(proof, sort_keys=True, separators=(',', ':')).encode()
    need(hashlib.sha256(encoded).hexdigest() == PROOF_SHA, 'vehicle material receipt changed')
    if executable is not None:
        from mc3_environment_raster import _read_elf
        need(hashlib.sha256(executable).hexdigest() == proof['source_executable_sha256'],
             'vehicle material executable identity mismatch')
        for pin in proof['intervals'].values():
            raw = _read_elf(executable, pin['start'], pin['end'] - pin['start'])
            need(hashlib.sha256(raw).hexdigest() == pin['sha256'], 'vehicle material source interval changed')
        for cls in proof['classes'].values():
            actual = [struct.unpack('<I', _read_elf(executable, cls['runtime_vtable'] + i, 4))[0]
                      for i in (36, 40, 60, 64)]
            need(actual == cls['vtable_methods_words'], 'vehicle material virtual methods changed')
    return proof


def need(condition, message):
    if not condition:
        raise ValueError(message)


def native_material(data, material, profile_delta=0, to_offset=None, source_ranges=None):
    """Read one root plus its original children/pass chain and texture inputs.

    ``material`` is a row from read_material_table/read_page_model. PPF callers
    must supply their page's serialized-pointer conversion explicitly. No
    guessed template-name-to-rendering rule changes the source graph.
    """
    need(isinstance(data, bytes) and len(data) >= 128, 'invalid native material carrier')
    base = struct.unpack_from('<I', data)[0]
    pointer = to_offset or (lambda value: value - base + 128)
    active, total = set(), [0]
    classes = source_contract()['classes']

    def bounds(offset, size):
        need(type(offset) is int and 0 <= offset <= offset + size <= len(data),
             'native material read outside carrier')
        if source_ranges is not None and size:
            source_ranges.append((offset, size))
        return offset

    def word(offset):
        return struct.unpack_from('<I', data, bounds(offset, 4))[0]

    def address(value, size=1):
        need(value != 0, 'null native material pointer')
        return bounds(pointer(value), size)

    def string(value):
        offset = address(value)
        end = data.find(b'\0', offset, min(offset + 128, len(data)))
        need(end > offset, 'invalid native material string extent')
        bounds(offset, end + 1 - offset)
        raw = data[offset:end]
        need(all(32 <= c < 127 for c in raw), 'non-ASCII native material string')
        return raw.decode('ascii')

    def texture(value):
        offset = address(value, 16)
        kind = word(offset) - profile_delta
        if kind == PARAMETER_CLASS:
            name = string(word(offset + 8))
            second = word(offset + 12)
            target = pointer(second)
            embedded = (0 <= target <= len(data) - 4 and word(target) == SLOT_CLASS + profile_delta)
            return {'name': name, 'kind': 'slot' if embedded else 'hash',
                    'source_offset': offset, 'slot_offset': target if embedded else None,
                    'hash': None if embedded else second}
        if kind == SLOT_CLASS:
            return {'name': string(word(offset + SLOT_NAME_POINTER)), 'kind': 'inline-slot',
                    'source_offset': offset, 'slot_offset': offset, 'hash': None}
        raise ValueError('unknown native material texture reference class')

    def state(value):
        if value == 0:
            return []
        start = address(value)
        end = start
        for _ in range(15):
            header = data[bounds(end, 1)]
            end += 1
            if header == 255:
                return decode_state_commands(data[start:end])
            end = bounds(end, 4 if header & 192 else 1) + (4 if header & 192 else 1)
        raise ValueError('native material state exceeds command bound')

    def pass_chain(start):
        passes, seen = [], set()
        while start is not None:
            need(start not in seen and len(passes) < 16, 'native material pass cycle or limit')
            seen.add(start)
            bounds(start, 32)
            count = data[start + 24]
            need(count <= 8, 'native material texture count outside bound')
            listing = address(word(start + 8), count * 4) if count else None
            refs = [texture(word(listing + i * 4)) for i in range(count)]
            passes.append({'source_offset': start, 'program': data[start + 4],
                           'state': state(word(start)), 'textures': refs,
                           'texture_animation_pointer': word(start + 12),
                           'texture_stage_pointer': word(start + 16),
                           'texture_transform_pointer': word(start + 20),
                           'texture_flags': list(data[start + 25:start + 28]),
                           'source_words': [word(start + i * 4) for i in range(8)]})
            next_pass = word(start + 28)
            start = address(next_pass, 32) if next_pass else None
        return passes

    def node(offset):
        total[0] += 1
        need(total[0] <= 64 and offset not in active, 'native material child cycle or limit')
        active.add(offset)
        bounds(offset, 12)
        flags = word(offset + 4)
        class_id = flags & 127
        need(str(class_id) in classes, 'unsupported native material class')
        cls = classes[str(class_id)]
        bounds(offset, cls['object_bytes'])
        if source_ranges is not None:
            source_ranges.append((offset, 12 if class_id in (0, 0x2D) else 48))
        result = {'source_offset': offset, 'serialized_vtable': word(offset),
                  'class_id': class_id, 'flags': flags, 'draw_bucket': (flags >> 7) & 31,
                  'runtime_vtable': cls['runtime_vtable'], 'bind_address': cls['bind'],
                  'draw_address': cls['draw'],
                  'parameter_words': [word(offset + i) for i in range(48, cls['object_bytes'], 4)]}
        if class_id in (0, 0x2D):
            result.update(kind='texture-wrapper', texture=texture(word(offset + 8)))
        else:
            bounds(offset, 48)
            result.update(kind='material', template=string(word(offset + 40)) if word(offset + 40) else None,
                          passes=pass_chain(offset + 8))
            if class_id in (5, 0x22, 0x23):
                count = word(offset + 56)
                need(1 <= count <= 8, 'native material child count outside bound')
                listing = address(word(offset + 48), count * 4)
                result.update(kind='composite', selected=word(offset + 52),
                              children=[node(address(word(listing + i * 4), 12)) for i in range(count)])
            # Raw byte indices are retained, not replaced with guessed defaults.
            if class_id == 4:
                bounds(offset + 48, 4)
                result['paint_input_indices'] = list(data[offset + 48:offset + 52])
            elif class_id == 0xD:
                bounds(offset + 48, 20)
                result['window_input_indices'] = list(data[offset + 48:offset + 57])
                result['window_texture_variants'] = [texture(word(offset + i)) for i in (60, 64)]
            elif class_id == 0xE:
                bounds(offset + 60, 36)
                result['glass_light_indices'] = list(data[offset + 60:offset + 62])
                result['glass_light_mode'] = word(offset + 64)
                result['glass_rgba_words'] = [word(offset + i) for i in (80, 84, 88, 92)]
        active.remove(offset)
        return result

    offset = material.get('file_offset', material.get('ppf_file_offset'))
    graph = node(offset)
    return {'schema': 1, 'source_carrier_sha256': hashlib.sha256(data).hexdigest(),
            'root': graph, 'claim_limits': [
                'Original material graph and ordered state inputs; specialized binder execution is separate.',
                'Absent state commands inherit caller state; template names do not replace compiled state.',
                'Gameplay texture/animation pointers are retained as source addresses, not inferred effects.']}
