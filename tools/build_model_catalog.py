#!/usr/bin/env python3
"""Build the multi-game source-model catalog without touching editable dealership models."""
import hashlib
import json
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
PUBLIC=ROOT/'dealership/public'


def model_catalog(public=PUBLIC):
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

if __name__ == '__main__':
    catalog=model_catalog()
    (PUBLIC/'models.json').write_text(json.dumps(catalog,indent=2)+'\n')
    print(f"{len(catalog['cars'])} source models -> {PUBLIC/'models.json'}")
