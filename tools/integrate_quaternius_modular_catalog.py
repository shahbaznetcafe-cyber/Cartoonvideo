"""Integrate licensed modular Quaternius Blend/FBX characters in one batch."""
from __future__ import annotations

import argparse
import json
import os
import subprocess
from pathlib import Path

from integrate_quaternius_animated_catalog import (
    ROOT, INVENTORY, CHARACTER_MANIFEST, CAPABILITY_REGISTRY, STANDARDIZER,
    DEFAULT_BLENDER, key, slug, read, write, relative, sha256, loop_mode,
    skeleton_mapping, story_actions,
)


REPORT = ROOT / "reports/quaternius_modular_integration.json"
ALLOWED_PACK_MARKERS = ("Blends-", "Individual Characters-20260715T070937")
COMPONENT_KEYS = {
    "basecharacter", "humansmaster", "chefhat", "cowboyhair",
    "ninjamalehair", "vikinghelmet", "zombiearm", "zombieribcage",
}
ANIMAL_KEYS = {"cow", "pug"}


def priority(candidate):
    return {"BLEND": 2, "FBX": 1}.get(str(candidate.get("format") or "").upper(), 0)


def select_candidates(inventory, existing_ids):
    selected = {}
    for candidate in inventory.get("candidates", []):
        pack = str(candidate.get("pack") or "")
        name = str(candidate.get("name") or "")
        item_key = key(name)
        character_id = f"quaternius_{slug(name)}"
        license_name = str((candidate.get("license") or {}).get("type") or "UNKNOWN")
        if not any(marker in pack for marker in ALLOWED_PACK_MARKERS):
            continue
        if item_key in COMPONENT_KEYS or character_id in existing_ids or license_name == "UNKNOWN":
            continue
        if str(candidate.get("format") or "").upper() not in {"BLEND", "FBX"}:
            continue
        current = selected.get(item_key)
        if current is None or priority(candidate) > priority(current):
            selected[item_key] = candidate
    return sorted(selected.values(), key=lambda item: item.get("name", "").casefold())


def category(name):
    item_key = key(name)
    if item_key in ANIMAL_KEYS:
        return "animals"
    if item_key.startswith("zombie"):
        return "zombie"
    return "humans"


def clips_from_conversion(conversion):
    source_names = set(conversion.get("source_actions") or [])
    aliases = conversion.get("aliases") or {}
    clips = {}
    for clip in conversion.get("actions") or []:
        name = str(clip.get("name") or "")
        duration = float(clip.get("duration") or 0)
        if not name or duration <= 0:
            continue
        record = {"durationSeconds": duration, "recommendedLoop": loop_mode(name),
                  "sourceKind": "authored" if name in source_names else "recorded_alias"}
        if name not in source_names and name in aliases:
            record["realSourceClip"] = aliases[name]
        clips[name] = record
    return clips


def registry_entry(candidate, conversion, output_glb, tier):
    name = str(candidate["name"])
    clips = clips_from_conversion(conversion)
    authored_only = {clip_name: clip for clip_name, clip in clips.items()
                     if clip.get("sourceKind") == "authored"}
    license_info = candidate.get("license") or {}
    bounds = conversion.get("final_bounds_blender") or {}
    return {
        "displayName": f"Quaternius {name.replace('_', ' ')}",
        "sourcePack": "Ultimate Modular Characters",
        "sourceAsset": relative(Path(candidate["sourceFile"])),
        "assetPath": relative(output_glb), "assetSha256": sha256(output_glb),
        "license": {"status": "verified", "name": license_info.get("type", "CC0-1.0"),
                    "source": license_info.get("source", ""), "localLicenseFilePresent": False},
        "tier": tier,
        "skeleton": {"armatureName": conversion.get("armature", ""),
                     "boneCount": len(conversion.get("bones") or []),
                     "skinnedMeshCount": len(conversion.get("meshes") or [])},
        "skeletonMapping": skeleton_mapping(conversion.get("bones") or []),
        "authoredClips": clips,
        "storyActionClips": story_actions(authored_only),
        "locomotionProfiles": {},
        "rootMotion": {"treatment": "authored_clip_plus_grounded_holder",
                       "worldTranslationOwner": "character_holder", "groundCorrection": True,
                       "worldDisplacementCalibrated": False},
        "interaction": {"enabled": False, "handIK": False, "supported": {}},
        "facial": {"ready": False, "jaw": False, "visemes": False, "blink": False,
                   "eyeTarget": False, "emotionMorphs": False, "dialogueLipSync": False},
        "cameraPolicy": {"reject": ["dialogue_close_up", "facial_close_up"],
                         "allowBodyReactionClose": True, "preferOffCenterComposition": True},
        "scaleAndGround": {"targetHeight": conversion.get("target_height", 1.72),
                           "measuredHeight": bounds.get("height"),
                           "groundOffset": (bounds.get("min") or [0, 0, 0])[2]},
        "limitations": ["No validated facial controls or dialogue lip-sync.",
                        "World locomotion and prop contact are not calibrated.",
                        "Automated runtime review is deferred until the final test pass."],
        "validation": {"status": "standardized_runtime_review_pending",
                       "machineReport": relative(Path(conversion["report_path"])),
                       "visualEvidence": "pending_deferred_by_user", "promotedByEvidence": False},
    }


def manifest_entry(candidate, tier):
    name = str(candidate["name"])
    item_slug = slug(name)
    return {"name": f"Quaternius {name.replace('_', ' ')}",
            "keywords": sorted(set([item_slug, category(name), "quaternius", "character"])),
            "blend": f"quaternius_{item_slug}.blend", "thumb": None,
            "capability_id": f"quaternius_{item_slug}", "animation_tier": tier}


def register(successes):
    manifest = read(CHARACTER_MANIFEST, [])
    registry = read(CAPABILITY_REGISTRY, {})
    registry.setdefault("characters", {})
    by_id = {item.get("capability_id"): item for item in manifest if item.get("capability_id")}
    for row in successes:
        item = manifest_entry(row["candidate"], row["tier"])
        by_id[item["capability_id"]] = item
        registry["characters"][item["capability_id"]] = registry_entry(
            row["candidate"], row["conversion"], row["glb"], row["tier"])
    preserved = [item for item in manifest if not item.get("capability_id")]
    write(CHARACTER_MANIFEST, preserved + sorted(by_id.values(), key=lambda item: item["name"].casefold()))
    write(CAPABILITY_REGISTRY, registry)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--execute", action="store_true")
    parser.add_argument("--blender", type=Path, default=DEFAULT_BLENDER)
    args = parser.parse_args()
    inventory = read(INVENTORY, {})
    registry = read(CAPABILITY_REGISTRY, {})
    candidates = select_candidates(inventory, set((registry.get("characters") or {}).keys()))
    planned = [{"id": f"quaternius_{slug(item['name'])}", "name": item["name"],
                "source": relative(Path(item["sourceFile"])), "format": item["format"]}
               for item in candidates]
    if not args.execute:
        write(REPORT, {"schemaVersion": 1, "status": "PREFLIGHT", "plannedCount": len(planned),
                       "characters": planned})
        print(json.dumps({"preflight": "READY", "count": len(planned)}))
        return 0
    if not args.blender.is_file():
        raise FileNotFoundError(args.blender)
    successes, failures = [], []
    for index, candidate in enumerate(candidates, 1):
        name = str(candidate["name"])
        item_slug = slug(name)
        character_id = f"quaternius_{item_slug}"
        output_glb = ROOT / f"threejs_render/assets/chars/{character_id}.glb"
        output_blend = ROOT / f"blender/rigged/blend/{character_id}.blend"
        report_path = ROOT / f"assets/characters/quaternius_expanded/{item_slug}/conversion.json"
        report_path.parent.mkdir(parents=True, exist_ok=True)
        print(f"[{index}/{len(candidates)}] {character_id}", flush=True)
        try:
            if not (output_glb.is_file() and output_blend.is_file() and report_path.is_file()):
                env = os.environ.copy(); env["SBZ_CHARACTER_ID"] = character_id; env["SBZ_CHARACTER_NAME"] = name
                result = subprocess.run([str(args.blender), "-b", "--python", str(STANDARDIZER), "--",
                                         candidate["sourceFile"], str(output_glb), str(output_blend), str(report_path)],
                                        cwd=ROOT, env=env, text=True, capture_output=True)
                if result.returncode:
                    raise RuntimeError((result.stdout + "\n" + result.stderr)[-2500:])
            conversion = read(report_path, {})
            if not conversion or not output_glb.is_file() or not output_blend.is_file():
                raise RuntimeError("standardizer did not produce the required runtime triplet")
            conversion["report_path"] = str(report_path)
            tier = "SKELETAL_BASIC" if conversion.get("bones") and conversion.get("source_actions") else "STATIC"
            successes.append({"candidate": candidate, "conversion": conversion,
                              "glb": output_glb, "tier": tier})
        except Exception as exc:
            failures.append({"id": character_id, "error": str(exc)[:2500]})
    register(successes)
    document = {"schemaVersion": 1, "status": "COMPLETE" if not failures else "PARTIAL",
                "plannedCount": len(candidates), "integratedCount": len(successes),
                "skeletalBasic": sum(row["tier"] == "SKELETAL_BASIC" for row in successes),
                "static": sum(row["tier"] == "STATIC" for row in successes),
                "failureCount": len(failures), "characters": planned, "failures": failures,
                "verification": "runtime and regression tests deferred by user"}
    write(REPORT, document)
    print(json.dumps({"integration": document["status"], "integrated": len(successes),
                      "skeletal": document["skeletalBasic"], "static": document["static"],
                      "failed": len(failures)}))
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
