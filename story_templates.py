"""
Story Templates — 15 ready-made kahani formulas (different scenarios).
User ek template chunta hai + topic deta hai -> AI us formula par poora script likhta hai
(format: 'Name: dialogue', jo seedha parse_script + video engine mein chala jaye).

Har template: id, name (roman), name_en, emoji, desc, mood, structure (beat sheet),
chars (library characters), lines (approx dialogue count), sample_topic.
"""

TEMPLATES = [
    {
        "id": "moral", "name": "Akhlaqi Kahani", "name_en": "Moral Story", "emoji": "📖",
        "desc": "Bachon ke liye sabak-amoz kahani — ghalti, anjaam, sabak.",
        "mood": "emotional", "chars": ["aloo", "tamatar"], "lines": 8,
        "sample_topic": "jhoot bolne ka bura anjaam",
        "structure": "Set up a normal situation. One character makes a mistake or bad choice. "
                     "Show the consequence. Another character explains the lesson. End with a clear moral message.",
    },
    {
        "id": "comedy", "name": "Comedy Skit", "name_en": "Comedy Skit", "emoji": "😂",
        "desc": "Halki-phulki hansi, misunderstanding aur funny punchline.",
        "mood": "comedy", "chars": ["mirch", "kela"], "lines": 8,
        "sample_topic": "ek dusre ko galti se pehchan na paana",
        "structure": "Start with a funny hook. Build a silly misunderstanding between characters. "
                     "Escalate the confusion with witty banter. End on an unexpected comic punchline.",
    },
    {
        "id": "health", "name": "Sehat Ka Sabak", "name_en": "Health & Nutrition", "emoji": "🥗",
        "desc": "Sabzion/phalon ke faide — sehat ka paigham (veggie characters perfect).",
        "mood": "educational", "chars": ["gajar", "aloo", "tamatar"], "lines": 9,
        "sample_topic": "sabzian khane se taakat milti hai",
        "structure": "A character feels weak or unhealthy. Vegetable friends explain their health "
                     "benefits one by one in a fun way. The character tries them and feels energetic. End with a health tip.",
    },
    {
        "id": "friendship", "name": "Dosti Ki Kahani", "name_en": "Friendship Story", "emoji": "🤝",
        "desc": "Dosti, qurbani aur ittehad ka paigham.",
        "mood": "emotional", "chars": ["kela", "ananas"], "lines": 8,
        "sample_topic": "sachi dosti mushkil waqt mein saabit hoti hai",
        "structure": "Two friends are happy together. One faces a problem or danger. The other helps "
                     "selflessly. Their bond grows stronger. End with a message about true friendship.",
    },
    {
        "id": "riddle", "name": "Paheli", "name_en": "Riddle / Guess", "emoji": "❓",
        "desc": "Bujho to jaanein — audience ke liye paheli aur jawab.",
        "mood": "comedy", "chars": ["aloo", "gajar"], "lines": 7,
        "sample_topic": "ek aisi cheez jo laal hai lekin phal nahi",
        "structure": "A character poses a fun riddle to the audience and friends. Others give funny wrong "
                     "guesses. Build suspense. Reveal the answer with a cheerful surprise. Invite viewers to comment.",
    },
    {
        "id": "goodbad", "name": "Achai vs Burai", "name_en": "Good vs Bad", "emoji": "⚖️",
        "desc": "Achai aur burai ka mqabla — achai jeet ti hai.",
        "mood": "drama", "chars": ["tamatar", "mirch"], "lines": 9,
        "sample_topic": "lalach bura anjaam laati hai",
        "structure": "Introduce a good character and a greedy/bad character. The bad one tries a shortcut "
                     "or trick. It backfires. The good character's honesty wins. End with justice and a lesson.",
    },
    {
        "id": "problem", "name": "Mushkil Ka Hal", "name_en": "Problem–Solution", "emoji": "💡",
        "desc": "Ek masla, mil kar hoshiyari se hal.",
        "mood": "educational", "chars": ["aloo", "kela", "gajar"], "lines": 9,
        "sample_topic": "paani ki kami ka masla",
        "structure": "A community problem appears. Characters discuss and fail with simple ideas. "
                     "Someone suggests a clever solution. They work as a team to solve it. End with teamwork message.",
    },
    {
        "id": "adventure", "name": "Mhim-Joi", "name_en": "Adventure", "emoji": "🗺️",
        "desc": "Safar, khatra aur bahaduri ka adventure.",
        "mood": "action", "chars": ["mirch", "ananas"], "lines": 9,
        "sample_topic": "jungle mein khoya hua khazana",
        "structure": "Characters set off on an exciting journey. They face an obstacle or danger. "
                     "They use courage and cleverness to overcome it. They reach the goal. End on a triumphant note.",
    },
    {
        "id": "debate", "name": "Behas / Muqabla", "name_en": "Debate / Contest", "emoji": "🎤",
        "desc": "Do characters ka mazaqiya muqabla — kaun behtar?",
        "mood": "comedy", "chars": ["aloo", "tamatar"], "lines": 8,
        "sample_topic": "kaun zyada important hai, aloo ya tamatar",
        "structure": "Two characters argue about who is better/more useful. Each boasts funny claims. "
                     "A third character or twist settles it. End with the lesson that everyone is important.",
    },
    {
        "id": "emotional", "name": "Jazbati Kahani", "name_en": "Emotional Journey", "emoji": "💗",
        "desc": "Dukh se khushi ka jazbati safar.",
        "mood": "emotional", "chars": ["kela", "aloo"], "lines": 8,
        "sample_topic": "akela mehsoos karna aur phir dost milna",
        "structure": "A character is sad or lonely. Show their struggle with feeling. A friend notices "
                     "and comforts them. Things turn hopeful. End with a warm, uplifting message.",
    },
    {
        "id": "talkshow", "name": "Talk Show", "name_en": "Interview / Talk Show", "emoji": "🎙️",
        "desc": "Ek character host, dusra mehmaan — funny interview.",
        "mood": "comedy", "chars": ["tamatar", "gajar"], "lines": 9,
        "sample_topic": "carrot se uski kamyabi ka interview",
        "structure": "A host character welcomes a guest on a fun show. Host asks quirky questions. "
                     "Guest gives funny/wise answers. A comic moment happens. End with a cheerful sign-off.",
    },
    {
        "id": "rhyme", "name": "Nazm / Geet", "name_en": "Rhyme / Poem", "emoji": "🎵",
        "desc": "Chhoti si rhyming nazm — bachon ke liye.",
        "mood": "comedy", "chars": ["aloo", "kela", "gajar"], "lines": 8,
        "sample_topic": "sabzion ka khushi bhara geet",
        "structure": "Characters sing a short, catchy rhyming poem together, each adding a line. "
                     "Keep lines short and rhythmic with repetition. End with a cheerful chorus everyone says.",
    },
    {
        "id": "festival", "name": "Eid / Tehwaar Special", "name_en": "Festival Special", "emoji": "🎉",
        "desc": "Eid ya kisi tehwaar ki khushi aur paigham.",
        "mood": "emotional", "chars": ["aloo", "tamatar", "kela"], "lines": 9,
        "sample_topic": "Eid ki khushiyan mil kar manana",
        "structure": "Characters prepare to celebrate a festival. A small conflict about sharing appears. "
                     "They resolve it with generosity. They celebrate together joyfully. End with a festive greeting.",
    },
    {
        "id": "safety", "name": "Hifazat Ka Sabak", "name_en": "Safety Lesson", "emoji": "🛡️",
        "desc": "Bachon ko hifazat/safety sikhaye (safai, traffic, ajnabi).",
        "mood": "educational", "chars": ["gajar", "mirch"], "lines": 8,
        "sample_topic": "sarak paar karne ke usool",
        "structure": "A character is about to do something unsafe. A wiser friend stops them and explains "
                     "the safe way step by step. They practice it correctly. End with a clear safety rule.",
    },
    {
        "id": "mystery", "name": "Jasoosi / Muamma", "name_en": "Mystery / Detective", "emoji": "🔍",
        "desc": "Kuch gum ho gaya — jasoosi kar ke hal.",
        "mood": "suspense", "chars": ["aloo", "tamatar", "mirch"], "lines": 9,
        "sample_topic": "gum-shuda tiffin ka muamma",
        "structure": "Something goes missing. A detective character gathers clues. Suspects give funny "
                     "alibis. Tension builds. The detective reveals the surprising truth. End by solving the case.",
    },
]

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
LENGTH_LINES = {"short": 6, "medium": 10, "long": 16}


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
        for e in char3d_lib.all_valid():
            slug = e.get("blend", "").replace(".blend", "")
            out.append({"id": e["name"], "name": e["name"],
                        "emoji": _cat_emoji(slug), "package": slug})
    except Exception:
        pass
    return out


def all_templates():
    """UI ke liye — halka (structure prompt ke bagair)."""
    return [{k: t[k] for k in ("id", "name", "name_en", "emoji", "desc", "mood", "chars", "lines", "sample_topic")}
            for t in TEMPLATES]


def get(template_id):
    return _BY_ID.get(template_id)


def generate_from_template(template_id, topic="", language="roman_urdu",
                           characters=None, lines=None, length="medium", quality="pro"):
    """
    Template ke formula par AI se poora script likhwao ('Name: dialogue' format).
    quality="pro" -> Quality Engine (template ki structure = structure_hint).
    """
    import providers
    t = get(template_id)
    if not t:
        raise ValueError(f"Template nahi mila: {template_id}")
    chars = [c for c in (characters or t["chars"]) if c]
    if len(chars) < 2:
        chars = (chars + [c for c in t["chars"] if c not in chars])[:2] or t["chars"]
    n = int(lines) if lines else LENGTH_LINES.get(length, 10)
    approx_sec = n * 5
    topic = (topic or t["sample_topic"]).strip()

    if quality == "pro":
        import scriptcraft
        return scriptcraft.craft(
            topic, language=language, characters=chars, length=length, lines=lines,
            genre=t["name_en"], structure_hint=t["structure"])["script"]

    lang_name = {"urdu": "Urdu (Urdu script)", "roman_urdu": "Roman Urdu",
                 "english": "English"}.get(language, "Roman Urdu")
    names = ", ".join(c.title() for c in chars)

    sysp = (
        "You are a professional viral short-video script writer for an animated cartoon channel. "
        "The characters can be anything the cast specifies (animals, fruits/vegetables, people, "
        "mascots, objects) — write for whatever cast is given, kids-friendly cartoon tone.\n"
        f"GENRE: {t['name_en']}.\n"
        f"STRUCTURE (follow this beat sheet exactly): {t['structure']}\n"
        f"CAST: use ONLY these characters as speakers, and use EVERY one of them at least once: {names}. "
        "Do NOT invent any other character.\n"
        f"LENGTH: exactly about {n} dialogue lines (roughly a {approx_sec}-second video). "
        "Do not go over.\n"
        f"LANGUAGE: write ALL dialogue in {lang_name}.\n"
        "QUALITY BAR:\n"
        "- Line 1 must be a STRONG hook that grabs attention instantly.\n"
        "- Give each character a distinct voice/personality consistent with the genre.\n"
        "- Build the beats, then land a clear, satisfying ending (moral/punchline/reveal per genre).\n"
        "- Keep every line short, punchy and natural to speak aloud.\n"
        "FORMAT (strict):\n"
        "- First output line: [Scene: <short place>]\n"
        "- Every other line: 'Name: (emotion) spoken line'  where emotion is one of "
        "happy|sad|angry|excited|surprised|neutral and is optional.\n"
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
                      cast_bios=None, continuity="", quality="pro"):
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
    if quality == "pro":
        import scriptcraft
        return scriptcraft.craft(idea, language=language, characters=characters,
                                 length=length, lines=lines, genre=genre,
                                 cast_bios=cast_bios, continuity=continuity)
    chars = [c for c in (characters or []) if c and c.strip()]
    n = int(lines) if lines else LENGTH_LINES.get(length, 10)
    approx_sec = n * 5
    lang_name = {"urdu": "Urdu (Urdu script)", "roman_urdu": "Roman Urdu",
                 "english": "English"}.get(language, "Roman Urdu")
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
        f"LENGTH: about {n} dialogue lines (~{approx_sec}s video). Do not go over.\n"
        f"LANGUAGE: write ALL dialogue in {lang_name}.\n"
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
        "- Every other line: 'Name: (emotion) spoken line'  (emotion optional, one of "
        "happy|sad|angry|excited|surprised|neutral)\n"
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
    "3min": (4, 9),
    "5min": (6, 10),
    "8min": (8, 12),
}


def generate_longform(idea, language="roman_urdu", characters=None,
                      minutes="5min", genre="auto", on_progress=None,
                      cast_bios=None, continuity=""):
    """
    Lambi multi-scene kahani (3-8 min). Returns dict:
      {script, title, genre, logline, cast, scenes:[{location, goal}]}.
    on_progress(step, total, msg) optional — UI/CLI progress ke liye.
    cast_bios / continuity: series-mode ke liye (recurring cast + pichhle episodes).
    """
    import json as _json
    import providers
    idea = (idea or "").strip()
    if not idea:
        raise ValueError("Idea chahiye (kis cheez par lambi video?)")
    chars = [c for c in (characters or []) if c and c.strip()]
    n_scenes, lines_per = LONGFORM_PLANS.get(minutes, LONGFORM_PLANS["5min"])
    lang_name = {"urdu": "Urdu (Urdu script)", "roman_urdu": "Roman Urdu",
                 "english": "English"}.get(language, "Roman Urdu")
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
        f"Plan EXACTLY {n_scenes} scenes forming a full arc: "
        "setup -> rising action -> midpoint turn -> climax -> resolution "
        "(distribute these beats across the scenes).\n"
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
        f"CAST (use consistent personalities): {cast_desc}\n"
        f"STORY LOGLINE: {logline}\n"
        "RULES:\n"
        f"- Write about {lines_per} dialogue lines for THIS scene only.\n"
        "- Advance the plot toward this scene's goal; end the scene at a natural point.\n"
        "- Distinct voice per character; short, punchy, natural-to-speak lines.\n"
        "- Do NOT resolve the whole story early unless this is the final scene.\n"
        "FORMAT (strict):\n"
        "- First line: [Scene: <location>]\n"
        "- Every other line: 'Name: (emotion) spoken line' (emotion one of "
        "happy|sad|angry|excited|surprised|neutral, optional).\n"
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
            scene_sys, user, max_tokens=1000, temperature=0.9))
        # ensure a scene header exists
        if not txt.lstrip().lower().startswith("[scene"):
            txt = f"[Scene: {loc}]\n{txt}"
        parts.append(txt.strip())
        # short recap for next scene continuity (last ~3 lines)
        tail = [l for l in txt.strip().splitlines() if ":" in l][-3:]
        recap = (recap + " | " if recap else "") + f"Scene {i} ({loc}): " + " ".join(tail)[:300]

    script = "\n\n".join(parts).strip()
    return {
        "script": script,
        "title": title,
        "genre": det_genre,
        "logline": logline,
        "cast": cast_names,
        "scenes": [{"location": s.get("location", ""), "goal": s.get("goal", "")} for s in scenes],
    }
