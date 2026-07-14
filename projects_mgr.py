"""
P7 — Project Management + Templates.
Projects projects/<name>/ folder mein hain (story.json, timeline.json, assets, chunks, final.mp4).
Templates = settings presets (templates/ folder).
"""
import json
import os
import shutil
import time

import config

TEMPLATES_DIR = os.path.join(config.BASE_DIR, "templates_presets")
os.makedirs(TEMPLATES_DIR, exist_ok=True)


# ---------------- Projects ----------------
def list_projects():
    """Saare projects + unka metadata (naya pehle)."""
    out = []
    for name in os.listdir(config.PROJECTS_DIR):
        pdir = os.path.join(config.PROJECTS_DIR, name)
        if not os.path.isdir(pdir):
            continue
        meta_path = os.path.join(pdir, "project_metadata.json")
        story_path = os.path.join(pdir, "story.json")
        info = {"name": name, "title": name, "scenes": 0, "characters": 0,
                "created": "", "duration": 0,
                "has_video": os.path.exists(os.path.join(pdir, "final.mp4"))}
        if os.path.exists(meta_path):
            try:
                info.update(json.load(open(meta_path, encoding="utf-8")))
            except Exception:
                pass
        elif os.path.exists(story_path):
            try:
                s = json.load(open(story_path, encoding="utf-8"))
                info["title"] = s.get("title", name)
                info["scenes"] = len(s.get("scenes", []))
                info["characters"] = len(s.get("characters", []))
            except Exception:
                pass
        timeline_path = os.path.join(pdir, "timeline.json")
        if os.path.exists(timeline_path):
            try:
                timeline = json.load(open(timeline_path, encoding="utf-8"))
                info["duration"] = round(sum(float(item.get("duration", 0) or 0)
                                             for item in timeline), 2)
            except (OSError, ValueError, TypeError, json.JSONDecodeError):
                pass
        job = load_job(name) or {}
        info["state"] = "complete" if info["has_video"] else job.get("state", "draft")
        info["stage"] = job.get("stage", "")
        info["updated"] = job.get("updated", "")
        info["mtime"] = os.path.getmtime(pdir)
        out.append(info)
    out.sort(key=lambda x: x.get("mtime", 0), reverse=True)
    return out


def save_metadata(proj_dir, parsed, settings, stats):
    meta = {
        "title": parsed.get("title", "Untitled"),
        "created": time.strftime("%Y-%m-%d %H:%M"),
        "characters": stats[0], "scenes": stats[1], "lines": stats[2],
        "settings": settings or {},
        "video": os.path.basename(proj_dir) + "/final.mp4",
    }
    json.dump(meta, open(os.path.join(proj_dir, "project_metadata.json"),
                         "w", encoding="utf-8"), ensure_ascii=False, indent=2)


def delete_project(name):
    pdir = os.path.join(config.PROJECTS_DIR, name)
    if os.path.isdir(pdir):
        shutil.rmtree(pdir)
        return True
    return False


# ---------------- Resume / crash-recovery (job.json) ----------------
def _job_path(proj_dir):
    return os.path.join(proj_dir, "job.json")


def save_job(proj_dir, **fields):
    """Job state disk par (crash/loadshedding ke baad resume ke liye)."""
    os.makedirs(proj_dir, exist_ok=True)
    p = _job_path(proj_dir)
    data = {}
    if os.path.exists(p):
        try:
            data = json.load(open(p, encoding="utf-8"))
        except Exception:
            data = {}
    data.update(fields)
    data["updated"] = time.strftime("%Y-%m-%d %H:%M:%S")
    json.dump(data, open(p, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
    return data


def load_job(name):
    p = _job_path(os.path.join(config.PROJECTS_DIR, name))
    if os.path.exists(p):
        try:
            return json.load(open(p, encoding="utf-8"))
        except Exception:
            pass
    return None


def resumable_projects():
    """Adhoore projects (job chal raha tha par final.mp4 nahi / state running|error)."""
    out = []
    for name in os.listdir(config.PROJECTS_DIR):
        pdir = os.path.join(config.PROJECTS_DIR, name)
        if not os.path.isdir(pdir):
            continue
        job = load_job(name)
        has_final = os.path.exists(os.path.join(pdir, "final.mp4"))
        if job and job.get("state") in ("running", "error") and not has_final:
            # progress hint: kitni voices/clips ban chuki
            done_clips = 0
            cd = os.path.join(pdir, "clips3d")
            if os.path.isdir(cd):
                done_clips = len([f for f in os.listdir(cd)
                                  if f.startswith("line_") and f.endswith(".mp4")])
            out.append({
                "name": name, "title": job.get("title", name),
                "state": job.get("state"), "stage": job.get("stage"),
                "message": job.get("message", ""), "updated": job.get("updated"),
                "done_clips": done_clips,
            })
    out.sort(key=lambda x: x.get("updated", ""), reverse=True)
    return out


def regenerate_scene(proj_name, scene_id):
    """Ek scene ka background + uske chunks delete karo taake re-render fresh ho."""
    pdir = os.path.join(config.PROJECTS_DIR, proj_name)
    removed = []
    bg = os.path.join(pdir, "assets", f"bg_scene{scene_id}.png")
    if os.path.exists(bg):
        os.remove(bg); removed.append(os.path.basename(bg))
    # us scene ke chunks (s{scene}_*) hata do
    chunks_dir = os.path.join(pdir, "chunks")
    if os.path.isdir(chunks_dir):
        for f in os.listdir(chunks_dir):
            if f.startswith(f"s{scene_id}_"):
                os.remove(os.path.join(chunks_dir, f)); removed.append(f)
    return removed


# ---------------- Templates (settings presets) ----------------
def save_template(name, settings):
    safe = "".join(c for c in name if c.isalnum() or c in "-_ ").strip() or "preset"
    path = os.path.join(TEMPLATES_DIR, safe + ".json")
    json.dump(settings, open(path, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
    return safe


def list_templates():
    out = []
    for f in os.listdir(TEMPLATES_DIR):
        if f.endswith(".json"):
            out.append(os.path.splitext(f)[0])
    return sorted(out)


def load_template(name):
    path = os.path.join(TEMPLATES_DIR, name + ".json")
    if os.path.exists(path):
        return json.load(open(path, encoding="utf-8"))
    return None
