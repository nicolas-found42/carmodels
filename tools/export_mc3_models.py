#!/usr/bin/env python3
"""Export separate MC3 preview conversions without modifying native extraction."""

import argparse
import copy
import json
from pathlib import Path
import re
import struct
import tempfile

from bake_models import ROOT, bake_car, read_glb
from mc3_model import PROFILE, preview_vehicle, sha, source_path, native_executable
from mc3_paint import add_paint_variants, read_native_appearance, LIMITS as PAINT_LIMITS
from import_mc3_catalogs import regular
from mc3_wheels import scanned_once
from mc3_textures import (
    texture_policy,
    TIRE_ALPHA_NOTE,
    LEGACY_TIRE_ALPHA_NOTE,
    LEGACY_NATIVE_TIRE_ALPHA_NOTE,
    LEGACY_VIEWER_TIRE_ALPHA_NOTE,
)
from mc3_tire_alpha import tire_alpha_translation
from model_png import decode_png

DEFAULT = ROOT / "games/midnight-club-3-remix/recovered-models"


def refresh_tire_materials(reference, output):
    """Reapply tire display policy to pinned conversions without native re-derivation.

    Original binary geometry/images, paint variants and source records stay exact.
    Like a full export, this only publishes to a separate, previously absent folder.
    """
    reference, output = map(Path, (reference, output))
    if reference.resolve().is_relative_to(
        output.resolve()
    ) or output.resolve().is_relative_to(reference.resolve()):
        raise ValueError("tire refresh output must be separate from its input")
    regular(output)
    if output.exists():
        raise ValueError("tire refresh output must not exist")
    index = json.loads(source_path(reference, "index.json").read_text())
    rows, files, seen = [], {}, set()
    for row in index["cars"]:
        code = row["code"]
        if (
            not re.fullmatch(r"vp_[a-z0-9_]+", code)
            or code in seen
            or row["file"] != code + ".glb"
            or row["source_profile"] != PROFILE
        ):
            raise ValueError("invalid tire refresh source identity/profile")
        seen.add(code)
        data = source_path(reference, row["file"]).read_bytes()
        if len(data) != row["bytes"] or sha(data) != row["sha256"]:
            raise ValueError("tire refresh reference hash/size differs")
        doc, binary = read_glb(data)
        if (
            doc.get("extras", {}).get("car") != code
            or doc["extras"].get("source_profile") != PROFILE
            or doc["extras"].get("records") != row.get("records")
        ):
            raise ValueError("tire refresh GLB identity/records differ")
        wheel_bound = {
            p["material"]
            for node in doc["nodes"]
            if node.get("extras", {}).get("nativeWheelComponent") in ("rim", "tire")
            for p in doc["meshes"][node["mesh"]]["primitives"]
        }
        other_bound = {
            p["material"]
            for node in doc["nodes"]
            if "mesh" in node
            and node.get("extras", {}).get("nativeWheelComponent")
            not in ("rim", "tire")
            for p in doc["meshes"][node["mesh"]]["primitives"]
        }
        if wheel_bound & other_bound:
            raise ValueError(
                "wheel/body material sharing requires a separate source export"
            )
        for node in doc["nodes"]:
            if node.get("extras", {}).get("nativeWheelComponent") != "tire":
                continue
            for primitive in doc["meshes"][node["mesh"]]["primitives"]:
                native = primitive["attributes"].get("_MC3_NATIVE_NORMAL")
                position = primitive["attributes"]["POSITION"]
                if (
                    native is None
                    or doc["accessors"][native]["count"]
                    != doc["accessors"][position]["count"]
                ):
                    raise ValueError(
                        "native tire normals missing; full source export required"
                    )
        for i in sorted(wheel_bound):
            doc["materials"][i]["doubleSided"] = False
        bound = {
            p["material"]
            for node in doc["nodes"]
            if node.get("extras", {}).get("nativeWheelComponent") == "tire"
            for p in doc["meshes"][node["mesh"]]["primitives"]
        }
        declared = {
            i
            for i, material in enumerate(doc["materials"])
            if material.get("extras", {}).get("shader_template") == "tire"
        }
        if not bound or bound != declared:
            raise ValueError("tire refresh native shader/geometry ownership differs")
        for i in sorted(bound):
            material = doc["materials"][i]
            record = material["extras"]
            texture = doc["textures"][
                material["pbrMetallicRoughness"]["baseColorTexture"]["index"]
            ]
            image = doc["images"][texture["source"]]
            view = doc["bufferViews"][image["bufferView"]]
            if (
                image.get("uri")
                or image.get("mimeType") != "image/png"
                or view["buffer"] != 0
            ):
                raise ValueError("tire refresh requires embedded native PNG")
            start = view.get("byteOffset", 0)
            _, _, rgba = decode_png(binary[start : start + view["byteLength"]])
            mode, _, note, use = texture_policy(
                record, {**record, "composite": []}, {"rgba": rgba}
            )
            if not use or mode != "OPAQUE":
                raise ValueError(
                    "tire refresh policy did not produce visible opaque rubber"
                )
            material["alphaMode"] = mode
            material["doubleSided"] = False
            material.pop("alphaCutoff", None)
            former = record.get("texture_policy_note")
            record["claim_limits"] = [
                v for v in record.get("claim_limits", []) if v != former
            ]
            record["claim_limits"].append(note)
            record["alpha_mode"], record["texture_policy_note"] = mode, note
        doc["extras"]["tireAlphaTranslation"] = tire_alpha_translation()
        payload = json.dumps(doc, separators=(",", ":"), allow_nan=False).encode()
        payload += b" " * (-len(payload) % 4)
        total = 12 + 8 + len(payload) + 8 + len(binary)
        result = (
            struct.pack("<4sII", b"glTF", 2, total)
            + struct.pack("<I4s", len(payload), b"JSON")
            + payload
            + struct.pack("<I4s", len(binary), b"BIN\0")
            + binary
        )
        if (
            bake_car("MC3_" + code.upper(), result, source_mode=False)["triangleCount"]
            != row["triangle_count"]
        ):
            raise ValueError("tire refresh changed triangle count")
        files[row["file"]] = result
        rows.append(
            {
                **row,
                "bytes": len(result),
                "sha256": sha(result),
                "tire_material_refresh": {
                    "reference_sha256": row["sha256"],
                    "retained_binary_sha256": sha(binary),
                    "geometry_rederived": False,
                    "materials": sorted(bound),
                    "wheel_materials": sorted(wheel_bound),
                },
                "claim_limits": list(
                    dict.fromkeys(
                        [
                            *[
                                v
                                for v in row["claim_limits"]
                                if v
                                not in (
                                    LEGACY_TIRE_ALPHA_NOTE,
                                    LEGACY_NATIVE_TIRE_ALPHA_NOTE,
                                    LEGACY_VIEWER_TIRE_ALPHA_NOTE,
                                )
                            ],
                            TIRE_ALPHA_NOTE,
                        ]
                    )
                ),
            }
        )
    if not rows:
        raise ValueError("tire refresh corpus is empty")
    files["index.json"] = (
        json.dumps({**index, "cars": rows}, indent=1) + "\n"
    ).encode()
    output.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(
        prefix=".mc3-tire-materials-", dir=output.parent
    ) as temp:
        stage = Path(temp) / "models"
        stage.mkdir()
        for name, data in files.items():
            (stage / name).write_bytes(data)
        stage.rename(output)
    return len(rows)


def refresh_appearance(extraction, reference, output):
    """Add native appearance to pinned previews; do not rederive their geometry.

    This path needs no executable. The retained GLB binary, native geometry
    records and wheel evidence remain historical source-bound conversions.
    Outputs go to a separate new directory; existing editions are never replaced.
    """
    extraction, reference, output = map(Path, (extraction, reference, output))
    for source in (extraction, reference):
        if source.resolve().is_relative_to(
            output.resolve()
        ) or output.resolve().is_relative_to(source.resolve()):
            raise ValueError("appearance output must be separate from its inputs")
    regular(output)
    if output.exists():
        raise ValueError("appearance output must not exist")
    index = json.loads(source_path(extraction, "index.json").read_text())
    preview_index = json.loads(source_path(reference, "index.json").read_text())
    rows = preview_index["cars"]
    codes = [row["code"] for row in rows]
    if len(set(codes)) != len(codes) or set(codes) != {
        v["id"] for v in index["vehicles"]
    }:
        raise ValueError("appearance source vehicle coverage differs")
    files, refreshed = {}, []
    for row in rows:
        code = row["code"]
        if (
            not re.fullmatch(r"vp_[a-z0-9_]+", code)
            or row["file"] != code + ".glb"
            or row["source_profile"] != PROFILE
        ):
            raise ValueError("invalid appearance source identity/profile")
        data = source_path(reference, row["file"]).read_bytes()
        if len(data) != row["bytes"] or sha(data) != row["sha256"]:
            raise ValueError("appearance reference hash/size differs")
        doc, binary = read_glb(data)
        if (
            doc.get("extras", {}).get("car") != code
            or doc["extras"].get("source_profile") != PROFILE
        ):
            raise ValueError("appearance reference GLB identity/profile differs")
        before = copy.deepcopy(doc)
        appearance = read_native_appearance(extraction, index, code)
        add_paint_variants(doc, appearance)
        # Fresh full conversions place buffers after appearance metadata too.
        buffers = doc.pop("buffers")
        doc["buffers"] = buffers
        for key in (
            "nodes",
            "accessors",
            "bufferViews",
            "buffers",
            "images",
            "textures",
            "samplers",
        ):
            if doc.get(key) != before.get(key):
                raise ValueError("appearance refresh changed geometry or textures")
        payload = json.dumps(doc, separators=(",", ":"), allow_nan=False).encode()
        payload += b" " * (-len(payload) % 4)
        total = 12 + 8 + len(payload) + 8 + len(binary)
        result = (
            struct.pack("<4sII", b"glTF", 2, total)
            + struct.pack("<I4s", len(payload), b"JSON")
            + payload
            + struct.pack("<I4s", len(binary), b"BIN\0")
            + binary
        )
        if (
            bake_car("MC3_" + code.upper(), result, source_mode=False)["triangleCount"]
            != row["triangle_count"]
        ):
            raise ValueError("appearance refresh changed triangle count")
        files[row["file"]] = result
        refreshed.append(
            {
                **row,
                "bytes": len(result),
                "sha256": sha(result),
                "native_appearance": appearance,
                "appearance_augmentation": {
                    "reference_sha256": row["sha256"],
                    "retained_binary_sha256": sha(binary),
                    "geometry_rederived": False,
                },
                "claim_limits": list(
                    dict.fromkeys([*row["claim_limits"], *PAINT_LIMITS])
                ),
            }
        )
    files["index.json"] = (
        json.dumps({**preview_index, "cars": refreshed}, indent=1) + "\n"
    ).encode()
    output.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(
        prefix=".mc3-appearance-", dir=output.parent
    ) as temp:
        stage = Path(temp) / "models"
        stage.mkdir()
        for name, data in files.items():
            (stage / name).write_bytes(data)
        stage.rename(output)
    return len(refreshed)


def export(extraction=ROOT / "games/midnight-club-3-remix/cars", output=DEFAULT):
    extraction, output = Path(extraction), Path(output)
    regular(output)
    if extraction.resolve().is_relative_to(
        output.resolve()
    ) or output.resolve().is_relative_to(extraction.resolve()):
        raise ValueError("preview export must be separate from native extraction")
    index = json.loads(source_path(extraction, "index.json").read_text())
    identities, manifests = set(), set()
    for car in index["vehicles"]:
        code, manifest = car["id"], car["manifest"]
        if (
            not isinstance(code, str)
            or not re.fullmatch(r"vp_[a-z0-9_]+", code)
            or manifest != code + "/manifest.json"
            or code in identities
            or manifest in manifests
        ):
            raise ValueError("duplicate or invalid native vehicle/output identity")
        source_path(extraction, manifest)
        identities.add(code)
        manifests.add(manifest)
    if not identities:
        raise ValueError("native preview corpus is empty")
    rows, files = [], {}
    executable = native_executable()
    with scanned_once():
        for car in index["vehicles"]:
            manifest = json.loads(source_path(extraction, car["manifest"]).read_text())
            if manifest["id"] != car["id"]:
                raise ValueError("preview manifest identity differs")
            data, evidence = preview_vehicle(extraction, manifest, index, executable)
            code = car["id"]
            baked = bake_car("MC3_" + code.upper(), data, source_mode=False)
            # Export provenance paths remain relative to the repository, never machine-specific.
            rows.append(
                {
                    "code": code,
                    "file": code + ".glb",
                    "source_profile": PROFILE,
                    "bytes": len(data),
                    "sha256": sha(data),
                    "triangle_count": baked["triangleCount"],
                    **evidence,
                }
            )
            files[code + ".glb"] = data
    files["index.json"] = (
        json.dumps({"schema": 1, "cars": rows, "source": index["source"]}, indent=1)
        + "\n"
    ).encode()
    if output.exists():
        expected = set(files)
        actual = {
            p.relative_to(output).as_posix() for p in output.rglob("*") if p.is_file()
        }
        if actual != expected:
            raise ValueError("existing preview export coverage differs")
        for name, data in files.items():
            regular(output / name)
            if (output / name).read_bytes() != data:
                raise ValueError("existing preview export differs; nothing overwritten")
        return 0
    output.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix=".mc3-preview-", dir=output.parent) as temp:
        stage = Path(temp) / "models"
        stage.mkdir()
        for name, data in files.items():
            (stage / name).write_bytes(data)
        stage.rename(output)
    return len(rows)


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument(
        "--extraction", type=Path, default=ROOT / "games/midnight-club-3-remix/cars"
    )
    p.add_argument("--output", type=Path, default=DEFAULT)
    modes = p.add_mutually_exclusive_group()
    modes.add_argument(
        "--appearance-only",
        action="store_true",
        help="augment pinned previews; retain historical geometry",
    )
    modes.add_argument(
        "--tire-materials-only",
        action="store_true",
        help="refresh native tire visibility; retain pinned geometry and image bytes",
    )
    p.add_argument(
        "--reference",
        type=Path,
        default=DEFAULT,
        help="pinned previews for metadata-only refreshes",
    )
    a = p.parse_args()
    if a.tire_materials_only:
        print(
            f"Refreshed {refresh_tire_materials(a.reference, a.output)} pinned MC3 tire materials"
        )
    elif a.appearance_only:
        print(
            f"Augmented {refresh_appearance(a.extraction, a.reference, a.output)} pinned MC3 preview appearances"
        )
    else:
        print(
            f"Exported {export(a.extraction, a.output)} source-bound static MC3 previews"
        )
