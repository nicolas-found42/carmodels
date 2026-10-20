"""LZX / RSC5 decompression controls on streams built by a small test-only encoder."""

import math
import struct
import unittest

import mcla_lzx
from mcla_lzx import (
    ALIGNED_BLOCK,
    EXTRA_BITS,
    FRAME,
    LENGTH_SYMBOLS,
    NUM_CHARS,
    POSITION_BASE,
    RSC5,
    UNCOMPRESSED,
    VERBATIM,
    LzxDecoder,
    LzxError,
    decode_table,
    decompress,
    parse_header,
)

CONSTANT = 0x0FF512EF
MAIN_ELEMENTS = NUM_CHARS + 34 * 8
# A complete pretree: twelve 4-bit and eight 5-bit codes.
PRE_LENGTHS = [4] * 12 + [5] * 8


def codes(lengths):
    """Canonical codes in the decoder's order: by length, then symbol."""
    out, code = {}, 0
    for length in range(1, 17):
        for symbol, size in enumerate(lengths):
            if size == length:
                out[symbol] = (code, length)
                code += 1
        code <<= 1
    return out


def complete(used, total):
    """Code lengths giving the used symbols a complete prefix code."""
    used = sorted(set(used))
    if len(used) == 1:
        used.append(next(s for s in range(total) if s not in used))
    lengths = [0] * total
    k = math.ceil(math.log2(len(used)))
    short = (1 << k) - len(used)
    for i, symbol in enumerate(used):
        lengths[symbol] = k - 1 if i < short else k
    return lengths


class BitWriter:
    def __init__(self):
        self.data, self.acc, self.count = bytearray(), 0, 0

    def write(self, value, count):
        for i in range(count - 1, -1, -1):
            self.acc = self.acc << 1 | (value >> i) & 1
            self.count += 1
            if self.count == 16:
                self.data += struct.pack("<H", self.acc)
                self.acc = self.count = 0

    def code(self, table, symbol):
        code, length = table[symbol]
        self.write(code, length)

    def align(self):
        if self.count:
            self.write(0, 16 - self.count)


class Encoder:
    """Emits LZX blocks into console chunks; a chunk closes whenever the output reaches a frame boundary."""

    def __init__(self, intel=0):
        self.chunks, self.writer, self.produced, self.chunk_start = (
            [],
            BitWriter(),
            0,
            0,
        )
        self.main = [0] * MAIN_ELEMENTS
        self.length = [0] * LENGTH_SYMBOLS
        self.r = [1, 1, 1]
        self.output = bytearray()
        self.writer.write(intel, 1)

    def lengths(self, previous, new, first, last, runs=False):
        pre = codes(PRE_LENGTHS)
        for size in PRE_LENGTHS:
            self.writer.write(size, 4)
        x = first
        while x < last:
            same = 1
            while x + same < last and new[x + same] == new[x]:
                same += 1
            if runs and new[x] == 0 and same >= 20:
                run = min(same, 51)
                self.writer.code(pre, 18)
                self.writer.write(run - 20, 5)
            elif runs and new[x] == 0 and same >= 4:
                run = min(same, 19)
                self.writer.code(pre, 17)
                self.writer.write(run - 4, 4)
            elif runs and same >= 4:
                run = min(same, 5)
                self.writer.code(pre, 19)
                self.writer.write(run - 4, 1)
                self.writer.code(pre, (previous[x] - new[x]) % 17)
            else:
                run = 1
                self.writer.code(pre, (previous[x] - new[x]) % 17)
            previous[x : x + run] = [new[x]] * run
            x += run

    def block(self, tokens, aligned=False, runs=False, size=None):
        """tokens: int literals, ('m', length, offset) explicit matches, ('r', register, length) repeats."""
        r = list(self.r)
        plan = []
        for token in tokens:
            if isinstance(token, int):
                plan.append((token, None))
                continue
            if token[0] == "r":
                slot, length = token[1], token[2]
                if slot == 1:
                    r[0], r[1] = r[1], r[0]
                elif slot == 2:
                    r[0], r[2] = r[2], r[0]
                offset = r[0]
            else:
                length, offset = token[1], token[2]
                formatted = offset + 2
                slot = max(s for s in range(3, 34) if POSITION_BASE[s] <= formatted)
                r = [offset, r[0], r[1]]
            header = min(length - 2, 7)
            plan.append((NUM_CHARS + slot * 8 + header, (length, offset, slot)))
        main = complete([s for s, _ in plan], MAIN_ELEMENTS)
        length_used = [m[0] - 9 for _, m in plan if m and m[0] - 2 >= 7]
        lengths = (
            complete(length_used, LENGTH_SYMBOLS)
            if length_used
            else [0] * LENGTH_SYMBOLS
        )
        produced = sum(1 if m is None else m[0] for _, m in plan)
        w = self.writer
        w.write(ALIGNED_BLOCK if aligned else VERBATIM, 3)
        size = produced if size is None else size
        w.write(size >> 8, 16)
        w.write(size & 0xFF, 8)
        if aligned:
            for _ in range(8):
                w.write(3, 3)
        self.lengths(self.main, main, 0, NUM_CHARS, runs)
        self.lengths(self.main, main, NUM_CHARS, MAIN_ELEMENTS, runs)
        self.lengths(self.length, lengths, 0, LENGTH_SYMBOLS, runs)
        main_codes, length_codes, aligned_codes = (
            codes(main),
            codes(lengths),
            codes([3] * 8),
        )
        for symbol, match in plan:
            self.writer.code(main_codes, symbol)
            if match is None:
                self.output.append(symbol)
                self.advance(1)
                continue
            length, offset, slot = match
            if length - 2 >= 7:
                self.writer.code(length_codes, length - 9)
            if slot >= 3:
                extra, verbatim = EXTRA_BITS[slot], offset + 2 - POSITION_BASE[slot]
                if aligned and extra >= 3:
                    self.writer.write(verbatim >> 3, extra - 3)
                    self.writer.code(aligned_codes, verbatim & 7)
                else:
                    self.writer.write(verbatim, extra)
            start = len(self.output) - offset
            for i in range(length):
                self.output.append(self.output[start + i])
            self.advance(length)
        self.r = r

    def stored(self, data, registers=(1, 1, 1), pad=True):
        w = self.writer
        w.write(UNCOMPRESSED, 3)
        w.write(len(data) >> 8, 16)
        w.write(len(data) & 0xFF, 8)
        if w.count == 0:
            w.write(0, 16)
        w.align()
        w.data += struct.pack("<III", *registers)
        self.r = list(registers)
        for byte in data:
            self.writer.data.append(byte)
            self.output.append(byte)
            self.advance(1)
        if len(data) & 1 and pad and self.produced != self.chunk_start:
            self.writer.data.append(0)

    def advance(self, count):
        self.produced += count
        if self.produced - self.chunk_start > FRAME:
            raise AssertionError("test token crosses a frame")
        if self.produced - self.chunk_start == FRAME:
            self.close()

    def close(self):
        if self.produced == self.chunk_start:
            return
        self.writer.align()
        self.chunks.append((self.produced - self.chunk_start, bytes(self.writer.data)))
        self.writer, self.chunk_start = BitWriter(), self.produced

    def body(self):
        self.close()
        out = bytearray()
        for size, data in self.chunks:
            out += (
                struct.pack(">H", len(data))
                if size == FRAME
                else b"\xff" + struct.pack(">HH", size, len(data))
            )
            out += data
        return bytes(out)


def flag_for(virtual):
    return 0xC0000000 | (virtual + 255) >> 8


def resource(body, size, kind=63, flag=None):
    flag = flag_for(size) if flag is None else flag
    return RSC5 + struct.pack(">IIII", kind, flag, CONSTANT, len(body)) + body


def pattern(n, seed=7):
    out, x = bytearray(), seed
    for _ in range(n):
        x = (x * 1103515245 + 12345) & 0x7FFFFFFF
        out.append(x >> 16 & 0x3F)
    return out


class Tables(unittest.TestCase):
    def test_complete_codes_decode_every_symbol(self):
        lengths = complete([0, 5, 9, 200], 256)
        table = decode_table(lengths, "t")
        for symbol, (code, length) in codes(lengths).items():
            entry = table[code << (16 - length)]
            self.assertEqual((entry >> 5, entry & 31), (symbol, length))

    def test_empty_tree_is_none_and_bad_trees_are_rejected(self):
        self.assertIsNone(decode_table([0] * 8, "t"))
        with self.assertRaisesRegex(LzxError, "incomplete"):
            decode_table([1, 2, 0], "t")
        with self.assertRaisesRegex(LzxError, "over-subscribed"):
            decode_table([1, 1, 1], "t")
        with self.assertRaisesRegex(LzxError, "longer than 16"):
            decode_table([17, 1], "t")

    def test_sizes_from_flag(self):
        flag = 0xC0000000 | (3 << 11) | 5 | (2 << 15) | (1 << 26)
        self.assertEqual(mcla_lzx.virtual_size(flag), 5 << 11)
        self.assertEqual(mcla_lzx.physical_size(flag), 2 << 9)

    def test_unsupported_window(self):
        with self.assertRaisesRegex(LzxError, "unsupported LZX window"):
            LzxDecoder(14)


class Decode(unittest.TestCase):
    def roundtrip(self, encoder, **kw):
        data = resource(encoder.body(), len(encoder.output), **kw)
        exact = len(encoder.output) % 256 == 0
        out, header = (
            decompress(data)
            if exact
            else decompress(data, expected=len(encoder.output))
        )
        self.assertEqual(out, bytes(encoder.output))
        return header

    def test_literals(self):
        e = Encoder()
        e.block(list(b"Midnight Club LA") * 16)
        header = self.roundtrip(e)
        self.assertEqual(
            (header["type"], header["constant"], header["virtual"]), (63, CONSTANT, 256)
        )

    def test_matches_overlap_repeats_and_length_tree(self):
        e = Encoder()
        tokens = list(b"abcdefgh") + [
            ("m", 30, 8),
            ("m", 3, 1),
            ("r", 0, 4),
            120,
            121,
            ("m", 5, 20),
            ("r", 1, 6),
            ("r", 2, 9),
            ("m", 257, 2),
        ]
        tokens += list(pattern(512 - 8 - 30 - 3 - 4 - 2 - 5 - 6 - 9 - 257))
        e.block(tokens)
        self.roundtrip(e)

    def test_aligned_offsets(self):
        e = Encoder()
        e.block(
            list(pattern(2000))
            + [("m", 40, 1500), ("m", 7, 70), ("m", 9, 5)]
            + list(pattern(2048 - 2056, 1))
        )
        tail = 2304 - len(e.output)
        e.block(list(pattern(tail, 3)), aligned=True)
        self.roundtrip(e)
        e2 = Encoder()
        e2.block(
            list(pattern(1000))
            + [("m", 24, 900), ("m", 12, 33)]
            + list(pattern(256 * 4 - 1036, 2)),
            aligned=True,
        )
        self.roundtrip(e2)

    def test_run_length_codes(self):
        e = Encoder()
        e.block(list(b"run") * 100 + list(b"abcd"), runs=True)
        e.block(
            list(b"abcdefgh") * 32, runs=True
        )  # eight equal non-zero lengths use the same-value run code
        self.roundtrip(e)

    def test_stored_block_then_repeat_register(self):
        e = Encoder()
        e.block(list(b"xy"))
        e.stored(b"stored-bytes!", registers=(4, 9, 2))
        e.block(
            [("r", 0, 6), ("r", 1, 5), ("r", 2, 3)] + list(pattern(256 - 2 - 13 - 14))
        )
        self.roundtrip(e)

    def test_stored_block_at_stream_start_on_word_boundary(self):
        e = Encoder()
        e.writer = (
            BitWriter()
        )  # drop the header bit; a 16-bit header lands on a word boundary below
        e.writer.write(0, 1)
        e.stored(bytes(pattern(256)))
        self.roundtrip(e)

    def test_multi_chunk_state_carries_over(self):
        e = Encoder()
        first = list(pattern(FRAME - 10)) + [("m", 10, 300)]
        e.block(
            first
            + list(b"second chunk")
            + [("m", 200, FRAME)]
            + list(pattern(FRAME - 212, 4))
        )
        e.block(list(pattern(256)))
        body = e.body()
        self.assertEqual(len(e.chunks), 3)
        self.assertNotEqual(body[0], 0xFF)  # full frames use the two-byte header
        self.roundtrip(e)

    def test_block_spanning_chunks_and_stored_continuation(self):
        e = Encoder()
        e.block(list(pattern(FRAME - 6)))
        e.stored(bytes(pattern(4096 + 6, 9)))
        self.roundtrip(e)

    def test_odd_final_stored_byte_has_no_padding(self):
        e = Encoder()
        e.block(list(pattern(10)))
        e.stored(bytes(pattern(245, 5)), pad=False)
        self.roundtrip(e)

    def test_odd_final_stored_byte_with_padding(self):
        e = Encoder()
        e.block(list(pattern(10)))
        e.stored(bytes(pattern(245, 5)))
        self.roundtrip(e)


class Rejections(unittest.TestCase):
    def good(self):
        e = Encoder()
        e.block(list(pattern(200)) + [("m", 56, 100)])
        return e, resource(e.body(), 256)

    def test_header_controls(self):
        e, data = self.good()
        with self.assertRaisesRegex(LzxError, "not an RSC5"):
            decompress(b"RSC5" + data[4:])
        with self.assertRaisesRegex(LzxError, "not an RSC5"):
            parse_header(data[:10])
        with self.assertRaisesRegex(LzxError, "body length differs"):
            decompress(data + b"\0")

    def test_truncated_stream(self):
        e, data = self.good()
        body = data[20:]
        cut = body[:5] + body[5:-4]
        cut = b"\xff" + struct.pack(">HH", 256, len(cut) - 5) + cut[5:]
        with self.assertRaisesRegex(LzxError, "truncated"):
            decompress(resource(cut, 256))
        with self.assertRaisesRegex(LzxError, "chunk outside resource"):
            decompress(resource(body[:-4], 256))
        with self.assertRaisesRegex(LzxError, "chunk header truncated"):
            decompress(resource(body + b"\xff\x00", 256))
        with self.assertRaisesRegex(LzxError, "chunk header truncated"):
            decompress(resource(body + b"\x00", 256))

    def test_flipped_block_type_bit(self):
        e, data = self.good()
        flipped = bytearray(data)
        flipped[26] ^= (
            0x40  # stream bit 1 (high byte of the first word): block type 001 becomes 101
        )
        with self.assertRaisesRegex(LzxError, "LZX block type 5"):
            decompress(bytes(flipped))

    def test_wrong_declared_size(self):
        e, data = self.good()
        with self.assertRaisesRegex(LzxError, "exceeds declared size"):
            decompress(data, expected=128)
        with self.assertRaisesRegex(LzxError, "declared 512"):
            decompress(data, expected=512)

    def test_wrong_window(self):
        e, data = self.good()
        with self.assertRaises(LzxError):
            decompress(data, window_bits=16)

    def test_intel_header_and_empty_block(self):
        e = Encoder(intel=1)
        e.block(list(pattern(256)))
        with self.assertRaisesRegex(LzxError, "Intel E8"):
            decompress(resource(e.body(), 256))
        e = Encoder()
        e.block(list(pattern(256)), size=0)
        with self.assertRaisesRegex(LzxError, "empty block"):
            decompress(resource(e.body(), 256))

    def test_empty_trees_used(self):
        decoder = LzxDecoder()
        decoder.block_type = VERBATIM
        with self.assertRaisesRegex(LzxError, "main tree empty"):
            decoder.decode_compressed(mcla_lzx.Bits(b"\0\0", 0, 2), 1)
        bits = mcla_lzx.Bits(b"\0\0", 0, 2)
        with self.assertRaisesRegex(LzxError, "length tree empty"):
            bits.symbol(None, "length")

    def test_length_run_past_tree(self):
        w = BitWriter()
        for size in PRE_LENGTHS:
            w.write(size, 4)
        w.code(codes(PRE_LENGTHS), 18)
        w.write(31, 5)
        w.align()
        bits = mcla_lzx.Bits(bytes(w.data) + bytes(4), 0, len(w.data) + 4)
        with self.assertRaisesRegex(LzxError, "length run past its tree"):
            LzxDecoder().read_lengths(bits, [0] * 40, 0, 40)

    def test_match_before_output_start(self):
        bad = Encoder()
        bad.output = bytearray(
            100
        )  # the encoder thinks history exists; the decoder has none
        bad.block([("m", 5, 50)] + list(pattern(251)))
        with self.assertRaisesRegex(LzxError, "before start of output"):
            decompress(resource(bad.body(), 256))

    def test_match_crossing_chunk(self):
        e = Encoder()
        e.block(list(pattern(246)) + [("m", 10, 100)])
        size_body = e.body()
        # Declare the chunk 4 bytes short of the decoded tokens.
        chunk = size_body[5:]
        bad = b"\xff" + struct.pack(">HH", 256, len(chunk)) + chunk
        good = decompress(resource(bad, 256))[0]
        self.assertEqual(len(good), 256)
        short = (
            b"\xff"
            + struct.pack(">HH", 252, len(chunk))
            + chunk
            + b"\xff"
            + struct.pack(">HH", 4, 2)
            + b"\0\0"
        )
        with self.assertRaisesRegex(LzxError, "ran past its chunk"):
            decompress(resource(short, 256))

    def test_chunk_size_mismatch(self):
        e, data = self.good()
        body = data[20:]
        chunk = body[5:] + b"\0\0\0\0"
        with self.assertRaisesRegex(LzxError, "chunk size mismatch"):
            decompress(
                resource(b"\xff" + struct.pack(">HH", 256, len(chunk)) + chunk, 256)
            )
        e = Encoder()
        e.block(list(pattern(10)))
        e.stored(bytes(pattern(246, 2)))
        body = e.body()
        chunk = body[5:] + b"\0\0"
        with self.assertRaisesRegex(LzxError, "chunk size mismatch"):
            decompress(
                resource(b"\xff" + struct.pack(">HH", 256, len(chunk)) + chunk, 256)
            )

    def test_stored_block_truncated(self):
        e = Encoder()
        e.block(list(pattern(10)))
        e.stored(bytes(pattern(246, 2)))
        body = e.body()
        chunk = body[5:]
        for cut in (len(chunk) - 250, len(chunk) - 4):
            short = chunk[:cut]
            with self.assertRaisesRegex(LzxError, "truncated"):
                decompress(
                    resource(b"\xff" + struct.pack(">HH", 256, len(short)) + short, 256)
                )

    def test_truncation_inside_symbols(self):
        e = Encoder()
        e.block(
            list(pattern(120))
            + [("m", 40, 100), ("m", 200, 3)]
            + list(pattern(16, 2))
            + [("m", 9, 7)] * 8
        )
        chunk = e.body()[5:]
        reasons = set()
        for cut in range(2, 40, 2):
            short = chunk[:-cut]
            with self.assertRaisesRegex(LzxError, "truncated") as caught:
                decompress(
                    resource(
                        b"\xff" + struct.pack(">HH", 448, len(short)) + short, 448
                    ),
                    expected=448,
                )
            reasons.add(str(caught.exception))
        self.assertEqual(reasons, {"LZX chunk truncated"})

    def test_zero_length_chunk(self):
        with self.assertRaisesRegex(LzxError, "chunk outside resource"):
            decompress(resource(b"\xff\x01\x00\x00\x00", 256))


if __name__ == "__main__":
    unittest.main(verbosity=2)
