#!/usr/bin/env python3
"""Derive the recovered inspector's candidate game-shading table from the committed receipts.

The table names the source Headers the pass-source join found with an aligned pass-4 or pass-5 draw,
which passes each one carries, the sampled view render target and its retained preview. It carries no
new claim: every field is copied from research/evidence/vu-dispatch/pass-source-join.json and the
preview it pins, so the inspector's "Game shading (candidate)" control can identify a shaded Header
offline.

    python3 tools/build_game_shading_assignments.py           # write the table and the preview copy
    python3 tools/build_game_shading_assignments.py --check   # verify both are current
"""

import argparse
import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RECEIPT = ROOT / "research/evidence/vu-dispatch/pass-source-join.json"
PREVIEW = ROOT / "research/evidence/vu-dispatch/pass4-retained-target.png"
OUTPUT = ROOT / "dealership/public/game-shading.json"
PREVIEW_OUTPUT = ROOT / "dealership/public/pass4-retained-target.png"
SCHEMA = "fr2-game-shading/v2"
RECEIPT_SCHEMA = "fr2-pass-source-join/v1"
DRAWS = {4: 37, 5: 63}
FR2_GAME = "ford-racing-2"
PASSES = (4, 5)
RULE = (
    "Pass 4: Header bit 0x10 maps to effective bit 0x80; a pass-4 draw requires "
    "(effective_flags & 0x88) == 0x80 and its per-draw global enable. "
    "Pass 5: Header bit 0x08 maps to effective bit 0x40; a pass-5 draw requires "
    "(effective_flags & 0x48) == 0x40 and its per-draw global enable. The rows below are the "
    "aligned draws of the pass-source join, not a proven live dispatch."
)
CLAIM_LIMITS = [
    "A static decode and a content join, not a captured frame: the receipt marks the Handler rule "
    "as conditional on runtime enable and context, so a Header here is eligible, not proven drawn.",
    "Only the cars with an aligned draw are listed; any other car or part renders unchanged.",
    "The preview is capture-time GS memory at the sampled address (view-render-target-0), not the "
    "post-render contents at the aligned draw. It is a stand-in for the sampled texture.",
    "The eye position and the 3x3 matrix are not in the receipt; the inspector uses the camera as the "
    "eye and a view-derived matrix, and labels the result candidate.",
    "The capture comparison verifies the pass-5 per-draw RGBA relation and the STQ T lane on 63 draws, "
    "not S: the specular intensity is a static reading of the decoded arithmetic, and the sampled "
    "specular texture function is not in the receipt.",
    "The pass-5 light inputs (DM[5], DM[6]) come from game state; the inspector substitutes the "
    "retained capture values as fixed stand-ins, so a listed Header is eligible for the highlight, "
    "not shown with the game's own light.",
]


class DerivationError(ValueError):
    pass


def need(condition, message):
    if not condition:
        raise DerivationError(message)


def text(value, label):
    need(isinstance(value, str) and value, "missing %s" % label)
    return value


def number(value, label):
    need(
        isinstance(value, int) and not isinstance(value, bool) and value >= 0,
        "invalid %s" % label,
    )
    return value


def derive(receipt_bytes, preview_bytes):
    need(len(receipt_bytes) and len(preview_bytes), "a source input is empty")
    receipt = json.loads(receipt_bytes)
    need(receipt.get("schema") == RECEIPT_SCHEMA, "pass-source-join schema differs")
    rows = receipt["rows"]
    for pass_word in PASSES:
        found = len([row for row in rows if row.get("pass_word") == pass_word])
        need(
            found == DRAWS[pass_word],
            "expected %d pass-%d draws, found %d"
            % (DRAWS[pass_word], pass_word, found),
        )
    cars = {}
    headers = {}
    draws = set()
    for row in rows:
        code = text(row.get("car"), "row car")
        offset = number(row.get("header_offset"), "header offset")
        index = number(row.get("header_index"), "header index")
        flags = number(row.get("header_flags"), "header flags")
        pass_word = row.get("pass_word")
        need(pass_word in PASSES, "unexpected pass word in the join")
        # One Header joins at most once per pass; the count guard alone cannot see a swap.
        need(
            (code, offset, pass_word) not in draws,
            "duplicate pass-%d draw for Header %d" % (pass_word, offset),
        )
        draws.add((code, offset, pass_word))
        entry = cars.setdefault(code, {"headers": []})
        header = headers.get((code, offset))
        if header is None:
            header = {"index": index, "offset": offset, "flags": flags, "passes": set()}
            headers[(code, offset)] = header
            entry["headers"].append(header)
        # One Header carries one index and one flag word however many passes align to it.
        need(
            header["index"] == index and header["flags"] == flags,
            "Header %d disagrees about its index or flags across passes" % offset,
        )
        header["passes"].add(row["pass_word"])
    texture = receipt["pass4_texture"]
    need(
        texture.get("identity") == "view-render-target-0",
        "sampled texture identity differs",
    )
    digest = hashlib.sha256(preview_bytes).hexdigest()
    need(
        digest == texture.get("png_sha256"),
        "retained preview differs from the receipt pin",
    )
    return {
        "schema": SCHEMA,
        "label": "candidate",
        "source": {
            "receipt": str(RECEIPT.relative_to(ROOT)),
            "receipt_sha256": hashlib.sha256(receipt_bytes).hexdigest(),
            "draws": {"4": DRAWS[4], "5": DRAWS[5]},
            "rule": RULE,
        },
        "pass4_texture": {
            "identity": texture["identity"],
            "file": "public/pass4-retained-target.png",
            "source_png": str(PREVIEW.relative_to(ROOT)),
            "sha256": digest,
            "width": number(texture["width"], "texture width"),
            "height": number(texture["height"], "texture height"),
            "psm": number(texture["PSM"], "texture format"),
            "tbp0": number(texture["TBP0"], "texture base"),
            "tbw": number(texture["TBW"], "texture buffer width"),
        },
        "cars": [
            {
                "code": code,
                "game": FR2_GAME,
                "label": "candidate",
                "headers": sorted(
                    (
                        {
                            "index": header["index"],
                            "offset": header["offset"],
                            "flags": header["flags"],
                            "passes": sorted(header["passes"]),
                        }
                        for header in entry["headers"]
                    ),
                    key=lambda header: (header["index"], header["offset"]),
                ),
            }
            for code, entry in sorted(cars.items())
        ],
        "claim_limits": CLAIM_LIMITS,
    }, preview_bytes


def build(root=ROOT, output=OUTPUT, preview_output=PREVIEW_OUTPUT, check=False):
    root, output, preview_output = Path(root), Path(output), Path(preview_output)
    need(
        output.resolve().parent == (root / "dealership/public").resolve(),
        "table output must stay under dealership/public",
    )
    need(
        preview_output.resolve().parent == output.resolve().parent,
        "preview output must stay beside the table",
    )
    table, preview = derive(
        (root / RECEIPT.relative_to(ROOT)).read_bytes(),
        (root / PREVIEW.relative_to(ROOT)).read_bytes(),
    )
    text_bytes = (json.dumps(table, indent=1, ensure_ascii=False) + "\n").encode()
    if check:
        need(
            output.is_file() and output.read_bytes() == text_bytes,
            "the game-shading assignment table is stale; run python3 tools/build_game_shading_assignments.py",
        )
        need(
            preview_output.is_file() and preview_output.read_bytes() == preview,
            "the copied retained preview is stale; run python3 tools/build_game_shading_assignments.py",
        )
    else:
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_bytes(text_bytes)
        preview_output.write_bytes(preview)
    return table


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true")
    arguments = parser.parse_args()
    try:
        result = build(check=arguments.check)
    except (DerivationError, OSError, KeyError) as error:
        sys.exit("GAME SHADING ASSIGNMENTS FAILED: " + str(error))
    car = result["cars"][0]
    counts = {
        pass_word: len(
            [header for header in car["headers"] if pass_word in header["passes"]]
        )
        for pass_word in PASSES
    }
    print(
        "PASS game-shading assignments: %d draws (%s) on %s (%d Headers: %d pass 4, %d pass 5)"
        % (
            sum(DRAWS.values()),
            ", ".join("%d pass %d" % (DRAWS[p], p) for p in PASSES),
            ", ".join(entry["code"] for entry in result["cars"]),
            len(car["headers"]),
            counts[4],
            counts[5],
        )
    )
