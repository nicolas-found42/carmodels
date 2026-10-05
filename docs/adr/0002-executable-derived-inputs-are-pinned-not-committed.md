---
status: accepted
---
# Executable-derived inputs are pinned by hash, not committed

Inputs derived from the game executable (the overlay microcode and its disassembly, the typed decompilation export, the executable) stay out of the repository; receipts carry their sha256 and `tools/static_inputs.py` locates them through environment variables and refuses an input that differs from its pin. Committing them would make every verifier runnable from a clean clone, but published executable-derived material cannot be taken back. The cost is that checks needing them skip in CI and on any machine without the inputs, so `tools/check.sh` runs those checks only when the three `CARMODELS_*` variables are set.
