# Similar projects: recovery, editing and presentation

Researched 2026-10-21, working solo at the user's request. This compares twelve projects against
the repo at `4bd8d756`, using author documentation and source, rather than popularity or screenshots.
GitHub references below pin the inspected commits. Other web references are dated observations.

## What we are comparing

Our strongest combined offering is a ready-to-browse car collection, editable downloads and recovery
evidence in one repository. The dealership catalog contains 1,435 entries across six games. Visitors
can inspect recovered originals separately from working GLBs, choose supported native paints, and
download models without first installing the games or a desktop extraction tool. Working models
have their own catalog and origin history; rebuilding the dealership preserves edits.
Sources: [project overview](../README.md), [editing contract](../dealership/dealership/README.md),
[working catalog](../dealership/dealership/catalog.json), [verification contract](../CONTRIBUTING.md).

We already have useful inspection foundations: the source viewer selects geometry scenes/records
and displays conversion limits, and car/game selection is encoded in the URL. The proposed gains
below extend those features toward connected part semantics and complete camera/appearance states;
they are not claims that we lack record inspection or car links.
Sources: [source viewer](../dealership/recovered.html), [selection URL handling](../dealership/dealership.mjs).

That is different from complete game-format editing or original-game rendering. Our native recovery
work is substantial, but runtime part selection, wheel behavior, shaders and animation still have
game-specific gaps. The MC3 research includes narrowly bounded native raster comparisons; it does
not establish complete gameplay rendering. Enhanced presentation and GT4 mesh refinement are
explicitly derived treatments, with limits. Sources: [open items](README.md#open-items),
[MC3 raster precision](midnight-club-3-remix-raster-precision.md),
[GT4 refinement contract](../dealership/dealership/README.md#enhanced-gran-turismo-4-edition).

“Better” and “worse” below mean suitability for a named task. Feature statements are documented
capabilities; the comparisons and explanations are my assessment. These are selective examples,
not exhaustive feature inventories. I did not install the competing applications or run identical
cars through them. Consequently, this study does not rank pixel accuracy, speed, stability or
export correctness. A missing feature in a README is not proof that the feature does not exist.

## Twelve comparisons

### 1. noclip.website — the closest presentation reference

**What it does:** Presents recovered game scenes in a browser. Its controls include camera
savestates and time freeze/advance. Its Need for Speed: Most Wanted scene loader loads Rockport City
from track and global resource files. Sources: [README and controls](https://github.com/magcius/noclip.website/blob/e47a8cc8a9fe16e83adc0bf19153ff04c666ceca/README.md),
[NFS scene loader](https://github.com/magcius/noclip.website/blob/e47a8cc8a9fe16e83adc0bf19153ff04c666ceca/src/NeedForSpeedMostWanted/scenes.ts).

**Better than us:** Exploring a recovered environment as a place, and returning to an interesting
camera/time state. Our dealership centers isolated cars. The difference follows from noclip's scene
loaders and navigation/state controls, rather than a claim that its materials are universally better.

**Worse for our use case:** A scene and its savestate are a less direct organizing unit for finding,
editing and downloading one car than our per-car catalog and GLB workflow. This is a workflow
comparison, not a claim that noclip cannot export anything.

**Borrow:** Shareable inspection states that bind car, camera, paint and presentation mode.

### 2. GTPS2ModelTool — native Gran Turismo authoring

**What it does:** Creates custom GT3 models. Author documentation also describes OBJ/PNG dumping,
including CAR4 input, while warning that dumped models are unsuitable for direct re-import. The
README warns that original-model rebuilding is constrained by texture-memory packing and that GT4
support needs substantial work. Sources: [pinned README](https://github.com/Nenkai/GTPS2ModelTool/blob/9595892f0480fc51052717a3519945ad5017fd53/README.md),
[author's model guide](https://nenkai.github.io/gt-modding-hub/ps2/models/).

**Better than us:** Building a custom model for the original GT3 engine. Its compiler and game
resource constraints address a goal our GLB export and Blender regression do not establish.

**Worse for our use case:** More assembly and format knowledge before a visitor gets a usable car;
the documented rebuilding limits also make it inappropriate to describe as a complete GT4 roundtrip.
Our already-assembled GT4 catalog is the more direct browsing deliverable.

**Borrow:** Explicit budgets and game-format validation if we ever offer native re-import.

### 3. PDTools — reusable Gran Turismo infrastructure

**What it does:** Provides libraries for Gran Turismo formats, compression, crypto, SpecDB
reading/writing and other game systems. Source: [pinned library index](https://github.com/Nenkai/PDTools/blob/2a9637d8c36100e4c211d73cd8140a9d690578d2/README.md).

**Better than us:** A developer looking for reusable Gran Turismo building blocks gets a broader,
explicit library surface. Our tools are organized around recovering and checking our own corpus.

**Worse for our use case:** Libraries leave the end-user application and assembled model collection
to the integrator. Our dealership supplies those outputs directly.

**Why this comparison needs attribution:** Our GT4 implementation already cites PDTools for PS2
model/texture layouts and SpecDB. Its contribution is upstream research, not independent evidence
that we solved the same formats unaided. Source: [our GT4 format references](gran-turismo-4-previews.md#sources).

**Borrow:** Publish stable parser interfaces and small format fixtures when reuse becomes a goal.

### 4. OpenNFS — recovered cars in an engine

**What it does:** Loads classic Need for Speed assets into a new engine, with Bullet vehicle
physics and dynamic lighting/shadows. The README separates current loaders from planned gameplay,
records uneven loader support, and requires users to supply original game files.
Source: [pinned README](https://github.com/OpenNFS/OpenNFS/blob/dcd9197033272f8be307a839105e74185809f9f9/README.md).

**Better than us:** Studying cars with tracks, vehicle dynamics and an engine around them. Our
showroom cannot establish how a recovered car behaves in motion or gameplay context.

**Worse for our use case:** Supplying game files and running an engine is more work than opening
our published collection. Its listed loader gaps also mean its scope should not be mistaken for
complete reproduction of every classic NFS game.

**Borrow:** A small car-on-track inspection scene could answer assembly questions before attempting
a full playable engine.

### 5. CodeWalker — inspect the asset in its world

**What it does:** Explores GTA V RPF archives, renders the world and supports entity/map editing.
Its selection panels expose entity, archetype and drawable details; its documented requirements
include PC GTA V, Windows and DirectX. Source: [pinned usage and format guide](https://github.com/dexyfex/CodeWalker/blob/485d56bec00262ed7fa472261cce7bbc6202b96e/README.md).

**Better than us:** Following the relationship between an object, its placement and the surrounding
world. Selectable entities and structured detail panels make the dependency/placement context
inspectable instead of presenting only the final assembled mesh.

**Worse for our use case:** The installed-game and desktop requirements add friction for casual
viewing, and GTA V specificity does not cover our six-game collection. Our MCLA decoding does not
make CodeWalker's GTA V RPF/resource support interchangeable with ours.

**Borrow:** Click a car part to reveal source identity, material, transform and assembly reason.

### 6. Sollumz — a real native-asset editing workflow

**What it does:** Imports, exports and creates GTA V assets in Blender. Documented capabilities
include vehicle creation, shader editing, bones/weights, animations, custom normals and automatic
texture loading. Source: [pinned features and requirements](https://github.com/Sollumz/Sollumz/blob/e124bddf7c0db12a61655aa98d23d0e7008b3b69/README.md).

**Better than us:** Editing game semantics inside the artist's tool: shaders, rigging and vehicle
structure, rather than only geometry in an interchange file. Our Blender check proves a bounded
GLB edit/export workflow, not native vehicle functionality.

**Worse for our use case:** A visitor must enter a Blender/GTA asset workflow instead of immediately
browsing our prebuilt car library. That specialization is an advantage for GTA modders and a poor
substitute for a cross-game public showroom.

**Borrow:** Semantic part/material controls and roundtrip fixtures before broader native editing.

### 7. ForzaTech extraction tools — expose the car's structure

**What it does:** Supplies Blender import scripts and format research for ForzaTech resources.
Documented importer examples include original mesh names, part/upgrade organization, LODs, wheel
scaling/positioning, normals and UVs. Material support is explicitly partial, with a narrow named
example. Source: [pinned importer features and setup](https://github.com/Doliman100/ForzaTech-extraction-tools/blob/d126767b4a63f4fdaa2143c4983f08a8c9974802/README.md).

**Better than us:** Making recovered structure available to an artist immediately: named parts,
upgrade groups and LODs live in Blender's outliner. We retain important native data, but retention
alone does not give the user a comparable editing interface.

**Worse for our use case:** Preparing an extracted game tree and configuring scripts/database
inputs is less accessible than our ready-made GLBs; partial material coverage also prevents a
blanket claim that it produces finished faithful cars.

**Borrow:** Preserve meaningful native names in visible, selectable part hierarchies.

### 8. ForzaTech Studio — integrated native car authoring

**What it does:** A Windows application with model/scene editors, material and texture inspection,
model creation/conversion and collision tools. It documents part transforms with undo/redo, native
car scene editing and manufacturer paint data. Some encrypted inputs need external decryption;
bone animation editing remains unfinished. Source: [pinned features and limits](https://github.com/D3FEKT/ForzaTechStudio/blob/4f373c5fb192551ce5249e320dd79b1399b693ca/README.md).

**Better than us:** Bringing related native tasks together: adjust a part, inspect its material,
follow texture references and write game resources. Our browser presentation and separate scripts
offer less direct authoring control.

**Worse for our use case:** Windows/runtime/game setup and input preparation precede use; our
public collection removes that preparation for browsing. Its advertised features are not an
independent benchmark of conversion correctness or rendering fidelity.

**Borrow:** A connected part → material → texture inspector, plus reversible part transforms.

### 9. AssetRipper — reconstruction beyond the mesh

**What it does:** Analyzes Unity game files, converts assets into native Unity format and helps
identify dependencies and broken references. Source: [pinned project description](https://github.com/AssetRipper/AssetRipper/blob/bb5f08ac061d43f85ae14386009b58b93b95156c/README.md).

**Better than us:** Reconstructing an engine-oriented asset graph, where relationships matter as
much as exported meshes. That is useful when a missing referenced resource explains an incomplete
asset; our current public workflow emphasizes cars and their exports.

**Worse for our use case:** Unity specialization does not replace the proprietary console-format
decoders needed for our current games. A general reconstruction tool also leaves the specific
finished car catalog to its user.

**Borrow:** Per-car dependency completeness reports, with unresolved resources visible.

### 10. AssetStudio — broad asset inspection and animation export

**What it does:** Explores/extracts Unity assets, exports meshes as OBJ and models/animations as
FBX, with scene-hierarchy and asset-list workflows. The inspected original repository is archived.
Sources: [pinned feature/usage guide](https://github.com/Perfare/AssetStudio/blob/d158e864b556b5970709c2a52e47944d53aa98a2/README.md),
[repository archive status](https://github.com/Perfare/AssetStudio).

**Better than us:** Discovering different asset types and explicitly associating selected animation
clips with model exports. Our showroom's static GLBs do not offer that animation-selection workflow.

**Worse for our use case:** Its Unity input scope does not cover our custom formats, and an archived
original repo is a maintenance limitation when planning new integrations. That does not establish
that every fork is unmaintained or that historical exports are unreliable.

**Borrow:** Distinguish the asset list from the assembled scene, and show animation associations.

### 11. NFS-CarToolkit — car-specific modding semantics

**What it does:** The author's 2019 release documents autosculpt support, markers, vinyls,
materials, ZModeler export and a DirectX 11 viewer. Its ConfigFree export supports a car from the
same game without a separate configuration file. This is dated capability evidence, not a claim
about the latest release. Source: [author's release article](https://nfs-tools.blogspot.com/2019/05/nfs-cartoolkit-v25-released.html).

**Better than us:** Treating customization and attachment markers as editing concepts. A useful car
mod needs more than a body mesh; our GLB workflow does not establish NFS-style customization or
same-game native export.

**Worse for our use case:** Its installed NFS modding workflow and game-specific configuration are
more involved than choosing a car from our browser catalog. The historical feature list does not
establish current compatibility or support quality.

**Borrow:** Expose attachment markers and customization alternatives with their native identities.

### 12. Noesis — reusable conversion and plugin infrastructure

**What it does:** Previews/converts model, image and animation formats through native modules and
Python plugins. The author's page specifies a Windows PC. Source: [official project page](https://www.richwhitehouse.com/index.php?content=inc_projects.php&showproject=91).

**Better than us:** Adding another format to a reusable conversion host rather than building its
preview, processing and plugin interfaces anew. That is a better starting point for exploratory
format work when a suitable plugin exists.

**Worse for our use case:** A conversion host still leaves the particular recovery, assembly,
catalog and public presentation to its user. Its plugin architecture alone does not establish
support for our games or fidelity for any particular car.

**Borrow:** A small decoder adapter contract with explicit capabilities and claim limits.

## What to prioritize here

My assessment is that our most defensible distinction is the combination of immediate access,
editable per-car outputs and inspectable recovery evidence. We should preserve that while making
the recovered semantics more useful. This is a recommendation from the comparisons, not a measured
user-preference ranking.

1. **Make parts explain themselves.** Use the CodeWalker/Forza/Sollumz examples to connect selected
   geometry to native part names, source records, materials, transforms and dependencies. Start with
   one car whose assembly is well understood; success means a visitor can explain which source
   resource produced a visible part without reading the recovery scripts.
2. **Show fidelity and completeness per car.** Build on our existing claim limits: distinguish
   decoded native inputs, static assembly choices, viewer approximations and presentation edits.
   Report missing dependencies and unresolved customization, rather than treating a loadable GLB
   as evidence of complete recovery. This directly addresses existing [game-specific open items](README.md#open-items).
3. **Add shareable inspection states.** Borrow noclip's state-oriented viewing: a link should reopen
   the same car, paint, camera and source/enhanced presentation. Extend the existing car/game URL
   selection and paint persistence rather than replacing them.
4. **Define the intended roundtrip before adding exporters.** If the goal is native game modding,
   choose one game and prove a bounded re-import in that game, including parts/materials and memory
   constraints. If the goal remains editable interchange assets, describe the GLB/Blender guarantee
   precisely. Sollumz and GTPS2ModelTool demonstrate why these are different acceptance criteria.

Broader game coverage alone is not the most useful next target suggested by this study. Several
comparators already cover broader engines or deeper native workflows; our existing source/editor
separation and evidence can support a more understandable car library first.

## Evidence boundaries and verification

GitHub READMEs were retrieved through the GitHub API at the linked commits. Non-GitHub articles
were read with Jev Browser. Search snippets served only as leads. The Models Resource was excluded
after its page presented a Cloudflare verification barrier. No claim relies on its inaccessible
content, third-party comments or screenshots.

The GTPS2 guide and README describe different boundaries: dumping for inspection is documented,
while complete native rebuilding and GT4 support remain limited. Neither passage is used to
claim a complete GT4 native roundtrip. Likewise, none of the competing projects is alleged to
lack tests or provenance merely because its README does not describe our particular receipt system.

Local verification for this documentation task: `env -u CI tools/check.sh`, with 127 checks passing,
zero failing and three Blender roundtrip checks skipped because Blender was unavailable. The asset
index verifier reported `VERIFY OK`, including rejection of corrupt manifests, rehashed cross-car
swaps and altered fidelity/schema declarations. This checks the local baseline; it does not test
the competing software or close any original-game fidelity gap. Session sources and check logs
are local under `.scratch/research/similar-projects-2026-10-21/`.
