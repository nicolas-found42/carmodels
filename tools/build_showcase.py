#!/usr/bin/env python3
"""Build the offline viewer data: manifest metadata, Jev silhouette labels, paint samples.

The HTML viewer builds procedural silhouettes from each car's Jev-classified body style and
real manifest performance data. Paint chips use a best-effort opaque-color sample from the
car's menu-icon payload. The current .ptg width/mip decode and original model geometry remain
unresolved, so the viewer labels its bodies as reconstructions and does not display partial
texture decodes as if they were finished.
"""
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CARS = ROOT / "ford-racing-2" / "cars"
OUT = ROOT / "dealership" / "public"


def model_catalog(public=OUT):
    """Combine per-game export indexes, retaining game identity for duplicate car codes."""
    cars = []
    ids = set()
    for index_path in sorted(public.glob("*/index.json")):
        game = index_path.parent.name
        index = json.loads(index_path.read_text())
        for entry in index["cars"]:
            identifier = game + "/" + entry["code"]
            if identifier in ids:
                raise ValueError("Duplicate dealership model: " + identifier)
            ids.add(identifier)
            model = index_path.parent / entry["file"]
            if not model.resolve().is_relative_to(index_path.parent.resolve()):
                raise ValueError("Model outside game folder: " + identifier)
            data = model.read_bytes()
            if hashlib.sha256(data).hexdigest() != entry["sha256"] or len(data) != entry["bytes"]:
                raise ValueError("Model hash/size differs: " + identifier)
            metadata = {key: entry[key] for key in ["code", "sha256", "bytes", "records"]}
            cars.append({**metadata, "id": identifier, "game": game,
                         "file": model.relative_to(public).as_posix()})
    return {"cars": cars}

# ---- body paint color extraction (from the car's menu icon = real game livery) ----
def body_paint(model_file, icon_file):
    """Dominant saturated color from the icon .ptg payload (linear RGBA stream).
    Fallback: palette ramps in the model container."""
    from collections import Counter
    paint = None
    if icon_file and icon_file.exists():
        d = icon_file.read_bytes()
        q = Counter()
        # payload regions = non-0xdd spans >= 2KB
        spans = []
        s = None
        for o in range(0, len(d) - 16, 16):
            nz = any(b != 0xdd for b in d[o:o+16])
            if nz and s is None: s = o
            if not nz and s is not None:
                if o - s >= 2048: spans.append((s, o))
                s = None
        if s is not None and len(d) - s >= 2048: spans.append((s, len(d)))
        for (a, b) in spans:
            raw = d[a:b]
            for i in range(0, len(raw) - 4, 4):
                r, g, bl, al = raw[i], raw[i+1], raw[i+2], raw[i+3]
                if al < 0x80:  # transparent background / dithered edges
                    continue
                mx, mn = max(r, g, bl), min(r, g, bl)
                if mx < 40 or mx - mn < 32:  # skip near-black and grey
                    continue
                # skip the pale-yellow UI background (high R+G, low-ish B, high value)
                if r > 216 and g > 216 and bl < 200:
                    continue
                q[(r >> 4, g >> 4, bl >> 4)] += 1
        if q:
            (rr, gg, bb), cnt = q.most_common(1)[0]
            paint = {"rgb": [rr*16+8, gg*16+8, bb*16+8], "count": cnt, "source": "icon"}
    if paint is None and model_file and model_file.exists():
        d = model_file.read_bytes()
        cands = Counter()
        n = len(d)
        for o in range(0, n - 4, 4):
            r, g, b, a = d[o], d[o+1], d[o+2], d[o+3]
            if a == 0x80 and not (abs(r-g) < 6 and abs(g-b) < 6):
                if max(r, g, b) > 40 and 4 < o < n - 8:
                    cands[(r, g, b)] += 1
        if cands:
            (rgb, cnt), rest = cands.most_common(1)[0], cands.most_common(4)[1:]
            paint = {"rgb": list(rgb), "count": cnt, "source": "model_ramp",
                     "runners": [[list(k), v] for k, v in rest]}
    return paint

# Jev 1.13 batch classification of the 35 manifest descriptions (33 auto, 2 flagged for review).
# The two review cases are resolved from the exact model names: Explorer Sport Trac XLT -> SUV;
# Mustang FR500 -> coupe silhouette (the race-prepped trim does not change the body shell).
JEV_STYLE = {
    "49_COUPE": "coupe", "49_COUPE_MOVIE": "coupe", "COBRA": "coupe",
    "CROWN_VICTORIA": "sedan", "EX": "concept", "EXPLORER": "suv",
    "F100_1956": "pickup", "F100_1965": "pickup", "F150": "pickup", "F150_2004": "pickup", "F350": "pickup",
    "FOCUS_FR200": "hatchback", "FOCUS_SVT": "hatchback", "FOCUS_WRC": "racecar",
    "FORD_GT": "coupe", "FORTYNINE": "concept", "FR500": "coupe", "GRAN_TORINO": "coupe",
    "GT90": "concept", "INDIGO": "concept", "LIGHTNING_SVT": "pickup",
    "MACH1_AGENT": "coupe", "MACH1_SIXTY": "coupe", "MACH3": "concept",
    "MUSTANG_68": "coupe", "MUSTANG_68B": "coupe", "MUSTANG_CONCEPT": "concept",
    "POWERSTROKE": "concept", "TAURUS_STOCK_A": "racecar", "TAURUS_STOCK_B": "racecar",
    "TAURUS_STOCK_C": "racecar", "TAURUS_STOCK_D": "racecar", "THUNDERBIRD": "coupe",
    "THUNDERBIRD_2002": "coupe", "THUNDERBIRD_MOVIE": "coupe",
}

# ---- manifest collection ----
def load_all():
    cars = []
    for mf in sorted(CARS.glob("*/manifest.json")):
        m = json.loads(mf.read_text())
        code = m["car_code"]
        if code not in JEV_STYLE:
            raise ValueError(f"No Jev body-style classification recorded for {code}")
        model_file = None
        icon_file = None
        for f in m["files"]:
            if "/model/" in f["dst"] and model_file is None:
                model_file = CARS.parent / f["dst"]
            if "/icon/" in f["dst"] and icon_file is None:
                icon_file = CARS.parent / f["dst"]
        paint = body_paint(model_file, icon_file)
        perf = m.get("performance", {})
        cars.append({
            "code": code,
            "name": m.get("display_name", code),
            "bodyStyle": JEV_STYLE.get(code, "concept"),
            "group": m.get("group"),
            "year": m.get("model_year"),
            "topSpeed": m.get("top_speed_mph"),
            "bhp": float(perf.get("BHP", 0) or 0),
            "kg": float(perf.get("WEIGHT_IN_KILOS", 0) or 0),
            "agility": float(perf.get("AGILITY", 0) or 0),
            "accel": float(perf.get("ACCELERATION", 0) or 0),
            "speed": float(perf.get("SPEED", 0) or 0),
            "weight": float(perf.get("WEIGHT", 0) or 0),
            "liveries": m.get("liveries", []),
            "paint": paint,
            "sound": m.get("sound", {}).get("shared_bank_hint", ""),
        })
    return cars

if __name__ == "__main__":
    cars = load_all()
    out = OUT / "cars.json"
    out.write_text(json.dumps(cars, indent=1))
    (OUT / "models.json").write_text(json.dumps(model_catalog(), indent=2) + "\n")
    print(f"{len(cars)} cars -> {out}; paint samples: {sum(1 for c in cars if c.get('paint'))}")
