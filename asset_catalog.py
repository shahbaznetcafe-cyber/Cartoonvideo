"""Read-only catalog of integrated and staged Quaternius scene assets."""
from __future__ import annotations

import re
from functools import lru_cache
from pathlib import Path

import config
import scene_assets


ROOT = Path(config.BASE_DIR)
WORK = ROOT / "work/quaternius"
WEAPONS = {"axe", "guitar", "knife", "pistol", "rifle", "shotgun", "smg", "spear",
           "woodenbat_barbed", "woodenbat_saw"}


def _slug(value):
    return re.sub(r"[^a-z0-9]+", "_", str(value).lower()).strip("_")


def _record(pack, name, category, path, *, status="available", license_status="verified"):
    return {"id": f"{_slug(pack)}_{_slug(name)}", "name": name.replace("_", " "),
            "pack": pack, "category": category, "status": status,
            "status_label": "Integrated" if status == "integrated" else
                            "License review" if license_status == "blocked" else "Available asset",
            "license_status": license_status,
            "path": str(path.relative_to(ROOT)).replace("\\", "/") if path.is_absolute() else str(path),
            "production_selectable": status == "integrated"}


def _pack_root(marker):
    return next((path for path in WORK.iterdir() if marker in path.name), None) if WORK.exists() else None


@lru_cache(maxsize=1)
def catalog():
    records = []
    for name in ("market", "kitchen", "garden"):
        path = ROOT / f"threejs_render/assets/env/{name}.glb"
        if path.is_file():
            records.append(_record("SBZ Environments", name.title(), "backgrounds", path, status="integrated"))

    # Composed worlds are production-ready recipes assembled from a few local
    # GLTF assets at render time.  This keeps them lightweight and lets story
    # keywords choose the right location without baking duplicate scene files.
    for background in scene_assets.composed_backgrounds():
        records.append({
            "id": background["id"], "name": background["name"],
            "pack": background["pack"], "category": "backgrounds",
            "status": "integrated", "status_label": "Production ready",
            "license_status": "verified", "path": f"composed://{background['id']}",
            "production_selectable": True, "description": background["description"],
        })

    nature = _pack_root("Stylized Nature MegaKit")
    if nature:
        for path in sorted(nature.rglob("*.gltf")):
            records.append(_record("Stylized Nature", path.stem, "backgrounds", path))

    pirate = _pack_root("Pirate Kit")
    if pirate:
        for path in sorted(pirate.rglob("*.gltf")):
            name = path.stem
            if name.startswith(("Characters_", "Enemy_")):
                continue
            category = ("backgrounds" if name.startswith("Environment_") else
                        "vehicles" if name.startswith("Ship_") else
                        "weapons" if name.startswith("Weapon_") else "props")
            records.append(_record("Pirate Kit", name, category, path, license_status="blocked"))

    space = _pack_root("Ultimate Space Kit")
    if space:
        for path in sorted(space.rglob("*.gltf")):
            name = path.stem
            if name.startswith(("Astronaut_", "Mech_", "Enemy_")):
                continue
            category = "vehicles" if name.startswith(("Rover_", "Spaceship_")) else \
                       "props" if name.startswith("Pickup_") else "backgrounds"
            records.append(_record("Ultimate Space Kit", name, category, path))

    zombie = _pack_root("Zombie Apocalypse Kit")
    if zombie:
        for path in sorted(zombie.rglob("*.gltf")):
            name = path.stem
            key = name.lower()
            if name.startswith(("Characters_", "Zombie_")):
                continue
            if name.startswith("Vehicle_"):
                category = "vehicles"
            elif key in WEAPONS:
                category = "weapons"
            elif name.startswith(("Street", "Traffic", "Container", "WaterTower", "TownSign", "FireHydrant")):
                category = "backgrounds"
            else:
                category = "props"
            records.append(_record("Zombie Apocalypse Kit", name, category, path))

    cars = _pack_root("Realistic Car Pack")
    if cars:
        seen = set()
        for path in sorted(cars.rglob("*.blend")):
            if path.stem.lower() in seen:
                continue
            seen.add(path.stem.lower())
            records.append(_record("Realistic Car Pack", path.stem, "vehicles", path))

    records.sort(key=lambda item: (item["category"], item["pack"], item["name"].casefold()))
    categories = ("backgrounds", "props", "vehicles", "weapons")
    return {"schema_version": 1,
            "summary": {category: sum(item["category"] == category for item in records)
                        for category in categories},
            "integrated": sum(item["production_selectable"] for item in records),
            "total": len(records), "assets": records}
