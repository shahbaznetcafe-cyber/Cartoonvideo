"""
Story Templates — 15 ready-made kahani formulas (different scenarios).
User ek template chunta hai + topic deta hai -> AI us formula par poora script likhta hai
(format: 'Name: dialogue', jo seedha parse_script + video engine mein chala jaye).

Har template: id, name (roman), name_en, emoji, desc, mood, structure (beat sheet),
chars (library characters), lines (approx dialogue count), sample_topic.
"""

import actions
import dialogue_style
import duration_planner

TEMPLATES = [
    {
        "id": "character_roles", "name": "Character-wise Story", "name_en": "Character-wise Story", "emoji": "??",
        "desc": "Selected cast ke roles, unique dialogue tone, body actions aur background changes automatically plan karein.",
        "mood": "adventure", "chars": ["aloo", "tamatar"], "lines": 12,
        "sample_topic": "ek purana map jo doston ko chhupe hue raaz tak le jata hai",
        "structure": "Use ONLY the selected cast. Assign each selected character one distinct role: protagonist, companion, guide, comic relief, rival, or helper. Give every character a consistent personality, dialogue style and visible objective. Build hook, goal, obstacle, discovery, action, resolution across changing locations. Never invent an unselected speaker. Every line must follow: Character Name: (emotion; body action; location) dialogue. Use short, natural, punctuated dialogue and safe visible actions. End with a visual resolution and brief takeaway.",
    },
    {
        "id": "cinematic_adventure", "name": "Cinematic Adventure", "name_en": "Cinematic Adventure", "emoji": "??",
        "desc": "Journey, obstacle, discovery aur a strong visual ending for any selected cast.",
        "mood": "action", "chars": ["aloo", "tamatar"], "lines": 12,
        "sample_topic": "ek lost signal ka peecha karte hue dangerous valley tak safar",
        "structure": "Use ONLY the selected cast. Create a clear travel story: establish location, reveal a goal, move to a second location, face one physical obstacle, discover a clue, then resolve it through teamwork. Each character must contribute a different skill. Use real location changes and walk, approach, look, point, reach, react, run or celebrate actions. Use strict production format: Character Name: (emotion; body action; location) dialogue.",
    },
    {
        "id": "mystery_case", "name": "Mystery Case", "name_en": "Mystery Case", "emoji": "??",
        "desc": "Clues, suspects, a reveal and proper scene progression without an extra invented cast.",
        "mood": "suspense", "chars": ["aloo", "tamatar"], "lines": 12,
        "sample_topic": "missing treasure compass ka mystery case",
        "structure": "Use ONLY the selected cast. One character notices a missing item; others become investigator, clue keeper, skeptical companion or helper. Move through at least three locations, place visible clues and make each clue change the next action. Build suspense, then reveal a fair answer. Do not add unnamed suspects. Use strict production format: Character Name: (emotion; body action; location) dialogue.",
    },
    {
        "id": "pirate_treasure", "name": "Pirate Treasure Quest", "name_en": "Pirate Treasure Quest", "emoji": "?",
        "desc": "Pirate Harbor, ship, map, cove aur treasure-focused story for selected pirate or adventure characters.",
        "mood": "action", "chars": ["aloo", "tamatar"], "lines": 12,
        "sample_topic": "storm se pehle Treasure Cove ka golden compass dhoondhna",
        "structure": "Use ONLY the selected cast. Set the opening at Pirate Harbor or on a ship, then move through dock, sea-side path and Treasure Cove. Give one character the map, one the practical skill, and any others a useful role. Include a visible chest, map, dock or ship interaction. Use walk, point, approach, reach, react and run actions. Use strict production format: Character Name: (emotion; body action; location) dialogue.",
    },
    {
        "id": "space_mission", "name": "Space Rescue Mission", "name_en": "Space Rescue Mission", "emoji": "??",
        "desc": "Planetary Outpost based mission with discovery, teamwork and safe action beats.",
        "mood": "action", "chars": ["aloo", "tamatar"], "lines": 12,
        "sample_topic": "Planetary Outpost par lost energy beacon ko activate karna",
        "structure": "Use ONLY the selected cast. Begin at Planetary Outpost, identify a mission, inspect a glowing object or signal, travel to a second outpost area, overcome one technical or terrain obstacle, and finish with a visible successful activation. Give each character a distinct mission role. Use strict production format: Character Name: (emotion; body action; location) dialogue.",
    },
    {
        "id": "teamwork_challenge", "name": "Teamwork Challenge", "name_en": "Teamwork Challenge", "emoji": "??",
        "desc": "Every selected character gets a useful job; suitable for children stories and mixed cast.",
        "mood": "educational", "chars": ["aloo", "tamatar", "gajar"], "lines": 12,
        "sample_topic": "community garden ko barish se bachana",
        "structure": "Use ONLY the selected cast. Present one visible shared problem. Give every selected character a different task, a short moment of doubt, then a coordinated solution. Change locations or camera focus as tasks progress. Use visual actions such as carry, point, look, reach, walk, react and celebrate. End with a practical teamwork lesson. Use strict production format: Character Name: (emotion; body action; location) dialogue.",
    },
    {
        "id": "funny_mixup", "name": "Funny Mix-up", "name_en": "Funny Mix-up", "emoji": "??",
        "desc": "Natural cartoon comedy with a visual misunderstanding and a clean payoff.",
        "mood": "comedy", "chars": ["aloo", "tamatar"], "lines": 10,
        "sample_topic": "ek mysterious box ko sab galat cheez samajh lete hain",
        "structure": "Use ONLY the selected cast. Open with a funny misunderstanding involving one visible prop. Escalate through contrasting reactions and location-aware body acting, then reveal a harmless truth. Do not make characters stand talking in one place; use approach, inspect, point, step back, reach and celebrate. End on one concise comic payoff. Use strict production format: Character Name: (emotion; body action; location) dialogue.",
    },
    {
        "id": "friendship_journey", "name": "Friendship Journey", "name_en": "Friendship Journey", "emoji": "??",
        "desc": "Warm emotional story with a shared journey, help moment and visible resolution.",
        "mood": "emotional", "chars": ["aloo", "tamatar"], "lines": 12,
        "sample_topic": "ek dost ko ghar ka raasta yaad dilane ka safar",
        "structure": "Use ONLY the selected cast. One character has a meaningful but child-friendly problem; another notices and helps. Travel through at least two locations, include a small obstacle and a sincere helping action. Keep dialogue gentle and concise, with visible look, listen, walk, point, reach and celebrate actions. End hopeful, not overly sentimental. Use strict production format: Character Name: (emotion; body action; location) dialogue.",
    },
    {
        "id": "learning_by_doing", "name": "Learning by Doing", "name_en": "Learning by Doing", "emoji": "??",
        "desc": "Educational story where the lesson comes from visible action instead of a lecture.",
        "mood": "educational", "chars": ["aloo", "tamatar"], "lines": 12,
        "sample_topic": "safai aur recycling se park ko behtar banana",
        "structure": "Use ONLY the selected cast. Teach one practical child-friendly idea through a visual challenge, attempt, correction and success. Each character must demonstrate or discover something rather than only explain it. Use scene locations and props that fit the topic. Keep one short clear takeaway at the end. Use strict production format: Character Name: (emotion; body action; location) dialogue.",
    },
    {
        "id": "action_escape", "name": "Action Escape", "name_en": "Action Escape", "emoji": "?",
        "desc": "Fast body-driven sequence for characters that support walk/run actions.",
        "mood": "action", "chars": ["aloo", "tamatar"], "lines": 10,
        "sample_topic": "crumbling bridge se safe route tak pahunchna",
        "structure": "Use ONLY the selected cast. Start with an immediate visual danger, establish a safe goal, then use a clear three-beat route: notice, react, move. Keep peril kid-friendly and non-violent. Use movement-focused actions: run, walk, stop, point, look, retreat, reach and celebrate. Change framing/location for each beat and finish safely. Use strict production format: Character Name: (emotion; body action; location) dialogue.",
    },
    {
        "id": "festival_event", "name": "Festival Event", "name_en": "Festival Event", "emoji": "??",
        "desc": "Celebration story with preparation, a small setback and a visual happy ending.",
        "mood": "joyful", "chars": ["aloo", "tamatar", "gajar"], "lines": 12,
        "sample_topic": "community festival ke liye lantern parade tayyar karna",
        "structure": "Use ONLY the selected cast. Open during preparation, give each character one contribution, introduce a small non-dangerous setback, solve it together, then reveal a celebration scene. Use props and scene changes; do not use a static stage. Finish with short inclusive dialogue. Use strict production format: Character Name: (emotion; body action; location) dialogue.",
    },
    {
        "id": "detective_vs_rival", "name": "Detective and Rival", "name_en": "Detective and Rival", "emoji": "???",
        "desc": "Three-character mystery/adventure with clearly separated character motivations.",
        "mood": "drama", "chars": ["aloo", "tamatar", "gajar"], "lines": 12,
        "sample_topic": "secret garden key ko pehle dhoondhne ka friendly race",
        "structure": "Use ONLY the selected cast. Assign one investigator, one competitive but harmless rival, and one grounded helper. Their goals must be understandable and no one is a villain. Use a clue trail across at least three locations, then resolve the friendly competition through fairness. Give each character a distinct dialogue rhythm and body action. Use strict production format: Character Name: (emotion; body action; location) dialogue.",
    },
]


# Genre-aware cast recommendations.  The UI applies the active library's list
# when a template is chosen; it never mixes SBZ and Quaternius automatically.
_TEMPLATE_CAST_RECOMMENDATIONS = {
    "character_roles": {"sbz": ["CuteFox", "CuteRobot"], "quaternius": ["Quaternius Adventurer", "Quaternius Casual Female"]},
    "cinematic_adventure": {"sbz": ["HelmetHero", "CuteFox"], "quaternius": ["Quaternius Adventurer", "Quaternius Farmer"]},
    "mystery_case": {"sbz": ["PuppyPolice", "TomatoReporterMicrophone"], "quaternius": ["Quaternius Doctor Female Young", "Quaternius Casual"]},
    "pirate_treasure": {"sbz": ["KiteKaptan", "CuteFox"], "quaternius": ["Quaternius Anne", "Quaternius Captain Barbarossa"]},
    "space_mission": {"sbz": ["RabbitAstronaut", "BatteryBot"], "quaternius": ["Quaternius Astronaut FinnTheFrog", "Quaternius Alien"]},
    "teamwork_challenge": {"sbz": ["FriendlyGreenDustbin", "WaterDrop", "TechGoat"], "quaternius": ["Quaternius Farmer", "Quaternius Casual 2", "Quaternius Doctor Male Young"]},
    "funny_mixup": {"sbz": ["AngryChili", "ConfidentBurger"], "quaternius": ["Quaternius Chicken", "Quaternius Cactoro"]},
    "friendship_journey": {"sbz": ["BubbleBunnyPlush", "CuteFox"], "quaternius": ["Quaternius Bunny", "Quaternius Dog"]},
    "learning_by_doing": {"sbz": ["PencilTeacher", "ToothbrushTinku"], "quaternius": ["Quaternius Doctor Male Young", "Quaternius Farmer"]},
    "action_escape": {"sbz": ["HelmetHero", "PuppyPolice"], "quaternius": ["Quaternius Adventurer", "Quaternius BlueSoldier Male"]},
    "festival_event": {"sbz": ["LadooLal", "LanternLala", "KiteKaptan"], "quaternius": ["Quaternius King", "Quaternius Casual Female", "Quaternius Farmer"]},
    "detective_vs_rival": {"sbz": ["PuppyPolice", "BookTeal", "CuteRobot"], "quaternius": ["Quaternius Anne", "Quaternius Henry", "Quaternius Captain Barbarossa"]},
}
for _template in TEMPLATES:
    _template["cast_recommendations"] = _TEMPLATE_CAST_RECOMMENDATIONS.get(_template["id"], {})

_BY_ID = {t["id"]: t for t in TEMPLATES}

# 10 rigged library characters — script mein speaker naam (roman, jo library keywords se map)
LIBRARY_CHARACTERS = [
    {"id": "aloo", "name": "Aloo", "emoji": "🥔", "package": "potato"},
    {"id": "tamatar", "name": "Tamatar", "emoji": "🍅", "package": "tomato"},
    {"id": "pyaz", "name": "Pyaz", "emoji": "🧅", "package": "onion"},
    {"id": "aam", "name": "Aam", "emoji": "🥭", "package": "mango"},
    {"id": "kela", "name": "Kela", "emoji": "🍌", "package": "banana"},
    {"id": "bhindi", "name": "Bhindi", "emoji": "🫑", "package": "ladyfinger"},
    {"id": "mooli", "name": "Mooli", "emoji": "🥬", "package": "radish"},
    {"id": "gajar", "name": "Gajar", "emoji": "🥕", "package": "carrot"},
    {"id": "mirch", "name": "Mirch", "emoji": "🌶️", "package": "chilli"},
    {"id": "ananas", "name": "Ananas", "emoji": "🍍", "package": "pineapple"},
]

# length preset -> approx dialogue lines (~5s/line bolne ka waqt)
LENGTH_LINES = {
    key: int(value["lines"])
    for key, value in duration_planner.DURATION_PRESETS.items()
}
# Backward compatibility for saved projects and older clients.
LENGTH_LINES.update({"short": 6, "medium": 12, "long": 24})


_ANIMALS = {"panda", "mouse", "toon", "duck", "dragon"}
_ROBOTS = {"robo", "mechbot"}
_HEROES = {"hero", "figure", "captain", "guy", "kid", "chibi", "chibi2", "girl", "fairy", "archer"}
_FRUITS = {"apple", "apple2", "apple3", "banana", "carrot", "chili", "corn", "cucumber",
           "eggplant", "grapes", "lemon", "mango", "mango2", "mango3", "okra", "pineapple",
           "potato", "potato2", "radish", "tomato"}


def _cat_emoji(slug):
    if slug in _ANIMALS:
        return "🐾"
    if slug in _ROBOTS:
        return "🤖"
    if slug in _HEROES:
        return "🦸"
    return "🎭"     # custom mascot


def available_characters():
    """3D library — sirf custom mascots (fruits/veg + Sketchfab generic hata diye gaye)."""
    out = []
    try:
        import char3d_lib
        import character_catalog
        metadata = character_catalog.selectable_metadata()
        for e in char3d_lib.all_valid():
            import character_performance
            slug = e.get("blend", "").replace(".blend", "")
            meta = metadata.get(slug.lower(), {})
            performance = character_performance.profile_for_entry(e)
            out.append({"id": e["name"], "name": e["name"],
                        "emoji": _cat_emoji(slug), "package": slug,
                        "library": meta.get("library", "sbz"),
                        "category": meta.get("category", "originals"),
                        "tier": meta.get("tier", e.get("animation_tier", "LEGACY")),
                        "speech_mode": performance.get("speech_mode"),
                        "lip_sync": performance.get("lip_sync"),
                        "facial_ready": performance.get("facial_ready", False),
                        "performance_label": performance.get("label"),
                        "performance_warning": performance.get("warning"),
                        "status": meta.get("status", "ready"),
                        "thumbnail": meta.get("thumbnail", f"/char3d-thumb/{slug}")})
    except Exception:
        pass
    return out


def all_templates():
    """UI ke liye — halka (structure prompt ke bagair)."""
    return [{k: t[k] for k in ("id", "name", "name_en", "emoji", "desc", "mood", "chars", "cast_recommendations", "lines", "sample_topic")}
            for t in TEMPLATES]


def get(template_id):
    return _BY_ID.get(template_id)


def unique_cast_names(characters=None):
    """Deduplicate cast names case-insensitively while preserving selection order."""
    result, seen = [], set()
    for item in characters or []:
        name = str(item or "").strip()
        key = name.casefold()
        if name and key not in seen:
            result.append(name)
            seen.add(key)
    return result


def resolve_script_cast(characters=None, library=None, default_count=3):
    """Return a strict, selectable cast from the requested character library.

    Library selection is a generation constraint, not merely a catalog filter.
    This prevents Quaternius prompts from silently using SBZ originals.
    """
    selected_library = str(library or "").strip().lower()
    requested = unique_cast_names(characters)
    if selected_library not in {"sbz", "quaternius"}:
        return requested
    available = [item for item in available_characters()
                 if str(item.get("library") or "sbz").lower() == selected_library]
    by_key = {str(item.get("name") or "").casefold(): str(item.get("name") or "")
              for item in available}
    chosen = []
    for name in requested:
        matched = by_key.get(name.casefold())
        if matched and matched not in chosen:
            chosen.append(matched)
    if not chosen:
        chosen = [str(item.get("name") or "") for item in available[:max(1, int(default_count))]]
        chosen = [name for name in chosen if name]
    if not chosen:
        raise ValueError(f"{selected_library.title()} library mein koi ready character available nahi")
    return chosen

def generate_from_template(template_id, topic="", language="roman_urdu",
                           characters=None, lines=None, length="medium", quality="pro", library=None):
    """
    Template ke formula par AI se poora script likhwao ('Name: dialogue' format).
    quality="pro" -> Quality Engine (template ki structure = structure_hint).
    """
    import providers
    t = get(template_id)
    if not t:
        raise ValueError(f"Template nahi mila: {template_id}")
    chars = resolve_script_cast(characters or t["chars"], library) if library else unique_cast_names(characters or t["chars"])
    if len(chars) < 2:
        chars = (chars + [c for c in t["chars"] if c not in chars])[:2] or t["chars"]
    length = duration_planner.normalize_duration(length)
    if not lines and duration_planner.use_longform(length):
        result = generate_longform(
            f"{topic or t['sample_topic']}\nRequired structure: {t['structure']}",
            language=language, characters=chars, minutes=length,
            genre=t["name_en"],
        )
        return result["script"]
    n = int(lines) if lines else LENGTH_LINES.get(length, 12)
    duration_brief = duration_planner.writing_brief(length)
    approx_sec = duration_brief["target_seconds"]
    topic = (topic or t["sample_topic"]).strip()

    if quality == "pro":
        import scriptcraft
        return scriptcraft.craft(
            topic, language=language, characters=chars, length=length, lines=lines,
            genre=t["name_en"], structure_hint=t["structure"])["script"]

    lang_name = dialogue_style.language_name(language)
    names = ", ".join(c.title() for c in chars)
    import character_performance
    performance_rule = character_performance.script_guidance(chars)

    sysp = (
        "You are a professional viral short-video script writer for an animated cartoon channel. "
        "The characters can be anything the cast specifies (animals, fruits/vegetables, people, "
        "mascots, objects) — write for whatever cast is given, kids-friendly cartoon tone.\n"
        f"GENRE: {t['name_en']}.\n"
        f"STRUCTURE (follow this beat sheet exactly): {t['structure']}\n"
        f"CAST: use ONLY these characters as speakers, and use EVERY one of them at least once: {names}. "
        "Do NOT invent any other character.\n"
        f"{performance_rule}\n"
        f"LENGTH: about {n} dialogue lines and {duration_brief['minimum_words']}-{duration_brief['maximum_words']} spoken words "
        f"(target {duration_brief['target_label']}; around {duration_brief['average_words_per_line']} words per line). "
        "Fill time with meaningful plot progression, not repeated filler.\n"
        f"LANGUAGE: write ALL dialogue in {lang_name}.\n"
        f"{dialogue_style.full_prompt_policy(language)}\n"
        f"{actions.prompt_policy()}\n"
        "QUALITY BAR:\n"
        "- Line 1 must be a STRONG hook that grabs attention instantly.\n"
        "- Give each character a distinct voice/personality consistent with the genre.\n"
        "- Build the beats, then land a clear, satisfying ending (moral/punchline/reveal per genre).\n"
        "- Keep every line short, punchy and natural to speak aloud.\n"
        "FORMAT (strict):\n"
        "- First output line: [Scene: <short place>]\n"
        "- Every other line: 'Name: (emotion; action; location) spoken line'.\n"
        "Reply with ONLY the script text, nothing else.")
    user = f"Topic / idea: {topic}"
    return providers.llm_generate(sysp, user, max_tokens=1400, temperature=0.85).strip()


# ---------------------------------------------------------------------------
# Phase 2 — FREE-FORM: bina template, seedha idea se poora script.
# User sirf ek idea likhta hai (optional: genre, length, cast). AI khud
# best structure/genre/cast decide kar ke 'Name: (emotion) line' script likhta hai.
# ---------------------------------------------------------------------------

GENRES = ["auto", "comedy", "moral", "educational", "emotional", "adventure",
          "drama", "mystery", "rhyme", "action", "suspense"]


def _clean_script(raw):
    """LLM output se code-fence/preamble hatao, sirf script text rakho."""
    raw = (raw or "").strip()
    if raw.startswith("```"):
        raw = raw.strip("`")
        # possible language tag on first line
        nl = raw.find("\n")
        if nl != -1 and len(raw[:nl].split()) == 1:
            raw = raw[nl + 1:]
    return raw.strip()


def generate_freeform(idea, language="roman_urdu", characters=None,
                      length="medium", lines=None, genre="auto",
                      cast_bios=None, continuity="", quality="pro", library=None,
                      series_memory=None):
    """
    Bina template, seedha idea se script. AI khud genre/structure/cast decide karta hai.
    quality="pro" -> multi-pass Quality Engine (plan->draft->polish, hook variants).
             "fast" -> ek LLM call (jaldi).
    Returns dict: {script, genre, cast, title, ...}.
    """
    import json as _json
    import providers
    idea = (idea or "").strip()
    if not idea:
        raise ValueError("Idea chahiye (kis cheez par video?)")
    length = duration_planner.normalize_duration(length)
    chars = resolve_script_cast(characters, library) if library else unique_cast_names(characters)
    if quality == "pro":
        import scriptcraft
        return scriptcraft.craft(idea, language=language, characters=chars,
                                 length=length, lines=lines, genre=genre,
                                 cast_bios=cast_bios, continuity=continuity,
                                 series_memory=series_memory)
    import character_performance
    performance_rule = character_performance.script_guidance(chars)
    n = int(lines) if lines else LENGTH_LINES.get(length, 12)
    duration_brief = duration_planner.writing_brief(length)
    approx_sec = duration_brief["target_seconds"]
    lang_name = dialogue_style.language_name(language)
    g = (genre or "auto").lower()

    if cast_bios:
        cast_rule = ("CAST: use ONLY these recurring characters, keeping each one's established "
                     "personality and speech style CONSISTENT, and use every one at least once:\n"
                     + "\n".join(f"- {b}" for b in cast_bios)
                     + "\nDo NOT invent any other character.")
    elif chars:
        cast_rule = ("CAST: use ONLY these characters as speakers, and use EVERY one at "
                     f"least once: {', '.join(c.title() for c in chars)}. Do NOT invent others.")
    else:
        cast_rule = ("CAST: YOU choose 2-3 characters that best fit the idea (they can be "
                     "animals, fruits/vegetables, people, mascots, objects). Give them short, "
                     "memorable names. Keep the cast small.")
    genre_rule = ("GENRE: auto-detect the best genre for this idea (comedy, moral, "
                  "educational, emotional, adventure, mystery, rhyme, etc.)."
                  if g in ("", "auto") else f"GENRE: {g}.")

    sysp = (
        "You are a professional viral short-video script writer for an animated cartoon channel. "
        "From a single idea you invent a tight, engaging story and write the full script.\n"
        f"{genre_rule}\n{cast_rule}\n"
        f"{performance_rule}\n"
        f"LENGTH: about {n} dialogue lines and {duration_brief['minimum_words']}-{duration_brief['maximum_words']} spoken words "
        f"(target {duration_brief['target_label']}; around {duration_brief['average_words_per_line']} words per line). "
        "Use meaningful story progression, not repeated filler.\n"
        f"LANGUAGE: write ALL dialogue in {lang_name}.\n"
        f"{dialogue_style.full_prompt_policy(language)}\n"
        f"{actions.prompt_policy()}\n"
        "STORY CRAFT:\n"
        "- Infer a clear arc from the idea: hook -> build -> turn -> satisfying ending.\n"
        "- Line 1 must be a STRONG hook that grabs attention in the first 2 seconds.\n"
        "- Give each character a distinct voice/personality.\n"
        "- Land a clear payoff (punchline / moral / reveal) that fits the genre.\n"
        "- Every line short, punchy, natural to speak aloud.\n"
        "OUTPUT: reply with ONLY JSON (no markdown), exactly:\n"
        "{\"title\": \"<catchy title in the script's language>\", "
        "\"genre\": \"<one word>\", \"cast\": [\"Name1\", \"Name2\"], "
        "\"script\": \"<the full script>\"}\n"
        "The \"script\" value MUST be:\n"
        "- First line: [Scene: <short place>]\n"
        "- Every other line: 'Name: (emotion; action; location) spoken line'\n"
        "- Lines separated by \\n.")
    user = f"Idea: {idea}"
    if continuity:
        user += ("\n\nSERIES CONTINUITY (this is a later episode — stay consistent with what "
                 f"happened before, you may reference it):\n{continuity}")
    raw = providers.llm_generate(sysp, user, max_tokens=1500, temperature=0.9)
    raw = _clean_script(raw)
    # JSON parse (robust)
    try:
        s, e = raw.find("{"), raw.rfind("}")
        obj = _json.loads(raw[s:e + 1])
        script = _clean_script(obj.get("script", ""))
        return {
            "script": script,
            "genre": obj.get("genre", g if g != "auto" else ""),
            "cast": obj.get("cast", chars),
            "title": obj.get("title", ""),
        }
    except Exception:
        # JSON toota — raw ko hi script maan lo (agar 'Name:' format dikhta hai)
        return {"script": raw, "genre": g if g != "auto" else "", "cast": chars, "title": ""}


# ---------------------------------------------------------------------------
# Phase 3 — LONG-FORM multi-scene story (3-8 min, YouTube-ready).
# Do-stage: pehle OUTLINE (acts/scenes ka beat-sheet) phir har scene ka dialogue
# alag likho (continuity ke sath). Yeh single-call se zyada coherent rehta hai.
# Output ek hi script text hota hai with multiple '[Scene: ...]' headers, jo
# story_parser.parse_script() khud multi-scene mein tod leta hai.
# ---------------------------------------------------------------------------

# target minutes -> (approx scenes, lines-per-scene). ~5s/line, ~12 lines/min.
LONGFORM_PLANS = {
    "30sec": (1, 6),
    "1min": (2, 6),
    "2min": (3, 8),
    "3min": (4, 9),
    "5min": (6, 10),
    "8min": (8, 12),
    "10min": (10, 12),
    "15min": (15, 12),
}


def generate_longform(idea, language="roman_urdu", characters=None,
                      minutes="5min", genre="auto", on_progress=None,
                      cast_bios=None, continuity="", library=None):
    """
    Multi-scene kahani (30 seconds to 15 minutes). Returns dict:
      {script, title, genre, logline, cast, scenes:[{location, goal}]}.
    on_progress(step, total, msg) optional — UI/CLI progress ke liye.
    cast_bios / continuity: series-mode ke liye (recurring cast + pichhle episodes).
    """
    import json as _json
    import providers
    idea = (idea or "").strip()
    if not idea:
        raise ValueError("Idea chahiye (kis cheez par lambi video?)")
    chars = resolve_script_cast(characters, library) if library else unique_cast_names(characters)
    import character_performance
    performance_rule = character_performance.script_guidance(chars)
    minutes = duration_planner.normalize_duration(minutes, default="5min")
    n_scenes, lines_per = LONGFORM_PLANS[minutes]
    duration_brief = duration_planner.writing_brief(minutes)
    # Divide the spoken-word contract across scenes.  The old ~5 sec/line
    # assumption allowed very short dialogue to turn a 15-minute selection
    # into a 3-4 minute video.
    scene_target_words = max(24, round(duration_brief["target_words"] / n_scenes))
    scene_min_words = max(20, round(duration_brief["minimum_words"] / n_scenes))
    scene_max_words = max(scene_min_words + 8, round(duration_brief["maximum_words"] / n_scenes))
    scene_token_budget = min(1800, max(700, int(scene_max_words * 2.4)))
    lang_name = dialogue_style.language_name(language)
    g = (genre or "auto").lower()

    def prog(i, msg):
        if on_progress:
            try:
                on_progress(i, n_scenes + 1, msg)
            except Exception:
                pass

    # -------- STAGE 1: OUTLINE (beat sheet) --------
    prog(0, "Kahani ka outline ban raha hai...")
    if cast_bios:
        cast_rule = ("Use ONLY these recurring characters, keeping each one's personality "
                     "CONSISTENT:\n" + "\n".join(f"- {b}" for b in cast_bios)
                     + "\nDo NOT invent others.")
    elif chars:
        cast_rule = ("Use ONLY these characters: "
                     f"{', '.join(c.title() for c in chars)}. Do NOT invent others.")
    else:
        cast_rule = ("Invent 2-4 characters that fit the idea (animals, fruits/vegetables, "
                     "people, mascots, objects). Give short, memorable names.")
    genre_rule = ("Auto-detect the best genre." if g in ("", "auto") else f"Genre: {g}.")
    cont_rule = (f"\nSERIES CONTINUITY (later episode — stay consistent, may reference "
                 f"prior events):\n{continuity}" if continuity else "")

    outline_sys = (
        "You are a professional long-form animated-story planner for a kids' cartoon channel. "
        "From one idea you design a coherent multi-scene story with a clear dramatic arc.\n"
        f"{genre_rule}\n{cast_rule}\n"
        f"{performance_rule}\n"
        f"{dialogue_style.full_prompt_policy(language)}\n"
        f"{actions.prompt_policy()}\n"
        f"Plan EXACTLY {n_scenes} scenes forming a full arc: "
        "setup -> rising action -> midpoint turn -> climax -> resolution "
        "(distribute these beats across the scenes).\n"
        f"TOTAL DURATION CONTRACT: {duration_brief['target_label']}; final dialogue must contain "
        f"{duration_brief['minimum_words']}-{duration_brief['maximum_words']} spoken words. "
        f"Give every scene enough plot material for roughly {scene_target_words} spoken words.\n"
        "Each scene must advance the plot and change location or situation.\n"
        "Reply with ONLY JSON (no markdown):\n"
        "{\"title\": \"<catchy title in the story's language>\", "
        "\"genre\": \"<one word>\", "
        "\"logline\": \"<one-sentence summary of the whole story>\", "
        "\"cast\": [{\"name\":\"..\",\"trait\":\"one-line personality\"}], "
        "\"scenes\": [{\"location\":\"<short place>\", "
        "\"goal\":\"<what happens / what this scene must accomplish, 1-2 sentences>\"}]}")
    outline_raw = providers.llm_generate(
        outline_sys, f"Idea: {idea}\nLanguage of title/logline: {lang_name}{cont_rule}",
        max_tokens=1200, temperature=0.85)
    outline_raw = _clean_script(outline_raw)
    try:
        s, e = outline_raw.find("{"), outline_raw.rfind("}")
        outline = _json.loads(outline_raw[s:e + 1])
    except Exception as ex:
        raise RuntimeError(f"Outline JSON parse fail: {ex}")

    title = outline.get("title", "")
    det_genre = outline.get("genre", g if g != "auto" else "")
    logline = outline.get("logline", "")
    cast_objs = outline.get("cast", []) or [{"name": c.title()} for c in chars]
    cast_names = [c.get("name", "") if isinstance(c, dict) else str(c) for c in cast_objs]
    cast_desc = "; ".join(
        f"{c.get('name','')} ({c.get('trait','')})" if isinstance(c, dict) else str(c)
        for c in cast_objs)
    scenes = outline.get("scenes", [])[:n_scenes]
    if not scenes:
        raise RuntimeError("Outline mein koi scene nahi mila")

    # -------- STAGE 2: har scene ka dialogue (continuity ke sath) --------
    scene_sys = (
        "You are a professional cartoon dialogue writer. Write ONE scene of an ongoing story. "
        f"Write ALL dialogue in {lang_name}. Keep continuity with what came before.\n"
        f"{dialogue_style.full_prompt_policy(language)}\n"
        f"{actions.prompt_policy()}\n"
        f"CAST (use consistent personalities): {cast_desc}\n"
        f"{performance_rule}\n"
        f"STORY LOGLINE: {logline}\n"
        "RULES:\n"
        f"- Write about {lines_per} dialogue lines for THIS scene only.\n"
        f"- STRICT WORD CONTRACT: dialogue must contain {scene_min_words}-{scene_max_words} spoken words "
        f"(aim {scene_target_words}); do not return a short scene.\n"
        "- Advance the plot toward this scene's goal; end the scene at a natural point.\n"
        "- Distinct voice per character; natural-to-speak lines. Use specific action, setting and "
        "reaction detail to meet the time; never fill with repeated phrases.\n"
        "- Do NOT resolve the whole story early unless this is the final scene.\n"
        "FORMAT (strict):\n"
        "- First line: [Scene: <location>]\n"
        "- Every other line: 'Name: (emotion; action; location) spoken line'.\n"
        "Reply with ONLY the scene text.")

    parts = []
    recap = ""
    for i, scn in enumerate(scenes, 1):
        loc = scn.get("location", "scene")
        goal = scn.get("goal", "")
        pos = ("FINAL scene — deliver the climax and a satisfying resolution/ending."
               if i == len(scenes) else
               ("OPENING scene — hook the viewer hard in the first 2 lines."
                if i == 1 else "MIDDLE scene — raise the stakes."))
        prog(i, f"Scene {i}/{len(scenes)} likh raha: {loc}")
        user = (f"Scene {i} of {len(scenes)}. {pos}\n"
                f"Location: {loc}\nThis scene's goal: {goal}\n"
                f"Story so far (recap): {recap or 'story start'}\n"
                "Write this scene now.")
        txt = _clean_script(providers.llm_generate(
            scene_sys, user, max_tokens=scene_token_budget, temperature=0.9))
        spoken_words = len(re.findall(r"\S+", " ".join(
            line.split(":", 1)[-1] for line in txt.splitlines()
            if ":" in line and not line.lstrip().lower().startswith("[scene")
        )))
        # Providers occasionally optimise too aggressively for punchy short
        # lines. One focused expansion pass protects the selected duration
        # without inventing a separate story or duplicating dialogue.
        if spoken_words < scene_min_words:
            expand_sys = (
                "You are a precise animated-story editor. Expand this ONE scene while preserving "
                "the exact cast, location, story facts and action format. Keep it natural, "
                "child-friendly and non-repetitive. Return ONLY the complete scene text.\n"
                f"STRICT: deliver {scene_min_words}-{scene_max_words} spoken dialogue words; "
                f"the current draft has only {spoken_words}. Add meaningful reactions, cause/effect, "
                "environmental detail and character decisions?not filler.\n"
                "FORMAT: [Scene: location] then Name: (emotion; action; location) dialogue.")
            txt = _clean_script(providers.llm_generate(
                expand_sys, f"Scene to expand:\n{txt}", max_tokens=scene_token_budget, temperature=0.65))
        # ensure a scene header exists
        if not txt.lstrip().lower().startswith("[scene"):
            txt = f"[Scene: {loc}]\n{txt}"
        parts.append(txt.strip())
        # short recap for next scene continuity (last ~3 lines)
        tail = [l for l in txt.strip().splitlines() if ":" in l][-3:]
        recap = (recap + " | " if recap else "") + f"Scene {i} ({loc}): " + " ".join(tail)[:300]

    script = "\n\n".join(parts).strip()
    actual_words = len(re.findall(r"\S+", " ".join(
        line.split(":", 1)[-1] for line in script.splitlines()
        if ":" in line and not line.lstrip().lower().startswith("[scene")
    )))
    return {
        "script": script,
        "duration_contract": {
            "selected": duration_brief["target_label"],
            "minimum_words": duration_brief["minimum_words"],
            "maximum_words": duration_brief["maximum_words"],
            "actual_words": actual_words,
            "within_budget": duration_brief["minimum_words"] <= actual_words <= duration_brief["maximum_words"],
        },
        "title": title,
        "genre": det_genre,
        "logline": logline,
        "cast": cast_names,
        "scenes": [{"location": s.get("location", ""), "goal": s.get("goal", "")} for s in scenes],
    }
