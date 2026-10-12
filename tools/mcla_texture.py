"""Read-only decoding of Midnight Club: Los Angeles textures (Xbox 360, big-endian RSC5).

Resources: texture dictionaries (`.xtd`, type 9) and part texture packs (`.xtp`/`.xtl`, type 83).
Layouts are readings taken from CodeX.Games.MCLA `RSC5/Rsc5Texture.cs` and `RSC5/Rsc5Drawable.cs`
(dedc3156; no code copied) and checked on every car texture of the disc:

- Texture dictionary: VFT, block map, parent, usage count, name-hash array (+0x10: pointer, count,
  capacity), texture pointer array (+0x18).
- Part texture pack: VFT, block map, shader group (+0x0C), zone, maximum-damage and scratch textures
  (+0x14, +0x18, +0x1C; null in rim, tire and brake packs).
- Shader group: VFT, texture dictionary or block map (+0x04), shader pointer array (+0x08).
- Shader: draw bucket (+0x09), parameter values (+0x10), count (+0x18), types (+0x1C: 0 texture,
  1 vector, n > 1 an array of n vectors), name hashes (+0x24), shader name (+0x30) and material
  file (+0x38). Parameter names are Jenkins hashes (`diffusesampler` = 0xF1FE2B71).
- Texture (grcTexture): VFT, name pointer (+0x18), D3D header pointer (+0x1C), width and height
  (+0x20), mip count (+0x27). The D3D header carries the Xenos fetch constant at +0x1C: dword 0
  holds the tiled flag (bit 31) and the pitch in 32-texel units (bits 22-30); dword 1 the format
  (bits 0-5), endian swap (bits 6-7) and base pointer (bits 12-31); dword 2 width-1 and height-1.

Base levels are untiled with the Xenos 2D tiled address function (independently written; the
mapping is a permutation of the padded surface, which the tests check) and DXT blocks are decoded
to RGBA8. Only mip level 0 is decoded.
"""
import struct

from mcla_resource import Resource, ResourceError

TEXTURE_VFTS = (0x24555500, 0x948A5400, 0x14415800)
DICTIONARY_VFTS = (0x44365500,)
PACK_VFTS = (0x28C25700, 0xBCC65600)
SHADER_GROUP_VFTS = (0xECCE5500, 0x8CF35400)
SHADER_VFTS = (0x64895500, 0x2CAA5400)
# Xenos format code -> (name, texels per block edge, bytes per block, endian swap expected)
FORMATS = {0x12: ('dxt1', 4, 8, 1), 0x14: ('dxt5', 4, 16, 1), 0x06: ('argb8888', 1, 4, 2)}
DIFFUSE = 0xF1FE2B71


class TextureError(ValueError):
    pass


def need(condition, message):
    if not condition:
        raise TextureError(message)


def tiled_offset(x, y, width, log_bytes):
    """Byte offset of block (x, y) in a Xenos 2D tiled surface `width` blocks wide (any width;
    rows are padded to 32 blocks) with 2**log_bytes bytes per block."""
    aligned = (width + 31) & ~31
    macro = ((x >> 5) + (y >> 5) * (aligned >> 5)) << (log_bytes + 7)
    micro = ((x & 7) + ((y & 0xE) << 2)) << log_bytes
    offset = macro + ((micro & ~0xF) << 1) + (micro & 0xF) + ((y & 1) << 4)
    return (((offset & ~0x1FF) << 3) + ((y & 16) << 7) + ((offset & 0x1C0) << 2)
            + (((((y & 8) >> 2) + (x >> 3)) & 3) << 6) + (offset & 0x3F))


def texture(r, at):
    """Header facts of one texture; raises when its fields disagree."""
    need(r.u32(at) in TEXTURE_VFTS, 'not a texture (VFT 0x%08x)' % r.u32(at))
    name = r.cstring(r.offset(r.u32(at + 0x18)))
    d3d = r.pointer(at + 0x1C, 0x34)
    need(d3d is not None, 'texture without a D3D header')
    width, height, mips = r.u16(at + 0x20), r.u16(at + 0x22), r.u8(at + 0x27)
    fetch = [r.u32(d3d + 0x1C + 4 * i) for i in range(6)]
    code, endian = fetch[1] & 0x3F, fetch[1] >> 6 & 3
    need(code in FORMATS, 'unsupported texture format 0x%02x' % code)
    kind, block, size, swap = FORMATS[code]
    need(endian == swap, 'unexpected endian swap %d for %s' % (endian, kind))
    need(fetch[0] >> 31 == 1, 'untiled texture')
    need(((fetch[2] & 0x1FFF) + 1, (fetch[2] >> 13 & 0x1FFF) + 1) == (width, height),
         'fetch-constant size differs from the texture header')
    pitch = (fetch[0] >> 22 & 0x1FF) * 32
    need(pitch >= width and pitch % block == 0, 'pitch narrower than the texture')
    need(fetch[1] & 0xF00 == 0, 'base address not page aligned')
    columns, rows = pitch // block, ((height + block - 1) // block + 31) & ~31
    base = r.offset(fetch[1] & 0xFFFFF000)
    shift = packed_offset(width, height)
    shift = (shift[0] // block, shift[1] // block)
    wide, high = (width + block - 1) // block + shift[0], (height + block - 1) // block + shift[1]
    used = tiled_extent(columns, wide, high, size)
    need(base + used <= len(r.data), 'texture data outside its resource')
    return {'name': name, 'width': width, 'height': height, 'format': kind, 'mips': mips, 'pitch': pitch,
            'offset': base, 'block': block, 'block_bytes': size, 'columns': columns, 'rows': rows,
            'packed': shift}


def packed_offset(width, height):
    """Texel offset of a base level stored in the packed mip tail: a surface whose shorter side is at
    most 16 texels keeps its base level 16 texels along the longer axis of the first 32x32 tile."""
    log_w, log_h = (width - 1).bit_length(), (height - 1).bit_length()
    if min(log_w, log_h) > 4:
        return (0, 0)
    return (0, 16) if log_w > log_h else (16, 0)


def tiled_extent(columns, wide, high, size):
    """Bytes from the base to the end of the last block of the visible area."""
    log = size.bit_length() - 1
    return max(tiled_offset(x, y, columns, log) for y in range(max(0, high - 32), high)
               for x in range(max(0, wide - 32), wide)) + size


def _rgb565(value):
    r, g, b = value >> 11, value >> 5 & 63, value & 31
    return (r << 3 | r >> 2, g << 2 | g >> 4, b << 3 | b >> 2)


def _colour_block(raw, at, opaque_only):
    c0, c1, bits = struct.unpack_from('<HHI', raw, at)
    a, b = _rgb565(c0), _rgb565(c1)
    if c0 > c1 or opaque_only:
        palette = [a + (255,), b + (255,), tuple((2 * p + q) // 3 for p, q in zip(a, b)) + (255,),
                   tuple((p + 2 * q) // 3 for p, q in zip(a, b)) + (255,)]
    else:
        palette = [a + (255,), b + (255,), tuple((p + q) // 2 for p, q in zip(a, b)) + (255,), (0, 0, 0, 0)]
    return [palette[bits >> (2 * i) & 3] for i in range(16)]


def _alpha_block(raw, at):
    a0, a1 = raw[at], raw[at + 1]
    bits = int.from_bytes(raw[at + 2:at + 8], 'little')
    if a0 > a1:
        table = [a0, a1] + [((7 - i) * a0 + i * a1) // 7 for i in range(1, 7)]
    else:
        table = [a0, a1] + [((5 - i) * a0 + i * a1) // 5 for i in range(1, 5)] + [0, 255]
    return [table[bits >> (3 * i) & 7] for i in range(16)]


def pixels(r, tex):
    """RGBA8 bytes of mip level 0, rows top to bottom."""
    width, height, block, size = tex['width'], tex['height'], tex['block'], tex['block_bytes']
    log = size.bit_length() - 1
    out = bytearray(width * height * 4)
    data = r.data
    dx, dy = tex['packed']
    for by in range((height + block - 1) // block):
        for bx in range((width + block - 1) // block):
            at = tex['offset'] + tiled_offset(bx + dx, by + dy, tex['columns'], log)
            if tex['format'] == 'argb8888':
                a, red, g, b = data[at], data[at + 1], data[at + 2], data[at + 3]
                o = (by * width + bx) * 4
                out[o:o + 4] = bytes((red, g, b, a))
                continue
            raw = bytearray(data[at:at + size])
            raw[0::2], raw[1::2] = raw[1::2], raw[0::2]  # 8-in-16 endian swap
            if tex['format'] == 'dxt1':
                texels = _colour_block(raw, 0, False)
            else:
                alpha = _alpha_block(raw, 0)
                texels = [c[:3] + (al,) for c, al in zip(_colour_block(raw, 8, True), alpha)]
            for i, texel in enumerate(texels):
                x, y = bx * 4 + (i & 3), by * 4 + (i >> 2)
                if x < width and y < height:
                    o = (y * width + x) * 4
                    out[o:o + 4] = bytes(texel)
    return bytes(out)


def texture_array(r, at):
    """Textures of a (pointer, count, capacity) array; a null slot stays None."""
    items, count = r.pointer(at), r.u16(at + 4)
    need(count <= r.u16(at + 6), 'array count above its capacity')
    if count == 0:
        return []
    need(items is not None, 'texture array without items')
    return [None if r.u32(items + 4 * i) == 0 else texture(r, r.offset(r.u32(items + 4 * i))) for i in range(count)]


def dictionary(r, at):
    """A texture dictionary: (name hash, texture) pairs."""
    hashes_at, count = r.pointer(at + 0x10), r.u16(at + 0x14)
    textures = texture_array(r, at + 0x18)
    need(count == len(textures), 'dictionary hash and texture counts differ')
    need(count == 0 or hashes_at is not None, 'dictionary without name hashes')
    need(all(tex is not None for tex in textures), 'dictionary with a null texture')
    return [{'hash': r.u32(hashes_at + 4 * i), **textures[i]} for i in range(count)]


def looks_like_dictionary(r, pointer):
    """The shader-group slot holds a texture dictionary only in some packs (otherwise a block map)."""
    if pointer >> 28 != 5:
        return False
    at = r.offset(pointer, 0x20)
    return (r.u32(at + 4) == 0 and r.u32(at + 0x10) >> 28 == 5 and r.u32(at + 0x18) >> 28 == 5
            and 0 < r.u16(at + 0x14) == r.u16(at + 0x1C))


def shader(r, at):
    need(r.u32(at) in SHADER_VFTS, 'not a shader (VFT 0x%08x)' % r.u32(at))
    count = r.u16(at + 0x18)
    values, types, names = r.pointer(at + 0x10), r.pointer(at + 0x1C), r.pointer(at + 0x24)
    need(count == 0 or all(p is not None for p in (values, types, names)),
         'shader without parameter arrays')
    params = []
    for i in range(count):
        kind, pointer, name = r.u8(types + i), r.u32(values + 4 * i), r.u32(names + 4 * i)
        param = {'hash': name, 'type': kind}
        if kind == 0:
            param['texture'] = None if pointer == 0 else texture(r, r.offset(pointer))
        elif pointer:
            at_value = r.offset(pointer, 16 * kind)
            param['value'] = [list(r.unpack('4f', at_value + 16 * k)) for k in range(kind)]
        params.append(param)
    name_at, file_at = r.u32(at + 0x30), r.u32(at + 0x38)
    return {'name': r.cstring(r.offset(name_at)) if name_at else None,
            'file': r.cstring(r.offset(file_at)) if file_at else None,
            'draw_bucket': r.u8(at + 9), 'params': params}


def shader_group(r, at):
    need(r.u32(at) in SHADER_GROUP_VFTS, 'not a shader group (VFT 0x%08x)' % r.u32(at))
    slot = r.u32(at + 4)
    own = dictionary(r, r.offset(slot)) if looks_like_dictionary(r, slot) else []
    shaders_at, count = r.pointer(at + 8), r.u16(at + 0xC)
    need(count > 0 and shaders_at is not None, 'shader group without shaders')
    return {'dictionary': own, 'shaders': [shader(r, r.offset(r.u32(shaders_at + 4 * i))) for i in range(count)]}


def decode(data, virtual, physical, resource_type):
    """`.xtd` (type 9) -> {'textures'}; `.xtp`/`.xtl` (type 83) -> {'shader_group', 'zone', ...}."""
    try:
        r = Resource(data, virtual, physical)
        if resource_type == 9:
            need(r.u32(0) in DICTIONARY_VFTS, 'not a texture dictionary (VFT 0x%08x)' % r.u32(0))
            return {'textures': dictionary(r, 0)}, r
        need(resource_type == 83, 'resource type %d holds no textures' % resource_type)
        need(r.u32(0) in PACK_VFTS, 'not a texture pack (VFT 0x%08x)' % r.u32(0))
        out = {name: None if r.u32(slot) == 0 else texture(r, r.offset(r.u32(slot)))
               for name, slot in (('zone', 0x14), ('max_damage', 0x18), ('scratch', 0x1C))}
        group = r.pointer(0x0C)
        need(group is not None, 'texture pack without a shader group')
        out['shader_group'] = shader_group(r, group)
        return out, r
    except (ResourceError, struct.error) as error:
        raise TextureError(str(error)) from None


def all_textures(decoded):
    """Every distinct texture of a decoded resource (by data offset), in first-seen order."""
    seen, out = set(), []

    def add(tex):
        if tex is not None and tex['offset'] not in seen:
            seen.add(tex['offset'])
            out.append(tex)
    for tex in decoded.get('textures', []):
        add(tex)
    for name in ('zone', 'max_damage', 'scratch'):
        add(decoded.get(name))
    group = decoded.get('shader_group') or {'dictionary': [], 'shaders': []}
    for tex in group['dictionary']:
        add(tex)
    for s in group['shaders']:
        for p in s['params']:
            add(p.get('texture'))
    return out
