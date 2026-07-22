"""Verified Runware model registry and editable task routing."""
from __future__ import annotations

import json
from copy import deepcopy
from pathlib import Path


ROOT = Path(__file__).resolve().parent


class RegistryError(ValueError):
    pass


class ModelRegistry:
    def __init__(self, path=None):
        self.path = Path(path or ROOT / "model_registry.json")
        self.data = json.loads(self.path.read_text(encoding="utf-8"))
        self._models = {}
        self._aliases = {}
        for model in self.data.get("models", []):
            internal = model.get("internalId")
            air = model.get("runwareAir")
            if not internal or not air or internal in self._models:
                raise RegistryError(f"Invalid or duplicate model registry entry: {internal!r}")
            self._models[internal] = model
            for alias in [internal, air, *model.get("legacyIds", [])]:
                previous = self._aliases.get(alias)
                if previous and previous != internal:
                    raise RegistryError(f"Ambiguous model alias: {alias}")
                self._aliases[alias] = internal

    def resolve(self, model_id):
        internal = self._aliases.get(str(model_id or ""))
        model = self._models.get(internal)
        if not model or not model.get("enabled"):
            raise RegistryError(f"Unknown or disabled Runware model: {model_id}")
        return deepcopy(model)

    def enabled(self):
        return [deepcopy(model) for model in self._models.values() if model.get("enabled")]

    def public_payload(self):
        return {
            "schemaVersion": self.data.get("schemaVersion"),
            "verifiedAt": self.data.get("verifiedAt"),
            "verification": deepcopy(self.data.get("verification", {})),
            "models": self.enabled(),
        }


class TaskRouter:
    def __init__(self, registry=None, path=None):
        self.registry = registry or ModelRegistry()
        self.path = Path(path or ROOT / "routing.json")
        self.data = json.loads(self.path.read_text(encoding="utf-8"))
        for task, route in self.data.get("tasks", {}).items():
            self.registry.resolve(route.get("primary"))
            for fallback in route.get("fallbacks", []):
                self.registry.resolve(fallback)

    @property
    def task_names(self):
        return tuple(self.data.get("tasks", {}).keys())

    def route(self, task, requested_model=None, allow_fallback=True):
        if task not in self.data.get("tasks", {}):
            raise RegistryError(f"Unsupported script task: {task}")
        spec = deepcopy(self.data["tasks"][task])
        primary = self.registry.resolve(requested_model or spec["primary"])
        fallbacks = []
        if allow_fallback:
            limit = max(0, int(self.data.get("maxProviderFallbacks", 1)))
            for model_id in spec.get("fallbacks", []):
                candidate = self.registry.resolve(model_id)
                if candidate["internalId"] != primary["internalId"]:
                    fallbacks.append(candidate)
                if len(fallbacks) >= limit:
                    break
        spec["models"] = [primary, *fallbacks]
        spec["task"] = task
        spec["requestTimeoutSeconds"] = int(self.data.get("requestTimeoutSeconds", 90))
        spec["maxTransportRetries"] = max(0, int(self.data.get("maxTransportRetries", 1)))
        return spec

    def public_payload(self):
        return deepcopy(self.data)
