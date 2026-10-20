"""Prepare bounded raw-patch reviews and separate evidence-verification batches; record escalation."""

import argparse
import difflib
import hashlib
import json
import math
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
# jev_review per-file limits (jev-mcp 0.13.0 lib.js: MAX_REVIEW_FILES, MAX_REVIEW_FILES_TOTAL_CHARS,
# MAX_REVIEW_DOC_CHARS). Within them every file is judged with the whole change in view.
MAX_FILES, MAX_FILES_CHARS, MAX_FILE_CHARS = 16, 200000, 50000
MAX_TESTS_CHARS = 50000
# Whole-call input budget. On 2026-10-12 a ~99,000-character jev_review call succeeded and calls of
# ~105,000+ characters failed upstream with `max_tokens_exceeded`; staying under 90,000 fails closed here.
MAX_CALL_CHARS = 90000


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True).encode()).hexdigest()


def snapshot(root, paths):
    files = {}
    for name in paths:
        path = Path(name)
        if path.is_absolute() or ".." in path.parts:
            raise ValueError("Review paths must be relative to the repository")
        target = Path(root) / path
        files[str(path)] = target.read_text() if target.exists() else None
    return {"schema": 1, "files": files}


def raw_diffs(baseline, root):
    if baseline.get("schema") != 1 or not baseline.get("files"):
        raise ValueError("Invalid or empty review baseline")
    before = baseline["files"]
    after = snapshot(root, list(before))["files"]
    # Detect renames within the explicit task scope, including originally untracked files.
    deleted = [n for n in before if before[n] is not None and after[n] is None]
    added = [n for n in before if before[n] is None and after[n] is not None]
    renames = {}
    for old in deleted:
        candidates = [
            (difflib.SequenceMatcher(None, before[old], after[new]).ratio(), new)
            for new in added
        ]
        if candidates:
            score, new = max(candidates)
            if score > 0.6:
                renames[old] = new
                added.remove(new)
    diffs = []
    for old in sorted(before):
        if old in renames.values():
            continue
        new = renames.get(old, old)
        text = "".join(
            difflib.unified_diff(
                (before[old] or "").splitlines(True),
                (after[new] or "").splitlines(True),
                fromfile="a/" + old if before[old] is not None else "/dev/null",
                tofile="b/" + new if after[new] is not None else "/dev/null",
            )
        )
        if text:
            diffs.append(text)
    return diffs


def diff_path(diff):
    """The post-change path of one raw file diff (the pre-change path for a deletion)."""
    for line in diff.splitlines():
        if line.startswith("+++ "):
            target = line[4:]
            if target != "/dev/null":
                return target[2:]
        elif line.startswith("--- ") and line[4:] != "/dev/null":
            source = line[6:]
    return source


def check_summary(receipt):
    """One computed line, so a judge never has to count manifest rows."""
    counts = {}
    for row in receipt["checks"]:
        counts[row["status"]] = counts.get(row["status"], 0) + 1
    return f"CHECK SUMMARY {len(receipt['checks'])} checks: " + ", ".join(
        f"{n} {s}" for s, n in sorted(counts.items())
    )


def scope_facts(baseline, root):
    """Added/modified/deleted files and, for each Python file, the same-directory modules importing it."""
    lines = [
        "SCOPE FACTS (computed by tools/review_payload.py from the baseline and working tree)"
    ]
    for name, before in sorted(baseline["files"].items()):
        path = Path(root) / name
        if before is None:
            state = "ADDED" if path.exists() else None
        elif not path.exists():
            state = "DELETED"
        else:
            state = "MODIFIED" if path.read_text() != before else None
        if state is None:
            continue
        line = f"{state} {name}"
        if name.endswith(".py"):
            pattern = re.compile(
                rf"^\s*(from\s+{re.escape(Path(name).stem)}\s+import\b|import\s+{re.escape(Path(name).stem)}\b)",
                re.M,
            )
            importers = sorted(
                str(other.relative_to(root))
                for other in path.parent.glob("*.py")
                if other != path and pattern.search(other.read_text())
            )
            line += " <- imported by: " + (
                ", ".join(importers) if importers else "nothing in its directory"
            )
        lines.append(line)
    return "\n".join(lines)


def review_tests(receipt, checks_dir, paths, facts=""):
    """Scope facts, check summary and the full logs of checks whose command names a file in the review scope."""
    lines = [
        facts,
        check_summary(receipt),
        *(f"{row['status'].upper()} {row['name']}" for row in receipt["checks"]),
    ]
    for row in receipt["checks"]:
        if any(part in paths for part in row["command"]):
            lines.append(
                f"\nLOG {row['name']} ({' '.join(row['command'])}) EXIT {row['exit_code']}\n"
                + (Path(checks_dir) / row["log"]).read_text()
            )
    text = "\n".join(lines)
    if len(text) > MAX_TESTS_CHARS:
        raise ValueError(
            "In-scope test logs exceed the budget; narrow the review scope, never truncate logs"
        )
    return text


def prepare(
    baseline,
    root,
    request,
    checks_dir,
    claims,
    output,
    max_diff_chars=24000,
    per_file=True,
):
    if not 1000 <= max_diff_chars <= 50000:
        raise ValueError("Diff cap must be between 1000 and 50000 characters")
    if not request.strip() or len(request) > 4000:
        raise ValueError("Request must be nonempty and at most 4000 characters")
    if any(not c.strip() or len(c) > 2000 for c in claims):
        raise ValueError("Each claim must be nonempty and at most 2000 characters")
    output = Path(output).resolve()
    output.mkdir(parents=True, exist_ok=True)
    if any(output.iterdir()):
        raise ValueError(
            "Review output must be empty; previous judgments are preserved"
        )
    diffs = raw_diffs(baseline, root)
    if not diffs:
        raise ValueError("No patch changes in the review scope")
    files = [{"path": diff_path(d), "diff": d} for d in diffs]
    per_file = (
        per_file
        and len(files) <= MAX_FILES
        and sum(len(d) for d in diffs) <= MAX_FILES_CHARS
    )
    groups, current = [], ""
    for diff in diffs:
        if len(diff) > (MAX_FILE_CHARS if per_file else max_diff_chars):
            raise ValueError(
                "A raw file diff exceeds the cap; narrow the change, never truncate hunks"
            )
        if current and len(current) + len(diff) > max_diff_chars:
            groups.append(current)
            current = ""
        current += diff
    if current:
        groups.append(current)
    checks_dir = Path(checks_dir)
    receipt = json.loads((checks_dir / "results.json").read_text())
    if receipt.get("schema") != 1 or not receipt.get("checks"):
        raise ValueError("Invalid or empty check manifest")
    if receipt.get("pending"):
        raise ValueError(
            "Check manifest has pending checks; wait for the run to finish"
        )
    manifest = {
        "id": "check-manifest",
        "text": check_summary(receipt) + "\n" + json.dumps(receipt, indent=2),
    }
    # Full logs are independent of the exit summary. Bundle them without dropping their tails.
    logs = {}
    for row in receipt["checks"]:
        log = Path(row["log"])
        if log.is_absolute() or ".." in log.parts:
            raise ValueError("Check log must belong to the evidence directory")
        logs[row["name"]] = (
            f"COMMAND {row['command']}\nSTATUS {row['status']} EXIT {row['exit_code']}\n"
            + (checks_dir / log).read_text()
        )
    tests = review_tests(
        receipt, checks_dir, {f["path"] for f in files}, scope_facts(baseline, root)
    )
    if per_file:
        calls = [
            {
                "tool": "jev_review",
                "args": {"request": request, "files": files, "tests": tests},
                "out": str(output / "review-001.json"),
            }
        ]
    else:
        calls = [
            {
                "tool": "jev_review",
                "args": {"request": request, "diff": diff, "tests": tests},
                "out": str(output / f"review-{i:03}.json"),
            }
            for i, diff in enumerate(groups, 1)
        ]
    for i in range(0, len(claims), 2):
        pair = claims[i : i + 2]
        # A claim that names checks is judged on their full logs; otherwise on every log.
        named = [
            name
            for name in logs
            if any(re.search(rf"\b{re.escape(name)}\b", claim) for claim in pair)
        ]
        evidence = [
            manifest,
            {
                "id": "full-check-logs",
                "text": "\n".join(logs[n] for n in (named or logs)),
            },
        ]
        if sum(len(e["text"]) for e in evidence) > 190000:
            raise ValueError(
                "Evidence exceeds the budget; select a relevant check subset"
            )
        calls.append(
            {
                "tool": "jev_verify",
                "args": {"claims": pair, "evidence": evidence},
                "out": str(output / f"verify-{i // 2 + 1:03}.json"),
            }
        )
    for call in calls:
        if len(json.dumps(call["args"])) > MAX_CALL_CHARS:
            raise ValueError(
                f"A {call['tool']} call exceeds {MAX_CALL_CHARS} characters; split the scope by concern "
                "or name fewer checks in a claim, never truncate"
            )
    bundle = {
        "schema": 1,
        "bundle_sha256": digest(calls),
        "paths": sorted(baseline["files"]),
        "calls": calls,
        "policy": "Every patch review and evidence claim must be resolved; verification never approves a patch.",
        "mode": "per-file" if per_file else "grouped",
        "claim_limits": [
            "Explicit text-file task scope only; binaries/generated assets need separate checks.",
            "Preparing this bundle does not call Jev or approve changes.",
        ],
    }
    (output / "calls.json").write_text(json.dumps(calls, indent=2) + "\n")
    (output / "bundle.json").write_text(json.dumps(bundle, indent=2) + "\n")
    return bundle


def unwrap(value):
    value = value.get("result", value)
    if value.get("isError") or "error" in value:
        raise ValueError("Judge operational failure")
    if "content" in value:
        value = json.loads(value["content"][0]["text"])
    return value


def probability(value):
    return (
        isinstance(value, (int, float))
        and not isinstance(value, bool)
        and math.isfinite(value)
        and 0 <= value <= 1
    )


def review_status(bundle, implementer, resolution=None):
    if digest(bundle["calls"]) != bundle["bundle_sha256"]:
        raise ValueError("Review bundle digest differs")
    unresolved, blocked = [], []
    for call in bundle["calls"]:
        path = Path(call["out"])
        try:
            receipt = json.loads(path.read_text())
            if receipt.get("args") != call["args"]:
                raise ValueError("Judge receipt arguments differ from this bundle")
            result = unwrap(receipt)
            if result.get("tool") != call["tool"]:
                raise ValueError("Unknown or malformed judge result")
            action = result.get("action")
            if call["tool"] == "jev_verify":
                results = result.get("results", [])
                if len(results) != len(call["args"]["claims"]) or any(
                    r.get("claim") != c
                    or r.get("verdict")
                    not in ["verified", "unsupported", "contradicted"]
                    or r.get("action") not in ["auto", "review"]
                    for r, c in zip(results, call["args"]["claims"])
                ):
                    raise ValueError(
                        "Verification results do not account for every claim"
                    )
                # jev_verify returns per-claim actions without an aggregate action.
                # Derive the aggregate only after validating every claim's schema.
                if action is None:
                    action = (
                        "review"
                        if any(r["action"] == "review" for r in results)
                        else "auto"
                    )
                if action == "auto" and any(
                    r.get("verdict") != "verified" or r.get("action") != "auto"
                    for r in results
                ):
                    raise ValueError("Auto verification contains unresolved claims")
                if any(not probability(r.get("confidence")) for r in results):
                    raise ValueError("Verification confidence is missing or invalid")
            else:
                per_file = "files" in call["args"]
                halves = result.get("files") if per_file else [result]
                if per_file and (
                    result.get("mode") != "per-file"
                    or not isinstance(halves, list)
                    or [f.get("path") for f in halves]
                    != [f["path"] for f in call["args"]["files"]]
                ):
                    raise ValueError("Per-file review does not account for every file")
                for half in halves:
                    scores = half.get("scores", {})
                    if (
                        not probability(half.get("safe_to_apply"))
                        or set(scores)
                        != {"correctness", "spec_match", "test_gap", "blast_radius"}
                        or any(
                            not probability(s.get("confidence"))
                            for s in scores.values()
                        )
                    ):
                        raise ValueError("Patch review scores are missing or invalid")
                if per_file and any(
                    f.get("action") not in ["auto", "review", "escalate"]
                    for f in halves
                ):
                    raise ValueError("Unknown or malformed per-file action")
                if (
                    per_file
                    and any(f.get("action") != "auto" for f in halves)
                    and action == "auto"
                ):
                    raise ValueError("Auto review contains unresolved files")
            if action not in ["auto", "review", "escalate"]:
                raise ValueError("Unknown or malformed judge action")
            if any(
                r.get("verdict") == "contradicted" for r in result.get("results", [])
            ):
                blocked.append(str(path))
            elif action != "auto":
                entry = {
                    "receipt": str(path),
                    "action": action,
                    "scores": result.get("scores"),
                    "safe_to_apply": result.get("safe_to_apply"),
                }
                if result.get("mode") == "per-file":
                    entry["files"] = [
                        {
                            k: f.get(k)
                            for k in ("path", "action", "safe_to_apply", "scores")
                        }
                        for f in result["files"]
                        if f.get("action") != "auto"
                    ]
                unresolved.append(entry)
        except (OSError, ValueError, KeyError, TypeError, IndexError, AttributeError):
            blocked.append(str(path))
    if resolution:
        if (
            resolution.get("bundle_sha256") != bundle["bundle_sha256"]
            or not resolution.get("reviewer")
            or resolution["reviewer"] == implementer
            or not resolution.get("rationale")
        ):
            raise ValueError(
                "Resolution requires an independent reviewer, matching bundle digest and rationale"
            )
        if resolution.get("verdict") == "approve" and not blocked:
            unresolved = []
    return {
        "status": "blocked"
        if blocked
        else "needs_independent_review"
        if unresolved
        else "accepted",
        "blocked": blocked,
        "unresolved": unresolved,
        "claim_limits": [
            "Resolution records a reviewer decision; it is not identity authentication."
        ],
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="mode", required=True)
    snap = sub.add_parser("snapshot")
    snap.add_argument("--paths", nargs="+", required=True)
    snap.add_argument("--output", type=Path, required=True)
    build = sub.add_parser("build")
    build.add_argument("--baseline", type=Path, required=True)
    build.add_argument("--request-file", type=Path, required=True)
    build.add_argument("--checks-dir", type=Path, required=True)
    build.add_argument("--claim", action="append", default=[])
    build.add_argument("--output-dir", type=Path, required=True)
    build.add_argument("--max-diff-chars", type=int, default=24000)
    build.add_argument(
        "--grouped",
        action="store_true",
        help="grouped whole-diff calls even when per-file review fits",
    )
    status = sub.add_parser("status")
    status.add_argument("--bundle", type=Path, required=True)
    status.add_argument("--implementer", required=True)
    status.add_argument("--resolution", type=Path)
    args = parser.parse_args()
    try:
        if args.mode == "snapshot":
            value = snapshot(ROOT, args.paths)
            args.output.parent.mkdir(parents=True, exist_ok=True)
            with args.output.open("x") as stream:
                stream.write(json.dumps(value, indent=2) + "\n")
        elif args.mode == "build":
            value = prepare(
                json.loads(args.baseline.read_text()),
                ROOT,
                args.request_file.read_text(),
                args.checks_dir,
                args.claim,
                args.output_dir,
                args.max_diff_chars,
                not args.grouped,
            )
            print(
                f"Prepared {len(value['calls'])} bounded calls; bundle {value['bundle_sha256']}"
            )
        else:
            resolution = (
                json.loads(args.resolution.read_text()) if args.resolution else None
            )
            value = review_status(
                json.loads(args.bundle.read_text()), args.implementer, resolution
            )
            print(json.dumps(value, indent=2))
            return 0 if value["status"] == "accepted" else 2
    except (ValueError, OSError) as error:
        parser.error(str(error))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
