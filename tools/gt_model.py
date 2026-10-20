"""Bounded GT1 body LOD / CTEX decoder and static GLB exporter.

Layout corroboration: JeevesGB/GTExplorer 069ab96f8353637a9ffc5c9b23695650e288e8ea
(gtcar.py, gttex.py, gtcar_render.py; MIT notice in tools/gt1/LICENSE).
All declared body LODs are parsed; no permissive vertex/palette fallback is used.
Shared wheel templates are recovered from the source-pinned native executable.
"""

import hashlib
import json
import math
import struct
import zlib

from gt_wheels import (
    POINTER_ADDRESS,
    SOURCE_SHA256,
    UNPACKED_SHA256,
    assemble_wheels,
    load_tables,
)

LIMITS = [
    "Static native body LOD conversion; original game execution and rendered equivalence are unverified.",
    "Static neutral wheel assembly uses the native showroom template; steering, spin and view-dependent game rounding are not reproduced.",
    "Display policy omits wheels from body LODs whose four native anchors all exceed lateral/longitudinal body bounds by more than 0.1m; original special-asset routing is unverified.",
    "Raw UV bytes sample native 256x256 sheets following the community renderer; its OBJ UV convention differs.",
    "Default display uses source colour set 0; every source colour set is available as a material variant.",
    "PS1 semi-transparency, illumination/paint flags and game shading are not reproduced.",
    "Complete native shadow geometry is retained as binary data and omitted from visible body scenes.",
    "Body winding follows stored normals; ambiguous face normals use geometry oriented away from the LOD centroid, a static display heuristic.",
]


def sha(data):
    return hashlib.sha256(data).hexdigest()


class Reader:
    def __init__(self, data, offset=0):
        self.data, self.offset = data, offset

    def read(self, size):
        end = self.offset + size
        if size < 0 or end > len(self.data):
            raise ValueError(f"Truncated GT-CAR at {self.offset}: need {size} bytes")
        raw = self.data[self.offset : end]
        self.offset = end
        return raw

    def unpack(self, fmt):
        return struct.unpack(fmt, self.read(struct.calcsize(fmt)))


def parse_car(data):
    if len(data) < 128 or not data.startswith(b"@(#)GT-CAR\0"):
        raise ValueError("Invalid GT-CAR header")
    reader = Reader(data, 16)
    wheels = [reader.unpack("<4h") for _ in range(4)]
    dimensions = reader.unpack("<4H")
    reader.read(4)
    (count,) = reader.unpack("<H")
    reader.read(66)
    if not 1 <= count <= 8:
        raise ValueError("GT-CAR LOD count outside bound")
    lods = []
    for lod_index in range(count):
        start = reader.offset
        vc, nc, tc, qc = reader.unpack("<4H")
        gtc, gqc = reader.unpack("<2H")
        utc, uqc = reader.unpack("<2H")
        extra_counts = reader.unpack("<2H")
        bounds_min, bounds_max = reader.unpack("<4h"), reader.unpack("<4h")
        scale, unknown_word = reader.unpack("<2H")
        if any(extra_counts):
            raise ValueError("Unsupported GT-CAR textured Gouraud face groups")
        if (
            not 1 <= vc <= 4096
            or not 1 <= nc <= 4096
            or any(x > 8192 for x in [tc, qc, gtc, gqc, utc, uqc])
        ):
            raise ValueError("GT-CAR LOD geometry count outside bound")
        if not 0 <= scale <= 30:
            raise ValueError("GT-CAR scale outside bound")
        factor = 2.0 ** (scale - 16) / 4096
        vertex_offset = reader.offset
        vertices = [
            (x * factor, y * factor, -z * factor)
            for x, y, z, w in (reader.unpack("<4h") for _ in range(vc))
        ]
        normal_offset = reader.offset
        normals = []
        for _ in range(nc):
            x, y, z, w = reader.unpack("<4h")
            length = math.sqrt(x * x + y * y + z * z)
            # Native zero normals are represented explicitly and counted below.
            normals.append(
                (x / length, y / length, -z / length) if length else (0.0, 0.0, 0.0)
            )
        faces = []
        for group, (number, quad, textured) in enumerate(
            [
                (tc, False, False),
                (qc, True, False),
                (gtc, False, "gouraud"),
                (gqc, True, "gouraud"),
                (utc, False, True),
                (uqc, True, True),
            ]
        ):
            for _ in range(number):
                offset = reader.offset
                b = reader.read(16)
                refs = [
                    b[0] + ((b[1] & 1) << 8),
                    (b[1] >> 1) + ((b[2] & 3) << 7),
                    (b[2] >> 2) + ((b[3] & 7) << 6),
                    b[4] + ((b[5] & 1) << 8),
                ]
                nr = [
                    ((b[5] + (b[6] << 8)) >> 1) & 511,
                    ((b[6] + (b[7] << 8)) >> 3) & 511,
                    (b[8] + (b[9] << 8)) & 511,
                    ((b[9] + (b[10] << 8)) >> 2) & 511,
                ]
                corners = 4 if quad else 3
                expected_type = (
                    (0x38 if quad else 0x30)
                    if textured == "gouraud"
                    else (0x2C if quad else 0x24)
                    if textured
                    else (0x28 if quad else 0x20)
                )
                if b[15] & 0xFC != expected_type:
                    raise ValueError(
                        f"GT-CAR face type disagrees with group at {offset}"
                    )
                if any(v >= vc for v in refs[:corners]):
                    raise ValueError(
                        f"GT-CAR face vertex index outside LOD at {offset}"
                    )
                if any(n >= nc for n in nr[:corners]):
                    raise ValueError(
                        f"GT-CAR face normal index outside LOD at {offset}"
                    )
                if any(normals[n] == (0.0, 0.0, 0.0) for n in nr[:corners]):
                    raise ValueError(f"GT-CAR referenced zero normal at {offset}")
                face = {
                    "vertices": refs[:corners],
                    "normals": nr[:corners],
                    "offset": offset,
                    "type": b[15],
                    "colour": list(b[12:15]),
                    "quad": quad,
                    "clut": None,
                    "group": group,
                    "flags": [
                        struct.unpack_from("<I", b)[0] & 0xF8000000,
                        struct.unpack_from("<I", b, 4)[0] & 0x80000000,
                    ],
                }
                if textured == "gouraud":
                    rgb = reader.read(12 if quad else 8)
                    face["corner_colours"] = [list(b[12:15])] + [
                        list(rgb[i : i + 3]) for i in range(0, len(rgb), 4)
                    ]
                elif textured:
                    uv = reader.read(12)
                    pal = struct.unpack_from("<H", uv, 2)[0]
                    clut = (pal >> 4) + (pal & 63)
                    if not 0 <= clut < 16:
                        raise ValueError(
                            f"GT-CAR CLUT outside native sheet at {offset}"
                        )
                    face.update(
                        {
                            "clut": clut,
                            "raw_clut": pal,
                            "uv": [
                                list(uv[0:2]),
                                list(uv[4:6]),
                                list(uv[8:10]),
                                list(uv[10:12]),
                            ][:corners],
                        }
                    )
                face["end"] = reader.offset
                faces.append(face)
        if not faces:
            raise ValueError("GT-CAR LOD has no polygons")
        lods.append(
            {
                "index": lod_index,
                "offset": start,
                "end": reader.offset,
                "scale": scale,
                "vertices": vertices,
                "normals": normals,
                "faces": faces,
                "vertex_offset": vertex_offset,
                "normal_offset": normal_offset,
                "bounds_min": bounds_min,
                "bounds_max": bounds_max,
                "unknown_word": unknown_word,
                "group_counts": [tc, qc, gtc, gqc, utc, uqc, *extra_counts],
                "threshold": struct.unpack_from("<i", data, 0x40 + lod_index * 8)[0],
            }
        )
        if lod_index != count - 1:
            reader.read(40)
    # Native MAIN 0x8007964c relocates a 32-byte header followed by triangle
    # records (three <4h> vertices) then quad records (four <4h> vertices).
    shadow_offset = reader.offset
    triangles, quads, shadow_scale, unknown_word = reader.unpack("<4H")
    bounds_min, bounds_max = reader.unpack("<4h"), reader.unpack("<4h")
    reader.read(8)
    if triangles > 8192 or quads > 8192 or shadow_scale > 30:
        raise ValueError("GT-CAR shadow count/scale outside bound")
    reader.read((triangles * 3 + quads * 4) * 8)
    shadow_end = reader.offset
    trailing = reader.read(len(data) - reader.offset)
    return {
        "lods": lods,
        "wheels": wheels,
        "wheel_dimensions": dimensions,
        "shadow": {
            "offset": shadow_offset,
            "end": shadow_end,
            "triangles": triangles,
            "quads": quads,
            "scale": shadow_scale,
            "bounds_min": bounds_min,
            "bounds_max": bounds_max,
            "unknown_word": unknown_word,
        },
        "trailing_bytes": len(trailing),
        "trailing_sha256": sha(trailing),
    }


def parse_tex(data):
    if len(data) < 0x8060 or not data.startswith(b"@(#)GT-CTEX\0"):
        raise ValueError("Invalid GT-CTEX header")
    (count,) = struct.unpack_from("<H", data, 14)
    if not 1 <= count <= 16 or len(data) != 0x8060 + count * 512:
        raise ValueError("GT-CTEX palette count/length differs")
    palettes = [
        list(struct.unpack_from("<256H", data, 0x8060 + i * 512)) for i in range(count)
    ]
    pixels = bytearray()
    for byte in data[0x60:0x8060]:
        pixels.extend((byte & 15, byte >> 4))
    return {
        "count": count,
        "colour_ids": list(data[16 : 16 + count]),
        "pixels": pixels,
        "palettes": palettes,
        "illumination_masks": list(struct.unpack_from("<16H", data, 32)),
        "paint_masks": list(struct.unpack_from("<16H", data, 64)),
    }


def png(data, clut, colour=0):
    if not 0 <= clut < 16 or not 0 <= colour < data["count"]:
        raise ValueError("GT texture palette selector outside range")
    palette = data["palettes"][colour][clut * 16 : (clut + 1) * 16]
    rgba = [
        bytes(
            (
                (c & 31) << 3,
                ((c >> 5) & 31) << 3,
                ((c >> 10) & 31) << 3,
                0 if c == 0 else 255,
            )
        )
        for c in palette
    ]
    # C-backed channel lookup keeps full-sheet corpus verification inexpensive.
    pixels = bytes(data["pixels"])
    expanded = bytearray(256 * 256 * 4)
    for channel in range(4):
        table = bytes([c[channel] for c in rgba]) + bytes(240)
        expanded[channel::4] = pixels.translate(table)
    raw = b"".join(b"\0" + expanded[y * 1024 : (y + 1) * 1024] for y in range(256))

    def chunk(kind, payload):
        return (
            struct.pack(">I", len(payload))
            + kind
            + payload
            + struct.pack(">I", zlib.crc32(kind + payload) & 0xFFFFFFFF)
        )

    return (
        b"\x89PNG\r\n\x1a\n"
        + chunk(b"IHDR", struct.pack(">2I5B", 256, 256, 8, 6, 0, 0, 0))
        + chunk(b"IDAT", zlib.compress(raw, 9))
        + chunk(b"IEND", b"")
    )


def srgb(v):
    return v / 12.92 if v <= 0.04045 else ((v + 0.055) / 1.055) ** 2.4


def wheel_bounds_fit(car, lod):
    """Conservative display policy for small special-asset LODs, not native routing."""
    bounds = [
        (min(v[i] for v in lod["vertices"]), max(v[i] for v in lod["vertices"]))
        for i in (0, 2)
    ]
    outside = []
    for x, _, z, _ in car["wheels"]:
        outside.append(
            any(
                value < low - 0.1 or value > high + 0.1
                for value, (low, high) in zip((x / 4096, -z / 4096), bounds)
            )
        )
    return not all(outside)


def body_face_frame(lod, face, centre):
    """Repair lit glTF orientation without changing native positions, UVs or colours.

    Stored normals carry direction on ordinary faces. Near-perpendicular or
    cancelling sums need a geometric fallback; the centroid is a documented
    approximation for these faces, not evidence of the game's lighting.
    """
    points = [lod["vertices"][v] for v in face["vertices"]]
    normals = [lod["normals"][n] for n in face["normals"]]
    geometric = [0.0, 0.0, 0.0]
    for j in range(1, len(points) - 1):
        a = [points[j][i] - points[0][i] for i in range(3)]
        b = [points[j + 1][i] - points[0][i] for i in range(3)]
        cross = [
            a[1] * b[2] - a[2] * b[1],
            a[2] * b[0] - a[0] * b[2],
            a[0] * b[1] - a[1] * b[0],
        ]
        geometric = [geometric[i] + cross[i] for i in range(3)]
    length = math.sqrt(sum(x * x for x in geometric))
    if length < 1e-12:
        return normals, False, False  # Keep nonzero stored normals on zero-area faces.
    summed = [sum(n[i] for n in normals) for i in range(3)]
    magnitude = math.sqrt(sum(x * x for x in summed))
    cosine = (
        sum(geometric[i] * summed[i] for i in range(3)) / length / magnitude
        if magnitude > 1e-9
        else 0.0
    )
    repaired = abs(cosine) < 0.15
    if repaired:
        outward = [
            sum(p[i] for p in points) / len(points) - centre[i] for i in range(3)
        ]
        cosine = sum(geometric[i] * outward[i] for i in range(3))
        sign = 1 if cosine >= 0 else -1
        normals = [tuple(sign * x / length for x in geometric)] * len(points)
    return normals, cosine < 0, repaired


def build_glb(car_data, tex_data, identity, metadata=None):
    car, tex = parse_car(car_data), parse_tex(tex_data)
    if metadata is not None and not isinstance(metadata, dict):
        raise ValueError("GT native metadata must be an object")
    # Copy caller data so later UI annotations cannot mutate an already-built
    # export. Reject non-JSON and non-finite values rather than producing bad GLB.
    metadata = json.loads(json.dumps(metadata or {}, allow_nan=False))
    colour_rows = metadata.get("colour_variants")
    if colour_rows is None:
        colour_rows = [
            {"index": i, "colour_id": colour_id}
            for i, colour_id in enumerate(tex["colour_ids"])
        ]
    if not isinstance(colour_rows, list) or len(colour_rows) != tex["count"]:
        raise ValueError("GT colour variant metadata coverage differs")
    variants = []
    for i, row in enumerate(colour_rows):
        if (
            not isinstance(row, dict)
            or type(row.get("index")) is not int
            or row["index"] != i
            or type(row.get("colour_id")) is not int
            or row["colour_id"] != tex["colour_ids"][i]
        ):
            raise ValueError("GT colour variant metadata identity differs")
        label = row.get("label") or row.get("name") or "Native colour"
        if not isinstance(label, str):
            raise ValueError("GT colour variant label must be text")
        variants.append(
            {
                "name": f"{label} [ID {row['colour_id']}, set {i}]",
                "extras": {"nativeColourSet": i, "nativeColourId": row["colour_id"]},
            }
        )
    binary = bytearray()
    doc = {
        "asset": {
            "version": "2.0",
            "generator": "Bounded GT1 native body and wheel exporter",
        },
        "scene": 0,
        "scenes": [],
        "nodes": [],
        "meshes": [],
        "accessors": [],
        "bufferViews": [],
        "buffers": [],
        "extensionsUsed": ["KHR_materials_variants"],
        "extensions": {"KHR_materials_variants": {"variants": variants}},
        "materials": [],
        "images": [],
        "textures": [],
        "samplers": [
            {"magFilter": 9728, "minFilter": 9728, "wrapS": 33071, "wrapT": 33071}
        ],
        "extras": {
            "sourceId": identity,
            "sourceCarSha256": sha(car_data),
            "sourceTexSha256": sha(tex_data),
            "sourceProfile": "gran-turismo-native-candidate",
            "claim_limits": LIMITS,
            "nativeWheelCentres": car["wheels"],
            "nativeWheelDimensions": car["wheel_dimensions"],
            "nativeShadow": {k: car["shadow"][k] for k in ("offset", "quads", "scale")},
            "nativeMetadata": metadata,
            "trailingBytes": car["trailing_bytes"],
            "trailingSha256": car["trailing_sha256"],
            "sourceColourSetCount": tex["count"],
            "sourceColourIds": tex["colour_ids"],
            "displayedColourSet": 0,
            "illuminationMasks": tex["illumination_masks"],
            "paintMasks": tex["paint_masks"],
        },
    }

    def view(payload, target=None):
        binary.extend(b"\0" * ((-len(binary)) % 4))
        index = len(doc["bufferViews"])
        row = {"buffer": 0, "byteOffset": len(binary), "byteLength": len(payload)}
        if target:
            row["target"] = target
        doc["bufferViews"].append(row)
        binary.extend(payload)
        return index

    def accessor(values, width, kind="f", bounds=False):
        payload = struct.pack("<" + kind * len(values), *values)
        row = {
            "bufferView": view(payload, 34963 if kind == "I" else 34962),
            "componentType": 5125 if kind == "I" else 5126,
            "count": len(values) // width,
            "type": {1: "SCALAR", 2: "VEC2", 3: "VEC3"}[width],
        }
        if bounds:
            actual = [v[0] for v in struct.iter_unpack("<f", payload)]
            row.update(
                {
                    "min": [min(actual[j::width]) for j in range(width)],
                    "max": [max(actual[j::width]) for j in range(width)],
                }
            )
        doc["accessors"].append(row)
        return len(doc["accessors"]) - 1

    payloads = {
        name: {
            "bufferView": view(payload),
            "byteLength": len(payload),
            "sha256": sha(payload),
        }
        for name, payload in [("car", car_data), ("ctex", tex_data)]
    }
    doc["extras"]["nativeSourcePayloads"] = payloads

    def source_ref(name, offset, length, **fields):
        payload = payloads[name]
        if not 0 <= offset <= offset + length <= payload["byteLength"]:
            raise ValueError("GT native source reference outside payload")
        return {
            "bufferView": payload["bufferView"],
            "byteOffset": offset,
            "byteLength": length,
            **fields,
        }

    native = {
        "schema": 1,
        "claimLimits": [
            "Retained native data; GTE shading, transparency and animation are not reproduced.",
            "Native LOD thresholds require camera state and are not distances in metres.",
        ],
        "faceFlags": {
            "encoding": ["word0 & 0xf8000000", "word1 & 0x80000000"],
            "meaning": "Unmodified packed source bits; runtime interpretation is not baked.",
        },
        "carHeader": source_ref("car", 0, 128),
        "ctex": {
            "header": source_ref("ctex", 0, 0x60),
            "indexedPixels": source_ref(
                "ctex",
                0x60,
                0x8000,
                width=256,
                height=256,
                encoding="4-bit indices; low nibble first",
            ),
            "palettes": [
                source_ref(
                    "ctex",
                    0x8060 + i * 512,
                    512,
                    colourSet=i,
                    colourId=tex["colour_ids"][i],
                    componentType=5123,
                    count=256,
                )
                for i in range(tex["count"])
            ],
            "illuminationMasks": source_ref(
                "ctex", 32, 32, componentType=5123, count=16
            ),
            "paintMasks": source_ref("ctex", 64, 32, componentType=5123, count=16),
            "paletteEncoding": "Little-endian PS1 RGB555 plus native bit15; word zero is transparent.",
        },
        "lods": [],
    }
    doc["extras"]["nativeData"] = native
    shadow = car["shadow"]
    shadow_positions = shadow["offset"] + 32
    native["shadow"] = {
        "header": source_ref("car", shadow["offset"], 32),
        "records": source_ref(
            "car",
            shadow_positions,
            shadow["end"] - shadow_positions,
            componentType=5122,
            components=4,
            byteStride=8,
            count=shadow["triangles"] * 3 + shadow["quads"] * 4,
        ),
        "triangles": shadow["triangles"],
        "quads": shadow["quads"],
        "scale": shadow["scale"],
        "boundsMin": shadow["bounds_min"],
        "boundsMax": shadow["bounds_max"],
        "unknownWord": shadow["unknown_word"],
        "topology": "Sequential triangle vertices followed by sequential quad vertices.",
        "coordinateSpace": "Native stored values; no visible shadow transform is asserted.",
    }
    tables = load_tables()
    native["wheelTemplates"] = {
        "sourceExecutableSha256": SOURCE_SHA256,
        "unpackedSha256": UNPACKED_SHA256,
        "pointerAddress": POINTER_ADDRESS,
        "tables": [
            {
                "lod": i,
                "address": table["virtual_address"],
                "quadCount": table["quad_count"],
                "bufferView": view(table["raw"]),
                "byteLength": len(table["raw"]),
                "sha256": table["sha256"],
            }
            for i, table in enumerate(tables)
        ],
    }
    selectors = sorted(
        {0}
        | {
            f["clut"]
            for lod in car["lods"]
            for f in lod["faces"]
            if f["clut"] is not None
        }
    )
    materials = {}
    images_by_payload = {}
    for clut in selectors:
        for colour in range(tex["count"]):
            payload = png(tex, clut, colour)
            image = images_by_payload.get(payload)
            if image is None:
                image = len(doc["images"])
                images_by_payload[payload] = image
                doc["images"].append(
                    {
                        "bufferView": view(payload),
                        "mimeType": "image/png",
                        "name": f"Native colour{colour} CLUT{clut}",
                    }
                )
                doc["textures"].append({"sampler": 0, "source": image})
            materials[clut, colour] = len(doc["materials"])
            doc["materials"].append(
                {
                    "name": f"Native colour{colour} CLUT{clut}",
                    "doubleSided": True,
                    "alphaMode": "MASK",
                    "alphaCutoff": 0.5,
                    "pbrMetallicRoughness": {
                        "baseColorTexture": {"index": image},
                        "metallicFactor": 0,
                        "roughnessFactor": 1,
                    },
                    "extras": {
                        "nativeCLUT": clut,
                        "nativeColourSet": colour,
                        "nativeColourId": tex["colour_ids"][colour],
                    },
                }
            )

    def variant_extensions(clut):
        return {
            "KHR_materials_variants": {
                "mappings": [
                    {"material": materials[clut, colour], "variants": [colour]}
                    for colour in range(tex["count"])
                ]
            }
        }

    records = []
    wheel_nodes = []
    # Native showroom calls select wheel template 0 independently of body LOD.
    # Reflect the whole assembly into the same glTF Z basis as the body.
    for wheel in assemble_wheels(car, lod=0, tables=tables):
        positions, normals, uvs, indices = [], [], [], []
        for quad in wheel["quads"]:
            for triangle in [(quad[0], quad[1], quad[3]), (quad[3], quad[1], quad[2])]:
                vertices = [
                    (
                        wheel["positions"][v][0] / 4096,
                        wheel["positions"][v][1] / 4096,
                        -wheel["positions"][v][2] / 4096,
                    )
                    for v in triangle
                ]
                # Compute flat normals after the coordinate reflection; native
                # wheel packets are textured polygons without stored normals.
                vertices[1], vertices[2] = vertices[2], vertices[1]
                a = [vertices[1][i] - vertices[0][i] for i in range(3)]
                b = [vertices[2][i] - vertices[0][i] for i in range(3)]
                normal = [
                    a[1] * b[2] - a[2] * b[1],
                    a[2] * b[0] - a[0] * b[2],
                    a[0] * b[1] - a[1] * b[0],
                ]
                length = math.sqrt(sum(x * x for x in normal))
                if not length:
                    raise ValueError("Degenerate native wheel triangle")
                normal = [x / length for x in normal]
                base = len(positions) // 3
                for vertex, reference in zip(
                    vertices, [triangle[0], triangle[2], triangle[1]]
                ):
                    positions.extend(vertex)
                    normals.extend(normal)
                    uvs.extend((c + 0.5) / 256 for c in wheel["uv"][reference])
                indices.extend((base, base + 1, base + 2))
        mesh, node = len(doc["meshes"]), len(doc["nodes"])
        primitive = {
            "attributes": {
                "POSITION": accessor(positions, 3, bounds=True),
                "NORMAL": accessor(normals, 3),
                "TEXCOORD_0": accessor(uvs, 2),
            },
            "indices": accessor(indices, 1, "I"),
            "mode": 4,
            "material": materials[0, 0],
            "extensions": variant_extensions(0),
        }
        wheel_index = wheel["wheel_index"]
        direction = 1 if wheel_index % 2 == 0 else -1
        anchor = car["wheels"][wheel_index]
        pivot = [anchor[0] + (direction * wheel["width"]) // 2, anchor[1], anchor[2]]
        doc["meshes"].append(
            {"name": f"Native wheel {wheel['wheel_index']}", "primitives": [primitive]}
        )
        doc["nodes"].append(
            {
                "name": f"Native wheel {wheel['wheel_index']}",
                "mesh": mesh,
                "extras": {
                    "nativeWheelIndex": wheel_index,
                    "nativeTemplateLOD": 0,
                    "nativeHeaderAnchor": anchor,
                    "nativePivotPosition": pivot,
                    "nativePivotPositionMetres": [
                        pivot[0] / 4096,
                        pivot[1] / 4096,
                        -pivot[2] / 4096,
                    ],
                    "nativeWidth": wheel["width"],
                    "nativeRadius": wheel["radius"],
                    "nativeAspectFixed": wheel["aspect_fixed"],
                    "pivotClaim": "Native neutral half-width-corrected attachment; vertices remain baked.",
                },
            }
        )
        wheel_nodes.append(node)
    doc["extras"]["wheelAssembly"] = {
        "templateLOD": 0,
        "quadsPerWheel": 31,
        "wheels": len(wheel_nodes),
        "basis": "Native CAR units /4096; entire assembly reflects Z",
        "pose": "Neutral showroom steering and spin",
    }
    for lod in car["lods"]:
        native["lods"].append(
            {
                "lod": lod["index"],
                "header": source_ref("car", lod["offset"], 40),
                "threshold": lod["threshold"],
                "thresholdSource": source_ref("car", 0x40 + lod["index"] * 8, 8),
                "scale": lod["scale"],
                "boundsMin": lod["bounds_min"],
                "boundsMax": lod["bounds_max"],
                "unknownWord": lod["unknown_word"],
                "groupCounts": lod["group_counts"],
                "vertices": source_ref(
                    "car",
                    lod["vertex_offset"],
                    len(lod["vertices"]) * 8,
                    componentType=5122,
                    components=4,
                    byteStride=8,
                    count=len(lod["vertices"]),
                ),
                "normals": source_ref(
                    "car",
                    lod["normal_offset"],
                    len(lod["normals"]) * 8,
                    componentType=5122,
                    components=4,
                    byteStride=8,
                    count=len(lod["normals"]),
                ),
            }
        )
        centre = [
            sum(v[i] for v in lod["vertices"]) / len(lod["vertices"]) for i in range(3)
        ]
        repaired_faces = reversed_faces = 0
        groups = {}
        for face in lod["faces"]:
            key = (
                "gouraud"
                if "corner_colours" in face
                else face["clut"]
                if face["clut"] is not None
                else ("colour", tuple(face["colour"]))
            )
            groups.setdefault(key, []).append(face)
        primitives = []
        for key, faces in groups.items():
            material_key = (key, 0) if type(key) is int else key
            if material_key not in materials:
                materials[key] = len(doc["materials"])
                doc["materials"].append(
                    {
                        "name": "Native per-corner RGB"
                        if key == "gouraud"
                        else "Native face RGB " + str(key[1]),
                        "doubleSided": True,
                        "pbrMetallicRoughness": {
                            "baseColorFactor": [1, 1, 1, 1]
                            if key == "gouraud"
                            else [srgb(v / 255) for v in key[1]] + [1],
                            "metallicFactor": 0,
                            "roughnessFactor": 1,
                        },
                    }
                )
            positions, normals, uvs, indices, colours = [], [], [], [], []
            native_faces = []
            for face in faces:
                base = len(positions) // 3
                first_triangle = len(indices) // 3
                face_normals, reverse, repaired = body_face_frame(lod, face, centre)
                repaired_faces += repaired
                reversed_faces += reverse
                for corner, v in enumerate(face["vertices"]):
                    positions.extend(lod["vertices"][v])
                    normals.extend(face_normals[corner])
                    if "corner_colours" in face:
                        # glTF vertex colours are linear; native RGB bytes are display encoded.
                        colours.extend(
                            [srgb(v / 255) for v in face["corner_colours"][corner]]
                        )
                    if face["clut"] is not None:
                        uvs.extend([(c + 0.5) / 256 for c in face["uv"][corner]])
                # Native CAR quads follow boundary order (0,1,2),(0,2,3).
                # Agree with the repaired normals so double-sided lighting faces outward.
                triangles = [(0, 1, 2), (0, 2, 3)] if face["quad"] else [(0, 1, 2)]
                for triangle in triangles:
                    indices.extend(
                        base + j
                        for j in (
                            triangle
                            if not reverse
                            else (triangle[0], triangle[2], triangle[1])
                        )
                    )
                native_faces.append(
                    {
                        "sourceOffset": face["offset"],
                        "sourceByteLength": face["end"] - face["offset"],
                        "group": face["group"],
                        "type": face["type"],
                        "colour": face["colour"],
                        "flags": face["flags"],
                        "rawCLUT": face.get("raw_clut"),
                        "vertexIndices": face["vertices"],
                        "normalIndices": face["normals"],
                        "firstVertex": base,
                        "firstTriangle": first_triangle,
                        "triangleCount": len(triangles),
                        "reversed": reverse,
                        "normalRepaired": repaired,
                    }
                )
            attrs = {
                "POSITION": accessor(positions, 3, bounds=True),
                "NORMAL": accessor(normals, 3),
            }
            if colours:
                attrs["COLOR_0"] = accessor(colours, 3)
            if uvs:
                attrs["TEXCOORD_0"] = accessor(uvs, 2)
            primitive = {
                "attributes": attrs,
                "indices": accessor(indices, 1, "I"),
                "mode": 4,
                "material": materials[material_key],
                "extras": {
                    "nativeLOD": lod["index"],
                    "nativeFaces": native_faces,
                    "nativeFaceSourceBufferView": payloads["car"]["bufferView"],
                },
            }
            if type(key) is int:
                primitive["extensions"] = variant_extensions(key)
            primitives.append(primitive)
        mesh = len(doc["meshes"])
        node = len(doc["nodes"])
        doc["meshes"].append({"name": f"LOD{lod['index']}", "primitives": primitives})
        doc["nodes"].append({"name": f"Native body LOD{lod['index']}", "mesh": mesh})
        visible_wheels = wheel_nodes if wheel_bounds_fit(car, lod) else []
        doc["scenes"].append(
            {
                "name": f"LOD{lod['index']}",
                "nodes": [node, *visible_wheels],
                "extras": {
                    "wheelAssemblySuppressed": bool(wheel_nodes and not visible_wheels)
                },
            }
        )
        records.append(
            {
                "lod": lod["index"],
                "offset": lod["offset"],
                "end": lod["end"],
                "vertices": len(lod["vertices"]),
                "normals": len(lod["normals"]),
                "zero_normals": sum(n == (0.0, 0.0, 0.0) for n in lod["normals"]),
                "polygons": len(lod["faces"]),
                "triangles": sum(2 if f["quad"] else 1 for f in lod["faces"]),
                "geometric_normal_repairs": repaired_faces,
                "reoriented_faces": reversed_faces,
                "wheel_template_lod": 0,
                "wheel_triangles": 62 * len(visible_wheels),
                "wheel_assembly_suppressed": bool(wheel_nodes and not visible_wheels),
            }
        )
    doc["buffers"] = [{"byteLength": len(binary)}]
    encoded = json.dumps(doc, separators=(",", ":"), ensure_ascii=True).encode()
    encoded += b" " * ((-len(encoded)) % 4)
    binary.extend(b"\0" * ((-len(binary)) % 4))
    glb = (
        struct.pack("<4sII", b"glTF", 2, 12 + 8 + len(encoded) + 8 + len(binary))
        + struct.pack("<I4s", len(encoded), b"JSON")
        + encoded
        + struct.pack("<I4s", len(binary), b"BIN\0")
        + binary
    )
    return glb, records
