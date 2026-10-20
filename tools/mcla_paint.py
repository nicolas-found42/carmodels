"""Native MCLA ambient paint tables and their bounded static glTF interpretation.

Only the exact ambient-car XML namespace is used. Repeated rows remain in provenance:
this module exposes distinct RGB choices without inventing retail names or player-car joins.
Paint type, selection frequency and game shader execution are not reproduced by glTF PBR.
"""

import copy
import hashlib
import math
import re
import xml.etree.ElementTree as ET

LIMITS = [
    "Native ambient XML vectors are interpreted as linear PBR factors; the original "
    "game colour space and shader response are not established.",
    "Only opaque, untextured AmbientCarPaint materials have a recovered paint channel. "
    "Player CarPaintCustomizable, wheel, caliper, window, neon and secondary-channel bindings remain unavailable.",
    "Paint type, selection frequency, reflections and native finishes have no recovered "
    "PBR translation; no finish controls are supplied.",
]


def paint_materials(doc):
    """Exact, whole-material ambient paint bindings without a guessed texture mask."""
    used = {
        primitive["material"]
        for mesh in doc.get("meshes", [])
        for primitive in mesh["primitives"]
    }
    return [
        i
        for i, material in enumerate(doc["materials"])
        if i in used
        and material.get("extras", {}).get("sourceShader") == "AmbientCarPaint"
        and material.get("alphaMode", "OPAQUE") == "OPAQUE"
        and "baseColorTexture" not in material["pbrMetallicRoughness"]
    ]


def game_paint(doc, palette=None, source=None):
    """Describe proven channels even when the car has no exact native palette join.

    Colour provenance is optional only when no palette was consumed. A source-car
    palette can contribute to the game-wide union even if this GLB has no paint part.
    """
    painted = paint_materials(doc)
    colours = []
    if palette is not None:
        if (
            not isinstance(source, dict)
            or not isinstance(source.get("file"), str)
            or re.fullmatch(
                r"shared/tune/ambients/traffic/(?:va_[a-z0-9_]+|0x[0-9a-f]{8})/"
                r"mcambientcartypecolor\.xml",
                source["file"],
            )
            is None
            or not isinstance(source.get("sha256"), str)
            or re.fullmatch(r"[0-9a-f]{64}", source["sha256"]) is None
        ):
            raise PaintError("ambient palette source identity missing")
        for choice in palette["choices"]:
            identity = (
                source["file"] + ":vColors[" + str(choice["source_rows"][0]) + "]"
            )
            colours.append(
                {
                    "id": "mcla-" + hashlib.sha256(identity.encode()).hexdigest()[:20],
                    "name": source["file"].split("/")[-2]
                    + " / ambient paint %02d" % choice["source_rows"][0],
                    "rgb": list(choice["rgb"]),
                    "source": identity + " (sha256 " + source["sha256"] + ")",
                }
            )
    return {
        "schema": 1,
        "channels": [{"id": "body", "name": "Body paint", "materials": painted}]
        if painted
        else [],
        "colors": colours,
        "limits": list(LIMITS),
    }


class PaintError(ValueError):
    pass


def decode(data):
    """Read mcAmbientCarTypeColor XML, retaining the complete ordered native palette."""
    try:
        if len(data) > 64 * 1024 or b"<!" in data:
            raise ValueError("unsupported ambient paint XML declaration/size")
        root = ET.fromstring(data)
        if (
            root.tag != "mcAmbientCarTypeColor"
            or root.attrib
            or sorted(child.tag for child in root)
            != ["fScale", "iPaintType", "vColors"]
        ):
            raise ValueError("unexpected ambient paint XML fields")
        colours, scale, kind = (
            root.find(name) for name in ("vColors", "fScale", "iPaintType")
        )
        if (
            colours.attrib != {"content": "vector3_array"}
            or list(colours)
            or list(scale)
            or list(kind)
            or set(scale.attrib) != {"value"}
            or set(kind.attrib) != {"value"}
        ):
            raise ValueError("unexpected ambient paint XML attributes")
        values = [float(word) for word in (colours.text or "").split()]
        factor, paint_type = float(scale.attrib["value"]), int(kind.attrib["value"])
        if (
            not values
            or len(values) % 3
            or len(values) > 3 * 256
            or not all(math.isfinite(value) and 0 <= value <= 1 for value in values)
        ):
            raise ValueError("invalid ambient paint RGB rows")
        # Other scales need a new source-backed shader interpretation before export.
        if factor != 1 or not 0 <= paint_type <= 0xFFFF:
            raise ValueError("unsupported ambient paint scale/type")
    except (ET.ParseError, ValueError) as error:
        raise PaintError(str(error)) from None
    rows = [values[i : i + 3] for i in range(0, len(values), 3)]
    choices = []
    for index, rgb in enumerate(rows):
        existing = next((choice for choice in choices if choice["rgb"] == rgb), None)
        if existing is None:
            choices.append({"rgb": rgb, "source_rows": [index]})
        else:
            existing["source_rows"].append(index)
    return {"rows": rows, "scale": factor, "paint_type": paint_type, "choices": choices}


def apply(builder, palette):
    """Bind native ambient choices only to exact AmbientCarPaint shader materials.

    Native vectors become linear PBR factors in this static interpretation. Textures,
    geometry and other shaders retain their original bindings. Row zero is a preview
    convention, rather than a recovered runtime default or paint-selection rule.
    """
    doc = builder.doc
    painted = paint_materials(doc)
    choices = palette["choices"]
    if not painted:
        return 0
    variants = [
        {
            "name": "Ambient paint %02d" % choice["source_rows"][0],
            "extras": {
                "nativeRGB": choice["rgb"],
                "nativePaletteRows": choice["source_rows"],
                "nativePaintType": palette["paint_type"],
            },
        }
        for choice in choices
    ]
    doc.setdefault("extensionsUsed", []).append("KHR_materials_variants")
    doc.setdefault("extensions", {})["KHR_materials_variants"] = {"variants": variants}
    alternatives = {}
    for index in painted:
        original = copy.deepcopy(doc["materials"][index])
        alternatives[index] = []
        for variant, choice in enumerate(choices):
            material = copy.deepcopy(original)
            material["pbrMetallicRoughness"]["baseColorFactor"] = choice["rgb"] + [1.0]
            material["extras"]["nativeAmbientPaintRows"] = choice["source_rows"]
            material["extras"]["nativePaintType"] = palette["paint_type"]
            if variant == 0:
                doc["materials"][index] = material
                alternatives[index].append(index)
            else:
                material["name"] += "/ambient-paint-%02d" % choice["source_rows"][0]
                alternatives[index].append(len(doc["materials"]))
                doc["materials"].append(material)
    for mesh in doc["meshes"]:
        for primitive in mesh["primitives"]:
            if primitive.get("material") in alternatives:
                primitive.setdefault("extensions", {})["KHR_materials_variants"] = {
                    "mappings": [
                        {"material": material, "variants": [variant]}
                        for variant, material in enumerate(
                            alternatives[primitive["material"]]
                        )
                    ]
                }
    return len(choices)
