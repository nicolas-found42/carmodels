#!/usr/bin/env python3
"""Serve the real-viewer acceptance harness; open its printed URL with Jev browser.

This is an explicit browser check, separate from the offline check suite. Its
result is written only after the browser posts every assertion. Asset pins must
be captured before implementation; absent or changed pilot inputs are blockers.
"""

import argparse
import functools
import hashlib
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
import json
from pathlib import Path
import threading

ROOT = Path(__file__).resolve().parents[1]
EXPECTED_CHECKS = (
    "pilot legacy identity and available nondefault source-root geometry",
    "save nondefault body geometry, native preset, camera and Enhanced",
    "clean frame restores every discrete setting and camera within 1e-6",
    "unknown car rejects identity and keeps usable legacy pilot",
    "unsupported native preset is rejected with default paint",
    "unsupported geometry is rejected with default scene",
    "version 99 rejected with usable defaults",
    "NaN camera component rejected with fitted camera",
    "Infinity camera component rejected with fitted camera",
    "JSON NaN token rejected with visible reason and usable car",
    "snapshot over 8 KiB rejected before parsing",
    "legacy link still selects MC3 350Z and repeated switches discard rejected camera and paint",
    "external requests blocked and saved snapshot restores locally again",
)


def hashes(pins):
    return {
        name: hashlib.sha256((ROOT / name).read_bytes()).hexdigest()
        for name in pins["files"]
    }


def finish_report(pins, before, report):
    after = hashes(pins)
    rows = report.get("checks", [])
    names = [row.get("name") for row in rows]
    complete = (
        len(names) == len(EXPECTED_CHECKS)
        and set(names) == set(EXPECTED_CHECKS)
        and all(row.get("status") == "pass" for row in rows)
    )
    report.update(
        schema=1,
        pilot=pins["pilot"],
        pinned_commit=pins["commit"],
        hashes_before=before,
        hashes_after=after,
        stored_assets_unchanged=before == after,
        external_network_blocked_by="CSP connect-src self on every response",
        ok=complete and before == after,
    )
    return report


def serve(pins_path, output, port=0):
    pins = json.loads(pins_path.read_text())
    before = hashes(pins)
    expected = {name: value["sha256"] for name, value in pins["files"].items()}
    if before != expected:
        raise ValueError("Pilot inputs changed since the initial pin; acceptance is blocked.")
    if output.exists():
        raise ValueError("Use a new browser evidence output path.")

    class Handler(SimpleHTTPRequestHandler):
        def end_headers(self):
            # Applies to the viewer responses too: a parent frame's CSP alone
            # would not block requests made inside a same-origin child frame.
            self.send_header(
                "Content-Security-Policy",
                "default-src 'self' data: blob:; script-src 'self' 'unsafe-inline'; "
                "style-src 'self' 'unsafe-inline'; connect-src 'self'; "
                "img-src 'self' data: blob:; frame-src 'self'",
            )
            self.send_header("Cache-Control", "no-store")
            super().end_headers()

        def do_POST(self):
            if self.path != "/inspection-test-result":
                self.send_error(404)
                return
            length = int(self.headers.get("Content-Length", "0"))
            if not 0 < length <= 200000:
                self.send_error(413)
                return
            report = finish_report(pins, before, json.loads(self.rfile.read(length)))
            output.parent.mkdir(parents=True, exist_ok=True)
            with output.open("x") as stream:
                json.dump(report, stream, indent=2, allow_nan=False)
                stream.write("\n")
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps({"ok": report["ok"]}).encode())
            print(f"Browser evidence: {output} (ok={report['ok']})", flush=True)
            threading.Thread(target=self.server.shutdown, daemon=True).start()

        def log_message(self, *args):
            pass

    with ThreadingHTTPServer(
        ("127.0.0.1", port), functools.partial(Handler, directory=str(ROOT))
    ) as server:
        print(
            f"Open with Jev browser: http://127.0.0.1:{server.server_port}"
            "/tools/test_inspection_browser.html",
            flush=True,
        )
        server.serve_forever()
    return 0 if json.loads(output.read_text())["ok"] else 1


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--pins", type=Path, default=ROOT / "tools/fixtures/inspection-pilot.json"
    )
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--port", type=int, default=0)
    args = parser.parse_args()
    raise SystemExit(serve(args.pins, args.output, args.port))
