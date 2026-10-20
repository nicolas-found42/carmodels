"""GT4 SpecDB decoding: joins and values pinned on the committed spec database, plus controls."""

import json
from pathlib import Path
import shutil
import tempfile
import unittest

from gt4_specdb import Table, car_specs, strings

ROOT = Path(__file__).resolve().parents[1]
SPECDB = ROOT / "games/gran-turismo-4/cars/provenance/specdb/GT4_EU2560"


class SpecTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.specs = car_specs(SPECDB)

    def test_every_model_code_joins_once_with_a_name(self):
        # The committed extraction index lists every code; most car folders are local only.
        index = json.loads((ROOT / "games/gran-turismo-4/cars/index.json").read_text())
        codes = {vehicle["id"] for vehicle in index["vehicles"]}
        self.assertEqual(set(self.specs), codes)
        self.assertEqual(len(codes), 730)
        self.assertTrue(all(spec["name"] for spec in self.specs.values()))
        self.assertEqual(len({spec["label"] for spec in self.specs.values()}), 730)

    def test_pinned_cars(self):
        acura = self.specs["acra0001"]
        self.assertEqual(
            (acura["label"], acura["name"], acura["year"]),
            ("acura_cl_types_01", "Acura CL 3.2 Type-S `01", 2001),
        )
        self.assertEqual(
            (acura["wheelbase_mm"], acura["tread_mm"], acura["tire_pos_related_mm"]),
            (2715, [1769, 1764], [646, 699]),
        )
        self.assertEqual(
            acura["front_tire"], {"aspect": 50, "rim_inches": 17.0, "width_mm": 215}
        )
        self.assertEqual(
            (acura["ride_height_mm"], self.specs["ford0005"]["ride_height_mm"]),
            ([140, 140], [155, 155]),
        )
        self.assertEqual(self.specs["toyt0071"]["name"], "Toyota MR2 V Edition (J) `02")
        self.assertEqual(self.specs["chev0001"]["name"], "Chevrolet Camaro Z28 302 `69")
        # Rim bytes under 90 are whole inches (1886 cars only): 26" front, 41" rear.
        benz = self.specs["benz0001"]
        self.assertEqual(
            (benz["front_tire"]["rim_inches"], benz["rear_tire"]["rim_inches"]),
            (26, 41),
        )

    def test_factory_colours_retain_duplicate_native_row_ids(self):
        paints = self.specs["acra0001"]["factory_colours"]
        self.assertEqual(
            [paint["name"] for paint in paints],
            [
                "Sundance Gold",
                "San Marino Red",
                "Nighthawk Black Pearl",
                "Satin Silver Metallic",
                "Taffeta White",
            ],
        )
        self.assertEqual([paint["index"] for paint in paints], list(range(5)))
        self.assertEqual([paint["var_order"] for paint in paints], list(range(1, 6)))
        self.assertEqual({paint["variation_row_id"] for paint in paints}, {271})
        self.assertEqual(
            [paint["colour_chips"] for paint in paints],
            [
                [0x0319496F, 0, 0, 0],
                [0x03180D50, 0, 0, 0],
                [0x03080808, 0, 0, 0],
                [0x03828282, 0, 0, 0],
                [0x01B5B7B7, 0, 0, 0],
            ],
        )
        # Native two-tone/livery swatches retain every word; these are not collapsed
        # to a guessed single paint factor or discarded as zero-alpha pixels.
        two_tone = next(
            paint
            for paint in self.specs["toyt0001"]["factory_colours"]
            if paint["name"] == "High Flash Two-Tone"
        )
        self.assertEqual(two_tone["colour_chips"], [0x01160A5F, 0x010F0F0F, 0, 0])
        self.assertEqual(
            sum(len(spec["factory_colours"]) for spec in self.specs.values()), 3903
        )
        self.assertEqual(
            sum(
                bool(paint["name"].strip())
                for spec in self.specs.values()
                for paint in spec["factory_colours"]
            ),
            3597,
        )
        self.assertEqual(self.specs["peug0001"]["factory_colours"][0]["name"], "")

    def test_huffman_rows_against_uncompressed_reading(self):
        table = Table(SPECDB, "CAR_NAME_british")
        self.assertTrue(table.attribute & 1)
        text = strings(SPECDB / "british_StrDB.sdb")
        rows = table.by_label()
        self.assertEqual(len(rows), table.count)
        self.assertTrue(
            all(
                0 <= int.from_bytes(row[:4], "little") < len(text)
                for row in rows.values()
            )
        )

    def test_corrupt_tables_fail(self):
        with tempfile.TemporaryDirectory() as temp:
            folder = Path(temp)
            for name in ("CHASSIS.dbt", "CHASSIS.idi"):
                shutil.copy(SPECDB / name, folder / name)
            data = bytearray((folder / "CHASSIS.dbt").read_bytes())
            data[:4] = b"XXXX"
            (folder / "CHASSIS.dbt").write_bytes(bytes(data))
            with self.assertRaisesRegex(ValueError, "invalid SpecDB table"):
                Table(folder, "CHASSIS")
            data[:4] = b"GTDB"
            data[8:12] = (10**6).to_bytes(4, "little")
            (folder / "CHASSIS.dbt").write_bytes(bytes(data))
            with self.assertRaisesRegex(ValueError, "counts out of range"):
                Table(folder, "CHASSIS")
        with tempfile.TemporaryDirectory() as temp:
            bad = Path(temp) / "x.sdb"
            bad.write_bytes(b"NOPE" + bytes(12))
            with self.assertRaisesRegex(ValueError, "string table"):
                strings(bad)


if __name__ == "__main__":
    unittest.main()
