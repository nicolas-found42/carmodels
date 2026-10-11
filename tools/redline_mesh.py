"""Bounded Redline native MDL decoder, following the shipped i386 loader.

Native spans: 0x3b6de (endian/layout), 0x3c4ba (corner expansion),
0x3c9ba (material grouping). This reads declared geometry, retaining opaque
trailer identity. It does not reproduce game lighting or shader composition.
"""

import hashlib
import math
import struct


MAX_MODEL_BYTES = 64 * 1024 * 1024
MAX_RECORDS = 500_000
ABSENT = 0xFFFFFFFF


def _vectors(data, offset, count, width, label):
    values = list(struct.iter_unpack(">" + "f" * width, data[offset:offset + count * width * 4]))
    if any(not math.isfinite(v) for row in values for v in row):
        raise ValueError(f"nonfinite {label}")
    return values


def _name(raw):
    end = raw.find(b"\0")
    value = raw if end < 0 else raw[:end]
    if any(v < 32 or v == 127 for v in value) or b"/" in value or b"\\" in value:
        raise ValueError("unsafe material texture name")
    name = value.decode("mac_roman")
    if name in {".", ".."}:
        raise ValueError("unsafe material texture name")
    return name


def decode_model(data):
    """Return raw arrays and zero-based corner indices, with source byte ranges.

Triangle corner tuples are (position, normal, UV, secondary UV). Optional
indices are None for the native 0xffffffff sentinel. The fourth corner word
in single-texture models is opaque and retained separately. Material -1 means
native material zero, which the native material draw loop omits.
"""
    if not isinstance(data, bytes) or not 28 <= len(data) <= MAX_MODEL_BYTES:
        raise ValueError("invalid model byte length")
    counts = struct.unpack_from(">6I", data)
    position_count, normal_count, uv_count, triangle_count, material_count, flags = counts
    if any(v > MAX_RECORDS for v in counts[:5]):
        raise ValueError("model record count exceeds limit")
    if flags & ~3:
        raise ValueError("unsupported model flags")
    dual = bool(flags & 2)
    if dual and material_count % 2:
        raise ValueError("secondary texture material count must be even")
    radius = struct.unpack_from(">f", data, 24)[0]
    if not math.isfinite(radius) or radius < 0:
        raise ValueError("invalid model radius")
    triangle_stride = 64 if dual else 52
    offsets = {"positions": 28}
    offsets["normals"] = offsets["positions"] + position_count * 12
    offsets["uvs"] = offsets["normals"] + normal_count * 12
    offsets["triangles"] = offsets["uvs"] + uv_count * 8
    offsets["materials"] = offsets["triangles"] + triangle_count * triangle_stride
    end = offsets["materials"] + material_count * 80
    if end > len(data):
        raise ValueError("truncated declared model records")
    positions = _vectors(data, offsets["positions"], position_count, 3, "positions")
    normals = _vectors(data, offsets["normals"], normal_count, 3, "normals")
    uvs = _vectors(data, offsets["uvs"], uv_count, 2, "UVs")
    materials = []
    for i in range(material_count):
        off = offsets["materials"] + i * 80
        values = struct.unpack_from(">10f", data, off + 40)
        if not all(math.isfinite(v) for v in values):
            raise ValueError("nonfinite material values")
        materials.append({"texture": _name(data[off:off + 32]),
                          "source_offset": off,
                          "native_resource_word": struct.unpack_from(">I", data, off + 32)[0],
                          "flags": struct.unpack_from(">I", data, off + 36)[0],
                          "values": values})
    triangles = []
    draw_material_count = material_count // 2 if dual else material_count
    corner_width = 5 if dual else 4
    for i in range(triangle_count):
        off = offsets["triangles"] + i * triangle_stride
        words = struct.unpack_from(">" + "I" * (triangle_stride // 4), data, off)
        material = words[0] & 0x7FFFFFFF
        if material > draw_material_count:
            raise ValueError("triangle material index out of bounds")
        corners, extras = [], []
        for j in range(3):
            row = words[1 + corner_width * j:1 + corner_width * (j + 1)]
            indices = []
            for k, count in enumerate((position_count, normal_count, uv_count, uv_count)):
                value = row[k] if k < 3 or dual else ABSENT
                if k > 0 and value == ABSENT:
                    indices.append(None)
                elif not 1 <= value <= count:
                    raise ValueError(f"triangle corner {k} index out of bounds")
                else:
                    indices.append(value - 1)
            corners.append(tuple(indices))
            extras.append(row[-1])
        # The native expansion tests each channel's first corner sentinel once,
        # then reads that channel for every corner. Mixed sentinels are unsafe.
        for channel in (1, 2, 3):
            if corners[0][channel] is not None and any(c[channel] is None for c in corners):
                raise ValueError("mixed missing corner indices")
        triangles.append({"corners": corners, "material": material - 1,
                          "native_material_word": words[0], "corner_extra_words": extras,
                          "source_offset": off})
    bounds = ([list(min(p[k] for p in positions) for k in range(3)),
               list(max(p[k] for p in positions) for k in range(3))] if positions else None)
    return {"format": "redline-mdl", "counts": dict(zip(
        ("positions", "normals", "uvs", "triangles", "materials"), counts[:5])),
        "flags": flags, "radius": radius, "positions": positions, "normals": normals,
        "uvs": uvs, "triangles": triangles, "materials": materials, "bounds": bounds,
        "source_offsets": offsets, "declared_bytes": end, "source_bytes": len(data),
        "source_sha256": hashlib.sha256(data).hexdigest(),
        "opaque_trailer": {"offset": end, "bytes": len(data) - end,
                           "sha256": hashlib.sha256(data[end:]).hexdigest()}}


def _face_normal(points):
    a = [points[1][k] - points[0][k] for k in range(3)]
    b = [points[2][k] - points[0][k] for k in range(3)]
    cross = (a[1] * b[2] - a[2] * b[1], a[2] * b[0] - a[0] * b[2],
             a[0] * b[1] - a[1] * b[0])
    length = math.sqrt(sum(v * v for v in cross))
    return tuple(v / length for v in cross) if length else (0.0, 0.0, 0.0)


def expanded_primitives(model):
    """Expand real triangles by native draw material; keep winding and UV origin.

No transform or UV flip is applied. Secondary UVs/material indices are retained
for callers to compose textures. Missing normals use the native cross product;
missing UV channels become zero coordinates, following the native expansion.
"""
    groups = {}
    dual = bool(model["flags"] & 2)
    for triangle in model["triangles"]:
        mi = triangle["material"]
        if mi < 0:
            continue
        group = groups.setdefault(mi, {"material": mi, "positions": [], "normals": [],
            "uvs": [], "secondary_uvs": [], "indices": [], "source_offsets": [],
            "secondary_material": mi + len(model["materials"]) // 2 if dual else None})
        corners = triangle["corners"]
        points = [model["positions"][c[0]] for c in corners]
        face = _face_normal(points) if corners[0][1] is None else None
        for point, corner in zip(points, corners):
            group["indices"].append(len(group["positions"]))
            group["positions"].append(point)
            group["normals"].append(face if face is not None else model["normals"][corner[1]])
            for field, channel in (("uvs", 2), ("secondary_uvs", 3)):
                group[field].append((0.0, 0.0) if corners[0][channel] is None
                                    else model["uvs"][corner[channel]])
        group["source_offsets"].append(triangle["source_offset"])
    return [groups[k] for k in sorted(groups)]
