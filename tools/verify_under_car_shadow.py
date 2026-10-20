#!/usr/bin/env python3
"""Derive the Ford Racing 2 under-car shadow table from the 35 pinned source GLBs.

Each recovered car carries exactly one record whose material is named UNDER_SHADOW, EX_UNDER_SHADOW2 or
GT90_UNDER_SHADOW. This verifier derives, per car, that record's identity, whether the exported default
scene references it, which exported scenes do, and the alpha of its own texture. The viewer rebuilds the
record for the default view because no exported tree references it; that drawn blend is a candidate,
since no capture in the repo covers this quad. A static derivation is not execution evidence: nothing
here establishes the game's blend function for the quad, only the exported data it would have to use.

Receipt: research/evidence/under-car-shadow/table.json.
"""

import argparse
import hashlib
import json
from pathlib import Path
import re
import struct
import sys

from bake_models import accessor, read_glb
from validate_car_mips import parse_png
from verifier_common import finish, make_need, run_controls

ROOT = Path(__file__).resolve().parents[1]
CORPUS = "dealership/public/ford-racing-2"
RECEIPT = ROOT / "research/evidence/under-car-shadow/table.json"
SCHEMA = "fr2-under-car-shadow-table/v1"
CARS = 35
# The viewer selects a material by this name shape (dealership/materials.mjs isRecoveredUnderShadow).
SHADOW_NAME = re.compile(r"(^|_)UNDER_SHADOW", re.IGNORECASE)
# The recovered glass path already scales one stored alpha unit as alpha/128; the exporter embeds the
# display-alpha PNG, whose alpha is min(255, 2a) over a stored 0..127, so its own alpha is that scale.
DISPLAY_ALPHA_DOUBLED = "the embedded PNG is the display-alpha conversion min(255, 2a) of the stored 0..127 alpha"
CLAIM_LIMITS = [
    "Static derivation from the committed source GLBs: record identity, exported scene membership and texture alpha only.",
    "No capture covers this quad, so the game blend function, its colour source and depth behaviour are not established here.",
    "The viewer blend is a candidate reading of the texture alpha, not a traced GS blend.",
    "Exporting the record into a tree would change the sha-pinned source GLBs, so the viewer rebuilds it at load time.",
]


class ShadowError(Exception):
    pass


def scene_records(doc, index):
    """The geometry records an exported scene reaches through its node tree."""
    seen, records, stack = set(), set(), list(doc["scenes"][index].get("nodes", []))
    while stack:
        current = stack.pop()
        if current in seen:
            continue
        seen.add(current)
        node = doc["nodes"][current]
        record = node.get("extras", {}).get("geometryRecord")
        if record is not None:
            records.add(record)
        stack.extend(node.get("children", []))
    return records


def shadow_records(doc):
    """Every (node, primitive, material) whose material name has the recovered under-car shadow shape."""
    found = []
    for node_index, node in enumerate(doc["nodes"]):
        if node.get("mesh") is None:
            continue
        for primitive_index, primitive in enumerate(
            doc["meshes"][node["mesh"]]["primitives"]
        ):
            source = doc["materials"][primitive["material"]]
            if SHADOW_NAME.search(source.get("name") or ""):
                found.append((node_index, primitive_index, primitive, source))
    return found


def node_transform(node):
    if "matrix" in node:
        return "matrix"
    return (
        "trs"
        if any(key in node for key in ("translation", "rotation", "scale"))
        else "none"
    )


def texture_facts(doc, binary, primitive, source):
    contract = source.get("pbrMetallicRoughness", {}).get("baseColorTexture")
    require = make_need(ShadowError)
    require(contract is not None, "the shadow material must sample a texture")
    image = doc["textures"][contract["index"]]["source"]
    view = doc["bufferViews"][doc["images"][image]["bufferView"]]
    start = view.get("byteOffset", 0)
    png = binary[start : start + view["byteLength"]]
    width, height, pixels = parse_png(png)
    require(width == height == 64, "the under-car shadow texture is 64x64")
    alphas = pixels[3::4]
    require(
        min(alphas) == 0 and max(alphas) > 0,
        "the under-car shadow texture must carry graded alpha",
    )
    return {
        "name": doc["images"][image].get("name"),
        "sha256": hashlib.sha256(png).hexdigest(),
        "bytes": len(png),
        "width": width,
        "height": height,
        "alpha_min": min(alphas),
        "alpha_max": max(alphas),
        "alpha_distinct": len(set(alphas)),
        "alpha_all_even": all(value % 2 == 0 for value in alphas),
        "stored_alpha_max_reading": max(alphas) // 2,
        "rgb_white": set(zip(pixels[0::4], pixels[1::4], pixels[2::4]))
        == {(255, 255, 255)},
        "alpha_scale": DISPLAY_ALPHA_DOUBLED,
    }


def plane_facts(doc, binary, primitive):
    """The record is the car's ground-contact plane: one Y for every vertex, normals pointing up."""
    positions = accessor(doc, binary, primitive["attributes"]["POSITION"], 3, 5126)
    heights = {round(position[1], 5) for position in positions}
    normals = (
        accessor(doc, binary, primitive["attributes"]["NORMAL"], 3, 5126)
        if "NORMAL" in primitive["attributes"]
        else []
    )
    upright = (
        all(abs(abs(normal[1]) - 1) < 1e-3 for normal in normals) if normals else None
    )
    return {
        "single_height": len(heights) == 1,
        "height": min(heights),
        "normals_upright": upright,
    }


def derive(inputs):
    """Per-car under-car shadow table, derived only from the supplied bytes."""
    require = make_need(ShadowError)
    glbs, manifests = inputs["glbs"], inputs["manifests"]
    require(len(glbs) == CARS, "expected the %d Ford Racing 2 source GLBs" % CARS)
    rows = []
    for code in sorted(glbs):
        data = glbs[code]
        digest = hashlib.sha256(data).hexdigest()
        manifest = json.loads(manifests[code])
        require(manifest.get("car") == code, "%s: manifest identity" % code)
        pins = [asset for asset in manifest["assets"] if asset["kind"] == "glb"]
        require(len(pins) == 1, "%s: one GLB pin in the manifest" % code)
        require(
            pins[0]["path"] == "%s/%s.glb" % (CORPUS, code),
            "%s: manifest GLB path" % code,
        )
        require(
            pins[0]["sha256"] == digest and pins[0]["bytes"] == len(data),
            "%s: GLB differs from its manifest pin" % code,
        )
        doc, binary = read_glb(data)
        require(doc.get("extras", {}).get("car") == code, "%s: model identity" % code)
        scene_index = doc["scene"]
        scene = doc["scenes"][scene_index]
        require(
            scene.get("extras", {}).get("visibilityPreset") == "low_speed",
            "%s: the default scene is the low-speed tree" % code,
        )
        default_records = scene_records(doc, scene_index)
        found = shadow_records(doc)
        require(found, "%s: no under-car shadow material in this car" % code)
        require(len(found) == 1, "%s: more than one under-car shadow record" % code)
        node_index, primitive_index, primitive, source = found[0]
        require(
            "TEXCOORD_0" in primitive["attributes"],
            "%s: the shadow record needs its own UVs to sample the texture alpha"
            % code,
        )
        record = doc["nodes"][node_index]["extras"].get("geometryRecord")
        require(
            record is not None, "%s: the shadow record needs a geometry record" % code
        )
        display = [
            asset
            for asset in manifest["assets"]
            if asset["kind"] == "model_texture_display"
            and asset["texture_name"]
            == doc["images"][
                doc["textures"][
                    source["pbrMetallicRoughness"]["baseColorTexture"]["index"]
                ]["source"]
            ].get("name")
        ]
        require(
            len(display) == 1, "%s: the shadow display PNG is in the manifest" % code
        )
        texture = texture_facts(doc, binary, primitive, source)
        texture["matches_manifest_display_png"] = (
            display[0]["sha256"] == texture["sha256"]
        )
        rows.append(
            {
                "code": code,
                "glb": {
                    "path": "%s/%s.glb" % (CORPUS, code),
                    "bytes": len(data),
                    "sha256": digest,
                },
                "default_scene": {"index": scene_index, "name": scene.get("name")},
                "material": source.get("name"),
                "gltf_alpha_mode": source.get(
                    "alphaMode", "OPAQUE (absent, the glTF default)"
                ),
                "double_sided": bool(source.get("doubleSided")),
                "node": node_index,
                "record": record,
                "primitive": primitive_index,
                "node_transform": node_transform(doc["nodes"][node_index]),
                "vertices": doc["accessors"][primitive["attributes"]["POSITION"]][
                    "count"
                ],
                "triangles": doc["accessors"][primitive["indices"]]["count"] // 3,
                "attributes": sorted(primitive["attributes"]),
                "plane": plane_facts(doc, binary, primitive),
                "in_default_scene": record in default_records,
                "scenes_referencing_record": [
                    index
                    for index in range(len(doc["scenes"]))
                    if record in scene_records(doc, index)
                ],
                "texture": texture,
            }
        )
    return {
        "schema": SCHEMA,
        "rows": len(rows),
        "default_view": "the viewer opens doc.scene (the low-speed tree) and offers every scene but the record layout as a choice",
        "cars": rows,
        "counts": {
            "cars": len(rows),
            "with_shadow_record": sum(1 for row in rows if row["material"]),
            "in_default_scene": sum(1 for row in rows if row["in_default_scene"]),
            "record_layout_only": sum(
                1 for row in rows if row["scenes_referencing_record"] == [0]
            ),
            "alpha_doubled_textures": sum(
                1 for row in rows if row["texture"]["alpha_all_even"]
            ),
            "white_rgb_textures": sum(1 for row in rows if row["texture"]["rgb_white"]),
            "manifest_display_png_equal": sum(
                1 for row in rows if row["texture"]["matches_manifest_display_png"]
            ),
            "single_height_planes": sum(
                1 for row in rows if row["plane"]["single_height"]
            ),
            "upright_normals": sum(
                1 for row in rows if row["plane"]["normals_upright"]
            ),
        },
        "material_names": sorted({row["material"] for row in rows}),
        "blend_state": {
            "original": "not captured",
            "drawn_by_the_viewer": "candidate",
            "reading": "the texture alpha is the blend factor at the recovered alpha/128 scale, and the quad keeps its stored colour; that colour is white in every car, so the blend lightens the studio background rather than darkening it as the game does",
            "capture_note": "the repo capture holds one car and no draw for this quad, so the original blend function, colour source and depth behaviour remain unsettled",
        },
        "claim_limits": CLAIM_LIMITS,
    }


def repack(doc, binary):
    """Rebuild the GLB container around an edited JSON chunk; the binary chunk is unchanged."""
    payload = json.dumps(doc, separators=(",", ":")).encode()
    payload += b" " * (-len(payload) % 4)
    return (
        struct.pack("<3I", 0x46546C67, 2, 12 + 8 + len(payload) + 8 + len(binary))
        + struct.pack("<2I", len(payload), 0x4E4F534A)
        + payload
        + struct.pack("<2I", len(binary), 0x004E4942)
        + binary
    )


def edited(inputs, code, mutate):
    """Apply a mutation to one GLB and re-pin its manifest, so the corpus stays self-consistent and
    the derivation must reject the mutation for its own reason instead of the pin check."""
    doc, binary = read_glb(inputs["glbs"][code])
    mutate(doc)
    data = repack(doc, binary)
    inputs["glbs"][code] = data
    manifest = json.loads(inputs["manifests"][code])
    pin = next(asset for asset in manifest["assets"] if asset["kind"] == "glb")
    pin["sha256"] = hashlib.sha256(data).hexdigest()
    pin["bytes"] = len(data)
    inputs["manifests"][code] = json.dumps(manifest).encode()


def shadow_node(doc):
    """The node carrying the (single) under-car shadow record of a corpus car."""
    found = shadow_records(doc)
    if len(found) != 1:
        raise ShadowError("the control needs exactly one under-car shadow record")
    return found[0][0]


def controls(first, second):
    """Mutations of the pinned corpus that must each be rejected by the derivation it threatens."""

    def into_default_scene(doc):
        doc["scenes"][doc["scene"]]["nodes"].append(shadow_node(doc))

    def duplicate_record(doc):
        doc["nodes"].append(json.loads(json.dumps(doc["nodes"][shadow_node(doc)])))

    def rename_material(doc):
        for source in doc["materials"]:
            if SHADOW_NAME.search(source.get("name") or ""):
                source["name"] = "BODY_PANEL"

    def drop_uvs(doc):
        node = doc["nodes"][shadow_node(doc)]
        for primitive in doc["meshes"][node["mesh"]]["primitives"]:
            if SHADOW_NAME.search(
                doc["materials"][primitive["material"]].get("name") or ""
            ):
                del primitive["attributes"]["TEXCOORD_0"]

    def swap_cars(inputs):
        inputs["glbs"][first], inputs["glbs"][second] = (
            inputs["glbs"][second],
            inputs["glbs"][first],
        )

    def repin(inputs):
        manifest = json.loads(inputs["manifests"][first])
        next(asset for asset in manifest["assets"] if asset["kind"] == "glb")[
            "sha256"
        ] = "0" * 64
        inputs["manifests"][first] = json.dumps(manifest).encode()

    return [
        (
            "shadow record added to the default scene tree",
            lambda inputs: edited(inputs, first, into_default_scene),
        ),
        (
            "second under-car shadow record added",
            lambda inputs: edited(inputs, first, duplicate_record),
        ),
        (
            "shadow material renamed away from its shape",
            lambda inputs: edited(inputs, first, rename_material),
        ),
        ("shadow record loses its UVs", lambda inputs: edited(inputs, first, drop_uvs)),
        ("two cars carry each other's GLB", swap_cars),
        ("one GLB pin replaced", repin),
    ]


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--write",
        action="store_true",
        help="replace the committed receipt with this derivation",
    )
    arguments = parser.parse_args(argv)
    corpus = ROOT / CORPUS
    if not corpus.is_dir():
        print("MISSING INPUT: %s (the committed Ford Racing 2 source GLBs)" % CORPUS)
        return 1
    codes = sorted(path.stem for path in corpus.glob("*.glb"))
    inputs = {
        "glbs": {code: (corpus / (code + ".glb")).read_bytes() for code in codes},
        "manifests": {
            code: (
                ROOT / "games/ford-racing-2/recovered/cars" / code / "manifest.json"
            ).read_bytes()
            for code in codes
        },
    }
    receipt = derive(inputs)
    results = run_controls(
        inputs, controls(codes[0], codes[1]), derive, ShadowError, baseline=receipt
    )
    receipt["tamper_controls"] = {
        result["mutation"]: {
            "rejected": result["rejected"],
            "by": result["by"],
            "reason": result["reason"],
        }
        for result in results
    }
    return finish(
        receipt,
        RECEIPT,
        (["--write"] if arguments.write else []),
        ROOT,
        {
            "schema": SCHEMA,
            "cars": receipt["counts"]["cars"],
            "in_default_scene": receipt["counts"]["in_default_scene"],
            "tamper_controls": len(results),
        },
    )


if __name__ == "__main__":
    sys.exit(main())
