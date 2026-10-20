"""Independent retained-native-data, material variant and corruption controls."""

import base64
import json
from pathlib import Path
import struct
import unittest

from bake_models import read_glb
from gt_model import build_glb, parse_car, sha
from model_png import decode_png

ROOT = Path(__file__).resolve().parents[1]


def packet(vertices, normals, colour, command, flag0=0x98000000, flag1=0x80000000):
    """Encode the native bit fields independently of the production decoder."""
    v = [*vertices, *([0] * (4 - len(vertices)))]
    n = [*normals, *([0] * (4 - len(normals)))]
    return struct.pack(
        "<4I",
        v[0] | v[1] << 9 | v[2] << 18 | flag0,
        v[3] | n[0] << 9 | n[1] << 19 | flag1,
        n[2] | n[3] << 10,
        colour[0] | colour[1] << 8 | colour[2] << 16 | command << 24,
    )


def car_fixture():
    data = bytearray(128)
    data[:11] = b"@(#)GT-CAR\0"
    data[12:16] = b"root"
    for i, centre in enumerate(
        [
            (500, 1200, 100, 123),
            (3000, 1200, 100, -123),
            (500, 1200, -100, 456),
            (3000, 1200, -100, -456),
        ]
    ):
        struct.pack_into("<4h", data, 16 + i * 8, *centre)
    struct.pack_into("<4H", data, 48, 513, 1025, 257, 513)
    struct.pack_into("<IH", data, 56, 0x12345678, 1)
    struct.pack_into("<II", data, 64, 0x90000, 0xDEADBEEF)
    data[88:128] = b"\xa5" * 40
    header = bytearray(40)
    struct.pack_into("<10H", header, 0, 4, 2, 1, 0, 0, 0, 1, 1, 0, 0)
    struct.pack_into("<8h", header, 20, -9, -8, -7, 123, 4096, 4096, 7, -123)
    struct.pack_into("<2H", header, 36, 16, 0x2345)
    data.extend(header)
    for vertex in [
        (0, 0, 0, 11),
        (4096, 0, 0, 22),
        (4096, 4096, 0, 33),
        (0, 4096, 0, 44),
    ]:
        data.extend(struct.pack("<4h", *vertex))
    data.extend(struct.pack("<8h", 0, 0, -4096, 99, 0, 4096, 0, -7))
    data.extend(packet([0, 1, 2], [1, 1, 1], [12, 34, 56], 0x23))
    data.extend(packet([0, 1, 3], [0, 0, 0], [255, 255, 255], 0x27))
    data.extend(bytes([0, 0, 0, 0, 255, 0, 0, 0, 0, 255, 0, 0]))
    data.extend(
        packet([0, 1, 2, 3], [0, 0, 0, 0], [255, 255, 255], 0x2F, 0x90000000, 0)
    )
    data.extend(bytes([0, 0, 1, 0, 255, 0, 0, 0, 255, 255, 0, 255]))
    data.extend(
        struct.pack(
            "<4H8h2I",
            1,
            1,
            18,
            0x3456,
            -500,
            0,
            -600,
            1,
            500,
            0,
            600,
            2,
            0xABCDEF00,
            0x11223344,
        )
    )
    for i in range(7):
        data.extend(struct.pack("<4h", i * 100, -i * 50, i * 10, 1000 + i))
    data.extend(b"\x01native\0trailing")
    return bytes(data)


def tex_fixture(duplicate=False):
    data = bytearray(0x8060 + 3 * 512)
    data[:12] = b"@(#)GT-CTEX\0"
    struct.pack_into("<H", data, 14, 3)
    data[16:19] = bytes([7, 7, 19])
    struct.pack_into("<16H", data, 32, *[1 << i for i in range(16)])
    struct.pack_into("<16H", data, 64, *[0xFFFF ^ (1 << i) for i in range(16)])
    data[0x60:0x8060] = bytes(range(256)) * 128
    for colour in range(3):
        seed = 0 if duplicate else colour
        words = []
        for i in range(256):
            word = (
                ((i + seed * 7) & 31)
                | (((i // 4 + seed * 3) & 31) << 5)
                | (((i // 16 + seed * 11) & 31) << 10)
            )
            words.append(
                0
                if i % 16 == 0
                else 0x8000
                if i % 16 == 1
                else word | (0x8000 if i & 1 else 0)
            )
        struct.pack_into("<256H", data, 0x8060 + colour * 512, *words)
    return bytes(data)


def buffer_view(doc, binary, index):
    view = doc["bufferViews"][index]
    return binary[
        view.get("byteOffset", 0) : view.get("byteOffset", 0) + view["byteLength"]
    ]


def source_bytes(doc, binary, ref):
    raw = buffer_view(doc, binary, ref["bufferView"])
    return raw[ref.get("byteOffset", 0) : ref.get("byteOffset", 0) + ref["byteLength"]]


def accessor(doc, binary, index):
    row = doc["accessors"][index]
    width = {"SCALAR": 1, "VEC2": 2, "VEC3": 3}[row["type"]]
    raw = buffer_view(doc, binary, row["bufferView"])
    kind = {5125: "I", 5126: "f"}[row["componentType"]]
    return struct.unpack_from(
        "<" + kind * width * row["count"], raw, row.get("byteOffset", 0)
    )


class NativeDataTests(unittest.TestCase):
    def build(self, metadata=None, duplicate=False):
        return read_glb(
            build_glb(
                car_fixture(), tex_fixture(duplicate), "native-fixture", metadata
            )[0]
        )

    def test_complete_sources_and_structured_raw_sections(self):
        doc, binary = self.build()
        extras = doc["extras"]
        for key, original in [("car", car_fixture()), ("ctex", tex_fixture())]:
            ref = extras["nativeSourcePayloads"][key]
            self.assertEqual(buffer_view(doc, binary, ref["bufferView"]), original)
            self.assertEqual(ref["byteLength"], len(original))
            self.assertEqual(ref["sha256"], sha(original))
        native = extras["nativeData"]
        self.assertEqual(
            source_bytes(doc, binary, native["carHeader"]), car_fixture()[:128]
        )
        tex = tex_fixture()
        self.assertEqual(source_bytes(doc, binary, native["ctex"]["header"]), tex[:96])
        self.assertEqual(
            source_bytes(doc, binary, native["ctex"]["indexedPixels"]), tex[96:0x8060]
        )
        self.assertEqual(
            source_bytes(doc, binary, native["ctex"]["illuminationMasks"]), tex[32:64]
        )
        self.assertEqual(
            source_bytes(doc, binary, native["ctex"]["paintMasks"]), tex[64:96]
        )
        for i, palette in enumerate(native["ctex"]["palettes"]):
            self.assertEqual(
                source_bytes(doc, binary, palette),
                tex[0x8060 + 512 * i : 0x8260 + 512 * i],
            )
            self.assertEqual(palette["colourId"], [7, 7, 19][i])
        shadow = native["shadow"]
        self.assertEqual(
            (shadow["triangles"], shadow["quads"], shadow["scale"]), (1, 1, 18)
        )
        self.assertEqual(shadow["boundsMin"], [-500, 0, -600, 1])
        self.assertEqual(shadow["boundsMax"], [500, 0, 600, 2])
        self.assertEqual(shadow["unknownWord"], 0x3456)
        positions = list(
            struct.iter_unpack("<4h", source_bytes(doc, binary, shadow["records"]))
        )
        self.assertEqual(
            positions, [(i * 100, -i * 50, i * 10, 1000 + i) for i in range(7)]
        )
        self.assertEqual(shadow["records"]["count"], 7)
        # Source shadows are retained without adding them to the visible scene.
        self.assertEqual(len(doc["scenes"]), 1)
        self.assertEqual(len(doc["meshes"]), 5)
        self.assertEqual(len(doc["scenes"][0]["nodes"]), 5)

    def test_every_material_variant_decodes_native_palette_pixels(self):
        metadata = {
            "colour_variants": [
                {"index": i, "colour_id": cid, "name": "Blue", "label": "Blue"}
                for i, cid in enumerate([7, 7, 19])
            ],
            "evidence": {"source": "fixture"},
        }
        doc, binary = self.build(metadata)
        self.assertEqual(doc["extras"]["nativeMetadata"], metadata)
        variants = doc["extensions"]["KHR_materials_variants"]["variants"]
        self.assertEqual(len(variants), 3)
        self.assertEqual(len({v["name"] for v in variants}), 3)
        self.assertTrue(
            all(
                f"ID {cid}" in variants[i]["name"] and f"set {i}" in variants[i]["name"]
                for i, cid in enumerate([7, 7, 19])
            )
        )
        checked = set()
        native_tex = tex_fixture()
        for mesh in doc["meshes"]:
            for primitive in mesh["primitives"]:
                default = doc["materials"][primitive["material"]]
                if "TEXCOORD_0" not in primitive["attributes"]:
                    self.assertNotIn("extensions", primitive)
                    continue
                self.assertEqual(default["extras"]["nativeColourSet"], 0)
                mappings = primitive["extensions"]["KHR_materials_variants"]["mappings"]
                self.assertEqual([m["variants"] for m in mappings], [[0], [1], [2]])
                for i, mapping in enumerate(mappings):
                    material = doc["materials"][mapping["material"]]
                    clut = material["extras"]["nativeCLUT"]
                    self.assertEqual(material["extras"]["nativeColourSet"], i)
                    self.assertEqual(
                        material["extras"]["nativeColourId"], [7, 7, 19][i]
                    )
                    if (i, clut) in checked:
                        continue
                    checked.add((i, clut))
                    texture = material["pbrMetallicRoughness"]["baseColorTexture"][
                        "index"
                    ]
                    image = doc["images"][doc["textures"][texture]["source"]]
                    width, height, rgba = decode_png(
                        buffer_view(doc, binary, image["bufferView"])
                    )
                    self.assertEqual((width, height), (256, 256))
                    words = struct.unpack_from(
                        "<16H", native_tex, 0x8060 + 512 * i + 32 * clut
                    )
                    entries = [
                        bytes(
                            [
                                (w & 31) * 8,
                                ((w >> 5) & 31) * 8,
                                ((w >> 10) & 31) * 8,
                                0 if w == 0 else 255,
                            ]
                        )
                        for w in words
                    ]
                    expected = b"".join(
                        entries[index]
                        for byte in native_tex[96:0x8060]
                        for index in (byte & 15, byte >> 4)
                    )
                    self.assertEqual(bytes(rgba), expected)
        self.assertEqual(
            checked, {(colour, clut) for colour in range(3) for clut in range(2)}
        )

    def test_face_packet_ownership_flags_original_normals_and_triangle_mapping(self):
        doc, binary = self.build()
        native = doc["extras"]["nativeData"]["lods"][0]
        self.assertEqual(native["threshold"], 0x90000)
        self.assertEqual(
            source_bytes(doc, binary, native["thresholdSource"]),
            struct.pack("<II", 0x90000, 0xDEADBEEF),
        )
        self.assertEqual(native["boundsMin"], [-9, -8, -7, 123])
        self.assertEqual(native["boundsMax"], [4096, 4096, 7, -123])
        self.assertEqual(native["unknownWord"], 0x2345)
        self.assertEqual(native["groupCounts"], [1, 0, 0, 0, 1, 1, 0, 0])
        raw_vertices = list(
            struct.iter_unpack("<4h", source_bytes(doc, binary, native["vertices"]))
        )
        raw_normals = list(
            struct.iter_unpack("<4h", source_bytes(doc, binary, native["normals"]))
        )
        self.assertEqual(raw_normals, [(0, 0, -4096, 99), (0, 4096, 0, -7)])
        body = doc["meshes"][doc["nodes"][doc["scenes"][0]["nodes"][0]]["mesh"]]
        offsets = []
        repaired = []
        for primitive in body["primitives"]:
            points = accessor(doc, binary, primitive["attributes"]["POSITION"])
            indices = accessor(doc, binary, primitive["indices"])
            for face in primitive["extras"]["nativeFaces"]:
                offsets.append(face["sourceOffset"])
                repaired.append(face["normalRepaired"])
                raw = car_fixture()[
                    face["sourceOffset"] : face["sourceOffset"]
                    + face["sourceByteLength"]
                ]
                self.assertEqual(
                    face["sourceByteLength"], 16 if face["group"] == 0 else 28
                )
                w0, w1, _, colour = struct.unpack_from("<4I", raw)
                self.assertEqual(face["flags"], [w0 & 0xF8000000, w1 & 0x80000000])
                self.assertEqual(face["type"], colour >> 24)
                self.assertEqual(
                    face["colour"],
                    [colour & 255, (colour >> 8) & 255, (colour >> 16) & 255],
                )
                self.assertEqual(
                    face["rawCLUT"],
                    None
                    if face["group"] == 0
                    else struct.unpack_from("<H", raw, 18)[0],
                )
                base = face["firstVertex"]
                for corner, reference in enumerate(face["vertexIndices"]):
                    x, y, z, _ = raw_vertices[reference]
                    self.assertEqual(
                        points[(base + corner) * 3 : (base + corner + 1) * 3],
                        (x / 4096, y / 4096, -z / 4096),
                    )
                corner_triangles = (
                    [(0, 1, 2), (0, 2, 3)]
                    if len(face["vertexIndices"]) == 4
                    else [(0, 1, 2)]
                )
                expected = []
                for a, b, c in corner_triangles:
                    expected.extend(
                        [base + a, base + c, base + b]
                        if face["reversed"]
                        else [base + a, base + b, base + c]
                    )
                start = face["firstTriangle"] * 3
                self.assertEqual(
                    indices[start : start + face["triangleCount"] * 3], tuple(expected)
                )
                self.assertEqual(
                    face["normalIndices"],
                    [1, 1, 1]
                    if face["group"] == 0
                    else [0] * len(face["vertexIndices"]),
                )
        self.assertEqual(len(set(offsets)), 3)
        self.assertIn(True, repaired)

    def test_all_wheel_templates_and_exact_odd_width_pivots_retained(self):
        doc, binary = self.build()
        templates = doc["extras"]["nativeData"]["wheelTemplates"]["tables"]
        source = json.loads(
            (
                ROOT / "research/evidence/gran-turismo-wheels/native-wheel-tables.json"
            ).read_text()
        )
        self.assertEqual([t["quadCount"] for t in templates], [31, 23, 15, 11, 1])
        self.assertEqual(
            [t["address"] for t in templates],
            [0x800970D0, 0x80096DEC, 0x80096C08, 0x80096AA4, 0x80096A80],
        )
        for output, original in zip(templates, source["tables"]):
            raw = buffer_view(doc, binary, output["bufferView"])
            self.assertEqual(raw, base64.b64decode(original["base64"]))
            self.assertEqual(output["sha256"], sha(raw))
            self.assertEqual(output["byteLength"], len(raw))
        wheel_nodes = [
            n for n in doc["nodes"] if "nativeWheelIndex" in n.get("extras", {})
        ]
        self.assertEqual(
            [n["extras"]["nativePivotPosition"] for n in wheel_nodes],
            [
                [756, 1200, 100],
                [2743, 1200, 100],
                [628, 1200, -100],
                [2871, 1200, -100],
            ],
        )
        for node in wheel_nodes:
            x, y, z = node["extras"]["nativePivotPosition"]
            self.assertEqual(
                node["extras"]["nativePivotPositionMetres"],
                [x / 4096, y / 4096, -z / 4096],
            )
            self.assertFalse(
                any(k in node for k in ("translation", "rotation", "scale", "matrix"))
            )
        self.assertNotIn("animations", doc)

    def test_duplicate_palette_images_are_shared_without_collapsing_variants(self):
        doc, _ = self.build(duplicate=True)
        self.assertEqual(
            len(doc["extensions"]["KHR_materials_variants"]["variants"]), 3
        )
        self.assertEqual(len(doc["materials"]), 7)
        self.assertEqual(len(doc["images"]), 2)
        self.assertEqual(len(doc["textures"]), 2)

    def test_unsupported_groups_and_malformed_native_data_are_rejected(self):
        for offset in (144, 146):
            bad = bytearray(car_fixture())
            struct.pack_into("<H", bad, offset, 1)
            with (
                self.subTest(offset=offset),
                self.assertRaisesRegex(ValueError, "Unsupported.*Gouraud"),
            ):
                parse_car(bytes(bad))
        shadow_offset = parse_car(car_fixture())["shadow"]["offset"]
        for offset, value in ((shadow_offset, 8193), (shadow_offset + 4, 31)):
            bad = bytearray(car_fixture())
            struct.pack_into("<H", bad, offset, value)
            with (
                self.subTest(offset=offset),
                self.assertRaisesRegex(ValueError, "shadow count/scale"),
            ):
                parse_car(bytes(bad))
        with self.assertRaisesRegex(ValueError, "Truncated"):
            parse_car(car_fixture()[: shadow_offset + 32 + 55])
        valid = [{"index": i, "colour_id": cid} for i, cid in enumerate([7, 7, 19])]
        for variants in (
            valid[:-1],
            list(reversed(valid)),
            [{**valid[0], "colour_id": 8}, *valid[1:]],
            [{**valid[0], "index": False}, *valid[1:]],
            [{**valid[0], "label": 12}, *valid[1:]],
        ):
            with (
                self.subTest(variants=variants),
                self.assertRaisesRegex(ValueError, "GT colour variant"),
            ):
                self.build({"colour_variants": variants})
        with self.assertRaisesRegex(ValueError, "metadata must be an object"):
            self.build([])
        with self.assertRaisesRegex(ValueError, "Out of range float"):
            self.build({"value": float("nan")})


if __name__ == "__main__":
    unittest.main(verbosity=2)
