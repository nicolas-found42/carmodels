"""Repair the pinned Blender glTF importer's custom-attribute ordering in memory.

Run in Blender's scripting workspace before importing MC3 GLBs. No installed
Blender files or model data are modified. Other importer revisions fail closed.
"""

import hashlib
import inspect

import bpy
from io_scene_gltf2.blender.imp import mesh


SOURCE_SHA256 = "42efeb8bce96506985776bb414cc86f7ab59e965130053c3c4fe86146ed53bad"


def install():
    if bpy.app.version != (4, 5, 14):
        raise RuntimeError(
            "Custom-attribute compatibility repair requires Blender 4.5.14"
        )
    if getattr(mesh.do_primitives, "_carmodels_ordered_attributes", False):
        return
    source = inspect.getsource(mesh.do_primitives)
    if hashlib.sha256(source.encode()).hexdigest() != SOURCE_SHA256:
        raise RuntimeError(
            "Unrecognized Blender glTF importer; refusing compatibility repair"
        )
    # The importer appends attribute_data in first-seen order, but later indexes
    # it while iterating this collection. A dict keeps both orders identical.
    source = source.replace("attributes = set({})", "attributes = {}")
    source = source.replace(
        "attributes.update(set(custom_attrs))",
        "attributes.update(dict.fromkeys(custom_attrs))",
    )
    namespace = dict(vars(mesh))
    exec(compile(source, "<carmodels-blender-gltf-compat>", "exec"), namespace)
    repaired = namespace["do_primitives"]
    repaired._carmodels_ordered_attributes = True
    mesh.do_primitives = repaired


if __name__ == "__main__":
    install()
    print(
        "Installed Blender 4.5.14 ordered custom-attribute import repair (this session only)"
    )
