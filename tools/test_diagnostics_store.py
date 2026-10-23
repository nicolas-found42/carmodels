"""Exercise retained incidents, privacy controls, HTTP retrieval and real CLI exports."""

import copy
from datetime import datetime, timezone
import functools
from http.server import ThreadingHTTPServer
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import threading
import unittest
from urllib.error import HTTPError
from urllib.request import Request, urlopen
import uuid

from diagnostics import DiagnosticStore, failure_details, git_identity, validate_bundle
from serve_library import LibraryHandler


def bundle():
    stamp = datetime.now(timezone.utc).isoformat()
    return {
        "schema": 1,
        "session_id": str(uuid.uuid4()),
        "app": "source",
        "started_at": stamp,
        "updated_at": stamp,
        "identity": {"git_sha": "abc"},
        "state": {"car": "ford-racing-2/COBRA"},
        "environment": {},
        "events": [{"seq": 1, "kind": "load.failure", "data": {"load_id": "1"}}],
    }


class Tests(unittest.TestCase):
    def test_bundle_validation_and_redaction(self):
        value = bundle()
        value["events"][0]["data"].update(
            query="PRIVATE",
            raw_response="PRIVATE",
            error={"message": "token=PRIVATE Bearer PRIVATE sk-PRIVATE"},
        )
        self.assertNotIn("PRIVATE", json.dumps(validate_bundle(value)))
        for field, replacement in [
            ("schema", 2),
            ("session_id", "../escape"),
            ("app", "other"),
            ("events", [{"seq": 1, "kind": "a"}, {"seq": 1, "kind": "b"}]),
            ("updated_at", "2026-01-01"),
        ]:
            changed = {**bundle(), field: replacement}
            with self.subTest(field=field), self.assertRaises(ValueError):
                validate_bundle(changed)

    def test_store_retention_and_out_of_order_upload(self):
        with tempfile.TemporaryDirectory() as temp:
            store = DiagnosticStore(temp, max_sessions=2)
            try:
                first = bundle()
                store.put(first)
                newer = copy.deepcopy(first)
                newer["events"].append({"seq": 2, "kind": "load.success"})
                store.put(newer)
                store.put(first)
                self.assertEqual(store.get(first["session_id"])["events"][-1]["seq"], 2)
                old = store.incidents / (first["session_id"] + ".json")
                os.utime(old, (1, 1))
                store.put(bundle())
                self.assertFalse(old.exists())
                store.put(bundle())
                store.put(bundle())
                self.assertEqual(len(store.list()), 2)
                self.assertEqual(list(store.incidents.glob("*.tmp")), [])
                store.max_bytes = 1
                store.prune()
                self.assertEqual(store.list(), [])
            finally:
                store.close()

    def test_rotated_service_events_and_secret_bearing_exception(self):
        with tempfile.TemporaryDirectory() as temp:
            store = DiagnosticStore(temp)
            try:
                try:
                    raise RuntimeError("Authorization: Bearer PRIVATE query=PRIVATE")
                except RuntimeError as error:
                    fields = failure_details(error)
                self.assertEqual(fields["error_type"], "RuntimeError")
                self.assertEqual(
                    fields["frames"][-1]["function"],
                    "test_rotated_service_events_and_secret_bearing_exception",
                )
                store.logger.handlers[0].maxBytes = 400
                for i in range(40):
                    store.log(
                        "filter.failure",
                        request_id=str(i),
                        query="PRIVATE",
                        raw_response="PRIVATE",
                        **fields,
                    )
                logs = list(Path(temp).glob("service.jsonl*"))
                self.assertLessEqual(len(logs), 5)
                self.assertNotIn("PRIVATE", "".join(p.read_text() for p in logs))
                self.assertIn("RuntimeError", "".join(p.read_text() for p in logs))
            finally:
                store.close()

    def test_cli_import_list_export_and_no_overwrite(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            source = root / "report.json"
            incident = bundle()
            source.write_text(json.dumps(incident))
            cli = [
                sys.executable,
                str(Path(__file__).with_name("diagnostics.py")),
                "--store",
                str(root / "store"),
            ]

            def run(*args):
                return subprocess.run([*cli, *args], capture_output=True, text=True)

            self.assertEqual(run("import", str(source)).returncode, 0)
            self.assertEqual(
                json.loads(run("list").stdout)[0]["session_id"], incident["session_id"]
            )
            output = root / "export.json"
            self.assertEqual(
                run(
                    "export", incident["session_id"], "--output", str(output)
                ).returncode,
                0,
            )
            self.assertEqual(json.loads(output.read_text())["state"], incident["state"])
            self.assertEqual(
                run(
                    "export", incident["session_id"], "--output", str(output)
                ).returncode,
                1,
            )
            self.assertEqual(json.loads(run("logs").stdout), [])

    def test_identity_changes_for_dirty_tracked_and_untracked_content(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            subprocess.run(["git", "init", "-q", temp], check=True)
            first = git_identity(root)
            target = root / "new.txt"
            target.write_text("first")
            second = git_identity(root)
            target.write_text("second")
            third = git_identity(root)
            self.assertFalse(first["dirty"])
            self.assertTrue(second["dirty"])
            self.assertNotEqual(
                first["working_tree_sha256"], second["working_tree_sha256"]
            )
            self.assertNotEqual(
                second["working_tree_sha256"], third["working_tree_sha256"]
            )

    def test_local_http_incident_retrieval_and_filter_failure_correlation(self):
        with tempfile.TemporaryDirectory() as temp:
            store = DiagnosticStore(Path(temp) / "store")

            class Handler(LibraryHandler):
                diagnostic_store = store
                build_identity = {"git_sha": "test"}

                @staticmethod
                def judgment(*args, **kwargs):
                    raise RuntimeError("SDK authorization=PRIVATE")

                def log_message(self, *args):
                    pass

            (Path(temp) / "public").mkdir()
            (Path(temp) / "public/models.json").write_text('{"cars":[]}')
            server = ThreadingHTTPServer(
                ("127.0.0.1", 0), functools.partial(Handler, directory=temp)
            )
            worker = threading.Thread(target=server.serve_forever, daemon=True)
            worker.start()
            base = f"http://127.0.0.1:{server.server_port}"

            def request(route, data=None, headers=None):
                req = Request(
                    base + route,
                    data=json.dumps(data).encode() if data is not None else None,
                    headers=headers
                    or {"Content-Type": "application/json", "X-Car-Diagnostics": "1"},
                )
                try:
                    return urlopen(req, timeout=3)
                except HTTPError as error:
                    return error

            try:
                report = bundle()
                with request("/api/diagnostics", report) as response:
                    self.assertEqual(response.status, 201)
                    self.assertEqual(
                        json.load(response)["session_id"], report["session_id"]
                    )
                with request("/api/diagnostics/" + report["session_id"]) as response:
                    self.assertEqual(json.load(response)["state"], report["state"])
                with request("/api/diagnostics") as response:
                    self.assertEqual(len(json.load(response)["incidents"]), 1)
                with request("/api/diagnostics/capabilities") as response:
                    self.assertEqual(json.load(response)["identity"]["git_sha"], "test")
                with request(
                    "/api/diagnostics", report, {"Content-Type": "application/json"}
                ) as response:
                    self.assertEqual(response.status, 403)
                for route in ("/api/diagnostics", "/api/diagnostics/capabilities"):
                    with request(
                        route, headers={"Origin": "https://evil.example"}
                    ) as response:
                        self.assertEqual(response.status, 403)
                with request("/api/diagnostics", {**report, "schema": 999}) as response:
                    self.assertEqual(response.status, 400)
                with request(
                    "/api/library-filter",
                    {"query": "PRIVATE"},
                    {
                        "Content-Type": "application/json",
                        "X-Car-Session": report["session_id"],
                    },
                ) as response:
                    self.assertEqual(response.status, 503)
                    request_id = response.headers["X-Request-ID"]
                events = [
                    json.loads(line)
                    for line in (store.root / "service.jsonl").read_text().splitlines()
                ]
                failures = [e for e in events if e["kind"] == "filter.failure"]
                self.assertEqual(failures[-1]["request_id"], request_id)
                self.assertEqual(failures[-1]["session_id"], report["session_id"])
                self.assertEqual(failures[-1]["error_type"], "RuntimeError")
                self.assertNotIn("PRIVATE", json.dumps(events))
            finally:
                server.shutdown()
                server.server_close()
                worker.join()
                store.close()


if __name__ == "__main__":
    unittest.main(verbosity=2)
