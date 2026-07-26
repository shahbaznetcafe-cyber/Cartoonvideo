"""Re-measure spoken words-per-second from rendered projects, per language.

Run this after changing TTS voices, speed, or the inter-line pauses, then update
duration_planner.WORDS_PER_SECOND with the numbers it prints.  It reads each
project's story.json (for language) and timeline.json (words + real durations).

    python tools/measure_speech_rate.py
"""
from __future__ import annotations

import json
import os
import re
import sys
from collections import defaultdict

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PROJECTS = os.path.join(ROOT, "projects")


def main():
    agg = defaultdict(lambda: [0, 0.0, 0])   # language -> [words, seconds, projects]
    if not os.path.isdir(PROJECTS):
        print("No projects/ directory found.")
        return 1
    for name in sorted(os.listdir(PROJECTS)):
        proj = os.path.join(PROJECTS, name)
        story_path = os.path.join(proj, "story.json")
        tl_path = os.path.join(proj, "timeline.json")
        if not (os.path.exists(story_path) and os.path.exists(tl_path)):
            continue
        try:
            story = json.load(open(story_path, encoding="utf-8"))
            timeline = json.load(open(tl_path, encoding="utf-8"))
        except (OSError, ValueError):
            continue
        if not timeline:
            continue
        words = sum(len(re.findall(r"\S+", str(e.get("text") or ""))) for e in timeline)
        seconds = sum(float(e.get("duration") or 0) for e in timeline)
        if words < 20 or seconds < 5:
            continue
        lang = str(story.get("language") or "unknown").lower()
        bucket = agg[lang]
        bucket[0] += words
        bucket[1] += seconds
        bucket[2] += 1

    if not agg:
        print("No usable rendered projects yet.")
        return 0
    print(f"{'language':14} {'projects':>8} {'words':>7} {'seconds':>9} {'words/sec':>10}")
    total_w = total_s = 0
    for lang, (words, seconds, count) in sorted(agg.items()):
        total_w += words
        total_s += seconds
        print(f"{lang:14} {count:8d} {words:7d} {seconds:9.1f} {words / seconds:10.3f}")
    print(f"\nOVERALL words/sec: {total_w / total_s:.3f}  (seconds/word: {total_s / total_w:.3f})")
    print("Update duration_planner.WORDS_PER_SECOND with the per-language values above.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
