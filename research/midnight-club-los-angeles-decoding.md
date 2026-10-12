# Midnight Club: Los Angeles resource decoding and part names

Date: 2026-10-12. Scope: decompress the RSC5 resources of the MCLA disc, decode the car models,
textures, tuning and streaming pack maps, and recover the car part names. Extraction itself is
covered by [midnight-club-los-angeles-extraction.md](midnight-club-los-angeles-extraction.md).
Receipts: [`resources.json`](evidence/midnight-club-los-angeles/resources.json) (every resource on
the disc) and [`decoding.json`](evidence/midnight-club-los-angeles/decoding.json) (every car file).

## Sources

All decoders are independently written in stock Python. The two community sources declare no licence,
so they were read as format references only; no code was copied.

| Source | Commit | Used for |
| --- | --- | --- |
| [Foxxyyy/CodeX.Games.MCLA](https://github.com/Foxxyyy/CodeX.Games.MCLA) `RSC5/Rsc5Data.cs`, `Rsc5ModelResource.cs`, `Rsc5Drawable.cs`, `Rsc5Texture.cs`, `RPF3/Rpf3Crypto.cs`, `Files/Xtl*`/`Xtd*`/`Xrsc*`/`XctFile.cs`, `Rsc5City.cs` | `dedc3156` | Pointer segments, model/geometry/vertex-buffer/skeleton/texture/shader layouts. Its `.xct` reader is for city data and does not fit car tuning; its LZX is a native XCompress binding |
| [Raskulk/MCLA-Tools](https://github.com/Raskulk/MCLA-Tools) `xrsc2obj.py` | `68419cee` | The console LZX chunk framing (a lead; its own LZX is self-described as untested) |
| Microsoft LZX (cabinet) format | — | Bitstream: 16-bit little-endian words, block types, pretree delta coding, repeated offsets, aligned offsets |

The 11 CodeX files fetched for this work were screened with `jev_screen` in 17 chunks before reading
(injection ≤ 0.03, all `pass`); digests of the screened text are in [`source-screens.json`](evidence/midnight-club-los-angeles/source-screens.json).
The Xenos 2D tiled address function and DXT block decoding are written from their published
descriptions; the untiler is tested to be a permutation of the padded surface.

## LZX (`tools/mcla_lzx.py`)

An RSC5 resource is a 20-byte big-endian header (`\x05CSR`, a type word whose low byte is the archive
resource type, the flag word, the constant `0x0FF512EF`, the body length) and a run of chunks:
`0xFF` + output size + input size, or a 2-byte input size for a full 0x8000-byte chunk. Each chunk starts
a fresh bit reader; the decoder state (window, trees, repeated offsets and a block in progress) carries
over. The window is 2^17. A compressed chunk must be consumed to its last 16-bit word. A stored block
of odd length is padded to a word except where the padding would be the chunk's last byte (one resource
on the disc ends that way). Intel E8 translation is rejected; no resource sets it.

Over the whole disc, 15,480 resources (14,928 in the cache archive, 276 in each audio archive, none in
the music archive or the four nested preload archives) decompress to exactly the virtual plus physical
size of their flag word: 6,237,589,504 bytes in 197,691 chunks. Every RSC5 header repeats its archive
flag and resource type. A full run takes about 3.5 minutes on 10 processes.

## Part names

Streaming pack maps (`.xspm`, type 19) are lists of part variants per slot: string fields (pointer,
length, capacity) naming model files (`hood0_lod_0`) and part bones (`hd00_stk`). The extractor now reads
every string field of the 106 maps (622 distinct strings) and offers levels 0–3 of every `_lod_<n>` name
(a RAGE drawable has four levels of detail). Candidates are offered with the existing plausibility rules
and each name is accepted only when its Jenkins hash equals the entry's.

| Name origin | Cache entries | All four archives |
| --- | ---: | ---: |
| disc string (executable and loose members, as before) | 7,426 | 9,918 |
| streaming-map string field | 4,433 | 4,685 |
| level variant of a `_lod_<n>` name | 4,310 | 4,520 |

All 9,273 files inside car packages are now named (5.7% before); no previously resolved name changed.
Printable text inside a map that no string field references is not a name source (tested). The audio
archives hold one more car package, `vp_se_chv_chp_96`, whose part names resolve through the same
strings; it is not extracted (open item).

## Models (`tools/mcla_model.py`)

Readings checked on all 9,044 car and shared models (8,849 in car packages):

- Root (VFT 0x0057C350; brakes 0x0056C884 with the same layout) → drawable LOD → models → geometries.
- Every geometry is a triangle list whose primitive count is a third of its index count; vertex and index
  buffers repeat the geometry's counts and stride; every index is inside its vertex buffer.
- One vertex component table (`0xAA1111111199A996`) on the whole disc: position float3, normal and
  tangent as signed 10-bit triples (1/511), colour as four bytes, texture coordinates as half2; the
  channel sizes always add up to the declared vertex size.
- Every vertex lies inside its geometry's bounding sphere (centre, radius) wherever one is stored.
- Skeletons: 224-byte bones with parent pointers that precede their children, an identity quaternion,
  and a stored model-space offset equal to the parent chain except below bones that carry an Euler
  rotation (window and gauge pivots in 17 resources).
- Join: every geometry's shader index lies inside its car's `.xtp` shader group, and some car uses the
  last shader. This is the reading of shader binding.

Totals: 49,328 geometries, 18,822,108 vertices and 20,525,809 triangles.

## Textures (`tools/mcla_texture.py`)

`.xtd` dictionaries (312 garage images) and `.xtp`/`.xtl` packs (212 car packs, 195 rim, tire and brake
packs): textures carry a name and a Xenos fetch constant. Only DXT1, DXT5 and ARGB8888 occur on car files,
all tiled, with DXT using the 8-in-16 and ARGB the 8-in-32 endian swap; the fetch-constant size always
equals the texture header. A base level whose shorter side is at most 16 texels is stored 16 texels into
the packed-mip tile (without this rule the 16×16 colour swatches decode as stripes). `.xtl` packs repeat
the `.xtp` shader list with half-size textures. All 6,180 textures decode (258 million texels); the GT-R's
decoded set shows legible "NISSAN" and "GT-R" badges, gauges and a California "MDNTCLB" plate.

## Tuning (`tools/mcla_tuning.py`)

No reference fits car tuning, so the layout was read from the data. Every car's `.xct` has seventeen
sections in one slot order: vehStuck, vehInput (base, mods), vehDamage, vehModel, vehCamShake, vehSim
(base, mods), vehGyro (base, mods), vehAbility (base, mods), two headerless float blocks, vehZone,
vehGrip, and one unnamed object. Each named section points to its owner (`<code>`, `<code>_base`,
`<code>_mods`), class and `$/tune/vehicle/` folder; the class names and the `%s_base`/`%s_mods` patterns
are in the executable. Section sizes agree across all 106 cars. Field names are not on the disc, so
fields are typed words by offset; the receipt records the type counts per slot.

## Verification

| Command | Result |
| --- | --- |
| `python3 tools/verify_mcla_resources.py` | 15,480 resources, 6,237,589,504 bytes; 7 controls rejected (truncated stream, flipped block-type bit, size 4 KiB short and long, windows 2^16 and 2^18, a flipped body bit) |
| `python3 tools/verify_mcla_decoding.py` | 106 cars: models, textures (RGBA digests), tuning and streaming maps decoded; joins hold; 13 controls rejected (index out of range, vertex outside its sphere, format size, primitive type, model/texture/tuning VFTs, fetch-constant size, format code, tiled flag, wrong tuning class and folder, row-major untiling) |
| `python3 tools/extract_mcla_cars.py --check` | `CHECKED 106 cars, 10702 files, 416762997 bytes` |
| `test_mcla_lzx`, `test_mcla_resource`, `test_mcla_model`, `test_mcla_texture`, `test_mcla_tuning`, `test_verify_mcla_*` | Synthetic streams (a test-only LZX encoder covers verbatim, aligned and stored blocks, run codes, repeated offsets, multi-chunk state) and synthetic resources with one mutation per structural rule |
| `line_coverage` | every MCLA reader and both verifiers at ≥ 99% of executable lines |

## Not established

- Tuning field meanings and names; the meaning of slot 16 and of the two float blocks.
- Part placement and assembly into a whole car (which part of each slot is stock, which body bone a
  part attaches to); previews are a separate change.
- Mip levels other than 0; shader parameters other than textures are recorded only by name hash.
- Render fidelity: nothing here is compared with the running game.
- The audio-archive car `vp_se_chv_chp_96` and the non-car resources (city, characters, audio) are
  decompressed but not decoded.
