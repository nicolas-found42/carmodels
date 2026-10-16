"""Bounded geometry decoding for the original SD garage and city-sky carriers.

The world layout packs normal W separately from the car layout's color plane.
Keep that lane and both UV sets verbatim; it is not a recovered color formula.
"""
import math
import struct
import base64
import hashlib
import json
from pathlib import Path

from mc3_pck import Pck, read_mesh_object

SHARED_TEXTURE_PROOF = (Path(__file__).resolve().parents[1] / 'research/evidence/'
                       'midnight-club-3-remix/previews/environment/shared-texture-native.json')
SHARED_TEXTURE_PIN_SHA = '705f8b2a593e554c29a7dceb5e1cc9d1655f24d1692d9411a609395b3ae73f55'


def shared_texture_contract(proof=None):
    from mc3_specular_native import EXECUTABLE_SHA
    proof = json.loads(SHARED_TEXTURE_PROOF.read_text()) if proof is None else proof
    if proof['source_sha256'] != EXECUTABLE_SHA:
        raise ValueError('shared texture receipt executable identity mismatch')
    pins = {key: proof[key] for key in ('intervals', 'selected_words', 'initial_data')}
    if hashlib.sha256(json.dumps(pins, sort_keys=True, separators=(',', ':')).encode()).hexdigest() != SHARED_TEXTURE_PIN_SHA:
        raise ValueError('native shared texture source pins changed')
    expected = {'file_palette_order': 'BGRA', 'native_alpha_max': 128,
                'alpha_formula': 'floor(source_alpha*128/255)',
                'format14_palette_entries': 256, 'format16_palette_entries': 16,
                'format16_nibble_order': 'low then high'}
    if proof['derived_contract'] != expected:
        raise ValueError('native shared texture contract changed')
    return expected


def shared_texture_from_executable(executable):
    """Re-derive every bounded shared-image proof from the original ELF."""
    from mc3_specular_native import EXECUTABLE_SHA
    if hashlib.sha256(executable).hexdigest() != EXECUTABLE_SHA:
        raise ValueError('native shared texture executable identity mismatch')
    if executable[:7] != b'\x7fELF\x01\x01\x01':
        raise ValueError('unsupported shared texture ELF')
    phoff = struct.unpack_from('<I', executable, 28)[0]
    width, count = struct.unpack_from('<HH', executable, 42)
    if width < 32 or count > 128 or phoff + width*count > len(executable):
        raise ValueError('invalid shared texture ELF segments')

    def read(start, size):
        matches = []
        for i in range(count):
            kind, offset, address, _, length = struct.unpack_from('<IIIII', executable, phoff+i*width)
            if kind == 1 and address <= start < start+size <= address+length:
                if offset+length > len(executable):
                    raise ValueError('truncated shared texture ELF segment')
                matches.append(executable[offset+start-address:offset+start-address+size])
        if len(matches) != 1:
            raise ValueError('missing or ambiguous shared texture ELF interval')
        return matches[0]

    proof = json.loads(SHARED_TEXTURE_PROOF.read_text())
    if proof['source_sha256'] != EXECUTABLE_SHA:
        raise ValueError('shared texture receipt executable identity mismatch')
    for interval in proof['intervals'].values():
        start, end = int(interval['start'], 16), int(interval['end'], 16)
        if hashlib.sha256(read(start, end-start)).hexdigest() != interval['sha256']:
            raise ValueError('native shared texture interval differs')
    for address, word in proof['selected_words'].items():
        if struct.unpack('<I', read(int(address, 16), 4))[0] != int(word, 16):
            raise ValueError('native shared texture instruction differs')
    for address, raw in proof['initial_data'].items():
        expected = bytes.fromhex(raw)
        if read(int(address, 16), len(expected)) != expected:
            raise ValueError('native shared texture initializer differs')
    return shared_texture_contract(proof)


def decode_native_shared_tex(data):
    """Decode native palette inputs for the authored garage environment images.

    524878 reads BGRA and converts alpha by floor(A*128/255), using the
    original PS2 alpha-range initializer61c294. The format16 expansion at
    5257b4..5257c4 proves low-nibble-first texels; native PSMT4 preserves that
    packing. Format14 uses the same palette reader with 256 entries.
    """
    shared_texture_contract()
    if len(data) < 14:
        raise ValueError('native shared texture lacks header')
    width, height, kind, levels = struct.unpack_from('<4H', data)
    if (width not in (16, 32, 64, 128, 256, 512)
            or height not in (16, 32, 64, 128, 256, 512)
            or kind not in (14, 16) or not 1 <= levels <= 8):
        raise ValueError('unsupported native shared texture profile')
    palette_count = 256 if kind == 14 else 16
    start = 14 + palette_count*4
    expected, w, h = start, width, height
    for _ in range(levels):
        expected += w*h if kind == 14 else (w*h+1)//2
        w, h = max(1, w//2), max(1, h//2)
    if len(data) != expected:
        raise ValueError('native shared texture palette or mip extent differs')
    palette = []
    for index in range(palette_count):
        blue, green, red, alpha = data[14+index*4:18+index*4]
        palette.append(bytes((red, green, blue, alpha*128//255)))
    if kind == 14:
        indices = data[start:start+width*height]
    else:
        indices = [nibble for value in data[start:start+(width*height+1)//2]
                   for nibble in (value & 15, value >> 4)][:width*height]
    rgba = b''.join(palette[index] for index in indices)
    return {'width': width, 'height': height, 'levels': levels,
            'rgba_base64': base64.b64encode(rgba).decode(),
            'rgba_sha256': hashlib.sha256(rgba).hexdigest(),
            'source_tex_sha256': hashlib.sha256(data).hexdigest(),
            'native_alpha_max': 128, 'file_palette_order': 'BGRA',
            'file_format': kind}


def decode_batches(planes):
    if not planes or any(p['cl'] > p['wl'] for p in planes):
        raise ValueError('garage VIF planes missing or use destination skip cycle')
    world = planes[0]['address'] == 0x9e
    first_address = 0x9e if world else 0x98
    headers = [i for i, p in enumerate(planes) if p['components'] in (1, 4)
               and p['bits'] == 32 and p['address'] in (first_address, 0x1c5)]
    if not headers or headers[0] != 0 or planes[0]['address'] != first_address:
        raise ValueError('garage mesh lacks a supported leading batch header')
    output = []
    for h, first in enumerate(headers):
        header = planes[first]
        if header['count'] != 2 or header['address'] not in (first_address, 0x1c5):
            raise ValueError('garage batch header layout differs')
        words = [v for row in header['values'] for v in row]
        scale = struct.unpack('<f', struct.pack('<I', words[0]))[0]
        count = words[1] if header['components'] == 1 else words[4]
        scales = {1/1024, 1/2048} if world else {1/256}
        if scale not in scales or not 1 <= count <= 48:
            raise ValueError('garage position scale or batch size differs')
        if header['components'] == 4:
            floats = struct.unpack('<4f', struct.pack('<4I', *words[:4]))
            if words[7] != count or not all(math.isfinite(x) for x in floats):
                raise ValueError('garage header count/float mismatch')
        origin = header['address']
        targets = {'positions': (origin + (0x62 if world else 0x56), (3,), (8, 16, 32) if world else (8, 16)),
                   'uvs': (origin + (0x32 if world else 0x2c), (2, 4), (8, 16, 32)),
                   'normals': (origin + 2, (3, 4) if world else (3,), (8,))}
        if not world:
            targets['colors'] = (origin + 0x80, (4,), (8,))
        arrays = {name: [None] * count for name in targets}
        last = headers[h+1] if h+1 < len(headers) else len(planes)
        for plane in planes[first+1:last]:
            candidates = [name for name, (address, widths, bits) in targets.items()
                          if plane['components'] in widths and plane['bits'] in bits
                          and address <= plane['address'] < address + count]
            if len(candidates) != 1:
                raise ValueError('unknown/ambiguous garage VIF attribute')
            name = candidates[0]
            start = plane['address'] - targets[name][0]
            if start + plane['count'] > count:
                raise ValueError('garage attribute exceeds vertex count')
            for i, value in enumerate(plane['values']):
                if arrays[name][start+i] is not None:
                    raise ValueError('overlapping garage VIF writes')
                arrays[name][start+i] = tuple(x-0x100000000 if x >= 0x80000000 else x
                                             for x in value) if plane['bits'] == 32 else tuple(value)
        if any(value is None for rows in arrays.values() for value in rows):
            raise ValueError('garage mesh lacks a complete vertex attribute')
        positions = [tuple(x*scale for x in row) for row in arrays['positions']]
        if not all(math.isfinite(x) for row in positions for x in row):
            raise ValueError('nonfinite garage position')
        normals = arrays['normals']
        output.append({'packet_offset': header['offset'], 'scale': scale,
                       'header_words': words, 'positions': positions,
                       'position_integers': arrays['positions'],
                       'uvs': [tuple(x/4096 for x in row[:2]) for row in arrays['uvs']],
                       'uv_integers': arrays['uvs'],
                       'lightmap_uvs': [tuple(x/4096 for x in row[2:]) for row in arrays['uvs']],
                       'normals': [tuple(x/128 for x in row[:3]) for row in normals],
                       'normal_integers': normals, 'adc': [row[0] & 1 for row in normals],
                       'normal_w_raw': [row[3] if len(row) == 4 else None for row in normals],
                       'colors': [tuple(x/255 for x in row[:3]) for row in arrays.get('colors', [])],
                       'color_integers': arrays.get('colors', []), 'world_layout': world})
    return output


def read_mesh(pck, offset):
    return read_mesh_object(pck, offset, batch_decoder=decode_batches)


def material_pass_inputs(pck, material):
    """Retain the bounded base-material pass bodies and their image bindings.

    Byte commands are decoded without assigning viewer material properties.
    The compiled body layout is shared by the base object (+8) and the linked
    subsequent pass bodies (+0). Texture parameters resolve their native slot.
    """
    from mc3_tire_alpha import decode_state_commands
    passes, seen = [], set()
    body = material + 8
    for _ in range(8):
        if body in seen:
            raise ValueError('cyclic garage material pass chain')
        seen.add(body)
        pck.bounds(body, 32)
        start = pck.pointer(pck.u32(body))
        end = start
        for _ in range(15):
            header = pck.data[pck.bounds(end)]
            end += 1
            if header == 255:
                break
            end += 4 if header & 0xc0 else 1
            pck.bounds(end - 1)
        else:
            raise ValueError('garage material state exceeds command bound')
        commands = decode_state_commands(pck.data[start:end])
        count = pck.data[body + 0x18]
        if count > 8:
            raise ValueError('garage material texture count outside bound')
        listing = pck.pointer(pck.u32(body + 8), count*4) if count else None
        slots = []
        for i in range(count):
            reference = pck.pointer(pck.u32(listing + i*4), 16)
            slot = reference
            if pck.u32(reference) == 0x7a20e0:
                slot = pck.pointer(pck.u32(reference + 12), 0xa0)
            if pck.u32(slot) != 0x7a2320:
                raise ValueError('unsupported garage pass texture reference')
            slots.append({'reference_offset': reference, 'slot_offset': slot,
                          'name': pck.text(pck.u32(slot + 0x78))})
        passes.append({'body_offset': body, 'state_offset': start,
                       'state_bytes_hex': pck.data[start:end].hex(),
                       'commands': commands, 'microprogram_index': pck.data[body + 4],
                       'textures': slots})
        following = pck.u32(body + 0x1c)
        if not following:
            return passes
        body = pck.pointer(following, 32)
    raise ValueError('garage material pass count outside bound')


def decode_prop_inputs(data):
    """Read the native SD garage category lists, retaining unresolved draw state.

    This is an input decoder, not a reflection-pass selection policy. Category
    zero carries five glow locators; category one carries nine static instances.
    The native factory relocates those separately (394290 -> 38f168).
    """
    pck = Pck(data, 'prop/sd_midnight_clear_garage_props.pck')
    from mc3_specular_native import prop_reflection_masks
    from mc3_model import native_rest_frames
    root = 128
    if pck.kind != 0x40 or pck.u32(root) != 0x7a9260:
        raise ValueError('unknown garage prop container')
    counts = [pck.u32(root + 0x10 + i*4) for i in range(29)]
    if counts != [5, 9] + [0]*27:
        raise ValueError('SD garage prop category counts differ')
    instances = []
    for category, count in enumerate(counts[:2]):
        listing = pck.pointer(pck.u32(root + 0x84 + category*4), count*4)
        for index in range(count):
            offset = pck.pointer(pck.u32(listing + index*4), 0x40)
            definition = pck.pointer(pck.u32(offset + 12), 0xb8)
            if pck.u32(definition + 0x28) != 0x7a9270:
                raise ValueError('unknown garage prop definition')
            record = {'category': category, 'index': index, 'offset': offset,
                      'flags_raw': pck.u32(offset + 8),
                      'definition_offset': definition,
                      'name': pck.text(pck.u32(definition + 8)),
                      'definition_flags_raw': pck.u32(definition + 0x94),
                      'definition_mesh_pointer_raw': pck.u32(definition + 0xb4),
                      'reflection_masks': prop_reflection_masks(
                          pck.u32(definition + 0x94), pck.u32(offset + 8))}
            if category == 0:
                if pck.u32(offset + 0x10) != 0x7a8a90:
                    raise ValueError('unknown garage glow instance profile')
                locator = pck.pointer(pck.u32(offset + 0x14), 0x24)
                effect = pck.pointer(pck.u32(locator + 0x1c), 0xb0)
                if pck.u32(effect) != 0x7b2140:
                    raise ValueError('unknown garage glow effect profile')
                position = struct.unpack_from('<3f', data, locator)
                if not all(math.isfinite(x) for x in position):
                    raise ValueError('nonfinite garage glow position')
                record.update({'locator_offset': locator, 'position_raw': position,
                               'locator_source_words': [pck.u32(locator+n*4) for n in range(9)],
                               'effect_offset': effect,
                               'effect_name': pck.text(pck.u32(effect+4)),
                               'effect_source_words': [pck.u32(effect+n*4) for n in range(44)],
                               'mesh': None})
            if category == 1:
                if (pck.u32(offset + 0x10) != 0x7a92a8
                        or pck.u32(definition + 0x2c) != 0x7a9298):
                    raise ValueError('unknown garage static instance profile')
                position = struct.unpack_from('<3f', data, offset + 0x14)
                rotation = struct.unpack_from('<3f', data, offset + 0x20)
                if not all(math.isfinite(x) for x in (*position, *rotation)):
                    raise ValueError('nonfinite garage instance transform')
                mesh_offset = pck.pointer(pck.u32(definition + 0xb4))
                record.update({'position_raw': position, 'rotation_raw': rotation,
                               'native_frame': native_rest_frames([{
                                   'rotation_raw': rotation, 'local_position': position,
                                   'parent': None}])[0],
                               'definition_flags_raw': pck.u32(definition + 0x94),
                               'reflection_masks': prop_reflection_masks(
                                   pck.u32(definition + 0x94), pck.u32(offset + 8)),
                               'mesh': read_mesh(pck, mesh_offset)})
            instances.append(record)
    return {'source': pck.fingerprint(), 'category_counts': counts,
            'material_collection_offset': pck.pointer(pck.u32(root + 12), 16),
            'instances': instances,
            'claim_limits': ['Source inputs only: normal W meaning and garage material '
                             'passes remain separate; no complete rendered environment is asserted.']}


def decode_garage(data):
    """Decode source-selected capture geometry and retain each shader pass input."""
    from mc3_environment_sky import decode_image_slot
    from mc3_materials import read_material_table
    from mc3_textures import material_bindings
    result = decode_prop_inputs(data)
    pck = Pck(data, result['source']['file'])
    selected = [i for i in result['instances'] if i.get('reflection_masks') and i.get('mesh')]
    used = sorted({draw['material'] for i in selected for draw in i['mesh']['draws']})
    materials = read_material_table(data, result['material_collection_offset'])
    output, images = {}, {}

    def texture(slot):
        name = pck.text(pck.u32(slot + 0x78))
        if name.startswith('__'):
            return {'name': name, 'runtime': True, 'slot_offset': slot}
        key = str(slot)
        if key not in images:
            images[key] = {'name': name, **decode_image_slot(pck, slot)}
        return {'name': name, 'image': key, 'slot_offset': slot}

    for index in used:
        material = materials[index]
        offset = material['file_offset']
        kind = material['vtable']
        flags = pck.u32(offset + 4)
        record = {'index': index, 'offset': offset, 'serialized_class': kind,
                  'flags_raw': flags, 'native_phase': (flags >> 7) & 31,
                  'reflection_phase_selected': ((flags >> 7) & 31) == 0}
        if kind == 0x7a1ef8:
            slot = pck.pointer(pck.u32(offset + 8), 16)
            if pck.u32(slot) == 0x7a20e0:
                slot = pck.pointer(pck.u32(slot + 12), 0xa0)
            if pck.u32(slot) != 0x7a2320:
                raise ValueError('unsupported garage texture handle payload')
            record.update({'kind': 'texture-handle', 'texture': texture(slot)})
        elif kind in (0x7a1f58, 0x7b2198):
            binding = material_bindings(data, material, 0xe80, pck.pointer)
            passes = material_pass_inputs(pck, offset)
            for entry in passes:
                for ref in entry['textures']:
                    ref.update(texture(ref['slot_offset']))
            record.update({'kind': 'compiled-material',
                           'template': binding['shader_template'], 'passes': passes})
        elif kind == 0x7a1fc8:
            # 2af9e8 low7=2 -> 2b5b58: inline parameter words, with
            # child references selected by the high-bit mask.
            count, children = (flags >> 22) & 7, flags >> 25
            if count != 5 or children != 1:
                raise ValueError('garage HDR parameter layout differs')
            slot = pck.pointer(pck.u32(offset + 8), 0xa0)
            if pck.u32(slot) != 0x7a2320:
                raise ValueError('garage HDR texture child is not an image')
            rgba = struct.unpack_from('<4f', data, offset + 12)
            if not all(math.isfinite(x) for x in rgba):
                raise ValueError('nonfinite garage HDR parameters')
            record.update({'kind': 'parameter-material', 'texture': texture(slot),
                           'parameter_count': count, 'child_mask': children,
                           'native_rgba_raw': rgba})
        else:
            # Preserve this class for its separately recovered native renderer.
            record.update({'kind': 'unresolved',
                           'raw_words': [pck.u32(offset + n*4) for n in range(8)]})
        output[str(index)] = record
    result.update({'selected_instances': [i['name'] for i in selected],
                   'materials': output, 'images': images})
    return result


def verify_fragment_source(data):
    """Re-derive every retained offline fragment from the original prop carrier."""
    path = (Path(__file__).resolve().parents[1] / 'research/evidence/'
            'midnight-club-3-remix/previews/tire-alpha-native/garage-packet-fragments.json')
    proof = json.loads(path.read_text())
    if hashlib.sha256(data).hexdigest() != proof['source']['sha256']:
        raise ValueError('garage fragment source identity mismatch')
    graph = proof['prop_graph']
    if len(data) != graph['source_bytes']:
        raise ValueError('garage fragment source size mismatch')
    spans = [*graph['retained_ranges'], *proof['material_graph']['retained_ranges'],
             {'offset': proof['packet_offset'],
             'bytes': proof['packet_bytes'], 'sha256': proof['packet_sha256']}]
    for span in spans:
        raw = data[span['offset']:span['offset']+span['bytes']]
        if hashlib.sha256(raw).hexdigest() != span['sha256']:
            raise ValueError('garage retained fragment differs from source')
    return {'source_sha256': proof['source']['sha256'], 'verified_fragments': len(spans)}


def garage_receipt(data):
    """Derive compact source input hashes without retaining private full carriers."""
    result = decode_garage(data)
    instances = []
    for instance in result['instances']:
        if not instance.get('reflection_masks') or not instance.get('mesh'):
            continue
        draws = instance['mesh']['draws']
        positions = [position for draw in draws for batch in draw['batches']
                     for position in batch['positions']]
        instances.append({
            'name': instance['name'], 'offset': instance['offset'],
            'definition_offset': instance['definition_offset'],
            'reflection_masks': instance['reflection_masks'],
            'flags_raw': instance['flags_raw'],
            'definition_flags_raw': instance['definition_flags_raw'],
            'position_raw': list(instance['position_raw']),
            'rotation_raw': list(instance['rotation_raw']),
            'draws': len(draws), 'vertices': len(positions),
            'mesh_offset': instance['mesh']['offset'],
            'local_bounds': [[min(p[i] for p in positions), max(p[i] for p in positions)]
                             for i in range(3)],
            'material_indices': sorted({draw['material'] for draw in draws})})
    images = {key: {k: value for k, value in image.items() if k != 'rgba_base64'}
              for key, image in result['images'].items()}
    materials = result['materials']
    # The command rows are a deterministic expansion of retained state hex;
    # avoid duplicating them throughout the compact proof receipt.
    for material in materials.values():
        for entry in material.get('passes', []):
            entry.pop('commands')
    glow_locators = [{key: instance[key] for key in (
        'offset', 'definition_offset', 'definition_flags_raw', 'definition_mesh_pointer_raw',
        'locator_offset', 'position_raw', 'locator_source_words', 'effect_offset')}
        for instance in result['instances'] if instance['category'] == 0]
    glow_effects = {str(instance['effect_offset']): {
        'name': instance['effect_name'], 'source_words': instance['effect_source_words']}
        for instance in result['instances'] if instance['category'] == 0}
    return {'schema': 1, 'source': result['source'], 'instances': instances,
            'materials': materials, 'images': images,
            'glow_locators': glow_locators, 'glow_effects': glow_effects,
            'claim_limits': [
                'Static source-selected inputs, not an original rendered environment capture.',
                'Prop transform Euler order follows native397810->240090; geometry and stored image bytes are decoded.',
                'Native material shader arithmetic, VU world color/lighting and GS rasterization remain separate.']}
