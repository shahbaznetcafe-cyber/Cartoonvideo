"""
Blender headless render — Mixamo rigged character + fruit head -> animated frames.
Chalao:  blender --background --python render_character.py -- <char.fbx> <head_img.png> <out_dir> [bg_img]

Mixamo FBX: armature + skinned mesh + baked animation. Bones "mixamorig:Head" etc.
Hum fruit head (image plane / textured sphere) ko Head bone se parent karte hain (follow kare).
"""
import bpy
import sys
import os
import math


def arg(i, default=None):
    a = sys.argv[sys.argv.index("--") + 1:]
    return a[i] if i < len(a) else default


CHAR_FBX = arg(0)
HEAD_IMG = arg(1)
OUT_DIR = arg(2)
BG_IMG = arg(3)
FRAME_LIMIT = int(arg(4) or 0)   # >0 -> sirf itne frames (fast test)

os.makedirs(OUT_DIR, exist_ok=True)


def clean():
    bpy.ops.wm.read_factory_settings(use_empty=True)


def import_character(path):
    bpy.ops.import_scene.fbx(filepath=path, automatic_bone_orientation=True)
    arm = next((o for o in bpy.context.scene.objects if o.type == "ARMATURE"), None)
    meshes = [o for o in bpy.context.scene.objects if o.type == "MESH"]
    return arm, meshes


def find_head_bone(arm):
    for cand in ("mixamorig:Head", "mixamorig1:Head", "Head", "head"):
        if cand in arm.pose.bones:
            return cand
    # fallback: koi bhi "head" wala
    for b in arm.pose.bones:
        if "head" in b.name.lower():
            return b.name
    return None


def add_fruit_head(arm, head_bone, img_path, char_h):
    """
    Fruit head = camera-facing textured plane jo Head bone ki location follow kare
    (Copy-Location constraint). Size character height ke mutabiq. Insaani sar ko dhaanp le.
    """
    if not (head_bone and img_path and os.path.exists(img_path)):
        print("HEAD_SKIP: img/bone missing", flush=True)
        return None
    img = bpy.data.images.load(img_path)
    ar = img.size[0] / img.size[1] if img.size[1] else 1.0
    size = max(0.2, char_h * 0.36)          # bara -> insaani sar poora dhaanp le

    bpy.ops.mesh.primitive_plane_add(size=1.0)
    plane = bpy.context.active_object
    plane.name = "FruitHead"
    plane.rotation_euler = (math.radians(90), 0, 0)   # camera (-Y) ki taraf khada
    plane.scale = (size * ar, size, size)

    mat = bpy.data.materials.new("head"); mat.use_nodes = True
    nt = mat.node_tree
    bsdf = nt.nodes["Principled BSDF"]
    tex = nt.nodes.new("ShaderNodeTexImage"); tex.image = img
    nt.links.new(tex.outputs["Color"], bsdf.inputs["Base Color"])
    nt.links.new(tex.outputs["Alpha"], bsdf.inputs["Alpha"])
    # Eevee-Next alpha
    try:
        mat.surface_render_method = 'DITHERED'
    except Exception:
        pass
    mat.use_backface_culling = False
    plane.data.materials.append(mat)

    # head bone location follow (rotation inherit nahi -> camera-facing rehta).
    # use_offset=True -> plane.location target ke upar offset ki tarah add hoti hai.
    c = plane.constraints.new('COPY_LOCATION')
    c.target = arm
    c.subtarget = head_bone
    c.use_offset = True
    plane.location = (0, -size * 0.55, size * 0.12)   # camera ki taraf aage (human sar ke saamne)
    print(f"HEAD_ADDED size={size:.2f} ar={ar:.2f}", flush=True)
    return plane


def char_height(meshes):
    import mathutils
    zs = [(m.matrix_world @ mathutils.Vector(c)).z for m in meshes for c in m.bound_box]
    return (max(zs) - min(zs)) if zs else 1.8, (min(zs) if zs else 0.0), (max(zs) if zs else 1.8)


def setup_scene(arm, meshes, bg_img):
    scene = bpy.context.scene
    h, bot, top = char_height(meshes)
    cx = 0.0
    cam_z = bot + h * 0.55
    dist = h * 2.2 + 1.0
    bpy.ops.object.camera_add(location=(cx, -dist, cam_z),
                              rotation=(math.radians(90), 0, 0))
    scene.camera = bpy.context.active_object

    bpy.ops.object.light_add(type='SUN', location=(3, -4, 8))
    bpy.context.active_object.data.energy = 3.5
    bpy.ops.object.light_add(type='AREA', location=(-3, -3, 4))
    bpy.context.active_object.data.energy = 200

    world = bpy.data.worlds.new("W"); scene.world = world; world.use_nodes = True
    bg = world.node_tree.nodes["Background"]
    if bg_img and os.path.exists(bg_img):
        env = world.node_tree.nodes.new("ShaderNodeTexEnvironment")
        env.image = bpy.data.images.load(bg_img)
        world.node_tree.links.new(env.outputs["Color"], bg.inputs["Color"])
    else:
        bg.inputs[0].default_value = (0.55, 0.72, 0.9, 1)


def render(out_dir):
    scene = bpy.context.scene
    scene.render.engine = 'BLENDER_EEVEE'
    scene.render.resolution_x = 1280
    scene.render.resolution_y = 720
    scene.render.image_settings.file_format = 'PNG'
    scene.render.filepath = os.path.join(out_dir, "frame_")
    # agar animation na ho to frame range 1..48 default
    if scene.frame_end <= scene.frame_start:
        scene.frame_start, scene.frame_end = 1, 48
    if FRAME_LIMIT > 0:   # fast test: sirf itne frames
        scene.frame_end = min(scene.frame_end, scene.frame_start + FRAME_LIMIT - 1)
    import time
    t0 = time.time()
    bpy.ops.render.render(animation=True)
    n = scene.frame_end - scene.frame_start + 1
    print(f"RENDER_DONE {n} frames in {time.time()-t0:.1f}s -> {out_dir}", flush=True)


def main():
    clean()
    arm, meshes = import_character(CHAR_FBX)
    if not arm:
        print("ERROR: armature nahi mili FBX mein"); return
    hb = find_head_bone(arm)
    ch, _, _ = char_height(meshes)
    print(f"armature: {arm.name} | head bone: {hb} | meshes: {len(meshes)} | "
          f"char_height: {ch:.2f} | frames: {bpy.context.scene.frame_start}-"
          f"{bpy.context.scene.frame_end}", flush=True)
    add_fruit_head(arm, hb, HEAD_IMG, ch)
    setup_scene(arm, meshes, BG_IMG)
    render(OUT_DIR)


main()
