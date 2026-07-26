"""Read-only Blender scene inventory for production re-rigging."""
import json
import os
import sys

import bpy
from mathutils import Vector


def _round_vec(value):
    return [round(float(item), 6) for item in value]


def _world_bounds(obj):
    corners = [obj.matrix_world @ Vector(corner) for corner in obj.bound_box]
    return {
        "min": _round_vec([min(p[i] for p in corners) for i in range(3)]),
        "max": _round_vec([max(p[i] for p in corners) for i in range(3)]),
    }


def _material_info(material):
    images = []
    if material and material.use_nodes and material.node_tree:
        for node in material.node_tree.nodes:
            if node.type == "TEX_IMAGE" and node.image:
                images.append({
                    "name": node.image.name,
                    "filepath": bpy.path.abspath(node.image.filepath),
                    "packed": bool(node.image.packed_file),
                    "size": list(node.image.size),
                })
    return {
        "name": material.name if material else "",
        "use_nodes": bool(material and material.use_nodes),
        "images": images,
    }


def main():
    args = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    if not args:
        raise SystemExit("output JSON path required")
    output = os.path.abspath(args[0])
    meshes = []
    armatures = []
    objects = []

    for obj in bpy.data.objects:
        objects.append({
            "name": obj.name,
            "type": obj.type,
            "parent": obj.parent.name if obj.parent else None,
            "parent_type": obj.parent_type,
            "parent_bone": obj.parent_bone,
            "location": _round_vec(obj.location),
            "rotation_euler": _round_vec(obj.rotation_euler),
            "scale": _round_vec(obj.scale),
            "hidden_render": obj.hide_render,
        })
        if obj.type == "MESH":
            shape_keys = []
            if obj.data.shape_keys:
                shape_keys = [key.name for key in obj.data.shape_keys.key_blocks]
            meshes.append({
                "name": obj.name,
                "data_name": obj.data.name,
                "vertices": len(obj.data.vertices),
                "polygons": len(obj.data.polygons),
                "world_bounds": _world_bounds(obj),
                "materials": [_material_info(slot.material) for slot in obj.material_slots],
                "modifiers": [
                    {
                        "name": mod.name,
                        "type": mod.type,
                        "object": getattr(getattr(mod, "object", None), "name", None),
                    }
                    for mod in obj.modifiers
                ],
                "vertex_groups": [group.name for group in obj.vertex_groups],
                "shape_keys": shape_keys,
            })
        elif obj.type == "ARMATURE":
            armatures.append({
                "name": obj.name,
                "bones": [
                    {
                        "name": bone.name,
                        "parent": bone.parent.name if bone.parent else None,
                        "head_local": _round_vec(bone.head_local),
                        "tail_local": _round_vec(bone.tail_local),
                        "use_deform": bone.use_deform,
                    }
                    for bone in obj.data.bones
                ],
            })

    report = {
        "source": bpy.data.filepath,
        "blender_version": bpy.app.version_string,
        "scene": bpy.context.scene.name,
        "frame_range": [bpy.context.scene.frame_start, bpy.context.scene.frame_end],
        "objects": objects,
        "meshes": meshes,
        "armatures": armatures,
        "materials": [material.name for material in bpy.data.materials],
        "images": [
            {
                "name": image.name,
                "filepath": bpy.path.abspath(image.filepath),
                "packed": bool(image.packed_file),
                "size": list(image.size),
            }
            for image in bpy.data.images
        ],
        "actions": [
            {
                "name": action.name,
                "frame_range": _round_vec(action.frame_range),
                "slots": len(getattr(action, "slots", [])),
            }
            for action in bpy.data.actions
        ],
    }
    os.makedirs(os.path.dirname(output), exist_ok=True)
    with open(output, "w", encoding="utf-8") as handle:
        json.dump(report, handle, ensure_ascii=False, indent=2)
    print("SBZ_SOURCE_INSPECTION=" + output)


if __name__ == "__main__":
    main()
