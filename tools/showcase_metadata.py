#!/usr/bin/env python3
"""Read source metadata and icon tints for an explicit dealership fork.

Normal dealership builds do not call this source reader. Existing editable catalogs
are never replaced from recovered metadata.
"""
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
CARS = ROOT / "ford-racing-2" / "cars"
OUT = ROOT / "viewer" / "public"

def sample_icon_rgba(rgba):
    """Prefer opaque saturated pixels; neutral icons use their opaque light pixels.

    This is an illustration colour, not segmentation of the car's painted body.
    Tile padding, headers and clipped edge pixels never enter the sample.
    """
    from collections import Counter
    saturated, neutral = Counter(), Counter()
    for i in range(0, len(rgba), 4):
        r, g, b, alpha = rgba[i:i + 4]
        if alpha < 128 or max(r, g, b) < 40 or (r > 216 and g > 216 and b < 200):
            continue
        bucket = (r >> 4, g >> 4, b >> 4)
        neutral[bucket] += 1
        if max(r, g, b) - min(r, g, b) >= 32:
            saturated[bucket] += 1
    counts = saturated or neutral
    if not counts:
        return None
    rgb, count = counts.most_common(1)[0]
    return {"rgb": [v * 16 + 8 for v in rgb], "count": count,
            "source": "decoded_icon", "selection": "saturated" if saturated else "neutral"}


def body_paint(icon_file, expected_sha256):
    from recover_car_ptg import decode_file, sha256
    data = icon_file.read_bytes()
    if sha256(data) != expected_sha256:
        raise ValueError(f"Menu icon differs from manifest pin: {icon_file}")
    metadata, rgba, _ = decode_file(data, str(icon_file))
    paint = sample_icon_rgba(rgba)
    if paint:
        paint.update({"source_sha256": sha256(data), "rgba_sha256": metadata["source_rgba_sha256"],
                      "dimensions": [metadata["header"]["width"], metadata["header"]["height"]]})
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
def load_source_metadata():
    cars = []
    for mf in sorted(CARS.glob("*/manifest.json")):
        m = json.loads(mf.read_text())
        code = m["car_code"]
        if code not in JEV_STYLE:
            raise ValueError(f"No Jev body-style classification recorded for {code}")
        icon_file = None
        icon_sha256 = None
        for f in m["files"]:
            if "/icon/" in f["dst"] and icon_file is None:
                icon_file = CARS.parent / f["dst"]
                icon_sha256 = f["sha256"]
        paint = body_paint(icon_file, icon_sha256) if icon_file else None
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
