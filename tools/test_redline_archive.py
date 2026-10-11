#!/usr/bin/env python3
"""Native package controls; no private game inputs are required."""

import base64
import hashlib
from pathlib import Path
import struct
import tempfile
import unittest
from unittest.mock import patch

from redline_archive import decompress, extract_package, read_package


def package(entries, holes=()):
    """Build a synthetic table with declared decoded sizes and stored bytes."""
    count = len(entries) + len(holes)
    header = b'R3Dl1n3\0' + struct.pack('>I', count) + b'\0' * 12
    table = []
    payload = bytearray()
    for name, size, packed in entries:
        raw = name.encode('mac_roman')
        table.append(struct.pack('>III', 24 + count * 268 + len(payload), size,
                                 len(packed)) + raw + b'\0' * (256 - len(raw)))
        payload.extend(packed)
    table.extend(holes)
    return header + b''.join(table) + payload


def raw(name='test.car', content=b'carName "Control"\r'):
    return name, len(content), b'\1\0\0\0' + content


class CompressionTests(unittest.TestCase):
    def test_raw_empty_and_seed_copies(self):
        self.assertEqual(decompress(b'\1\0\0\0', 0), b'')
        self.assertEqual(decompress(b'\0\0\0\0', 0), b'')
        self.assertEqual(decompress(b'\0\0\0\0\3\0\0\0\0\0', 6), b'123123')
        self.assertEqual(decompress(b'\0\0\0\0\1\0\17\0', 18),
                         b'123456789012345678')

    def test_literal_hash_and_overlapping_copy(self):
        # Native depth-eight hash of ABC is bucket 3288; the first completed
        # literal triple enters slot3288, then the match reads that exact slot.
        packed = b'\0\0\0\0\10\0ABC\xcf\xd8'
        self.assertEqual(decompress(packed, 21), b'ABC' * 7)

    def test_control_groups_and_cursor_wrap(self):
        content = bytes(range(40))
        packed = b'\0\0\0\0' + b''.join(b'\0\0' + content[i:i + 16]
                                          for i in range(0, 40, 16))
        self.assertEqual(decompress(packed, 40), content)

    def test_pinned_native_car_stream(self):
        # NyrksDiablo.car's complete native stored stream, package SHA-256
        # a6324f008f2559ef45a10b4a80f771d6744ef0d1432a9dd3bf13eeb480fe5917. Includes repeated triples,
        # delayed literal hashing, depth-eight replacements and cursor wraps.
        packed = base64.b64decode(
            b'AAAAAAAAO2RpYWJsby5jYXINOzIwMACAMCBMYW1ib3JnaGluaSBEsqIAACBWVA0NYnVpbHRJbiAxDTuBIdCoTmFtZS'
            b'AiD22zp1hQIg3WqE55MAByaydzxJ3QM2hhbGxlbmdlUmUAwHF1aXJlbWVudHMgMHgx8G7YJgAoSGVsbHJhaXNlciBR'
            b'yTsAimluAgBlYzE1LjcgTGl0cmUgVi0xMkGAQhp5ZWFyIAFtDWRpc3BsYWOyFAIIIFBiDXByaWNlIDI18G4wDQ07AA'
            b'AtLS1hZXJvZHluYW1pY3MNAABmcm9udEFpclJlc2lzdGFuAQIgTjAuNQ1zaWRlS20yLjANdG8aAHBLaTPg6/IoTGlm'
            b'dCAtMC4wMQ0WEnLgqiWlMqMdY2hhc8CaDW1gbyAxNgwUMDfg68AucnRpYSB7AW0sAmozNTBogX0NO5HbQ1D28AB70J'
            b'ssMC40MywwimAAMjgzfQ2f29O0MTV9DQ1udW1DAABvbGxCb3hlcyAyDSMgMA1jQQTwaC50ZnIg4I85NTUwCTg1Mywy'
            b'EIMuMjl91SZsIHswig+/bGwudHI81LbILcD39bNyTdXYmGL5gzI3NdkeYmZJ1P1I34BZhvFI2Z36k/dJI2Dk6Xc4NS'
            b'wxLjMxMAn8+TM4MADkd0PU34AGc9WAMIg2NzYC9JPfh5Aq+lbB4xHbMC44Mjj0sks8Hthfhi4yN/W2+pMR2AcB0ZhA'
            b'BJImZ3JhcGgR7G1vZGVsICIBgKSxbWRsIg1pbnRlcmlvck3ZWgqgLfX2LmKpZHJpdmVyUG9zQUU0MQ6KgDQhljAwAH'
            b'N0ZTCJbmdXaGVlbKlKRMA1NDEKMn0NetxBbmdsZSAxALu51YAhVHVybnMgM9HCutdleHR1oMkiTZAgb21vX3XcX3fR'
            b'0y5wY3QiO51SYYhgZGl1AGkuMTjlwm9ycyA0tXqBYHvxRjEOODIsAId0lYVmI7My0SSFZi40OCOzMzkw1iEwLjEIMg'
            b'vQgXRhY2hvVIVBklY4ayYGLtKZklVQb/LxICJww6Sv2FdpZHRoQMEgMC4yNQ2SUlrgrCAtMTE5Ax3x7QDGIDI5DXNw'
            b'ZWVkx9ozvDE0MKPYM7p/Ao9j4iqS1YRgCMMzumRPMjFk4zEwIDE2LgBQNzUNDWV4aGF1c3QxpEowEQk07AI1LNOaJA'
            b'wyokoxihoODfQsY2Vuc2VQsKNsYXRlo0owCTL1YuMQvwIuNjEB6THQAkMCkSIDjQ1wb3fwADU38mt0b3JxdWUQvCA4'
            b'NzADmlJQTSA20OpAvTE8Uc000epoNG1heFHNOdDq4epkbGVRyzHw7eDqamUcB3JrUcrT7QOJSW5lQhyRgQOJRnJpY3'
            b'QkoWlvIBMwMGASbmfAK1NhbXDwyiIDiQDgbm9ybWFsMi53YXYiDUEG9bFBBQ0gKhh64KhQylNvdW5kR2FpbpAINw0Q'
            b'AmZ1bGxayzEuMg1hSVRocm90dDSGbGWZLDWSZx/iMS4xoohVy1BpdGMy79/BmmezS+Gabkm1SzifZLNJwUYNaG9ybv'
            b'a2wHuT4NQGox1zdTC6bnNw0A1zdXBzYMNw0EkLiHQwDWSgMmVyU+BIbmdAtjXQ6kAE8ihT0K93YXlC0AMx0uzhEIUn'
            b'AWpABFF3ZKGtdDB0ABJuDTtmaW5hbEShrVJhcFcgNC4TCrBFHyM1MKBUeENsdfBVVKIDVHJhbrQBc2bwADEAaZAfZk'
            b'BJUPVpYWxMb2NrAEVDb2VmZmljaVDwIKBqDXNogDZVOixwUc058Gvg6nK8RG93blLN82tn4KlTd7k4wXxUafBLwMHi'
            b'wkfgqXMgOLJ6cZRCinMgpVrQmDERETENeJQwsHoymWQygKywejOZYTFgXS41Mg07eJSQBzWwejSbZiBZC2QyIRY1ET'
            b'WaZC44OJrjMC458Zc2m2A2TZugQCMgznM3nGJEAsL+cw2Q1ML61SLD+y5w4fswiIG5LnydMjhhAsCFxPnFK8D3DcT5'
            b'ZgcUdXdyC2VkkAgegDF1c1DI44+gUjgxMzU5MzQwMTd4cZbwUybjmQ9ytR8zMHVxYnJhawBVcVHg6sT48IFoYW5khI'
            b'jQm3Zx01rC+C1zbGltLWAYAEtjLWhvbGVkLmKpxPl35CQzNXVxdP0/hEEzsHj2eKJLcRExDe+xQhjP9iESf3P/eK9U'
            b'bHO2ly5QyJ94ZSAWf4Muj4ggFC9gwbNt319pc5+g7PRzLg/CaW8yd3MwVDCINzkzDi2goxCDz/x1ce+PTwkQGrDNAl'
            b'U0f3Hn7l/JxPl3g+b8hIgyMzDYnX37KGAx6O7fXF9lwbIFwjT2/mlrM3dzMlTP4MGyzy3+/y5PCB8ZQq/li/b4X8nP'
            b'+HVxj4srEN8ZwvgPEWHqzPkF6J/vM+LCTGlnaHRzIDITEWxC9BAZMlQ+ATjwjRBPAekhXxTUZGkx1CwwLC0xfQ3xMB'
            b'TUcmdiQUXxiRCJhmZ0eXBlMOwU0HNpDjR6UGtA3hTQb25GbGFnAGt4kOgV02Zme2jF3rDrI2DkGdQxjf+JdHMuZJ8H'
            b'Ln9RgcUuf9MPEJEIBd9HTMDtH9Wy6TIF2qRMNjIwCTdTfDAA6zcU0G/qcxWsNkCpAIQU0AIQ1udk7jUP2uDlIyD+7z'
            b'MK2DGIT4vvF4LGdFEvjJDYFNBv6sbYMbJ4GdShVP/lPwy/+OD2E6swDyGzH9fgFGTqNA/aMTAG2hwOxmO7r6VLgWwu'
            b'XyWfAx+rc9MX3eHP4YB0D914suk2D9nn2z8Iv/jo8jEsFwUCEObkb+jG2DgP27NsNwrY0BmF/0GLMzD4MS45N0ABGd'
            b'A7DHJRMQ8QCY9ngsVk6OP71mBPTHMubxwOpuKjSN8fGdAtPwkyJx8MBdhv7296xdjP7MDCsuk5CtjUGDI5YAI5PAc/'
            b'CT8k77kw/vsu32B/SwFqs+nm5KpP72cw0I8iID8k77m/J8DCz+m5X8XCMTEN2BQPUMM2hmVm6RcFdFIvMwzeNc9jeN'
            b'7/MOZibZwgWRzUNh8MuPgfAf+8FNBl6s9jr5cHa9Zg5X+kSTcxDTIswPEXAG/oFawRCRIJj2WPxuAUR0kw/+/W4G6a'
            b'xuGlSy8Jv//gFHRRHwkPFpAI32B4H9/GwMtn1P4wLiEJM/FiMcCDGdAwQKkeAJCBLbXt599gf0r/OwdrvuYvCr/95R'
            b'YxDx8ND95D9U9Lcx7TEDUZ1DAu//q/uuHyb+kEkiAz/7kc0g/aMK/iMLNsQC0c1R8Mtvj/vzCKKTN/UtMX5mFi69Bt'
            b'FNBIThGUcCQf1KBSATE5Poa//z+IMWouM+9kTfDg4CMQfQ/br1Rv6B2o0AIU0AIQxmP5v2LrMS6n4RY97+DFwPDnH9'
            b'OvUW/qH6sF2A8WIG+Rw//BwO9hMHgwMA=='
        )
        decoded = decompress(packed, 6840)
        self.assertEqual(hashlib.sha256(decoded).hexdigest(),
                         '2d73b4c9c7254ce58c54efd8b4084325ee8191ef3983f531a3cd84a426a3fe9a')
        self.assertIn(b'model "diablo.mdl"', decoded)
        with self.assertRaisesRegex(ValueError, 'length mismatch|truncated'):
            decompress(packed[:-1], 6840)

    def test_corrupt_and_bounded_streams(self):
        cases = [
            (b'\0\0\0', 0, 'truncated compression flag'),
            (b'\2\0\0\0', 0, 'unsupported compression flag'),
            (b'\1\0\0\0A', 0, 'raw member length mismatch'),
            (b'\0\0\0\0\0', 1, 'truncated or empty control group'),
            (b'\0\0\0\0\0\0', 0, 'truncated or empty control group'),
            (b'\0\0\0\0\1\0\0', 3, 'truncated copy token'),
            (b'\0\0\0\0\1\0\0\0', 2, 'exceeds declared size'),
            (b'\0\0\0\0\0\0A', 2, 'length mismatch'),
            (b'\0\0\0\0\0\0A', 100, 'expansion exceeds LZRW bound'),
        ]
        for packed, expected, reason in cases:
            with self.subTest(reason=reason), self.assertRaisesRegex(ValueError, reason):
                decompress(packed, expected)
        with self.assertRaisesRegex(ValueError, 'size exceeds bound'):
            decompress(b'\1\0\0\0', 9, max_bytes=8)
        with self.assertRaisesRegex(ValueError, 'size exceeds bound'):
            decompress(b'\1\0\0\0', -1)


class PackageTests(unittest.TestCase):
    def test_members_paths_hashes_and_sparse_table_bytes(self):
        content = b'carName "Control"\r'
        source = package([raw(), raw('Icon\r', b'')], [b'\0' * 268,
                          b'\xa1\xb1\xc1\xd3' * 67])
        records = read_package(source)
        self.assertEqual([r['name'] for r in records], ['test.car', 'Icon\r'])
        self.assertEqual(records[0]['data'], content)
        self.assertEqual(records[0]['offset'], 24 + 268 * 4)
        self.assertEqual(records[0]['sha256'], hashlib.sha256(content).hexdigest())
        self.assertEqual(records[0]['compression'], 'raw')
        self.assertEqual(records[0]['stored_bytes'], len(content) + 4)
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'source.redplug'
            path.write_bytes(source)
            self.assertEqual(read_package(path), records)
            output = Path(directory) / 'members'
            extract_package(path, output)
            self.assertEqual((output / 'test.car').read_bytes(), content)
            self.assertEqual((output / 'Icon%0D').read_bytes(), b'')
            with self.assertRaises(FileExistsError):
                extract_package(path, output)
            self.assertEqual((output / 'test.car').read_bytes(), content)

    def test_header_table_offsets_and_complete_eof_coverage(self):
        source = package([raw()])
        with self.assertRaisesRegex(TypeError, 'path or bytes'):
            read_package(8)
        view = memoryview(bytes(16)).cast('B', shape=[2, 8])
        with patch('redline_archive.MAX_PACKAGE_BYTES', 8):
            with self.assertRaisesRegex(ValueError, 'package size exceeds bound'):
                read_package(view)
            with tempfile.TemporaryDirectory() as directory:
                path = Path(directory) / 'oversized.redplug'
                path.write_bytes(source)
                with self.assertRaisesRegex(ValueError, 'package size exceeds bound'):
                    read_package(path)
        mutations = []
        bad = bytearray(source);bad[0] = 0;mutations.append((bad, 'invalid native'))
        bad = bytearray(source);struct.pack_into('>I', bad, 8, 100001)
        mutations.append((bad, 'truncated or excessive'))
        mutations.append((source[:200], 'truncated or excessive'))
        bad = bytearray(source);struct.pack_into('>I', bad, 24, 291)
        mutations.append((bad, 'gap or trailing'))
        bad = bytearray(source);struct.pack_into('>I', bad, 24, len(source) + 1)
        mutations.append((bad, 'gap or trailing'))
        bad = bytearray(source);struct.pack_into('>I', bad, 32, len(source))
        mutations.append((bad, 'gap or trailing'))
        mutations.append((source + b'?', 'gap or trailing'))
        bad = bytearray(package([raw('a'), raw('b')]))
        struct.pack_into('>I', bad, 292, struct.unpack_from('>I', bad, 24)[0])
        mutations.append((bad, 'gap or overlapping'))
        bad = bytearray(source);bad[36] = 0
        mutations.append((bad, 'gap or trailing'))
        for data, reason in mutations:
            with self.subTest(reason=reason), self.assertRaisesRegex(ValueError, reason):
                read_package(data)

    def test_names_traversal_case_collision_and_bombs(self):
        for name in ('../test.car', '/test.car', 'a\\b', 'a:b', '..', '.', 'bad\n'):
            with self.subTest(name=name), self.assertRaisesRegex(ValueError, 'unsafe'):
                read_package(package([raw(name)]))
        with self.assertRaisesRegex(ValueError, 'case-colliding'):
            read_package(package([raw('Test.car'), raw('test.car')]))
        with self.assertRaisesRegex(ValueError, 'case-colliding'):
            read_package(package([raw('é.car'), raw('É.car')]))
        bad = bytearray(package([raw()]))
        bad[36:292] = b'A' * 256
        with self.assertRaisesRegex(ValueError, 'unterminated'):
            read_package(bad)
        with self.assertRaisesRegex(ValueError, 'decoded package size exceeds bound'):
            read_package(package([raw()]), max_member_bytes=1)
        with self.assertRaisesRegex(ValueError, 'decoded package size exceeds bound'):
            read_package(package([raw('a'), raw('b')]), max_total_bytes=20)


if __name__ == '__main__':
    unittest.main()
