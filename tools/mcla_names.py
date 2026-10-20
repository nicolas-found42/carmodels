"""Read MCLA version-11 localization tables and join vehicle codes to exact UI keys.

The cache member is little-endian, including its UTF-16 text. Names are copied from
the English table only when the original ASCII key equals the complete vehicle code;
hash equality alone is insufficient. Unknown codes retain their archive identifier.
This establishes shipped text, not a retail identity or a runtime playable roster.
"""

import argparse
import hashlib
import json
from pathlib import Path
import re
import struct
import sys

from mcla_rpf import jenkins

SOURCE_ENTRY = 21936
SOURCE_HASH = 0xA4C1E8FA
SOURCE_SHA256 = "c01f84edf4563d21084140839b9ead10405f97ae01949ad4abc90b5fb8a3965d"
SOURCE_BYTES = 2157137
VERSION = 11
HEADER_BYTES = 56
MAX_KEYS = 100000
MAX_TEXT_UNITS = 100000
CODE = re.compile(r"v(?:a|p|pd)_[a-z0-9_]+")
ROOT = Path(__file__).resolve().parents[1]
RECEIPT = ROOT / "research/evidence/midnight-club-los-angeles/display-names.json"
LIMITS = [
    "Names are exact shipped English UI strings, joined by complete ASCII key plus Jenkins hash; "
    "they do not establish retail identity or a runtime playable roster.",
    "Only this pinned localization member is covered; missing codes retain their archive ID. "
    "Ambient identities and the GT-R/city-bus names are unresolved here.",
    "Manufacturer and retail year are unknown; neither is expanded from an archive code. "
    "Surrounding UI whitespace is removed only for display; the original text is retained.",
]


class NamesError(ValueError):
    """Invalid localization structure, ownership, or source identity."""


def need(condition, message):
    if not condition:
        raise NamesError(message)


class Reader:
    def __init__(self, data, start, end):
        self.data, self.at, self.end = data, start, end

    def take(self, count):
        need(0 <= count <= self.end - self.at, "localization field outside section")
        value = self.data[self.at : self.at + count]
        self.at += count
        return value

    def unpack(self, fmt):
        return struct.unpack("<" + fmt, self.take(struct.calcsize("<" + fmt)))

    def text(self, count, encoding):
        try:
            return self.take(count).decode(encoding)
        except UnicodeDecodeError as error:
            raise NamesError("invalid localization text encoding") from error


def parse(data):
    """Return keys and independent language sections, checking every byte and hash join.

    Language positions are numeric: English is position 0 in this source. Repeated
    offsets and offsets equal to EOF represent absent sections; they are not silently
    aliased to another language. No names are synthesized from code components.
    """
    need(len(data) >= HEADER_BYTES, "localization header truncated")
    version, *offsets = struct.unpack_from("<12I", data)
    flags, count = struct.unpack_from("<II", data, 48)
    need(version == VERSION, "unsupported localization version")
    need(flags == 512, "unexpected localization header flags")
    need(0 < count <= MAX_KEYS, "invalid localization key count")
    need(
        HEADER_BYTES < offsets[0] < len(data), "localization first section outside file"
    )
    need(
        offsets == sorted(offsets) and offsets[-1] == len(data),
        "invalid localization section offsets",
    )
    keys_reader = Reader(data, HEADER_BYTES, offsets[0])
    keys, hashes = [], {}
    for _ in range(count):
        (size,) = keys_reader.unpack("I")
        need(0 < size <= 4096, "invalid localization key length")
        key = keys_reader.text(size, "ascii")
        need(
            "\0" not in key and keys_reader.take(1) == b"\0",
            "localization key terminator missing",
        )
        h = jenkins(key)
        need(h not in hashes, "duplicate localization key or hash collision")
        hashes[h] = key
        keys.append(key)
    need(keys_reader.at == keys_reader.end, "trailing localization key bytes")
    languages = {}
    for language, start in enumerate(offsets):
        end = offsets[language + 1] if language + 1 < len(offsets) else len(data)
        if start == end:
            continue
        reader = Reader(data, start, end)
        (entries,) = reader.unpack("I")
        need(entries == count, "localization language/key count mismatch")
        records = {}
        for _ in range(entries):
            offset = reader.at
            h, entry_flags, font_bytes = reader.unpack("IHI")
            need(entry_flags == 1, "unexpected localization entry flags")
            need(font_bytes <= 1024, "invalid localization font length")
            font = reader.text(font_bytes, "ascii")
            need("\0" not in font, "embedded localization font terminator")
            (units,) = reader.unpack("I")
            need(0 < units <= MAX_TEXT_UNITS, "invalid localization text length")
            text = reader.text(units * 2, "utf-16le")
            need(
                text.endswith("\0") and "\0" not in text[:-1],
                "localization text terminator missing",
            )
            scale_x, scale_y, trailer = reader.unpack("ffH")
            need(
                (scale_x, scale_y, trailer) == (1.0, 1.0, 0),
                "unexpected localization record trailer",
            )
            need(h in hashes, "localization record has no source key")
            need(h not in records, "duplicate localization record hash")
            key = hashes[h]
            records[h] = {
                "key": key,
                "hash": h,
                "text": text[:-1],
                "font": font,
                "offset": offset,
            }
        need(reader.at == end, "trailing localization language bytes")
        languages[language] = records
    need(0 in languages, "English localization section missing")
    return {"version": version, "keys": keys, "languages": languages}


def decode_source(data):
    """Parse only the pinned loose cache member from the supplied Complete Edition disc."""
    need(
        len(data) == SOURCE_BYTES and hashlib.sha256(data).hexdigest() == SOURCE_SHA256,
        "MCLA localization source digest mismatch",
    )
    return parse(data)


def display_identity(table, code):
    """Produce catalog identity without guessing manufacturer, retail year, or trim.

    A record under a different key, including a collision or a short/pinkslip key,
    never names this car. The source string is preserved verbatim in name_source.text;
    surrounding UI whitespace alone is removed from the display name.
    """
    need(isinstance(code, str) and CODE.fullmatch(code), "invalid MCLA vehicle code")
    h = jenkins(code)
    record = table["languages"][0].get(h)
    exact = (
        record is not None and record["key"] == code and bool(record["text"].strip())
    )
    source = {"kind": "ui-string" if exact else "code-fallback", "language": 0}
    if exact:
        source.update(key=code, hash=h, offset=record["offset"], text=record["text"])
    return {
        "name": record["text"].strip() if exact else code,
        "manufacturer": "Unknown",
        "year": None,
        "name_source": source,
    }


def identities_for(codes, data=None):
    """Derive identity rows from pinned bytes; missing input safely produces code fallbacks."""
    codes = list(codes)
    need(len(codes) == len(set(codes)), "duplicate MCLA vehicle codes")
    table = decode_source(data) if data is not None else {"languages": {0: {}}}
    return {code: display_identity(table, code) for code in sorted(codes)}


def load_from_disc(iso):
    """Read the pinned localization payload by hash, allowing only identical duplicate members.

    The executable-derived archive key stays in memory and is never returned or logged.
    Hash selection is checked by the full source payload digest before anything is used.
    """
    from extract_mcla_cars import CACHE, locate_key
    from mcla_rpf import Rpf3Archive
    from xdvdfs import XdvdfsDisc
    from xex2 import load_image

    disc = XdvdfsDisc(iso)
    try:
        paths = {entry["path"]: entry for entry in disc.entries}
        need(
            "default.xex" in paths and CACHE in paths,
            "MCLA disc executable/cache missing",
        )
        executable = paths["default.xex"]
        image, _ = load_image(disc.region(executable)(0, executable["size"]))
        key, _ = locate_key(image)
        cache_entry = paths[CACHE]
        cache = Rpf3Archive(disc.region(cache_entry), cache_entry["size"], key)
        matches = [
            entry
            for entry in cache.entries
            if entry["kind"] == "file"
            and not entry["resource"]
            and entry["hash"] == SOURCE_HASH
        ]
        need(matches, "MCLA localization archive member missing")
        payloads = [cache.payload(entry) for entry in matches]
        need(
            all(payload == payloads[0] for payload in payloads),
            "conflicting MCLA localization hash members",
        )
        decode_source(payloads[0])
        return payloads[0]
    finally:
        disc.close()


def derive(codes, data):
    """Compact reproducible receipt: source identity, complete requested coverage and limits."""
    table = decode_source(data)
    identities = identities_for(codes, data)
    resolved = sum(
        row["name_source"]["kind"] == "ui-string" for row in identities.values()
    )
    return {
        "schema": 1,
        "source": {
            "archive": "xarchive_cache.rpf",
            "member_hash": "%08x" % SOURCE_HASH,
            "bytes": len(data),
            "sha256": SOURCE_SHA256,
        },
        "table": {
            "version": table["version"],
            "keys": len(table["keys"]),
            "language_sections": sorted(table["languages"]),
        },
        "coverage": {
            "vehicles": len(identities),
            "ui_strings": resolved,
            "code_fallbacks": len(identities) - resolved,
        },
        "vehicles": [{"id": code, **row} for code, row in identities.items()],
        "claim_limits": LIMITS,
    }


def main(argv=None):
    from extract_mcla_cars import DEFAULT_ISO
    from verifier_common import finish

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--iso", type=Path, default=DEFAULT_ISO)
    parser.add_argument(
        "--table", type=Path, help="Pinned loose UI table instead of disc input"
    )
    parser.add_argument(
        "--index",
        type=Path,
        default=ROOT / "games/midnight-club-los-angeles/cars/index.json",
    )
    parser.add_argument("--receipt", type=Path, default=RECEIPT)
    parser.add_argument("--write", action="store_true")
    args = parser.parse_args(argv)
    if not (args.table or args.iso).is_file():
        parser.error("MCLA localization input missing: provide --iso or --table")
    try:
        index = json.loads(args.index.read_text())
        data = args.table.read_bytes() if args.table else load_from_disc(args.iso)
        receipt = derive([row["id"] for row in index["vehicles"]], data)
        # Structural mutations are independent of the source digest guard.
        for label, offset, value, expected in [
            ("version", 0, 10, "unsupported localization version"),
            (
                "language_offset",
                4,
                len(data) + 1,
                "localization first section outside file",
            ),
            ("key_count", 52, 0, "invalid localization key count"),
        ]:
            mutated = bytearray(data)
            struct.pack_into("<I", mutated, offset, value)
            try:
                parse(mutated)
            except NamesError as error:
                need(
                    str(error) == expected,
                    "localization control rejected for unrelated reason",
                )
            else:
                raise NamesError("localization control escaped: " + label)
        receipt["controls"] = ["version", "language_offset", "key_count"]
        return finish(
            receipt,
            args.receipt,
            ["--write"] if args.write else [],
            ROOT,
            receipt["coverage"],
        )
    except (ValueError, OSError) as error:
        print("FAIL: " + str(error))
        return 1


if __name__ == "__main__":
    sys.exit(main())
