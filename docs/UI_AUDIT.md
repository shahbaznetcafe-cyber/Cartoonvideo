# SBZ AI Video Studio — Phase 0 UI Audit

Audit date: 2026-07-13  
Repository root: `D:\flayer\sbz-studio`  
Audited frontend: `templates/index.html`  
Baseline commit: `b5d00ad` (`main`), with existing uncommitted ElevenLabs voice-selector work preserved  
Scope: audit and baseline only; no redesign or backend contract changes were made

## 1. Baseline summary

The current frontend is a single Flask/Jinja template containing the complete UI, presentation, and browser logic:

- 1,209 lines / approximately 72 KB in `templates/index.html`
- approximately 6,980 inline CSS characters
- approximately 42,712 inline JavaScript characters
- 182 inline `style=` declarations
- 102 unique static DOM IDs in the current working-tree source
- 54 named JavaScript functions
- 33 `fetch()` call sites
- 8 `alert()` calls and 2 `confirm()` calls

The page currently uses a fixed three-column layout:

1. 210 px navigation sidebar
2. central creation column
3. 380 px settings inspector

Both the central column and right inspector scroll independently. The document itself also has a small vertical overflow. This produces two to three competing scroll contexts, especially at 1280x720.

The running server was intentionally not restarted because a video generation test was active. Baseline screenshots were captured with a separate isolated headless Chrome process. The running process served the pre-ElevenLabs-selector template (97 runtime IDs); the current source contains five additional ElevenLabs UI IDs, bringing the audited source total to 102. This source/runtime difference is expected until the application is restarted later by the user.

## 2. Baseline screenshots and browser results

| Viewport | Screenshot | Horizontal page overflow | Middle pane | Inspector pane | Preview/Generate visible initially |
|---|---|---:|---:|---:|---:|
| 1920x1080 | [baseline-1920x1080.png](ui-baseline/baseline-1920x1080.png) | No | 1,496 px content / 1,024 px viewport | 1,029 / 1,024 px | No |
| 1440x900 | [baseline-1440x900.png](ui-baseline/baseline-1440x900.png) | No | 1,526 / 844 px | 1,029 / 844 px | No |
| 1280x720 | [baseline-1280x720.png](ui-baseline/baseline-1280x720.png) | No | 1,539 / 664 px | 1,029 / 664 px | No |

Machine-readable capture data: [baseline-report.json](ui-baseline/baseline-report.json)

Browser findings:

- HTTP document load: 200 at all three sizes.
- JavaScript page errors: none.
- Failed application API requests: none during initial load.
- Console: one 404 for `/favicon.ico` in the first isolated page; no application JavaScript exception.
- No horizontal page scrollbar was present at the three requested baseline sizes.
- The main Preview and Generate actions are below the first viewport at every audited size.

Latest automated baseline from this same working tree, recorded before the audit capture:

- Python: 46 tests passed.
- Three.js runtime: 14 tests passed.
- The suites were not re-run during the active user render, to avoid competing for CPU/GPU resources; Phase 1 will re-run them before its checkpoint.

## 3. Existing feature inventory

### Application shell

- SBZ AI Video Studio title and version
- engine-ready status
- raw LLM/image/TTS provider status
- left navigation shortcuts to generator, script, generation controls, and projects
- collapsible right-side settings groups

### Script creation

- manual script editor
- dialogue formatting hint
- script analysis
- script improvement
- YouTube package generation: titles, description, tags, thumbnail text, pinned comment, and chapters
- quick/free-form AI generation with genre, language, length, and Pro quality
- long-form multi-scene generation with genre, language, and target duration
- story-template selection and generation
- generated scripts are copied into the manual script editor

### Characters and series

- recurring character library
- create and delete recurring characters
- character name, gender, trait, and catchphrase
- series creation with premise, genre, language, and cast
- existing series selection
- episode history
- continuity-aware episode generation

### Preview and scene editing

- script parsing into characters and scenes
- automatic 3D character assignment
- GLB capability/compatibility reporting
- character package override
- costume, accessory, and held-item override
- scene background prompt editing
- dialogue text editing
- line emotion editing
- confirm edited plan and generate without changing the preview API shape

### Video generation

- direct generation without preview
- confirm-and-generate from edited preview
- 3D Characters, Puppet 2D, and Cinematic story modes
- multi-character toggle
- Three.js and Blender render-engine selection
- quality, FPS, fast preview, and NVENC controls
- motion preset, render mode, vignette, intro, and outro behavior
- captions/subtitles controls
- Edge TTS and ElevenLabs provider selection
- Urdu accent, voice volume, and music volume
- API/provider tester
- live four-stage progress: story, voice, assets, render
- Stop Generation
- final video preview and MP4 download

### Projects and recovery

- project count and list
- load an existing project into the editor
- play completed project video
- delete project
- unfinished-project detection
- resume unfinished projects from cached work
- stop-state message explaining that completed work is safe
- project list refresh after completion, stop, and errors

## 4. DOM ID inventory

All current IDs must remain stable until every reference has been moved and contract-tested. A mechanical comparison found no literal `getElementById()` reference without a corresponding static element.

| Area | IDs |
|---|---|
| Shell/status | `provStatus` |
| Resume/projects | `resumeCard`, `resumeList`, `projCardTop`, `projCount`, `projList` |
| Script core | `scriptCard`, `script`, `scriptFeedback`, `pkgPanel`, `scriptTabs` |
| Quick AI | `ffIdea`, `ffGenre`, `ffLang`, `ffLenSeg`, `ffPro`, `ffGenBtn`, `ffMsg` |
| Long-form | `lfIdea`, `lfGenre`, `lfLang`, `lfMinSeg`, `lfGenBtn`, `lfMsg`, `lfOutline` |
| Recurring characters | `chName`, `chGender`, `chTrait`, `chPhrase`, `charList` |
| Series/episodes | `serSel`, `newSeriesBox`, `serName`, `serPremise`, `serGenre`, `serLang`, `serCast`, `epBox`, `serInfo`, `epHistory`, `epIdea`, `epLenSeg`, `epGenBtn`, `epMsg` |
| Templates | `tplGrid`, `tplPanel`, `tplName`, `tplTopic`, `tplChars`, `tplLenSeg`, `tplLang`, `tplGenBtn`, `tplMsg` |
| Generation/preview/result | `genCard`, `storySeg`, `multiChar`, `render_engine`, `previewBtn`, `genBtn`, `costEst`, `previewCard`, `pvTitle`, `pvChars`, `pvScenes`, `pvGenBtn`, `progressCard`, `steps`, `stopBtn`, `errMsg`, `resultCard`, `rTitle`, `rVideo`, `rDownload` |
| Style/format | `style`, `aspectSeg`, `quality`, `fps`, `fast_preview`, `gpu_encode` |
| Motion/render | `motionSeg`, `modeSeg`, `vignette`, `intro_on` |
| Captions | `cap_enabled`, `cap_words`, `cap_size`, `posSeg`, `cap_hl`, `hlSeg`, `cap_perspk` |
| Voice/audio | `tts_provider`, `edge_voice_group`, `urdu_accent`, `eleven_voice_group`, `elevenlabs_voice_id`, `eleven_voice_status`, `refresh_eleven_voices`, `voice_volume`, `music_volume` |
| Advanced/API test | `test_img`, `testBtn`, `testResult` |

Total: 102 unique static IDs.

IDs primarily used through delegated/query-selector logic rather than literal `getElementById()` calls are `aspectSeg`, `costEst`, `epLenSeg`, `ffLenSeg`, `hlSeg`, `lfMinSeg`, `modeSeg`, `motionSeg`, `posSeg`, `scriptTabs`, `steps`, `storySeg`, and `tplLenSeg`.

Runtime-created elements also depend on these class/data contracts:

- `.tab`, `.tabpanel`, `data-t`
- `.seg`, `button.on`, `data-v`
- `.tplChip`, `data-id`, `data-cid`
- `.pvRow`, `.pvVeg`, `.pvCostume`, `.pvAcc`, `.pvHeld`, `.capSlot`, `data-cid`
- `.pvScene`, `.pvBg`, `.pvLine`, `.pvEmo`, `.pvText`, `data-si`, `data-li`
- `#steps li`, `data-s`, `.msg`

## 5. JavaScript function and handler inventory

### Boot and provider initialization

- `load`, `loadLib`, `loadTemplates`, `load3dValidation`
- `loadElevenLabsVoices`, `syncVoiceProviderUI`, `elevenVoiceLabel`
- `initScriptTabs`, `segVal`
- `escHtml`, `capabilityMarkup`

Boot order is currently `loadLib()` followed by `load()`. `load()` fetches options, applies defaults, binds the TTS/voice controls, then starts templates, resumable-project, projects-list, and script-tab initialization.

### Script/AI functions

- `genFreeform`, `genLongform`, `genFromTemplate`
- `selectTemplate`, `toggleChar`
- `analyzeScript`, `improveScript`, `genPackage`
- `_scriptLang`, `_copy`, `suggestStyle`

### Character and series functions

- `renderCharList`, `addChar`, `delChar`
- `renderSeriesSel`, `renderCastPicker`
- `toggleNewSeries`, `createSeries`, `selectSeries`, `genEpisode`

### Preview and generation functions

- `preview`, `renderPreview`, `collectEditedParsed`
- `generate`, `confirmGenerate`, `startJob`
- `setStages`, `poll`, `stopJob`, `_resetStop`
- `showResult`, `showErr`, `reset`

### Project/recovery functions

- `checkResumable`, `loadProjectsList`, `toggleProjects`
- `openProject`, `playProject`, `delProject`
- `resumeProject`, `dropProject`

### Settings/test function

- `collectSettings`, `testRunware`

Static inline handlers currently call navigation `scrollIntoView`, project toggling, all script generators, character/series actions, Analyze/Improve/Package, style suggestion, Preview/Generate/Confirm, Stop, and API testing. Additional handlers are inserted dynamically for template/character chips, segmented controls, preview character changes, project actions, resume actions, deletion, and clipboard copy.

## 6. API endpoint inventory used by the current frontend

The redesign must preserve method, URL, payload keys, and response assumptions for every route below.

| Method | Endpoint | Current purpose / payload dependency |
|---|---|---|
| GET | `/api/options` | Styles, voices, provider status, accents, render engines, defaults |
| GET | `/api/voices/elevenlabs?refresh=1` | Optional account voice refresh and story-ranked voice list |
| GET | `/api/characters3d/validation` | Character capability reports |
| GET | `/api/story-templates` | Story template catalog |
| GET | `/api/characters` | Available template/3D character packages |
| POST | `/api/story-templates/generate` | `{template_id, topic, language, length, characters}` -> script |
| POST | `/api/freeform` | `{idea, genre, language, length, quality}` -> generated story/script metadata |
| POST | `/api/longform` | `{idea, genre, language, minutes}` -> long-form story/script metadata |
| GET | `/api/characters-lib` | Recurring character library |
| POST | `/api/characters-lib` | `{name, gender, trait, catchphrase}` |
| DELETE | `/api/characters-lib/<cid>` | Delete recurring character |
| GET | `/api/series` | Series list |
| GET | `/api/series/<sid>` | Series detail and episode history |
| POST | `/api/series` | `{name, premise, genre, language, cast}` |
| POST | `/api/series/<sid>/episode` | `{idea, length}` -> episode/script |
| POST | `/api/suggest-style` | `{script}` -> `{style}` |
| POST | `/api/analyze` | `{script, language}` -> scores, titles, improvements, strengths |
| POST | `/api/improve` | `{script, language}` -> improved script |
| POST | `/api/metadata` | `{script, language}` -> YouTube package |
| GET | `/api/costumes` | Costume options for preview characters |
| GET | `/api/accessories` | Accessory options for preview characters |
| GET | `/api/held` | Held-item options for preview characters |
| POST | `/api/preview` | `{script}` -> title, language, characters, scenes, packages, parsed plan |
| GET | `/api/resumable` | Unfinished/resumable project summaries |
| GET | `/api/projects` | Project summaries |
| GET | `/api/project/<name>` | Script, settings, parsed plan, final-video state |
| DELETE | `/api/projects/<name>` | Delete project data/video |
| POST | `/api/resume/<name>` | Resume a cached project -> job ID |
| POST | `/api/generate` | `{script, settings, parsed?}` -> job ID and project name |
| GET | `/api/status/<job_id>` | Poll state/stage/progress/result/error every 1.5 seconds |
| POST | `/api/stop/<job_id>` | Mark the current job cancelled while keeping cached work |
| POST | `/api/test-runware` | `{image: boolean}` -> provider diagnostics |
| GET | `/char3d-thumb/<name>` | Preview character thumbnail |
| GET | `/projects/<path>` | Final MP4 preview/download |

### Existing backend routes not actively surfaced by `index.html`

These contracts must also remain intact even if later views expose them more clearly:

- `POST /api/cost`
- `GET /api/templates`
- `POST /api/template`
- `GET /api/template/<name>`
- `POST /api/batch`
- `GET /api/platforms`
- `POST /api/export/<name>`
- `GET /api/plugins`
- `POST /api/plugins/install`
- `PUT /api/series/<sid>`
- `DELETE /api/series/<sid>`
- `GET /char-img/<path>`

`costEst` exists in the DOM, but the current frontend does not call `POST /api/cost`. The redesign should wire estimation only with the existing route and response shape; it must not invent a replacement API.

## 7. `collectSettings()` contract

The following exact payload is sent under `settings` to `/api/generate`. Phase work must retain every key, including duplicated top-level/nested caption state and the constant outro flag.

| Key | UI source / current behavior |
|---|---|
| `style` | `style` select |
| `aspect` | selected `aspectSeg` button |
| `quality` | `quality` select |
| `fps` | `fps` select value |
| `fast_preview` | `fast_preview` checkbox |
| `motion_preset` | selected `motionSeg` button |
| `render_mode` | selected `modeSeg` button |
| `story_mode` | selected `storySeg` button |
| `multi_char` | `multiChar` checkbox |
| `render_engine` | `render_engine` select |
| `gpu` | `"auto"` when `gpu_encode` is checked, otherwise `"off"` |
| `vignette` | `vignette` checkbox |
| `subtitles_on` | `cap_enabled` checkbox |
| `intro_on` | `intro_on` checkbox |
| `outro_on` | always `true` |
| `tts_provider` | `tts_provider` select |
| `urdu_accent` | `urdu_accent` only for Edge; otherwise empty string |
| `elevenlabs_voice_id` | selected ElevenLabs voice only for ElevenLabs; otherwise empty string |
| `voice_volume` | `voice_volume` text value |
| `music_volume` | `music_volume` number value |
| `captions.enabled` | `cap_enabled` checkbox |
| `captions.words_per_group` | `cap_words` value |
| `captions.font_size` | `cap_size` value |
| `captions.position` | selected `posSeg` button |
| `captions.highlight_color` | `cap_hl` value |
| `captions.highlight_style` | selected `hlSeg` button |
| `captions.per_speaker_color` | `cap_perspk` checkbox |

Project loading currently restores only subtitle and intro state from saved settings. All other current values remain in the form. The redesign must improve state restoration carefully without changing saved project JSON or generation payloads.

## 8. Critical user flows

### Initialization

1. Fetch global options/defaults and provider status.
2. Populate style and provider-dependent voice UI.
3. Fetch template catalog and character packages.
4. Fetch recurring characters and series.
5. Fetch resumable projects and project list.
6. Bind tabs, segmented buttons, and dynamic controls.

### Manual script to render

1. User writes script in `script`.
2. Optional Analyze, Improve, YouTube Package, or style suggestion.
3. User either previews or directly generates.
4. Preview parses script and renders editable character/scene controls.
5. Confirm collects the edited parsed plan without changing its structure.
6. Generate sends script, exact settings object, and optional parsed plan.
7. UI polls every 1.5 seconds and updates the four stages.
8. Done displays `/projects/<video_rel>` and download link.

### AI script generation

Quick Idea, Long-form, Template, and Series Episode each have distinct payloads, but all successful paths replace the manual `script` value and keep the rest of the page state in memory.

### Resume flow

1. `/api/resumable` supplies unfinished items.
2. Resume hides the resume card, shows progress, and calls `/api/resume/<name>`.
3. Returned job ID enters the same polling loop as a new generation.
4. Completed clips/assets remain cached; stop/error paths refresh resumable and project lists.

### Existing project flow

1. `/api/projects` renders project rows.
2. Load fetches `/api/project/<name>` and restores script, parsed plan, and limited saved settings.
3. Completed projects can set the result video source directly.
4. Delete calls the existing DELETE route after native confirmation.

## 9. Regression-sensitive contracts

- Do not rename or remove the 102 IDs before their callers are migrated and tested.
- Preserve dynamic class names and `data-*` attributes used by preview, tabs, segments, templates, progress, and character overrides.
- Preserve global state objects: `OPTS`, `CUR_JOB`, `CHAR_CAPS`, `PLAN`, template/character selections, series state, and preview option caches.
- Preserve boot execution order and async data dependencies.
- Preserve `PLAN.parsed` deep-copy editing and `char_overrides`, `costumes`, `accessories`, and `held` keys.
- Preserve the 1.5-second job polling behavior unless backend compatibility is verified.
- Preserve stop semantics and cached resume messaging.
- Preserve media URL construction and cache-busting query timestamps.
- Preserve conditional Edge/ElevenLabs settings behavior.
- Preserve the nested captions object and top-level subtitle flag.
- Preserve all current error response handling while replacing native alerts with app UI later.
- Do not turn view navigation into page reloads; current in-memory form and plan state must survive view/step changes.

## 10. Baseline UX and accessibility findings

### High priority

- The screen reads as a long settings form rather than a focused creation workflow.
- Resume projects dominate the top of the creation screen.
- Preview/Generate actions are initially off-screen at all requested sizes.
- Center and inspector have independent scrollbars; the document has a small third vertical overflow.
- All settings are presented at once, creating high cognitive load.
- Navigation scrolls to page sections rather than switching application views.
- Project deletion and form validation rely on native `confirm()`/`alert()`.
- Current runtime exposes the full provider string permanently.

### Visual/system consistency

- Color tokens do not match the requested production design system.
- Blue, green, purple, amber, and red are used inconsistently for primary actions.
- Decorative emoji are used as icons throughout markup and generated HTML.
- Many visual rules are inline, preventing reliable responsive and state styling.
- Helper text is frequently 10–11 px, below the requested 12 px minimum.

### Accessibility

- Many labels are not explicitly associated with controls through `for`/`id`.
- Script tabs and segmented controls do not expose tab/radio semantics.
- Dynamic progress and errors are not in `aria-live` regions.
- Drawers/modals/toasts and Escape handling do not yet exist.
- Focus states are inconsistent and some clickable content is not a semantic button.
- Dynamic HTML actions depend on inline handlers.
- Reduced-motion behavior is absent.

## 11. Proposed file-level implementation plan

No backend Python change is currently required for the redesign. Any later compatibility change must be isolated, minimal, and approved by evidence from a failing frontend contract.

### Phase 1 — safe file organization

Modify/create exactly:

- `templates/index.html`: retain Jinja-compatible markup and all IDs; replace active inline CSS/JS with cache-versioned Flask static references; preserve loading/execution order.
- `static/css/studio.css`: receive the complete active CSS, initially without visual redesign.
- `static/js/studio.js`: receive the complete active JavaScript, initially without behavior changes.
- `static/icons/icons.svg`: create a local `currentColor` SVG sprite foundation; no CDN.
- `tests/test_ui_contract.py`: assert required IDs, static references, endpoint strings, and `collectSettings()` contract markers.

Verification before Phase 2: Python tests, Three.js tests, isolated browser load at all target sizes, console/network check, and spot checks for boot/options/projects/voice controls. Commit only the organization checkpoint.

### Phase 2 — workspace shell and information architecture

Modify:

- `templates/index.html`
- `static/css/studio.css`
- `static/js/studio.js`
- `static/icons/icons.svg`
- `tests/test_ui_contract.py`

Add the top app bar, real client-side views, collapsible navigation, four-step stepper, contextual inspector, and persistent in-memory studio state. Existing functional nodes will be moved, not recreated with new IDs.

### Phase 3 — script experience

Modify the same frontend files. Add Write Script / Generate with AI tabs, AI sub-tabs, counters, secondary action hierarchy, success toast, and safe replace/undo state. Keep all existing generation endpoint payloads.

### Phase 4 — cast and scenes

Modify the same frontend files. Recompose the existing `PLAN` preview UI into character/scene cards while retaining `renderPreview()` and `collectEditedParsed()` data contracts. Add reorder controls only where they update the existing parsed array safely.

### Phase 5 — style and audio

Modify the same frontend files. Present beginner controls first and move technical controls into an accessible advanced drawer. Preserve every `collectSettings()` key and provider-dependent voice behavior.

### Phase 6 — preview and render

Modify the same frontend files. Create preview summary, cost display using existing `/api/cost`, focused generation state, persistent Stop action, safe-resume copy, and final result actions. No generation/status response change.

### Phase 7 — dashboard and projects

Modify the same frontend files. Reuse `/api/projects`, `/api/resumable`, `/api/project/<name>`, `/api/resume/<name>`, and DELETE without changing shapes. Replace native delete confirmation with an in-app dialog.

### Phases 8–10 — design system, responsive behavior, UX/accessibility

Primarily modify `static/css/studio.css`, `static/icons/icons.svg`, and interaction/accessibility logic in `static/js/studio.js`; make only semantic markup changes in `templates/index.html`. Add requested tokens, icon replacement, responsive breakpoints, focus/keyboard support, toasts, dialogs, loading/empty/disabled states, `aria-*`, and reduced motion.

### Phase 11 — functional verification

Create/update:

- `docs/UI_VERIFICATION.md`: the 20-flow acceptance checklist, console/API results, viewport measurements, and unresolved issues.
- `docs/ui-after/`: after screenshots for 1920x1080, 1440x900, and 1280x720 (plus 1600x900 and 1366x768 where practical).
- `tests/test_ui_contract.py`: final static contract coverage.

Run all existing Python and Three.js tests plus isolated browser smoke verification. Manual actions that incur provider cost or start renders must be explicitly controlled so active user work is not disturbed.

### Phase 12 — handoff

Update `docs/UI_VERIFICATION.md` with changed files, exact run commands, rollback instructions, before/after links, unresolved items, and explicit confirmation that backend routes and payloads are unchanged.

## 12. Phase gates

Each phase must satisfy all of the following before the next begins:

- no missing DOM ID references
- no JavaScript console errors
- no broken initial API calls
- current form data survives navigation relevant to that phase
- no omitted `collectSettings()` key
- no page-level horizontal overflow at target desktop widths
- primary action remains reachable at 1280x720
- existing tests remain green
- focused checkpoint commit contains only that phase

Phase 1 must not begin until this audit and file-level plan are approved.
