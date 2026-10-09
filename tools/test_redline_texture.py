"""Native TXR layout/pixel checks and malformed image/extent controls."""
import base64
import hashlib
import io
import struct
import unittest
from unittest import mock

import redline_texture as texture
from model_png import decode_png
from test_model_png import png as filtered_png


def txr(levels):
    offset = 4 + len(levels) * 4
    offsets, payload = [], bytearray()
    for level, (width, height, compressed, pixels) in enumerate(levels):
        offsets.append(offset)
        blob = struct.pack('>9I', len(pixels) if compressed else 0, 0xDE1, level, 0x83F2 if compressed else 0x1908, width, height, 0, 0x1908, 0x1401) + pixels + b'abc'
        payload.extend(blob)
        offset += len(blob)
    return struct.pack('>I', len(levels)) + struct.pack('>' + str(len(levels)) + 'I', *offsets) + payload


def tga(width, height, pixels, *, flags=32, kind=2, depth=24):
    return struct.pack('<3B2HB2H2H2B', 0, 0, kind, 0, 0, 0, 0, 0, width, height, depth, flags) + pixels


class TextureTests(unittest.TestCase):
    def test_native_source_fixture_and_nonzero_padding(self):
        # Verbatim black.raw.txr; 3 native tail bytes are nonzero, not RGBA.
        data = base64.b64decode('AAAAAQAAAAgAAAAAAAAN4QAAAAAAABkIAAAAAQAAAAEAAAAAAAAZCAAAFAEAAAD/f///')
        self.assertEqual(hashlib.sha256(data).hexdigest(), '03be930dd8a62189905a8474b8fdec45598380e1f0669dfde6f18c455e1b18c3')
        self.assertEqual(texture.decode_image(data, 'black.raw.txr'), (1, 1, b'\0\0\0\xff'))
        changed = data[:-3] + b'xyz'
        self.assertEqual(texture.decode_image(changed, 'black.raw.txr'), (1, 1, b'\0\0\0\xff'))

    def test_dxt3_all_colors_and_explicit_alpha(self):
        alpha = sum(i << (4 * i) for i in range(16))
        selectors = sum((i % 4) << (2 * i) for i in range(16))
        block = struct.pack('<QHHI', alpha, 0xF800, 0x001F, selectors)
        width, height, rgba = texture.decode_image(txr([(4, 4, True, block)]), 'test.txr')
        expected = [(255, 0, 0), (0, 0, 255), (170, 0, 85), (85, 0, 170)]
        self.assertEqual((width, height), (4, 4))
        self.assertEqual(rgba, b''.join(bytes((*expected[i % 4], i * 17)) for i in range(16)))
        # DXT3 c0 <= c1 still has four colors, never DXT1 transparency.
        block = struct.pack('<QHHI', 0xFFFFFFFFFFFFFFFF, 0, 0xFFFF, selectors)
        rgba = texture.decode_image(txr([(4, 4, True, block)]), 'test.txr')[2]
        self.assertEqual(rgba[:16], bytes([0, 0, 0, 255, 255, 255, 255, 255, 85, 85, 85, 255, 170, 170, 170, 255]))

    def test_dxt3_partial_blocks_and_raw_mips(self):
        block = struct.pack('<QHHI', 0xFFFFFFFFFFFFFFFF, 0x07E0, 0, 0)
        self.assertEqual(texture.decode_image(txr([(3, 2, True, block)]), 'a.txr'), (3, 2, b'\0\xff\0\xff' * 6))
        raw = bytes(range(64))
        self.assertEqual(texture.decode_image(txr([(4, 4, False, raw), (2, 2, False, bytes(16)), (1, 1, False, bytes(4))]), 'a.txr'), (4, 4, raw))

    def test_native_raw_planes_and_square_extents(self):
        planes = bytes(range(16)), bytes(range(16, 32))
        self.assertEqual(texture.decode_raw3d(b''.join(planes)), (2, 2, planes))
        self.assertEqual(texture.decode_image(b''.join(planes), 'wheel.raw3d'), (2, 2, planes[0]))
        self.assertEqual(texture.decode_image(b'\x05\x09\x0e', 'a.raw'), (1, 1, b'\x05\x09\x0e\xff'))
        self.assertEqual(texture.decode_image(b'\x05', 'a.graw'), (1, 1, b'\x05\x05\x05\xff'))
        self.assertEqual(texture.decode_image(b'\x05\x09\x0e\x10', 'a.RGBA'), (1, 1, b'\x05\x09\x0e\x10'))
        for data in (b'', bytes(7), bytes(24)):
            with self.assertRaises(ValueError):
                texture.decode_raw3d(data)
        with self.assertRaisesRegex(ValueError, 'not square'):
            texture.decode_image(bytes(6), 'a.raw')

    def test_txr_mutation_controls(self):
        original = txr([(2, 2, False, bytes(16)), (1, 1, False, bytes(4))])
        controls = [(0, 33, 'table'), (4, 8, 'offsets'), (8, 12, 'offsets'), (16, 0, 'descriptor'), (20, 9, 'descriptor'), (24, 0x83F2, 'raw format'), (28, 16385, 'dimensions'), (44, 0x1406, 'descriptor')]
        for offset, value, reason in controls:
            data = bytearray(original)
            struct.pack_into('>I', data, offset, value)
            with self.subTest(offset=offset), self.assertRaisesRegex(ValueError, reason):
                texture.decode_image(bytes(data), 'a.txr')
        for mutated in (original[:-1], original + b'x'):
            with self.assertRaisesRegex(ValueError, 'extent'):
                texture.decode_image(mutated, 'a.txr')
        changed = bytearray(original)
        second = struct.unpack_from('>I', changed, 8)[0]
        struct.pack_into('>I', changed, second + 16, 2)
        with self.assertRaisesRegex(ValueError, 'mip dimensions'):
            texture.decode_image(bytes(changed), 'a.txr')
        compressed = txr([(4, 4, True, bytes(15))])
        with self.assertRaisesRegex(ValueError, 'compressed format or size'):
            texture.decode_image(compressed, 'a.txr')

    def test_tga_channel_orientation_rle_and_grayscale(self):
        # Stored bottom/right first: blue, green; output green, blue.
        self.assertEqual(texture.decode_image(tga(2, 1, b'\xff\0\0\0\xff\0', flags=16), 'a.tga'), (2, 1, b'\0\xff\0\xff\0\0\xff\xff'))
        rgba = texture.decode_image(tga(1, 2, b'\xff\0\0\0\xff\0', flags=0), 'a.tga')[2]
        self.assertEqual(rgba, b'\0\xff\0\xff\0\0\xff\xff')
        repeated = tga(3, 1, b'\x82\0\0\xff\x80', kind=10, depth=32, flags=40)
        self.assertEqual(texture.decode_image(repeated, 'a.tga')[2], b'\xff\0\0\x80' * 3)
        self.assertEqual(texture.decode_image(tga(2, 1, b'\x01\x04', kind=3, depth=8), 'a.tga')[2], bytes([1, 1, 1, 255, 4, 4, 4, 255]))
        for data, reason in [(tga(1, 1, b'\x82\0\0\xff', kind=10), 'exceeds'), (tga(1, 1, b'\0\0'), 'truncated'), (tga(1, 1, b'\0\0\0', flags=64), 'Unsupported')]:
            with self.assertRaisesRegex(ValueError, reason):
                texture.decode_image(data, 'a.tga')

    def test_png_identity_size_and_corruption(self):
        rgba = bytes([5, 9, 14, 0, 60, 70, 80, 90])
        png = texture.encode_png(2, 1, rgba)
        self.assertEqual(decode_png(png), (2, 1, rgba))
        self.assertEqual(texture.decode_image(png, 'renamed.pct'), (2, 1, rgba))
        with mock.patch.object(texture, '_pillow_image', return_value=None):
            self.assertEqual(texture.decode_image(png, 'a.png'), (2, 1, rgba))
        expected = bytes([10, 20, 30, 40, 50, 60, 70, 80])
        residuals = [expected, bytes([10, 20, 30, 40, 40, 40, 40, 40]), bytes(8), bytes([5, 10, 15, 20, 20, 20, 20, 20]), bytes(8)]
        for mode, residual in enumerate(residuals):
            image = filtered_png([b'\0' + expected, bytes([mode]) + residual])
            self.assertEqual(texture.decode_image(image, 'a.png'), decode_png(image))
        for width, height, pixels in [(0, 1, b''), (16385, 1, b''), (5000, 5000, b''), (1, 1, b'x')]:
            with self.assertRaises(ValueError):
                texture.encode_png(width, height, pixels)
        with self.assertRaises(ValueError):
            texture.decode_image(png[:-4], 'a.png')
        bad = bytearray(png)
        bad[29] ^= 1
        with self.assertRaises(ValueError):
            texture.decode_image(bytes(bad), 'a.png')
        for image, reason in [(filtered_png([b'\0' + bytes(9)]), 'row size'), (filtered_png([b'\5' + bytes(8)]), 'filter')]:
            with self.assertRaisesRegex(ValueError, reason):
                texture.decode_image(image, 'a.png')

    def test_unknown_audio_and_decoder_failures(self):
        with self.assertRaisesRegex(ValueError, 'audio'):
            texture.decode_image(b'asnd' + bytes(20), 'sample.ima')
        for data in (b'', b'not an image', bytearray(b'not bytes')):
            with self.assertRaises(ValueError):
                texture.decode_image(data, 'unknown')
        pict = bytearray(526)
        struct.pack_into('>4h', pict, 514, 0, 0, 2, 2)
        pict[522:526] = b'\0\x11\x02\xff'
        with mock.patch.object(texture.sys, 'platform', 'linux'), self.assertRaisesRegex(ValueError, 'requires macOS'):
            texture.decode_image(bytes(pict), 'a.pct')

    def test_optional_pillow_images(self):
        try:
            from PIL import Image
        except ImportError:
            self.skipTest('Pillow is not installed in this interpreter')
        for kind in ('PNG', 'TIFF', 'BMP'):
            stream = io.BytesIO()
            image = Image.new('LA', (2, 1), (73, 101)) if kind == 'PNG' else Image.new('RGB', (2, 1), (1, 2, 3))
            image.save(stream, format=kind)
            result = texture.decode_image(stream.getvalue(), kind.lower())
            self.assertEqual(result, (2, 1, image.convert('RGBA').tobytes()))
        # A PSD can retain authoring layers and a separate flattened composite.
        # Two empty layer records are not two animation/image frames.
        record = struct.pack('>4iH', 0, 0, 1, 1, 0) + b'8BIMnorm\xff\0\0\0' + struct.pack('>I', 0)
        layer_info = struct.pack('>h', 2) + record * 2
        layer_mask = struct.pack('>I', len(layer_info)) + layer_info + bytes(4)
        psd = b'8BPS' + struct.pack('>H6sHIIHH', 1, bytes(6), 3, 1, 1, 8, 3)
        psd += bytes(8) + struct.pack('>I', len(layer_mask)) + layer_mask + b'\0\0\x0b\x16\x21'
        with Image.open(io.BytesIO(psd)) as authoring:
            self.assertEqual(authoring.n_frames, 2)
        self.assertEqual(texture.decode_image(psd, 'renamed.pct'), (1, 1, b'\x0b\x16\x21\xff'))
        stream = io.BytesIO()
        image.save(stream, format='TIFF', save_all=True, append_images=[image.copy()])
        with self.assertRaisesRegex(ValueError, 'multiple frames'):
            texture.decode_image(stream.getvalue(), 'a.tif')


if __name__ == '__main__':
    unittest.main()
