# Midnight Club: Los Angeles static previews

`tools/mcla_preview.py` builds a GLB from the independently decoded extraction, without changing
native resources. `build_car(extraction, vehicle, index=None)` returns bytes and an assembly record.
The profile is `mcla-xbox360-static-stock-v2`. Every consumed file is checked against the extraction
index's size and SHA-256 before decoding; the GLB records source archive entries, hashes, chosen parts,
attachment names, native model/bone indices, composed affine node matrices, omissions, and claim limits.

## Assembly readings

The native frame is Y up, facing −Z, with +X right. This is a reading of front/rear bumper and axle
positions: the GT-R's `bumf` has z ≈ −1.9913, `bumr` z ≈ +1.9757, and its front `axl_0/1` have
z ≈ −1.4348. No global rotation is applied.

The preview includes `body_lod_0.xrsc` and variant zero of ordinary slots (`hood0_lod_0.xrsc`, etc.).
Widebody alternatives are excluded when regular exterior slots exist. Four DUB packages instead lack their regular variant-zero exterior family: `widebody0` and available `*_wide0` parts supply their outer shell. Those parts are selected only for this absence pattern, preserving the regular/wide mutual exclusion. Occluders and deforming `conv_top` resources are omitted; a rigid raised convertible roof is preferred over its lowered alternative. These choices do not execute an XCC configuration, so “stock” remains the explicit static variant-zero convention.

Each native drawable LOD contains parallel model-pointer and bone-index arrays. The decoder validates matching counts, capacities, source segment bounds and bone indices. The exporter retains one mesh/node per native model, and combines the body attachment pose with that model's bound bone pose. This restores embedded ambient wheels, trunk/window panels and internal part mechanisms that previously lost their individual placement.

Resource root `+0x30` points to native cached transforms: count/capacity and inline little-endian 3×4 matrices at block `+0x20`, 48 bytes per bone. The decoder verifies finite, orthogonal proper-rotation bases and retains the raw cache separately from draw poses. Independent native calibration tested all six canonical Euler orders on 1,491 selected part resources / 7,453 bones. Only Rz·Ry·Rx reproduced every cached rotation as global Euler orientation times inverse global joint orientation, with maximum error 1.33e-7. A parent-cache times local-delta hypothesis failed six XLR-V descendants, reaching error 1.99. Joint orientation therefore accumulates through the entire ancestor chain: `Bind[i] = Bind[parent] × Orient[i]`, and draw orientation is `Cache[i].R × Bind[i]`. Restoring only the bone's local orientation left XLR-V linkages floating. Draw translation is cached bone translation minus cached root translation plus authored resource-root translation; it agrees with independently composed global Euler/local translations within 1.36e-7. This retains authored root placement while correctly composing rotated descendants; substituting every bone's authored offset left the S7 windows raised. Rotated resources without a cache remain rejected. This is source algebra and controlled static-render evidence, rather than observation of the game's runtime consumer.

Body attachment aliases remain explicit. Doors prefer the scissor leaf where it exists and retain the selected part's own compensation: this closes the Miura's low door while preserving GT-R placement. Car arms, axles, guides and shocks retain their native resource placement without an extra axle-center offset. Motorcycle front_fork resources attach to the native front_steer frame. Rigid convertible roofs prefer conv_tops/hardtops over a matching resource-root name; the XLR-V's opposing top/root frames close its panels, and cumulative body joint orientations seat its linkages and rear deck. Whole-car parts attach at the root and retain their authored offsets. Unknown selected attachments still raise.

Exhaust instances compose the selected bumper's body attachment, its native exhaust-anchor matrix, the inverse exhaust draw-root pose, and the model's bound draw pose. Replacing the template authoring frame with the anchor frame prevents the Murciélago's root rotation from turning its pipes outward a second time; relative child bindings and anchor cant remain retained. Among 48 instanced exhaust templates, only the regular Murciélago has a nonzero root rotation, and all have zero root translation. `exst0/1` and primary/secondary aliases are supported. Anchor indices are qualified by their bumper source file, avoiding collisions with duplicated body labels. Missing selected bumpers/anchors remain recorded omissions. Native anchor orientation removes the detached outward-facing GT-R pipes; source geometry and simplified materials remain subject to the visual audit and do not establish runtime rendering equivalence.

## Wheels and material approximations

Player wheels use exact `whl_stk_<vehicle suffix>` names, DLC wheels `whld_stk_<suffix>`. A hashed
folder is accepted only when it equals the Jenkins hash of that complete expected name: the GT-R's
`0xab0115fa` equals `jenkins('whl_stk_nsn_gtr_08')`. The Mercedes S600 source name lacks `_07`.
DUB variants use the corresponding base stock rim by a declared preview convention. Ambient models retain embedded wheel geometry through their native model bindings. The player `vp_citybus_07` body lacks wheel geometry and a shared stock rim. Its explicit ambient `va_citybus_07` family supplies only the eight wheel-bound models; exact authored/composed wheel-pose equality is required, and donor model/texture hashes and the limited substitution are recorded. This is a static preview family join, not proof of game runtime substitution.

Shared tire models have radial radius 0.5. Wheel centers come from body `axl_0..3`, or motorcycle
`axl_front`/`axl_rear`. Wheel sizing remains a design approximation: tire radius equals axle height
above y=0, rim radius uses the measured source tire bead/outer-radius ratio, brake radius 0.55, and full car wheel width is 0.65 of
tire radius (motorcycle width 0.35). The car tire has inner radial extent ≈0.406 and outer ≈0.5 (ratio ≈0.812), so the rim meets the source tire bead. Radial scale is twice the chosen radius; X scale is twice the chosen width because shared car tire width is 0.5. The native car rim show face points toward −X in all 56 selected car-rim resources. Right (+X) wheels receive a
180° Y rotation; centered motorcycle wheels keep their native frame. Normalized shared-wheel instances remove authored resource-root placement while retaining relative bound-bone offsets; this prevents the 240SX rim's source root Z offset from moving it outside its tire. Player vehicles require exactly the four car axle names or the two motorcycle axle names: absent, partial, mixed and extra axle sets fail. Ambient vehicles retain their own wheels; the player bus uses the guarded wheel-only family join above. Matching named stock brakes are included; unidentified brake packs are omitted.
The per-wheel scales and sources are retained in the assembly record. None of these ratios is a
decoded tire specification or a claim about the game’s runtime wheel matrix.

The source half-resolution XTL pack is preferred; XTP is used when no XTL exists. Geometry shader
indices select that pack's shader group. Base-colour textures use `diffusesampler` (0xF1FE2B71).
The RGB of parameter 0x1468B111 is read as diffuse colour when finite and in range; its fourth lane
can be NaN padding and is not used. Default colour is neutral grey. Source normals and first UVs
are retained except for the explicitly recorded S7 divider reconstruction below; absent normals are calculated. Materials are opaque, with source texture alpha forced
to 255, because source alpha can encode shader effects. Vertex colour, glass blending, reflection,
normal maps, damage, lamps and runtime paint are not reproduced. Tires use neutral rubber rather
than a guessed shared texture ownership join. Identical source meshes are instanced at wheel/exhaust
placements, preserving triangle counts while reducing storage.

The source showcase fits its camera near plane to `extent / 100` and keeps the far plane at `extent × 100`. The previous near plane at `extent / 10000` wasted depth precision: controlled 24-bit Metal captures of the unchanged CL65 GLB showed large jagged glass/trim seams, which disappeared at divisors 100 and 20 in both views. Camera positions, geometry and materials were unchanged. The dealership already uses near 0.1 / far 200 and showed a clean CL65 seam. The smaller near plane increase preserves close inspection while bounding the fitted depth range at 10,000:1. Native BlackOpaqueGlass shader artifacts contain depth/prepass names, but their numeric state and runtime execution remain unestablished; no guessed shader depth bias or material deletion was introduced.

## Authorized S7 preview geometry cleanup

The S7 resource `vp_sln_s7_06/resources/vehicle/vp_sln_s7_06/skirts0_lod_0.xrsc`
has source SHA-256 `299e37d98e80e2399bb4eb9cef1d2a051f1119526e7e2c1b5022b758c205de5c`.
Its painted model 0, geometry 1 contains two main shell components (1,633 triangles each),
four upper intake dividers (38 triangles each), and six lower dividers (32 triangles each).
Their native part-root and body attachment frames are identity; their protruding faces are
source-authored geometry, rather than a remaining dropped binding or duplicated attachment offset.
The user explicitly chose a documented cleanup of the derived previews.

`tools/mcla_preview_geometry.py` targets only that resource/model/primitive and requires both the
resource pin and a fingerprint of every decoded geometry attribute and metadata field. Other inputs
are returned unchanged. The accepted reading fits native X(Y) and Z(Y) centerlines to each divider,
contracts X/Z residuals to 10%, and insets the two sides by 10 mm. Y coordinates, all ten divider
identities, original triangle indices and attribute-seam coordinate equality stay intact. Normals use
the inverse transpose of the positive affine contraction; UVs, colour lanes, tangents, all main-shell
positions/normals, materials and node poses remain unchanged. This changes 292 vertices / 344 source
triangles without adding vertices or removing triangles. Maximum displacement is about 93.437 mm;
the divider surface areas become about 10% of their source areas. This is a significant deliberate
profile reconstruction, not a recovered game deformation or a submillimetre seam repair.

Finite clipping, contact-only retraction and lateral inset alternatives were retained as failed or
insufficient controls. One finite clipping candidate preserved positive triangle counts but left only
1.7–8.0% of lower-divider area; it was rejected for effectively removing their shapes. Contact-only
retraction also split original attribute-seam coordinates and left visible teeth. The accepted
reconstruction produces narrow readable divider edges in the inspected views. Strict finite contact
pair count increases from 114 to 144, while summed intersection-segment length falls from about
2.437 m to 0.438 m. Remaining blade-to-shell attachment contacts prevent any claim of zero intersections.
The GLB records the repair profile, source and geometry hashes, source triangle ranges, before/after
bounds, centerlines, areas and displacement separately in `preview_geometry_repairs`.

Ownership controls with all dividers removed isolate the broad upper gray backdrop to native
blackmatte and painted cavity surfaces in the same skirt assembly. Body/fender removal and primitive
colours disprove a separate misplaced door or interior explanation. Simplified neutral opaque
materials make the dark-named cavity appear gray; geometry is not deleted solely for that shade.
Native XRSC and ZIP bytes remain unchanged. The static previews still do not establish original
paint/shader execution, runtime damage, or hidden-face absence of defects.

## Verification and limits

`python3 tools/test_mcla_preview.py` exercises synthetic native RSC5 models and texture packs through
the real decompressor and decoders, verifies stock/wide selection, noncommuting attachment/model composition, authored root compensation, distinct model bindings, unchanged geometry attributes, normalized wheel placement, mesh reuse, deterministic GLB bytes, and source provenance. Controls reject
changed source bytes, duplicate extraction rows, unsafe paths and symlink escape, absent stock rims,
ambiguous packs, invalid axle height, out-of-range shaders/indices, empty triangles and selected
skinned models. Additional controls check exhaust omission, rigid roof selection, hashed rim lookup,
motorcycles, ambient wheel preservation and normal/material fallbacks.

The original profile-v1 all-extraction experiment built 106/106 source vehicles successfully. The scratch summary
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
brand texture selection and full brake ownership; runtime animation and skinning transforms; gameplay verification
of every attachment alias; faithful glass/paint/reflection shaders. Native asset bytes and extraction
records remain available independently of these preview approximations.

## Native assembly correction and browser regression

The earlier translation-only profile dropped the LOD binding array and part orientation. Native resource probes and independent source-byte checks established those omissions. A 1,474-resource / 7,404-bone check reproduced bindings and native joint bases. Subsequent controlled contrasts established the missing mesh preorientation and composed descendant placement described above. Controlled local probes restored ambient wheels, Miura doors/arms, Cobalt hood and RX7 trunk placement, DUB outer shells and player-bus wheels; later probes covered S7 doors/windows, Focus/RS4/S5/Evo X trunks, motorcycle forks/steering, shared rim facing and rebasing, exhaust root frames and Gallardo scissor leaves. Trunk-mounted lamps inherit the selected trunk root orientation before their own source compensation. Front-fork resources attach to the native front_steer frame; other mechanical parts retain their authored resource placement. Scissor aliases include names without _anim, and duplicate labels resolve through native left/right door ancestry, retaining original bone names and indices. These observations motivate profile v2; they are bounded static-render evidence rather than execution of the original game.

Use `python3 tools/import_mcla_catalog.py --refresh` for an intentional source-profile upgrade. The importer validates the old edition's exact GLB/ZIP pins, identities, coverage and known profile before staging a complete replacement; failures restore the old directory. Native package bytes remain preserved. Then run `python3 tools/import_mcla_dealership.py --upgrade-unedited`, `python3 tools/build_model_catalog.py`, and `python3 tools/build_dealership.py`. Edited dealership models and custom metadata are preserved.

The browser regression uses Jev Browser for every MCLA source and dealership model, retaining independent selected-ID/load/download/hash checks and inspected orbital screenshots. Text-based Jev screening, auditing and classification cross-check visual captions, not pixels; uncertain cases retain review status. Final coverage and remaining limitations are recorded with the actual check receipts rather than inferred from successful loads.
