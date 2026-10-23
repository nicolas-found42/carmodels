#!/usr/bin/env python3
"""Serve the real-viewer acceptance harness; open its printed URL with Jev browser.

This is an explicit browser check, separate from the offline check suite. Its
result is written only after the browser posts every assertion. Asset pins must
be captured before implementation; absent or changed pilot inputs are blockers.
"""

import argparse
import functools
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
import json
from pathlib import Path
import threading

from verifier_common import sha256

ROOT = Path(__file__).resolve().parents[1]
EXPECTED_CHECKS = (
    "named pilot records exist in authoritative list",
    "list selection highlights only visible selected geometry",
    "details match independent ownership and parent-chain matrices",
    "keyboard arrows and Enter reach both named records",
    "canvas pointer selection selects both native identities",
    "hidden record selection preserves unrelated visibility",
    "nearest positive ray hit and native identity ties",
    "ownership rebind and parent translation controls reject specifically",
    "missing optional metadata displays Unknown",
    "source and dealership link navigation stays local and usable",
)


def hashes(pins):
    return {
        name: sha256((ROOT / name).read_bytes())
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
        pilot=pins.get("pilot", pins.get("modelId")),
        pinned_commit=pins.get("commit", pins.get("pinned_commit")),
        hashes_before=before,
        hashes_after=after,
        stored_assets_unchanged=before == after,
        external_network_blocked_by="CSP connect-src self on every response",
        claim_limits=["Tests static recovered pilot selection and ownership, not native runtime rendering or animation."],
        ok=complete and before == after,
    )
    return report


def serve(pins_path, output, port=0):
    pins = json.loads(pins_path.read_text())
    before = hashes(pins)
    expected = {
        name: value["sha256"] if isinstance(value, dict) else value
        for name, value in pins["files"].items()
    }
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
            if self.path != "/mc3-inspection-test-result":
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
            "/tools/test_mc3_inspection_browser.html",
            flush=True,
        )
        server.serve_forever()
    return 0 if json.loads(output.read_text())["ok"] else 1


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--pins", type=Path, default=ROOT / "tools/fixtures/mc3-inspection-pins.json"
    )
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--port", type=int, default=0)
    args = parser.parse_args()
    raise SystemExit(serve(args.pins, args.output, args.port))
