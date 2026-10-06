#!/usr/bin/env python3
"""Regression checks for the dump reference-frame extraction and its controls."""
import copy
import json
from pathlib import Path
import tempfile

import recover_dump_reference_frame as check


def main():
    inputs = check.load_inputs()
    result = check.derive(inputs)
    assert len(result["rows"]) == 2
    race, menu = result["rows"]
    assert race["serial"] == menu["serial"] == "SLES-51705"
    assert race["disc_crc"] == menu["disc_crc"] == "0x37f695cd"
    for row in (race, menu):
        assert (row["width"], row["height"], row["screenshot_bytes"]) == (640, 480, 640 * 480 * 4)
        assert row["state_version"] == 9 and row["png_sha256"] and row["screenshot_sha256"]
        assert row["png_path"].startswith("research/evidence/reference-frames/frames/")
    assert race["screenshot_sha256"] != menu["screenshot_sha256"], "the two dumps embed different frames"
    assert result["render_fidelity_complete"] is False and result["claim_limits"]
    # The compressed pin bites before derivation: a changed dump file fails in load_inputs.
    pinned = copy.deepcopy(inputs)
    pinned["dumps"][0]["data"] += b"x"
    try:
        check.derive(pinned)
    except check.FrameError:
        raise AssertionError("stray trailing byte rejected by derivation, not by the pin")
    with tempfile.NamedTemporaryFile(suffix=".gs.zst") as altered:
        altered.write(check.DUMPS[0]["path"].read_bytes()[:-1] + b"\x00")
        altered.flush()
        original = check.DUMPS[0]["path"]
        try:
            check.DUMPS[0]["path"] = Path(altered.name)
            try:
                check.load_inputs()
            except check.FrameError:
                pass
            else:
                raise AssertionError("changed dump bytes accepted by load_inputs")
        finally:
            check.DUMPS[0]["path"] = original
    controls = check.controls(inputs)
    assert len(controls) == 5 and all(c["rejected"] for c in controls)
    truncate = controls[-1]
    assert "RGBA byte count" in truncate.get("reason", ""), truncate
    result["controls"] = controls
    assert json.loads(check.OUT.read_text()) == result
    print("PASS test_recover_dump_reference_frame: two frames, five intended corruption failures, pin-fired control")


if __name__ == "__main__":
    main()
