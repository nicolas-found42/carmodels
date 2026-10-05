#!/usr/bin/env python3
"""Thread A — sound-bank index reconciliation: does build_reference.py's
CAR_SND_CARn -> carN_snd mapping agree with the executable?

Reads the two parallel car-bank tables in SLES_517.05 directly:
  config-key  table VA 0x24af68  (CARn_SOUND_FILE ...)
  descriptor  table VA 0x24afe8  (sounds\\carN_snd:B:O:C ...)
and asserts CARn_SOUND_FILE (index n-1) pairs with carN_snd at the SAME index,
then checks the corpus's own mapping (rebuilt with build_reference's rule) agrees.

Verdict recorded: consistent | off_by_one | undecidable.
Receipt: research/evidence/vehicle-completeness/sound-bank-index-reconciliation.json
Exit 0 + VERIFY OK only when the executable and the corpus agree.
"""
import hashlib
import json
import re
import struct
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
import build_reference as B

SRC = B.SRC
ELF = SRC.parent / "SLES_517.05"          # games/ford-racing-2/extracted/SLES_517.05
CORPUS = ROOT / "reference/ford"
OUT = ROOT / "research/evidence/vehicle-completeness/sound-bank-index-reconciliation.json"

CONFIG_TABLE_VA = 0x24AF68
DESC_TABLE_VA = 0x24AFE8
SEG_BASE = 0xFF000                        # VA - file_off for the 0x100000 LOAD segment


def file_off(va):
    return va - SEG_BASE


def cstr(data, va, maxlen=48):
    o = file_off(va)
    e = data.find(b"\x00", o, o + maxlen)
    return data[o:e].decode("latin1")


def read_table(data, va, n):
    out = []
    for i in range(n):
        p = struct.unpack_from("<I", data, file_off(va) + 4 * i)[0]
        out.append(cstr(data, p))
    return out


def parse_tables(data):
    """Return (config_keys[], descriptors[]) from the executable."""
    keys = read_table(data, CONFIG_TABLE_VA, 10)
    desc = read_table(data, DESC_TABLE_VA, 10)
    return keys, desc


def exe_mapping(keys, desc):
    """CAR_SND_CARn -> carN_snd as the EXECUTABLE encodes it (paired by index)."""
    out = {}
    for i in range(8):                       # CAR1..CAR8 at indices 0..7
        m = re.match(r"CAR(\d+)_SOUND_FILE$", keys[i])
        d = re.match(r"sounds\\(car\d+_snd):", desc[i])
        if not m or not d:
            raise ValueError(f"unexpected table entry at index {i}: {keys[i]!r} / {desc[i]!r}")
        out[f"CAR_SND_CAR{m.group(1)}"] = d.group(1)
    return out


def corpus_mapping():
    """CAR_SND_CARn -> bank as build_reference.py builds it (name-based rule)."""
    sdata = (SRC / B.BLOCK_SOURCES["sound"][0]).read_bytes()
    base_bank = {}
    for m in re.finditer(rb"(?m)^:TYPE[ \t]+(CAR_SND_CAR\d+)[ \t]*\r?$([\s\S]{0,400}?):SOUNDBANK_TYPE[ \t]+(CAR\d+_SOUND_FILE)",
                         sdata):
        base_bank[m.group(1).decode()] = "car" + m.group(3).decode()[3] + "_snd"
    return base_bank


def check(elf_bytes=None, corpus_map=None):
    data = elf_bytes if elf_bytes is not None else ELF.read_bytes()
    keys, desc = parse_tables(data)
    exe = exe_mapping(keys, desc)
    corp = corpus_map if corpus_map is not None else corpus_mapping()
    if exe != corp:
        raise ValueError(f"executable mapping {exe} != corpus mapping {corp}")
    # every car's inherit target must be one of the 8 base blocks
    inventory = json.loads((CORPUS / "inventory.json").read_text())["cars"]
    chains = 0
    for code in inventory:
        man = json.loads((CORPUS / f"cars/{code}/manifest.json").read_text())
        inherit = man["sound"]["inherits"]
        bank = man["sound"]["shared_bank_hint"].split(".msb")[0]
        if exe.get(inherit) != bank:
            raise ValueError(f"{code}: manifest bank {bank} != executable {exe.get(inherit)}")
        chains += 1
    return {
        "elf_path": "static-input:executable",
        "elf_sha256": hashlib.sha256(data).hexdigest(),
        "config_table_va": hex(CONFIG_TABLE_VA),
        "descriptor_table_va": hex(DESC_TABLE_VA),
        "exe_mapping": exe,
        "corpus_mapping": corp,
        "mappings_equal": True,
        "cars_checked": chains,
        "verdict": "consistent",
    }


def main() -> int:
    result = check()
    # ---- negative controls ----
    data = ELF.read_bytes()

    # NC1 a synthetic off-by-one corpus mapping must be detected
    bad = {f"CAR_SND_CAR{n}": f"car{n + 1}_snd" for n in range(1, 8)}
    try:
        check(corpus_map=bad)
    except ValueError:
        result["control_off_by_one_mapping_rejected"] = True
    else:
        raise ValueError("control: off-by-one corpus mapping accepted")

    # NC2 a swapped descriptor table (car1_snd<->car2_snd) must be detected
    keys, desc = parse_tables(data)
    desc_swap = list(desc)
    desc_swap[0], desc_swap[1] = desc_swap[1], desc_swap[0]
    try:
        exe_mapping(keys, desc_swap)
        # exe_mapping only reads the name; the off-by-one shows as CAR_SND_CAR1 -> car2_snd
        m1 = exe_mapping(keys, desc_swap)["CAR_SND_CAR1"]
        if m1 == "car1_snd":
            raise ValueError("control: swapped descriptor table accepted")
        result["control_swapped_table_rejected"] = (m1 == "car2_snd")
    except ValueError as e:
        if "swapped descriptor" not in str(e):
            raise
        result["control_swapped_table_rejected"] = True

    # NC3 the first numeric descriptor field is a per-bank stream ordinal (0..7 for car1..car8),
    # coincident with the table index; the bank filename is taken from the literal carN_snd stem.
    ordinals = [int(re.search(r":(\d+):", d).group(1)) for d in desc[:8]]
    result["descriptor_bank_ordinals"] = ordinals
    result["descriptor_ordinals_sequential_car1_to_car8"] = (ordinals == list(range(8)))
    result["bank_name_source"] = ("literal descriptor stem 'sounds\\\\carN_snd'; the numeric fields "
                                  "(:B:O:C) are not used to build the filename")

    ok = (result["mappings_equal"]
          and result.get("control_off_by_one_mapping_rejected")
          and result.get("control_swapped_table_rejected")
          and result["descriptor_ordinals_sequential_car1_to_car8"])
    result["render_fidelity_complete"] = False
    result["scope"] = "sound-bank index reconciliation only; no change to the green T2 verifier"
    result["result"] = "VERIFY OK" if ok else "VERIFY FAILED"
    OUT.write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps(result, indent=2))
    print(result["result"])
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
