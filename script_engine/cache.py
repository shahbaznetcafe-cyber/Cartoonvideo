"""Stable, secret-free disk cache for billable text requests."""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path


class RequestCache:
    def __init__(self, root):
        self.root = Path(root)

    @staticmethod
    def key(payload):
        canonical = json.dumps(payload, ensure_ascii=False, sort_keys=True,
                               separators=(",", ":")).encode("utf-8")
        return hashlib.sha256(canonical).hexdigest()

    def get(self, key):
        path = self.root / f"{key}.json"
        if not path.exists():
            return None
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            return None

    def put(self, key, value):
        self.root.mkdir(parents=True, exist_ok=True)
        path = self.root / f"{key}.json"
        temp = path.with_suffix(".tmp")
        temp.write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding="utf-8")
        os.replace(temp, path)
        return path
