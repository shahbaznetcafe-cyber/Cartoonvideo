"""
M1 — Story Intelligence Engine (Phase 3 + 8).
Raw script -> structured JSON: characters, scenes, dialogue, emotion, background.
Yeh poore studio ki reedh hai — baqi sab modules isi JSON par chalenge.
"""
import json
import re

import config
import dialogue_style
from runware_client import post_tasks, new_uuid


SYSTEM_PROMPT = """You are a story/script analysis engine for an automated 2D
video studio. You receive a raw script (Urdu, Roman Urdu, Hindi, Hinglish, or English) and break it
down into a precise STRUCTURE that the video engine can render.

Reply with ONLY a valid JSON object (no markdown, no commentary) with this schema:

{
  "title": "short video title (same language as script)",
  "language": "urdu | roman_urdu | hindi | hinglish | english",
  "characters": [
    {"id": "lowercase_id", "name": "display name", "gender": "male|female|child",
     "role": "short description"}
  ],
  "scenes": [
    {
      "id": 1,
      "location": "short place name e.g. kitchen, market, school",
      "time": "day|evening|night",
      "mood": "comedy|drama|suspense|educational|emotional|action",
      "transition": "hard_cut|short_dissolve|whip_pan|match_cut|fade|camera_motivated",
      "transition_duration": 0.0,
      "background_prompt": "ENGLISH image prompt for this scene's background, no characters in it",
      "lines": [
        {"speaker": "character_id OR narrator", "text": "the spoken line in original language",
         "emotion": "happy|sad|angry|excited|scared|confused|thinking|surprised|neutral",
         "action": "short stage direction e.g. 'enters room', 'points finger', or '' "}
      ]
    }
  ]
}

Rules:
- Detect EVERY speaker. If text is pure narration, speaker = "narrator".
- Split into logical scenes whenever location/time/topic changes.
- Open on the story problem, surprise, or funniest action in the FIRST spoken line. Do
  not begin with greetings, channel branding, or setup that can be inferred visually.
- For a normal YouTube episode, target 5-7 scenes, 4-7 purposeful lines per scene, and
  roughly 30-42 spoken lines total. Consolidate repeated explanations and reactions.
  Preserve additional lines only when the user explicitly requests a longer episode.
- Keep each "text" as one natural spoken line. Prefer a concise line over splitting a
  repeated idea into several dialogue turns.
- Every scene must introduce a visibly different condition, location, action, or
  consequence. Every line's action must be concrete enough to animate on screen.
- Always include at least one character. Infer gender sensibly.
- background_prompt must always be in ENGLISH and describe ONLY the scene (no people).
- Treat transition as the edit INTO this scene. Use hard_cut for the first scene and
  for normal dialogue continuity. Use a visible transition only when story action,
  camera movement, time change, montage, or a deliberate visual match motivates it.
  Never decorate every scene. Visible transition_duration must be 0.15 to 0.5 seconds;
  hard_cut and match_cut use 0.0 seconds.
- PUNCTUATION for natural voice flow: add correct punctuation to every "text" so
  text-to-speech reads with natural rhythm and pauses. Use commas for short pauses,
  a full stop / question mark / exclamation mark at the end of each sentence, and an
  ellipsis (...) for hesitation or a dramatic pause. Break run-on lines with commas and
  full stops. Match the script's language: for Urdu-script text use Urdu marks (، ۔ ؟),
  for Roman Urdu / English use Latin marks (, . ? !). Do NOT change the words — only
  clean up and add punctuation.
- If the input is Hinglish, preserve its approximate Hindi/English ratio and return
  language="hinglish". Do not translate Hindi words into English or vice versa.
"""


def _extract_json(text):
    text = text.strip()
    text = re.sub(r"^```(?:json)?", "", text).strip()
    text = re.sub(r"```$", "", text).strip()
    s, e = text.find("{"), text.rfind("}")
    if s != -1 and e != -1:
        text = text[s:e + 1]
    return json.loads(text)


def _assign_voices(data):
    """Har character ko ek edge-tts voice de do (gender ke hisab se)."""
    voice_map = config.voice_map_for_language(data.get("language"))
    for ch in data.get("characters", []):
        g = (ch.get("gender") or "male").lower()
        ch["voice"] = voice_map.get(g, voice_map["male"])
    # narrator entry agar lines mein use hua hai
    speakers = {ln.get("speaker") for sc in data.get("scenes", []) for ln in sc.get("lines", [])}
    have = {c["id"] for c in data.get("characters", [])}
    if "narrator" in speakers and "narrator" not in have:
        data["characters"].append({
            "id": "narrator", "name": "Narrator", "gender": "male",
            "role": "story narrator", "voice": voice_map["narrator"],
        })
    return data


_SCENE_RE = re.compile(r"^\s*\[\s*scene\s*:\s*(.+?)\s*\]\s*$", re.IGNORECASE)
_DIALOGUE_RE = re.compile(r"^\s*([^:\n]{1,80})\s*:\s*(.+?)\s*$")
_DIRECTION_RE = re.compile(r"^\s*\(([^)]+)\)\s*(.*)$")
_EMOTIONS = {
    "happy", "sad", "angry", "excited", "scared", "confused", "thinking",
    "surprised", "neutral", "relieved",
}


def _speaker_id(name):
    """Create a stable renderer-safe id while preserving non-Latin names."""
    value = re.sub(r"[^\w]+", "_", str(name).strip().lower(), flags=re.UNICODE)
    return value.strip("_") or "narrator"


def _detect_language(text):
    has_devanagari = bool(re.search(r"[\u0900-\u097f]", text))
    has_urdu = bool(re.search(r"[\u0600-\u06ff]", text))
    has_latin = bool(re.search(r"[A-Za-z]{2,}", text))
    if has_devanagari:
        return "hinglish" if has_latin else "hindi"
    if has_urdu:
        return "urdu"
    return "roman_urdu" if has_latin else "english"


def _infer_gender(name):
    value = str(name).casefold()
    if any(token in value for token in ("amy", "girl", "bibi", "aunty", "nani", "dadi", "amma")):
        return "female"
    if any(token in value for token in ("kid", "child", "baby", "bacha", "bachi")):
        return "child"
    return "male"


def parse_structured_script(script_text):
    """Parse the studio's ``[Scene:]``/``Speaker:`` format without an LLM.

    AI-generated and manually formatted studio scripts already carry the exact
    scene and speaker boundaries the renderer needs. Re-sending those scripts to
    an online model made direct rendering slow, costly and vulnerable to provider
    stalls. Return ``None`` only when the input is genuinely unstructured, so the
    existing LLM parser remains available for prose.
    """
    scenes = []
    current = None
    speakers = {}

    for raw_line in str(script_text or "").splitlines():
        line = raw_line.strip()
        if not line:
            continue
        scene_match = _SCENE_RE.match(line)
        if scene_match:
            current = {
                "id": len(scenes) + 1,
                "location": scene_match.group(1).strip(),
                "time": "day",
                "mood": "neutral",
                "transition": "hard_cut",
                "transition_duration": 0.0,
                "background_prompt": scene_match.group(1).strip(),
                "lines": [],
            }
            scenes.append(current)
            continue

        dialogue_match = _DIALOGUE_RE.match(line)
        if not dialogue_match:
            continue
        if current is None:
            current = {
                "id": 1, "location": "story scene", "time": "day",
                "mood": "neutral", "transition": "hard_cut",
                "transition_duration": 0.0,
                "background_prompt": "story scene", "lines": [],
            }
            scenes.append(current)

        display_name = dialogue_match.group(1).strip()
        speaker = _speaker_id(display_name)
        text = dialogue_match.group(2).strip()
        emotion, action = "neutral", ""
        direction = _DIRECTION_RE.match(text)
        if direction:
            cue = direction.group(1).strip().casefold()
            text = direction.group(2).strip()
            if cue in _EMOTIONS:
                emotion = cue
            else:
                action = cue
        if not text:
            continue
        current["lines"].append({
            "speaker": speaker, "text": text, "emotion": emotion, "action": action,
        })
        speakers.setdefault(speaker, {
            "id": speaker, "name": display_name,
            "gender": _infer_gender(display_name), "role": "story character",
        })

    line_count = sum(len(scene["lines"]) for scene in scenes)
    if not scenes or line_count == 0:
        return None
    scenes = [scene for scene in scenes if scene["lines"]]
    if not scenes:
        return None
    for index, scene in enumerate(scenes, 1):
        scene["id"] = index
    return _assign_voices({
        "title": scenes[0]["location"] or "Untitled",
        "language": _detect_language(script_text),
        "characters": list(speakers.values()),
        "scenes": scenes,
    })


def parse_script(script_text):
    structured = parse_structured_script(script_text)
    if structured:
        return structured
    import providers
    raw = providers.llm_generate(
        SYSTEM_PROMPT, f"SCRIPT:\n{script_text}",
        max_tokens=4000, temperature=0.4)

    try:
        parsed = _extract_json(raw)
    except Exception as e:
        raise RuntimeError(f"Scene JSON parse nahi hua:\n{raw[:600]}\n({e})")

    parsed.setdefault("title", "Untitled")
    parsed.setdefault("characters", [])
    parsed.setdefault("scenes", [])
    return _assign_voices(parsed)


def stats(parsed):
    """Quick summary (CLI ke liye)."""
    n_chars = len(parsed.get("characters", []))
    n_scenes = len(parsed.get("scenes", []))
    n_lines = sum(len(s.get("lines", [])) for s in parsed.get("scenes", []))
    return n_chars, n_scenes, n_lines
