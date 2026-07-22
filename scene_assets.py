"""Safe, data-driven scene dressing selection for the Three.js renderer.

Only locally verified, non-character source assets are exposed here.  The
source files stay in the user's Quaternius inventory; the renderer serves them
read-only during a render, so textures and materials remain intact without
copying or bulk-converting the catalogue.
"""
from __future__ import annotations

from pathlib import Path

import config


ROOT = Path(config.BASE_DIR)
NATURE = ROOT / "work/quaternius/Stylized Nature MegaKit[Standard]/glTF"
SPACE = ROOT / "work/quaternius/Ultimate Space Kit - March 2023-20260715T070157Z-1-001/Ultimate Space Kit - March 2023/Environment/GLTF"
ZOMBIE = ROOT / "work/quaternius/Zombie Apocalypse Kit - March 2024-20260715T065801Z-1-001/Zombie Apocalypse Kit - March 2024/Environment/glTF"
PIRATE = ROOT / "work/quaternius/Pirate Kit - Nov 2023-20260715T065953Z-1-001/Pirate Kit - Nov 2023/glTF"


# Reusable, layered worlds made from the local 3D packs.  They are recipes,
# not baked scenes: a render loads just the small set of assets it needs and
# can still place story props and characters naturally within the world.
COMPOSED_BACKGROUNDS = (
    {"id": "forest_story_path", "name": "Forest Story Path", "preset": "forest",
     "variant": "forest_path", "pack": "Stylized Nature MegaKit",
     "description": "Tree-lined path with flowers, rocks and foreground foliage."},
    {"id": "forest_blooming_clearing", "name": "Blooming Forest Clearing", "preset": "forest",
     "variant": "blooming_farm", "pack": "Stylized Nature MegaKit",
     "description": "Warm flower clearing for gentle discoveries and dialogue."},
    {"id": "pirate_harbor", "name": "Pirate Harbor", "preset": "pirate",
     "variant": "pirate_harbor", "pack": "Quaternius Pirate Kit",
     "description": "Dock, ship, palms, cliff and barrels with a deep sea-side composition."},
    {"id": "pirate_treasure_cove", "name": "Treasure Cove", "preset": "pirate",
     "variant": "treasure_cove", "pack": "Quaternius Pirate Kit",
     "description": "Hidden cove with treasure chest, palms, rocks and a broken dock."},
    {"id": "space_outpost", "name": "Planetary Outpost", "preset": "space",
     "variant": "space_outpost", "pack": "Ultimate Space Kit",
     "description": "Science-fiction base, dome, solar panels and distant planet."},
    {"id": "apocalypse_street", "name": "Ruined City Street", "preset": "apocalypse",
     "variant": "apocalypse_street", "pack": "Zombie Apocalypse Kit",
     "description": "Cracked road, containers, streetlights and barriers for action beats."},
)


def composed_backgrounds():
    """Return UI-friendly production background recipes without duplicating assets."""
    return [dict(item, status="integrated", production_selectable=True) for item in COMPOSED_BACKGROUNDS]


def _asset(asset_id, root, filename, *, target_height, position, rotation_y=0.0):
    """Create a renderer-safe asset declaration only when its source exists."""
    source = root / filename
    if not source.is_file():
        return None
    return {
        "id": asset_id,
        "source": str(source),
        "targetHeight": float(target_height),
        "position": [float(position[0]), float(position[1]), float(position[2])],
        "rotationY": float(rotation_y),
        "readOnlySource": True,
    }


def _available(candidates):
    return [item for item in candidates if item is not None]


def dressings_for(environment, scene_index=0):
    """Return a deterministic, layered set of real local 3D assets.

    Each recipe has foreground, midground and background scale references so
    the generated video reads as a location, rather than a flat stage.
    """
    environment = environment or {}
    preset = str(environment.get("preset") or "sunny").lower()
    variant = str(environment.get("variant") or "").lower()
    phase = int(scene_index or 0) % 3

    if preset in {"forest", "sunny", "storm", "mud"} or "farm" in variant:
        tree = ("CommonTree_1.gltf", "CommonTree_3.gltf", "Pine_2.gltf")[phase]
        return _available([
            _asset("nature_back_tree", NATURE, tree, target_height=4.4, position=(-3.55, 0, -2.45), rotation_y=.22),
            _asset("nature_side_tree", NATURE, "CommonTree_4.gltf", target_height=3.25, position=(3.4, 0, -1.85), rotation_y=-.22),
            _asset("nature_bush", NATURE, "Bush_Common_Flowers.gltf", target_height=.70, position=(2.55, 0, -.45), rotation_y=-.35),
            _asset("nature_flowers", NATURE, "Flower_3_Group.gltf", target_height=.46, position=(-1.85, 0, .42), rotation_y=.1),
            _asset("nature_rockpath", NATURE, "RockPath_Round_Wide.gltf", target_height=.13, position=(.35, 0, 1.05), rotation_y=.04),
            _asset("nature_foreground_fern", NATURE, "Fern_1.gltf", target_height=.58, position=(-3.05, 0, 1.35), rotation_y=.18),
        ])

    if preset in {"space", "sci_fi"} or any(word in variant for word in ("space", "planet", "rocket")):
        return _available([
            _asset("space_base", SPACE, "Base_Large.gltf", target_height=.58, position=(0, 0, -2.05), rotation_y=0),
            _asset("space_building", SPACE, "Building_L.gltf", target_height=2.75, position=(-2.8, 0, -2.15), rotation_y=.18),
            _asset("space_dome", SPACE, "GeodesicDome.gltf", target_height=1.7, position=(2.5, 0, -1.75), rotation_y=-.26),
            _asset("space_planet", SPACE, "Planet_3.gltf", target_height=2.3, position=(3.7, 2.65, -5.5), rotation_y=.08),
            _asset("space_solar", SPACE, "SolarPanel_Ground.gltf", target_height=.82, position=(-1.5, 0, .45), rotation_y=.14),
            _asset("space_rock", SPACE, "Rock_Large_2.gltf", target_height=.56, position=(3.05, 0, .72), rotation_y=-.18),
        ])

    if preset in {"pirate", "island", "beach"} or any(word in variant for word in ("pirate", "island", "dock", "treasure", "cove")):
        treasure = "Prop_Chest_Gold.gltf" if "treasure" in variant or phase == 1 else "Prop_Chest_Closed.gltf"
        dock = "Environment_Dock_Broken.gltf" if "cove" in variant else "Environment_Dock.gltf"
        return _available([
            _asset("pirate_ship", PIRATE, "Ship_Large.gltf", target_height=3.9, position=(-3.8, 0, -3.7), rotation_y=.18),
            _asset("pirate_dock", PIRATE, dock, target_height=1.3, position=(-1.9, 0, -1.55), rotation_y=.08),
            _asset("pirate_cliff", PIRATE, "Environment_Cliff2.gltf", target_height=3.35, position=(3.55, 0, -2.85), rotation_y=-.2),
            _asset("pirate_palm", PIRATE, "Environment_PalmTree_2.gltf", target_height=4.15, position=(-3.25, 0, .35), rotation_y=.24),
            _asset("pirate_chest", PIRATE, treasure, target_height=.62, position=(1.35, 0, .55), rotation_y=.12),
            _asset("pirate_barrel", PIRATE, "Prop_Barrel.gltf", target_height=.66, position=(2.12, 0, .44), rotation_y=.16),
        ])

    if preset in {"apocalypse", "city", "urban"} or any(word in variant for word in ("apocalypse", "zombie", "city", "street")):
        return _available([
            _asset("city_street", ZOMBIE, "Street_Straight_Crack1.gltf", target_height=.10, position=(0, 0, -1.55), rotation_y=0),
            _asset("city_container", ZOMBIE, "Container_Green.gltf", target_height=1.32, position=(-2.65, 0, -1.85), rotation_y=.12),
            _asset("city_light", ZOMBIE, "StreetLights.gltf", target_height=3.05, position=(2.85, 0, -2.2), rotation_y=-.12),
            _asset("city_barrier", ZOMBIE, "TrafficBarrier_1.gltf", target_height=.64, position=(1.25, 0, .56), rotation_y=.1),
            _asset("city_tower", ZOMBIE, "WaterTower.gltf", target_height=3.8, position=(3.85, 0, -4.1), rotation_y=0),
            _asset("city_barrel", ZOMBIE, "Barrel.gltf", target_height=.62, position=(-2.25, 0, .55), rotation_y=.18),
        ])
    return []


def renderer_props(environment, scene_index=0):
    """Convert static asset dressings into existing renderer prop records."""
    props = []
    for asset in dressings_for(environment, scene_index):
        props.append({
            "id": f"dressing_{asset['id']}", "type": "dressing",
            "asset": asset,
            "position": asset["position"],
            "stateStart": {"x": asset["position"][0], "y": asset["position"][1],
                           "z": asset["position"][2], "rotationY": asset["rotationY"],
                           "growth": 1.0, "open": 0.0, "glow": 0.0},
            "stateEnd": {"x": asset["position"][0], "y": asset["position"][1],
                         "z": asset["position"][2], "rotationY": asset["rotationY"],
                         "growth": 1.0, "open": 0.0, "glow": 0.0},
            "consequence": "static_environment_dressing",
            "assetRole": "environment_dressing",
        })
    return props
