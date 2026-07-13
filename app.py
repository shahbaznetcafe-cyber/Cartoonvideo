"""
P8 — SBZ AI Video Studio — Desktop UI (Flask backend).
3-column UI (nav + controls + settings). Saare P1-P6 features wired.
Chalao:  python app.py    (browser khud khulega, ya Electron se .exe)
"""
import sys
import threading
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

STAGE_LABEL = {"story": "Story analyze", "voice": "Voices",
               "asset": "Backgrounds + Characters", "render": "Compositing + Render"}

URDU_VOICES = ["ur-IN-SalmanNeural", "ur-IN-GulNeural",   # Indian Urdu
               "ur-PK-AsadNeural", "ur-PK-UzmaNeural"]     # Pakistani Urdu
ENG_VOICES = ["en-US-GuyNeural", "en-US-AriaNeural", "en-US-JennyNeural"]


def _run(job_id, script, settings, parsed=None, proj_name=None):
    import projects_mgr, os as _os, time as _t, json as _j
    proj_dir = _os.path.join(config.PROJECTS_DIR, proj_name) if proj_name else None
    _last = [0.0]

    def on_progress(stage, i, t, msg):
        JOBS[job_id].update(state="running", stage=stage,
                            stage_label=STAGE_LABEL.get(stage, stage),
                            i=i, total=t, message=msg)
        # job.json disk par (throttled) -> crash ke baad resume
        if proj_dir and (stage == "story" or _t.time() - _last[0] > 4):
            _last[0] = _t.time()
            try:
                projects_mgr.save_job(proj_dir, state="running", stage=stage, message=msg)
            except Exception:
                pass
    try:
        result = builder.build(script, proj_name=proj_name, on_progress=on_progress,
                               settings=settings, parsed=parsed,
                               should_cancel=lambda: JOBS.get(job_id, {}).get("cancel"))
        JOBS[job_id].update(state="done", result=result)
        if proj_dir:
            title = None
            try:
                title = _j.load(open(_os.path.join(proj_dir, "story.json"),
                                     encoding="utf-8")).get("title")
            except Exception:
                pass
            try:
                projects_mgr.save_job(proj_dir, state="done", title=title or proj_name,
                                      result=result)
            except Exception:
                pass
    except Exception as e:
        # STOP (Cancelled) -> 'stopped' (error nahi); partial project resumable rehta
        if type(e).__name__ == "Cancelled":
            JOBS[job_id].update(state="stopped", message="Ruk gaya (resume ho sakta)")
            if proj_dir:
                try:
                    projects_mgr.save_job(proj_dir, state="error", stage="stopped",
                                          message="user ne stop kiya")
                except Exception:
                    pass
            return
        import traceback
        traceback.print_exc()
        JOBS[job_id].update(state="error", error=str(e))
        if proj_dir:
            try:
                projects_mgr.save_job(proj_dir, state="error", error=str(e)[:300])
            except Exception:
                pass


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/api/options")
def api_options():
    """Dropdowns ke liye: styles, voices, providers, defaults."""
    return jsonify({
        "styles": styles.list_styles(),
        "voices": URDU_VOICES + ENG_VOICES,
        "providers": providers.status(),
        "urdu_accents": list(config.VOICE_SETS.keys()),
        "render_engines": ["threejs", "blender"],
        "defaults": {
            "style": config.STYLE, "quality": config.VIDEO_QUALITY,
            "aspect": config.ASPECT, "fps": config.FPS,
            "motion_preset": config.MOTION_PRESET, "render_mode": config.RENDER_MODE,
            "captions": config.CAPTIONS, "urdu_accent": config.URDU_ACCENT,
            "tts_provider": getattr(config, "TTS_PROVIDER", "edge"),
            "elevenlabs_voice_id": getattr(config, "ELEVENLABS_VOICE_ID", ""),
            "elevenlabs_model": getattr(config, "ELEVENLABS_MODEL", "eleven_v3"),
            "render_engine": getattr(config, "RENDER_ENGINE", "threejs"),
            "subtitles_on": getattr(config, "SUBTITLES_ON", True),
            "intro_on": getattr(config, "INTRO_ON", False),
            "outro_on": getattr(config, "OUTRO_ON", True),
        },
    })


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
    import char3d_lib
    return jsonify(char3d_lib.validation_report())


@app.route("/api/suggest-style", methods=["POST"])
def api_suggest_style():
    script = (request.get_json(force=True) or {}).get("script", "")
    return jsonify({"style": styles.suggest_style(script)})


@app.route("/api/cost", methods=["POST"])
def api_cost():
    d = request.get_json(force=True) or {}
    return jsonify(providers.estimate_cost(
        d.get("scenes", 6), d.get("lines", 6), d.get("chars", 2),
        d.get("render_mode", "draft")))


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
    projects_mgr.save_job(proj_dir, name=proj_name, script=script, settings=settings,
                          state="running", stage="story")
    JOBS[job_id] = {"state": "running", "stage": "story", "stage_label": "Shuru...",
                    "i": 0, "total": 1, "message": "", "result": None, "error": None,
                    "project": proj_name}
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


@app.route("/api/stop/<job_id>", methods=["POST"])
def api_stop(job_id):
    """Chalti hui generation STOP karo — abhi wala Blender line kill, loop ruk jaye.
    Jitna ban chuka wo project mein safe (resume ho sakta)."""
    j = JOBS.get(job_id)
    if not j:
        return jsonify({"error": "Job nahi mila"}), 404
    j["cancel"] = True
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
    import projects_mgr, os as _os, json as _j
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
    job_id = str(uuid.uuid4())
    JOBS[job_id] = {"state": "running", "stage": "story", "stage_label": "Resume...",
                    "i": 0, "total": 1, "message": "Resume ho raha...", "result": None,
                    "error": None, "project": name}
    projects_mgr.save_job(proj_dir, state="running")
    threading.Thread(target=_run, args=(job_id, script, settings, parsed, name),
                     daemon=True).start()
    return jsonify({"job_id": job_id, "project": name})


@app.route("/api/preview", methods=["POST"])
def api_preview():
    """Script parse + character assignment — video se pehle plan (editable) dikhane ke liye."""
    import story_parser, character_library, os as _os
    data = request.get_json(force=True) or {}
    script = (data.get("script") or "").strip()
    if len(script) < 10:
        return jsonify({"error": "Script bohat chhota hai"}), 400
    try:
        parsed = story_parser.parse_script(script)
    except Exception as e:
        return jsonify({"error": str(e)[:400]}), 500

    chars = parsed.get("characters", [])
    # 3D library se assign (jo asal render mein use hota) -> preview = output
    import char3d_lib
    blend3d = char3d_lib.assign(chars)              # {id: blend_path}
    manifest_by_slug = {
        _os.path.splitext(_os.path.basename(str(entry.get("blend") or "")))[0].lower(): entry
        for entry in char3d_lib.load()
    }
    out_chars = []
    for ch in chars:
        bp = blend3d.get(ch["id"]) or ""
        slug = _os.path.splitext(_os.path.basename(bp))[0] if bp else ""
        avatar = f"/char3d-thumb/{slug}" if slug else None
        entry = manifest_by_slug.get(slug.lower())
        capability = char3d_lib.validate_entry(entry) if entry else None
        out_chars.append({"id": ch["id"], "name": ch.get("name"), "gender": ch.get("gender"),
                          "voice": ch.get("voice"), "package": slug, "avatar": avatar,
                          "capability": capability})

    import story_templates
    return jsonify({"title": parsed.get("title"), "language": parsed.get("language"),
                    "characters": out_chars, "scenes": parsed.get("scenes", []),
                    "veggies": story_templates.available_characters(),
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
        return jsonify({"error": "job nahi mila"}), 404
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
            length=d.get("length", "medium"))
        return jsonify({"script": script})
    except Exception as e:
        return jsonify({"error": str(e)[:400]}), 500


@app.route("/api/freeform", methods=["POST"])
def api_freeform():
    """Phase 2 — bina template, seedha idea se script."""
    import story_templates
    d = request.get_json(force=True) or {}
    idea = (d.get("idea") or "").strip()
    if not idea:
        return jsonify({"error": "Idea likhein (kis cheez par video?)"}), 400
    try:
        return jsonify(story_templates.generate_freeform(
            idea, language=d.get("language", "roman_urdu"),
            characters=d.get("characters"), length=d.get("length", "medium"),
            lines=d.get("lines"), genre=d.get("genre", "auto"),
            quality=d.get("quality", "pro")))
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
                                     platform=d.get("platform", "youtube")))


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
            genre=d.get("genre", "auto")))
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
    from runware_client import post_tasks, new_uuid
    d = request.get_json(silent=True) or {}
    do_img = d.get("image", True)

    key = config.RUNWARE_API_KEY
    tests = {"key": {"ok": bool(key and key != "your_runware_key_here"),
                     "masked": (key[:5] + "…" + key[-4:]) if key else "(none)"}}
    if not tests["key"]["ok"]:
        return jsonify({"ok": False, "tests": tests, "msg": "API key .env mein nahi mili"})

    # --- LLM (textInference) ---
    t0 = time.time()
    try:
        r = post_tasks([{"taskType": "textInference", "taskUUID": new_uuid(),
                         "model": config.TEXT_MODEL,
                         "settings": {"maxTokens": 24, "temperature": 0.1},
                         "messages": [{"role": "user", "content": "Reply with exactly: API OK"}]}],
                       timeout=60)
        tests["llm"] = {"ok": True, "ms": int((time.time() - t0) * 1000),
                        "model": config.TEXT_MODEL,
                        "sample": (r[0].get("text", "") or "").strip()[:40]}
    except Exception as e:
        tests["llm"] = {"ok": False, "ms": int((time.time() - t0) * 1000),
                        "model": config.TEXT_MODEL, "error": str(e)[:400]}

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
                              "model": config.IMAGE_MODEL, "error": str(e)[:400]}

    overall = tests["llm"]["ok"] and (not do_img or tests.get("image", {}).get("ok"))
    return jsonify({"ok": overall, "tests": tests})


@app.route("/projects/<path:filename>")
def serve_project(filename):
    return send_from_directory(config.PROJECTS_DIR, filename)


if __name__ == "__main__":
    import os
    url = "http://127.0.0.1:5050"
    if os.getenv("NO_BROWSER") != "1":   # Electron khud window kholta hai
        threading.Timer(1.2, lambda: webbrowser.open(url)).start()
    print(f"\n🎬 SBZ Studio UI: {url}\n")
    app.run(host="127.0.0.1", port=5050, debug=False)
