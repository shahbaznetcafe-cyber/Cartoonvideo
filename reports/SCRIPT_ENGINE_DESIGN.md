# Retention Script Engine — Detailed Design

Design doc for upgrading SBZ script generation from "coherent story" to
"retention-built, platform-aware story" for YouTube monetization.

> **Honesty contract:** This design contains **no invented metrics, no fake
> benchmarks, and no guaranteed-views claims.** Retention is only ever proven by
> uploading real videos and reading YouTube Analytics. This engine raises the
> *probability* of good retention by encoding craft that professional creators
> use; it cannot promise outcomes. Any number that would need real data is
> marked `[NEEDS REAL DATA]`.

---

## 1. Goal & non-goals

**Goal:** Every generated script should (a) open with a scroll-stopping hook,
(b) hold attention with escalating beats and pattern interrupts, (c) pay off
emotionally, (d) match its own clickable title/thumbnail promise, and (e) place
engagement CTAs at emotional peaks — while staying kid-safe and capability-aware
(body-only vs jaw vs facial characters).

**Non-goals:**
- No guaranteed virality or view counts.
- No scraping of live YouTube trends (we take a topic/keyword from the user).
- No change to the render pipeline; this is script-layer only.
- Not replacing the human. A review/edit gate stays (YouTube inauthenticity policy).

---

## 2. Current architecture (grounded in code)

Two systems exist today:

| System | File | Role | Retention craft? |
|---|---|---|---|
| **Primary** | [scriptcraft.py](../scriptcraft.py) | `craft()` = PLAN→DRAFT→POLISH. Feeds freeform/longform/templates. | Partial — 3 blind hooks, one-line "first 2s" note, single critic pass |
| **Structured** | [script_engine/](../script_engine/) | 9-stage schema-validated pipeline with approve gates. | None — STORY_ARCHITECT only asks for "coherent child-safe story" |

Entry points that reach `scriptcraft.craft()`:
- [story_templates.py:268](../story_templates.py) `generate_from_template()`
- [story_templates.py:345](../story_templates.py) `generate_freeform()`
- `api_freeform` / `api_longform` / `api_story_template_generate` in [app.py](../app.py)

`craft()` returns:
```
{script, title, genre, logline, cast, hook, hooks, beats, cta, character_performance}
```

**Gap summary:** hooks are generated blind (no scoring), beats are a fixed
4-item list (`setup→escalation→turn→payoff`) not tuned per genre/platform, the
critic pass is holistic (no line-level retention check), there is no
title↔script contract, no emotional-arc model, no CTA-timing logic, and series
memory is only a free-text `continuity` string.

---

## 3. Target architecture — the Retention Script Engine

Upgrade `scriptcraft.craft()` into a **5-stage** pipeline (keeps the same public
return contract, adds fields):

```
IDEA
  │
  ├─▶ (0) PREMISE      → clickable title + logline + core promise + audience
  │
  ├─▶ (1) BEAT-SHEET   → genre-tuned retention structure (cold-open, open-loop,
  │                       escalation ladder, twist, payoff, CTA anchor)
  │
  ├─▶ (2) HOOK LAB     → 6-8 hook variants → rubric score → pick best + reason
  │
  ├─▶ (3) DRAFT        → full script bound to beat-sheet + hook + emotional arc
  │
  ├─▶ (4) RETENTION    → line-level critic: hook strength, dead-line cull,
  │       CRITIC          voice-distinctness, pattern-interrupt spacing, payoff,
  │                       CTA at peak
  │
  └─▶ RESULT (enriched dict)
```

Each stage is a pure function `providers.llm_generate(...) → validated dict/text`,
mirroring the existing `_plan/_draft/_polish` style so it drops into the current
provider/cache/cancel plumbing.

---

## 4. Component design

### A. Retention Beat-Sheet models (`beatsheets.py`, new)

Replace the fixed `["setup","escalation","turn","payoff"]` with **named,
per-genre beat sheets** as data, each a list of typed beats:

```python
BEAT = {"id","type","purpose","retentionRole","minWords","emotion"}
# type ∈ cold_open | open_loop | setup | escalation | pattern_interrupt
#        | twist | climax | payoff | button | cta
```

Example (moral-story genre, ~1 min):
```
cold_open        (0-5s)   pose the dramatic question, no "once upon a time"
open_loop        (5-10s)  plant the thing the viewer must see resolved
escalation×2-3            each beat raises stakes / adds a complication
pattern_interrupt        a surprise reaction / sound / location change mid-way
twist                    expectation flip
climax                   highest tension
payoff                   loop closes; the lesson is *shown*, not lectured
cta / button             engagement line at the emotional peak
```

Beat sheets are **duration-scaled**: `duration_planner.writing_brief()` already
gives target words; the beat-sheet allocates words per beat so pacing is planned,
not accidental. Beat sheets are also **capability-aware**: for a body-only cast,
`escalation`/`twist` beats get more physical-action weight and shorter speech
(reuses `character_performance.script_guidance`).

Genres to ship: `moral_story, comedy_skit, adventure, mystery, friendship,
learning`. Each maps to an existing template in [story_templates.py](../story_templates.py)
so the UI genre picker just selects a beat sheet.

### B. Hook Lab (`hooklab.py`, new; upgrades `_plan` hooks)

Today: 3 hooks, model picks one blind. New:

1. Generate **6-8** hook variants across fixed *angles*: question, shock,
   bold-claim, in-media-res action, funny-contradiction, relatable-problem,
   countdown/list, "you won't believe".
2. Score each on a **deterministic rubric** (model returns per-hook sub-scores,
   we combine with fixed weights — the *weights* are ours, not the model's):
   - `curiosity` (opens a loop) · `clarity` (instantly understood) ·
     `emotion` · `promiseMatch` (fits the title) · `sayable` (natural TTS in the
     language) · `childSafe`.
3. Pick top hook; keep the ranked list in the result for the UI to override.

**Why scoring, not vibes:** blind single-pick can't be inspected or A/B'd. Scored
variants give the creator a dropdown of hooks with reasons — a real pro workflow.
The rubric weights are tunable in config; **their "correctness" can only be
validated by real upload tests** `[NEEDS REAL DATA]`, so they ship as sensible
defaults, not as proven values.

### C. Retention Critic pass (`_retention_critic`, upgrades `_polish`)

Keep `_polish`'s holistic edit but add an explicit, structured pre-pass that
returns a **per-line judgement**, then applies it:

```
for each line: {keep|tighten|cut, reason, retentionRisk: low|med|high}
```
Rules the critic enforces (all craft, no data):
- Line 1 must be the chosen hook, unmodified in intent.
- No two adjacent lines with the same function (kills "talking heads" stall).
- A pattern-interrupt beat must land inside the middle third.
- Cut any line that neither advances plot, raises stakes, nor reveals character.
- CTA sits at/after the climax, never cold.
- Voice-distinctness: each character's lines must be swappable-test-distinct.

Output stays the same script format so nothing downstream changes.

### D. Title ↔ Script contract (stage 0 PREMISE + `metadata.py` link)

Currently title is a by-product of the plan. Invert it: **premise-first.**

1. Stage 0 produces `{title, promise, logline, audience, coreMessage}` where
   `promise` = the single curiosity/benefit the title implies.
2. Every later stage receives `promise`; the critic checks the payoff *delivers*
   it (click-bait mismatch = retention death and policy risk).
3. Feed the same `promise` into [metadata.py](../metadata.py) so the generated
   title/description/thumbnail-text and the script are one coherent package.

### E. Emotional arc model (field on the plan, enforced in draft+critic)

Attach an intended emotion curve to the beat sheet, e.g.
`calm → curious → worried → tense → relief → warm`. The draft prompt gets the
curve; the critic flags a *flat* arc (same emotion 3+ beats running). This maps
directly onto the renderer, which already consumes per-line `emotion` and drives
face/pose — so a planned arc improves the *visuals* too, not just the words.

### F. Series / character memory (`series.py` integration)

Replace the free-text `continuity` string with structured recall from
[series.py](../series.py):
```
{characterId: {persona, catchphrase, speechStyle, relationships, priorEvents[]}}
```
Injected into PREMISE + DRAFT so recurring characters stay consistent and can
carry running gags (catchphrase = channel identity = subscriber retention).
This is the growth lever: channels grow on *recurring characters*, not one-offs.

### G. CTA placement

CTA becomes a **typed beat** (D above) with an anchor: `at_climax | after_payoff
| mid_cliffhanger`. Default `after_payoff` for stories, `mid_cliffhanger` for
multi-part series. The critic verifies the CTA is not the coldest line in the
script.

### H. Trend / topic input (honest scope)

The creator supplies a topic/keyword/seasonal angle (e.g. "Ramadan sharing",
"exam stress"). We **do not** invent trend data. Stage 0 folds the topic into the
premise. Optional future hook: let the user paste a competitor title they liked;
we extract its *structure* (not its content) as a beat-sheet hint. Anything
claiming live trend numbers would be fabricated, so it is out of scope.

---

## 5. Data structures

Enriched result dict (superset of today's — old keys preserved for
compatibility with `story_parser` / `build.py`):
```python
{
  # existing (unchanged):
  "script", "title", "genre", "logline", "cast", "hook", "hooks",
  "beats", "cta", "character_performance",
  # new:
  "promise": str,                      # the click promise the payoff must deliver
  "audience": str,
  "beatSheet": [BEAT, ...],            # typed, word-budgeted, emotion-tagged
  "emotionArc": [str, ...],
  "hookRanking": [{"text","angle","scores","total","reason"}, ...],
  "ctaAnchor": str,
  "retentionReport": {                 # from the critic, for the review UI
     "lineJudgements": [...], "flags": [...], "arcFlatness": bool
  },
  "seriesRefs": {...} | None,
}
```
`build.py`/`story_parser` read only `script` today, so they are unaffected; the
new fields power the **review UI** and `metadata.py`.

---

## 6. Prompt changes (specific)

- `_plan` → split into **`_premise`** (title/promise/audience) and
  **`_beatsheet`** (selects + fills a genre beat sheet with word budgets).
- Hook generation moves to `hooklab.generate_and_score()`; the plan just records
  the winner + ranking.
- `_draft` gains: `PROMISE`, `BEAT SHEET (typed, per-beat word budget)`,
  `EMOTION ARC`, `SERIES MEMORY`. It writes beat-by-beat, not free-form.
- `_polish` → `_retention_critic` returns structured line judgements first, then
  rewrites. Same output format.
- All prompts keep the existing `dialogue_style.full_prompt_policy(language)` +
  `actions.prompt_policy()` + `character_performance` guidance so language,
  capability and safety rules are unchanged.

---

## 7. Integration points

| Touch | Change |
|---|---|
| [scriptcraft.py](../scriptcraft.py) `craft()` | 3-stage → 5-stage; return enriched dict |
| `beatsheets.py`, `hooklab.py` | new modules (pure, testable) |
| [story_templates.py](../story_templates.py) | genre → beat-sheet id mapping |
| [metadata.py](../metadata.py) | consume `promise` for title/desc/thumbnail alignment |
| [series.py](../series.py) | structured `seriesRefs` provider |
| [app.py](../app.py) preview/UI | show hook ranking + retention report in the review step |
| [config.py](../config.py) | rubric weights, beat-sheet defaults, feature flag |

Feature-flag the whole thing: `SCRIPT_ENGINE_V2 = os.getenv(...) == "1"`, default
on but with a fallback to current `craft()` so nothing breaks mid-migration.

---

## 8. Testing strategy (honest)

**What we CAN test deterministically (no LLM, no network):**
- Beat-sheet selection & word-budget allocation sums to the duration brief.
- Hook rubric combiner: given fixed sub-scores, the ranking/weights are correct.
- Critic rule engine: given a synthetic script, it flags adjacent same-function
  lines, a missing mid pattern-interrupt, a cold CTA, a flat arc.
- Schema validation of the enriched dict; back-compat of old keys.
- `metadata.py` uses `promise` and stays within title length limits.

**What we CANNOT unit-test (be explicit):**
- Whether a hook *actually* retains viewers — that is `[NEEDS REAL DATA]`, only
  YouTube Analytics on real uploads answers it. The tests prove the *machinery*
  is correct, not that the output is popular.

**Recommended real-world loop:** ship 3-5 videos per beat sheet, read 30-day
retention/CTR in Analytics, then tune rubric weights and beat word-budgets from
*your own* data. Build a tiny local log so the creator can record which hook
angle they used per video and correlate later.

---

## 9. Phased rollout

1. **Phase 1 — Beat sheets + Hook Lab** (`beatsheets.py`, `hooklab.py`, wire into
   `_plan`). Biggest quality jump; fully unit-testable.
2. **Phase 2 — Retention Critic** (upgrade `_polish`). Line-level culling.
3. **Phase 3 — Premise-first + title contract** (stage 0 + `metadata.py`).
4. **Phase 4 — Emotion arc + CTA anchor** (draft/critic enforcement).
5. **Phase 5 — Series memory** (structured `series.py` recall).
6. **Phase 6 — Review UI** surfacing hook ranking + retention report + edit gate.

Each phase is independently shippable and keeps `craft()`'s contract.

---

## 10. Risks & honest limitations

- **LLM variance:** more stages = more calls = more latency/cost and more places
  to drift. Mitigate with caching (already in the engine) and the feature flag.
- **Over-optimization looks fake:** aggressive hooks + templated structure can
  trip YouTube's mass-produced-content policy. The human edit gate and per-video
  variety (randomized beat/hook choices) are the guardrail, not optional.
- **Language nuance:** hooks that work in English may fall flat in Urdu/Hindi;
  the rubric's `sayable`/`emotion` scores are model-judged and imperfect. Real
  A/B in-language is the only true check `[NEEDS REAL DATA]`.
- **No trend guarantee:** we improve craft, not luck. This is stated plainly to
  the creator in the UI so expectations are honest.

---

## 11. Open decisions for the owner

1. Build order — confirm Phase 1 (beat sheets + hook lab) first?
2. Default language for hook-angle tuning (Roman Urdu?).
3. Keep the advanced `script_engine/` 9-stage pipeline as the "pro/manual" mode,
   or fold its review-gate idea into `scriptcraft` and retire the duplicate?
4. How many hook variants to show the creator in the UI (6? 8?).
