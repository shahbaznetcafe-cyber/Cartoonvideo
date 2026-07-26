"""
Multi-character 3D scene render: ek hi frame mein 2-3 rigged characters saath.
Bolne wala (speaking) = jaw lip-sync + active gestures; baaki = idle (saans/halki sway).
Sab ek 3D environment mein, camera dono/teeno ko frame karta.

Run: blender --background --python animate_scene.py -- <spec.json>
spec.json = {
  "out": dir, "flimit": 0, "fps": 24, "res": "960x540", "env": glb_path_or_"",
  "chars": [ {"blend":path, "openness":path_or_"", "emotion":"happy", "speaking":true,
              "slot":0}, ... ]   # slot 0..n-1 left->right
}
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

spec_path = sys.argv[sys.argv.index("--")+1:][0]
spec = json.load(open(spec_path, encoding="utf-8"))
OUT = spec["out"]; FLIMIT = int(spec.get("flimit", 0))
FPS = int(spec.get("fps", 24)); RES = spec.get("res", "960x540")
ENV_GLB = spec.get("env") or ""
CHARS = spec["chars"]
SHOT = spec.get("shot", "wide")          # wide | medium | closeup (camera direction)
FOCUS = int(spec.get("focus", 0))        # kis slot par focus (bolne wala)
EXPOSURE = float(spec.get("exposure", -0.2))   # style-look ki exposure
NC = len(CHARS)
os.makedirs(OUT, exist_ok=True)

bpy.ops.wm.read_factory_settings(use_empty=True)
sc = bpy.context.scene


def append_char(blendpath):
    """Rig + Char ek doosre blend se append karo (parent + armature ref preserve)."""
    with bpy.data.libraries.load(blendpath, link=False) as (df, dt):
        dt.objects = [n for n in df.objects if n in ("Rig", "Char")]
    rig = char = None
    for obj in dt.objects:
        if obj is None:
            continue
        sc.collection.objects.link(obj)
        if obj.type == 'ARMATURE':
            rig = obj
        elif obj.type == 'MESH':
            char = obj
    return rig, char


# ---------- environment ----------
floor = 0.0; env_cx = 0.0; env_cy = 0.0; Wr = 7.0
if ENV_GLB and os.path.exists(ENV_GLB):
    before = set(sc.objects)
    bpy.ops.import_scene.gltf(filepath=ENV_GLB)
    env_objs = [o for o in sc.objects if o not in before]
    av = [o.matrix_world @ mathutils.Vector(c) for o in env_objs if o.type == 'MESH' for c in o.bound_box]
    if av:
        exs = [v.x for v in av]; eys = [v.y for v in av]; ezs = [v.z for v in av]
        esize = max(max(exs)-min(exs), max(eys)-min(eys), max(ezs)-min(ezs))
        escale = 7.0/(esize or 1.0)
        for o in env_objs:
            if o.parent is None:
                o.scale = tuple(sv*escale for sv in o.scale)
        bpy.context.view_layer.update()
        av = [o.matrix_world @ mathutils.Vector(c) for o in env_objs if o.type == 'MESH' for c in o.bound_box]
        ezs = [v.z for v in av]; exs = [v.x for v in av]; eys = [v.y for v in av]
        floor = min(ezs); env_cx = (min(exs)+max(exs))/2; env_cy = (min(eys)+max(eys))/2
        Wr = max(exs)-min(exs)

# ---------- load + place characters ----------
TH = 1.5                       # char target height (m)
SPACING = 1.55                 # do characters ke beech faasla (m)
loaded = []
for c in CHARS:
    rig, char = append_char(c["blend"])
    if not rig or not char:
        print(f"SKIP {c['blend']} (no rig/char)", flush=True)
        continue
    # costume (Tier 1): texture par color/palette
    if costumes and c.get("costume"):
        try:
            costumes.apply(char, c["costume"])
        except Exception as ex:
            print(f"costume fail {c.get('costume')}: {ex}", flush=True)
    # accessory (Tier 2): worn prop (head/face) — rig se parent, transform follow
    if accessories and c.get("accessory"):
        try:
            accessories.build(char, rig, c["accessory"])
        except Exception as ex:
            print(f"accessory fail {c.get('accessory')}: {ex}", flush=True)
    # held item (hand) — arm_R bone se parent (gesture ke saath chale)
    if accessories and c.get("held"):
        try:
            accessories.build(char, rig, c["held"])
        except Exception as ex:
            print(f"held fail {c.get('held')}: {ex}", flush=True)
    # scale to target height
    cvv = [char.matrix_world @ mathutils.Vector(v) for v in char.bound_box]
    ch_h = max(v.z for v in cvv) - min(v.z for v in cvv)
    cs = TH/(ch_h or 1.0)
    rig.scale = (cs, cs, cs); bpy.context.view_layer.update()
    # floor par khada + slot x offset (center around env_cx)
    slot = int(c.get("slot", 0))
    xoff = (slot - (NC-1)/2.0) * SPACING
    cvv = [char.matrix_world @ mathutils.Vector(v) for v in char.bound_box]
    cbot = min(v.z for v in cvv)
    rig.location = (env_cx + xoff, env_cy + 0.6, rig.location.z + (floor-cbot) + 0.045)
    # camera (+Y) ki taraf mooh
    rig.rotation_euler = (rig.rotation_euler.x, rig.rotation_euler.y,
                          rig.rotation_euler.z + math.radians(180))
    bpy.context.view_layer.update()

    # openness values (speaker) warna zeros
    vals = [0.0]; nv = 1
    op_path = c.get("openness") or ""
    if c.get("speaking") and op_path and os.path.exists(op_path):
        od = json.load(open(op_path)); vals = od.get("values", [0.0]) or [0.0]; nv = len(vals)

    def pb(name, _rig=rig):
        b = _rig.pose.bones.get(name)
        if b:
            b.rotation_mode = 'XYZ'
        return b

    loaded.append({
        "rig": rig, "char": char, "vals": vals, "nv": nv,
        "speaking": bool(c.get("speaking")), "emo": (c.get("emotion") or "neutral").lower(),
        "jaw": pb("jaw"), "aL": pb("arm_L"), "aR": pb("arm_R"), "body": pb("body"),
        "phase": slot * 1.3,   # har char ka gesture phase alag (natural)
    })

if not loaded:
    print("NO_CHARS"); sys.exit(1)

# frame count = max openness length (ya speaker ki), FLIMIT se cap
nmax = max(d["nv"] for d in loaded)
n = nmax if FLIMIT <= 0 else min(nmax, FLIMIT)
sc.frame_start = 1; sc.frame_end = n


def smooth_op(vals, nv, idx):
    lo = max(0, idx-2); hi = min(nv, idx+3)
    return sum(vals[i % nv] for i in range(lo, hi)) / (hi-lo)


def emphasis(t):
    ph = (t % 2.5)/2.5
    return math.sin(ph*math.pi) ** 3


# ---------- animate ----------
for f in range(1, n+1):
    t = (f-1)/FPS
    for d in loaded:
        rig = d["rig"]; char = d["char"]; ph = d["phase"]
        speaking = d["speaking"]
        angry = d["emo"] in ("angry", "sad")
        if speaking:
            op = smooth_op(d["vals"], d["nv"], min(f-1, d["nv"]-1))
            amp = 20 if angry else 12; freq = 2.4 if angry else 1.7
        else:
            op = 0.0                      # listener: mooh band
            amp = 4.5; freq = 1.0         # halki idle harkat
        em = emphasis(t + ph) if speaking else 0.0
        jaw = d["jaw"]; aL = d["aL"]; aR = d["aR"]; body = d["body"]
        if jaw:
            jaw.rotation_euler = (-0.14*min(1.0, op*1.6), 0, math.radians(2*math.sin((t+ph)*3.1)))
            jaw.keyframe_insert("rotation_euler", frame=f)
        if aL:
            g = amp*(0.6*math.sin((t+ph)*freq) + 0.4*math.sin((t+ph)*0.7+1.0)) + op*14 + em*16
            aL.rotation_euler = (math.radians(op*8), 0, math.radians(g))
            aL.keyframe_insert("rotation_euler", frame=f)
        if aR:
            g = -amp*(0.6*math.sin((t+ph)*freq+0.7) + 0.4*math.sin((t+ph)*0.6)) - op*14 - em*16
            aR.rotation_euler = (math.radians(op*8), 0, math.radians(g))
            aR.keyframe_insert("rotation_euler", frame=f)
        if body:
            body.location = (0.006*math.sin((t+ph)*0.9), 0, 0.012*math.sin((t+ph)*2.1))
            body.rotation_euler = (math.radians(op*2.5), 0, math.radians(2.5*math.sin((t+ph)*0.55) + em*2))
            body.keyframe_insert("location", frame=f)
            body.keyframe_insert("rotation_euler", frame=f)
        # squash-stretch (breathing + talk bounce) — char rig se scaled hai, ye local squash
        sy = 1.0 + 0.018*math.sin((t+ph)*1.4) - op*0.045
        sxz = 1.0 + (1.0-sy)*0.6
        char.scale = (sxz, sxz, sy)
        char.keyframe_insert("scale", frame=f)

print(f"SCENE_KEYED {n} frames, {len(loaded)} chars", flush=True)

# ---------- camera DIRECTION (shot variety + Track-To aim + push-in) ----------
RX, RY = (int(x) for x in RES.lower().split("x"))
scene_w = (NC-1)*SPACING + 1.6
char_y = env_cy + 0.6
focus_x = env_cx + (FOCUS - (NC-1)/2.0)*SPACING     # bolne wale ki x

# shot -> (cam_x, distance(+Y), height, lens, aim_x, aim_z_frac, push_in)
if SHOT == "closeup":
    cam_x = focus_x; dist = 2.05; height = floor + TH*1.1; lens = 56
    aim_x = focus_x; aim_z = floor + TH*0.8; push = 0.92
elif SHOT == "medium":
    cam_x = focus_x; dist = 2.55; height = floor + TH*1.02; lens = 52
    aim_x = focus_x; aim_z = floor + TH*0.66; push = 0.94
else:  # wide (establishing) — sab characters
    cam_x = env_cx; dist = 3.4 + scene_w*0.62; height = floor + TH*1.02; lens = 40 if NC >= 2 else 46
    aim_x = env_cx; aim_z = floor + TH*0.6; push = 0.97

# aim empty + Track-To (pitch/yaw auto)
bpy.ops.object.empty_add(location=(aim_x, char_y, aim_z))
aim = bpy.context.active_object; aim.name = "AimTarget"
bpy.ops.object.camera_add(location=(cam_x, char_y + dist, height))
cam = bpy.context.active_object; sc.camera = cam; cam.data.lens = lens
con = cam.constraints.new('TRACK_TO'); con.target = aim
con.track_axis = 'TRACK_NEGATIVE_Z'; con.up_axis = 'UP_Y'
# subtle push-in (dolly): shuru thoda door, aakhir thoda nazdeek -> zindagi
cam.location = (cam_x, char_y + dist, height); cam.keyframe_insert("location", frame=1)
cam.location = (cam_x, char_y + dist*push, height + TH*(1-push)*0.3); cam.keyframe_insert("location", frame=max(2, n))

# LIGHTING — balanced (pehle overexposed/washed-out tha): key + soft fill, kam energy
key = None
bpy.ops.object.light_add(type='SUN', location=(3, -4, 8))
key = bpy.context.active_object; key.data.energy = 2.3; key.data.angle = math.radians(15)
try: key.data.color = (1.0, 0.97, 0.9)          # halka warm key
except Exception: pass
bpy.ops.object.light_add(type='AREA', location=(env_cx - 2, env_cy + 2.5, floor + 3))
fill = bpy.context.active_object; fill.data.energy = 130; fill.data.size = 6
try: fill.data.color = (0.85, 0.9, 1.0)         # thoda cool fill (shadows soft)
except Exception: pass
w = bpy.data.worlds.new("W"); sc.world = w; w.use_nodes = True
w.node_tree.nodes["Background"].inputs[0].default_value = (0.62, 0.74, 0.86, 1)
w.node_tree.nodes["Background"].inputs[1].default_value = 0.55   # ambient kam -> contrast/rang wapas
sc.render.film_transparent = False

sc.render.engine = 'BLENDER_EEVEE'; sc.render.resolution_x = RX; sc.render.resolution_y = RY
try: sc.eevee.taa_render_samples = 8
except Exception: pass
# COLOR — exposure thoda neeche (overexposure recover). Saturation/contrast ffmpeg mein
# (blender3d line-clip encode par eq=...) — Blender 5.1 compositor API flaky.
try:
    sc.view_settings.view_transform = 'Standard'   # Filmic desaturate karta -> Standard
    sc.view_settings.exposure = EXPOSURE           # style-look se
except Exception:
    pass
sc.render.image_settings.file_format = 'PNG'; sc.render.image_settings.color_mode = 'RGBA'
sc.render.filepath = os.path.join(OUT, "frame_")
import time; t0 = time.time()
bpy.ops.render.render(animation=True)
print(f"RENDER_DONE {n} frames in {time.time()-t0:.1f}s -> {OUT}", flush=True)
