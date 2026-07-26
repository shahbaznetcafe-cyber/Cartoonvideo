"""Run the explicit paid Phase 7 benchmark and write sanitized reports."""
from __future__ import annotations

import argparse
import json
import statistics
import sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from script_engine import ScriptPipeline, StructuredTextEngine


DATASET = ROOT / "benchmarks" / "phase7_dataset.json"
REPORT_JSON = ROOT / "reports" / "phase7_model_benchmark.json"
REPORT_MD = ROOT / "reports" / "phase7_model_benchmark.md"
SAMPLE_DIR = ROOT / "reports" / "phase7_benchmark_samples"

MODEL_POOLS = {
    "story_outline": ["runware.deepseek.v4.pro", "runware.openai.gpt.5.4.mini"],
    "urdu": ["runware.zai.glm.5.1", "runware.deepseek.v4.pro"],
    "roman_urdu": ["runware.zai.glm.5.1", "runware.deepseek.v4.flash"],
    "hindi": ["runware.zai.glm.5.1", "runware.openai.gpt.5.4.mini"],
    "mixed_urdu_english": ["runware.deepseek.v4.flash", "runware.openai.gpt.5.4.mini"],
    "script_to_animation": ["runware.google.gemini.3.5.flash", "runware.openai.gpt.5.4.mini"],
}

REVIEW_SCHEMA = {
    "$id": "sbz://schemas/phase7-benchmark-review-v1", "type": "object",
    "required": ["reviews"], "properties": {"reviews": {
        "type": "array", "minItems": 1, "items": {"type": "object",
            "required": ["id", "naturalness", "grammar", "characterVoice",
                         "storyCoherence", "culturalAppropriateness", "repetitionControl",
                         "childSuitability", "structuredValidity", "animationFeasibility", "notes"],
            "properties": {
                "id": {"type": "string"},
                "naturalness": {"type": "number", "minimum": 1, "maximum": 10},
                "grammar": {"type": "number", "minimum": 1, "maximum": 10},
                "characterVoice": {"type": "number", "minimum": 1, "maximum": 10},
                "storyCoherence": {"type": "number", "minimum": 1, "maximum": 10},
                "culturalAppropriateness": {"type": "number", "minimum": 1, "maximum": 10},
                "repetitionControl": {"type": "number", "minimum": 1, "maximum": 10},
                "childSuitability": {"type": "number", "minimum": 1, "maximum": 10},
                "structuredValidity": {"type": "number", "minimum": 1, "maximum": 10},
                "animationFeasibility": {"type": "number", "minimum": 1, "maximum": 10},
                "notes": {"type": "string"}
            }
        }
    }}
}


def write_json(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding="utf-8")


def model_for(sample, index):
    key = "story_outline" if sample["stage"] == "story_outline" else sample["group"]
    pool = MODEL_POOLS[key]
    return pool[index % len(pool)]


def auto_metrics(output, language):
    text = json.dumps(output, ensure_ascii=False)
    words = [word.casefold() for word in text.replace("\n", " ").split() if len(word) > 2]
    unique_ratio = len(set(words)) / max(1, len(words))
    urdu_chars = sum("\u0600" <= char <= "\u06ff" for char in text)
    hindi_chars = sum("\u0900" <= char <= "\u097f" for char in text)
    latin_chars = sum(char.isascii() and char.isalpha() for char in text)
    total_letters = max(1, urdu_chars + hindi_chars + latin_chars)
    expected_ratio = ((urdu_chars / total_letters) if language == "urdu" else
                      (hindi_chars / total_letters) if language == "hindi" else
                      (latin_chars / total_letters))
    unsafe = any(token in text.casefold() for token in ("graphic violence", "suicide", "sexual"))
    return {"uniqueWordRatio": round(unique_ratio, 4),
            "expectedScriptRatio": round(expected_ratio, 4),
            "childSafetyProxy": 0 if unsafe else 1,
            "structuredJsonValid": True}


def average(values):
    values = [float(value) for value in values if value is not None]
    return round(sum(values) / len(values), 4) if values else None


def aggregate(results):
    groups = defaultdict(list)
    for item in results:
        groups[item.get("modelInternalId") or item.get("requestedModel")].append(item)
    summary = {}
    score_fields = ["naturalness", "grammar", "characterVoice", "storyCoherence",
                    "culturalAppropriateness", "repetitionControl", "childSuitability",
                    "structuredValidity", "animationFeasibility"]
    for model, items in groups.items():
        successes = [item for item in items if item["status"] == "PASS"]
        summary[model] = {
            "samples": len(items), "passed": len(successes),
            "failureRate": round((len(items) - len(successes)) / max(1, len(items)), 4),
            "averageLatencyMs": average(item.get("latencyMs") for item in successes),
            "returnedCostTotal": round(sum(float(item.get("cost") or 0) for item in successes), 8),
            "costCoverage": sum(item.get("cost") is not None for item in successes),
            "averageScores": {field: average((item.get("review") or {}).get(field)
                                               for item in successes) for field in score_fields},
        }
    return summary


def best_model(results, predicate, score_field):
    candidates = defaultdict(list)
    for item in results:
        if item["status"] == "PASS" and predicate(item):
            score = (item.get("review") or {}).get(score_field)
            if score is not None:
                candidates[item["modelInternalId"]].append(float(score))
    if not candidates:
        return None
    return max(candidates, key=lambda model: sum(candidates[model]) / len(candidates[model]))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--live", action="store_true")
    parser.add_argument("--confirm-paid-comparison", action="store_true")
    parser.add_argument("--limit", type=int, default=0)
    args = parser.parse_args()
    if not (args.live and args.confirm_paid_comparison):
        print("Live benchmark blocked. Use --live --confirm-paid-comparison explicitly.")
        return 2
    dataset = json.loads(DATASET.read_text(encoding="utf-8"))["samples"]
    if args.limit:
        dataset = dataset[:max(1, args.limit)]
    pipeline, engine = ScriptPipeline(), StructuredTextEngine()
    results, successful_for_review = [], []
    stage_indexes = defaultdict(int)
    for sample in dataset:
        index = stage_indexes[sample["group"]]; stage_indexes[sample["group"]] += 1
        requested_model = model_for(sample, index)
        try:
            record = pipeline.run_stage(
                sample["stage"], sample["prompt"], language=sample["language"],
                mode=sample.get("mode"), requested_model=requested_model,
                allow_fallback=True, use_cache=True, project="phase7-benchmark")
            meta = record["metadata"]
            item = {"id": sample["id"], "group": sample["group"],
                    "stage": sample["stage"], "language": sample["language"],
                    "status": "PASS", "requestedModel": requested_model,
                    "modelInternalId": meta["modelInternalId"], "modelAir": meta["modelAir"],
                    "latencyMs": meta["latencyMs"], "cost": meta["cost"],
                    "cache": meta["cache"], "retryCount": meta["retryCount"],
                    "fallbackUsed": meta["fallbackUsed"],
                    "fallbackReason": meta.get("fallbackReason"),
                    "diagnostics": record.get("diagnostics", []),
                    "autoMetrics": auto_metrics(record["output"], sample["language"]),
                    "output": record["output"]}
            results.append(item); successful_for_review.append(item)
            write_json(SAMPLE_DIR / f"{sample['id']}.json", record)
            print(f"PASS {sample['id']} model={meta['modelInternalId']} latencyMs={meta['latencyMs']}", flush=True)
        except Exception as exc:
            item = {"id": sample["id"], "group": sample["group"], "stage": sample["stage"],
                    "language": sample["language"], "status": "FAIL",
                    "requestedModel": requested_model, "errorType": type(exc).__name__,
                    "error": str(exc)[:240], "diagnostics": getattr(exc, "diagnostics", [])}
            results.append(item)
            print(f"FAIL {sample['id']} type={type(exc).__name__}", flush=True)

    reviewer_runs = []
    for start in range(0, len(successful_for_review), 5):
        batch = successful_for_review[start:start + 5]
        review_input = [{"id": item["id"], "group": item["group"], "stage": item["stage"],
                         "language": item["language"], "output": item["output"]} for item in batch]
        try:
            review_result = engine.generate(
                "QUALITY_REVIEWER", json.dumps(review_input, ensure_ascii=False),
                language="english", schema=REVIEW_SCHEMA,
                requested_model="runware.openai.gpt.5.4", allow_fallback=True,
                use_cache=True, generation_settings={"benchmarkBatch": start // 5})
            by_id = {review["id"]: review for review in review_result["output"]["reviews"]}
            for item in batch:
                if item["id"] in by_id:
                    item["review"] = by_id[item["id"]]
            reviewer_runs.append(review_result["metadata"])
            print(f"REVIEW batch={start // 5 + 1} model={review_result['metadata']['modelInternalId']}", flush=True)
        except Exception as exc:
            reviewer_runs.append({"batch": start // 5, "status": "FAIL",
                                  "error": str(exc)[:240]})
            print(f"REVIEW_FAIL batch={start // 5 + 1}", flush=True)

    for item in results:
        item.pop("output", None)
    model_summary = aggregate(results)
    recommendations = {
        "bestParser": best_model(results, lambda item: item["group"] == "script_to_animation", "animationFeasibility"),
        "bestUrduDialogue": best_model(results, lambda item: item["group"] == "urdu" and item["stage"] == "character_dialogue", "naturalness"),
        "bestHindiDialogue": best_model(results, lambda item: item["group"] == "hindi", "naturalness"),
        "bestStoryPlanner": best_model(results, lambda item: item["stage"] == "story_outline", "storyCoherence"),
        "bestStructuredOutput": best_model(results, lambda item: True, "structuredValidity"),
    }
    successful = [item for item in results if item["status"] == "PASS"]
    cost_reported = [item for item in successful if item.get("cost") is not None]
    if cost_reported:
        economical = min(
            cost_reported,
            key=lambda item: (float(item["cost"]), item.get("latencyMs") or float("inf")),
        )
        recommendations["fastestEconomicalOption"] = economical["modelInternalId"]
        recommendations["fastestEconomicalEvidence"] = "Runware-returned cost and latency"
    elif successful:
        fastest = min(successful, key=lambda item: item.get("latencyMs") or float("inf"))
        recommendations["fastestEconomicalOption"] = fastest["modelInternalId"]
        recommendations["fastestEconomicalEvidence"] = (
            "No Runware cost was returned; this is latency-only and does not mean free"
        )
    report = {
        "schemaVersion": 1, "title": "Phase 7 Task-Based Model Benchmark",
        "dataset": "benchmarks/phase7_dataset.json", "sampleCount": len(dataset),
        "comparisonExplicitlyEnabled": True, "universalWinnerDeclared": False,
        "credentialsIncluded": False, "results": results, "reviewerRuns": reviewer_runs,
        "modelSummary": model_summary, "recommendations": recommendations,
        "limitations": [
            "Models are distributed across samples rather than every model receiving every prompt.",
            "Language scores are model-reviewed proxies and still require native-speaker human review.",
            "Returned cost is reported only when Runware includes it; null cost is not treated as free.",
            "Benchmark results are a routing aid, not a universal model ranking."
        ]
    }
    write_json(REPORT_JSON, report)
    lines = ["# Phase 7 Task-Based Runware Benchmark", "",
             f"Samples: **{len(dataset)}** · Passed: **{len(successful)}** · Failed: **{len(dataset)-len(successful)}**",
             "", "No universal winner is declared. Recommendations are task-specific.", "",
             "## Model comparison", "",
             "| Model | Samples | Pass | Failure rate | Avg latency | Returned cost | Cost coverage |",
             "|---|---:|---:|---:|---:|---:|---:|"]
    for model, summary in sorted(model_summary.items()):
        lines.append(f"| `{model}` | {summary['samples']} | {summary['passed']} | {summary['failureRate']:.0%} | {summary['averageLatencyMs'] or 'n/a'} ms | ${summary['returnedCostTotal']:.6f} | {summary['costCoverage']}/{summary['passed']} |")
    lines += ["", "## Task recommendations", ""]
    for name, model in recommendations.items():
        lines.append(f"- **{name}:** `{model or 'insufficient evidence'}`")
    lines += ["", "## Limitations", ""] + [f"- {item}" for item in report["limitations"]]
    REPORT_MD.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"PHASE7_BENCHMARK passed={len(successful)} failed={len(dataset)-len(successful)}")
    return 0 if len(successful) == len(dataset) else 1


if __name__ == "__main__":
    raise SystemExit(main())
