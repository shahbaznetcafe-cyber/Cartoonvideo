"""Deterministic provider-neutral dialogue-to-viseme timeline generation."""

from __future__ import annotations

import hashlib
import json
import math
import os
import subprocess
from array import array
from pathlib import Path
from typing import Any

import viseme_maps


SCHEMA_VERSION = 1
GENERATOR_VERSION = "sbz-viseme-timeline-v1"
ATTACK_MS = 25
RELEASE_MS = 55
TRANSITION_MS = 35
COARTICULATION_MS = 50


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _sha256_json(value: Any) -> str:
    encoded = json.dumps(value, ensure_ascii=False, sort_keys=True,
                         separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _probe_duration(path: Path) -> float:
    result = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration",
         "-of", "default=noprint_wrappers=1:nokey=1", str(path)],
        capture_output=True, text=True,
    )
    try:
        return max(0.0, float(result.stdout.strip()))
    except (TypeError, ValueError):
        return 0.0


def _load_timestamps(value) -> tuple[list[dict[str, Any]], str]:
    if value is None:
        return [], "none"
    source = "inline"
    if isinstance(value, (str, os.PathLike)):
        path = Path(value)
        if not path.is_file():
            return [], "missing"
        source = "sidecar"
        try:
            value = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return [], "invalid"
    if isinstance(value, dict):
        level = str(value.get("level") or source)
        value = value.get("words") or value.get("timestamps") or value.get("items") or []
        source = level
    if not isinstance(value, list):
        return [], "invalid"
    return [dict(item) for item in value if isinstance(item, dict)], source


def _normalise_spans(items, text: str, duration: float) -> list[dict[str, Any]]:
    fallback_tokens = list(viseme_maps.iter_tokens(text))
    spans = []
    for index, item in enumerate(items):
        start = item.get("t", item.get("start", item.get("offset")))
        length = item.get("d", item.get("duration"))
        end = item.get("end")
        try:
            start = float(start)
            if length is None and end is not None:
                length = float(end) - start
            length = float(length)
        except (TypeError, ValueError):
            continue
        start = max(0.0, min(duration, start))
        end = max(start, min(duration, start + max(0.0, length)))
        if end <= start:
            continue
        token = item.get("w", item.get("word", item.get("text")))
        if not token and index < len(fallback_tokens):
            token = fallback_tokens[index]["text"]
        spans.append({
            "text": str(token or text or ""),
            "start": round(start, 6),
            "end": round(end, 6),
        })
    spans.sort(key=lambda item: (item["start"], item["end"], item["text"]))
    previous_end = 0.0
    clean = []
    for span in spans:
        start = max(previous_end, span["start"])
        if span["end"] > start:
            clean.append({"text": span["text"], "start": start, "end": span["end"]})
            previous_end = span["end"]
    return clean


def _punctuation_gap(fragment: str) -> float:
    if any(mark in fragment for mark in (".", "!", "?", "؟", "۔", "...")):
        return 0.12
    if any(mark in fragment for mark in (",", "،", ";", ":")):
        return 0.065
    return 0.025


def _fallback_spans(text: str, duration: float) -> list[dict[str, Any]]:
    tokens = list(viseme_maps.iter_tokens(text))
    if not tokens or duration <= 0:
        return []
    lead = min(0.08, duration * 0.04)
    trail = min(0.10, duration * 0.05)
    gaps = []
    for index, token in enumerate(tokens[:-1]):
        fragment = text[token["end"]:tokens[index + 1]["start"]]
        gaps.append(_punctuation_gap(fragment))
    gap_total = sum(gaps)
    max_gap_total = duration * 0.25
    if gap_total > max_gap_total and gap_total:
        scale = max_gap_total / gap_total
        gaps = [gap * scale for gap in gaps]
        gap_total = sum(gaps)
    reserved = lead + trail + gap_total
    if reserved >= duration and reserved:
        scale = duration * 0.25 / reserved
        lead *= scale
        trail *= scale
        gaps = [gap * scale for gap in gaps]
        gap_total = sum(gaps)
    available = max(0.0, duration - lead - trail - gap_total)
    weights = [max(1.0, len(token["text"]) ** 0.65) for token in tokens]
    unit = available / sum(weights)
    cursor = lead
    spans = []
    for index, (token, weight) in enumerate(zip(tokens, weights)):
        end = min(duration, cursor + unit * weight)
        if end > cursor:
            spans.append({"text": token["text"], "start": cursor, "end": end})
        if index < len(gaps):
            cursor = end + gaps[index]
    return spans


def _energy_speech_mask(path: Path, fps: int, frame_count: int) -> list[bool] | None:
    """Best-effort audio silence gate; returns None when decoding is unavailable."""
    sample_rate = 16000
    try:
        result = subprocess.run(
            ["ffmpeg", "-v", "error", "-i", str(path), "-ac", "1",
             "-ar", str(sample_rate), "-f", "s16le", "-"],
            capture_output=True, timeout=120,
        )
    except (OSError, subprocess.SubprocessError):
        return None
    if result.returncode or len(result.stdout) < 2:
        return None
    samples = array("h")
    samples.frombytes(result.stdout[:len(result.stdout) // 2 * 2])
    if not samples:
        return None
    window = max(1, round(sample_rate / fps))
    energy = []
    for frame in range(frame_count):
        chunk = samples[frame * window:(frame + 1) * window]
        if not chunk:
            energy.append(0.0)
        else:
            energy.append(math.sqrt(sum(sample * sample for sample in chunk) / len(chunk)))
    peak = max(energy, default=0.0)
    if peak <= 0:
        return [False] * frame_count
    threshold = max(80.0, peak * 0.035)
    raw = [value >= threshold for value in energy]
    # Keep quiet consonants adjacent to voiced frames while preserving real pauses.
    return [raw[i] or (i > 0 and raw[i - 1]) or (i + 1 < len(raw) and raw[i + 1])
            for i in range(len(raw))]


def _fit_phonemes_to_frames(phonemes: list[str], count: int) -> list[str]:
    if count <= 0 or not phonemes:
        return []
    if len(phonemes) <= count:
        return phonemes
    if count == 1:
        return [phonemes[len(phonemes) // 2]]
    return [phonemes[round(index * (len(phonemes) - 1) / (count - 1))]
            for index in range(count)]


def _allocate_frames(phonemes: list[str], count: int) -> list[int]:
    phonemes = _fit_phonemes_to_frames(phonemes, count)
    if not phonemes:
        return []
    base = [1] * len(phonemes)
    remaining = count - len(phonemes)
    if remaining <= 0:
        return base
    weights = [viseme_maps.PHONEME_DURATION.get(value, 1.0) for value in phonemes]
    total = sum(weights)
    exact = [remaining * weight / total for weight in weights]
    floors = [int(value) for value in exact]
    for index, value in enumerate(floors):
        base[index] += value
    leftover = remaining - sum(floors)
    order = sorted(range(len(exact)), key=lambda i: (-(exact[i] - floors[i]), i))
    for index in order[:leftover]:
        base[index] += 1
    return base


def _one_hot(viseme: str) -> list[float]:
    return [1.0 if name == viseme else 0.0 for name in viseme_maps.VISEME_ORDER]


def _coarticulate(targets: list[list[float]], labels: list[str], fps: int) -> None:
    radius = max(1, round(COARTICULATION_MS * fps / 1000))
    silence = "viseme_sil"
    for boundary in range(1, len(labels)):
        previous, current = labels[boundary - 1], labels[boundary]
        if previous == current or silence in (previous, current):
            continue
        prev_index = viseme_maps.VISEME_ORDER.index(previous)
        curr_index = viseme_maps.VISEME_ORDER.index(current)
        for distance in range(radius):
            before = boundary - radius + distance
            after = boundary + distance
            incoming = 0.18 + 0.32 * (distance + 1) / radius
            outgoing = 0.35 * (radius - distance) / radius
            if 0 <= before < len(targets):
                targets[before] = [0.0] * len(viseme_maps.VISEME_ORDER)
                targets[before][prev_index] = 1.0 - incoming
                targets[before][curr_index] = incoming
            if 0 <= after < len(targets):
                targets[after] = [0.0] * len(viseme_maps.VISEME_ORDER)
                targets[after][curr_index] = 1.0 - outgoing
                targets[after][prev_index] = outgoing


def _alpha(milliseconds: int, fps: int) -> float:
    return 1.0 - math.exp(-1.0 / (fps * milliseconds / 1000.0))


def _sparse_weights(values: list[float]) -> dict[str, float]:
    rounded = [round(max(0.0, value), 4) if value >= 0.0005 else 0.0 for value in values]
    total = sum(rounded)
    if total <= 0:
        rounded[0] = 1.0
    else:
        largest = max(range(len(rounded)), key=lambda index: rounded[index])
        rounded[largest] = round(rounded[largest] + (1.0 - total), 4)
    return {name: value for name, value in zip(viseme_maps.VISEME_ORDER, rounded) if value > 0}


def _build_report(text: str, audio_hash: str, duration: float, fps: int,
                  language: str, spans: list[dict[str, Any]], timestamp_source: str,
                  timestamp_hash: str, speech_mask: list[bool] | None) -> dict[str, Any]:
    frame_count = max(1, int(math.ceil(duration * fps)))
    silence = "viseme_sil"
    labels = [silence] * frame_count
    events = []

    for token_index, span in enumerate(spans):
        start_frame = max(0, min(frame_count - 1, int(round(span["start"] * fps))))
        end_frame = max(start_frame + 1, min(frame_count, int(round(span["end"] * fps))))
        count = end_frame - start_frame
        phonemes = viseme_maps.token_to_phonemes(span["text"], language)
        phonemes = _fit_phonemes_to_frames(phonemes, count)
        lengths = _allocate_frames(phonemes, count)
        cursor = start_frame
        for phoneme, length in zip(phonemes, lengths):
            viseme = viseme_maps.PHONEME_TO_VISEME[phoneme]
            event_end = min(end_frame, cursor + length)
            if event_end <= cursor:
                continue
            labels[cursor:event_end] = [viseme] * (event_end - cursor)
            events.append({
                "viseme": viseme,
                "start_frame": cursor,
                "end_frame": event_end,
                "start": round(cursor / fps, 6),
                "end": round(event_end / fps, 6),
                "token_index": token_index,
                "token": span["text"],
            })
            cursor = event_end

    targets = [_one_hot(label) for label in labels]
    if speech_mask is not None:
        for index in range(min(len(targets), len(speech_mask))):
            if not speech_mask[index]:
                targets[index] = _one_hot(silence)
                labels[index] = silence
    _coarticulate(targets, labels, fps)

    attack_alpha = _alpha(ATTACK_MS, fps)
    release_alpha = _alpha(RELEASE_MS, fps)
    transition_alpha = _alpha(TRANSITION_MS, fps)
    state = _one_hot(silence)
    frames = []
    for frame, target in enumerate(targets):
        if frame == 0 or frame == frame_count - 1:
            state = _one_hot(silence)
        else:
            target_speech = 1.0 - target[0]
            state_speech = 1.0 - state[0]
            if target_speech > state_speech + 1e-8:
                alpha = attack_alpha
            elif target_speech < state_speech - 1e-8:
                alpha = release_alpha
            else:
                alpha = transition_alpha
            state = [current + alpha * (wanted - current)
                     for current, wanted in zip(state, target)]
        weights = _sparse_weights(state)
        dominant = max(viseme_maps.VISEME_ORDER, key=lambda name: weights.get(name, 0.0))
        frames.append({
            "frame": frame,
            "time": round(frame / fps, 6),
            "dominant": dominant,
            "weights": weights,
        })

    request = {
        "generator": GENERATOR_VERSION,
        "audio_sha256": audio_hash,
        "text_sha256": hashlib.sha256(text.encode("utf-8")).hexdigest(),
        "timestamps_sha256": timestamp_hash,
        "timestamp_source": timestamp_source,
        "language": language,
        "fps": fps,
        "duration": round(duration, 6),
        "audio_silence_gate": speech_mask is not None,
    }
    request_hash = _sha256_json(request)
    return {
        "schema_version": SCHEMA_VERSION,
        "generator": GENERATOR_VERSION,
        "audio_sha256": audio_hash,
        "request_sha256": request_hash,
        "text_sha256": request["text_sha256"],
        "timestamps_sha256": timestamp_hash,
        "language": language,
        "timestamp_source": timestamp_source,
        "duration": round(duration, 6),
        "fps": fps,
        "frame_count": frame_count,
        "viseme_order": list(viseme_maps.VISEME_ORDER),
        "settings": {
            "attack_ms": ATTACK_MS,
            "release_ms": RELEASE_MS,
            "transition_ms": TRANSITION_MS,
            "coarticulation_ms": COARTICULATION_MS,
            "audio_silence_gate": speech_mask is not None,
        },
        "events": events,
        "frames": frames,
    }


def generate_viseme_timeline(dialogue_text: str, audio_file, word_timestamps=None,
                             *, language: str | None = None, fps: int = 24,
                             duration: float | None = None,
                             use_audio_silence_gate: bool = True) -> dict[str, Any]:
    """Generate a deterministic viseme timeline without writing a cache file."""
    path = Path(audio_file).expanduser().resolve()
    if not path.is_file():
        raise FileNotFoundError(f"Audio file not found: {path}")
    fps = int(fps)
    if fps < 1 or fps > 240:
        raise ValueError("fps must be between 1 and 240")
    duration = float(duration) if duration is not None else _probe_duration(path)
    if not math.isfinite(duration) or duration <= 0:
        raise ValueError("Audio duration must be greater than zero")

    text = str(dialogue_text or "")
    lang = viseme_maps.normalize_language(language, text)
    raw_timestamps, timestamp_source = _load_timestamps(word_timestamps)
    timestamp_hash = _sha256_json(raw_timestamps)
    spans = _normalise_spans(raw_timestamps, text, duration)
    if not spans:
        spans = _fallback_spans(text, duration)
        timestamp_source = "text_fallback"
    audio_hash = _sha256_file(path)
    frame_count = max(1, int(math.ceil(duration * fps)))
    speech_mask = (_energy_speech_mask(path, fps, frame_count)
                   if use_audio_silence_gate else None)
    return _build_report(text, audio_hash, duration, fps, lang, spans,
                         timestamp_source, timestamp_hash, speech_mask)


def cached_viseme_timeline(dialogue_text: str, audio_file, cache_dir,
                           word_timestamps=None, *, language: str | None = None,
                           fps: int = 24, duration: float | None = None,
                           use_audio_silence_gate: bool = True):
    """Return ``(report, path, cache_hit)`` using an audio-hash cache key."""
    audio_path = Path(audio_file).expanduser().resolve()
    if not audio_path.is_file():
        raise FileNotFoundError(f"Audio file not found: {audio_path}")
    text = str(dialogue_text or "")
    lang = viseme_maps.normalize_language(language, text)
    raw_timestamps, timestamp_source = _load_timestamps(word_timestamps)
    audio_hash = _sha256_file(audio_path)
    request_identity = {
        "generator": GENERATOR_VERSION,
        "audio_sha256": audio_hash,
        "text_sha256": hashlib.sha256(text.encode("utf-8")).hexdigest(),
        "timestamps_sha256": _sha256_json(raw_timestamps),
        "timestamp_source": timestamp_source,
        "language": lang,
        "fps": int(fps),
        "duration": round(float(duration), 6) if duration is not None else None,
        "audio_gate": bool(use_audio_silence_gate),
    }
    request_hash = _sha256_json(request_identity)
    directory = Path(cache_dir).expanduser().resolve()
    directory.mkdir(parents=True, exist_ok=True)
    cache_path = directory / f"{audio_hash}_{request_hash[:16]}.visemes.json"
    if cache_path.is_file():
        try:
            cached = json.loads(cache_path.read_text(encoding="utf-8"))
            if (cached.get("schema_version") == SCHEMA_VERSION and
                    cached.get("generator") == GENERATOR_VERSION and
                    cached.get("audio_sha256") == audio_hash):
                return cached, str(cache_path), True
        except (OSError, json.JSONDecodeError):
            pass

    report = generate_viseme_timeline(
        text, audio_path, word_timestamps, language=lang, fps=fps,
        duration=duration, use_audio_silence_gate=use_audio_silence_gate,
    )
    temp_path = cache_path.with_suffix(cache_path.suffix + ".tmp")
    temp_path.write_text(json.dumps(report, ensure_ascii=False, indent=2,
                                    sort_keys=True) + "\n", encoding="utf-8")
    os.replace(temp_path, cache_path)
    return report, str(cache_path), False
