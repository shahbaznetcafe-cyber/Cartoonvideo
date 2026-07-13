"""GLB character capability validation for SBZ AI Video Studio.

This module reads only the JSON metadata chunk of a GLB.  It intentionally has
no Three.js or Blender dependency, so validation can run in Flask, tests, and
pre-render checks without loading or changing a character asset.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import struct
from pathlib import Path
from typing import Any, Iterable


SCHEMA_VERSION = 1

REQUIRED_VISEMES = (
    "viseme_sil", "viseme_PP", "viseme_FF", "viseme_TH", "viseme_DD",
    "viseme_kk", "viseme_CH", "viseme_SS", "viseme_nn", "viseme_RR",
    "viseme_aa", "viseme_E", "viseme_I", "viseme_O", "viseme_U",
)

REQUIRED_FACIAL = (
    "eyeBlinkLeft", "eyeBlinkRight", "browInnerUp", "browDownLeft",
    "browDownRight", "mouthSmileLeft", "mouthSmileRight",
    "mouthFrownLeft", "mouthFrownRight",
)

ARKIT_MORPHS = (
    "eyeBlinkLeft", "eyeBlinkRight", "eyeLookDownLeft", "eyeLookDownRight",
    "eyeLookInLeft", "eyeLookInRight", "eyeLookOutLeft", "eyeLookOutRight",
    "eyeLookUpLeft", "eyeLookUpRight", "eyeSquintLeft", "eyeSquintRight",
    "eyeWideLeft", "eyeWideRight", "jawForward", "jawLeft", "jawRight",
    "jawOpen", "mouthClose", "mouthFunnel", "mouthPucker", "mouthLeft",
    "mouthRight", "mouthSmileLeft", "mouthSmileRight", "mouthFrownLeft",
    "mouthFrownRight", "mouthDimpleLeft", "mouthDimpleRight",
    "mouthStretchLeft", "mouthStretchRight", "mouthRollLower",
    "mouthRollUpper", "mouthShrugLower", "mouthShrugUpper",
    "mouthPressLeft", "mouthPressRight", "mouthLowerDownLeft",
    "mouthLowerDownRight", "mouthUpperUpLeft", "mouthUpperUpRight",
    "browDownLeft", "browDownRight", "browInnerUp", "browOuterUpLeft",
    "browOuterUpRight", "cheekPuff", "cheekSquintLeft", "cheekSquintRight",
    "noseSneerLeft", "noseSneerRight", "tongueOut",
)

EYE_MORPHS = (
    "eyeLookDownLeft", "eyeLookDownRight", "eyeLookInLeft", "eyeLookInRight",
    "eyeLookOutLeft", "eyeLookOutRight", "eyeLookUpLeft", "eyeLookUpRight",
)

LEGACY_BODY_BONES = ("body", "jaw", "arm_L", "arm_R", "leg_L", "leg_R")

MIXAMO_CORE_BONES = (
    "Hips", "Spine", "Spine1", "Spine2", "Neck", "Head",
    "LeftShoulder", "LeftArm", "LeftForeArm", "LeftHand",
    "RightShoulder", "RightArm", "RightForeArm", "RightHand",
    "LeftUpLeg", "LeftLeg", "LeftFoot",
    "RightUpLeg", "RightLeg", "RightFoot",
)

_FINGERS = ("Thumb", "Index", "Middle", "Ring", "Pinky")
TALKINGHEAD_BODY_BONES = MIXAMO_CORE_BONES + ("LeftToeBase", "RightToeBase") + tuple(
    f"{side}Hand{finger}{joint}"
    for side in ("Left", "Right")
    for finger in _FINGERS
    for joint in (1, 2, 3)
)


def _key(value: str) -> str:
    """Normalize common Blender/Mixamo/exporter namespaces for comparison."""
    value = str(value or "").strip()
    for separator in ("|", "/", "\\"):
        if separator in value:
            value = value.rsplit(separator, 1)[-1]
    if ":" in value:
        value = value.rsplit(":", 1)[-1]
    lower = value.lower()
    if lower.startswith("mixamorig"):
        value = value[len("mixamorig"):].lstrip("_:-. ")
    return "".join(ch.lower() for ch in value if ch.isalnum())


def _coverage(required: Iterable[str], available: Iterable[str]) -> dict[str, list[str]]:
    by_key: dict[str, str] = {}
    for item in available:
        by_key.setdefault(_key(item), item)
    present, missing = [], []
    for canonical in required:
        if _key(canonical) in by_key:
            present.append(canonical)
        else:
            missing.append(canonical)
    return {"present": present, "missing": missing}


def _issue(code: str, message: str) -> dict[str, str]:
    return {"code": code, "message": message}


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _parse_glb(path: Path) -> tuple[dict[str, Any] | None, list[dict[str, str]], list[dict[str, str]], int | None]:
    errors: list[dict[str, str]] = []
    warnings: list[dict[str, str]] = []
    try:
        data = path.read_bytes()
    except OSError as exc:
        return None, [_issue("file_read_error", str(exc))], warnings, None

    if len(data) < 12:
        return None, [_issue("truncated_header", "GLB header is shorter than 12 bytes")], warnings, None

    magic, version, declared_length = struct.unpack_from("<4sII", data, 0)
    if magic != b"glTF":
        errors.append(_issue("invalid_magic", "File does not start with the GLB magic bytes"))
    if version != 2:
        errors.append(_issue("unsupported_version", f"GLB version {version} is not supported; expected version 2"))
    if declared_length > len(data):
        errors.append(_issue("truncated_file", f"Header declares {declared_length} bytes but file contains {len(data)}"))
    elif declared_length < len(data):
        warnings.append(_issue("trailing_bytes", f"Ignoring {len(data) - declared_length} trailing bytes"))

    limit = min(declared_length, len(data))
    offset = 12
    json_chunk: bytes | None = None
    while offset < limit:
        if offset + 8 > limit:
            errors.append(_issue("truncated_chunk_header", "GLB chunk header is truncated"))
            break
        chunk_length, chunk_type = struct.unpack_from("<II", data, offset)
        offset += 8
        if offset + chunk_length > limit:
            errors.append(_issue("truncated_chunk", "GLB chunk extends beyond the declared file length"))
            break
        chunk = data[offset:offset + chunk_length]
        offset += chunk_length
        if chunk_type == 0x4E4F534A and json_chunk is None:  # JSON
            json_chunk = chunk

    if json_chunk is None:
        errors.append(_issue("missing_json_chunk", "GLB has no JSON metadata chunk"))
        return None, errors, warnings, version

    try:
        document = json.loads(json_chunk.rstrip(b"\x00 \t\r\n").decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        errors.append(_issue("invalid_json_chunk", f"Invalid GLB JSON metadata: {exc}"))
        return None, errors, warnings, version
    if not isinstance(document, dict):
        errors.append(_issue("invalid_document", "GLB JSON root must be an object"))
        return None, errors, warnings, version

    asset_version = str((document.get("asset") or {}).get("version") or "")
    if not asset_version.startswith("2"):
        errors.append(_issue("invalid_asset_version", "glTF asset.version must be 2.x"))
    return document, errors, warnings, version


def validate_glb(path: os.PathLike[str] | str, character: dict[str, Any] | None = None) -> dict[str, Any]:
    """Inspect one GLB and return a deterministic, JSON-serializable report."""
    source = Path(path).expanduser().resolve()
    character = dict(character or {})
    report: dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "character": {
            "name": str(character.get("name") or source.stem),
            "blend": str(character.get("blend") or ""),
            "registered": not bool(character.get("unregistered")),
        },
        "source": {
            "path": str(source),
            "exists": source.is_file(),
            "sha256": "",
            "glb_version": None,
        },
        "valid_glb": False,
        "mesh_count": 0,
        "skeleton_bones": [],
        "skins": [],
        "skinned_meshes": [],
        "morph_targets": [],
        "morph_targets_by_mesh": [],
        "body": {},
        "visemes": {"present": [], "missing": list(REQUIRED_VISEMES)},
        "facial": {"present": [], "missing": list(REQUIRED_FACIAL)},
        "blink_eye_emotion": {},
        "mixamo_compatible": False,
        "talkinghead_compatible": False,
        "tier": None,
        "compatibility_percent": 0,
        "warnings": [],
        "errors": [],
    }

    if not source.is_file():
        report["errors"].append(_issue("file_not_found", f"GLB file not found: {source}"))
        return report
    if source.suffix.lower() != ".glb":
        report["errors"].append(_issue("unsupported_extension", "Character validator accepts binary .glb files only"))
        return report

    report["source"]["sha256"] = _sha256(source)
    document, errors, warnings, version = _parse_glb(source)
    report["source"]["glb_version"] = version
    report["errors"].extend(errors)
    report["warnings"].extend(warnings)
    if document is None:
        return report

    nodes = document.get("nodes") if isinstance(document.get("nodes"), list) else []
    meshes = document.get("meshes") if isinstance(document.get("meshes"), list) else []
    skins = document.get("skins") if isinstance(document.get("skins"), list) else []
    report["mesh_count"] = len(meshes)

    joint_indices: set[int] = set()
    skin_rows = []
    for skin_index, skin in enumerate(skins):
        skin = skin if isinstance(skin, dict) else {}
        joints = skin.get("joints") if isinstance(skin.get("joints"), list) else []
        valid_joints = []
        for joint in joints:
            if isinstance(joint, int) and 0 <= joint < len(nodes):
                valid_joints.append(joint)
                joint_indices.add(joint)
            else:
                report["errors"].append(_issue(
                    "invalid_joint_index", f"Skin {skin_index} contains invalid joint index {joint!r}"))
        skin_rows.append({
            "index": skin_index,
            "name": str(skin.get("name") or f"skin_{skin_index}"),
            "joint_count": len(valid_joints),
        })
    report["skins"] = skin_rows

    bone_names = []
    for index in sorted(joint_indices):
        node = nodes[index] if isinstance(nodes[index], dict) else {}
        bone_names.append(str(node.get("name") or f"node_{index}"))
    report["skeleton_bones"] = sorted(set(bone_names), key=lambda value: value.casefold())

    skinned_rows = []
    for node_index, node in enumerate(nodes):
        if not isinstance(node, dict) or "mesh" not in node or "skin" not in node:
            continue
        mesh_index, skin_index = node.get("mesh"), node.get("skin")
        if not isinstance(mesh_index, int) or not 0 <= mesh_index < len(meshes):
            report["errors"].append(_issue(
                "invalid_mesh_index", f"Node {node_index} references invalid mesh index {mesh_index!r}"))
            continue
        if not isinstance(skin_index, int) or not 0 <= skin_index < len(skins):
            report["errors"].append(_issue(
                "invalid_skin_index", f"Node {node_index} references invalid skin index {skin_index!r}"))
            continue
        mesh = meshes[mesh_index] if isinstance(meshes[mesh_index], dict) else {}
        skinned_rows.append({
            "node": str(node.get("name") or f"node_{node_index}"),
            "mesh": str(mesh.get("name") or f"mesh_{mesh_index}"),
            "skin": str((skins[skin_index] if isinstance(skins[skin_index], dict) else {}).get("name") or f"skin_{skin_index}"),
        })
    report["skinned_meshes"] = skinned_rows

    all_targets: list[str] = []
    targets_by_mesh = []
    for mesh_index, mesh in enumerate(meshes):
        mesh = mesh if isinstance(mesh, dict) else {}
        primitives = mesh.get("primitives") if isinstance(mesh.get("primitives"), list) else []
        target_count = max((len(p.get("targets") or []) for p in primitives if isinstance(p, dict)), default=0)
        extras = mesh.get("extras") if isinstance(mesh.get("extras"), dict) else {}
        names = extras.get("targetNames") if isinstance(extras.get("targetNames"), list) else []
        if not names:
            for primitive in primitives:
                pextras = primitive.get("extras") if isinstance(primitive, dict) and isinstance(primitive.get("extras"), dict) else {}
                if isinstance(pextras.get("targetNames"), list):
                    names = pextras["targetNames"]
                    break
        names = [str(name) for name in names if str(name).strip()]
        if target_count and not names:
            report["warnings"].append(_issue(
                "unnamed_morph_targets", f"Mesh {mesh_index} has {target_count} morph targets without targetNames"))
        elif target_count and len(names) != target_count:
            report["warnings"].append(_issue(
                "morph_name_count_mismatch",
                f"Mesh {mesh_index} has {target_count} morph targets but {len(names)} names"))
        all_targets.extend(names)
        if target_count or names:
            targets_by_mesh.append({
                "mesh": str(mesh.get("name") or f"mesh_{mesh_index}"),
                "target_count": target_count,
                "names": names,
            })
    report["morph_targets"] = sorted(set(all_targets), key=lambda value: value.casefold())
    report["morph_targets_by_mesh"] = targets_by_mesh

    legacy = _coverage(LEGACY_BODY_BONES, report["skeleton_bones"])
    mixamo = _coverage(MIXAMO_CORE_BONES, report["skeleton_bones"])
    talkinghead_body = _coverage(TALKINGHEAD_BODY_BONES, report["skeleton_bones"])
    visemes = _coverage(REQUIRED_VISEMES, report["morph_targets"])
    facial = _coverage(REQUIRED_FACIAL, report["morph_targets"])
    arkit = _coverage(ARKIT_MORPHS, report["morph_targets"])
    blink = _coverage(("eyeBlinkLeft", "eyeBlinkRight"), report["morph_targets"])
    eyes = _coverage(EYE_MORPHS, report["morph_targets"])
    emotion_names = tuple(name for name in REQUIRED_FACIAL if not name.startswith("eyeBlink"))
    emotion = _coverage(emotion_names, report["morph_targets"])

    report["body"] = {
        "legacy": legacy,
        "mixamo_core": mixamo,
        "talkinghead_full": talkinghead_body,
    }
    report["visemes"] = visemes
    report["facial"] = facial
    report["blink_eye_emotion"] = {"blink": blink, "eye_look": eyes, "emotion": emotion}

    has_skinned_mesh = bool(skinned_rows)
    has_jaw = not _coverage(("jaw",), report["skeleton_bones"])["missing"]
    has_mouth_driver = has_jaw or not _coverage(("jawOpen",), report["morph_targets"])["missing"]
    report["mixamo_compatible"] = has_skinned_mesh and not mixamo["missing"]
    report["talkinghead_compatible"] = (
        has_skinned_mesh and not talkinghead_body["missing"] and
        not visemes["missing"] and not arkit["missing"]
    )

    report["valid_glb"] = not report["errors"]
    if report["valid_glb"]:
        if not visemes["missing"] and not facial["missing"]:
            report["tier"] = "FULL_FACIAL"
        elif not visemes["missing"]:
            report["tier"] = "VISEME_FACE"
        elif report["mixamo_compatible"] or (has_skinned_mesh and not has_jaw):
            report["tier"] = "SKELETAL_BASIC"
        elif has_jaw:
            report["tier"] = "LEGACY_JAW"

    legacy_ratio = len(legacy["present"]) / len(LEGACY_BODY_BONES)
    mixamo_ratio = len(mixamo["present"]) / len(MIXAMO_CORE_BONES)
    body_ratio = max(mixamo_ratio, legacy_ratio * 0.4)
    score = 0.0
    if report["valid_glb"]:
        score += 10
        score += 10 if meshes else 0
        score += 20 * body_ratio
        score += 5 if skins else 0
        score += 5 if has_skinned_mesh else 0
        score += 30 * len(visemes["present"]) / len(REQUIRED_VISEMES)
        score += 15 * len(facial["present"]) / len(REQUIRED_FACIAL)
        score += 5 if has_mouth_driver else 0
    report["compatibility_percent"] = int(round(min(100, score)))

    if report["valid_glb"] and not meshes:
        report["warnings"].append(_issue("no_meshes", "GLB contains no meshes"))
    if report["valid_glb"] and report["tier"] is None:
        report["warnings"].append(_issue(
            "unsupported_character", "No supported jaw, skeletal, or viseme animation capability was detected"))
    if report["tier"] == "LEGACY_JAW":
        report["warnings"].append(_issue(
            "legacy_jaw_fallback", "Character will continue using the existing jaw-openness fallback"))
    elif report["tier"] == "SKELETAL_BASIC":
        report["warnings"].append(_issue(
            "missing_visemes", "Character has no complete viseme set; facial lip-sync will use an available fallback"))
    elif report["tier"] == "VISEME_FACE":
        report["warnings"].append(_issue(
            "incomplete_facial_set", "Visemes are complete, but blink/emotion morphs are incomplete"))

    return report


def format_human_report(report: dict[str, Any]) -> str:
    """Create a compact report suitable for CLI logs or a plain-text UI."""
    name = report.get("character", {}).get("name") or "Character"
    lines = [
        f"{name}: {report.get('tier') or 'UNSUPPORTED'} ({report.get('compatibility_percent', 0)}%)",
        f"GLB: {'valid' if report.get('valid_glb') else 'invalid'}",
        f"Bones: {len(report.get('skeleton_bones') or [])}; skinned meshes: {len(report.get('skinned_meshes') or [])}",
        f"Visemes: {len(report.get('visemes', {}).get('present') or [])}/{len(REQUIRED_VISEMES)}",
        f"Facial controls: {len(report.get('facial', {}).get('present') or [])}/{len(REQUIRED_FACIAL)}",
        f"Mixamo: {'yes' if report.get('mixamo_compatible') else 'no'}; TalkingHead strict: {'yes' if report.get('talkinghead_compatible') else 'no'}",
    ]
    missing = report.get("visemes", {}).get("missing") or []
    if missing:
        lines.append("Missing visemes: " + ", ".join(missing))
    for issue in report.get("warnings") or []:
        lines.append("Warning: " + issue.get("message", str(issue)))
    for issue in report.get("errors") or []:
        lines.append("Error: " + issue.get("message", str(issue)))
    return "\n".join(lines)


def _cli() -> int:
    parser = argparse.ArgumentParser(description="Inspect SBZ Three.js GLB character capabilities")
    parser.add_argument("paths", nargs="+", help="One or more .glb files")
    parser.add_argument("--output", help="Write JSON report to this path instead of stdout")
    args = parser.parse_args()
    reports = [validate_glb(path) for path in args.paths]
    payload: Any = reports[0] if len(reports) == 1 else {"schema_version": SCHEMA_VERSION, "characters": reports}
    rendered = json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True)
    if args.output:
        Path(args.output).write_text(rendered + "\n", encoding="utf-8")
    else:
        print(rendered)
    return 0 if all(report["valid_glb"] for report in reports) else 1


if __name__ == "__main__":
    raise SystemExit(_cli())
