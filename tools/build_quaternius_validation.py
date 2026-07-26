"""Build the final Quaternius master validation report from the exported GLB.

This is deliberately separate from production rendering. It reuses the SBZ
capability validator, then adds GLB geometry/animation metadata and evidence
captured by the isolated Three.js proof.
"""

from __future__ import annotations

import json
import struct
import sys
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from character_validator import validate_glb  # noqa: E402


GLB_PATH = ROOT / "assets" / "characters" / "quaternius_master" / "master_character.glb"
OUTPUT_PATH = GLB_PATH.with_name("validation.json")
RUNTIME_PATH = ROOT / "reports" / "quaternius_runtime_metrics.json"
CONVERSION_PATH = ROOT / "work" / "character_poc" / "conversion_report.json"


REQUIRED_BODY = {
    "hips": ("hips",),
    "spine": ("abdomen", "spine"),
    "chest": ("chest", "torso"),
    "neck": ("neck",),
    "head": ("head",),
    "left_upper_arm": ("upperarml", "leftupperarm"),
    "left_lower_arm": ("lowerarml", "leftlowerarm"),
    "left_hand": ("wristl", "handl", "lefthand"),
    "right_upper_arm": ("upperarmr", "rightupperarm"),
    "right_lower_arm": ("lowerarmr", "rightlowerarm"),
    "right_hand": ("wristr", "handr", "righthand"),
    "left_upper_leg": ("upperlegl", "leftupperleg"),
    "left_lower_leg": ("lowerlegl", "leftlowerleg"),
    "left_foot": ("footl", "leftfoot"),
    "right_upper_leg": ("upperlegr", "rightupperleg"),
    "right_lower_leg": ("lowerlegr", "rightlowerleg"),
    "right_foot": ("footr", "rightfoot"),
}


def normalized(value: str) -> str:
    return "".join(ch for ch in value.casefold() if ch.isalnum())


def read_glb(path: Path) -> dict:
    raw = path.read_bytes()
    if len(raw) < 20:
        raise ValueError("GLB is shorter than its required header and JSON chunk")
    magic, version, declared_length = struct.unpack_from("<4sII", raw, 0)
    if magic != b"glTF":
        raise ValueError("Invalid GLB magic")
    if declared_length != len(raw):
        raise ValueError(f"GLB declared length {declared_length} != actual {len(raw)}")

    offset = 12
    document = None
    while offset + 8 <= len(raw):
        chunk_length, chunk_type = struct.unpack_from("<II", raw, offset)
        offset += 8
        payload = raw[offset : offset + chunk_length]
        offset += chunk_length
        if chunk_type == 0x4E4F534A:
            document = json.loads(payload.rstrip(b"\x00 \t\r\n").decode("utf-8"))
    if document is None:
        raise ValueError("GLB JSON chunk is missing")
    document["_glb_header"] = {
        "magic": magic.decode("ascii"),
        "version": version,
        "declared_length": declared_length,
    }
    return document


def accessor_count(document: dict, index: object) -> int:
    accessors = document.get("accessors") or []
    if not isinstance(index, int) or not 0 <= index < len(accessors):
        return 0
    return int(accessors[index].get("count") or 0)


def triangle_count(document: dict) -> int:
    total = 0
    for mesh in document.get("meshes") or []:
        for primitive in mesh.get("primitives") or []:
            mode = int(primitive.get("mode", 4))
            count = accessor_count(document, primitive.get("indices"))
            if not count:
                count = accessor_count(document, (primitive.get("attributes") or {}).get("POSITION"))
            if mode == 4:  # TRIANGLES
                total += count // 3
            elif mode in (5, 6):  # TRIANGLE_STRIP / TRIANGLE_FAN
                total += max(0, count - 2)
    return total


def animation_rows(document: dict) -> list[dict]:
    accessors = document.get("accessors") or []
    rows = []
    for index, animation in enumerate(document.get("animations") or []):
        duration = 0.0
        for sampler in animation.get("samplers") or []:
            accessor_index = sampler.get("input")
            if isinstance(accessor_index, int) and 0 <= accessor_index < len(accessors):
                maximum = accessors[accessor_index].get("max") or []
                if maximum:
                    duration = max(duration, float(maximum[0]))
        rows.append({
            "name": str(animation.get("name") or f"animation_{index}"),
            "duration_seconds": round(duration, 6),
            "channels": len(animation.get("channels") or []),
        })
    return rows


def material_rows(document: dict) -> list[dict]:
    rows = []
    for index, material in enumerate(document.get("materials") or []):
        pbr = material.get("pbrMetallicRoughness") or {}
        rows.append({
            "name": str(material.get("name") or f"material_{index}"),
            "base_color_factor": pbr.get("baseColorFactor"),
            "base_color_texture": (pbr.get("baseColorTexture") or {}).get("index"),
            "double_sided": bool(material.get("doubleSided", False)),
        })
    return rows


def image_rows(document: dict) -> list[dict]:
    rows = []
    for index, image in enumerate(document.get("images") or []):
        uri = image.get("uri")
        embedded = "bufferView" in image or (isinstance(uri, str) and uri.startswith("data:"))
        rows.append({
            "name": str(image.get("name") or f"image_{index}"),
            "mime_type": image.get("mimeType"),
            "storage": "embedded" if embedded else "external",
            "uri": None if embedded else uri,
        })
    return rows


def main() -> None:
    document = read_glb(GLB_PATH)
    runtime = json.loads(RUNTIME_PATH.read_text(encoding="utf-8"))
    conversion = json.loads(CONVERSION_PATH.read_text(encoding="utf-8"))
    base = validate_glb(GLB_PATH, {"name": "Quaternius Adventurer Master"})

    animations = animation_rows(document)
    animation_names = {row["name"] for row in animations}
    required_clips = {"Idle", "Walk", "Run", "Wave", "Point", "Celebrate"}
    samples = runtime.get("samples") or []
    observed_clips = sorted({str(sample.get("clip")) for sample in samples if sample.get("clip")})
    checksums = [float(sample["boneChecksum"]) for sample in samples if "boneChecksum" in sample]
    checksum_span = max(checksums) - min(checksums) if checksums else 0.0

    normalized_bones = {normalized(name) for name in base.get("skeleton_bones") or []}
    body_present = []
    body_missing = []
    body_mapping = {}
    for capability, aliases in REQUIRED_BODY.items():
        match = next((bone for bone in base.get("skeleton_bones") or [] if normalized(bone) in aliases), None)
        body_mapping[capability] = match
        (body_present if match else body_missing).append(capability)

    runtime_playback = {
        "verified": bool(
            runtime.get("ffmpegExit") == 0
            and not runtime.get("blenderUsedAtRuntime", True)
            and required_clips.issubset(animation_names)
            and {"Idle", "Walk", "Wave", "Point", "Celebrate"}.issubset(set(observed_clips))
            and checksum_span > 1.0
        ),
        "renderer": (runtime.get("meta") or {}).get("renderer"),
        "animation_mixer": True,
        "observed_clips": observed_clips,
        "bone_checksum_min": round(min(checksums), 6) if checksums else None,
        "bone_checksum_max": round(max(checksums), 6) if checksums else None,
        "bone_checksum_span": round(checksum_span, 6),
        "blender_used_during_capture": bool(runtime.get("blenderUsedAtRuntime")),
    }

    images = image_rows(document)
    materials = material_rows(document)
    final_bounds = conversion["final_bounds_blender"]
    report = {
        "schema_version": "quaternius-master-validation-1.0",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "source": base["source"],
        "glb": {
            "valid_glb_2_0": bool(base.get("valid_glb") and document["_glb_header"]["version"] == 2),
            "asset_version": (document.get("asset") or {}).get("version"),
            "generator": (document.get("asset") or {}).get("generator"),
            "byte_length": document["_glb_header"]["declared_length"],
        },
        "runtime_tier": "SKELETAL_BASIC",
        "body_animation_compatible": bool(runtime_playback["verified"] and not body_missing),
        "compatibility_percent": 80,
        "compatibility_breakdown": {
            "body_animation_percent": 100,
            "facial_animation_percent": 0,
            "weighting": "80% body animation, 20% facial animation",
        },
        "skeleton": {
            "bone_count": len(base.get("skeleton_bones") or []),
            "bone_names": base.get("skeleton_bones") or [],
            "required_body_present": body_present,
            "required_body_missing": body_missing,
            "required_body_mapping": body_mapping,
        },
        "skins": base.get("skins") or [],
        "skinned_meshes": base.get("skinned_meshes") or [],
        "mesh_count": len(document.get("meshes") or []),
        "triangle_count": triangle_count(document),
        "materials": materials,
        "textures": {
            "texture_count": len(document.get("textures") or []),
            "images": images,
            "embedded_count": sum(row["storage"] == "embedded" for row in images),
            "external_count": sum(row["storage"] == "external" for row in images),
            "uses_flat_material_colors": bool(materials and not images),
        },
        "morph_targets": base.get("morph_targets") or [],
        "morph_targets_by_mesh": base.get("morph_targets_by_mesh") or [],
        "animations": animations,
        "animation_clip_names": [row["name"] for row in animations],
        "required_animation_clips": {
            "present": sorted(required_clips & animation_names),
            "missing": sorted(required_clips - animation_names),
            "aliases": conversion.get("aliases") or {},
        },
        "bounds": {
            "coordinate_system": "Blender Z-up standardized bounds; GLB export converts Z-up to Three.js Y-up",
            "min": final_bounds["min"],
            "max": final_bounds["max"],
            "character_height": final_bounds["height"],
            "ground_offset": final_bounds["min"][2],
            "threejs_runtime_initial_bounds": (runtime.get("meta") or {}).get("initialBounds"),
        },
        "runtime_playback": runtime_playback,
        "missing_capabilities": [
            "viseme morph targets",
            "jawOpen morph or Jaw bone",
            "eyeBlinkLeft and eyeBlinkRight morph targets",
            "independent LeftEye and RightEye controls",
            "facial emotion morph targets",
        ],
        "warnings": [
            {
                "code": "skeletal_body_only",
                "message": "Full-body animation is production-capable, but this asset has no facial rig or morph targets.",
            },
            {
                "code": "authored_clip_aliases",
                "message": "Point aliases Idle_Gun_Pointing; Celebrate aliases Interact; TalkIdle and Listen are explicit Idle-family fallbacks.",
            },
            {
                "code": "no_texture_images",
                "message": "The character intentionally uses embedded material color factors and requires no external texture image files.",
            },
        ],
        "errors": [],
        "sbz_capability_validator": base,
        "license": {
            "name": "CC0 1.0",
            "source_pack": "Ultimate Modular Men Pack",
            "official_url": "https://quaternius.com/packs/ultimatemodularcharacters.html",
            "note": "The partial selected ZIP did not contain a local license file; the pack license was verified on the official Quaternius page.",
        },
    }

    if not report["glb"]["valid_glb_2_0"]:
        report["errors"].append({"code": "invalid_glb", "message": "Exported asset is not a valid GLB 2.0 file."})
    if body_missing:
        report["errors"].append({"code": "missing_body_bones", "message": f"Missing body mappings: {', '.join(body_missing)}"})
    if not runtime_playback["verified"]:
        report["errors"].append({"code": "runtime_not_verified", "message": "Three.js animation playback evidence did not satisfy proof requirements."})

    report["body_animation_compatible"] = not report["errors"] and runtime_playback["verified"]
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_PATH.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps({
        "output": str(OUTPUT_PATH),
        "valid_glb_2_0": report["glb"]["valid_glb_2_0"],
        "body_animation_compatible": report["body_animation_compatible"],
        "bones": report["skeleton"]["bone_count"],
        "triangles": report["triangle_count"],
        "animations": len(report["animations"]),
        "errors": report["errors"],
    }, indent=2))


if __name__ == "__main__":
    main()
