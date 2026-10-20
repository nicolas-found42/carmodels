"""Source-pinned GT1 native identities, specifications and colour-name joins.

Only exact SPEC codes acquire names or statistics. Native racing/special source
families remain independent: suffix similarity is never an identity join. Values
describe the native base specification, not arbitrary installed tuning or a
measurement of a recovered mesh. Year and manufacturer joins remain unresolved.
"""

import base64
import copy
import hashlib
import json
import math
from pathlib import Path
import re
import struct
import zlib

ROOT = Path(__file__).resolve().parents[1]
LOOKUPS = ROOT / "research/evidence/gran-turismo-metadata/native-lookups.json"
LOOKUPS_SHA256 = "1e31cb469d843293ed80f4cbeef097550536dffd8188a12359009f0ddde7b397"
SPEC_SHA256 = "80a8e585b52faf712ab295b831507d97ce2c155c890256c446525460703fceac"
COLOUR_SHA256 = "55c96636f6d403231ededb8626085101d5ec3eef63ad9bb3010c8ac406c273d9"
SYSTEM_SHA256 = "1af60e0df9d44ff890c2a82979f4b689228cc6128b45053685873b6c2c97223b"
LIMITS = [
    "Native base specifications only; installed tuning and racing-family relationships are not inferred.",
    "Year and manufacturer are unresolved; native model/grade spelling is preserved.",
    "Metadata dimensions describe game specifications, not independently measured exported geometry.",
    "Named colours follow native identifier matching; duplicate and missing identifiers are preserved.",
]


def sha(data):
    return hashlib.sha256(data).hexdigest()


def _u16(data, offset):
    return struct.unpack_from("<H", data, offset)[0]


def _u32(data, offset):
    return struct.unpack_from("<I", data, offset)[0]


def _code(raw):
    if len(raw) != 6 or raw[-1] != 0 or not re.fullmatch(rb"[a-z0-9-]{5}\x00", raw):
        raise ValueError("GT metadata native code outside five-character profile")
    return raw[:5].decode("ascii")


def native_directory(system_data):
    """Return all 344 native CAR directory codes in their source ordinal order."""
    if sha(system_data) != SYSTEM_SHA256:
        raise ValueError("GT metadata SYSTEM source pin differs")
    if (
        len(system_data) != 14768
        or not system_data.startswith(b"@(#)GTENV\0")
        or _u16(system_data, 14) != 344
    ):
        raise ValueError("GT metadata SYSTEM header differs")
    # MENU 800368a8: system table +0x20 + ordinal*6. The table begins +0xb7c.
    codes = [_code(system_data[0xB9C + i * 6 : 0xBA2 + i * 6]) for i in range(344)]
    if len(set(codes)) != len(codes):
        raise ValueError("GT metadata native directory contains duplicate codes")
    return codes


def _section(data, signature, stride):
    """Strict bounded table/string parser; independently exercised with mutations."""
    if (
        len(data) < 28
        or data[:12] != signature.ljust(12, b"\0")
        or _u16(data, 12) != 16
        or _u32(data, 16) != 0
        or _u32(data, 20) != stride
    ):
        raise ValueError("GT metadata section header differs")
    count = _u16(data, 14)
    offset = 24 + count * stride
    if offset + 4 > len(data):
        raise ValueError("GT metadata record extent outside section")
    groups = _u32(data, offset)
    offset += 4 + groups * 4
    if not 1 <= groups <= 16 or offset > len(data):
        raise ValueError("GT metadata string-group extent outside section")
    if any(data[24 + count * stride + 4 : offset]):
        raise ValueError("GT metadata unresolved native string pointers differ")
    strings = []
    for _ in range(groups):
        if offset + 2 > len(data):
            raise ValueError("GT metadata string-count extent outside section")
        size = _u16(data, offset)
        offset += 2
        items = []
        for _ in range(size):
            if offset >= len(data):
                raise ValueError("GT metadata string extent outside section")
            length = data[offset]
            if offset + length + 2 > len(data) or data[offset + length + 1] != 0:
                raise ValueError("GT metadata string extent or terminator differs")
            try:
                value = data[offset + 1 : offset + length + 1].decode("ascii")
            except UnicodeDecodeError as error:
                raise ValueError("GT metadata string is not ASCII") from error
            if any(ord(char) < 32 or ord(char) > 126 for char in value):
                raise ValueError("GT metadata string outside printable profile")
            items.append(value)
            offset += length + 2
        if offset & 1:
            if offset >= len(data) or data[offset] != 0:
                raise ValueError("GT metadata string alignment differs")
            offset += 1
        strings.append(items)
    if any(data[offset:]):
        raise ValueError("GT metadata trailing section bytes differ")
    return [
        data[24 + i * stride : 24 + (i + 1) * stride] for i in range(count)
    ], strings


def _string(strings, reference):
    group, index = reference >> 16, reference & 0xFFFF
    if group >= len(strings) or index >= len(strings[group]):
        raise ValueError("GT metadata string reference outside pool")
    return strings[group][index]


def _lookup_receipt(path=LOOKUPS):
    data = Path(path).read_bytes()
    if sha(data) != LOOKUPS_SHA256:
        raise ValueError("GT metadata native lookup receipt pin differs")
    return json.loads(data)


def _native_colour_rows(receipt):
    raw = zlib.decompress(
        base64.b64decode(receipt["colour_rows_zlib_base64"], validate=True)
    )
    if sha(raw) != receipt["colour_rows_decoded_sha256"]:
        raise ValueError("GT metadata retained colour lookup pin differs")
    return {
        index: [
            {"slot": slot, "colour_id": identifier, "name": name}
            for slot, identifier, name in items
        ]
        for index, items in json.loads(raw)
    }


def _lookup_tables(path=LOOKUPS):
    receipt = _lookup_receipt(path)
    tables = {}
    for name, table in receipt["tables"].items():
        pointers = base64.b64decode(table["pointer_base64"], validate=True)
        values = []
        if len(pointers) != len(table["strings"]) * 4:
            raise ValueError("GT metadata native lookup pointer count differs")
        for index, cell in enumerate(table["strings"]):
            raw = base64.b64decode(cell["base64"], validate=True)
            if (
                _u32(pointers, index * 4) != cell["address"]
                or not raw.endswith(b"\0")
                or b"\0" in raw[:-1]
            ):
                raise ValueError("GT metadata native lookup cell differs")
            values.append(raw[:-1].decode("ascii"))
        tables[name] = values
    pointers = base64.b64decode(receipt["rotary_pointer_base64"], validate=True)
    rotary = {}
    for index, row in enumerate(receipt["rotary"]):
        if struct.unpack_from("<II", pointers, index * 8) != (
            row["key_address"],
            row["factor"],
        ):
            raise ValueError("GT metadata rotary lookup pointer differs")
        key = base64.b64decode(row["key_base64"], validate=True)
        if not re.fullmatch(rb"[a-z0-9-]{4}\x00", key) or row["factor"] not in (
            2,
            3,
            4,
        ):
            raise ValueError("GT metadata rotary lookup cell differs")
        rotary[key[:-1].decode("ascii")] = row["factor"]
    return tables, rotary


def database_from_bytes(spec_bytes, colour_bytes, system_bytes):
    """Decode the pinned retail inputs, also usable before extraction writes files."""
    native_codes = native_directory(system_bytes)
    if sha(spec_bytes) != SPEC_SHA256 or sha(colour_bytes) != COLOUR_SHA256:
        raise ValueError("GT metadata CARINF source pin differs")
    records, strings = _section(spec_bytes, b"@(#)SPEC", 0x1A8)
    color_records, color_strings = _section(colour_bytes, b"@(#)COLOR", 0x54)
    if len(records) != 178 or len(color_records) != 142:
        raise ValueError("GT metadata SPEC/COLOR coverage differs")
    tables, rotary = _lookup_tables()
    specs = {}
    for index, row in enumerate(records):
        code = _code(row[:6])
        if code in specs or code not in native_codes:
            raise ValueError("GT metadata SPEC native identity differs")
        model, grade = (
            _string(strings, _u32(row, offset)) for offset in (0x188, 0x18C)
        )
        values = {
            name: _u16(row, offset)
            for name, offset in {
                "mass_kg": 0x5A,
                "length_mm": 0x194,
                "width_mm": 0x0C,
                "height_mm": 0x0E,
                "wheelbase_mm": 0x10,
                "front_tread_mm": 0x14,
                "rear_tread_mm": 0x16,
                "displacement_raw": 0x196,
                "power_raw": 0x198,
                "power_rpm": 0x19A,
                "torque_raw": 0x19C,
                "torque_rpm": 0x19E,
            }.items()
        }
        for name, table, offset in [
            ("drive", "drive", 0x8A),
            ("aspiration", "aspiration", 0x1A3),
            ("engine_type", "engine_type", 0x1A4),
            ("engine_configuration", "engine_configuration", 0x1A5),
            ("suspension_front", "suspension", 0x1A6),
            ("suspension_rear", "suspension", 0x1A7),
        ]:
            if row[offset] >= len(tables[table]):
                raise ValueError("GT metadata specification enum outside table")
            values[name] = tables[table][row[offset]]
        factor = rotary.get(code[:4])
        values.update(
            power_hp_game=values["power_raw"] * 1000 // 1014,
            power_conversion="floor(raw * 1000 / 1014); native display label HP",
            torque_kgm=values["torque_raw"] / 100,
            displacement_cc=values["displacement_raw"] if factor is None else None,
            displacement_rotary_chamber_cc=654 if factor is not None else None,
            displacement_rotary_factor=factor,
            displacement_display_kind="rotary-chamber-times-factor"
            if factor is not None
            else "cc",
            specification_scope="native-base",
        )
        specs[code] = {
            "spec_index": index,
            "name": " ".join([model, grade]).strip(),
            "native_model_name": model,
            "native_grade_name": grade,
            "specifications": values,
        }
    colors = {}
    for row in color_records:
        spec_index = _u16(row, 0) - 1
        if not 0 <= spec_index < len(records) or spec_index in colors:
            raise ValueError("GT metadata COLOR specification reference differs")
        colors[spec_index] = [
            {
                "slot": slot,
                "colour_id": identifier,
                "name": _string(color_strings, _u32(row, 20 + slot * 4)),
            }
            for slot, identifier in enumerate(row[2:18])
            if identifier
        ]
    retained = _lookup_receipt()
    identities = [
        {
            "code": code,
            "spec_index": row["spec_index"],
            "model": row["native_model_name"],
            "grade": row["native_grade_name"],
        }
        for code, row in specs.items()
    ]
    if (
        identities != retained["identities"]
        or native_codes != retained["native_codes"]
        or colors != _native_colour_rows(retained)
    ):
        raise ValueError("GT metadata retained identity/colour derivation differs")
    return {
        "specs": specs,
        "colours": colors,
        "native_codes": native_codes,
        "provenance": {
            "schema": 1,
            "carinf_spec_sha256": SPEC_SHA256,
            "carinf_colour_sha256": COLOUR_SHA256,
            "system_sha256": SYSTEM_SHA256,
            "native_lookup_sha256": LOOKUPS_SHA256,
            "identity_join": "Exact five-character native code; one archive prefix underscore may be removed.",
            "spec_consumer": "GTMENU 8001f450/8001eb08",
            "colour_consumer": "GTMENU 80032198; identifier OR 0x20; first matching slot",
            "claim_limits": LIMITS,
        },
    }


def load_database(metadata_dir):
    """Require the extracted native shared inputs; never guess a missing table."""
    directory = Path(metadata_dir)
    try:
        return database_from_bytes(
            (directory / "sections/13.bin").read_bytes(),
            (directory / "sections/38.bin").read_bytes(),
            (directory / "SYSTEM.DAT").read_bytes(),
        )
    except FileNotFoundError as error:
        raise ValueError(
            "GT metadata requires CARINF sections13/38 and SYSTEM.DAT; re-extract the source"
        ) from error


def model_metadata(database, code, colour_ids):
    """Join one native family without collapsing or inheriting suffix variants."""
    if not isinstance(code, str) or not re.fullmatch(r"_?[a-z0-9-]{5}", code):
        raise ValueError("GT metadata model code outside exact native profile")
    if (
        not isinstance(colour_ids, list)
        or not 1 <= len(colour_ids) <= 16
        or any(type(value) is not int or not 0 <= value <= 255 for value in colour_ids)
    ):
        raise ValueError("GT metadata colour identifiers outside CTEX profile")
    native_code = code[1:] if code.startswith("_") else code
    if native_code not in database["native_codes"]:
        raise ValueError("GT metadata model code absent from native directory")
    row = database["specs"].get(native_code)
    index = row["spec_index"] if row else None
    name_rows = database["colours"].get(index, [])
    variants, matches = [], []
    for palette, identifier in enumerate(colour_ids):
        found = [item for item in name_rows if item["colour_id"] == (identifier | 0x20)]
        name = found[0]["name"] if found else None
        variants.append(
            {
                "index": palette,
                "colour_id": identifier,
                "name": name,
                "label": name
                if name
                else f"Native colour {palette + 1} (0x{identifier:02x})",
            }
        )
        matches.append(
            {
                "index": palette,
                "lookup_colour_id": identifier | 0x20,
                "matching_slots": copy.deepcopy(found),
            }
        )
    provenance = copy.deepcopy(database["provenance"])
    provenance.update(
        native_code=native_code,
        native_directory_index=(
            database["native_codes"].index(native_code)
            if native_code in database["native_codes"]
            else None
        ),
        colour_name_matches=matches,
        colour_source_slots=copy.deepcopy(name_rows),
    )
    if row:
        provenance.update(
            native_model_name=row["native_model_name"],
            native_grade_name=row["native_grade_name"],
        )
    return {
        "identity": {
            "status": "verified" if row else "unresolved",
            "name": row["name"] if row else None,
            "spec_index": index,
        },
        "specifications": copy.deepcopy(row["specifications"]) if row else None,
        "colour_variants": variants,
        "provenance": provenance,
    }


def validate_model_metadata(metadata):
    """Validate detached export/catalog metadata against retained native lookups.

    This checks exact native identity/colour ownership, numeric shape and derived
    unit conversions. Native source equality of every specification is established
    by the producer's source-pinned decoder, not by a detached catalog record.
    """

    def require(condition, reason):
        if not condition:
            raise ValueError("GT model metadata " + reason)

    def integer(value, low, high):
        return type(value) is int and low <= value <= high

    def same(value, expected):
        if type(value) is not type(expected):
            return False
        if isinstance(expected, dict):
            return value.keys() == expected.keys() and all(
                same(value[key], cell) for key, cell in expected.items()
            )
        if isinstance(expected, list):
            return len(value) == len(expected) and all(
                same(a, b) for a, b in zip(value, expected)
            )
        return value == expected

    require(
        isinstance(metadata, dict)
        and set(metadata)
        == {"identity", "specifications", "colour_variants", "provenance"},
        "top-level shape differs",
    )
    identity, specs = metadata["identity"], metadata["specifications"]
    variants, provenance = metadata["colour_variants"], metadata["provenance"]
    require(
        isinstance(identity, dict)
        and set(identity) == {"status", "name", "spec_index"},
        "identity shape differs",
    )
    require(isinstance(provenance, dict), "provenance shape differs")
    receipt = _lookup_receipt()
    code = provenance.get("native_code")
    require(
        isinstance(code, str) and code in receipt["native_codes"], "native code differs"
    )
    expected = next((row for row in receipt["identities"] if row["code"] == code), None)
    expected_identity = {
        "status": "verified" if expected else "unresolved",
        "name": " ".join([expected["model"], expected["grade"]]).strip()
        if expected
        else None,
        "spec_index": expected["spec_index"] if expected else None,
    }
    require(
        same(identity, expected_identity),
        "identity name/status/index differs from native lookup",
    )
    required_provenance = {
        "schema",
        "carinf_spec_sha256",
        "carinf_colour_sha256",
        "system_sha256",
        "native_lookup_sha256",
        "identity_join",
        "spec_consumer",
        "colour_consumer",
        "claim_limits",
        "native_code",
        "native_directory_index",
        "colour_name_matches",
        "colour_source_slots",
    }
    if expected:
        required_provenance.update(["native_model_name", "native_grade_name"])
        require(
            provenance.get("native_model_name") == expected["model"]
            and provenance.get("native_grade_name") == expected["grade"],
            "native model/grade differs",
        )
    require(set(provenance) == required_provenance, "provenance fields differ")
    for field, value in [
        ("schema", 1),
        ("carinf_spec_sha256", SPEC_SHA256),
        ("carinf_colour_sha256", COLOUR_SHA256),
        ("system_sha256", SYSTEM_SHA256),
        ("native_lookup_sha256", LOOKUPS_SHA256),
        ("claim_limits", LIMITS),
        ("native_directory_index", receipt["native_codes"].index(code)),
        (
            "identity_join",
            "Exact five-character native code; one archive prefix underscore may be removed.",
        ),
        ("spec_consumer", "GTMENU 8001f450/8001eb08"),
        ("colour_consumer", "GTMENU 80032198; identifier OR 0x20; first matching slot"),
    ]:
        require(same(provenance.get(field), value), "provenance " + field + " differs")
    if not expected:
        require(specs is None, "unresolved identity carries specifications")
    else:
        raw_fields = {
            "mass_kg",
            "length_mm",
            "width_mm",
            "height_mm",
            "wheelbase_mm",
            "front_tread_mm",
            "rear_tread_mm",
            "displacement_raw",
            "power_raw",
            "power_rpm",
            "torque_raw",
            "torque_rpm",
        }
        enum_fields = {
            "drive": "drive",
            "aspiration": "aspiration",
            "engine_type": "engine_type",
            "engine_configuration": "engine_configuration",
            "suspension_front": "suspension",
            "suspension_rear": "suspension",
        }
        derived_fields = {
            "power_hp_game",
            "power_conversion",
            "torque_kgm",
            "displacement_cc",
            "displacement_rotary_chamber_cc",
            "displacement_rotary_factor",
            "displacement_display_kind",
            "specification_scope",
        }
        require(
            isinstance(specs, dict)
            and set(specs) == raw_fields | set(enum_fields) | derived_fields,
            "specifications shape differs",
        )
        for field in raw_fields:
            upper = (
                10000
                if field == "mass_kg"
                else 30000
                if field.endswith("_mm")
                else 65535
            )
            lower = (
                1
                if field == "mass_kg" or field.endswith("_mm") or field == "power_raw"
                else 0
            )
            require(
                integer(specs[field], lower, upper),
                "numeric " + field + " outside profile",
            )
        tables, rotary = _lookup_tables()
        for field, table in enum_fields.items():
            require(specs[field] in tables[table], "enum " + field + " differs")
        require(
            integer(specs["power_hp_game"], 0, 65535)
            and specs["power_hp_game"] == specs["power_raw"] * 1000 // 1014,
            "power conversion differs",
        )
        require(
            type(specs["torque_kgm"]) in (int, float)
            and math.isfinite(specs["torque_kgm"])
            and specs["torque_kgm"] == specs["torque_raw"] / 100,
            "torque conversion differs",
        )
        require(
            specs["power_conversion"]
            == "floor(raw * 1000 / 1014); native display label HP"
            and specs["specification_scope"] == "native-base",
            "specification qualification differs",
        )
        factor = rotary.get(code[:4])
        require(
            same(specs["displacement_rotary_factor"], factor)
            and same(specs["displacement_rotary_chamber_cc"], 654 if factor else None)
            and same(
                specs["displacement_cc"], None if factor else specs["displacement_raw"]
            )
            and specs["displacement_display_kind"]
            == ("rotary-chamber-times-factor" if factor else "cc"),
            "displacement representation differs",
        )
    require(
        isinstance(variants, list) and 1 <= len(variants) <= 16,
        "colour variants shape differs",
    )
    source_slots = _native_colour_rows(receipt).get(
        expected["spec_index"] if expected else None, []
    )
    require(
        same(provenance.get("colour_source_slots"), source_slots),
        "native colour slots differ",
    )
    matches = []
    for index, variant in enumerate(variants):
        require(
            isinstance(variant, dict)
            and set(variant) == {"index", "colour_id", "name", "label"},
            "colour variant fields differ",
        )
        identifier = variant["colour_id"]
        require(
            integer(variant["index"], 0, 15)
            and variant["index"] == index
            and integer(identifier, 0, 255),
            "colour index/identifier differs",
        )
        found = [row for row in source_slots if row["colour_id"] == (identifier | 0x20)]
        name = found[0]["name"] if found else None
        require(
            variant["name"] == name
            and variant["label"]
            == (name if name else f"Native colour {index + 1} (0x{identifier:02x})"),
            "native colour name/label differs",
        )
        matches.append(
            {
                "index": index,
                "lookup_colour_id": identifier | 0x20,
                "matching_slots": found,
            }
        )
    require(
        same(provenance.get("colour_name_matches"), matches),
        "colour match provenance differs",
    )
    return metadata
