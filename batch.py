"""
P7 — Batch generation: ek folder ke saare .txt scripts -> alag-alag videos.
    python batch.py path/to/scripts_folder
"""
import glob
import os
import sys

import build as builder

try:
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")
except Exception:
    pass


def find_scripts(folder):
    return sorted(glob.glob(os.path.join(folder, "*.txt")))


def batch_generate(folder, settings=None, on_progress=None, on_each=None):
    """
    Folder ke har .txt ke liye video banao. on_each(i, total, name, result_or_error).
    return: list of {script, status, video/error}.
    """
    scripts = find_scripts(folder)
    results = []
    total = len(scripts)
    for i, path in enumerate(scripts, start=1):
        name = os.path.splitext(os.path.basename(path))[0]
        with open(path, encoding="utf-8") as f:
            text = f.read().strip()
        if len(text) < 10:
            results.append({"script": name, "status": "skipped", "error": "khaali/chhota"})
            continue

        def prog(stage, ci, ct, msg):
            if on_progress:
                on_progress(i, total, name, stage, ci, ct, msg)

        try:
            res = builder.build(text, proj_name=f"{name}-batch", on_progress=prog,
                                settings=settings)
            results.append({"script": name, "status": "done", "video": res["video"]})
        except Exception as e:
            results.append({"script": name, "status": "error", "error": str(e)})
        if on_each:
            on_each(i, total, name, results[-1])
    return results


def main():
    if len(sys.argv) < 2:
        print("Istemaal: python batch.py <scripts_folder>")
        sys.exit(1)
    folder = sys.argv[1]
    scripts = find_scripts(folder)
    print(f"\n📁 {len(scripts)} scripts mile {folder} mein\n")

    def on_each(i, total, name, res):
        icon = "✅" if res["status"] == "done" else ("⏭️" if res["status"] == "skipped" else "❌")
        print(f"  {icon} [{i}/{total}] {name}: {res['status']}")

    results = batch_generate(folder, on_each=on_each)
    done = sum(1 for r in results if r["status"] == "done")
    print(f"\n✅ {done}/{len(results)} videos ban gaye\n")


if __name__ == "__main__":
    main()
