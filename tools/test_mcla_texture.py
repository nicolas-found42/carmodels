"""Texture decoding on synthetic tiled surfaces: Xenos addressing, packed mips, DXT/ARGB texels and pack layout."""
import struct
import unittest

import mcla_texture
from mcla_texture import (DICTIONARY_VFTS, FORMATS, PACK_VFTS, SHADER_GROUP_VFTS, SHADER_VFTS, TEXTURE_VFTS,
                          TextureError, all_textures, decode, packed_offset, pixels, tiled_offset)
from test_mcla_resource import Builder

RED, BLUE = 0xF800, 0x001F
CODES = {'dxt1': 0x12, 'dxt5': 0x14, 'argb8888': 0x06}


def dxt1(c0, c1, indices):
    return struct.pack('<HHI', c0, c1, sum(i << (2 * k) for k, i in enumerate(indices)))


def dxt5(a0, a1, alpha_indices, colour):
    return bytes([a0, a1]) + sum(i << (3 * k) for k, i in enumerate(alpha_indices)).to_bytes(6, 'little') + colour


def swap16(raw):
    raw = bytearray(raw)
    raw[0::2], raw[1::2] = raw[1::2], raw[0::2]
    return bytes(raw)


def put_texture(b, name, width, height, kind, blocks, vft=TEXTURE_VFTS[0]):
    """A texture whose base level holds `blocks` {(bx, by): raw little-endian block} at their tiled offsets."""
    code = CODES[kind]
    _, block, size, swap = FORMATS[code]
    tex, d3d = b.alloc(0x40), b.alloc(0x34)
    pitch = (width + 31) // 32 * 32
    columns = pitch // block
    rows = ((height + block - 1) // block + 31) & ~31
    data = b.alloc(((columns + 31) & ~31) * rows * size, align=4096)
    dx, dy = packed_offset(width, height)
    for (bx, by), raw in blocks.items():
        at = data + tiled_offset(bx + dx // block, by + dy // block, columns, size.bit_length() - 1)
        b.data[at:at + size] = raw if kind == 'argb8888' else swap16(raw)
    b.put(tex, 'I', vft)
    b.put(tex + 0x18, 'IIHH', b.pointer(b.text(name)), b.pointer(d3d), width, height)
    b.put(tex + 0x27, 'B', 1)
    b.put(d3d + 0x1C, '6I', 1 << 31 | (pitch // 32) << 22 | 2, b.pointer(data) | swap << 6 | code,
          (width - 1) | (height - 1) << 13, 0, 0, 0)
    return tex, d3d


def put_dictionary(b, textures, vft=0):
    at, hashes, items = b.alloc(0x20), b.alloc(4 * len(textures)), b.alloc(4 * len(textures))
    b.put(at, 'II', vft, 0)
    b.put(at + 0x10, 'IHHIHH', b.pointer(hashes), len(textures), len(textures), b.pointer(items), len(textures), len(textures))
    for i, tex in enumerate(textures):
        b.put(hashes + 4 * i, 'I', 0x1000 + i)
        b.put(items + 4 * i, 'I', b.pointer(tex))
    return at


def build_pack(shader_name='BumpSpec'):
    b = Builder()
    root = b.alloc(0x50)
    zone, zone_d3d = put_texture(b, 'car_zone', 8, 8, 'dxt1', {(0, 0): dxt1(RED, BLUE, [0] * 16),
                                                               (1, 1): dxt1(RED, BLUE, [1] * 16)})
    trim, _ = put_texture(b, 'car_trim.dds', 128, 64, 'dxt5',
                          {(0, 0): dxt5(255, 0, [1] * 16, dxt1(BLUE, RED, [0] * 16)),
                           (31, 15): dxt5(0, 255, [7] * 16, dxt1(BLUE, RED, [1] * 16))})
    scratch, _ = put_texture(b, 'car_scratch', 32, 32, 'argb8888', {(31, 31): bytes([128, 1, 2, 3])}, TEXTURE_VFTS[1])
    own = put_dictionary(b, [trim, scratch])
    group, shaders = b.alloc(0x10), b.alloc(4)
    shader, values, types, names = b.alloc(0x40), b.alloc(16), b.alloc(4), b.alloc(16)
    vector, array = b.alloc(16), b.alloc(32)
    b.put(root, 'II', PACK_VFTS[0], 0)
    b.put(root + 0x0C, 'IIIII', b.pointer(group), 0, b.pointer(zone), 0, 0)
    b.put(group, 'IIIHH', SHADER_GROUP_VFTS[0], b.pointer(own), b.pointer(shaders), 1, 1)
    b.put(shaders, 'I', b.pointer(shader))
    b.put(shader, 'I', SHADER_VFTS[0])
    b.put(shader + 9, 'B', 3)
    b.put(shader + 0x10, 'I', b.pointer(values))
    b.put(shader + 0x18, 'H', 4)
    b.put(shader + 0x1C, 'I', b.pointer(types))
    b.put(shader + 0x24, 'I', b.pointer(names))
    b.put(shader + 0x30, 'I', b.pointer(b.text(shader_name)))
    b.put(shader + 0x38, 'I', b.pointer(b.text('T:/mc4/materials/paint.mtlgeo')))
    b.put(values, '4I', b.pointer(trim), b.pointer(vector), b.pointer(array), 0)
    b.put(types, '4B', 0, 1, 2, 0)
    b.put(names, '4I', 0xF1FE2B71, 0x1468B111, 0x12345678, 0x46B7C64F)
    b.put(vector, '4f', 1.0, 0.5, 0.25, 0.0)
    b.put(array, '8f', *range(8))
    data, virtual, physical = b.segment()
    return bytearray(data), virtual, physical, {'root': root, 'zone': zone, 'zone_d3d': zone_d3d, 'group': group,
                                                'shader': shader, 'own': own, 'trim': trim}


def build_dictionary():
    b = Builder()
    root, hashes, items = b.alloc(0x20), b.alloc(4), b.alloc(4)
    tex, _ = put_texture(b, 'mr_car.dds', 16, 16, 'dxt5', {(0, 0): dxt5(255, 255, [0] * 16, dxt1(RED, RED, [0] * 16))},
                         TEXTURE_VFTS[2])
    b.put(root, 'II', DICTIONARY_VFTS[0], 0)
    b.put(root + 0x10, 'IHHIHH', b.pointer(hashes), 1, 1, b.pointer(items), 1, 1)
    b.put(hashes, 'I', 0x99)
    b.put(items, 'I', b.pointer(tex))
    data, virtual, physical = b.segment()
    return bytearray(data), virtual, physical, root


def patched(data, at, fmt, *values):
    data = bytearray(data)
    struct.pack_into('>' + fmt, data, at, *values)
    return data


def texel(rgba, width, x, y):
    o = (y * width + x) * 4
    return tuple(rgba[o:o + 4])


class Addressing(unittest.TestCase):
    def test_tiled_offset_is_a_permutation_of_the_padded_surface(self):
        for log in (2, 3, 4):
            for width, height in ((32, 32), (64, 32), (32, 96), (96, 64)):
                offsets = sorted(tiled_offset(x, y, width, log) >> log for y in range(height) for x in range(width))
                self.assertEqual(offsets, list(range(width * height)), (log, width, height))

    def test_packed_offsets(self):
        self.assertEqual(packed_offset(256, 256), (0, 0))
        self.assertEqual(packed_offset(16, 16), (16, 0))
        self.assertEqual(packed_offset(8, 4), (0, 16))
        self.assertEqual(packed_offset(4, 8), (16, 0))
        self.assertEqual(packed_offset(64, 8), (0, 16))


class Decoding(unittest.TestCase):
    def setUp(self):
        self.data, self.virtual, self.physical, self.at = build_pack()

    def test_pack_layout_shaders_and_dictionary(self):
        decoded, _ = decode(bytes(self.data), self.virtual, self.physical, 83)
        self.assertEqual(decoded['zone']['name'], 'car_zone')
        self.assertIsNone(decoded['max_damage'])
        group = decoded['shader_group']
        self.assertEqual([t['name'] for t in group['dictionary']], ['car_trim.dds', 'car_scratch'])
        self.assertEqual(group['dictionary'][0]['hash'], 0x1000)
        shader = group['shaders'][0]
        self.assertEqual((shader['name'], shader['file'], shader['draw_bucket']),
                         ('BumpSpec', 'T:/mc4/materials/paint.mtlgeo', 3))
        params = shader['params']
        self.assertEqual(params[0]['texture']['format'], 'dxt5')
        self.assertEqual(params[1]['value'], [[1.0, 0.5, 0.25, 0.0]])
        self.assertEqual(params[2]['value'], [[0.0, 1.0, 2.0, 3.0], [4.0, 5.0, 6.0, 7.0]])
        self.assertIsNone(params[3]['texture'])
        self.assertEqual([t['name'] for t in all_textures(decoded)], ['car_zone', 'car_trim.dds', 'car_scratch'])

    def test_texels(self):
        decoded, r = decode(bytes(self.data), self.virtual, self.physical, 83)
        zone = pixels(r, decoded['zone'])
        self.assertEqual(texel(zone, 8, 0, 0), (255, 0, 0, 255))
        self.assertEqual(texel(zone, 8, 7, 7), (0, 0, 255, 255))
        trim_texture, scratch_texture = decoded['shader_group']['dictionary']
        trim = pixels(r, trim_texture)
        self.assertEqual(texel(trim, 128, 0, 0), (0, 0, 255, 0))        # alpha index 1 of (255, 0) is 0
        self.assertEqual(texel(trim, 128, 127, 63), (255, 0, 0, 255))   # alpha index 7 of (0, 255) is 255
        scratch = pixels(r, scratch_texture)
        self.assertEqual(texel(scratch, 32, 31, 31), (1, 2, 3, 128))

    def test_dxt_modes(self):
        def block(raw, kind):  # The decoder's production path, from stored (8-in-16 swapped) bytes.
            rgba = mcla_texture._block_rgba(swap16(raw), kind)
            return [tuple(rgba[4 * i:4 * i + 4]) for i in range(16)]
        self.assertEqual(block(dxt1(BLUE, RED, [3] * 16), 'dxt1')[0], (0, 0, 0, 0))
        self.assertEqual(block(dxt1(BLUE, RED, [2] * 16), 'dxt1')[0], (127, 0, 127, 255))
        self.assertEqual(block(dxt1(RED, BLUE, [2] * 16), 'dxt1')[0], (170, 0, 85, 255))
        # DXT5 colour is always four-colour (opaque) and takes each texel's alpha from the alpha block.
        self.assertEqual(block(dxt5(10, 200, [6, 7, 2] + [0] * 13, dxt1(BLUE, RED, [3] * 16)), 'dxt5')[:3],
                         [(170, 0, 85, 0), (170, 0, 85, 255), (170, 0, 85, 48)])
        self.assertEqual(block(dxt5(200, 10, [2] + [0] * 15, dxt1(RED, BLUE, [1, 0] + [0] * 14)), 'dxt5')[:2],
                         [(0, 0, 255, 172), (255, 0, 0, 200)])
        self.assertEqual(len(block(dxt1(RED, BLUE, [0] * 16), 'dxt1')), 16)

    def test_texture_dictionary_resource(self):
        data, virtual, physical, _ = build_dictionary()
        decoded, r = decode(bytes(data), virtual, physical, 9)
        self.assertEqual(decoded['textures'][0]['hash'], 0x99)
        self.assertEqual(texel(pixels(r, decoded['textures'][0]), 16, 3, 3), (255, 0, 0, 255))

    def test_shader_group_slot_holding_a_block_map(self):
        data = patched(self.data, self.at['group'] + 4, 'I', 0)
        self.assertEqual(decode(bytes(data), self.virtual, self.physical, 83)[0]['shader_group']['dictionary'], [])
        data = patched(self.data, self.at['own'] + 0x1C, 'H', 1)
        self.assertEqual(decode(bytes(data), self.virtual, self.physical, 83)[0]['shader_group']['dictionary'], [])


class Rejections(unittest.TestCase):
    def setUp(self):
        self.data, self.virtual, self.physical, self.at = build_pack()

    def rejects(self, data, reason, kind=83):
        with self.assertRaisesRegex(TextureError, reason):
            decode(bytes(data), self.virtual, self.physical, kind)

    def test_texture_header(self):
        zone, d3d = self.at['zone'], self.at['zone_d3d'] + 0x1C
        self.rejects(patched(self.data, zone, 'I', 1), 'not a texture')
        self.rejects(patched(self.data, zone + 0x1C, 'I', 0), 'without a D3D header')
        fetch1 = struct.unpack_from('>I', self.data, d3d + 4)[0]
        self.rejects(patched(self.data, d3d + 4, 'I', fetch1 ^ 0x01), 'unsupported texture format')
        self.rejects(patched(self.data, d3d + 4, 'I', fetch1 ^ 0xC0), 'unexpected endian swap')
        self.rejects(patched(self.data, d3d + 4, 'I', fetch1 | 0x100), 'not page aligned')
        self.rejects(patched(self.data, d3d + 4, 'I', fetch1 & 0xFF | 0x50FFF000), 'outside its segment')
        fetch0 = struct.unpack_from('>I', self.data, d3d)[0]
        self.rejects(patched(self.data, d3d, 'I', fetch0 & 0x7FFFFFFF), 'untiled texture')
        self.rejects(patched(self.data, d3d, 'I', fetch0 & ~(0x1FF << 22)), 'pitch narrower')
        self.rejects(patched(self.data, d3d + 8, 'I', 15 | 7 << 13), 'fetch-constant size differs')
        self.rejects(patched(self.data, zone + 0x20, 'HH', 16, 16), 'fetch-constant size differs')

    def test_data_beyond_the_resource(self):
        trim = self.at['trim']
        d3d = struct.unpack_from('>I', self.data, trim + 0x1C)[0] & 0x0FFFFFFF
        fetch1 = struct.unpack_from('>I', self.data, d3d + 0x20)[0]
        moved = (fetch1 & 0xFF) | (0x50000000 | ((self.virtual - 1) & ~0xFFF))
        self.rejects(patched(self.data, d3d + 0x20, 'I', moved), 'outside its resource')

    def test_pack_group_and_shader(self):
        self.rejects(patched(self.data, 0, 'I', 1), 'not a texture pack')
        self.rejects(patched(self.data, self.at['root'] + 0x0C, 'I', 0), 'without a shader group')
        self.rejects(patched(self.data, self.at['group'], 'I', 1), 'not a shader group')
        self.rejects(patched(self.data, self.at['group'] + 0x0C, 'H', 0), 'without shaders')
        self.rejects(patched(self.data, self.at['shader'], 'I', 1), 'not a shader')
        self.rejects(self.data, 'holds no textures', kind=50)
        self.rejects(patched(self.data, 0, 'I', 1), 'not a texture dictionary', kind=9)

    def test_dictionary_arrays(self):
        self.rejects(patched(self.data, self.at['own'] + 0x1C, 'HH', 2, 1), 'count above its capacity')
        data, virtual, physical, root = build_dictionary()
        with self.assertRaisesRegex(TextureError, 'hash and texture counts differ'):
            decode(bytes(patched(data, root + 0x14, 'H', 2)), virtual, physical, 9)

    def test_required_null_arrays_raise_texture_errors(self):
        for offset in (0x10, 0x1C, 0x24):
            with self.subTest(offset=offset):
                self.rejects(patched(self.data, self.at['shader'] + offset, 'I', 0),
                             'without parameter arrays')
        data, virtual, physical, root = build_dictionary()
        items = struct.unpack_from('>I', data, root + 0x18)[0] & 0x0FFFFFFF
        for offset, reason in ((root + 0x10, 'without name hashes'), (items, 'null texture')):
            with self.subTest(offset=offset):
                with self.assertRaisesRegex(TextureError, reason):
                    decode(bytes(patched(data, offset, 'I', 0)), virtual, physical, 9)
        # Empty shaders and dictionaries still allow null arrays.
        empty_shader = patched(self.data, self.at['shader'] + 0x18, 'H', 0)
        for offset in (0x10, 0x1C, 0x24):
            empty_shader = patched(empty_shader, self.at['shader'] + offset, 'I', 0)
        decoded, _ = decode(bytes(empty_shader), self.virtual, self.physical, 83)
        self.assertEqual(decoded['shader_group']['shaders'][0]['params'], [])
        empty = patched(data, root + 0x10, 'IHHIHH', 0, 0, 0, 0, 0, 0)
        self.assertEqual(decode(bytes(empty), virtual, physical, 9)[0]['textures'], [])

    def test_texture_array_edges(self):
        b = Builder()
        at = b.alloc(16)
        b.put(at, 'IHH', 0, 0, 0)
        b.put(at + 8, 'IHH', 0, 1, 1)
        r = mcla_texture.Resource(*b.segment())
        self.assertEqual(mcla_texture.texture_array(r, at), [])
        with self.assertRaisesRegex(TextureError, 'without items'):
            mcla_texture.texture_array(r, at + 8)

    def test_struct_errors_become_texture_errors(self):
        original = mcla_texture.shader_group
        mcla_texture.shader_group = lambda *_: struct.unpack('>I', b'')
        try:
            self.rejects(self.data, 'unpack requires')
        finally:
            mcla_texture.shader_group = original


if __name__ == '__main__':
    unittest.main(verbosity=2)
