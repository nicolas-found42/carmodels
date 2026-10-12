# Midnight Club: Los Angeles — native car files

Extracted from the supplied Xbox 360 disc image, Complete Edition (USA, Europe). The original
`.7z` and the ISO unpacked from it remain under `game-files/` and are never committed or edited:

| File | Bytes | SHA-256 |
| --- | ---: | --- |
| `Midnight Club - Los Angeles - Complete Edition (USA, Europe).7z` | 6,612,480,974 | `cadd0f7b71bc888435793fd9d2fde68d1667a01d6f146592846b5487317986e8` |
| `Midnight Club - Los Angeles - Complete Edition (USA, Europe).iso` | 7,838,695,424 | `877a9415f695d27f8170d04d3f18aab13e2b4de3cbabda824e04c9338b2914e9` |

The ISO's SHA-1 (`4ca07fcf…b263`) equals the Redump value on the archive's own `Vimm's Lair.txt`.
The image was unpacked with `bsdtar -xf <archive>` (libarchive, stock on macOS).

Car data sits in the disc's `xarchive_cache.rpf`, an RPF3 archive with an AES-encrypted table and
hashed names. The repo-owned readers decrypt `default.xex`, locate the archive key in it by its
SHA-256 pin (the key itself is never written out), decrypt the table and recover names from strings
found on the same disc.

`cars/` holds **106 cars** (one per directory under `resources/vehicle/`) and **10,702 files**
totaling **416,762,997 bytes**. Only `index.json` (every file's SHA-256) and `provenance/` are
committed; the rest is local and re-derived from the disc (see `.gitignore`):

```text
cars/
  index.json                         disc identity, archive summary, name statistics, every file hash
  <code>/manifest.json               per-file archive path, name hash and source, offsets, stored SHA-256, role
  <code>/resources/vehicle/<code>/   the car's package: RSC5 model parts, tuning (.xct), streaming map (.xspm),
                                     part/damage textures (.xtp/.xtl)
  <code>/resources/vehicle/configs/  car configurations whose name contains the code (.xcc)
  <code>/resources/ambients/<code>/  ambient-traffic definition (va_ cars)
  <code>/resources/ui/textures/garage/...  garage, showroom and reward textures naming the code
  shared/resources/{rims,tires,brakes}/    wheels, tires and brakes; owners not inferred
  shared/vehicle/, shared/tune/vehicle/    shared vehicle effects and vehicle tuning
  shared/resources/vehicle/configs/        configurations naming no car code
  provenance/disc.inventory.json           complete XDVDFS listing
  provenance/<archive>.rpf.inventory.json  every decrypted RPF3 table with recovered names
  provenance/archive-key.json              key SHA-256 and its location in the executable image
```

Car IDs are directory names: 49 `vp_`, 16 `vpd_` and 41 `va_`. Reading the prefixes as player,
downloadable-content player and ambient traffic is an interpretation; IDs are not decoded retail names. The disc carries the code `vp_nsn_gtr_08`
only inside the garage texture name `mr_vp_nsn_gtr_08` (other strings spell it `vpd_nsn_gtr_08`).
All 9,273 files inside car packages are named: most part names come from the string fields of each
car's LZX-decompressed streaming pack map (`.xspm`) and from level variants of `_lod_<n>` names, and
every manifest row records its `name_origin`. Elsewhere, entries no candidate hashes to keep `0x<hash>`
names; resource-type extensions are borrowed only where every resolved name of that type agrees.

From the repository root:

```sh
python3 tools/extract_mcla_cars.py --check
python3 tools/verify_mcla_resources.py   # every RSC5 resource of the disc decompresses to its declared size
python3 tools/verify_mcla_decoding.py    # every car model, texture, tuning file and streaming map decodes
```

The readers are `tools/mcla_lzx.py` (Xbox 360 LZX), `tools/mcla_model.py` (geometry and skeletons),
`tools/mcla_texture.py` (Xenos untiling, DXT/ARGB to RGBA) and `tools/mcla_tuning.py` (tuning sections);
formats and readings are in [the decoding note](../research/midnight-club-los-angeles-decoding.md).

The check reads the ISO again and rejects changed, missing, extra or linked output. Initial
extraction uses the same command without `--check` (`--output` chooses another destination). The
destination must be absent, empty, or hold only the committed `index.json` and `provenance/`, as in a
fresh clone; those files must equal their newly derived bytes, and nothing is overwritten.

## Not established

RSC5 resources are stored as on the disc (LZX-compressed); the readers decode them on demand. Tuning
field names, part assembly, GLB conversion, catalog entries, runtime dependency closure, shared wheel
ownership and game-render fidelity remain open. See
[the extraction note](../research/midnight-club-los-angeles-extraction.md) for format sources,
verification and open items.
