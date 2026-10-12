"""RSC5 pointer, bounds and string-field controls on synthetic resources (plus the builder other tests use)."""
import struct
import unittest

from mcla_resource import Resource, ResourceError, string_records


class Builder:
    """Lays out big-endian structures in a virtual segment; `pointer(at)` is the 0x5XXXXXXX form."""

    def __init__(self):
        self.data = bytearray()

    def alloc(self, size, align=16, fill=0):
        self.data += bytes((-len(self.data)) % align)
        at = len(self.data)
        self.data += bytes([fill]) * size
        return at

    @staticmethod
    def pointer(at):
        return 0 if at is None else 0x50000000 | at

    def put(self, at, fmt, *values):
        struct.pack_into('>' + fmt, self.data, at, *values)

    def text(self, value):
        at = self.alloc(len(value) + 1, 4)
        self.data[at:at + len(value)] = value.encode()
        return at

    def segment(self, physical=b''):
        """(bytes, virtual size, physical size) with the virtual segment padded to 256 bytes."""
        self.data += bytes([0xCD]) * ((-len(self.data)) % 256)
        return bytes(self.data) + physical, len(self.data), len(physical)


class ResourceTests(unittest.TestCase):
    def test_pointers_segments_and_reads(self):
        b = Builder()
        at = b.alloc(16)
        b.put(at, 'IHHf', 0x60000004, 7, 9, 1.5)
        data, virtual, physical = b.segment(b'\0\0\0\0WXYZ')
        r = Resource(data, virtual, physical)
        self.assertEqual(r.offset(0x50000004), 4)
        self.assertEqual(r.offset(0x60000004, 4), virtual + 4)
        self.assertEqual(r.pointer(at, 4), virtual + 4)
        self.assertEqual((r.u16(4), r.u16(6), r.f32(8), r.u8(virtual + 4)), (7, 9, 1.5, ord('W')))
        self.assertIsNone(r.pointer(12))  # a zero word is null
        with self.assertRaisesRegex(ResourceError, 'not a resource pointer'):
            r.offset(0x70000000)
        with self.assertRaisesRegex(ResourceError, 'outside its segment'):
            r.offset(0x60000006, 4)
        with self.assertRaisesRegex(ResourceError, 'outside its segment'):
            r.offset(0x50000000 | virtual, 1)
        with self.assertRaisesRegex(ResourceError, 'read outside'):
            r.u32(len(data) - 2)
        with self.assertRaisesRegex(ResourceError, 'size differs'):
            Resource(data + b'\0', virtual, physical)

    def test_strings_and_string_fields(self):
        b = Builder()
        field = b.alloc(16)
        name = b.text('hood0_lod_0')
        bad = b.text('two\x01')
        b.put(field, 'IHH', b.pointer(name), 11, 16)
        b.put(field + 8, 'IHH', 0, 0, 0)
        data, virtual, physical = b.segment()
        r = Resource(data, virtual, physical)
        self.assertEqual(r.string_at(field), 'hood0_lod_0')
        self.assertIsNone(r.string_at(field + 8))
        self.assertEqual(r.cstring(name), 'hood0_lod_0')
        with self.assertRaisesRegex(ResourceError, 'without its terminator'):
            r.cstring(name, 4)
        with self.assertRaisesRegex(ResourceError, 'not printable'):
            r.cstring(bad)
        b.put(field, 'IHH', b.pointer(name), 16, 16)
        r = Resource(*b.segment())
        with self.assertRaisesRegex(ResourceError, 'not below its capacity'):
            r.string_at(field)
        end = Resource(b'abc', 3, 0)
        with self.assertRaisesRegex(ResourceError, 'without its terminator'):
            end.cstring(0)

    def test_string_records_need_exact_length_capacity_and_printable_text(self):
        b = Builder()
        table = b.alloc(48)
        good, other, bad = b.text('door_l_stk'), b.text('seat00'), b.text('x\x02yz')
        b.put(table, 'IHH', b.pointer(good), 10, 16)        # a record
        b.put(table + 8, 'IHH', b.pointer(other), 4, 16)    # wrong length: no NUL after four characters
        b.put(table + 16, 'IHH', b.pointer(bad), 4, 16)     # not printable
        b.put(table + 24, 'IHH', b.pointer(other), 6, 6)    # length not below capacity
        b.put(table + 32, 'IHH', 0x60000000, 6, 16)         # physical pointer
        b.put(table + 40, 'IHH', b.pointer(other), 6, 8)    # a record
        data, virtual, _ = b.segment()
        self.assertEqual(string_records(data, virtual), ['door_l_stk', 'seat00'])
        b.put(table + 40, 'IHH', b.pointer(virtual - 2), 6, 8)  # runs past the segment
        data, virtual, _ = b.segment()
        self.assertEqual(string_records(data, virtual), ['door_l_stk'])


if __name__ == '__main__':
    unittest.main(verbosity=2)
