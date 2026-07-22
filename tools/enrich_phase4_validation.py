"""Attach source, license and conversion evidence to Phase 4 validation JSON."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "assets/characters/quaternius_representative/phase4_manifest.json"


def resolve(value: str) -> Path:
    return ROOT / value


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def unique_materials(meshes: list[dict]) -> list[str]:
    return sorted({name for mesh in meshes for name in mesh.get("materials", [])})


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest", type=Path, default=MANIFEST)
    args = parser.parse_args()
    manifest = json.loads(args.manifest.read_text(encoding="utf-8"))
    for character in manifest["characters"]:
        source_path = resolve(character["source"])
        glb_path = resolve(character["outputGlb"])
        inspection = json.loads(resolve(character["sourceInspection"]).read_text(encoding="utf-8"))
        conversion = json.loads(resolve(character["conversionReport"]).read_text(encoding="utf-8"))
        validation_path = resolve(character["validationReport"])
        validation = json.loads(validation_path.read_text(encoding="utf-8"))
        source_clips = sorted(action["name"] for action in inspection["actions"])
        exported_clips = sorted(action["name"] for action in conversion["actions"])
        source_materials = unique_materials(inspection["meshes"])
        validation["phase4"] = {
            "characterId": character["id"],
            "source": {
                "path": character["source"],
                "sha256": sha256(source_path),
                "preserved": True,
                "inspection": character["sourceInspection"],
            },
            "license": manifest["license"],
            "preConversion": {
                "armatureCount": len(inspection["armatures"]),
                "boneCount": len(inspection["armatures"][0]["bones"]),
                "meshCount": len(inspection["meshes"]),
                "materialNames": source_materials,
                "externalImageCount": len(inspection["images"]),
                "authoredClipNames": source_clips,
                "alreadyStandardized": False,
            },
            "standardization": {
                "process": "blender/standardize_quaternius_master.py",
                "outputGlb": character["outputGlb"],
                "outputGlbSha256": sha256(glb_path),
                "outputBlend": character["outputBlend"],
                "targetHeight": conversion["target_height"],
                "finalHeight": conversion["final_bounds_blender"]["height"],
                "groundOffset": conversion["final_bounds_blender"]["min"][2],
                "normalizationScale": conversion["normalization_scale"],
                "materialNames": conversion["materials"],
                "sourceMaterialsPreserved": source_materials == sorted(conversion["materials"]),
                "exportedClipNames": exported_clips,
                "sourceClipsPreserved": set(source_clips).issubset(exported_clips),
                "recordedAliases": conversion["aliases"],
            },
            "runtimeProof": {
                "status": "pending_deferred_by_user",
                "scene": "threejs_render/phase4_multi_character/index.html",
                "capture": "threejs_render/phase4_multi_character/capture.mjs",
            },
            "status": "standardized_and_schema_validated_runtime_review_pending",
        }
        validation_path.write_text(json.dumps(validation, indent=2, ensure_ascii=False) + "\n",
                                   encoding="utf-8")
        print(f"PHASE4_VALIDATION_ENRICHED={character['id']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
