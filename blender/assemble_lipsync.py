"""
Headless: Mixamo body + AI 3D head + JAW-BONE lip-sync (real 3D mouth open/close from audio).
Jaw = head ka lower-front hissa, audio openness se rotate. Peeche dark mouth-interior.

Run: blender --background --python assemble_lipsync.py -- <body.fbx> <head.glb> <out_dir> <openness.json> [flimit] [mult] [offz]
"""
import bpy, sys, os, math, json
import mathutils

def arg(i, d=None):
    a = sys.argv[sys.argv.index("--")+1:]
    return a[i] if i < len(a) else d

BODY = arg(0); HEAD_GLB = arg(1); OUT = arg(2); OPEN_JSON = arg(3)
FLIMIT = int(arg(4) or 0); SIZE_MULT = float(arg(5) or 1.0); OFF_Z = float(arg(6) or 0.12)
os.makedirs(OUT, exist_ok=True)

bpy.ops.wm.read_factory_settings(use_empty=True)

# --- body ---
bpy.ops.import_scene.fbx(filepath=BODY, automatic_bone_orientation=True)
body_arm = next(o for o in bpy.context.scene.objects if o.type=='ARMATURE')
body_meshes = [o for o in bpy.context.scene.objects if o.type=='MESH']
hb = next((b.name for b in body_arm.pose.bones if 'head' in b.name.lower() and 'top' not in b.name.lower()), None)
zs=[(m.matrix_world @ mathutils.Vector(c)).z for m in body_meshes for c in m.bound_box]
ch_h = max(zs)-min(zs)

# --- head glb ---
before=set(bpy.context.scene.objects)
bpy.ops.import_scene.gltf(filepath=HEAD_GLB)
new=[o for o in bpy.context.scene.objects if o not in before]
hmesh=[o for o in new if o.type=='MESH']
bpy.ops.object.select_all(action='DESELECT')
for m in hmesh: m.select_set(True)
bpy.context.view_layer.objects.active=hmesh[0]
if len(hmesh)>1: bpy.ops.object.join()
head=bpy.context.view_layer.objects.active; head.name="FruitHead3D"
head.parent=None
bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)
bpy.ops.object.select_all(action='DESELECT'); head.select_set(True)
bpy.context.view_layer.objects.active=head
bpy.ops.object.origin_set(type='ORIGIN_GEOMETRY', center='BOUNDS')

# scale (width) + orient + place at head bone
target_w = ch_h * 0.27 * SIZE_MULT
s = target_w / (head.dimensions.x or 1.0)
head.scale=(s,s,s); bpy.ops.object.transform_apply(scale=True)
head_h = head.dimensions.z
head.rotation_euler=(math.radians(90),0,0)
bpy.ops.object.transform_apply(rotation=True)
bone = body_arm.pose.bones[hb]
wpos = body_arm.matrix_world @ bone.head
head.location = wpos + mathutils.Vector((0,0,head_h*OFF_Z))
bpy.context.view_layer.update()

# --- head world bbox (mouth region) ---
bb=[head.matrix_world @ mathutils.Vector(c) for c in head.bound_box]
xs=[v.x for v in bb]; ys=[v.y for v in bb]; zs2=[v.z for v in bb]
cx=(min(xs)+max(xs))/2; cy=(min(ys)+max(ys))/2
bot=min(zs2); top=max(zs2); h=top-bot; front=min(ys)
hinge_z = bot + h*0.42
mouth_z = bot + h*0.28

# --- head armature (root + jaw) ---
bpy.ops.object.armature_add(location=(cx, cy, hinge_z))
hrig=bpy.context.active_object; hrig.name="HeadRig"
bpy.ops.object.mode_set(mode='EDIT')
ebs=hrig.data.edit_bones
root=ebs[0]; root.name="root"; root.head=(cx,cy,hinge_z); root.tail=(cx,cy,top)
jaw=ebs.new("jaw"); jaw.head=(cx, cy, hinge_z); jaw.tail=(cx, front, bot+h*0.12); jaw.parent=root
bpy.ops.object.mode_set(mode='OBJECT')

# --- weights: lower-front verts -> jaw, baqi -> root ---
vg_root=head.vertex_groups.new(name="root"); vg_jaw=head.vertex_groups.new(name="jaw")
mw=head.matrix_world
band = h*0.16     # sirf mouth ke qareeb chhota band
for v in head.data.vertices:
    wv=mw @ v.co
    wj=0.0
    dz = mouth_z - wv.z                       # mouth se neeche (lower lip/chin)
    front = (cy - wv.y)/(h*0.5)               # front (-Y) -> zyada, back -> 0
    if -h*0.05 < dz < band and front > 0:     # sirf mouth-neeche front area
        wj = (1.0 - min(1.0, max(0.0, dz)/band)) * min(1.0, front*1.4)
    vg_jaw.add([v.index], wj, 'REPLACE')
    vg_root.add([v.index], 1.0-wj, 'REPLACE')

md=head.modifiers.new("arm", 'ARMATURE'); md.object=hrig
head.parent=hrig
head.matrix_parent_inverse = hrig.matrix_world.inverted()   # world position preserve (jump na ho)

# (mouth interior sphere abhi off — pehle sirf jaw deform test)

# --- head-rig ko body head bone follow karao ---
c=hrig.constraints.new('CHILD_OF'); c.target=body_arm; c.subtarget=hb
c.inverse_matrix=(body_arm.matrix_world @ bone.matrix).inverted()

# --- jaw animation from openness ---
od=json.load(open(OPEN_JSON)); vals=od["values"]; nv=len(vals)
sc=bpy.context.scene
end = sc.frame_end
if FLIMIT>0: end=min(end, sc.frame_start+FLIMIT-1)
pj=hrig.pose.bones["jaw"]
pj.rotation_mode='XYZ'
for f in range(sc.frame_start, end+1):
    op = vals[(f-1) % nv] if nv else 0.0
    ang = -0.13 * min(1.0, op*1.6)   # openness -> jaw halka neeche (~7.5deg max, subtle)
    pj.rotation_euler = (ang, 0, 0)
    pj.keyframe_insert("rotation_euler", frame=f)

print(f"LIPSYNC_RIG bone={hb} target_w={target_w:.2f} hinge_z={hinge_z:.2f} openness={nv}", flush=True)

# --- scene + render ---
bpy.ops.object.camera_add(location=(0,-ch_h*2.3, min(zs)+ch_h*0.6), rotation=(math.radians(88),0,0))
sc.camera=bpy.context.active_object
bpy.ops.object.light_add(type='SUN', location=(3,-4,8)); bpy.context.active_object.data.energy=3.5
bpy.ops.object.light_add(type='AREA', location=(-3,-3,4)); bpy.context.active_object.data.energy=300
w=bpy.data.worlds.new("W"); sc.world=w; w.use_nodes=True
w.node_tree.nodes["Background"].inputs[0].default_value=(0.55,0.62,0.72,1)
sc.render.engine='BLENDER_EEVEE'
sc.render.resolution_x=720; sc.render.resolution_y=900
try: sc.eevee.taa_render_samples=8
except: pass
sc.render.image_settings.file_format='PNG'
sc.render.filepath=os.path.join(OUT,"frame_")
sc.frame_end=end
import time; t0=time.time()
bpy.ops.render.render(animation=True)
print(f"RENDER_DONE {end-sc.frame_start+1} frames in {time.time()-t0:.1f}s -> {OUT}", flush=True)
