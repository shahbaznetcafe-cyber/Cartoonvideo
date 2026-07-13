"""
Sab full3d characters ko auto-rig (body + arms + legs + jaw) + manual weights.
Har ek: rigged .blend save + test-pose thumbnail (limbs+jaw move confirm).

Run: blender --background --python rig_all.py -- <out_dir> <glb1> <glb2> ...
"""
import bpy, sys, os, math
import mathutils

args = sys.argv[sys.argv.index("--")+1:]
OUT = args[0]; GLBS = args[1:]
os.makedirs(OUT, exist_ok=True)
BLENDS = os.path.join(OUT, "blend"); os.makedirs(BLENDS, exist_ok=True)


def rig_one(glb):
    name = os.path.splitext(os.path.basename(glb))[0].replace("_full", "")
    bpy.ops.wm.read_factory_settings(use_empty=True)
    before = set(bpy.context.scene.objects)
    bpy.ops.import_scene.gltf(filepath=glb)
    meshes = [o for o in bpy.context.scene.objects if o.type == 'MESH' and o not in before]
    if not meshes:
        print(f"RIG {name} no-mesh", flush=True); return None
    bpy.ops.object.select_all(action='DESELECT')
    for m in meshes: m.select_set(True)
    bpy.context.view_layer.objects.active = meshes[0]
    if len(meshes) > 1: bpy.ops.object.join()
    char = bpy.context.view_layer.objects.active; char.name = "Char"
    char.parent = None
    bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)
    bpy.ops.object.origin_set(type='ORIGIN_GEOMETRY', center='BOUNDS')
    char.location = (0, 0, 0); bpy.context.view_layer.update()

    verts = [char.matrix_world @ v.co for v in char.data.vertices]
    xs = [v.x for v in verts]; ys = [v.y for v in verts]; zs = [v.z for v in verts]
    minx, maxx = min(xs), max(xs); miny, maxy = min(ys), max(ys); minz, maxz = min(zs), max(zs)
    cx = (minx+maxx)/2; cy = (miny+maxy)/2; H = maxz-minz; Wd = maxx-minx

    def extreme(pred, key):
        best = None; bv = None
        for v in verts:
            if pred(v):
                k = key(v)
                if bv is None or k > bv: bv = k; best = v
        return best or mathutils.Vector((cx, cy, minz))

    leg_top = minz + H*0.28
    arm_l = extreme(lambda v: v.z > leg_top, lambda v: -v.x)
    arm_r = extreme(lambda v: v.z > leg_top, lambda v: v.x)
    leg_l = extreme(lambda v: v.z < leg_top and v.x < cx, lambda v: -v.z)
    leg_r = extreme(lambda v: v.z < leg_top and v.x > cx, lambda v: -v.z)
    mouth_z = minz + H*0.42; front = miny

    # armature
    bpy.ops.object.armature_add(location=(cx, cy, minz+H*0.4))
    arm = bpy.context.active_object; arm.name = "Rig"
    bpy.ops.object.mode_set(mode='EDIT')
    ebs = arm.data.edit_bones
    root = ebs[0]; root.name = "body"; root.head = (cx, cy, minz+H*0.2); root.tail = (cx, cy, maxz)
    def mk(n, h, t): b = ebs.new(n); b.head = h; b.tail = t; b.parent = root; return b
    mk("arm_L", (cx-Wd*0.2, cy, minz+H*0.55), (arm_l.x, arm_l.y, arm_l.z))
    mk("arm_R", (cx+Wd*0.2, cy, minz+H*0.55), (arm_r.x, arm_r.y, arm_r.z))
    mk("leg_L", (cx-Wd*0.12, cy, leg_top), (leg_l.x, leg_l.y, leg_l.z))
    mk("leg_R", (cx+Wd*0.12, cy, leg_top), (leg_r.x, leg_r.y, leg_r.z))
    mk("jaw", (cx, cy, mouth_z+H*0.06), (cx, front, mouth_z-H*0.06))
    bpy.ops.object.mode_set(mode='OBJECT')

    # manual weights
    vg = {n: char.vertex_groups.new(name=n) for n in ("body","arm_L","arm_R","leg_L","leg_R","jaw")}
    mw = char.matrix_world; arm_x = Wd*0.30; soft = Wd*0.10; band = H*0.14
    for v in char.data.vertices:
        p = mw @ v.co
        w = {k: 0.0 for k in vg}
        if p.z < leg_top:                                  # legs
            (("leg_L" if p.x < cx else "leg_R"),)
            k = "leg_L" if p.x < cx else "leg_R"
            w[k] = min(1.0, (leg_top-p.z)/soft + 0.4)
        elif p.x < cx - arm_x:                             # left arm
            w["arm_L"] = min(1.0, (cx-arm_x-p.x)/soft + 0.3)
        elif p.x > cx + arm_x:                             # right arm
            w["arm_R"] = min(1.0, (p.x-(cx+arm_x))/soft + 0.3)
        else:                                              # jaw: front-lower mouth
            dz = mouth_z - p.z
            fr = (cy - p.y)/(H*0.5)
            if -H*0.04 < dz < band and fr > 0:
                w["jaw"] = (1.0 - min(1.0, max(0.0, dz)/band)) * min(1.0, fr*1.3)
        w["body"] = max(0.0, 1.0 - sum(w.values()))
        for n, wv in w.items():
            if wv > 0: vg[n].add([v.index], wv, 'REPLACE')
    char.parent = arm
    md = char.modifiers.new("arm", 'ARMATURE'); md.object = arm

    # save rigged blend
    bpy.ops.wm.save_as_mainfile(filepath=os.path.join(BLENDS, f"{name}.blend"))

    # test pose (limbs up + jaw open) + thumbnail
    bpy.ops.object.mode_set(mode='POSE')
    for bn, r in (("arm_L",(0,0,math.radians(50))), ("arm_R",(0,0,math.radians(-50))),
                  ("jaw",(math.radians(-12),0,0))):
        pb = arm.pose.bones[bn]; pb.rotation_mode='XYZ'; pb.rotation_euler = r
    bpy.ops.object.mode_set(mode='OBJECT')

    sc = bpy.context.scene
    bpy.ops.object.camera_add(location=(cx, miny-H*1.6, (minz+maxz)/2), rotation=(math.radians(90),0,0))
    cam = bpy.context.active_object; sc.camera = cam; cam.data.type='ORTHO'; cam.data.ortho_scale=H*1.25
    bpy.ops.object.light_add(type='SUN', location=(2,-4,6)); bpy.context.active_object.data.energy=3.5
    bpy.ops.object.light_add(type='AREA', location=(-3,-3,4)); bpy.context.active_object.data.energy=200
    w2 = bpy.data.worlds.new("W"); sc.world = w2; w2.use_nodes = True
    w2.node_tree.nodes["Background"].inputs[0].default_value = (0.9,0.9,0.92,1)
    sc.render.engine = 'BLENDER_EEVEE'; sc.render.resolution_x=300; sc.render.resolution_y=360
    try: sc.eevee.taa_render_samples = 16
    except: pass
    sc.render.image_settings.file_format='PNG'; sc.render.filepath = os.path.join(OUT, f"{name}.png")
    bpy.ops.render.render(write_still=True)
    print(f"RIG {name} OK", flush=True)


for g in GLBS:
    try: rig_one(g)
    except Exception as e:
        print(f"RIG FAIL {os.path.basename(g)}: {e}", flush=True)
print("RIG_ALL_DONE", flush=True)
