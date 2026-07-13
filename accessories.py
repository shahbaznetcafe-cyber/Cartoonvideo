"""
Tier 2 Accessories — PROCEDURAL props (Blender primitives se), koi download/attribution nahi.
3 slots:
  - head : sar ke top par (crown, hats, halo, horns, bow, flower)
  - face : chehre ke saamne (glasses, sunglasses, moustache) — front(-Y) par
  - hand : haath mein (sword, wand, mic) — arm_R bone se parent (gesture ke saath chale)

build(char, rig, name): slot ke hisab se position + Rig/bone se parent (transform follow).
"""

ACCESSORIES = {
    "none":       {"slot": "-", "group": "—", "label": "Koi nahi"},
    # ---- head ----
    "crown":      {"slot": "head", "group": "Sar", "label": "👑 Crown (taj)", "type": "crown", "color": (0.95, 0.72, 0.12)},
    "party_hat":  {"slot": "head", "group": "Sar", "label": "🎉 Party Hat", "type": "cone", "color": (0.95, 0.20, 0.45), "h": 2.2, "r": 0.85},
    "wizard_hat": {"slot": "head", "group": "Sar", "label": "🧙 Wizard Hat", "type": "wizard", "color": (0.30, 0.16, 0.62)},
    "top_hat":    {"slot": "head", "group": "Sar", "label": "🎩 Top Hat", "type": "tophat", "color": (0.06, 0.06, 0.08)},
    "cap":        {"slot": "head", "group": "Sar", "label": "🧢 Cap", "type": "cap", "color": (0.85, 0.14, 0.14)},
    "halo":       {"slot": "head", "group": "Sar", "label": "😇 Halo", "type": "halo", "color": (1.0, 0.85, 0.25), "emit": True},
    "horns":      {"slot": "head", "group": "Sar", "label": "😈 Horns", "type": "horns", "color": (0.55, 0.08, 0.08)},
    "bow":        {"slot": "head", "group": "Sar", "label": "🎀 Bow", "type": "bow", "color": (0.95, 0.35, 0.6)},
    "flower":     {"slot": "head", "group": "Sar", "label": "🌸 Flower", "type": "flower", "color": (0.98, 0.45, 0.7)},
    # ---- face ----
    "glasses":    {"slot": "face", "group": "Chehra", "label": "🤓 Glasses", "type": "glasses", "color": (0.05, 0.05, 0.06)},
    "sunglasses": {"slot": "face", "group": "Chehra", "label": "🕶️ Sunglasses", "type": "sunglasses", "color": (0.02, 0.02, 0.03)},
    "moustache":  {"slot": "face", "group": "Chehra", "label": "👨 Moustache", "type": "moustache", "color": (0.15, 0.09, 0.05)},
}

# haath mein pakde jaane wale (alag dropdown)
HELD = {
    "none":   {"slot": "hand", "group": "—", "label": "Koi nahi"},
    "sword":  {"slot": "hand", "group": "Haath", "label": "⚔️ Sword", "type": "sword", "color": (0.75, 0.77, 0.82)},
    "wand":   {"slot": "hand", "group": "Haath", "label": "🪄 Wand", "type": "wand", "color": (0.95, 0.80, 0.25), "emit": True},
    "mic":    {"slot": "hand", "group": "Haath", "label": "🎤 Mic", "type": "mic", "color": (0.08, 0.08, 0.10)},
    "staff":  {"slot": "hand", "group": "Haath", "label": "🔱 Magic Staff", "type": "staff", "color": (0.45, 0.30, 0.75), "emit": True},
    "balloon":{"slot": "hand", "group": "Haath", "label": "🎈 Balloon", "type": "balloon", "color": (0.90, 0.20, 0.30)},
}

_ALL = {**ACCESSORIES, **HELD}


def list_accessories():
    """Worn props (head+face) — pehla dropdown."""
    return [{"id": k, "label": v["label"], "group": v.get("group", "Sar")} for k, v in ACCESSORIES.items()]


def list_held():
    """Hand items — doosra dropdown."""
    return [{"id": k, "label": v["label"], "group": v.get("group", "Haath")} for k, v in HELD.items()]


def build(char, rig, name):
    """Blender ke andar: char par accessory prop banao (slot ke hisab se)."""
    import bpy, math, mathutils
    spec = _ALL.get(name)
    if not spec or name in ("", "none", "-"):
        return False

    bb = [char.matrix_world @ mathutils.Vector(c) for c in char.bound_box]
    xs = [v.x for v in bb]; ys = [v.y for v in bb]; zs = [v.z for v in bb]
    cx = (min(xs)+max(xs))/2; cy = (min(ys)+max(ys))/2
    top = max(zs); bot = min(zs); W = max(xs)-min(xs); H = max(zs)-min(zs)
    front = min(ys)                        # -Y = camera/chehra side
    hr = max(W*0.30, H*0.14)
    # ASLI eye-level (front vertices se) — mane/horn/ears ki height se gumraah na ho
    face_z = top - H*0.16
    try:
        fv = [char.matrix_world @ v.co for v in char.data.vertices]
        ymin2 = min(v.y for v in fv); yr = (max(v.y for v in fv) - ymin2) or 1.0
        fz = sorted(v.z for v in fv if v.y <= ymin2 + yr*0.16)   # aage ke 16% (chehra)
        if fz:
            face_z = fz[int(len(fz)*0.66)]                        # upper-front ~ aankhein
    except Exception:
        pass

    created = []

    def cyl(r, d, loc, rot=(0, 0, 0)):
        bpy.ops.mesh.primitive_cylinder_add(radius=r, depth=d, location=loc, rotation=rot, vertices=20)
        return bpy.context.active_object

    def box(sx, sy, sz, loc, rot=(0, 0, 0)):
        bpy.ops.mesh.primitive_cube_add(size=1, location=loc, rotation=rot)
        o = bpy.context.active_object; o.scale = (sx, sy, sz); return o

    def cone(r1, r2, d, loc, rot=(0, 0, 0)):
        bpy.ops.mesh.primitive_cone_add(radius1=r1, radius2=r2, depth=d, location=loc, rotation=rot, vertices=18)
        return bpy.context.active_object

    def torus(maj, minr, loc, rot=(0, 0, 0)):
        bpy.ops.mesh.primitive_torus_add(major_radius=maj, minor_radius=minr, location=loc, rotation=rot,
                                         major_segments=20, minor_segments=8)
        return bpy.context.active_object

    def sphere(r, loc):
        bpy.ops.mesh.primitive_uv_sphere_add(radius=r, location=loc, segments=16, ring_count=10)
        return bpy.context.active_object

    t = spec["type"]; col = spec.get("color", (0.9, 0.9, 0.9))
    slot = spec["slot"]

    # ---------------- HEAD ----------------
    if t == "crown":
        created.append(torus(hr*0.85, hr*0.16, (cx, cy, top - hr*0.4)))
        for i in range(6):
            a = i/6.0*2*math.pi
            created.append(cone(hr*0.16, 0.0, hr*0.5, (cx+math.cos(a)*hr*0.85, cy+math.sin(a)*hr*0.85, top - hr*0.15)))
    elif t == "cone":
        d = hr*spec.get("h", 2.2); z0 = top - hr*0.2
        created.append(cone(hr*spec.get("r", 0.85), 0.0, d, (cx, cy, z0 + d*0.45)))
    elif t == "wizard":
        d = hr*2.9; z0 = top - hr*0.2
        created.append(cone(hr*0.9, 0.0, d, (cx, cy, z0 + d*0.42)))
        created.append(torus(hr*1.05, hr*0.10, (cx, cy, z0 + hr*0.05)))
    elif t == "tophat":
        z0 = top - hr*0.25
        created.append(cyl(hr*0.72, hr*1.5, (cx, cy, z0 + hr*0.75)))
        created.append(cyl(hr*1.15, hr*0.10, (cx, cy, z0 + hr*0.02)))
    elif t == "cap":
        dome = sphere(hr*0.85, (cx, cy, top)); dome.scale = (1, 1, 0.6); created.append(dome)
        created.append(cyl(hr*0.55, hr*0.06, (cx, front - hr*0.5, top - hr*0.05)))
    elif t == "halo":
        created.append(torus(hr*0.7, hr*0.09, (cx, cy, top + hr*0.32)))
    elif t == "horns":
        for sgn in (-1, 1):
            created.append(cone(hr*0.22, 0.0, hr*0.8, (cx+sgn*hr*0.5, cy, top-hr*0.02),
                                rot=(math.radians(sgn*20), math.radians(sgn*-8), 0)))
    elif t == "bow":
        for sgn in (-1, 1):
            created.append(cone(hr*0.42, 0.0, hr*0.7, (cx+sgn*hr*0.42, cy, top+hr*0.1), rot=(0, math.radians(sgn*90), 0)))
        created.append(sphere(hr*0.14, (cx, cy, top+hr*0.1)))
    elif t == "flower":
        created.append(sphere(hr*0.16, (cx+hr*0.7, cy-hr*0.2, top-hr*0.1)))
        for i in range(5):
            a = i/5.0*2*math.pi
            created.append(sphere(hr*0.13, (cx+hr*0.7+math.cos(a)*hr*0.22, cy-hr*0.2, top-hr*0.1+math.sin(a)*hr*0.22)))

    # ---------------- FACE (front -Y) ----------------
    elif t in ("glasses", "sunglasses"):
        eye_z = face_z; yf = front + hr*0.02      # asli eye-level (front geometry se)
        lens_r = hr*0.34
        if t == "sunglasses":
            for sgn in (-1, 1):
                l = box(lens_r*1.0, hr*0.05, lens_r*0.7, (cx+sgn*lens_r*1.15, yf, eye_z))
                created.append(l)
        else:
            for sgn in (-1, 1):
                created.append(torus(lens_r, hr*0.05, (cx+sgn*lens_r*1.15, yf, eye_z), rot=(math.radians(90), 0, 0)))
        created.append(cyl(hr*0.04, lens_r*0.9, (cx, yf, eye_z), rot=(0, math.radians(90), 0)))   # bridge
        # temples (arms) peeche
        for sgn in (-1, 1):
            created.append(cyl(hr*0.03, hr*0.8, (cx+sgn*lens_r*2.0, cy+hr*0.1, eye_z), rot=(math.radians(90), 0, 0)))
    elif t == "moustache":
        m_z = face_z - H*0.07; yf = front + hr*0.02   # aankhon ke thoda neeche (mooch)
        for sgn in (-1, 1):
            created.append(cone(hr*0.10, hr*0.02, hr*0.5, (cx+sgn*hr*0.18, yf, m_z), rot=(0, math.radians(sgn*70), 0)))

    # ---------------- HAND (arm_R) ----------------
    elif slot == "hand":
        L = H*0.5
        if t == "sword":
            created.append(box(L*0.05, L*0.05, L*0.72, (0, 0, L*0.36)))         # blade up
            created.append(box(L*0.28, L*0.06, L*0.04, (0, 0, 0)))              # guard
            created.append(cyl(L*0.04, L*0.16, (0, 0, -L*0.09)))               # handle
        elif t == "wand":
            created.append(cyl(L*0.03, L*0.55, (0, 0, L*0.27)))
            created.append(sphere(L*0.09, (0, 0, L*0.58)))                     # glowing tip
        elif t == "staff":
            created.append(cyl(L*0.04, L*0.9, (0, 0, L*0.45)))
            created.append(torus(L*0.13, L*0.04, (0, 0, L*0.95)))
            created.append(sphere(L*0.10, (0, 0, L*0.95)))
        elif t == "mic":
            created.append(cyl(L*0.05, L*0.42, (0, 0, L*0.21)))
            created.append(sphere(L*0.11, (0, 0, L*0.48)))
        elif t == "balloon":
            created.append(cyl(L*0.012, L*0.7, (0, 0, L*0.35)))                # string
            b = sphere(L*0.22, (0, 0, L*0.92)); b.scale = (1, 1, 1.2); created.append(b)

    if not created:
        return False

    # join
    bpy.ops.object.select_all(action='DESELECT')
    for o in created:
        o.select_set(True)
    bpy.context.view_layer.objects.active = created[0]
    if len(created) > 1:
        bpy.ops.object.join()
    acc = bpy.context.view_layer.objects.active
    acc.name = "Accessory_" + name

    # material
    m = bpy.data.materials.new("acc"); m.use_nodes = True
    b = m.node_tree.nodes.get("Principled BSDF")
    if b:
        b.inputs["Base Color"].default_value = (*col, 1.0)
        try:
            b.inputs["Roughness"].default_value = 0.4
            if slot == "hand" and t in ("sword", "mic"):
                b.inputs["Metallic"].default_value = 0.8
        except Exception:
            pass
        if spec.get("emit"):
            try:
                b.inputs["Emission Color"].default_value = (*col, 1.0)
                b.inputs["Emission Strength"].default_value = 2.0
            except Exception:
                pass
    acc.data.materials.append(m)

    # ---- parent ----
    if slot == "hand":
        pb = rig.pose.bones.get("arm_R") or rig.pose.bones.get("arm_L")
        if pb:
            hand = rig.matrix_world @ pb.tail
            # item ko hand par le jao (blade thoda forward tilt) + bone se parent (gesture follow)
            acc.location = hand
            acc.rotation_euler = (math.radians(35), 0, 0)   # thoda aage jhuka
            bpy.context.view_layer.update()
            wm = acc.matrix_world.copy()
            acc.parent = rig; acc.parent_type = 'BONE'; acc.parent_bone = pb.name
            bpy.context.view_layer.update()
            acc.matrix_world = wm
            return True
    # head/face -> Rig object se parent (keep transform)
    acc.parent = rig
    acc.matrix_parent_inverse = rig.matrix_world.inverted()
    return True
