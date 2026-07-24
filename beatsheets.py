"""
Phase 1 — Retention beat sheets (data-driven story structure).

A beat sheet replaces the old fixed ``["setup","escalation","turn","payoff"]``
with a named, per-genre sequence of *typed* beats.  Each beat carries a
retention role, an intended emotion, and a relative word ``weight``.  Given a
duration writing-brief (from ``duration_planner.writing_brief``) the beats are
scaled into an exact per-beat word budget so pacing is planned, not accidental.

No network, no LLM: this module is pure data + arithmetic and is fully unit
testable.  ``scriptcraft`` consumes ``build(genre, brief)`` and feeds the result
into the draft prompt and the enriched result dict.
"""
from __future__ import annotations

# Beat types (also the contract for the Phase 2 retention critic):
#   cold_open | open_loop | setup | escalation | pattern_interrupt
#   | twist | climax | payoff | button | cta
def _beat(bid, btype, purpose, retention, weight, emotion):
    return {"id": bid, "type": btype, "purpose": purpose,
            "retentionRole": retention, "weight": float(weight), "emotion": emotion}


# Each sheet is ordered opening -> ending.  Weights are RELATIVE (not percent);
# they are normalised against the duration brief at build() time.
BEAT_SHEETS = {
    "moral_story": [
        _beat("cold_open", "cold_open",
              "Pose the dramatic question in one punchy line — no 'once upon a time'.",
              "Stops the scroll in the first seconds.", 1.0, "curious"),
        _beat("open_loop", "open_loop",
              "Plant the exact thing the viewer must see resolved.",
              "Opens a curiosity loop that holds attention.", 1.1, "intrigued"),
        _beat("setup", "setup",
              "Show the character's normal world and clear want.",
              "Gives stakes something to threaten.", 1.4, "warm"),
        _beat("escalation_1", "escalation",
              "First complication raises the stakes.",
              "Keeps tension climbing.", 1.5, "worried"),
        _beat("pattern_interrupt", "pattern_interrupt",
              "A surprise reaction, sound, or location change mid-story.",
              "Resets attention before the drop-off point.", 1.0, "surprised"),
        _beat("escalation_2", "escalation",
              "Second, bigger complication; the wrong choice tempts.",
              "Raises stakes toward the peak.", 1.5, "tense"),
        _beat("climax", "climax",
              "Highest tension — the character must choose.",
              "The emotional peak viewers stay for.", 1.3, "tense"),
        _beat("payoff", "payoff",
              "The loop closes; the lesson is SHOWN through action, not lectured.",
              "Satisfying resolution that earns a like.", 1.4, "relief"),
        _beat("cta", "cta",
              "Warm engagement line at the peak of good feeling.",
              "Converts emotion into a comment/subscribe.", 0.6, "warm"),
    ],
    "comedy_skit": [
        _beat("cold_open", "cold_open",
              "Open mid-joke or on a funny contradiction with one visible prop.",
              "Instant laugh hook.", 1.0, "playful"),
        _beat("open_loop", "open_loop",
              "Set up the misunderstanding the viewer wants resolved.",
              "Curiosity + comedy loop.", 1.0, "amused"),
        _beat("escalation_1", "escalation",
              "Escalate through contrasting reactions.",
              "Comedy compounds.", 1.4, "playful"),
        _beat("pattern_interrupt", "pattern_interrupt",
              "A sudden reversal or deadpan beat.",
              "Attention reset via surprise.", 1.0, "surprised"),
        _beat("escalation_2", "escalation",
              "Bigger, sillier consequence.",
              "Peak comedic tension.", 1.4, "playful"),
        _beat("twist", "twist",
              "Reveal the harmless truth behind the mix-up.",
              "The 'aha' that earns a rewatch.", 1.2, "surprised"),
        _beat("payoff", "payoff",
              "One concise comic button.",
              "Lands the laugh.", 1.1, "happy"),
        _beat("cta", "cta",
              "Comment-bait tied to the joke (ask the viewer to pick a side).",
              "Drives comments.", 0.6, "playful"),
    ],
    "adventure": [
        _beat("cold_open", "cold_open",
              "Drop the viewer into motion or mild danger — in media res.",
              "Action hook.", 1.0, "excited"),
        _beat("open_loop", "open_loop",
              "Name the goal / treasure / destination.",
              "Sets the quest loop.", 1.0, "curious"),
        _beat("setup", "setup",
              "Give each character a distinct useful role.",
              "Invests the viewer in the team.", 1.2, "hopeful"),
        _beat("escalation_1", "escalation",
              "First obstacle on the route.",
              "Raises stakes.", 1.4, "tense"),
        _beat("pattern_interrupt", "pattern_interrupt",
              "A discovery or new location changes the plan.",
              "Attention reset.", 1.1, "surprised"),
        _beat("escalation_2", "escalation",
              "A harder, physical obstacle.",
              "Toward the peak.", 1.4, "tense"),
        _beat("climax", "climax",
              "Teamwork solves the biggest challenge.",
              "Peak payoff moment.", 1.3, "triumphant"),
        _beat("payoff", "payoff",
              "Reach the goal; show the reward.",
              "Satisfying arrival.", 1.2, "joyful"),
        _beat("cta", "cta",
              "Tease the next adventure / ask where to go next.",
              "Series pull + comments.", 0.6, "excited"),
    ],
    "mystery": [
        _beat("cold_open", "cold_open",
              "Open on the moment something goes missing/wrong.",
              "Question hook.", 1.0, "puzzled"),
        _beat("open_loop", "open_loop",
              "State the mystery question plainly.",
              "The loop the whole video answers.", 1.0, "curious"),
        _beat("setup", "setup",
              "Introduce investigator + clue-keeper roles.",
              "Frames the hunt.", 1.2, "focused"),
        _beat("escalation_1", "escalation",
              "First clue changes the next action.",
              "Progress + tension.", 1.4, "intrigued"),
        _beat("pattern_interrupt", "pattern_interrupt",
              "A misleading clue or false suspicion.",
              "Attention reset via doubt.", 1.1, "surprised"),
        _beat("escalation_2", "escalation",
              "Second clue narrows it down.",
              "Closing in.", 1.3, "tense"),
        _beat("twist", "twist",
              "A fair, surprising reveal.",
              "Payoff for staying.", 1.3, "surprised"),
        _beat("payoff", "payoff",
              "Resolve fairly; no unnamed suspects.",
              "Satisfying answer.", 1.1, "relief"),
        _beat("cta", "cta",
              "Ask viewers if they guessed it.",
              "Comment driver.", 0.6, "playful"),
    ],
    "friendship": [
        _beat("cold_open", "cold_open",
              "Open on a small but real child-friendly problem.",
              "Emotional hook.", 1.0, "worried"),
        _beat("open_loop", "open_loop",
              "Will someone notice and help?",
              "Emotional loop.", 1.0, "hopeful"),
        _beat("setup", "setup",
              "Show the friendship and the stakes.",
              "Investment.", 1.3, "warm"),
        _beat("escalation_1", "escalation",
              "The problem gets harder; a small obstacle.",
              "Tension.", 1.4, "worried"),
        _beat("pattern_interrupt", "pattern_interrupt",
              "An unexpected gesture or moment.",
              "Attention reset.", 1.0, "surprised"),
        _beat("climax", "climax",
              "A sincere helping action.",
              "Emotional peak.", 1.3, "tender"),
        _beat("payoff", "payoff",
              "Hopeful resolution, not over-sentimental.",
              "Warm satisfaction.", 1.3, "warm"),
        _beat("cta", "cta",
              "Ask viewers to tag a friend.",
              "Share driver.", 0.6, "warm"),
    ],
    "learning": [
        _beat("cold_open", "cold_open",
              "Open on a surprising question or a wrong guess.",
              "Curiosity hook.", 1.0, "curious"),
        _beat("open_loop", "open_loop",
              "Promise the one thing they'll learn.",
              "Benefit loop.", 1.0, "intrigued"),
        _beat("setup", "setup",
              "Set the visual challenge.",
              "Framing.", 1.2, "focused"),
        _beat("escalation_1", "escalation",
              "First attempt fails or half-works.",
              "Tension via trial.", 1.4, "determined"),
        _beat("pattern_interrupt", "pattern_interrupt",
              "A surprising correction or fact.",
              "Attention reset.", 1.1, "surprised"),
        _beat("climax", "climax",
              "The correct method clicks.",
              "Peak insight.", 1.3, "excited"),
        _beat("payoff", "payoff",
              "Show the success; one clear takeaway.",
              "Satisfying learning.", 1.3, "proud"),
        _beat("cta", "cta",
              "Ask viewers to try it and report back.",
              "Comment/engagement.", 0.6, "encouraging"),
    ],
}

DEFAULT_GENRE = "moral_story"

# Where the engagement line belongs for each genre.  "after_payoff" = land the
# resolution first, then ask (default for self-contained stories).
# "mid_cliffhanger" suits serialised stories that tease the next episode.
CTA_ANCHORS = {
    "moral_story": "after_payoff",
    "comedy_skit": "after_payoff",
    "adventure": "after_payoff",
    "mystery": "after_payoff",
    "friendship": "after_payoff",
    "learning": "after_payoff",
}
DEFAULT_CTA_ANCHOR = "after_payoff"

# Free-text genres and story_templates ids -> a beat sheet.
GENRE_ALIASES = {
    "auto": DEFAULT_GENRE, "": DEFAULT_GENRE, "story": DEFAULT_GENRE,
    "moral": "moral_story", "moral_story": "moral_story", "sabaq": "moral_story",
    "nasihat": "moral_story", "lesson_story": "moral_story",
    "comedy": "comedy_skit", "comedy_skit": "comedy_skit", "funny": "comedy_skit",
    "funny_mixup": "comedy_skit", "mazah": "comedy_skit", "skit": "comedy_skit",
    "adventure": "adventure", "cinematic_adventure": "adventure",
    "pirate_treasure": "adventure", "space_mission": "adventure",
    "action_escape": "adventure", "quest": "adventure", "safar": "adventure",
    "mystery": "mystery", "mystery_case": "mystery",
    "detective_vs_rival": "mystery", "jasoos": "mystery",
    "friendship": "friendship", "friendship_journey": "friendship",
    "dosti": "friendship", "teamwork_challenge": "friendship",
    "festival_event": "friendship", "character_roles": "friendship",
    "learning": "learning", "learning_by_doing": "learning",
    "seekho": "learning", "educational": "learning",
}


def resolve_genre(genre):
    """Map any genre/template id/free word to a known beat-sheet key."""
    key = str(genre or "").strip().lower().replace(" ", "_")
    if key in BEAT_SHEETS:
        return key
    if key in GENRE_ALIASES:
        return GENRE_ALIASES[key]
    # substring fallback (e.g. "space adventure" -> adventure)
    for alias, target in GENRE_ALIASES.items():
        if alias and alias in key:
            return target
    return DEFAULT_GENRE


def _allocate_words(weights, total_words, floor=3):
    """Largest-remainder allocation: integers that sum EXACTLY to total_words,
    each >= floor, proportional to weights.  Deterministic (Hamilton method)."""
    n = len(weights)
    total_words = max(total_words, floor * n)
    wsum = sum(weights) or 1.0
    exact = [w / wsum * total_words for w in weights]
    base = [max(floor, int(x)) for x in exact]
    remainder = total_words - sum(base)
    if remainder > 0:
        # give leftover words to the beats with the largest fractional parts
        order = sorted(range(n), key=lambda i: (exact[i] - int(exact[i])), reverse=True)
        for k in range(remainder):
            base[order[k % n]] += 1
    elif remainder < 0:
        # trim from the largest beats without dropping below floor
        order = sorted(range(n), key=lambda i: base[i], reverse=True)
        k = 0
        while remainder < 0:
            i = order[k % n]
            if base[i] > floor:
                base[i] -= 1
                remainder += 1
            k += 1
            if k > n * total_words:      # safety, cannot loop forever
                break
    return base


def build(genre, brief):
    """Return a duration-scaled beat sheet for ``genre``.

    ``brief`` is a ``duration_planner.writing_brief`` dict (uses ``target_words``).
    Each returned beat gains an integer ``words`` budget; the budgets sum exactly
    to ``brief['target_words']``.  Also returns the ordered emotion arc.
    """
    key = resolve_genre(genre)
    sheet = BEAT_SHEETS[key]
    target_words = int((brief or {}).get("target_words") or 0)
    weights = [b["weight"] for b in sheet]
    words = _allocate_words(weights, target_words) if target_words > 0 else [0] * len(sheet)
    beats = []
    for beat, w in zip(sheet, words):
        item = dict(beat)
        item["words"] = int(w)
        beats.append(item)
    return {
        "genre": key,
        "beats": beats,
        "emotionArc": [b["emotion"] for b in beats],
        "ctaAnchor": CTA_ANCHORS.get(key, DEFAULT_CTA_ANCHOR),
        "totalWords": sum(words),
    }


def assign_to_scenes(built, scene_count):
    """Spread a built beat sheet across N long-form scenes.

    Long-form writes scene by scene, so each scene needs its own slice of the
    retention structure.  Beats are distributed in order and every scene gets at
    least one beat; the opening scene always owns the cold_open and the final
    scene always owns the payoff/cta beats.
    """
    beats = list(built.get("beats") or [])
    n = max(1, int(scene_count or 1))
    if not beats:
        return [{"roles": [], "emotions": [], "words": 0} for _ in range(n)]
    if n >= len(beats):
        # More scenes than beats: one beat each, trailing scenes reuse the last.
        groups = [[b] for b in beats] + [[beats[-1]]] * (n - len(beats))
        groups = groups[:n]
    else:
        groups = [[] for _ in range(n)]
        for index, beat in enumerate(beats):
            # Proportional placement keeps the opening/closing beats at the ends.
            slot = min(n - 1, index * n // len(beats))
            groups[slot].append(beat)
        for slot in range(n):          # never leave a scene without a role
            if not groups[slot]:
                groups[slot].append(beats[min(slot, len(beats) - 1)])
    return [{
        "roles": [b["type"] for b in group],
        "purposes": [b["purpose"] for b in group],
        "emotions": [b["emotion"] for b in group],
        "words": sum(int(b.get("words") or 0) for b in group),
    } for group in groups]


def as_prompt_lines(built):
    """Render a built beat sheet as newline text for the draft prompt."""
    lines = []
    for i, b in enumerate(built.get("beats", []), 1):
        lines.append(
            f"{i}. [{b['type']}] (~{b['words']} words, emotion: {b['emotion']}) "
            f"{b['purpose']}")
    return "\n".join(lines)
