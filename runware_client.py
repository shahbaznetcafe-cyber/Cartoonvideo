"""Runware REST helper (veggie-tool wala, reuse)."""
import uuid
import requests

import config


def post_tasks(tasks, timeout=180):
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {config.RUNWARE_API_KEY}",
    }
    resp = requests.post(config.RUNWARE_ENDPOINT, headers=headers, json=tasks, timeout=timeout)
    if resp.status_code != 200:
        raise RuntimeError(f"Runware HTTP {resp.status_code}: {resp.text[:500]}")
    body = resp.json()
    if isinstance(body, dict) and body.get("errors"):
        raise RuntimeError(f"Runware error: {body['errors']}")
    data = body.get("data") if isinstance(body, dict) else None
    if not data:
        raise RuntimeError(f"Runware se khaali jawab: {body}")
    return data


def new_uuid():
    return str(uuid.uuid4())
