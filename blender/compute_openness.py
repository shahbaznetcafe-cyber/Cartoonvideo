"""Audio -> per-frame mouth openness (0..1) -> json. Jaw lip-sync ke liye.
Tier 1: edge-tts word timestamps (<audio>.words.json) mile to speech-gated;
warna energy-threshold fallback. lipsync.openness_track dono handle karta."""
import sys, json, os
sys.path.insert(0, r"D:\flayer\sbz-studio")
import lipsync

audio = sys.argv[1]; fps = int(sys.argv[2]); out = sys.argv[3]
words = audio + ".words.json"
words = words if os.path.exists(words) else None

vals, n = lipsync.openness_track(audio, fps=fps, words_path=words)
json.dump({"fps": fps, "n": n, "values": vals,
           "src": os.path.basename(audio), "mode": ("words" if words else "energy")},
          open(out, "w"))
print(f"OPENNESS_DONE {n} frames ({'words' if words else 'energy'}) -> {out}", flush=True)
