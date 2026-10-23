# Incident diagnostics

Both viewers have a **Diagnostics** panel. Recording is local by default on a static
site: up to 256 events per session, eight sessions, seven days and 512 KiB total.
**Save diagnostic history** disables recording and clears saved reports. Browser
storage denial is visible; the live report remains exportable but cannot survive reload.
Reports contain build/catalog/model hashes, selected car/geometry/preset/paint, camera,
viewer settings, load phases, HTTP outcomes, cancellation/stale-result ordering, timings,
runtime errors and WebGL context loss/restoration. Model bytes, search text, credentials
and raw provider envelopes are excluded. Error strings are bounded and sanitized.

Use **Download diagnostics** or **Copy diagnostics** to share a report. The session
selector includes previous visits after reload. **Replay viewer state** restores a
selected session in the same viewer; the file input restores an exported report.
Replay uses currently served assets and does not reproduce historical GPU behavior.
An exported incident should accompany an issue when reporting an intermittent failure.

## Local agent access

```sh
python3 tools/serve_library.py --port 8081
python3 tools/diagnostics.py list
python3 tools/diagnostics.py export SESSION_ID --output /tmp/car-incident.json
python3 tools/diagnostics.py logs --session-id SESSION_ID
python3 tools/diagnostics.py logs --request-id REQUEST_ID
```

On loopback, **Share automatically with this local library server** is enabled initially
and can be disabled separately from browser recording. It mirrors reports to
`.scratch/diagnostics/`; previously saved sessions are recovered on reconnect/reload.
The API provides `GET /api/diagnostics/capabilities`, `GET /api/diagnostics`,
`GET /api/diagnostics/SESSION_ID` and `POST /api/diagnostics`. Reads check the local
Host/Origin; writes additionally require JSON and `X-Car-Diagnostics: 1`. No permissive
CORS is enabled. The listener binds to loopback. A custom store is available with
`--diagnostics-dir` on the server and `--store` before the CLI subcommand.

Static hosting has no collector. Browser storage is not remotely readable by an agent.
A visitor must download/share their report; import it with:

```sh
python3 tools/diagnostics.py import /path/to/car-incident.json
```

The local store retains at most 64 incidents, 10 MiB and seven days. New uploads
cannot overwrite a newer event sequence with an older one. Service JSONL logs rotate
at 1 MiB with four backups. Filter diagnostics preserve phase, exception class and
stack frame locations, never exception messages from SDKs. Response `X-Request-ID`
connects the browser's `filter.response` event to service logs; `X-Car-Session` connects
the session. Keep exported files and local logs out of commits.

## Reproduce and verify

```sh
node tools/replay_incident.mjs /tmp/car-incident.json
CARMODELS_INCIDENT_ID=SESSION_ID tools/check.sh --only test_diagnostics,test_diagnostics_store,test_model_load,test_viewer_loading
```

Offline replay uses the shipped fetch function, GLB parser and the same latest-load
publication guard as both viewers. It recreates recorded primary request successes,
HTTP failures, stalled-body timeouts, cancellations and response ordering. It does not
make network requests. GLB bytes must exist locally and match their recorded SHA-256;
missing/changed bytes and incomplete traces fail explicitly. For a deliberate before/after
comparison, `--allow-version-mismatch` permits changed assets and marks that limitation
in the report. Replay reports whether recorded load failures occurred and whether the
latest successful selection remained visible. Runtime-only, texture decode, camera,
paint and GPU failures require state replay in a real browser and a targeted regression.
An unrepresented failure does not count as reproduced.

The regression battery checks reload persistence, quota denial, redaction, age/size
limits, multiple tabs, stale publication, 404, body timeout, corrupted asset identity,
incomplete traces, local API restrictions, CLI export, log rotation and SDK exception
privacy. Its deliberate obsolete-publication mutation must fail the replay invariant.
For a new bug, first retain the incident, establish a failing symptom assertion, then
run that assertion against the fix. Passing a general suite alone does not prove the
reported incident is fixed.

Check manifests and history include a stable run UUID, exact Node version, commit,
working-tree content fingerprint, catalog hashes, incident ID and absolute evidence
path in the local ledger. CI artifacts retain the manifest, index and individual logs
for a requested 90 days; inspect GitHub's actual expiration when investigating older
runs. Check history proves automated execution, not visitor behavior or game fidelity.

## Shared inspection pilot

In the source viewer, `gran-turismo-4/acra0001` offers **Copy inspection link**.
The link restores a version-1 inspection snapshot: car, geometry, native preset and
supported paint channels, camera position/orbit target and projection, display controls,
and Original/Enhanced presentation. It uses the diagnostics live snapshot and replay paths,
even when diagnostic history is disabled. No model bytes or credentials enter the snapshot.
The URL-encoded snapshot value is limited to 8 KiB; the full URL also contains the page
address and legacy game/car parameters. Legacy links continue to work.

The pilot's exported showroom scene remains the default. Its additional **Source part**
geometry choices show actual named root nodes (body, wheels and tires) from that scene;
they are inspection views, not additional recovered LODs. Other cars' geometry choices
and sharing behavior are unchanged. Loading a link validates choices against the currently
served pilot and reports rejected fields visibly. Unsupported versions, malformed/oversized
snapshots and unavailable cars fall back to the legacy car choice or the pilot. Invalid
appearance or camera fields preserve a valid car and use its defaults, including clearing
remembered paint. A link is applied once at startup; later car switches do not replay it.
Restoration changes viewer state and normal browser paint preferences. It does not modify source/native files,
working GLBs, or the catalog, and does not reproduce original-game lighting or GPU behavior.

Run `node tools/test_inspection_state.mjs` for the bounded codec and malformed-field
controls (also in `tools/check.sh`). The separate real-browser acceptance harness is
served by `python3 tools/verify_inspection_browser.py --output <new-evidence.json>`; open its printed URL with the Jev browser. It uses new
iframe documents and cleared browser storage, blocks external connections by CSP,
checks all issue criteria, and hashes the pinned source/native/working files before
and after. Missing or changed pinned inputs block the run; an incomplete browser
report is not a pass. The harness does not launch a browser or run in the offline suite.
