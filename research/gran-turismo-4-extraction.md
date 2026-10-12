# Gran Turismo 4 native car extraction

Date: 2026-10-11. Scope: extract GT4's native car files from the supplied disc image
and list them in the source catalog. No geometry or texture decoding.

## Input

| Fact | Value | How established |
| --- | --- | --- |
| Disc image | `Gran Turismo 4 (axekin.com).iso`, 5,660,540,928 bytes, SHA-256 `efcb2ac8…830ef5` | hashed locally; pinned in `gran-turismo-4/cars/index.json` |
| Region/boot | `SYSTEM.CNF`: `BOOT2 = cdrom0:\SCES_517.19;1`, `VMODE = PAL` | read from the ISO9660 tree |
| Volume | `GT4.VOL;1`, LBA 105,879, 3,084,849,152 bytes | ISO9660 directory record |
| Disc layout | The ISO9660 volume covers 1,622,400 sectors; the image has 2,763,936. Every selected GT4.VOL extent lies inside the file's ISO9660 extent, so no data past it is read | extent bounds checked per file |

## Volume format

Sources (format reference only; no code was copied):

- GT Modding Hub, [PS2 GT4 RoFS](https://github.com/Nenkai/gt-modding-hub/blob/master/docs/formats/volume/ps2_gt4_volume.md)
  and [GT4 file structure](https://nenkai.github.io/gt-modding-hub/ps2/gt4/file_structure/).
- [Razer2015/GT4FS](https://github.com/Razer2015/GT4FS) at commit `b938f71f`, `Volume.cs`,
  `TocHeader.cs`, `Node.cs`, `Entries/RecordEntry.cs` and `GT.Shared/Polyphony/PS2Zip.cs`.
  The repository declares no licence, so the repo's Python reader is written independently.

What `tools/gt4_volume.py` implements, and what the real disc confirmed:

1. The volume starts with a decoy GT3-style table. The real table is the first 2 KiB page
   whose big-endian magic is `0xAD90B9AC` (bitwise NOT of `RoFS`; encrypted) or `RoFS`
   (plain), with little-endian version `0x00030001`. On this disc it is page `0x2159`
   (offset `0x10AC800`), matching the hub's value for retail GT4.
2. Header: compressed table length 435,187; 213 header pages; page length 0x800; 474 table pages.
3. Page offsets follow at +0x40, each XORed with `0x14AC327A × (index + 1)`. The decoded
   offsets start at `0x40 + 4 × 475` and end at the compressed length, as required.
4. Each table page is raw DEFLATE (stored as one non-final block) and inflates to exactly
   0x800 bytes, then every byte is XORed with `0x55`. 6 pages are index pages (skipped;
   they only accelerate lookup) and 468 are entry pages.
5. Entry records: big-endian parent node id + ASCII name; type byte 0 = directory (node id),
   1 = file (page, `time_t`, size), 2 = compressed (page, `time_t`, stored size, size).
   The tree has one root (`.`, node 1) and 21,620 records: 432 directories and 21,188 files.
6. File data starts after the header pages; a file sits at `data_offset + page × 0x800`.
   Compressed files are PS2Zip: big-endian `0xC5EEF7FF`, little-endian negated size, then
   raw DEFLATE.

The reader rejects a missing table, unknown header bytes, out-of-order offsets, a page
that does not inflate to one page, entries outside their page, unknown types, unsafe or
duplicate paths, missing/cyclic parents, extents outside the volume and PS2Zip
size/stream mismatches. Each of those has a control in `tools/test_gt4_volume.py`.

## Car files

| Volume path | Files | Header | Reading |
| --- | ---: | --- | --- |
| `car/lod/<code>` | 730 | `CAR4` | race model |
| `car/lod/<code>.pat` | 730 | `Pat0` | colour patch |
| `car/menu/<code>` | 730 | `CAR4` | menu/showroom model |
| `car/open/<code>`, `.pat` | 57 + 57 | `CAR4`, `Pat0` | open-top variant |
| `wheel/{lod,menu}/<name>` | 1,159 + 1,159 | `MDLS` | wheels; 730 names equal a car code |
| `wheel/open/<name>` | 36 | `MDLS` | open-top wheels; 14 names equal a car code |
| `tire/{lod,menu}`, `wing/{lod,menu}` | 90 + 89, 21 + 21 | `MDLS` | shared parts |

The role names are readings of the directory layout and the hub's file-structure page.
Every one of the 6,802 files under `car/`, `wheel/`, `tire/` and `wing/` is a compressed
entry and inflated to its table size with no trailing data.

Selection (`tools/extract_gt4_cars.py`): one car per `car/lod` model code; a car takes its
`car/*` files and the wheels named with its exact code. Other wheels, tires and wings go
to `shared/`. The spec database `specdb/GT4_EU2560/` (except 944 `RACES/` rows) and the
complete volume table are kept under `provenance/`. Result: 730 cars, 3,778 per-car files
(882,541,058 bytes), 6,591 output files in total (942,613,925 bytes). File timestamps
range from 2004-03-31 to 2005-01-26 (UTC).

## Source catalog

`tools/import_gt4_catalog.py` re-derives the extraction from the ISO, then writes one ZIP
per car to `dealership/public/gran-turismo-4/native/` (730 packages, 310,020,706 bytes,
284,513–740,386 bytes each) and an `index.json`. ZIP members are the car's files at
their volume paths plus `manifest.json`. `tools/build_model_catalog.py` validates each
package through a per-game validator and lists them as `gran-turismo-4/<code>` with
`asset_kind: native-package` and variant `native`. The catalog has 1,715 entries.

Equality is judged on decoded members, not ZIP bytes: a different zlib build may encode
DEFLATE differently. The offline check (`import_gt4_catalog.py --check`, check name
`gt4_catalog`) requires every member to equal the extraction byte for byte. The extraction and the
ZIPs are local (about 590 MB of git objects, two copies of the same native data); the committed
`cars/index.json` and source `index.json` pin every file's SHA-256.

## Verification

| Command | Result |
| --- | --- |
| `python3 tools/extract_gt4_cars.py --check` | `CHECKED 730 cars, 6591 files, 942613925 bytes` (also under stock Python 3.9.6) |
| `python3 tools/import_gt4_catalog.py --check` | `CHECKED 730 GT4 source packages` |
| `tools/check.sh` | all checks pass, including the new `test_gt4_volume`, `test_extract_gt4_cars`, `test_import_gt4_catalog`, `gt4_catalog` and `gt4_extraction` |
| `recovered.html?game=gran-turismo-4` (local `serve_library.py`) | 730 entries; `acra0001` serves a 396,681-byte ZIP; status reads "5 native files · 3D preview unavailable"; no console errors |

`gt4_extraction` runs only where the ISO is present; elsewhere it is reported as a skip.

## Tooling notes

The task asked to consult [awesome-ghidra](https://github.com/AllsafeCyberSecurity/awesome-ghidra).
It lists general Ghidra scripts, plugins and teaching material; none targets PS2 or GT4
data formats. The volume is a data format with published documentation and a strong
self-check (every table page and payload must inflate to its declared length), so no
executable analysis was needed for this extraction. `CORE.GT4` (the packed executable)
was not opened. Ghidra/REA analysis becomes relevant for CAR4 geometry decoding.

## Not established

- Model decoding, previews and retail names were added later; see
  [gran-turismo-4-previews.md](gran-turismo-4-previews.md). The 810 `specdb/.../CARS` rows versus
  730 models remain unexplained.
- Owners of the 880 shared wheels, runtime dependency closure and load precedence.
- Anything about other GT4 regions or builds; only this PAL disc was read.
