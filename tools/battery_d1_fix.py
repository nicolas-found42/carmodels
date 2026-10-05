#!/usr/bin/env python3
"""D1 fixes: re-run decide (string requirements), verify + gate (single-string evidence)."""
import json, os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from jev_mcp_call import call

R = "/Users/Nicolas/Documents/github/hermes/projects/carmodels"
OUT = os.path.join(R, "research/evidence/carselection-2026-10-05")

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
PINE = "PCSX2 v2.8.2, Ford Racing 2, SLES-51705, uuid 37f695cd, game 1.00, status 1 (paused)"
EVIDENCE_DOC = (
    "VNC status: " + VNC_STATUS + ".\n"
    "Live screenshot transcript: " + LIVE_TRANSCRIPT + "\n"
    "Slot 98 screenshot transcript: " + SLOT98_TRANSCRIPT + "\n"
    "PINE identity: " + PINE + ".\n"
    "Container facts: no xdotool/xte, no python-Xlib, DISPLAY=:99 under Xvfb; "
    "hidden jev-browser session connected via trusted evaluate click on noVNC_connect_button; "
    "prior session found frame-step navigation unreliable with lagging screenshots; "
    "input indicators enabled in ini. Slot 100 is the live paused race to preserve; new saves go to 101+."
)

decide_args = {
    "decision": "Which input path drives the headless game for the ordinary car-selection capture?",
    "evidence": EVIDENCE_DOC[:12000],
    "priorities": "Stay headless (no desktop window, no focus theft). Ordinary controller input only: no guest-memory writes, cheats, patches, or memory cards. Bounded effort: stop after ~30 observed key presses without verified indicator response. Preserve slot 100; new saves to slots 101+.",
    "candidates": [
        {"id": "browser_keys", "description": "Send toggled key presses (M/N/I/K/J/L/O/Space) via hidden Playwright press_key to the connected noVNC canvas; observe via noVNC screenshots and input indicators."},
        {"id": "jev_act_clicks", "description": "Use Jev-driven browser act/click on noVNC UI controls only (Connect, fullscreen). No game input possible this way."},
        {"id": "container_xlib", "description": "Install a key-injection helper (python-xlib/XTEST) inside the container. Needs image change and user approval; not currently allowed."},
        {"id": "static_only", "description": "No input at all: analyse slot 98/99 EE images already on disk and abandon the ordinary-capture goal."},
    ],
    "requirements": [
        "Keeps PCSX2 headless with no native window or desktop focus theft",
        "Uses only ordinary controller input plus read-only/capture APIs",
        "Can actually deliver game button presses, not just browser-UI clicks",
    ],
}

verify_args = {
    "claims": [
        "The live emulator state is a paused Quick Race at 0 MPH, position 6/6, LAP 1/3.",
        "The hidden browser connected to the container display (VNC status Connected).",
        "Slot 98 holds the Living Legends theme screen with six padlocked car thumbnails and BACK/OK prompts.",
        "PINE identity reports status 1 (paused), game SLES-51705.",
    ],
    "evidence": EVIDENCE_DOC,
}

for name, tool, args in [("d1-06-decide", "jev_decide", decide_args),
                         ("d1-09-verify", "jev_verify", verify_args)]:
    res = call(tool, args)
    content = res.get("result", res)
    if isinstance(content, dict) and "content" in content:
        try:
            content = json.loads(content["content"][0]["text"])
        except Exception as ex:
            content = {"parse_error": str(ex), "raw": content}
    json.dump({"args": args, "result": content}, open(os.path.join(OUT, name + ".json"), "w"), indent=2)
    print("---", tool)
    print(json.dumps(content, indent=1)[:2000])

decide = json.load(open(os.path.join(OUT, "d1-06-decide.json")))["result"]
sel = (decide.get("recommendation", {}) or {}).get("selected", "unknown")
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
    "evidence": EVIDENCE_DOC + "\nDecide result: " + json.dumps(decide)[:3000],
}
res = call("jev_gate", gate_args)
content = res.get("result", res)
if isinstance(content, dict) and "content" in content:
    try:
        content = json.loads(content["content"][0]["text"])
    except Exception as ex:
        content = {"parse_error": str(ex), "raw": content}
json.dump({"args": gate_args, "result": content}, open(os.path.join(OUT, "d1-12-gate-input-path-decision.json"), "w"), indent=2)
print("--- jev_gate")
print(json.dumps(content, indent=1)[:2500])
