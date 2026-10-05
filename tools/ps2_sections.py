"""Bounded offline section-chain translation of FR2 FUN_0011ed90.

Serialized spans are kept separate from expanded memory records. Names refer to
loader offsets/strides; their game meaning remains unresolved.
"""
from __future__ import annotations

import struct

import ps2_container
from evidence_common import Incomplete, Invalid

MAX_BYTES = 128 * 1024 * 1024
MAX_RECORDS = 1_000_000
LATER_PROFILES = ("loader68", "measured_legacy60")


class Reader:
    def __init__(self, data: bytes, offset: int):
        self.data = data
        self.pos = offset

    def take(self, size: int, what: str) -> int:
        at = self.pos
        if size < 0 or at < 0 or size > len(self.data) - at:
            raise Invalid(f"{what} at {at:#x} (+{size}) exceeds {len(self.data)} bytes")
        self.pos += size
        return at

    def word(self, what: str) -> int:
        return struct.unpack_from("<I", self.data, self.take(4, what))[0]

    def count(self, what: str, mask: int = 0xFFFFFFFF) -> int:
        value = self.word(what) & mask
        if value > MAX_RECORDS:
            raise Invalid(f"{what} count {value} exceeds {MAX_RECORDS}")
        return value

    def span(self, count: int, stride: int, what: str, aligned: bool = False) -> dict:
        if count < 0 or count > MAX_RECORDS:
            raise Invalid(f"{what} count {count} outside 0..{MAX_RECORDS}")
        size = count * stride
        at = self.take(size, what)
        end = self.pos
        if aligned:
            self.take(ps2_container.align16(end) - end, what + " alignment")
        return {"offset": at, "count": count, "stride": stride, "size": size, "end": end}


def header(reader: Reader) -> dict:
    """FUN_00121420: 8-byte prefix plus flag-dependent four-byte slots."""
    at = reader.take(8, "geometry header")
    flags, count, third, fourth = struct.unpack_from("<4H", reader.data, at)
    size = 20 if flags & 0x800 else 0
    size += 4 if flags & 0x100 else 0
    size += 4 if third == 0xFFFF or flags & 6 else 0
    size += 4 * sum(bool(flags & bit) for bit in (8, 0x10, 0x40, 0x80))
    reader.take(size, "geometry header optional slots")
    return {"offset": at, "size": reader.pos - at, "flags": flags,
            "count": count, "third": third, "fourth": fourth}


def geometry(data: bytes, parsed: dict) -> tuple[Reader, dict]:
    start = parsed["next_section"]["offset"]
    r = Reader(data, start)
    count = r.count("0x34 record table")
    table = r.span(count, 0x34, "0x34 record table")
    groups = []
    total = 0
    for i in range(count):
        at = table["offset"] + i * 0x34
        pair = struct.unpack_from("<H", data, at + 0x1C)[0], struct.unpack_from("<H", data, at + 0x28)[0]
        total += sum(pair)
        groups.append(pair)
    if total > MAX_RECORDS:
        raise Invalid(f"geometry header total {total} exceeds {MAX_RECORDS}")
    headers = [header(r) for _ in range(total)]
    header_end = r.pos
    r.take(ps2_container.align16(r.pos) - r.pos, "geometry header alignment")
    payload_start = r.pos
    for h in headers:
        n, flags = h["count"], h["flags"]
        planes = {"six_byte": r.span(n, 6, "six-byte geometry plane", True)}
        if flags & 0x800:
            planes["twenty_byte"] = r.span(n, 20, "twenty-byte geometry plane", True)
        planes["four_byte"] = r.span(n, 4, "four-byte geometry plane", True)
        if h["third"] != 0xFFFF:
            planes["third_four_byte"] = r.span(n, 4, "third four-byte geometry plane", True)
        for bit in (0x40, 0x80):
            if flags & bit:
                planes[f"flag_{bit:02x}"] = r.span(n, 4, f"flag {bit:#x} geometry plane", True)
        h["planes"] = planes
    return r, {"section_start": start, "table": table, "group_header_counts": groups,
               "header_count": total, "header_end": header_end, "payload_start": payload_start,
               "section_end": r.pos, "headers": headers}


def parse(data: bytes, later_profile: str = "loader68") -> dict:
    if len(data) > MAX_BYTES:
        raise Invalid(f"model exceeds {MAX_BYTES} byte processing bound")
    if later_profile not in LATER_PROFILES:
        raise Invalid(f"unsupported later-section profile {later_profile!r}")
    textures = ps2_container.parse(data)
    r, geo = geometry(data, textures)
    global_at = r.pos
    if later_profile == "loader68":
        r.take(68, "later-section global header")
        raw_header_words = list(struct.unpack_from("<17I", data, global_at))
        if raw_header_words[0] != 17:
            raise Incomplete("later-section header is outside the measured 17-word profile",
                             {"geometry_end": geo["section_end"],
                              "observed_first_word": raw_header_words[0],
                              "profile": later_profile})
        counts = raw_header_words.copy()
    else:
        r.take(60, "measured legacy 15-word global header")
        raw_header_words = list(struct.unpack_from("<15I", data, global_at))
        # This measured profile omits the ordinary ignored 0x11 word and its
        # final global word. Keep its observed words separate from this logical
        # allocation array so callers can audit the mapping.
        counts = [17] + raw_header_words + [0]
    if any(n > MAX_RECORDS for n in counts[1:]):
        raise Invalid("later-section counts exceed the processing bound")
    records = []
    node_counts = {"node_80": 0, "node_2c": 0, "pairs": 0}

    def nodes(kind: str, roots: int) -> list[dict]:
        """Iterative preorder cursor translation; no Python recursion on untrusted input."""
        result = []
        pending = [0] * roots
        while pending:
            depth = pending.pop()
            node_counts[kind] += 1
            if node_counts[kind] > MAX_RECORDS or depth > 256:
                raise Invalid(f"{kind} traversal exceeds node/depth processing bound")
            if kind == "node_80":
                span = r.span(1, 108, "FUN_001205e0 serialized node")
                children = struct.unpack_from("<I", data, span["offset"] + 12)[0]
            else:
                span = r.span(1, 32, "FUN_001208d0 fixed words")
                pairs = r.count("FUN_001208d0 pair descriptor", 0x3F)
                span["pairs"] = r.span(pairs, 8, "FUN_001208d0 pairs")
                node_counts["pairs"] += pairs
                children = r.count("FUN_001208d0 children", 0xFF)
            if children > MAX_RECORDS - node_counts[kind] - len(pending):
                raise Invalid(f"{kind} children exceed remaining node budget")
            span["children"] = children
            span["depth"] = depth
            span["serialized_end"] = r.pos
            result.append(span)
            pending.extend([depth + 1] * children)
        return result

    for i in range(counts[1]):
        at = r.pos
        if [r.word("record sentinel") for _ in range(4)] != [0xFFFFFFFF] * 4:
            raise Invalid(f"record {i} sentinel is not four 0xffffffff words at {at:#x}")
        index = r.word("record index")
        if index >= counts[1]:
            raise Invalid(f"record index {index} outside {counts[1]} expanded records")
        flags = r.word("record six-bit count") & 0x3F
        entry = {"offset": at, "index": index, "expanded_70": r.span(flags, 80, "0x70 memory entries")}
        entry["entries_1c"] = r.span(r.count("0x1c entries"), 28, "0x1c entries")
        entry["vectors_c"] = r.span(r.count("0xc vectors"), 12, "0xc vectors")
        entry["references_8"] = r.span(r.count("references_8", 0xFF), 8, "8-byte references")
        signed = r.count("signed-halfword entries", 0xFFFF)
        if signed >= 0x8000:
            raise Invalid("negative signed-halfword entry count outside measured profile")
        entry["expanded_24"] = r.span(signed, 32, "0x24 memory entries")
        options = r.word("record options")
        entry["options"] = options
        if options & 4:
            entry["optional_1c"] = r.span(r.count("optional_1c"), 28, "optional 0x1c entries")
        if options & 2:
            entry["optional_halfword"] = r.word("optional halfword slot") & 0xFFFF
            entry["nodes_80"] = nodes("node_80", r.count("node_80 roots", 0xFF))
        entry["floats"] = r.span(r.count("float list", 0xFF), 4, "float list")
        entry["node_2c_capacity"] = r.count("node_2c allocation count")
        entry["pair_capacity"] = r.count("pair allocation count")
        pairs_before = node_counts["pairs"]
        entry["references_4"] = r.span(r.count("reference list", 0xFF), 4, "reference list")
        entry["halfwords"] = [r.word("halfword slot") & 0xFFFF for _ in range(3)]
        entry["pairs"] = r.span(r.count("record pairs", 0xFF), 8, "record pairs")
        node_counts["pairs"] += entry["pairs"]["count"]
        roots = r.count("record final roots", 0xFF)
        if options & 1:
            entry["literal_roots"] = r.span(roots, 4, "literal roots")
        else:
            before = node_counts["node_2c"]
            entry["nodes_2c"] = nodes("node_2c", roots)
            if node_counts["node_2c"] - before > entry["node_2c_capacity"]:
                raise Invalid("recursive nodes exceed the record allocation count")
        if node_counts["pairs"] - pairs_before > entry["pair_capacity"]:
            raise Invalid("recursive/record pairs exceed the record allocation count")
        entry["end"] = r.pos
        records.append(entry)

    observed = [0] * 17
    for entry in records:
        for index, key in ((2, "references_8"), (3, "expanded_24"), (4, "expanded_70"),
                           (6, "entries_1c"), (8, "vectors_c"), (12, "references_4"),
                           (13, "floats"), (16, "optional_1c")):
            observed[index] += entry.get(key, {}).get("count", 0)
        observed[5] += bool(entry["entries_1c"]["count"])
        observed[7] += bool(entry["vectors_c"]["count"])
        observed[9] += entry["node_2c_capacity"]
        observed[10] += entry["pair_capacity"]
        observed[11] += entry.get("literal_roots", {}).get("count", 0)
    observed[14] = node_counts["node_80"]
    for index in range(2, 17):
        if index != 15 and counts[index] != observed[index]:
            raise Invalid(f"global allocation word {index} is {counts[index]}, observed {observed[index]}")

    tail_start = r.pos
    tail = {}
    if counts[15]:
        packed, floats = r.count("packed table count"), r.count("six-float table count")
        tail["table_counts"] = r.span(counts[15], 4, "packed table group counts")
        group_counts = [
            struct.unpack_from("<I", data, tail["table_counts"]["offset"] + 4 * i)[0]
            for i in range(counts[15])
        ]
        if any(n > MAX_RECORDS for n in group_counts):
            raise Invalid("packed table group count exceeds the processing bound")
        if sum(group_counts) > packed:
            raise Invalid("packed table group ranges exceed the packed entry allocation")
        tail["packed"] = r.span(packed, 4, "packed u16,u8,u8 table")
        tail["six_floats"] = r.span(floats, 24, "six-float table")
        # stack_21c is used only to relocate already-loaded nodes; no input is read there.
    rows, row_values = r.count("row table count"), r.count("row allocation count")
    tail["row_allocation_count"] = row_values
    tail["rows"] = [r.span(r.count("row value count"), 24, "six-float row") for _ in range(rows)]
    if sum(row["count"] for row in tail["rows"]) != row_values:
        raise Invalid("row payload count differs from its allocation count")
    final, vectors, byte_capacity = r.count("final record count"), r.count("final vector count"), r.count("final byte count")
    tail["final_allocation_counts"] = [final, vectors, byte_capacity]
    tail["records"] = []
    for _ in range(final):
        at = r.pos
        raw, n, size = r.word("final raw word"), r.count("final vectors"), r.count("final bytes")
        item = {"offset": at, "raw_word": raw, "byte_span": r.span(size, 1, "final bytes")}
        item["fixed"] = r.span(1, 60, "final 15-word serialized body")
        item["vectors"] = r.span(n, 144, "final 36-float vectors") if n else r.span(1, 28, "final seven-float body")
        item["end"] = r.pos
        tail["records"].append(item)
    observed_vectors = sum(item["vectors"]["count"] for item in tail["records"] if item["vectors"]["stride"] == 144)
    observed_bytes = sum(item["byte_span"]["count"] for item in tail["records"])
    if observed_vectors != vectors or observed_bytes != byte_capacity:
        raise Invalid("final vector/byte payload counts differ from their allocation counts")
    logical_end = r.pos
    padding = ps2_container.align16(logical_end) - logical_end
    at = r.take(padding, "final 16-byte alignment")
    if any(data[at:r.pos]):
        raise Invalid("final alignment padding is not zero")
    if r.pos != len(data):
        raise Invalid(f"section chain ends at {r.pos:#x}, file ends at {len(data):#x}")
    return {"tree": textures["tree"], "textures": textures["textures"], "geometry": geo,
            "later": {"section_start": global_at, "profile": later_profile,
                      "global_header": {"offset": global_at,
                                        "size": 68 if later_profile == "loader68" else 60,
                                        "raw_words": raw_header_words},
                      "global_words": counts, "records": records, "node_counts": node_counts},
            "tail": {"section_start": tail_start, **tail, "logical_end": logical_end, "padding": padding},
            "end": r.pos, "bytes": len(data), "exact_eof": True}
