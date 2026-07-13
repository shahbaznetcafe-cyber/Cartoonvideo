"""
Runware image-to-video (lip-sync/animation) ka EK test clip.
Maqsad: API format + cost confirm karna. (R2-B integrate karne se pehle.)
"""
import base64
import sys
import time

import config
from runware_client import post_tasks, new_uuid

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass


def data_uri(path):
    with open(path, "rb") as f:
        b64 = base64.b64encode(f.read()).decode()
    return "data:image/png;base64," + b64


def main():
    config.require_api_key()
    img = "characters/tomato.png"
    uri = data_uri(img)
    uid = new_uuid()

    task = {
        "taskType": "videoInference",
        "taskUUID": uid,
        "deliveryMethod": "async",
        "model": "klingai:3@2",
        "positivePrompt": ("cute cartoon tomato character talking and gesturing, "
                           "expressive happy face, natural mouth movement, lively, "
                           "subtle body motion, clean background"),
        "duration": 5,
        "frameImages": [{"inputImage": uri}],
    }

    print("[1] videoInference bhej raha hoon (async)...")
    resp = post_tasks([task])
    print("    initial response:", resp)

    print("[2] polling getResponse...")
    for i in range(40):
        time.sleep(6)
        poll = post_tasks([{"taskType": "getResponse", "taskUUID": uid}])
        d = poll[0]
        status = d.get("status", "?")
        print(f"    [{i}] status={status} keys={list(d.keys())}")
        if d.get("videoURL") or status == "success":
            print("\n✅ DONE")
            print("    videoURL:", d.get("videoURL"))
            print("    cost:", d.get("cost"))
            return
        if status == "error":
            print("    ERROR:", d)
            return
    print("    (timeout — abhi tak ready nahi)")


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"\n❌ {e}")
