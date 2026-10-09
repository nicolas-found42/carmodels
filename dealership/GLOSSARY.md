# Viewer

The two static three.js pages that display the recovered car corpus in a browser, offline.

## Language

**Source-model showcase**:
The showcase of recovered original assets, preserving their provenance and experimental recovery interpretations.
_Avoid_: Dealership, model viewer, main viewer

**Dealership**:
The editable vehicle showcase with its own model copies and catalog. A dealership model can diverge from its source without changing that source.
_Avoid_: Silhouette gallery, source-model showcase

**Dealership model**:
An independently editable vehicle edition, initially copied from a recovered source model.
_Avoid_: Source model, recovery artifact

**Source model**:
A recovered vehicle asset belonging to the source corpus and its verification evidence.
_Avoid_: Dealership model, editable edition

**Dealership catalog**:
The names, vehicle information and presentation choices owned by the dealership.
_Avoid_: Source manifest, recovery index

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
Display data compiled from a showcase’s own model and catalog inputs.
_Avoid_: Source manifest, recovery index
