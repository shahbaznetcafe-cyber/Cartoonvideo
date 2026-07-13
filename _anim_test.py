import sys, time
sys.stdout.reconfigure(encoding="utf-8")
import video_gen
t0=time.time()
prompt=("cartoon potato character gently gesturing and looking around, subtle natural body "
        "movement, breathing, slight camera push in, market background alive, cinematic")
out="projects/cine-test/_anim_scene1.mp4"
video_gen.animate_character("projects/cine-test/scenes/scene_1.png", prompt, 5, out,
                            on_progress=lambda s: print(f"  status: {s} ({int(time.time()-t0)}s)", flush=True))
print(f"DONE in {int(time.time()-t0)}s -> {out}")
