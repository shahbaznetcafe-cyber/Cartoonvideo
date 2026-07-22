"""Standardize one ready-made Quaternius humanoid and export an animated GLB.

The source asset is imported into a clean temporary scene and never modified.
Usage (through Blender):
  -- source.gltf output.glb work.blend conversion_report.json
"""
from __future__ import annotations

import json
import hashlib
import math
import os
import sys
import time
from pathlib import Path

import bpy
from mathutils import Vector


TARGET_HEIGHT = 1.72
ALIASES = {
    "Point": "Idle_Gun_Pointing",
    "Celebrate": "Interact",
    "TalkIdle": "Idle",
    "Listen": "Idle_Neutral",
}


def arguments():
    try:
        values = sys.argv[sys.argv.index("--") + 1:]
    except ValueError:
        values = []
    if len(values) != 4:
        raise SystemExit("Expected: source.gltf output.glb output.blend report.json")
    return [Path(value).resolve() for value in values]


def world_bounds(objects):
    points = [obj.matrix_world @ Vector(corner) for obj in objects for corner in obj.bound_box]
    if not points:
        raise RuntimeError("No character mesh bounds available")
    minimum = Vector(tuple(min(point[i] for point in points) for i in range(3)))
    maximum = Vector(tuple(max(point[i] for point in points) for i in range(3)))
    return minimum, maximum


def set_active(obj):
    if bpy.context.object and bpy.context.object.mode != "OBJECT":
        bpy.ops.object.mode_set(mode="OBJECT")
    bpy.ops.object.select_all(action="DESELECT")
    obj.select_set(True)
    bpy.context.view_layer.objects.active = obj


def descendants(parent):
    result = []
    stack = list(parent.children)
    while stack:
        item = stack.pop()
        result.append(item)
        stack.extend(item.children)
    return result


def action_duration(action, fps):
    start, end = action.frame_range
    return max(0.0, float(end - start) / float(fps))


def sha256(path):
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def main():
    started = time.perf_counter()
    source, output_glb, output_blend, report_path = arguments()
    if not source.is_file():
        raise FileNotFoundError(source)
    character_name = os.getenv("SBZ_CHARACTER_NAME") or source.stem
    character_id = os.getenv("SBZ_CHARACTER_ID") or "quaternius_" + "".join(
        char.lower() if char.isalnum() else "_" for char in character_name
    ).strip("_")
    for output in (output_glb, output_blend, report_path):
        output.parent.mkdir(parents=True, exist_ok=True)

    suffix = source.suffix.lower()
    if suffix == ".blend":
        bpy.ops.wm.open_mainfile(filepath=str(source), load_ui=False)
    else:
        bpy.ops.wm.read_factory_settings(use_empty=True)
        if suffix in {".gltf", ".glb"}:
            bpy.ops.import_scene.gltf(filepath=str(source), import_pack_images=True)
        elif suffix == ".fbx":
            bpy.ops.import_scene.fbx(filepath=str(source), use_anim=True)
        else:
            raise RuntimeError(f"Unsupported standardization source: {source.suffix}")
    scene = bpy.context.scene
    source_fps = scene.render.fps / scene.render.fps_base

    armatures = [obj for obj in scene.objects if obj.type == "ARMATURE"]
    if len(armatures) != 1:
        raise RuntimeError(f"Expected one production armature, found {len(armatures)}")
    armature = armatures[0]
    armature.name = "QuaterniusMasterRig"
    armature.data.name = "QuaterniusMasterSkeleton"
    armature["sbz_character_type"] = "QUATERNIUS_ANIMATED"
    armature["sbz_runtime_tier"] = "SKELETAL_BASIC"
    armature["sbz_forward_blender"] = "-Y"
    armature["sbz_forward_threejs"] = "+Z_CAMERA"

    character_objects = [obj for obj in descendants(armature) if obj.type == "MESH"]
    if not character_objects:
        raise RuntimeError("Imported armature has no child meshes")

    # Remove only unrelated source helpers, cameras and lights. The selected
    # character's complete mesh hierarchy remains intact.
    keep = {armature, *descendants(armature)}
    removed = []
    for obj in list(scene.objects):
        if obj not in keep and obj.type in {"CAMERA", "LIGHT", "MESH", "EMPTY"}:
            removed.append({"name": obj.name, "type": obj.type})
            bpy.data.objects.remove(obj, do_unlink=True)

    scene.frame_set(0)
    bpy.context.view_layer.update()
    before_min, before_max = world_bounds(character_objects)
    source_height = before_max.z - before_min.z
    # Quaternius kits use mixed authoring units. A large source mesh is still
    # safe because this pipeline applies one uniform scale and verifies final
    # bounds after grounding; reject only genuinely corrupt/extreme imports.
    if not 0.01 < source_height < 100.0:
        raise RuntimeError(f"Implausible source height: {source_height}")

    # Apply object-level orientation/scale only. Pose bones and animation key
    # data are not destructively transformed or rebuilt.
    uniform_scale = TARGET_HEIGHT / source_height
    armature.scale = tuple(value * uniform_scale for value in armature.scale)
    set_active(armature)
    bpy.ops.object.transform_apply(location=False, rotation=True, scale=True)
    bpy.context.view_layer.update()

    scaled_min, scaled_max = world_bounds(character_objects)
    center = (scaled_min + scaled_max) * 0.5
    armature.location.x -= center.x
    armature.location.y -= center.y
    armature.location.z -= scaled_min.z
    bpy.context.view_layer.update()
    final_min, final_max = world_bounds(character_objects)

    # Preserve all imported actions and add deterministic aliases by copying
    # authored actions on the same skeleton (no retargeting/procedural motion).
    original_actions = {action.name: action for action in bpy.data.actions}
    source_action_names = sorted(original_actions, key=str.casefold)
    missing_alias_sources = []
    for final_name, source_name in ALIASES.items():
        if final_name in bpy.data.actions:
            continue
        source_action = original_actions.get(source_name)
        if source_action is None:
            missing_alias_sources.append({"alias": final_name, "source": source_name})
            continue
        copied = source_action.copy()
        copied.name = final_name
        copied.use_fake_user = True

    # Remove only truly empty actions; imported and alias actions have a slot.
    removed_actions = []
    for action in list(bpy.data.actions):
        if len(action.slots) == 0:
            removed_actions.append(action.name)
            bpy.data.actions.remove(action)
        else:
            action.use_fake_user = True

    # Pack any real images; this source uses material colors, but the workflow
    # remains texture-safe for compatible Quaternius variants.
    packed_images = []
    for image in bpy.data.images:
        if image.source == "FILE" and not image.packed_file:
            try:
                image.pack()
                packed_images.append(image.name)
            except RuntimeError:
                pass

    scene["sbz_master_character"] = character_name
    scene["sbz_character_id"] = character_id
    scene["sbz_source"] = str(source)
    scene["sbz_ground_blender_z"] = 0.0
    scene["sbz_ground_threejs_y"] = 0.0
    scene.frame_start = 0
    scene.frame_end = max((math.ceil(action.frame_range[1]) for action in bpy.data.actions), default=1)

    bpy.ops.wm.save_as_mainfile(filepath=str(output_blend))

    bpy.ops.object.select_all(action="DESELECT")
    armature.select_set(True)
    for obj in character_objects:
        obj.select_set(True)
    bpy.context.view_layer.objects.active = armature
    bpy.ops.export_scene.gltf(
        filepath=str(output_glb),
        export_format="GLB",
        use_selection=True,
        export_animations=True,
        export_animation_mode="ACTIONS",
        export_skins=True,
        export_morph=True,
        export_materials="EXPORT",
        export_image_format="AUTO",
        export_yup=True,
        export_apply=False,
        export_cameras=False,
        export_lights=False,
        export_extras=True,
    )

    fps = scene.render.fps / scene.render.fps_base
    actions = sorted(
        ({"name": action.name, "duration": round(action_duration(action, fps), 5),
          "frame_range": [round(float(v), 4) for v in action.frame_range]}
         for action in bpy.data.actions), key=lambda row: row["name"].casefold())
    materials = sorted({slot.material.name for obj in character_objects for slot in obj.material_slots if slot.material})
    report = {
        "character_name": character_name,
        "character_id": character_id,
        "source": str(source),
        "source_sha256": sha256(source),
        "blender_executable": bpy.app.binary_path,
        "blender_version": bpy.app.version_string,
        "armature": armature.name,
        "bones": [bone.name for bone in armature.data.bones],
        "meshes": [{"name": obj.name, "vertices": len(obj.data.vertices), "triangles": sum(len(poly.vertices) - 2 for poly in obj.data.polygons),
                    "materials": [slot.material.name for slot in obj.material_slots if slot.material]}
                   for obj in character_objects],
        "materials": materials,
        "images": [{"name": image.name, "packed": bool(image.packed_file), "size": list(image.size)} for image in bpy.data.images],
        "actions": actions,
        "source_actions": source_action_names,
        "source_fps": source_fps,
        "aliases": ALIASES,
        "missing_alias_sources": missing_alias_sources,
        "removed_helpers": removed,
        "removed_empty_actions": removed_actions,
        "packed_images": packed_images,
        "source_bounds": {"min": list(before_min), "max": list(before_max), "height": source_height},
        "final_bounds_blender": {"min": list(final_min), "max": list(final_max), "height": final_max.z - final_min.z},
        "normalization_scale": uniform_scale,
        "target_height": TARGET_HEIGHT,
        "output_glb": str(output_glb),
        "output_blend": str(output_blend),
        "conversion_seconds": round(time.perf_counter() - started, 4),
    }
    report_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print("QUATERNIUS_STANDARDIZED=" + json.dumps({"glb": str(output_glb), "blend": str(output_blend), "actions": len(actions)}), flush=True)


if __name__ == "__main__":
    main()
