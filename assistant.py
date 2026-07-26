"""
P11 — AI Assistant. Script analyze kar ke behtari ke mashware deta hai,
aur chahein to script khud behtar (improve) kar deta hai.
"""
import json

import dialogue_style


def _parse_json(raw):
    raw = raw.strip().strip("`")
    s, e = raw.find("{"), raw.rfind("}")
    return json.loads(raw[s:e + 1])


def analyze(script, language="urdu"):
    """Script ka analysis + suggestions (JSON)."""
    import providers
    sysp = (
        "You are a viral short-video coach. Analyze the script and reply with ONLY JSON: "
        "{\"hook_score\": 1-10, \"pacing\": \"good|slow|fast\", "
        "\"style_suggestion\": \"...\", \"music_mood\": \"comedy|drama|...\", "
        "\"title_ideas\": [3 catchy titles], "
        "\"improvements\": [3-5 short actionable tips], "
        "\"strong_points\": [2 things done well]}. "
        "Keep tips in the script's language.")
    sysp += " " + dialogue_style.YOUTUBE_STORY_RULES
    user = f"Language: {language}\nScript:\n{script[:1200]}"
    try:
        return _parse_json(providers.llm_generate(sysp, user, max_tokens=600, temperature=0.6))
    except Exception as e:
        return {"error": str(e)}


def improve_script(script, language="urdu"):
    """Script ko behtar likho — stronger hook, behtar pacing, punchy dialogue."""
    import providers
    sysp = (
        "You improve short-video scripts: stronger opening hook, better pacing, "
        "punchier dialogue, clear emotional beats. Keep the SAME characters, language, "
        "and speaker-name format (Name: line). "
        + dialogue_style.full_prompt_policy(language)
        + " Reply with ONLY the improved script text.")
    user = f"Language: {language}\nScript:\n{script}"
    try:
        return providers.llm_generate(sysp, user, max_tokens=1500, temperature=0.8).strip()
    except Exception as e:
        return f"[error] {e}"
