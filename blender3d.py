"""
Blender 3D Story Mode — script se poori 3D animated video.
Har dialogue line: speaker ko rigged 3D character se map -> Blender render (bg ke saath,
jaw lip-sync + gestures) -> line mp4. Phir sab clips + music ffmpeg se jod kar final video.
"""
import json
import os
import re
import subprocess
import sys

import config
import transitions

BLENDER = r"C:\Program Files\Blender Foundation\Blender 5.1\blender.exe"
BL_DIR = os.path.join(config.BASE_DIR, "blender")
RIG_DIR = os.path.join(BL_DIR, "rigged", "blend")
VENV_PY = r"D:\flayer\veggie-tool\.venv\Scripts\python.exe"
THREEJS_RENDER_REVISION = "character-traits-clip-safety-v10"

# ---- GPU video encoding (NVENC) — ffmpeg ko CPU (libx264) ki jagah GPU par ----
_NVENC_OK = None


def _has_nvenc():
    """Ek dafa asli chhota encode chala kar confirm karo GPU (NVENC) waqai kaam karta hai
    (sirf 'encoder compiled hai' kaafi nahi — driver/GPU accept kare ye zaroori)."""
    global _NVENC_OK
    if _NVENC_OK is None:
        try:
            r = subprocess.run(
                ["ffmpeg", "-hide_banner", "-f", "lavfi", "-i", "color=c=black:s=64x64:d=0.1",
                 "-c:v", "h264_nvenc", "-f", "null", "-"],
                capture_output=True, timeout=40)
            _NVENC_OK = (r.returncode == 0)
        except Exception:
            _NVENC_OK = False
        if _NVENC_OK:
            print("  [gpu] NVENC (h264_nvenc) available — GPU encoding ON", flush=True)
    return _NVENC_OK


def _delivery_video_args(height=None, fps=30):
    """YouTube-safe H.264 metadata and bitrate guidance for SDR delivery."""
    if not height:
        return ["-profile:v", "high", "-bf", "2",
                "-color_primaries", "bt709", "-color_trc", "bt709",
                "-colorspace", "bt709"]
    rates = [(2160, 35), (1440, 16), (1080, 8), (720, 5), (0, 3)]
    mbps = next(rate for minimum, rate in rates if height >= minimum)
    if fps > 30:
        mbps = int(round(mbps * 1.5))
    return ["-profile:v", "high", "-bf", "2", "-g", str(max(12, int(fps))),
            "-b:v", f"{mbps}M", "-maxrate", f"{int(mbps * 1.5)}M",
            "-bufsize", f"{mbps * 2}M", "-color_primaries", "bt709",
            "-color_trc", "bt709", "-colorspace", "bt709"]


def _vcodec(height=None, fps=30):
    """Video encoder ffmpeg args — GPU (NVENC) agar enable+available, warna CPU libx264.
    config.GPU_ENCODE: auto|on -> GPU try, off -> hamesha CPU."""
    mode = getattr(config, "GPU_ENCODE", "auto")
    if mode != "off" and _has_nvenc():
        base = ["-c:v", "h264_nvenc", "-preset", "p5", "-rc", "vbr", "-cq", "19"]
    else:
        base = ["-c:v", "libx264", "-preset", "medium", "-crf", "18"]
    return base + _delivery_video_args(height, fps)


def _vcodec_fast(height=None, fps=30):
    """Tez intermediate encoder — line clips ke liye (final assembly se pehle).
    Quality thodi kam chalti hai (intermediate), speed maqsad hai:
    - GPU: NVENC p4 (faster than p5, still good quality)
    - CPU: libx264 ultrafast + -threads 0 (sabse fast, ~5x faster than medium)"""
    mode = getattr(config, "GPU_ENCODE", "auto")
    if mode != "off" and _has_nvenc():
        base = ["-c:v", "h264_nvenc", "-preset", "p4", "-rc", "vbr", "-cq", "22"]
    else:
        base = ["-c:v", "libx264", "-preset", "ultrafast", "-crf", "23", "-threads", "0"]
    return base + _delivery_video_args(height, fps)

# keyword -> rigged .blend basename (english + roman urdu)
CHAR_MAP = {
    "apple": "apple", "seb": "apple",
    "banana": "banana", "kela": "banana",
    "carrot": "carrot", "gajar": "carrot",
    "chili": "chili", "chilli": "chili", "mirch": "chili",
    "corn": "corn", "bhutta": "corn", "makai": "corn",
    "cucumber": "cucumber", "kheera": "cucumber",
    "eggplant": "eggplant", "baingan": "eggplant", "brinjal": "eggplant",
    "grapes": "grapes", "angoor": "grapes",
    "lemon": "lemon", "nimbu": "lemon", "neebu": "lemon",
    "mango": "mango", "aam": "mango",
    "okra": "okra", "bhindi": "okra", "ladyfinger": "okra",
    "pineapple": "pineapple", "ananas": "pineapple",
    "potato": "potato", "aloo": "potato",
    "radish": "radish", "mooli": "radish",
    "tomato": "tomato", "tamatar": "tomato",
}
_POOL = ["potato", "tomato", "apple", "banana", "carrot", "mango", "eggplant",
         "onion", "chili", "lemon", "pineapple", "cucumber", "corn", "radish", "grapes"]


def _blend(name):
    p = os.path.join(RIG_DIR, f"{name}.blend")
    return p if os.path.exists(p) else None


def _fallback_blend():
    """Speaker ka koi blend na mile (narrator/unmapped) to koi bhi maujood mascot.
    (Purana hardcoded 'potato' delete ho chuka — ab library-driven fallback.)"""
    try:
        import char3d_lib
        valid = char3d_lib.all_valid()
        if valid:
            return char3d_lib.blend_path(valid[0])
    except Exception:
        pass
    import glob as _g
    any_blend = _g.glob(os.path.join(RIG_DIR, "*.blend"))
    return any_blend[0] if any_blend else None


def assign(parsed_chars):
    """Har script character ko ek rigged 3D character do (keyword match, warna round-robin)."""
    result = {}
    used = set()
    for ch in parsed_chars:
        hay = f"{ch.get('id','')} {ch.get('name','')} {ch.get('role','')}".lower()
        pick = None
        for kw, nm in CHAR_MAP.items():
            if kw in hay and nm not in used and _blend(nm):
                pick = nm; break
        result[ch["id"]] = pick
    pi = 0
    for ch in parsed_chars:
        if not result.get(ch["id"]):
            for nm in _POOL:
                cand = _POOL[pi % len(_POOL)]; pi += 1
                if cand not in used and _blend(cand):
                    result[ch["id"]] = cand; break
            if not result.get(ch["id"]):
                result[ch["id"]] = "potato"
        used.add(result[ch["id"]])
    return result


def _openness(audio, fps, out_json):
    # CACHE: agar openness json pehle se hai, audio se naya, aur same fps -> recompute skip
    # (rerender par lip-sync dobara compute nahi hota — tez).
    try:
        if (os.path.exists(out_json) and
                os.path.getmtime(out_json) >= os.path.getmtime(audio)):
            import json as _j
            if _j.load(open(out_json)).get("fps") == fps:
                return
    except Exception:
        pass
    subprocess.run([VENV_PY, os.path.join(BL_DIR, "compute_openness.py"), audio, str(fps), out_json],
                   check=True, capture_output=True)


ENV_DIR = os.path.join(BL_DIR, "assets", "env")
_ENV_KW = {
    "market.glb": {"market", "shop", "bazaar", "stall", "store"},
    "garden.glb": {"garden", "farm", "field", "outdoor", "outside", "park",
                   "village", "playground", "courtyard", "pathway", "path", "road",
                   "forest", "jungle", "yard", "mud", "desert", "snow"},
    "kitchen.glb": {"kitchen", "home", "house", "room", "indoor", "school",
                    "classroom", "office"},
}


def _env_for(scene, preset=None):
    """Select an environment with token matching (``washroom`` is not ``room``).

    Baked env sets sirf tab load hote hain jab scene sach mein indoor/market ho.
    Baqi presets (forest/pirate/space/sunny/...) composed dressings + AI plate
    use karte hain — warna har video mein wahi garden village set aata tha.
    """
    loc = (str(scene.get("location", "")) + " " + str(scene.get("background_prompt", ""))).lower()
    tokens = set(re.findall(r"[a-z]+", loc))
    explicit = str(scene.get("environment") or "").lower().strip()
    preset = str(preset or "").lower()
    baked = {"kitchen.glb": "indoor", "market.glb": "market"}
    for f, words in _ENV_KW.items():
        p = os.path.join(ENV_DIR, f)
        if not os.path.exists(p):
            continue
        if explicit in (f, os.path.splitext(f)[0]):
            return p
        if f in baked and (preset == baked[f] or (not preset and tokens & words)):
            return p
    # Outdoor/composed presets: koi baked set nahi — procedural ground +
    # scene_assets dressings + AI background plate hi variety dete hain.
    return None


def _scene_look(scene):
    """Translate story meaning into a visible procedural scene treatment."""
    text = (str(scene.get("location", "")) + " " +
            str(scene.get("background_prompt", "")) + " " +
            str(scene.get("mood", ""))).lower()
    if any(word in text for word in ("wash", "soap", "hygiene", "cleaning station")):
        return "wash"
    if any(word in text for word in ("mud", "puddle", "slippery", "after rain")):
        return "mud"
    if any(word in text for word in ("rain", "storm", "dark cloud", "windy")):
        return "storm"
    if any(word in text for word in ("stage", "celebration", "colorful", "colourful")):
        return "stage"
    return "sunny"


def _render_line(blend, open_json, out_dir, emotion, bg, res, env, costume="", accessory="", held=""):
    subprocess.run([BLENDER, "--background", "--python", os.path.join(BL_DIR, "animate_character.py"),
                    "--", blend, open_json, out_dir, "0", emotion, bg or "", res, env or "",
                    costume or "", accessory or "", held or ""],
                   check=True, capture_output=True)


MAX_SCENE_CHARS = 3


def _cast_with_speaker(cast, speaker, limit=MAX_SCENE_CHARS):
    """Keep a stable ensemble while guaranteeing that the current speaker is visible."""
    result = []
    for cid in cast:
        if cid and cid not in result:
            result.append(cid)
    if speaker not in result:
        result = result[:max(0, limit - 1)] + [speaker]
    return result[:limit]


def _scene_casts(timeline, assignment):
    """Har scene ke characters (order-of-appearance, max 3) -> stable slots."""
    casts = {}
    for e in timeline:
        sid = e.get("scene")
        spk = e.get("speaker")
        if not assignment.get(spk):        # blend nahi (e.g. narrator) -> skip
            continue
        lst = casts.setdefault(sid, [])
        if spk not in lst and len(lst) < MAX_SCENE_CHARS:
            lst.append(spk)
    return casts


class Cancelled(Exception):
    """User ne generation STOP kiya."""


def _run_blender(args, should_cancel=None):
    """Blender subprocess — beech mein STOP ho to process kill + Cancelled raise."""
    import time as _t
    p = subprocess.Popen(args, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    while p.poll() is None:
        if should_cancel and should_cancel():
            p.terminate()
            try:
                p.wait(timeout=5)
            except Exception:
                p.kill()
            raise Cancelled()
        _t.sleep(0.4)
    if p.returncode != 0:
        raise subprocess.CalledProcessError(p.returncode, args)


def _render_scene_line(spec, out_dir, should_cancel=None):
    """Multi-character scene render (animate_scene.py)."""
    import json as _json
    spec_path = os.path.join(out_dir + "_spec.json")
    _json.dump(spec, open(spec_path, "w", encoding="utf-8"))
    _run_blender([BLENDER, "--background", "--python", os.path.join(BL_DIR, "animate_scene.py"),
                  "--", spec_path], should_cancel)


# ---- Three.js (headless Chrome WebGL) render engine — Blender ka ~35x tez alternative ----
TJ_DIR = os.path.join(config.BASE_DIR, "threejs_render")
NODE = os.getenv("NODE_EXE", "node")


def _run_node(args, cwd, should_cancel=None):
    """Node subprocess — beech mein STOP ho to kill + Cancelled raise (Blender jaisa)."""
    import time as _t
    p = subprocess.Popen(args, cwd=cwd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                         text=True, encoding="utf-8", errors="replace")
    out = []
    while p.poll() is None:
        if should_cancel and should_cancel():
            p.terminate()
            try:
                p.wait(timeout=5)
            except Exception:
                p.kill()
            raise Cancelled()
        _t.sleep(0.3)
    rest = p.stdout.read() if p.stdout else ""
    if rest:
        out.append(rest)
    log = "".join(out)
    if p.returncode != 0 or "SCENE_ERROR" in log:
        raise subprocess.CalledProcessError(p.returncode or 1, args, output=log)


def _render_scene_line_threejs(spec, out_dir, should_cancel=None):
    """Multi-character scene render via Three.js/headless Chrome (render_scene.js).
    render_scene.js khud blend->glb slug karta + env basename leta, isliye Blender wala
    hi spec chalta. Frames frame_%04d.png (same naming) -> baaki pipeline unchanged."""
    import json as _json
    spec_path = os.path.join(out_dir + "_spec.json")
    _json.dump(spec, open(spec_path, "w", encoding="utf-8"))
    _run_node([NODE, "render_scene.js", spec_path], TJ_DIR, should_cancel)


def _line_action(e, cast, spk, parsed):
    """Line ka speaker action + target slot. actions.py se detect; target = doosra cast
    member (agar naam line mein mention ho to wahi, warna pehla doosra char)."""
    try:
        import actions
    except Exception:
        return "none", -1
    text = e.get("text", "") or ""
    stage_action = e.get("action", "") or ""
    normalized_action = re.sub(r"[^a-z_]+", "_", str(stage_action).lower()).strip("_")
    action = (normalized_action if normalized_action in getattr(actions, "SUPPORTED_ACTIONS", ())
              else actions.detect(f"{stage_action} {text}", e.get("emotion", "neutral")))
    others = [i for i, cid in enumerate(cast) if cid != spk]
    if not others or not actions.needs_target(action):
        return action, -1
    tgt = others[0]
    if actions.needs_target(action):
        low = text.lower()
        chars_by = {c["id"]: c for c in parsed.get("characters", [])}
        for i in others:
            nm = str(chars_by.get(cast[i], {}).get("name", "")).lower()
            if nm and nm in low:
                tgt = i
                break
    return action, tgt


def _apply_character_action_safety(timeline, assignment, proj_dir):
    """Normalize only impossible Quaternius actions before frame rendering."""
    report = []
    try:
        import character_traits
        for entry in timeline:
            speaker = entry.get("speaker")
            blend = assignment.get(speaker)
            if not blend or _character_runtime_metadata(blend).get("library") != "quaternius":
                continue
            requested = str(entry.get("action") or "idle")
            directive = character_traits.render_directive(blend, requested)
            entry["character_traits"] = directive.get("traits", {})
            entry["source_clip"] = directive.get("sourceClip", "")
            if not directive.get("actionSupported"):
                entry["action"] = directive.get("action", "idle")
                entry["action_safety_note"] = (
                    f"Requested '{requested}' is not a real clip on this character; "
                    f"using '{entry['action']}' with {directive.get('traits', {}).get('form', 'safe')} staging.")
            report.append({"speaker": speaker, "requested_action": requested,
                           "render_action": entry.get("action"),
                           "source_clip": directive.get("sourceClip", ""),
                           "supported": bool(directive.get("actionSupported")),
                           "traits": directive.get("traits", {})})
        with open(os.path.join(proj_dir, "character_action_safety.json"), "w", encoding="utf-8") as handle:
            json.dump({"schema_version": 1, "lines": report}, handle, ensure_ascii=False, indent=2)
    except Exception as exc:
        print(f"  [character action safety] unavailable: {exc}", flush=True)
    return timeline

def _prepare_acting_lines(timeline, casts, parsed, multi=True, engine="threejs"):
    """Resolve cast/action once so rendering and saved acting state share one contract."""
    scene_line_idx = {}
    prepared = []
    for entry in timeline:
        speaker = entry.get("speaker")
        scene_id = entry.get("scene")
        scene_index = scene_line_idx.get(scene_id, 0)
        scene_line_idx[scene_id] = scene_index + 1
        cast = list(casts.get(scene_id, [])) if multi else []
        if engine == "threejs" and not cast:
            cast = [speaker]
        if cast:
            cast = _cast_with_speaker(cast, speaker)
            action, target = _line_action(entry, cast, speaker, parsed)
        else:
            action, target = "none", -1
        prepared.append({"cast": cast, "action": action, "target": target,
                         "scene_index": scene_index})
    return prepared


def _shot_for_line(entry, scene_index, cast):
    """Story-motivated shot selection instead of a mechanical repeating pattern."""
    if scene_index == 0:
        return "wide"
    action = str(entry.get("action") or "").lower()
    emotion = str(entry.get("emotion") or "neutral").lower()
    text = str(entry.get("text") or "")
    if emotion in {"surprised", "scared", "sad", "angry", "confused"} or "?" in text or "؟" in text:
        return "closeup"
    if action and action not in {"smiles", "nods", "looks", "speaks"}:
        return "medium"
    if len(cast) > 1 and scene_index % 4 == 0:
        return "wide"
    return "medium" if scene_index % 2 == 0 else "closeup"


def _clear_frames(frames_dir):
    """Remove only renderer-owned frame PNGs before a retry."""
    import glob as _g
    for path in _g.glob(os.path.join(frames_dir, "frame_*.png")):
        try:
            os.remove(path)
        except OSError:
            pass


def _pre_render_character_validation(assignment, proj_dir):
    """Write warning-only GLB capability data without changing render selection."""
    try:
        import char3d_lib
        report = char3d_lib.validate_assignments(assignment)
        path = os.path.join(proj_dir, "character_validation.json")
        with open(path, "w", encoding="utf-8") as handle:
            json.dump(report, handle, ensure_ascii=False, indent=2, sort_keys=True)
            handle.write("\n")
        for character in report.get("characters", []):
            meta = character.get("character", {})
            label = meta.get("id") or meta.get("name") or "character"
            print(f"  [character] {label}: {character.get('tier') or 'UNSUPPORTED'} "
                  f"({character.get('compatibility_percent', 0)}%)", flush=True)
            for issue in (character.get("warnings") or []) + (character.get("errors") or []):
                print(f"  [character warning] {label}: {issue.get('message', issue)}", flush=True)
        return report
    except Exception as exc:
        # Validator is advisory in Phase 1: never regress the established renderer.
        print(f"  [character warning] capability validation unavailable: {exc}", flush=True)
        return {"schema_version": 1, "characters": [], "validation_error": str(exc)}


def _resolve_viseme_path(proj_dir, reference):
    """Resolve a timeline sidecar safely; missing files trigger jaw fallback."""
    if not reference:
        return ""
    path = reference if os.path.isabs(reference) else os.path.join(proj_dir, reference)
    return path if os.path.exists(path) else ""


def _lip_sync_inputs(character_id, speaker, openness_path, viseme_path, performance=None):
    """Only the current speaker receives inputs supported by the real face rig."""
    speaking = character_id == speaker
    if performance is None:
        return {
            "openness": openness_path if speaking else "",
            "visemes": viseme_path if speaking else "",
        }
    mode = str(performance.get("lipSyncMode") or "none")
    if not speaking or mode == "none":
        return {"openness": "", "visemes": ""}
    if mode == "jaw_openness":
        return {"openness": openness_path, "visemes": ""}
    return {"openness": openness_path, "visemes": viseme_path}


def _character_runtime_metadata(blend):
    """Attach explicit body-animation capability without changing legacy rigs."""
    try:
        import char3d_lib
        return char3d_lib.runtime_metadata(blend)
    except Exception:
        return {"capabilityId": "", "animationTier": "LEGACY", "facialTier": "SKELETAL_BASIC",
                "speechMode": "body_only", "lipSyncMode": "none",
                "facialReady": False, "library": "sbz"}


def _character_sync_metadata(character_id, speaker, openness_path, viseme_path, blend):
    metadata = _character_runtime_metadata(blend)
    return {
        **metadata,
        **_lip_sync_inputs(character_id, speaker, openness_path, viseme_path, metadata),
    }


def _character_render_directive(character_id, blend, requested_action, requested_clip=""):
    """Use only real clip-backed actions for Quaternius; preserve SBZ legacy behavior."""
    metadata = _character_runtime_metadata(blend)
    if metadata.get("library") != "quaternius":
        return {"action": requested_action or "none", "sourceClip": requested_clip or "", "traits": {}}
    try:
        import character_traits
        return character_traits.render_directive(blend, requested_action, requested_clip)
    except Exception as exc:
        print(f"  [character traits] {character_id}: {exc}", flush=True)
        return {"action": "idle", "sourceClip": "", "traits": {"poseMode": "clip_only"}}

def _capability_safe_shot(shot, blend):
    """Only validated full-facial rigs may receive a facial/dialogue close-up."""
    metadata = _character_runtime_metadata(blend)
    if (not metadata.get("facialReady")
            and shot in {"closeup", "dialogue_close_up", "facial_close_up"}):
        return "medium"
    return shot


def _clip_probe(path):
    try:
        raw = subprocess.check_output(
            ["ffprobe", "-v", "error", "-select_streams", "v:0",
             "-show_entries", "stream=duration,nb_frames,width,height", "-of", "json", path],
            text=True)
        stream = (json.loads(raw).get("streams") or [{}])[0]
        return (float(stream.get("duration") or 0.0),
                int(stream.get("nb_frames") or 0),
                int(stream.get("width") or 0),
                int(stream.get("height") or 0))
    except Exception:
        return 0.0, 0, 0, 0


def _clip_is_valid(video_path, audio_path, fps, ratio=0.90, expected_size=None):
    """Reject truncated/one-frame shots before they can enter final assembly."""
    if not os.path.exists(video_path) or os.path.getsize(video_path) < 10000:
        return False
    video_dur, frames, width, height = _clip_probe(video_path)
    if expected_size and (width, height) != tuple(expected_size):
        return False
    audio_dur = _probe_duration(audio_path)
    # A real short spoken line can be below half a second. Validate against
    # its audio duration plus two video frames, rather than rejecting it solely
    # because of a fixed 0.50s floor. This still rejects one-frame/truncated clips.
    minimum_duration = max(2.0 / max(1, int(fps or 24)), audio_dur * ratio)
    minimum_frames = max(2, int(minimum_duration * fps * 0.70))
    return video_dur >= minimum_duration and frames >= minimum_frames


def _render_revision_matches(video_path, revision=THREEJS_RENDER_REVISION):
    """Only reuse clips produced by the current visual-direction runtime."""
    try:
        if not os.path.exists(video_path + ".revision") and os.path.exists(video_path) and os.path.getsize(video_path) > 10000:
            _write_render_revision(video_path, revision)
            return True
        with open(video_path + ".revision", encoding="utf-8") as handle:
            return handle.read().strip() == revision
    except OSError:
        return False


def _write_render_revision(video_path, revision=THREEJS_RENDER_REVISION):
    path = video_path + ".revision"
    temp = path + ".tmp"
    with open(temp, "w", encoding="utf-8", newline="\n") as handle:
        handle.write(revision + "\n")
    os.replace(temp, path)
    return path


def _duration_matches(actual, expected, fps, tolerance_seconds=0.12):
    """Container-safe duration comparison with at least two frames of tolerance."""
    tolerance = max(float(tolerance_seconds), 2.0 / max(1, int(fps or 24)))
    return abs(float(actual) - float(expected)) <= tolerance


def _stream_duration(path, selector):
    """Return one encoded stream duration; zero means unavailable."""
    try:
        out = subprocess.check_output(
            ["ffprobe", "-v", "error", "-select_streams", selector,
             "-show_entries", "stream=duration",
             "-of", "default=noprint_wrappers=1:nokey=1", path], text=True)
        return float(out.strip())
    except Exception:
        return 0.0


# Largest tail gap we will absorb by holding the last frame. Anything bigger is
# a story-length problem and must not be hidden behind a still image.
MAX_TAIL_PAD_SECONDS = 2.0


def _enforce_target_duration(video_path, target_seconds, fps):
    """Meet the selected duration without silently removing spoken dialogue."""
    target = float(target_seconds or 0)
    if target <= 0:
        return video_path, 1.0, None
    actual = _probe_duration(video_path)
    tolerance = max(2.0 / max(1, int(fps or 24)), 0.04)
    if abs(actual - target) <= tolerance:
        return video_path, 1.0, "already exact"
    output = video_path + ".target.mp4"
    if actual < target:
        padding = target - actual
        # A frozen last frame is dead air: a 2-minute selection that only had
        # 83s of story used to ship 37s of still image. Only absorb a rounding
        # gap; a real shortfall keeps the natural duration and is reported so
        # the script (not the renderer) gets fixed.
        if padding > MAX_TAIL_PAD_SECONDS:
            return video_path, 1.0, (
                f"kept natural {actual:.1f}s (preset {target:.1f}s; "
                f"{padding:.1f}s short — script too brief, freeze-frame padding refused)")
        graph = (f"[0:v]tpad=stop_mode=clone:stop_duration={padding:.6f}[v];" f"[0:a]apad=pad_dur={padding:.6f}[a]")
        action, scale = f"held ending +{padding:.2f}s", 1.0
    else:
        # Preset guidance hai, compressor nahi: overrun par speech ki raftaar
        # tez NAHI karte (kids pacing) — natural duration rakho.
        return video_path, 1.0, (f"kept natural {actual:.1f}s "
                                 f"(preset {target:.1f}s; speech retime skipped)")
    subprocess.run(["ffmpeg", "-y", "-i", video_path, "-filter_complex", graph, "-map", "[v]", "-map", "[a]", "-t", f"{target:.6f}", *_vcodec(None, fps), "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", getattr(config, "AUDIO_BITRATE", "384k"), "-movflags", "+faststart", output, "-loglevel", "error"], check=True)
    os.replace(output, video_path)
    return video_path, scale, action

def _validate_final_duration(video_path, expected_duration, fps):
    """Reject timeline drift or an independently truncated A/V stream."""
    actual = _probe_duration(video_path)
    video_duration = _stream_duration(video_path, "v:0") or actual
    audio_duration = _stream_duration(video_path, "a:0") or actual
    # AAC priming/mux rounding may extend format/audio duration by roughly a
    # quarter-second. Video remains frame-accurate and gets the tighter limit.
    video_tolerance = max(0.15, 3.0 / max(1, int(fps or 24)))
    container_tolerance = max(0.35, 4.0 / max(1, int(fps or 24)))
    if abs(video_duration - float(expected_duration)) > video_tolerance:
        raise RuntimeError(
            f"final video stream duration mismatch: expected {expected_duration:.3f}s, "
            f"got {video_duration:.3f}s")
    if (abs(audio_duration - float(expected_duration)) > container_tolerance or
            abs(actual - float(expected_duration)) > container_tolerance):
        raise RuntimeError(
            f"final duration mismatch: expected {expected_duration:.3f}s, got {actual:.3f}s")
    return actual


def _encode_line_frames(frames_dir, audio_path, grade, line_mp4, height, fps):
    """PNG frames + audio -> line mp4. Tez ultrafast/p4 preset (intermediate clip)."""
    subprocess.run([
        "ffmpeg", "-y", "-threads", "0",
        "-framerate", str(fps),
        "-i", os.path.join(frames_dir, "frame_%04d.png"), "-i", audio_path,
        "-vf", grade, *_vcodec_fast(height, fps), "-pix_fmt", "yuv420p",
        "-c:a", "aac", "-b:a", getattr(config, "AUDIO_BITRATE", "384k"),
        "-shortest", line_mp4, "-loglevel", "error",
    ], check=True)


def render_3d_video(parsed, timeline, scene_bg, proj_dir, out_path, on_progress=None,
                    should_cancel=None, target_duration=None):
    """timeline ki har line ka 3D clip render + assemble -> final video."""
    import char3d_lib
    VW, VH = config.get_dimensions()
    # Native delivery resolution by default; FAST_PREVIEW remains the explicit speed mode.
    max_h = getattr(config, "BLENDER3D_MAX_H", 1080)
    if VH > max_h:
        VW = int(round(VW * max_h / VH / 2) * 2); VH = max_h
    fps = getattr(config, "BLENDER3D_FPS", 24)   # 3D-specific fps (kam frames = tez)
    # target_duration UI se preset string bhi ho sakta hai ("1min", "medium").
    try:
        target_seconds = float(target_duration or 0)
    except (TypeError, ValueError):
        import duration_planner
        target_seconds = float(duration_planner.preset(target_duration)["seconds"])
    selected_library = str(parsed.get("character_library") or "sbz").strip().lower()
    assignment = char3d_lib.assign(parsed.get("characters", []),
                                   parsed.get("char_overrides"), library=selected_library)   # {char_id: blend_path}
    scene_map = {sc["id"]: sc for sc in parsed.get("scenes", [])}
    clips_dir = os.path.join(proj_dir, "clips3d"); os.makedirs(clips_dir, exist_ok=True)
    total = len(timeline)
    line_mp4s = []
    rendered_timeline = []
    engine = getattr(config, "RENDER_ENGINE", "threejs")
    if engine == "threejs":
        _pre_render_character_validation(assignment, proj_dir)
    multi = getattr(config, "BLENDER3D_MULTI", True)
    casts = _scene_casts(timeline, assignment) if multi else {}
    costume_map = parsed.get("costumes", {}) or {}   # {char_id: costume preset}
    acc_map = parsed.get("accessories", {}) or {}    # {char_id: worn prop (head/face)}
    held_map = parsed.get("held", {}) or {}          # {char_id: hand item}
    res = f"{VW}x{VH}"
    # Style dropdown -> 3D visual LOOK (rang/roshni ka mahaul)
    try:
        import looks
        grade = looks.grade_for(config.STYLE); look_exposure = looks.exposure_for(config.STYLE)
    except Exception:
        grade = getattr(config, "COLOR_GRADE", "eq=saturation=1.5:contrast=1.12"); look_exposure = -0.2
    if engine == "threejs":
        _apply_character_action_safety(timeline, assignment, proj_dir)
    acting_lines = _prepare_acting_lines(timeline, casts, parsed, multi, engine)
    animation_plan = None
    production_plan = None
    if engine == "threejs":
        import acting_state
        animation_plan = acting_state.build_plan(timeline, acting_lines, fps)
        acting_state.write_plan(proj_dir, animation_plan)
        import production_director
        production_plan = production_director.build_plan(
            parsed, timeline, assignment, acting_lines, fps, acting_plan=animation_plan)
        production_director.write_plan(proj_dir, production_plan)
        for warning in production_plan.get("warnings", []):
            print(f"  [direction warning] line {warning.get('line')}: "
                  f"{warning.get('message')}", flush=True)

    # ---- PARALLEL 3D LINE RENDER (ThreeJS) ----
    # Har line ek alag Node.js subprocess hai — inhe parallel chala saktay hain.
    # Sequential fallback: THREEJS_RENDER_WORKERS=1 ya engine!=threejs.
    n_workers = getattr(config, "THREEJS_RENDER_WORKERS", 3) if engine == "threejs" else 1

    def _render_one_line(args):
        """Worker function: ek line ka poora render (openness->threejs->encode).
        Thread-safe: har line apni alag directory/files use karta hai."""
        (i, e, acting_context, acting_line, directed_line) = args
        spk = e.get("speaker")
        audio = os.path.join(proj_dir, e["audio"])
        oj = os.path.join(clips_dir, f"open_{i}.json")
        viseme_ref = e.get("visemes") or ""
        vj = _resolve_viseme_path(proj_dir, viseme_ref)
        if viseme_ref and not vj:
            print(f"  [viseme warning] line {i}: timeline missing -> openness fallback", flush=True)
            vj = ""
        frames_dir = os.path.join(clips_dir, f"line_{i}")
        line_mp4 = os.path.join(clips_dir, f"line_{i}.mp4")
        sidx = acting_context["scene_index"]

        # cache check
        clip_valid = _clip_is_valid(line_mp4, audio, fps, expected_size=(VW, VH))
        revision_valid = engine != "threejs" or _render_revision_matches(line_mp4)
        if clip_valid and revision_valid:
            if on_progress:
                on_progress(i, total, f"3D line {i}/{total} [{spk}] (cached)")
            return (i, line_mp4, e, True)   # (index, path, entry, was_cached)

        if on_progress:
            on_progress(i, total, f"3D render line {i}/{total} [{spk}]...")
        if os.path.exists(line_mp4):
            reason = ("outdated visual-direction revision" if clip_valid and not revision_valid
                      else "truncated or one-frame clip")
            print(f"  [render cache reject] line {i}: {reason}", flush=True)
            try:
                os.remove(line_mp4)
            except OSError:
                pass

        _clear_frames(frames_dir)
        _openness(audio, fps, oj)
        bg = scene_bg.get(e.get("scene"))
        scene_data = scene_map.get(e.get("scene"), {})
        env = _env_for(scene_data,
                       preset=(directed_line.get("environment") or {}).get("preset")
                       or _scene_look(scene_data))
        cast = acting_context["cast"]
        if cast:
            shot = _capability_safe_shot(
                directed_line.get("shot") or _shot_for_line(e, sidx, cast),
                assignment.get(spk) or _fallback_blend(),
            )
            focus = cast.index(spk)
            spk_action, tgt_slot = acting_context["action"], acting_context["target"]
            spec = {
                "out": frames_dir, "flimit": 0, "fps": fps, "res": res, "env": env or "",
                "duration": float(e.get("duration") or _probe_duration(audio)),
                "shot": shot, "focus": focus, "exposure": look_exposure,
                "sceneLook": (directed_line.get("environment") or {}).get("preset")
                             or _scene_look(scene_data),
                "backgroundImage": bg or "",
                "direction": directed_line.get("camera") or {},
                "environmentMotion": directed_line.get("environment") or {},
                "props": directed_line.get("props") or [],
                "timeOffset": acting_line.get("timeOffset", 0.0),
                "animationStateSchema": animation_plan.get("schema_version") if animation_plan else 0,
                "chars": [{
                    "id": cid,
                    "blend": assignment.get(cid) or _fallback_blend(),
                    **_character_sync_metadata(
                        cid, spk, oj, vj, assignment.get(cid) or _fallback_blend()),
                    "emotion": e.get("emotion", "neutral") if cid == spk else "neutral",
                    "speaking": cid == spk, "slot": si,
                    "costume": costume_map.get(cid, ""),
                    "accessory": acc_map.get(cid, ""),
                    "held": held_map.get(cid, ""),
                    "action": ((directed_line.get("characters") or {}).get(cid) or {}).get(
                        "action", spk_action if cid == spk else "none"),
                    "sourceClip": ((directed_line.get("characters") or {}).get(cid) or {}).get("sourceClip", ""),
                    **_character_render_directive(
                        cid, assignment.get(cid) or _fallback_blend(),
                        ((directed_line.get("characters") or {}).get(cid) or {}).get(
                            "action", spk_action if cid == spk else "listen"),
                        ((directed_line.get("characters") or {}).get(cid) or {}).get("sourceClip", "")),
                    "baseClip": ((directed_line.get("characters") or {}).get(cid) or {}).get("baseClip", ""),
                    "crossfadeSeconds": ((directed_line.get("characters") or {}).get(cid) or {}).get("crossfadeSeconds", 0.22),
                    "blocking": ((directed_line.get("characters") or {}).get(cid) or {}).get("blocking", {}),
                    "interaction": ((directed_line.get("characters") or {}).get(cid) or {}).get("interaction"),
                    "target": (tgt_slot if cid == spk else focus),
                    "acting": acting_line.get("characters", {}).get(cid, {}),
                } for si, cid in enumerate(cast)],
            }
            if engine == "threejs":
                _render_scene_line_threejs(spec, frames_dir, should_cancel)
            else:
                _render_scene_line(spec, frames_dir, should_cancel)
        else:
            _render_line(assignment.get(spk) or _fallback_blend(), oj, frames_dir,
                         e.get("emotion", "neutral"), bg, res, env,
                         costume_map.get(spk, ""), acc_map.get(spk, ""), held_map.get(spk, ""))

        _encode_line_frames(frames_dir, audio, grade, line_mp4, VH, fps)

        # Fail-safe: retry bad ensemble as single-speaker shot
        if not _clip_is_valid(line_mp4, audio, fps, expected_size=(VW, VH)) and engine == "threejs":
            print(f"  [render retry] line {i}: single-speaker safety fallback", flush=True)
            _clear_frames(frames_dir)
            fallback_spec = {
                "out": frames_dir, "flimit": 0, "fps": fps, "res": res,
                "duration": float(e.get("duration") or _probe_duration(audio)),
                "env": env or "", "shot": "medium", "focus": 0,
                "exposure": look_exposure,
                "sceneLook": (directed_line.get("environment") or {}).get("preset")
                             or _scene_look(scene_data),
                "backgroundImage": bg or "",
                "direction": directed_line.get("camera") or {},
                "environmentMotion": directed_line.get("environment") or {},
                "props": directed_line.get("props") or [],
                "timeOffset": acting_line.get("timeOffset", 0.0),
                "animationStateSchema": animation_plan.get("schema_version") if animation_plan else 0,
                "chars": [{
                    "id": spk,
                    "blend": assignment.get(spk) or _fallback_blend(),
                    **_character_sync_metadata(
                        spk, spk, oj, vj, assignment.get(spk) or _fallback_blend()),
                    "emotion": e.get("emotion", "neutral"),
                    "speaking": True, "slot": 0, "costume": costume_map.get(spk, ""),
                    "accessory": acc_map.get(spk, ""), "held": held_map.get(spk, ""),
                    "action": acting_context["action"], "target": -1,
                    "sourceClip": ((directed_line.get("characters") or {}).get(spk) or {}).get("sourceClip", ""),
                    **_character_render_directive(
                        spk, assignment.get(spk) or _fallback_blend(), acting_context["action"],
                        ((directed_line.get("characters") or {}).get(spk) or {}).get("sourceClip", "")),
                    "baseClip": ((directed_line.get("characters") or {}).get(spk) or {}).get("baseClip", ""),
                    "crossfadeSeconds": ((directed_line.get("characters") or {}).get(spk) or {}).get("crossfadeSeconds", 0.22),
                    "blocking": ((directed_line.get("characters") or {}).get(spk) or {}).get("blocking", {}),
                    "interaction": ((directed_line.get("characters") or {}).get(spk) or {}).get("interaction"),
                    "acting": acting_line.get("characters", {}).get(spk, {}),
                }],
            }
            _render_scene_line_threejs(fallback_spec, frames_dir, should_cancel)
            _encode_line_frames(frames_dir, audio, grade, line_mp4, VH, fps)

        if not _clip_is_valid(line_mp4, audio, fps, expected_size=(VW, VH)):
            raise RuntimeError(f"line {i} failed duration/frame validation")
        if engine == "threejs":
            _write_render_revision(line_mp4)
        return (i, line_mp4, e, False)   # (index, path, entry, was_cached)

    # Build job list (only non-cancelled lines)
    job_args = [
        (i, e, acting_lines[i - 1],
         animation_plan["lines"][i - 1] if animation_plan else {},
         production_plan["lines"][i - 1] if production_plan else {})
        for i, e in enumerate(timeline, 1)
    ]

    if n_workers > 1:
        from concurrent.futures import ThreadPoolExecutor, as_completed
        print(f"  [3D render] {n_workers} parallel workers (ThreeJS)", flush=True)
        results = {}
        with ThreadPoolExecutor(max_workers=n_workers) as pool:
            futures = {pool.submit(_render_one_line, args): args[0] for args in job_args}
            for fut in as_completed(futures):
                if should_cancel and should_cancel():
                    pool.shutdown(wait=False, cancel_futures=True)
                    raise Cancelled()
                try:
                    idx, mp4, entry, _ = fut.result()
                    results[idx] = (mp4, entry)
                except Cancelled:
                    raise
                except Exception as ex:
                    line_i = futures[fut]
                    raise RuntimeError(f"3D line {line_i} render failed: {ex}") from ex
        # Results ko original order mein sort karo
        for i, _ in enumerate(timeline, 1):
            mp4, entry = results[i]
            line_mp4s.append(mp4)
            rendered_timeline.append(entry)
    else:
        # Sequential fallback (THREEJS_RENDER_WORKERS=1 ya non-threejs engine)
        for args in job_args:
            if should_cancel and should_cancel():
                raise Cancelled()
            try:
                _, mp4, entry, _ = _render_one_line(args)
                line_mp4s.append(mp4)
                rendered_timeline.append(entry)
            except Cancelled:
                raise
            except Exception as ex:
                raise RuntimeError(f"3D line {args[0]} render failed; final assembly stopped: {ex}") from ex

    if not line_mp4s:
        raise RuntimeError("Koi 3D clip nahi bana")
    if len(line_mp4s) != len(timeline):
        raise RuntimeError("Render incomplete: final assembly refused missing dialogue clips")

    # assemble: intro + clips + outro, music, burned subtitles
    if on_progress:
        on_progress(total, total, "Final assembly (intro/outro, subtitles, music)...")
    _assemble(line_mp4s, proj_dir, rendered_timeline, parsed, out_path, VW, VH, fps, target_seconds=target_seconds)
    return out_path


def _ts(s):
    h = int(s // 3600); m = int(s % 3600 // 60); sec = s % 60
    return f"{h:02d}:{m:02d}:{sec:06.3f}".replace(".", ",")


def _wrap_subtitle(text, target=44):
    """Balance a subtitle into at most two mobile-readable lines."""
    words = str(text or "").split()
    if len(" ".join(words)) <= target or len(words) < 2:
        return " ".join(words)
    best = None
    for split in range(1, len(words)):
        left, right = " ".join(words[:split]), " ".join(words[split:])
        score = max(len(left), len(right)) + abs(len(left) - len(right)) * 0.25
        if best is None or score < best[0]:
            best = (score, left, right)
    return f"{best[1]}\n{best[2]}" if best else " ".join(words)


def _build_srt(timeline, srt_path, offset=0.0, starts=None, durations=None):
    """Script text + durations se accurate SRT (whisper ki zaroorat nahi)."""
    t = offset; out = []
    for i, e in enumerate(timeline, 1):
        dur = (float(durations[i - 1]) if durations is not None
               else float(e.get("duration") or 3.0))
        if starts is not None:
            t = float(starts[i - 1])
        txt = _wrap_subtitle((e.get("text") or "").strip())
        if txt:
            out.append(f"{i}\n{_ts(t)} --> {_ts(t + dur)}\n{txt}\n")
        t += dur
    open(srt_path, "w", encoding="utf-8").write("\n".join(out))
    return t


def _probe_audio(path):
    """Line clip ke audio params (sample-rate, channel-layout) — intro/outro match karne ko."""
    try:
        out = subprocess.check_output(
            ["ffprobe", "-v", "error", "-select_streams", "a:0",
             "-show_entries", "stream=sample_rate,channels", "-of", "csv=p=0", path],
            text=True).strip().split(",")
        return int(out[0]), ("mono" if out[1] == "1" else "stereo")
    except Exception:
        return 44100, "stereo"


def _probe_duration(path):
    try:
        out = subprocess.check_output(
            ["ffprobe", "-v", "error", "-show_entries", "format=duration",
             "-of", "default=noprint_wrappers=1:nokey=1", path], text=True)
        return float(out.strip())
    except Exception:
        return 3.0


def _card(text_lines, out_mp4, VW, VH, fps, seconds=1.8, bg=(24, 20, 34),
          accent=(255, 210, 90), ar=44100, cl="stereo"):
    """Title/outro card -> chhoti mp4 (silent aac) jo line-clips ke saath concat ho sake."""
    from PIL import Image, ImageDraw, ImageFont
    img = Image.new("RGB", (VW, VH), bg)
    d = ImageDraw.Draw(img)

    def font(sz):
        for f in ("C:/Windows/Fonts/segoeuib.ttf", "C:/Windows/Fonts/arialbd.ttf"):
            try:
                return ImageFont.truetype(f, sz)
            except Exception:
                pass
        return ImageFont.load_default()
    sizes = [int(VH * 0.14)] + [int(VH * 0.08)] * (len(text_lines) - 1)
    cols = [accent] + [(240, 240, 245)] * (len(text_lines) - 1)
    total_h = sum(s + int(VH * 0.03) for s in sizes)
    y = (VH - total_h) // 2
    for i, ln in enumerate(text_lines):
        fnt = font(sizes[i])
        bb = d.textbbox((0, 0), ln, font=fnt); w = bb[2] - bb[0]
        d.text(((VW - w) // 2, y), ln, font=fnt, fill=cols[i])
        y += sizes[i] + int(VH * 0.03)
    png = out_mp4 + ".png"; img.save(png)
    subprocess.run(["ffmpeg", "-y", "-loop", "1", "-t", str(seconds), "-i", png,
                    "-f", "lavfi", "-t", str(seconds), "-i", f"anullsrc=r={ar}:cl={cl}",
                    "-vf", f"scale={VW}:{VH},format=yuv420p", "-r", str(fps),
                    *_vcodec(VH, fps), "-c:a", "aac",
                    "-b:a", getattr(config, "AUDIO_BITRATE", "384k"),
                    "-ar", str(ar), "-shortest",
                    out_mp4, "-loglevel", "error"], check=True)
    return out_mp4


def _audio_qc(path):
    """Final QC: loudness measurement (LUFS/dBTP) + silence + missing-audio detection."""
    try:
        import audiopost
        if not audiopost.has_audio(path):
            print("  [audio QC] WARNING: final video mein audio stream NAHI mili!", flush=True)
            return
        m = audiopost.measure_loudness(path)
        I, tp = m.get("I"), m.get("TP")
        ok = (I is not None and -16.5 <= I <= -13.5) and (tp is None or tp <= -0.5)
        print(f"  [audio QC] Integrated {I} LUFS | TruePeak {tp} dBTP | LRA {m.get('LRA')} "
              f"-> {'OK' if ok else 'CHECK'} (target ~{config.TARGET_LUFS} LUFS / {config.TARGET_TP} dBTP)",
              flush=True)
        sil = audiopost.detect_silence(path, thr_db=-45, min_d=1.5)
        if sil:
            print(f"  [audio QC] {len(sil)} lamba silence span (>1.5s) — pehla {sil[0]}", flush=True)
    except Exception as ex:
        print(f"  [audio QC skip] {ex}", flush=True)


def _assemble(mp4s, proj_dir, timeline, parsed, out_path, VW, VH, fps, target_seconds=0.0):
    import audio as audio_mod
    cdir = os.path.join(proj_dir, "clips3d")
    title = (parsed or {}).get("title", "") or "Cartoon"
    brand = getattr(config, "BRAND_NAME", "SBZ Cartoons")
    intro_sec = 0.0
    line_plan = transitions.plan_transitions(timeline, 0.30)

    clips = list(mp4s)
    clip_plan = list(line_plan)
    have_intro = False
    have_outro = False
    ar, cl = _probe_audio(mp4s[0])          # intro/outro audio ko line-clips se match karo
    # Hook-first default: intro is optional; outro remains independently configurable.
    if getattr(config, "INTRO_ON", False):
        try:
            intro = _card([brand, title], os.path.join(cdir, "_intro.mp4"), VW, VH, fps, 1.8,
                          ar=ar, cl=cl)
            clips = [intro] + clips
            clip_plan = [transitions.decision("fade", 0.35, "title card exit")] + clip_plan
            intro_sec = 1.8
            have_intro = True
        except Exception as ex:
            print(f"  [intro skip] {str(ex)[:100]}", flush=True)
    if getattr(config, "OUTRO_ON", True):
        try:
            outro = _card(["Pasand aaya?", "SUBSCRIBE karo!", brand],
                          os.path.join(cdir, "_outro.mp4"), VW, VH, fps, 2.2, bg=(30, 16, 40),
                          ar=ar, cl=cl)
            clips = clips + [outro]
            clip_plan = clip_plan + [transitions.decision("fade", 0.35, "outro card entry")]
            have_outro = True
        except Exception as ex:
            print(f"  [outro skip] {str(ex)[:100]}", flush=True)

    # Mixed editorial assembly: clean concat for cuts, xfade only at motivated
    # boundaries. Windows cannot spawn a process whose command line contains
    # hundreds of absolute clip paths.  Render small transition-aware batches
    # first, then concatenate the batch outputs through FFmpeg's manifest
    # demuxer.  This keeps long projects resumable and path-length safe.
    clip_durs = [_probe_duration(path) for path in clips]
    tmp = out_path + ".c.mp4"
    max_batch_inputs = 10

    def render_batch(batch_paths, batch_durations, batch_plan, batch_output):
        filters, video_label, audio_label, batch_duration = transitions.build_av_filter_graph(
            batch_durations, batch_plan)
        inputs = []
        for batch_path in batch_paths:
            inputs += ["-i", batch_path]
        subprocess.run(["ffmpeg", "-y", *inputs, "-filter_complex", ";".join(filters),
                        "-map", f"[{video_label}]", "-map", f"[{audio_label}]",
                        *_vcodec(VH, fps), "-pix_fmt", "yuv420p", "-c:a", "aac",
                        "-b:a", getattr(config, "AUDIO_BITRATE", "384k"),
                        "-r", str(fps), "-movflags", "+faststart",
                        batch_output, "-loglevel", "error"], check=True)
        return batch_duration

    if len(clips) <= max_batch_inputs:
        filters, video_label, audio_label, assembled_duration = transitions.build_av_filter_graph(
            clip_durs, clip_plan)
        inputs = []
        for path in clips:
            inputs += ["-i", path]
        subprocess.run(["ffmpeg", "-y", *inputs, "-filter_complex", ";".join(filters),
                        "-map", f"[{video_label}]", "-map", f"[{audio_label}]",
                        *_vcodec(VH, fps), "-pix_fmt", "yuv420p", "-c:a", "aac",
                        "-b:a", getattr(config, "AUDIO_BITRATE", "384k"),
                        "-r", str(fps), "-movflags", "+faststart",
                        tmp, "-loglevel", "error"], check=True)
    else:
        batch_dir = os.path.join(cdir, "_assembly_batches")
        os.makedirs(batch_dir, exist_ok=True)
        batch_outputs = []
        assembled_duration = 0.0
        # A transition across a batch boundary is deliberately converted to a
        # clean cut. Dialogue already defaults to hard cuts, and this avoids
        # attempting a 144-input filter graph just to preserve one boundary.
        for batch_no, batch_start in enumerate(range(0, len(clips), max_batch_inputs), 1):
            batch_end = min(len(clips), batch_start + max_batch_inputs)
            if batch_start:
                clip_plan[batch_start - 1] = transitions.decision(
                    "hard_cut", reason="long-render assembly batch boundary")
            batch_paths = clips[batch_start:batch_end]
            batch_durations = clip_durs[batch_start:batch_end]
            batch_plan = clip_plan[batch_start:batch_end - 1]
            batch_output = os.path.join(batch_dir, f"batch_{batch_no:03d}.mp4")
            assembled_duration += render_batch(batch_paths, batch_durations, batch_plan, batch_output)
            batch_outputs.append(batch_output)

        manifest = os.path.join(batch_dir, "concat.txt")
        with open(manifest, "w", encoding="utf-8", newline="\n") as handle:
            for batch_output in batch_outputs:
                # concat demuxer accepts forward-slash absolute paths with
                # -safe 0; quote escaping keeps project names safe as well.
                escaped = os.path.abspath(batch_output).replace("\\", "/").replace("'", r"'\\''")
                handle.write(f"file '{escaped}'\n")
        subprocess.run(["ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", manifest,
                        "-c", "copy", "-movflags", "+faststart", tmp,
                        "-loglevel", "error"], check=True)
        print(f"  [assembly] {len(clips)} clips -> {len(batch_outputs)} Windows-safe batches", flush=True)

    first_line_index = 1 if have_intro else 0
    last_line_index = len(clip_durs) - (1 if have_outro else 0)
    line_durs = clip_durs[first_line_index:last_line_index]
    # Take the persisted plan from the final clip plan, because long renders
    # convert only batch-boundary transitions to clean cuts.
    line_plan = clip_plan[first_line_index:first_line_index + max(0, len(line_durs) - 1)]
    line_offset = (clip_durs[0] - transitions.overlap(clip_plan[0])
                   if have_intro else 0.0)
    line_starts = transitions.timeline_starts(line_durs, line_plan, line_offset)
    outro_start = (line_starts[-1] + line_durs[-1] -
                   (transitions.overlap(clip_plan[-1]) if have_outro else 0.0))
    try:
        json.dump(line_plan,
                  open(os.path.join(proj_dir, "transitions.json"), "w", encoding="utf-8"),
                  ensure_ascii=False, indent=2)
    except Exception:
        pass
    print(f"  [transitions] {transitions.summarize(line_plan)}", flush=True)

    # ---- PROFESSIONAL AUDIO MASTER: music ducking + SFX + fades + limiter + loudnorm ----
    tmp2 = out_path + ".m.mp4"
    try:
        import audiopost
        import actions as _act
        audiopost.ensure_synth_sfx()                     # out-of-box sfx (user override kar sakta)
        track = None
        try:
            track = audio_mod.select_music([e.get("mood") for e in timeline],
                                           selection=getattr(config, "MUSIC_TRACK", "auto"))
        except Exception:
            pass
        # SFX events (action/emotion + scene-transition whoosh + subscribe CTA) — overuse mat karo
        sfx_events = []
        if getattr(config, "SFX_ON", True):
            last = -10.0
            prev_scene = None
            parsed_scenes = {sc.get("id"): sc for sc in (parsed or {}).get("scenes", [])}
            for idx, e in enumerate(timeline):
                t = line_starts[idx]
                sc = e.get("scene")
                incoming = line_plan[idx - 1] if idx else None
                if sc != prev_scene:
                    ambience = {"storm": "rain", "mud": "mud", "wash": "bubbles"}.get(
                        _scene_look(parsed_scenes.get(sc, {})))
                    if ambience:
                        sfx_events.append((t + 0.08, ambience, -16 if ambience == "rain" else -12))
                if (prev_scene is not None and sc != prev_scene and incoming and
                        incoming.get("type") in ("whip_pan", "camera_motivated") and
                        (t - last) > 1.0):
                    sfx_events.append((max(0.0, t - 0.12), "transition", -8))
                    last = t
                prev_scene = sc
                try:
                    act = _act.detect(e.get("text", ""), e.get("emotion", "neutral"))
                except Exception:
                    act = "none"
                name = audiopost.sfx_for_line(act, e.get("emotion"))
                if name and (t - last) > 1.5:            # min 1.5s gap — overuse se bacho
                    sfx_events.append((t + 0.1, name, -9))
                    last = t
            if have_outro:                               # outro par subscribe CTA
                sfx_events.append((outro_start + 0.4, "subscribe", -7))
        total_dur = audiopost.probe_duration(tmp)
        audiopost.master_mix(tmp, tmp2, track, sfx_events, total_dur,
                             mono=getattr(config, "AUDIO_MONO", False))
        os.remove(tmp)
    except Exception as ex:
        print(f"  [audio master fail -> raw] {str(ex)[:150]}", flush=True)
        os.replace(tmp, tmp2)

    tmp2, time_scale, duration_action = _enforce_target_duration(tmp2, target_seconds, fps)
    if duration_action and duration_action.startswith("kept natural"):
        expected_duration = _probe_duration(tmp2)
    else:
        expected_duration = float(target_seconds or assembled_duration)
    if duration_action:
        print(f"  [duration] {duration_action}; delivery target {expected_duration:.2f}s", flush=True)
    if time_scale != 1.0:
        line_starts = [start / time_scale for start in line_starts]
        line_durs = [duration / time_scale for duration in line_durs]
    # burned subtitles (accurate SRT from script) — libass, relative path (Windows-safe)
    if getattr(config, "SUBTITLES_ON", True):
        try:
            srt = os.path.join(cdir, "subs.srt")
            _build_srt(timeline, srt, offset=intro_sec,
                       starts=line_starts, durations=line_durs)
            lang = (parsed or {}).get("language", "roman_urdu")
            fontname = "Segoe UI" if lang == "urdu" else "Arial"
            fsz = max(24, int(VH / 22))
            style = (f"FontName={fontname},FontSize={fsz},PrimaryColour=&H00FFFFFF,"
                     f"OutlineColour=&H00202020,BorderStyle=1,Outline=3,Shadow=1,"
                     f"Alignment=2,MarginV={int(VH*0.07)},Bold=1,WrapStyle=0")
            subprocess.run(["ffmpeg", "-y", "-i", tmp2, "-vf",
                            f"subtitles=subs.srt:force_style='{style}'",
                            *_vcodec(VH, fps), "-pix_fmt", "yuv420p", "-c:a", "copy",
                            "-movflags", "+faststart",
                            os.path.basename(out_path), "-loglevel", "error"],
                           check=True, cwd=cdir)
            # ffmpeg ne cdir mein out banaya -> move to out_path
            made = os.path.join(cdir, os.path.basename(out_path))
            os.replace(made, out_path); os.remove(tmp2)
            _validate_final_duration(out_path, expected_duration, fps)
            _audio_qc(out_path)
            return
        except Exception as ex:
            print(f"  [subtitles skip] {str(ex)[:120]}", flush=True)
    os.replace(tmp2, out_path)
    _validate_final_duration(out_path, expected_duration, fps)
    _audio_qc(out_path)
