#!/usr/bin/env python3
"""Serve both local car libraries, with an optional server-side semantic filter API."""

import argparse
import functools
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
import json
from pathlib import Path
import threading
import time
import uuid
from urllib.parse import urlparse

from library_filter import diagnostic_observer, live_interpret, model_status
from diagnostics import (
    DEFAULT_STORE,
    MAX_BUNDLE,
    SESSION_ID,
    DiagnosticStore,
    failure_details,
    git_identity,
)

ROOT = Path(__file__).resolve().parents[1] / "dealership"
STARTUP = {
    "available": "uses the TypeSafe model.",
    "sdk_unavailable": "needs the TypeSafe SDK (typesafe-sdk), which this Python cannot import.",
    "credentials_missing": "needs OPENROUTER_API_KEY in the server environment.",
}


class LibraryHandler(SimpleHTTPRequestHandler):
    judgment = staticmethod(live_interpret)
    api_lock = threading.Lock()
    diagnostic_store = None
    build_identity = None

    def handle_one_request(self):
        self.request_id = str(uuid.uuid4())
        self.request_started = time.monotonic()
        return super().handle_one_request()

    def event(self, kind, **fields):
        if self.diagnostic_store is not None:
            session_id = getattr(self, "headers", {}).get("X-Car-Session", "")
            self.diagnostic_store.log(
                kind,
                request_id=self.request_id,
                session_id=session_id if SESSION_ID.fullmatch(session_id) else None,
                **fields,
            )

    def log_request(self, code="-", size="-"):
        self.event(
            "http.response",
            method=self.command,
            route=urlparse(self.path).path
            if self.path.startswith("/api/")
            else "static",
            status=code,
            elapsed_ms=round((time.monotonic() - self.request_started) * 1000, 3),
        )
        # Never put request query strings in stderr either.
        self.log_message(
            "%s %s %s",
            self.command,
            "api" if self.path.startswith("/api/") else "static",
            code,
        )

    def local_request(self):
        allowed = {
            f"localhost:{self.server.server_port}",
            f"127.0.0.1:{self.server.server_port}",
        }
        host = self.headers.get("Host")
        return host in allowed and self.headers.get("Origin") in (
            None,
            "http://" + host,
        )

    def end_headers(self):
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Request-ID", self.request_id)
        super().end_headers()

    def reply(self, status, payload):
        data = json.dumps(payload, allow_nan=False).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def do_POST(self):
        if self.path == "/api/diagnostics":
            self.receive_incident()
            return
        if self.path != "/api/library-filter":
            self.reply(404, {"status": "error", "message": "Unknown endpoint."})
            return
        allowed_hosts = {
            f"localhost:{self.server.server_port}",
            f"127.0.0.1:{self.server.server_port}",
        }
        if self.headers.get("Host") not in allowed_hosts:
            self.reply(
                403, {"status": "error", "message": "Use the local library address."}
            )
            return
        self.connection.settimeout(5)
        origin = self.headers.get("Origin")
        expected = f"http://{self.headers.get('Host', '')}"
        if origin is not None and origin != expected:
            self.reply(
                403, {"status": "error", "message": "Use the local library page."}
            )
            return
        try:
            length = int(self.headers.get("Content-Length", "0"))
            if (
                not 0 < length <= 2048
                or self.headers.get("Content-Type", "").split(";")[0]
                != "application/json"
            ):
                raise ValueError("Invalid request")
            payload = json.loads(self.rfile.read(length))
            if not isinstance(payload, dict) or set(payload) not in (
                {"query"},
                {"query", "catalog"},
            ):
                raise ValueError("Invalid payload")
            catalog = payload.get("catalog", "source")
            if catalog not in ("source", "dealership"):
                raise ValueError("Invalid catalog")
            query = payload["query"]
            if (
                not isinstance(query, str)
                or not 1 <= len(query.strip()) <= 500
                or any(ord(c) < 32 for c in query)
            ):
                raise ValueError("Invalid query")
        except (ValueError, UnicodeError, OSError):
            self.reply(
                400,
                {
                    "status": "error",
                    "message": "Enter a query of 1 to 500 printable characters.",
                },
            )
            return
        if not self.api_lock.acquire(blocking=False):
            self.reply(
                429,
                {"status": "error", "message": "A filter request is already running."},
            )
            return
        status = 200
        token = diagnostic_observer.set(self.event)
        try:
            path = (
                "public/models.json"
                if catalog == "source"
                else "public/dealership/cars.json"
            )
            data = json.loads((Path(self.directory) / path).read_text())
            cars = data["cars"] if catalog == "source" else data
            receipt = self.judgment(query, cars, catalog=catalog)
            # Do not expose raw provider envelopes in the UI; local experiments retain those separately.
            response = {
                key: receipt.get(key)
                for key in (
                    "status",
                    "filters",
                    "message",
                    "decided_by",
                    "reason",
                    "signals",
                    "usage",
                    "latency_seconds",
                )
            }
            # Validate before leaving the error boundary; reply serializes before
            # sending headers too, so malformed receipts still produce one 503.
            json.dumps(response, allow_nan=False)
            # The outcome, never the query text, goes to the server log.
            self.log_message(
                "library filter: %s by %s%s",
                receipt.get("status"),
                receipt.get("decided_by") or "nothing",
                f" ({receipt['reason']})" if receipt.get("reason") else "",
            )
            self.event(
                "filter.result",
                phase="complete",
                status=receipt.get("status"),
                reason=receipt.get("reason"),
                decided_by=receipt.get("decided_by"),
                latency_seconds=receipt.get("latency_seconds"),
                usage=receipt.get("usage"),
                model=receipt.get("model"),
                request_sha256=receipt.get("request_sha256"),
            )
        except Exception as error:
            self.event("filter.failure", phase="handler", **failure_details(error))
            status = 503
            response = {
                "status": "error",
                "message": "The model catalog is unavailable.",
            }
        finally:
            diagnostic_observer.reset(token)
            self.api_lock.release()
        # The filter work is complete before a client can receive its response
        # and send the next request. Slow response writes must not hold the slot.
        self.reply(status, response)

    def receive_incident(self):
        if not self.local_request() or self.headers.get("X-Car-Diagnostics") != "1":
            self.reply(
                403, {"status": "error", "message": "Use the local diagnostic client."}
            )
            return
        if self.diagnostic_store is None:
            self.reply(
                503, {"status": "error", "message": "Diagnostic store unavailable."}
            )
            return
        self.connection.settimeout(5)
        try:
            length = int(self.headers.get("Content-Length", "0"))
            if (
                not 0 < length <= MAX_BUNDLE
                or self.headers.get("Content-Type") != "application/json"
            ):
                raise ValueError("Invalid incident request")
            value = json.loads(self.rfile.read(length))
            session_id = self.diagnostic_store.put(value)
            self.event("incident.stored", incident_id=session_id)
            self.reply(201, {"schema": 1, "session_id": session_id})
        except (ValueError, UnicodeError, OSError):
            self.reply(
                400, {"status": "error", "message": "Invalid diagnostic bundle."}
            )

    def do_GET(self):
        if urlparse(self.path).path.startswith("/api/diagnostics"):
            self.read_incident()
            return
        if (
            urlparse(self.path).path == "/build-info.mjs"
            and self.build_identity is not None
        ):
            # Source edits take effect without restarting the local server.
            self.server.diagnostic_identity = git_identity()
            data = (
                "export const buildInfo = "
                + json.dumps(self.server.diagnostic_identity)
                + ";\n"
            ).encode()
            self.send_response(200)
            self.send_header("Content-Type", "text/javascript")
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)
            return
        if urlparse(self.path).path == "/":
            self.send_response(302)
            self.send_header("Location", "/dealership.html")
            self.end_headers()
            return
        super().do_GET()

    def read_incident(self):
        if not self.local_request():
            self.reply(
                403, {"status": "error", "message": "Use the local library address."}
            )
            return
        if self.diagnostic_store is None:
            self.reply(503, {"status": "error"})
            return
        path = urlparse(self.path).path
        if path == "/api/diagnostics/capabilities":
            self.reply(
                200,
                {
                    "schema": 1,
                    "identity": getattr(
                        self.server, "diagnostic_identity", self.build_identity
                    ),
                },
            )
        elif path == "/api/diagnostics":
            self.reply(200, {"schema": 1, "incidents": self.diagnostic_store.list()})
        else:
            try:
                self.reply(
                    200,
                    self.diagnostic_store.get(path.removeprefix("/api/diagnostics/")),
                )
            except (ValueError, FileNotFoundError):
                self.reply(404, {"status": "error"})


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--port", type=int, default=8081)
    parser.add_argument("--diagnostics-dir", type=Path, default=DEFAULT_STORE)
    args = parser.parse_args()
    LibraryHandler.diagnostic_store = DiagnosticStore(args.diagnostics_dir)
    LibraryHandler.build_identity = git_identity()
    with ThreadingHTTPServer(
        ("127.0.0.1", args.port), functools.partial(LibraryHandler, directory=str(ROOT))
    ) as server:
        print(f"Car library: http://localhost:{args.port}/dealership.html", flush=True)
        print(
            "Natural-language filter: exact game/variant phrases work offline; other wording "
            + STARTUP[model_status()],
            flush=True,
        )
        try:
            server.serve_forever()
        finally:
            LibraryHandler.diagnostic_store.close()
