"""Bounded MC3 PS2 material identities for a documented geometry preview.

Saved class addresses identify three source package profiles. This module does
not emulate the game's shader; diffuse images are decoded by ``mc3_textures``.
Display factors are neutral inspection choices except the observed colored-glass
vector and the texture policy applied by the converter; callers must retain
those fidelity limits in output provenance.
"""
import math
import struct

HEADER_BYTES = 0x80
MAX_MATERIALS = 1024
MAX_BYTES = 64 * 1024 * 1024
COLLECTION_PROFILES = {0x7a1138: ('original', 0),
                       0x7a1338: ('mercedes', 0x200),
                       0x7a2440: ('remix', 0x1308)}
SHADERS = {
    0x7aa7c8: 'lit_textured', 0x7a10d8: 'black_matte',
    0x7aa828: 'drop_shadow', 0x7aa2e8: 'masked_chrome',
    0x7aa588: 'composite_material_wrapper', 0x7a9920: 'carpaint',
    0x7aa948: 'colored_glass', 0x7aa8e8: 'car_window',
    0x7aa5e8: 'rubber', 0x7a9740: 'emissive_thirdbrakelight',
    0x7aa408: 'carbon_fiber', 0x7aa228: 'aa_chrome',
    0x7aa3a8: 'chrome', 0x7aab90: 'composite_material_wrapper',
    0x7a1078: 'material_wrapper', 0x7aa288: 'aa_trim',
    0x7aa468: 'default_shiny', 0x7a96e0: 'emissive_headlight',
    0x7a9860: 'emissive_taillight', 0x7a9800: 'emissive_reverselight',
    0x7aaa08: 'licenseplate', 0x7a97a0: 'emissive_brakelight',
    0x7aab30: 'composite_material_wrapper', 0x7a98c0: 'carpaint_novinyl',
}
CLAIM_LIMITS = (
    'Native shader categories identify surfaces; game shader behavior is not emulated.',
    'Diffuse images are decoded only where a material lists one; environment, specular, metal-flake, paint, '
    'licence-plate and runtime logo slots are not.',
    'Neutral inspection factors are display choices, not recovered native paint colors.',
    'Colored-glass factors translate the native tint vector; GS shading is not emulated.',
)


def _require(data, pos, size):
    if not isinstance(pos, int) or pos < 0 or size < 0 or pos + size > len(data):
        raise ValueError('material read outside PCK')


def _u32(data, pos):
    _require(data, pos, 4)
    return struct.unpack_from('<I', data, pos)[0]


def _pointer(data, ptr, size):
    pos = ptr - _u32(data, 0) + HEADER_BYTES
    if pos < HEADER_BYTES:
        raise ValueError('material pointer before PCK body')
    _require(data, pos, size)
    return pos


def _header(data):
    if not HEADER_BYTES <= len(data) <= MAX_BYTES:
        raise ValueError('material PCK size outside bound')
    base, _, version, declared = struct.unpack_from('<4I', data)
    if version != 1 or declared != len(data) - HEADER_BYTES:
        raise ValueError('material PCK version or payload length mismatch')
    if not base or base + declared > 0xffffffff:
        raise ValueError('material PCK serialized address outside bound')


def read_material_table(data, collection_offset):
    """Read an explicitly selected native pointer collection and its materials.

    Every returned index remains the game's original u16 draw-material index.
    Unknown classes are preserved with a neutral opaque inspection material.
    """
    _header(data)
    _require(data, collection_offset, 16)
    profile = COLLECTION_PROFILES.get(_u32(data, collection_offset))
    if profile is None:
        raise ValueError('unsupported material collection profile')
    name, delta = profile
    count, capacity = struct.unpack_from('<HH', data, collection_offset + 8)
    if not 1 <= count <= capacity <= MAX_MATERIALS:
        raise ValueError('invalid material collection count')
    array = _pointer(data, _u32(data, collection_offset + 4), count * 4)
    materials = []
    for index in range(count):
        obj = _pointer(data, _u32(data, array + index * 4), 0x30)
        vtable = _u32(data, obj)
        category = SHADERS.get(vtable - delta, 'unmapped')
        material = {'index': index, 'profile': name, 'file_offset': obj,
                    'vtable': vtable, 'shader_category': category,
                    'base_color': [0.65, 0.65, 0.65, 1.0],
                    'alpha_mode': 'OPAQUE', 'metallic': 0.0, 'roughness': 0.6,
                    'display_factor_source': 'neutral-inspection-fallback',
                    'claim_limits': list(CLAIM_LIMITS)}
        if category == 'colored_glass':
            _require(data, obj + 0x50, 16)
            rgba = list(struct.unpack_from('<4f', data, obj + 0x50))
            if not all(math.isfinite(v) and 0 <= v <= 1 for v in rgba):
                raise ValueError('invalid colored-glass source vector')
            material['native_rgba'] = rgba
            material['native_rgba_offset'] = obj + 0x50
            # Ghidra's FUN_003b71b0 writes these native fields and
            # FUN_003b7408 reads them into GS RGBA. glTF uses the unmodified
            # vector as an inspection translation, without emulating its
            # reflection shader or GS color/alpha packing.
            material['base_color'] = list(rgba)
            material['alpha_mode'] = 'BLEND' if rgba[3] < 1 else 'OPAQUE'
            material['display_factor_source'] = 'native-colored-glass-vector'
        materials.append(material)
    return materials


def find_material_tables(data):
    """Return bounded candidate collections; caller supplies the root binding.

    Generic pointer collections use the same class, so only collections whose
    majority of objects are recognized material classes qualify. No largest
    table or first-table assumption selects the model's primary collection.
    """
    _header(data)
    tables = []
    for pos in range(HEADER_BYTES, len(data) - 15, 4):
        if _u32(data, pos) not in COLLECTION_PROFILES:
            continue
        try:
            materials = read_material_table(data, pos)
        except ValueError:
            continue
        known = sum(m['shader_category'] != 'unmapped' for m in materials)
        if known * 10 >= len(materials) * 7:
            tables.append({'file_offset': pos, 'materials': materials})
    return tables
