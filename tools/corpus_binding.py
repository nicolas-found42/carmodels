"""Bind corpus-mode verifiers to the pinned archive baseline.

After `corpus_identity()` has pinned the executable, archive header and archive data, the archive's
own independent read defines which files should exist and what each one's SHA-256 is. Nothing here
depends on hard-coded counts or on the historical extraction manifest.
"""

from dataclasses import dataclass
from pathlib import Path

from corpus_contract import corpus_identity
from evidence_common import Incomplete, Invalid, sha256
from format_contracts import archive

MAX_BYTES = 128 * 1024 * 1024
PREVIEW = 5


@dataclass(frozen=True)
class Entry:
    path: str  # archive path, exact case with the ;1 suffix
    disk: Path
    bytes: int
    sha256: str

    @property
    def name(self) -> str:
        return self.path.rsplit("/", 1)[-1]

    def load(self) -> bytes:
        """Read the file once, bounded, and require it to equal the archive's independent output.

        Messages omit the file name; callers prefix it. The size is compared before any read so a
        huge replacement file is rejected without being loaded."""
        if self.bytes > MAX_BYTES:
            raise Invalid(f"{self.bytes} bytes exceeds the {MAX_BYTES} byte processing bound")
        size = self.disk.stat().st_size
        if size != self.bytes:
            raise Invalid(f"content differs from the archive baseline output (length {size} vs {self.bytes})")
        data = self.disk.read_bytes()
        if sha256(data) != self.sha256:
            raise Invalid("content differs from the archive baseline output (SHA-256 mismatch)")
        return data


class Baseline:
    def __init__(self, game: Path):
        self.files_root = game / "extracted" / "files"
        if not self.files_root.is_dir():
            raise Incomplete(f"corpus files directory missing: {self.files_root}")
        self.provenance = corpus_identity(game)
        extracted = game / "extracted"
        self._files = archive((extracted / "FILES.HDR").read_bytes(), (extracted / "FILES.DAT").read_bytes())["files"]

    def entries(self, *suffixes: str) -> list[Entry]:
        """Expected files whose archive path ends with a suffix (case-insensitive); missing ones are incomplete."""
        found = [
            Entry(f["path"], self.files_root / f["path"].lstrip("/"), f["output_bytes"], f["output_sha256"])
            for f in self._files
            if f["path"].lower().endswith(tuple(s.lower() for s in suffixes))
        ]
        missing = [e.path for e in found if not e.disk.is_file()]
        if missing:
            raise Incomplete(
                f"{len(missing)} of {len(found)} files expected by the archive are missing on disk: "
                + ", ".join(missing[:PREVIEW])
                + (" ..." if len(missing) > PREVIEW else ""),
                {"expected_files": len(found), "missing_files": missing},
            )
        return found

    @staticmethod
    def _by_stem(found: list[Entry], suffix: str) -> dict[str, Entry]:
        stems: dict[str, Entry] = {}
        for entry in found:
            stem = entry.path[: -len(suffix)].lower()
            if stem in stems:
                raise Invalid(f"archive paths {stems[stem].path} and {entry.path} differ only by case")
            stems[stem] = entry
        return stems

    def pairs(self, header_suffix: str, payload_suffix: str) -> tuple[list[tuple[Entry, Entry]], list[str]]:
        """(header, payload) entries paired by archive name, plus names that lack a partner in the archive."""
        headers = self._by_stem(self.entries(header_suffix), header_suffix)
        payloads = self._by_stem(self.entries(payload_suffix), payload_suffix)
        unpaired = [e.path for k, e in headers.items() if k not in payloads] + [e.path for k, e in payloads.items() if k not in headers]
        return [(headers[k], payloads[k]) for k in sorted(headers) if k in payloads], sorted(unpaired)
