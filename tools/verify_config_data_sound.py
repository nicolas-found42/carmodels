#!/usr/bin/env python3
"""T2 — config / data-DAT / sound parity verifier (independent, destination-side).

Parity audit for the per-car config extracts, the per-car GAMEPLAY data DAT, and
the per-car sound-bank inheritance chain.

It is NOT a re-extraction: it reuses build_reference.py's parsing primitives
(block_spans / clean_block / field + the col-0 block patterns) and asserts that
the corpus on disk equals what those parsers derive from the shared source
configs in S, that every recorded file sha256 matches the manifest, that each
car carries exactly one data DAT, and that each car's sound.txt :INHERIT_TYPE
resolves one hop to a base bank whose carN_snd.msb/.msh exist in _shared/sounds.

Scope: 35 cars x config (11 files) + data DAT + sound chain. Geometry/textures/
liveries/GLB are closed by T1. Render fidelity stays out.

Receipt: research/evidence/vehicle-completeness/t2-config-data-sound-validation.json
Exit 0 + "VERIFY OK" only when every equality holds and all negative controls reject.
"""
import hashlib
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
import build_reference as B  # parsing primitives + constants (NOT re-derived)

CORPUS = ROOT / "reference/ford"
SRC = B.SRC
OUT = ROOT / "research/evidence/vehicle-completeness/t2-config-data-sound-validation.json"

CONFIG_NAMES = ["cardata", "body", "engine", "setup", "sound", "gearbox",
                "brake", "tyres_front", "tyres_back", "control", "overlay"]
SHARED_CONFIG_NAMES = [Path(r).name for r in B.SHARED_CONFIG]
BASE_BANK_RX = rb"(?m)^:TYPE[ \t]+(CAR_SND_CAR\d+)[ \t]*\r?$([\s\S]{0,400}?):SOUNDBANK_TYPE[ \t]+(CAR\d+_SOUND_FILE)"


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def read_bytes(path: Path, overrides):
    """Bytes as presented to the checker: an override simulates a mutated corpus."""
    key = str(path)
    if overrides and key in overrides:
        return overrides[key]
    return path.read_bytes()


def check(root: Path, overrides=None, hide=None):
    """Raise ValueError on any divergence; return the parity result dict on success.

    overrides: path -> bytes, simulating mutated file content.
    hide: set of paths treated as absent on disk (existence checks).
    """
    overrides = overrides or {}
    hide = {str(h) for h in (hide or set())}

    def exists(path: Path) -> bool:
        return str(path) not in hide and path.is_file()

    corpus = root / "reference/ford"
    if not SRC.is_dir():
        raise ValueError(f"source tree missing: {SRC}")

    # ---- derive expected config bytes from S, via build_reference's parsers ----
    cardata_bytes = (SRC / f"{B.CONFIG_DIR}/CARDATA.DAT;1").read_bytes()
    car_spans = B.block_spans(cardata_bytes, B.CAR_TYPE_RX)
    cars = sorted(car_spans)
    if len(cars) != 35:
        raise ValueError(f"expected 35 CARDATA cars, parsed {len(cars)}")

    parsed = {}
    for name, (rel, pat, _field) in B.BLOCK_SOURCES.items():
        data = (SRC / rel).read_bytes()
        parsed[name] = (rel, data, B.block_spans(data, pat))
    tyre_rel, tyre_pat = B.TYRE_SOURCE
    tyre_data = (SRC / tyre_rel).read_bytes()
    tyre_spans = B.block_spans(tyre_data, tyre_pat)

    # base sound blocks: CAR_SND_CARn -> bank stem  (same rule as build_reference)
    sdata = (SRC / B.BLOCK_SOURCES["sound"][0]).read_bytes()
    base_bank = {}
    for m in re.finditer(BASE_BANK_RX, sdata):
        base_bank[m.group(1).decode()] = "car" + m.group(3).decode()[3] + "_snd"

    # ---- shared files must be present ----
    for name in SHARED_CONFIG_NAMES:
        if not exists(corpus / "_shared/config" / name):
            raise ValueError(f"missing shared config {name}")

    config_files_checked = 0
    data_files_checked = 0
    sound_chains = 0
    manifest_files_checked = 0

    for code in cars:
        s, e = car_spans[code]
        cardata_block = cardata_bytes[s:e]
        cdir = corpus / "cars" / code

        # expected per-car config bytes from S
        expected = {"cardata": B.clean_block(cardata_block)}
        for name, (rel, _data, spans) in parsed.items():
            key = B.field(cardata_block, B.BLOCK_SOURCES[name][2])
            if key is None or key not in spans:
                raise ValueError(f"{code}: {name} type {key!r} unresolved")
            expected[name] = B.clean_block(parsed[name][1][spans[key][0]:spans[key][1]])
        for side, field_name in (("tyres_front", "CAR_FRONT_TYRE_TYPE"),
                                 ("tyres_back", "CAR_BACK_TYRE_TYPE")):
            key = B.field(cardata_block, field_name)
            if key is None or key not in tyre_spans:
                raise ValueError(f"{code}: {side} type {key!r} unresolved")
            expected[side] = B.clean_block(tyre_data[tyre_spans[key][0]:tyre_spans[key][1]])

        # (1) config x11 txt set equality on disk
        actual_names = {p.name for p in (cdir / "config").iterdir()} if (cdir / "config").is_dir() else set()
        want_names = {f"{n}.txt" for n in CONFIG_NAMES}
        if actual_names != want_names:
            raise ValueError(f"{code}: config file set mismatch {sorted(actual_names)}")

        # (2) each config file equals the S-derived bytes (content + sha256), override-aware
        for name in CONFIG_NAMES:
            path = cdir / "config" / f"{name}.txt"
            got = read_bytes(path, overrides)
            if got != expected[name]:
                raise ValueError(f"{code}: config/{name}.txt != S-derived block")
            if sha256_bytes(got) != sha256_bytes(expected[name]):
                raise ValueError(f"{code}: config/{name}.txt sha256 mismatch")
            config_files_checked += 1

        # (3) exactly one data DAT, named by OWN_GAMEPLAY
        data_dir = cdir / "data"
        data_files = sorted(p.name for p in data_dir.iterdir()) if data_dir.is_dir() else []
        if data_files != [B.OWN_GAMEPLAY[code]]:
            raise ValueError(f"{code}: data DAT set {data_files} != [{B.OWN_GAMEPLAY[code]}]")
        data_files_checked += 1

        # (4) sound inheritance chain resolves to an existing shared bank
        sound_txt = read_bytes(cdir / "config/sound.txt", overrides)
        m = re.search(rb"(?m)^:INHERIT_TYPE[ \t]+(\S+)", sound_txt)
        if not m:
            raise ValueError(f"{code}: no :INHERIT_TYPE in sound.txt")
        inherit = m.group(1).decode()
        bank = base_bank.get(inherit)
        if bank is None:
            raise ValueError(f"{code}: :INHERIT_TYPE {inherit} has no base bank")
        for ext in (".msb;1", ".msh;1"):
            if not exists(corpus / "_shared/sounds" / f"{bank}{ext}"):
                raise ValueError(f"{code}: shared bank {bank}{ext} missing")
        sound_chains += 1

        # (5) manifest records every file with a matching sha256 (disk == manifest)
        man = read_bytes(cdir / "manifest.json", overrides)
        doc = json.loads(man)
        if doc.get("car_code") != code:
            raise ValueError(f"{code}: manifest car_code mismatch")
        recorded = {f["dst"] for f in doc["files"]}
        on_disk = {p.relative_to(corpus).as_posix()
                   for p in cdir.rglob("*")
                   if p.is_file() and p.name not in ("manifest.json", "manifest.md")}
        if recorded != on_disk:
            raise ValueError(f"{code}: manifest file set != disk file set")
        for f in doc["files"]:
            p = corpus / f["dst"]
            d = read_bytes(p, overrides)
            if len(d) != f["bytes"] or sha256_bytes(d) != f["sha256"]:
                raise ValueError(f"{code}: manifest hash/size mismatch {f['dst']}")
            manifest_files_checked += 1

        # (5b) manifest sound hint consistent with the resolved chain
        hint = (doc.get("sound") or {}).get("shared_bank_hint")
        if hint and bank not in hint:
            raise ValueError(f"{code}: manifest sound hint inconsistent with chain")

    if config_files_checked != 35 * 11:
        raise ValueError(f"config files checked {config_files_checked} != 385")
    if data_files_checked != 35 or sound_chains != 35:
        raise ValueError("data/sound car count mismatch")

    return {
        "cars": len(cars),
        "config_files_checked": config_files_checked,
        "config_set_equality": True,
        "config_s_derived_content_equality": True,
        "data_files_checked": data_files_checked,
        "sound_chains_resolved": sound_chains,
        "shared_config_files_present": len(SHARED_CONFIG_NAMES),
        "manifest_files_checked": manifest_files_checked,
        "manifest_disk_parity": True,
    }


def main() -> int:
    root = ROOT
    result = check(root)
    result["result"] = "VERIFY OK"

    # ---- negative controls: each mutation must be rejected ----
    cars = sorted(json.loads((CORPUS / "inventory.json").read_text())["cars"])

    def rejects(label, overrides, marker, hide=None):
        try:
            check(root, overrides, hide=hide)
        except ValueError as e:
            if marker not in str(e):
                raise ValueError(f"control {label}: rejected for the wrong reason: {e}")
            result[f"control_{label}_rejected"] = True
            return
        raise ValueError(f"control {label}: mutation ACCEPTED")

    # NC1 mutated config hash/content
    c0 = CORPUS / f"cars/{cars[0]}/config/cardata.txt"
    mutated = bytearray(c0.read_bytes())
    mutated[-2] ^= 0x01
    rejects("mutated_config_hash", {str(c0): bytes(mutated)}, "!= S-derived block")

    # NC2 cross-car config swap
    c1 = CORPUS / f"cars/{cars[1]}/config/cardata.txt"
    a0, a1 = c0.read_bytes(), c1.read_bytes()
    rejects("cross_car_config_swap", {str(c0): a1, str(c1): a0}, "!= S-derived block")

    # NC3 missing shared sound bank referenced by a resolved chain
    base_snd = json.loads((CORPUS / f"cars/{cars[0]}/manifest.json").read_text())["sound"]["shared_bank_hint"]
    bank0 = base_snd.split(".msb")[0]
    rejects("missing_shared_banks",
            None,
            "shared bank",
            hide={CORPUS / "_shared/sounds" / f"{bank0}.msb;1",
                  CORPUS / "_shared/sounds" / f"{bank0}.msh;1"})

    # NC4 manifest sha tamper (recorded hash no longer matches disk)
    m0 = CORPUS / f"cars/{cars[0]}/manifest.json"
    doc = json.loads(m0.read_bytes())
    doc["files"][0]["sha256"] = "0" * 64
    rejects("manifest_sha_tamper", {str(m0): (json.dumps(doc, indent=1) + "\n").encode()},
            "manifest hash/size mismatch")

    # NC5 manifest tamper via hash override is covered above; broken-chain NC3 covers bank lookup.
    result["controls"] = [k for k in result if k.startswith("control_")]
    result["controls_all_rejected"] = all(result[k] for k in result["controls"])
    result["render_fidelity_complete"] = False
    result["scope"] = ("35 cars x config (11 files) + data DAT + sound chain; "
                       "geometry/textures/liveries/GLB out (T1), render fidelity out")
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps(result, indent=2))
    print("VERIFY OK" if result["controls_all_rejected"] else "VERIFY FAILED")
    return 0 if result["controls_all_rejected"] else 1


if __name__ == "__main__":
    sys.exit(main())
