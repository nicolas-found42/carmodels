"""Read-only decoding of Midnight Club: Los Angeles model resources (`.xrsc`, RSC5 type 63).

Layouts are readings taken from CodeX.Games.MCLA `RSC5/Rsc5ModelResource.cs` and `RSC5/Rsc5Drawable.cs`
(dedc3156; no code copied) and checked on every car model of the disc:

- Model resource: VFT, block map, pointer to a drawable LOD (+0x08), skeleton pointer (+0x24).
- Drawable LOD: pointer array of models (pointer, count, capacity).
- Model (grmModel): VFT, geometry pointer array (+0x04), bounding spheres (+0x0C: one per geometry
  plus one for the model when it has several), shader index per geometry (+0x10), matrix count,
  flags, type, matrix index, stride, skin flag (+0x14..+0x19), geometry count (+0x1A).
- Geometry (grmGeometry): vertex buffer (+0x0C), index buffer (+0x1C), index count (+0x2C),
  primitive count (+0x30), vertex count (+0x34), primitive type (+0x36), vertex stride (+0x3C).
- Vertex buffer: vertex count (+0x04), stride (+0x0C), vertex format (+0x10), vertex data (+0x18).
  The format is a channel mask, a byte size and sixteen 4-bit component types.
- Index buffer: index count (+0x04), 16-bit index data (+0x08).
- Skeleton (crSkeletonData): bone array (+0x00), bone count (+0x14); 224-byte bones with a name
  pointer, parent pointer (+0x10), index (+0x14), id (+0x16), local translation (+0x20), rotation
  quaternion (+0x40) and model-space offset (+0x60).

All values are big-endian. Coordinates are native: Y up, the car faces -Z (a reading recorded where
previews are assembled). Every structural rule below raises ModelError when a resource breaks it.
"""
import math
import struct

from mcla_resource import Resource, ResourceError

# Root VFTs, stored little-endian: 0x0057C350 (car and rim models), 0x0056C884 (brake models, same layout).
MODEL_VFTS = (0x50C35700, 0x84C85600)
TRIANGLE_LIST = 3
TYPE_TABLE = 0xAA1111111199A996  # the only vertex component-type table on the disc
CHANNELS = ('position', 'blend_weights', 'blend_indices', 'normal', 'colour0', 'colour1',
            'texcoord0', 'texcoord1', 'texcoord2', 'texcoord3', 'texcoord4', 'texcoord5', 'texcoord6',
            'texcoord7', 'tangent', 'binormal')
COMPONENT = {1: ('half2', 4), 6: ('float3', 12), 9: ('ubyte4', 4), 10: ('dec3n', 4)}
BONE = 224
SPHERE_TOLERANCE = 1e-3
F3 = struct.Struct('>3f')
H2 = struct.Struct('>2e')
U32 = struct.Struct('>I')


class ModelError(ValueError):
    pass


def need(condition, message):
    if not condition:
        raise ModelError(message)


def vertex_format(mask, size, types):
    """[(channel name, kind, byte offset)] for a vertex format; raises unless the sizes add up."""
    need(types == TYPE_TABLE, 'unexpected vertex component table 0x%016x' % types)
    layout, offset = [], 0
    for channel in range(16):
        if mask >> channel & 1:
            kind, width = COMPONENT[types >> (4 * channel) & 15]  # every code of TYPE_TABLE is listed
            layout.append((CHANNELS[channel], kind, offset))
            offset += width
    need(mask >> 16 == 0, 'vertex channel mask above 16 channels')
    need(offset == size, 'vertex format size %d differs from its channels (%d)' % (size, offset))
    need(layout and layout[0][0] == 'position', 'vertex format without positions')
    return layout


def dec3n(word):
    """Three signed 10-bit components scaled by 1/511."""
    out = []
    for shift in (0, 10, 20):
        value = word >> shift & 0x3FF
        out.append((value - 1024 if value & 0x200 else value) / 511)
    return tuple(out)


def read_channel(data, start, stride, count, kind, offset):
    at = start + offset
    if kind == 'float3':
        return [F3.unpack_from(data, at + i * stride) for i in range(count)]
    if kind == 'half2':
        return [H2.unpack_from(data, at + i * stride) for i in range(count)]
    if kind == 'dec3n':
        return [dec3n(U32.unpack_from(data, at + i * stride)[0]) for i in range(count)]
    return [tuple(data[at + i * stride:at + i * stride + 4]) for i in range(count)]


def skeleton(r, at):
    """Bones in stored order: name, id, parent index, local translation, Euler rotation, model-space offset.

    Checks: each bone's index field equals its position, parents precede children, the rotation
    quaternion is the identity, and below unrotated ancestors each stored model-space offset equals the
    parent's offset plus the local translation. Rotations are carried as Euler angles (+0x30, +0x70);
    `rotated` marks a bone whose ancestors rotate, so its stored offset is not a plain sum."""
    bones_at, count = r.pointer(at), r.u16(at + 0x14)
    need(count > 0 and bones_at is not None, 'skeleton without bones')
    r.need(bones_at, count * BONE)
    bones = []
    for index in range(count):
        b = bones_at + index * BONE
        name = r.cstring(r.offset(r.u32(b)))
        parent_pointer = r.u32(b + 0x10)
        parent = -1
        if parent_pointer:
            delta = r.offset(parent_pointer, BONE) - bones_at
            need(delta % BONE == 0 and 0 <= delta // BONE < index, 'bone parent outside its skeleton or after the bone')
            parent = delta // BONE
        need(r.u16(b + 0x14) == index, 'bone index field differs from its position')
        local = r.unpack('3f', b + 0x20)
        euler = r.unpack('3f', b + 0x30)
        need(r.unpack('4f', b + 0x40) == (0.0, 0.0, 0.0, 1.0), 'bone %s has a rotation quaternion' % name)
        orient = r.unpack('3f', b + 0x70)
        model_space = r.unpack('3f', b + 0x60)
        rotated = parent >= 0 and (bones[parent]['rotated'] or any(bones[parent]['euler']) or any(bones[parent]['orient']))
        if not rotated:
            expected = local if parent < 0 else tuple(p + q for p, q in zip(bones[parent]['model'], local))
            need(all(abs(a - b) <= 1e-4 for a, b in zip(model_space, expected)),
                 'bone %s model-space offset differs from its parent chain' % name)
        bones.append({'name': name, 'id': r.u16(b + 0x16), 'parent': parent, 'local': local, 'euler': euler,
                      'orient': orient, 'model': model_space, 'rotated': rotated})
    return bones


def geometry(r, at, sphere):
    vb, ib = r.pointer(at + 0x0C, 0x20), r.pointer(at + 0x1C, 0x10)
    need(vb is not None and ib is not None, 'geometry without vertex or index buffer')
    need(all(r.u32(at + k) == 0 for k in (0x10, 0x14, 0x18, 0x20, 0x24, 0x28)), 'geometry with a second buffer set')
    index_count, primitives = r.u32(at + 0x2C), r.u32(at + 0x30)
    vertex_count, primitive_type, stride = r.u16(at + 0x34), r.u16(at + 0x36), r.u16(at + 0x3C)
    need(primitive_type == TRIANGLE_LIST, 'primitive type %d is not a triangle list' % primitive_type)
    need(primitives * 3 == index_count, 'primitive count differs from index count')
    need(r.u16(vb + 4) == vertex_count, 'vertex buffer count differs from the geometry')
    need(r.u32(vb + 0x0C) == stride, 'vertex buffer stride differs from the geometry')
    need(r.u32(vb + 0x08) == r.u32(vb + 0x18), 'locked vertex data differs from vertex data')
    fvf = r.offset(r.u32(vb + 0x10), 16)
    layout = vertex_format(r.u32(fvf), r.u8(fvf + 4), r.unpack('Q', fvf + 8)[0])
    need(r.u8(fvf + 4) == stride, 'vertex format size differs from the stride')
    data_at = r.offset(r.u32(vb + 0x18), vertex_count * stride)
    need(r.u32(ib + 4) == index_count, 'index buffer count differs from the geometry')
    index_at = r.offset(r.u32(ib + 8), 2 * index_count)
    indices = list(struct.unpack_from('>%dH' % index_count, r.data, index_at))
    need(not indices or max(indices) < vertex_count, 'index outside the vertex buffer')
    channels = {name: read_channel(r.data, data_at, stride, vertex_count, kind, offset) for name, kind, offset in layout}
    if sphere is not None:
        cx, cy, cz, radius = sphere
        limit = (radius + SPHERE_TOLERANCE) ** 2
        need(all((x - cx) ** 2 + (y - cy) ** 2 + (z - cz) ** 2 <= limit for x, y, z in channels['position']),
             'vertex outside its bounding sphere')
    return {'vertex_count': vertex_count, 'index_count': index_count, 'stride': stride,
            'channels': [name for name, _, _ in layout], 'indices': indices, 'sphere': sphere, **channels}


def model(r, at):
    geometries_at, count = r.pointer(at + 4), r.u16(at + 8)
    need(count > 0 and geometries_at is not None, 'model without geometries')
    need(r.u16(at + 0x1A) == count, 'model geometry count fields differ')
    spheres_at = r.pointer(at + 0x0C)
    shaders_at = r.pointer(at + 0x10, 2 * count)
    spheres = None
    if spheres_at is not None:
        stored = count + 1 if count > 1 else 1
        r.need(spheres_at, 16 * stored)
        spheres = [r.unpack('4f', spheres_at + 16 * i) for i in range(stored)]
        need(all(math.isfinite(v) for s in spheres for v in s), 'bounding sphere is not finite')
    shaders = [r.u16(shaders_at + 2 * i) for i in range(count)] if shaders_at is not None else [None] * count
    matrix_count, flags, _kind, matrix_index, _stride, skin = r.unpack('6B', at + 0x14)
    geometries = []
    for i in range(count):
        sphere = None if spheres is None else spheres[i + 1 if count > 1 else 0]
        g = geometry(r, r.offset(r.u32(geometries_at + 4 * i), 0x50), sphere)
        g['shader'] = shaders[i]
        geometries.append(g)
    return {'geometries': geometries, 'sphere': None if spheres is None else spheres[0],
            'matrix_count': matrix_count, 'matrix_index': matrix_index, 'flags': flags, 'skinned': bool(skin)}


def decode(data, virtual, physical):
    """A decompressed model resource -> {'skeleton': [...], 'models': [...]}."""
    try:
        r = Resource(data, virtual, physical)
        need(r.u32(0) in MODEL_VFTS, 'not a model resource (VFT 0x%08x)' % r.u32(0))
        lod = r.pointer(8, 8)
        need(lod is not None, 'model resource without a drawable LOD')
        models_at, count = r.pointer(lod), r.u16(lod + 4)
        need(count > 0 and models_at is not None, 'drawable LOD without models')
        skeleton_at = r.pointer(0x24, 0x40)
        bones = skeleton(r, skeleton_at) if skeleton_at is not None else []
        models = [model(r, r.offset(r.u32(models_at + 4 * i), 0x1C)) for i in range(count)]
    except (ResourceError, struct.error) as error:
        raise ModelError(str(error)) from None
    return {'skeleton': bones, 'models': models}


def summary(decoded):
    """Fixed facts of a decoded model resource, for receipts."""
    geometries = [g for m in decoded['models'] for g in m['geometries']]
    points = [p for g in geometries for p in g['position']]
    low = [min(p[k] for p in points) for k in range(3)] if points else None
    high = [max(p[k] for p in points) for k in range(3)] if points else None
    return {'bones': len(decoded['skeleton']), 'models': len(decoded['models']), 'geometries': len(geometries),
            'vertices': sum(g['vertex_count'] for g in geometries),
            'triangles': sum(g['index_count'] for g in geometries) // 3,
            'bounds': None if low is None else [[round(v, 4) for v in low], [round(v, 4) for v in high]]}
