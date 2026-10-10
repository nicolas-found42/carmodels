"""MC3 texture decoding, binding and display-policy controls.

Synthetic fixtures exercise every layout and each corruption separately; the
corpus checks decode every selected source texture and require the decoder
choices (block swizzle, palette order) to beat their alternatives.
"""
import json
import struct
import unittest

from bake_models import ROOT, read_glb
from mc3_materials import read_material_table
from mc3_model import bind_textures, build_glb
from mc3_pck import read_vehicle
from mc3_wheels import read_default_wheels
from mc3_textures import (SLOT_CLASS, TextureError, bind_material_textures, indexed_to_rgba,
                          material_bindings, palette_csm1, read_page_slots, read_slot_textures,
                          read_tex, shared_texture_rows, smoothness, texture_policy)
from ps2_container import _block_order8, unswizzle8

CARS = ROOT / 'midnight-club-3-remix/cars'
PARAMETER = 0x7A1260
BASE = 0x6800000


def palette_bytes(alpha=0x80):
    return b''.join(bytes((i, 255 - i, (i * 3) & 255, alpha)) for i in range(256))


def swizzled(linear, side):
    """Plane whose GS block order unswizzles back to ``linear``."""
    order = _block_order8(side, side)
    plane = bytearray(side * side)
    for pixel, source in enumerate(order):
        plane[source] = linear[pixel]
    return bytes(plane)


def linear_image(side):
    return bytes((x * 5 + y * 3) % 192 for y in range(side) for x in range(side))


def pad(data):
    """At least 16 padding bytes, then 16-byte alignment, as in the source heap."""
    data += b'\xcd' * 16
    while len(data) % 16:
        data.append(0xCD)


def slot_fixture(delta=0, levels=1, name=b'vp_test', width=0x100):
    data = bytearray(128)
    struct.pack_into('<4I', data, 0, BASE, 0x38E030, 1, 0)
    obj = bytearray(0xC0)
    struct.pack_into('<III', obj, 0, SLOT_CLASS + delta, 0, 0xE7)
    struct.pack_into('<I', obj, 0x0C, 0x01040000 | width)
    obj[0xA0:0xA0 + len(name) + 1] = name + b'\0'
    struct.pack_into('<I', obj, 0x78, BASE + 128 + 0xA0 - 128)
    data += obj
    pad(data)
    image = linear_image(256)
    pixels = swizzled(image, 256)
    if levels == 1:
        data += pixels + palette_bytes()
    else:
        for filler in (pixels, bytes(16384), bytes(4096)):
            data += filler
            pad(data)
            data += bytes(28)
            pad(data)
        data += bytes(1024) + palette_bytes()
    pad(data)
    return bytes(data), image


class PaletteAndImageTests(unittest.TestCase):
    def test_csm1_is_a_bijection_that_swaps_blocks_eight_and_sixteen(self):
        entries = bytes(i for i in range(256) for _ in range(4))
        order = [entry[0] for entry in palette_csm1(entries)]
        self.assertEqual(sorted(order), list(range(256)))
        self.assertEqual(order[:8], list(range(8)))
        self.assertEqual(order[8:16], list(range(16, 24)))
        self.assertEqual(order[16:24], list(range(8, 16)))
        self.assertEqual(order[24:32], list(range(24, 32)))
        with self.assertRaisesRegex(TextureError, '256 RGBA'):
            palette_csm1(bytes(1020))

    def test_alpha_scaling_clamps_and_rejects_bad_palettes(self):
        entries = [bytes((1, 2, 3, a)) for a in [0, 0x40, 0x80, 0xFF] * 64]
        out = indexed_to_rgba(bytes([0, 1, 2, 3]), entries, 2)
        self.assertEqual([out[i] for i in (3, 7, 11, 15)], [0, 128, 255, 255])
        self.assertEqual(indexed_to_rgba(bytes([1]), entries, 1)[3], 0x40)
        with self.assertRaisesRegex(TextureError, '256 RGBA'):
            indexed_to_rgba(b'\0', entries[:255], 2)
        with self.assertRaisesRegex(TextureError, '256 RGBA'):
            indexed_to_rgba(b'\0', [b'abc'] * 256, 2)


class EmbeddedSlotTests(unittest.TestCase):
    def test_every_profile_and_level_layout_unswizzles_to_the_source_image(self):
        for delta in (0, 0x200, 0x1308):
            for levels in (1, 4):
                with self.subTest(delta=delta, levels=levels):
                    data, image = slot_fixture(delta, levels)
                    found = read_slot_textures(data, delta)
                    self.assertEqual(list(found), ['vp_test'])
                    texture = found['vp_test']
                    self.assertEqual((texture['width'], texture['height'], texture['levels']), (256, 256, levels))
                    expected = indexed_to_rgba(image, palette_csm1(palette_bytes()), 2)
                    self.assertEqual(texture['rgba'], expected)

    def test_wrong_profile_and_non_image_slots_are_not_decoded(self):
        data, _ = slot_fixture(0)
        self.assertEqual(read_slot_textures(data, 0x200), {})
        changed = bytearray(data)
        struct.pack_into('<I', changed, 128 + 8, 0x5063)
        self.assertEqual(read_slot_textures(bytes(changed), 0), {})
        changed = bytearray(data)
        struct.pack_into('<I', changed, 128 + 12, 0x01040040)
        self.assertEqual(read_slot_textures(bytes(changed), 0), {})

    def test_layout_and_pointer_corruptions_are_rejected_for_their_own_reason(self):
        data, _ = slot_fixture(0)
        cases = {
            'short pixel block': (data[:-17 - 16] + data[-16:], 'measured layout'),
            'long pixel block': (data[:-16] + b'\x01' * 20 + data[-16:], 'measured layout'),
            'no padding after slot': (data[:128 + 0xC0] + data[128 + 0xC0:].replace(b'\xcd', b'\x01'), 'padding'),
        }
        for label, (changed, reason) in cases.items():
            with self.subTest(label):
                with self.assertRaisesRegex(TextureError, reason):
                    read_slot_textures(changed, 0)
        changed = bytearray(data)
        struct.pack_into('<I', changed, 128 + 0x78, 0x1000)
        with self.assertRaisesRegex(TextureError, 'name pointer'):
            read_slot_textures(bytes(changed), 0)
        changed = bytearray(data)
        changed[128 + 0xA0] = 0
        with self.assertRaisesRegex(TextureError, 'missing or duplicated'):
            read_slot_textures(bytes(changed), 0)
        twin = bytes(data) + bytes(data[128:128 + 0xC0]) + b'\xcd' * 0x80
        with self.assertRaisesRegex(TextureError, 'duplicated|name pointer'):
            read_slot_textures(twin, 0)

    def test_pixel_block_starting_with_padding_byte_is_not_mistaken_for_padding(self):
        data, image = slot_fixture(0)
        begin = data.index(b'\xcd' * 16) + 0x10
        changed = bytearray(data)
        order = _block_order8(256, 256)
        first = order.index(0)
        changed[begin + 0] = 0xCD
        found = read_slot_textures(bytes(changed), 0)['vp_test']
        entry = palette_csm1(palette_bytes())[0xCD]
        self.assertEqual(found['rgba'][first * 4:first * 4 + 4], bytes((entry[0], entry[1], entry[2], 255)))


class SharedTexTests(unittest.TestCase):
    @staticmethod
    def tex(width, height, levels, payload=None):
        body = b''
        w, h = width, height
        for _ in range(levels):
            body += bytes((i * 7) % 256 for i in range(w * h))
            w, h = max(1, w // 2), max(1, h // 2)
        palette = b''.join(bytes((i, 0, 0, i)) for i in range(256))
        return struct.pack('<7H', width, height, 14, levels, 1, 0, 0) + palette + (body if payload is None else payload)

    def test_levels_palette_and_alpha_are_read_without_scaling(self):
        texture = read_tex(self.tex(32, 16, 2))
        self.assertEqual((texture['width'], texture['height'], texture['levels']), (32, 16, 2))
        self.assertEqual(texture['rgba'][4:8], bytes((7, 0, 0, 7)))
        self.assertEqual(len(texture['rgba']), 32 * 16 * 4)

    def test_size_dimension_and_level_corruptions(self):
        good = self.tex(16, 16, 1)
        for changed, reason in ((good + b'\0', 'declared size'), (good[:-1], 'declared size'),
                                (self.tex(16, 16, 1, b'')[:20], 'shorter than'),
                                (struct.pack('<4H', 8, 16, 14, 1) + good[8:], 'bounds'),
                                (struct.pack('<4H', 16, 16, 14, 0) + good[8:], 'bounds'),
                                (struct.pack('<4H', 1024, 16, 14, 1) + good[8:], 'bounds')):
            with self.subTest(reason=reason, size=len(changed)):
                with self.assertRaisesRegex(TextureError, reason):
                    read_tex(changed)

    def test_divergent_duplicate_occurrences_are_rejected(self):
        rows = {'files': [{'file': f'shared/assets/{n}/vehicle/shared_texture/texture/a_tex.tex', 'sha256': s}
                          for n, s in ((1, 'a' * 64), (2, 'a' * 64))]}
        self.assertEqual(list(shared_texture_rows(rows)), ['a_tex'])
        rows['files'][1]['sha256'] = 'b' * 64
        with self.assertRaisesRegex(TextureError, 'differing duplicate'):
            shared_texture_rows(rows)
        rows = {'files': [{'file': 'shared/assets/1/vehicle/va_bus/texture/a_tex.tex', 'sha256': 'a' * 64}]}
        self.assertEqual(shared_texture_rows(rows), {})


KNOWN_TEMPLATES = {
    'aa_chrome', 'aa_trim', 'black_matte', 'car_decal', 'car_window', 'carbon_fiber', 'carpaint',
    'carpaint_novinyl', 'chrome', 'colored_glass', 'default_shiny', 'drop_shadow', 'emissive_brakelight',
    'emissive_coplight_pass1', 'emissive_coplight_pass2', 'emissive_headlight', 'emissive_reverselight',
    'emissive_taillight', 'emissive_thirdbrakelight', 'exhaust_chrome', 'licenseplate', 'lit_textured',
    'lit_textured_bike_forks', 'lit_textured_damage', 'masked_chrome', 'more_chrome_wheel',
    'more_chrome_wheel_hi_lod', 'player_brakelight', 'player_reverselight', 'player_taillight', 'rubber',
    'sprocket', 'wheel_inner', 'default_shiny_rim', 'default_shiny_rim_no_alpha', 'wheel_floating_poly',
    'tire', 'tex_overlay_chrome_wheel_hi_lod', 'more_chrome_wheel_hi_lod_aa', 'davin_speed_reflector_insert',
    'bike_brake_rotor', 'bike_brake_rotor_no_glow', 'brake_caliper', 'brake_rotor', 'single_pass_wheel',
    'subtract_chrome_wheel_hi_lod', 'wheel', 'car_decal_chrome', 'rider_helmet_matte', 'rider_reflective',
}


class Heap:
    """Tiny serialized heap: allocate bytes, get native pointers back."""

    def __init__(self):
        self.data = bytearray(128)
        struct.pack_into('<4I', self.data, 0, BASE, 0x38E030, 1, 0)

    def add(self, payload, align=16):
        while len(self.data) % align:
            self.data.append(0xCD)
        offset = len(self.data)
        self.data += payload
        return offset

    @staticmethod
    def ptr(offset):
        return BASE + offset - 128


def material_fixture(delta=0, refs=(), template=b'lit_textured', category='lit_textured', parts=None, count=None):
    """One material object plus its texture list. ``refs`` items are (name, 'hash'|'slot'|'inline')."""
    heap = Heap()
    material = heap.add(bytes(0x80))
    name = heap.add(template + b'.shadert\0')
    pointers = []
    for text, kind in refs:
        label = heap.add(text.encode() + b'\0')
        if kind == 'inline':
            slot = bytearray(0xC0)
            struct.pack_into('<I', slot, 0, SLOT_CLASS + delta)
            struct.pack_into('<I', slot, 0x78, heap.ptr(label))
            pointers.append(heap.add(bytes(slot)))
            continue
        target = 0x016E0D40
        if kind == 'slot':
            slot = bytearray(0xC0)
            struct.pack_into('<I', slot, 0, SLOT_CLASS + delta)
            struct.pack_into('<I', slot, 0x78, heap.ptr(label))
            target = heap.ptr(heap.add(bytes(slot)))
        pointers.append(heap.add(struct.pack('<IIII', PARAMETER + delta, 0x0001CD02, heap.ptr(label), target)))
    array = heap.add(b''.join(struct.pack('<I', heap.ptr(p)) for p in pointers) or bytes(4))
    struct.pack_into('<I', heap.data, material + 0x10, heap.ptr(array))
    heap.data[material + 0x20] = len(pointers) if count is None else count
    struct.pack_into('<I', heap.data, material + 0x28, heap.ptr(name))
    if parts is not None:
        subs = []
        for part in parts:
            sub = heap.add(bytes(0x40))
            label = heap.add(part + b'.shadert\0')
            struct.pack_into('<I', heap.data, sub + 0x28, heap.ptr(label))
            subs.append(sub)
        array = heap.add(b''.join(struct.pack('<I', heap.ptr(p)) for p in subs))
        struct.pack_into('<I', heap.data, material + 0x30, heap.ptr(array))
        struct.pack_into('<I', heap.data, material + 0x38, len(parts))
    return bytes(heap.data), {'index': 0, 'file_offset': material, 'shader_category': category}


def to_offset(pointer):
    return pointer - BASE + 128


class BindingTests(unittest.TestCase):
    def bindings(self, **kwargs):
        data, material = material_fixture(**kwargs)
        return material_bindings(data, material, kwargs.get('delta', 0), to_offset)

    def test_references_and_template_are_read_in_every_profile(self):
        for delta in (0, 0x200, 0x1308):
            with self.subTest(delta=delta):
                result = self.bindings(delta=delta, refs=[('suspension_00', 'hash'), ('vp_test', 'slot'),
                                                          ('__envmap__', 'hash'), ('vp_inline', 'inline')])
                self.assertEqual(result['shader_template'], 'lit_textured')
                self.assertEqual([(r['name'], r['kind']) for r in result['refs']],
                                 [('suspension_00', 'hash'), ('vp_test', 'slot'), ('__envmap__', 'hash'),
                                  ('vp_inline', 'inline-slot')])

    def test_strings_beside_the_material_are_not_references_unless_the_list_names_them(self):
        # Node names such as exh_02 and grill_00 once bound to paint and chrome.
        heap = Heap()
        data, material = material_fixture(refs=[('__metalflake__', 'hash')], template=b'carpaint', category='carpaint')
        data = data + b'exh_02\0grill_00\0fog_light_00\0'
        base = struct.unpack_from('<I', data, 0)[0]
        shared = {name: [{'file': name}] for name in ('exh_02', 'grill_00', 'fog_light_00')}
        record = bind_material_textures(data, [material], {}, shared, 0, lambda p: p - base + 128)[0]
        self.assertEqual((record['resolved'], record['runtime_bound']), ([], ['__metalflake__']))
        del heap

    def test_composite_wrappers_report_their_sub_materials(self):
        decal = self.bindings(category='composite_material_wrapper', parts=[b'car_decal', b'car_decal_chrome'])
        paint = self.bindings(category='composite_material_wrapper', parts=[b'carpaint', b'carbon_fiber'])
        self.assertEqual((decal['shader_template'], decal['composite'], decal['refs']),
                         ('car_decal', ['car_decal', 'car_decal_chrome'], []))
        self.assertEqual(paint['composite'], ['carpaint', 'carbon_fiber'])
        small = self.bindings(category='material_wrapper')
        self.assertEqual(small, {'shader_template': None, 'composite': [], 'refs': []})

    def test_malformed_lists_templates_and_wrappers_are_rejected_for_their_own_reason(self):
        data, material = material_fixture(refs=[('a_name', 'hash')])
        start = material['file_offset']
        array = to_offset(struct.unpack_from('<I', data, start + 0x10)[0])
        entry = to_offset(struct.unpack_from('<I', data, array)[0])
        cases = []
        changed = bytearray(data)
        changed[start + 0x20] = 9
        cases.append((changed, 'longer than the measured bound'))
        changed = bytearray(data)
        struct.pack_into('<I', changed, array, struct.unpack_from('<I', data, start + 0x28)[0])
        cases.append((changed, 'neither a parameter nor a slot'))
        changed = bytearray(data)
        struct.pack_into('<I', changed, start + 0x28, BASE + 0x10)
        cases.append((changed, 'template name'))
        changed = bytearray(data)
        struct.pack_into('<I', changed, entry + 8, BASE + 128 - 8)
        cases.append((changed, 'readable name'))
        for changed, reason in cases:
            with self.subTest(reason=reason):
                with self.assertRaisesRegex(TextureError, reason):
                    material_bindings(bytes(changed), material, 0, to_offset)
        for count in (0, 9):
            data, material = material_fixture(category='composite_material_wrapper', parts=[b'carpaint'])
            changed = bytearray(data)
            struct.pack_into('<I', changed, material['file_offset'] + 0x38, count)
            with self.assertRaisesRegex(TextureError, 'part count'):
                material_bindings(bytes(changed), material, 0, to_offset)

    def test_resolution_order_runtime_names_case_and_unknown_names(self):
        data, material = material_fixture(refs=[('none', 'hash'), ('fog_light_00', 'hash'), ('__logo__', 'hash'),
                                                 ('mystery_name', 'hash'), ('Vp_Test', 'slot'), ('vp_test', 'inline')])
        base = struct.unpack_from('<I', data, 0)[0]
        slots, shared = {'vp_test': {}}, {'fog_light_00': [{'file': 'x'}]}
        record = bind_material_textures(data, [material], slots, shared, 0, lambda p: p - base + 128)[0]
        self.assertEqual([(r['name'], r['source']) for r in record['resolved']],
                         [('fog_light_00', 'shared'), ('vp_test', 'embedded')])
        self.assertEqual(record['runtime_bound'], ['__logo__'])


class PolicyTests(unittest.TestCase):
    @staticmethod
    def material(category='lit_textured'):
        return {'shader_category': category}

    @staticmethod
    def record(template, resolved=(), runtime=(), composite=()):
        return {'shader_template': template, 'resolved': list(resolved), 'runtime_bound': list(runtime),
                'composite': list(composite)}

    @staticmethod
    def image(alpha):
        return {'rgba': bytes((10, 20, 30, alpha)) * 4}

    def test_effect_surfaces_never_keep_their_texture(self):
        mode, color, _, use = texture_policy(self.material('drop_shadow'), self.record('drop_shadow'), self.image(255))
        self.assertEqual((mode, use), ('BLEND', False))
        mode, color, _, use = texture_policy(self.material('unmapped'), self.record('wheel_floating_poly'), self.image(255))
        self.assertEqual((mode, color[3], use), ('BLEND', 0.0, False))
        mode, color, _, use = texture_policy(
            self.material('composite_material_wrapper'),
            self.record('car_decal', runtime=['__logo__'], composite=['car_decal', 'car_decal_chrome']), None)
        self.assertEqual((mode, color[3], use), ('BLEND', 0.0, False))
        wrapper = self.material('composite_material_wrapper')
        self.assertEqual(texture_policy(wrapper, self.record('carpaint', [{'name': 'fx_carbon_fiber'}],
                                                             composite=['carpaint', 'carbon_fiber']), self.image(255)),
                         (None, None, None, False))

    def test_textured_materials_alpha_test_only_where_the_image_has_cutouts(self):
        solid = texture_policy(self.material(), self.record('lit_textured'), self.image(255))
        cutout = texture_policy(self.material(), self.record('lit_textured'), self.image(0))
        no_alpha = texture_policy(self.material('default_shiny'), self.record('default_shiny_rim_no_alpha'), self.image(0))
        self.assertEqual([solid[0], cutout[0], no_alpha[0]], ['OPAQUE', 'MASK', 'OPAQUE'])
        self.assertTrue(all(row[3] for row in (solid, cutout, no_alpha)))
        self.assertEqual(texture_policy(self.material(), self.record('lit_textured'), None), (None, None, None, False))


class GlbTransportTests(unittest.TestCase):
    @staticmethod
    def parts(uvs):
        batch = {'positions': [(0, 0, 0), (1, 0, 0), (0, 1, 0)], 'packet_offset': 128, 'uvs': uvs}
        return [{'name': 'native.mesh', 'bone': 0, 'mesh': {'source': {'sha256': 'a' * 64},
                 'draws': [{'material': 0, 'batches': [batch]}]}}]

    @staticmethod
    def material(**extra):
        return {'shader_category': 'lit_textured', 'base_color': [1, 1, 1, 1], 'alpha_mode': 'MASK',
                'texture_key': 'k', **extra}

    texture = {'k': {'name': 'vp_test', 'width': 2, 'height': 2, 'rgba': bytes(range(16)), 'source': 'test',
                     'file': 'f', 'sha256': 'b' * 64, 'levels': 1}}

    def test_texture_uv_alpha_cutoff_and_embedded_png_reach_the_glb(self):
        data, _ = build_glb('vp_test', self.parts([(0, 0), (1, 0), (0, 1)]), [self.material()], [], self.texture)
        doc, blob = read_glb(data)
        primitive = doc['meshes'][0]['primitives'][0]
        uv = doc['accessors'][primitive['attributes']['TEXCOORD_0']]
        self.assertEqual((uv['type'], uv['componentType'], uv['count']), ('VEC2', 5126, 3))
        material = doc['materials'][0]
        self.assertEqual((material['alphaMode'], material['alphaCutoff']), ('MASK', 0.5))
        self.assertEqual(material['pbrMetallicRoughness']['baseColorTexture'], {'index': 0})
        view = doc['bufferViews'][doc['images'][0]['bufferView']]
        self.assertEqual(doc['images'][0]['mimeType'], 'image/png')
        self.assertEqual(bytes(blob[view['byteOffset']:view['byteOffset'] + 8]), b'\x89PNG\r\n\x1a\n')
        self.assertEqual(doc['extras']['nativeTextures'][0]['sha256'], 'b' * 64)

    def test_missing_texture_and_malformed_uv_controls(self):
        with self.assertRaisesRegex(ValueError, 'texture key missing'):
            build_glb('vp_test', self.parts([(0, 0), (1, 0), (0, 1)]), [self.material()], [], {})
        for uvs in ([(0, 0), (1, 0)], [(0, 0), (1, 0), (0, float('nan'))], [(0, 0, 0), (1, 0, 0), (0, 1, 0)]):
            with self.subTest(uvs=uvs):
                with self.assertRaisesRegex(ValueError, 'finite UV'):
                    build_glb('vp_test', self.parts(uvs), [self.material()], [], self.texture)


class PageSlotTests(unittest.TestCase):
    @staticmethod
    def page(side=64, name=b'whl_rm_test_h', header=(0, 0, 0)):
        size = side * side + 1024 + 0x100
        page = bytearray(size + 0x400)
        struct.pack_into('<4I', page, 0, *header, size)
        linear = linear_image(side)
        page[0x90:0x90 + side * side] = swizzled(linear, side)
        page[0x90 + side * side:0x90 + side * side + 1024] = palette_bytes()
        root = size
        base = 0x682C8B0
        slot = root + 0x40
        struct.pack_into('<I', page, slot, SLOT_CLASS + 0x1308)
        struct.pack_into('<I', page, slot + 0x4C, 0)
        struct.pack_into('<I', page, slot + 0x78, base + 0x100)
        page[root + 0x100:root + 0x100 + len(name) + 1] = name + b'\0'
        return bytes(page), root, base, linear

    def test_square_block_decodes_and_other_shapes_are_reported_not_guessed(self):
        for side in (16, 32, 64, 128):
            with self.subTest(side=side):
                page, root, base, linear = self.page(side)
                slots, skipped = read_page_slots(page, root, base)
                self.assertEqual(skipped, [])
                self.assertEqual(slots['whl_rm_test_h']['rgba'],
                                 indexed_to_rgba(linear, palette_csm1(palette_bytes()), 2))
        page, root, base, _ = self.page(64)
        changed = bytearray(page)
        struct.pack_into('<I', changed, 12, 0x180)
        slots, skipped = read_page_slots(bytes(changed), root, base)
        self.assertEqual((slots, skipped), ({}, [{'name': 'whl_rm_test_h', 'block_bytes': 0x180}]))

    def test_header_and_name_pointer_corruptions_are_ignored(self):
        page, root, base, _ = self.page(64, header=(1, 0, 0))
        self.assertEqual(read_page_slots(page, root, base), ({}, []))
        page, root, base, _ = self.page(64)
        changed = bytearray(page)
        struct.pack_into('<I', changed, root + 0x40 + 0x78, 0x10)
        self.assertEqual(read_page_slots(bytes(changed), root, base), ({}, []))


def corpus_available():
    return (CARS / 'index.json').is_file()


@unittest.skipUnless(corpus_available(), 'MC3 extraction is not present')
class CorpusTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.index = json.loads((CARS / 'index.json').read_text())
        cls.profile_delta = {'original': 0, 'mercedes': 0x200, 'remix': 0x1308}

    def main_package(self, code):
        manifest = json.loads((CARS / f'{code}/manifest.json').read_text())
        member = next(m for m in manifest['members'] if m['file'].endswith(f'/{code}.pck'))
        path = CARS / member['file']
        return path, path.read_bytes()

    def test_every_package_has_one_decodable_image_slot_and_decoder_choices_beat_alternatives(self):
        weakest = 0.0
        for vehicle in self.index['vehicles']:
            code = vehicle['id']
            path, data = self.main_package(code)
            materials = read_material_table(data, read_vehicle(path)['material_collection_offset'])
            delta = self.profile_delta[materials[0]['profile']]
            slots = read_slot_textures(data, delta)
            self.assertEqual(len(slots), 1, code)
            texture = next(iter(slots.values()))
            self.assertEqual((texture['width'], texture['height']), (256, 256), code)
            self.assertEqual(texture['levels'], 4 if delta == 0x1308 else 1, code)
            weakest = max(weakest, smoothness(texture['rgba'], 256, 256))
        self.assertLess(weakest, 75.0)

    def test_block_swizzle_and_palette_order_are_selected_by_the_image_itself(self):
        path, data = self.main_package('vp_corvettez06_03')
        texture = next(iter(read_slot_textures(data, 0).values()))
        begin = texture['slot_offset'] + 0x180
        pixels, palette = data[begin:begin + 65536], data[begin + 65536:begin + 66560]
        plain = [palette[i * 4:i * 4 + 4] for i in range(256)]
        scores = {}
        for swizzle in (True, False):
            for ordered in (True, False):
                image = unswizzle8(pixels, 256, 256) if swizzle else pixels
                rgba = indexed_to_rgba(image, palette_csm1(palette) if ordered else plain, 2)
                scores[(swizzle, ordered)] = smoothness(rgba, 256, 256)
        best = min(scores, key=scores.get)
        self.assertEqual(best, (True, True))
        self.assertLess(scores[best] * 3, min(value for key, value in scores.items() if not key[0]))
        self.assertLess(scores[best], scores[(True, False)])

    def test_shadow_texture_alpha_is_a_soft_blob_with_a_clear_border(self):
        rows = [r for r in self.index['files'] if r['file'].endswith('shared_texture/texture/vp_shadow.tex')]
        texture = read_tex((CARS / rows[0]['file']).read_bytes())
        alpha = texture['rgba'][3::4]
        self.assertEqual((texture['width'], texture['height']), (64, 64))
        self.assertEqual(alpha[0], 0)
        self.assertEqual(alpha[32 * 64 + 32], 255)
        self.assertGreater(len(set(alpha)), 100)

    def test_binding_coverage_is_exact_across_every_package(self):
        shared = shared_texture_rows(self.index)
        counts, templates = {}, set()
        for vehicle in self.index['vehicles']:
            path, data = self.main_package(vehicle['id'])
            materials = read_material_table(data, read_vehicle(path)['material_collection_offset'])
            delta = self.profile_delta[materials[0]['profile']]
            base = struct.unpack_from('<I', data, 0)[0]
            records = bind_material_textures(data, materials, read_slot_textures(data, delta), shared, delta,
                                             lambda pointer, base=base: pointer - base + 128)
            for material, record in zip(materials, records):
                category = material['shader_category']
                counts[category] = counts.get(category, 0) + 1
                if record['shader_template']:
                    templates.add(record['shader_template'])
                if category in ('carpaint', 'chrome', 'aa_chrome', 'aa_trim', 'car_window', 'colored_glass',
                                'licenseplate', 'material_wrapper', 'composite_material_wrapper'):
                    self.assertEqual(record['resolved'], [], (vehicle['id'], material['index'], category))
                if category in ('lit_textured', 'default_shiny', 'rubber', 'carbon_fiber', 'drop_shadow') \
                        or category.startswith('emissive_'):
                    self.assertTrue(record['resolved'], (vehicle['id'], material['index'], category))
                if category == 'composite_material_wrapper':
                    self.assertIn(tuple(record['composite']), {('car_decal', 'car_decal_chrome'),
                                                               ('carpaint', 'carbon_fiber'),
                                                               ('carpaint_novinyl', 'carbon_fiber', 'chrome')})
        self.assertGreater(sum(counts.values()), 2300)
        self.assertLessEqual(templates, KNOWN_TEMPLATES)

    def test_every_selected_wheel_page_binds_and_effect_polygons_keep_no_texture(self):
        root = CARS
        seen, polys, textured = set(), 0, 0
        sample = {'vp_350z_04', 'vp_aprilia_mille_04', 'vp_belair_57', 'vp_corvettez06_03', 'vp_d_chingon_04',
                  'vp_d_tokyo_cop_01', 'vp_esprit_04', 'vp_sl500_04', 'vp_ninja_03', 'vp_hummer_02',
                  'vp_cuevito_99', 'vp_ducati_999r_04', 'vp_kwz_cop_98', 'vp_monster_sr4_04', 'vp_murcielago_04',
                  'vp_gto_70', 'vp_golfr32_04', 'vp_d_yukon_05', 'vp_skully_01', 'vp_viper_03'}
        for vehicle in (v for v in self.index['vehicles'] if v['id'] in sample):
            wheels = None
            for bike in (False, True):
                try:
                    wheels = read_default_wheels(root, vehicle['id'], bike=bike)
                    break
                except ValueError:
                    continue
            self.assertIsNotNone(wheels, vehicle['id'])
            for component in wheels['components']:
                model = component['model']
                key = (model['page_offset'], len(model['materials']))
                if key in seen:
                    continue
                seen.add(key)
                for material, record in zip(model['materials'], model['texture_records']):
                    self.assertLessEqual({record['shader_template']} - {None}, KNOWN_TEMPLATES, record)
                    template = record['shader_template'] or ''
                    mode, _, _, use = texture_policy(material, record, {'rgba': bytes(4)})
                    if 'floating_poly' in template:
                        polys += 1
                        self.assertEqual((mode, use), ('BLEND', False))
                    textured += bool(record['resolved'])
        self.assertGreater(len(seen), 15)
        self.assertGreater(polys, 10)
        self.assertGreater(textured, 30)

    def test_corvette_binding_reaches_materials_with_expected_templates(self):
        path, data = self.main_package('vp_corvettez06_03')
        shared = shared_texture_rows(self.index)
        materials = read_material_table(data, read_vehicle(path)['material_collection_offset'])
        textures = {}
        bind_textures(data, materials, textures, shared, CARS, 'main')
        by_template = {m['shader_template']: m for m in materials if m.get('shader_template')}
        self.assertEqual(by_template['lit_textured']['shader_category'], 'lit_textured')
        self.assertEqual(by_template['car_decal']['alpha_mode'], 'BLEND')
        self.assertEqual(by_template['car_decal']['base_color'][3], 0.0)
        self.assertNotIn('texture_key', by_template['car_decal'])
        self.assertEqual(by_template['drop_shadow'].get('texture_key'), None)
        self.assertIn('main:vp_corvettez06_03', textures)
        self.assertIn('shared:suspension_00', textures)
        self.assertNotIn('shared:vp_shadow', textures)
        self.assertEqual(by_template['player_taillight']['texture_name'], 'vp_corvettez06_03')


if __name__ == '__main__':
    unittest.main()
