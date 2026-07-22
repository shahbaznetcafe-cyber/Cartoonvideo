"""Generate the bounded Phase 7 live proof without logging prompts or credentials."""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from script_engine import ScriptPipeline


REPORT_DIR = ROOT / "reports" / "phase7_samples"
PROJECT = "phase7-proof"


CASES = [
    {
        "name": "01_urdu_story",
        "stage": "story_outline",
        "language": "urdu",
        "model": "runware.deepseek.v4.pro",
        "content": "ایک بہادر بچہ جنگل میں گم شدہ پرندے کو اس کے گھونسلے تک پہنچاتا ہے۔ کہانی بچوں کے لیے نرم، دلچسپ اور امید بھری ہو۔",
    },
    {
        "name": "02_roman_urdu_dialogue",
        "stage": "character_dialogue",
        "language": "roman_urdu",
        "model": "runware.zai.glm.5.1",
        "content": "Scene: jungle path. Ali notices a moving box. Sara warns him. Write one short natural Roman Urdu scene with distinct voices, punctuation and physical actions.",
    },
    {
        "name": "03_hindi_dialogue",
        "stage": "character_dialogue",
        "language": "hindi",
        "model": "runware.zai.glm.5.1",
        "content": "दृश्य: गाँव का स्कूल। मीरा को एक घायल चिड़िया मिलती है और कबीर उसकी मदद करता है। बच्चों के लिए स्वाभाविक, छोटा संवाद लिखें।",
    },
    {
        "name": "04_script_doctor",
        "stage": "script_doctor",
        "language": "roman_urdu",
        "mode": "robotic_naturalizer",
        "model": "runware.openai.gpt.5.4.mini",
        "content": "[Scene: Jungle]\nAli: Main box dekhta hoon aur main box ke paas jaata hoon.\nSara: Tum box ke paas mat jao kyun ke box ajeeb hai.\nAli: Main phir bhi box ko dekhunga.",
    },
    {
        "name": "05_parser_for_animation",
        "stage": "scene_breakdown",
        "language": "roman_urdu",
        "model": "runware.google.gemini.3.5.flash",
        "content": "[Scene: Forest path, day]\nNarrator: Ali jungle ke raste par aahista chal raha hai.\nAli: Yeh box yahan kaise aaya?\n(Action: Ali box ki taraf ishara karta hai.)",
    },
    {
        "name": "06_animation_storyboard",
        "stage": "animation_plan",
        "language": "roman_urdu",
        "model": "runware.google.gemini.3.5.flash",
        "content": (
            "Create exactly a 2-second, 24 FPS board. Character id hero uses capabilityId "
            "quaternius_adventurer and tier SKELETAL_INTERACTIVE. Use one contiguous action "
            "beat from frame 0 to 48, exact authored source clip Idle, animationAction "
            "offscreen_hold, cameraIntent medium, and no dialogue close-up."
        ),
    },
]


def write_json(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding="utf-8")


def main():
    pipeline = ScriptPipeline()
    results, failures = [], []
    for case in CASES:
        kwargs = {
            "language": case["language"], "requested_model": case["model"],
            "mode": case.get("mode"), "allow_fallback": True, "use_cache": True,
            "project": PROJECT,
        }
        try:
            record = pipeline.run_stage(case["stage"], case["content"], **kwargs)
            write_json(REPORT_DIR / f"{case['name']}.json", record)
            results.append({
                "name": case["name"], "stage": case["stage"], "language": case["language"],
                "status": "PASS", "model": record["metadata"]["modelInternalId"],
                "air": record["metadata"]["modelAir"],
                "latencyMs": record["metadata"]["latencyMs"],
                "cost": record["metadata"]["cost"], "cache": record["metadata"]["cache"],
                "fallbackUsed": record["metadata"]["fallbackUsed"],
            })
            if case["stage"] == "scene_breakdown":
                pipeline.approve_stage(PROJECT, "scene_breakdown")
            print(f"PASS {case['name']} model={record['metadata']['modelInternalId']} "
                  f"latencyMs={record['metadata']['latencyMs']}", flush=True)
        except Exception as exc:
            failure = {"name": case["name"], "stage": case["stage"],
                       "status": "FAIL", "errorType": type(exc).__name__,
                       "error": str(exc)[:300],
                       "diagnostics": getattr(exc, "diagnostics", [])}
            failures.append(failure); results.append(failure)
            write_json(REPORT_DIR / f"{case['name']}_failure.json", failure)
            print(f"FAIL {case['name']} type={type(exc).__name__}", flush=True)
    summary = {
        "schemaVersion": 1,
        "title": "Phase 7 Runware Live Proof",
        "credentialsIncluded": False,
        "comparisonMode": False,
        "boundedFallbacks": 1,
        "passed": len(results) - len(failures),
        "failed": len(failures),
        "results": results,
    }
    write_json(ROOT / "reports" / "phase7_live_proof.json", summary)
    print(f"PHASE7_LIVE_PROOF passed={summary['passed']} failed={summary['failed']}")
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
