"""
SBZ AI Video Studio — settings.
Filhal M1 (Story Parser) ke liye sirf Runware LLM chahiye.
"""
import os
from dotenv import load_dotenv

load_dotenv()

RUNWARE_ENDPOINT = "https://api.runware.ai/v1"
RUNWARE_API_KEY = os.getenv("RUNWARE_API_KEY", "").strip()

TEXT_MODEL = os.getenv("TEXT_MODEL", "openai:gpt@5.4-mini")
IMAGE_MODEL = os.getenv("IMAGE_MODEL", "runware:101@1")

# Urdu voice sets (edge-tts, free) — Indian (ur-IN) + Pakistani (ur-PK), per gender
VOICE_SETS = {
    "pakistani": {"male": "ur-PK-AsadNeural", "female": "ur-PK-UzmaNeural",
                  "child": "ur-PK-UzmaNeural", "narrator": "ur-PK-AsadNeural"},
    "indian":    {"male": "ur-IN-SalmanNeural", "female": "ur-IN-GulNeural",
                  "child": "ur-IN-GulNeural", "narrator": "ur-IN-SalmanNeural"},
}
URDU_ACCENT = os.getenv("URDU_ACCENT", "pakistani")   # indian | pakistani
# default edge-tts voices (per gender) — accent ke hisab se
VOICE_MAP = dict(VOICE_SETS.get(URDU_ACCENT, VOICE_SETS["pakistani"]))


def set_urdu_accent(accent):
    """Urdu accent switch (indian/pakistani) — VOICE_MAP in-place update (references valid rahein)."""
    global URDU_ACCENT
    URDU_ACCENT = accent if accent in VOICE_SETS else "pakistani"
    VOICE_MAP.clear(); VOICE_MAP.update(VOICE_SETS[URDU_ACCENT])
    return URDU_ACCENT

# P4 — Style system (163+ styles). Default style; per-scene override bhi ho sakta.
STYLE = os.getenv("STYLE", "3d cartoon")

# Characters: sirf library wale use karo (AI se naye mat banao) — auto-assign per script
LIBRARY_ONLY = os.getenv("LIBRARY_ONLY", "1") == "1"

# Puppet animation: AI-rigged characters ko real animate karo (lip-sync+blink+expression)
PUPPET_ANIMATION = os.getenv("PUPPET_ANIMATION", "1") == "1"

# Story mode: "blender3d" (asli 3D rigged chars) | "puppet" (2D library chars) |
# "cinematic" (har line = full-scene AI image, reference-video style, voiceover-driven)
STORY_MODE = os.getenv("STORY_MODE", "blender3d")

# 3D render engine: "blender" (Eevee headless, ~2-3s/frame) | "threejs" (headless Chrome
# WebGL, ~60ms/frame = ~35x tez, same rigged glb characters). threejs default (tez + koi
# Blender install pe depend nahi karta agar Chrome maujood ho).
RENDER_ENGINE = os.getenv("RENDER_ENGINE", "threejs")   # threejs | blender
# 3D delivery defaults to native Full HD. FAST_PREVIEW still renders at 480p.
BLENDER3D_MAX_H = int(os.getenv("BLENDER3D_MAX_H", "1080"))
# 3D mode fps (kam = tez render, kam frames). 24 cartoon talking ke liye smooth.
BLENDER3D_FPS = int(os.getenv("BLENDER3D_FPS", "24"))
# 3D multi-character: scene ke saare characters (max 3) ek saath frame mein (speaker bolta,
# baaki idle). Off = purana single-speaker-per-shot.
BLENDER3D_MULTI = os.getenv("BLENDER3D_MULTI", "1") == "1"
# Video polish (branding): burned subtitles + intro/outro title cards
SUBTITLES_ON = os.getenv("SUBTITLES_ON", "1") == "1"
INTRO_ON = os.getenv("INTRO_ON", "0") == "1"       # hook-first by default
OUTRO_ON = os.getenv("OUTRO_ON", "1") == "1"
BRAND_NAME = os.getenv("BRAND_NAME", "SBZ Cartoons")     # channel naam (intro/outro par)

# P5 — Audio + overlays
MUSIC_VOLUME = float(os.getenv("MUSIC_VOLUME", "0.12"))   # dialogue ke neeche ducking
# Professional audio master (social-video standards) — audiopost.py
AUDIO_SR = int(os.getenv("AUDIO_SR", "48000"))            # 48 kHz
AUDIO_BITRATE = os.getenv("AUDIO_BITRATE", "384k")        # YouTube stereo delivery
TARGET_LUFS = float(os.getenv("TARGET_LUFS", "-14.5"))    # YouTube-ready speech mix
TARGET_TP = float(os.getenv("TARGET_TP", "-1.0"))         # true peak (dBTP)
AUDIO_MONO = os.getenv("AUDIO_MONO", "0") == "1"          # stereo default (mono agar maange)
SFX_ON = os.getenv("SFX_ON", "1") == "1"                  # scene/action sound effects
MUSIC_MOOD_AUTO = os.getenv("MUSIC_MOOD_AUTO", "1") == "1"
SFX_ENABLED = os.getenv("SFX_ENABLED", "1") == "1"
VIGNETTE = os.getenv("VIGNETTE", "1") == "1"              # cinematic vignette overlay
OVERLAY = os.getenv("OVERLAY", "")                        # assets/overlays/ ki file (sparks/light-leak)
OVERLAY_OPACITY = float(os.getenv("OVERLAY_OPACITY", "0.35"))
VOICE_VOLUME = os.getenv("VOICE_VOLUME", "+0%")

# P3 — Multi-provider engine
LLM_PROVIDER = os.getenv("LLM_PROVIDER", "runware")     # runware|huggingface|groq|gemini|openai|openrouter|together
IMAGE_PROVIDER = os.getenv("IMAGE_PROVIDER", "runware")  # runware|fal|replicate
TTS_PROVIDER = os.getenv("TTS_PROVIDER", "edge")         # edge|elevenlabs|fish
ELEVENLABS_VOICE_ID = os.getenv("ELEVENLABS_VOICE_ID", "").strip()
# Eleven v3 supports Urdu and expressive character/audiobook delivery.  Keep the
# environment override for accounts that deliberately use another model.
ELEVENLABS_MODEL = os.getenv("ELEVENLABS_MODEL", "eleven_v3").strip() or "eleven_v3"
# HuggingFace InferenceClient model (HF_TOKEN .env mein daalein)
HF_MODEL = os.getenv("HF_MODEL", "meta-llama/Meta-Llama-3-8B-Instruct")
# fallback chains (provider fail/no-key ho to agla)
LLM_FALLBACK = ["runware", "huggingface", "groq", "gemini", "openai", "openrouter", "together"]
IMAGE_FALLBACK = ["runware", "fal", "replicate"]
TTS_FALLBACK = ["edge", "elevenlabs", "fish"]

# Captions (P2) — karaoke
WHISPER_MODEL = os.getenv("WHISPER_MODEL", "base")
CAPTIONS = {
    "enabled": False,                # default OFF (Urdu whisper transcription abhi reliable nahi)
    "words_per_group": 3,            # ek waqt mein kitne words
    "font_size": 58,
    "color": "#FFFFFF",
    "outline": "#000000",
    "outline_size": 4,
    "highlight_color": "#FFE000",    # current word ka rang (karaoke)
    "highlight_style": "color",      # color | box | scale
    "highlight_bg": "#3700B3",
    "position": "bottom",            # bottom | center | top
    "margin": 110,
    "per_speaker_color": True,       # har character ka apna highlight rang
}

# Motion preset: subtle | dynamic | cinematic  (P1)
MOTION_PRESET = os.getenv("MOTION_PRESET", "dynamic")
# Render mode: draft (procedural, free) | cinematic (Runware AI-video, paid)
RENDER_MODE = os.getenv("RENDER_MODE", "draft")
# Cinematic mode ka video model
VIDEO_MODEL = os.getenv("VIDEO_MODEL", "klingai:3@2")

# P6 — Resolution & Render Engine
VIDEO_QUALITY = os.getenv("VIDEO_QUALITY", "1080p")   # 720p | 1080p | 2K | 4K
ASPECT = os.getenv("ASPECT", "landscape")             # landscape(16:9) | portrait(9:16) | square(1:1)
FPS = int(os.getenv("FPS", "30"))                     # 30 | 60
GPU_ENCODE = os.getenv("GPU_ENCODE", "auto")          # auto | on | off (NVENC)
FAST_PREVIEW = os.getenv("FAST_PREVIEW", "0") == "1"  # low-res tez draft (480p)
RENDER_WORKERS = int(os.getenv("RENDER_WORKERS", "3"))  # parallel chunk render
RENDER_BACKEND = os.getenv("RENDER_BACKEND", "process")  # process (asli parallel) | thread
RESUME = os.getenv("RESUME", "1") == "1"              # chunk cache se resume

_H_BY_QUALITY = {"720p": 720, "1080p": 1080, "2k": 1440, "4k": 2160}


def get_dimensions():
    """(W, H) — quality + aspect + fast-preview ke hisab se (even numbers)."""
    h = _H_BY_QUALITY.get(VIDEO_QUALITY.lower(), 1080)
    if FAST_PREVIEW:
        h = 480
    a = ASPECT.lower()

    def even(x):
        return int(round(x / 2) * 2)
    if a == "portrait":
        return (h, even(h * 16 / 9))      # e.g. 1080 x 1920
    if a == "square":
        return (h, h)                      # 1080 x 1080
    return (even(h * 16 / 9), h)           # landscape 1920 x 1080


BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECTS_DIR = os.path.join(BASE_DIR, "projects")
os.makedirs(PROJECTS_DIR, exist_ok=True)


def require_api_key():
    if not RUNWARE_API_KEY or RUNWARE_API_KEY == "your_runware_key_here":
        raise SystemExit(
            "\n[!] Runware API key nahi mili. .env mein RUNWARE_API_KEY daalein.\n"
        )

# Video color grade (ffmpeg eq) — vibrant cartoon rang
COLOR_GRADE = os.getenv("COLOR_GRADE", "eq=saturation=1.5:contrast=1.12:brightness=0.03:gamma=0.98")
