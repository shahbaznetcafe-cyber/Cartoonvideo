"""
P11 — Plugin System. plugins/ folder mein packs daalein:
har plugin ek folder hai jisme plugin.json hai (type: characters|music|styles|template).
install karne par woh sahi jagah register/copy ho jata hai.
"""
import json
import os
import shutil

import config

PLUGINS_DIR = os.path.join(config.BASE_DIR, "plugins")
os.makedirs(PLUGINS_DIR, exist_ok=True)


def list_plugins():
    """plugins/ ke saare packs + unke manifest."""
    out = []
    for name in os.listdir(PLUGINS_DIR):
        pdir = os.path.join(PLUGINS_DIR, name)
        manifest = os.path.join(pdir, "plugin.json")
        if os.path.isdir(pdir) and os.path.exists(manifest):
            try:
                m = json.load(open(manifest, encoding="utf-8"))
                out.append({"folder": name, "name": m.get("name", name),
                            "type": m.get("type", "?"),
                            "description": m.get("description", ""),
                            "path": pdir})
            except Exception as e:
                out.append({"folder": name, "error": str(e)})
    return out


def install_plugin(plugin_folder):
    """Ek plugin ko register/copy karo (sahi jagah)."""
    pdir = os.path.join(PLUGINS_DIR, plugin_folder) if not os.path.isabs(plugin_folder) else plugin_folder
    m = json.load(open(os.path.join(pdir, "plugin.json"), encoding="utf-8"))
    typ = m.get("type")

    if typ == "characters":
        # PNGs -> characters/, entries -> characters.json
        import character_library as cl
        os.makedirs(cl.LIB_DIR, exist_ok=True)
        manifest = cl._load_manifest()
        existing = {e.get("file") for e in manifest}
        added = 0
        for ch in m.get("characters", []):
            src = os.path.join(pdir, ch["file"])
            if os.path.exists(src):
                shutil.copy(src, os.path.join(cl.LIB_DIR, os.path.basename(ch["file"])))
                ch["file"] = os.path.basename(ch["file"])
                if ch["file"] not in existing:
                    manifest.append(ch); added += 1
        json.dump(manifest, open(cl.MANIFEST, "w", encoding="utf-8"),
                  ensure_ascii=False, indent=2)
        return {"type": typ, "added": added}

    if typ == "music":
        mood = m.get("mood", "calm")
        dest = os.path.join(config.BASE_DIR, "assets", "music", mood)
        os.makedirs(dest, exist_ok=True)
        n = 0
        for f in m.get("files", []):
            src = os.path.join(pdir, f)
            if os.path.exists(src):
                shutil.copy(src, dest); n += 1
        return {"type": typ, "mood": mood, "added": n}

    if typ == "styles":
        import styles
        custom = styles._load_custom()
        custom.update(m.get("styles", {}))
        json.dump(custom, open(styles.CUSTOM_FILE, "w", encoding="utf-8"),
                  ensure_ascii=False, indent=2)
        return {"type": typ, "added": len(m.get("styles", {}))}

    if typ == "template":
        import projects_mgr
        projects_mgr.save_template(m.get("name", "plugin-preset"), m.get("settings", {}))
        return {"type": typ, "added": 1}

    return {"error": f"unknown plugin type: {typ}"}


def install_all():
    """plugins/ ke saare packs install karo."""
    results = []
    for p in list_plugins():
        if "error" not in p:
            try:
                results.append({"name": p["name"], **install_plugin(p["folder"])})
            except Exception as e:
                results.append({"name": p["name"], "error": str(e)})
    return results
