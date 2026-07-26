# Phase 7 Runware Provider Architecture

Date: 2026-07-15

## Outcome

The existing Runware integration was extended rather than replaced. Browser code calls Flask only; the Runware credential remains in the existing backend configuration path.

## Request path

1. `templates/index.html` and `static/js/studio.js` collect the selected stage, language, model and optional comparison consent.
2. Flask endpoints in `app.py` create a cancellable background job.
3. `script_engine/pipeline.py` selects the stage schema and saves structured intermediate output.
4. Normalized providers in `script_engine/providers.py` map the stage to a task category.
5. `script_engine/engine.py` resolves an editable route, cache key, validated model and bounded fallback.
6. `runware_client.py` uses either Runware native tasks or the OpenAI-compatible chat endpoint.
7. Output is parsed as untrusted data, schema-validated and semantically validated before it can be approved.

## Normalized interfaces

- `TextParserProvider`
- `StoryGenerationProvider`
- `DialogueGenerationProvider`
- `ScriptEnhancementProvider`
- `TranslationProvider`
- `AnimationPlanningProvider`

## Persistence and approval

The stages are Story Idea, Story Outline, Character Profiles, Scene Breakdown, Character Dialogue, Script Doctor, Visual Story Beats, Animation Plan and Storyboard. Each record is stored under the selected project's `script_pipeline` directory. A stage can be edited, approved or regenerated independently. Animation Plan and Storyboard reject unapproved input.

## Reliability boundaries

- One transport retry after a transient failure.
- One JSON repair attempt.
- At most one model fallback.
- Comparison sends a second paid request only when explicitly enabled.
- Cancellation is checked before requests, between retries and while streaming.
- Cache keys include task, executable model ID, prompt version, content hash, schema version, language, mode and generation settings.
- Cache and reports exclude credentials and authorization headers.

## Compatibility

Existing provider selection, legacy Runware model aliases, `/api/preview`, story parsing, rendering and project flows remain available. The Phase 7 engine is additive and no complete episode was generated.
