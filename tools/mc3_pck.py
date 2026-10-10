"""Bounded reader for the three serialized MC3 PS2 geometry pointer profiles.

Static packet geometry and source rest joints, with native flags retained.
This module does not choose customization parts or assert game shading.
"""
from __future__ import annotations

import hashlib
import math
from pathlib import Path
import struct

MAX_BYTES = 64 * 1024 * 1024
MAX_PARTS = 4096
MAX_VERTICES = 1_000_000
MODEL_VTABLES = {0x7A9420, 0x7AA728, 0x7A9620}
MESH_VTABLES = {0x7A0F98, 0x7A22A0, 0x7A1198}
GROUP_VTABLES = {0x7A0EF0, 0x7A21F8, 0x7A10F0}
MATERIAL_VTABLES = {0x7A1138, 0x7A2440, 0x7A1338}


class Pck:
    def __init__(self, data: bytes, source: str = "memory"):
        if not 128 <= len(data) <= MAX_BYTES:
            raise ValueError("PCK carrier size outside bound")
        self.data, self.source = data, source
        self.base, self.kind, version, size = struct.unpack_from("<4I", data)
        if version != 1 or size != len(data) - 128:
            raise ValueError("PCK version or declared payload length mismatch")
        if not self.base or self.base + size > 0xFFFFFFFF:
            raise ValueError("PCK base outside serialized address range")
        self.sha256 = hashlib.sha256(data).hexdigest()
        self.decoded_vertices = 0

    @classmethod
    def file(cls, path: Path | str) -> Pck:
        path = Path(path)
        if not path.is_file() or path.stat().st_size > MAX_BYTES:
            raise ValueError("PCK file size outside bound")
        return cls(path.read_bytes(), str(path))

    def bounds(self, offset: int, size: int = 1) -> int:
        if offset < 128 or size < 0 or offset + size > len(self.data):
            raise ValueError("PCK range outside payload")
        return offset

    def pointer(self, pointer: int, size: int = 1) -> int:
        return self.bounds(pointer - self.base + 128, size)

    def u32(self, offset: int) -> int:
        return struct.unpack_from("<I", self.data, self.bounds(offset, 4))[0]

    def u16(self, offset: int) -> int:
        return struct.unpack_from("<H", self.data, self.bounds(offset, 2))[0]

    def text(self, pointer: int) -> str:
        start = self.pointer(pointer)
        end = self.data.find(b"\0", start, min(start + 513, len(self.data)))
        if end < start:
            raise ValueError("PCK name lacks bounded terminator")
        try:
            return self.data[start:end].decode("ascii")
        except UnicodeError as error:
            raise ValueError("PCK name is not ASCII") from error

    def fingerprint(self) -> dict:
        return {"file": self.source, "sha256": self.sha256,
                "bytes": len(self.data), "serialized_base": self.base}


def vif_planes(pck: Pck, start: int, size: int) -> list[dict]:
    """Expand bounded VIF UNPACK arrays, including STCYCL and row deltas.

    Only the commands present in this geometry corpus are accepted. Each plane
    retains its source command offset, destination VU address and cycle state.
    Values are UNPACK vectors, not a sparse VU memory image; destination skip
    cycles are rejected by the contiguous geometry decoder below.
    """
    data = pck.data
    end = pck.bounds(start, size) + size
    cursor = start
    cl = wl = 1
    mode = mask = 0
    row = [0, 0, 0, 0]
    col = [0, 0, 0, 0]
    planes = []
    while cursor < end:
        if cursor + 4 > end:
            raise ValueError("truncated VIF command")
        word = struct.unpack_from("<I", data, cursor)[0]
        cmd, count, imm = (word >> 24) & 0x7F, (word >> 16) & 255, word & 65535
        length = 0
        if cmd & 0x60 == 0x60:
            count = count or 256
            components, bits = ((cmd >> 2) & 3) + 1, (32, 16, 8, 5)[cmd & 3]
            if bits == 5:
                raise ValueError("unsupported VIF packed five-bit format")
            consumed = count if wl <= cl else (count // wl) * cl + min(count % wl, cl)
            length = consumed * components * (bits // 8)
            if cursor + 4 + length > end:
                raise ValueError("VIF unpack exceeds draw packet")
            unsigned = bool(imm & 0x4000)
            code = {32: "I", 16: "H" if unsigned else "h", 8: "B" if unsigned else "b"}[bits]
            raw = struct.unpack_from("<" + code * consumed * components, data, cursor + 4)
            values = []
            input_index = 0
            for i in range(count):
                has_input = wl <= cl or i % wl < cl
                vector = list(raw[input_index:input_index + components]) if has_input else row[:components]
                if has_input:
                    input_index += components
                    if mode:
                        vector = [value + row[j] for j, value in enumerate(vector)]
                        if mode == 2:
                            row[:components] = vector
                if cmd & 0x10:
                    selectors = (mask >> ((i % 4) * 8)) & 255
                    for j in range(components):
                        selected = (selectors >> (j * 2)) & 3
                        if selected == 1:
                            vector[j] = row[j]
                        elif selected == 2:
                            vector[j] = col[i % 4]
                        elif selected == 3:
                            raise ValueError("unsupported VIF protected destination mask")
                values.append(tuple(vector))
            planes.append({"offset": cursor, "payload_offset": cursor + 4,
                           "command": cmd, "address": imm & 1023,
                           "count": count, "components": components, "bits": bits,
                           "unsigned": unsigned, "mode": mode, "cl": cl, "wl": wl,
                           "values": values})
        elif cmd == 1:
            cl, wl = (imm & 255) or 256, (imm >> 8) or 256
        elif cmd == 5:
            if imm not in {0, 1, 2}:
                raise ValueError("unsupported VIF offset mode")
            mode = imm
        elif cmd in {0x20, 0x30, 0x31}:
            length = 4 if cmd == 0x20 else 16
            if cursor + 4 + length > end:
                raise ValueError("truncated VIF state command")
            values = struct.unpack_from("<" + "I" * (length // 4), data, cursor + 4)
            signed = [x if x < 0x80000000 else x - 0x100000000 for x in values]
            if cmd == 0x20:
                mask = values[0]
            elif cmd == 0x30:
                row = signed
            else:
                col = signed
        elif cmd not in {0, 2, 3, 4, 6, 7, 0x10, 0x11, 0x13, 0x14, 0x15, 0x17}:
            raise ValueError(f"unsupported VIF command {cmd:#x}")
        cursor += 4 + ((length + 3) // 4) * 4
    if cursor != end:
        raise ValueError("VIF command alignment exceeds packet")
    return planes


def decode_batches(planes: list[dict]) -> list[dict]:
    # CL > WL advances the destination over unwritten VU addresses. Treating
    # those vectors as contiguous would silently produce different geometry.
    # No supported source draw uses this mode; retain raw scan state but reject
    # it before interpreting either a batch header or any attribute array.
    if any(plane["cl"] > plane["wl"] for plane in planes):
        raise ValueError("unsupported VIF destination skip cycle")
    batches = []
    headers = [i for i, p in enumerate(planes) if p["components"] in {1, 4} and p["bits"] == 32]
    if not headers or headers[0] != 0:
        raise ValueError("draw lacks leading VIF batch header")
    for index, first in enumerate(headers):
        header = planes[first]
        if header["count"] != 2 or header["address"] not in {0x98, 0x1C5}:
            raise ValueError("unknown VIF batch header layout")
        words = [v for vector in header["values"] for v in vector]
        scale = struct.unpack("<f", struct.pack("<I", words[0]))[0]
        count = words[1] if header["components"] == 1 else words[4]
        if scale not in {1 / 4096, 1 / 8192, 1 / 16384, 1 / 32768} or not 1 <= count <= 256:
            raise ValueError("unknown position scale or batch vertex count")
        if header["components"] == 4:
            floats = struct.unpack("<4f", struct.pack("<4I", *words[:4]))
            if words[7] != count or not all(math.isfinite(x) for x in floats):
                raise ValueError("VIF batch header count or float mismatch")
        last = headers[index + 1] if index + 1 < len(headers) else len(planes)
        arrays = {"positions": [None] * count, "uvs": [None] * count,
                  "colors": [None] * count, "normals": [None] * count}
        targets = {"positions": (header["address"] + 0x56, {3}, {8, 16}),
                   "uvs": (header["address"] + 0x2C, {2, 4}, {8, 16, 32}),
                   "colors": (header["address"] + 0x80, {4}, {8}),
                   "normals": (header["address"] + 2, {3}, {8})}
        for plane in planes[first + 1:last]:
            matches = [name for name, (address, components, bits) in targets.items()
                       if plane["components"] in components and plane["bits"] in bits
                       and address <= plane["address"] < address + count]
            if len(matches) != 1:
                raise ValueError("unknown or ambiguous VIF attribute destination")
            name = matches[0]
            slot = plane["address"] - targets[name][0]
            if slot + plane["count"] > count:
                raise ValueError("VIF attribute exceeds declared vertices")
            for i, value in enumerate(plane["values"]):
                if arrays[name][slot + i] is not None:
                    raise ValueError("overlapping VIF attribute writes")
                arrays[name][slot + i] = tuple(x - 0x100000000 if x >= 0x80000000 else x for x in value) if plane["bits"] == 32 else value
        if any(value is None for value in arrays["positions"]):
            raise ValueError("missing VIF position values")
        for name in ["uvs", "colors", "normals"]:
            if any(value is None for value in arrays[name]):
                raise ValueError(f"missing VIF {name} values")
        positions = [tuple(x * scale for x in value) for value in arrays["positions"]]
        if not all(math.isfinite(x) for point in positions for x in point):
            raise ValueError("non-finite position")
        batches.append({"packet_offset": header["offset"], "scale": scale,
                        "header_words": words, "positions": positions,
                        "position_integers": arrays["positions"],
                        "uvs": [tuple(x / 4096 for x in v[:2]) for v in arrays["uvs"]],
                        "uv_integers": arrays["uvs"],
                        "normals": [tuple(x / 128 for x in v) for v in arrays["normals"]],
                        "adc": [v[0] & 1 for v in arrays["normals"]],
                        "normal_integers": arrays["normals"],
                        "colors": [tuple(x / 255 for x in v[:3]) for v in arrays["colors"]],
                        "color_integers": arrays["colors"],
                        "flags": [v[3] for v in arrays["colors"]]})
    return batches



def strip_indices(batch: dict) -> list[int]:
    """Candidate PS2 strip topology: normal-X bit zero permits a triangle.

    The native normal-X low bit is one for the first two vertices of every
    checked batch. Retain that observation separately from runtime fidelity.
    Degenerate triangles are omitted by an exact cross-product calculation.
    """
    positions, adc = batch["positions"], batch["adc"]
    if any(len(point) != 3 or not all(math.isfinite(value) for value in point) for point in positions):
        raise ValueError("strip positions must be finite XYZ vectors")
    if len(positions) != len(adc) or any(value not in {0, 1} for value in adc):
        raise ValueError("strip position and ADC count mismatch")
    indices = []
    for i in range(2, len(positions)):
        if adc[i]:
            continue
        a, b, c = (i - 2, i - 1, i) if i % 2 == 0 else (i - 1, i - 2, i)
        p, q, r = positions[a], positions[b], positions[c]
        u = [q[j] - p[j] for j in range(3)]
        v = [r[j] - p[j] for j in range(3)]
        cross = [u[1] * v[2] - u[2] * v[1], u[2] * v[0] - u[0] * v[2], u[0] * v[1] - u[1] * v[0]]
        if any(value != 0 for value in cross):
            indices.extend((a, b, c))
    return indices


def read_mesh_object(pck: Pck, offset: int) -> dict:
    if pck.u32(offset) not in MESH_VTABLES:
        raise ValueError("unknown serialized mesh profile")
    count = pck.u32(offset + 8)
    if not 1 <= count <= MAX_PARTS:
        raise ValueError("mesh draw count outside bound")
    materials = pck.pointer(pck.u32(offset + 12), count * 2)
    table = pck.pointer(pck.u32(offset + 16), count * 8)
    draws = []
    for i in range(count):
        descriptor = pck.pointer(pck.u32(table + i * 8), 8)
        packet_pointer, qwc, vertices = struct.unpack_from("<IHH", pck.data, descriptor)
        if not qwc or not vertices:
            raise ValueError("empty mesh draw packet")
        pck.decoded_vertices += vertices
        if pck.decoded_vertices > MAX_VERTICES:
            raise ValueError("PCK decoded vertex budget exceeded")
        packet = pck.pointer(packet_pointer, qwc * 16)
        batches = decode_batches(vif_planes(pck, packet, qwc * 16))
        if sum(len(b["positions"]) for b in batches) != vertices:
            raise ValueError("draw descriptor vertex count mismatch")
        draws.append({"material": pck.u16(materials + i * 2), "descriptor_offset": descriptor,
                      "packet_offset": packet, "packet_bytes": qwc * 16,
                      "vertex_count": vertices, "batches": batches})
    return {"offset": offset, "vtable": pck.u32(offset), "draws": draws,
            "source": pck.fingerprint()}


def read_mesh(path: Path | str) -> dict:
    pck = Pck.file(path)
    if pck.kind != 22:
        raise ValueError("unknown standalone mesh carrier profile")
    return read_mesh_object(pck, 128)


def read_group(pck: Pck, offset: int) -> list[dict]:
    if pck.u16(offset) != 2 or pck.u32(offset + 4) not in GROUP_VTABLES:
        raise ValueError("unknown mesh collection profile")
    count = pck.u16(offset + 2)
    if not 1 <= count <= MAX_PARTS:
        raise ValueError("part count outside bound")
    arrays = [pck.pointer(pck.u32(offset + field), count * 4) for field in (8, 12, 16)]
    parts = []
    for i in range(count):
        mesh, name, bone = [pck.u32(array + i * 4) for array in arrays]
        mesh_offset = pck.pointer(mesh) if mesh else None
        parts.append({"name": pck.text(name), "bone": bone, "mesh_offset": mesh_offset,
                      "mesh": read_mesh_object(pck, mesh_offset) if mesh else None})
    return parts


def read_bones(pck: Pck, offset: int) -> dict:
    """Read the shipped 0x44-byte rest-joint tree and raw rotation vectors.

    FUN_0058dc18 supplies the joint layout and translation ancestry rule.
    Rotation composition is intentionally left to the renderer's proven path.
    """
    count = pck.u16(offset)
    if not 1 <= count <= MAX_PARTS:
        raise ValueError("invalid bone count")
    start = pck.pointer(pck.u32(offset + 8), count * 68)

    def joint_index(pointer: int) -> int | None:
        if not pointer:
            return None
        target = pck.pointer(pointer, 68)
        delta = target - start
        if delta < 0 or delta % 68 or delta // 68 >= count:
            raise ValueError("bone reference outside joint array")
        return delta // 68

    bones = []
    for index in range(count):
        joint = start + index * 68
        if pck.u16(joint + 56) != index:
            raise ValueError("bone index mismatch")
        position = struct.unpack_from("<3f", pck.data, joint)
        local = struct.unpack_from("<3f", pck.data, joint + 32)
        rotation = struct.unpack_from("<3f", pck.data, joint + 44)
        if not all(math.isfinite(value) for vector in (position, local, rotation) for value in vector):
            raise ValueError("nonfinite bone frame")
        parent_pointer = pck.u32(joint + 28)
        bones.append({"index": index, "offset": joint, "name": pck.text(pck.u32(joint + 12)),
                      "parent": joint_index(parent_pointer),
                      "parent_offset": pck.pointer(parent_pointer, 68) if parent_pointer else None,
                      "sibling": joint_index(pck.u32(joint + 20)),
                      "child": joint_index(pck.u32(joint + 24)),
                      "global_position": position, "local_position": local, "rotation_raw": rotation,
                      "flags_raw": pck.u32(joint + 60)})
    if bones[0]["parent"] is not None or bones[0]["sibling"] is not None:
        raise ValueError("invalid bone root")
    visited = set()
    pending = [(0, None)]
    while pending:
        index, parent = pending.pop()
        if index in visited or bones[index]["parent"] != parent:
            raise ValueError("bone ancestry cycle or mismatch")
        visited.add(index)
        bone = bones[index]
        parent_position = bones[parent]["global_position"] if parent is not None else (0, 0, 0)
        if any(abs(bone["local_position"][axis] + parent_position[axis] - bone["global_position"][axis]) > 1e-5 for axis in range(3)):
            raise ValueError("bone rest translation mismatch")
        if bone["sibling"] is not None:
            pending.append((bone["sibling"], parent))
        if bone["child"] is not None:
            pending.append((bone["child"], index))
    if len(visited) != count:
        raise ValueError("unreachable bone records")
    return {"offset": offset, "joint_array_offset": start,
            "header_words_raw": list(struct.unpack_from("<4H", pck.data, offset)), "bones": bones}


def read_vehicle(path: Path | str) -> dict:
    pck = Pck.file(path)
    if pck.kind != 0x38E030:
        raise ValueError("unknown vehicle carrier profile")
    candidates = [offset for offset in range(128, len(pck.data) - 28, 4)
                  if struct.unpack_from("<I", pck.data, offset)[0] in MODEL_VTABLES]
    valid = []
    for candidate in candidates:
        try:
            collection = pck.pointer(pck.u32(candidate + 8), 20)
            groups = [pck.pointer(pck.u32(candidate + field), 20) for field in (16, 20, 24)]
            if pck.u32(collection) in MATERIAL_VTABLES and all(pck.u16(g) == 2 and pck.u32(g + 4) in GROUP_VTABLES for g in groups):
                valid.append(candidate)
        except ValueError:
            continue
    candidates = valid
    if len(candidates) != 1:
        raise ValueError("vehicle model root missing or ambiguous")
    root = candidates[0]
    material_collection = pck.pointer(pck.u32(root + 8), 20)
    if pck.u32(material_collection) not in MATERIAL_VTABLES:
        raise ValueError("unknown material collection profile")
    count = pck.u16(material_collection + 8)
    if not 1 <= count <= MAX_PARTS or count != pck.u16(material_collection + 10):
        raise ValueError("material collection count mismatch")
    array = pck.pointer(pck.u32(material_collection + 4), count * 4)
    materials = [{"index": i, "offset": pck.pointer(pck.u32(array + i * 4))}
                 for i in range(count)]
    lods = {name: read_group(pck, pck.pointer(pck.u32(root + field), 20))
            for name, field in (("high", 16), ("middle", 20), ("low", 24))}
    skeleton = read_bones(pck, pck.pointer(pck.u32(root + 104), 12))
    for parts in lods.values():
        for part in parts:
            if part["bone"] >= len(skeleton["bones"]):
                raise ValueError("mesh bone index outside vehicle skeleton")
            if part["mesh"] and any(draw["material"] >= count for draw in part["mesh"]["draws"]):
                raise ValueError("mesh material index outside vehicle table")
    return {"source": pck.fingerprint(), "profile": "mc3-ps2-serialized-vif-v1",
            "model_offset": root, "model_vtable": pck.u32(root),
            "material_collection_offset": material_collection,
            "materials": materials, "lods": lods, "skeleton": skeleton,
            "claim_limits": ["Rotation interpretation and customization selection require separate evidence.",
                             "Native per-vertex flags remain uninterpreted.",
                             "Colour scale candidates require rendered validation; UV scale 1/4096 and orientation were checked against rendered livery lettering."]}


def read_resource_group(path: Path | str) -> dict:
    """Read the same exact vehicle profile's fully embedded shared HLOD group.

    Name keys are case-sensitive source strings. Duplicate names and unresolved
    meshes reject the resource carrier; no filename similarity is consulted.
    """
    vehicle = read_vehicle(path)
    named = {}
    for part in vehicle["lods"]["high"]:
        if part["name"] in named:
            raise ValueError("duplicate shared resource name")
        if part["mesh"] is None:
            raise ValueError("unresolved shared resource mesh")
        named[part["name"]] = part
    return {"source": vehicle["source"], "model_offset": vehicle["model_offset"],
            "material_collection_offset": vehicle["material_collection_offset"],
            "materials": vehicle["materials"], "skeleton": vehicle["skeleton"],
            "parts": named, "profile": vehicle["profile"], "claim_limits": vehicle["claim_limits"]}
