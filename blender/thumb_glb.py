"""Har full3d glb ka front thumbnail (library dekhne ke liye)."""
import bpy, sys, os, math, mathutils

args = sys.argv[sys.argv.index("--")+1:]
OUT = args[0]; glbs = args[1:]
os.makedirs(OUT, exist_ok=True)

for glb in glbs:
    bpy.ops.wm.read_factory_settings(use_empty=True)
    name = os.path.splitext(os.path.basename(glb))[0].replace("_full", "")
    try:
        bpy.ops.import_scene.gltf(filepath=glb)
    except Exception as e:
        print(f"THUMB {name} FAIL {e}", flush=True); continue
    meshes = [o for o in bpy.context.scene.objects if o.type == 'MESH']
    if not meshes:
        continue
    verts = [m.matrix_world @ v.co for m in meshes for v in m.data.vertices]
    xs = [v.x for v in verts]; zs = [v.z for v in verts]; ys = [v.y for v in verts]
    cx = (min(xs)+max(xs))/2; cz = (min(zs)+max(zs))/2; H = max(zs)-min(zs)
    bpy.ops.object.camera_add(location=(cx, min(ys)-H*1.6, cz), rotation=(math.radians(90),0,0))
    cam = bpy.context.active_object; bpy.context.scene.camera = cam
    cam.data.type = 'ORTHO'; cam.data.ortho_scale = H*1.25
    bpy.ops.object.light_add(type='SUN', location=(2,-4,6)); bpy.context.active_object.data.energy=3.5
    bpy.ops.object.light_add(type='AREA', location=(-3,-3,4)); bpy.context.active_object.data.energy=200
    w = bpy.data.worlds.new("W"); bpy.context.scene.world = w; w.use_nodes = True
    w.node_tree.nodes["Background"].inputs[0].default_value = (0.9,0.9,0.92,1)
    sc = bpy.context.scene
    sc.render.engine = 'BLENDER_EEVEE'
    sc.render.resolution_x = 300; sc.render.resolution_y = 360
    try: sc.eevee.taa_render_samples = 16
    except: pass
    sc.render.image_settings.file_format = 'PNG'
    sc.render.filepath = os.path.join(OUT, f"{name}.png")
    bpy.ops.render.render(write_still=True)
    print(f"THUMB {name} OK", flush=True)
print("THUMBS_DONE", flush=True)
