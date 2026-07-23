"""
P8 — SBZ AI Video Studio — Desktop UI (Flask backend).
3-column UI (nav + controls + settings). Saare P1-P6 features wired.
Chalao:  python app.py    (browser khud khulega, ya Electron se .exe)
"""
import sys
import os
import threading
import time
import uuid
import webbrowser

from flask import Flask, jsonify, request, render_template, send_from_directory

import config
import styles
import providers
import build as builder

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

app = Flask(__name__)
JOBS = {}
SCRIPT_JOBS = {}
INSTANCE_ID = str(uuid.uuid4())
SERVER_STARTED_AT = time.time()
_INSTANCE_LOCK_HANDLE = None

STAGE_LABEL = {"story": "Story analyze", "voice": "Voices",
               "asset": "Backgrounds + Characters", "render": "Compositing + Render"}

URDU_VOICES = ["ur-IN-SalmanNeural", "ur-IN-GulNeural",   # Indian Urdu
               "ur-PK-AsadNeural", "ur-PK-UzmaNeural"]     # Pakistani Urdu
ENG_VOICES = ["en-US-GuyNeural", "en-US-AriaNeural", "en-US-JennyNeural"]


def _run(job_id, script, settings, parsed=None, proj_name=None):
    import projects_mgr, os as _os, time as _t, json as _j
    proj_dir = _os.path.join(config.PROJECTS_DIR, proj_name) if proj_name else None
    _last = [0.0]
    heartbeat_stop = threading.Event()

    def persist_job(**overrides):
        if not proj_dir:
            return
        job = dict(JOBS.get(job_id) or {})
        fields = {
            "job_id": job_id, "project": proj_name, "owner_pid": os.getpid(),
            "instance_id": INSTANCE_ID, "state": job.get("state", "running"),
            "stage": job.get("stage", "story"), "stage_label": job.get("stage_label", ""),
            "i": job.get("i", 0), "total": job.get("total", 1),
            "message": job.get("message", ""), "heartbeat_at": round(_t.time(), 3),
        }
        fields.update(overrides)
        projects_mgr.save_job(proj_dir, **fields)

    def heartbeat():
        while not heartbeat_stop.wait(3.0):
            try:
                job = JOBS.get(job_id)
                if job is not None:
                    job["heartbeat_at"] = round(_t.time(), 3)
                persist_job()
            except Exception:
                pass

    heartbeat_thread = threading.Thread(target=heartbeat,
                                        name=f"job-heartbeat-{job_id[:8]}", daemon=True)
    heartbeat_thread.start()

    def on_progress(stage, i, t, msg):
        job = JOBS.setdefault(job_id, {})
        job.update(state="running", stage=stage,
                   stage_label=STAGE_LABEL.get(stage, stage),
                   i=i, total=t, message=msg,
                   progress_updated_at=round(_t.time(), 3))
        # job.json disk par (throttled) -> crash ke baad resume
        if proj_dir and (stage == "story" or _t.time() - _last[0] > 4):
            _last[0] = _t.time()
            try:
                persist_job()
            except Exception:
                pass
    try:
        result = builder.build(script, proj_name=proj_name, on_progress=on_progress,
                               settings=settings, parsed=parsed,
                               should_cancel=lambda: JOBS.get(job_id, {}).get("cancel"))
        JOBS[job_id].update(state="done", result=result, error=None,
                            message="Video complete")
        if proj_dir:
            title = None
            try:
                title = _j.load(open(_os.path.join(proj_dir, "story.json"),
                                     encoding="utf-8")).get("title")
            except Exception:
                pass
            try:
                projects_mgr.save_job(proj_dir, state="done", title=title or proj_name,
                                      result=result, error=None, message="Video complete",
                                      heartbeat_at=None)
            except Exception:
                pass
    except Exception as e:
        # STOP (Cancelled) -> 'stopped' (error nahi); partial project resumable rehta
        if type(e).__name__ == "Cancelled":
            JOBS[job_id].update(state="stopped", message="Ruk gaya (resume ho sakta)")
            if proj_dir:
                try:
                    projects_mgr.save_job(proj_dir, state="stopped", stage="stopped",
                                          message="User stopped generation; cached work is resumable.",
                                          heartbeat_at=None)
                except Exception:
                    pass
            return
        import traceback
        traceback.print_exc()
        JOBS[job_id].update(state="error", error=str(e))
        if proj_dir:
            try:
                projects_mgr.save_job(proj_dir, state="error", error=str(e)[:300],
                                      message="Generation failed; cached work is resumable.",
                                      heartbeat_at=None)
            except Exception:
                pass
    finally:
        heartbeat_stop.set()
        heartbeat_thread.join(timeout=1.0)


def _acquire_instance_lock():
    """Hold a cross-process lock so manual Flask and Electron cannot both bind 5050."""
    global _INSTANCE_LOCK_HANDLE
    lock_dir = os.path.join(config.BASE_DIR, "work")
    os.makedirs(lock_dir, exist_ok=True)
    path = os.path.join(lock_dir, "sbz-studio-5050.lock")
    handle = open(path, "a+b")
    if os.path.getsize(path) == 0:
        handle.write(b"0")
        handle.flush()
    handle.seek(0)
    try:
        if os.name == "nt":
            import msvcrt
            msvcrt.locking(handle.fileno(), msvcrt.LK_NBLCK, 1)
        else:
            import fcntl
            fcntl.flock(handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
    except (OSError, IOError):
        handle.close()
        return False
    handle.seek(0)
    handle.truncate()
    handle.write(f"pid={os.getpid()} instance={INSTANCE_ID}\n".encode("ascii"))
    handle.flush()
    _INSTANCE_LOCK_HANDLE = handle
    return True


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/api/health")
def api_health():
    return jsonify({
        "ok": True, "app": "sbz-ai-video-studio", "version": "1.0",
        "pid": os.getpid(), "instance_id": INSTANCE_ID,
        "uptime_seconds": round(time.time() - SERVER_STARTED_AT, 1),
        "active_jobs": sum(job.get("state") == "running" for job in JOBS.values()),
    })


@app.route("/api/options")
def api_options():
    """Dropdowns ke liye: styles, voices, providers, defaults."""
    return jsonify({
        "styles": styles.list_styles(),
        "voices": URDU_VOICES + ENG_VOICES,
        "providers": providers.status(),
        "llm_models": providers.llm_model_options(),
        "edge_voices": providers.EDGE_VOICE_FALLBACK,
        "google_voices": providers.GOOGLE_HINDI_VOICES,
        "urdu_accents": list(config.VOICE_SETS.keys()),
        "render_engines": ["threejs", "blender"],
        "defaults": {
            "style": config.STYLE, "quality": config.VIDEO_QUALITY,
            "aspect": config.ASPECT, "fps": config.FPS,
            "captions": config.CAPTIONS, "urdu_accent": config.URDU_ACCENT,
            "tts_provider": getattr(config, "TTS_PROVIDER", "edge"),
            "voice_speed": getattr(config, "VOICE_SPEED", 1.0),
            "music_track": getattr(config, "MUSIC_TRACK", "auto"),
            "edge_voice": getattr(config, "EDGE_VOICE", ""),
            "google_tts_voice": getattr(config, "GOOGLE_TTS_VOICE", "hi-IN-Standard-B"),
            "elevenlabs_voice_id": getattr(config, "ELEVENLABS_VOICE_ID", ""),
            "elevenlabs_model": getattr(config, "ELEVENLABS_MODEL", "eleven_v3"),
            "llm_provider": getattr(config, "LLM_PROVIDER", "runware"),
            "llm_model": getattr(config, "LLM_MODEL", ""),
            "render_engine": getattr(config, "RENDER_ENGINE", "threejs"),
            "subtitles_on": getattr(config, "SUBTITLES_ON", True),
            "intro_on": getattr(config, "INTRO_ON", False),
            "outro_on": getattr(config, "OUTRO_ON", True),
        },
    })


@app.route("/api/music")
def api_music():
    """Local background-music catalog for the desktop selector."""
    import audio
    return jsonify({"tracks": audio.music_catalog(),
                    "selected": getattr(config, "MUSIC_TRACK", "auto")})

# ---------------- Phase 7: Runware structured script engine ----------------
@app.route("/api/script-engine/options")
def api_script_engine_options():
    """Safe registry/routing metadata; credentials and prompts never enter the browser."""
    from script_engine.pipeline import STAGES
    from script_engine.prompts import LANGUAGES, SCRIPT_DOCTOR_MODES
    from script_engine.registry import ModelRegistry, TaskRouter
    registry = ModelRegistry()
    router = TaskRouter(registry)
    return jsonify({
        "models": registry.public_payload(),
        "routing": router.public_payload(),
        "stages": list(STAGES),
        "languages": list(LANGUAGES),
        "scriptDoctorModes": list(SCRIPT_DOCTOR_MODES),
        "credentialsBackendOnly": True,
    })


@app.route("/api/script-engine/models/verify", methods=["POST"])
def api_script_engine_verify_models():
    """Re-check configured AIR identifiers with Runware modelSearch, without inference."""
    from runware_client import discover_models, redact_sensitive
    from script_engine.registry import ModelRegistry
    registry = ModelRegistry()
    results = []
    try:
        for model in registry.enabled():
            matches = discover_models(model["legacyIds"][0], limit=10)
            actual = next((item for item in matches if item.get("air") == model["runwareAir"]), None)
            results.append({"internalId": model["internalId"], "runwareAir": model["runwareAir"],
                            "verified": bool(actual), "capabilities": (actual or {}).get("capabilities", [])})
        return jsonify({"ok": all(item["verified"] for item in results), "models": results})
    except Exception as exc:
        return jsonify({"ok": False, "models": results,
                        "error": redact_sensitive(str(exc))[:300]}), 503


@app.route("/api/script-engine/start", methods=["POST"])
def api_script_engine_start():
    """Start one reviewable stage; model comparison requires an explicit request flag."""
    from script_engine.pipeline import STAGES
    from script_engine.prompts import LANGUAGES, SCRIPT_DOCTOR_MODES
    data = request.get_json(force=True) or {}
    stage = str(data.get("stage") or "").strip()
    content = str(data.get("content") or "").strip()
    language = str(data.get("language") or "roman_urdu").strip()
    mode = data.get("mode")
    compare = data.get("compare") is True
    if stage not in STAGES:
        return jsonify({"error": "Invalid script pipeline stage"}), 400
    if language not in LANGUAGES:
        return jsonify({"error": "Invalid script language"}), 400
    if not content or len(content) > 50000:
        return jsonify({"error": "Content must contain 1 to 50,000 characters"}), 400
    if stage == "script_doctor" and mode not in SCRIPT_DOCTOR_MODES:
        return jsonify({"error": "Select a valid Script Doctor mode"}), 400
    if compare and not data.get("comparison_model"):
        return jsonify({"error": "Comparison model is required when comparison is enabled"}), 400
    if stage in {"animation_plan", "storyboard"}:
        if data.get("approved_input") is not True or not data.get("project"):
            return jsonify({"error": "Approve a structured story stage before animation planning"}), 409
        from script_engine import ScriptPipeline
        approved = [item for item in ScriptPipeline().workflow(data.get("project"))["stages"]
                    if item.get("approved")]
        if not approved:
            return jsonify({"error": "No approved project stage was found"}), 409
    job_id = str(uuid.uuid4())
    cancel_event = threading.Event()
    SCRIPT_JOBS[job_id] = {"state": "queued", "stage": stage, "result": None,
                           "error": None, "cancel_event": cancel_event,
                           "comparisonEnabled": compare}

    def run_script_stage():
        from script_engine import GenerationCancelled, ScriptPipeline
        from runware_client import redact_sensitive
        pipeline = ScriptPipeline()
        try:
            SCRIPT_JOBS[job_id].update(state="running")
            common = dict(language=language, mode=mode,
                          allow_fallback=data.get("allow_fallback", True) is True,
                          use_cache=data.get("use_cache", True) is True,
                          cancel_event=cancel_event, project=data.get("project"))
            primary = pipeline.run_stage(stage, content,
                                         requested_model=data.get("model"), **common)
            result = {"primary": primary}
            if compare:
                if cancel_event.is_set():
                    raise GenerationCancelled("Script generation cancelled")
                comparison = pipeline.run_stage(
                    stage, content, requested_model=data.get("comparison_model"),
                    **dict(common, allow_fallback=False))
                result["comparison"] = comparison
            SCRIPT_JOBS[job_id].update(state="done", result=result)
        except GenerationCancelled:
            SCRIPT_JOBS[job_id].update(state="cancelled", error="Generation cancelled")
        except Exception as exc:
            SCRIPT_JOBS[job_id].update(state="error",
                                       error=redact_sensitive(str(exc))[:400],
                                       diagnostics=getattr(exc, "diagnostics", []))

    threading.Thread(target=run_script_stage, daemon=True).start()
    return jsonify({"job_id": job_id, "state": "queued"}), 202


@app.route("/api/script-engine/status/<job_id>")
def api_script_engine_status(job_id):
    job = SCRIPT_JOBS.get(job_id)
    if not job:
        return jsonify({"error": "Script job not found"}), 404
    return jsonify({key: value for key, value in job.items() if key != "cancel_event"})


@app.route("/api/script-engine/cancel/<job_id>", methods=["POST"])
def api_script_engine_cancel(job_id):
    job = SCRIPT_JOBS.get(job_id)
    if not job:
        return jsonify({"error": "Script job not found"}), 404
    job["cancel_event"].set()
    if job["state"] == "queued":
        job["state"] = "cancelled"
    return jsonify({"cancelled": True, "state": job["state"]})


@app.route("/api/script-engine/approve", methods=["POST"])
def api_script_engine_approve():
    from script_engine import ScriptPipeline
    data = request.get_json(force=True) or {}
    try:
        record = ScriptPipeline().approve_stage(
            data.get("project"), data.get("stage"), data.get("output"))
        return jsonify(record)
    except Exception as exc:
        from runware_client import redact_sensitive
        return jsonify({"error": redact_sensitive(str(exc))[:400],
                        "diagnostics": getattr(exc, "diagnostics", [])}), 400


@app.route("/api/script-engine/workflow/<project>")
def api_script_engine_workflow(project):
    from script_engine import ScriptPipeline
    return jsonify(ScriptPipeline().workflow(project))


@app.route("/api/voices/edge")
def api_edge_voices():
    """Current free Hindi/Urdu Edge voices with an offline fallback list."""
    return jsonify(providers.edge_voice_options(force=request.args.get("refresh") == "1"))


@app.route("/api/voices/google")
def api_google_voices():
    """Supported Hindi Google Cloud voice presets and configuration status."""
    return jsonify(providers.google_voice_options())


@app.route("/api/voices/elevenlabs")
def api_elevenlabs_voices():
    """Sanitized, story-ranked voices available to the configured account."""
    try:
        force = request.args.get("refresh") == "1"
        return jsonify(providers.elevenlabs_voice_options(force=force))
    except Exception as exc:
        return jsonify({"available": False, "voices": [],
                        "error": str(exc)[:240]}), 503


@app.route("/api/characters3d/validation")
def api_characters3d_validation():
    """Read-only capability report for every Three.js character GLB."""
    import os
    import char3d_lib
    requested = {value.strip().lower() for value in request.args.get("packages", "").split(",") if value.strip()}
    entries = None
    if requested:
        entries = [entry for entry in char3d_lib.load()
                   if os.path.splitext(os.path.basename(str(entry.get("blend") or "")))[0].lower()
                   in requested]
    return jsonify(char3d_lib.validation_report(entries=entries))


@app.route("/api/character-catalog")
def api_character_catalog():
    """Unified SBZ/Quaternius catalog; unsafe inventory stays non-selectable."""
    import character_catalog
    return jsonify(character_catalog.catalog())


@app.route("/api/asset-catalog")
def api_asset_catalog():
    """Browse integrated and staged local environment/prop assets."""
    import asset_catalog
    return jsonify(asset_catalog.catalog())


@app.route("/api/suggest-style", methods=["POST"])
def api_suggest_style():
    script = (request.get_json(force=True) or {}).get("script", "")
    return jsonify({"style": styles.suggest_style(script)})


@app.route("/api/cost", methods=["POST"])
def api_cost():
    d = request.get_json(force=True) or {}
    return jsonify(providers.estimate_cost(
        d.get("scenes", 6), d.get("lines", 6), d.get("chars", 2)))


@app.route("/api/generate", methods=["POST"])
def api_generate():
    data = request.get_json(force=True) or {}
    script = (data.get("script") or "").strip()
    if len(script) < 10:
        return jsonify({"error": "Script bohat chhota hai"}), 400
    settings = data.get("settings") or {}
    parsed = data.get("parsed")   # preview se edit hua plan (optional)
    job_id = str(uuid.uuid4())
    # stable project folder + job.json (crash/loadshedding recovery ke liye)
    import projects_mgr, os as _os, time as _t
    proj_name = f"project-{int(_t.time())}"
    proj_dir = _os.path.join(config.PROJECTS_DIR, proj_name)
    _os.makedirs(proj_dir, exist_ok=True)
    started_at = round(_t.time(), 3)
    projects_mgr.save_job(proj_dir, name=proj_name, script=script, settings=settings,
                          job_id=job_id, project=proj_name, state="running", stage="story",
                          stage_label=STAGE_LABEL["story"], i=0, total=1,
                          message="Preparing story analysis...", started_at=started_at,
                          heartbeat_at=started_at, owner_pid=os.getpid(),
                          instance_id=INSTANCE_ID)
    JOBS[job_id] = {"state": "running", "stage": "story", "stage_label": "Shuru...",
                    "i": 0, "total": 1, "message": "", "result": None, "error": None,
                    "project": proj_name, "started_at": started_at,
                    "progress_updated_at": started_at}
    threading.Thread(target=_run, args=(job_id, script, settings, parsed, proj_name),
                     daemon=True).start()
    return jsonify({"job_id": job_id, "project": proj_name})


@app.route("/api/project/<name>")
def api_project_detail(name):
    """Purana project load karo — script + plan wapas editor mein (kaam jari rakhne ko)."""
    import projects_mgr, os as _os, json as _j
    pdir = _os.path.join(config.PROJECTS_DIR, name)
    if not _os.path.isdir(pdir):
        return jsonify({"error": "Project nahi mila"}), 404
    job = projects_mgr.load_job(name) or {}
    parsed = None
    sp = _os.path.join(pdir, "story.json")
    if _os.path.exists(sp):
        try:
            parsed = _j.load(open(sp, encoding="utf-8"))
            import story_parser
            story_parser.normalize_parsed_directions(parsed)
        except Exception:
            pass
    script = job.get("script", "")
    if not script and parsed:                    # purane projects: plan se script wapas banao
        lines = []
        for sc in parsed.get("scenes", []):
            lines.append(f"[Scene: {sc.get('location', '')}]")
            for ln in sc.get("lines", []):
                em = ln.get("emotion")
                pre = f"({em}) " if em and em != "neutral" else ""
                lines.append(f"{ln.get('speaker')}: {pre}{ln.get('text', '')}")
        script = "\n".join(lines)
    has_video = _os.path.exists(_os.path.join(pdir, "final.mp4"))
    title = (parsed or {}).get("title") or job.get("title") or name
    return jsonify({"name": name, "title": title, "script": script,
                    "settings": job.get("settings") or {}, "parsed": parsed,
                    "has_video": has_video,
                    "video_rel": name + "/final.mp4" if has_video else None})


@app.route("/api/project/<name>/open-folder", methods=["POST"])
def api_open_project_folder(name):
    """Open a validated local project directory in Windows Explorer."""
    import os
    if name != os.path.basename(name):
        return jsonify({"error": "Project name invalid hai"}), 400
    project_dir = os.path.abspath(os.path.join(config.PROJECTS_DIR, name))
    projects_root = os.path.abspath(config.PROJECTS_DIR)
    if os.path.commonpath([projects_root, project_dir]) != projects_root:
        return jsonify({"error": "Project path invalid hai"}), 400
    if not os.path.isdir(project_dir):
        return jsonify({"error": "Project folder nahi mila"}), 404
    try:
        os.startfile(project_dir)
    except (AttributeError, OSError) as exc:
        return jsonify({"error": f"Folder open nahi hua: {exc}"}), 500
    return jsonify({"ok": True})


@app.route("/api/stop/<job_id>", methods=["POST"])
def api_stop(job_id):
    """Chalti hui generation STOP karo — abhi wala Blender line kill, loop ruk jaye.
    Jitna ban chuka wo project mein safe (resume ho sakta)."""
    j = JOBS.get(job_id)
    if not j:
        import projects_mgr
        durable = projects_mgr.find_job(job_id)
        if durable and durable.get("state") in {"interrupted", "error", "stopped"}:
            return jsonify({"ok": True, "project": durable.get("project"),
                            "already_stopped": True})
        return jsonify({"error": "Job is not active on this server. Resume it from Projects."}), 409
    j["cancel"] = True
    j["message"] = "Stopping safely after the current operation..."
    return jsonify({"ok": True, "project": j.get("project")})


@app.route("/api/resumable")
def api_resumable():
    """Adhoore projects jo resume ho sakte (crash/close ke baad)."""
    import projects_mgr
    return jsonify(projects_mgr.resumable_projects())


@app.route("/api/resume/<name>", methods=["POST"])
def api_resume(name):
    """Project ko jahan tak bana hai wahin se complete karo (voices/backgrounds/clips
    cache se skip). job.json na bhi ho to story.json (plan) se resume."""
    import projects_mgr, os as _os, json as _j, time as _t
    proj_dir = _os.path.join(config.PROJECTS_DIR, name)
    if not _os.path.isdir(proj_dir):
        return jsonify({"error": "Project nahi mila"}), 404
    job = projects_mgr.load_job(name) or {}
    script = job.get("script", "")
    settings = job.get("settings") or {}
    parsed = None
    sp = _os.path.join(proj_dir, "story.json")   # edited plan (costumes/accessories samet)
    if _os.path.exists(sp):
        try:
            parsed = _j.load(open(sp, encoding="utf-8"))
        except Exception:
            pass
    # purane project (job.json nahi): plan se script wapas banao
    if not script and parsed:
        _lines = []
        for _sc in parsed.get("scenes", []):
            _lines.append(f"[Scene: {_sc.get('location', '')}]")
            for _ln in _sc.get("lines", []):
                _em = _ln.get("emotion")
                _pre = f"({_em}) " if _em and _em != "neutral" else ""
                _lines.append(f"{_ln.get('speaker')}: {_pre}{_ln.get('text', '')}")
        script = "\n".join(_lines)
    if not parsed and len(script) < 10:
        return jsonify({"error": "Resume ke liye data nahi (na plan na script)"}), 400
    existing_age = projects_mgr.job_age_seconds(job)
    if job.get("state") == "running" and existing_age <= projects_mgr.STALE_JOB_SECONDS:
        return jsonify({"error": "This project is already running in the active app instance."}), 409
    job_id = str(uuid.uuid4())
    started_at = round(_t.time(), 3)
    JOBS[job_id] = {"state": "running", "stage": "story", "stage_label": "Resume...",
                    "i": 0, "total": 1, "message": "Resume ho raha...", "result": None,
                    "error": None, "project": name, "started_at": started_at,
                    "progress_updated_at": started_at}
    projects_mgr.save_job(proj_dir, state="running", job_id=job_id, project=name,
                          stage="story", stage_label="Resume", i=0, total=1,
                          message="Resuming cached project...", started_at=started_at,
                          heartbeat_at=started_at, owner_pid=os.getpid(),
                          instance_id=INSTANCE_ID, error=None)
    threading.Thread(target=_run, args=(job_id, script, settings, parsed, name),
                     daemon=True).start()
    return jsonify({"job_id": job_id, "project": name})


@app.route("/api/preview", methods=["POST"])
def api_preview():
    """Script parse + character assignment — video se pehle plan (editable) dikhane ke liye."""
    import story_parser, duration_planner, os as _os
    data = request.get_json(force=True) or {}
    script = (data.get("script") or "").strip()
    if len(script) < 10:
        return jsonify({"error": "Script bohat chhota hai"}), 400
    try:
        parsed = story_parser.parse_script(script)
        parsed, scenes_auto_generated = duration_planner.auto_segment_scenes(
            parsed, script, selected=data.get("target_duration", "1min"))
        duration_info = duration_planner.duration_analysis(
            script, parsed, selected=data.get("target_duration", "1min"))
    except Exception as e:
        return jsonify({"error": str(e)[:400]}), 500

    import character_performance
    character_performance.annotate_story_requirements(parsed)
    selected_library = str(data.get("character_library") or parsed.get("character_library") or "sbz").strip().lower()
    if selected_library not in {"sbz", "quaternius"}:
        selected_library = "sbz"
    # A library tab is a render constraint, not merely a catalog filter.
    parsed["character_library"] = selected_library
    chars = parsed.get("characters", [])
    # 3D library se assign (jo asal render mein use hota) -> preview = output
    import char3d_lib
    blend3d = char3d_lib.assign(chars, library=selected_library)  # {id: blend_path}
    manifest_by_slug = {
        _os.path.splitext(_os.path.basename(str(entry.get("blend") or "")))[0].lower(): entry
        for entry in char3d_lib.load()
    }
    out_chars = []
    performance_by_character = {}
    for ch in chars:
        bp = blend3d.get(ch["id"]) or ""
        slug = _os.path.splitext(_os.path.basename(bp))[0] if bp else ""
        avatar = f"/char3d-thumb/{slug}" if slug else None
        entry = manifest_by_slug.get(slug.lower())
        capability = char3d_lib.validate_entry(entry) if entry else None
        performance = (character_performance.profile_for_entry(entry) if entry else
                       character_performance.policy_for_tier("SKELETAL_BASIC", name=ch.get("name")))
        performance_by_character[ch["id"]] = performance
        out_chars.append({"id": ch["id"], "name": ch.get("name"), "gender": ch.get("gender"),
                          "voice": ch.get("voice"), "package": slug, "avatar": avatar,
                          "capability": capability, "performance": performance,
                          "casting_decision": character_performance.casting_decision(ch, performance)})

    performance_warnings = []
    for scene in parsed.get("scenes", []):
        for line in scene.get("lines", []):
            performance = performance_by_character.get(line.get("speaker"))
            if not performance:
                continue
            words = len(str(line.get("text") or "").split())
            if (performance.get("speech_mode") in {"body_only", "static"}
                    and words > int(performance.get("max_spoken_words") or 0)):
                performance_warnings.append({
                    "scene": scene.get("id"), "speaker": line.get("speaker"),
                    "speech_mode": performance.get("speech_mode"), "words": words,
                    "message": (
                        f"{performance.get('name')} has no facial lip-sync controls; "
                        "keep this performance action-led and use a medium/body shot."
                    ),
                })

    import story_templates, production_director
    dialogue_cast_recommendations = character_performance.dialogue_cast_recommendations()
    motion_preflight = production_director.preview_motion_audit(parsed, blend3d)
    return jsonify({"title": parsed.get("title"), "language": parsed.get("language"),
                    "characters": out_chars, "scenes": parsed.get("scenes", []),
                    "veggies": story_templates.available_characters(),
                    "performance_warnings": performance_warnings,
                    "dialogue_cast_recommendations": dialogue_cast_recommendations,
                    "motion_preflight": motion_preflight,
                    "scenes_auto_generated": scenes_auto_generated,
                    "duration_analysis": duration_info,
                    "auto_direction_summary": {
                        "directed_lines": sum(bool(line.get("action"))
                                              for scene in parsed.get("scenes", [])
                                              for line in scene.get("lines", [])),
                        "automatic_actions": sum(
                            line.get("action_source") == "automatic_story_direction"
                            for scene in parsed.get("scenes", [])
                            for line in scene.get("lines", [])),
                    },
                    "parsed": parsed})


@app.route("/api/costumes")
def api_costumes():
    import costumes
    return jsonify(costumes.list_costumes())


@app.route("/api/accessories")
def api_accessories():
    import accessories
    return jsonify(accessories.list_accessories())


@app.route("/api/held")
def api_held():
    import accessories
    return jsonify(accessories.list_held())


@app.route("/char-img/<path:filename>")
def serve_char_img(filename):
    import os as _os
    return send_from_directory(_os.path.join(config.BASE_DIR, "characters"), filename)


@app.route("/char3d-thumb/<name>")
def serve_char3d_thumb(name):
    """3D character ka rigged thumbnail (blender/rigged/<slug>.png)."""
    import os as _os
    d = _os.path.join(config.BASE_DIR, "blender", "rigged")
    fn = name if name.endswith(".png") else name + ".png"
    if _os.path.exists(_os.path.join(d, fn)):
        return send_from_directory(d, fn)
    return ("", 404)


@app.route("/api/status/<job_id>")
def api_status(job_id):
    job = JOBS.get(job_id)
    if not job:
        import projects_mgr
        job = projects_mgr.find_job(job_id)
        if not job:
            return jsonify({"error": "job nahi mila"}), 404
        job = dict(job)
        job["durable"] = True
        if job.get("state") == "running" and projects_mgr.job_age_seconds(job) > projects_mgr.STALE_JOB_SECONDS:
            job.update(state="interrupted", stage="interrupted",
                       message="Backend session ended. Resume from Projects to continue cached work.")
    return jsonify(job)


# ---------------- P7: Projects, Templates, Batch ----------------
@app.route("/api/projects")
def api_projects():
    import projects_mgr
    return jsonify(projects_mgr.list_projects())


@app.route("/api/projects/<name>", methods=["DELETE"])
def api_delete_project(name):
    import projects_mgr
    return jsonify({"deleted": projects_mgr.delete_project(name)})


@app.route("/api/templates")
def api_templates():
    import projects_mgr
    return jsonify(projects_mgr.list_templates())


@app.route("/api/template", methods=["POST"])
def api_save_template():
    import projects_mgr
    d = request.get_json(force=True) or {}
    name = projects_mgr.save_template(d.get("name", "preset"), d.get("settings", {}))
    return jsonify({"saved": name})


@app.route("/api/template/<name>")
def api_load_template(name):
    import projects_mgr
    t = projects_mgr.load_template(name)
    return jsonify(t or {})


@app.route("/api/batch", methods=["POST"])
def api_batch():
    import batch as batch_mod
    data = request.get_json(force=True) or {}
    folder = (data.get("folder") or "").strip()
    if not folder or not __import__("os").path.isdir(folder):
        return jsonify({"error": "Folder nahi mila"}), 400
    settings = data.get("settings") or {}
    job_id = str(uuid.uuid4())
    JOBS[job_id] = {"state": "running", "stage": "batch", "message": "Batch shuru...",
                    "i": 0, "total": 0, "results": [], "error": None}

    def run():
        def on_each(i, total, name, res):
            JOBS[job_id].update(i=i, total=total, message=f"{name}: {res['status']}")
            JOBS[job_id]["results"].append(res)
        try:
            batch_mod.batch_generate(folder, settings=settings, on_each=on_each)
            JOBS[job_id].update(state="done")
        except Exception as e:
            JOBS[job_id].update(state="error", error=str(e))
    threading.Thread(target=run, daemon=True).start()
    return jsonify({"job_id": job_id})


# ---------------- P9: Export & Publish ----------------
@app.route("/api/platforms")
def api_platforms():
    import export
    return jsonify(list(export.PLATFORM_PRESETS.keys()))


@app.route("/api/export/<name>", methods=["POST"])
def api_export(name):
    import os
    import json as _json
    import export
    pdir = os.path.join(config.PROJECTS_DIR, name)
    story_p = os.path.join(pdir, "story.json")
    tl_p = os.path.join(pdir, "timeline.json")
    if not (os.path.exists(story_p) and os.path.exists(tl_p)):
        return jsonify({"error": "project nahi mila"}), 404
    parsed = _json.load(open(story_p, encoding="utf-8"))
    timeline = _json.load(open(tl_p, encoding="utf-8"))
    script = "\n".join(ln.get("text", "") for sc in parsed.get("scenes", [])
                       for ln in sc.get("lines", []))
    want = (request.get_json(silent=True) or {}).get("want", ["srt", "audio", "thumbnail", "seo"])
    out = export.export_all(pdir, timeline, parsed, script, want=want)
    # paths ko relative banao (download ke liye)
    rel = {}
    for k, v in out.items():
        rel[k] = v if k == "seo" else (name + "/" + os.path.basename(v) if v else None)
    return jsonify(rel)


# ---------------- P11: AI Assistant + Plugins ----------------
@app.route("/api/analyze", methods=["POST"])
def api_analyze():
    import assistant
    d = request.get_json(force=True) or {}
    return jsonify(assistant.analyze(d.get("script", ""), d.get("language", "urdu")))


@app.route("/api/improve", methods=["POST"])
def api_improve():
    import assistant
    d = request.get_json(force=True) or {}
    return jsonify({"script": assistant.improve_script(
        d.get("script", ""), d.get("language", "urdu"))})


@app.route("/api/plugins")
def api_plugins():
    import plugins
    return jsonify(plugins.list_plugins())


@app.route("/api/plugins/install", methods=["POST"])
def api_install_plugin():
    import plugins
    d = request.get_json(force=True) or {}
    if d.get("folder"):
        return jsonify(plugins.install_plugin(d["folder"]))
    return jsonify({"installed": plugins.install_all()})


@app.route("/api/story-templates")
def api_story_templates():
    import story_templates
    return jsonify(story_templates.all_templates())


@app.route("/api/characters")
def api_characters():
    import story_templates
    return jsonify(story_templates.available_characters())


@app.route("/api/story-templates/generate", methods=["POST"])
def api_story_template_generate():
    import story_templates
    d = request.get_json(force=True) or {}
    tid = d.get("template_id")
    if not tid:
        return jsonify({"error": "template_id chahiye"}), 400
    try:
        script = story_templates.generate_from_template(
            tid, topic=d.get("topic", ""), language=d.get("language", "roman_urdu"),
            characters=d.get("characters"), lines=d.get("lines"),
            length=d.get("length", "medium"), library=d.get("character_library"))
        return jsonify({"script": script})
    except Exception as e:
        return jsonify({"error": str(e)[:400]}), 500


@app.route("/api/freeform", methods=["POST"])
def api_freeform():
    """Phase 2 — bina template, seedha idea se script."""
    import story_templates, duration_planner
    d = request.get_json(force=True) or {}
    idea = (d.get("idea") or "").strip()
    if not idea:
        return jsonify({"error": "Idea likhein (kis cheez par video?)"}), 400
    try:
        length = duration_planner.normalize_duration(d.get("length", "1min"))
        if duration_planner.use_longform(length):
            return jsonify(story_templates.generate_longform(
                idea, language=d.get("language", "roman_urdu"),
                characters=d.get("characters"), minutes=length,
                genre=d.get("genre", "auto"), library=d.get("character_library")))
        return jsonify(story_templates.generate_freeform(
            idea, language=d.get("language", "roman_urdu"),
            characters=d.get("characters"), length=length,
            lines=d.get("lines"), genre=d.get("genre", "auto"),
            quality=d.get("quality", "pro"), library=d.get("character_library")))
    except Exception as e:
        return jsonify({"error": str(e)[:400]}), 500


@app.route("/api/metadata", methods=["POST"])
def api_metadata():
    """Track C — script se YouTube package (titles/description/tags/thumbnail...)."""
    import metadata
    d = request.get_json(force=True) or {}
    script = (d.get("script") or "").strip()
    if len(script) < 20:
        return jsonify({"error": "Pehle script banayein (bohat chhota hai)"}), 400
    return jsonify(metadata.generate(script, language=d.get("language", "roman_urdu"),
                                     platform=d.get("platform", "youtube"),
                                     promise=d.get("promise", ""),
                                     title_hint=d.get("title", "")))


@app.route("/api/longform", methods=["POST"])
def api_longform():
    """Phase 3 — lambi multi-scene story (3-8 min)."""
    import story_templates
    d = request.get_json(force=True) or {}
    idea = (d.get("idea") or "").strip()
    if not idea:
        return jsonify({"error": "Idea likhein (kis cheez par lambi video?)"}), 400
    try:
        return jsonify(story_templates.generate_longform(
            idea, language=d.get("language", "roman_urdu"),
            characters=d.get("characters"), minutes=d.get("minutes", "5min"),
            genre=d.get("genre", "auto"), library=d.get("character_library")))
    except Exception as e:
        return jsonify({"error": str(e)[:400]}), 500


# ---------------- Phase 4: Recurring characters + Series ----------------
@app.route("/api/characters-lib")
def api_characters_lib():
    import series
    return jsonify(series.list_characters())


@app.route("/api/characters-lib", methods=["POST"])
def api_add_character():
    import series
    d = request.get_json(force=True) or {}
    try:
        return jsonify(series.add_character(
            d.get("name", ""), trait=d.get("trait", ""), gender=d.get("gender", "male"),
            catchphrase=d.get("catchphrase", ""), role=d.get("role", ""), cid=d.get("id")))
    except Exception as e:
        return jsonify({"error": str(e)[:300]}), 400


@app.route("/api/characters-lib/<cid>", methods=["DELETE"])
def api_del_character(cid):
    import series
    return jsonify({"deleted": series.delete_character(cid)})


@app.route("/api/series")
def api_list_series():
    import series
    return jsonify(series.list_series())


@app.route("/api/series/<sid>")
def api_get_series(sid):
    import series
    return jsonify(series.get_series(sid) or {})


@app.route("/api/series", methods=["POST"])
def api_create_series():
    import series
    d = request.get_json(force=True) or {}
    try:
        return jsonify(series.create_series(
            d.get("name", ""), premise=d.get("premise", ""), genre=d.get("genre", "auto"),
            language=d.get("language", "roman_urdu"), cast=d.get("cast")))
    except Exception as e:
        return jsonify({"error": str(e)[:300]}), 400


@app.route("/api/series/<sid>", methods=["PUT"])
def api_update_series(sid):
    import series
    d = request.get_json(force=True) or {}
    try:
        return jsonify(series.update_series(sid, **d))
    except Exception as e:
        return jsonify({"error": str(e)[:300]}), 400


@app.route("/api/series/<sid>", methods=["DELETE"])
def api_delete_series(sid):
    import series
    return jsonify({"deleted": series.delete_series(sid)})


@app.route("/api/series/<sid>/episode", methods=["POST"])
def api_generate_episode(sid):
    import series
    d = request.get_json(force=True) or {}
    try:
        return jsonify(series.generate_episode(
            sid, idea=d.get("idea", ""), length=d.get("length", "medium"),
            save_episode=d.get("save", True)))
    except Exception as e:
        return jsonify({"error": str(e)[:400]}), 500


@app.route("/api/test-runware", methods=["POST"])
def api_test_runware():
    """Runware API health check — LLM + Image endpoints test (latency + errors)."""
    import time
    from runware_client import post_tasks, new_uuid, redact_sensitive
    d = request.get_json(silent=True) or {}
    do_img = d.get("image", True)
    requested_model = str(d.get("model") or "").strip()
    available_models = {item["model"] for item in providers.llm_model_options()
                        if item.get("provider") == "runware"}
    llm_model = requested_model if requested_model in available_models else providers._selected_model(
        "runware", config.TEXT_MODEL)

    key = config.RUNWARE_API_KEY
    tests = {"key": {"ok": bool(key and key != "your_runware_key_here"),
                     "masked": "[configured]" if key else "(none)"}}
    if not tests["key"]["ok"]:
        return jsonify({"ok": False, "tests": tests, "msg": "API key .env mein nahi mili"})

    # --- LLM (textInference) ---
    t0 = time.time()
    try:
        r = post_tasks([{"taskType": "textInference", "taskUUID": new_uuid(),
                         "model": llm_model,
                         "settings": {"maxTokens": 24, "temperature": 0.1},
                         "messages": [{"role": "user", "content": "Reply with exactly: API OK"}]}],
                       timeout=60)
        tests["llm"] = {"ok": True, "ms": int((time.time() - t0) * 1000),
                        "model": llm_model,
                        "sample": (r[0].get("text", "") or "").strip()[:40]}
    except Exception as e:
        tests["llm"] = {"ok": False, "ms": int((time.time() - t0) * 1000),
                        "model": llm_model, "error": redact_sensitive(str(e))[:400]}

    # --- Image (imageInference) — chhoti 512 test ---
    if do_img:
        t0 = time.time()
        try:
            r = post_tasks([{"taskType": "imageInference", "taskUUID": new_uuid(),
                             "model": config.IMAGE_MODEL, "positivePrompt": "a red apple, simple",
                             "width": 512, "height": 512, "numberResults": 1,
                             "outputType": "URL", "outputFormat": "PNG"}], timeout=120)
            url = r[0].get("imageURL", "")
            tests["image"] = {"ok": bool(url), "ms": int((time.time() - t0) * 1000),
                              "model": config.IMAGE_MODEL, "url": url}
        except Exception as e:
            tests["image"] = {"ok": False, "ms": int((time.time() - t0) * 1000),
                              "model": config.IMAGE_MODEL,
                              "error": redact_sensitive(str(e))[:400]}

    overall = tests["llm"]["ok"] and (not do_img or tests.get("image", {}).get("ok"))
    return jsonify({"ok": overall, "tests": tests})


@app.route("/projects/<path:filename>")
def serve_project(filename):
    return send_from_directory(config.PROJECTS_DIR, filename)


if __name__ == "__main__":
    url = "http://127.0.0.1:5050"
    if not _acquire_instance_lock():
        print("SBZ Studio backend is already running on this machine.", flush=True)
        raise SystemExit(0)
    try:
        import projects_mgr
        recovered = projects_mgr.recover_stale_jobs()
        if recovered:
            print(f"Recovered {len(recovered)} interrupted project(s) for safe resume.", flush=True)
    except Exception as exc:
        print(f"Stale-job recovery warning: {exc}", flush=True)
    if os.getenv("NO_BROWSER") != "1":   # Electron khud window kholta hai
        threading.Timer(1.2, lambda: webbrowser.open(url)).start()
    print(f"\n🎬 SBZ Studio UI: {url}\n")
    app.run(host="127.0.0.1", port=5050, debug=False, threaded=True,
            use_reloader=False)
