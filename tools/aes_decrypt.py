"""Pure-Python AES decryption (FIPS-197) for the stock interpreter, which has no crypto module.

Decryption only: ECB and CBC over whole 16-byte blocks. Checked against the FIPS-197
appendix C vectors in test_aes_decrypt.py. Speed is adequate for archive tables and one
executable image; it is not constant-time and must never handle secrets of this repo.
"""


def _tables():
    sbox, inverse = [0] * 256, [0] * 256
    p = q = 1
    while True:
        p ^= (p << 1) ^ (0x1B if p & 0x80 else 0)
        p &= 0xFF
        q ^= q << 1
        q ^= q << 2
        q ^= q << 4
        q &= 0xFF
        if q & 0x80:
            q ^= 0x09
        value = q ^ ((q << 1 | q >> 7) & 0xFF) ^ ((q << 2 | q >> 6) & 0xFF) ^ ((q << 3 | q >> 5) & 0xFF) \
            ^ ((q << 4 | q >> 4) & 0xFF) ^ 0x63
        sbox[p] = value
        inverse[value] = p
        if p == 1:
            break
    sbox[0], inverse[0x63] = 0x63, 0

    def mul(a, b):
        out = 0
        while b:
            if b & 1:
                out ^= a
            a = ((a << 1) ^ (0x1B if a & 0x80 else 0)) & 0xFF
            b >>= 1
        return out
    decrypt = [[0] * 256 for _ in range(4)]
    for x in range(256):
        s = inverse[x]
        word = (mul(s, 14) << 24) | (mul(s, 9) << 16) | (mul(s, 13) << 8) | mul(s, 11)
        for r in range(4):
            decrypt[r][x] = ((word >> (8 * r)) | (word << (32 - 8 * r))) & 0xFFFFFFFF
    mix = [[0] * 256 for _ in range(4)]  # InvMixColumns of a plain byte, for the key schedule
    for x in range(256):
        word = (mul(x, 14) << 24) | (mul(x, 9) << 16) | (mul(x, 13) << 8) | mul(x, 11)
        for r in range(4):
            mix[r][x] = ((word >> (8 * r)) | (word << (32 - 8 * r))) & 0xFFFFFFFF
    return sbox, inverse, decrypt, mix


SBOX, INVERSE, TD, MIX = _tables()
RCON = [0x01, 0x02, 0x04, 0x08, 0x10, 0x20, 0x40, 0x80, 0x1B, 0x36]


class AesDecryptor:
    def __init__(self, key):
        if len(key) not in (16, 24, 32):
            raise ValueError('AES key must be 16, 24 or 32 bytes')
        nk = len(key) // 4
        self.rounds = nk + 6
        words = [int.from_bytes(key[4 * i:4 * i + 4], 'big') for i in range(nk)]
        for i in range(nk, 4 * (self.rounds + 1)):
            t = words[i - 1]
            if i % nk == 0:
                t = ((t << 8) | (t >> 24)) & 0xFFFFFFFF
                t = (SBOX[t >> 24] << 24) | (SBOX[t >> 16 & 255] << 16) | (SBOX[t >> 8 & 255] << 8) | SBOX[t & 255]
                t ^= RCON[i // nk - 1] << 24
            elif nk > 6 and i % nk == 4:
                t = (SBOX[t >> 24] << 24) | (SBOX[t >> 16 & 255] << 16) | (SBOX[t >> 8 & 255] << 8) | SBOX[t & 255]
            words.append(words[i - nk] ^ t)
        # Equivalent inverse cipher: reversed round keys, InvMixColumns on the middle ones.
        keys = [words[4 * r:4 * r + 4] for r in range(self.rounds + 1)][::-1]
        for r in range(1, self.rounds):
            keys[r] = [MIX[0][w >> 24] ^ MIX[1][w >> 16 & 255] ^ MIX[2][w >> 8 & 255] ^ MIX[3][w & 255]
                       for w in keys[r]]
        self.keys = keys

    def block(self, data):
        k = self.keys
        t0, t1, t2, t3 = TD
        s0 = int.from_bytes(data[0:4], 'big') ^ k[0][0]
        s1 = int.from_bytes(data[4:8], 'big') ^ k[0][1]
        s2 = int.from_bytes(data[8:12], 'big') ^ k[0][2]
        s3 = int.from_bytes(data[12:16], 'big') ^ k[0][3]
        for r in range(1, self.rounds):
            rk = k[r]
            s0, s1, s2, s3 = (
                t0[s0 >> 24] ^ t1[s3 >> 16 & 255] ^ t2[s2 >> 8 & 255] ^ t3[s1 & 255] ^ rk[0],
                t0[s1 >> 24] ^ t1[s0 >> 16 & 255] ^ t2[s3 >> 8 & 255] ^ t3[s2 & 255] ^ rk[1],
                t0[s2 >> 24] ^ t1[s1 >> 16 & 255] ^ t2[s0 >> 8 & 255] ^ t3[s3 & 255] ^ rk[2],
                t0[s3 >> 24] ^ t1[s2 >> 16 & 255] ^ t2[s1 >> 8 & 255] ^ t3[s0 & 255] ^ rk[3])
        rk, inv = k[self.rounds], INVERSE
        out = (
            ((inv[s0 >> 24] << 24) | (inv[s3 >> 16 & 255] << 16) | (inv[s2 >> 8 & 255] << 8) | inv[s1 & 255]) ^ rk[0],
            ((inv[s1 >> 24] << 24) | (inv[s0 >> 16 & 255] << 16) | (inv[s3 >> 8 & 255] << 8) | inv[s2 & 255]) ^ rk[1],
            ((inv[s2 >> 24] << 24) | (inv[s1 >> 16 & 255] << 16) | (inv[s0 >> 8 & 255] << 8) | inv[s3 & 255]) ^ rk[2],
            ((inv[s3 >> 24] << 24) | (inv[s2 >> 16 & 255] << 16) | (inv[s1 >> 8 & 255] << 8) | inv[s0 & 255]) ^ rk[3])
        return b''.join(w.to_bytes(4, 'big') for w in out)

    def ecb(self, data):
        if len(data) % 16:
            raise ValueError('AES input is not whole blocks')
        return b''.join(self.block(data[i:i + 16]) for i in range(0, len(data), 16))

    def cbc(self, data, iv=bytes(16)):
        if len(data) % 16 or len(iv) != 16:
            raise ValueError('AES input is not whole blocks')
        out, previous = bytearray(), iv
        for i in range(0, len(data), 16):
            chunk = data[i:i + 16]
            plain = int.from_bytes(self.block(chunk), 'big') ^ int.from_bytes(previous, 'big')
            out += plain.to_bytes(16, 'big')
            previous = chunk
        return bytes(out)
