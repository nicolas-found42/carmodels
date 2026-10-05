"""Bounded level-zero indices under FR2's static model upload contract.

FUN_00222358 selects PSMCT32 for packed format3 and PSMCT16 for packed
format4, then samples PSMT8/PSMT4. Direct uploads retain linear indices.
GS address arithmetic was checked against PCSX2 GSTables.cpp at
81526d4dc7cc70e4ae75abb35a789417456c6d43. This is an offline file
interpretation; no original uploader, GS, emulator, or game code is run.
The earlier baseline results are preserved as a superseded decoding profile.
"""
from functools import lru_cache
import struct

from evidence_common import Invalid
from ps2_container import Unsupported, unswizzle8

MAX_DIMENSION = 512


def _xor_basis(value: int, basis: tuple[int, ...]) -> int:
    result = 0
    for bit, mask in enumerate(basis):
        if (value >> bit) & 1:
            result ^= mask
    return result


def _block(x: int, y: int) -> int:
    return _xor_basis(x | y << 2, (2, 8, 1, 4, 16))


# Exhaustively compared with all 32 blocks and 128/512 public table cells.
_INVERSE_BLOCK = { _block(x, y): (x, y) for y in range(8) for x in range(4) }
_INVERSE_COLUMN16 = {
    _xor_basis(x | y << 4, (2, 8, 16, 1, 4, 32, 64)): (x, y)
    for y in range(8) for x in range(16)
}


@lru_cache(maxsize=8)
def _packed4_order(width: int, height: int, uw: int, uh: int, dbw: int, tbw: int) -> tuple[int, ...]:
    order = []
    pages_wide = (tbw * 64) // 128
    for y in range(height):
        for x in range(width):
            page = (y // 128) * pages_wide + x // 128
            block = _block((x % 128) // 32, (y % 128) // 16)
            column = _xor_basis((x % 32) | (y % 16) << 5, (8, 32, 64, 2, 4, 16, 65, 192, 256))
            nibble = page * 16384 + block * 512 + column
            halfword = nibble // 4
            upload_page, in_page = divmod(halfword, 4096)
            bx, by = _INVERSE_BLOCK[in_page // 128]
            cx, cy = _INVERSE_COLUMN16[in_page % 128]
            ux = (upload_page % dbw) * 64 + bx * 16 + cx
            uy = (upload_page // dbw) * 64 + by * 8 + cy
            if ux >= uw or uy >= uh:
                raise Invalid('packed four-bit mapping reads an unwritten upload coordinate')
            order.append((uy * uw + ux) * 4 + (nibble & 3))
    if len(set(order)) != width * height or min(order) != 0 or max(order) != width * height - 1:
        raise Invalid('packed four-bit upload is not an exact nibble permutation')
    return tuple(order)


def _span(data: bytes, offset: int, size: int, label: str) -> bytes:
    if type(offset) is not int or type(size) is not int or offset < 0 or size < 0 or offset > len(data) or size > len(data) - offset:
        raise Invalid(f'{label} is outside the input bytes')
    return data[offset:offset + size]


def decode_indices(data: bytes, texture: dict) -> bytes:
    """Return one palette index byte per level-zero pixel, with stored alpha untouched."""
    descriptor = _span(data, texture['descriptor_offset'], 64, 'texture descriptor')
    field, = struct.unpack_from('<Q', descriptor, 0x38)
    buffer_field, = struct.unpack_from('<Q', descriptor, 0x30)
    fmt = descriptor[0x34]
    width, height = 1 << ((field >> 15) & 15), 1 << ((field >> 19) & 15)
    if fmt != texture['format'] or width != texture['width'] or height != texture['height']:
        raise Invalid('texture item differs from its descriptor')
    if fmt not in (3, 4):
        raise Unsupported('only indexed format3/format4 are interpreted')
    if max(width, height) > MAX_DIMENSION or width * height < 2:
        raise Unsupported('indexed dimensions are outside the bounded 2..512 profile')
    level = texture['levels'][0]
    size = width * height * (8 if fmt == 3 else 4) // 8
    if level['size'] != size or level['width'] != width or level['height'] != height:
        raise Invalid('level-zero dimensions or size differ from the descriptor')
    plane = _span(data, level['offset'], size, 'level-zero plane')
    uw, uh = 1 << ((field >> 23) & 15), 1 << ((field >> 27) & 15)
    packed = bool(field & 256)
    expected = (width // 2, height // 2) if packed else (width, height)
    if (uw, uh) != expected:
        raise Invalid('transfer dimensions do not match the measured upload profile')
    tbw, dbw = (buffer_field >> 16) & 63, (buffer_field >> 22) & 63
    if tbw != max(2, width // 64) or dbw != (max(1, uw // 64) if packed else tbw):
        raise Invalid('buffer width does not match the measured upload profile')
    if fmt == 3:
        return unswizzle8(plane, width, height) if packed else plane
    if not packed:
        return bytes(n for byte in plane for n in (byte & 15, byte >> 4))
    order = _packed4_order(width, height, uw, uh, dbw, tbw)
    return bytes((plane[n // 2] >> ((n & 1) * 4)) & 15 for n in order)
