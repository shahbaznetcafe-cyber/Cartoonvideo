"""POC: headless Blender se ek animated 3D character (placeholder) render -> PNG frames."""
import bpy, sys, math, os

out_dir = sys.argv[-1]  # last arg = output dir
os.makedirs(out_dir, exist_ok=True)

# clean scene
bpy.ops.wm.read_factory_settings(use_empty=True)
scene = bpy.context.scene

# --- simple "character": body (cylinder) + head (sphere, fruit-ish) ---
bpy.ops.mesh.primitive_uv_sphere_add(radius=1.0, location=(0, 0, 2.2))
head = bpy.context.active_object
bpy.ops.mesh.primitive_cylinder_add(radius=0.7, depth=2.2, location=(0, 0, 0.9))
body = bpy.context.active_object

# color materials
def mat(obj, rgba):
    m = bpy.data.materials.new("m"); m.use_nodes = True
    m.node_tree.nodes["Principled BSDF"].inputs["Base Color"].default_value = rgba
    obj.data.materials.append(m)
mat(head, (0.9, 0.55, 0.1, 1))   # orange head
mat(body, (0.8, 0.72, 0.5, 1))   # beige body

# --- animation: gentle bob + rotate (talk-like) over 48 frames ---
scene.frame_start = 1; scene.frame_end = 48
for f in range(1, 49):
    t = (f - 1) / 48.0
    head.location.z = 2.2 + 0.08 * math.sin(t * math.pi * 4)
    head.rotation_euler.z = 0.15 * math.sin(t * math.pi * 2)
    head.keyframe_insert("location", frame=f)
    head.keyframe_insert("rotation_euler", frame=f)

# camera + light
bpy.ops.object.camera_add(location=(0, -7, 2.2), rotation=(math.radians(85), 0, 0))
scene.camera = bpy.context.active_object
bpy.ops.object.light_add(type='SUN', location=(3, -3, 6)); bpy.context.active_object.data.energy = 4
world = bpy.data.worlds.new("W"); scene.world = world
world.use_nodes = True
world.node_tree.nodes["Background"].inputs[0].default_value = (0.5, 0.7, 0.9, 1)

# --- render (Eevee, fast) ---
scene.render.engine = 'BLENDER_EEVEE'
scene.render.resolution_x = 640; scene.render.resolution_y = 360
scene.render.image_settings.file_format = 'PNG'
scene.render.filepath = os.path.join(out_dir, "frame_")
import time; t0 = time.time()
bpy.ops.render.render(animation=True)
print(f"RENDER_DONE {48} frames in {time.time()-t0:.1f}s")
