"""
M1 — Story Intelligence Engine (Phase 3 + 8).
Raw script -> structured JSON: characters, scenes, dialogue, emotion, background.
Yeh poore studio ki reedh hai — baqi sab modules isi JSON par chalenge.
"""
import json
import re

import config
import dialogue_style
import actions
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
- PRESERVE ALL SPOKEN LINES. Do NOT drop, summarize, truncate, or consolidate dialogue lines from the input script. Extract every single line into the JSON structure so the rendered video duration matches the full length of the input script.
- Keep each "text" as one natural spoken line.
- Every scene must introduce a visibly different condition, location, action, or
  consequence. Every line's action must be one concrete renderer-supported verb:
  idle, look, listen, walk, run, approach, exit, wave, point, reach, pickup, give,
  celebrate, jump, dance, nod, shake, hug, help, pull, punch, kick, hit, fall, sit,
  stand, wash, slip, or splash. Never use vague directions such as "acts naturally".
- Always include at least one character. Infer gender sensibly.
- background_prompt must always be in ENGLISH and describe ONLY the scene (no people).
  Include location type, time of day, lighting, weather, depth layers and story props
  required by the actions. Keep the foreground clear enough for character performance.
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
_DIALOGUE_RE = re.compile(r"^\s*([^:\-\n\[]{1,60})\s*[:\-]\s*(.+?)\s*$")
_DIRECTION_RE = re.compile(r"^\s*\(([^)]+)\)\s*(.*)$")
_EMOTIONS = {
    "happy", "sad", "angry", "excited", "scared", "confused", "thinking",
    "surprised", "neutral", "relieved",
}
_EMOTION_ALIASES = {
    "happy": ("खुश", "मुस्कुर", "प्रसन्न", "relief", "राहत", "khush", "muskur"),
    "sad": ("उदास", "दुख", "रोते", "sad", "udaas", "dukhi"),
    "angry": ("गुस्स", "क्रोधित", "नाराज़", "angry", "gussa", "naraz"),
    "excited": ("उत्साहित", "जोश", "excited", "energetic", "हिम्मती"),
    "scared": ("डर", "घबरा", "भय", "scared", "afraid", "dari", "dara"),
    "confused": ("उलझ", "confused", "परेशान", "hairan pareshan"),
    "thinking": ("सोच", "संदेह", "focused", "फोकस", "thinking", "गौर"),
    "surprised": ("चौंक", "हैरान", "surpris", "shocked"),
    "neutral": ("सतर्क", "शांत", "रुकते", "neutral", "calm", "alert"),
}

# Production templates use these common English acting cues.  Keep aliases
# separate from the historical multilingual table to avoid misclassifying the
# final location part in ``(emotion; action; location)``.
_EMOTION_ALIASES["thinking"] += ("curious", "curiosity")
_EMOTION_ALIASES["neutral"] += ("serious", "determined")


def _normalize_emotion(value):
    key = str(value or "").strip().casefold()
    if key in _EMOTIONS:
        return key
    for emotion, markers in _EMOTION_ALIASES.items():
        if any(marker in key for marker in markers):
            return emotion
    return None


def normalize_parsed_directions(data):
    """Repair saved/LLM plans so emotion and renderer action remain separate."""
    for scene in (data or {}).get("scenes", []):
        for line in scene.get("lines", []):
            raw_action = str(line.get("action") or "").strip().casefold()
            parts = [part.strip() for part in re.split(r"[;|]", raw_action) if part.strip()]
            supported = next((part for part in reversed(parts)
                              if part in actions.SUPPORTED_ACTIONS), None)
            current_emotion = _normalize_emotion(line.get("emotion")) or "neutral"
            if not raw_action:
                line["emotion"] = current_emotion
                continue
            if current_emotion == "neutral":
                for part in parts:
                    if part == supported:
                        continue
                    inferred = _normalize_emotion(part)
                    if inferred:
                        current_emotion = inferred
                        break
            if supported:
                line["action"] = supported
            elif raw_action not in actions.SUPPORTED_ACTIONS:
                detected = actions.detect(f"{raw_action} {line.get('text') or ''}", current_emotion)
                line["action"] = "idle" if detected == "none" else detected
            line["emotion"] = current_emotion
    return data


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
    if any(token in value for token in ("amy", "girl", "bibi", "aunty", "nani", "dadi", "amma",
                                             "मीरा", "रिया", "सिया", "परी", "लड़की", "महिला")):
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
        text = dialogue_match.group(2).strip().strip('"\'“”«»')
        emotion, action = "neutral", ""
        direction = _DIRECTION_RE.match(text)
        if direction:
            cue = direction.group(1).strip().casefold()
            text = direction.group(2).strip().strip('"\'“”«»')
            # Professional generated scripts may provide ``emotion; action``.
            # Older one-token cues remain fully backward compatible.
            cue_parts = [part.strip() for part in re.split(r"[;|]", cue) if part.strip()]
            action_parts, location_parts = [], []
            # Only the FINAL part of a full "(emotion; action; location)" cue is
            # ever a location.  Earlier parts that match neither a recognised
            # emotion nor a supported action are unrecognised synonyms (e.g. a
            # hand-written "nervous" or "hop" outside the small built-in
            # vocabularies) -- drop them instead of grafting them onto the
            # location.  Grafting used to compare that noisy per-line string
            # against the scene's location every line, so almost every line
            # started a brand-new scene (one script fragmented 8 intended
            # scenes into 48).  A 1- or 2-part cue never carries a location,
            # matching the historical "older one-token cues" behaviour.
            location_index = len(cue_parts) - 1 if len(cue_parts) >= 3 else -1
            for index, part in enumerate(cue_parts):
                normalized_emotion = _normalize_emotion(part)
                normalized_action = part.casefold()
                if normalized_emotion and emotion == "neutral" and normalized_action not in actions.SUPPORTED_ACTIONS:
                    emotion = normalized_emotion
                elif normalized_action in actions.SUPPORTED_ACTIONS:
                    action_parts.append(normalized_action)
                elif index == location_index:
                    # Production templates use (emotion; action; location).
                    # Keep that final location cue instead of treating it as a
                    # broken action.  It can create a real scene boundary.
                    location_parts.append(part)
            action = "; ".join(action_parts)
            location_cue = "; ".join(location_parts)
        else:
            location_cue = ""
        if location_cue:
            normalized_cue = location_cue.casefold()
            current_location = str(current.get("location") or "").casefold()
            # A repeated cue stays in the same scene.  A new cue starts a real
            # storyboard scene so the background director can change location.
            if current["lines"] and normalized_cue != current_location:
                current = {
                    "id": len(scenes) + 1, "location": location_cue, "time": "day",
                    "mood": "neutral", "transition": "hard_cut",
                    "transition_duration": 0.0, "background_prompt": location_cue, "lines": [],
                }
                scenes.append(current)
            elif not current["lines"] or current_location == "story scene":
                current["location"] = location_cue
                current["background_prompt"] = location_cue
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
    return normalize_parsed_directions(_assign_voices({
        "title": scenes[0]["location"] or "Untitled",
        "language": _detect_language(script_text),
        "characters": list(speakers.values()),
        "scenes": scenes,
    }))


def parse_script(script_text, target_duration=None):
    structured = parse_structured_script(script_text)
    if structured:
        if target_duration:
            import duration_planner
            structured, _ = duration_planner.auto_segment_scenes(
                structured, script_text=script_text, selected=target_duration)
        return structured
    import providers
    prompt_extra = f"\nTarget Duration: {target_duration}. Extract ALL spoken lines fully." if target_duration else ""
    raw = providers.llm_generate(
        SYSTEM_PROMPT + prompt_extra, f"SCRIPT:\n{script_text}",
        max_tokens=4000, temperature=0.4)

    try:
        parsed = _extract_json(raw)
    except Exception as e:
        raise RuntimeError(f"Scene JSON parse nahi hua:\n{raw[:600]}\n({e})")

    parsed.setdefault("title", "Untitled")
    parsed.setdefault("characters", [])
    parsed.setdefault("scenes", [])
    result = normalize_parsed_directions(_assign_voices(parsed))
    if target_duration:
        import duration_planner
        result, _ = duration_planner.auto_segment_scenes(
            result, script_text=script_text, selected=target_duration)
    return result


def stats(parsed):
    """Quick summary (CLI ke liye)."""
    n_chars = len(parsed.get("characters", []))
    n_scenes = len(parsed.get("scenes", []))
    n_lines = sum(len(s.get("lines", [])) for s in parsed.get("scenes", []))
    return n_chars, n_scenes, n_lines
