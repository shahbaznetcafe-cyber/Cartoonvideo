"""Test: rigged character ko 3D environment (glb) mein place + framing dekho."""
import bpy, sys, os, math, mathutils

def arg(i, d=None):
    a = sys.argv[sys.argv.index("--")+1:]
    return a[i] if i < len(a) else d

BLEND = arg(0); ENV = arg(1); OUT = arg(2)
os.makedirs(OUT, exist_ok=True)

bpy.ops.wm.open_mainfile(filepath=BLEND)
rig = bpy.data.objects.get("Rig"); char = bpy.data.objects.get("Char")

# --- environment import ---
before = set(bpy.context.scene.objects)
bpy.ops.import_scene.gltf(filepath=ENV)
env_objs = [o for o in bpy.context.scene.objects if o not in before]
# env bbox
allv = []
for o in env_objs:
    if o.type == 'MESH':
        allv += [o.matrix_world @ mathutils.Vector(c) for c in o.bound_box]
if allv:
    exs = [v.x for v in allv]; eys = [v.y for v in allv]; ezs = [v.z for v in allv]
    esize = max(max(exs)-min(exs), max(eys)-min(eys), max(ezs)-min(ezs))
    escale = 7.0 / (esize or 1.0)
    # ek empty parent bana kar sab env ko scale/move
    for o in env_objs:
        if o.parent is None:
            o.scale = (o.scale[0]*escale, o.scale[1]*escale, o.scale[2]*escale)
    bpy.context.view_layer.update()
    allv = []
    for o in env_objs:
        if o.type == 'MESH':
            allv += [o.matrix_world @ mathutils.Vector(c) for c in o.bound_box]
    ezs = [v.z for v in allv]; exs=[v.x for v in allv]; eys=[v.y for v in allv]
    floor = min(ezs); env_cx=(min(exs)+max(exs))/2; env_cy=(min(eys)+max(eys))/2
else:
    floor = 0; env_cx=0; env_cy=0

# --- character: scale + floor par khada ---
cv = [char.matrix_world @ mathutils.Vector(c) for c in char.bound_box]
ch_h = max(v.z for v in cv) - min(v.z for v in cv)
target_h = 0.85
cs = target_h / ch_h
rig.scale = (cs, cs, cs)
bpy.context.view_layer.update()
cv = [char.matrix_world @ mathutils.Vector(c) for c in char.bound_box]
cbot = min(v.z for v in cv); cz_off = floor - cbot
rig.location = (env_cx, env_cy + 0.3, rig.location.z + cz_off + 0.02)   # room center
bpy.context.view_layer.update()

# --- camera: OPEN side (+Y) se andar dekho, thoda door + wide (kitchen dikhe) ---
sc = bpy.context.scene
bpy.ops.object.camera_add(location=(env_cx, env_cy + 4.3, floor + target_h*1.3),
                          rotation=(math.radians(83), 0, math.radians(180)))
cam = bpy.context.active_object; sc.camera = cam; cam.data.lens = 30
bpy.ops.object.light_add(type='SUN', location=(3,-4,8)); bpy.context.active_object.data.energy=3.0
bpy.ops.object.light_add(type='AREA', location=(0,-4,4)); bpy.context.active_object.data.energy=400
w=bpy.data.worlds.new("W"); sc.world=w; w.use_nodes=True
w.node_tree.nodes["Background"].inputs[0].default_value=(0.5,0.55,0.6,1)
sc.render.engine='BLENDER_EEVEE'; sc.render.resolution_x=960; sc.render.resolution_y=540
try: sc.eevee.taa_render_samples=24
except: pass
sc.render.image_settings.file_format='PNG'; sc.render.filepath=os.path.join(OUT,"scene.png")
sc.frame_set(1)
bpy.ops.render.render(write_still=True)
print(f"ENV_SCENE floor={floor:.2f} ch_scale={cs:.2f} -> {OUT}", flush=True)
