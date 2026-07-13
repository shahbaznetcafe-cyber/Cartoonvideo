"""
P3 — Multi-Provider Engine.
LLM / Image / TTS ke kai providers, ek unified interface + auto-fallback.
Jis provider ki key .env mein hogi woh available; configured fail ho to agla try.
Sirf woh providers chalenge jinki key hai (Runware + edge abhi mojood).
"""
import asyncio
import os
import time

import requests

import config
from runware_client import post_tasks, new_uuid


def _key(name):
    return os.getenv(name, "").strip()


def _download(url, out_path, tries=6):
    """Robust download: har network error (IncompleteRead/ConnectionError/timeout) par retry
    + truncation check (Content-Length se). Streaming taake bade file safe aayein."""
    last = None
    for a in range(tries):
        try:
            r = requests.get(url, timeout=180, stream=True)
            r.raise_for_status()
            expected = int(r.headers.get("Content-Length") or 0)
            data = r.content                       # poora body (ChunkedEncoding par yahan error)
            if expected and len(data) < expected:
                raise IOError(f"truncated {len(data)}/{expected}")
            if len(data) < 500:                    # image bohat chhoti = fail
                raise IOError(f"too small ({len(data)}b)")
            with open(out_path, "wb") as f:
                f.write(data)
            return out_path
        except Exception as e:                     # HTTPError/ConnectionError/IncompleteRead/IOError sab
            last = e
            time.sleep(1.5 * (a + 1))
    raise RuntimeError(f"download fail baad {tries} tries: {last}")


# ============================ LLM ============================
def _llm_runware_av():
    return bool(config.RUNWARE_API_KEY)


def _llm_runware(system, user, max_tokens, temperature):
    task = {
        "taskType": "textInference", "taskUUID": new_uuid(),
        "model": config.TEXT_MODEL,
        "settings": {"systemPrompt": system, "temperature": temperature,
                     "maxTokens": max_tokens},
        "messages": [{"role": "user", "content": user}],
    }
    return post_tasks([task])[0].get("text", "")


# OpenAI-compatible providers (base_url, key_env, model_env, default_model)
_OAI = {
    "groq":       ("https://api.groq.com/openai/v1", "GROQ_API_KEY", "GROQ_MODEL", "llama-3.1-8b-instant"),
    "openai":     ("https://api.openai.com/v1", "OPENAI_API_KEY", "OPENAI_MODEL", "gpt-4o-mini"),
    "openrouter": ("https://openrouter.ai/api/v1", "OPENROUTER_API_KEY", "OPENROUTER_MODEL", "meta-llama/llama-3.1-8b-instruct"),
    "together":   ("https://api.together.xyz/v1", "TOGETHER_API_KEY", "TOGETHER_MODEL", "meta-llama/Llama-3-8b-chat-hf"),
    "gemini":     ("https://generativelanguage.googleapis.com/v1beta/openai", "GOOGLE_API_KEY", "GEMINI_MODEL", "gemini-1.5-flash"),
}


def _oai_av(name):
    return lambda: bool(_key(_OAI[name][1]))


def _oai_gen(name):
    base, keyenv, modelenv, default = _OAI[name]

    def fn(system, user, max_tokens, temperature):
        r = requests.post(
            base + "/chat/completions",
            headers={"Authorization": f"Bearer {_key(keyenv)}",
                     "Content-Type": "application/json"},
            json={"model": os.getenv(modelenv, default),
                  "messages": [{"role": "system", "content": system},
                               {"role": "user", "content": user}],
                  "temperature": temperature, "max_tokens": max_tokens},
            timeout=90)
        r.raise_for_status()
        return r.json()["choices"][0]["message"]["content"]
    return fn


# ---- HuggingFace (InferenceClient) ----
_hf_clients = {}


def _hf_token():
    return (_key("HF_TOKEN") or _key("HUGGINGFACE_API_KEY")
            or _key("HUGGINGFACEHUB_API_TOKEN"))


def _llm_hf_av():
    return bool(_hf_token())


def _llm_hf(system, user, max_tokens, temperature):
    from huggingface_hub import InferenceClient
    model = os.getenv("HF_MODEL", "meta-llama/Meta-Llama-3-8B-Instruct")
    cli = _hf_clients.get(model)
    if cli is None:
        cli = InferenceClient(model, token=_hf_token())
        _hf_clients[model] = cli
    msgs = [{"role": "system", "content": system},
            {"role": "user", "content": user}]
    resp = cli.chat_completion(msgs, max_tokens=max_tokens, temperature=temperature)
    return resp.choices[0].message.content


_LLM = {"runware": (_llm_runware_av, _llm_runware),
        "huggingface": (_llm_hf_av, _llm_hf)}
for _n in _OAI:
    _LLM[_n] = (_oai_av(_n), _oai_gen(_n))


def llm_generate(system, user, max_tokens=900, temperature=0.6, tries=3):
    import time
    order = [config.LLM_PROVIDER] + [p for p in config.LLM_FALLBACK
                                     if p != config.LLM_PROVIDER]
    errs = []
    for name in order:
        pr = _LLM.get(name)
        if not pr or not pr[0]():
            continue
        for a in range(tries):
            try:
                return pr[1](system, user, max_tokens, temperature)
            except Exception as e:
                msg = str(e)
                errs.append(f"{name}: {e}")
                # transient (504/timeout/429/5xx) -> backoff retry; warna agla provider
                if any(t in msg for t in ("504", "timeout", "Timeout", "429", "502", "503")):
                    time.sleep(3.0 * (a + 1))
                    continue
                break
    raise RuntimeError("LLM providers fail: " + ("; ".join(errs) or "koi available nahi"))


# ============================ IMAGE ============================
def _img_runware_av():
    return bool(config.RUNWARE_API_KEY)


def _img_runware(prompt, width, height, negative, out_path):
    task = {
        "taskType": "imageInference", "taskUUID": new_uuid(),
        "model": config.IMAGE_MODEL, "positivePrompt": prompt,
        "negativePrompt": negative or "low quality, blurry",
        "width": width, "height": height, "numberResults": 1,
        "outputType": "URL", "outputFormat": "PNG",
    }
    url = post_tasks([task])[0].get("imageURL")
    if not url:
        raise RuntimeError("Runware: image URL nahi mila")
    return _download(url, out_path)


def _img_fal_av():
    return bool(_key("FAL_KEY"))


def _img_fal(prompt, width, height, negative, out_path):
    size = "landscape_16_9" if width >= height else "portrait_16_9"
    r = requests.post(
        "https://fal.run/fal-ai/flux/schnell",
        headers={"Authorization": f"Key {_key('FAL_KEY')}",
                 "Content-Type": "application/json"},
        json={"prompt": prompt, "image_size": size,
              "num_inference_steps": 4, "num_images": 1},
        timeout=120)
    r.raise_for_status()
    return _download(r.json()["images"][0]["url"], out_path)


_IMG = {"runware": (_img_runware_av, _img_runware),
        "fal": (_img_fal_av, _img_fal)}


def image_generate(prompt, width, height, out_path, negative=""):
    order = [config.IMAGE_PROVIDER] + [p for p in config.IMAGE_FALLBACK
                                       if p != config.IMAGE_PROVIDER]
    errs = []
    for name in order:
        pr = _IMG.get(name)
        if not pr or not pr[0]():
            continue
        try:
            return pr[1](prompt, width, height, negative, out_path)
        except Exception as e:
            errs.append(f"{name}: {e}")
    raise RuntimeError("Image providers fail: " + ("; ".join(errs) or "koi available nahi"))


# ============================ TTS ============================
def _tts_edge_av():
    return True


def _tts_edge(text, voice, out_path, rate, pitch, volume):
    """edge-tts synth. Audio ke saath WordBoundary timestamps bhi capture karo
    (lip-sync Tier 1: TTS se word-level timings) -> <out_path>.words.json sidecar.
    Urdu voices bhi word boundaries dete hain. .save() ye metadata phenk deta tha."""
    async def run():
        comm = __import__("edge_tts").Communicate(
            text, voice, rate=rate, pitch=pitch, volume=volume)
        words, sents = [], []
        with open(out_path, "wb") as f:
            async for chunk in comm.stream():
                ct = chunk.get("type")
                if ct == "audio":
                    f.write(chunk["data"])
                elif ct in ("WordBoundary", "SentenceBoundary"):
                    # offset/duration 100-nanosecond ticks (Azure) -> seconds
                    rec = {"t": round(chunk["offset"] / 1e7, 4),
                           "d": round(chunk["duration"] / 1e7, 4),
                           "w": chunk.get("text", "")}
                    (words if ct == "WordBoundary" else sents).append(rec)
        # word-level behtar; Urdu voices sirf sentence dete -> wahi speech-span
        spans = words or sents
        if spans:
            import json as _j
            _j.dump({"words": spans, "level": ("word" if words else "sentence")},
                    open(out_path + ".words.json", "w", encoding="utf-8"), ensure_ascii=False)
    asyncio.run(run())
    return out_path


def _eleven_key():
    # dono naam support: ELEVENLABS_API_KEY ya Eleven_Labs_API_Key
    return _key("ELEVENLABS_API_KEY") or _key("Eleven_Labs_API_Key")


def _eleven_voice():
    # default: Sarah (multilingual). Change: ELEVENLABS_VOICE_ID
    return _key("ELEVENLABS_VOICE_ID") or "EXAVITQu4vr4xnSDxMaL"


def _tts_eleven_av():
    return bool(_eleven_key())


def _tts_eleven(text, voice, out_path, rate, pitch, volume):
    r = requests.post(
        f"https://api.elevenlabs.io/v1/text-to-speech/{_eleven_voice()}",
        headers={"xi-api-key": _eleven_key(), "Content-Type": "application/json"},
        json={"text": text,
              "model_id": os.getenv("ELEVENLABS_MODEL", "eleven_multilingual_v2")},
        timeout=120)
    r.raise_for_status()
    with open(out_path, "wb") as f:
        f.write(r.content)
    return out_path


_TTS = {"edge": (_tts_edge_av, _tts_edge),
        "elevenlabs": (_tts_eleven_av, _tts_eleven)}


def tts_synthesize(text, voice, out_path, rate="+0%", pitch="+0Hz", volume="+0%"):
    order = [config.TTS_PROVIDER] + [p for p in config.TTS_FALLBACK
                                     if p != config.TTS_PROVIDER]
    errs = []
    for name in order:
        pr = _TTS.get(name)
        if not pr or not pr[0]():
            continue
        try:
            return pr[1](text, voice, out_path, rate, pitch, volume)
        except Exception as e:
            errs.append(f"{name}: {e}")
    raise RuntimeError("TTS providers fail: " + ("; ".join(errs) or "koi available nahi"))


# ============================ STATUS + COST ============================
def status():
    """Kaunse providers available hain (key present)."""
    return {
        "llm": [n for n, (av, _) in _LLM.items() if av()],
        "image": [n for n, (av, _) in _IMG.items() if av()],
        "tts": [n for n, (av, _) in _TTS.items() if av()],
    }


def estimate_cost(scene_count, line_count, char_count, render_mode="draft"):
    """Mota-mota cost estimate (USD)."""
    llm = 0.01
    bg = scene_count * 0.003          # Runware FLUX image
    chars = char_count * 0.01         # character images (agar AI banaye)
    voices = 0.0                      # edge-tts free
    video = line_count * 0.28 if render_mode == "cinematic" else 0.0
    total = llm + bg + chars + voices + video
    return {"llm": llm, "backgrounds": round(bg, 3), "characters": round(chars, 3),
            "voices": voices, "ai_video": round(video, 2), "total": round(total, 2)}
