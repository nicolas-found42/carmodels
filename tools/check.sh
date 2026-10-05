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
step "verify_config_data_sound"     python3 tools/verify_config_data_sound.py
step "verify_sound_bank_index"      python3 tools/verify_sound_bank_index.py
step "test_static_inputs"           python3 tools/test_static_inputs.py

if python3 tools/static_inputs.py --available; then
  step "verify_vu_dispatch_map" python3 tools/verify_vu_dispatch_map.py
  step "test_vu_dispatch_map"   python3 tools/test_vu_dispatch_map.py
else
  echo "skip  verify_vu_dispatch_map, test_vu_dispatch_map  (static inputs not set; see CONTRIBUTING.md, Static inputs)"
fi
exit $status
