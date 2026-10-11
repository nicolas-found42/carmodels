"""Source-bound MC3 PS2 texture decoding for the static preview.

Two carriers are decoded:

* a PCK-embedded image slot (class value 0x7A14A0 plus the package profile
  delta): a 256x256 PSMT8 image in GS block order followed by a CSM1-ordered
  RGBA palette whose alpha uses 0..0x80 as 0..opaque;
* a shared ``.tex`` file: 14-byte header, RGBA palette, linear 8-bit index
  levels, alpha already in 0..255.

Each decoder checks exact byte accounting and rejects short, long or ambiguous
input. Image orientation, palette order and swizzle were fixed against the
decoded images themselves (neighbour-smoothness controls in the tests), not
against the original GS. Native shader blending is not emulated.
"""
import re
import struct
import zlib

from ps2_container import unswizzle8

SLOT_CLASS = 0x7A14A0
SLOT_IMAGE_SIGNATURE = (0xE7, 0x100)
SLOT_NAME_POINTER = 0x78
SLOT_BYTES = 0xC0
MAX_DIMENSION = 512
FILL = b'\xcd' * 16


class TextureError(ValueError):
    pass


def palette_csm1(palette):
    """CSM1 order: entries 8..15 and 16..23 of every 32 trade places."""
    if len(palette) != 1024:
        raise TextureError('palette must hold 256 RGBA entries')
    entries = [palette[i * 4:i * 4 + 4] for i in range(256)]
    return [entries[(i & ~0x18) | ((i & 8) << 1) | ((i & 16) >> 1)] for i in range(256)]


def indexed_to_rgba(indices, entries, alpha_scale):
    if len(entries) != 256 or any(len(entry) != 4 for entry in entries):
        raise TextureError('palette entries must be 256 RGBA quads')
    table = [bytes((r, g, b, min(255, a * alpha_scale))) for r, g, b, a in entries]
    return b''.join(table[i] for i in indices)


def encode_png(width, height, rgba):
    """Small RGBA8 PNG writer; no filtering, so the decoded bytes stay exact."""
    if len(rgba) != width * height * 4:
        raise TextureError('RGBA length differs from dimensions')

    def chunk(kind, payload):
        return struct.pack('>I', len(payload)) + kind + payload + struct.pack('>I', zlib.crc32(kind + payload))

    stride = width * 4
    raw = b''.join(b'\0' + rgba[y * stride:(y + 1) * stride] for y in range(height))
    return (b'\x89PNG\r\n\x1a\n' + chunk(b'IHDR', struct.pack('>2I5B', width, height, 8, 6, 0, 0, 0))
            + chunk(b'IDAT', zlib.compress(raw, 9)) + chunk(b'IEND', b''))


def smoothness(rgba, width, height):
    """Mean absolute RGB step between 4-neighbours; wrong swizzle/palette order raises it."""
    total = count = 0
    for y in range(height):
        row = y * width * 4
        for x in range(width):
            here = row + x * 4
            if x + 1 < width:
                total += sum(abs(rgba[here + k] - rgba[here + 4 + k]) for k in range(3))
                count += 1
            if y + 1 < height:
                total += sum(abs(rgba[here + k] - rgba[here + width * 4 + k]) for k in range(3))
                count += 1
    return total / count if count else 0.0


def _u32(data, offset):
    if offset < 0 or offset + 4 > len(data):
        raise TextureError('texture field outside carrier')
    return struct.unpack_from('<I', data, offset)[0]


def _next_data(data, position, limit):
    """Start of the next non-padding run (16-byte aligned) and its raw extent."""
    while position < limit and data[position] == 0xCD:
        position += 1
    if position >= limit:
        return None
    begin = position & ~15
    end = data.find(FILL, position, limit)
    return begin, limit if end < 0 else end


def _blocks_after(data, start, limit):
    """Pixel/palette blocks after a slot, checked by exact byte counts.

    Only two layouts are accepted: one 66560-byte block (256x256 indices plus
    palette), or four levels of 65536, 16384, 4096 and 2048 bytes (the last is
    32x32 indices plus palette) with a short header record before each later
    level. The expected size, not a padding run, fixes each block end, because
    a block may end in 0xCD pixel bytes.
    """
    position = data.find(FILL, start, limit)
    if position < 0:
        raise TextureError('slot has no padding before its pixel data')
    first = _next_data(data, position, limit)
    if first is None:
        raise TextureError('slot has no pixel data')
    begin = first[0]
    single = begin + 66560
    if first[1] - begin >= 66560 and single <= limit and data[single:single + 16] in (FILL, b''):
        return [(begin, single)]
    blocks = []
    cursor = begin
    for size in (65536, 16384, 4096, 2048):
        if cursor is None or cursor + size > limit or data[cursor + size:cursor + size + 16] not in (FILL, b''):
            raise TextureError('texture pixel/palette blocks do not match a measured layout')
        blocks.append((cursor, cursor + size))
        following = _next_data(data, cursor + size, limit)
        while following is not None and following[1] - following[0] < 64 and size != 2048:
            following = _next_data(data, following[1], limit)
        cursor = following[0] if following else None
    return blocks


def read_slot_textures(data, delta=0, base=None):
    """Return embedded image slots by serialized name.

    ``base`` is the PCK serialized base (word 0) when the carrier is a PCK
    adapter view; names are read through the native pointer at slot+0x78.
    """
    if base is None:
        base = _u32(data, 0)
    vtable = SLOT_CLASS + delta
    pattern = struct.pack('<I', vtable)
    found = {}
    position = data.find(pattern, 128)
    while position >= 0:
        if position % 4 == 0 and position + SLOT_BYTES <= len(data):
            words = struct.unpack_from('<4I', data, position)
            if words[2] == SLOT_IMAGE_SIGNATURE[0] and (words[3] & 0xFFFF) == SLOT_IMAGE_SIGNATURE[1]:
                name_at = _u32(data, position + SLOT_NAME_POINTER) - base + 128
                if not 128 <= name_at < len(data):
                    raise TextureError('texture slot name pointer outside carrier')
                end = data.find(b'\0', name_at, name_at + 128)
                name = data[name_at:end].decode('ascii') if end > name_at else ''
                if not name or name in found:
                    raise TextureError('texture slot name missing or duplicated')
                found[name] = decode_slot(data, position, name)
        position = data.find(pattern, position + 4)
    return found


def decode_slot(data, offset, name):
    blocks = _blocks_after(data, offset + SLOT_BYTES, len(data))
    sizes = [end - begin for begin, end in blocks]
    levels = len(blocks)
    if levels == 1:
        pixels, palette = data[blocks[0][0]:blocks[0][0] + 65536], data[blocks[0][0] + 65536:blocks[0][1]]
    else:
        pixels = data[blocks[0][0]:blocks[0][1]]
        palette = data[blocks[3][1] - 1024:blocks[3][1]]
    if len(pixels) != 65536 or len(palette) != 1024:
        raise TextureError('texture pixel/palette bytes differ from the measured layout')
    rgba = indexed_to_rgba(unswizzle8(pixels, 256, 256), palette_csm1(palette), 2)
    return {'name': name, 'width': 256, 'height': 256, 'rgba': rgba, 'levels': levels,
            'slot_offset': offset, 'block_sizes': sizes,
            'source': 'pck-embedded-psmt8-csm1'}


def read_tex(data):
    """Decode level zero of a shared 8-bit ``.tex`` (palette first, linear indices)."""
    if len(data) < 14 + 1024:
        raise TextureError('shared texture shorter than header and palette')
    width, height, _format, levels = struct.unpack_from('<4H', data, 0)
    if not (16 <= width <= MAX_DIMENSION and 16 <= height <= MAX_DIMENSION) or not 1 <= levels <= 8:
        raise TextureError('shared texture dimensions or level count outside bounds')
    expected, w, h = 14 + 1024, width, height
    for _ in range(levels):
        expected += w * h
        w, h = max(1, w // 2), max(1, h // 2)
    if len(data) != expected:
        raise TextureError('shared texture is not a palette plus 8-bit levels of the declared size')
    palette = data[14:14 + 1024]
    entries = [palette[i * 4:i * 4 + 4] for i in range(256)]
    pixels = data[14 + 1024:14 + 1024 + width * height]
    return {'width': width, 'height': height, 'levels': levels,
            'rgba': indexed_to_rgba(pixels, entries, 1), 'source': 'shared-tex-8bit'}


SHARED_TEXTURE_DIRS = ('shared_texture', 'shared_stripes')
SHARED_TEXTURE_PATH = re.compile(
    r'shared/assets/\d+/vehicle/(?:%s)/texture/([A-Za-z0-9_]+)\.tex' % '|'.join(SHARED_TEXTURE_DIRS))
RUNTIME_BOUND = ('__envmap__', '__metalflake__', '__specular__', '__decal__', '__logo__',
                 '__licenseplate__')
DECAL_TEMPLATES = ('car_decal', 'car_decal_chrome')


def shared_texture_rows(extraction_index):
    """Index rows for shared ``.tex`` files, by texture name; duplicates must be byte-identical."""
    rows = {}
    for row in extraction_index['files']:
        match = SHARED_TEXTURE_PATH.fullmatch(row['file'])
        if match:
            rows.setdefault(match.group(1), []).append(row)
    for name, group in rows.items():
        if len({row['sha256'] for row in group}) != 1:
            raise TextureError(f'shared texture {name} has differing duplicate occurrences')
    return rows


PARAMETER_CLASS = 0x7A1260
MATERIAL_TEXTURE_LIST = 0x10
MATERIAL_TEXTURE_COUNT = 0x20
MATERIAL_TEMPLATE_NAME = 0x28
WRAPPER_PARTS = 0x30
WRAPPER_COUNT = 0x38


def _c_string(data, offset):
    if not 0 <= offset < len(data):
        return None
    end = data.find(b'\0', offset, offset + 96)
    raw = data[offset:end] if end > offset else b''
    return raw.decode('ascii') if raw and re.fullmatch(rb'[\x21-\x7e]+', raw) else None


def _template(data, material, to_offset):
    name = _c_string(data, to_offset(_u32(data, material + MATERIAL_TEMPLATE_NAME)))
    if name is None or not name.endswith('.shadert'):
        raise TextureError('material lacks a shader template name')
    return name[:-len('.shadert')]


def material_bindings(data, material, delta, to_offset):
    """Shader template and texture references of one material object.

    Layout (read from the base material class constructor FUN_002aff88 and its
    texture list loader, and checked against every material in the corpus):
    +0x10 points to an array of texture-reference pointers whose length is the
    byte at +0x20; +0x28 points to the template name. Each reference is either a
    parameter entry (class 0x7A1260 plus profile delta: name pointer at +8, then
    an embedded slot pointer or a name hash) or an embedded slot object. A
    composite wrapper (+0x30 array, +0x38 count) lists sub-materials, each with
    its own template name; the small ``material_wrapper`` class carries no textures.
    """
    category = material['shader_category']
    if category == 'material_wrapper':
        return {'shader_template': None, 'composite': [], 'refs': []}
    if category == 'composite_material_wrapper':
        parts = to_offset(_u32(data, material['file_offset'] + WRAPPER_PARTS))
        count = _u32(data, material['file_offset'] + WRAPPER_COUNT)
        if not 1 <= count <= 8:
            raise TextureError('composite wrapper part count outside bound')
        names = [_template(data, to_offset(_u32(data, parts + 4 * i)), to_offset) for i in range(count)]
        return {'shader_template': names[0], 'composite': names, 'refs': []}
    start = material['file_offset']
    count = data[start + MATERIAL_TEXTURE_COUNT] if start + MATERIAL_TEXTURE_COUNT < len(data) else 0
    if count > 8:
        raise TextureError('material texture list longer than the measured bound')
    listing = to_offset(_u32(data, start + MATERIAL_TEXTURE_LIST))
    parameter, slot = PARAMETER_CLASS + delta, SLOT_CLASS + delta
    refs = []
    for index in range(count):
        target = to_offset(_u32(data, listing + 4 * index))
        word = _u32(data, target)
        if word == parameter:
            name = _c_string(data, to_offset(_u32(data, target + 8)))
            second = to_offset(_u32(data, target + 12))
            kind = 'slot' if 0 <= second <= len(data) - 4 and _u32(data, second) == slot else 'hash'
        elif word == slot:
            name, kind = _c_string(data, to_offset(_u32(data, target + SLOT_NAME_POINTER))), 'inline-slot'
        else:
            raise TextureError('texture list entry is neither a parameter nor a slot object')
        if not name:
            raise TextureError('texture reference has no readable name')
        refs.append({'name': name, 'kind': kind})
    return {'shader_template': _template(data, start, to_offset), 'composite': [], 'refs': refs}


def bind_material_textures(data, materials, slots, shared_rows, delta, to_offset):
    """Resolve each material's texture references against embedded slots and shared ``.tex`` files.

    Runtime-bound names (__envmap__, __logo__ ...) stay unresolved by design.
    Returns binding records parallel to ``materials``.
    """
    lowered = {name.lower(): name for name in slots}
    records = []
    for material in materials:
        binding = material_bindings(data, material, delta, to_offset)
        resolved, runtime = [], []
        for ref in binding['refs']:
            name = ref['name']
            if name in RUNTIME_BOUND:
                if name not in runtime:
                    runtime.append(name)
            elif name in ('none', 'noalpha'):
                continue
            elif name.lower() in lowered:
                if not any(r['name'] == lowered[name.lower()] and r['source'] == 'embedded' for r in resolved):
                    resolved.append({'name': lowered[name.lower()], 'source': 'embedded', 'reference': ref['kind']})
            elif name in shared_rows:
                if not any(r['name'] == name and r['source'] == 'shared' for r in resolved):
                    resolved.append({'name': name, 'source': 'shared', 'reference': ref['kind']})
        records.append({'index': material['index'], 'shader_template': binding['shader_template'],
                        'composite': binding['composite'], 'resolved': resolved, 'runtime_bound': runtime})
    return records


def texture_policy(material, record, texture):
    """Display decision for one material: (alpha_mode, colour, note, use_texture).

    * drop_shadow: a ground blob-shadow quad (texture ``vp_shadow``, defaults
      shadowR/G/B/A 1,0,0,1 and isAdditive 0 in FUN_003b8e18); the converter omits
      the quad, so no texture is attached.
    * car_decal*: texture is the runtime __logo__ slot, absent from the disc
      file; the surface is drawn fully transparent rather than as a gray plane.
    * wheel_floating_poly: speed-driven effect polygon; transparent at rest.
    * composite wrappers choose their shader at run time (paint, carbon, vinyl);
      they keep the neutral paint surface.
    * textured: texture-only colour; alpha-tested where the image has cut-outs.
    """
    template = record['shader_template'] or ''
    if 'floating_poly' in template:
        return 'BLEND', [1.0, 1.0, 1.0, 0.0], ('wheel_floating_poly is a speed-driven effect polygon '
                                               '(runtime rimSpeed parameter, default 0); drawn transparent at rest'), False
    if template == 'drop_shadow':
        # The converter omits these ground shadow quads; the material stays in the
        # table with no texture so an unused image is never embedded.
        return 'BLEND', [0.0, 0.0, 0.0, 1.0], 'ground shadow effect plane is omitted from the preview', False
    if template in DECAL_TEMPLATES or any(part in DECAL_TEMPLATES for part in record['composite']):
        return 'BLEND', [1.0, 1.0, 1.0, 0.0], 'runtime __logo__ texture absent; drawn transparent', False
    if texture is None or material['shader_category'] == 'composite_material_wrapper':
        return None, None, None, False
    rgba = texture['rgba']
    if 'no_alpha' in template or 'noalpha' in template:
        return 'OPAQUE', [1.0, 1.0, 1.0, 1.0], 'shader declares no alpha; image alpha ignored', True
    cutout = any(rgba[i] < 128 for i in range(3, len(rgba), 4))
    return ('MASK' if cutout else 'OPAQUE'), [1.0, 1.0, 1.0, 1.0], (
        'alpha-tested at 0.5 because the image has transparent texels' if cutout else 'opaque image'), True


PAGE_BLOCK_OVERHEAD = 0x100


def read_page_slots(page, root, base, delta=0x1308):
    """Image slots of one pf05 page, by serialized name.

    ``page`` holds the page bytes; ``root`` is the model body offset inside it
    and ``base`` the body's serialized address. A slot's word at +0x4C is the
    page offset of its block; the block header word at +0x0C is the block size,
    and the image data (``size - 0x100`` bytes: square 8-bit indices then the
    1024-byte palette) starts 0x90 into the block. Blocks of other shapes
    (4-bit palettes, mip secondaries with no square size) are skipped and
    reported in the second return value as undecoded.
    """
    vtable = struct.pack('<I', SLOT_CLASS + delta)
    slots, skipped = {}, []
    position = page.find(vtable, root)
    while position >= 0:
        if position % 4 == 0 and position + 0x80 <= len(page):
            words = struct.unpack_from('<32I', page, position)
            name_at = words[SLOT_NAME_POINTER // 4] - base + root
            block = words[19]
            if 0 <= name_at < len(page) and block + 16 <= len(page):
                end = page.find(b'\0', name_at, name_at + 96)
                header = struct.unpack_from('<4I', page, block)
                name = page[name_at:end].decode('ascii', 'replace') if end > name_at else ''
                if name and header[:3] == (0, 0, 0) and re.fullmatch(r'[A-Za-z0-9_]+', name):
                    size = header[3]
                    data_bytes = size - PAGE_BLOCK_OVERHEAD
                    side = int(round((data_bytes - 1024) ** 0.5)) if data_bytes > 1024 else 0
                    if side in (16, 32, 64, 128, 256) and side * side + 1024 == data_bytes \
                            and block + size <= len(page) and name not in slots:
                        data = page[block + 0x90:block + 0x90 + data_bytes]
                        pixels, palette = data[:side * side], data[side * side:]
                        rgba = indexed_to_rgba(unswizzle8(pixels, side, side), palette_csm1(palette), 2)
                        slots[name] = {'name': name, 'width': side, 'height': side, 'rgba': rgba,
                                       'levels': 1, 'slot_offset': position, 'block_offset': block,
                                       'source': 'pf05-page-psmt8-csm1'}
                    elif name not in slots:
                        skipped.append({'name': name, 'block_bytes': size})
        position = page.find(vtable, position + 4)
    return slots, skipped
