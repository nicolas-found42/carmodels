#!/usr/bin/env python3
"""Bounded incident store, sanitized service events, and agent-facing diagnostic CLI."""

import argparse
from datetime import datetime, timezone
import hashlib
import json
import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path
import re
import subprocess
import sys
import threading
import time
import traceback
import uuid

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_STORE = ROOT / ".scratch/diagnostics"
MAX_BUNDLE = 524288
SESSION_ID = re.compile(r"^[a-f0-9-]{36}$")
LOG_FIELDS = {
    "request_id",
    "session_id",
    "method",
    "route",
    "status",
    "reason",
    "phase",
    "elapsed_ms",
    "decided_by",
    "model",
    "request_sha256",
    "error_type",
    "frames",
    "latency_seconds",
    "usage",
    "incident_id",
    "git_sha",
}


def safe_text(value, limit=1000):
    text = re.sub(r"(https?://[^\s?]+)\?[^\s)]+", r"\1?[redacted]", str(value))
    text = re.sub(
        r"(?:Bearer\s+|(?:api[_-]?key|authorization|token|password|secret)\s*[=:]\s*)[^\s,;]+",
        "[redacted]",
        text,
        flags=re.I,
    )
    return re.sub(r"\bsk-[\w-]+", "[redacted]", text)[:limit]


def clean(value, depth=0):
    if depth > 9:
        return None
    if isinstance(value, str):
        return safe_text(value)
    if value is None or isinstance(value, (bool, int)):
        return value
    if isinstance(value, float):
        return value if abs(value) < float("inf") else None
    if isinstance(value, list):
        return [clean(v, depth + 1) for v in value[:256]]
    if isinstance(value, dict):
        return {
            safe_text(k, 64): clean(v, depth + 1)
            for k, v in list(value.items())[:60]
            if not re.search(
                r"query|search|token|secret|password|authorization|raw_response|cookie|payload",
                k,
                re.I,
            )
        }
    return None


def failure_details(error):
    """Never stringify SDK errors: they may include request headers and provider bodies."""
    return {
        "error_type": type(error).__name__,
        "frames": [
            {
                "file": Path(frame.filename).name,
                "function": frame.name,
                "line": frame.lineno,
            }
            for frame in traceback.extract_tb(error.__traceback__)[-8:]
        ],
    }


def git_identity(root=ROOT):
    def git(*args):
        try:
            result = subprocess.run(
                ["git", *args], cwd=root, capture_output=True, timeout=15
            )
        except (OSError, subprocess.TimeoutExpired):
            return b""
        return result.stdout if result.returncode == 0 else b""

    status = git("status", "--porcelain", "-z")
    digest = hashlib.sha256(git("diff", "HEAD", "--binary") + status)
    for name in git("ls-files", "--others", "--exclude-standard", "-z").split(b"\0"):
        if not name:
            continue
        path = Path(root) / name.decode(errors="surrogateescape")
        if path.is_file() and not path.is_symlink():
            digest.update(name)
            with path.open("rb") as stream:
                for block in iter(lambda: stream.read(1024 * 1024), b""):
                    digest.update(block)
    return {
        "git_sha": git("rev-parse", "HEAD").decode().strip() or None,
        "working_tree_sha256": digest.hexdigest(),
        "dirty": bool(status),
        "edition": "local",
    }


def validate_bundle(value):
    if not isinstance(value, dict) or value.get("schema") != 1:
        raise ValueError("Unsupported incident schema")
    if not SESSION_ID.fullmatch(str(value.get("session_id", ""))):
        raise ValueError("Invalid session ID")
    if value.get("app") not in ("source", "dealership"):
        raise ValueError("Invalid viewer edition")
    for field in ("started_at", "updated_at"):
        stamp = datetime.fromisoformat(str(value.get(field, "")).replace("Z", "+00:00"))
        if stamp.tzinfo is None:
            raise ValueError("Timestamp must include timezone")
    events = value.get("events")
    if not isinstance(events, list) or len(events) > 256:
        raise ValueError("Invalid incident events")
    previous = 0
    for event in events:
        if (
            not isinstance(event, dict)
            or type(event.get("seq")) is not int
            or event["seq"] <= previous
        ):
            raise ValueError("Incident event order is invalid")
        previous = event["seq"]
        if not isinstance(event.get("kind"), str) or len(event["kind"]) > 64:
            raise ValueError("Invalid incident event kind")
    result = clean(
        {
            k: value[k]
            for k in (
                "schema",
                "session_id",
                "app",
                "started_at",
                "updated_at",
                "identity",
                "environment",
                "state",
                "events",
            )
            if k in value
        }
    )
    if len(json.dumps(result).encode()) > MAX_BUNDLE:
        raise ValueError("Incident exceeds size limit")
    return result


class DiagnosticStore:
    def __init__(
        self, root=DEFAULT_STORE, *, max_sessions=64, max_bytes=10 * 1024 * 1024, days=7
    ):
        self.root = Path(root)
        self.incidents = self.root / "incidents"
        self.incidents.mkdir(parents=True, exist_ok=True)
        self.max_sessions, self.max_bytes, self.days = max_sessions, max_bytes, days
        self.lock = threading.RLock()
        self.logger = logging.Logger("car-diagnostics")
        handler = RotatingFileHandler(
            self.root / "service.jsonl", maxBytes=1024 * 1024, backupCount=4
        )
        handler.setFormatter(logging.Formatter("%(message)s"))
        self.logger.addHandler(handler)

    def close(self):
        for handler in self.logger.handlers:
            handler.close()

    def log(self, kind, **fields):
        row = {
            "schema": 1,
            "at": datetime.now(timezone.utc).isoformat(),
            "kind": kind,
            **clean({k: v for k, v in fields.items() if k in LOG_FIELDS}),
        }
        with self.lock:
            self.logger.info(json.dumps(row, allow_nan=False))

    def prune(self):
        files = sorted(
            self.incidents.glob("*.json"), key=lambda p: p.stat().st_mtime, reverse=True
        )
        size = 0
        for index, path in enumerate(files):
            size += path.stat().st_size
            if (
                index >= self.max_sessions
                or size > self.max_bytes
                or path.stat().st_mtime < time.time() - self.days * 86400
            ):
                path.unlink(missing_ok=True)

    def put(self, value):
        bundle = validate_bundle(value)
        session_id = bundle["session_id"]
        with self.lock:
            target = self.incidents / (session_id + ".json")
            # A delayed network write must not replace a newer timeline.
            if target.exists():
                old = json.loads(target.read_text())
                if (old["events"][-1]["seq"] if old["events"] else 0) > (
                    bundle["events"][-1]["seq"] if bundle["events"] else 0
                ):
                    return session_id
            temporary = target.with_suffix("." + uuid.uuid4().hex + ".tmp")
            temporary.write_text(json.dumps(bundle, allow_nan=False) + "\n")
            temporary.replace(target)
            self.prune()
        return session_id

    def get(self, session_id):
        if not SESSION_ID.fullmatch(session_id):
            raise ValueError("Invalid session ID")
        with self.lock:
            self.prune()
            return json.loads((self.incidents / (session_id + ".json")).read_text())

    def list(self):
        with self.lock:
            self.prune()
            rows = []
            for path in sorted(self.incidents.glob("*.json")):
                value = json.loads(path.read_text())
                rows.append(
                    {
                        k: value.get(k)
                        for k in (
                            "session_id",
                            "app",
                            "started_at",
                            "updated_at",
                            "identity",
                        )
                    }
                )
                rows[-1]["car"] = value.get("state", {}).get("car")
                rows[-1]["event_count"] = len(value.get("events", []))
                rows[-1]["failures"] = [
                    {
                        "kind": event["kind"],
                        "seq": event["seq"],
                        "at": event.get("at"),
                        "load_id": event.get("data", {}).get("load_id"),
                    }
                    for event in value.get("events", [])
                    if event["kind"]
                    in (
                        "load.failure",
                        "fetch.timeout",
                        "runtime.error",
                        "runtime.rejection",
                        "webglcontextlost",
                    )
                ][-8:]
            return rows


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--store", type=Path, default=DEFAULT_STORE)
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("list")
    export = commands.add_parser("export")
    export.add_argument("session_id")
    export.add_argument("--output", type=Path)
    ingest = commands.add_parser("import")
    ingest.add_argument("file", type=Path)
    logs = commands.add_parser("logs")
    logs.add_argument("--request-id")
    logs.add_argument("--session-id")
    args = parser.parse_args()
    store = DiagnosticStore(args.store)
    try:
        if args.command == "list":
            result = store.list()
        elif args.command == "import":
            if args.file.stat().st_size > MAX_BUNDLE:
                raise ValueError("Incident exceeds size limit")
            result = {"session_id": store.put(json.loads(args.file.read_text()))}
        elif args.command == "export":
            result = store.get(args.session_id)
            if args.output:
                with args.output.open("x") as stream:
                    json.dump(result, stream, indent=2)
                return 0
        else:
            result = []
            for path in reversed(
                [
                    store.root / "service.jsonl",
                    *sorted(store.root.glob("service.jsonl.*")),
                ]
            ):
                if path.exists():
                    for line in path.read_text().splitlines():
                        row = json.loads(line)
                        if args.request_id and row.get("request_id") != args.request_id:
                            continue
                        if args.session_id and row.get("session_id") != args.session_id:
                            continue
                        result.append(row)
        print(json.dumps(result, indent=2))
    except (ValueError, OSError, json.JSONDecodeError) as error:
        parser.exit(1, str(error) + "\n")
    finally:
        store.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
