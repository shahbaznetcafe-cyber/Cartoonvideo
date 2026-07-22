"""Generate Phase 4 capability entries from conversion evidence."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "assets/characters/quaternius_representative/phase4_manifest.json"
REGISTRY = ROOT / "assets/characters/capability_registry.json"
ALIAS_NAMES = {"Celebrate", "Listen", "Point", "TalkIdle"}
REPEAT_CLIPS = {"Idle", "Idle_Gun", "Idle_Gun_Pointing", "Idle_Neutral", "Idle_Sword",
                "Listen", "Run", "Run_Back", "Run_Left", "Run_Right", "Run_Shoot",
                "TalkIdle", "Walk"}
SKELETON_MAPPING = {
    "root": "Root", "hips": "Hips", "spine": "Abdomen", "chest": "Chest",
    "neck": "Neck", "head": "Head", "leftShoulder": "Shoulder.L",
    "leftUpperArm": "UpperArm.L", "leftLowerArm": "LowerArm.L", "leftHand": "Wrist.L",
    "rightShoulder": "Shoulder.R", "rightUpperArm": "UpperArm.R",
    "rightLowerArm": "LowerArm.R", "rightHand": "Wrist.R",
    "leftUpperLeg": "UpperLeg.L", "leftLowerLeg": "LowerLeg.L", "leftFoot": "Foot.L",
    "rightUpperLeg": "UpperLeg.R", "rightLowerLeg": "LowerLeg.R", "rightFoot": "Foot.R",
}


def resolve(value: str) -> Path:
    return ROOT / value


def sha256(path: Path) -> str:
    digest = hashlib.sha256(path.read_bytes())
    return digest.hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest", type=Path, default=MANIFEST)
    args = parser.parse_args()
    manifest = json.loads(args.manifest.read_text(encoding="utf-8"))
    registry = json.loads(REGISTRY.read_text(encoding="utf-8"))
    for character in manifest["characters"]:
        conversion = json.loads(resolve(character["conversionReport"]).read_text(encoding="utf-8"))
        validation = json.loads(resolve(character["validationReport"]).read_text(encoding="utf-8"))
        aliases = conversion.get("aliases") or {}
        clips = {}
        for action in conversion["actions"]:
            name = action["name"]
            clip = {
                "durationSeconds": action["duration"],
                "recommendedLoop": "repeat" if name in REPEAT_CLIPS else "once",
                "sourceKind": "recorded_alias" if name in ALIAS_NAMES else "authored",
            }
            if name in aliases:
                clip["realSourceClip"] = aliases[name]
            clips[name] = clip
        registry["characters"][character["id"]] = {
            "displayName": character["displayName"],
            "sourcePack": manifest.get("sourcePack", "Quaternius verified pack"),
            "sourceAsset": character["source"],
            "assetPath": character["outputGlb"],
            "assetSha256": sha256(resolve(character["outputGlb"])),
            "license": manifest["license"],
            "tier": "SKELETAL_BASIC",
            "skeleton": {
                "armatureName": conversion["armature"],
                "boneCount": len(conversion["bones"]),
                "skinnedMeshCount": len(conversion["meshes"]),
            },
            "skeletonMapping": SKELETON_MAPPING,
            "authoredClips": clips,
            "storyActionClips": {
                "idle": {"realClip": "Idle", "authored": True},
                "listen": {"realClip": "Idle_Neutral", "authored": True},
                "walk_in_place": {"realClip": "Walk", "authored": True},
                "wave": {"realClip": "Wave", "authored": True},
                "interact": {"realClip": "Interact", "authored": True},
                "point": {"realClip": "Idle_Gun_Pointing", "authored": True,
                          "disclosure": "Uses the real authored gun-pointing idle source clip."},
            },
            "locomotionProfiles": {},
            "rootMotion": {
                "treatment": "in_place_clip_plus_grounded_holder",
                "worldTranslationOwner": "character_holder",
                "animatedBonePositionTracks": "preserved",
                "groundCorrection": True,
                "worldDisplacementCalibrated": False,
            },
            "interaction": {"enabled": False, "handIK": False, "supported": {}},
            "facial": {"ready": False, "jaw": False, "visemes": False, "blink": False,
                       "eyeTarget": False, "emotionMorphs": False, "dialogueLipSync": False},
            "cameraPolicy": {"reject": ["dialogue_close_up", "facial_close_up"],
                             "allowBodyReactionClose": True, "preferOffCenterComposition": True},
            "scaleAndGround": {
                "targetHeight": conversion["target_height"],
                "measuredHeight": conversion["final_bounds_blender"]["height"],
                "groundOffset": conversion["final_bounds_blender"]["min"][2],
            },
            "limitations": [
                "Body-animation character only; no facial controls or dialogue lip-sync.",
                "World locomotion displacement is not calibrated, so this entry remains SKELETAL_BASIC.",
                "No hand IK or validated prop-contact profile.",
                "Automated multi-character runtime capture is deferred until the final test pass.",
            ],
            "validation": {
                "status": validation["phase4"]["status"],
                "machineReport": character["validationReport"],
                "visualEvidence": "pending_deferred_by_user",
                "facialValidation": "failed_missing_controls",
                "promotedByEvidence": False,
            },
        }
        print(f"PHASE4_REGISTERED={character['id']}")
    REGISTRY.write_text(json.dumps(registry, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
