"""Acceptance-runner controls: partial reports and changed pilot bytes cannot pass."""

import copy
import hashlib
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import verify_inspection_browser as verifier


class BrowserEvidenceTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.asset = self.root / "pilot.glb"
        self.asset.write_bytes(b"pinned pilot input")
        self.pins = {
            "pilot": "gran-turismo-4/acra0001",
            "commit": "initial-pinned-commit",
            "files": {
                "pilot.glb": {
                    "sha256": hashlib.sha256(self.asset.read_bytes()).hexdigest()
                }
            },
        }
        self.report = {
            "checks": [
                {"name": name, "status": "pass"}
                for name in verifier.EXPECTED_CHECKS
            ]
        }
        self.root_patch = patch.object(verifier, "ROOT", self.root)
        self.root_patch.start()
        self.addCleanup(self.root_patch.stop)

    def finish(self, report=None, before=None):
        return verifier.finish_report(
            self.pins,
            before or verifier.hashes(self.pins),
            copy.deepcopy(self.report if report is None else report),
        )

    def test_complete_report_preserves_every_pin(self):
        result = self.finish()
        self.assertTrue(result["ok"])
        self.assertEqual(result["hashes_before"], result["hashes_after"])
        self.assertEqual(result["pinned_commit"], self.pins["commit"])

    def test_partial_duplicate_failed_and_skipped_reports_do_not_pass(self):
        for mode in ("empty", "partial", "duplicate", "fail", "skip"):
            with self.subTest(mode=mode):
                report = copy.deepcopy(self.report)
                if mode == "empty":
                    report["checks"] = []
                elif mode == "partial":
                    report["checks"].pop()
                elif mode == "duplicate":
                    report["checks"][-1] = report["checks"][0]
                else:
                    report["checks"][0]["status"] = mode
                self.assertFalse(self.finish(report)["ok"])

    def test_changed_pilot_bytes_fail_even_with_all_browser_assertions_passed(self):
        before = verifier.hashes(self.pins)
        self.asset.write_bytes(b"changed pilot input")
        result = self.finish(before=before)
        self.assertFalse(result["ok"])
        self.assertFalse(result["stored_assets_unchanged"])

    def test_missing_or_changed_start_input_blocks_before_server(self):
        pins = self.root / "pins.json"
        pins.write_text(json.dumps(self.pins))
        self.asset.write_bytes(b"changed")
        with self.assertRaisesRegex(ValueError, "Pilot inputs changed"):
            verifier.serve(pins, self.root / "result.json")
        self.asset.unlink()
        with self.assertRaises(FileNotFoundError):
            verifier.serve(pins, self.root / "result.json")

    def test_existing_evidence_cannot_be_replaced(self):
        pins = self.root / "pins.json"
        pins.write_text(json.dumps(self.pins))
        output = self.root / "result.json"
        output.write_text("old evidence")
        with self.assertRaisesRegex(ValueError, "new browser evidence"):
            verifier.serve(pins, output)
        self.assertEqual(output.read_text(), "old evidence")


if __name__ == "__main__":
    unittest.main(verbosity=2)
