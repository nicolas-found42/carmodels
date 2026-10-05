"""Provenance and immutable result directories shared by the three checks."""

from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import platform
import sys
import uuid


class Invalid(ValueError):
    """Input contradicts the supported contract."""

    def __init__(self, message, details=None):
        super().__init__(message)
        self.details = details or {}


class Incomplete(ValueError):
    """A required prerequisite or observation is missing."""

    def __init__(self, message, details=None):
        super().__init__(message)
        self.details = details or {}


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def identity(path: Path) -> dict:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return {"bytes": path.stat().st_size, "sha256": digest.hexdigest()}


def write_result(output: Path, check: str, action, inputs: list[Path]) -> int:
    run_id = (
        datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ") + "-" + uuid.uuid4().hex
    )
    run = output / run_id
    run.mkdir(parents=True)
    result = {
        "schema_version": 1,
        "run_id": run_id,
        "check": check,
        "command": sys.argv,
        "tools": {"python": platform.python_version(), "platform": platform.platform()},
        "inputs": {},
        "status": "incomplete",
        "diagnostics": [],
        "details": {},
    }
    try:
        for path in inputs:
            result["inputs"][str(path)] = identity(path)
        result["details"] = action()
        result["status"] = "fail" if result["details"].get("failures") else "pass"
        result["diagnostics"].extend(result["details"].get("failures", []))
    except Incomplete as exc:
        result["details"] = exc.details
        result["diagnostics"].append(str(exc))
    except FileNotFoundError as exc:
        result["diagnostics"].append(str(exc))
    except (Invalid, ValueError, KeyError, IndexError, TypeError, OSError) as exc:
        result["status"] = "fail"
        result["details"] = getattr(exc, "details", {})
        result["diagnostics"].append(f"{type(exc).__name__}: {exc}")
    report = "# " + check + ": " + result["status"] + "\n\n"
    report += (
        "\n".join(result["diagnostics"])
        + "\n\n```json\n"
        + json.dumps(result["details"], indent=2)
        + "\n```\n"
    )
    (run / "report.md").write_text(report)
    result["artifacts"] = {"report.md": identity(run / "report.md")}
    (run / "result.json").write_text(json.dumps(result, indent=2) + "\n")
    print(
        json.dumps(
            {
                "status": result["status"],
                "result": str(run / "result.json"),
                "diagnostics": result["diagnostics"],
            }
        )
    )
    return {"pass": 0, "fail": 1, "incomplete": 2}[result["status"]]
