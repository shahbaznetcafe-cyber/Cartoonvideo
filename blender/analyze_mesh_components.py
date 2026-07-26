"""Analyze disconnected components and legacy group coverage without saving."""
import json
import os
import sys

import bpy
from mathutils import Vector


def main():
    args = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    output = os.path.abspath(args[0])
    obj = max((item for item in bpy.data.objects if item.type == "MESH"),
              key=lambda item: len(item.data.vertices))
    mesh = obj.data
    parent = list(range(len(mesh.vertices)))

    def find(index):
        while parent[index] != index:
            parent[index] = parent[parent[index]]
            index = parent[index]
        return index

    def union(left, right):
        left, right = find(left), find(right)
        if left != right:
            parent[right] = left

    for edge in mesh.edges:
        union(edge.vertices[0], edge.vertices[1])

    components = {}
    for vertex in mesh.vertices:
        components.setdefault(find(vertex.index), []).append(vertex.index)

    group_names = {group.index: group.name for group in obj.vertex_groups}
    result = []
    for indices in components.values():
        world = [obj.matrix_world @ mesh.vertices[index].co for index in indices]
        sums = {}
        for index in indices:
            for membership in mesh.vertices[index].groups:
                name = group_names.get(membership.group, str(membership.group))
                sums[name] = sums.get(name, 0.0) + membership.weight
        total_weight = sum(sums.values()) or 1.0
        result.append({
            "vertex_count": len(indices),
            "centroid": [round(sum(v[i] for v in world) / len(world), 6) for i in range(3)],
            "min": [round(min(v[i] for v in world), 6) for i in range(3)],
            "max": [round(max(v[i] for v in world), 6) for i in range(3)],
            "legacy_weights": {
                name: round(value / total_weight, 5)
                for name, value in sorted(sums.items(), key=lambda item: item[1], reverse=True)
            },
            "sample_indices": indices[:12],
        })
    result.sort(key=lambda item: item["vertex_count"], reverse=True)
    os.makedirs(os.path.dirname(output), exist_ok=True)
    with open(output, "w", encoding="utf-8") as handle:
        json.dump({"mesh": obj.name, "component_count": len(result),
                   "components": result}, handle, indent=2)
    print("SBZ_COMPONENTS=" + output)


if __name__ == "__main__":
    main()
