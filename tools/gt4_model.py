"""Read-only Gran Turismo 4 CAR4 / ModelSet2 (MDLS) / TextureSet1 (Tex1) decoding.

Layouts follow Nenkai's MIT-licensed PDTools (ModelSet2, PGLUshape, VIF, render commands,
TextureSet1, GSMemory) and GT-File-Specifications-Documentation (CAR4 header); see
research/gran-turismo-4-previews.md for pinned commits. Every offset is bounds-checked.
This module decodes static geometry and textures only; runtime VM state is not executed.
"""
from array import array
import math
import struct

MDLS = b'MDLS'
TEX1 = b'Tex1'
CAR4 = b'CAR4'
SCALE = 1 / 4096  # Integer VIF unpacks are fixed point with 12 fractional bits.
MAX_STEPS = 20000
PSMCT32, PSMT8, PSMT4 = 0x00, 0x13, 0x14
# CAR4 header slots (GT4_CAR4_CarInfo.bt): car info, collision, body, body patch, wheel, wheel
# patch, wing, two tire model sets, built-in driver.
CAR4_SLOTS = ('car_info', 'collision', 'body', 'body_patch', 'wheel', 'wheel_patch', 'wing',
              'tire_front', 'tire_rear', 'driver')


class Reader:
    def __init__(self, data):
        self.data = data

    def need(self, offset, size):
        if offset < 0 or size < 0 or offset + size > len(self.data):
            raise ValueError('read outside GT4 model data')

    def unpack(self, fmt, offset):
        self.need(offset, struct.calcsize(fmt))
        return struct.unpack_from(fmt, self.data, offset)

    def u32(self, offset):
        return self.unpack('<I', offset)[0]


def car4_slots(data):
    r = Reader(data)
    if data[:4] != CAR4:
        raise ValueError('not a CAR4 car model')
    values = r.unpack('<10I', 0x10)
    slots = {}
    for name, offset in zip(CAR4_SLOTS, values):
        if offset:
            r.need(offset, 4)
            slots[name] = offset
    for name in ('body', 'wheel', 'tire_front', 'tire_rear'):
        if name in slots and data[slots[name]:slots[name] + 4] != MDLS:
            raise ValueError('CAR4 model set slot lacks MDLS: ' + name)
    if 'body' not in slots:
        raise ValueError('CAR4 has no body model set')
    return slots


def car_info(data, offset):
    """Fields used for placement: TirePosRelated holds front/rear tire diameters (metres)."""
    r = Reader(data)
    front, rear = r.unpack('<2f', offset + 0x58)
    return {'tire_diameter_front': front, 'tire_diameter_rear': rear}


def collision_bounds(data, offset):
    r = Reader(data)
    count = data[offset] if offset < len(data) else 0
    if not 0 < count <= 64:
        raise ValueError('invalid CAR4 collision model')
    points = [r.unpack('<3f', offset + 4 + 24 * i) for i in range(count)]
    return [[min(p[k] for p in points) for k in range(3)], [max(p[k] for p in points) for k in range(3)]]


class ModelSet:
    """One MDLS block; all offsets inside it are relative to its start."""
    HEADER = struct.Struct('<4sIIII BB HHHHHHHHHHH BBH 6x H 11I')

    def __init__(self, data, base):
        self.r, self.base, self.data = Reader(data), base, data
        fields = self.r.unpack(self.HEADER.format, base)
        (magic, _, _, _, size, _, _, self.model_count, self.shape_count, self.material_count,
         self.lod_count, self.colour_count, *_rest) = fields
        offsets = fields[-11:]
        if magic != MDLS or not 0 < size <= len(data) - base:
            raise ValueError('invalid MDLS header')
        if not (self.model_count <= 64 and self.shape_count <= 4096 and self.material_count <= 512
                and self.lod_count <= 16 and self.colour_count <= 64):
            raise ValueError('MDLS counts exceed limits')
        self.size = size
        self.models_at, self.shapes_at, self.materials_at, self.textures_at = offsets[:4]
        self.end = base + size

    def at(self, offset, size=0):
        if offset < 0 or offset + size > self.size:
            raise ValueError('MDLS offset outside model set')
        return self.base + offset

    def materials(self):
        rows = []
        for i in range(self.material_count):
            values = self.r.unpack('<16f', self.at(self.materials_at + 0x50 * i, 0x50))
            rows.append({'ambient': values[0:4], 'diffuse': values[4:8], 'specular': values[8:12]})
        return rows

    def model_commands(self, index):
        if not 0 <= index < self.model_count:
            raise ValueError('model index outside MDLS')
        p = self.at(self.models_at + 0x28 * index, 0x28)
        bounds = self.r.unpack('<B', p + 1)[0]
        origin = self.r.unpack('<f3f', p + 8)
        return self.at(self.r.u32(p + 0x18)), bounds, origin

    def shape(self, index):
        if not 0 <= index < self.shape_count:
            raise ValueError('shape index outside MDLS')
        offset = self.r.u32(self.at(self.shapes_at + 4 * index, 4))
        p = self.at(offset, 16)
        _, _, bits, _, chunks, strip_verts, triangles = self.r.unpack('<IIBBHHH', p)
        if chunks > 256:
            raise ValueError('shape packet count exceeds limit')
        packets = []
        for i in range(chunks):
            data_at, qwords, flags = self.r.unpack('<IHH', p + 16 + 8 * i)
            start = p + data_at
            if not (self.base <= start and start + 16 * qwords <= self.end):
                raise ValueError('VIF packet outside model set')
            packets.append({'texture': flags & 0x1FF, 'material': (flags >> 9) & 0x7F,
                            **packet_geometry(vif_commands(self.data, start, qwords))})
        verts = sum(len(p['positions']) for p in packets)
        tris = sum(len(p['triangles']) for p in packets)
        if verts != strip_verts or tris != triangles:
            raise ValueError('shape strip totals differ from header')
        return {'kind': bits & 0x1F, 'packets': packets, 'vertices': verts, 'triangles': tris}

    def texture_set(self, colour, lod):
        if not (0 <= colour < self.colour_count and 0 <= lod < self.lod_count):
            raise ValueError('texture set outside MDLS')
        table = self.r.u32(self.at(self.textures_at + 4 * colour, 4))
        offset = self.r.u32(self.at(table + 4 * lod, 4))
        return TextureSet(self.data, self.at(offset, 0x30), self.end)


def vif_commands(data, pos, qwords):
    """VIFcode stream of one shape packet; returns UNPACK payloads (addr, format, rows)."""
    end = pos + 16 * qwords
    if end > len(data):
        raise ValueError('VIF packet outside file')
    out = []
    while pos < end:
        addr, num, cmd = struct.unpack_from('<HBB', data, pos)
        pos += 4
        op = cmd & 0x7F
        if op & 0x60 == 0x60:
            fmt = op & 0x0F
            width = (fmt >> 2) + 1
            size = (4, 2, 1)[fmt & 3] if fmt & 3 != 3 else None
            if size is None or fmt == 0x0F:
                raise ValueError('unsupported VIF unpack format')
            count = num or 256
            total = count * width * size
            if pos + total > end:
                raise ValueError('VIF unpack outside packet')
            code = {4: 'i', 2: 'h', 1: 'b'}[size]
            if addr & 0x4000:  # USN: unsigned unpack.
                code = code.upper()
            values = struct.unpack_from('<%d%s' % (count * width, code), data, pos)
            rows = [values[i * width:(i + 1) * width] for i in range(count)]
            out.append((addr, fmt, rows))
            pos += total
        elif op in (0x30, 0x31):  # STROW / STCOL carry four words.
            pos += 16
        elif op == 0x20:  # STMASK carries one word.
            pos += 4
        elif op in (0x00, 0x01, 0x05, 0x10, 0x11, 0x13, 0x14, 0x15, 0x17):
            pass
        else:
            raise ValueError('unsupported VIF command 0x%02x' % op)
        pos = (pos + 3) & ~3
    return out


def as_float(row):
    return struct.unpack('<%df' % len(row), struct.pack('<%dI' % len(row), *[v & 0xFFFFFFFF for v in row]))


def packet_geometry(commands):
    """Attributes may arrive as contiguous segments of differing widths; later disjoint data
    (morph targets at another slot offset) is not part of the rest pose and is ignored."""
    slots = {'position': [], 'uv': [], 'normal': [], 'colour': []}
    strips = None
    for addr, fmt, rows in commands:
        if (addr & 0x3FF) == 0xC0:  # GIF tag.
            continue
        if fmt == 0x02:
            strips = [v[0] for v in rows]
            continue
        slot_base = addr & 0x3C0
        offset = (addr & 0x3FF) - slot_base
        width = (fmt >> 2) + 1
        floats = (fmt & 3) == 0 and bool(addr & 0x4000)
        if slot_base == 0x00 and width == 3:
            name = 'position'
        elif width == 2:
            name = 'uv'
        elif width == 3:
            name = 'normal'
        elif width == 4 and fmt == 0x0E:
            name = 'colour'
        else:
            raise ValueError('unexpected VIF attribute layout')
        target = slots[name]
        if offset != len(target):
            continue
        for row in rows:
            if name == 'colour':
                target.append(tuple(min(v, 0x80) / 0x80 for v in row))
            elif floats:
                target.append(as_float(row))
            elif name == 'normal' and fmt == 0x0A:
                target.append(tuple(v / 127 for v in row))
            else:
                target.append(tuple(v * SCALE for v in row))
    positions = slots['position']
    if strips is None or not strips or strips[0] != len(strips) - 1:
        raise ValueError('VIF packet lacks strip lengths')
    lengths = [(b + 6) // 3 for b in strips[1:]]
    if sum(lengths) != len(positions) or any(n < 3 for n in lengths):
        raise ValueError('strip lengths differ from vertex count')
    triangles, start = [], 0
    for n in lengths:
        for k in range(n - 2):
            a, b, c = start + k, start + k + 1, start + k + 2
            triangles.append((a, b, c) if k % 2 == 0 else (c, b, a))
        start += n
    for name in ('uv', 'normal', 'colour'):
        if slots[name] and len(slots[name]) != len(positions):
            slots[name] = []
    if any(not all(math.isfinite(v) for v in p) for p in positions):
        raise ValueError('non-finite vertex position')
    return {'positions': positions, 'uvs': slots['uv'], 'normals': slots['normal'],
            'colours': slots['colour'], 'triangles': triangles}


IDENTITY = (1., 0., 0., 0., 0., 1., 0., 0., 0., 0., 1., 0., 0., 0., 0., 1.)


def multiply(a, b):
    """Row-vector convention: a point p becomes p * a * b."""
    return tuple(sum(a[r * 4 + k] * b[k * 4 + c] for k in range(4)) for r in range(4) for c in range(4))


def transform(m, p):
    x, y, z = p
    return (x * m[0] + y * m[4] + z * m[8] + m[12], x * m[1] + y * m[5] + z * m[9] + m[13],
            x * m[2] + y * m[6] + z * m[10] + m[14])


# Operand sizes for render commands that do not affect static shape selection (PDTools RenderCommands).
SKIP = {11: 0, 14: 1, 23: 0, 24: 0, 25: 1, 28: 2, 29: 0, 30: 0, 31: 1, 32: 2, 33: 4, 34: 0,
        35: 0, 36: 4, 39: 4, 40: 16, 41: 1, 42: 1, 45: 0, 46: 0, 47: 1, 49: 12, 50: 4,
        51: 16, 52: 4, 53: 4, 64: 0, 67: 0, 68: 2, 69: 2, 70: 2, 72: 2, 73: 2, 74: 2, 75: 2, 76: 2,
        78: 0, 79: 0, 80: 1, 81: 2, 82: 16, 83: 16, 84: 8, 85: 8, 86: 0, 87: 0, 88: 0, 89: 1, 90: 2}


def walk_model(ms, index, lod=0, branch=0, depth=0, callback_matrices=None):
    """Static walk: the chosen LOD, callback branch `branch`, VM branches' first target and identity
    for VM-driven transforms. Returns draws [(shape, texture table, matrix, state)] where state
    records depth-mask and alpha-test (ModelSet2::begin enables both). `callback_matrices` maps a
    model-callback parameter to a matrix the caller supplies in place of the game's runtime one."""
    if depth > 8:
        raise ValueError('render model recursion limit')
    d, r = ms.data, ms.r
    pc, _, _ = ms.model_commands(index)
    draws, table, stack, matrix = [], 0, [], IDENTITY
    state = {'depth_mask': True, 'alpha_test': True}
    for _ in range(MAX_STEPS):
        if not ms.base <= pc < ms.end:
            raise ValueError('render command outside model set')
        op = d[pc]
        pc += 1
        if op == 0:
            return draws
        if op in (2, 3):
            child = d[pc] if op == 2 else r.unpack('<H', pc)[0]
            pc += 1 if op == 2 else 2
            draws += [(s, t, multiply(m, matrix), f) for s, t, m, f in walk_model(ms, child, lod, branch, depth + 1, callback_matrices)]
        elif op in (4, 5):
            shape = d[pc] if op == 4 else r.unpack('<H', pc)[0]
            pc += 1 if op == 4 else 2
            draws.append((shape, table, matrix, dict(state)))
        elif op == 6:
            parameter, count = r.unpack('<H', pc)[0], d[pc + 2]
            if callback_matrices and parameter in callback_matrices:
                matrix = multiply(callback_matrices[parameter], matrix)
            table_at = pc + 3
            pc = table_at + 2 * count if not count else table_at + 2 * min(branch, count - 1) + r.unpack('<H', table_at + 2 * min(branch, count - 1))[0]
        elif op == 7:
            count = d[pc + 16]
            table_at = pc + 17
            if not count:
                raise ValueError('LOD select without branches')
            pick = min(lod, count - 1)
            pc = table_at + 2 * pick + r.unpack('<H', table_at + 2 * pick)[0]
        elif op == 8:
            pc += d[pc]
        elif op == 9:
            pc += r.unpack('<H', pc)[0]
        elif op == 10:
            pc += 1 + 12 * d[pc] + 2
        elif op == 12:
            stack.append(matrix)
            if len(stack) > 64:
                raise ValueError('matrix stack overflow')
        elif op == 13:
            if not stack:
                raise ValueError('matrix stack underflow')
            matrix = stack.pop()
        elif op in (15, 16):
            m = r.unpack('<16f', pc)
            pc += 64
            matrix = m if op == 15 else multiply(m, matrix)
        elif op in (17, 18):
            x, y, z = r.unpack('<3f', pc)
            pc += 12
            m = (1, 0, 0, 0, 0, 1, 0, 0, 0, 0, 1, 0, x, y, z, 1) if op == 17 else (x, 0, 0, 0, 0, y, 0, 0, 0, 0, z, 0, 0, 0, 0, 1)
            matrix = multiply(m, matrix)
        elif op == 19:
            pc += 16
        elif op in (20, 21, 22):
            a = r.unpack('<f', pc)[0]
            pc += 4
            c, s = math.cos(a), math.sin(a)
            m = {20: (1, 0, 0, 0, 0, c, s, 0, 0, -s, c, 0, 0, 0, 0, 1),
                 21: (c, 0, -s, 0, 0, 1, 0, 0, s, 0, c, 0, 0, 0, 0, 1),
                 22: (c, s, 0, 0, -s, c, 0, 0, 0, 0, 1, 0, 0, 0, 0, 1)}[op]
            matrix = multiply(m, matrix)
        elif op in (26, 27):
            state['alpha_test'] = op == 26
        elif op in (37, 38):
            state['depth_mask'] = op == 38
        elif op == 43:
            table = d[pc]
            pc += 1
        elif op == 44:
            table = r.unpack('<H', pc)[0]
            pc += 2
        elif op == 77:
            count = d[pc + 2]
            table_at = pc + 3
            pc = table_at + 2 * count if not count else table_at + r.unpack('<h', table_at)[0]
        elif op in SKIP:
            pc += SKIP[op]
        else:
            raise ValueError('unsupported render command %d' % op)
    raise ValueError('render command step limit')


# ---------------------------------------------------------------- textures

def _page_table(page_w, page_h, block_w, block_h, layout, columns_per_block, column_fn):
    """Word (and sub-word) location of every pixel inside one GS page."""
    table = []
    for py in range(page_h):
        for px in range(page_w):
            bx, by = px // block_w, py // block_h
            block = layout[bx + by * (page_w // block_w)]
            x, y = px - bx * block_w, py - by * block_h
            table.append(block * 64 + column_fn(x, y))
    return table


CT32_BLOCKS = (0, 1, 4, 5, 16, 17, 20, 21, 2, 3, 6, 7, 18, 19, 22, 23,
               8, 9, 12, 13, 24, 25, 28, 29, 10, 11, 14, 15, 26, 27, 30, 31)
CT32_WORDS = (0, 1, 4, 5, 8, 9, 12, 13, 2, 3, 6, 7, 10, 11, 14, 15)
T8_WORDS = ((0, 1, 4, 5, 8, 9, 12, 13, 0, 1, 4, 5, 8, 9, 12, 13, 2, 3, 6, 7, 10, 11, 14, 15, 2, 3, 6, 7, 10, 11, 14, 15,
             8, 9, 12, 13, 0, 1, 4, 5, 8, 9, 12, 13, 0, 1, 4, 5, 10, 11, 14, 15, 2, 3, 6, 7, 10, 11, 14, 15, 2, 3, 6, 7),
            (8, 9, 12, 13, 0, 1, 4, 5, 8, 9, 12, 13, 0, 1, 4, 5, 10, 11, 14, 15, 2, 3, 6, 7, 10, 11, 14, 15, 2, 3, 6, 7,
             0, 1, 4, 5, 8, 9, 12, 13, 0, 1, 4, 5, 8, 9, 12, 13, 2, 3, 6, 7, 10, 11, 14, 15, 2, 3, 6, 7, 10, 11, 14, 15))
T8_BYTES = tuple([0] * 8 + [2] * 8 + [0] * 8 + [2] * 8 + [1] * 8 + [3] * 8 + [1] * 8 + [3] * 8)
T4_BLOCKS = (0, 2, 8, 10, 1, 3, 9, 11, 4, 6, 12, 14, 5, 7, 13, 15,
             16, 18, 24, 26, 17, 19, 25, 27, 20, 22, 28, 30, 21, 23, 29, 31)
_T4_ROW0 = (0, 1, 4, 5, 8, 9, 12, 13) * 4
_T4_ROW1 = (2, 3, 6, 7, 10, 11, 14, 15) * 4
_T4_ROW2 = (8, 9, 12, 13, 0, 1, 4, 5) * 4
_T4_ROW3 = (10, 11, 14, 15, 2, 3, 6, 7) * 4
T4_WORDS = (_T4_ROW0 + _T4_ROW1 + _T4_ROW2 + _T4_ROW3, _T4_ROW2 + _T4_ROW3 + _T4_ROW0 + _T4_ROW1)
T4_NIBBLES = tuple(([0] * 8 + [2] * 8 + [4] * 8 + [6] * 8) * 2 + ([1] * 8 + [3] * 8 + [5] * 8 + [7] * 8) * 2)

CT32_PAGE = _page_table(64, 32, 8, 8, CT32_BLOCKS, 1,
                        lambda x, y: (y // 2) * 16 + CT32_WORDS[x + (y % 2) * 8])
T8_PAGE = []
for _py in range(64):
    for _px in range(128):
        _bx, _by = _px // 16, _py // 16
        _x, _y = _px - _bx * 16, _py - _by * 16
        _col = _y // 4
        _i = _x + (_y % 4) * 16
        T8_PAGE.append(((CT32_BLOCKS[_bx + _by * 8] * 64 + _col * 16 + T8_WORDS[_col & 1][_i]) << 2) | T8_BYTES[_i])
T4_PAGE = []
for _py in range(128):
    for _px in range(128):
        _bx, _by = _px // 32, _py // 16
        _x, _y = _px - _bx * 32, _py - _by * 16
        _col = _y // 4
        _i = _x + (_y % 4) * 32
        T4_PAGE.append(((T4_BLOCKS[_bx + _by * 4] * 64 + _col * 16 + T4_WORDS[_col & 1][_i]) << 3) | T4_NIBBLES[_i])
GS_WORDS = 1 << 20


class GSMemory:
    def __init__(self):
        self.words = array('I', bytes(4 * GS_WORDS))

    def write_ct32(self, bp, bw, width, height, data):
        if len(data) < 4 * width * height:
            raise ValueError('GS transfer data truncated')
        src = array('I')
        src.frombytes(bytes(data[:4 * width * height]))
        if src.itemsize != 4:
            raise ValueError('unsupported array word size')
        words, base, i = self.words, bp * 64, 0
        bw = max(bw, 1)
        for y in range(height):
            row_page = (y // 32) * bw
            row_off = (y % 32) * 64
            for x in range(width):
                address = base + (x // 64 + row_page) * 2048 + CT32_PAGE[row_off + (x % 64)]
                if address >= GS_WORDS:
                    raise ValueError('GS transfer outside memory')
                words[address] = src[i]
                i += 1

    def read_ct32(self, bp, bw, width, height, offset_words=0):
        words, base, out = self.words, bp * 64, []
        bw = max(bw, 1)
        for y in range(height):
            for x in range(width):
                address = base + (x // 64 + (y // 32) * bw) * 2048 + CT32_PAGE[(y % 32) * 64 + (x % 64)] + offset_words
                out.append(words[address % GS_WORDS])
        return out

    def read_indices(self, psm, bp, bw, width, height):
        words, base, out = self.words, bp * 64, bytearray(width * height)
        bw = max(bw >> 1, 1)  # TBW is in 64-pixel units; T8/T4 pages are 128 pixels wide.
        i = 0
        for y in range(height):
            for x in range(width):
                if psm == PSMT8:
                    loc = T8_PAGE[(y % 64) * 128 + (x % 128)]
                    address = base + (x // 128 + (y // 64) * bw) * 2048 + (loc >> 2)
                    out[i] = (words[address % GS_WORDS] >> (8 * (loc & 3))) & 0xFF
                else:
                    loc = T4_PAGE[(y % 128) * 128 + (x % 128)]
                    address = base + (x // 128 + (y // 128) * bw) * 2048 + (loc >> 3)
                    out[i] = (words[address % GS_WORDS] >> (4 * (loc & 7))) & 0x0F
                i += 1
        return out


def _bits(value, low, count):
    return (value >> low) & ((1 << count) - 1)


class TextureSet:
    def __init__(self, data, base, limit):
        r = Reader(data)
        if data[base:base + 4] != TEX1:
            raise ValueError('missing Tex1 texture set')
        size = r.u32(base + 12)
        self.data, self._memory, self.textures, self.transfers = data, None, [], []
        if size == 0:  # Placeholder set for an unused texture LOD.
            return
        if size < 0x30 or base + size > limit:
            raise ValueError('Tex1 outside model set')
        _, _, count, transfers, tex_at, transfer_at, _ = r.unpack('<hHHHIII', base + 0x10)
        if count > 512 or transfers > 64:
            raise ValueError('Tex1 counts exceed limits')
        for i in range(count):
            tex0, _, _, _, clamp = r.unpack('<5Q', base + tex_at + 0x28 * i)
            self.textures.append({
                'tbp': _bits(tex0, 0, 14), 'tbw': _bits(tex0, 14, 6), 'psm': _bits(tex0, 20, 6),
                'tw': _bits(tex0, 26, 4), 'th': _bits(tex0, 30, 4), 'tcc': _bits(tex0, 34, 1),
                'cbp': _bits(tex0, 37, 14), 'cpsm': _bits(tex0, 51, 4), 'csa': _bits(tex0, 56, 5),
                'wms': _bits(clamp, 0, 2), 'wmt': _bits(clamp, 2, 2),
                'maxu': _bits(clamp, 14, 10), 'maxv': _bits(clamp, 34, 10)})
        for i in range(transfers):
            offset, bp, bw, fmt, w, h = r.unpack('<IHBBHH', base + transfer_at + 12 * i)
            if fmt != PSMCT32 or w > 1024 or h > 2048:
                raise ValueError('unsupported Tex1 transfer')
            r.need(base + offset, 4 * w * h)
            self.transfers.append((bp, bw, w, h, base + offset))

    def memory(self):
        if self._memory is None:
            gs = GSMemory()
            for bp, bw, w, h, at in self.transfers:
                gs.write_ct32(bp, bw, w, h, memoryview(self.data)[at:at + 4 * w * h])
            self._memory = gs
        return self._memory

    def image(self, index):
        """RGBA8 image at the full 2^TW x 2^TH size; GS alpha 0..0x80 is rescaled to 0..255."""
        if not 0 <= index < len(self.textures):
            raise ValueError('texture index outside Tex1')
        t = self.textures[index]
        width, height = 1 << t['tw'], 1 << t['th']
        if width > 1024 or height > 1024:
            raise ValueError('texture dimensions exceed limit')
        gs = self.memory()
        if t['psm'] in (PSMT4, PSMT8):
            if t['cpsm'] != PSMCT32:
                raise ValueError('unsupported CLUT format')
            indices = gs.read_indices(t['psm'], t['tbp'], t['tbw'], width, height)
            if t['psm'] == PSMT4:
                palette = gs.read_ct32(t['cbp'], 1, 8, 2, t['csa'] * 8)
            else:
                raw = gs.read_ct32(t['cbp'], 1, 16, 16, t['csa'] * 8)
                # The 16x16 CLUT is stored as 8x2 tiles (PDTools MakeTiledPalette, after tiledggd).
                palette = [0] * 256
                for i, colour in enumerate(raw):
                    palette[((i // 32) * 2 + (i // 8) % 2) * 16 + ((i // 16) % 2) * 8 + i % 8] = colour
            colours = [_rgba(c) for c in palette]
            rgba = b''.join(colours[i] for i in indices)
        elif t['psm'] == PSMCT32:
            rgba = b''.join(_rgba(c) for c in gs.read_ct32(t['tbp'], t['tbw'], width, height))
        else:
            raise ValueError('unsupported texture format 0x%x' % t['psm'])
        return {'width': width, 'height': height, 'rgba': rgba,
                'clamp': (t['wms'] != 0, t['wmt'] != 0), 'region': (t['maxu'] + 1, t['maxv'] + 1)}


def _rgba(word):
    return bytes((word & 0xFF, (word >> 8) & 0xFF, (word >> 16) & 0xFF, min(255, ((word >> 24) & 0xFF) * 255 // 0x80)))
