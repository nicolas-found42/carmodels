"""Native geometry regression, expansion and targeted corruption controls."""

import base64
import math
from pathlib import Path
import struct
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parent))
from redline_mesh import decode_model, expanded_primitives


def fixture(dual=False, normals=True, uvs=True, trailer=b""):
    flags = 2 if dual else 0
    n = 3 if normals else 0
    u = 3 if uvs else 0
    data = struct.pack(">6If", 3, n, u, 1, 2 if dual else 1, flags, 2.0)
    data += struct.pack(">9f", 0, 0, 0, 1, 0, 0, 0, 1, 0)
    if normals:
        data += struct.pack(">9f", 0, 0, 1, 0, 0, 1, 0, 0, 1)
    if uvs:
        data += struct.pack(">6f", 0, 0, 1, 0, 0, 1)
    words = [1]
    for i in range(1, 4):
        words.extend((i, i if normals else 0xFFFFFFFF, i if uvs else 0xFFFFFFFF))
        if dual:
            words.append(4 - i if uvs else 0xFFFFFFFF)
        words.append(0xFFFFFFFF)
    data += struct.pack(">" + "I" * len(words), *words)
    for name in ([b"paint.pct", b"layer.tif"] if dual else [b"paint.pct"]):
        data += name.ljust(32, b"\0") + struct.pack(">2I10f", 17, 32,
            0, 0, 0, 0, .5, .5, .5, 1, 1, 1)
    return data + trailer


class MeshTests(unittest.TestCase):
    def test_shipped_finish_line_fixture(self):
        # Verbatim native resource: circuitfinishline.mdl, 391 bytes. This is a
        # source-byte fixture; it is not reconstructed by the decoder under test.
        raw = base64.b64decode(
            "AAAABgAAAAYAAAAEAAAAAgAAAAEAAAAAQsijlcLH//00u+eiwQAAAMLH//20sSrb"
            "QPAAAMDomHA9mz6QwOOansDomHA9mz4/QNOansCLFs09mz6QwOOansCLFs09mz4/"
            "QNOaniWIK/s/gAAAMzzZXCXMQfg/gAAAMzzZXCWIK/s/gAAAMzzZXAAAAAA/gAAA"
            "MzzZXCUIK/s/gAAAMzzZXCUIK/s/gAAAMzzZXD99r308vi1gPEpb2TyRA8A/fSu"
            "AP3+bEzwpXIU/fjHGAAAAAQAAAAMAAAABAAAAAf////8AAAAEAAAAAgAAAAL/////"
            "AAAABgAAAAMAAAAE/////wAAAAEAAAAFAAAABAAAAAP/////AAAAAwAAAAUAAAAB"
            "/////wAAAAYAAAAGAAAABP////9maW5pc2hsaW5lc3RyaXBlMS50aWYAAAAAAAAA"
            "AAAAAAAAASwAAAAiAAAAAAAAAAAAAAAAAAAAAD8AAAA/AAAAPwAAAD+AAAA/gAAA"
            "P4AAAAAAAA==")
        self.assertEqual(len(raw), 391)
        m = decode_model(raw)
        self.assertEqual(m["counts"], {"positions": 6, "normals": 6, "uvs": 4,
            "triangles": 2, "materials": 1})
        self.assertEqual(m["triangles"][0]["corners"],
                         [(2, 0, 0, None), (3, 1, 1, None), (5, 2, 3, None)])
        self.assertEqual(m["materials"][0]["source_offset"], 308)
        self.assertEqual(m["materials"][0]["texture"], "finishlinestripe1.tif")
        self.assertEqual(m["materials"][0]["flags"], 34)
        self.assertEqual(m["opaque_trailer"]["bytes"], 3)
        self.assertEqual(expanded_primitives(m)[0]["source_offsets"], [204, 256])

    def test_records_offsets_and_expansion(self):
        raw = fixture(trailer=b"opaque")
        m = decode_model(raw)
        self.assertEqual(m["source_offsets"], {"positions": 28, "normals": 64,
            "uvs": 100, "triangles": 124, "materials": 176})
        self.assertEqual(m["triangles"][0]["corners"],
                         [(0, 0, 0, None), (1, 1, 1, None), (2, 2, 2, None)])
        self.assertEqual(m["materials"][0]["texture"], "paint.pct")
        self.assertEqual(m["opaque_trailer"]["bytes"], 6)
        self.assertEqual(m["bounds"], [[0, 0, 0], [1, 1, 0]])
        p = expanded_primitives(m)[0]
        self.assertEqual(p["positions"], m["positions"])
        self.assertEqual(p["normals"], m["normals"])
        self.assertEqual(p["uvs"], m["uvs"])
        self.assertEqual(p["indices"], [0, 1, 2])
        self.assertEqual(p["source_offsets"], [124])
        self.assertIsNone(p["secondary_material"])

    def test_dual_texture_and_absent_channels(self):
        m = decode_model(fixture(dual=True))
        p = expanded_primitives(m)[0]
        self.assertEqual(p["secondary_material"], 1)
        self.assertEqual(p["secondary_uvs"], list(reversed(m["uvs"])))
        self.assertEqual(m["source_offsets"]["materials"], 188)
        p = expanded_primitives(decode_model(fixture(normals=False, uvs=False)))[0]
        self.assertEqual(p["normals"], [(0, 0, 1)] * 3)
        self.assertEqual(p["uvs"], [(0, 0)] * 3)
        degenerate = bytearray(fixture(normals=False))
        degenerate[28:64] = bytes(36)
        self.assertEqual(expanded_primitives(decode_model(bytes(degenerate)))[0]["normals"],
                         [(0, 0, 0)] * 3)

    def test_counts_truncation_flags_and_numeric_controls(self):
        raw = fixture()
        mutations = [(0, ">I", 500_001, "record count"),
                     (0, ">I", 300, "truncated"),
                     (20, ">I", 4, "unsupported model flags"),
                     (24, ">f", -1, "radius"),
                     (28, ">f", math.inf, "positions"),
                     (64, ">f", math.nan, "normals"),
                     (100, ">f", math.inf, "UVs"),
                     (216, ">f", math.inf, "material values")]
        for offset, fmt, value, error in mutations:
            with self.subTest(error=error):
                bad = bytearray(raw)
                struct.pack_into(fmt, bad, offset, value)
                with self.assertRaisesRegex(ValueError, error):
                    decode_model(bytes(bad))
        for bad in (raw[:27], raw[:255], bytearray(raw)):
            with self.assertRaises(ValueError):
                decode_model(bad)
        bad = bytearray(fixture(dual=True))
        struct.pack_into(">I", bad, 16, 1)
        with self.assertRaisesRegex(ValueError, "must be even"):
            decode_model(bytes(bad))

    def test_index_channel_and_name_controls(self):
        raw = fixture()
        for offset, value, error in [(124, 2, "material index"),
                    (128, 0, "corner 0"), (132, 4, "corner 1"),
                    (136, 4, "corner 2"), (148, 0xFFFFFFFF, "mixed missing")]:
            bad = bytearray(raw)
            struct.pack_into(">I", bad, offset, value)
            with self.assertRaisesRegex(ValueError, error):
                decode_model(bytes(bad))
        for name in (b"../paint", b"folder\\paint", b"bad\nname", b".."):
            bad = bytearray(raw)
            bad[176:208] = name.ljust(32, b"\0")
            with self.assertRaisesRegex(ValueError, "unsafe material"):
                decode_model(bytes(bad))
        bad = bytearray(raw)
        bad[176:208] = b"caf\x8e.pct".ljust(32, b"\0")
        self.assertEqual(decode_model(bytes(bad))["materials"][0]["texture"], "café.pct")

    def test_native_material_zero_omitted_high_bit_preserved(self):
        raw = bytearray(fixture())
        struct.pack_into(">I", raw, 124, 0)
        self.assertEqual(expanded_primitives(decode_model(bytes(raw))), [])
        struct.pack_into(">I", raw, 124, 0x80000001)
        m = decode_model(bytes(raw))
        self.assertEqual(m["triangles"][0]["native_material_word"], 0x80000001)
        self.assertEqual(m["triangles"][0]["material"], 0)
        self.assertEqual(len(expanded_primitives(m)[0]["indices"]), 3)


if __name__ == "__main__":
    unittest.main()
