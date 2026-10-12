"""Read-only Gran Turismo 4 SpecDB (GTDB/GTID/GTST) decoding for car names and dimensions.

Layouts follow the GT Modding Hub DBT/IDI/SDB pages and Nenkai's MIT-licensed PDTools.SpecDB
(Huffman row extraction, GT4 column maps); see research/gran-turismo-4-previews.md.
Joins are by table id, never by column position across games.
"""
from pathlib import Path
import struct

MAX_ROWS = 100000


class Table:
    def __init__(self, folder, name):
        self.name = name
        self.data = Path(folder, name + '.dbt').read_bytes()
        idi = Path(folder, name + '.idi').read_bytes()
        if self.data[:4] != b'GTDB' or idi[:4] != b'GTID' or len(self.data) < 16 or len(idi) < 16:
            raise ValueError('invalid SpecDB table: ' + name)
        self.attribute, _, self.count, self.row_size = struct.unpack_from('<HHIi', self.data, 4)
        labels = struct.unpack_from('<i', idi, 4)[0]
        self.table_id = struct.unpack_from('<i', idi, 12)[0]
        if not (0 <= self.count <= MAX_ROWS and 0 < self.row_size <= 4096 and 0 <= labels <= MAX_ROWS
                and 16 + 8 * self.count <= len(self.data) and 16 + 8 * labels <= len(idi)):
            raise ValueError('SpecDB table counts out of range: ' + name)
        self.labels = {}
        for i in range(labels):
            offset, row_id = struct.unpack_from('<ii', idi, 16 + 8 * i)
            start = 16 + 8 * labels + offset + 2
            end = idi.find(b'\0', start)
            if not 0 <= offset or end < 0:
                raise ValueError('SpecDB label outside table: ' + name)
            self.labels[row_id] = idi[start:end].decode('latin-1')
        self.rows_at = [struct.unpack_from('<ii', self.data, 16 + 8 * i) for i in range(self.count)]
        position = 16 + 8 * self.count
        self.codebook = position
        if self.attribute & 1:
            self.lookup = position + 8
            self.codes = position + 0x208
            position += self._i32(position)
            self.templates = position + 8
            self.data_at = position + self._i32(position)
        else:
            self.data_at = position

    def _i32(self, offset):
        if not 0 <= offset <= len(self.data) - 4:
            raise ValueError('SpecDB read outside table: ' + self.name)
        return struct.unpack_from('<i', self.data, offset)[0]

    def _symbol(self, bits):
        data = self.data
        entry = self.lookup + (bits & 0xFF) * 2
        if data[entry + 1]:
            return data[entry], data[entry + 1]
        count = self._i32(self.codebook + 4)
        for size in range(9, 32):
            target = bits & ((1 << size) - 1)
            low, high = -1, count
            while low + 1 != high:
                mid = (low + high) // 2
                at = self.codes + mid * 8
                code_size, code = data[at], self._i32(at + 4)
                if code == target and code_size == size:
                    return data[at + 1], size
                if size > code_size or (size == code_size and target > code):
                    low = mid
                else:
                    high = mid
        raise ValueError('SpecDB Huffman code not found: ' + self.name)

    def row(self, index):
        row_id, offset = self.rows_at[index]
        start, data, size = self.data_at + offset, self.data, self.row_size
        if not self.attribute & 1:
            if start + size > len(data):
                raise ValueError('SpecDB row outside table: ' + self.name)
            return row_id, data[start:start + size]
        parts, symbols, bit = data[start], bytearray(), 0
        for _ in range(parts):
            byte = bit // 8
            chunk = data[start + 1 + byte:start + 5 + byte].ljust(4, b'\0')
            value, used = self._symbol(struct.unpack('<I', chunk)[0] >> (bit - byte * 8))
            symbols.append(value)
            bit += used
        if not symbols:
            raise ValueError('empty SpecDB row: ' + self.name)
        kind, template, raw = symbols[0] >> 6, symbols[0] & 63, symbols[1:]
        base = self.templates + template * size
        if kind == 0:
            return row_id, data[base:base + size]
        if kind == 1:
            if len(raw) < size:
                raise ValueError('short SpecDB row: ' + self.name)
            return row_id, bytes(raw[:size])
        if kind == 2:
            row = bytearray(data[base:base + size])
            patch = 1 + size // 8 + (1 if size % 8 else 0)
            for i in range(size):
                if raw[i // 8] >> (i % 8) & 1 and patch < len(symbols):
                    row[i] = symbols[patch]
                    patch += 1
            return row_id, bytes(row)
        raise ValueError('unsupported SpecDB row type: ' + self.name)

    def by_id(self):
        return dict(self.row(i) for i in range(self.count))

    def by_label(self):
        return {self.labels[row_id]: data for row_id, data in (self.row(i) for i in range(self.count))}


def strings(path):
    data = Path(path).read_bytes()
    if data[:4] != b'GTST':
        raise ValueError('invalid SpecDB string table')
    count = struct.unpack_from('<i', data, 4)[0]
    out = []
    for i in range(count):
        offset = struct.unpack_from('<i', data, 16 + 4 * i)[0]
        start = 16 + 4 * count + offset + 2
        end = data.find(b'\0', start)
        if end < 0:
            raise ValueError('SpecDB string outside table')
        out.append(data[start:end].decode('utf-8', 'replace'))
    return out


def car_specs(folder, locale='british'):
    """Model code -> retail name, chassis dimensions and default tire sizes."""
    text = strings(Path(folder, locale + '_StrDB.sdb'))
    cars = Table(folder, 'GENERIC_CAR').by_label()
    names = Table(folder, 'CAR_NAME_' + locale).by_label()
    variations = Table(folder, 'CAR_VARIATION_' + locale).by_label()
    variation_rows = Table(folder, 'VARIATION' + locale).by_id()
    parts = Table(folder, 'DEFAULT_PARTS').by_id()
    tables = {name: Table(folder, name) for name in ('CHASSIS', 'FRONTTIRE', 'REARTIRE', 'TIRESIZE', 'SUSPENSION')}
    rows = {name: table.by_id() for name, table in tables.items()}
    out = {}
    for label, row in sorted(cars.items()):
        parts_id = struct.unpack_from('<i', row, 0)[0]
        variation_id = struct.unpack_from('<i', variations[label], 0)[0]
        variation = variation_rows[variation_id]
        model = text[struct.unpack_from('<i', variation, 0)[0]]
        keys = {}
        part_row = parts[parts_id]
        for i in range(len(part_row) // 8):
            key, table_id = struct.unpack_from('<ii', part_row, 8 * i)
            keys[table_id] = key
        chassis = struct.unpack_from('<13h', rows['CHASSIS'][keys[tables['CHASSIS'].table_id]])
        # SUSPENSION shorts: ride height min/max/default front, then rear (mm).
        suspension = struct.unpack_from('<6h', rows['SUSPENSION'][keys[tables['SUSPENSION'].table_id]])

        def tire(table):
            size = rows['TIRESIZE'][struct.unpack_from('<i', rows[table][keys[tables[table].table_id]])[0]]
            # TIRESIZE bytes: aspect/5, category, rim inches x10, width/5 mm (e.g. 215/50R17 = 10, 0, 170, 43).
            # Reading: rim bytes under 90 are whole inches. Only the two 1886 cars use them (26/41, 34/45);
            # every other rim is 9.0" or more, and x10 would give their wooden wheels 0.1 m diameters.
            rim = size[2] / 10 if size[2] >= 90 else size[2]
            return {'aspect': size[0] * 5, 'rim_inches': rim, 'width_mm': size[3] * 5}
        name = text[struct.unpack_from('<i', names[label], 0)[0]] if label in names else None
        if model in out:
            raise ValueError('model code used by two spec cars: ' + model)
        out[model] = {'label': label, 'name': name, 'year': struct.unpack_from('<h', row, 12)[0],
                      'wheelbase_mm': chassis[2], 'length_mm': chassis[0], 'height_mm': chassis[1],
                      'mass_kg': chassis[3], 'tread_mm': [chassis[9], chassis[10]],
                      'tire_pos_related_mm': [chassis[11], chassis[12]],  # Equal CarInfo TirePosRelated; not tire diameters.
                      'model_bounds_mm': [round(v, 1) for v in struct.unpack_from('<4f', variation, 16)],
                      'ride_height_mm': [suspension[2], suspension[5]],
                      'front_tire': tire('FRONTTIRE'), 'rear_tire': tire('REARTIRE')}
    return out
