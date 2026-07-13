"""
Headless assembly: Mixamo rigged body (FBX) + AI 3D head (GLB) -> animated 3D character.
3D head Head-bone se parent hota hai -> jism ke saath 3D mein ghoomta/hilta (flat nahi).

Run: blender --background --python assemble_character.py -- <body.fbx> <head.glb> <out_dir> [frame_limit]
"""
import bpy, sys, os, math
import mathutils

def arg(i, d=None):
    a = sys.argv[sys.argv.index("--")+1:]
    return a[i] if i < len(a) else d

BODY = arg(0); HEAD_GLB = arg(1); OUT = arg(2); FLIMIT = int(arg(3) or 0)
SIZE_MULT = float(arg(4) or 1.0)   # per-fruit size tweak
OFF_Z = float(arg(5)) if arg(5) else 0.12   # vertical offset (head_h ka fraction) — face align
FACE_SEQ = arg(6)                  # optional: 2D animated face frames dir (lip-sync + expression)


def apply_face_projection(head, seq_dir):
    """2D animated face (image sequence) ko 3D head ke front par project — lip-sync + facial."""
    import glob
    frames = sorted(glob.glob(os.path.join(seq_dir, "face_*.png")))
    if not frames:
        return
    img = bpy.data.images.load(frames[0]); img.source = 'SEQUENCE'
    mat = bpy.data.materials.new("faceproj"); mat.use_nodes = True
    nt = mat.node_tree; nt.nodes.clear()
    out = nt.nodes.new("ShaderNodeOutputMaterial")
    bsdf = nt.nodes.new("ShaderNodeBsdfPrincipled"); bsdf.inputs["Roughness"].default_value = 0.6
    tc = nt.nodes.new("ShaderNodeTexCoord")
    sep = nt.nodes.new("ShaderNodeSeparateXYZ")
    comb = nt.nodes.new("ShaderNodeCombineXYZ")
    tex = nt.nodes.new("ShaderNodeTexImage"); tex.image = img; tex.extension = 'CLIP'
    tex.image_user.frame_duration = len(frames)
    tex.image_user.frame_start = 1
    tex.image_user.use_cyclic = True
    tex.image_user.use_auto_refresh = True
    mapn = nt.nodes.new("ShaderNodeMapping")           # aspect/fit tweak
    mapn.inputs["Location"].default_value = (0.5, 0.5, 0.0)
    mapn.inputs["Scale"].default_value = (1.15, 1.05, 1.0)
    # transparent jagah -> brown potato base (kaala nahi)
    brown = nt.nodes.new("ShaderNodeRGB"); brown.outputs[0].default_value = (0.62, 0.46, 0.26, 1)
    mix = nt.nodes.new("ShaderNodeMixRGB")
    L = nt.links
    L.new(tc.outputs["Generated"], sep.inputs["Vector"])
    L.new(sep.outputs["X"], comb.inputs["X"])
    L.new(sep.outputs["Z"], comb.inputs["Y"])
    # center karo: (v-0.5)*scale+0.5
    subn = nt.nodes.new("ShaderNodeVectorMath"); subn.operation = 'SUBTRACT'
    subn.inputs[1].default_value = (0.5, 0.5, 0.0)
    L.new(comb.outputs["Vector"], subn.inputs[0])
    L.new(subn.outputs["Vector"], mapn.inputs["Vector"])
    L.new(mapn.outputs["Vector"], tex.inputs["Vector"])
    L.new(brown.outputs[0], mix.inputs["Color1"])
    L.new(tex.outputs["Color"], mix.inputs["Color2"])
    L.new(tex.outputs["Alpha"], mix.inputs["Fac"])     # face alpha -> blend
    L.new(mix.outputs["Color"], bsdf.inputs["Base Color"])
    L.new(bsdf.outputs["BSDF"], out.inputs["Surface"])
    head.data.materials.clear(); head.data.materials.append(mat)
    print(f"FACE_PROJ_APPLIED {len(frames)} frames", flush=True)
os.makedirs(OUT, exist_ok=True)

bpy.ops.wm.read_factory_settings(use_empty=True)

# --- body (Mixamo) ---
bpy.ops.import_scene.fbx(filepath=BODY, automatic_bone_orientation=True)
arm = next(o for o in bpy.context.scene.objects if o.type=='ARMATURE')
body_meshes = [o for o in bpy.context.scene.objects if o.type=='MESH']
# head bone
hb = next((b.name for b in arm.pose.bones if 'head' in b.name.lower() and 'top' not in b.name.lower()), None)
# char height
zs=[(m.matrix_world @ mathutils.Vector(c)).z for m in body_meshes for c in m.bound_box]
ch_h = max(zs)-min(zs)

# --- AI head (glb) ---
before = set(bpy.context.scene.objects)
bpy.ops.import_scene.gltf(filepath=HEAD_GLB)
new = [o for o in bpy.context.scene.objects if o not in before]
head_meshes = [o for o in new if o.type=='MESH']
# sabko ek object mein join
bpy.ops.object.select_all(action='DESELECT')
for m in head_meshes: m.select_set(True)
bpy.context.view_layer.objects.active = head_meshes[0]
if len(head_meshes) > 1:
    bpy.ops.object.join()
head = bpy.context.view_layer.objects.active
head.name = "FruitHead3D"
head.parent = None
bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)
# origin ko geometry center par
bpy.ops.object.select_all(action='DESELECT'); head.select_set(True)
bpy.context.view_layer.objects.active = head
bpy.ops.object.origin_set(type='ORIGIN_GEOMETRY', center='BOUNDS')

# WIDTH ke hisab se scale -> har head insaani sar ki chaudai dhaanp le (bara taake baal chhupein)
target_w = ch_h * 0.27 * SIZE_MULT
s = target_w / (head.dimensions.x or 1.0)
head.scale = (s, s, s)
bpy.ops.object.transform_apply(scale=True)
head_h = head.dimensions.z   # scale ke baad head ki height

# head bone (base) ki world position
bone = arm.pose.bones[hb]
wpos = arm.matrix_world @ bone.head
head.rotation_euler = (math.radians(90), 0, 0)   # gltf front -> camera (-Y) ki taraf
# head center ko human sar par baithao (thoda upar bone se, taake neck bhi cover ho)
head.location = wpos + mathutils.Vector((0, 0, head_h * OFF_Z))
bpy.context.view_layer.update()

# CHILD_OF constraint -> head bone follow (3D mein ghoomta, flat nahi)
c = head.constraints.new('CHILD_OF')
c.target = arm; c.subtarget = hb
c.inverse_matrix = (arm.matrix_world @ bone.matrix).inverted()

print(f"HEAD_PLACED bone={hb} char_h={ch_h:.2f} target_w={target_w:.2f} scale={s:.3f} head_h={head_h:.2f}", flush=True)

if FACE_SEQ:
    apply_face_projection(head, FACE_SEQ)

# --- scene: camera + lights + bg ---
top=max(zs); bot=min(zs)
bpy.ops.object.camera_add(location=(0, -ch_h*2.3, bot+ch_h*0.6),
                          rotation=(math.radians(88),0,0))
bpy.context.scene.camera = bpy.context.active_object
bpy.ops.object.light_add(type='SUN', location=(3,-4,8)); bpy.context.active_object.data.energy=3.5
bpy.ops.object.light_add(type='AREA', location=(-3,-3,4)); bpy.context.active_object.data.energy=300
w=bpy.data.worlds.new("W"); bpy.context.scene.world=w; w.use_nodes=True
w.node_tree.nodes["Background"].inputs[0].default_value=(0.55,0.62,0.72,1)

# --- render (K620 par tez: kam samples + light Eevee) ---
sc=bpy.context.scene
sc.render.engine='BLENDER_EEVEE'
sc.render.resolution_x=720; sc.render.resolution_y=900
# SPEED: Eevee render samples kam (default 64 -> 8) = ~kaafi tez, quality thodi kam
try:
    sc.eevee.taa_render_samples = 8
except Exception:
    pass
# mehnge effects draft mein off
for attr, val in (("use_gtao", False), ("use_ssr", False), ("use_bloom", False),
                  ("use_shadow_high_bitdepth", False)):
    try: setattr(sc.eevee, attr, val)
    except Exception: pass
sc.render.image_settings.file_format='PNG'
sc.render.filepath=os.path.join(OUT,"frame_")
if FLIMIT>0:
    sc.frame_end=min(sc.frame_end, sc.frame_start+FLIMIT-1)
import time; t0=time.time()
bpy.ops.render.render(animation=True)
n=sc.frame_end-sc.frame_start+1
print(f"RENDER_DONE {n} frames in {time.time()-t0:.1f}s -> {OUT}", flush=True)
