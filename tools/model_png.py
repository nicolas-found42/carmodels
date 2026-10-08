"""Decode embedded RGB/RGBA PNGs for editable models, independently of recovery verifiers."""
import struct
import zlib


def decode_png(data):
    if data[:8] != b'\x89PNG\r\n\x1a\n':
        raise ValueError('Model texture is not PNG; export textures as PNG')
    offset, header, compressed, ended = 8, None, bytearray(), False
    while offset + 12 <= len(data):
        size = struct.unpack_from('>I', data, offset)[0]
        kind = data[offset + 4:offset + 8]
        end = offset + 12 + size
        if end > len(data):
            raise ValueError('Truncated model PNG chunk')
        payload = data[offset + 8:end - 4]
        if zlib.crc32(kind + payload) != struct.unpack_from('>I', data, end - 4)[0]:
            raise ValueError('Model PNG CRC mismatch')
        if kind == b'IHDR':
            if header is not None or offset != 8 or size != 13:
                raise ValueError('Invalid model PNG header')
            header = struct.unpack('>2I5B', payload)
        elif kind == b'IDAT':
            compressed.extend(payload)
        elif kind == b'IEND':
            if size or end != len(data):
                raise ValueError('Invalid model PNG ending')
            ended = True
            break
        elif kind[:1].isupper():
            raise ValueError('Unsupported model PNG critical chunk')
        offset = end
    if header is None or not ended:
        raise ValueError('Incomplete model PNG')
    width, height, depth, color, compression, filtering, interlace = header
    if not width or not height or width * height > 16_777_216 or depth != 8 or color not in (2, 6) or (compression, filtering, interlace) != (0, 0, 0):
        raise ValueError('Model PNG requires non-interlaced RGB8 or RGBA8')
    channels = 3 if color == 2 else 4
    stride = width * channels
    expected = height * (stride + 1)
    decoder = zlib.decompressobj()
    raw = decoder.decompress(bytes(compressed), expected + 1)
    if len(raw) != expected or not decoder.eof or decoder.unused_data or decoder.unconsumed_tail:
        raise ValueError('Model PNG decompressed size differs')
    pixels, previous = bytearray(), bytearray(stride)
    for y in range(height):
        start = y * (stride + 1)
        mode, row = raw[start], bytearray(raw[start + 1:start + 1 + stride])
        if mode > 4:
            raise ValueError('Invalid model PNG filter')
        for x in range(stride) if mode else ():
            left = row[x - channels] if x >= channels else 0
            up = previous[x]
            upper_left = previous[x - channels] if x >= channels else 0
            p = left + up - upper_left
            distances = [abs(p - v) for v in (left, up, upper_left)]
            paeth = (left, up, upper_left)[distances.index(min(distances))]
            predictor = (0, left, up, (left + up) // 2, paeth)[mode]
            row[x] = (row[x] + predictor) & 255
        if channels == 4:
            pixels.extend(row)
        else:
            for x in range(0, stride, 3):
                pixels.extend(row[x:x + 3] + b'\xff')
        previous = row
    return width, height, bytes(pixels)
