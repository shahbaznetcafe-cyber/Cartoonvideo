# Phase 7 Task-Based Runware Benchmark

Samples: **40** · Passed: **40** · Failed: **0**

No universal winner is declared. Recommendations are task-specific.

## Model comparison

| Model | Samples | Pass | Failure rate | Avg latency | Returned cost | Cost coverage |
|---|---:|---:|---:|---:|---:|---:|
| `runware.deepseek.v4.flash` | 10 | 10 | 0% | 22220.6 ms | $0.000000 | 0/10 |
| `runware.deepseek.v4.pro` | 11 | 11 | 0% | 20127.5455 ms | $0.000000 | 0/11 |
| `runware.google.gemini.3.5.flash` | 1 | 1 | 0% | 4268.0 ms | $0.003390 | 1/1 |
| `runware.openai.gpt.5.4.mini` | 11 | 11 | 0% | 4956.0909 ms | $0.018021 | 11/11 |
| `runware.zai.glm.5.1` | 7 | 7 | 0% | 39358.7143 ms | $0.000000 | 0/7 |

## Task recommendations

- **bestParser:** `runware.openai.gpt.5.4.mini`
- **bestUrduDialogue:** `runware.deepseek.v4.pro`
- **bestHindiDialogue:** `runware.openai.gpt.5.4.mini`
- **bestStoryPlanner:** `runware.openai.gpt.5.4.mini`
- **bestStructuredOutput:** `runware.openai.gpt.5.4.mini`
- **fastestEconomicalOption:** `runware.openai.gpt.5.4.mini`
- **fastestEconomicalEvidence:** `Runware-returned cost and latency`

## Limitations

- Models are distributed across samples rather than every model receiving every prompt.
- Language scores are model-reviewed proxies and still require native-speaker human review.
- Returned cost is reported only when Runware includes it; null cost is not treated as free.
- Benchmark results are a routing aid, not a universal model ranking.
