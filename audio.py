"""
P5 — Audio: mood-based music selection + SFX library.
Music: assets/music/<mood>/*.mp3 (ya assets/music/*.mp3). Mood scene se auto-chuna jata hai.
SFX:   assets/sfx/<name>.mp3 — transitions/ambient par auto-insert (jab files hon).
"""
import glob
import os
from collections import Counter

import config

MUSIC_DIR = os.path.join(config.BASE_DIR, "assets", "music")
SFX_DIR = os.path.join(config.BASE_DIR, "assets", "sfx")
OVERLAY_DIR = os.path.join(config.BASE_DIR, "assets", "overlays")
for _d in (MUSIC_DIR, SFX_DIR, OVERLAY_DIR):
    os.makedirs(_d, exist_ok=True)

# scene mood -> music category (folder)
MOOD_MUSIC = {
    "comedy": "happy", "educational": "calm", "drama": "emotional",
    "suspense": "tense", "emotional": "emotional", "action": "energetic",
    "neutral": "calm",
}


def _find(folder):
    files = []
    for extension in ("*.mp3", "*.MP3", "*.wav", "*.WAV", "*.m4a", "*.M4A"):
        files.extend(glob.glob(os.path.join(folder, extension)))
    return sorted(set(files))


def music_catalog():
    """Safe local catalog for the desktop selector; never exposes arbitrary paths."""
    tracks = []
    for root, _dirs, _files in os.walk(MUSIC_DIR):
        for path in _find(root):
            relative = os.path.relpath(path, MUSIC_DIR).replace("\\", "/")
            category = os.path.basename(os.path.dirname(relative)) or "library"
            if "/" not in relative:
                category = "library"
            title = os.path.splitext(os.path.basename(relative))[0].replace("_", " ").replace("-", " ").title()
            tracks.append({"id": relative, "title": title, "category": category, "path": path})
    return sorted(tracks, key=lambda item: (item["category"], item["title"]))


def _manual_track(selection):
    if not selection or str(selection).strip().lower() in ("auto", "mood", "default"):
        return None
    requested = os.path.normpath(str(selection).replace("/", os.sep))
    if os.path.isabs(requested) or requested.startswith(".."):
        return None
    candidate = os.path.abspath(os.path.join(MUSIC_DIR, requested))
    root = os.path.abspath(MUSIC_DIR) + os.sep
    if not candidate.startswith(root) or not os.path.isfile(candidate):
        return None
    return candidate


def select_music(scene_moods, selection=None):
    """Resolve explicit local choice first; otherwise select a deterministic mood match."""
    manual = _manual_track(selection if selection is not None else getattr(config, "MUSIC_TRACK", "auto"))
    if manual:
        return manual
    if not config.MUSIC_MOOD_AUTO:
        files = _find(MUSIC_DIR)
        return files[0] if files else None

    cat = "calm"
    if scene_moods:
        dom = Counter([m or "neutral" for m in scene_moods]).most_common(1)[0][0]
        cat = MOOD_MUSIC.get(dom, "calm")
    for folder in (os.path.join(MUSIC_DIR, cat), MUSIC_DIR):
        files = _find(folder)
        if files:
            return files[0]
    # If there is no exact mood folder, a catalog track is still preferable to silence.
    catalog = music_catalog()
    return catalog[0]["path"] if catalog else None

def get_sfx(name):
    """Named SFX (e.g. 'whoosh','transition','footsteps') — file ya None."""
    if not config.SFX_ENABLED:
        return None
    for ext in (".mp3", ".wav", ".MP3"):
        p = os.path.join(SFX_DIR, name + ext)
        if os.path.exists(p):
            return p
    return None


def overlay_file():
    """config.OVERLAY ya assets/overlays mein pehli video."""
    if config.OVERLAY:
        p = os.path.join(OVERLAY_DIR, config.OVERLAY)
        if os.path.exists(p):
            return p
    vids = glob.glob(os.path.join(OVERLAY_DIR, "*.mp4")) + \
        glob.glob(os.path.join(OVERLAY_DIR, "*.mov"))
    return vids[0] if vids else None
