"""Source-bound MC3 material input order and generated-texture ownership.

Raw default words remain untyped: individual native binders choose integer or
floating interpretations. This does not synthesize gameplay state or pixels.
"""

import hashlib
import json
from pathlib import Path
import struct


EVIDENCE = (
    Path(__file__).resolve().parents[1]
    / "research/evidence/midnight-club-3-remix/previews/vehicle-inputs-native.json"
)
PROOF_SHA = "b9e6d05cf7331c209223328f18ead7a0615125afbe3231f8359ed2b8c8fd10f8"
FRAGMENT_SHA = "5f3569c66e2a43b3429c374861433cc59516a3ff4d289e429cc1e1cc10e882ec"


def digest(value):
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()


def need(condition, message):
    if not condition:
        raise ValueError(message)


def source_contract(receipt=None):
    proof = json.loads(EVIDENCE.read_text()) if receipt is None else receipt
    need(digest(proof) == PROOF_SHA, "vehicle input source receipt changed")
    return proof


def from_executable(data):
    from mc3_environment_raster import _read_elf

    proof = source_contract()
    need(
        hashlib.sha256(data).hexdigest() == proof["source_executable_sha256"],
        "vehicle input executable identity changed",
    )
    for row in proof["intervals"].values():
        raw = _read_elf(data, row["start"], row["end"] - row["start"])
        need(
            hashlib.sha256(raw).hexdigest() == row["sha256"],
            "vehicle input source interval changed",
        )
    return proof


def native_material_inputs(data, collection_offset, to_offset=None):
    """Retain native list order, names and original default words for one table.

    The caller binds the material collection. PPF callers must supply their
    actual page pointer conversion; this function never selects a collection.
    """
    source_contract()
    need(type(data) is bytes and len(data) >= 128, "invalid vehicle input carrier")
    base = struct.unpack_from("<I", data)[0]
    pointer = to_offset or (lambda value: value - base + 128)

    def bounds(offset, size):
        need(
            type(offset) is int and 0 <= offset <= offset + size <= len(data),
            "vehicle input read outside carrier",
        )
        return offset

    bounds(collection_offset, 16)
    head = struct.unpack_from("<I", data, collection_offset + 12)[0]
    rows, seen = [], set()
    while head:
        offset = bounds(pointer(head), 12)
        need(
            offset not in seen and len(rows) < 256, "vehicle input cycle or count limit"
        )
        seen.add(offset)
        head, name_pointer, word = struct.unpack_from("<3I", data, offset)
        need(name_pointer != 0, "null vehicle input name")
        start = bounds(pointer(name_pointer), 1)
        end = data.find(b"\0", start, min(start + 128, len(data)))
        need(end > start, "invalid vehicle input name extent")
        raw = data[start:end]
        need(all(32 <= byte < 127 for byte in raw), "non-ASCII vehicle input name")
        rows.append(
            {
                "index": len(rows),
                "name": raw.decode("ascii"),
                "word": word,
                "source_offset": offset,
                "name_offset": start,
            }
        )
    return rows


def fragment_fixture():
    proof = json.loads(EVIDENCE.with_name("vehicle-inputs-fragments.json").read_text())
    need(digest(proof) == FRAGMENT_SHA, "vehicle input fragments changed")
    return proof


def verify_fragment_source(data):
    proof = fragment_fixture()
    need(
        len(data) == proof["source_bytes"]
        and hashlib.sha256(data).hexdigest() == proof["source_sha256"],
        "vehicle input fixture source identity changed",
    )
    for row in proof["fragments"]:
        raw = bytes.fromhex(row["hex"])
        need(
            data[row["offset"] : row["offset"] + len(raw)] == raw,
            "vehicle input source fragment changed",
        )
    actual = native_material_inputs(data, proof["collection_offset"])
    need(actual == proof["expected_inputs"], "vehicle input original list changed")
    return {"inputs": len(actual), "source_fragments": len(proof["fragments"])}


def native_input_table(data, collection_offset, to_offset=None):
    """Package source identity alongside the ordered inputs for GLB metadata."""
    rows = native_material_inputs(data, collection_offset, to_offset)
    return {
        "schema": 1,
        "source_carrier_sha256": hashlib.sha256(data).hexdigest(),
        "collection_offset": collection_offset,
        "inputs": rows,
        "claim_limits": [
            "Serialized source defaults only; runtime-appended defaults and actor updates are not fabricated.",
            "Raw words have binder-specific float/integer interpretations.",
            "Collection belongs to this original source carrier, never an adapter buffer.",
        ],
    }
