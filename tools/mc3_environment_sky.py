"""Decode the source-selected MC3 San Diego night environment sky, without styling."""

import base64
import hashlib
import json
from pathlib import Path
import struct

from mc3_pck import Pck, strip_indices
from mc3_garage import read_mesh
from mc3_textures import palette_csm1, indexed_to_rgba
from ps2_container import unswizzle8


def need(condition, message):
    if not condition:
        raise ValueError(message)


def decode_image(pck, handle):
    """The world texture handle selects one PSMT8/CLUT32 image and upload block."""
    need(pck.u32(handle) == 0x7a1ef8, 'unknown sky texture handle')
    slot = pck.pointer(pck.u32(handle + 8), 0xa0)
    result = decode_image_slot(pck, slot)
    result['source']['handle_offset'] = handle
    return result


def decode_image_slot(pck, slot):
    """Decode one explicitly selected world PSMT8/CLUT32 image slot."""
    need(pck.u32(slot) == 0x7a2320, 'unknown sky image class')
    tex0 = struct.unpack_from('<Q', pck.data, slot + 0x10)[0]
    need((tex0 >> 20) & 63 == 19 and (tex0 >> 51) & 15 == 0,
         'sky image is not PSMT8 with CLUT32')
    need((tex0 >> 34) & 1 == 1 and (tex0 >> 35) & 3 == 0,
         'sky TEX0 color function changed')
    width, height = 1 << ((tex0 >> 26) & 15), 1 << ((tex0 >> 30) & 15)
    need(16 <= width <= 256 and 16 <= height <= 256,
         'sky image dimensions outside measured profile')
    need(pck.u16(slot + 12) * 256 == width * height
         and pck.u16(slot + 14) * 256 == width * height + 1024,
         'sky image transfer extent differs from TEX0')
    descriptor = pck.pointer(pck.u32(slot + 0x48), 0x90)
    need(pck.data[descriptor + 0x1c:descriptor + 0x90] == b'\xcd' * 0x74,
         'sky upload padding differs from source profile')
    length = width * height
    start = pck.bounds(descriptor + 0x90, length + 1024 + 16)
    need(pck.data[start + length + 1024:start + length + 1040] == b'\xcd' * 16,
         'sky image upload extent mismatch')
    tex1 = struct.unpack_from('<Q', pck.data, slot + 0x88)[0]
    clamp = pck.data[slot + 0x85]
    need((tex1 >> 5) & 1 == 1 and (tex1 >> 6) & 7 == 4,
         'world image filtering differs from native linear profile')
    need(clamp in (0, 5), 'world image wrapping differs from native profile')
    indices = unswizzle8(pck.data[start:start + length], width, height)
    palette = pck.data[start + length:start + length + 1024]
    # Keep native 0..128 alpha. These are raw GPU input bytes, not display PNGs.
    rgba = indexed_to_rgba(indices, palette_csm1(palette), 1)
    return {'width': width, 'height': height, 'rgba_base64': base64.b64encode(rgba).decode(),
            'rgba_sha256': hashlib.sha256(rgba).hexdigest(),
            'sampler': {'filter': 'linear', 'fraction_bits': 4,
                        'wrap_s': 'clamp' if clamp & 3 == 1 else 'repeat',
                        'wrap_t': 'clamp' if (clamp >> 2) & 3 == 1 else 'repeat'},
            'source': {'slot_offset': slot,
                       'tex0': hex(tex0), 'upload_offset': start}}


def decode_sky(data):
    pck = Pck(data, 'city/sd/sd_midnight_clear.pck')
    need(pck.kind == 0x43 and pck.u32(128) == 0x7a0138, 'unknown MC3 city sky profile')
    sky = pck.pointer(pck.u32(128 + 0x190), 0x100)
    need(pck.u32(sky + 0x18) == 0x7a0178 and pck.u32(sky + 0x30) == 2,
         'unknown serialized sky object')
    # 561ec4 clears t0; 25c238 selects sky+38 when that flag is zero.
    mesh_offset = pck.pointer(pck.u32(sky + 0x38))
    mesh = read_mesh(pck, mesh_offset)
    collection = pck.pointer(pck.u32(128 + 0x10), 16)
    need(pck.u32(collection) == 0x7a1fb8, 'unknown sky texture collection')
    count, capacity = struct.unpack_from('<HH', data, collection + 8)
    need(count == capacity == 10, 'sky texture collection extent changed')
    array = pck.pointer(pck.u32(collection + 4), count * 4)
    used = sorted({draw['material'] for draw in mesh['draws']})
    need(used == [5, 6, 7, 8, 9], 'reflection sky texture ownership changed')
    textures = {str(index): decode_image(pck, pck.pointer(pck.u32(array + index * 4)))
                for index in used}
    primitives = []
    for draw in mesh['draws']:
        for batch in draw['batches']:
            primitives.append({'texture': draw['material'], 'positions': batch['positions'],
                               'uvs': batch['uvs'], 'colors_native': batch['color_integers'],
                               'indices': strip_indices(batch),
                               'source_packet_offset': batch['packet_offset']})
    return {'schema': 1, 'source': pck.fingerprint(), 'sky_offset': sky,
            'mesh_offset': mesh_offset, 'textures': textures, 'primitives': primitives,
            'native_initial_state': {
                'rotation_degrees': struct.unpack_from('<f', data, sky + 0x54)[0],
                'translation_offset': struct.unpack_from('<3f', data, sky + 0xe4),
                'invert_y': True},
            'claim_limits': ['Decoded source inputs; sky VU shading and runtime sky animation are separate.']}


def verify_fragment_source(data):
    """Rederive the offline fragment evidence from the complete original city PCK."""
    path = (Path(__file__).resolve().parents[1] / 'research/evidence/'
            'midnight-club-3-remix/previews/environment/sky-fragments.json')
    proof = json.loads(path.read_text())
    need(len(data) == proof['source_bytes']
         and hashlib.sha256(data).hexdigest() == proof['source_sha256'],
         'original city sky source identity differs')
    for span in proof['retained_ranges']:
        offset, length = span['offset'], span['bytes']
        need(0 <= offset < offset + length <= len(data), 'sky source fragment outside input')
        need(hashlib.sha256(data[offset:offset + length]).hexdigest() == span['sha256'],
             'sky source fragment differs')
    sky = decode_sky(data)
    for index, texture in sky['textures'].items():
        need(texture['rgba_sha256'] == proof['expected_rgba_sha256'][index],
             'original sky decoded image differs')
    for key in ('sky_offset', 'mesh_offset', 'native_initial_state'):
        need(json.loads(json.dumps(sky[key])) == proof['expected_sky'][key],
             'original sky selection or initial state differs')
    return sky
