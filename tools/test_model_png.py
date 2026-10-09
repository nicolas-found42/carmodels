"""Independent PNG filter fixtures and malformed texture controls."""
import struct
import unittest
import zlib

from model_png import decode_png


def png(rows, color=6):
    def chunk(kind, data):
        return struct.pack('>I', len(data)) + kind + data + struct.pack('>I', zlib.crc32(kind + data))
    return b'\x89PNG\r\n\x1a\n' + chunk(b'IHDR', struct.pack('>2I5B', 2, len(rows), 8, color, 0, 0, 0)) + chunk(b'IDAT', zlib.compress(b''.join(rows))) + chunk(b'IEND', b'')


class ModelPngTests(unittest.TestCase):
    def test_all_filters_and_rgb(self):
        # Same two RGBA pixels on both rows. Expected residuals calculated explicitly.
        expected = bytes([10, 20, 30, 40, 50, 60, 70, 80])
        residuals = [expected, bytes([10, 20, 30, 40, 40, 40, 40, 40]), bytes(8),
                     bytes([5, 10, 15, 20, 20, 20, 20, 20]), bytes(8)]
        for mode, residual in enumerate(residuals):
            self.assertEqual(decode_png(png([b'\0' + expected, bytes([mode]) + residual])), (2, 2, expected * 2))
        self.assertEqual(decode_png(png([b'\0\x01\x02\x03\x04\x05\x06'], 2))[2], b'\x01\x02\x03\xff\x04\x05\x06\xff')

    def test_invalid_controls(self):
        valid = png([b'\0' + bytes(8)])
        damaged = bytearray(valid); damaged[30] ^= 1
        for data, reason in [(bytes(damaged), 'CRC'), (valid[:-4], 'Incomplete'), (b'jpeg', 'not PNG'),
                             (png([b'\5' + bytes(8)]), 'filter'), (png([b'\0' + bytes(9)]), 'size')]:
            with self.assertRaisesRegex(ValueError, reason):
                decode_png(data)


if __name__ == '__main__':
    unittest.main()
