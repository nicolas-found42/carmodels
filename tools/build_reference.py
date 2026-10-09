#!/usr/bin/env python3
"""Build the Ford Racing 2 per-car reference corpus.

Source : private input bundle: games/ford-racing-2/extracted/files  (990 files extracted
         from the PAL PS2 disc's FILES.HDR/FILES.DAT container; serial SLES-51705)
Dest   : projects/carmodels/ford-racing-2

Layout (one folder per car, keyed by the CARDATA.DAT :CAR_TYPE code):

  cars/<CODE>/
    model/     <STEM>.PS2;1              - the vehicle model container (verbatim)
    graphics/
      icon/    <default>.ptg;1           - menu icon (GRAPHICS/GAME/CARS)
      liveries/<a..z>.ptg;1              - every VALID_LIVERY texture (GRAPHICS/GAME/LIVERY)
    data/      <OWN>.DAT;1               - its own GAMEPLAY challenge script
    config/    cardata.txt body.txt engine.txt setup.txt sound.txt gearbox.txt
               brake.txt tyres_front.txt tyres_back.txt control.txt overlay.txt - :TYPE blocks
    manifest.md, manifest.json           - provenance + sha256 per file

  _shared/
    config/     the shared DATA/ASCII/CARS/*.DAT + CAMERAS.DAT (verbatim copies)
    sounds/     car1..8_snd + car_gen .msb/.msh (shared sample banks)
    gameplay/   GAMEPLAY/*.DAT not belonging to a single car (cups, quick races, attract)

Self-verifying: every recorded file's sha256 is recomputed at the destination
before it reports success.

Block-splitting note: :TYPE / :CAR_TYPE block keys are anchored at column 0.
Nested occurrences indented inside blocks (e.g. CARSOUND's :SOUND_INFO
"\\t:TYPE WIND_NOISE", BODYDATA spoilers, TYREDATA skid groups) must NOT split
a block, so patterns are ^:TYPE / ^:CAR_TYPE with no leading whitespace class.
"""
import static_inputs
import hashlib
import json
import re
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path

SRC = static_inputs.bundle_path() / 'games/ford-racing-2/extracted/files'
DST = Path(__file__).resolve().parents[1] / 'ford-racing-2'

CONFIG_DIR = "DATA/ASCII/CARS"
GAMEPLAY_DIR = "DATA/ASCII/GAMEPLAY"
MODEL_DIR = "3DDATA/CARS"
ICON_DIR = "GRAPHICS/GAME/CARS"
LIVERY_DIR = "GRAPHICS/GAME/LIVERY"
CAMERA_DIR = "DATA/ASCII/CAMERAS"
SOUNDS_DIR = "SOUNDS"

# code -> model file stem (the stem is also the model's internal name root)
STEM = {
    "49_COUPE": "49COUPE", "49_COUPE_MOVIE": "49MOVIE", "GRAN_TORINO": "G_TORINO",
    "MACH1_AGENT": "MACH1A", "MACH1_SIXTY": "MACH1S", "MUSTANG_68": "MUST68",
    "MUSTANG_68B": "MUST68B", "THUNDERBIRD": "TBIRD", "COBRA": "COBRA",
    "CROWN_VICTORIA": "CROWNV", "FOCUS_SVT": "FOCUSSVT", "FORTYNINE": "FORTYNIN",
    "LIGHTNING_SVT": "LIGHTNIN", "POWERSTROKE": "POWERST", "THUNDERBIRD_2002": "TBIRD2",
    "THUNDERBIRD_MOVIE": "TBIRDM", "EX": "EX", "EXPLORER": "EXPLORER",
    "F100_1956": "F100_56", "F100_1965": "F100_65", "F150": "F150", "F150_2004": "F150_04",
    "F350": "F350", "FOCUS_WRC": "FOCUSWRC", "FOCUS_FR200": "FR200", "FR500": "FR500",
    "FORD_GT": "FORDGT", "GT90": "GT90", "INDIGO": "INDIGO", "MACH3": "MACH3",
    "MUSTANG_CONCEPT": "MUSTCON", "TAURUS_STOCK_A": "TAURUSA", "TAURUS_STOCK_B": "TAURUSB",
    "TAURUS_STOCK_C": "TAURUSC", "TAURUS_STOCK_D": "TAURUSD",
}

# code -> its own GAMEPLAY challenge file
OWN_GAMEPLAY = {
    "49_COUPE": "49COUPE.DAT;1", "49_COUPE_MOVIE": "49MOVIE.DAT;1",
    "GRAN_TORINO": "G_TORINO.DAT;1", "MACH1_AGENT": "MACH1_A.DAT;1",
    "MACH1_SIXTY": "MACH1_S.DAT;1", "MUSTANG_68": "MUST68.DAT;1",
    "MUSTANG_68B": "MUST68B.DAT;1", "THUNDERBIRD": "TBIRD.DAT;1", "COBRA": "COBRA.DAT;1",
    "CROWN_VICTORIA": "CROWNV.DAT;1", "FOCUS_SVT": "FOCUSSVT.DAT;1",
    "FORTYNINE": "FORTY_N.DAT;1", "LIGHTNING_SVT": "LIGHTNIN.DAT;1",
    "POWERSTROKE": "POWERST.DAT;1", "THUNDERBIRD_2002": "TBIRD_22.DAT;1",
    "THUNDERBIRD_MOVIE": "TBIRD_M.DAT;1", "EX": "EX.DAT;1", "EXPLORER": "EXPLORER.DAT;1",
    "F100_1956": "F100_56.DAT;1", "F100_1965": "F100_65.DAT;1", "F150": "F150.DAT;1",
    "F150_2004": "F150_04.DAT;1", "F350": "F350.DAT;1", "FOCUS_WRC": "FOCUSWRC.DAT;1",
    "FOCUS_FR200": "FR200.DAT;1", "FR500": "FR500.DAT;1", "FORD_GT": "FORD_GT.DAT;1",
    "GT90": "GT90.DAT;1", "INDIGO": "INDIGO.DAT;1", "MACH3": "MACH3.DAT;1",
    "MUSTANG_CONCEPT": "MUSTCON.DAT;1", "TAURUS_STOCK_A": "TAURUSA.DAT;1",
    "TAURUS_STOCK_B": "TAURUSB.DAT;1", "TAURUS_STOCK_C": "TAURUSC.DAT;1",
    "TAURUS_STOCK_D": "TAURUSD.DAT;1",
}

SHARED_CONFIG = [
    f"{CONFIG_DIR}/CARDATA.DAT;1", f"{CONFIG_DIR}/BODYDATA.DAT;1",
    f"{CONFIG_DIR}/ENGDATA.DAT;1", f"{CONFIG_DIR}/CARSETUP.DAT;1",
    f"{CONFIG_DIR}/CARSOUND.DAT;1", f"{CONFIG_DIR}/GEARDATA.DAT;1",
    f"{CONFIG_DIR}/BRAKDATA.DAT;1", f"{CONFIG_DIR}/TYREDATA.DAT;1",
    f"{CONFIG_DIR}/CTRLDATA.DAT;1", f"{CONFIG_DIR}/OVERDATA.DAT;1",
    f"{CAMERA_DIR}/CAMERAS.DAT;1",
]

# per-car config block sources: extract name -> (source .DAT, col-0 block pattern, CARDATA field)
BLOCK_SOURCES = {
    "body":    (f"{CONFIG_DIR}/BODYDATA.DAT;1",  rb"(?m)^:TYPE[ \t]+(\S+)",  "CAR_BODY_TYPE"),
    "engine":  (f"{CONFIG_DIR}/ENGDATA.DAT;1",   rb"(?m)^:TYPE[ \t]+(\S+)",  "CAR_ENGINE_TYPE"),
    "setup":   (f"{CONFIG_DIR}/CARSETUP.DAT;1",  rb"(?m)^:CAR_TYPE[ \t]+(\S+)[ \t]*\r?$", "CAR_SETUP_TYPE"),
    "sound":   (f"{CONFIG_DIR}/CARSOUND.DAT;1",  rb"(?m)^:TYPE[ \t]+(\S+)",  "CAR_SOUND_TYPE"),
    "gearbox": (f"{CONFIG_DIR}/GEARDATA.DAT;1",  rb"(?m)^:TYPE[ \t]+(\S+)",  "CAR_GEARBOX_TYPE"),
    "brake":   (f"{CONFIG_DIR}/BRAKDATA.DAT;1",  rb"(?m)^:TYPE[ \t]+(\S+)",  "CAR_BRAKE_TYPE"),
    "control": (f"{CONFIG_DIR}/CTRLDATA.DAT;1",  rb"(?m)^:TYPE[ \t]+(\S+)",  "CAR_CONTROL_TYPE"),
    "overlay": (f"{CONFIG_DIR}/OVERDATA.DAT;1",  rb"(?m)^:TYPE[ \t]+(\S+)",  "CAR_OVERLAY_TYPE"),
}
TYRE_SOURCE = (f"{CONFIG_DIR}/TYREDATA.DAT;1", rb"(?m)^:TYPE[ \t]+(\S+)")

CAR_TYPE_RX = rb"(?m)^:CAR_TYPE[ \t]+(\S+)[ \t]*\r?$"

SPLIT_RX = re.compile(rb"\r\n|\n")


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def block_spans(data: bytes, pattern: bytes):
    """Find col-0 block keys; return key -> (start, end) span up to the next key."""
    ms = list(re.finditer(pattern, data))
    out = {}
    for i, m in enumerate(ms):
        end = ms[i + 1].start() if i + 1 < len(ms) else len(data)
        out[m.group(1).decode("ascii", "replace")] = (m.start(), end)
    return out


def clean_block(raw: bytes) -> bytes:
    """Trim trailing blank / //-comment lines; keep the block itself verbatim (CRLF)."""
    lines = SPLIT_RX.split(raw)
    while lines:
        t = lines[-1].strip()
        if t == b"" or t.startswith(b"//"):
            lines.pop()
        else:
            break
    return b"\r\n".join(lines) + b"\r\n"


def field(block: bytes, key: str):
    m = re.search(rb"(?m)^:" + key.encode() + rb"[ \t]+(.+?)\r?$", block)
    return m.group(1).decode("ascii", "replace").strip() if m else None


def main() -> int:
    if not SRC.is_dir():
        print(f"FAIL: source tree missing: {SRC}")
        return 2

    # ---------- parse CARDATA ----------
    cardata_bytes = (SRC / f"{CONFIG_DIR}/CARDATA.DAT;1").read_bytes()
    car_spans = block_spans(cardata_bytes, CAR_TYPE_RX)
    cars = []
    for code, (s, e) in car_spans.items():
        blk = cardata_bytes[s:e]
        liveries = [(m.group(1).decode(), m.group(2).decode())
                    for m in re.finditer(rb"(?m)^:VALID_LIVERY[ \t]+(\S+)[ \t]+(\S+)[ \t]*\r?$", blk)]
        perf = {m.group(1).decode(): m.group(2).decode()
                for m in re.finditer(rb"(?m)^:CAR_PERFORMANCE[ \t]+(\w+)[ \t]+([\d.]+)[ \t]*\r?$", blk)}
        cars.append({
            "code": code, "span": (s, e),
            "body": field(blk, "CAR_BODY_TYPE"), "engine": field(blk, "CAR_ENGINE_TYPE"),
            "setup": field(blk, "CAR_SETUP_TYPE"), "sound": field(blk, "CAR_SOUND_TYPE"),
            "gearbox": field(blk, "CAR_GEARBOX_TYPE"), "brake": field(blk, "CAR_BRAKE_TYPE"),
            "tyre_front": field(blk, "CAR_FRONT_TYRE_TYPE"), "tyre_back": field(blk, "CAR_BACK_TYRE_TYPE"),
            "control": field(blk, "CAR_CONTROL_TYPE"), "overlay": field(blk, "CAR_OVERLAY_TYPE"),
            "group": field(blk, "CAR_GROUP_TYPE"), "icon": field(blk, "ICON_FILENAME"),
            "text_enum": field(blk, "INGAME_TEXT_ENUM"), "year": field(blk, "CAR_MODEL_YEAR"),
            "top_speed": field(blk, "CAR_APPROXIMATE_TOP_SPEED"),
            "liveries": liveries, "perf": perf,
        })
    assert len(cars) == 35, f"expected 35 cars, parsed {len(cars)}"

    # ---------- parse shared config block spans ----------
    parsed = {}
    for name, (rel, pat, _) in BLOCK_SOURCES.items():
        data = (SRC / rel).read_bytes()
        parsed[name] = (rel, data, block_spans(data, pat))
    tyre_rel, tyre_pat = TYRE_SOURCE
    tyre_data = (SRC / tyre_rel).read_bytes()
    parsed["tyres"] = (tyre_rel, tyre_data, block_spans(tyre_data, tyre_pat))

    # ---------- English display names ----------
    tlate = (SRC / "LANGUAGE/tlate_en.dat;1").read_bytes().decode("utf-16-le", "replace")
    txt = {}
    for line in tlate.split("\r\n"):
        line = line.strip("\ufeff").strip()
        if line.startswith("TXT_CARS_") and " " in line:
            k, v = line.split(" ", 1)
            txt[k] = v.strip()

    # ---------- GAMEPLAY reference map ----------
    gameplay_files = sorted(p for p in (SRC / GAMEPLAY_DIR).iterdir() if p.name.endswith(".DAT;1"))
    gameplay_refs = {}
    for p in gameplay_files:
        refs = {m.group(1).decode() for m in re.finditer(rb"(?m)^[ \t]*:CAR_TYPE[ \t]+(\S+)", p.read_bytes())}
        gameplay_refs[p.name] = refs
    own = {OWN_GAMEPLAY[c["code"]] for c in cars}
    shared_gameplay = [p for p in gameplay_files if p.name not in own]

    # ---------- copy + extract ----------
    records = {"cars": {}, "shared": []}

    def copy(src: Path, dst: Path, rec: list):
        assert src.is_file(), f"missing source {src}"
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dst)
        rec.append({"src": str(src.relative_to(SRC)), "dst": str(dst.relative_to(DST)),
                    "bytes": src.stat().st_size, "sha256": sha256(src)})

    for c in cars:
        code = c["code"]
        cdir = DST / "cars" / code
        rec = []
        stem = STEM[code]
        copy(SRC / MODEL_DIR / f"{stem}.PS2;1", cdir / "model" / f"{stem}.PS2;1", rec)
        default_lv = c["liveries"][0][1].lower()
        copy(SRC / ICON_DIR / f"{default_lv}.ptg;1", cdir / "graphics/icon" / f"{default_lv}.ptg;1", rec)
        for _, lv in c["liveries"]:
            copy(SRC / LIVERY_DIR / f"{lv.lower()}.ptg;1", cdir / "graphics/liveries" / f"{lv.lower()}.ptg;1", rec)
        copy(SRC / GAMEPLAY_DIR / OWN_GAMEPLAY[code], cdir / "data" / OWN_GAMEPLAY[code], rec)
        # config block extracts: (fname, source rel path, raw bytes)
        extracts = [("cardata.txt", f"{CONFIG_DIR}/CARDATA.DAT;1", cardata_bytes[c["span"][0]:c["span"][1]])]
        for name, (rel, _, _) in BLOCK_SOURCES.items():
            key = c[name]
            rel, data, spans = parsed[name]
            assert key in spans, f"{code}: {name} type {key!r} unresolved"
            extracts.append((f"{name}.txt", rel, data[spans[key][0]:spans[key][1]]))
        rel, data, spans = parsed["tyres"]
        for side, tkey in (("front", c["tyre_front"]), ("back", c["tyre_back"])):
            assert tkey in spans, f"{code}: tyre type {tkey!r} unresolved"
            extracts.append((f"tyres_{side}.txt", rel, data[spans[tkey][0]:spans[tkey][1]]))
        for fname, src_ref, raw in extracts:
            content = clean_block(raw)
            dstf = cdir / "config" / fname
            dstf.parent.mkdir(parents=True, exist_ok=True)
            dstf.write_bytes(content)
            rec.append({"src": f"{src_ref} [extracted block]",
                        "dst": str(dstf.relative_to(DST)), "bytes": len(content),
                        "sha256": sha256_bytes(content)})
        records["cars"][code] = rec

    for rel in SHARED_CONFIG:
        copy(SRC / rel, DST / "_shared/config" / Path(rel).name, records["shared"])
    for p in sorted((SRC / SOUNDS_DIR).iterdir()):
        if p.name.startswith("car") and (".msb" in p.name or ".msh" in p.name):
            copy(p, DST / "_shared/sounds" / p.name, records["shared"])
    for p in shared_gameplay:
        copy(p, DST / "_shared/gameplay" / p.name, records["shared"])

    # ---------- manifests ----------
    base_bank = {}  # CAR_SND_CARn -> bank stem
    sdata = (SRC / BLOCK_SOURCES["sound"][0]).read_bytes()
    for m in re.finditer(rb"(?m)^:TYPE[ \t]+(CAR_SND_CAR\d+)[ \t]*\r?$([\s\S]{0,400}?):SOUNDBANK_TYPE[ \t]+(CAR\d+_SOUND_FILE)", sdata):
        base_bank[m.group(1).decode()] = "car" + m.group(3).decode()[3] + "_snd"

    for c in cars:
        code = c["code"]
        cdir = DST / "cars" / code
        rec = records["cars"][code]
        name = txt.get(c["text_enum"]) or code
        srel, sdata2, sspans = parsed["sound"]
        inherit = None
        if c["sound"] in sspans:
            s, e = sspans[c["sound"]]
            m = re.search(rb"(?m)^:INHERIT_TYPE[ \t]+(\S+)", sdata2[s:e])
            inherit = m.group(1).decode() if m else None
        bank = base_bank.get(inherit) if inherit else None
        referenced_by = sorted(n for n, refs in gameplay_refs.items()
                               if code in refs and n != OWN_GAMEPLAY[code])
        manifest = {
            "car_code": code, "display_name": name, "text_enum": c["text_enum"],
            "group": c["group"], "model_year": c["year"], "icon_token": c["icon"],
            "liveries": [{"label": lab, "code": lv} for lab, lv in c["liveries"]],
            "performance": c["perf"], "top_speed_mph": c["top_speed"],
            "sound": {"type": c["sound"], "inherits": inherit,
                      "shared_bank_hint": f"{bank}.msb;1, {bank}.msh;1 (in _shared/sounds/)" if bank else None},
            "config_cross_refs": {
                "body_type": c["body"], "engine_type": c["engine"], "setup_type": c["setup"],
                "gearbox_type": c["gearbox"], "brake_type": c["brake"],
                "tyre_front": c["tyre_front"], "tyre_back": c["tyre_back"],
                "control_type": c["control"], "overlay_type": c["overlay"],
            },
            "referenced_by_gameplay": referenced_by,
            "files": rec,
        }
        (cdir / "manifest.json").write_text(json.dumps(manifest, indent=1) + "\n")

        lines = [
            f"# {code} — {name}", "",
            "- Ford Racing 2 (PS2 PAL, serial SLES-51705); extracted from FILES.HDR/FILES.DAT container",
            f"- Group: {c['group']} | Model year: {c['year']} | Top speed (CAR_APPROXIMATE_TOP_SPEED): {c['top_speed']} | Icon token: {c['icon']}",
            f"- Model: `model/{STEM[code]}.PS2;1` ({rec[0]['bytes']} bytes) — named part tree inside (wheels, hubs, lights, exhausts)",
            f"- Sound: `{c['sound']}`" + (f" → inherits `{inherit}`" if inherit else "")
            + (f" → shared bank hint `{bank}.msb/.msh` (see `_shared/sounds/`)" if bank else ""),
            f"- Liveries ({len(c['liveries'])}): " + ", ".join(f"`{lv}` ({lab})" for lab, lv in c["liveries"]),
            "- Config blocks: `config/` — cardata, body, engine, setup, sound, gearbox, brake, tyres_front, tyres_back, control, overlay (11 files)",
            f"- Challenge script: `data/{OWN_GAMEPLAY[code]}`",
        ]
        if referenced_by:
            lines.append("- Also referenced by shared gameplay files: " + ", ".join(f"`{n}`" for n in referenced_by))
        (cdir / "manifest.md").write_text("\n".join(lines) + "\n")

    # ---------- root files ----------
    inventory = {
        "game": "Ford Racing 2 (2003), PAL PS2 CD, serial SLES-51705",
        "source_tree": str(SRC),
        "generated_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "counts": {
            "cars": len(cars),
            "models": sum(1 for v in records["cars"].values() if any("/model/" in f["dst"] for f in v)),
            "liveries": sum(len(c["liveries"]) for c in cars),
            "icons": sum(1 for v in records["cars"].values() if any("/graphics/icon/" in f["dst"] for f in v)),
            "own_gameplay": len(cars),
            "shared_gameplay": len(shared_gameplay),
            "shared_sounds": sum(1 for f in records["shared"] if "/sounds/" in f["dst"]),
            "shared_config": sum(1 for f in records["shared"] if "/config/" in f["dst"]),
            "config_extracts": sum(1 for v in records["cars"].values() for f in v if " [extracted " in f["src"]),
        },
        "cars": {c["code"]: {"display_name": txt.get(c["text_enum"]), "group": c["group"],
                             "model_year": c["year"], "stem": STEM[c["code"]],
                             "directory": f"cars/{c['code']}"} for c in cars},
    }
    (DST / "inventory.json").write_text(json.dumps(inventory, indent=1) + "\n")

    readme = f"""# Ford Racing 2 — car reference corpus

Vehicle assets and configuration from the PAL PS2 disc (serial SLES-51705), copied out of
the pinned local extraction and organised one folder per car. Filenames keep
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
- `inventory.json` — machine-readable index of all {len(cars)} cars

{inventory['counts']['cars']} cars · {inventory['counts']['models']} models ·
{inventory['counts']['liveries']} liveries · {inventory['counts']['icons']} icons ·
{inventory['counts']['shared_config']} shared config files · {inventory['counts']['shared_sounds']} shared sound files.

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
"""
    (DST / "README.md").write_text(readme)

    # ---------- verification ----------
    errors, checked = [], 0
    all_recs = [r for v in records["cars"].values() for r in v] + records["shared"]
    for r in all_recs:
        f = DST / r["dst"]
        if not f.is_file():
            errors.append(f"missing {r['dst']}")
        elif f.stat().st_size != r["bytes"]:
            errors.append(f"size mismatch {r['dst']}")
        elif sha256(f) != r["sha256"]:
            errors.append(f"sha256 mismatch {r['dst']}")
        else:
            checked += 1

    log_lines = [
        f"Ford Racing 2 car reference build — {datetime.now(timezone.utc).isoformat(timespec='seconds')}",
        f"source: {SRC}",
        f"dest:   {DST}",
        f"cars: {len(cars)} | files recorded: {len(all_recs)} | sha256 verified: {checked}",
        f"errors: {len(errors)}",
    ] + ([f"  ERR {e}" for e in errors] if errors else ["  all sha256 checks passed"])
    (DST / "extraction-log.txt").write_text("\n".join(log_lines) + "\n")

    print("\n".join(log_lines))
    print("BUILD OK" if not errors else "BUILD FAILED")
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
