"""
Fruit character (full 3D glb) ko auto-rig karo: body + 2 arms + 2 legs bones + auto-weights.
Test: aik arm/leg pose karke render. Phir animate ho sakta hai.

Run: blender --background --python autorig_character.py -- <char.glb> <out_dir> [test]
"""
import bpy, sys, os, math
import mathutils

def arg(i, d=None):
    a = sys.argv[sys.argv.index("--")+1:]
    return a[i] if i < len(a) else d

GLB = arg(0); OUT = arg(1); TEST = arg(2) == "test"
os.makedirs(OUT, exist_ok=True)

bpy.ops.wm.read_factory_settings(use_empty=True)

# --- import + join ---
before = set(bpy.context.scene.objects)
bpy.ops.import_scene.gltf(filepath=GLB)
new = [o for o in bpy.context.scene.objects if o not in before]
meshes = [o for o in new if o.type == 'MESH']
bpy.ops.object.select_all(action='DESELECT')
for m in meshes: m.select_set(True)
bpy.context.view_layer.objects.active = meshes[0]
if len(meshes) > 1: bpy.ops.object.join()
char = bpy.context.view_layer.objects.active; char.name = "FruitChar"
char.parent = None
bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)
bpy.ops.object.origin_set(type='ORIGIN_GEOMETRY', center='BOUNDS')
char.location = (0, 0, 0)
bpy.context.view_layer.update()

# --- mesh analyze: bbox + limb tips ---
verts = [char.matrix_world @ v.co for v in char.data.vertices]
xs = [v.x for v in verts]; ys = [v.y for v in verts]; zs = [v.z for v in verts]
minx, maxx = min(xs), max(xs); miny, maxy = min(ys), max(ys); minz, maxz = min(zs), max(zs)
cx = (minx+maxx)/2; cy = (miny+maxy)/2; cz = (minz+maxz)/2
H = maxz - minz; Wd = maxx - minx

# arm tips: sab se left/right vertex (mid-upper height)
def extreme(pred, key):
    best = None; bv = None
    for v in verts:
        if pred(v):
            k = key(v)
            if bv is None or k > bv:
                bv = k; best = v
    return best

mid_z = minz + H*0.45
arm_l = extreme(lambda v: v.z > minz+H*0.30, lambda v: -v.x)   # leftmost upper
arm_r = extreme(lambda v: v.z > minz+H*0.30, lambda v: v.x)    # rightmost upper
# leg tips: bottom, left/right of center
leg_l = extreme(lambda v: v.z < minz+H*0.30 and v.x < cx, lambda v: -(v.z))  # lowest left  (max -z)
leg_r = extreme(lambda v: v.z < minz+H*0.30 and v.x > cx, lambda v: -(v.z))  # lowest right
# body attach points (limb shoulders/hips) — center ki taraf
shoulder_z = minz + H*0.55
hip_z = minz + H*0.30

print(f"BBOX H={H:.2f} W={Wd:.2f} center=({cx:.2f},{cy:.2f},{cz:.2f})", flush=True)
print(f"arm_l={tuple(round(x,2) for x in arm_l)} arm_r={tuple(round(x,2) for x in arm_r)}", flush=True)
print(f"leg_l={tuple(round(x,2) for x in leg_l)} leg_r={tuple(round(x,2) for x in leg_r)}", flush=True)

# --- armature banao ---
bpy.ops.object.armature_add(location=(cx, cy, cz))
arm = bpy.context.active_object; arm.name = "CharRig"
bpy.ops.object.mode_set(mode='EDIT')
ebs = arm.data.edit_bones
root = ebs[0]; root.name = "body"; root.head = (cx, cy, minz+H*0.2); root.tail = (cx, cy, maxz)

def mkbone(name, head, tail):
    b = ebs.new(name); b.head = head; b.tail = tail; b.parent = root; return b

mkbone("arm_L", (cx-Wd*0.2, cy, shoulder_z), (arm_l.x, arm_l.y, arm_l.z))
mkbone("arm_R", (cx+Wd*0.2, cy, shoulder_z), (arm_r.x, arm_r.y, arm_r.z))
mkbone("leg_L", (cx-Wd*0.12, cy, hip_z), (leg_l.x, leg_l.y, leg_l.z))
mkbone("leg_R", (cx+Wd*0.12, cy, hip_z), (leg_r.x, leg_r.y, leg_r.z))
bpy.ops.object.mode_set(mode='OBJECT')

# --- manual weights: limb stubs -> apne bone (full), baqi body ---
vg = {n: char.vertex_groups.new(name=n) for n in ("body","arm_L","arm_R","leg_L","leg_R")}
mw = char.matrix_world
arm_x = Wd*0.30      # is se aage (x) = arm stub
leg_top = minz + H*0.26   # is se neeche + side = leg stub
soft = Wd*0.10       # falloff
for v in char.data.vertices:
    p = mw @ v.co
    wl = {"body":0.0,"arm_L":0.0,"arm_R":0.0,"leg_L":0.0,"leg_R":0.0}
    if p.x < cx - arm_x and p.z > leg_top:            # left arm
        wl["arm_L"] = min(1.0, (cx-arm_x - p.x)/soft + 0.3)
    elif p.x > cx + arm_x and p.z > leg_top:          # right arm
        wl["arm_R"] = min(1.0, (p.x - (cx+arm_x))/soft + 0.3)
    elif p.z < leg_top:                                # legs (bottom)
        if p.x < cx: wl["leg_L"] = min(1.0, (leg_top - p.z)/soft + 0.4)
        else:        wl["leg_R"] = min(1.0, (leg_top - p.z)/soft + 0.4)
    limbw = sum(wl.values())
    wl["body"] = max(0.0, 1.0 - limbw)
    for n, wv in wl.items():
        if wv > 0: vg[n].add([v.index], wv, 'REPLACE')
char.parent = arm
md = char.modifiers.new("arm", 'ARMATURE'); md.object = arm
print("RIGGED + manual-weights", flush=True)

if TEST:
    # pose test: dono baazu upar (cheer/wave)
    bpy.ops.object.mode_set(mode='POSE')
    import math as _m
    arm.pose.bones["arm_L"].rotation_mode='XYZ'; arm.pose.bones["arm_L"].rotation_euler=(_m.radians(-70),0,0)
    arm.pose.bones["arm_R"].rotation_mode='XYZ'; arm.pose.bones["arm_R"].rotation_euler=(_m.radians(-70),0,0)
    arm.pose.bones["leg_L"].rotation_mode='XYZ'; arm.pose.bones["leg_L"].rotation_euler=(_m.radians(30),0,0)
    bpy.ops.object.mode_set(mode='OBJECT')

# --- render (front) ---
sc = bpy.context.scene
bpy.ops.object.camera_add(location=(0, -H*2.2, cz), rotation=(math.radians(90),0,0))
sc.camera = bpy.context.active_object
bpy.ops.object.light_add(type='SUN', location=(3,-4,8)); bpy.context.active_object.data.energy=3.5
bpy.ops.object.light_add(type='AREA', location=(-3,-3,4)); bpy.context.active_object.data.energy=200
w=bpy.data.worlds.new("W"); sc.world=w; w.use_nodes=True
w.node_tree.nodes["Background"].inputs[0].default_value=(0.55,0.62,0.72,1)
sc.render.engine='BLENDER_EEVEE'
sc.render.resolution_x=500; sc.render.resolution_y=600
try: sc.eevee.taa_render_samples=16
except: pass
sc.render.image_settings.file_format='PNG'
sc.render.filepath=os.path.join(OUT,"rig_test.png")
sc.frame_set(1)
bpy.ops.render.render(write_still=True)
print(f"RENDER_DONE -> {OUT}", flush=True)
