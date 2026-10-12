"""Read-only RSC5 / Xbox 360 LZX decompression for Midnight Club: Los Angeles resources.

Independently written in stock Python. The LZX bitstream follows Microsoft's LZX format as used in
cabinet files (16-bit little-endian words read most significant bit first; 3-bit block type and 24-bit
block size; verbatim, aligned-offset and uncompressed blocks; a 20-symbol pretree delta-coding the main,
length and aligned trees; three repeated-offset registers). The console framing is a reading taken from
Raskulk/MCLA-Tools `xrsc2obj.py` (68419cee) and checked here on every resource of the disc:

- RSC5 header, big-endian: magic `\\x05CSR`, resource type, flag word, a constant word, the byte length
  of the compressed body that follows the 20-byte header.
- The body is a run of chunks. `0xFF b1 b2 b3 b4` gives a chunk's output and input sizes; otherwise
  `b0 b1` gives the input size of a 0x8000-byte output chunk. Each chunk starts the bit reader afresh,
  the decoder state (window, trees, offset registers, a block in progress) carries over.
- The window is 2**17 bytes. The output must equal the virtual plus physical size of the flag word.
"""
import struct

RSC5 = b'\x05CSR'
HEADER = 20
WINDOW_BITS = 17
FRAME = 0x8000
MIN_MATCH = 2
NUM_CHARS = 256
PRETREE = 20
LENGTH_SYMBOLS = 249
ALIGNED = 8
VERBATIM, ALIGNED_BLOCK, UNCOMPRESSED = 1, 2, 3
TABLE_BITS = 16

EXTRA_BITS, POSITION_BASE = [], []
_base = 0
for _slot in range(51):
    _extra = min(17, max(0, _slot // 2 - 1))
    EXTRA_BITS.append(_extra)
    POSITION_BASE.append(_base)
    _base += 1 << _extra
del _base, _slot, _extra
POSITION_SLOTS = {15: 30, 16: 32, 17: 34, 18: 36, 19: 38, 20: 42, 21: 50}


class LzxError(ValueError):
    pass


def virtual_size(flag):
    return (flag & 0x7FF) << (((flag >> 11) & 15) + 8)


def physical_size(flag):
    return ((flag >> 15) & 0x7FF) << (((flag >> 26) & 15) + 8)


def decode_table(lengths, name):
    """Canonical Huffman decode table indexed by the next 16 bits: entry = symbol << 5 | length.
    An all-zero tree yields None (allowed until a symbol is needed); any other tree must be complete."""
    if not any(lengths):
        return None
    if max(lengths) > TABLE_BITS:
        raise LzxError(name + ' tree code longer than 16 bits')
    table = [0] * (1 << TABLE_BITS)
    code = 0
    for length in range(1, TABLE_BITS + 1):
        span = 1 << (TABLE_BITS - length)
        for symbol, size in enumerate(lengths):
            if size == length:
                start = code * span
                if start + span > len(table):
                    raise LzxError(name + ' tree over-subscribed')
                table[start:start + span] = [symbol << 5 | length] * span
                code += 1
        code <<= 1
    if code != 1 << (TABLE_BITS + 1):
        raise LzxError(name + ' tree incomplete')
    return table


class Bits:
    """MSB-first reader over 16-bit little-endian words of one chunk."""

    def __init__(self, data, start, end):
        swapped = bytearray(data[start:end])
        if len(swapped) & 1:
            swapped.append(0)
        swapped[0::2], swapped[1::2] = swapped[1::2], swapped[0::2]
        self.buf = bytes(swapped) + bytes(8)
        self.limit = (end - start) * 8
        self.base = start
        self.pos = 0

    def peek16(self):
        pos = self.pos
        b = pos >> 3
        return ((self.buf[b] << 16 | self.buf[b + 1] << 8 | self.buf[b + 2]) >> (8 - (pos & 7))) & 0xFFFF

    def read(self, count):
        if count == 0:
            return 0
        pos = self.pos
        b = pos >> 3
        value = int.from_bytes(self.buf[b:b + 4], 'big')
        self.pos = pos + count
        if self.pos > self.limit:
            raise LzxError('LZX chunk truncated')
        return (value >> (32 - (pos & 7) - count)) & ((1 << count) - 1)

    def symbol(self, table, name):
        if table is None:
            raise LzxError(name + ' tree empty but used')
        entry = table[self.peek16()]
        self.pos += entry & 31
        if self.pos > self.limit:
            raise LzxError('LZX chunk truncated')
        return entry >> 5


class LzxDecoder:
    """One LZX stream; `chunk` decodes one console chunk and returns its output bytes."""

    def __init__(self, window_bits=WINDOW_BITS):
        if window_bits not in POSITION_SLOTS:
            raise LzxError('unsupported LZX window')
        self.window = 1 << window_bits
        self.main_elements = NUM_CHARS + POSITION_SLOTS[window_bits] * 8
        self.main_lengths = [0] * self.main_elements
        self.length_lengths = [0] * LENGTH_SYMBOLS
        self.main = self.length = self.aligned = None
        self.r0 = self.r1 = self.r2 = 1
        self.block_type = None
        self.block_remaining = 0
        self.block_odd = False
        self.header_read = False
        self.out = bytearray()

    def read_lengths(self, bits, lengths, first, last):
        pre = decode_table([bits.read(4) for _ in range(PRETREE)], 'pretree')
        x = first
        while x < last:
            z = bits.symbol(pre, 'pretree')
            if z == 17:
                run, value = bits.read(4) + 4, 0
            elif z == 18:
                run, value = bits.read(5) + 20, 0
            elif z == 19:
                run = bits.read(1) + 4
                value = (lengths[x] - bits.symbol(pre, 'pretree') + 17) % 17
            else:
                run, value = 1, (lengths[x] - z + 17) % 17
            if x + run > last:
                raise LzxError('LZX length run past its tree')
            lengths[x:x + run] = [value] * run
            x += run

    def block_header(self, bits):
        self.block_type = bits.read(3)
        size = bits.read(16) << 8 | bits.read(8)
        if size == 0:
            raise LzxError('LZX empty block')
        self.block_remaining = size
        if self.block_type == ALIGNED_BLOCK:
            self.aligned = decode_table([bits.read(3) for _ in range(ALIGNED)], 'aligned')
        if self.block_type in (VERBATIM, ALIGNED_BLOCK):
            self.read_lengths(bits, self.main_lengths, 0, NUM_CHARS)
            self.read_lengths(bits, self.main_lengths, NUM_CHARS, self.main_elements)
            self.main = decode_table(self.main_lengths, 'main')
            self.read_lengths(bits, self.length_lengths, 0, LENGTH_SYMBOLS)
            self.length = decode_table(self.length_lengths, 'length')
            return None
        if self.block_type != UNCOMPRESSED:
            raise LzxError('LZX block type %d' % self.block_type)
        self.block_odd = bool(size & 1)
        # Align to the next 16-bit word (a whole word is skipped when already aligned), then R0-R2.
        at = (bits.pos // 16 + 1) * 2
        return at

    def chunk(self, data, start, end, size):
        """Decode `size` output bytes from data[start:end]; returns them."""
        out = self.out
        target = len(out) + size
        bits = Bits(data, start, end)
        raw = None  # byte offset into data while inside an uncompressed block
        if not self.header_read:
            if bits.read(1):
                raise LzxError('LZX Intel E8 translation not supported')
            self.header_read = True
        if self.block_type == UNCOMPRESSED and self.block_remaining:
            raw = start
        while len(out) < target:
            if self.block_remaining == 0:
                if raw is not None:
                    if self.block_odd:
                        raw += 1
                    bits = Bits(data, raw, end)
                    raw = None
                at = self.block_header(bits)
                if at is not None:
                    raw = bits.base + at
                    if raw + 12 > end:
                        raise LzxError('LZX chunk truncated')
                    self.r0, self.r1, self.r2 = struct.unpack_from('<III', data, raw)
                    raw += 12
            room = target - len(out)
            if raw is not None:
                run = min(self.block_remaining, room)
                if raw + run > end:
                    raise LzxError('LZX chunk truncated')
                out += data[raw:raw + run]
                raw += run
                self.block_remaining -= run
                continue
            try:
                produced = self.decode_compressed(bits, min(self.block_remaining, room))
            except IndexError:
                raise LzxError('LZX chunk truncated') from None
            self.block_remaining -= produced
        if len(out) != target:
            raise LzxError('LZX match ran past its chunk')
        if raw is not None:
            # An odd stored block is padded to a word, except where the padding would be the chunk's last byte.
            if self.block_remaining == 0 and self.block_odd and raw < end:
                raw += 1
            used = raw - start
            expected = end - start
        else:
            used, expected = bits.base - start + (bits.pos + 15) // 16 * 2, end - start
        if used != expected:
            raise LzxError('LZX chunk size mismatch: used %d of %d bytes' % (used, end - start))
        return out[target - size:target]

    def decode_compressed(self, bits, want):
        """Decode symbols until at least `want` bytes are produced; returns the count produced."""
        out = self.out
        begin = len(out)
        stop = begin + want
        main, length, aligned = self.main, self.length, self.aligned
        is_aligned = self.block_type == ALIGNED_BLOCK
        r0, r1, r2 = self.r0, self.r1, self.r2
        if main is None:
            raise LzxError('main tree empty but used')
        buf, limit = bits.buf, bits.limit
        pos = bits.pos
        while len(out) < stop:
            b = pos >> 3
            entry = main[((buf[b] << 16 | buf[b + 1] << 8 | buf[b + 2]) >> (8 - (pos & 7))) & 0xFFFF]
            pos += entry & 31
            symbol = entry >> 5
            if symbol < NUM_CHARS:
                out.append(symbol)
                continue
            symbol -= NUM_CHARS
            match = symbol & 7
            slot = symbol >> 3
            bits.pos = pos
            if match == 7:
                match += bits.symbol(length, 'length')
            match += MIN_MATCH
            if slot == 0:
                offset = r0
            elif slot == 1:
                offset = r1
                r1 = r0
                r0 = offset
            elif slot == 2:
                offset = r2
                r2 = r0
                r0 = offset
            else:
                extra = EXTRA_BITS[slot]
                offset = POSITION_BASE[slot] - 2
                if is_aligned and extra >= 3:
                    offset += (bits.read(extra - 3) << 3) + bits.symbol(aligned, 'aligned')
                else:
                    offset += bits.read(extra)
                r2, r1, r0 = r1, r0, offset
            pos = bits.pos
            if pos > limit:
                raise LzxError('LZX chunk truncated')
            start = len(out) - offset
            if offset > self.window or start < 0:
                raise LzxError('LZX match before start of output')
            if offset >= match:
                out += out[start:start + match]
            else:
                pattern = out[start:]
                out += (pattern * (match // offset + 1))[:match]
        if pos > limit:
            raise LzxError('LZX chunk truncated')
        bits.pos = pos
        self.r0, self.r1, self.r2 = r0, r1, r2
        return len(out) - begin


def parse_header(data):
    if len(data) < HEADER or data[:4] != RSC5:
        raise LzxError('not an RSC5 resource')
    _magic, kind, flag, constant, length = struct.unpack_from('>4sIIII', data, 0)
    return {'type': kind, 'flag': flag, 'constant': constant, 'body_bytes': length,
            'virtual': virtual_size(flag), 'physical': physical_size(flag)}


def decompress(data, window_bits=WINDOW_BITS, expected=None):
    """RSC5 resource bytes -> decompressed bytes (virtual segment then physical segment)."""
    header = parse_header(data)
    if HEADER + header['body_bytes'] != len(data):
        raise LzxError('RSC5 body length differs from stored size')
    if expected is None:
        expected = header['virtual'] + header['physical']
    decoder = LzxDecoder(window_bits)
    at, end = HEADER, len(data)
    header['chunks'] = 0
    while at < end:
        if data[at] == 0xFF:
            if at + 5 > end:
                raise LzxError('LZX chunk header truncated')
            size, length = struct.unpack_from('>HH', data, at + 1)
            at += 5
        else:
            if at + 2 > end:
                raise LzxError('LZX chunk header truncated')
            size, length = FRAME, struct.unpack_from('>H', data, at)[0]
            at += 2
        if length == 0 or at + length > end:
            raise LzxError('LZX chunk outside resource')
        if len(decoder.out) + size > expected:
            raise LzxError('LZX output exceeds declared size')
        decoder.chunk(data, at, at + length, size)
        header['chunks'] += 1
        at += length
    if len(decoder.out) != expected:
        raise LzxError('LZX output %d bytes, declared %d' % (len(decoder.out), expected))
    return bytes(decoder.out), header
