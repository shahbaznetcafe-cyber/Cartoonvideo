"""Unified, read-only character catalog for the desktop UI.

``characters3d.json`` remains the render authority. This module adds library,
category and capability metadata. Unstandardized Quaternius inventory is
visible to users but never selectable by the production renderer.
"""
from __future__ import annotations

import json
import os
import re
from pathlib import Path

import config
import char3d_lib


BASE_DIR = Path(config.BASE_DIR)
INVENTORY_PATH = BASE_DIR / "reports" / "quaternius_inventory.json"
CAPABILITY_PATH = BASE_DIR / "assets" / "characters" / "capability_registry.json"
SCHEMA_VERSION = 1

COMPONENT_NAMES = {
    "basecharacter", "humansmaster", "chefhat", "cowboyhair",
    "ninjamalehair", "vikinghelmet", "zombiearm", "zombieribcage",
}
ANIMAL_NAMES = {
    "alpaking", "alpakingevolved", "armabee", "armabeeevolved", "birb",
    "bunny", "cat", "chicken", "cow", "dino", "dog", "dragon",
    "dragonevolved", "fish", "frog", "germanshepherd", "monkroose",
    "pigeon", "pug", "shark", "sharky", "squidle", "yeti",
}


def _read_json(path: Path, default):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError, TypeError):
        return default


def _key(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "", str(value or "").lower())


def _slug(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", str(value or "").lower()).strip("_")


def _relative(path_value: str) -> str:
    try:
        return os.path.relpath(path_value, BASE_DIR).replace("\\", "/")
    except (TypeError, ValueError):
        return ""


def _category(name: str, pack: str = "", library: str = "quaternius") -> str:
    if library == "sbz":
        return "originals"
    key = _key(name)
    pack_key = _key(pack)
    if key in ANIMAL_NAMES:
        return "animals"
    if "pirate" in pack_key:
        return "pirates"
    if "space" in pack_key:
        return "space"
    if "zombie" in pack_key or key.startswith("zombie"):
        return "zombie"
    if "monster" in pack_key:
        return "monsters"
    return "humans"


def _capability_characters():
    document = _read_json(CAPABILITY_PATH, {})
    return document.get("characters", {}) if isinstance(document, dict) else {}


def _ready_records():
    import character_performance
    capabilities = _capability_characters()
    records = []
    for entry in char3d_lib.load():
        blend = str(entry.get("blend") or "")
        blend_slug = Path(blend).stem
        capability_id = str(entry.get("capability_id") or "")
        is_quaternius = capability_id.startswith("quaternius_") or blend_slug.startswith("quaternius_")
        capability = capabilities.get(capability_id, {}) if is_quaternius else {}
        library = "quaternius" if is_quaternius else "sbz"
        exists = bool(char3d_lib.blend_path(entry))
        performance = character_performance.profile_for_entry(entry)
        traits = {}
        if is_quaternius:
            try:
                import character_traits
                traits = character_traits.traits_for_entry(entry)
            except Exception:
                traits = {}
        tier = entry.get("animation_tier") or capability.get("tier") or performance.get("tier") or "LEGACY"
        clip_count = len(capability.get("authoredClips", {}))
        # 0 authored clips = T-pose statue in a story; kabhi selectable nahi.
        # SBZ originals (legacy jaw pipeline) apni procedural animation rakhte hain.
        animatable = library != "quaternius" or clip_count > 0
        records.append({
            "id": capability_id or f"sbz_{_slug(entry.get('name') or blend_slug)}",
            "name": entry.get("name") or blend_slug,
            "library": library,
            "category": _category(entry.get("name") or blend_slug,
                                  capability.get("sourcePack", ""), library),
            "pack": capability.get("sourcePack", "SBZ Originals"),
            "license": capability.get("license", {}).get("name", "Project asset"),
            "license_status": capability.get("license", {}).get("status", "local"),
            "tier": tier,
            "status": ("ready" if exists and animatable
                       else "no_animation_clips" if exists else "missing_runtime_asset"),
            "status_label": ("Ready" if exists and animatable
                             else "No animations" if exists else "Runtime asset missing"),
            "selectable": exists and animatable,
            "reason": ("Available in the existing production renderer." if exists and animatable
                       else "Is character ke paas koi animation clip nahi — story mein static rahega."
                       if exists else "The manifest entry exists but its Blender runtime file is missing."),
            "blend": blend,
            "package": blend_slug,
            "thumbnail": f"/char3d-thumb/{blend_slug}",
            "source_format": "BLEND + GLB",
            "clip_count": len(capability.get("authoredClips", {})),
            "facial_ready": bool(performance.get("facial_ready")),
            "speech_mode": performance.get("speech_mode"),
            "lip_sync": performance.get("lip_sync"),
            "performance_label": performance.get("label"),
            "performance_warning": performance.get("warning"),
            "body_form": traits.get("form", "humanoid" if library == "sbz" else "unknown"),
            "pose_mode": traits.get("poseMode", "humanoid"),
            "ground_mode": traits.get("groundMode", "grounded"),
            "allowed_actions": traits.get("allowedActions", []),
        })
    return records


def _candidate_priority(candidate):
    rank = {"GLTF": 3, "FBX": 2, "BLEND": 1}.get(str(candidate.get("format") or "").upper(), 0)
    animated = 1 if candidate.get("animationClips") else 0
    licensed = 1 if candidate.get("license", {}).get("type") not in (None, "", "UNKNOWN") else 0
    return rank, animated, licensed


def _pending_records(integrated_keys):
    inventory = _read_json(INVENTORY_PATH, {})
    candidates = inventory.get("candidates", []) if isinstance(inventory, dict) else []
    selected = {}
    for candidate in candidates:
        name = str(candidate.get("name") or "").strip()
        key = _key(name)
        if not name or key in integrated_keys or key in COMPONENT_NAMES:
            continue
        current = selected.get(key)
        if current is None or _candidate_priority(candidate) > _candidate_priority(current):
            selected[key] = candidate

    records = []
    for key, candidate in selected.items():
        name = str(candidate.get("name") or key)
        pack = str(candidate.get("pack") or "Quaternius")
        license_info = candidate.get("license") or {}
        license_name = str(license_info.get("type") or "UNKNOWN")
        fmt = str(candidate.get("format") or "UNKNOWN").upper()
        has_skin = bool(candidate.get("armaturePresent") and candidate.get("skins"))
        if license_name == "UNKNOWN":
            status, label = "blocked_license", "License review"
            reason = "Local archive has no verified license record; production selection is disabled."
        elif fmt == "GLTF" and has_skin:
            status, label = "needs_rig_adapter", "Needs rig adapter"
            reason = candidate.get("rejectionReason") or "Animated source needs a skeleton mapping before production use."
        else:
            status, label = "needs_standardization", "Needs standardization"
            reason = candidate.get("rejectionReason") or "Source must be inspected and standardized in Blender."
        source = str(candidate.get("sourceFile") or "")
        records.append({
            "id": f"quaternius_{_slug(name)}",
            "name": name.replace("_", " "),
            "library": "quaternius",
            "category": _category(name, pack),
            "pack": pack.split("-2026", 1)[0].rstrip("-"),
            "license": license_name,
            "license_status": "blocked" if license_name == "UNKNOWN" else "verified",
            "tier": "UNVALIDATED",
            "status": status,
            "status_label": label,
            "selectable": False,
            "reason": reason,
            "blend": "",
            "package": "",
            "thumbnail": "",
            "source": _relative(source),
            "source_format": fmt,
            "clip_count": len(candidate.get("animationClips") or []),
            "facial_ready": False,
        })
    return records


def catalog():
    ready = _ready_records()
    integrated_keys = set()
    for item in ready:
        if item["library"] != "quaternius":
            continue
        integrated_keys.add(_key(item["name"]))
        integrated_keys.add(_key(str(item["name"]).removeprefix("Quaternius ")))
        integrated_keys.add(_key(str(item["id"]).removeprefix("quaternius_")))
    integrated_keys.update({"casual2", "casualhoodie"})
    pending = _pending_records(integrated_keys)
    characters = sorted(ready + pending,
                        key=lambda item: (item["library"] != "sbz", not item["selectable"],
                                          item["category"], item["name"].casefold()))
    sbz = [item for item in characters if item["library"] == "sbz"]
    quaternius = [item for item in characters if item["library"] == "quaternius"]
    return {
        "schema_version": SCHEMA_VERSION,
        "summary": {
            "total": len(characters),
            "sbz": len(sbz),
            "quaternius": len(quaternius),
            "selectable": sum(1 for item in characters if item["selectable"]),
            "quaternius_ready": sum(1 for item in quaternius if item["selectable"]),
            "quaternius_pending": sum(1 for item in quaternius if not item["selectable"]),
            "license_blocked": sum(1 for item in quaternius if item["status"] == "blocked_license"),
        },
        "libraries": [
            {"id": "sbz", "label": "SBZ Originals", "count": len(sbz)},
            {"id": "quaternius", "label": "Quaternius Library", "count": len(quaternius)},
        ],
        "categories": {
            "sbz": [{"id": "originals", "label": "Originals"}],
            "quaternius": [
                {"id": "humans", "label": "Humans"},
                {"id": "pirates", "label": "Pirates"},
                {"id": "space", "label": "Space"},
                {"id": "zombie", "label": "Zombie"},
                {"id": "monsters", "label": "Monsters"},
                {"id": "animals", "label": "Animals"},
            ],
        },
        "characters": characters,
    }


def selectable_metadata():
    """Metadata keyed by the legacy Blender package slug."""
    return {item["package"].lower(): item for item in catalog()["characters"]
            if item.get("selectable") and item.get("package")}
