"""
Tier 1 Costumes — character ke texture par color/palette badlo (tint + hue/sat/value).
Pure-data presets (app + Blender dono import kar sakte). apply() sirf Blender ke andar
chalta (bpy).  Single-material characters par reliable — outfit ka rang/mood badalta.

Node chain (Base Color se pehle inject): texture -> HueSatValue -> Mix(COLOR tint) -> BSDF.
Har preset: {group, label, hue?, sat?, val?, tint?(rgb), fac?, blend?}
"""

# groups UI mein optgroup ban'te hain
COSTUMES = {
    "default": {"group": "—", "label": "Default (asli)", "tint": None},

    # ---- Basic colors ----
    "red":    {"group": "Colors", "label": "🔴 Red",    "tint": (0.85, 0.10, 0.10), "fac": 0.7, "blend": "COLOR", "sat": 1.15},
    "blue":   {"group": "Colors", "label": "🔵 Blue",   "tint": (0.12, 0.28, 0.88), "fac": 0.7, "blend": "COLOR", "sat": 1.15},
    "green":  {"group": "Colors", "label": "🟢 Green",  "tint": (0.14, 0.64, 0.20), "fac": 0.7, "blend": "COLOR", "sat": 1.15},
    "purple": {"group": "Colors", "label": "🟣 Purple", "tint": (0.46, 0.16, 0.74), "fac": 0.7, "blend": "COLOR", "sat": 1.15},
    "pink":   {"group": "Colors", "label": "🩷 Pink",   "tint": (0.94, 0.36, 0.64), "fac": 0.65, "blend": "COLOR", "sat": 1.1},
    "orange": {"group": "Colors", "label": "🟠 Orange", "tint": (0.95, 0.48, 0.10), "fac": 0.68, "blend": "COLOR", "sat": 1.2},
    "cyan":   {"group": "Colors", "label": "🩵 Cyan",   "tint": (0.12, 0.72, 0.82), "fac": 0.68, "blend": "COLOR", "sat": 1.15},
    "gold":   {"group": "Colors", "label": "🟡 Gold / Royal", "tint": (0.96, 0.72, 0.16), "fac": 0.62, "blend": "COLOR", "val": 1.1, "sat": 1.2},

    # ---- Team colors (strong, jerseys/uniform) ----
    "team_green":  {"group": "Team", "label": "💚 Green Team",  "tint": (0.10, 0.60, 0.16), "fac": 0.82, "blend": "COLOR", "sat": 1.3},
    "team_blue":   {"group": "Team", "label": "💙 Blue Team",   "tint": (0.08, 0.24, 0.92), "fac": 0.82, "blend": "COLOR", "sat": 1.3},
    "team_red":    {"group": "Team", "label": "❤️ Red Team",    "tint": (0.90, 0.08, 0.08), "fac": 0.82, "blend": "COLOR", "sat": 1.3},
    "team_yellow": {"group": "Team", "label": "💛 Yellow Team", "tint": (0.96, 0.80, 0.06), "fac": 0.8, "blend": "COLOR", "sat": 1.35, "val": 1.05},
    "team_black":  {"group": "Team", "label": "🖤 Black Team",  "sat": 0.35, "val": 0.5, "tint": (0.10, 0.10, 0.12), "fac": 0.4, "blend": "COLOR"},

    # ---- Seasonal / Festive ----
    "eid":       {"group": "Seasonal", "label": "🌙 Eid (green-gold)", "tint": (0.16, 0.62, 0.28), "fac": 0.6, "blend": "COLOR", "sat": 1.25, "val": 1.08},
    "azadi":     {"group": "Seasonal", "label": "🇵🇰 Azadi (14 Aug)", "tint": (0.05, 0.55, 0.18), "fac": 0.78, "blend": "COLOR", "sat": 1.3, "val": 1.05},
    "winter":    {"group": "Seasonal", "label": "❄️ Winter (frosty)", "tint": (0.55, 0.72, 0.95), "fac": 0.5, "blend": "COLOR", "sat": 0.8, "val": 1.12},
    "summer":    {"group": "Seasonal", "label": "☀️ Summer (bright)", "tint": (0.98, 0.62, 0.15), "fac": 0.4, "blend": "COLOR", "sat": 1.35, "val": 1.1},
    "autumn":    {"group": "Seasonal", "label": "🍂 Autumn (warm)", "tint": (0.80, 0.40, 0.10), "fac": 0.58, "blend": "COLOR", "sat": 1.15, "val": 0.96},
    "spring":    {"group": "Seasonal", "label": "🌸 Spring (fresh)", "tint": (0.55, 0.85, 0.45), "fac": 0.42, "blend": "COLOR", "sat": 1.2, "val": 1.1},
    "christmas": {"group": "Seasonal", "label": "🎄 Christmas (red)", "tint": (0.85, 0.10, 0.14), "fac": 0.65, "blend": "COLOR", "sat": 1.3, "val": 1.02},
    "halloween": {"group": "Seasonal", "label": "🎃 Halloween (spooky)", "tint": (0.92, 0.42, 0.05), "fac": 0.55, "blend": "COLOR", "sat": 1.25, "val": 0.68},

    # ---- Mood / Style ----
    "villain": {"group": "Mood", "label": "😈 Villain (dark)", "sat": 0.75, "val": 0.62, "tint": (0.30, 0.12, 0.38), "fac": 0.35, "blend": "COLOR"},
    "party":   {"group": "Mood", "label": "🎉 Party (vivid)", "sat": 1.5, "val": 1.06, "tint": None},
    "pastel":  {"group": "Mood", "label": "🎨 Pastel (soft)", "sat": 0.55, "val": 1.16, "tint": None},
    "neon":    {"group": "Mood", "label": "💡 Neon (glow)", "sat": 1.85, "val": 1.12, "tint": None},
    "vintage": {"group": "Mood", "label": "📽️ Vintage (sepia)", "sat": 0.42, "val": 1.0, "tint": (0.78, 0.62, 0.42), "fac": 0.42, "blend": "COLOR"},
    "night":   {"group": "Mood", "label": "🌃 Night (cool)", "sat": 0.8, "val": 0.68, "tint": (0.30, 0.42, 0.72), "fac": 0.4, "blend": "COLOR"},
    "mono":    {"group": "Mood", "label": "⚫ Black & White", "sat": 0.0, "val": 1.02, "tint": None},
}

# UI order (groups)
_GROUP_ORDER = ["—", "Colors", "Team", "Seasonal", "Mood"]


def list_costumes():
    items = [{"id": k, "label": v["label"], "group": v.get("group", "Mood")}
             for k, v in COSTUMES.items()]
    items.sort(key=lambda x: (_GROUP_ORDER.index(x["group"]) if x["group"] in _GROUP_ORDER else 99))
    return items


def apply(char, name):
    """Blender ke andar: char (mesh) ke har material mein costume color-chain inject."""
    import bpy  # sirf Blender mein
    p = COSTUMES.get(name)
    if not p or name in ("", "default", "none"):
        return False
    changed = False
    for mat in list(char.data.materials):
        if not mat:
            continue
        if not mat.use_nodes:
            mat.use_nodes = True
        nt = mat.node_tree
        bsdf = next((n for n in nt.nodes if n.type == 'BSDF_PRINCIPLED'), None)
        if not bsdf:
            continue
        inp = bsdf.inputs.get("Base Color")
        if inp is None:
            continue
        # source socket (texture ya ek RGB node se default color)
        if inp.is_linked:
            last = inp.links[0].from_socket
        else:
            rgb = nt.nodes.new("ShaderNodeRGB")
            rgb.outputs[0].default_value = inp.default_value
            last = rgb.outputs[0]

        # 1) Hue / Saturation / Value
        if any(k in p for k in ("hue", "sat", "val")):
            hsv = nt.nodes.new("ShaderNodeHueSaturation")
            hsv.inputs["Hue"].default_value = p.get("hue", 0.5)
            hsv.inputs["Saturation"].default_value = p.get("sat", 1.0)
            hsv.inputs["Value"].default_value = p.get("val", 1.0)
            nt.links.new(last, hsv.inputs["Color"])
            last = hsv.outputs["Color"]

        # 2) Color tint mix (COLOR blend = hue badle, detail rahe)
        if p.get("tint"):
            mix = None
            try:
                mix = nt.nodes.new("ShaderNodeMix")
                mix.data_type = 'RGBA'
                mix.blend_type = p.get("blend", "COLOR")
                mix.inputs["Factor"].default_value = p.get("fac", 0.5)
                nt.links.new(last, mix.inputs["A"])
                mix.inputs["B"].default_value = (*p["tint"], 1.0)
                nt.links.new(mix.outputs["Result"], inp)
            except Exception:
                if mix:
                    nt.nodes.remove(mix)
                mix = nt.nodes.new("ShaderNodeMixRGB")
                mix.blend_type = p.get("blend", "COLOR")
                mix.inputs["Fac"].default_value = p.get("fac", 0.5)
                nt.links.new(last, mix.inputs["Color1"])
                mix.inputs["Color2"].default_value = (*p["tint"], 1.0)
                nt.links.new(mix.outputs["Color"], inp)
        else:
            nt.links.new(last, inp)
        changed = True
    return changed
