#!/usr/bin/env python3
"""Extract Midnight Club: Los Angeles native car files from the supplied Xbox 360 disc image.

The disc is XDVDFS; car data sits in the RPF3 archive `xarchive_cache.rpf`, whose table is
AES-encrypted. The key is located inside the disc's own `default.xex` image by its SHA-256
pin, so no key is stored in this repository. Archive names are hashes; names are recovered
only from strings found on the same disc: the executable, loose cache members and the string
fields of the LZX-decompressed streaming pack maps (plus level variants of `_lod_<n>` names).
Selection is a declared namespace boundary, not inferred runtime closure. RSC5 resources stay as
stored (LZX-compressed); --check derives every output again from the disc.
"""

import argparse
import hashlib
import json
from pathlib import Path
import re
import tempfile
import zlib

from mc3_archive import safe_name
from mcla_lzx import decompress
from mcla_resource import string_records
from mcla_rpf import Rpf3Archive, jenkins_final, jenkins_partial
from xdvdfs import XdvdfsDisc
from xex2 import load_image

ROOT = Path(__file__).resolve().parents[1]
GAME = "Midnight Club: Los Angeles"
DEFAULT_ISO = (
    ROOT
    / "games/midnight-club-los-angeles/game-files/Midnight Club - Los Angeles - Complete Edition (USA, Europe).iso"
)
KEY_SHA256 = "71f5abd83015a713952b7c2f2c25289f92f3cf9a9dd740c40a511a62ea5b505c"
CACHE = "xarchive_cache.rpf"
VEHICLES = "resources/vehicle/"
CONFIGS = VEHICLES + "configs/"
AMBIENTS = "resources/ambients/"
AMBIENT_PAINT = "tune/ambients/traffic/"
UI = "resources/ui/textures/garage/"
SHARED = (
    "resources/rims/",
    "resources/tires/",
    "resources/brakes/",
    "vehicle/",
    "tune/vehicle/",
)
CODE = re.compile(r"v(?:a|p|pd)_[a-z0-9_]+")
# File extensions tried after recovered stems: a reading of the resource-type table in
# CodeX.Games.MCLA plus loose-file extensions seen in recovered names.
RESOURCE_EXTENSIONS = (
    "xrsc",
    "xtp",
    "xtl",
    "xspm",
    "xct",
    "xtd",
    "xdr",
    "xft",
    "xwt",
    "xshp",
    "xcs",
    "xapk",
    "xmd",
    "xbtm",
    "xsf",
    "xaph",
    "xapb",
    "xck",
    "xmp",
    "xlm",
)
EXTENSIONS = RESOURCE_EXTENSIONS + ("xcc", "mesh", "type", "dds", "xml")
TOKEN = re.compile(rb"[A-Za-z0-9_./\\\-]{3,120}")
STEM = re.compile(r"[a-z0-9_\-]{1,100}")
LOD = re.compile(r"(.+_lod_)[0-9]")
LOD_LEVELS = 4  # a RAGE drawable keeps four levels of detail
LOD_VARIANT = "lod-variant"
STREAMING_MAP = 19
ORIGINS = ("disc-string", "streaming-map", LOD_VARIANT)
LIMITS = [
    "Native archive extraction: RSC5 resources are written as stored (LZX-compressed). Only the streaming "
    "pack maps are decompressed here, to read their strings; model, texture and tuning decoding are separate tools.",
    "Car IDs are vehicle directory names under resources/vehicle/ (vp_ player, vpd_ downloadable-content "
    "player, va_ ambient), not decoded retail names or a verified playable roster.",
    "Archive names are 32-bit hashes. A name is resolved only when exactly one plausible candidate hashes to it; "
    "candidates are strings from this disc (the executable, loose cache members and the string fields of the "
    "streaming pack maps) and levels 0-3 of their _lod_<n> names. Other entries keep 0x<hash> names. A resolved "
    "name can still be a hash collision; name_origin records which source offered it.",
    "Configs and garage UI textures join a car only when its full code occurs in the file name; rims, tires, "
    "brakes, shared vehicle effects and vehicle tuning are shared with ownership unknown.",
    "Selection is a declared namespace boundary; runtime dependency closure and load precedence are unknown.",
    "Checks establish byte extraction and source preservation, not game execution or visual fidelity.",
]


def sha(data):
    return hashlib.sha256(data).hexdigest()


def json_bytes(value):
    return (json.dumps(value, indent=1, sort_keys=True) + "\n").encode()


def source_digests(path):
    sha256, sha1 = hashlib.sha256(), hashlib.sha1()
    with Path(path).open("rb") as stream:
        while chunk := stream.read(8 * 1024 * 1024):
            sha256.update(chunk)
            sha1.update(chunk)
    return sha256.hexdigest(), sha1.hexdigest()


def locate_key(image):
    """The single 4-byte-aligned 32-byte window of the executable image matching the pin."""
    hits = [
        at
        for at in range(0, len(image) - 31, 4)
        if sha(image[at : at + 32]) == KEY_SHA256
    ]
    if len(hits) != 1:
        raise ValueError("archive key not found exactly once in default.xex")
    return image[hits[0] : hits[0] + 32], hits[0]


def components(texts):
    """Lower-cased names and their path components."""
    names = set()
    for text in texts:
        text = text.lower().replace("\\", "/")
        names.add(text)
        names.update(text.split("/"))
    names.discard("")
    return names


def harvest(blobs):
    """Lower-cased names and path components found as printable runs in the supplied bytes."""
    return components(
        match.decode("ascii") for blob in blobs for match in TOKEN.findall(blob)
    )


def streaming_map_names(cache):
    """Strings named by string fields of every streaming pack map (resource type 19) in the cache."""
    texts, maps = [], 0
    for entry in cache.entries:
        if (
            entry["kind"] == "file"
            and entry["resource"]
            and entry["resource_type"] == STREAMING_MAP
        ):
            data, header = decompress(cache.stored(entry))
            texts.extend(string_records(data, header["virtual"]))
            maps += 1
    return components(texts), maps


def dictionary(sources, wanted):
    """Hash -> sorted candidate names, and each candidate's origin.

    `sources` is a sequence of (origin, names), earliest origin first; a candidate keeps the first origin
    that offers it. Names are offered as-is, as an embedded car code and as stems with known extensions;
    a stem ending in `_lod_<digit>` is also offered at levels 0-3 with the origin 'lod-variant'."""
    found, origins = {}, {}

    def offer(name, h, origin):
        if h in wanted and name not in (".", ".."):
            found.setdefault(h, set()).add(name)
            origins.setdefault(name, origin)

    stems = {}
    for origin, names in sources:
        for name in sorted(names):
            offer(name, jenkins_final(jenkins_partial(name)), origin)
            stem = name.rsplit(".", 1)[0] if "." in name else name
            if STEM.fullmatch(stem):
                stems.setdefault(stem, origin)
                # A car code embedded after a prefix (mr_vp_..., msh_vpd_...) is offered on its own.
                parts = stem.split("_")
                for start in range(1, len(parts)):
                    suffix = "_".join(parts[start:])
                    if CODE.fullmatch(suffix):
                        offer(suffix, jenkins_final(jenkins_partial(suffix)), origin)
                        stems.setdefault(suffix, origin)
    for stem in sorted(stems):
        lod = LOD.fullmatch(stem)
        if lod:
            for level in range(LOD_LEVELS):
                stems.setdefault(lod.group(1) + str(level), LOD_VARIANT)
    for stem in sorted(stems):
        state = jenkins_partial(stem + ".")
        for extension in EXTENSIONS:
            offer(
                stem + "." + extension,
                jenkins_final(jenkins_partial(extension, state)),
                stems[stem],
            )
    return {h: sorted(v) for h, v in found.items()}, origins


def plausible(entry, name):
    """Structural agreement between an entry and a candidate name (rejects most hash noise)."""
    if "/" in name:
        return (
            False  # entries hash one path component; a harvested path cannot name one
        )
    extension = name.rsplit(".", 1)[1] if "." in name else ""
    if entry["kind"] == "directory":
        return "." not in name
    return (extension in RESOURCE_EXTENSIONS) == entry["resource"]


class Named:
    """Entry names and archive paths for one RPF3 archive under the disc dictionary."""

    def __init__(self, archive, names, origins=None):
        self.archive, self.names, self.origins = archive, names, origins or {}
        typed = {}
        for entry in archive.entries:
            accepted = self.accepted(entry)
            if entry["kind"] == "file" and entry["resource"] and len(accepted) == 1:
                typed.setdefault(entry["resource_type"], set()).add(
                    accepted[0].rsplit(".", 1)[1]
                )
        # An unresolved resource borrows an extension only when every resolved entry of its type agrees.
        self.extension = {
            kind: next(iter(v)) for kind, v in typed.items() if len(v) == 1
        }
        self.paths = {}
        for entry in archive.entries:
            self.paths[entry["index"]] = self._path(entry)
        seen = set()
        for path in self.paths.values():
            if path.casefold() in seen:
                raise ValueError("duplicate archive path: " + path)
            seen.add(path.casefold())

    def accepted(self, entry):
        return [c for c in self.names.get(entry["hash"], []) if plausible(entry, c)]

    def origin(self, entry):
        """Where the single accepted candidate came from (None for an unresolved entry)."""
        candidates = self.accepted(entry)
        return (
            self.origins.get(candidates[0], ORIGINS[0])
            if len(candidates) == 1
            else None
        )

    def name(self, entry):
        candidates = self.accepted(entry)
        if len(candidates) == 1:
            return candidates[0], "resolved"
        name = "0x%08x" % entry["hash"]
        if entry["kind"] == "file" and entry["resource"]:
            name += "." + self.extension.get(
                entry["resource_type"], "rsc%d" % entry["resource_type"]
            )
        return name, "unresolved"

    def _path(self, entry):
        if entry["parent"] is None:
            return ""
        # Rpf3Archive guarantees a parent precedes its children, so its path is already known.
        path = (
            self.paths[entry["parent"]]
            + self.name(entry)[0]
            + ("/" if entry["kind"] == "directory" else "")
        )
        safe_name(path, directory=entry["kind"] == "directory")
        return path

    def inventory(self):
        rows = []
        for entry in self.archive.entries:
            row = {k: v for k, v in entry.items() if k not in ("parent",)}
            row["path"] = self.paths[entry["index"]]
            row["name_source"] = (
                self.name(entry)[1] if entry["parent"] is not None else "root"
            )
            if row["name_source"] == "resolved":
                row["name_origin"] = self.origin(entry)
            candidates, accepted = (
                self.names.get(entry["hash"], []),
                self.accepted(entry),
            )
            if len(accepted) > 1:
                row["name_candidates"] = accepted
            if len(accepted) < len(candidates):
                row["rejected_candidates"] = [
                    c for c in candidates if c not in accepted
                ]
            rows.append(row)
        return rows


def owner(path, codes):
    """The longest car code occurring as a whole underscore-delimited run in the file stem."""
    stem = "_" + path.rsplit("/", 1)[-1].rsplit(".", 1)[0] + "_"
    matches = [code for code in codes if "_" + code + "_" in stem]
    return max(matches, key=len) if matches else None


def select(named, codes_by_directory):
    """(output prefix, role) for each selected cache file, by declared namespace."""
    codes = sorted(set(codes_by_directory.values()))
    selected = {}
    for entry in named.archive.entries:
        if entry["kind"] != "file":
            continue
        path = named.paths[entry["index"]]
        directory = path.split("/")
        choice = None
        if path.startswith(CONFIGS):
            code = owner(path, codes)
            choice = (code, "config") if code else ("shared", "shared-config")
        elif (
            path.startswith(AMBIENT_PAINT)
            and len(directory) == 5
            and directory[-1] == "mcambientcartypecolor.xml"
        ):
            # Retain the complete native namespace, including unresolved directory
            # hashes. Preview consumers join only an exact known car directory.
            choice = ("shared", "shared-ambient-paint")
        elif path.startswith(VEHICLES) and len(directory) > 3:
            choice = (codes_by_directory[directory[2]], "vehicle-package")
        elif (
            path.startswith(AMBIENTS)
            and len(directory) > 3
            and directory[2] in codes_by_directory
        ):
            # Keyed by archive name, so an unresolved car (0x<hash> in both trees) keeps its ambient files.
            choice = (codes_by_directory[directory[2]], "ambient-definition")
        elif path.startswith(UI):
            code = owner(path, codes)
            choice = (code, "garage-ui-texture") if code else None
        elif path.startswith(SHARED):
            prefix = next(p for p in SHARED if path.startswith(p))
            choice = ("shared", "shared-" + prefix.strip("/").replace("/", "-"))
        if choice:
            selected[entry["index"]] = choice
    return selected


class Output:
    """Emits each output once (case-insensitively unique, safe path) and records its row."""

    def __init__(self, emit):
        self.emit, self.files, self.keys = emit, [], set()

    def put(self, path, data, provenance=None):
        safe_name(path)
        if path.casefold() in self.keys:
            raise ValueError("duplicate output path")
        self.keys.add(path.casefold())
        self.emit(path, data)
        row = {"file": path, "bytes": len(data), "sha256": sha(data)}
        if provenance:
            row["source"] = provenance
        self.files.append(row)
        return row


def open_archives(disc):
    """Decrypt default.xex, locate the archive key in its image and open every RPF3 archive."""
    by_path = {e["path"]: e for e in disc.entries}
    if "default.xex" not in by_path or CACHE not in by_path:
        raise ValueError("default.xex or " + CACHE + " missing")
    xex_entry = by_path["default.xex"]
    xex = disc.region(xex_entry)(0, xex_entry["size"])
    image, xex_facts = load_image(xex)
    key, key_offset = locate_key(image)
    archives = {
        e["path"]: Rpf3Archive(disc.region(e), e["size"], key)
        for e in disc.entries
        if e["kind"] == "file" and e["path"].endswith(".rpf")
    }
    key_record = {
        "algorithm": "AES-256-ECB, sixteen passes over the 16-byte-aligned table prefix",
        "key_sha256": KEY_SHA256,
        "located_in": "default.xex image",
        "image_offset": key_offset,
        "xex_sha256": sha(xex),
        "image_sha256": sha(image),
        "xex": xex_facts,
        "claim_limits": [
            "The key itself is not stored; it is re-located in the pinned disc executable."
        ],
    }
    return image, archives, key_record


def name_sources(image, cache):
    """The executable image, then each loose cache member that is not itself an archive (streamed)."""
    yield image
    for entry in cache.entries:
        if entry["kind"] == "file" and not entry["resource"]:
            data = cache.payload(entry)
            if data[:4] != b"RPF3":
                yield data


def vehicle_codes(cache, named):
    """Vehicle directory name -> car ID; an unresolved directory gets unresolved_<hash>."""
    directory = next(
        (e for e in cache.entries if named.paths[e["index"]] == VEHICLES), None
    )
    if directory is None:
        raise ValueError("resources/vehicle missing from " + CACHE)
    codes = {}
    for index in range(directory["first"], directory["first"] + directory["children"]):
        entry = cache.entries[index]
        name, source = named.name(entry)
        if entry["kind"] != "directory" or name == "configs":
            continue
        if source == "resolved" and not CODE.fullmatch(name):
            raise ValueError("unexpected vehicle directory: " + name)
        codes[name] = (
            name if source == "resolved" else "unresolved_%08x" % entry["hash"]
        )
    if not codes:
        raise ValueError("no vehicle directories found")
    return codes


def emit_cars(out, cache, named, codes, base):
    """Write every selected cache member under its car or shared/, then one manifest per car."""
    selected = select(named, codes)
    cars = {code: [] for code in sorted(codes.values())}
    for index in sorted(selected, key=lambda i: named.paths[i]):
        entry, (prefix, role) = cache.entries[index], selected[index]
        path = named.paths[index]
        stored = cache.stored(entry)
        provenance = {
            "archive": CACHE,
            "archive_path": path,
            "hash": "%08x" % entry["hash"],
            "name_source": named.name(entry)[1],
            "entry": index,
            "archive_offset": entry["offset"],
            "iso_offset": base + entry["offset"],
            "stored_bytes": len(stored),
            "stored_sha256": sha(stored),
            "role": role,
        }
        if named.origin(entry):
            provenance["name_origin"] = named.origin(entry)
        if entry["resource"]:
            provenance.update(
                resource_type=entry["resource_type"],
                flag="%08x" % entry["flag"],
                virtual_bytes=entry["virtual"],
                physical_bytes=entry["physical"],
            )
        else:
            provenance["compressed"] = entry["compressed"]
        row = out.put(prefix + "/" + path, cache.payload(entry), provenance)
        if prefix != "shared":
            cars[prefix].append(row)
    vehicles = []
    for code, rows in cars.items():
        roles = sorted({row["source"]["role"] for row in rows})
        if "vehicle-package" not in roles:
            raise ValueError("car without a vehicle package: " + code)
        out.put(
            code + "/manifest.json",
            json_bytes(
                {"id": code, "files": rows, "roles": roles, "claim_limits": LIMITS}
            ),
        )
        vehicles.append(
            {
                "id": code,
                "manifest": code + "/manifest.json",
                "files": len(rows),
                "bytes": sum(row["bytes"] for row in rows),
                "roles": roles,
                "name_source": "unresolved"
                if code.startswith("unresolved_")
                else "resolved",
            }
        )
    return vehicles


def derive(iso, emit):
    """Emit one payload at a time; the 7.8 GB disc is never held in memory."""
    iso = Path(iso)
    source_pin, source_sha1 = source_digests(iso)
    out = Output(emit)
    disc = XdvdfsDisc(iso)
    try:
        image, archives, key_record = open_archives(disc)
        cache = archives[CACHE]
        harvested = harvest(name_sources(image, cache))
        map_names, maps = streaming_map_names(cache)
        wanted = {
            entry["hash"] for archive in archives.values() for entry in archive.entries
        }
        names, origins = dictionary(
            [(ORIGINS[0], harvested), (ORIGINS[1], map_names)], wanted
        )
        named = {
            path: Named(archive, names, origins) for path, archive in archives.items()
        }
        by_path = {e["path"]: e for e in disc.entries}
        vehicles = emit_cars(
            out,
            cache,
            named[CACHE],
            vehicle_codes(cache, named[CACHE]),
            disc.offset(by_path[CACHE]["sector"]),
        )
        out.put(
            "provenance/disc.inventory.json",
            json_bytes(
                {
                    "generation": disc.generation,
                    "partition_offset": disc.partition,
                    "root": disc.root,
                    "entries": disc.entries,
                    "claim_limits": [
                        "Complete XDVDFS listing; only selected archive members are extracted."
                    ],
                }
            ),
        )
        resolved, by_origin = {}, {}
        for path, archive in archives.items():
            records = named[path].inventory()
            resolved[path] = sum(
                1 for row in records if row["name_source"] == "resolved"
            )
            by_origin[path] = {
                origin: sum(1 for row in records if row.get("name_origin") == origin)
                for origin in ORIGINS
            }
            out.put(
                "provenance/" + path + ".inventory.json",
                json_bytes(
                    {
                        "archive": path,
                        "entries": archive.count,
                        "table_bytes": archive.toc_size,
                        "encrypted": archive.encrypted,
                        "unknown_header_word": archive.unknown,
                        "records": records,
                        "claim_limits": [
                            "Complete decrypted RPF3 table; names are disc-string readings of hashes."
                        ],
                    }
                ),
            )
        out.put("provenance/archive-key.json", json_bytes(key_record))
        if source_digests(iso)[0] != source_pin:
            raise ValueError("disc changed during extraction")
        index = {
            "schema": 1,
            "game": GAME,
            "source": {
                "file": iso.name,
                "bytes": disc.size,
                "sha256": source_pin,
                "sha1": source_sha1,
                "format": "XDVDFS " + disc.generation,
            },
            "archives": {
                path: {
                    "iso_offset": disc.offset(by_path[path]["sector"]),
                    "bytes": by_path[path]["size"],
                    "entries": archive.count,
                    "resolved_names": resolved[path],
                    "resolved_by_origin": by_origin[path],
                }
                for path, archive in archives.items()
            },
            "names": {
                "harvested_strings": len(harvested),
                "streaming_maps": maps,
                "streaming_map_strings": len(map_names),
                "hashes_with_candidates": len(names),
                "ambiguous_hashes": sum(1 for v in names.values() if len(v) > 1),
                "sources": [
                    "disc-string: default.xex image and "
                    + CACHE
                    + " loose (non-resource, non-archive) members",
                    "streaming-map: string fields of every "
                    + CACHE
                    + " streaming pack map (resource type 19), LZX-decompressed",
                    "lod-variant: levels 0-3 of a _lod_<n> name from either source",
                ],
            },
            "selection": {
                "per_car": [
                    VEHICLES + "<code>/",
                    AMBIENTS + "<code>/",
                    CONFIGS + " (full code in name)",
                    UI + " (full code in name)",
                ],
                "shared": list(SHARED)
                + [
                    CONFIGS + " (no code in name)",
                    AMBIENT_PAINT + "<code-or-hash>/mcambientcartypecolor.xml",
                ],
                "provenance": [
                    "XDVDFS listing",
                    "every RPF3 table",
                    "archive key location",
                ],
            },
            "vehicles": vehicles,
            "files": out.files.copy(),
            "claim_limits": LIMITS,
        }
        out.put("index.json", json_bytes(index))
        return index, out.files
    finally:
        disc.close()


def output_files(destination):
    destination = Path(destination)
    if destination.is_symlink() or not destination.is_dir():
        raise ValueError("missing or linked extraction destination")
    found = set()
    for path in destination.rglob("*"):
        if path.is_symlink():
            raise ValueError("linked extraction output")
        if path.is_file():
            found.add(path.relative_to(destination).as_posix())
    return found


def file_sha(path):
    digest = hashlib.sha256()
    with Path(path).open("rb") as stream:
        while chunk := stream.read(1024 * 1024):
            digest.update(chunk)
    return digest.hexdigest()


def check_extraction(iso, destination):
    destination = Path(destination)
    found = output_files(destination)
    expected = set()

    def compare(relative, data):
        expected.add(relative)
        path = destination / relative
        if relative not in found:
            raise ValueError("extraction file coverage mismatch: missing " + relative)
        if path.stat().st_size != len(data) or file_sha(path) != sha(data):
            raise ValueError("extraction byte mismatch: " + relative)

    index, files = derive(iso, compare)
    if expected != found:
        raise ValueError("extraction file coverage mismatch: extra files")
    return index, files


def committed(relative):
    """The extraction files kept in Git (see .gitignore); a fresh clone already has them."""
    return relative == "index.json" or relative.startswith("provenance/")


def write_extraction(iso, destination):
    """Stage the whole extraction, then install it. A destination may already hold only the committed
    index and provenance files, and each of them must equal its newly derived bytes."""
    destination = Path(destination)
    for parent in (destination, *destination.parents):
        if parent.is_symlink():
            raise ValueError("linked extraction destination")
    existing = output_files(destination) if destination.is_dir() else set()
    # A destination holding the input is never empty or committed-only, so this keeps the input out of it.
    if (destination.exists() and not destination.is_dir()) or any(
        not committed(r) for r in existing
    ):
        raise ValueError(
            "destination must be absent or empty, or hold only the committed index.json and provenance/"
        )
    destination.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(
        prefix="mcla-stage-", dir=destination.parent
    ) as temp:
        stage = Path(temp) / "cars"
        stage.mkdir()

        def emit(relative, data):
            path = stage / relative
            path.parent.mkdir(parents=True, exist_ok=True)
            with path.open("xb") as stream:
                stream.write(data)

        index, files = derive(iso, emit)
        for relative in sorted(existing):
            staged = stage / relative
            if not staged.is_file() or file_sha(staged) != file_sha(
                destination / relative
            ):
                raise ValueError(
                    "committed file differs from the derivation: " + relative
                )
        if not existing:
            if destination.exists():
                destination.rmdir()  # Proven empty; no existing content removed.
            stage.rename(destination)
        else:
            for row in files:
                if row["file"] not in existing:
                    target = destination / row["file"]
                    target.parent.mkdir(parents=True, exist_ok=True)
                    (stage / row["file"]).rename(target)
    return index, files


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--iso", type=Path, default=DEFAULT_ISO)
    parser.add_argument(
        "--output", type=Path, default=ROOT / "games/midnight-club-los-angeles/cars"
    )
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    try:
        index, files = (check_extraction if args.check else write_extraction)(
            args.iso, args.output
        )
        print(
            f"{'CHECKED' if args.check else 'EXTRACTED'} {len(index['vehicles'])} cars, "
            f"{len(files)} files, {sum(f['bytes'] for f in files)} bytes"
        )
    except (ValueError, OSError, zlib.error) as error:
        print("ERROR:", error)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
