"""Assemble a static GLB preview of one Gran Turismo 4 car from its native CAR4 menu model.

The body, wheel and tire model sets come from the CAR4 file; wheel placement comes from the
spec database (wheelbase, tread, tire size) because the game supplies wheel matrices at
runtime. Every placement rule here is a reading, recorded in the GLB and catalog limits.
"""

import hashlib
import json
import math
import struct

from gt4_model import (
    ModelSet,
    car4_slots,
    car_info,
    collision_bounds,
    factory_models,
    transform,
    walk_model,
)
from mc3_textures import encode_png

PROFILE = "gt4-ps2-static-car-v2"
EXTERNAL_TEXTURE = 511
# Shape kinds 2 (untextured vertex-colour body duplicate, read as a reflection pass) and 5 (shadow)
# are overlays on the lit body, not surfaces of their own.
OVERLAY_KINDS = (2, 5)
ALPHA_REFERENCE = (
    0x20 * 255 // 0x80
)  # pglAlphaFunc1ub(GEQUAL, 0x20) in rescaled 0..255 alpha.
TIRE_INNER, TIRE_OUTER = (
    1.0,
    1.317,
)  # Normalized tire model: bead radius 1, tread radius ~1.317.
LIMITS = [
    "Static showroom (menu) model: render-command LOD 0 and callback branch 0; runtime VM transforms, lamps, damage and animation are not executed.",
    "Wheel placement is a reading of spec-database wheelbase, tread and tire sizes (axles at +/- half wheelbase from the model origin); the game supplies wheel matrices at runtime, including those of body callbacks 11-14 (brake parts).",
    "Factory paint variants apply native Pat0 material/palette patches and Tex1 CLUT selectors; names use exact SpecDB ModelCode/VarOrder joins. Native diffuse factors are clamped to the glTF range; reflections, specular passes and PS2 blending are not reproduced.",
    "Overlay shapes (kind 2 reflection-like duplicates, kind 5 shadows) and flat ground planes are omitted; native coordinates are used unchanged (the car faces -Z, its right side is +X).",
]
PAINT_LIMITS = [
    "Original factory presets use the recovered native texture palettes and material patches. Game-wide colour overrides are unavailable until cross-car palette correspondence and paint channels are recovered.",
    "Independent paint channels and finish controls have not been recovered. A diffuse material factor is not a reusable paint colour: different native presets can share the same factor and change texture pixels instead.",
]


def sha(data):
    return hashlib.sha256(data).hexdigest()


def _normalize(v):
    n = math.sqrt(sum(c * c for c in v))
    return tuple(c / n for c in v) if n > 1e-12 else (0.0, 1.0, 0.0)


def _face_normals(positions, triangles):
    normals = [[0.0, 0.0, 0.0] for _ in positions]
    for a, b, c in triangles:
        pa, pb, pc = positions[a], positions[b], positions[c]
        u = [pb[k] - pa[k] for k in range(3)]
        v = [pc[k] - pa[k] for k in range(3)]
        n = (
            u[1] * v[2] - u[2] * v[1],
            u[2] * v[0] - u[0] * v[2],
            u[0] * v[1] - u[1] * v[0],
        )
        for i in (a, b, c):
            for k in range(3):
                normals[i][k] += n[k]
    return [_normalize(n) for n in normals]


class Builder:
    def __init__(self):
        self.blob = bytearray()
        self.doc = {
            "asset": {"version": "2.0", "generator": PROFILE},
            "scene": 0,
            "scenes": [],
            "nodes": [],
            "meshes": [],
            "materials": [],
            "bufferViews": [],
            "accessors": [],
            "samplers": [
                {"magFilter": 9729, "minFilter": 9729, "wrapS": 33071, "wrapT": 33071},
                {"magFilter": 9729, "minFilter": 9729, "wrapS": 10497, "wrapT": 10497},
            ],
        }
        self.textures, self.materials, self.image_cache = {}, {}, {}

    def view(self, payload):
        self.blob.extend(b"\0" * (-len(self.blob) % 4))
        start = len(self.blob)
        self.blob.extend(payload)
        self.doc["bufferViews"].append(
            {"buffer": 0, "byteOffset": start, "byteLength": len(payload)}
        )
        return len(self.doc["bufferViews"]) - 1

    def accessor(self, rows, kind):
        if kind == "index":
            view = self.view(struct.pack("<%dI" % len(rows), *rows))
            item = {"componentType": 5125, "count": len(rows), "type": "SCALAR"}
        else:
            width = len(rows[0])
            flat = [v for row in rows for v in row]
            if not all(math.isfinite(v) for v in flat):
                raise ValueError("non-finite GLB attribute")
            view = self.view(struct.pack("<%df" % len(flat), *flat))
            item = {
                "componentType": 5126,
                "count": len(rows),
                "type": {2: "VEC2", 3: "VEC3", 4: "VEC4"}[width],
            }
            if kind == "position":
                item["min"] = [min(r[k] for r in rows) for k in range(3)]
                item["max"] = [max(r[k] for r in rows) for k in range(3)]
        item["bufferView"] = view
        self.doc["accessors"].append(item)
        return len(self.doc["accessors"]) - 1

    def texture(self, key, image):
        if key not in self.textures:
            identity = (
                image["width"],
                image["height"],
                image["clamp"],
                sha(image["rgba"]),
            )
            if identity in self.image_cache:
                self.textures[key] = self.image_cache[identity]
                return self.textures[key]
            view = self.view(encode_png(image["width"], image["height"], image["rgba"]))
            doc = self.doc
            doc.setdefault("images", []).append(
                {"bufferView": view, "mimeType": "image/png", "name": key}
            )
            sampler = 0 if all(image["clamp"]) else 1
            doc.setdefault("textures", []).append(
                {"source": len(doc["images"]) - 1, "sampler": sampler}
            )
            self.textures[key] = (
                len(doc["textures"]) - 1,
                min(image["rgba"][3::4]) < ALPHA_REFERENCE,
            )
            self.image_cache[identity] = self.textures[key]
        return self.textures[key]

    def material(self, key, colour, texture=None, mode="OPAQUE", native=None):
        if key not in self.materials:
            pbr = {
                "baseColorFactor": list(colour),
                "metallicFactor": 0.0,
                "roughnessFactor": 0.7,
            }
            entry = {
                "name": key,
                "doubleSided": True,
                "pbrMetallicRoughness": pbr,
                "alphaMode": "OPAQUE",
            }
            if native is not None:
                entry["extras"] = {"gt4_material": native}
            if texture is not None:
                pbr["baseColorTexture"] = {"index": texture[0]}
                # Default GT4 state: alpha test GEQUAL 0x20 (of 0x80) with depth writes; glass is drawn
                # with depth writes off. Texture alpha otherwise feeds the reflection pass, not opacity.
                if mode == "BLEND":
                    entry["alphaMode"] = "BLEND"
                elif mode == "MASK" and texture[1]:
                    entry["alphaMode"] = "MASK"
                    entry["alphaCutoff"] = ALPHA_REFERENCE / 255
            self.doc["materials"].append(entry)
            self.materials[key] = len(self.doc["materials"]) - 1
        return self.materials[key]

    def finish(self):
        self.doc["buffers"] = [{"byteLength": len(self.blob)}]
        payload = json.dumps(self.doc, separators=(",", ":"), allow_nan=False).encode()
        payload += b" " * (-len(payload) % 4)
        self.blob.extend(b"\0" * (-len(self.blob) % 4))
        length = 12 + 8 + len(payload) + 8 + len(self.blob)
        return (
            struct.pack("<4sII", b"glTF", 2, length)
            + struct.pack("<I4s", len(payload), b"JSON")
            + payload
            + struct.pack("<I4s", len(self.blob), b"BIN\0")
            + bytes(self.blob)
        )


def weld(group, textured, coloured):
    """Strips repeat their shared vertices; merge exact duplicates (all attributes equal)."""
    keys, remap, out = (
        {},
        [],
        {"positions": [], "normals": [], "uvs": [], "colours": []},
    )
    for i, position in enumerate(group["positions"]):
        key = (
            position,
            group["normals"][i],
            group["uvs"][i] if textured else None,
            group["colours"][i] if coloured else None,
        )
        if key not in keys:
            keys[key] = len(out["positions"])
            out["positions"].append(position)
            out["normals"].append(group["normals"][i])
            if textured:
                out["uvs"].append(group["uvs"][i])
            if coloured:
                out["colours"].append(group["colours"][i])
        remap.append(keys[key])
    group.update(out)
    group["indices"] = [remap[i] for i in group["indices"]]


def model_mesh(
    builder,
    ms,
    label,
    models,
    vertex_fn=None,
    mirror=False,
    callbacks=None,
    paints=None,
):
    """Merge draws of the given models into one glTF mesh grouped by material/texture."""
    groups, stats = (
        {},
        {
            "shapes": 0,
            "triangles": 0,
            "omitted_flat_shapes": 0,
            "omitted_overlay_shapes": 0,
        },
    )
    paints = paints or [ms]
    materials = [paint.materials() for paint in paints]
    images = {}
    for model in models:
        for shape_index, table, matrix, state in walk_model(
            ms, model, 0, callback_matrices=callbacks
        ):
            shape = ms.shape(shape_index)
            # Kind-0 shapes drawn with depth writes off carry no MDLS material: they redraw body
            # geometry the same frame already drew, which reads as dark blotches over the paint.
            if shape["kind"] in OVERLAY_KINDS or (
                shape["kind"] == 0 and not state["depth_mask"]
            ):
                stats["omitted_overlay_shapes"] += 1
                continue
            world = [
                [transform(matrix, p) for p in packet["positions"]]
                for packet in shape["packets"]
            ]
            ys = [p[1] for packet in world for p in packet]
            if ys and max(ys) - min(ys) < 1e-3:
                stats["omitted_flat_shapes"] += 1
                continue
            stats["shapes"] += 1
            for packet, positions in zip(shape["packets"], world):
                if vertex_fn:
                    positions = [vertex_fn(p) for p in positions]
                texture = packet["texture"]
                tex_key = None
                if texture and texture != EXTERNAL_TEXTURE and packet["uvs"]:
                    tex_key = f"{label}/set{table}/tex{texture - 1}"
                    if tex_key not in images:
                        images[tex_key] = [
                            paint.texture_set(0, table).image(texture - 1, colour)
                            for colour, paint in enumerate(paints)
                        ]
                material_index = (
                    packet["material"] - 1
                )  # Packet IDs are one-based; 0 means none.
                if material_index >= ms.material_count:
                    raise ValueError("packet material index outside MDLS")
                key = (
                    tex_key,
                    material_index,
                    bool(packet["colours"]),
                    "BLEND"
                    if not state["depth_mask"]
                    else "MASK"
                    if state["alpha_test"]
                    else "OPAQUE",
                )
                group = groups.setdefault(
                    key,
                    {
                        "positions": [],
                        "normals": [],
                        "uvs": [],
                        "colours": [],
                        "indices": [],
                    },
                )
                base = len(group["positions"])
                if mirror:
                    positions = [(-x, y, z) for x, y, z in positions]
                normals = packet["normals"] if packet["normals"] else None
                group["positions"].extend(positions)
                if normals:
                    rotated = [
                        _normalize(
                            [
                                n[0] * matrix[0] + n[1] * matrix[4] + n[2] * matrix[8],
                                n[0] * matrix[1] + n[1] * matrix[5] + n[2] * matrix[9],
                                n[0] * matrix[2] + n[1] * matrix[6] + n[2] * matrix[10],
                            ]
                        )
                        for n in normals
                    ]
                    group["normals"].extend(
                        [(-n[0], n[1], n[2]) if mirror else tuple(n) for n in rotated]
                    )
                else:
                    group["normals"].extend(
                        _face_normals(positions, packet["triangles"])
                    )
                if tex_key:
                    group["uvs"].extend(tuple(uv) for uv in packet["uvs"])
                if packet["colours"]:
                    group["colours"].extend(tuple(c[:3]) for c in packet["colours"])
                group["indices"].extend(
                    base + i
                    for tri in packet["triangles"]
                    for i in (tri if not mirror else tri[::-1])
                )
                stats["triangles"] += len(packet["triangles"])
    primitives = []
    for (tex_key, material_index, coloured, mode), group in sorted(
        groups.items(), key=lambda kv: (kv[0][0] or "", *kv[0][1:])
    ):
        if not group["indices"]:
            continue
        weld(group, bool(tex_key), coloured)
        if coloured and all(c == (1.0, 1.0, 1.0) for c in group["colours"]):
            coloured, group["colours"] = False, []
        paint_materials = []
        for colour in range(len(paints)):
            key = f"{tex_key or label + '/untextured'}/mat{material_index}{'+vc' if coloured else ''}/{mode}/paint{colour}"
            texture = (
                builder.texture(f"{tex_key}/paint{colour}", images[tex_key][colour])
                if tex_key
                else None
            )
            native = materials[colour][material_index] if material_index >= 0 else None
            factor = (
                native["diffuse"]
                if native
                else (
                    (1.0, 1.0, 1.0, 1.0)
                    if (texture or coloured)
                    else (0.55, 0.55, 0.55, 1.0)
                )
            )
            if not all(math.isfinite(value) for value in factor):
                raise ValueError("non-finite native material factor")
            factor = tuple(max(0.0, min(1.0, value)) for value in factor)
            paint_materials.append(builder.material(key, factor, texture, mode, native))
        attributes = {
            "POSITION": builder.accessor(group["positions"], "position"),
            "NORMAL": builder.accessor(group["normals"], "normal"),
        }
        if tex_key:
            attributes["TEXCOORD_0"] = builder.accessor(group["uvs"], "uv")
        if coloured:
            attributes["COLOR_0"] = builder.accessor(group["colours"], "colour")
        primitives.append(
            {
                "mode": 4,
                "material": paint_materials[0],
                "attributes": attributes,
                "indices": builder.accessor(group["indices"], "index"),
                "extensions": {
                    "KHR_materials_variants": {
                        "mappings": [
                            {"material": material, "variants": [colour]}
                            for colour, material in enumerate(paint_materials)
                        ]
                    }
                },
            }
        )
    if not primitives:
        return None, stats
    builder.doc["meshes"].append({"name": label, "primitives": primitives})
    return len(builder.doc["meshes"]) - 1, stats


def tire_diameter(tire):
    """Metres, from the spec database's tire size (rim inches plus two sidewalls)."""
    diameter = (
        tire["rim_inches"] * 25.4 + 2 * tire["aspect"] / 100 * tire["width_mm"]
    ) / 1000
    if not 0.3 < diameter < 1.5:
        raise ValueError("implausible spec-database tire size")
    return diameter


def wheel_layout(spec):
    """Readings in the native frame, used unchanged in glTF: the car faces -z and its right side is +x; axles at -/+ half wheelbase; wheel centre track = tread - tire width; the ground lies the
    default SUSPENSION ride height below the model origin, so centre height = tire radius - ride height."""
    half_base = spec["wheelbase_mm"] / 2000
    out = []
    for index, (axle, z, tire) in enumerate(
        (
            ("front", -half_base, spec["front_tire"]),
            ("rear", half_base, spec["rear_tire"]),
        )
    ):
        tread = spec["tread_mm"][0 if axle == "front" else 1] / 1000
        width = tire["width_mm"] / 1000
        outer = tire_diameter(tire) / 2
        ground = spec["ride_height_mm"][index] / 1000
        if not 0 <= ground < outer:
            raise ValueError("implausible spec-database ride height")
        rim = min(tire["rim_inches"] * 0.0127, outer * 0.95)
        for side, sign in (("left", -1), ("right", 1)):
            out.append(
                {
                    "name": f"{axle}_{side}",
                    "axle": axle,
                    "side": side,
                    "centre": [sign * (tread - width) / 2, outer - ground, z],
                    "width": width,
                    "outer_radius": outer,
                    "rim_radius": rim,
                }
            )
    return out


def build_car(data, code, spec, source):
    """Return (glb bytes, record) for one CAR4 menu model."""
    slots = car4_slots(data)
    info = car_info(data, slots["car_info"])
    bounds = collision_bounds(data, slots["collision"])
    builder = Builder()
    wheels = wheel_layout(spec)
    body_paints = factory_models(data, slots, "body")
    body = body_paints[0]
    colours = spec["factory_colours"]
    if [paint["index"] for paint in colours] != list(range(len(body_paints))):
        raise ValueError("SpecDB and Pat0 factory colour counts differ")
    # Reading: body callbacks 11-14 load the matrices of the left-front, right-front, left-rear and
    # right-rear wheels for brake parts modelled in wheel-local coordinates. Over 725 cars, the parts
    # of 11/13 sit at local +x and of 12/14 at local -x (inboard only if 11/13 are at -x, the left
    # side), and 11/12 carry the larger discs in 411 cars against 63 (front).
    callbacks = {}
    for parameter, name in zip(
        (11, 12, 13, 14), ("front_left", "front_right", "rear_left", "rear_right")
    ):
        cx, cy, cz = next(w["centre"] for w in wheels if w["name"] == name)
        callbacks[parameter] = (
            1.0,
            0.0,
            0.0,
            0.0,
            0.0,
            1.0,
            0.0,
            0.0,
            0.0,
            0.0,
            1.0,
            0.0,
            cx,
            cy,
            cz,
            1.0,
        )
    body_mesh, body_stats = model_mesh(
        builder,
        body,
        "body",
        range(min(body.model_count, 2)),
        callbacks=callbacks,
        paints=body_paints,
    )
    if body_mesh is None:
        raise ValueError("no drawable body geometry")
    nodes = [{"name": "body", "mesh": body_mesh}]
    parts = {"body": body_stats}
    wheel_paints = factory_models(data, slots, "wheel") if "wheel" in slots else []
    if wheel_paints and len(wheel_paints) != len(body_paints):
        raise ValueError("body and wheel Pat0 colour counts differ")
    wheel_set = wheel_paints[0] if wheel_paints else None
    tire_sets = {
        axle: ModelSet(data, slots[f"tire_{axle}"])
        for axle in ("front", "rear")
        if f"tire_{axle}" in slots
    }
    for axle_index, axle in enumerate(("front", "rear")):
        pair = [w for w in wheels if w["axle"] == axle]
        w, outer, rim = pair[0]["width"], pair[0]["outer_radius"], pair[0]["rim_radius"]

        def place(p, radial, w=w):
            # Local x=0 is the outer face; place() puts it at +x, and nodes on the glTF -x side mirror it.
            x, y, z = p
            return (-(x - 0.5) * w, y * radial, z * radial)

        def tire_vertex(p, w=w, outer=outer, rim=rim):
            x, y, z = p
            r = math.hypot(y, z)
            if r < 1e-9:
                return place(p, rim)
            target = rim + (r - TIRE_INNER) / (TIRE_OUTER - TIRE_INNER) * (outer - rim)
            return place((x, y * target / r, z * target / r), 1.0)

        meshes = []
        if wheel_set is not None:
            model = min(2 * axle_index, wheel_set.model_count - 1)
            meshes.append(
                ("wheel",)
                + model_mesh(
                    builder,
                    wheel_set,
                    f"wheel_{axle}",
                    [model],
                    lambda p, rim=rim, place=place: place(p, rim),
                    mirror=False,
                    paints=wheel_paints,
                )
            )
        if axle in tire_sets:
            meshes.append(
                ("tire",)
                + model_mesh(
                    builder,
                    tire_sets[axle],
                    f"tire_{axle}",
                    [0],
                    tire_vertex,
                    mirror=False,
                )
            )
        for kind, mesh, stats in meshes:
            if mesh is None:
                continue
            parts[f"{kind}_{axle}"] = stats
            for wheel in pair:
                cx, cy, cz = wheel["centre"]
                # Left (-x) wheels mirror the mesh so its outer face points outward.
                nodes.append(
                    {
                        "name": f"{kind}_{wheel['name']}",
                        "mesh": mesh,
                        "translation": [cx, cy, cz],
                        "scale": [-1 if wheel["side"] == "left" else 1, 1, 1],
                    }
                )
    doc = builder.doc
    doc["extensionsUsed"] = ["KHR_materials_variants"]
    doc["extensions"] = {
        "KHR_materials_variants": {
            "variants": [
                {
                    "name": colour["name"]
                    if colour["name"].strip()
                    else f"Native paint {colour['index']}",
                    "extras": {"gt4_factory_colour": colour},
                }
                for colour in colours
            ]
        }
    }
    doc["nodes"] = nodes
    doc["scenes"] = [
        {"name": "Showroom model — static wheels", "nodes": list(range(len(nodes)))}
    ]
    record = {
        "role": "showroom",
        "source": source,
        "parts": parts,
        "triangles": parts["body"]["triangles"]
        + 2 * sum(v["triangles"] for k, v in parts.items() if k != "body"),
        "textures": len(doc.get("images", [])),
        "wheels": wheels,
        "factory_colours": colours,
        "collision_bounds": bounds,
        "tire_pos_related": list(info["tire_pos_related"]),
    }
    doc["extras"] = {
        "source_profile": PROFILE,
        "car": code,
        "name": spec["name"],
        "record": record,
        "claim_limits": LIMITS,
        "gamePaint": {
            "schema": 1,
            "channels": [],
            "colors": [],
            "limits": PAINT_LIMITS,
        },
    }
    return builder.finish(), record
