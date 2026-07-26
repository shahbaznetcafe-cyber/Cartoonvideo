"""Create a production humanoid rig for the existing PotatoWaistcoat asset.

The input blend is opened read-only by the calling Blender process.  This
script only saves a new production blend and GLB; it never saves over input.

Run:
  blender potatowaistcoat.blend --background --python this_file.py -- \
    output.blend output.glb output.mp4 report.json
"""

from __future__ import annotations

import hashlib
import json
import math
import os
import shutil
import subprocess
import sys
from collections import deque
from pathlib import Path

import bpy
from mathutils import Matrix, Vector


SOURCE = Path(bpy.data.filepath).resolve()


def args() -> list[str]:
    try:
        return sys.argv[sys.argv.index("--") + 1 :]
    except ValueError:
        return []


def clamp(value: float, lo: float = 0.0, hi: float = 1.0) -> float:
    return max(lo, min(hi, value))


def smoothstep(lo: float, hi: float, value: float) -> float:
    if hi == lo:
        return float(value >= hi)
    t = clamp((value - lo) / (hi - lo))
    return t * t * (3.0 - 2.0 * t)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def set_active(obj: bpy.types.Object) -> None:
    bpy.ops.object.mode_set(mode="OBJECT") if bpy.context.object and bpy.context.object.mode != "OBJECT" else None
    bpy.ops.object.select_all(action="DESELECT")
    obj.select_set(True)
    bpy.context.view_layer.objects.active = obj


def bone(edit_bones, name: str, head, tail, parent=None, deform=True):
    item = edit_bones.new(name)
    item.head = head
    item.tail = tail
    item.parent = parent
    item.use_connect = bool(parent and (Vector(head) - parent.tail).length <= 0.0001)
    item.use_deform = deform
    return item


def connected_components(mesh: bpy.types.Mesh) -> list[list[int]]:
    neighbours = [[] for _ in mesh.vertices]
    for edge in mesh.edges:
        a, b = edge.vertices
        neighbours[a].append(b)
        neighbours[b].append(a)
    unseen = set(range(len(mesh.vertices)))
    result: list[list[int]] = []
    while unseen:
        seed = unseen.pop()
        queue = deque([seed])
        component = [seed]
        while queue:
            current = queue.popleft()
            for other in neighbours[current]:
                if other in unseen:
                    unseen.remove(other)
                    queue.append(other)
                    component.append(other)
        result.append(component)
    return result


def identify_eye_components(mesh: bpy.types.Mesh) -> tuple[set[int], set[int]]:
    """Find the two detached eyeball components from geometry, not names."""
    candidates = []
    for component in connected_components(mesh):
        if not 45 <= len(component) <= 120:
            continue
        coords = [mesh.vertices[i].co for i in component]
        minimum = Vector((min(v.x for v in coords), min(v.y for v in coords), min(v.z for v in coords)))
        maximum = Vector((max(v.x for v in coords), max(v.y for v in coords), max(v.z for v in coords)))
        center = (minimum + maximum) * 0.5
        size = maximum - minimum
        if center.y < -0.27 and 0.10 < abs(center.x) < 0.20 and 0.08 < center.z < 0.18 and size.z < 0.18:
            candidates.append((center.x, set(component)))
    left = next((vertices for x, vertices in candidates if x < 0.0), set())
    right = next((vertices for x, vertices in candidates if x > 0.0), set())
    return left, right


def cache_legacy_weights(mesh_obj: bpy.types.Object) -> list[dict[str, float]]:
    group_names = {group.index: group.name for group in mesh_obj.vertex_groups}
    cached = []
    for vertex in mesh_obj.data.vertices:
        cached.append({group_names[item.group]: item.weight for item in vertex.groups if item.group in group_names})
    return cached


def add_weight(target: dict[str, float], name: str, amount: float) -> None:
    if amount > 0.000001:
        target[name] = target.get(name, 0.0) + amount


def body_weights(co: Vector) -> dict[str, float]:
    z = co.z
    # The face projects forward from the torso and must follow Head even at
    # mouth/chin height.  The waistcoat ends just below z=-0.05.
    if co.y < -0.19 and z > -0.19 and abs(co.x) < 0.32:
        return {"Head": 1.0}
    if z >= 0.03:
        return {"Head": 1.0}
    if z >= -0.07:
        t = smoothstep(-0.07, 0.03, z)
        return {"Chest": 1.0 - t, "Neck": t * 0.25, "Head": t * 0.75}
    if z >= -0.24:
        t = smoothstep(-0.24, -0.07, z)
        return {"Spine": 1.0 - t, "Chest": t}
    if z >= -0.48:
        t = smoothstep(-0.48, -0.24, z)
        return {"Hips": 1.0 - t, "Spine": t}
    return {"Hips": 1.0}


def chain_weights(t: float, names: tuple[str, str, str], first_end: float, second_end: float, blend: float) -> dict[str, float]:
    a, b, c = names
    result: dict[str, float] = {}
    if t < first_end - blend:
        result[a] = 1.0
    elif t < first_end + blend:
        f = smoothstep(first_end - blend, first_end + blend, t)
        result[a], result[b] = 1.0 - f, f
    elif t < second_end - blend:
        result[b] = 1.0
    elif t < second_end + blend:
        f = smoothstep(second_end - blend, second_end + blend, t)
        result[b], result[c] = 1.0 - f, f
    else:
        result[c] = 1.0
    return result


def create_rig(mesh_obj: bpy.types.Object, legacy: list[dict[str, float]]) -> bpy.types.Object:
    # Remove only copied-scene legacy armature modifiers and armatures.
    for modifier in list(mesh_obj.modifiers):
        if modifier.type == "ARMATURE":
            mesh_obj.modifiers.remove(modifier)
    # Parent transform was already preserved and baked by main().
    mesh_obj.parent = None
    old_armatures = [obj for obj in bpy.data.objects if obj.type == "ARMATURE"]
    for obj in old_armatures:
        bpy.data.objects.remove(obj, do_unlink=True)

    armature_data = bpy.data.armatures.new("PotatoWaistcoat_ProductionSkeleton")
    rig = bpy.data.objects.new("PotatoWaistcoat_ProductionRig", armature_data)
    bpy.context.collection.objects.link(rig)
    rig.show_in_front = True
    rig["sbz_animation_tier"] = "SKELETAL_BASIC"
    rig["sbz_forward_axis"] = "-Y"
    rig["sbz_ground_z"] = -1.139068

    set_active(rig)
    bpy.ops.object.mode_set(mode="EDIT")
    eb = armature_data.edit_bones
    root = bone(eb, "Root", (0, 0, -1.139), (0, 0, -1.02), None, False)
    hips = bone(eb, "Hips", (0, 0, -0.61), (0, 0, -0.43), root)
    spine = bone(eb, "Spine", (0, 0, -0.43), (0, 0, -0.21), hips)
    chest = bone(eb, "Chest", (0, 0, -0.21), (0, 0, 0.02), spine)
    neck = bone(eb, "Neck", (0, 0, 0.02), (0, 0, 0.14), chest)
    head = bone(eb, "Head", (0, 0, 0.14), (0, 0, 0.66), neck)

    l_shoulder = bone(eb, "LeftShoulder", (-0.06, 0, -0.07), (-0.205, 0, -0.095), chest)
    l_upper = bone(eb, "LeftUpperArm", (-0.205, 0, -0.095), (-0.355, 0.005, -0.34), l_shoulder)
    l_lower = bone(eb, "LeftLowerArm", (-0.355, 0.005, -0.34), (-0.465, 0.012, -0.535), l_upper)
    bone(eb, "LeftHand", (-0.465, 0.012, -0.535), (-0.515, -0.015, -0.625), l_lower)
    r_shoulder = bone(eb, "RightShoulder", (0.06, 0, -0.07), (0.205, 0, -0.095), chest)
    r_upper = bone(eb, "RightUpperArm", (0.205, 0, -0.095), (0.355, 0.005, -0.34), r_shoulder)
    r_lower = bone(eb, "RightLowerArm", (0.355, 0.005, -0.34), (0.465, 0.012, -0.535), r_upper)
    bone(eb, "RightHand", (0.465, 0.012, -0.535), (0.515, -0.015, -0.625), r_lower)

    l_thigh = bone(eb, "LeftUpperLeg", (-0.12, 0, -0.56), (-0.145, 0, -0.84), hips)
    l_shin = bone(eb, "LeftLowerLeg", (-0.145, 0, -0.84), (-0.16, -0.02, -1.075), l_thigh)
    bone(eb, "LeftFoot", (-0.16, -0.02, -1.075), (-0.16, -0.17, -1.105), l_shin)
    r_thigh = bone(eb, "RightUpperLeg", (0.12, 0, -0.56), (0.145, 0, -0.84), hips)
    r_shin = bone(eb, "RightLowerLeg", (0.145, 0, -0.84), (0.16, -0.02, -1.075), r_thigh)
    bone(eb, "RightFoot", (0.16, -0.02, -1.075), (0.16, -0.17, -1.105), r_shin)

    # Source eye pieces are stylised eyelid/pupil cards rather than complete
    # spherical eyeballs. Keep look-at controls, but rigidly attach the visual
    # geometry to Head to prevent bind-pose squashing.
    bone(eb, "LeftEye", (-0.16, -0.30, 0.15), (-0.16, -0.39, 0.15), head, False)
    bone(eb, "RightEye", (0.16, -0.30, 0.15), (0.16, -0.39, 0.15), head, False)
    bone(eb, "Jaw", (0, -0.22, -0.10), (0, -0.41, -0.27), head)
    bpy.ops.object.mode_set(mode="OBJECT")

    # Delete legacy groups after their weights have been cached.
    for group in list(mesh_obj.vertex_groups):
        mesh_obj.vertex_groups.remove(group)
    group_names = [b.name for b in armature_data.bones if b.use_deform]
    groups = {name: mesh_obj.vertex_groups.new(name=name) for name in group_names}
    left_eye, right_eye = identify_eye_components(mesh_obj.data)

    weight_stats = {
        "left_eye_vertices": len(left_eye),
        "right_eye_vertices": len(right_eye),
        "central_torso_arm_weight_max": 0.0,
        "upper_body_leg_weight_max": 0.0,
        "unweighted_vertices": 0,
    }
    for vertex in mesh_obj.data.vertices:
        index = vertex.index
        co = vertex.co
        old = legacy[index]
        weights: dict[str, float] = {}
        if index in left_eye or index in right_eye:
            weights = {"Head": 1.0}
        else:
            old_l_arm = old.get("arm_L", 0.0)
            old_r_arm = old.get("arm_R", 0.0)
            old_l_leg = old.get("leg_L", 0.0)
            old_r_leg = old.get("leg_R", 0.0)
            old_jaw = old.get("jaw", 0.0)

            # Spatial gates are the manual correction zones. They deliberately
            # keep the central waistcoat out of shoulder and hip chains.
            l_arm = old_l_arm * smoothstep(0.16, 0.285, -co.x)
            r_arm = old_r_arm * smoothstep(0.16, 0.285, co.x)
            l_leg = old_l_leg * smoothstep(-0.47, -0.67, co.z) * smoothstep(0.045, 0.13, -co.x)
            r_leg = old_r_leg * smoothstep(-0.47, -0.67, co.z) * smoothstep(0.045, 0.13, co.x)
            jaw = old_jaw * smoothstep(-0.16, -0.28, co.y)
            limb_total = clamp(l_arm + r_arm + l_leg + r_leg + jaw, 0.0, 0.98)

            for name, value in body_weights(co).items():
                add_weight(weights, name, value * (1.0 - limb_total))

            if l_arm:
                t = clamp(((-co.x - 0.19) + max(0.0, -co.z - 0.08) * 0.52) / 0.59)
                for name, value in chain_weights(t, ("LeftUpperArm", "LeftLowerArm", "LeftHand"), 0.50, 0.87, 0.075).items():
                    add_weight(weights, name, value * l_arm)
            if r_arm:
                t = clamp(((co.x - 0.19) + max(0.0, -co.z - 0.08) * 0.52) / 0.59)
                for name, value in chain_weights(t, ("RightUpperArm", "RightLowerArm", "RightHand"), 0.50, 0.87, 0.075).items():
                    add_weight(weights, name, value * r_arm)
            if l_leg:
                t = clamp((-co.z - 0.54) / 0.60)
                for name, value in chain_weights(t, ("LeftUpperLeg", "LeftLowerLeg", "LeftFoot"), 0.52, 0.88, 0.07).items():
                    add_weight(weights, name, value * l_leg)
            if r_leg:
                t = clamp((-co.z - 0.54) / 0.60)
                for name, value in chain_weights(t, ("RightUpperLeg", "RightLowerLeg", "RightFoot"), 0.52, 0.88, 0.07).items():
                    add_weight(weights, name, value * r_leg)
            add_weight(weights, "Jaw", jaw)

        total = sum(weights.values())
        if total <= 0.000001:
            weights = {"Hips": 1.0}
            total = 1.0
            weight_stats["unweighted_vertices"] += 1
        for name, value in weights.items():
            normalized = value / total
            groups[name].add([index], normalized, "REPLACE")
            if abs(co.x) < 0.16 and -0.32 < co.z < 0.22 and "Arm" in name:
                weight_stats["central_torso_arm_weight_max"] = max(weight_stats["central_torso_arm_weight_max"], normalized)
            if co.z > -0.38 and "Leg" in name:
                weight_stats["upper_body_leg_weight_max"] = max(weight_stats["upper_body_leg_weight_max"], normalized)

    modifier = mesh_obj.modifiers.new(name="ProductionArmature", type="ARMATURE")
    modifier.object = rig
    modifier.use_deform_preserve_volume = True
    mesh_obj.parent = rig
    mesh_obj.parent_type = "OBJECT"
    mesh_obj["sbz_weighting"] = "spatial-manual-v2"
    mesh_obj["sbz_weight_stats"] = json.dumps(weight_stats, sort_keys=True)
    return rig


def add_shape_keys(mesh_obj: bpy.types.Object, legacy: list[dict[str, float]]) -> list[str]:
    """Add conservative facial controls using known face spatial regions."""
    if mesh_obj.data.shape_keys:
        mesh_obj.shape_key_clear()
    mesh_obj.shape_key_add(name="Basis", from_mix=False)
    created = []

    jaw = mesh_obj.shape_key_add(name="jawOpen", from_mix=False)
    jaw.value = 0.0
    jaw.slider_min = 0.0
    jaw.slider_max = 1.0
    pivot = Vector((0.0, -0.20, -0.10))
    rotation = Matrix.Rotation(math.radians(-13.0), 4, "X")
    changed = 0
    for vertex in mesh_obj.data.vertices:
        influence = legacy[vertex.index].get("jaw", 0.0) * smoothstep(-0.16, -0.30, vertex.co.y)
        if influence > 0.01:
            transformed = pivot + rotation @ (vertex.co - pivot)
            jaw.data[vertex.index].co = vertex.co.lerp(transformed, clamp(influence))
            changed += 1
    if changed:
        created.append("jawOpen")

    # Large stylised eyelids allow a safe spatial blink. Only the upper-front
    # face band moves; eyeball components themselves remain rigid eye controls.
    for name, center_x in (("eyeBlinkLeft", -0.16), ("eyeBlinkRight", 0.16)):
        key = mesh_obj.shape_key_add(name=name, from_mix=False)
        key.value = 0.0
        key.slider_min = 0.0
        key.slider_max = 1.0
        changed = 0
        for vertex in mesh_obj.data.vertices:
            co = vertex.co
            dx = abs(co.x - center_x)
            if co.y < -0.295 and dx < 0.105 and 0.14 < co.z < 0.27:
                x_weight = 1.0 - smoothstep(0.045, 0.105, dx)
                z_weight = 1.0 - smoothstep(0.14, 0.27, abs(co.z - 0.205) + 0.14)
                influence = clamp(x_weight * max(0.35, z_weight))
                key.data[vertex.index].co.z -= 0.075 * influence
                key.data[vertex.index].co.y += 0.012 * influence
                changed += 1
        if changed:
            created.append(name)
    return created


def set_pose_rotation(rig, bone_name: str, degrees_xyz) -> None:
    pb = rig.pose.bones[bone_name]
    pb.rotation_mode = "XYZ"
    pb.rotation_euler = tuple(math.radians(v) for v in degrees_xyz)


def key_pose(rig, frame: int, rotations: dict[str, tuple[float, float, float]], locations=None) -> None:
    bpy.context.scene.frame_set(frame)
    for pb in rig.pose.bones:
        pb.rotation_mode = "XYZ"
        pb.rotation_euler = (0, 0, 0)
        pb.location = (0, 0, 0)
    for name, rotation in rotations.items():
        set_pose_rotation(rig, name, rotation)
    for name, location in (locations or {}).items():
        rig.pose.bones[name].location = location
    for pb in rig.pose.bones:
        pb.keyframe_insert("rotation_euler", frame=frame, group=pb.name)
        pb.keyframe_insert("location", frame=frame, group=pb.name)


def new_action(rig, name: str):
    rig.animation_data_create()
    rig.animation_data_clear()
    rig.animation_data_create()
    action = bpy.data.actions.new(name=name)
    action.use_fake_user = True
    rig.animation_data.action = action
    return action


def stash_action(rig, action, start: int, end: int) -> None:
    rig.animation_data.action = None
    track = rig.animation_data.nla_tracks.new()
    track.name = action.name
    strip = track.strips.new(action.name, start, action)
    strip.name = action.name
    strip.action_frame_start = start
    strip.action_frame_end = end
    track.mute = True


def create_actions(rig: bpy.types.Object) -> dict[str, list[int]]:
    clips: dict[str, list[int]] = {}

    idle = new_action(rig, "Idle")
    key_pose(rig, 1, {"Chest": (0, 0, -1.0), "Head": (0, 0, 1.5)})
    key_pose(rig, 36, {"Chest": (1.5, 0, 1.0), "Head": (-1.0, 1.5, -1.0), "LeftUpperArm": (0, 0, -2), "RightUpperArm": (0, 0, 2)})
    key_pose(rig, 72, {"Chest": (0, 0, -1.0), "Head": (0, 0, 1.5)})
    stash_action(rig, idle, 1, 72)
    clips["Idle"] = [1, 72]

    walk = new_action(rig, "Walk")
    walk_keys = [
        (1, 24, -24, 20, -20, 8, -8),
        (13, 0, 0, 0, 0, 0, 0),
        (25, -24, 24, -20, 20, -8, 8),
        (37, 0, 0, 0, 0, 0, 0),
        (49, 24, -24, 20, -20, 8, -8),
    ]
    for frame, l_leg, r_leg, l_arm, r_arm, l_knee, r_knee in walk_keys:
        key_pose(rig, frame, {
            "LeftUpperLeg": (l_leg, 0, 0), "RightUpperLeg": (r_leg, 0, 0),
            "LeftLowerLeg": (max(0, -l_leg) + abs(l_knee), 0, 0),
            "RightLowerLeg": (max(0, -r_leg) + abs(r_knee), 0, 0),
            "LeftUpperArm": (l_arm, 0, 0), "RightUpperArm": (r_arm, 0, 0),
            "LeftLowerArm": (-12, 0, -5), "RightLowerArm": (-12, 0, 5),
            "Chest": (0, 0, -l_leg * 0.06),
        }, {"Hips": (0, 0, 0.012 if frame in (13, 37) else 0)})
    stash_action(rig, walk, 1, 49)
    clips["Walk"] = [1, 49]

    talk = new_action(rig, "TalkIdle")
    key_pose(rig, 1, {"Head": (0, -3, 0), "LeftUpperArm": (-6, 0, -4), "RightUpperArm": (-6, 0, 4)})
    key_pose(rig, 18, {"Head": (2, 3, -2), "Jaw": (7, 0, 0), "LeftUpperArm": (-18, -4, -12), "LeftLowerArm": (-28, 0, -10)})
    key_pose(rig, 36, {"Head": (-2, -2, 2), "Jaw": (2, 0, 0), "RightUpperArm": (-18, 4, 12), "RightLowerArm": (-28, 0, 10)})
    key_pose(rig, 54, {"Head": (1, 2, -1), "Jaw": (8, 0, 0), "LeftUpperArm": (-10, 0, -6), "RightUpperArm": (-10, 0, 6)})
    key_pose(rig, 72, {"Head": (0, -3, 0), "LeftUpperArm": (-6, 0, -4), "RightUpperArm": (-6, 0, 4)})
    stash_action(rig, talk, 1, 72)
    clips["TalkIdle"] = [1, 72]

    diagnostic = new_action(rig, "DeformationTest")
    key_pose(rig, 1, {})
    key_pose(rig, 20, {"LeftUpperArm": (-55, 10, -48), "RightUpperArm": (-55, -10, 48)})
    key_pose(rig, 40, {"LeftUpperArm": (-38, 0, -55), "RightUpperArm": (-38, 0, 55), "LeftLowerArm": (-95, 0, -12), "RightLowerArm": (-95, 0, 12)})
    key_pose(rig, 60, {"LeftUpperLeg": (52, 0, 8), "RightUpperLeg": (-38, 0, -8), "LeftLowerLeg": (86, 0, 0), "RightLowerLeg": (100, 0, 0)})
    key_pose(rig, 80, {})
    stash_action(rig, diagnostic, 1, 80)
    clips["DeformationTest"] = [1, 80]

    rig["sbz_animation_clips"] = ",".join(clips)
    return clips


def make_material(name: str, color, roughness=0.65):
    material = bpy.data.materials.new(name)
    material.diffuse_color = (*color, 1.0)
    material.use_nodes = True
    principled = material.node_tree.nodes.get("Principled BSDF")
    principled.inputs["Base Color"].default_value = (*color, 1.0)
    principled.inputs["Roughness"].default_value = roughness
    return material


def look_at(obj: bpy.types.Object, target: Vector) -> None:
    obj.rotation_euler = (target - obj.location).to_track_quat("-Z", "Y").to_euler()


def setup_render_scene(mesh_obj, rig, output_mp4: Path) -> None:
    scene = bpy.context.scene
    scene.render.engine = "BLENDER_EEVEE"
    scene.render.resolution_x = 960
    scene.render.resolution_y = 540
    scene.render.resolution_percentage = 100
    scene.render.fps = 24
    scene.frame_start = 1
    scene.frame_end = 240
    frames_dir = output_mp4.parent / f".{output_mp4.stem}_frames"
    if frames_dir.exists():
        shutil.rmtree(frames_dir)
    frames_dir.mkdir(parents=True, exist_ok=True)
    scene.render.image_settings.file_format = "PNG"
    scene.render.image_settings.color_mode = "RGB"
    scene.render.image_settings.color_depth = "8"
    scene.render.filepath = str(frames_dir / "frame_")
    scene.render.film_transparent = False
    if scene.world is None:
        scene.world = bpy.data.worlds.new("ValidationWorld")
    scene.world.color = (0.035, 0.045, 0.065)

    bpy.ops.mesh.primitive_plane_add(size=20, location=(0, 0, -1.142))
    floor = bpy.context.object
    floor.name = "ValidationFloor"
    floor.data.materials.append(make_material("ValidationFloorMaterial", (0.06, 0.085, 0.12), 0.82))
    floor["validation_only"] = True

    bpy.ops.object.camera_add(location=(2.7, -4.7, 0.65))
    camera = bpy.context.object
    camera.name = "ValidationCamera"
    camera.data.lens = 58
    look_at(camera, Vector((0, 0, -0.23)))
    scene.camera = camera

    for name, location, energy, size, color in (
        ("Key", (-2.5, -3.0, 3.0), 850, 3.0, (1.0, 0.86, 0.72)),
        ("Fill", (3.0, -1.8, 1.3), 600, 2.5, (0.55, 0.72, 1.0)),
        ("Rim", (0.5, 2.0, 2.6), 900, 2.0, (1.0, 0.58, 0.35)),
    ):
        data = bpy.data.lights.new(name, "AREA")
        data.energy, data.shape, data.size, data.color = energy, "DISK", size, color
        light = bpy.data.objects.new(name, data)
        bpy.context.collection.objects.link(light)
        light.location = location
        look_at(light, Vector((0, 0, -0.2)))

    # Presentation action: first half turntable, second half locomotion test.
    action = new_action(rig, "Presentation10s")
    for frame, yaw in ((1, 0), (31, 90), (61, 180), (91, 270), (120, 360)):
        key_pose(rig, frame, {"Chest": (0, 0, math.sin(frame * 0.08) * 1.2)})
        # Turn around world Z on the armature object. Root is a vertical bone,
        # so its local Euler Z is not a world-space yaw axis.
        rig.rotation_mode = "XYZ"
        rig.rotation_euler = (0.0, 0.0, math.radians(yaw))
        rig.location = (0.0, 0.0, 0.0)
        rig.keyframe_insert("rotation_euler", frame=frame, group="WorldMotion")
        rig.keyframe_insert("location", frame=frame, group="WorldMotion")
    walk_frames = [121, 136, 151, 166, 181, 196, 211, 226, 240]
    for index, frame in enumerate(walk_frames):
        phase = index % 4
        l = (24, 0, -24, 0)[phase]
        r = -l
        key_pose(rig, frame, {
            "LeftUpperLeg": (l, 0, 0), "RightUpperLeg": (r, 0, 0),
            "LeftLowerLeg": (max(0, -l) + 8, 0, 0), "RightLowerLeg": (max(0, -r) + 8, 0, 0),
            "LeftUpperArm": (-l * 0.72, 0, 0), "RightUpperArm": (-r * 0.72, 0, 0),
            "LeftLowerArm": (-12, 0, -5), "RightLowerArm": (-12, 0, 5),
        }, {"Hips": (0, 0, 0.015 if phase in (1, 3) else 0)})
        rig.rotation_mode = "XYZ"
        rig.rotation_euler = (0.0, 0.0, 0.0)
        rig.location = (0.0, -0.075 * index, 0.0)
        rig.keyframe_insert("rotation_euler", frame=frame, group="WorldMotion")
        rig.keyframe_insert("location", frame=frame, group="WorldMotion")
    # Keep Presentation active for rendering; export mode ACTIONS includes it.
    rig.animation_data.action = action
    action.use_fake_user = True
    mesh_obj.hide_render = False


def inspect_deformation(mesh_obj, rig) -> dict:
    depsgraph = bpy.context.evaluated_depsgraph_get()
    diagnostic = bpy.data.actions.get("DeformationTest")
    rig.animation_data.action = diagnostic
    samples = []
    baseline_extent = None
    for frame in (1, 20, 40, 60, 80):
        bpy.context.scene.frame_set(frame)
        bpy.context.view_layer.update()
        evaluated = mesh_obj.evaluated_get(depsgraph)
        positions = [evaluated.matrix_world @ vertex.co for vertex in evaluated.data.vertices]
        minimum = [min(v[i] for v in positions) for i in range(3)]
        maximum = [max(v[i] for v in positions) for i in range(3)]
        extent = [maximum[i] - minimum[i] for i in range(3)]
        if baseline_extent is None:
            baseline_extent = extent
        samples.append({
            "frame": frame,
            "min": [round(v, 6) for v in minimum],
            "max": [round(v, 6) for v in maximum],
            "extent": [round(v, 6) for v in extent],
            "ground_penetration": round(max(0.0, -1.142 - minimum[2]), 6),
        })
    rig.animation_data.action = bpy.data.actions.get("Presentation10s")
    bpy.context.scene.frame_set(1)
    return {"samples": samples, "baseline_extent": baseline_extent}


def export_glb(output_glb: Path) -> None:
    bpy.ops.object.select_all(action="DESELECT")
    mesh_obj = bpy.data.objects.get("PotatoWaistcoat")
    rig = bpy.data.objects.get("PotatoWaistcoat_ProductionRig")
    if mesh_obj is None or rig is None:
        raise RuntimeError("Character objects missing before GLB export")
    mesh_obj.select_set(True)
    rig.select_set(True)
    bpy.context.view_layer.objects.active = rig
    bpy.ops.export_scene.gltf(
        filepath=str(output_glb),
        export_format="GLB",
        use_selection=True,
        export_animations=True,
        export_animation_mode="ACTIONS",
        export_skins=True,
        export_armature_object_remove=False,
        export_morph=True,
        export_yup=True,
        export_apply=False,
        export_cameras=False,
        export_lights=False,
        export_extras=True,
    )


def encode_render(output_mp4: Path) -> None:
    frames_dir = output_mp4.parent / f".{output_mp4.stem}_frames"
    ffmpeg = Path(r"C:\Program Files\ffmpeg\bin\ffmpeg.exe")
    if not ffmpeg.is_file():
        raise RuntimeError(f"FFmpeg not found: {ffmpeg}")
    command = [
        str(ffmpeg), "-hide_banner", "-loglevel", "warning", "-y",
        "-framerate", "24", "-i", str(frames_dir / "frame_%04d.png"),
        "-c:v", "libx264", "-preset", "medium", "-crf", "18",
        "-pix_fmt", "yuv420p", "-movflags", "+faststart", str(output_mp4),
    ]
    subprocess.run(command, check=True)
    shutil.rmtree(frames_dir)


def build_report(mesh_obj, rig, clips, morphs, deformation, output_blend, output_glb, output_mp4) -> dict:
    materials = []
    images = []
    for slot in mesh_obj.material_slots:
        if slot.material:
            materials.append(slot.material.name)
            if slot.material.use_nodes:
                for node in slot.material.node_tree.nodes:
                    if node.type == "TEX_IMAGE" and node.image:
                        images.append({
                            "name": node.image.name,
                            "packed": bool(node.image.packed_file),
                            "size": list(node.image.size),
                        })
    weights = json.loads(mesh_obj.get("sbz_weight_stats", "{}"))
    remaining = []
    if weights.get("central_torso_arm_weight_max", 1) > 0.05:
        remaining.append("Central torso retains excessive arm influence.")
    if weights.get("upper_body_leg_weight_max", 1) > 0.05:
        remaining.append("Upper body retains excessive leg influence.")
    if weights.get("unweighted_vertices", 1):
        remaining.append("Some vertices were unweighted before safety assignment.")
    max_penetration = max(row["ground_penetration"] for row in deformation["samples"])
    if max_penetration > 0.03:
        remaining.append(f"Extreme bend test reaches {max_penetration:.3f}m below validation floor; visual review required.")
    return {
        "schema_version": 1,
        "character": "PotatoWaistcoat v2",
        "source": str(SOURCE),
        "source_sha256": sha256(SOURCE),
        "outputs": {
            "blend": str(output_blend), "glb": str(output_glb), "mp4": str(output_mp4),
        },
        "orientation": {"forward": "-Y", "up": "+Z", "pose": "relaxed A-pose", "ground_z": -1.142},
        "armatures": [{"name": rig.name, "bone_count": len(rig.data.bones)}],
        "bones": [bone.name for bone in rig.data.bones],
        "hierarchy": {bone.name: bone.parent.name if bone.parent else None for bone in rig.data.bones},
        "meshes": [{"name": mesh_obj.name, "vertices": len(mesh_obj.data.vertices), "polygons": len(mesh_obj.data.polygons)}],
        "materials": materials,
        "textures": images,
        "morph_targets": morphs,
        "animation_clips": clips,
        "weights": weights,
        "deformation_test": deformation,
        "known_limitations": [
            "The source is a single stylised low-detail mesh; fingers and toe bones are not present.",
            "LeftEye and RightEye are non-deform look-at controls because the source eye cards are fused visually to the head.",
            "Blink morphs are conservative spatial corrections and should be reviewed before close-up shots.",
            "Walk is a short authored test cycle, not motion-capture locomotion.",
        ],
        "remaining_deformation_problems": remaining,
        "status": "PASS_AUTOMATED" if not remaining else "NEEDS_VISUAL_REVIEW",
    }


def main() -> None:
    values = args()
    if len(values) != 4:
        raise SystemExit("Expected output.blend output.glb output.mp4 report.json")
    output_blend, output_glb, output_mp4, report_path = [Path(v).resolve() for v in values]
    for path in (output_blend, output_glb, output_mp4, report_path):
        path.parent.mkdir(parents=True, exist_ok=True)
    if SOURCE == output_blend:
        raise RuntimeError("Refusing to overwrite source blend")

    meshes = [obj for obj in bpy.context.scene.objects if obj.type == "MESH"]
    if len(meshes) != 1:
        raise RuntimeError(f"Expected one source mesh, found {len(meshes)}")
    mesh_obj = meshes[0]
    mesh_obj.name = "PotatoWaistcoat"
    mesh_obj.data.name = "PotatoWaistcoatMesh"
    # Preserve the source's legacy armature-object offset before deleting that
    # parent. This is critical: without baking it, the feet float by 0.189845m.
    source_world = mesh_obj.matrix_world.copy()
    mesh_obj.parent = None
    mesh_obj.matrix_world = source_world
    set_active(mesh_obj)
    bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)
    legacy = cache_legacy_weights(mesh_obj)
    rig = create_rig(mesh_obj, legacy)
    morphs = add_shape_keys(mesh_obj, legacy)
    clips = create_actions(rig)
    setup_render_scene(mesh_obj, rig, output_mp4)
    deformation = inspect_deformation(mesh_obj, rig)

    bpy.context.scene["sbz_character_type"] = "PRODUCTION_HUMANOID"
    bpy.context.scene["sbz_source_file"] = str(SOURCE)
    bpy.context.scene["sbz_original_preserved"] = True
    bpy.context.scene.frame_set(1)
    bpy.ops.wm.save_as_mainfile(filepath=str(output_blend))
    export_glb(output_glb)
    report = build_report(mesh_obj, rig, clips, morphs, deformation, output_blend, output_glb, output_mp4)
    report_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
    if os.environ.get("SBZ_PREFLIGHT") == "1":
        frames_dir = output_mp4.parent / f".{output_mp4.stem}_frames"
        for frame in (1, 31, 61, 91, 121, 151, 181, 211, 240):
            bpy.context.scene.frame_set(frame)
            bpy.context.scene.render.filepath = str(frames_dir / f"preflight_{frame:04d}.png")
            bpy.ops.render.render(write_still=True)
            print(f"PREFLIGHT_FRAME={frame}", flush=True)
    else:
        bpy.ops.render.render(animation=True)
        encode_render(output_mp4)
    print("POTATO_PRODUCTION_OK " + json.dumps({"blend": str(output_blend), "glb": str(output_glb), "mp4": str(output_mp4), "report": str(report_path)}), flush=True)


if __name__ == "__main__":
    main()
