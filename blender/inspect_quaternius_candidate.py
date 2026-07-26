"""Read-only Blender inspection for a Quaternius GLTF candidate."""
import json
import os
import sys

import bpy
from mathutils import Vector


def main():
    args = sys.argv[sys.argv.index("--") + 1:]
    source, output = map(os.path.abspath, args[:2])
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.ops.import_scene.gltf(filepath=source, import_pack_images=True)
    scene = bpy.context.scene
    scene.frame_set(0)
    meshes = [obj for obj in scene.objects if obj.type == "MESH"]
    armatures = [obj for obj in scene.objects if obj.type == "ARMATURE"]
    points = []
    for obj in meshes:
        points.extend(obj.matrix_world @ Vector(corner) for corner in obj.bound_box)
    report = {
        "source": source,
        "blender": bpy.app.version_string,
        "objects": [{"name": o.name, "type": o.type, "parent": o.parent.name if o.parent else None,
                     "location": list(o.location), "rotation": list(o.rotation_euler), "scale": list(o.scale)}
                    for o in scene.objects],
        "bounds": {"min": [min(p[i] for p in points) for i in range(3)],
                   "max": [max(p[i] for p in points) for i in range(3)]},
        "armatures": [{"name": a.name, "bones": [b.name for b in a.data.bones]} for a in armatures],
        "meshes": [{"name": m.name, "vertices": len(m.data.vertices), "polygons": len(m.data.polygons),
                    "materials": [s.material.name for s in m.material_slots if s.material],
                    "shape_keys": [k.name for k in m.data.shape_keys.key_blocks] if m.data.shape_keys else []}
                   for m in meshes],
        "actions": [{"name": a.name, "frame_range": list(a.frame_range), "slots": len(a.slots)} for a in bpy.data.actions],
        "images": [{"name": i.name, "packed": bool(i.packed_file), "size": list(i.size)} for i in bpy.data.images],
    }
    os.makedirs(os.path.dirname(output), exist_ok=True)
    with open(output, "w", encoding="utf-8") as handle:
        json.dump(report, handle, indent=2)
    print("QUATERNIUS_INSPECTION=" + output, flush=True)


if __name__ == "__main__":
    main()
