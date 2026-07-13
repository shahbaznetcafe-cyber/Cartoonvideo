"""Har FBX ka T-pose thumbnail render (character pehchanne ke liye)."""
import bpy, sys, os, math, mathutils

args = sys.argv[sys.argv.index("--")+1:]
OUT = args[0]
fbx_list = args[1:]
os.makedirs(OUT, exist_ok=True)

def clear():
    bpy.ops.wm.read_factory_settings(use_empty=True)

for idx, fbx in enumerate(fbx_list, 1):
    clear()
    try:
        bpy.ops.import_scene.fbx(filepath=fbx, automatic_bone_orientation=True)
    except Exception as e:
        print(f"THUMB {idx} FAIL {e}", flush=True); continue
    meshes = [o for o in bpy.context.scene.objects if o.type=='MESH']
    if not meshes:
        print(f"THUMB {idx} no mesh", flush=True); continue
    # frame 1 (T-pose)
    bpy.context.scene.frame_set(1)
    zs=[(m.matrix_world @ mathutils.Vector(c)).z for m in meshes for c in m.bound_box]
    xs=[(m.matrix_world @ mathutils.Vector(c)).x for m in meshes for c in m.bound_box]
    h=max(zs)-min(zs); cx=(max(xs)+min(xs))/2; cz=(max(zs)+min(zs))/2
    bpy.ops.object.camera_add(location=(cx, -h*1.6, cz), rotation=(math.radians(90),0,0))
    cam=bpy.context.active_object; bpy.context.scene.camera=cam
    cam.data.ortho_scale = h*1.15; cam.data.type='ORTHO'
    bpy.ops.object.light_add(type='SUN', location=(2,-4,6)); bpy.context.active_object.data.energy=4
    w=bpy.data.worlds.new("W"); bpy.context.scene.world=w; w.use_nodes=True
    w.node_tree.nodes["Background"].inputs[0].default_value=(0.9,0.9,0.92,1)
    sc=bpy.context.scene
    sc.render.engine='BLENDER_EEVEE'; sc.render.resolution_x=300; sc.render.resolution_y=450
    sc.render.image_settings.file_format='PNG'
    sc.render.filepath=os.path.join(OUT, f"thumb_{idx}.png")
    bpy.ops.render.render(write_still=True)
    print(f"THUMB {idx} OK meshes={[m.name for m in meshes]} h={h:.2f}", flush=True)
print("ALL_THUMBS_DONE", flush=True)
