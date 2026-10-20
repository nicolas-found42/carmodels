"""Raw rename/untracked diffs, budget controls and fail-closed review resolution."""

import json
from pathlib import Path
import tempfile
import unittest

from unittest.mock import patch

import review_payload
from review_payload import (
    MAX_FILE_CHARS,
    MAX_FILES,
    diff_path,
    digest,
    prepare,
    raw_diffs,
    review_status,
    scope_facts,
    snapshot,
)


class ReviewPayloadTests(unittest.TestCase):
    def test_raw_scope_and_bounded_calls(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            (root / "old.py").write_text("def f():\n    return 1\n")
            baseline = snapshot(root, ["old.py", "new.py", "untracked.py"])
            (root / "old.py").rename(root / "new.py")
            (root / "new.py").write_text("def f():\n    return 2\n")
            (root / "untracked.py").write_text('print("new")\n')
            diffs = raw_diffs(baseline, root)
            self.assertTrue(
                any(
                    "--- a/old.py\n+++ b/new.py" in d and "-    return 1" in d
                    for d in diffs
                )
            )
            self.assertTrue(any("+++ b/untracked.py" in d for d in diffs))
            checks = root / "checks"
            checks.mkdir()
            (checks / "test.log").write_text("full beginning\nfull ending\n")
            (checks / "results.json").write_text(
                json.dumps(
                    {
                        "schema": 1,
                        "exit_code": 0,
                        "checks": [
                            {
                                "name": "test",
                                "command": ["test"],
                                "status": "pass",
                                "exit_code": 0,
                                "log": "test.log",
                            }
                        ],
                    }
                )
            )
            bundle = prepare(
                baseline,
                root,
                "Change return and add file",
                checks,
                ["one", "two", "three"],
                root / "review",
            )
            self.assertEqual(
                [c["tool"] for c in bundle["calls"]],
                ["jev_review", "jev_verify", "jev_verify"],
            )
            self.assertIn(
                "full beginning\nfull ending",
                bundle["calls"][1]["args"]["evidence"][1]["text"],
            )
            self.assertTrue(
                bundle["calls"][1]["args"]["evidence"][0]["text"].startswith(
                    "CHECK SUMMARY 1 checks: 1 pass"
                )
            )
            self.assertEqual(
                review_status(bundle, "implementer")["status"],
                "blocked",
                "missing receipts cannot pass",
            )
            with self.assertRaisesRegex(ValueError, "previous judgments"):
                prepare(baseline, root, "request", checks, [], root / "review")
            (root / "untracked.py").write_text("x" * 2000)
            with self.assertRaisesRegex(ValueError, "never truncate"):
                prepare(
                    baseline,
                    root,
                    "request",
                    checks,
                    [],
                    root / "too-big",
                    max_diff_chars=1000,
                    per_file=False,
                )
            (root / "untracked.py").write_text("x" * (MAX_FILE_CHARS + 1))
            with self.assertRaisesRegex(ValueError, "never truncate"):
                prepare(baseline, root, "request", checks, [], root / "too-big-file")

    def test_per_file_review_sees_every_file_and_in_scope_logs(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            names = ["tools/a.py", "tools/test_a.py", "notes.md"]
            baseline = snapshot(root, names)
            (root / "tools").mkdir()
            for name in names:
                (root / name).write_text(name + "\n")
            checks = root / "checks"
            checks.mkdir()
            (checks / "a.log").write_text("test_one ... ok\nRan 1 test\nOK\n")
            (checks / "b.log").write_text("UNRELATED LOG\n")
            (checks / "results.json").write_text(
                json.dumps(
                    {
                        "schema": 1,
                        "exit_code": 0,
                        "checks": [
                            {
                                "name": "test_a",
                                "command": ["python3", "tools/test_a.py"],
                                "status": "pass",
                                "exit_code": 0,
                                "log": "a.log",
                            },
                            {
                                "name": "other",
                                "command": ["python3", "tools/other.py"],
                                "status": "skip",
                                "exit_code": 0,
                                "log": "b.log",
                            },
                        ],
                    }
                )
            )
            bundle = prepare(
                baseline,
                root,
                "request",
                checks,
                ["test_a passed", "every check passed"],
                root / "review",
            )
            self.assertEqual(bundle["mode"], "per-file")
            verify = bundle["calls"][1]["args"]["evidence"]
            self.assertIn("test_one ... ok", verify[1]["text"])
            self.assertNotIn(
                "UNRELATED LOG",
                verify[1]["text"],
                "a claim naming test_a gets only its log",
            )
            unnamed = prepare(
                baseline,
                root,
                "request",
                checks,
                ["every check passed"],
                root / "review-unnamed",
            )
            self.assertIn(
                "UNRELATED LOG", unnamed["calls"][1]["args"]["evidence"][1]["text"]
            )
            bundle["calls"] = bundle["calls"][:1]
            [call] = bundle["calls"]
            self.assertEqual([f["path"] for f in call["args"]["files"]], sorted(names))
            self.assertNotIn("diff", call["args"])
            tests = call["args"]["tests"]
            self.assertIn("CHECK SUMMARY 2 checks: 1 pass, 1 skip", tests)
            self.assertIn(
                "ADDED tools/a.py <- imported by: nothing in its directory", tests
            )
            self.assertIn("ADDED notes.md", tests)
            self.assertIn("SKIP other", tests)
            self.assertIn("test_one ... ok", tests)
            self.assertNotIn("UNRELATED LOG", tests)
            grouped = prepare(
                baseline, root, "request", checks, [], root / "grouped", per_file=False
            )
            self.assertEqual(
                (grouped["mode"], list(grouped["calls"][0]["args"])),
                ("grouped", ["request", "diff", "tests"]),
            )
            many = [f"f{i}.txt" for i in range(MAX_FILES + 1)]
            wide = snapshot(root, many)
            for name in many:
                (root / name).write_text("x\n")
            self.assertEqual(
                prepare(wide, root, "request", checks, [], root / "wide")["mode"],
                "grouped",
            )

    def test_input_rejections(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            with self.assertRaisesRegex(ValueError, "relative to the repository"):
                snapshot(root, ["/etc/passwd"])
            with self.assertRaisesRegex(ValueError, "relative to the repository"):
                snapshot(root, ["../outside.py"])
            with self.assertRaisesRegex(ValueError, "empty review baseline"):
                raw_diffs({"schema": 1, "files": {}}, root)
            (root / "gone.py").write_text(
                "def removed_helper():\n    return [1, 2, 3]\n"
            )
            baseline = snapshot(root, ["gone.py", "a.py", "b.py"])
            (root / "gone.py").unlink()
            (root / "a.py").write_text("a = 1\n")
            (root / "b.py").write_text("b = 2\n")
            deletion = next(
                d for d in raw_diffs(baseline, root) if "+++ /dev/null" in d
            )
            self.assertEqual(diff_path(deletion), "gone.py")
            (root / "c.py").write_text("import a\nfrom b import b\n")
            facts = scope_facts(
                {
                    "schema": 1,
                    "files": {
                        **baseline["files"],
                        "c.py": "import a\nfrom b import b\n",
                    },
                },
                root,
            )
            self.assertIn("DELETED gone.py", facts)
            self.assertIn("ADDED a.py <- imported by: c.py", facts)
            self.assertIn("ADDED b.py <- imported by: c.py", facts)
            self.assertNotIn("c.py <-", facts, "unchanged files are not listed")
            (root / "c.py").unlink()
            checks = root / "checks"
            checks.mkdir()
            (checks / "a.log").write_text("ok\n")
            manifest = {
                "schema": 1,
                "exit_code": 0,
                "checks": [
                    {
                        "name": "a",
                        "command": ["python3", "a.py"],
                        "status": "pass",
                        "exit_code": 0,
                        "log": "a.log",
                    }
                ],
            }
            (checks / "results.json").write_text(json.dumps(manifest))
            out = iter(range(100))

            def build(**changes):
                arguments = dict(
                    baseline=baseline,
                    root=root,
                    request="request",
                    checks_dir=checks,
                    claims=[],
                    output=root / f"review-{next(out)}",
                )
                arguments.update(changes)
                return prepare(**arguments)

            for changes, message in [
                ({"max_diff_chars": 999}, "Diff cap"),
                ({"request": " "}, "Request must be"),
                ({"claims": ["x" * 2001]}, "Each claim"),
                ({"baseline": snapshot(root, ["a.py"])}, "No patch changes"),
            ]:
                with self.subTest(message), self.assertRaisesRegex(ValueError, message):
                    build(**changes)
            grouped = build(per_file=False, max_diff_chars=1000)
            self.assertEqual(
                len([c for c in grouped["calls"] if c["tool"] == "jev_review"]), 1
            )
            (root / "b.py").write_text("b = 2\n" + "y = 0\n" * 120)
            self.assertEqual(
                len(
                    [
                        c
                        for c in build(per_file=False, max_diff_chars=1000)["calls"]
                        if c["tool"] == "jev_review"
                    ]
                ),
                2,
                "grouped mode splits at the cap",
            )
            with (
                patch.object(review_payload, "MAX_TESTS_CHARS", 10),
                self.assertRaisesRegex(ValueError, "never truncate logs"),
            ):
                build()
            for bad, message in [
                ({"schema": 2, "checks": manifest["checks"]}, "check manifest"),
                ({**manifest, "pending": ["still_running"]}, "pending checks"),
                (
                    {
                        **manifest,
                        "checks": [{**manifest["checks"][0], "log": "../a.log"}],
                    },
                    "evidence directory",
                ),
            ]:
                (checks / "results.json").write_text(json.dumps(bad))
                with self.subTest(message), self.assertRaisesRegex(ValueError, message):
                    build()
            (checks / "results.json").write_text(json.dumps(manifest))
            (checks / "a.log").write_text("z" * 195000)
            with (
                patch.object(review_payload, "MAX_TESTS_CHARS", 10**6),
                self.assertRaisesRegex(ValueError, "Evidence exceeds the budget"),
            ):
                build(claims=["one claim"])
            (checks / "a.log").write_text("z" * 95000)
            with (
                patch.object(review_payload, "MAX_TESTS_CHARS", 10**6),
                self.assertRaisesRegex(
                    ValueError,
                    "jev_review call exceeds 90000 characters; split the scope",
                ),
            ):
                build()

    def test_status_rejects_tampered_or_failed_receipts(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "review.json"
            calls = [{"tool": "jev_review", "args": {}, "out": str(path)}]
            bundle = {"calls": calls, "bundle_sha256": digest(calls)}
            with self.assertRaisesRegex(ValueError, "digest differs"):
                review_status({**bundle, "bundle_sha256": "0" * 64}, "author")
            scores = {
                k: {"score": 1, "confidence": 0.97}
                for k in ["correctness", "spec_match", "test_gap", "blast_radius"]
            }
            result = {
                "tool": "jev_review",
                "action": "auto",
                "safe_to_apply": 0.97,
                "scores": scores,
            }
            wrapped = {"content": [{"text": json.dumps(result)}]}
            path.write_text(json.dumps({"args": {}, "result": wrapped}))
            self.assertEqual(
                review_status(bundle, "author")["status"],
                "accepted",
                "MCP content envelopes are unwrapped",
            )
            for bad in [
                {**result, "tool": "jev_gate"},
                {**result, "action": "maybe"},
                {"isError": True},
            ]:
                path.write_text(json.dumps({"args": {}, "result": bad}))
                self.assertEqual(review_status(bundle, "author")["status"], "blocked")

    def test_per_file_status_requires_every_file(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "review.json"
            args = {
                "request": "r",
                "files": [{"path": "a.py", "diff": "d"}, {"path": "b.py", "diff": "d"}],
                "tests": "t",
            }
            calls = [{"tool": "jev_review", "args": args, "out": str(path)}]
            bundle = {"calls": calls, "bundle_sha256": digest(calls)}
            scores = {
                k: {"score": 1, "confidence": 0.97}
                for k in ["correctness", "spec_match", "test_gap", "blast_radius"]
            }
            files = [
                {"path": p, "action": "auto", "safe_to_apply": 0.97, "scores": scores}
                for p in ("a.py", "b.py")
            ]
            result = {
                "tool": "jev_review",
                "mode": "per-file",
                "action": "auto",
                "safe_to_apply": 0.97,
                "files": files,
            }

            def status():
                path.write_text(json.dumps({"args": args, "result": result}))
                return review_status(bundle, "author")

            self.assertEqual(status()["status"], "accepted")
            files[1]["action"], result["action"] = "escalate", "escalate"
            outcome = status()
            self.assertEqual(outcome["status"], "needs_independent_review")
            self.assertEqual(
                [f["path"] for f in outcome["unresolved"][0]["files"]], ["b.py"]
            )
            result["action"] = "auto"
            self.assertEqual(
                status()["status"],
                "blocked",
                "an auto aggregate cannot hide an unresolved file",
            )
            files[1]["action"] = "auto"
            result["files"] = files[:1]
            self.assertEqual(
                status()["status"],
                "blocked",
                "every reviewed file must be accounted for",
            )
            result["files"] = files
            files[1]["action"], result["action"] = "approved", "escalate"
            self.assertEqual(
                status()["status"],
                "blocked",
                "an invented per-file action cannot be resolved",
            )
            files[1]["action"], result["action"] = "auto", "auto"
            files[0]["scores"] = {}
            self.assertEqual(status()["status"], "blocked")

    def test_escalation_requires_independent_resolution(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "review.json"
            calls = [{"tool": "jev_review", "args": {}, "out": str(path)}]
            bundle = {"calls": calls, "bundle_sha256": digest(calls)}
            result = {
                "tool": "jev_review",
                "action": "escalate",
                "safe_to_apply": 0.58,
                "scores": {
                    k: {"score": 1, "confidence": 0.3}
                    for k in ["correctness", "spec_match", "test_gap", "blast_radius"]
                },
            }
            path.write_text(json.dumps({"args": {}, "result": result}))
            self.assertEqual(
                review_status(bundle, "author")["status"], "needs_independent_review"
            )
            resolution = {
                "bundle_sha256": bundle["bundle_sha256"],
                "reviewer": "author",
                "verdict": "approve",
                "rationale": "reviewed",
            }
            with self.assertRaisesRegex(ValueError, "independent"):
                review_status(bundle, "author", resolution)
            resolution["reviewer"] = "another-reviewer"
            self.assertEqual(
                review_status(bundle, "author", resolution)["status"], "accepted"
            )
            path.write_text(
                json.dumps({"args": {"different_request": True}, "result": result})
            )
            self.assertEqual(
                review_status(bundle, "author", resolution)["status"],
                "blocked",
                "stale receipts cannot resolve this bundle",
            )
            path.write_text(json.dumps({"tool": "jev_review", "action": "auto"}))
            self.assertEqual(
                review_status(bundle, "author", resolution)["status"],
                "blocked",
                "malformed scores cannot be approved",
            )
            result["safe_to_apply"] = float("nan")
            path.write_text(json.dumps({"args": {}, "result": result}))
            self.assertEqual(
                review_status(bundle, "author", resolution)["status"], "blocked"
            )
            path.write_text(
                json.dumps(
                    {"isError": True, "content": [{"text": "max_tokens_exceeded"}]}
                )
            )
            self.assertEqual(
                review_status(bundle, "author", resolution)["status"], "blocked"
            )

    def test_actual_per_claim_verify_output_and_invalid_controls(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "verify.json"
            calls = [
                {"tool": "jev_verify", "args": {"claims": ["claim"]}, "out": str(path)}
            ]
            bundle = {"calls": calls, "bundle_sha256": digest(calls)}
            result = {
                "tool": "jev_verify",
                "results": [
                    {
                        "claim": "claim",
                        "verdict": "verified",
                        "confidence": 0.76,
                        "action": "review",
                    }
                ],
            }

            def save():
                path.write_text(
                    json.dumps({"args": calls[0]["args"], "result": result})
                )

            save()
            self.assertEqual(
                review_status(bundle, "author")["status"], "needs_independent_review"
            )
            resolution = {
                "bundle_sha256": bundle["bundle_sha256"],
                "reviewer": "reviewer",
                "verdict": "approve",
                "rationale": "independently verified",
            }
            self.assertEqual(
                review_status(bundle, "author", resolution)["status"], "accepted"
            )
            result["results"][0].update(confidence=0.99, action="auto")
            save()
            self.assertEqual(review_status(bundle, "author")["status"], "accepted")
            for change in [
                {"verdict": "contradicted"},
                {"action": "unknown"},
                {"confidence": -1},
                {"claim": "other"},
            ]:
                original = dict(result["results"][0])
                result["results"][0].update(change)
                save()
                self.assertEqual(
                    review_status(bundle, "author", resolution)["status"], "blocked"
                )
                result["results"][0] = original
            del result["results"][0]["action"]
            save()
            self.assertEqual(
                review_status(bundle, "author", resolution)["status"], "blocked"
            )

    def test_contradicted_or_missing_claims_block_even_with_resolution(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "verify.json"
            calls = [
                {"tool": "jev_verify", "args": {"claims": ["claim"]}, "out": str(path)}
            ]
            bundle = {"calls": calls, "bundle_sha256": digest(calls)}
            resolution = {
                "bundle_sha256": bundle["bundle_sha256"],
                "reviewer": "reviewer",
                "verdict": "approve",
                "rationale": "reviewed",
            }
            for results in [
                [],
                [
                    {
                        "claim": "claim",
                        "verdict": "contradicted",
                        "action": "auto",
                        "confidence": 1,
                    }
                ],
            ]:
                path.write_text(
                    json.dumps(
                        {
                            "args": calls[0]["args"],
                            "result": {
                                "tool": "jev_verify",
                                "action": "auto",
                                "results": results,
                            },
                        }
                    )
                )
                self.assertEqual(
                    review_status(bundle, "author", resolution)["status"], "blocked"
                )
            # A well-formed low-confidence contradiction (no aggregate action) still blocks, even with a resolution.
            contradicted = [
                {
                    "claim": "claim",
                    "verdict": "contradicted",
                    "action": "review",
                    "confidence": 0.6,
                }
            ]
            path.write_text(
                json.dumps(
                    {
                        "args": calls[0]["args"],
                        "result": {"tool": "jev_verify", "results": contradicted},
                    }
                )
            )
            self.assertEqual(
                review_status(bundle, "author", resolution)["status"], "blocked"
            )


if __name__ == "__main__":
    unittest.main()
