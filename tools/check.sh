#!/bin/sh
# Run the offline checks from the repo root: tools/check.sh
# Static-input checks run only when the three CARMODELS_* variables are set (tools/static_inputs.py).
# Add a new verifier or test to the `step` lists below.
cd "$(dirname "$0")/.." || exit 1
status=0
log=$(mktemp)
trap 'rm -f "$log"' EXIT

step() { # label command...
  label=$1; shift
  if "$@" >"$log" 2>&1; then
    printf 'ok    %s  (%s)\n' "$label" "$(tail -n 1 "$log" | cut -c1-80)"
  else
    printf 'FAIL  %s\n' "$label"; tail -n 20 "$log"; status=1
  fi
}

if command -v ruff >/dev/null 2>&1; then
  step "ruff check tools" ruff check tools
elif [ -n "${CI:-}" ]; then
  echo "FAIL  ruff is not installed"; status=1
else
  echo "skip  ruff check tools  (ruff is not installed; pip install ruff)"
fi

step "verify_recovered_asset_index" python3 tools/verify_recovered_asset_index.py
if command -v node >/dev/null 2>&1; then
  step "test_viewer_scenes" node tools/test_viewer_scenes.mjs
else
  echo "skip  test_viewer_scenes  (Node.js is not installed)"
fi
step "test_static_inputs"           python3 tools/test_static_inputs.py
step "test_recovery_inputs"         python3 tools/test_recovery_inputs.py

if python3 tools/static_inputs.py --available; then
  step "verify_config_data_sound" python3 tools/verify_config_data_sound.py
  step "verify_sound_bank_index" python3 tools/verify_sound_bank_index.py
  step "verify_vu_dispatch_map" python3 tools/verify_vu_dispatch_map.py
  step "test_vu_dispatch_map"   python3 tools/test_vu_dispatch_map.py
  step "test_vu1_decode" python3 tools/test_vu1_decode.py
  step "verify_vu_pass_handlers" python3 tools/verify_vu_pass_handlers.py
  step "test_vu_pass_handlers" python3 tools/test_vu_pass_handlers.py
else
  echo "skip  verify_config_data_sound, verify_sound_bank_index, verify_vu_dispatch_map, test_vu_dispatch_map, test_vu1_decode, verify_vu_pass_handlers, test_vu_pass_handlers  (static inputs not set; see CONTRIBUTING.md, Static inputs)"
fi
if python3 tools/verify_vu_handler_dump.py --available; then
  step "verify_vu_handler_dump" python3 tools/verify_vu_handler_dump.py
  step "test_vu_handler_dump" python3 tools/test_vu_handler_dump.py
else
  echo "skip  verify_vu_handler_dump, test_vu_handler_dump  (runtime captures not present; see docs/static-inputs.md)"
fi
if python3 tools/recover_dump_reference_frame.py --available; then
  step "recover_dump_reference_frame" python3 tools/recover_dump_reference_frame.py
  step "test_recover_dump_reference_frame" python3 tools/test_recover_dump_reference_frame.py
else
  echo "skip  recover_dump_reference_frame, test_recover_dump_reference_frame  (GS dumps not present; see docs/static-inputs.md)"
fi
if python3 tools/verify_pass_source_join.py --available; then
  step "verify_pass_source_join" python3 tools/verify_pass_source_join.py
  step "test_pass_source_join" python3 tools/test_pass_source_join.py
else
  echo "skip  verify_pass_source_join, test_pass_source_join  (pinned captures or static inputs not present; see CONTRIBUTING.md)"
fi
exit $status
