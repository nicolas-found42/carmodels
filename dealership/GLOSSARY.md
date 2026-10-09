# Viewer

The two static three.js pages that display the recovered car corpus in a browser, offline.

## Language

**Recovered inspector**:
`recovered.html`, which renders the recovered original geometry of one car with its embedded model textures.
_Avoid_: Model viewer, main viewer

**Silhouette gallery**:
`index.html`, which shows procedural silhouette meshes shaped by each car's handling values; the meshes are reconstructions, not the game models.
_Avoid_: Car gallery, model gallery

**Tree**:
One of the five translated object-tree candidates retained per car; tree zero is the default.
_Avoid_: Hierarchy, scene graph

**Record**:
One geometry record of a car, selectable together with a tree in the inspector.
_Avoid_: Mesh, part

**Texture variant**:
A numeric texture selector offered in the inspector and exported as a KHR_materials_variants variant.
_Avoid_: Livery, skin

**Visibility preset**:
A stored wheel and light state, such as low-speed or moving-wheel, derived from the original visibility routines.
_Avoid_: Animation, pose

**Honesty label**:
The on-screen note that marks an item as a candidate or a procedural reconstruction.
_Avoid_: Disclaimer, warning

**Showcase data**:
`public/cars.json`, the manifest-derived data the silhouette gallery reads; `tools/build_showcase.py` regenerates it.
_Avoid_: Car list, manifest
