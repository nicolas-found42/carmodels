# Gran Turismo native model data

GT1 canonical exports enrich the existing 342 day-derived families with verified
native names, base specifications and every CTEX colour set. Exact SPEC-code joins
cover 178 families. The remaining 164 retain source-code names and null
specifications: 159 have an unproved racing-suffix correspondence, and five other
codes have no direct SPEC record. An arcade byte alias does not establish retail
identity. Model year, manufacturer, body style, top speed and ratings stay unknown.

## Native metadata sources

`tools/gt_metadata.py` checks the pinned CARINF SPEC section 13, COLOR section 38,
and SYSTEM.DAT before decoding. SPEC has 178 records of 424 bytes; COLOR has 142
records of 84 bytes. SYSTEM's 344 six-byte native codes corroborate the existing
external archive map in ordinal order. The archive selection still records that
external-map dependency rather than promoting an unexamined loader expression.

GTMENU `80012a58`/`80012b18` consume SPEC code/index; `8001f450` resolves native
model and grade string references; `8001eb08` displays dimensions, mass, power,
torque, engine and suspension fields. `80016010` consumes the drive enum.
`80031630` initializes the effective specification from its base record; later
equipment can modify it, so source base values are never assigned to an unmatched
racing family. The exported power retains both its raw scalar and the game's
integer `raw * 1000 / 1014` HP conversion. Rotary displacement retains native
chamber/factor fields rather than reporting the chamber scalar as total cc.

The compact [native lookup receipt](evidence/gran-turismo-metadata/native-lookups.json)
retains lookup bytes and source identities for enum labels, model/grade names,
colour slots and the rotary special table. Original decompilation and captured RAM
remain local inputs. Routine decoding reads the committed native metadata and
receipt, without requiring the local Ghidra projects or captures.

GTMENU `80032198` joins colour names using a one-based SPEC reference and palette
ID OR 0x20; `80016c44` consumes the result. The 142 directly linked canonical
families have 877 palette sets, of which 876 IDs have a matching name. Names cannot
be zipped by position: ten records differ from CTEX order, including a duplicate
identifier and one missing name. Unmatched names stay null, with the set index and
native identifier retained. Other families still expose every native colour set
with an identifier label.

## Retained rendering inputs

Every GLB embeds the complete original CAR and CTEX payloads with hashes and
buffer-view references. Structured `extras.nativeData` locates raw palette words,
indexed texels and both CTEX masks; original positions/normals, native bounds and
LOD descriptors; shadow vertices; and all five wheel templates. Primitive
`extras.nativeFaces` joins each source packet to its output vertices and triangles,
retaining command/type, packed flags, raw CLUT, source corner indices and recorded
normal/winding repairs. Wheel nodes retain neutral attachment pivots and dimensions
while their visible coordinates remain unchanged.

`KHR_materials_variants` maps every source colour set, including set 0, onto body
and wheel materials. Both source and editable viewers can select the palettes.
Default geometry, repaired normals and neutral wheel assembly remain the existing
static display policy. Native shadow records are preserved outside visible scenes.

The newer MAIN renderer shows why raw data matters: `80072528` can emit an
additional normal-derived textured packet for flagged faces; `8006cb7c` supplies
the associated state. `800222e0`/`80022438` identify a scene-dependent palette
rewrite path using the first CTEX mask table. These are static analysis leads for
future renderer work, not rendered-equivalence claims. The second table's precise
paint meaning remains unestablished. Camera/GTE-dependent LOD thresholds are
preserved as native values rather than labelled as metre distances. Unsupported
nonzero seventh/eighth body polygon groups fail explicitly; both counts are zero
throughout the retained corpus.

## Upgrades and checks

`extract_gt_cars.py --refresh-metadata` rederives existing native bytes before
upgrading manifests and adding SYSTEM.DAT. Unexpected files, altered native bytes,
detached declarations and symlinks fail before installation. Metadata installation
rolls back on failure. Export then checks native metadata against its pinned inputs
and embeds the same metadata in its source index and GLBs.

The dealership importer verifies catalog/embedded metadata agreement and source
code ownership. `--upgrade-unedited` replaces only models equal to their recorded
source; it updates generated metadata defaults and preserves custom names, values,
notes and edited geometry. Source metadata history remains separate from owner
overrides. Colour availability follows the loaded working GLB.

`test_gt_metadata.py` checks native joins, provenance and malformed/detached values.
`test_gt_native_data.py` independently checks complete payloads, decoded palette
pixels, face ownership, shadow records, LOD descriptors, wheel templates and pivots.
Importer tests cover custom-field preservation, edited geometry, repeat upgrades
and false identity/name controls. `tools/check.sh --game gran-turismo --full`
includes these checks and rederives the entire canonical export and extraction.
These checks establish retained data and static conversion behavior; original-game
shading, transparency, shadows, tuning, animation and timing equivalence remain open.
