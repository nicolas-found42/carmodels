"""Localization parsing and source identity controls on an independent synthetic table."""

import hashlib
import json
from pathlib import Path
import struct
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

import mcla_names as names
from mcla_rpf import jenkins

CODE = "vp_aud_rs4_07"


def build(keys=None, texts=None):
    keys = keys or [CODE, CODE + "_shrt", "pinkslip_" + CODE]
    texts = texts or ["2008 RS4 ", "08 RS4", "JIN'S AUDI RS4"]
    key_data = b"".join(
        struct.pack("<I", len(key)) + key.encode() + b"\0" for key in keys
    )
    records = []
    for key, text in zip(keys, texts):
        encoded = (text + "\0").encode("utf-16le")
        records.append(
            struct.pack("<IHI", jenkins(key), 1, 6)
            + b"nofont"
            + struct.pack("<I", len(encoded) // 2)
            + encoded
            + struct.pack("<ffH", 1, 1, 0)
        )
    language = struct.pack("<I", len(keys)) + b"".join(records)
    start = names.HEADER_BYTES + len(key_data)
    end = start + len(language)
    return (
        struct.pack("<12I", 11, start, *([end] * 10))
        + struct.pack("<II", 512, len(keys))
        + key_data
        + language
    )


def mutate(data, offset, fmt, value):
    changed = bytearray(data)
    struct.pack_into("<" + fmt, changed, offset, value)
    return changed


class NamesTests(unittest.TestCase):
    def setUp(self):
        self.data = build()
        (self.start,) = struct.unpack_from("<I", self.data, 4)
        self.record = self.start + 4

    def rejects(self, data, reason):
        with self.assertRaisesRegex(names.NamesError, reason):
            names.parse(data)

    def test_exact_key_and_source_whitespace(self):
        table = names.parse(self.data)
        self.assertEqual(len(table["keys"]), 3)
        self.assertEqual(list(table["languages"]), [0])
        row = names.display_identity(table, CODE)
        self.assertEqual(row["name"], "2008 RS4")
        self.assertEqual(row["name_source"]["text"], "2008 RS4 ")
        self.assertEqual(row["name_source"]["hash"], jenkins(CODE))
        self.assertEqual(row["name_source"]["offset"], self.record)
        self.assertEqual((row["manufacturer"], row["year"]), ("Unknown", None))

    def test_missing_key_never_selects_short_or_pinkslip(self):
        table = names.parse(
            build([CODE + "_shrt", "pinkslip_" + CODE], ["08 RS4", "JIN'S AUDI RS4"])
        )
        self.assertEqual(names.display_identity(table, CODE)["name"], CODE)

    def test_hash_only_collision_never_names_car(self):
        table = names.parse(self.data)
        table["languages"][0][jenkins(CODE)]["key"] = "another_vehicle"
        self.assertEqual(
            names.display_identity(table, CODE)["name_source"]["kind"], "code-fallback"
        )

    def test_empty_display_falls_back(self):
        table = names.parse(build([CODE], ["  "]))
        self.assertEqual(names.display_identity(table, CODE)["name"], CODE)

    def test_unicode_little_endian(self):
        table = names.parse(build([CODE], ["日本語 Š 🚗"]))
        self.assertEqual(names.display_identity(table, CODE)["name"], "日本語 Š 🚗")

    def test_source_pin_and_fallback(self):
        with self.assertRaisesRegex(names.NamesError, "source digest mismatch"):
            names.decode_source(self.data)
        with (
            patch.object(names, "SOURCE_BYTES", len(self.data)),
            patch.object(names, "SOURCE_SHA256", hashlib.sha256(self.data).hexdigest()),
        ):
            identities = names.identities_for([CODE, "va_unknown"], self.data)
            self.assertEqual(identities[CODE]["name"], "2008 RS4")
            receipt = names.derive([CODE, "va_unknown"], self.data)
            self.assertEqual(
                receipt["coverage"],
                {"vehicles": 2, "ui_strings": 1, "code_fallbacks": 1},
            )
        self.assertEqual(names.identities_for([CODE])[CODE]["name"], CODE)

    def test_duplicate_and_invalid_codes(self):
        with self.assertRaisesRegex(names.NamesError, "duplicate MCLA"):
            names.identities_for([CODE, CODE])
        for code in ["../vp_car", "VP_CAR", "vp_", "not_vehicle"]:
            with self.assertRaisesRegex(names.NamesError, "invalid MCLA vehicle"):
                names.identities_for([code])

    def test_version_header_and_offsets(self):
        self.rejects(b"", "header truncated")
        self.rejects(mutate(self.data, 0, "I", 10), "unsupported localization version")
        self.rejects(mutate(self.data, 48, "I", 0), "header flags")
        self.rejects(mutate(self.data, 52, "I", 0), "key count")
        self.rejects(mutate(self.data, 4, "I", len(self.data)), "first section outside")
        self.rejects(mutate(self.data, 44, "I", len(self.data) - 1), "section offsets")
        self.rejects(mutate(self.data, 8, "I", self.start - 1), "section offsets")

    def test_key_encoding_length_terminator_and_trailer(self):
        self.rejects(mutate(self.data, 56, "I", 5000), "key length")
        self.rejects(mutate(self.data, 60, "B", 255), "text encoding")
        self.rejects(mutate(self.data, 60 + len(CODE), "B", 65), "key terminator")
        self.rejects(mutate(self.data, 52, "I", 2), "trailing localization key")
        self.rejects(build([CODE, CODE], ["A", "B"]), "duplicate localization key")

    def test_language_count_hash_and_duplicate(self):
        self.rejects(
            mutate(self.data, self.start, "I", 2), "language/key count mismatch"
        )
        self.rejects(mutate(self.data, self.record, "I", 0), "no source key")
        text = "2008 RS4 "
        next_record = self.record + 30 + 2 * (len(text) + 1)
        self.rejects(
            mutate(self.data, next_record, "I", jenkins(CODE)),
            "duplicate localization record",
        )

    def test_font_flags_lengths_and_text(self):
        self.rejects(mutate(self.data, self.record + 4, "H", 2), "entry flags")
        self.rejects(mutate(self.data, self.record + 6, "I", 1025), "font length")
        self.rejects(mutate(self.data, self.record + 10, "B", 0), "font terminator")
        self.rejects(mutate(self.data, self.record + 10, "B", 255), "text encoding")
        self.rejects(mutate(self.data, self.record + 16, "I", 0), "text length")
        self.rejects(
            mutate(self.data, self.record + 16, "I", names.MAX_TEXT_UNITS),
            "outside section",
        )
        self.rejects(mutate(self.data, self.record + 20, "H", 0xD800), "text encoding")
        self.rejects(mutate(self.data, self.record + 20, "H", 0), "text terminator")
        null = self.record + 20 + 2 * len("2008 RS4 ")
        self.rejects(mutate(self.data, null, "H", 65), "text terminator")
        self.rejects(mutate(self.data, null + 2, "f", 2), "record trailer")

    def test_section_bounds_and_absent_english(self):
        self.rejects(self.data[:-1], "section offsets")
        data = self.data + b"!"
        # Extra byte is inside the sole language section, not an unparsed tail.
        for i in range(2, 12):
            data = mutate(data, i * 4, "I", len(data))
        self.rejects(data, "trailing localization language")
        self.rejects(
            mutate(self.data, 8, "I", self.start),
            "English localization section missing",
        )

    def test_cli_reproduces_and_rejects_changed_receipt(self):
        with tempfile.TemporaryDirectory() as temporary:
            base = Path(temporary)
            table, index, receipt = (
                base / "table.bin",
                base / "index.json",
                base / "receipt.json",
            )
            table.write_bytes(self.data)
            index.write_text(json.dumps({"vehicles": [{"id": CODE}]}))
            args = [
                "--table",
                str(table),
                "--index",
                str(index),
                "--receipt",
                str(receipt),
            ]
            with (
                patch.object(names, "ROOT", base),
                patch.object(names, "SOURCE_BYTES", len(self.data)),
                patch.object(
                    names, "SOURCE_SHA256", hashlib.sha256(self.data).hexdigest()
                ),
            ):
                self.assertEqual(names.main([*args, "--write"]), 0)
                self.assertEqual(names.main(args), 0)
                receipt.write_text("{}")
                self.assertEqual(names.main(args), 1)

    def test_disc_hash_lookup_duplicate_and_failure_controls(self):
        import extract_mcla_cars
        import mcla_rpf
        import xdvdfs
        import xex2

        closed = []
        disc = SimpleNamespace(
            entries=[
                {"path": "default.xex", "size": 1},
                {"path": "xarchive_cache.rpf", "size": 1},
            ],
            region=lambda entry: lambda start, size: b"x",
            close=lambda: closed.append(True),
        )
        members = [
            {
                "kind": "file",
                "resource": False,
                "hash": names.SOURCE_HASH,
                "index": index,
            }
            for index in (0, 1)
        ]
        payloads = {0: self.data, 1: self.data}
        archive = SimpleNamespace(
            entries=members, payload=lambda entry: payloads[entry["index"]]
        )
        with (
            patch.object(xdvdfs, "XdvdfsDisc", return_value=disc),
            patch.object(xex2, "load_image", return_value=(b"image", {})),
            patch.object(
                extract_mcla_cars, "locate_key", return_value=(b"not-real-key", 0)
            ),
            patch.object(mcla_rpf, "Rpf3Archive", return_value=archive),
            patch.object(names, "SOURCE_BYTES", len(self.data)),
            patch.object(names, "SOURCE_SHA256", hashlib.sha256(self.data).hexdigest()),
        ):
            self.assertEqual(names.load_from_disc("disc.iso"), self.data)
            payloads[1] = self.data + b"bad"
            with self.assertRaisesRegex(names.NamesError, "conflicting MCLA"):
                names.load_from_disc("disc.iso")
            payloads[0] = payloads[1] = b"bad"
            with self.assertRaisesRegex(names.NamesError, "source digest mismatch"):
                names.load_from_disc("disc.iso")
            members.clear()
            with self.assertRaisesRegex(names.NamesError, "archive member missing"):
                names.load_from_disc("disc.iso")
            disc.entries.clear()
            with self.assertRaisesRegex(names.NamesError, "executable/cache missing"):
                names.load_from_disc("disc.iso")
        self.assertEqual(len(closed), 5)


if __name__ == "__main__":
    unittest.main(verbosity=2)
