"""Run the existing Blender standardizer from one data-driven manifest."""
from __future__ import annotations

import argparse
import json
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_MANIFEST = ROOT / "assets/characters/quaternius_representative/phase4_manifest.json"
DEFAULT_BLENDER = Path(r"C:\Program Files\Blender Foundation\Blender 5.1\blender.exe")
STANDARDIZER = ROOT / "blender/standardize_quaternius_master.py"


def resolve(value: str) -> Path:
    path = Path(value)
    return path if path.is_absolute() else ROOT / path


def preflight(document: dict, *, allow_existing: bool) -> list[dict]:
    characters = document.get("characters") or []
    ids = {item.get("id") for item in characters}
    expected = set(document.get("expectedCharacterIds") or [])
    if not expected or ids != expected or len(characters) != len(expected):
        raise RuntimeError("Manifest characters do not match expectedCharacterIds")
    license_record = document.get("license") or {}
    if license_record.get("status") != "verified" or license_record.get("name") != "CC0 1.0":
        raise RuntimeError("Phase 4 source license is not verified")
    prepared = []
    for item in characters:
        paths = {key: resolve(item[key]) for key in (
            "source", "sourceInspection", "outputGlb", "outputBlend", "conversionReport")}
        if not paths["source"].is_file():
            raise FileNotFoundError(paths["source"])
        if not paths["sourceInspection"].is_file():
            raise FileNotFoundError(paths["sourceInspection"])
        existing = [str(paths[key]) for key in ("outputGlb", "outputBlend", "conversionReport")
                    if paths[key].exists()]
        if existing and not allow_existing:
            raise RuntimeError(f"{item['id']} is already standardized: {existing}")
        prepared.append({"item": item, "paths": paths, "existing": existing})
    return prepared


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    parser.add_argument("--blender", type=Path, default=DEFAULT_BLENDER)
    parser.add_argument("--execute", action="store_true")
    parser.add_argument("--allow-existing", action="store_true")
    args = parser.parse_args()
    document = json.loads(args.manifest.read_text(encoding="utf-8"))
    prepared = preflight(document, allow_existing=args.allow_existing)
    print(json.dumps({"preflight": "PASS", "characters": [row["item"]["id"] for row in prepared],
                      "alreadyStandardized": sum(bool(row["existing"]) for row in prepared)}))
    if not args.execute:
        return 0
    if not args.blender.is_file():
        raise FileNotFoundError(args.blender)
    for row in prepared:
        paths = row["paths"]
        for key in ("outputGlb", "outputBlend", "conversionReport"):
            paths[key].parent.mkdir(parents=True, exist_ok=True)
        command = [str(args.blender), "-b", "--python", str(STANDARDIZER), "--",
                   str(paths["source"]), str(paths["outputGlb"]),
                   str(paths["outputBlend"]), str(paths["conversionReport"])]
        subprocess.run(command, cwd=ROOT, check=True)
    print(json.dumps({"conversion": "COMPLETE", "count": len(prepared)}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
