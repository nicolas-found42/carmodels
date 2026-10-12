"""FIPS-197 appendix C known-answer vectors, CBC chaining and malformed-input controls.

`AesEncryptor` is a deliberately plain, test-only forward cipher used to build encrypted
fixtures for the MCLA disc tests; it is checked against the same vectors.
"""
import unittest

from aes_decrypt import SBOX, AesDecryptor


def _xtime(a):
    return ((a << 1) ^ (0x1B if a & 0x80 else 0)) & 0xFF


class AesEncryptor:
    def __init__(self, key):
        nk = len(key) // 4
        self.rounds = nk + 6
        words = [list(key[4 * i:4 * i + 4]) for i in range(nk)]
        rcon = 1
        for i in range(nk, 4 * (self.rounds + 1)):
            t = list(words[i - 1])
            if i % nk == 0:
                t = [SBOX[b] for b in t[1:] + t[:1]]
                t[0] ^= rcon
                rcon = _xtime(rcon)
            elif nk > 6 and i % nk == 4:
                t = [SBOX[b] for b in t]
            words.append([a ^ b for a, b in zip(words[i - nk], t)])
        self.keys = [sum(words[4 * r:4 * r + 4], []) for r in range(self.rounds + 1)]

    def block(self, data):
        s = [a ^ b for a, b in zip(data, self.keys[0])]
        for r in range(1, self.rounds + 1):
            s = [SBOX[b] for b in s]
            s = [s[(i + 4 * (i % 4)) % 16] for i in range(16)]  # ShiftRows on column-major state
            if r < self.rounds:
                mixed = []
                for c in range(4):
                    a = s[4 * c:4 * c + 4]
                    total = a[0] ^ a[1] ^ a[2] ^ a[3]
                    mixed += [a[i] ^ total ^ _xtime(a[i] ^ a[(i + 1) % 4]) for i in range(4)]
                s = mixed
            s = [a ^ b for a, b in zip(s, self.keys[r])]
        return bytes(s)

    def ecb(self, data):
        return b''.join(self.block(data[i:i + 16]) for i in range(0, len(data), 16))

    def cbc(self, data, iv=bytes(16)):
        out, previous = bytearray(), iv
        for i in range(0, len(data), 16):
            previous = self.block(bytes(a ^ b for a, b in zip(data[i:i + 16], previous)))
            out += previous
        return bytes(out)


PLAIN = bytes.fromhex('00112233445566778899aabbccddeeff')
VECTORS = [
    ('000102030405060708090a0b0c0d0e0f', '69c4e0d86a7b0430d8cdb78070b4c55a'),
    ('000102030405060708090a0b0c0d0e0f1011121314151617', 'dda97ca4864cdfe06eaf70a0ec0d7191'),
    ('000102030405060708090a0b0c0d0e0f101112131415161718191a1b1c1d1e1f', '8ea2b7ca516745bfeafc49904b496089'),
]


class AesTests(unittest.TestCase):
    def test_fips197_vectors(self):
        for key, cipher in VECTORS:
            self.assertEqual(AesDecryptor(bytes.fromhex(key)).block(bytes.fromhex(cipher)), PLAIN)

    def test_fixture_encryptor_round_trips(self):
        for key, cipher in VECTORS:
            self.assertEqual(AesEncryptor(bytes.fromhex(key)).block(PLAIN).hex(), cipher)
        key = bytes(range(32))
        data = bytes(range(256)) * 2
        self.assertEqual(AesDecryptor(key).cbc(AesEncryptor(key).cbc(data, b'v' * 16), b'v' * 16), data)

    def test_wrong_key_does_not_decrypt(self):
        key, cipher = VECTORS[2]
        wrong = bytearray.fromhex(key)
        wrong[0] ^= 1
        self.assertNotEqual(AesDecryptor(bytes(wrong)).block(bytes.fromhex(cipher)), PLAIN)

    def test_cbc_chains_previous_ciphertext(self):
        # NIST SP 800-38A F.2.2 (CBC-AES128.Decrypt), first two blocks.
        aes = AesDecryptor(bytes.fromhex('2b7e151628aed2a6abf7158809cf4f3c'))
        iv = bytes.fromhex('000102030405060708090a0b0c0d0e0f')
        cipher = bytes.fromhex('7649abac8119b246cee98e9b12e9197d5086cb9b507219ee95db113a917678b2')
        self.assertEqual(aes.cbc(cipher, iv).hex(),
                         '6bc1bee22e409f96e93d7e117393172aae2d8a571e03ac9c9eb76fac45af8e51')
        self.assertEqual(aes.ecb(cipher[:16]), aes.cbc(cipher[:16], bytes(16)))

    def test_rejects_partial_blocks_and_bad_keys(self):
        with self.assertRaisesRegex(ValueError, 'key must be'):
            AesDecryptor(b'short')
        with self.assertRaisesRegex(ValueError, 'whole blocks'):
            AesDecryptor(bytes(16)).ecb(b'x' * 17)
        with self.assertRaisesRegex(ValueError, 'whole blocks'):
            AesDecryptor(bytes(16)).cbc(b'x' * 16, b'iv')


if __name__ == '__main__':
    unittest.main(verbosity=2)
