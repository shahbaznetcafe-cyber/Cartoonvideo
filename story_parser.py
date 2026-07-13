"""
M1 — Story Intelligence Engine (Phase 3 + 8).
Raw script -> structured JSON: characters, scenes, dialogue, emotion, background.
Yeh poore studio ki reedh hai — baqi sab modules isi JSON par chalenge.
"""
import json
import re

import config
from runware_client import post_tasks, new_uuid


SYSTEM_PROMPT = """You are a story/script analysis engine for an automated 2D
video studio. You receive a raw script (Urdu, Roman Urdu, or English) and break it
down into a precise STRUCTURE that the video engine can render.

Reply with ONLY a valid JSON object (no markdown, no commentary) with this schema:

{
  "title": "short video title (same language as script)",
  "language": "urdu | roman_urdu | english",
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
    for ch in data.get("characters", []):
        g = (ch.get("gender") or "male").lower()
        ch["voice"] = config.VOICE_MAP.get(g, config.VOICE_MAP["male"])
    # narrator entry agar lines mein use hua hai
    speakers = {ln.get("speaker") for sc in data.get("scenes", []) for ln in sc.get("lines", [])}
    have = {c["id"] for c in data.get("characters", [])}
    if "narrator" in speakers and "narrator" not in have:
        data["characters"].append({
            "id": "narrator", "name": "Narrator", "gender": "male",
            "role": "story narrator", "voice": config.VOICE_MAP["narrator"],
        })
    return data


def parse_script(script_text):
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
