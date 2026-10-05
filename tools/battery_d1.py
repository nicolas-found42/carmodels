#!/usr/bin/env python3
"""D1 battery: input-path + starting-slot decision for ordinary car-selection capture.
Runs all 12 Jev tools via jev_mcp_call.call(); saves args+result receipts.
Jev advises; code owns bytes, counts, hashes. Usage: battery_d1.py (runs all, prints summary)."""
import json, os, sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__))))
from jev_mcp_call import call

R = "/Users/Nicolas/Documents/github/hermes/projects/carmodels"
OUT = os.path.join(R, "research/evidence/carselection-2026-10-05")
os.makedirs(OUT, exist_ok=True)

LIVE_TRANSCRIPT = (
    "VNC desktop shows one window titled 'Ford Racing 2'. First-person race view: track ahead, "
    "trees and structures left, fencing and stone wall right, rear-view mirror top center, two "
    "circular gauges bottom. HUD text: 'POSITION 6/6', 'Paused' upper-right, 'LAP 1/3', "
    "'LAP 00:00.00', 'LAST 00:00.00', 'BEST 00:00.00', gear '1', '000 MPH', tachometer 'x1000'. "
    "Small white symbols lower-left edge may be input indicators, too small to identify. "
    "No menu items, car names, or button prompts readable."
)
SLOT98_TRANSCRIPT = (
    "'Select a Challenge Theme' screen from Ford Racing 2 over a racetrack scene. Seven circular "
    "theme icons across upper middle: star (selected, gold), movie camera, SVT logo, trophy, paint "
    "palette, wrench, checkered flag. Title 'LIVING LEGENDS'. Six car thumbnails in a row below, each "
    "with a padlock badge (pale green, tan, light blue, brown, white, red cars); sixth red car "
    "highlighted with yellow border. Lower left 'ROOKIE 0%', lower right 'BACK' (triangle) and 'OK' "
    "(X) prompts. Visible text: SELECT A CHALLENGE THEME, FORD RACING 2, SVT, LIVING LEGENDS, "
    "ROOKIE 0%, BACK, OK. No car names or livery names readable."
)
VNC_STATUS = "Connected (unencrypted) to 3f7463603fbf:99"
PINE_IDENTITY = {"version": "PCSX2 v2.8.2", "title": "Ford Racing 2", "id": "SLES-51705",
                 "uuid": "37f695cd", "game_version": "1.00", "status": 1}
KEYMAP = ("Controller macros bound to keys: M=Cross, N=Circle, I=Up, K=Down, J=Left, L=Right, "
          "O=Start, P=R2, B=Triangle. A press toggles the button on and a second press toggles it "
          "off, so every action needs two key presses with observation between them. Space toggles "
          "emulator pause; F7 frame-advance; F8 screenshot; Shift+F8 single-frame GSDump. "
          "Starting states under sstates: slot 99 = main menu (boot default), slot 98 = 'Select a "
          "Challenge Theme / Living Legends' car-selection strip, slots 93/95/96/97 = in-race/other, "
          "slot 100 = paused Quick Race at zero MPH position 6/6 (current live state).")

BATTERY = [
    ("jev_screen", {"text": LIVE_TRANSCRIPT,
                    "purpose": "decide navigation inputs for ordinary car-selection capture"}),
    ("jev_noul", {"propositions": [
        "Sending the M key twice through the noVNC canvas toggles Cross on then off in the headless PCSX2 window.",
        "Loading PINE slot 98 while paused replaces the live race state with the Living Legends theme screen.",
        "Pressing Cross on a padlocked car thumbnail in slot 98 advances to another screen.",
        "The slot 98 cars are locked, so Cross on a thumbnail produces no screen advance.",
        "Reading the input-indicator overlay in a noVNC screenshot proves a key press registered.",
    ], "context": KEYMAP + " Live VNC status: " + VNC_STATUS + ". " + LIVE_TRANSCRIPT}),
    ("jev_find", {"query": "best starting emulator state for an ordinary-controller car-selection capture",
                  "candidates": [
                      {"id": "slot98", "text": "Slot 98: Select a Challenge Theme / Living Legends screen with six-car thumbnail strip, red car highlighted, OK prompt. " + SLOT98_TRANSCRIPT},
                      {"id": "slot99", "text": "Slot 99: main menu, container boot default. Earlier state, requires navigating menus forward to reach any car selection."},
                      {"id": "slot100_live", "text": "Slot 100 / current live state: paused Quick Race at 0 MPH, position 6/6, LAP 1/3. " + LIVE_TRANSCRIPT},
                  ], "top_k": 3}),
    ("jev_rerank", {"query": "first input action after loading slot 98, to reach an ordinary car or livery selection screen",
                    "candidates": [
                        {"id": "cross_thumb", "text": "Unpause, press M twice (Cross on/off) on the highlighted red thumbnail, observe, pause."},
                        {"id": "move_then_cross", "text": "Unpause, press J/L twice (Left/Right) to move highlight, then M twice, observe, pause."},
                        {"id": "start_button", "text": "Unpause, press O twice (Start button), observe, pause."},
                        {"id": "circle_back", "text": "Unpause, press N twice (Circle/BACK), observe, pause."},
                        {"id": "save_first", "text": "Save a new slot 101 copy of the live state before any load, preserving slot 100 untouched."},
                    ]}),
    ("jev_classify", {
        "items": [
            {"id": "live", "text": LIVE_TRANSCRIPT},
            {"id": "slot98", "text": SLOT98_TRANSCRIPT},
        ],
        "classes": [
            {"id": "race_paused", "description": "In-race view with HUD (position, lap, speed) and a pause indicator. Example: POSITION 6/6, LAP 1/3, 000 MPH, Paused."},
            {"id": "theme_select_strip", "description": "Challenge-theme icon row plus a car thumbnail strip, with BACK/OK prompts. Example: LIVING LEGENDS with six thumbnails."},
            {"id": "car_select_labels", "description": "Car selection screen showing readable car names or livery/colour labels. Must quote at least one name."},
            {"id": "manual_review", "description": "Cannot be placed confidently in any other class; ambiguous or conflicting signals."},
        ],
        "purpose": "label observed emulator screens before choosing navigation inputs",
        "context": "Ford Racing 2 headless capture; classes are mutually exclusive screen types."}),
    ("jev_decide", {
        "decision": "Which input path drives the headless game for the ordinary car-selection capture?",
        "evidence": ("VNC status: " + VNC_STATUS + ". Live state is paused race (PINE status 1, POSITION 6/6, 000 MPH). "
                     "Slot 98 holds the Living Legends theme/car-strip screen; slot 100 is the live paused race to preserve. "
                     "Container has no xdotool/xte and no python-Xlib; DISPLAY=:99 under Xvfb. "
                     "Hidden jev-browser session connected via trusted evaluate click on noVNC_connect_button; screenshots work. "
                     "Prior session judged frame-step navigation unreliable with lagging screenshots; input indicators enabled in ini."),
        "priorities": "Stay headless (no desktop window, no focus theft). Ordinary controller input only: no guest-memory writes, cheats, patches, or memory cards. Bounded effort: stop after ~30 observed key presses without verified indicator response. Preserve slot 100; new saves go to slots 101+.",
        "candidates": [
            {"id": "browser_keys", "description": "Send toggled key presses (M/N/I/K/J/L/O/Space) via hidden Playwright press_key to the connected noVNC canvas; observe via noVNC screenshots and input indicators."},
            {"id": "jev_act_clicks", "description": "Use Jev-driven browser act/click on noVNC UI controls only (Connect, fullscreen). No game input possible this way."},
            {"id": "container_xlib", "description": "Install a key-injection helper (python-xlib/XTEST) inside the container. Needs image change and user approval; not currently allowed."},
            {"id": "static_only", "description": "No input at all: analyse slot 98/99 EE images already on disk and abandon the ordinary-capture goal."},
        ],
        "requirements": [
            {"id": "headless", "description": "The path keeps PCSX2 headless with no native window or desktop focus theft."},
            {"id": "ordinary", "description": "The path uses only ordinary controller/keyboard input plus read-only/capture APIs."},
            {"id": "game_input", "description": "The path can actually deliver game button presses (Cross/Circle/d-pad), not just browser-UI clicks."},
        ]}),
    ("jev_compare", {"passage_a": SLOT98_TRANSCRIPT, "passage_b": LIVE_TRANSCRIPT,
                     "aspects": ["screen type", "pause state", "visible car/label text"]}),
    ("jev_extract", {"document": KEYMAP, "fields": [
        {"id": "cross", "pattern": "M=Cross", "description": "key bound to the Cross button"},
        {"id": "circle", "pattern": "N=Circle", "description": "key bound to the Circle button"},
        {"id": "up", "pattern": "I=Up", "description": "key bound to d-pad Up"},
        {"id": "start", "pattern": "O=Start", "description": "key bound to the Start button"},
        {"id": "triangle", "pattern": "B=Triangle", "description": "key bound to the Triangle button"},
        {"id": "pause", "pattern": "Space toggles emulator pause", "description": "key that toggles emulator pause"},
        {"id": "slot98", "pattern": "slot 98", "description": "savestate slot holding the theme/car-strip screen"},
        {"id": "slot100", "pattern": "slot 100", "description": "savestate slot of the live paused race to preserve"},
    ]}),
    ("jev_verify", {
        "claims": [
            "The live emulator state is a paused Quick Race at 0 MPH, position 6/6, LAP 1/3.",
            "The hidden browser connected to the container display (VNC status Connected).",
            "Slot 98 holds the Living Legends theme screen with six padlocked car thumbnails and BACK/OK prompts.",
            "PINE identity reports status 1 (paused), game SLES-51705.",
        ],
        "evidence": ["Live VNC screenshot transcript: " + LIVE_TRANSCRIPT,
                     "VNC status string: " + VNC_STATUS,
                     "Slot 98 screenshot transcript: " + SLOT98_TRANSCRIPT,
                     "PINE identity: " + json.dumps(PINE_IDENTITY),
                     "Keymap and slot table: " + KEYMAP]}),
]

# jev_audit depends on extract output; jev_review/jev_gate depend on prior outputs.
# They are appended after the first pass runs.


def save(name, args, res):
    receipt = {"args": args, "result": res}
    path = os.path.join(OUT, name)
    json.dump(receipt, open(path, "w"), indent=2)
    usage = res.get("usage") if isinstance(res, dict) else None
    return path, usage


def main():
    results = {}
    total_in, total_out = 0, 0
    for i, (tool, args) in enumerate(BATTERY, 1):
        name = "d1-%02d-%s.json" % (i, tool.replace("jev_", ""))
        try:
            res = call(tool, args)
            content = res.get("result", res)
            if isinstance(content, dict) and "content" in content:
                try:
                    content = json.loads(content["content"][0]["text"])
                except Exception:
                    content = content
        except Exception as e:
            content = {"error": str(e)}
        p, usage = save(name, args, content)
        results[tool] = content
        if isinstance(usage, dict):
            total_in += usage.get("input_tokens", 0) or 0
            total_out += usage.get("output_tokens", 0) or 0
        print("---", tool, "->", os.path.basename(p))
        print(json.dumps(content, indent=1)[:1500])

    # jev_audit: audit extract values against the KEYMAP source
    ext = results.get("jev_extract", {})
    records = []
    if isinstance(ext, dict):
        fields = ext.get("fields", ext.get("results", {}))
        if isinstance(fields, dict):
            for fid, f in fields.items():
                records.append({"id": fid, "request": "extract " + fid,
                                "value": f.get("value", "") if isinstance(f, dict) else ""})
    audit_args = {"source": KEYMAP, "records": records}
    try:
        res = call("jev_audit", audit_args)
        content = res.get("result", res)
        if isinstance(content, dict) and "content" in content:
            content = json.loads(content["content"][0]["text"])
    except Exception as e:
        content = {"error": str(e)}
    save("d1-10-audit-keymap-extract.json", audit_args, content)
    results["jev_audit"] = content
    print("--- jev_audit -> d1-10-audit-keymap-extract.json")
    print(json.dumps(content, indent=1)[:1500])

    # jev_review: review the connect+observe procedure (request + action-diff)
    decide = results.get("jev_decide", {})
    review_args = {
        "request": "Open the noVNC URL in the hidden Playwright browser and prove that the live emulator state is observable, without touching the desktop.",
        "diff": ("+ opened hidden session fr2 on http://127.0.0.1:54239/vnc.html\n"
                 "+ clicked noVNC_connect_button via trusted page JS (evaluate)\n"
                 "+ VNC status: " + VNC_STATUS + "\n"
                 "+ screenshot shows paused race POSITION 6/6 000 MPH, matching slot-100 live state\n"
                 "+ no window promoted to desktop; no game input sent; no memory written"),
    }
    try:
        res = call("jev_review", review_args)
        content = res.get("result", res)
        if isinstance(content, dict) and "content" in content:
            content = json.loads(content["content"][0]["text"])
    except Exception as e:
        content = {"error": str(e)}
    save("d1-11-review-connect-observe.json", review_args, content)
    results["jev_review"] = content
    print("--- jev_review -> d1-11-review-connect-observe.json")
    print(json.dumps(content, indent=1)[:1500])

    # jev_gate: gate the D1 decision record itself
    sel = (decide.get("recommendation", {}) or {}).get("selected", "unknown") if isinstance(decide, dict) else "unknown"
    gate_args = {
        "request": "Decide the input path and starting slot for the ordinary car-selection capture.",
        "diff": json.dumps({"decision": "d1-input-path-and-start",
                            "selected_input_path": sel,
                            "starting_slot": "98",
                            "preserve_slot": "100 untouched; new saves to 101+"}, indent=1),
        "claims": [
            "The selected input path keeps PCSX2 headless with no desktop focus theft.",
            "The selected input path uses only ordinary controller input plus read-only/capture APIs.",
            "Slot 98 is the chosen starting state; slot 100 stays untouched.",
        ],
        "evidence": ["VNC status: " + VNC_STATUS,
                     "Live transcript: " + LIVE_TRANSCRIPT,
                     "Slot98 transcript: " + SLOT98_TRANSCRIPT,
                     "PINE identity: " + json.dumps(PINE_IDENTITY),
                     "Decide result: " + json.dumps(decide)[:3000]],
    }
    try:
        res = call("jev_gate", gate_args)
        content = res.get("result", res)
        if isinstance(content, dict) and "content" in content:
            content = json.loads(content["content"][0]["text"])
    except Exception as e:
        content = {"error": str(e)}
    save("d1-12-gate-input-path-decision.json", gate_args, content)
    print("--- jev_gate -> d1-12-gate-input-path-decision.json")
    print(json.dumps(content, indent=1)[:2000])
    print("TOKENS in=%d out=%d" % (total_in, total_out))


if __name__ == "__main__":
    main()
