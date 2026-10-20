"""Native ambient paint XML, weighted choices and isolated material bindings."""

import copy
import unittest

from gt4_glb import Builder
from mcla_paint import PaintError, apply, decode, game_paint

XML = (
    b'<mcAmbientCarTypeColor><vColors content="vector3_array">1 1 1\n0.2 0 0\n1 1 1</vColors>'
    b'<fScale value="1"/><iPaintType value="2"/></mcAmbientCarTypeColor>'
)


class Paints(unittest.TestCase):
    def test_order_duplicates_and_native_type_are_preserved(self):
        palette = decode(XML)
        self.assertEqual(palette["rows"], [[1, 1, 1], [0.2, 0, 0], [1, 1, 1]])
        self.assertEqual(
            palette["choices"],
            [
                {"rgb": [1, 1, 1], "source_rows": [0, 2]},
                {"rgb": [0.2, 0, 0], "source_rows": [1]},
            ],
        )
        self.assertEqual((palette["scale"], palette["paint_type"]), (1, 2))

    def test_only_ambient_paint_primitives_switch_and_other_bindings_survive(self):
        builder = Builder()
        for name in ("AmbientCarPaint", "AmbientBumpSpec", "CarPaintCustomizable"):
            index = builder.material(name, [0.8, 0.8, 0.8, 1])
            builder.doc["materials"][index]["extras"] = {"sourceShader": name}
            if name != "AmbientCarPaint":
                builder.doc["materials"][index]["pbrMetallicRoughness"][
                    "baseColorTexture"
                ] = {"index": 3}
        before = copy.deepcopy(builder.doc["materials"])
        builder.doc["meshes"] = [
            {
                "primitives": [
                    {"material": index, "attributes": {"POSITION": 5}}
                    for index in range(3)
                ]
            }
        ]
        self.assertEqual(apply(builder, decode(XML)), 2)
        self.assertEqual(builder.doc["materials"][1:3], before[1:3])
        p = builder.doc["meshes"][0]["primitives"]
        self.assertNotIn("extensions", p[1])
        self.assertNotIn("extensions", p[2])
        mappings = p[0]["extensions"]["KHR_materials_variants"]["mappings"]
        self.assertEqual(
            mappings,
            [{"material": 0, "variants": [0]}, {"material": 3, "variants": [1]}],
        )
        self.assertEqual(
            builder.doc["materials"][3]["pbrMetallicRoughness"]["baseColorFactor"],
            [0.2, 0, 0, 1],
        )
        self.assertNotIn(
            "baseColorTexture", builder.doc["materials"][3]["pbrMetallicRoughness"]
        )
        self.assertEqual(p[0]["attributes"], {"POSITION": 5})

    def test_missing_paint_shader_does_not_create_misleading_variants(self):
        builder = Builder()
        builder.material("trim", [0.8, 0.8, 0.8, 1])
        self.assertEqual(apply(builder, decode(XML)), 0)
        self.assertNotIn("extensions", builder.doc)

    def test_metadata_keeps_provenance_and_channels_without_palette(self):
        builder = Builder()
        builder.material("body", [0.8, 0.8, 0.8, 1])
        builder.doc["materials"][0]["extras"] = {"sourceShader": "AmbientCarPaint"}
        builder.doc["meshes"] = [{"primitives": [{"material": 0}]}]
        source = {
            "file": "shared/tune/ambients/traffic/va_test/mcambientcartypecolor.xml",
            "sha256": "a" * 64,
        }
        palette = decode(XML)
        record = game_paint(builder.doc, palette, source)
        self.assertEqual(
            record["channels"], [{"id": "body", "name": "Body paint", "materials": [0]}]
        )
        self.assertEqual([c["rgb"] for c in record["colors"]], [[1, 1, 1], [0.2, 0, 0]])
        self.assertIn(source["file"] + ":vColors[0]", record["colors"][0]["source"])
        self.assertEqual(record, game_paint(builder.doc, palette, source))
        self.assertEqual(game_paint(builder.doc)["channels"], record["channels"])
        self.assertEqual(game_paint(builder.doc)["colors"], [])
        with self.assertRaisesRegex(PaintError, "source identity missing"):
            game_paint(builder.doc, palette)
        for changed in (
            {**source, "file": ""},
            {**source, "file": "../va_test/mcambientcartypecolor.xml"},
            {**source, "sha256": "z" * 64},
        ):
            with self.assertRaisesRegex(PaintError, "source identity missing"):
                game_paint(builder.doc, palette, changed)
        # Palette availability cannot assert a paint region on an unrelated shader.
        builder.doc["materials"][0]["extras"]["sourceShader"] = "CarPaintCustomizable"
        unavailable = game_paint(builder.doc, palette, source)
        self.assertEqual(unavailable["channels"], [])
        self.assertEqual(unavailable["colors"], record["colors"])

    def test_textured_blended_unused_paint_is_unavailable_without_mask_evidence(self):
        for mutation in ("textured", "blended", "unused"):
            with self.subTest(mutation=mutation):
                builder = Builder()
                builder.material("body", [0.8, 0.8, 0.8, 1])
                builder.doc["materials"][0]["extras"] = {
                    "sourceShader": "AmbientCarPaint"
                }
                builder.doc["meshes"] = [{"primitives": [{"material": 0}]}]
                if mutation == "textured":
                    builder.doc["materials"][0]["pbrMetallicRoughness"][
                        "baseColorTexture"
                    ] = {"index": 0}
                elif mutation == "blended":
                    builder.doc["materials"][0]["alphaMode"] = "BLEND"
                else:
                    builder.doc["meshes"] = []
                before = copy.deepcopy(builder.doc)
                self.assertEqual(apply(builder, decode(XML)), 0)
                self.assertEqual(builder.doc, before)
                self.assertEqual(game_paint(builder.doc)["channels"], [])

    def test_rejects_malformed_or_unsupported_source(self):
        for old, new, reason in (
            (b"1 1 1\n0.2 0 0\n1 1 1", b"", "RGB rows"),
            (b"0.2 0 0", b"0.2 0", "RGB rows"),
            (b"0.2 0 0", b"nan 0 0", "RGB rows"),
            (b"0.2 0 0", b"1.2 0 0", "RGB rows"),
            (b'value="1"', b'value="0.5"', "scale/type"),
            (b'value="2"', b'value="-1"', "scale/type"),
            (b"vector3_array", b"float_array", "attributes"),
            (
                b'<fScale value="1"/>',
                b'<fScale value="1"/><fScale value="1"/>',
                "fields",
            ),
            (b"mcAmbientCarTypeColor", b"Other", "fields"),
        ):
            with (
                self.subTest(reason=reason),
                self.assertRaisesRegex(PaintError, reason),
            ):
                decode(XML.replace(old, new))
        for data in (b"<", b"<!DOCTYPE p>" + XML, XML + b" " * 65536):
            with self.assertRaises(PaintError):
                decode(data)


if __name__ == "__main__":
    unittest.main(verbosity=2)
