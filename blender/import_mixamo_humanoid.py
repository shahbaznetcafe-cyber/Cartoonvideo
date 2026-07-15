"""Build an SBZ-ready humanoid GLB from a Mixamo character and animations.

The downloaded character and animation files remain local assets (the project
gitignore excludes their directories).  This script is reusable code only.

Run with Blender:

    blender --background --python blender/import_mixamo_humanoid.py -- \
      character.fbx output.glb output.blend Idle=idle.fbx Talking=talking.fbx
"""

from __future__ import annotations

import os
import sys

import bpy


def _arguments() -> list[str]:
    try:
        return sys.argv[sys.argv.index("--") + 1 :]
    except ValueError:
        return []


def _fail(message: str) -> None:
    raise SystemExit(f"MIXAMO_IMPORT_ERROR: {message}")


def _import_fbx(path: str) -> list[bpy.types.Object]:
    before = set(bpy.context.scene.objects)
    bpy.ops.import_scene.fbx(
        filepath=path,
        use_anim=True,
        automatic_bone_orientation=False,
    )
    return [obj for obj in bpy.context.scene.objects if obj not in before]


def _first_armature(objects: list[bpy.types.Object]) -> bpy.types.Object | None:
    return next((obj for obj in objects if obj.type == "ARMATURE"), None)


def _remove_imported(objects: list[bpy.types.Object]) -> None:
    for obj in objects:
        if obj.name in bpy.context.scene.objects:
            bpy.data.objects.remove(obj, do_unlink=True)


def _attach_animation(
    target: bpy.types.Object,
    clip_name: str,
    animation_fbx: str,
) -> tuple[int, int]:
    imported = _import_fbx(animation_fbx)
    source_armature = _first_armature(imported)
    if source_armature is None or source_armature.animation_data is None:
        _remove_imported(imported)
        _fail(f"no animation armature found in {animation_fbx}")

    source_action = source_armature.animation_data.action
    if source_action is None:
        _remove_imported(imported)
        _fail(f"no action found in {animation_fbx}")

    action = source_action.copy()
    action.name = clip_name
    action.use_fake_user = True
    start, end = (int(round(value)) for value in action.frame_range)

    animation_data = target.animation_data_create()
    track = animation_data.nla_tracks.new()
    track.name = clip_name
    strip = track.strips.new(clip_name, start, action)
    strip.name = clip_name
    strip.action_frame_start = start
    strip.action_frame_end = end

    source_armature.animation_data.action = None
    _remove_imported(imported)
    return start, end


def main() -> None:
    args = _arguments()
    if len(args) < 3:
        _fail("expected character.fbx output.glb output.blend [Name=animation.fbx ...]")

    character_fbx, output_glb, output_blend, *animation_specs = args
    character_fbx = os.path.abspath(character_fbx)
    output_glb = os.path.abspath(output_glb)
    output_blend = os.path.abspath(output_blend)
    for path in (character_fbx,):
        if not os.path.isfile(path):
            _fail(f"file not found: {path}")

    bpy.ops.wm.read_factory_settings(use_empty=True)
    character_objects = _import_fbx(character_fbx)
    armature = _first_armature(character_objects)
    meshes = [obj for obj in character_objects if obj.type == "MESH"]
    if armature is None or not meshes:
        _fail("character FBX must contain an armature and at least one mesh")

    armature.name = "HumanoidRig"
    for obj in meshes:
        obj.name = f"HumanoidMesh_{obj.name}"

    if armature.animation_data:
        armature.animation_data_clear()

    clip_ranges: dict[str, tuple[int, int]] = {}
    for spec in animation_specs:
        if "=" not in spec:
            _fail(f"invalid animation argument: {spec}")
        clip_name, animation_path = spec.split("=", 1)
        animation_path = os.path.abspath(animation_path)
        if not clip_name.strip() or not os.path.isfile(animation_path):
            _fail(f"invalid animation: {spec}")
        clip_ranges[clip_name.strip()] = _attach_animation(
            armature,
            clip_name.strip(),
            animation_path,
        )

    scene = bpy.context.scene
    scene.render.fps = 30
    if clip_ranges:
        scene.frame_start = min(start for start, _ in clip_ranges.values())
        scene.frame_end = max(end for _, end in clip_ranges.values())
    scene["sbz_character_type"] = "MIXAMO_HUMANOID"
    scene["sbz_animation_clips"] = ",".join(clip_ranges)

    os.makedirs(os.path.dirname(output_glb), exist_ok=True)
    os.makedirs(os.path.dirname(output_blend), exist_ok=True)
    bpy.ops.wm.save_as_mainfile(filepath=output_blend)
    bpy.ops.export_scene.gltf(
        filepath=output_glb,
        export_format="GLB",
        export_animations=True,
        export_animation_mode="NLA_TRACKS",
        export_nla_strips=True,
        export_skins=True,
        export_armature_object_remove=True,
        export_morph=True,
        export_yup=True,
        export_apply=False,
        export_cameras=False,
        export_lights=False,
        export_extras=True,
    )
    print(
        "MIXAMO_IMPORT_OK "
        f"armature={armature.name} meshes={len(meshes)} "
        f"clips={','.join(clip_ranges) or 'none'} glb={output_glb}",
        flush=True,
    )


if __name__ == "__main__":
    main()
