"""Minimal XEX2 (Xbox 360 executable) image loader: normal/no encryption, basic packing only.

Header readings (big-endian), checked on the MCLA `default.xex`: `XEX2`, module flags,
PE data offset, reserved, security-info offset, optional-header count, then (key, value)
pairs. Optional header 0x3FF (file format info) gives encryption type (0 none, 1 normal)
and compression type (1 basic: (data, zero-fill) block pairs). The security info carries
the image size at +4 and the AES-128 file key at +0x150. The session key is the file key
decrypted under the retail key with AES-ECB; the image is AES-CBC with a zero IV.

The retail key is the public XEX2 key used by open-source Xbox 360 emulators (Xenia
`src/xenia/cpu/xex_module.cc`, `xe_xex2_retail_key`). LZX ("normal") packing is not implemented.
"""
import struct

from aes_decrypt import AesDecryptor

RETAIL_KEY = bytes.fromhex('20b185a59d28fdc340583fbb0896bf91')
FORMAT_INFO = 0x3FF
MAX_IMAGE = 256 * 1024 * 1024


def load_image(xex):
    """Return (image bytes, facts) for a basic-packed XEX2; raises on anything else."""
    if len(xex) < 24 or xex[:4] != b'XEX2':
        raise ValueError('not an XEX2 executable')
    _, pe_offset, _, security, count = struct.unpack_from('>IIIII', xex, 4)
    if not 24 + 8 * count <= pe_offset <= len(xex) or not security + 0x160 <= pe_offset:
        raise ValueError('XEX2 header outside file')
    headers = dict(struct.unpack_from('>II', xex, 24 + 8 * i) for i in range(count))
    if FORMAT_INFO not in headers:
        raise ValueError('XEX2 file format info missing')
    at = headers[FORMAT_INFO]
    if not 24 + 8 * count <= at <= pe_offset - 8:
        raise ValueError('XEX2 file format info outside header')
    size, encryption, compression = struct.unpack_from('>IHH', xex, at)
    if compression != 1:
        raise ValueError('only basic XEX2 packing is supported')
    if encryption not in (0, 1) or size < 8 or (size - 8) % 8 or at + size > pe_offset:
        raise ValueError('unsupported XEX2 file format info')
    blocks = [struct.unpack_from('>II', xex, at + 8 + 8 * i) for i in range((size - 8) // 8)]
    image_size = struct.unpack_from('>I', xex, security + 4)[0]
    if not 0 < image_size <= MAX_IMAGE or sum(d + z for d, z in blocks) != image_size:
        raise ValueError('XEX2 block sizes disagree with image size')
    payload = xex[pe_offset:]
    stored = sum(d for d, _ in blocks)
    cipher = (stored + 15) & ~15 if encryption else stored  # AES works on whole 16-byte blocks
    if cipher > len(payload):
        raise ValueError('XEX2 payload shorter than its blocks')
    if encryption:
        session = AesDecryptor(RETAIL_KEY).ecb(xex[security + 0x150:security + 0x160])
        payload = AesDecryptor(session).cbc(payload[:cipher])
    image, position = bytearray(), 0
    for data, zero in blocks:
        image += payload[position:position + data]
        image += bytes(zero)
        position += data
    if image[:2] != b'MZ':
        raise ValueError('XEX2 image is not a PE (wrong key or packing)')
    pe = struct.unpack_from('<I', image, 0x3C)[0] if len(image) >= 0x40 else len(image)
    if image[pe:pe + 4] != b'PE\0\0':
        raise ValueError('XEX2 image lacks a PE header')
    return bytes(image), {'image_bytes': image_size, 'encryption': encryption, 'compression': compression,
                          'blocks': [list(b) for b in blocks]}
