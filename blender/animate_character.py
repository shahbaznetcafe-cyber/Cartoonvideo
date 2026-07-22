"""
Rigged character (.blend) ko animate karo: jaw lip-sync (audio openness) + arm gestures + body bob.
Render frames. (audio mux baahar ffmpeg se.)

Run: blender --background --python animate_character.py -- <char.blend> <openness.json> <out_dir> [flimit] [emotion]
"""
import bpy, sys, os, math, json
import mathutils
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))  # BASE_DIR
try:
    import costumes
except Exception:
    costumes = None
try:
    import accessories
except Exception:
    accessories = None

def arg(i, d=None):
    a = sys.argv[sys.argv.index("--")+1:]
    return a[i] if i < len(a) else d

BLEND = arg(0); OPEN_JSON = arg(1); OUT = arg(2)
FLIMIT = int(arg(3) or 0); EMO = (arg(4) or "neutral").lower()
BG_IMG = arg(5)                 # optional scene background image (2D backdrop)
RES = arg(6) or "600x700"       # output resolution WxH
ENV_GLB = arg(7)                # optional 3D environment glb (character us scene mein khada)
COSTUME = arg(8)                # optional costume preset (color/palette)
ACCESSORY = arg(9)              # optional worn accessory (head/face)
HELD = arg(10)                  # optional hand item (sword/wand/mic...)
os.makedirs(OUT, exist_ok=True)

bpy.ops.wm.open_mainfile(filepath=BLEND)
rig = bpy.data.objects.get("Rig")
char = bpy.data.objects.get("Char")
if not rig:
    print("NO_RIG"); sys.exit(1)
if costumes and COSTUME:
    try: costumes.apply(char, COSTUME)
    except Exception as ex: print(f"costume fail: {ex}", flush=True)
if accessories and ACCESSORY:
    try: accessories.build(char, rig, ACCESSORY)
    except Exception as ex: print(f"accessory fail: {ex}", flush=True)
if accessories and HELD:
    try: accessories.build(char, rig, HELD)
    except Exception as ex: print(f"held fail: {ex}", flush=True)

od = json.load(open(OPEN_JSON)); vals = od["values"]; nv = len(vals); fps = od.get("fps", 30)
sc = bpy.context.scene
sc.frame_start = 1
n = nv if FLIMIT <= 0 else min(nv, FLIMIT)
sc.frame_end = n

angry = EMO in ("angry", "sad")
amp = 20 if angry else 12          # base arm gesture degrees
freq = 2.4 if angry else 1.7

def pb(name):
    b = rig.pose.bones.get(name)
    if b: b.rotation_mode = 'XYZ'
    return b

jaw = pb("jaw"); aL = pb("arm_L"); aR = pb("arm_R"); body = pb("body")

def smooth_op(idx):
    """openness ko smooth karo -> jaw jitter na kare (moving average)."""
    lo = max(0, idx-2); hi = min(nv, idx+3)
    return sum(vals[i % nv] for i in range(lo, hi)) / (hi-lo)

def emphasis(t):
    """har ~2.5s halka anticipation+emphasis beat (point banana)."""
    ph = (t % 2.5) / 2.5
    return math.sin(ph*math.pi) ** 3   # 0..1 pulse, ease

for f in range(1, n+1):
    t = (f-1)/fps
    op = smooth_op(f-1)
    em = emphasis(t)
    # jaw lip-sync (smooth) + halki jaw sway
    if jaw:
        jaw.rotation_euler = (-0.14*min(1.0, op*1.6), 0, math.radians(2*math.sin(t*3.1)))
        jaw.keyframe_insert("rotation_euler", frame=f)
    # arms: LAYERED sine (varied) + speech emphasis + emphasis beat, dono baazu alag phase (overlap)
    if aL:
        g = amp*(0.6*math.sin(t*freq) + 0.4*math.sin(t*0.7+1.0)) + op*14 + em*16
        aL.rotation_euler = (math.radians(op*8), 0, math.radians(g))          # thoda upar-neeche bhi
        aL.keyframe_insert("rotation_euler", frame=f)
    if aR:
        g = -amp*(0.6*math.sin(t*freq+0.7) + 0.4*math.sin(t*0.6)) - op*14 - em*16
        aR.rotation_euler = (math.radians(op*8), 0, math.radians(g))
        aR.keyframe_insert("rotation_euler", frame=f)
    # body: sway + bob + halka forward lean jab bol raha
    if body:
        body.location = (0.006*math.sin(t*0.9), 0, 0.012*math.sin(t*2.1))
        body.rotation_euler = (math.radians(op*2.5), 0, math.radians(2.5*math.sin(t*0.55) + em*2))
        body.keyframe_insert("location", frame=f)
        body.keyframe_insert("rotation_euler", frame=f)
    # CHAR squash-stretch: breathing + talking bounce (cartoon principle)
    if char:
        sy = 1.0 + 0.018*math.sin(t*1.4) - op*0.045          # bolte waqt halka squash (height)
        sxz = 1.0 + (1.0-sy)*0.6                              # volume conserve (chaudai)
        char.scale = (sxz, sxz, sy)
        char.keyframe_insert("scale", frame=f)

print(f"ANIM_KEYED {n} frames emo={EMO} (polished)", flush=True)

# resolution
RX, RY = (int(x) for x in RES.lower().split("x"))
verts = [char.matrix_world @ v.co for v in char.data.vertices]
zs=[v.z for v in verts]; ys=[v.y for v in verts]; xs=[v.x for v in verts]
cx=(min(xs)+max(xs))/2; cz=(min(zs)+max(zs))/2; H=max(zs)-min(zs); cyy=(min(ys)+max(ys))/2

bpy.ops.object.light_add(type='SUN', location=(3,-4,8)); bpy.context.active_object.data.energy=3.5
bpy.ops.object.light_add(type='AREA', location=(-3,-3,4)); bpy.context.active_object.data.energy=250
w=bpy.data.worlds.new("W"); sc.world=w; w.use_nodes=True
w.node_tree.nodes["Background"].inputs[0].default_value=(0.55,0.62,0.72,1)

if ENV_GLB and os.path.exists(ENV_GLB):
    # 3D ENVIRONMENT: character ko scene mein khada karo (Sketchfab glb)
    before=set(bpy.context.scene.objects)
    bpy.ops.import_scene.gltf(filepath=ENV_GLB)
    env_objs=[o for o in bpy.context.scene.objects if o not in before]
    av=[o.matrix_world @ mathutils.Vector(c) for o in env_objs if o.type=='MESH' for c in o.bound_box]
    if av:
        exs=[v.x for v in av]; eys=[v.y for v in av]; ezs=[v.z for v in av]
        esize=max(max(exs)-min(exs), max(eys)-min(eys), max(ezs)-min(ezs))
        escale=7.0/(esize or 1.0)
        for o in env_objs:
            if o.parent is None: o.scale=tuple(sv*escale for sv in o.scale)
        bpy.context.view_layer.update()
        av=[o.matrix_world @ mathutils.Vector(c) for o in env_objs if o.type=='MESH' for c in o.bound_box]
        ezs=[v.z for v in av]; exs=[v.x for v in av]; eys=[v.y for v in av]
        floor=min(ezs); env_cx=(min(exs)+max(exs))/2; env_cy=(min(eys)+max(eys))/2
        Wr=max(exs)-min(exs); Hr=max(ezs)-floor
    else:
        floor=0; env_cx=0; env_cy=0; Wr=7; Hr=4
    # char scale (rig par) + floor par khada — bada rakho taake frame bhare
    cvv=[char.matrix_world @ mathutils.Vector(c) for c in char.bound_box]
    ch_h=max(v.z for v in cvv)-min(v.z for v in cvv); th=1.5; cs=th/ch_h
    rig.scale=(cs,cs,cs); bpy.context.view_layer.update()
    cvv=[char.matrix_world @ mathutils.Vector(c) for c in char.bound_box]
    cbot=min(v.z for v in cvv)
    rig.location=(env_cx, env_cy+0.6, rig.location.z + (floor-cbot) + 0.045)
    # character ko camera (+Y) ki taraf mooh karo (Sketchfab/Rodin front -Y hota hai)
    rig.rotation_euler = (rig.rotation_euler.x, rig.rotation_euler.y,
                          rig.rotation_euler.z + math.radians(180))
    bpy.context.view_layer.update()
    # perspective camera: nazdeek + character ke upper-body par aim (kam sky/grey)
    cam_y = env_cy + 3.0; cam_z = floor + th*0.95
    bpy.ops.object.camera_add(location=(env_cx, cam_y, cam_z))
    cam=bpy.context.active_object; sc.camera=cam; cam.data.lens=50
    # character center par point karo: Z=180 (mooh -Y taraf), X=90+downtilt
    tgt_z = floor + th*0.62
    dy = cam_y - (env_cy+0.6); dz = cam_z - tgt_z   # dz>0 => camera upar => neeche dekho
    cam.rotation_euler = (math.radians(90) - math.atan2(dz, dy), 0, math.radians(180))
    bpy.ops.object.light_add(type='AREA', location=(env_cx, env_cy+3, floor+3)); bpy.context.active_object.data.energy=500
    # world bg: halka sky-blue (stark grey ki jagah) -> professional aasman
    w.node_tree.nodes["Background"].inputs[0].default_value=(0.53,0.71,0.88,1)
    sc.render.film_transparent=False
elif BG_IMG and os.path.exists(BG_IMG):
    # SCENE mode: character neeche (ground par), peeche bg backdrop plane, poora frame
    cam_z = cz - H*0.05
    bpy.ops.object.camera_add(location=(cx, cyy-H*2.4, cam_z), rotation=(math.radians(90),0,0))
    cam=bpy.context.active_object; sc.camera=cam; cam.data.type='ORTHO'; cam.data.ortho_scale=H*2.6
    # backdrop plane peeche
    bpy.ops.mesh.primitive_plane_add(size=H*8, location=(cx, cyy+H*2.5, cz))
    bd=bpy.context.active_object; bd.rotation_euler=(math.radians(90),0,0)
    img=bpy.data.images.load(BG_IMG)
    m=bpy.data.materials.new("bg"); m.use_nodes=True
    nt=m.node_tree; bsdf=nt.nodes["Principled BSDF"]
    tx=nt.nodes.new("ShaderNodeTexImage"); tx.image=img
    nt.links.new(tx.outputs["Color"], bsdf.inputs["Base Color"])
    bsdf.inputs["Roughness"].default_value=1.0
    try: bsdf.inputs["Emission Color"].default_value=(1,1,1,1); bsdf.inputs["Emission Strength"].default_value=0.6
    except Exception: pass
    bd.data.materials.append(m)
    sc.render.film_transparent=False
else:
    # portrait/solo mode: tight framing, halka bg
    bpy.ops.object.camera_add(location=(cx, cyy-H*1.7, cz), rotation=(math.radians(90),0,0))
    cam=bpy.context.active_object; sc.camera=cam; cam.data.type='ORTHO'; cam.data.ortho_scale=H*1.5

sc.render.engine='BLENDER_EEVEE'; sc.render.resolution_x=RX; sc.render.resolution_y=RY
try: sc.eevee.taa_render_samples=6
except: pass
sc.render.image_settings.file_format='PNG'
sc.render.image_settings.color_mode='RGBA'
sc.render.filepath=os.path.join(OUT,"frame_")
import time; t0=time.time()
bpy.ops.render.render(animation=True)
print(f"RENDER_DONE {n} frames in {time.time()-t0:.1f}s -> {OUT}", flush=True)
