# Midnight Club: Los Angeles static previews

`tools/mcla_preview.py` builds a GLB from the independently decoded extraction, without changing
native resources. `build_car(extraction, vehicle, index=None)` returns bytes and an assembly record.
The profile is `mcla-xbox360-static-stock-v1`. Every consumed file is checked against the extraction
index's size and SHA-256 before decoding; the GLB records source archive entries, hashes, chosen parts,
attachment names, node translations and scales, omissions, and claim limits.

## Assembly readings

The native frame is Y up, facing −Z, with +X right. This is a reading of front/rear bumper and axle
positions: the GT-R's `bumf` has z ≈ −1.9913, `bumr` z ≈ +1.9757, and its front `axl_0/1` have
z ≈ −1.4348. No global rotation is applied.

The preview includes `body_lod_0.xrsc` and variant zero of ordinary slots (`hood0_lod_0.xrsc`, etc.).
Widebody alternatives (`widebody`, `hood_wide`, `door_*_wide`, `spoiler_wide`, `trunk_wide`) are omitted:
these contain alternative surfaces and including all of them causes overlaps. Occluders are omitted.
A rigid raised convertible roof is preferred over its lowered alternative; deforming `conv_top`
resources are omitted. These choices do not decode or execute an XCC configuration, so “stock” means
the explicitly selected variant-zero preview convention, not a proven factory configuration.

A part's first skeleton bone is matched exactly to the body skeleton when possible. Otherwise an
explicit slot table supplies the attachment: hood→`hd`/`hood`/`hoods`; front bumper→`bumf`/
`f_bumpers`/`bmpf_bone`; rear bumper→`bumr`/`r_bumpers`/`bumr_bone`; spoiler→`splr` and older aliases;
doors and interior door panels→the regular door hinge, not the origin-valued door category bone.
Seats and steering wheels have corresponding older-name aliases. Suspension arms use their axle
center; whole-car interior, fenders and sub-bumpers use the root. The exporter copies stored
model-space translations. It does not reproduce animated pose, skeleton rotation or skin deformation.
An unknown selected attachment raises rather than silently placing a part at the origin.

Exhaust pipe instances use the primary/secondary exhaust anchors of the selected rear bumper,
translated by that bumper's body attachment. When the bumper or its anchors are absent, exhaust
pipes are omitted and recorded. This avoids using anchors from an unselected bumper variant.

## Wheels and material approximations

Player wheels use exact `whl_stk_<vehicle suffix>` names, DLC wheels `whld_stk_<suffix>`. A hashed
folder is accepted only when it equals the Jenkins hash of that complete expected name: the GT-R's
`0xab0115fa` equals `jenkins('whl_stk_nsn_gtr_08')`. The Mercedes S600 source name lacks `_07`.
DUB variants use the corresponding base stock rim by a declared preview convention. Ambient models
and `vp_citybus_07` retain embedded wheel geometry; no unrelated rim is substituted.

Shared tire models have radial radius 0.5. Wheel centers come from body `axl_0..3`, or motorcycle
`axl_front`/`axl_rear`. Wheel sizing remains a design approximation: tire radius equals axle height
above y=0, rim radius uses the measured source tire bead/outer-radius ratio, brake radius 0.55, and full car wheel width is 0.65 of
tire radius (motorcycle width 0.35). The car tire has inner radial extent ≈0.406 and outer ≈0.5 (ratio ≈0.812), so the rim meets the source tire bead. Radial scale is twice the chosen radius; X scale is twice the chosen width because shared car tire width is 0.5. Left wheels receive a
180° Y rotation. Player vehicles require exactly the four car axle names or the two motorcycle axle names: absent, partial, mixed and extra axle sets fail. Ambient vehicles and the player bus keep their embedded-wheel exception. Matching named stock brakes are included; unidentified brake packs are omitted.
The per-wheel scales and sources are retained in the assembly record. None of these ratios is a
decoded tire specification or a claim about the game’s runtime wheel matrix.

The source half-resolution XTL pack is preferred; XTP is used when no XTL exists. Geometry shader
indices select that pack's shader group. Base-colour textures use `diffusesampler` (0xF1FE2B71).
The RGB of parameter 0x1468B111 is read as diffuse colour when finite and in range; its fourth lane
can be NaN padding and is not used. Default colour is neutral grey. Source normals and first UVs
are retained; absent normals are calculated. Materials are opaque, with source texture alpha forced
to 255, because source alpha can encode shader effects. Vertex colour, glass blending, reflection,
normal maps, damage, lamps and runtime paint are not reproduced. Tires use neutral rubber rather
than a guessed shared texture ownership join. Identical source meshes are instanced at wheel/exhaust
placements, preserving triangle counts while reducing storage.

## Verification and limits

`python3 tools/test_mcla_preview.py` exercises synthetic native RSC5 models and texture packs through
the real decompressor and decoders, verifies stock selection, hinge translations, normalized wheel
placement and orientation, mesh reuse, deterministic GLB bytes, and source provenance. Controls reject
changed source bytes, duplicate extraction rows, unsafe paths and symlink escape, absent stock rims,
ambiguous packs, invalid axle height, out-of-range shaders/indices, empty triangles and selected
skinned models. Additional controls check exhaust omission, rigid roof selection, hashed rim lookup,
motorcycles, ambient wheel preservation and normal/material fallbacks.

A local all-extraction experiment built 106/106 source vehicles successfully. The scratch summary
`.scratch/mcla/assembly-probe.json` records each vehicle's bytes, triangles, parts and wheels; the
aggregate visible triangle count before dealership baking was 6,851,647. GLB byte totals change with provenance metadata and are reported by the catalog verifier. This
checks parser joins and bounded assembly completeness. It does not establish visual equivalence,
prove the factory configuration or validate every alias against gameplay. A successful render and
valid GLB alone would not establish those stronger claims either.

Jev screened the live TypeSafe Choice and citation-check documentation before use (injection 0.11,
pass). Noul assigned 0.85 to treating axle-height tire scaling as a transparent approximation and
0.86 to avoiding simultaneous stock/widebody surfaces. A classification experiment separated source
fields, assembly readings and preview choices; material simplification classified automatically at
1.00. Attachment wording (0.83), axle-center wording (0.84) and radius wording (0.58) required review;
these are retained as signals, not automatic proof. No unchanged judgment was retried for a preferred
answer. Deterministic hash/name/geometry calculations stay in ordinary code. Final review and test
claims require a Jev gate with the actual final diff and executed logs.

Open evidence gaps: XCC configuration semantics and runtime stock selection; wheel/tire size fields,
brand texture selection and full brake ownership; rotational part transforms; gameplay verification
of every attachment alias; faithful glass/paint/reflection shaders. Native asset bytes and extraction
records remain available independently of these preview approximations.
