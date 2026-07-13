"""
P2 — Whisper word-level timing (free, local faster-whisper).
Har line ki audio se words + (start,end) nikalta hai — karaoke captions ke liye.
Model ek hi baar load hota hai (singleton).
"""
import config

_MODEL = None


def _model():
    global _MODEL
    if _MODEL is None:
        from faster_whisper import WhisperModel
        _MODEL = WhisperModel(config.WHISPER_MODEL, device="cpu", compute_type="int8")
    return _MODEL


def word_timings(audio_path, language=None):
    """
    return: list[{start, end, word}] — agar fail ho to khaali list (fallback caption).
    """
    try:
        segs, _info = _model().transcribe(
            audio_path, word_timestamps=True, language=language)
        words = []
        for s in segs:
            for w in (s.words or []):
                txt = (w.word or "").strip()
                if txt:
                    words.append({"start": float(w.start),
                                  "end": float(w.end), "word": txt})
        return words
    except Exception as e:
        print(f"  [whisper fallback] {e}")
        return []
