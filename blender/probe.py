import bpy, sys
p = sys.argv[sys.argv.index("--")+1]
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.fbx(filepath=p, automatic_bone_orientation=True)
arm=[o for o in bpy.context.scene.objects if o.type=='ARMATURE']
mesh=[o for o in bpy.context.scene.objects if o.type=='MESH']
sc=bpy.context.scene
print("ARMATURES", len(arm), [a.name for a in arm])
print("MESHES", len(mesh), [m.name for m in mesh])
print("FRAMES", sc.frame_start, sc.frame_end)
if arm:
    bones=list(arm[0].pose.bones.keys())
    print("NBONES", len(bones))
    print("HEADBONE", [b for b in bones if 'head' in b.lower()][:3])
    print("SAMPLE", bones[:4])
