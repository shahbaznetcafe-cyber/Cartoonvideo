"""
Phase 2 — Retention Critic (deterministic rule engine).

Parses a generated cartoon script and flags the structural problems that make
viewers drop off: a hook that isn't first, static "talking-heads" stretches, a
flat emotional arc, duplicate/dead lines, a missing mid-video pattern interrupt,
and a cold or too-early CTA.  It emits a per-line report and a set of targeted
fix instructions that ``scriptcraft`` feeds into the polish rewrite.

Pure and fully unit-testable: no LLM, no network.  It judges *structure*, which
is what can be checked deterministically; it cannot judge whether a line is
"funny" or will actually retain — that is only knowable from real analytics.
"""
from __future__ import annotations

import re

SCENE_RE = re.compile(r"^\s*\[?\s*scene\s*:", re.IGNORECASE)
# "Name: (emotion; action; location) spoken text"  — paren block optional.
LINE_RE = re.compile(r"^\s*([^:()\n]+?)\s*:\s*(?:\((.*?)\))?\s*(.*\S)?\s*$")

_NO_ACTION = {"", "none", "idle", "still", "stand", "standing", "-", "na", "nahi"}
FLAT_ARC_RUN = 3          # same emotion this many lines in a row = flat
MONOLOGUE_RUN = 3         # same speaker this many lines in a row = stall
CTA_ZONE = 0.6            # CTA should fall in the last 40% of the script

# A satisfying ending resolves the tension.  We check the ending *emotion*
# (language-safe) rather than promise word-overlap, which would false-positive
# across languages (an English promise vs a Roman-Urdu script share no tokens
# even when the payoff genuinely delivers it).
RESOLUTION_EMOTIONS = {
    "relief", "relieved", "happy", "joyful", "joy", "proud", "warm", "tender",
    "triumphant", "content", "satisfied", "encouraging", "hopeful", "grateful",
    "cheerful", "delighted", "peaceful",
}

# A story with no tension anywhere has nothing for the payoff to resolve, which
# is the classic "nothing happens" retention killer.
TENSION_EMOTIONS = {
    "worried", "tense", "scared", "afraid", "nervous", "shocked", "surprised",
    "angry", "sad", "puzzled", "confused", "anxious", "desperate", "determined",
    "suspicious", "frustrated", "urgent", "alarmed",
}
# Fraction of the planned distinct emotions the script should actually use.
ARC_COVERAGE_MIN = 0.5


def _tokens(text):
    return [t for t in re.findall(r"[^\W\d_]+", str(text or "").lower()) if len(t) > 1]


def _split_paren(block):
    """Split '(emotion; action; location)' into its parts (';' or ',' delimited)."""
    raw = str(block or "").strip()
    if not raw:
        return "", "", ""
    parts = re.split(r"[;,]", raw)
    parts = [p.strip() for p in parts]
    emotion = parts[0] if parts else ""
    action = parts[1] if len(parts) > 1 else ""
    location = parts[2] if len(parts) > 2 else ""
    return emotion, action, location


def parse_script(script):
    """Return {'scene': first scene header, 'lines': [line dicts]}.

    Each line: {index, speaker, emotion, action, location, text, hasAction}.
    Scene headers and blank lines are excluded from ``lines``.
    """
    scene = ""
    lines = []
    for raw in str(script or "").splitlines():
        if not raw.strip():
            continue
        if SCENE_RE.match(raw):
            if not scene:
                scene = raw.strip()
            continue
        m = LINE_RE.match(raw)
        if not m:
            continue
        speaker = (m.group(1) or "").strip()
        emotion, action, location = _split_paren(m.group(2))
        text = (m.group(3) or "").strip()
        if not speaker or not text:
            continue
        has_action = action.strip().lower() not in _NO_ACTION
        lines.append({
            "index": len(lines),
            "speaker": speaker,
            "emotion": emotion.lower(),
            "action": action,
            "location": location,
            "text": text,
            "hasAction": has_action,
        })
    return {"scene": scene, "lines": lines}


def _overlap(a, b):
    ta, tb = set(_tokens(a)), set(_tokens(b))
    if not ta or not tb:
        return 0.0
    return len(ta & tb) / len(ta | tb)


def analyze(script, *, hook="", cta="", promise="", beat_sheet=None,
            planned_arc=None, cta_anchor="after_payoff", expected_cast=None):
    """Deterministic retention analysis. Returns a report dict.

    ``promise`` is accepted for the title↔script contract, but the delivery check
    is intentionally structural (the ending must *resolve*), not a word-overlap
    against the promise — see RESOLUTION_EMOTIONS for why.
    """
    parsed = parse_script(script)
    lines = parsed["lines"]
    n = len(lines)
    judgements = [{"index": ln["index"], "speaker": ln["speaker"],
                   "emotion": ln["emotion"], "hasAction": ln["hasAction"],
                   "reasons": [], "retentionRisk": "low"} for ln in lines]
    flags = []

    def add(i, reason, risk="med"):
        j = judgements[i]
        j["reasons"].append(reason)
        order = {"low": 0, "med": 1, "high": 2}
        if order[risk] > order[j["retentionRisk"]]:
            j["retentionRisk"] = risk

    # 1) Hook must be first and must be the chosen hook.
    if n and hook:
        if _overlap(lines[0]["text"], hook) < 0.34:
            add(0, "opening line is not the chosen hook", "high")
            flags.append("hook_not_first")

    # 2) Static talking-heads: adjacent lines both without a body action.
    for i in range(1, n):
        if not lines[i]["hasAction"] and not lines[i - 1]["hasAction"]:
            add(i, "static talking-heads (no body action two lines running)", "med")
            if "static_talking_heads" not in flags:
                flags.append("static_talking_heads")

    # 3) Monologue stall: same speaker several lines in a row.
    run = 1
    for i in range(1, n):
        if lines[i]["speaker"].casefold() == lines[i - 1]["speaker"].casefold():
            run += 1
            if run >= MONOLOGUE_RUN:
                add(i, "monologue stall (same speaker 3+ lines)", "med")
                if "monologue_stall" not in flags:
                    flags.append("monologue_stall")
        else:
            run = 1

    # 4) Flat arc: same emotion for a long run.
    run, arc_flat = 1, False
    for i in range(1, n):
        if lines[i]["emotion"] and lines[i]["emotion"] == lines[i - 1]["emotion"]:
            run += 1
            if run >= FLAT_ARC_RUN:
                arc_flat = True
                add(i, "flat emotional arc (same emotion 3+ lines)", "med")
        else:
            run = 1
    if arc_flat and "flat_arc" not in flags:
        flags.append("flat_arc")

    # 5) Duplicate / dead lines (near-identical spoken text).
    for i in range(1, n):
        for j in range(i):
            if _overlap(lines[i]["text"], lines[j]["text"]) >= 0.8:
                add(i, f"near-duplicate of line {j + 1} (dead line)", "high")
                if "duplicate_lines" not in flags:
                    flags.append("duplicate_lines")
                break

    # 6) Missing mid pattern interrupt: the middle third needs one high-energy
    #    beat (a body action or an emotion change).
    if n >= 6:
        lo, hi = n // 3, (2 * n) // 3
        mid = lines[lo:hi] or lines[lo:lo + 1]
        emotions = {ln["emotion"] for ln in mid}
        if not any(ln["hasAction"] for ln in mid) and len(emotions) <= 1:
            flags.append("missing_mid_interrupt")

    # 7) CTA placement, anchored to the beat sheet's intent.
    if cta and n:
        pos = None
        for ln in lines:
            if _overlap(ln["text"], cta) >= 0.4:
                pos = ln["index"]
        if pos is None:
            flags.append("cta_missing")
        elif cta_anchor == "mid_cliffhanger":
            # Serialised stories tease mid-story; a CTA on the final line (or in
            # the last quarter) misses the cliffhanger moment.  Compare against
            # the last index explicitly so short scripts are handled correctly.
            if pos == n - 1 or pos >= 0.75 * n:
                add(pos, "CTA should land on the mid-story cliffhanger, not the very end", "med")
                flags.append("cta_off_anchor")
        elif pos < CTA_ZONE * n:
            add(pos, "CTA appears too early (should land after the payoff)", "med")
            flags.append("cta_too_early")

    # 8) Weak payoff: the story must END on a resolution, not on unresolved
    #    tension.  The payoff may sit on its own line or share a line with the
    #    CTA, so the ending resolves if EITHER of the last two lines carries a
    #    resolution emotion.  Only flag when neither does (and they have emotions).
    if n >= 3:
        tail = lines[-2:]
        emotions = [ln["emotion"] for ln in tail if ln["emotion"]]
        resolves = any(e in RESOLUTION_EMOTIONS for e in emotions)
        if emotions and not resolves:
            add(lines[-1]["index"], "ends on unresolved emotion — land a satisfying payoff", "med")
            flags.append("weak_payoff")

    # 9) No tension anywhere: the payoff has nothing to resolve.
    script_emotions = [ln["emotion"] for ln in lines if ln["emotion"]]
    if n >= 4 and script_emotions and not any(
            e in TENSION_EMOTIONS for e in script_emotions):
        flags.append("no_tension_beat")

    # 10) Emotion arc vs the planned beat-sheet arc: the script should actually
    #     travel through the intended moods, not collapse them into one or two.
    if planned_arc:
        planned_distinct = {str(e).lower() for e in planned_arc if e}
        used_distinct = set(script_emotions)
        if planned_distinct:
            coverage = len(used_distinct) / len(planned_distinct)
            if coverage < ARC_COVERAGE_MIN:
                flags.append("arc_off_plan")

    # 11) Series cast drift: a recurring show must not invent new speakers, and
    #     should actually use the established cast.
    if expected_cast:
        allowed = {str(name).strip().casefold() for name in expected_cast if str(name).strip()}
        if allowed:
            used = {ln["speaker"].casefold() for ln in lines}
            intruders = sorted(used - allowed)
            if intruders:
                for ln in lines:
                    if ln["speaker"].casefold() in intruders:
                        add(ln["index"], f"'{ln['speaker']}' is not in the series cast", "high")
                flags.append("cast_drift")
            if allowed - used:
                flags.append("cast_unused")

    high = sum(1 for j in judgements if j["retentionRisk"] == "high")
    med = sum(1 for j in judgements if j["retentionRisk"] == "med")
    return {
        "lineCount": n,
        "lineJudgements": judgements,
        "flags": flags,
        "arcFlatness": arc_flat,
        "riskCounts": {"high": high, "med": med, "low": n - high - med},
    }


_FIX_TEXT = {
    "hook_not_first": "Make line 1 the chosen scroll-stopping hook, verbatim in intent.",
    "static_talking_heads": "Break up stretches where characters just talk: give at "
        "least one a visible body action (walk, point, reach, react) or cut the weaker line.",
    "monologue_stall": "Avoid the same character speaking 3+ lines in a row; interleave "
        "reactions from other characters.",
    "flat_arc": "The emotion is flat for several lines — vary the mood so tension moves "
        "toward the climax.",
    "duplicate_lines": "Remove near-duplicate lines; every line must add new story, stakes "
        "or character.",
    "missing_mid_interrupt": "Add a mid-video pattern interrupt (a surprise reaction, sound, "
        "or location change) so attention resets before the drop-off point.",
    "cta_too_early": "Move the engagement/CTA line to after the payoff, at the emotional peak.",
    "cta_missing": "End with one short engagement line (a question or call to comment) after "
        "the payoff.",
    "weak_payoff": "The ending doesn't resolve — deliver the title's promise with a clear, "
        "satisfying payoff (relief/joy/pride), not unresolved tension.",
    "cta_off_anchor": "Move the engagement line to the mid-story cliffhanger where the "
        "curiosity peaks, not the final line.",
    "no_tension_beat": "Nothing is at stake anywhere — add a real complication or worry "
        "before the ending so the payoff means something.",
    "arc_off_plan": "The emotional journey collapsed: move through the planned moods "
        "(curious -> worried -> tense -> relief) instead of staying in one register.",
    "cast_drift": "A speaker outside the series cast appeared — use only the established "
        "recurring characters so the show stays recognisable.",
    "cast_unused": "Some established cast members never speak — give each recurring "
        "character at least one line.",
}


def flag_notes(report):
    """Flags as {flag, note} pairs for the review UI (same wording as the fixes)."""
    return [{"flag": f, "note": _FIX_TEXT[f]}
            for f in report.get("flags", []) if f in _FIX_TEXT]


def fix_instructions(report):
    """Turn flags into targeted rewrite directives for the polish pass.

    Returns '' when the script already passes every structural check, which lets
    ``scriptcraft`` skip an unnecessary rewrite.
    """
    directives = [_FIX_TEXT[f] for f in report.get("flags", []) if f in _FIX_TEXT]
    # Cite the highest-risk lines so the rewrite is surgical, not wholesale.
    risky = [str(j["index"] + 1) for j in report.get("lineJudgements", [])
             if j["retentionRisk"] == "high"]
    if risky:
        directives.append("Pay special attention to line(s) " + ", ".join(risky) + ".")
    return "\n".join(f"- {d}" for d in directives)
