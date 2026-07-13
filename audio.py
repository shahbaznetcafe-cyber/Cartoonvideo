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
    return (glob.glob(os.path.join(folder, "*.mp3")) +
            glob.glob(os.path.join(folder, "*.MP3")) +
            glob.glob(os.path.join(folder, "*.wav")))


def select_music(scene_moods):
    """Video ke dominant mood ke hisab se ek music track chuno (ya None)."""
    if not config.MUSIC_MOOD_AUTO:
        files = _find(MUSIC_DIR)
        return files[0] if files else None

    cat = "calm"
    if scene_moods:
        dom = Counter([m or "neutral" for m in scene_moods]).most_common(1)[0][0]
        cat = MOOD_MUSIC.get(dom, "calm")

    for d in (os.path.join(MUSIC_DIR, cat), MUSIC_DIR):
        files = _find(d)
        if files:
            return files[0]
    return None


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
