"""
P3 — Multi-Provider Engine.
LLM / Image / TTS ke kai providers, ek unified interface + auto-fallback.
Jis provider ki key .env mein hogi woh available; configured fail ho to agla try.
Sirf woh providers chalenge jinki key hai (Runware + edge abhi mojood).
"""
import asyncio
import base64
import os
import re
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
        "model": _selected_model("runware", config.TEXT_MODEL),
        "settings": {"systemPrompt": system, "temperature": temperature,
                     "maxTokens": max_tokens},
        "messages": [{"role": "user", "content": user}],
    }
    return post_tasks([task])[0].get("text", "")


# OpenAI-compatible providers (base_url, key_env, model_env, default_model)
_OAI = {
    "deepseek":   ("https://api.deepseek.com", "DEEPSEEK_API_KEY", "DEEPSEEK_MODEL", "deepseek-v4-flash"),
    "zai":        ("https://api.z.ai/api/paas/v4", "ZAI_API_KEY", "ZAI_MODEL", "glm-4.7-flash"),
    "groq":       ("https://api.groq.com/openai/v1", "GROQ_API_KEY", "GROQ_MODEL", "llama-3.1-8b-instant"),
    "openai":     ("https://api.openai.com/v1", "OPENAI_API_KEY", "OPENAI_MODEL", "gpt-4o-mini"),
    "openrouter": ("https://openrouter.ai/api/v1", "OPENROUTER_API_KEY", "OPENROUTER_MODEL", "meta-llama/llama-3.1-8b-instruct"),
    "together":   ("https://api.together.xyz/v1", "TOGETHER_API_KEY", "TOGETHER_MODEL", "meta-llama/Llama-3-8b-chat-hf"),
    "gemini":     ("https://generativelanguage.googleapis.com/v1beta/openai", "GOOGLE_API_KEY", "GEMINI_MODEL", "gemini-1.5-flash"),
}

LLM_MODEL_CATALOG = [
    # A single Runware key/gateway serves every vendor model below.
    {"provider": "runware", "vendor": "DeepSeek", "model": "deepseek-v4-flash", "label": "DeepSeek V4 Flash", "cost": "lowest cost", "description": "Fast, economical multilingual script drafting"},
    {"provider": "runware", "vendor": "DeepSeek", "model": "deepseek-v4-pro", "label": "DeepSeek V4 Pro", "cost": "best value", "description": "Strong long-form reasoning and story structure"},
    {"provider": "runware", "vendor": "Z.AI", "model": "zai-glm-4-7", "label": "GLM 4.7", "cost": "low cost", "description": "Economical multilingual writing"},
    {"provider": "runware", "vendor": "Z.AI", "model": "zai-glm-5-1", "label": "GLM 5.1", "cost": "high quality", "description": "Long-form planning and polished scripts"},
    {"provider": "runware", "vendor": "OpenAI", "model": "openai-gpt-5-4-mini", "label": "GPT-5.4 Mini", "cost": "balanced", "description": "Recommended balance of quality, speed and cost"},
    {"provider": "runware", "vendor": "OpenAI", "model": "openai-gpt-5-4", "label": "GPT-5.4", "cost": "premium", "description": "Higher-quality story writing and revision"},
    {"provider": "runware", "vendor": "Google", "model": "google-gemini-3-5-flash", "label": "Gemini 3.5 Flash", "cost": "fast", "description": "Fast multilingual scripts and analysis"},
    {"provider": "runware", "vendor": "Google", "model": "google-gemini-3-1-pro", "label": "Gemini 3.1 Pro", "cost": "premium", "description": "High-quality long-form multilingual stories"},
]

_RUNWARE_MODEL_ALIASES = {
    "openai:gpt@5.4-mini": "openai-gpt-5-4-mini",
    "deepseek:v4@flash": "deepseek-v4-flash",
    "deepseek:v4@pro": "deepseek-v4-pro",
    "zai:glm@4.7": "zai-glm-4-7",
    "zai:glm@5.1": "zai-glm-5-1",
}


def _selected_model(provider, fallback):
    selected = str(getattr(config, "LLM_MODEL", "") or "").strip()
    if provider == "runware":
        selected = _RUNWARE_MODEL_ALIASES.get(selected, selected)
        fallback = _RUNWARE_MODEL_ALIASES.get(str(fallback), str(fallback))
    valid = {item["model"] for item in LLM_MODEL_CATALOG if item["provider"] == provider}
    return selected if selected in valid else fallback


def llm_model_options():
    return [dict(item) for item in LLM_MODEL_CATALOG]


def _oai_av(name):
    return lambda: bool(_key(_OAI[name][1]))


def _oai_gen(name):
    base, keyenv, modelenv, default = _OAI[name]

    def fn(system, user, max_tokens, temperature):
        model = _selected_model(name, os.getenv(modelenv, default))
        r = requests.post(
            base + "/chat/completions",
            headers={"Authorization": f"Bearer {_key(keyenv)}",
                     "Content-Type": "application/json"},
            json={"model": model,
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
    model = _selected_model("huggingface", os.getenv("HF_MODEL", config.HF_MODEL))
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
EDGE_VOICE_FALLBACK = [
    {"name": "hi-IN-AaravNeural", "locale": "hi-IN", "gender": "Male"},
    {"name": "hi-IN-AnanyaNeural", "locale": "hi-IN", "gender": "Female"},
    {"name": "hi-IN-ArjunNeural", "locale": "hi-IN", "gender": "Male"},
    {"name": "hi-IN-KavyaNeural", "locale": "hi-IN", "gender": "Female"},
    {"name": "hi-IN-KunalNeural", "locale": "hi-IN", "gender": "Male"},
    {"name": "hi-IN-MadhurNeural", "locale": "hi-IN", "gender": "Male"},
    {"name": "hi-IN-RehaanNeural", "locale": "hi-IN", "gender": "Male"},
    {"name": "hi-IN-SwaraNeural", "locale": "hi-IN", "gender": "Female"},
    {"name": "ur-IN-GulNeural", "locale": "ur-IN", "gender": "Female"},
    {"name": "ur-IN-SalmanNeural", "locale": "ur-IN", "gender": "Male"},
    {"name": "ur-PK-AsadNeural", "locale": "ur-PK", "gender": "Male"},
    {"name": "ur-PK-UzmaNeural", "locale": "ur-PK", "gender": "Female"},
]
GOOGLE_HINDI_VOICES = [
    {"name": "hi-IN-Standard-A", "gender": "Female", "tier": "Standard"},
    {"name": "hi-IN-Standard-B", "gender": "Male", "tier": "Standard"},
    {"name": "hi-IN-Standard-C", "gender": "Male", "tier": "Standard"},
    {"name": "hi-IN-Standard-D", "gender": "Female", "tier": "Standard"},
    {"name": "hi-IN-Standard-E", "gender": "Female", "tier": "Standard"},
    {"name": "hi-IN-Standard-F", "gender": "Male", "tier": "Standard"},
    {"name": "hi-IN-Wavenet-A", "gender": "Female", "tier": "WaveNet"},
    {"name": "hi-IN-Wavenet-B", "gender": "Male", "tier": "WaveNet"},
    {"name": "hi-IN-Wavenet-C", "gender": "Male", "tier": "WaveNet"},
    {"name": "hi-IN-Wavenet-D", "gender": "Female", "tier": "WaveNet"},
]
_EDGE_VOICE_CACHE = {"at": 0.0, "voices": None}


def edge_voice_options(force=False):
    """Fetch current Edge voice inventory, with an offline Hindi/Urdu fallback."""
    now = time.monotonic()
    cached = _EDGE_VOICE_CACHE.get("voices")
    if cached and not force and now - _EDGE_VOICE_CACHE.get("at", 0) < 3600:
        return {"available": True, "voices": cached, "selected": config.EDGE_VOICE}
    voices = []
    try:
        raw = asyncio.run(__import__("edge_tts").list_voices())
        for voice in raw:
            short = str(voice.get("ShortName") or "")
            locale = str(voice.get("Locale") or "")
            if locale not in {"hi-IN", "ur-IN", "ur-PK"}:
                continue
            voices.append({"name": short, "locale": locale,
                           "gender": str(voice.get("Gender") or "")})
    except Exception:
        voices = [dict(voice) for voice in EDGE_VOICE_FALLBACK]
    voices.sort(key=lambda voice: (voice["locale"], voice["gender"], voice["name"]))
    _EDGE_VOICE_CACHE.update(at=now, voices=voices)
    return {"available": True, "voices": voices, "selected": config.EDGE_VOICE}


def google_voice_options():
    return {"available": _tts_google_av(), "voices": [dict(v) for v in GOOGLE_HINDI_VOICES],
            "selected": config.GOOGLE_TTS_VOICE,
            "note": "Google Cloud billing setup required; monthly free quota may apply."}


def _speed(value):
    try:
        return max(0.7, min(1.2, float(value)))
    except (TypeError, ValueError):
        return 1.0


def _edge_rate(rate, speed):
    match = re.search(r"([+-]?\d+)", str(rate or "+0%"))
    character_rate = int(match.group(1)) if match else 0
    combined = max(-50, min(100, character_rate + round((_speed(speed) - 1) * 100)))
    return f"{combined:+d}%"


def _tts_edge_av():
    return True


def _tts_edge(text, voice, out_path, rate, pitch, volume, speed=1.0):
    """edge-tts synth. Audio ke saath WordBoundary timestamps bhi capture karo
    (lip-sync Tier 1: TTS se word-level timings) -> <out_path>.words.json sidecar.
    Urdu voices bhi word boundaries dete hain. .save() ye metadata phenk deta tha."""
    async def run():
        selected = config.EDGE_VOICE or voice
        comm = __import__("edge_tts").Communicate(
            text, selected, rate=_edge_rate(rate, speed), pitch=pitch, volume=volume)
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
            with open(out_path + ".words.json", "w", encoding="utf-8") as handle:
                _j.dump({"words": spans, "level": ("word" if words else "sentence")},
                        handle, ensure_ascii=False)
    asyncio.run(run())
    return out_path


def _eleven_key():
    # dono naam support: ELEVENLABS_API_KEY ya Eleven_Labs_API_Key
    return _key("ELEVENLABS_API_KEY") or _key("Eleven_Labs_API_Key")


def _eleven_voice():
    # Sarah remains the backwards-compatible fallback when no UI/env selection exists.
    return (getattr(config, "ELEVENLABS_VOICE_ID", "") or
            _key("ELEVENLABS_VOICE_ID") or "EXAVITQu4vr4xnSDxMaL")


_ELEVEN_VOICE_CACHE = {"at": 0.0, "payload": None}
_STORY_VOICE_TERMS = {
    "child": 16, "children": 16, "kid": 16, "young": 10, "teen": 6,
    "storyteller": 15, "storytelling": 15, "narrator": 12, "narration": 12,
    "audiobook": 10, "story": 5, "animation": 4, "cartoon": 5,
    "playful": 6, "friendly": 4, "warm": 3, "expressive": 5,
    "bright": 4, "energetic": 3, "soft": 3, "gentle": 4,
    # These can be useful character voices, but are poor defaults for young viewers.
    "fierce": -10, "warrior": -12, "villain": -12, "horror": -14,
    "scary": -12, "seductive": -12, "husky": -5, "deep": -4,
}


def _story_voice_score(voice):
    labels = voice.get("labels") or {}
    text = " ".join([
        str(voice.get("name") or ""), str(voice.get("description") or ""),
        str(voice.get("category") or ""),
        *[f"{key} {value}" for key, value in labels.items()],
    ]).lower()
    return sum(weight for term, weight in _STORY_VOICE_TERMS.items() if term in text)


def _format_elevenlabs_voices(voices):
    """Sanitize and rank account voices, putting children/story voices first."""
    result = []
    for raw in voices or []:
        voice_id = str(raw.get("voice_id") or "").strip()
        name = str(raw.get("name") or "").strip()
        if not voice_id or not name:
            continue
        labels = {str(k): str(v) for k, v in (raw.get("labels") or {}).items()
                  if v not in (None, "")}
        score = _story_voice_score(raw)
        result.append({
            "voice_id": voice_id,
            "name": name,
            "category": str(raw.get("category") or ""),
            "description": str(raw.get("description") or "")[:240],
            "labels": labels,
            "story_score": score,
            "recommended": score >= 8,
        })
    result.sort(key=lambda voice: (
        not voice["recommended"], -voice["story_score"], voice["name"].casefold()))
    return result


def elevenlabs_voice_options(force=False):
    """Return voices available to the configured ElevenLabs account.

    The official v2 endpoint supports 100 voices per page.  Results are cached for
    five minutes so opening the settings panel does not repeatedly spend API calls.
    """
    key = _eleven_key()
    if not key:
        raise RuntimeError("ElevenLabs API key configured nahi hai")
    now = time.monotonic()
    cached = _ELEVEN_VOICE_CACHE.get("payload")
    if not force and cached and now - _ELEVEN_VOICE_CACHE.get("at", 0) < 300:
        return cached

    voices, token = [], None
    for _page in range(5):
        params = {"page_size": 100, "include_total_count": "true",
                  "sort": "name", "sort_direction": "asc"}
        if token:
            params["next_page_token"] = token
        response = requests.get(
            "https://api.elevenlabs.io/v2/voices",
            headers={"xi-api-key": key}, params=params, timeout=30)
        response.raise_for_status()
        data = response.json()
        voices.extend(data.get("voices") or [])
        token = data.get("next_page_token")
        if not data.get("has_more") or not token:
            break

    ranked = _format_elevenlabs_voices(voices)
    configured = _eleven_voice()
    ids = {voice["voice_id"] for voice in ranked}
    selected = configured if configured in ids else (ranked[0]["voice_id"] if ranked else "")
    payload = {
        "available": True,
        "voices": ranked,
        "recommended_count": sum(1 for voice in ranked if voice["recommended"]),
        "selected": selected,
        "model": getattr(config, "ELEVENLABS_MODEL", "eleven_v3"),
    }
    _ELEVEN_VOICE_CACHE.update(at=now, payload=payload)
    return payload


def _tts_eleven_av():
    return bool(_eleven_key())


def _tts_eleven(text, voice, out_path, rate, pitch, volume, speed=1.0):
    # Edge voice names must never leak into the ElevenLabs URL.  A per-character
    # ElevenLabs ID may override the global UI selection when one is supplied.
    voice_id = (voice if re.fullmatch(r"[A-Za-z0-9]{20,64}", str(voice or ""))
                else _eleven_voice())
    r = requests.post(
        f"https://api.elevenlabs.io/v1/text-to-speech/{voice_id}",
        headers={"xi-api-key": _eleven_key(), "Content-Type": "application/json"},
        json={"text": text,
              "model_id": getattr(config, "ELEVENLABS_MODEL", "eleven_v3"),
              "voice_settings": {"speed": _speed(speed)}},
        timeout=120)
    r.raise_for_status()
    with open(out_path, "wb") as f:
        f.write(r.content)
    return out_path


def _google_tts_key():
    return _key("GOOGLE_TTS_API_KEY") or _key("GOOGLE_API_KEY")


def _tts_google_av():
    return bool(_google_tts_key())


def _tts_google(text, voice, out_path, rate, pitch, volume, speed=1.0):
    hz = re.search(r"([+-]?\d+)", str(pitch or "+0Hz"))
    pitch_semitones = max(-20.0, min(20.0, (int(hz.group(1)) / 10 if hz else 0)))
    response = requests.post(
        "https://texttospeech.googleapis.com/v1/text:synthesize",
        params={"key": _google_tts_key()},
        headers={"Content-Type": "application/json; charset=utf-8"},
        json={
            "input": {"text": text},
            "voice": {"languageCode": "hi-IN", "name": config.GOOGLE_TTS_VOICE},
            "audioConfig": {"audioEncoding": "MP3", "speakingRate": _speed(speed),
                            "pitch": pitch_semitones},
        }, timeout=120)
    response.raise_for_status()
    audio = response.json().get("audioContent")
    if not audio:
        raise RuntimeError("Google TTS ne audioContent return nahi kiya")
    with open(out_path, "wb") as handle:
        handle.write(base64.b64decode(audio))
    return out_path


_TTS = {"edge": (_tts_edge_av, _tts_edge),
        "google": (_tts_google_av, _tts_google),
        "elevenlabs": (_tts_eleven_av, _tts_eleven)}


def tts_synthesize(text, voice, out_path, rate="+0%", pitch="+0Hz", volume="+0%", speed=None):
    order = [config.TTS_PROVIDER] + [p for p in config.TTS_FALLBACK
                                     if p != config.TTS_PROVIDER]
    errs = []
    for name in order:
        pr = _TTS.get(name)
        if not pr or not pr[0]():
            continue
        try:
            return pr[1](text, voice, out_path, rate, pitch, volume,
                         config.VOICE_SPEED if speed is None else speed)
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
