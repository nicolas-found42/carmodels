"""Read source-bound MC3 shared wheel components without guessing placement.

The shared decal library stores archive/page handles. Config indices select
those handles, not similarly named PPF pages. Geometry stays in native units;
wheel sizing, game deformation and joint rotation are separate renderer work.
"""
from __future__ import annotations

import hashlib
import math
from pathlib import Path
import re
import stat
import struct

from mc3_materials import read_material_table
from mc3_pck import MAX_PARTS, Pck, read_mesh_object
from mc3_textures import bind_material_textures, read_page_slots

MAX_PPF_BYTES = 64 * 1024 * 1024
MODEL_CLASS = 0x7AA728
HANDLE_CLASS = 0x7AA718


def _fingerprint(path: Path, data: bytes) -> dict:
    return {"file": str(path), "bytes": len(data),
            "sha256": hashlib.sha256(data).hexdigest()}


def _source(root: Path, filename: str) -> tuple[Path, bytes, list[dict]]:
    shared = (root / "shared").absolute()
    for entry in [shared, *shared.parents]:
        if entry.is_symlink():
            raise ValueError("symlink in shared wheel source ancestry")
    paths = sorted((root / "shared").rglob(filename))
    if not paths:
        raise ValueError(f"missing shared wheel source: {filename}")
    for path in paths:
        for entry in [path, *path.parents]:
            if entry.is_symlink():
                raise ValueError("symlink in shared wheel source ancestry")
        info = path.stat()
        if not stat.S_ISREG(info.st_mode) or info.st_nlink != 1:
            raise ValueError("nonregular or hard-linked shared wheel source")
        if info.st_size > MAX_PPF_BYTES:
            raise ValueError("shared wheel source outside size bound")
    records = [(path, path.read_bytes()) for path in paths]
    if len({hashlib.sha256(data).digest() for _, data in records}) != 1:
        raise ValueError(f"conflicting shared wheel source copies: {filename}")
    path, data = records[0]
    return path, data, [_fingerprint(p, d) for p, d in records]


def read_default_config(root: Path | str, vehicle_id: str) -> dict:
    """Require byte-identical default configs; never choose numbered customs."""
    if not re.fullmatch(r"vp_[A-Za-z0-9_]+", vehicle_id):
        raise ValueError("invalid vehicle source ID")
    path, data, copies = _source(Path(root), vehicle_id + ".carcfg")
    text = data.decode("ascii")
    fields = {}
    keys = ["RimMdlIdx", "TireMdlIdx", "BikeTireMdlIdx"]
    keys += [f"{name}{axle}" for name in ("RimSize", "TireWidth", "TireProfile")
             for axle in range(2)]
    for key in keys:
        values = re.findall(r"^\s*" + key + r"\s+(-?\d+)\s*$", text, re.MULTILINE)
        if len(values) != 1:
            raise ValueError(f"missing or ambiguous default wheel field: {key}")
        fields[key] = int(values[0])
    return {"source": _fingerprint(path, data), "copies": copies, "fields": fields}


def _collection(library: Pck, offset: int) -> list[int]:
    count = library.u32(offset + 4)
    if not 1 <= count <= MAX_PARTS:
        raise ValueError("wheel library collection count outside bound")
    array = library.pointer(library.u32(offset), count * 4)
    return [library.pointer(library.u32(array + i * 4), 16) for i in range(count)]


def select_handle(library: Pck, collection_offset: int, index: int, archive: int) -> dict:
    rows = _collection(library, collection_offset)
    if not 0 <= index < len(rows):
        raise ValueError("wheel config index outside library collection")
    row = rows[index]
    if library.u32(row) != HANDLE_CLASS:
        raise ValueError("unknown wheel resource handle profile")
    packed = library.u32(row + 12)
    if packed >> 23 != archive:
        raise ValueError("wheel handle selects unexpected native archive")
    return {"library_row_offset": row, "config_index": index,
            "packed_handle": packed, "archive": archive, "page": packed & 0x7FFFFF}


def ppf_page(data: bytes, index: int) -> dict:
    """Native FUN_0042b690 masks: 19-bit sector offset, 12-bit sector length."""
    if not 12 <= len(data) <= MAX_PPF_BYTES or data[:4] != b"pf05":
        raise ValueError("unknown wheel PPF header")
    count = struct.unpack_from("<I", data, 4)[0]
    if not 1 <= count <= MAX_PARTS or 12 + count * 4 > len(data):
        raise ValueError("invalid wheel PPF page table")
    if not 0 <= index < count:
        raise ValueError("wheel page outside PPF table")
    word = struct.unpack_from("<I", data, 12 + index * 4)[0]
    offset, size = (word & 0x7FFFF) << 11, (word >> 20) << 11
    if offset < 12 + count * 4 or not size or offset + size > len(data):
        raise ValueError("wheel PPF page outside source bytes")
    return {"index": index, "packed_page": word, "offset": offset, "bytes": size}


def read_page_model(data: bytes, page: dict, source: str = "memory") -> dict:
    """Adapt the native 32-byte embedded header to existing bounded PCK reads.

    The view's 128-byte header is an in-memory parser adapter. Every payload
    byte is source-exact; offsets in provenance map back to the original PPF.
    """
    start, end = page["offset"], page["offset"] + page["bytes"]
    if start < 0 or end > len(data) or end <= start:
        raise ValueError("wheel model page outside source")
    candidates = []
    for root in range(start + 32, end - 108, 16):
        if struct.unpack_from("<I", data, root)[0] != MODEL_CLASS:
            continue
        base, kind, version, size = struct.unpack_from("<4I", data, root - 32)
        if base and kind == 0 and version == 0 and 108 <= size and root + size <= end:
            candidates.append((root, base, size))
    if len(candidates) != 1:
        raise ValueError("wheel model body missing or ambiguous")
    root, base, size = candidates[0]
    adapter = struct.pack("<4I", base, 0, 1, size) + bytes(112) + data[root:root + size]
    pck = Pck(adapter, source)
    carrier = {"file": source, "bytes": len(data),
               "sha256": hashlib.sha256(data).hexdigest(), "carrier_type": "pf05",
               "model_file_offset": root, "adapter_sha256": pck.sha256}
    material_offset = pck.pointer(pck.u32(136), 16)
    materials = read_material_table(adapter, material_offset)
    lods = {}
    for name, field in (("high", 16), ("middle", 20), ("low", 24)):
        pointer = pck.u32(128 + field)
        if not pointer:
            lods[name] = []
            continue
        group = pck.pointer(pointer, 12)
        count = pck.u16(group + 2)
        if pck.u16(group) != 0 or pck.u32(group + 4) != 0x7A2228 or not 1 <= count <= MAX_PARTS:
            raise ValueError("unknown native wheel mesh collection")
        array = pck.pointer(pck.u32(group + 8), count * 4)
        meshes = [read_mesh_object(pck, pck.pointer(pck.u32(array + i * 4), 24))
                  for i in range(count)]
        for mesh in meshes:
            mesh["source"] = carrier.copy()
            mesh["ppf_file_offset"] = root + mesh["offset"] - 128
            for draw in mesh["draws"]:
                draw["ppf_descriptor_offset"] = root + draw["descriptor_offset"] - 128
                draw["ppf_packet_offset"] = root + draw["packet_offset"] - 128
        if any(draw["material"] >= len(materials) for mesh in meshes for draw in mesh["draws"]):
            raise ValueError("wheel material index outside native table")
        lods[name] = meshes
    for material in materials:
        material["ppf_file_offset"] = root + material["file_offset"] - 128
    page_view = data[start:end]
    slots, skipped = read_page_slots(page_view, root - start, base)
    ppf_materials = [{**m, "file_offset": m["ppf_file_offset"]} for m in materials]
    texture_records = bind_material_textures(data, ppf_materials, slots, {}, 0x1308,
                                              lambda pointer: pointer - base + root)
    return {"model_file_offset": root, "embedded_header_offset": root - 32,
            "serialized_base": base, "payload_bytes": size, "lods": lods,
            "materials": materials, "texture_slots": slots, "skipped_texture_slots": skipped,
            "texture_records": texture_records, "page_offset": start,
            "adapter_offset_rule": "ppf_offset = model_file_offset + adapter_offset - 128",
            "claim_limits": ["Native unscaled component geometry; placement and rotation are not applied.",
                             "Game textures, tire deformation and runtime shading are not emulated."]}


def read_default_wheels(root: Path | str, vehicle_id: str, *, bike: bool = False) -> dict:
    """Select native handles by explicit vehicle class and default config."""
    root = Path(root)
    config = read_default_config(root, vehicle_id)
    fields = config["fields"]
    lib_path, lib_data, lib_copies = _source(root, "decal.pck")
    library = Pck(lib_data, str(lib_path))
    if library.kind != 0x25:
        raise ValueError("unknown native shared wheel library")
    rim = select_handle(library, library.pointer(library.u32(128 + 0x28), 8),
                        fields["RimMdlIdx"], 5)
    selections = [{"component": "rim", "axle": None, **rim}]
    for axle in range(2):
        if bike:
            collection = library.pointer(library.u32(128 + 0x30), 8)
            index = fields["BikeTireMdlIdx"]
        else:
            profile = fields[f"TireProfile{axle}"]
            count = library.u32(128 + 0x44)
            if count != 8 or not 0 <= profile < count:
                raise ValueError("tire profile outside native library")
            profiles = library.pointer(library.u32(128 + 0x2C), count * 4)
            collection = library.pointer(library.u32(profiles + profile * 4), 8)
            index = fields["TireMdlIdx"]
        selections.append({"component": "tire", "axle": axle,
                           **select_handle(library, collection, index, 3)})
    sources = {"library": _fingerprint(lib_path, lib_data), "library_copies": lib_copies}
    archives = {}
    for name in ("rim", "tire"):
        path, data, copies = _source(root, name + ".ppf")
        archives[name] = (path, data)
        sources[name] = _fingerprint(path, data)
        sources[name + "_copies"] = copies
    for selection in selections:
        path, data = archives[selection["component"]]
        page = ppf_page(data, selection["page"])
        selection["page_record"] = page
        selection["model"] = read_page_model(data, page, str(path))
    return {"config": config, "sources": sources, "bike": bike, "components": selections}


EXECUTABLE_SHA256 = '1b237ade5cafaf8ddd9fd049f40d81eb46f38f2600a8f1c7273d4f836973fe9d'


def _elf_address(data: bytes, address: int, size: int) -> int:
    if data[:7] != b'\x7fELF\x01\x01\x01' or len(data) < 52:
        raise ValueError('unknown native wheel sizing ELF profile')
    table = struct.unpack_from('<I', data, 28)[0]
    stride, count = struct.unpack_from('<2H', data, 42)
    if stride != 32 or not 1 <= count <= 64 or table + stride * count > len(data):
        raise ValueError('invalid native wheel sizing ELF segments')
    matches = []
    for i in range(count):
        kind, offset, virtual, _, file_size = struct.unpack_from('<5I', data, table + i * stride)
        if kind == 1 and virtual <= address and address + size <= virtual + file_size:
            candidate = offset + address - virtual
            if candidate + size <= len(data):
                matches.append(candidate)
    if len(matches) != 1:
        raise ValueError('wheel sizing address missing or ambiguous in ELF')
    return matches[0]


def read_native_sizing_tables(executable: bytes | Path | str) -> dict:
    """Read the exact supplied SLUS_213.55 profile, with executable provenance."""
    data = executable if isinstance(executable, bytes) else Path(executable).read_bytes()
    digest = hashlib.sha256(data).hexdigest()
    if digest != EXECUTABLE_SHA256:
        raise ValueError('unsupported wheel sizing executable fingerprint')
    tables = {}
    for name, address, count in (('width', 0x619A18, 9), ('profile', 0x669840, 8),
                                  ('rim', 0x669A10, 17)):
        offset = _elf_address(data, address, count * 4)
        raw = data[offset:offset + count * 4]
        tables[name] = {'address': address, 'elf_offset': offset,
                        'sha256': hashlib.sha256(raw).hexdigest(),
                        'values': list(struct.unpack('<' + 'f' * count, raw))}
    return {'source': {'sha256': digest, 'bytes': len(data), 'profile': 'SLUS_213.55'},
            'tables': tables,
            'native_functions': ['004afb00', '004afab0', '004af9c8', '002f85d0',
                                 '003042c8', '002f6c48', '002c55f0']}


def read_vehicle_class(root: Path | str, vehicle_id: str) -> dict:
    """Read the exact Vehicle/Class record, including nested performance blocks."""
    if not re.fullmatch(r'vp_[A-Za-z0-9_]+', vehicle_id):
        raise ValueError('invalid vehicle source ID')
    path, data, copies = _source(Path(root), 'vehicle.lst')
    text = re.sub(r';[^\r\n]*', '', data.decode('ascii'))
    classes = []
    for match in re.finditer(r'\bVehicle\s*\{', text):
        start, depth, end = match.end(), 1, match.end()
        while depth and end < len(text):
            depth += (text[end] == '{') - (text[end] == '}')
            end += 1
        if depth:
            raise ValueError('unbalanced native vehicle class record')
        record = text[start:end - 1]
        names = re.findall(r'^\s*Name\s+(\S+)\s*$', record, re.MULTILINE)
        if names != [vehicle_id]:
            continue
        values = re.findall(r'^\s*Class\s+(\S+)\s*$', record, re.MULTILINE)
        if len(values) != 1:
            raise ValueError('missing or ambiguous native vehicle class')
        classes.append(values[0])
    if len(classes) != 1:
        raise ValueError('missing or ambiguous native vehicle class record')
    return {'class': classes[0],
            'source': _fingerprint(path, data), 'copies': copies,
            'native_class_value': {'CHOPPER': 5, 'SPORTBIKE': 6, 'COPBIKE': 10}.get(classes[0])}


def read_wheel_sizing(executable: bytes | Path | str, config_fields: dict, *,
                      axle: int, bike: bool = False, vehicle_class: str | None = None,
                      wheel_max_x: float | None = None, wheel_rest_y: float | None = None) -> dict:
    """Compose source-bound static basis scaling; animation and placement are separate.

    Car wheel joints use (2*width, ratio, ratio); the renderer multiplies
    only the rim Y/Z basis by profile diameter. Bike joints use twice their
    rest Y; rim Y/Z additionally receives the class-specific native factor.
    """
    if type(axle) is not int or axle not in (0, 1):
        raise ValueError('invalid native wheel axle')
    native = read_native_sizing_tables(executable)
    fields = config_fields
    if bike:
        if vehicle_class not in ('CHOPPER', 'SPORTBIKE', 'COPBIKE'):
            raise ValueError('unknown native bike class for wheel sizing')
        if wheel_max_x is None or wheel_rest_y is None or not all(
                math.isfinite(v) and 0 < v <= 2 for v in (wheel_max_x, wheel_rest_y)):
            raise ValueError('missing or invalid native bike wheel joint dimensions')
        # FUN_002c55f0 stores these exact float32 defaults; render consumes them.
        width_factor = struct.unpack('<f', struct.pack('<I', 0x3F63D70A))[0]
        rim_factor = struct.unpack('<f', struct.pack('<I',
                                  0x3F59999A if vehicle_class == 'CHOPPER' else 0x3F333333))[0]
        width = width_factor * 4 * wheel_max_x
        diameter = 2 * wheel_rest_y
        rim, tire = [width, diameter * rim_factor, diameter * rim_factor], [width, diameter, diameter]
        inputs = {'class': vehicle_class, 'wheel_constraint_transmax_x': wheel_max_x,
                  'wheel_rest_global_y': wheel_rest_y, 'native_width_factor': width_factor,
                  'native_rim_factor': rim_factor}
    else:
        indices = [fields.get(f'{name}{axle}') for name in ('TireWidth', 'TireProfile', 'RimSize')]
        if any(type(index) is not int for index in indices):
            raise ValueError('missing native car wheel sizing indices')
        width_index, profile_index, rim_size = indices
        if not 0 <= width_index < 9 or not 0 <= profile_index < 8 or not 12 <= rim_size < 29:
            raise ValueError('native car wheel sizing index outside table')
        width = native['tables']['width']['values'][width_index] * 2
        profile = native['tables']['profile']['values'][profile_index]
        diameter = native['tables']['rim']['values'][rim_size - 12]
        ratio = diameter / profile
        rim, tire = [width, diameter, diameter], [width, ratio, ratio]
        inputs = {'width_index': width_index, 'profile_index': profile_index,
                  'rim_size': rim_size, 'profile_diameter': profile, 'rim_profile_ratio': ratio}
    return {'rim_scale': rim, 'tire_scale': tire, 'axle': axle, 'bike': bike,
            'inputs': inputs, 'native': native,
            'claim_limits': ['Static rest pose sizing derived from native renderer; runtime wheel rotation, camber, tire deformation and physics are not emulated.']}
