"""Bounded FR2 archive and asset profiles. Unknown words are retained as data."""

import struct
import zlib
from evidence_common import Invalid, sha256

FILE = 0xFFFFFFFF
CHUNK = 2048
MAX_OUTPUT = 128 * 1024 * 1024


def require(condition, message):
    if not condition:
        raise Invalid(message)


def words(data, offset, count, label):
    require(
        0 <= offset <= len(data) and 0 <= count <= (len(data) - offset) // 4,
        f"{label}: truncated words at {offset:#x}, count={count}",
    )
    return struct.unpack_from(f"<{count}I", data, offset)


def archive_header(hdr: bytes) -> dict:
    (nseg,) = words(hdr, 0, 1, "archive header")
    require(nseg > 0 and nseg <= (len(hdr) - 4) // 8, "invalid segment count")
    table_end = 4 + nseg * 8
    (declared_count,) = words(hdr, table_end, 1, "record count")
    start = table_end + 4
    require((len(hdr) - start) % 28 == 0, "truncated archive record")
    count = (len(hdr) - start) // 28
    require(
        count == declared_count, "declared record count differs from available records"
    )
    segments = [words(hdr, 4 + i * 8, 2, "segment") for i in range(nseg)]
    covered = set()
    for size, first in segments:
        require(
            first <= count and size <= count - first, "segment span exceeds records"
        )
        for i in range(first, first + size):
            require(i not in covered, "overlapping segment partition")
            covered.add(i)
    require(len(covered) == count, "segments do not partition records")
    records = []
    for i in range(count):
        off = start + i * 28
        name = hdr[off : off + 16]
        require(b"\0" in name, f"record {i}: unterminated name")
        end = name.index(0)
        require(
            end > 0 and all(32 <= b < 127 for b in name[:end]),
            f"record {i}: invalid name",
        )
        # Bytes after the first NUL are uninitialized in the measured corpus.
        text = name[:end].decode("ascii")
        require(
            text not in {".", ".."} and not any(c in text for c in "/\\"),
            f"record {i}: unsafe path",
        )
        kind, chunk, stored = words(hdr, off + 16, 3, "record")
        require(kind == FILE or kind < nseg, f"record {i}: invalid directory segment")
        records.append(
            {
                "idx": i,
                "name": text,
                "type": kind,
                "u1": chunk,
                "u2": stored,
                "hdr_span": [off, off + 28],
                "name_tail_hex": name[end:].hex(),
            }
        )
    paths, active, visited, claimed = {}, set(), set(), set()
    # Explicit stack avoids recursion on attacker-controlled directory chains.
    stack = [(0, "", False)]
    while stack:
        seg, prefix, leave = stack.pop()
        if leave:
            active.remove(seg)
            continue
        require(seg not in active, f"directory cycle at segment {seg}")
        require(seg not in visited, f"segment {seg} referenced more than once")
        visited.add(seg)
        active.add(seg)
        stack.append((seg, prefix, True))
        size, first = segments[seg]
        children = []
        for i in range(first, first + size):
            r = records[i]
            path = prefix + "/" + r["name"]
            require(path not in claimed, f"duplicate path {path}")
            claimed.add(path)
            paths[i] = path
            if r["type"] != FILE:
                children.append((r["type"], path, False))
        stack.extend(reversed(children))
    require(
        len(paths) == count and len(visited) == nseg,
        "unreachable archive records or segments",
    )
    for record in records:
        record["path"] = paths[record["idx"]]
    return {"segments": [list(segment) for segment in segments], "records": records}


def archive(hdr: bytes, dat: bytes) -> dict:
    parsed = archive_header(hdr)
    segments, records = parsed["segments"], parsed["records"]
    nseg, count = len(segments), len(records)
    files, spans = [], []
    for r in records:
        if r["type"] != FILE:
            continue
        offset, stored = r["u1"] * CHUNK, r["u2"]
        require(
            offset <= len(dat) and stored <= len(dat) - offset,
            f"record {r['idx']}: file span exceeds DAT (short read)",
        )
        blob = dat[offset : offset + stored]
        classification, decoded, trailing = decode_payload(blob)
        item = dict(
            r,
            dat_span=[offset, offset + stored],
            classification=classification,
            output_bytes=len(decoded),
            output_sha256=sha256(decoded),
            stored_sha256=sha256(blob),
            wrapper_padding=trailing,
        )
        files.append(item)
        spans.append((offset, offset + stored))
    spans.sort()
    end, unused = 0, []
    for begin, stop in spans:
        require(begin >= end, "overlapping file data spans")
        if begin > end:
            unused.append({"span": [end, begin], "sha256": sha256(dat[end:begin])})
        end = stop
    if end < len(dat):
        unused.append({"span": [end, len(dat)], "sha256": sha256(dat[end:])})
    return {
        "segments": [list(s) for s in segments],
        "records": records,
        "files": files,
        "unused_dat": unused,
        "counts": {
            "segments": nseg,
            "records": count,
            "files": len(files),
            "raw": sum(f["classification"] == "raw" for f in files),
            "zlib": sum(f["classification"] == "zlib" for f in files),
        },
    }


def decode_payload(blob: bytes):
    if len(blob) >= 6 and blob[4] == 0x78 and blob[5] in {1, 0x5E, 0x9C, 0xDA}:
        (declared,) = words(blob, 0, 1, "zlib length")
        require(declared <= MAX_OUTPUT, "declared output exceeds bounded profile")
        d = zlib.decompressobj()
        try:
            decoded = d.decompress(blob[4:], declared + 1)
        except zlib.error as exc:
            raise Invalid(f"corrupt zlib stream: {exc}") from exc
        require(d.eof and not d.unconsumed_tail, "incomplete or oversized zlib stream")
        require(
            len(decoded) == declared,
            f"zlib output length mismatch: {len(decoded)} != {declared}",
        )
        require(
            not d.unused_data or not any(d.unused_data), "nonzero trailing zlib bytes"
        )
        return (
            "zlib",
            decoded,
            {"bytes": len(d.unused_data), "sha256": sha256(d.unused_data)},
        )
    return "raw", blob, {"bytes": 0, "sha256": sha256(b"")}


def bank(data: bytes, payload: bytes) -> dict:
    self_size, unknown, count = words(data, 0, 3, "bank header")
    require(self_size == len(data), "bank self-size mismatch")
    require(count > 0, "empty descriptor set is unsupported")
    require(count <= (len(data) - 12) // 16, "descriptor count/bounds mismatch")
    tail = data[12 + count * 16 :]
    require(
        len(tail) <= 64 and not any(tail),
        "bank descriptor tail must be bounded zero padding",
    )
    end, descriptors = 0, []
    for i in range(count):
        off = 12 + i * 16
        size, raw, start, rate = words(data, off, 4, "descriptor")
        require(start == end, f"descriptor {i}: broken start/length chain")
        require(
            size <= len(payload) - start, f"descriptor {i}: sample span exceeds bank"
        )
        end = start + size
        descriptors.append(
            {
                "descriptor_span": [off, off + 16],
                "sample_span": [start, end],
                "length": size,
                "unknown": raw,
                "rate": rate,
            }
        )
    require(end == len(payload), "descriptors do not cover paired bank")
    return {
        "self_size": self_size,
        "unknown": unknown,
        "count": count,
        "descriptors": descriptors,
        "payload_codec": "unknown",
        "padding_span": [12 + count * 16, len(data)],
    }


def model(data: bytes) -> dict:
    leading, root_count = words(data, 0, 2, "model header")
    require(root_count > 0, "model has no root names; pool boundary unresolved")
    roots = list(words(data, 8, root_count, "root names"))
    offsets = roots.copy()
    pos = 8 + root_count * 4
    groups = []
    lowest = min(offsets)  # running minimum: recomputing it per group made parsing quadratic
    while pos < lowest:
        (size,) = words(data, pos, 1, "group count")
        require(
            size <= (lowest - pos - 4) // 4, "group crosses string-pool boundary"
        )
        names = list(words(data, pos + 4, size, "group names"))
        groups.append({"span": [pos, pos + 4 + size * 4], "offsets": names})
        offsets.extend(names)
        lowest = min([lowest, *names])
        pos += 4 + size * 4
    require(pos == min(offsets), "name-tree boundary does not equal string-pool start")
    names = []
    last_end = pos
    for off in offsets:
        require(pos <= off < len(data), f"name offset {off:#x} out of range")
        end = data.find(b"\0", off, min(len(data), off + 61))
        require(
            end > off and all(32 <= b < 127 for b in data[off:end]),
            f"unterminated/invalid model name at {off:#x}",
        )
        names.append(
            {"offset": off, "end": end + 1, "name": data[off:end].decode("ascii")}
        )
        last_end = max(last_end, end + 1)
    return {
        "leading_count": leading,
        "leading_count_semantics": "unresolved",
        "roots": roots,
        "groups": groups,
        "names": names,
        "string_pool_start": pos,
        "remaining_span": [last_end, len(data)],
        "remaining_sha256": sha256(data[last_end:]),
        "geometry": "not decoded",
    }


def sprite(data: bytes) -> dict:
    header = list(words(data, 0, 8, "sprite header"))
    count, a, b, stride, cell, width, height, one = header
    require(
        0 < width <= stride and height > 0,
        "sprite dimensions exceed stride or are empty",
    )
    require(one == 1 and cell == 32 and count == 1, "unsupported sprite header profile")
    # Measured index ordering exchanges bits 3 and 4 in each 32-entry block.
    pattern = b"".join(
        bytes([227, 227, 227, (i & ~24) | ((i & 8) << 1) | ((i & 16) >> 1)])
        for i in range(256)
    )
    start = data.find(pattern[:4], 32, min(len(data), 1024))
    require(start >= 32, "unsupported sprite pattern table")
    require(
        data[start : start + 1024] == pattern, "truncated or invalid sprite table span"
    )
    image_start = start + 1024
    require(
        height <= (len(data) - image_start) // stride, "truncated sprite rows/payload"
    )
    row_end = image_start + height * stride
    require(
        len(data) in {row_end, image_start + cell * stride},
        "unsupported trailing sprite allocation",
    )
    require(all(v == 0xDD for v in data[row_end:]), "incorrect trailing sprite padding")
    pixels = bytearray()
    for row in range(height):
        off = image_start + row * stride
        pixels.extend(data[off : off + width])
        require(
            all(v == 0xDD for v in data[off + width : off + stride]),
            f"sprite row {row}: incorrect padding",
        )
    return {
        "header": header,
        "unknown_words": [a, b],
        "width": width,
        "height": height,
        "stride": stride,
        "table_span": [start, image_start],
        "table_role": "unknown",
        "prefix_span": [32, start],
        "prefix_hex": data[32:start].hex(),
        "payload_span": [image_start, row_end],
        "padding_span": [row_end, len(data)],
        "pixel_sha256": sha256(bytes(pixels)),
    }
