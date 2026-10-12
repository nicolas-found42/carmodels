# Midnight Club: Los Angeles native car extraction

Date: 2026-10-12. Scope: set up `midnight-club-los-angeles/` from the supplied archive and extract
the game's native car files into `midnight-club-los-angeles/cars/`. No geometry or texture decoding.
Receipt: [`evidence/midnight-club-los-angeles/extraction.json`](evidence/midnight-club-los-angeles/extraction.json).

## Input

| Fact | Value | How established |
| --- | --- | --- |
| Archive | `Midnight Club - Los Angeles - Complete Edition (USA, Europe).7z`, 6,612,480,974 bytes, SHA-256 `cadd0f7b…7986e8` | moved from `~/Downloads` into `game-files/`; hashed locally |
| Disc image | the archive's only image member, 7,838,695,424 bytes, SHA-256 `877a9415…2914e9`, SHA-1 `4ca07fcf…b263` | unpacked with `bsdtar -xf`; SHA-1 equals the Redump value in the archive's `Vimm's Lair.txt`; pinned in `cars/index.json` |
| Platform | Xbox 360, XGD2 layout: XDVDFS volume descriptor at partition offset `0xFD90000`, sector 32 | `MICROSOFT*XBOX*MEDIA` at both ends of the descriptor; the image size is the XGD2 size |
| Disc contents | 16 entries: `default.xex`, four RPF3 archives, Bink videos, a system update | `provenance/disc.inventory.json` |

## Formats

Sources (format reference only; no code was copied — neither repository declares a licence):

- [Foxxyyy/CodeX.Games.MCLA](https://github.com/Foxxyyy/CodeX.Games.MCLA) at `dedc3156`: `RPF3/Rpf3File.cs`
  (header, entry layout, resource flags), `RPF3/Rpf3Crypto.cs` (sixteen AES-256-ECB passes).
- [Raskulk/MCLA-Tools](https://github.com/Raskulk/MCLA-Tools) at `68419cee`: README and `xrsc2obj.py`
  header comments (RSC5 container with Xbox 360 LZX body).
- [GTAMods RPF archive](https://gtamods.com/wiki/RPF_archive): RPF3 is the GTA IV audio / MCLA version.
- XEX2 retail key and header layout as used by the Xenia emulator (`xe_xex2_retail_key`).

All seven fetched source texts were screened with `jev_screen` before use (injection ≤ 0.03; the
three CodeX RPF3 files passed as relevant, the READMEs and the xrsc header were marked not relevant
and were not relied on). Receipt: [`source-screens.json`](evidence/midnight-club-los-angeles/source-screens.json)
records digests of the exact screened text, not the text.

What the repo-owned readers implement, and what the real disc confirmed:

1. **XDVDFS** (`tools/xdvdfs.py`): directory binary trees of 4-byte-aligned records (left/right
   offsets in dwords, sector, size, attributes, name). Records never cross a sector. The reader rejects
   cycles, unsafe or duplicate names, extents outside the image and overlapping files.
2. **XEX2** (`tools/xex2.py`): `default.xex` has normal (AES) encryption and **basic** packing
   (two blocks, 8,617,984 + 622,592 stored bytes with a 1,114,112-byte zero fill), so no LZX is needed.
   The session key is the file key decrypted under the retail key; the image is AES-128-CBC with a zero
   IV. The result starts with `MZ`, has a PE header and is exactly the declared 0x9E0000 bytes.
3. **Archive key**: the 32-byte RPF3 key occurs exactly once in the decrypted image, at offset
   `0x7D8AC4`. The tool finds it by SHA-256 (`71f5abd8…5b505c`) over 4-byte-aligned windows; only the
   digest and offset are recorded (`provenance/archive-key.json`). The pin was taken from the CodeX
   key literal and confirmed by its single occurrence in the disc executable and by the decrypted tables
   passing every structural check below.
4. **RPF3** (`tools/mcla_rpf.py`): little-endian header `RPF3`, table size, entry count, unknown word,
   encryption flag (−1 on all four archives); table at 0x800, AES-256-ECB applied sixteen times. 16-byte
   entries: directories (third word has bit 31) give first child and count; files give size, offset and a
   flag word. Both top flag bits mark an RSC resource whose offset carries the resource type in its low
   byte; otherwise bit 30 marks raw DEFLATE. The reader requires a root directory, contiguous children
   after their parent, exactly one parent per entry, every entry reachable, extents inside the archive,
   exact DEFLATE sizes and the `\x05CSR` (RSC5) header on every resource. Decryption is pure Python
   (`tools/aes_decrypt.py`, FIPS-197 and SP 800-38A vectors) because the stock interpreter has no
   crypto module.
5. **Names** are Jenkins one-at-a-time hashes of lower-cased names; none are stored. Names are
   recovered from 448,917 printable strings harvested from the executable image and the cache
   archive's loose members, offered as-is, with a known extension, and (for strings such as
   `mr_vp_nsn_gtr_08`) as an embedded car code. A candidate must agree with its entry: directories take
   no dotted name, resources take a resource extension, loose files do not. An entry is named only when
   exactly one plausible candidate remains. The first run, without those rules, named directories and
   files with binary noise such as `-tm2.xlm`, `w3hu.dds` and `anaj.xbtm`; with them, 7,426 of 23,931
   cache entries are named; 8 hashes have more than one raw candidate and 3 cache entries keep several plausible ones. A remaining collision is possible and
   stays a claim limit.

## Car files

`xarchive_cache.rpf` (2,130,739,200 bytes, 23,931 entries) holds all car data under
`resources/vehicle/<code>/`: 49 `vp_`, 16 `vpd_` and 41 `va_` directories plus `configs/`. One
directory hashes to no harvested string directly; the embedded-code rule names it `vp_nsn_gtr_08`
from the garage texture `mr_vp_nsn_gtr_08` (the same hash appears in an external CodeX name list,
which the tool does not use). The prefix readings (player, downloadable-content player, ambient
traffic) are interpretations.

| Resource type | Files in car packages | Resolved extension | Reading (CodeX type table) |
| ---: | ---: | --- | --- |
| 63 | 8,849 | `.xrsc` (only `body_lod_0.xrsc` resolves by name) | model resource parts |
| 83 | 212 | `.xtp`, `.xtl` | part and damage textures |
| 50 | 106 | `.xct` | car tuning |
| 19 | 106 | `.xspm` | streaming pack map |

Selection (`tools/extract_mcla_cars.py`) is a declared namespace boundary: a car takes its vehicle
directory, its `resources/ambients/<code>/` directory, and the configs and garage UI textures whose
file name contains its full code as an underscore-delimited run (the longest code wins, so
`sh_vp_lam_murcielago_06_dub` goes to the `_dub` car). Rims, tires, brakes, `vehicle/` effects,
`tune/vehicle/` and configs naming no code go to `shared/`. The other three archives (audio, low audio,
music) and the preload copy `preload/xarchive_carconfigs.rpf` (a nested RPF3 duplicating the configs)
are inventoried, not extracted. Result: 106 cars, 10,702 output files, 415,232,242 bytes; 94.3% of the
9,273 car-package files keep `0x<hash>` names.

RSC5 resources are written exactly as stored (their LZX-compressed body included); DEFLATE members
are written inflated, with the stored SHA-256 kept in each manifest.

## Verification

| Command | Result |
| --- | --- |
| `python3 tools/extract_mcla_cars.py` | `EXTRACTED 106 cars, 10702 files, 415232242 bytes` (35 s) |
| `python3 tools/extract_mcla_cars.py --check` | `CHECKED 106 cars, 10702 files, 415232242 bytes`, also under stock Python 3.9.6 |
| `test_aes_decrypt`, `test_xdvdfs`, `test_xex2`, `test_mcla_rpf`, `test_extract_mcla_cars` | synthetic encrypted disc, XEX and archive with tamper controls: wrong key, unreachable or doubly-parented entries, bad DEFLATE sizes, missing RSC5 header, overlapping extents, XGD2 offset, multi-sector directories, colliding and ambiguous names, missing disc members, unexpected vehicle directory, a disc changed mid-run, rewritten index masking a payload change, extra and linked output |

| `line_coverage` | 100% of executable lines in the four readers and the extractor under their tests |

`mcla_extraction` in `tools/check.sh` runs the full re-derivation only where the ISO is present. The Jev review of this change and the fixes it prompted are in [jev-review-escalations-2026-10-12.md](jev-review-escalations-2026-10-12.md).

## Not established

- RSC5/LZX decoding: no model, texture, tuning or streaming-map content is read, so part names inside
  `.xspm` maps, geometry, materials and wheel placement are unknown. No GLB conversion; the cars are not
  in either catalog yet.
- Ownership of shared rims, tires and brakes, runtime dependency closure and load precedence.
- Meaning of the RPF3 header's unknown word and of the per-directory flag words.
- Anything about the PS3 release or other builds; only this Xbox 360 disc was read.
