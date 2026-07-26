"""
Phase 1 — Hook Lab (multi-variant hook generation + deterministic scoring).

The old planner produced 3 hooks and let the model pick one blind.  Hook Lab
generates several hooks across fixed *angles*, has the model self-rate each on a
rubric, then combines those sub-scores with OUR fixed weights so the choice is
inspectable and overridable.  The combiner (``score_hooks``) is pure and fully
unit-testable; only ``generate_and_score`` touches the LLM.

Honesty: the rubric weights are sensible defaults, not values proven to lift
retention.  Only real uploads + YouTube Analytics can validate them.
"""
from __future__ import annotations

import json

# Fixed hook angles we ask the writer to cover (variety beats one blind guess).
ANGLES = (
    "question",          # pose an irresistible question
    "shock",             # a surprising statement
    "bold_claim",        # a strong claim that demands proof
    "in_media_res",      # drop into mid-action
    "funny_contradiction",
    "relatable_problem",
    "countdown_list",    # "3 cheezein jo..."
    "curiosity_gap",     # "you won't believe what..."
)

# Rubric dimensions the model rates 0..10; we normalise to 0..1 and weight.
# Weights sum to 1.0.  childSafe is also a hard gate (see score_hooks).
RUBRIC_WEIGHTS = {
    "curiosity": 0.28,     # does it open a loop?
    "clarity": 0.20,       # instantly understood?
    "emotion": 0.22,       # does it make you feel something?
    "promiseMatch": 0.15,  # fits the title/promise?
    "sayable": 0.10,       # natural to speak aloud in the language?
    "childSafe": 0.05,     # kid-appropriate?
}
CHILD_SAFE_GATE = 0.5      # below this, the hook is heavily deprioritised
_GATE_PENALTY = 0.2


def _norm(value):
    """Coerce a model score on the prompted 0..10 scale to 0..1.

    The prompt always asks for 0-10, so we divide by 10 (not auto-detect): that
    keeps a rating of ``1`` meaning 1/10 = 0.1, never a perfect 1.0.
    """
    try:
        v = float(value)
    except (TypeError, ValueError):
        return 0.0
    return max(0.0, min(1.0, v / 10.0))


def score_hooks(hooks, weights=None):
    """Pure combiner.  ``hooks`` = list of {text, angle, scores:{dim:0..10}}.

    Returns a new list sorted best-first, each with a combined ``total`` (0..1)
    and integer ``rank``.  Deterministic: ties break by original order.
    """
    weights = weights or RUBRIC_WEIGHTS
    scored = []
    for index, hook in enumerate(hooks or []):
        raw = hook.get("scores") or {}
        dims = {dim: _norm(raw.get(dim)) for dim in weights}
        total = sum(weights[dim] * dims[dim] for dim in weights)
        if dims.get("childSafe", 1.0) < CHILD_SAFE_GATE:
            total *= _GATE_PENALTY          # unsafe hooks sink, never chosen
        scored.append({
            "text": str(hook.get("text") or "").strip(),
            "angle": str(hook.get("angle") or "").strip(),
            "scores": dims,
            "total": round(total, 4),
            "_order": index,
        })
    scored.sort(key=lambda h: (-h["total"], h["_order"]))
    for rank, hook in enumerate(scored, 1):
        hook["rank"] = rank
        hook.pop("_order", None)
    return scored


def _build_prompt(idea, promise, lang_name, count):
    system = (
        "You are a world-class short-video hook writer. Write scroll-stopping "
        f"opening lines in {lang_name}.\n"
        f"Produce {count} DISTINCT hooks, each using a different angle from this "
        f"list: {', '.join(ANGLES)}.\n"
        "Each hook is ONE spoken line that could be the very first thing said in "
        "the video. Keep it natural to say aloud, kid-safe, and true to the story "
        "(no clickbait the story can't deliver).\n"
        "For EACH hook, self-rate 0-10 on: curiosity (opens a loop), clarity "
        "(instantly understood), emotion, promiseMatch (fits the promise), sayable "
        "(natural spoken), childSafe.\n"
        "Reply with ONLY JSON:\n"
        '{"hooks":[{"text":"..","angle":"question","scores":{"curiosity":0,'
        '"clarity":0,"emotion":0,"promiseMatch":0,"sayable":0,"childSafe":0}}]}'
    )
    user = f"Story idea: {idea}\nTitle promise (what the payoff must deliver): {promise}"
    return system, user


def _parse(raw):
    text = (raw or "").strip()
    if text.startswith("```"):
        text = text.strip("`")
        nl = text.find("\n")
        if nl != -1 and len(text[:nl].split()) <= 1:
            text = text[nl + 1:]
    start, end = text.find("{"), text.rfind("}")
    data = json.loads(text[start:end + 1])
    hooks = data.get("hooks") if isinstance(data, dict) else data
    return hooks if isinstance(hooks, list) else []


def generate_and_score(providers, idea, promise, lang_name, count=8,
                       fallback_hook=""):
    """LLM hook generation + deterministic scoring.

    Returns {"hook": best_text, "hooks": [texts...], "ranking": [scored...]}.
    Never raises: on any failure it returns the fallback hook so ``craft`` keeps
    working exactly as before.
    """
    try:
        system, user = _build_prompt(idea, promise, lang_name, count)
        raw = providers.llm_generate(system, user, max_tokens=1200, temperature=0.9)
        parsed = _parse(raw)
        ranking = score_hooks(parsed)
    except Exception as exc:   # network/parse/provider issues must not break craft
        print(f"  [hooklab fallback] {str(exc)[:140]}", flush=True)
        ranking = []
    if not ranking:
        best = str(fallback_hook or idea or "").strip()
        return {"hook": best, "hooks": [best] if best else [], "ranking": []}
    return {
        "hook": ranking[0]["text"],
        "hooks": [h["text"] for h in ranking],
        "ranking": ranking,
    }
