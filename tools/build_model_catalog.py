#!/usr/bin/env python3
"""Build the multi-game source-model catalog without touching editable dealership models."""
import hashlib
import json
from pathlib import Path

from import_mc3_catalogs import GAME as MC3_GAME, source_package

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
            if entry.get('asset_kind') == 'native-package' or game == MC3_GAME:
                if game != MC3_GAME:
                    raise ValueError('Unsupported native package game: ' + identifier)
                source_package(entry, index_path.parent)
            elif entry.get('asset_kind') not in (None, 'glb'):
                raise ValueError('Unsupported source asset kind: ' + identifier)
            else:
                data = model.read_bytes()
                if hashlib.sha256(data).hexdigest() != entry["sha256"] or len(data) != entry["bytes"]:
                    raise ValueError("Model hash/size differs: " + identifier)
            metadata = {key: entry[key] for key in ["code", "sha256", "bytes", "records"]}
            # Exporters can describe source identities without inventing display names.
            for key in ["display_name", "source_profile", "source_variant", "claim_limits", "asset_kind", "native_members"]:
                if key in entry:
                    value = entry[key]
                    if key == "claim_limits":
                        if not isinstance(value, list) or not all(isinstance(item, str) for item in value):
                            raise ValueError("Invalid model claim limits: " + identifier)
                    elif key == 'native_members':
                        if not isinstance(value, int) or isinstance(value, bool) or value < 1:
                            raise ValueError('Invalid native member count: ' + identifier)
                    elif not isinstance(value, str):
                        raise ValueError("Invalid model metadata: " + identifier)
                    metadata[key] = entry[key]
            cars.append({**metadata, "id": identifier, "game": game,
                         "file": model.relative_to(public).as_posix()})
    return {"cars": cars}

if __name__ == '__main__':
    catalog=model_catalog()
    (PUBLIC/'models.json').write_text(json.dumps(catalog,indent=2)+'\n')
    print(f"{len(catalog['cars'])} source entries -> {PUBLIC/'models.json'}")
