"""Bounded Redline TXR and conventional image decoding to top-to-bottom RGBA8.

TXR descriptors follow the pinned game's upload routine at 0x645e0: a BE mip
count/offset table and nine BE words per mip, followed by OpenGL pixel data.
The observed corpus uses RGBA8 or DXT3. The three bytes after each payload are
retained native padding, not pixels. DXT3 follows EXT_texture_compression_s3tc;
this is not a claim of identical driver interpolation or game rendering.
Standard uncommon formats need Pillow; PICT uses macOS ImageIO via sips.
"""
import io
import math
import struct
import subprocess
import sys
import tempfile
import warnings
import zlib
from pathlib import Path

from model_png import decode_png

MAX_PIXELS = 16_777_216
MAX_BYTES = 128 * 1024 * 1024


def _dimensions(width, height):
    if not isinstance(width, int) or not isinstance(height, int) or not 0 < width <= 16384 or not 0 < height <= 16384 or width * height > MAX_PIXELS:
        raise ValueError('Redline image dimensions exceed bounds')


def encode_png(width, height, rgba):
    """Encode RGBA8 without altering orientation, alpha, or channel values."""
    _dimensions(width, height)
    if len(rgba) != width * height * 4:
        raise ValueError('Redline RGBA size differs from dimensions')

    def chunk(kind, data):
        return struct.pack('>I', len(data)) + kind + data + struct.pack('>I', zlib.crc32(kind + data))

    stride = width * 4
    raw = b''.join(b'\0' + rgba[y * stride:(y + 1) * stride] for y in range(height))
    return b'\x89PNG\r\n\x1a\n' + chunk(b'IHDR', struct.pack('>2I5B', width, height, 8, 6, 0, 0, 0)) + chunk(b'IDAT', zlib.compress(raw)) + chunk(b'IEND', b'')


def _rgb565(value):
    red, green, blue = value >> 11, (value >> 5) & 63, value & 31
    return ((red << 3) | (red >> 2), (green << 2) | (green >> 4), (blue << 3) | (blue >> 2))


def _dxt3(data, width, height):
    if len(data) != ((width + 3) // 4) * ((height + 3) // 4) * 16:
        raise ValueError('Redline DXT3 payload size differs')
    pixels = bytearray(width * height * 4)
    offset = 0
    for by in range(0, height, 4):
        for bx in range(0, width, 4):
            alpha, c0, c1, selectors = struct.unpack_from('<QHHI', data, offset)
            offset += 16
            first, second = _rgb565(c0), _rgb565(c1)
            # DXT3 always has four colors, even when c0 <= c1.
            colors = (first, second, tuple((2 * a + b) // 3 for a, b in zip(first, second)), tuple((a + 2 * b) // 3 for a, b in zip(first, second)))
            for y in range(min(4, height - by)):
                row = bytearray()
                for x in range(min(4, width - bx)):
                    i = y * 4 + x
                    row.extend(colors[(selectors >> (2 * i)) & 3])
                    row.append(((alpha >> (4 * i)) & 15) * 17)
                start = ((by + y) * width + bx) * 4
                pixels[start:start + len(row)] = row
    return bytes(pixels)


def decode_txr(data):
    """Validate every retained mip, return the highest-resolution pixels only."""
    if len(data) < 8 or len(data) > MAX_BYTES:
        raise ValueError('Redline TXR byte size exceeds bounds')
    count = struct.unpack_from('>I', data)[0]
    if not 0 < count <= 32 or len(data) < 4 + count * 4:
        raise ValueError('Redline TXR mip table invalid')
    offsets = struct.unpack_from('>' + str(count) + 'I', data, 4)
    if offsets[0] != 4 + 4 * count or any(a >= b for a, b in zip(offsets, offsets[1:])):
        raise ValueError('Redline TXR offsets invalid')
    first = None
    previous = None
    for level, start in enumerate(offsets):
        end = offsets[level + 1] if level + 1 < count else len(data)
        if start + 36 > end or end > len(data):
            raise ValueError('Redline TXR mip descriptor truncated')
        size, target, declared_level, internal, width, height, border, format_, type_ = struct.unpack_from('>9I', data, start)
        _dimensions(width, height)
        if (target, declared_level, border, format_, type_) != (0xDE1, level, 0, 0x1908, 0x1401):
            raise ValueError('Unsupported Redline TXR descriptor')
        if previous and (width, height) != (max(1, previous[0] // 2), max(1, previous[1] // 2)):
            raise ValueError('Redline TXR mip dimensions inconsistent')
        previous = width, height
        if size:
            expected = ((width + 3) // 4) * ((height + 3) // 4) * 16
            if internal != 0x83F2 or size != expected:
                raise ValueError('Unsupported Redline TXR compressed format or size')
        else:
            if internal != 0x1908:
                raise ValueError('Unsupported Redline TXR raw format')
            expected = width * height * 4
        # Every observed mip has three trailing bytes. Native uploads use only
        # the declared data; padding is sometimes nonzero and must not be read.
        if end - start != 36 + expected + 3:
            raise ValueError('Redline TXR mip payload extent differs')
        if first is None:
            payload = data[start + 36:start + 36 + expected]
            first = width, height, _dxt3(payload, width, height) if size else payload
    return first


def decode_raw3d(data):
    """Return square edge, edge, two native RGBA8 planes (loader 0x649e6).

    The game's 3D upload uses depth two; its 2D fallback uses only plane zero.
    Preserve both planes here so callers can explicitly choose representation.
    """
    if not isinstance(data, bytes) or not data or len(data) > MAX_BYTES or len(data) % 8:
        raise ValueError('Redline raw3d byte size invalid')
    edge = math.isqrt(len(data) // 8)
    _dimensions(edge, edge)
    if edge * edge * 8 != len(data):
        raise ValueError('Redline raw3d planes are not square')
    plane_size = edge * edge * 4
    return edge, edge, (data[:plane_size], data[plane_size:])


def _raw(data, suffix):
    channels = {'raw': 3, 'graw': 1, 'rgba': 4}[suffix]
    edge = math.isqrt(len(data) // channels)
    _dimensions(edge, edge)
    if edge * edge * channels != len(data):
        raise ValueError('Redline raw image is not square')
    if channels == 4:
        return edge, edge, data
    rgba = bytearray()
    for i in range(0, len(data), channels):
        rgba.extend(data[i:i + 3] if channels == 3 else data[i:i + 1] * 3)
        rgba.append(255)
    return edge, edge, bytes(rgba)


def _tga(data):
    if len(data) < 18:
        raise ValueError('Redline TGA header truncated')
    ident, cmap, kind, cmap_start, cmap_size, cmap_depth, x, y, width, height, depth, flags = struct.unpack_from('<3B2HB2H2H2B', data)
    _dimensions(width, height)
    if not cmap and kind in (2, 10) and depth == 16:
        return _standard(data)
    if cmap or kind not in (2, 3, 10, 11) or depth not in (8, 24, 32) or (kind in (3, 11)) != (depth == 8) or flags & 0xC0 or flags & 15 not in (0, 8):
        raise ValueError('Unsupported Redline TGA format')
    offset, channels, total = 18 + ident, depth // 8, width * height
    raw = bytearray()
    while len(raw) // channels < total:
        if kind in (10, 11):
            if offset >= len(data):
                raise ValueError('Redline TGA RLE packet truncated')
            packet = data[offset]
            offset += 1
            n, repeated = (packet & 127) + 1, packet & 128
        else:
            n, repeated = total, False
        if len(raw) // channels + n > total:
            raise ValueError('Redline TGA RLE packet exceeds pixel count')
        size = channels if repeated else n * channels
        if offset + size > len(data):
            raise ValueError('Redline TGA pixels truncated')
        raw.extend(data[offset:offset + size] * (n if repeated else 1))
        offset += size
    pixels = bytearray(total * 4)
    for row in range(height):
        for col in range(width):
            index = (row * width + col) * channels
            source = raw[index:index + channels]
            pixel = bytes([source[0]] * 3 + [255]) if channels == 1 else bytes((source[2], source[1], source[0], source[3] if channels == 4 else 255))
            dest_y = row if flags & 32 else height - 1 - row
            dest_x = width - 1 - col if flags & 16 else col
            dest = (dest_y * width + dest_x) * 4
            pixels[dest:dest + 4] = pixel
    return width, height, bytes(pixels)


def _pict(data):
    # Check the conventional 512-byte file header and PICT v2 frame before
    # handing this bounded input to the installed macOS ImageIO decoder.
    if len(data) < 526 or data[522:526] != b'\0\x11\x02\xff':
        raise ValueError('Unsupported Redline PICT header')
    top, left, bottom, right = struct.unpack_from('>4h', data, 514)
    _dimensions(right - left, bottom - top)
    if sys.platform != 'darwin' or not Path('/usr/bin/sips').is_file():
        raise ValueError('Redline PICT conversion requires macOS sips')
    with tempfile.TemporaryDirectory(prefix='redline-pict-') as directory:
        src, dst = Path(directory) / 'input.pict', Path(directory) / 'output.png'
        src.write_bytes(data)
        try:
            result = subprocess.run(['/usr/bin/sips', '-s', 'format', 'png', str(src), '--out', str(dst)], capture_output=True, timeout=30)
        except (OSError, subprocess.TimeoutExpired) as exc:
            raise ValueError('Redline PICT ImageIO decoder unavailable or timed out') from exc
        if result.returncode or not dst.is_file() or dst.stat().st_size > MAX_BYTES:
            raise ValueError('Redline PICT ImageIO conversion failed')
        return decode_image(dst.read_bytes(), 'output.png')


def _pillow_image():
    try:
        from PIL import Image
    except ImportError:
        return None
    return Image


def _standard(data):
    Image = _pillow_image()
    if Image is None:
        raise ValueError('This Redline image format requires Pillow')
    try:
        with warnings.catch_warnings():
            warnings.simplefilter('error', Image.DecompressionBombWarning)
            with Image.open(io.BytesIO(data)) as image:
                if image.format not in {'PNG', 'JPEG', 'TIFF', 'PSD', 'BMP', 'TGA'}:
                    raise ValueError('Unsupported Redline standard image format')
                _dimensions(*image.size)
                # PSD n_frames counts authoring layers, not image animation.
                # The initial Pillow tile is the stored composite; leave it
                # selected and avoid decoding layer metadata just to count it.
                if image.format != 'PSD' and getattr(image, 'n_frames', 1) != 1:
                    raise ValueError('Redline image contains multiple frames')
                if image.format == 'PNG':
                    # Pillow's pixel load alone does not check every chunk CRC.
                    image.verify()
                    with Image.open(io.BytesIO(data)) as verified:
                        rgba = verified.convert('RGBA')
                        return rgba.width, rgba.height, rgba.tobytes()
                # Native source pixels, without color-profile or EXIF rotation.
                rgba = image.convert('RGBA')
                return rgba.width, rgba.height, rgba.tobytes()
    except (OSError, SyntaxError, Image.DecompressionBombWarning, Image.DecompressionBombError) as exc:
        raise ValueError('Invalid Redline standard image') from exc


def _png_envelope(data):
    """Pillow accepts some incomplete PNGs; require a complete CRC-valid file."""
    offset, header, compressed = 8, None, bytearray()
    while offset + 12 <= len(data):
        size = struct.unpack_from('>I', data, offset)[0]
        kind = data[offset + 4:offset + 8]
        end = offset + 12 + size
        if end > len(data):
            raise ValueError('Redline PNG chunk truncated')
        body = data[offset + 8:end - 4]
        if zlib.crc32(kind + body) != struct.unpack_from('>I', data, end - 4)[0]:
            raise ValueError('Redline PNG CRC mismatch')
        if kind == b'IHDR':
            if offset != 8 or header or size != 13:
                raise ValueError('Redline PNG header invalid')
            _dimensions(*struct.unpack_from('>2I', body))
            header = struct.unpack('>2I5B', body)
        elif not header:
            raise ValueError('Redline PNG header missing')
        elif kind == b'IDAT':
            compressed.extend(body)
        elif kind == b'IEND':
            if size or not compressed or end != len(data):
                raise ValueError('Redline PNG ending invalid')
            width, height, depth, color, compression, filtering, interlace = header
            channels = {0: 1, 2: 3, 3: 1, 4: 2, 6: 4}.get(color)
            depths = (1, 2, 4, 8, 16) if color == 0 else (1, 2, 4, 8) if color == 3 else (8, 16)
            if channels is None or depth not in depths or compression or filtering or interlace not in (0, 1):
                raise ValueError('Unsupported Redline PNG header')
            # Validate only row extents and filter bytes, leaving pixel/filter
            # reconstruction to Pillow or the independent stdlib decoder.
            passes = [(0, 0, 1, 1)] if not interlace else [(0, 0, 8, 8), (4, 0, 8, 8), (0, 4, 4, 8), (2, 0, 4, 4), (0, 2, 2, 4), (1, 0, 2, 2), (0, 1, 1, 2)]
            rows = []
            for x, y, dx, dy in passes:
                pw, ph = max(0, (width - x + dx - 1) // dx), max(0, (height - y + dy - 1) // dy)
                if pw and ph:
                    rows.extend([1 + (pw * channels * depth + 7) // 8] * ph)
            expected = sum(rows)
            decoder = zlib.decompressobj()
            try:
                raw = decoder.decompress(bytes(compressed), expected + 1)
            except zlib.error as exc:
                raise ValueError('Redline PNG compressed pixels invalid') from exc
            if len(raw) != expected or not decoder.eof or decoder.unused_data or decoder.unconsumed_tail:
                raise ValueError('Redline PNG decoded row size differs')
            start = 0
            for row_size in rows:
                if raw[start] > 4:
                    raise ValueError('Redline PNG filter invalid')
                start += row_size
            return
        elif kind[:1].isupper() and kind != b'PLTE':
            raise ValueError('Redline PNG unknown critical chunk')
        offset = end
    raise ValueError('Redline PNG ending missing')


def decode_image(data, name=''):
    """Return width, height, RGBA8; unknown/corrupt formats fail explicitly.

    Rows remain in native storage order. For raw3d, use the game's documented
    first-plane 2D fallback; use decode_raw3d to retain both source planes.
    """
    if not isinstance(data, bytes) or not data or len(data) > MAX_BYTES:
        raise ValueError('Redline image byte size exceeds bounds')
    suffix = str(name).lower().rsplit('.', 1)[-1]
    if suffix == 'ima' or data[:4] == b'asnd':
        raise ValueError('Redline IMA is audio, not an image')
    if suffix == 'txr':
        return decode_txr(data)
    if suffix == 'raw3d':
        width, height, planes = decode_raw3d(data)
        return width, height, planes[0]
    if suffix in {'raw', 'graw', 'rgba'}:
        return _raw(data, suffix)
    if data[:8] == b'\x89PNG\r\n\x1a\n':
        _png_envelope(data)
        # Use the installed C decoder when available: large filtered car
        # textures otherwise spend seconds per image in Python pixel loops.
        if _pillow_image() is not None:
            return _standard(data)
        try:
            return decode_png(data)
        except ValueError:
            return _standard(data)
    if suffix == 'tga':
        return _tga(data)
    if len(data) >= 526 and data[522:526] == b'\0\x11\x02\xff':
        return _pict(data)
    return _standard(data)
