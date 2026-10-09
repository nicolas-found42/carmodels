# Ford Racing 2 — car reference corpus

Vehicle assets and configuration from the PAL PS2 disc (serial SLES-51705), copied out of
the `reverse-engineering` extraction tree and organised one folder per car. Filenames keep
the disc's verbatim form (including the `;1` version suffix).

## Layout

- `cars/<CAR_CODE>/` — one folder per vehicle, named by its `CARDATA.DAT` `:CAR_TYPE` code
  (the join key used across all config files). Contains:
  - `model/<STEM>.PS2;1` — the vehicle model container; named part trees inside
    (WHEEL_*, HUB_*, BRAKE_LIGHTS_*, EXHAUST, ...)
  - `graphics/icon/*.ptg;1` — menu icon (== the car's default livery texture)
  - `graphics/liveries/*.ptg;1` — every livery texture
  - `data/*.DAT;1` — the car's own GAMEPLAY challenge script
  - `config/` — the car's blocks extracted verbatim from the shared config files:
    `cardata.txt` (its CARDATA record), `body.txt`, `engine.txt`, `setup.txt`,
    `sound.txt`, `gearbox.txt`, `brake.txt`, `tyres_front.txt`, `tyres_back.txt`, `control.txt`, `overlay.txt`
  - `manifest.md` / `manifest.json` — provenance and sha256 per file
- `_shared/config/` — the shared config `.DAT` files (all cars' blocks combined), incl. `CAMERAS.DAT`
- `_shared/sounds/` — shared sample banks (`car1..8_snd` + `car_gen` `.msb`/`.msh`)
- `_shared/gameplay/` — GAMEPLAY scripts spanning several cars (cups, quick races, attract)
- `inventory.json` — machine-readable index of all 35 cars

35 cars · 35 models ·
136 liveries · 35 icons ·
11 shared config files · 18 shared sound files.

## Notes

- The car code (`:CAR_TYPE`) is the join key: each car's `manifest.json` records every
  cross-reference (body/engine/setup/gearbox/brake/tyre/control/overlay types + sound chain).
- Sound inheritance: car sound blocks (:INHERIT_TYPE) point at base banks `CAR_SND_CAR1..8`,
  which bind `CARn_SOUND_FILE`; the ELF (`SLES_517.05`) contains the matching
  `car1_snd`..`car8_snd` strings, so `carN_snd.msb/.msh` is the shared bank per base block.
- `49_COUPE`..`TAURUS_STOCK_D` etc. — 35 cars total; `MACH1A`/`MACH1S`/`MUST68B`/`TBIRDM`/
  `49MOVIE`/`MACH1_AGENT` are single-livery "movie/agent" variants.

Rebuild: `python3 tools/build_reference.py` from `projects/carmodels/` (self-verifying:
recomputes sha256 for every file at the destination before reporting success).
