"""Standardize licensed animated Quaternius inventory into the SBZ runtime.

This is intentionally data-driven. It selects one preferred animated glTF per
unique character from the inspected inventory, excludes already-integrated
models and license-blocked packs, and records every result before registration.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
INVENTORY = ROOT / "reports/quaternius_inventory.json"
CHARACTER_MANIFEST = ROOT / "characters3d.json"
CAPABILITY_REGISTRY = ROOT / "assets/characters/capability_registry.json"
REPORT = ROOT / "reports/quaternius_animated_integration.json"
STANDARDIZER = ROOT / "blender/standardize_quaternius_master.py"
DEFAULT_BLENDER = Path(r"C:\Program Files\Blender Foundation\Blender 5.1\blender.exe")

ALLOWED_PACK_MARKERS = ("Ultimate Monsters", "Ultimate Space Kit", "Zombie Apocalypse Kit")
PIRATE_PACK_MARKER = "Pirate Kit"
COMPONENT_KEYS = {"zombiearm", "zombieribcage"}
ANIMAL_KEYS = {
    "alpaking", "alpakingevolved", "armabee", "armabeeevolved", "birb", "bunny",
    "cat", "chicken", "dino", "dog", "dragon", "dragonevolved", "fish", "frog",
    "germanshepherd", "monkroose", "pigeon", "pug", "shark", "sharky", "squidle", "yeti",
}


def key(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "", str(value or "").lower())


def slug(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", str(value or "").lower()).strip("_")


def read(path: Path, default):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return default


def write(path: Path, document):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(document, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def relative(path: Path) -> str:
    return path.resolve().relative_to(ROOT).as_posix()


def category(name: str, pack: str) -> str:
    item_key = key(name)
    if item_key in ANIMAL_KEYS:
        return "animals"
    if "Space" in pack:
        return "space"
    if "Zombie" in pack or item_key.startswith("zombie"):
        return "zombie"
    return "monsters"


def candidate_priority(candidate):
    clips = len(candidate.get("animationClips") or [])
    bones = len(candidate.get("skeletonBones") or [])
    return clips, bones, -int(candidate.get("approximateTriangleCount") or 0)


def select_candidates(inventory, existing_ids, allow_user_authorized_pirate=False):
    selected = {}
    for candidate in inventory.get("candidates", []):
        pack = str(candidate.get("pack") or "")
        name = str(candidate.get("name") or "")
        item_key = key(name)
        character_id = f"quaternius_{slug(name)}"
        license_name = str((candidate.get("license") or {}).get("type") or "UNKNOWN")
        is_pirate = PIRATE_PACK_MARKER in pack
        allowed_pack = any(marker in pack for marker in ALLOWED_PACK_MARKERS)
        if not allowed_pack and not (allow_user_authorized_pirate and is_pirate):
            continue
        if item_key in COMPONENT_KEYS or character_id in existing_ids:
            continue
        if str(candidate.get("format") or "").upper() != "GLTF":
            continue
        if ((license_name == "UNKNOWN" and not (allow_user_authorized_pirate and is_pirate))
                or not candidate.get("armaturePresent") or not candidate.get("skins")):
            continue
        if not candidate.get("animationClips"):
            continue
        current = selected.get(item_key)
        if current is None or candidate_priority(candidate) > candidate_priority(current):
            selected[item_key] = candidate
    return sorted(selected.values(), key=lambda item: (item.get("pack", ""), item.get("name", "").casefold()))


def loop_mode(name: str) -> str:
    lower = name.lower()
    return "repeat" if any(word in lower for word in ("idle", "walk", "run", "fly", "swim")) else "once"


def authored_clips(candidate):
    clips = {}
    for clip in candidate.get("animationClips") or []:
        duration = float(clip.get("duration") or 0)
        name = str(clip.get("name") or "").strip()
        if name and duration > 0:
            clips[name] = {"durationSeconds": duration, "recommendedLoop": loop_mode(name),
                           "sourceKind": "authored"}
    return clips


def story_actions(clips):
    mappings = {}
    exact = {name.lower(): name for name in clips}
    for action, names in {
        "idle": ("idle", "idle_neutral"), "walk_in_place": ("walk",),
        "run_in_place": ("run",), "attack": ("attack",), "interact": ("interact",),
        "wave": ("wave",),
    }.items():
        real = next((exact[name] for name in names if name in exact), None)
        if real:
            mappings[action] = {"realClip": real, "authored": True}
    return mappings


def skeleton_mapping(bones):
    lookup = {key(name): name for name in bones}
    aliases = {
        "root": ("root",), "hips": ("hips", "pelvis"), "spine": ("spine", "spine01", "abdomen"),
        "chest": ("chest", "spine02", "spine2"), "neck": ("neck",), "head": ("head",),
        "leftUpperArm": ("leftupperarm", "upperarml", "armleft"),
        "leftLowerArm": ("leftlowerarm", "lowerarml", "forearmleft"),
        "leftHand": ("lefthand", "wristl", "handleft"),
        "rightUpperArm": ("rightupperarm", "upperarmr", "armright"),
        "rightLowerArm": ("rightlowerarm", "lowerarmr", "forearmright"),
        "rightHand": ("righthand", "wristr", "handright"),
        "leftUpperLeg": ("leftupperleg", "upperlegl", "thighleft"),
        "leftLowerLeg": ("leftlowerleg", "lowerlegl", "calfleft"),
        "leftFoot": ("leftfoot", "footl"),
        "rightUpperLeg": ("rightupperleg", "upperlegr", "thighright"),
        "rightLowerLeg": ("rightlowerleg", "lowerlegr", "calfright"),
        "rightFoot": ("rightfoot", "footr"),
    }
    return {target: lookup[alias] for target, choices in aliases.items()
            for alias in choices if alias in lookup}


def registry_entry(candidate, conversion, output_glb):
    name = str(candidate["name"])
    clips = authored_clips(candidate)
    license_info = candidate.get("license") or {}
    source_pack = str(candidate.get("pack") or "Quaternius").split("-2026", 1)[0].rstrip("-")
    user_authorized = PIRATE_PACK_MARKER in source_pack and str(license_info.get("type") or "UNKNOWN") == "UNKNOWN"
    bounds = conversion.get("final_bounds_blender") or {}
    return {
        "displayName": f"Quaternius {name.replace('_', ' ')}",
        "sourcePack": source_pack,
        "sourceAsset": relative(Path(candidate["sourceFile"])),
        "assetPath": relative(output_glb),
        "assetSha256": sha256(output_glb),
        "license": {
            "status": "user_authorized_pending_source_license" if user_authorized else "verified",
            "name": license_info.get("type", "UNKNOWN" if user_authorized else "CC0-1.0"),
            "source": license_info.get("source", ""),
            "localLicenseFilePresent": bool(license_info.get("source")),
            "note": ("User explicitly authorized local Pirate Kit use; source archive did not include a license file."
                     if user_authorized else ""),
        },
        "tier": "SKELETAL_BASIC",
        "skeleton": {"armatureName": conversion.get("armature", "QuaterniusMasterRig"),
                     "boneCount": len(conversion.get("bones") or []),
                     "skinnedMeshCount": len(conversion.get("meshes") or [])},
        "skeletonMapping": skeleton_mapping(conversion.get("bones") or []),
        "authoredClips": clips,
        "storyActionClips": story_actions(clips),
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
                           "measuredHeight": bounds.get("height"), "groundOffset": (bounds.get("min") or [0, 0, 0])[2]},
        "limitations": ["Body-animation character only; no validated facial controls or dialogue lip-sync.",
                        "World locomotion and prop contact are not calibrated.",
                        "Automated runtime review is deferred until the final test pass."],
        "validation": {"status": "standardized_runtime_review_pending",
                       "machineReport": relative(Path(conversion["report_path"])),
                       "visualEvidence": "pending_deferred_by_user", "promotedByEvidence": False},
    }


def manifest_entry(candidate):
    name = str(candidate["name"])
    item_slug = slug(name)
    return {
        "name": f"Quaternius {name.replace('_', ' ')}",
        "keywords": sorted(set([item_slug, category(name, candidate.get("pack", "")), "quaternius",
                                "animated", "character"])),
        "blend": f"quaternius_{item_slug}.blend", "thumb": None,
        "capability_id": f"quaternius_{item_slug}", "animation_tier": "SKELETAL_BASIC",
    }


def register(successes):
    manifest = read(CHARACTER_MANIFEST, [])
    registry = read(CAPABILITY_REGISTRY, {})
    registry.setdefault("characters", {})
    by_id = {item.get("capability_id"): item for item in manifest if item.get("capability_id")}
    for row in successes:
        candidate, conversion, glb = row["candidate"], row["conversion"], row["glb"]
        item = manifest_entry(candidate)
        by_id[item["capability_id"]] = item
        registry["characters"][item["capability_id"]] = registry_entry(candidate, conversion, glb)
    preserved = [item for item in manifest if not item.get("capability_id")]
    manifest = preserved + sorted(by_id.values(), key=lambda item: item["name"].casefold())
    write(CHARACTER_MANIFEST, manifest)
    write(CAPABILITY_REGISTRY, registry)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--execute", action="store_true")
    parser.add_argument("--allow-user-authorized-pirate", action="store_true",
                        help="include local Pirate Kit sources under explicit user authorization")
    parser.add_argument("--blender", type=Path, default=DEFAULT_BLENDER)
    args = parser.parse_args()
    inventory = read(INVENTORY, {})
    registry = read(CAPABILITY_REGISTRY, {})
    candidates = select_candidates(
        inventory, set((registry.get("characters") or {}).keys()),
        allow_user_authorized_pirate=args.allow_user_authorized_pirate)
    planned = [{"id": f"quaternius_{slug(item['name'])}", "name": item["name"],
                "pack": item["pack"], "source": relative(Path(item["sourceFile"])),
                "clips": len(item.get("animationClips") or [])} for item in candidates]
    if not args.execute:
        write(REPORT, {"schemaVersion": 1, "status": "PREFLIGHT", "plannedCount": len(planned),
                       "characters": planned,
                       "pirateMode": "user_authorized" if args.allow_user_authorized_pirate else "blocked"})
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
                env = os.environ.copy()
                env["SBZ_CHARACTER_ID"] = character_id
                env["SBZ_CHARACTER_NAME"] = name
                result = subprocess.run([str(args.blender), "-b", "--python", str(STANDARDIZER), "--",
                                         candidate["sourceFile"], str(output_glb), str(output_blend), str(report_path)],
                                        cwd=ROOT, env=env, text=True, capture_output=True)
                if result.returncode:
                    raise RuntimeError((result.stdout + "\n" + result.stderr)[-2500:])
            conversion = read(report_path, {})
            if not conversion or not output_glb.is_file() or not output_blend.is_file():
                raise RuntimeError("standardizer did not produce the required runtime triplet")
            conversion["report_path"] = str(report_path)
            successes.append({"candidate": candidate, "conversion": conversion, "glb": output_glb})
        except Exception as exc:
            failures.append({"id": character_id, "error": str(exc)[:2500]})
    register(successes)
    document = {"schemaVersion": 1, "status": "COMPLETE" if not failures else "PARTIAL",
                "plannedCount": len(candidates), "integratedCount": len(successes),
                "failureCount": len(failures), "characters": planned,
                "failures": failures,
                "pirateMode": "user_authorized" if args.allow_user_authorized_pirate else "blocked",
                "verification": "runtime and regression tests deferred by user"}
    write(REPORT, document)
    print(json.dumps({"integration": document["status"], "integrated": len(successes),
                      "failed": len(failures)}))
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
