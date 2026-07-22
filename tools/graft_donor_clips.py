"""Graft baked animation clips from a donor glb onto clip-less sibling rigs.

The five STATIC Quaternius humans (casual/formal/medieval/scifi/soldier) share
the modular-human bone names with the animated 23-bone rigs, so donor channels
retarget by bone NAME. Channels for bones the target lacks are skipped, and a
small alias map bridges naming differences (Fist -> Hand wrist, Bone -> Root).

Usage:
    python tools/graft_donor_clips.py --donor quaternius_casual_male \
        quaternius_casual quaternius_formal quaternius_medieval \
        quaternius_scifi quaternius_soldier
"""
from __future__ import annotations

import argparse
import json
import struct
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CHARS = ROOT / "threejs_render" / "assets" / "chars"

# donor bone -> target bone; None = drop the channel entirely.
BONE_ALIASES = {
    "Bone": "Root",
    "Body": None,          # donor mesh-carrier helper; target has no equivalent
    "Fist.L": "Hand.L",
    "Fist.R": "Hand.R",
    "PoleTarget.L": None,  # IK helpers — motion is already baked into limbs
    "PoleTarget.R": None,
}


def load_glb(path):
    data = path.read_bytes()
    magic, version, _ = struct.unpack("<III", data[:12])
    assert magic == 0x46546C67, f"not a glb: {path}"
    jlen, jtype = struct.unpack("<II", data[12:20])
    assert jtype == 0x4E4F534A
    gltf = json.loads(data[20:20 + jlen])
    rest = data[20 + jlen:]
    binary = b""
    if rest:
        blen, btype = struct.unpack("<II", rest[:8])
        assert btype == 0x004E4942
        binary = rest[8:8 + blen]
    return gltf, bytearray(binary), version


def save_glb(path, gltf, binary, version):
    j = json.dumps(gltf, separators=(",", ":")).encode("utf-8")
    j += b" " * ((4 - len(j) % 4) % 4)
    b = bytes(binary)
    b += b"\x00" * ((4 - len(b) % 4) % 4)
    total = 12 + 8 + len(j) + 8 + len(b)
    out = struct.pack("<III", 0x46546C67, version, total)
    out += struct.pack("<II", len(j), 0x4E4F534A) + j
    out += struct.pack("<II", len(b), 0x004E4942) + b
    path.write_bytes(out)


def node_names(gltf):
    return {n.get("name"): i for i, n in enumerate(gltf.get("nodes", []))}


def copy_accessor(donor, donor_bin, target, target_bin, accessor_index, cache):
    """Copy one accessor + backing bufferView data into the target glb."""
    if accessor_index in cache:
        return cache[accessor_index]
    acc = dict(donor["accessors"][accessor_index])
    bv_index = acc.get("bufferView")
    if bv_index is not None:
        bv = dict(donor["bufferViews"][bv_index])
        start = bv.get("byteOffset", 0)
        chunk = bytes(donor_bin[start:start + bv["byteLength"]])
        pad = (4 - len(target_bin) % 4) % 4
        target_bin.extend(b"\x00" * pad)
        new_bv = {"buffer": 0, "byteOffset": len(target_bin),
                  "byteLength": bv["byteLength"]}
        if "byteStride" in bv:
            new_bv["byteStride"] = bv["byteStride"]
        target_bin.extend(chunk)
        target.setdefault("bufferViews", []).append(new_bv)
        acc["bufferView"] = len(target["bufferViews"]) - 1
    target.setdefault("accessors", []).append(acc)
    new_index = len(target["accessors"]) - 1
    cache[accessor_index] = new_index
    return new_index


def graft(donor_slug, target_slug):
    donor_path = CHARS / f"{donor_slug}.glb"
    target_path = CHARS / f"{target_slug}.glb"
    donor, donor_bin, _ = load_glb(donor_path)
    target, target_bin, version = load_glb(target_path)
    if target.get("animations"):
        return f"{target_slug}: already has {len(target['animations'])} clips, skipped"
    donor_nodes = {i: n.get("name") for i, n in enumerate(donor.get("nodes", []))}
    target_by_name = node_names(target)

    grafted = 0
    for anim in donor.get("animations", []):
        cache = {}
        samplers, channels, sampler_remap = [], [], {}
        for ci, ch in enumerate(anim.get("channels", [])):
            donor_node = ch.get("target", {}).get("node")
            name = donor_nodes.get(donor_node)
            mapped = BONE_ALIASES.get(name, name)
            if mapped is None or mapped not in target_by_name:
                continue
            si = ch["sampler"]
            if si not in sampler_remap:
                s = anim["samplers"][si]
                samplers.append({
                    "input": copy_accessor(donor, donor_bin, target, target_bin,
                                           s["input"], cache),
                    "output": copy_accessor(donor, donor_bin, target, target_bin,
                                            s["output"], cache),
                    "interpolation": s.get("interpolation", "LINEAR"),
                })
                sampler_remap[si] = len(samplers) - 1
            channels.append({
                "sampler": sampler_remap[si],
                "target": {"node": target_by_name[mapped],
                           "path": ch["target"]["path"]},
            })
        if channels:
            target.setdefault("animations", []).append({
                "name": anim.get("name", f"clip_{grafted}"),
                "samplers": samplers, "channels": channels,
            })
            grafted += 1
    # single-buffer glb: refresh buffer byteLength
    if target.get("buffers"):
        pad = (4 - len(target_bin) % 4) % 4
        target_bin.extend(b"\x00" * pad)
        target["buffers"][0]["byteLength"] = len(target_bin)
    save_glb(target_path, target, target_bin, version)
    return f"{target_slug}: grafted {grafted} clips from {donor_slug}"


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("targets", nargs="+")
    parser.add_argument("--donor", default="quaternius_casual_male")
    args = parser.parse_args()
    for t in args.targets:
        print(graft(args.donor, t))


if __name__ == "__main__":
    main()
