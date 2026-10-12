"""Read-only access to decompressed Midnight Club: Los Angeles RSC5 resources (Xbox 360, big-endian).

A decompressed resource is its virtual segment followed by its physical segment. Pointers inside it
are 32-bit words: 0x5XXXXXXX addresses the virtual segment, 0x6XXXXXXX the physical segment, 0 is null
(reading taken from CodeX.Games.MCLA `RSC5/Rsc5Data.cs` at dedc3156; no code copied). Every read is
bounds-checked against the segment it addresses.
"""
import re
import struct

VIRTUAL, PHYSICAL = 0x5, 0x6
PRINTABLE = re.compile(rb'[\x20-\x7e]+')


class ResourceError(ValueError):
    pass


class Resource:
    def __init__(self, data, virtual, physical):
        if len(data) != virtual + physical:
            raise ResourceError('resource size differs from its segments')
        self.data, self.virtual, self.physical = data, virtual, physical

    def offset(self, pointer, size=0):
        """File offset of a non-null pointer whose `size` bytes lie inside its segment."""
        segment, at = pointer >> 28, pointer & 0x0FFFFFFF
        if segment == VIRTUAL:
            limit, base = self.virtual, 0
        elif segment == PHYSICAL:
            limit, base = self.physical, self.virtual
        else:
            raise ResourceError('not a resource pointer: 0x%08x' % pointer)
        if at + size > limit:
            raise ResourceError('pointer 0x%08x outside its segment' % pointer)
        return base + at

    def need(self, at, size):
        if at < 0 or at + size > len(self.data):
            raise ResourceError('read outside resource')

    def unpack(self, fmt, at):
        self.need(at, struct.calcsize(fmt))
        return struct.unpack_from('>' + fmt, self.data, at)

    def u8(self, at):
        return self.unpack('B', at)[0]

    def u16(self, at):
        return self.unpack('H', at)[0]

    def u32(self, at):
        return self.unpack('I', at)[0]

    def f32(self, at):
        return self.unpack('f', at)[0]

    def pointer(self, at, size=0):
        """Follow the pointer stored at `at`; None when it is null."""
        value = self.u32(at)
        return None if value == 0 else self.offset(value, size)

    def cstring(self, at, length=None):
        """A NUL-terminated printable string at file offset `at` (exactly `length` characters when given)."""
        end = self.data.find(b'\0', at, len(self.data))
        if end < 0 or (length is not None and end - at != length):
            raise ResourceError('string without its terminator')
        text = self.data[at:end]
        if text and not PRINTABLE.fullmatch(text):
            raise ResourceError('string is not printable ASCII')
        return text.decode('ascii')

    def string_at(self, at):
        """A string field: pointer, 16-bit length, 16-bit capacity (None when the pointer is null)."""
        pointer, length, capacity = self.unpack('IHH', at)
        if pointer == 0:
            return None
        if length >= capacity:
            raise ResourceError('string length not below its capacity')
        return self.cstring(self.offset(pointer, length + 1), length)


def string_records(data, virtual):
    """Every string a well-formed string field of the virtual segment references.

    A record is a 4-byte-aligned (pointer, length, capacity) triple whose pointer addresses the virtual
    segment, whose length is non-zero and below the capacity, and whose target is exactly `length`
    printable characters followed by a NUL."""
    found = []
    for at in range(0, virtual - 7, 4):
        pointer, length, capacity = struct.unpack_from('>IHH', data, at)
        if pointer >> 28 != VIRTUAL or not 0 < length < capacity:
            continue
        start = pointer & 0x0FFFFFFF
        end = start + length
        if end >= virtual or data[end] != 0 or not PRINTABLE.fullmatch(data[start:end]):
            continue
        found.append(data[start:end].decode('ascii'))
    return found
