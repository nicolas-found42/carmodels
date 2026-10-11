"""Pinned native GT1 wheel tables and neutral CAR-header wheel assembly.

The game stores wheel templates in packed GTMAIN, separate from GT-CAR bodies.
The retained table bytes are runtime inputs, hash-checked without private discs.
--check additionally rederives them from the caller's pinned original executable.
No game execution, dynamic steering/roll or original lighting is reproduced.
"""
import argparse
import base64
import hashlib
import json
from pathlib import Path
import struct

ROOT = Path(__file__).resolve().parents[1]
TABLE_RECEIPT = ROOT / 'research/evidence/gran-turismo-wheels/native-wheel-tables.json'
SOURCE_SHA256 = '3fd17ae24e23b9c939d15951d6dafe254fa6611488327c128dfe4637f83d36f8'
UNPACKED_SHA256 = '0d7e00755c0d9234113607daf39ced3728ffe42d4e1984e32eb664f4542f48fd'
LOAD = 0x80010000
POINTER_ADDRESS = 0x800974b4
POINTER_SHA256 = '657aab6ad9e81594ab8a43aeef925792fa847a5a5fb46cd365838ef463107955'
PINS = (
    (0x800970d0, 31, '564e3b6f90eef359aae9a786305e0637bd64af86a73bce119009952892ba9bc4'),
    (0x80096dec, 23, '1d950790503ee817711be9a787dd982e81e3c2fadade95561c1a4a58409e8863'),
    (0x80096c08, 15, 'bf2132bfcb830058c7111ec17bdd226a4ea0b81c564efc3c4111b82798517006'),
    (0x80096aa4, 11, '15aed478a9f9042a899678ecf5544ebe33bb245c5baff739a5e646babef1800d'),
    (0x80096a80, 1, '262c063775e827c79ada3e13f9350f94cfa137800bc32729160094e90d1d3cb8'),
)


def sha(data):
    return hashlib.sha256(data).hexdigest()


def decode_pslz(data, expected_sha=SOURCE_SHA256):
    """Bounded backward PSLZ loader translation; static bytes, no emulation.

    A caller-supplied alternate digest permits independently constructed tests;
    production extraction always uses the native SOURCE_SHA256 default.
    """
    if sha(data) != expected_sha:
        raise ValueError('PSLZ source pin differs')
    if len(data) < 2048 or data[:8] != b'PS-X EXE':
        raise ValueError('Invalid PS-X executable header')
    pc, load, packed_size = (struct.unpack_from('<I', data, o)[0] for o in (16, 24, 28))
    header = pc - load + 2048 - 28
    if len(data) != packed_size + 2048 or not 2048 <= header <= len(data) - 28:
        raise ValueError('PSLZ packed extent or loader header outside source')
    magic, end, size, source, stub, stub_size, original_load = struct.unpack_from('<7I', data, header)
    if (magic != 0x5a4c5350 or original_load != load or not 0 < size <= 16 * 1024 * 1024
            or end + 1 != load + size or stub != end + 1 or not 28 <= stub_size <= 4096
            or header + stub_size > len(data) or source != load + header - 2050):
        raise ValueError('PSLZ loader fields outside bounded profile')
    memory = bytearray(max(size, packed_size))
    memory[:packed_size] = data[2048:]
    ip, op = source - load, end - load

    def read():
        nonlocal ip
        if not 0 <= ip < packed_size:
            raise ValueError('PSLZ compressed read outside source')
        value = memory[ip]
        ip -= 1
        return value

    while ip < op:
        flags = read()
        for bit in range(8):
            if ip >= op:
                break
            value = read()
            if flags & (1 << bit):
                length, distance = value + 3, read()
                if distance & 128:
                    distance = ((distance & 127) << 8) | read()
                distance += 1
                if op - length + 1 < 0 or op + distance >= size:
                    raise ValueError('PSLZ match outside decoded extent')
                for _ in range(length):
                    memory[op] = memory[op + distance]
                    op -= 1
            else:
                if not 0 <= op < size:
                    raise ValueError('PSLZ literal outside decoded extent')
                memory[op] = value
                op -= 1
    if ip != -1 or op != -1:
        raise ValueError('PSLZ input/output did not converge at load boundary')
    return bytes(memory[:size])


def _table(raw, address, count, digest):
    if len(raw) != 4 + count * 32 or sha(raw) != digest:
        raise ValueError('Native wheel table byte pin differs')
    if struct.unpack_from('<I', raw)[0] != count:
        raise ValueError('Native wheel quad count differs')
    vertices = tuple(struct.unpack_from('<3hH', raw, o) for o in range(4, len(raw), 8))
    return {'virtual_address': address, 'quad_count': count, 'sha256': digest,
            'vertices': vertices, 'raw': raw}


def load_tables(path=TABLE_RECEIPT):
    """Read immutable native source vertices; each payload and pointer is pinned."""
    doc = json.loads(Path(path).read_text())
    if (doc.get('schema') != 1 or doc.get('source_executable_sha256') != SOURCE_SHA256
            or doc.get('unpacked_sha256') != UNPACKED_SHA256 or doc.get('load_address') != LOAD
            or doc.get('pointer_array_address') != POINTER_ADDRESS
            or doc.get('pointer_array_sha256') != POINTER_SHA256):
        raise ValueError('Native wheel receipt provenance differs')
    try:
        pointers = base64.b64decode(doc['pointer_array_base64'], validate=True)
        rows = doc['tables']
        if len(rows) != len(PINS) or len(pointers) != 20 or sha(pointers) != POINTER_SHA256:
            raise ValueError('Native wheel pointer array or coverage differs')
        tables = []
        for lod, (row, (address, count, digest)) in enumerate(zip(rows, PINS)):
            if (row['lod'], row['virtual_address'], row['quad_count'], row['sha256']) != (lod, address, count, digest):
                raise ValueError('Native wheel table declarations differ')
            if struct.unpack_from('<I', pointers, lod * 4)[0] != address:
                raise ValueError('Native wheel pointer declaration differs')
            tables.append(_table(base64.b64decode(row['base64'], validate=True), address, count, digest))
        return tuple(tables)
    except (KeyError, TypeError, struct.error) as error:
        raise ValueError('Malformed native wheel receipt') from error


def check_source(source, tables=None):
    """Recompute retained bytes from a pinned private original GTMAIN executable."""
    tables = load_tables() if tables is None else tables
    unpacked = decode_pslz(Path(source).read_bytes())
    if sha(unpacked) != UNPACKED_SHA256:
        raise ValueError('Unpacked GTMAIN pin differs')
    pointers = unpacked[POINTER_ADDRESS - LOAD:POINTER_ADDRESS - LOAD + 20]
    if sha(pointers) != POINTER_SHA256:
        raise ValueError('Native wheel pointer source pin differs')
    for table in tables:
        offset = table['virtual_address'] - LOAD
        if unpacked[offset:offset + len(table['raw'])] != table['raw']:
            raise ValueError('Native wheel retained bytes differ from executable')
    return {'source_sha256': SOURCE_SHA256, 'unpacked_sha256': UNPACKED_SHA256,
            'tables': len(tables), 'quads': [t['quad_count'] for t in tables],
            'claim_limits': ['Static byte derivation; game not executed.']}


def assemble_wheels(car, lod=0, tables=None):
    """Neutral native-coordinate quads in raw CAR units, before viewer /4096,-Z.

    Native matrix aspect uses floor(width*4096/radius). The exporter preserves
    that ratio but emits floats instead of reproducing camera-dependent GTE
    projection, saturation or matrix multiplication quantization.
    """
    tables = load_tables() if tables is None else tables
    if type(lod) is not int or not 0 <= lod < len(tables):
        raise ValueError('Native wheel LOD outside profile')
    centres, dimensions = car.get('wheels'), car.get('wheel_dimensions')
    if not isinstance(centres, (list, tuple)) or len(centres) != 4 or not isinstance(dimensions, (list, tuple)) or len(dimensions) != 4:
        raise ValueError('Native wheel CAR header shape differs')
    if any(type(v) is not int or not 0 <= v <= 32767 for v in dimensions):
        raise ValueError('Native wheel dimension outside signed draw profile')
    if any(not isinstance(c, (list, tuple)) or len(c) != 4 or any(type(v) is not int or not -32768 <= v <= 32767 for v in c) for c in centres):
        raise ValueError('Native wheel centre outside signed header')
    table = tables[lod]
    groups = []
    for wheel, centre in enumerate(centres):
        width, radius = dimensions[0:2] if wheel < 2 else dimensions[2:4]
        if not width or not radius:
            continue
        direction = 1 if wheel % 2 == 0 else -1
        aspect = (width * 4096) // radius
        if aspect > 32767:
            raise ValueError('Native wheel aspect outside signed matrix profile')
        shift = (direction * width) // 2
        positions, uv = [], []
        for x, y, z, packed in table['vertices']:
            axial = (z * aspect) >> 12
            positions.append((centre[0] + shift + direction * axial * radius / 4096,
                              centre[1] + y * radius / 4096,
                              centre[2] - direction * x * radius / 4096))
            uv.append((packed & 255, packed >> 8))
        groups.append({'wheel_index': wheel, 'positions': positions, 'uv': uv,
                       'quads': [(i, i + 1, i + 2, i + 3) for i in range(0, len(positions), 4)],
                       'table_lod': lod, 'width': width, 'radius': radius,
                       'aspect_fixed': aspect, 'table_sha256': table['sha256']})
    return groups


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--check', type=Path, metavar='GTMAIN.EXE', help='Pinned private original executable')
    args = parser.parse_args()
    tables = load_tables()
    result = check_source(args.check, tables) if args.check else {'tables': len(tables), 'quads': [t['quad_count'] for t in tables]}
    print(json.dumps(result, sort_keys=True))


if __name__ == '__main__':
    main()
