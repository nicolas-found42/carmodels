"""XEX2 loader controls on synthetic executables: basic packing, retail-key encryption and rejections."""
import struct
import unittest

from aes_decrypt import AesDecryptor
from test_aes_decrypt import AesEncryptor
from xex2 import RETAIL_KEY, load_image

SESSION = bytes(range(16, 32))


def pe_image(body=b'', size=0x3000):
    image = bytearray(size)
    image[:2] = b'MZ'
    struct.pack_into('<I', image, 0x3C, 0x80)
    image[0x80:0x84] = b'PE\0\0'
    image[0x100:0x100 + len(body)] = body
    return bytes(image)


def xex_fixture(image, encrypted=True, compression=1, zero_tail=0x1000):
    """Basic packing: the image minus a zero tail is stored, then the tail is zero-filled."""
    stored = image[:len(image) - zero_tail]
    if image[len(stored):] != bytes(zero_tail):
        raise ValueError('fixture tail is not zero')
    blocks = [(len(stored), zero_tail)]
    format_info = struct.pack('>IHH', 8 + 8 * len(blocks), 1 if encrypted else 0, compression)
    format_info += b''.join(struct.pack('>II', d, z) for d, z in blocks)
    security_at, format_at, pe_at = 0x40, 0x200, 0x400
    header = bytearray(pe_at)
    struct.pack_into('>4sIIIII', header, 0, b'XEX2', 1, pe_at, 0, security_at, 1)
    struct.pack_into('>II', header, 24, 0x3FF, format_at)
    struct.pack_into('>I', header, security_at + 4, len(image))
    file_key = AesEncryptor(RETAIL_KEY).ecb(SESSION)  # decrypts back to SESSION under the retail key
    header[security_at + 0x150:security_at + 0x160] = file_key if encrypted else bytes(16)
    header[format_at:format_at + len(format_info)] = format_info
    payload = stored + bytes((-len(stored)) % 16)
    if encrypted:
        payload = AesEncryptor(SESSION).cbc(payload)
    return bytes(header) + payload


class Xex2Tests(unittest.TestCase):
    def test_session_key_derivation(self):
        self.assertEqual(AesDecryptor(RETAIL_KEY).ecb(AesEncryptor(RETAIL_KEY).ecb(SESSION)), SESSION)

    def test_loads_encrypted_and_plain_basic_images(self):
        image = pe_image(b'archive key lives here')
        for encrypted in (True, False):
            loaded, facts = load_image(xex_fixture(image, encrypted))
            self.assertEqual(loaded, image)
            self.assertEqual(facts['encryption'], int(encrypted))
            self.assertEqual(facts['blocks'], [[len(image) - 0x1000, 0x1000]])

    def test_rejects_unsupported_and_corrupt_executables(self):
        image = pe_image()
        with self.assertRaisesRegex(ValueError, 'not an XEX2'):
            load_image(b'XEX1' + xex_fixture(image)[4:])
        with self.assertRaisesRegex(ValueError, 'only basic'):
            load_image(xex_fixture(image, compression=2))
        wrong_key = bytearray(xex_fixture(image))
        wrong_key[0x40 + 0x150] ^= 1
        with self.assertRaisesRegex(ValueError, 'not a PE'):
            load_image(bytes(wrong_key))
        resized = bytearray(xex_fixture(image))
        struct.pack_into('>I', resized, 0x40 + 4, len(image) + 0x1000)
        with self.assertRaisesRegex(ValueError, 'disagree with image size'):
            load_image(bytes(resized))
        with self.assertRaisesRegex(ValueError, 'shorter than its blocks'):
            load_image(xex_fixture(image)[:0x400 + 0x100])
        odd = pe_image(size=0x3000 + 8)  # stored bytes end mid AES block
        with self.assertRaisesRegex(ValueError, 'shorter than its blocks'):
            load_image(xex_fixture(odd)[:-8])
        self.assertEqual(load_image(xex_fixture(odd))[0], odd)
        outside = bytearray(xex_fixture(image))
        struct.pack_into('>I', outside, 8, len(outside) + 1)  # PE data offset past the file
        with self.assertRaisesRegex(ValueError, 'header outside file'):
            load_image(bytes(outside))
        no_format = bytearray(xex_fixture(image))
        struct.pack_into('>I', no_format, 24, 0x2FF)  # the only optional header is not file format info
        with self.assertRaisesRegex(ValueError, 'file format info missing'):
            load_image(bytes(no_format))
        unknown = bytearray(xex_fixture(image))
        struct.pack_into('>H', unknown, 0x200 + 4, 2)  # encryption type 2
        with self.assertRaisesRegex(ValueError, 'unsupported XEX2 file format info'):
            load_image(bytes(unknown))
        far = bytearray(xex_fixture(image))
        struct.pack_into('>I', far, 28, 0x3FF0)  # file format info offset beyond the header
        with self.assertRaisesRegex(ValueError, 'file format info outside header'):
            load_image(bytes(far))
        past_end = bytearray(pe_image(size=0x2000))
        struct.pack_into('<I', past_end, 0x3C, 0x2000 - 2)  # PE pointer leaves two bytes of image
        with self.assertRaisesRegex(ValueError, 'lacks a PE header'):
            load_image(xex_fixture(bytes(past_end)))
        tiny = b'MZ' + bytes(0x2E)  # shorter than the 0x3C pointer field
        with self.assertRaisesRegex(ValueError, 'lacks a PE header'):
            load_image(xex_fixture(tiny, zero_tail=0x10))
        no_pe = bytearray(image)
        no_pe[0x80:0x84] = b'NE\0\0'
        with self.assertRaisesRegex(ValueError, 'lacks a PE header'):
            load_image(xex_fixture(bytes(no_pe)))


if __name__ == '__main__':
    unittest.main(verbosity=2)
