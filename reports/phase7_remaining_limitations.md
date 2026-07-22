# Phase 7 Remaining Limitations

- GLM 4.7 remains recorded but disabled because live inference returned `invalidModel` even though model search discovered it. It must be re-verified before enabling.
- Runware returned cost for 12 of 40 generation samples and all 8 reviewer batches. Missing cost is unknown, not free.
- The reported benchmark cost total of **$0.130950** includes only responses where Runware returned cost metadata. It excludes unknown-cost calls and the separate six-case proof.
- The 40-sample benchmark distributes models by task; it does not send every prompt to every model. This controls paid usage but means recommendations are routing evidence, not a universal ranking.
- Quality scores are model-reviewed proxies. Urdu, Roman Urdu and Hindi should receive native-speaker human review before final production routing is locked.
- Seven benchmark outputs required the single permitted model fallback after structured validation failed. GLM 5.1 had five such cases and Gemini 3.5 Flash had two. The recovered output passed validation, but schema reliability should continue to be monitored.
- OpenAI-compatible responses from DeepSeek and GLM supplied token usage but not returned cost in these runs.
- Browser UI uses asynchronous job polling rather than rendering token-by-token streamed text. The shared Runware client supports cancellable streaming for future UI use.
- Capability-aware animation validation currently has a production registry entry for the validated Adventurer path. Other characters must be registered before their animation actions can be trusted.
- `pytest` is not installed; all 90 discoverable repository tests pass with `unittest`. An existing non-failing resource warning in `styles.py` remains outside Phase 7 scope.
- No complete mini-episode was generated. Phase 7 is stopped at structured proof for human review.
