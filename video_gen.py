"""
P1 (premium) — Runware image-to-video: character ko AI se animate karo.
Cinematic render mode mein har bolne wale ki AI-animated clip banti hai.
Cache hoti hai (dobara generate nahi). Async + polling.
"""
import base64
import os
import time

import config
from runware_client import post_tasks, new_uuid


def _data_uri(path):
    with open(path, "rb") as f:
        return "data:image/png;base64," + base64.b64encode(f.read()).decode()


def animate_character(image_path, prompt, dur, cache_path, model=None,
                      on_progress=None):
    """
    image + prompt -> AI-animated mp4 (cache_path). Pehle se ho to wahi return.
    """
    if os.path.exists(cache_path) and os.path.getsize(cache_path) > 10000:
        return cache_path
    os.makedirs(os.path.dirname(cache_path), exist_ok=True)

    model = model or config.VIDEO_MODEL
    uid = new_uuid()
    clip_dur = int(min(10, max(5, round(dur))))

    task = {
        "taskType": "videoInference",
        "taskUUID": uid,
        "deliveryMethod": "async",
        "model": model,
        "positivePrompt": prompt,
        "duration": clip_dur,
        "frameImages": [{"inputImage": _data_uri(image_path)}],
    }
    post_tasks([task])

    # poll
    url = None
    for i in range(60):
        time.sleep(6)
        d = post_tasks([{"taskType": "getResponse", "taskUUID": uid}])[0]
        if on_progress:
            on_progress(d.get("status", "processing"))
        if d.get("videoURL"):
            url = d["videoURL"]
            break
        if d.get("status") == "error":
            raise RuntimeError(f"AI-video error: {d}")
    if not url:
        raise RuntimeError("AI-video timeout")

    import requests
    r = requests.get(url, timeout=180)
    r.raise_for_status()
    with open(cache_path, "wb") as f:
        f.write(r.content)
    return cache_path


def char_prompt(name, emotion):
    return (f"cute cartoon {name} character talking and gesturing, "
            f"{emotion} expression, expressive face, natural mouth movement, "
            f"lively subtle body motion, solid black background")
