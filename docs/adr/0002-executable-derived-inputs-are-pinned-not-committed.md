---
status: accepted
---
# Executable-derived inputs are pinned by hash and provisioned separately

The executable, overlay microcode and disassembly, and typed decompilation export are private static inputs. They are provisioned in a local input bundle outside tracked files. Receipts carry their SHA-256 pins, and verifiers reject changed bytes. Repo-owned parser code and tools consume the inputs; no source checkout is required.

This records the existing storage and reproducibility arrangement. It does not establish a legal or publication policy. Committing the inputs is an alternative that could make more checks run from a fresh clone, but that choice has not been made. Checks requiring inputs skip when none are configured; a complete local check must provision them first. Configuration and provisioning are documented in `docs/static-inputs.md`.
