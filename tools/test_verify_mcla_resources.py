"""Full-disc decompression verifier on a synthetic encrypted disc whose resources are real LZX streams."""

import hashlib
import io
import json
from pathlib import Path
import struct
import tempfile
import unittest
from contextlib import redirect_stdout
from unittest.mock import patch

import extract_mcla_cars
from test_extract_mcla_cars import KEY, PIN
from test_mcla_lzx import Encoder, pattern, resource
from test_mcla_rpf import rpf_fixture
from test_xdvdfs import disc_fixture
from test_xex2 import pe_image, xex_fixture
import verify_mcla_resources
from verify_mcla_resources import VerifyError, derive, main


def lzx(kind, size, seed):
    encoder = Encoder()
    encoder.block(list(pattern(size - 40, seed)) + [("m", 40, 30)])
    return entry(kind, resource(encoder.body(), size, kind=kind))


def stored(kind, size, seed):
    encoder = Encoder()
    encoder.stored(bytes(pattern(size, seed)))
    return entry(kind, resource(encoder.body(), size, kind=kind))


def entry(kind, data):
    """An archive resource entry whose flag word repeats the RSC5 header's."""
    return ("resource", kind, data, struct.unpack_from(">I", data, 8)[0] & 0x3FFFFFFF)


def disc(path, tree):
    files = [
        ("default.xex", xex_fixture(pe_image(KEY))),
        ("xarchive_cache.rpf", rpf_fixture(tree, KEY)),
    ]
    path.write_bytes(disc_fixture(files))
    return path


def tree(extra=None):
    out = {
        "resources": {
            "vehicle": {
                "vp_a": {
                    "vp_a.xspm": lzx(19, 512, 1),
                    "body_lod_0.xrsc": lzx(63, 1024, 2),
                    "big.xtp": stored(83, 70000 // 256 * 256, 3),
                }
            }
        },
        "preload": {
            "inner.rpf": ("loose", rpf_fixture({"x.xml": ("loose", b"x")}, KEY))
        },
    }
    out["resources"]["vehicle"]["vp_a"].update(extra or {})
    return out


class ResourceVerifier(unittest.TestCase):
    def setUp(self):
        pin = patch.object(extract_mcla_cars, "KEY_SHA256", PIN)
        pin.start()
        self.addCleanup(pin.stop)
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.root = Path(temp.name)

    def pinned(self, iso):
        index = self.root / "index.json"
        index.write_text(
            json.dumps(
                {
                    "source": {
                        "file": iso.name,
                        "sha256": hashlib.sha256(iso.read_bytes()).hexdigest(),
                    }
                }
            )
        )
        for name, value in (
            ("INDEX", index),
            ("RECEIPT", self.root / "receipt.json"),
            ("ROOT", self.root),
        ):
            p = patch.object(verify_mcla_resources, name, value)
            p.start()
            self.addCleanup(p.stop)

    def test_receipt_facts_and_controls(self):
        iso = disc(self.root / "disc.iso", tree())
        self.pinned(iso)
        receipt = derive(iso, 1)
        cache = receipt["archives"]["xarchive_cache.rpf"]
        self.assertEqual(
            (cache["resources"], cache["output_bytes"]), (3, 512 + 1024 + 69888)
        )
        self.assertGreater(cache["chunks"], 3)  # the stored pack spans three frames
        self.assertEqual(
            receipt["by_type"],
            {
                "19": {"resources": 1, "output_bytes": 512},
                "63": {"resources": 1, "output_bytes": 1024},
                "83": {"resources": 1, "output_bytes": 69888},
            },
        )
        self.assertEqual(receipt["nested_archives"][0]["resources"], 0)
        self.assertEqual(receipt["header_constant"], "0x0ff512ef")
        reasons = {c["mutation"]: c["reason"] for c in receipt["controls"]["results"]}
        self.assertEqual(len(reasons), 7)
        self.assertIn(
            "truncated",
            reasons[
                "truncated stream (last 4 bytes of the chunk removed, lengths adjusted)"
            ],
        )
        self.assertIn("block type", reasons["flipped block-type bit"])
        self.assertIn("tree", reasons["window 2**16 instead of 2**17"])

    def test_main_writes_then_reproduces_and_parallel_matches(self):
        iso = disc(self.root / "disc.iso", tree())
        self.pinned(iso)
        with redirect_stdout(io.StringIO()):
            self.assertEqual(main(["--iso=" + str(iso), "--write", "--processes=1"]), 0)
            self.assertEqual(main(["--iso=" + str(iso), "--processes=2"]), 0)
            receipt = self.root / "receipt.json"
            receipt.write_text(receipt.read_text().replace("0x0ff512ef", "0x00000000"))
            self.assertEqual(main(["--iso=" + str(iso), "--processes=1"]), 1)
        self.assertEqual(main(["--available", "--iso=" + str(iso)]), 0)
        self.assertEqual(
            main(["--available", "--iso=" + str(self.root / "absent.iso")]), 1
        )
        out = io.StringIO()
        with redirect_stdout(out):
            self.assertEqual(main(["--iso=" + str(self.root / "absent.iso")]), 1)
        self.assertIn("MISSING INPUT", out.getvalue())

    def test_rejections(self):
        iso = disc(self.root / "disc.iso", tree())
        self.pinned(iso)
        other = disc(self.root / "other.iso", tree({"extra.xrsc": lzx(63, 256, 9)}))
        with self.assertRaisesRegex(VerifyError, "differs from the pinned"):
            derive(other, 1)
        broken = bytearray(lzx(63, 1024, 2)[2])
        broken[26] ^= 0x40
        bad = disc(
            self.root / "bad.iso", tree({"body_lod_0.xrsc": entry(63, bytes(broken))})
        )
        self.pinned(bad)
        out = io.StringIO()
        with redirect_stdout(out):
            self.assertEqual(main(["--iso=" + str(bad), "--processes=1"]), 1)
        self.assertIn("failed to decompress", out.getvalue())

    def test_summary_checks(self):
        row = {
            "archive": "a.rpf",
            "entry": 1,
            "type": 63,
            "flag_matches": True,
            "type_matches": True,
            "constant": 0x0FF512EF,
            "chunks": 1,
            "stored": 4,
            "bytes": 8,
            "sha256": "0" * 64,
        }
        for change, message in (
            ({"flag_matches": False}, "flag differs"),
            ({"type_matches": False}, "type differs"),
            ({"constant": 1}, "header constant"),
        ):
            with self.subTest(message), self.assertRaisesRegex(VerifyError, message):
                verify_mcla_resources.summarise([dict(row, **change)], [])

    def test_control_escapes_and_wrong_reasons_are_reported(self):
        encoder = Encoder()
        encoder.block(list(pattern(472, 1)) + [("m", 40, 30)])
        data = resource(encoder.body(), 512, kind=19)
        digest = hashlib.sha256(bytes(encoder.output)).hexdigest()
        with patch.object(
            verify_mcla_resources, "decompress", lambda *_, **__: (b"", {})
        ):
            with self.assertRaisesRegex(VerifyError, "escaped"):
                verify_mcla_resources.run_controls(data, digest)
        two = resource(encoder.body() + encoder.body(), 1024, kind=19)
        with self.assertRaisesRegex(VerifyError, "single chunk"):
            verify_mcla_resources.run_controls(two, digest)

        def wrong(*_, **__):
            raise verify_mcla_resources.LzxError("unrelated")

        with patch.object(verify_mcla_resources, "decompress", wrong):
            with self.assertRaisesRegex(VerifyError, "another reason"):
                verify_mcla_resources.run_controls(data, digest)


if __name__ == "__main__":
    unittest.main(verbosity=2)
