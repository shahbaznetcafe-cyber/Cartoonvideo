"""
M2 — Voice Engine (Phase 9).
story.json se har dialogue line ki awaaz banata hai (per-character).
Same-gender characters ko alag sunane ke liye pitch/rate vary karta hai.
Har line ki audio + duration ek timeline mein save hoti hai.
"""
import asyncio
import hashlib
import json
import os
import subprocess

import edge_tts

import config
import dialogue_style
import viseme_timeline

# Same gender ke kai characters ko distinguish karne ke liye variations
_PITCH_RATE_VARIANTS = [
    ("+0Hz", "+0%"),
    ("-30Hz", "-4%"),
    ("+25Hz", "+6%"),
    ("-15Hz", "+3%"),
    ("+40Hz", "-3%"),
    ("-45Hz", "+8%"),
]


def assign_voice_params(parsed):
    """Har character ko (voice, pitch, rate) do — gender same ho to bhi alag."""
    seen = {}
    for ch in parsed.get("characters", []):
        g = (ch.get("gender") or "male").lower()
        idx = seen.get(g, 0)
        seen[g] = idx + 1
        pitch, rate = _PITCH_RATE_VARIANTS[idx % len(_PITCH_RATE_VARIANTS)]
        ch["pitch"] = pitch
        ch["rate"] = rate
    return parsed


def _char_lookup(parsed):
    return {c["id"]: c for c in parsed.get("characters", [])}


def transliterate_roman_to_urdu(texts):
    """
    Roman Urdu lines -> Urdu script (TTS ke liye). edge-tts ka ur-PK voice Urdu script
    theek bolta hai, Roman (Latin) ghalat. Sab lines ek LLM call mein. Fail -> original.
    """
    import json
    import providers
    if not texts:
        return texts
    sysp = ("You are an Urdu transliteration engine. Convert each Roman-Urdu (Urdu written "
            "in Latin letters) string into proper Urdu script (اردو). Keep the SAME words and "
            "meaning, only change the script. Do NOT translate to a different language. "
            "Add natural Urdu punctuation for smooth text-to-speech flow: use ، for short "
            "pauses (commas), ۔ at sentence ends, ؟ for questions, ! for excitement, and ... "
            "for a hesitation/dramatic pause. This punctuation controls the voice rhythm, so "
            "place it where a person would naturally pause. "
            "Reply with ONLY a JSON array of strings, exact same length and order as input.")
    user = json.dumps(texts, ensure_ascii=False)
    try:
        raw = providers.llm_generate(sysp, user, max_tokens=2200, temperature=0.2)
        s, e = raw.find("["), raw.rfind("]")
        arr = json.loads(raw[s:e + 1])
        if isinstance(arr, list) and len(arr) == len(texts):
            return [str(a) for a in arr]
        print(f"  [translit] length mismatch ({len(arr)} vs {len(texts)}) -> original")
    except Exception as ex:
        print(f"  [translit fail] {ex} -> original text")
    return texts


def _duration(path):
    r = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration",
         "-of", "default=noprint_wrappers=1:nokey=1", path],
        capture_output=True, text=True,
    )
    try:
        return float(r.stdout.strip())
    except ValueError:
        return 2.0


def _synthesis_signature(text, voice, rate, pitch):
    payload = {
        "text": text, "voice": voice, "rate": rate, "pitch": pitch,
        "provider": config.TTS_PROVIDER, "speed": round(float(config.VOICE_SPEED), 3),
        "edge_voice": config.EDGE_VOICE, "google_voice": config.GOOGLE_TTS_VOICE,
        "eleven_voice": config.ELEVENLABS_VOICE_ID,
    }
    return hashlib.sha256(json.dumps(payload, sort_keys=True, ensure_ascii=False).encode("utf-8")).hexdigest()


def generate_voices(parsed, proj_dir, on_progress=None):
    """
    Har line ki mp3 banao -> proj_dir/voices/.
    return: timeline = list of dicts (scene, speaker, text, emotion, audio, duration).
    """
    assign_voice_params(parsed)
    chars = _char_lookup(parsed)

    voices_dir = os.path.join(proj_dir, "voices")
    os.makedirs(voices_dir, exist_ok=True)
    visemes_dir = os.path.join(proj_dir, "visemes")

    timeline = []
    # total lines (progress ke liye)
    all_lines = [(sc, ln) for sc in parsed["scenes"] for ln in sc.get("lines", [])]
    total = len(all_lines)

    # Roman Urdu -> Urdu script (TTS ke liye) — ek batch call. Captions Roman rahenge.
    tts_texts = [ln.get("text", "") for _, ln in all_lines]
    if (parsed.get("language") or "").lower() == "roman_urdu":
        if on_progress:
            on_progress(0, total, "Roman -> Urdu script (TTS)...")
        tts_texts = transliterate_roman_to_urdu(tts_texts)

    for i, (sc, ln) in enumerate(all_lines, start=1):
        spk = ln.get("speaker", "narrator")
        ch = chars.get(spk, {})
        language_voices = config.voice_map_for_language(parsed.get("language"))
        voice = ch.get("voice", language_voices["narrator"])
        pitch = ch.get("pitch", "+0Hz")
        rate = ch.get("rate", "+0%")
        # per-character voice override (characters.json "voice" field)
        try:
            import character_library
            lib = character_library.find_for(ch) if ch else None
            if lib and lib.get("voice"):
                voice = lib["voice"]
        except Exception:
            pass

        fname = f"s{sc['id']}_l{i}.mp3"
        fpath = os.path.join(voices_dir, fname)
        speak_text = dialogue_style.normalize_spoken_punctuation(
            tts_texts[i - 1] or ln["text"], parsed.get("language"))
        signature = _synthesis_signature(speak_text, voice, rate, pitch)
        signature_path = fpath + ".synthesis.json"
        cached_signature = ""
        try:
            with open(signature_path, encoding="utf-8") as handle:
                cached_signature = json.load(handle).get("signature", "")
        except Exception:
            pass

        # RESUME: agar valid mp3 pehle se hai to dobara na banao (crash ke baad tez)
        if (os.path.exists(fpath) and os.path.getsize(fpath) > 500
                and cached_signature == signature):
            dur = _duration(fpath)
            if on_progress:
                on_progress(i, total, f"Voice {i}/{total}: [{spk}] (cached)")
        else:
            import providers
            providers.tts_synthesize(speak_text, voice, fpath, rate=rate, pitch=pitch,
                                     volume=config.VOICE_VOLUME, speed=config.VOICE_SPEED)
            # professional cleanup: lead/trail silence trim + loudness-normalize + 48k.
            # words.json (lip-sync spans) ko trim-amount se shift karo taake sync sahi rahe.
            try:
                import audiopost
                import json as _json
                tmpf = fpath + ".clean.mp3"
                ndur, lead = audiopost.clean_voice(fpath, tmpf)
                if ndur > 0.1 and os.path.exists(tmpf):
                    os.replace(tmpf, fpath)
                    wj = fpath + ".words.json"
                    if lead > 0.001 and os.path.exists(wj):
                        with open(wj, encoding="utf-8") as handle:
                            d = _json.load(handle)
                        for w in d.get("words", []):
                            w["t"] = round(max(0.0, w["t"] - lead), 4)
                        with open(wj, "w", encoding="utf-8") as handle:
                            _json.dump(d, handle, ensure_ascii=False)
            except Exception as _ex:
                print(f"  [voice clean skip] {_ex}", flush=True)
            with open(signature_path, "w", encoding="utf-8") as handle:
                json.dump({"signature": signature, "provider": config.TTS_PROVIDER,
                           "speed": config.VOICE_SPEED}, handle, ensure_ascii=False)
            dur = _duration(fpath)

        first_in_scene = i == 1 or all_lines[i - 2][0].get("id") != sc.get("id")
        entry = {
            "scene": sc["id"],
            "location": sc.get("location"),
            "time": sc.get("time"),
            "mood": sc.get("mood"),
            "background_prompt": sc.get("background_prompt"),
            "speaker": spk,
            "text": ln["text"],
            "emotion": ln.get("emotion", "neutral"),
            "action": ln.get("action", ""),
            # Scene-level direction applies only to the incoming first line.
            "transition": (ln.get("transition") or
                           (sc.get("transition") if first_in_scene else None)),
            "transition_duration": (ln.get("transition_duration") or
                                    (sc.get("transition_duration")
                                     if first_in_scene else None)),
            "audio": os.path.join("voices", fname),
            "duration": round(dur, 2),
        }

        # Provider-neutral facial timeline. Failure is advisory so the existing
        # openness JSON remains the guaranteed fallback for legacy jaw rigs.
        try:
            words_path = fpath + ".words.json"
            _, viseme_path, _cache_hit = viseme_timeline.cached_viseme_timeline(
                ln.get("text", ""), fpath, visemes_dir,
                words_path if os.path.exists(words_path) else None,
                language=parsed.get("language"),
                fps=getattr(config, "BLENDER3D_FPS", 24),
                duration=dur,
            )
            entry["visemes"] = os.path.relpath(viseme_path, proj_dir)
            entry["viseme_schema"] = viseme_timeline.SCHEMA_VERSION
        except Exception as _ex:
            print(f"  [viseme timeline skip -> openness fallback] {_ex}", flush=True)

        timeline.append(entry)

        if on_progress:
            on_progress(i, total, f"Voice {i}/{total}: [{spk}]")

    return timeline
