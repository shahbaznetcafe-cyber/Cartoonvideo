"""
M1 demo/CLI:  python parse.py sample_script.txt
Script ko structured scene-JSON mein todta hai aur projects/<name>/story.json mein save karta hai.
"""
import json
import os
import sys
import time

import config
import story_parser

try:
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")
except Exception:
    pass


def main():
    if len(sys.argv) < 2:
        print("Istemaal: python parse.py <script-file.txt>")
        sys.exit(1)

    path = sys.argv[1]
    with open(path, encoding="utf-8") as f:
        script_text = f.read()

    print("\n🧠 Script analyze ho raha hai (Story Parser)...\n")
    parsed = story_parser.parse_script(script_text)

    n_chars, n_scenes, n_lines = story_parser.stats(parsed)
    print(f"Title    : {parsed['title']}")
    print(f"Language : {parsed.get('language')}")
    print(f"Characters: {n_chars} | Scenes: {n_scenes} | Dialogue lines: {n_lines}\n")

    print("— Characters —")
    for c in parsed["characters"]:
        print(f"  • {c['name']} ({c['gender']}) -> voice: {c['voice']}")

    print("\n— Scenes —")
    for sc in parsed["scenes"]:
        print(f"  Scene {sc['id']}: {sc.get('location')} / {sc.get('time')} / {sc.get('mood')}")
        for ln in sc.get("lines", []):
            print(f"     [{ln['speaker']}] ({ln.get('emotion')}) {ln['text']}")

    # save project
    name = f"project-{int(time.time())}"
    proj_dir = os.path.join(config.PROJECTS_DIR, name)
    os.makedirs(proj_dir, exist_ok=True)
    out = os.path.join(proj_dir, "story.json")
    with open(out, "w", encoding="utf-8") as f:
        json.dump(parsed, f, ensure_ascii=False, indent=2)

    print(f"\n✅ story.json save ho gaya -> {out}\n")


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"\n❌ Error: {e}\n", file=sys.stderr)
        sys.exit(1)
