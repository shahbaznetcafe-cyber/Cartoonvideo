"""
Professional audio post-production — social-video standards.
- clean_voice: leading/trailing silence trim + highpass + loudness-normalize + 48k
- master_mix: music ducking (sidechain) + fades + crossfade-loop + SFX + limiter (-1 dBTP)
             + loudnorm (~-15 LUFS) + 48k AAC 192k stereo
- measure_loudness / detect_silence / has_audio: QC (final loudness, silence, missing audio)
- SFX hooks: walk/run/struggle/pull/success/surprise/whoosh/transition/subscribe (files ya synth)

Target: I≈-14..-16 LUFS, TP≤-1 dBTP, 48kHz, AAC 192k, stereo (mono agar project maange).
"""
import os
import re
import subprocess

import config

SFX_DIR = os.path.join(config.BASE_DIR, "assets", "sfx")
os.makedirs(SFX_DIR, exist_ok=True)

SR = int(getattr(config, "AUDIO_SR", 48000))
BITRATE = getattr(config, "AUDIO_BITRATE", "192k")
TARGET_I = float(getattr(config, "TARGET_LUFS", -15.0))      # -14..-16 window
TARGET_TP = float(getattr(config, "TARGET_TP", -1.0))        # dBTP
MUSIC_DUCK_DB = float(getattr(config, "MUSIC_DUCK_DB", -18.0))  # ducked music level under speech


def _run(args):
    subprocess.run(args, check=True, capture_output=True, text=True)


def _try(args):
    try:
        return subprocess.run(args, capture_output=True, text=True)
    except Exception:
        return None


def probe_duration(path):
    r = _try(["ffprobe", "-v", "error", "-show_entries", "format=duration",
              "-of", "csv=p=0", path])
    try:
        return float((r.stdout or "").strip())
    except Exception:
        return 0.0


def has_audio(path):
    """Missing-audio detection — kya file mein koi audio stream hai."""
    r = _try(["ffprobe", "-v", "error", "-select_streams", "a",
              "-show_entries", "stream=codec_type", "-of", "csv=p=0", path])
    return bool(r and "audio" in (r.stdout or ""))


def measure_loudness(path):
    """Final loudness measurement — ebur128 se integrated LUFS + true peak (dBTP)."""
    r = _try(["ffmpeg", "-hide_banner", "-nostats", "-i", path,
              "-af", "ebur128=peak=true", "-f", "null", "-"])
    txt = (r.stderr or "") if r else ""
    I = tp = lra = None
    m = re.findall(r"I:\s*(-?\d+\.?\d*)\s*LUFS", txt)
    if m:
        I = float(m[-1])
    m = re.findall(r"Peak:\s*(-?\d+\.?\d*)\s*dBFS", txt)
    if m:
        tp = float(m[-1])
    m = re.findall(r"LRA:\s*(-?\d+\.?\d*)\s*LU", txt)
    if m:
        lra = float(m[-1])
    return {"I": I, "TP": tp, "LRA": lra}


def detect_silence(path, thr_db=-40, min_d=0.6):
    """Silence detection — lambe silence spans (start,end) list."""
    r = _try(["ffmpeg", "-hide_banner", "-nostats", "-i", path,
              "-af", f"silencedetect=noise={thr_db}dB:d={min_d}", "-f", "null", "-"])
    txt = (r.stderr or "") if r else ""
    spans, cur = [], None
    for line in txt.splitlines():
        m = re.search(r"silence_start:\s*(-?\d+\.?\d*)", line)
        if m:
            cur = float(m.group(1))
        m = re.search(r"silence_end:\s*(-?\d+\.?\d*)", line)
        if m and cur is not None:
            spans.append((cur, float(m.group(1))))
            cur = None
    return spans


def _lead_silence(path, thr_db=-42):
    """Leading silence (seconds) — word timestamps shift karne ke liye."""
    r = _try(["ffmpeg", "-hide_banner", "-nostats", "-i", path,
              "-af", f"silencedetect=noise={thr_db}dB:d=0.05", "-f", "null", "-"])
    txt = (r.stderr or "") if r else ""
    starts = re.findall(r"silence_start:\s*(-?\d+\.?\d*)", txt)
    ends = re.findall(r"silence_end:\s*(-?\d+\.?\d*)", txt)
    if starts and abs(float(starts[0])) < 0.06 and ends:
        return max(0.0, float(ends[0]))
    return 0.0


def clean_voice(in_path, out_path, target_i=-16.0):
    """Voice line cleanup: highpass (rumble) + lead/trail silence trim (chhota pad) +
    loudness-normalize + 48k. Returns (new_duration, lead_trimmed_seconds).
    lead_trimmed se caller words.json (lip-sync timings) shift kare."""
    lead = _lead_silence(in_path)
    pad_start = 0.06
    af = ("highpass=f=75,"
          f"silenceremove=start_periods=1:start_silence={pad_start}:start_threshold=-45dB:detection=peak,"
          "areverse,"
          "silenceremove=start_periods=1:start_silence=0.12:start_threshold=-45dB:detection=peak,"
          "areverse,"
          f"loudnorm=I={target_i}:TP=-1.5:LRA=11,"
          f"aresample={SR}")
    try:
        _run(["ffmpeg", "-y", "-i", in_path, "-af", af, "-ar", str(SR),
              out_path, "-loglevel", "error"])
    except Exception:
        return probe_duration(in_path), 0.0
    return probe_duration(out_path), max(0.0, lead - pad_start)


# ---------------- SFX ----------------
# action/emotion -> sfx naam. "" = koi sfx nahi (overuse se bacho).
ACTION_SFX = {
    "walk": "walk", "run": "run", "approach": "walk", "come": "walk", "go": "walk",
    "pull": "pull", "reach": "pull",
    "help": "struggle", "rescue": "struggle", "save": "struggle", "hug": "struggle",
    "celebrate": "success", "win": "success", "cheer": "success",
    "jump": "whoosh",
}
EMO_SFX = {"surprise": "surprise", "shocked": "surprise", "amazed": "surprise",
           "scared": "surprise"}


def sfx_file(name):
    """assets/sfx/<name>.<ext> — user file preferred (synth se override)."""
    if not name:
        return None
    for ext in (".mp3", ".wav", ".ogg", ".MP3", ".WAV", ".m4a"):
        p = os.path.join(SFX_DIR, name + ext)
        if os.path.exists(p):
            return p
    return None


def ensure_synth_sfx():
    """Agar SFX files na hon to kuch saaf synthetic (abstract) sfx bana do taake feature
    out-of-box kaam kare. User apni behtar files assets/sfx/ mein daal kar override kare.
    Sirf abstract sounds synth (whoosh/success/surprise/subscribe/transition) — footsteps/
    struggle synth acche nahi lagte, wo file-only hooks rehte hain."""
    recipes = {
        # whoosh: pink noise sweep (band-pass) + fade
        "whoosh": ["-f", "lavfi", "-i", "anoisesrc=d=0.5:c=pink:a=0.5",
                   "-af", "highpass=f=300,lowpass=f=3000,afade=t=in:st=0:d=0.05,"
                          "afade=t=out:st=0.25:d=0.25,volume=0.7"],
        "transition": ["-f", "lavfi", "-i", "anoisesrc=d=0.4:c=pink:a=0.4",
                       "-af", "highpass=f=500,lowpass=f=4000,afade=t=in:st=0:d=0.03,"
                              "afade=t=out:st=0.2:d=0.2,volume=0.6"],
        "rain": ["-f", "lavfi", "-i", "anoisesrc=d=3.0:c=pink:a=0.35",
                 "-af", "highpass=f=500,lowpass=f=6500,afade=t=in:st=0:d=0.25,"
                        "afade=t=out:st=2.4:d=0.6,volume=0.35"],
        "mud": ["-f", "lavfi", "-i", "anoisesrc=d=0.55:c=brown:a=0.5",
                "-af", "lowpass=f=650,afade=t=in:st=0:d=0.03,"
                       "afade=t=out:st=0.22:d=0.32,volume=0.7"],
        "bubbles": ["-f", "lavfi", "-i", "sine=frequency=950:duration=0.7",
                    "-af", "tremolo=f=12:d=0.8,highpass=f=700,"
                           "afade=t=out:st=0.35:d=0.35,volume=0.22"],
        # success: rising major triad (C5-E5-G5) short bells
        "success": ["-f", "lavfi", "-i",
                    "sine=frequency=523:duration=0.5",
                    "-f", "lavfi", "-i", "sine=frequency=659:duration=0.5",
                    "-f", "lavfi", "-i", "sine=frequency=784:duration=0.5",
                    "-filter_complex",
                    "[0:a]adelay=0|0[a];[1:a]adelay=120|120[b];[2:a]adelay=240|240[c];"
                    "[a][b][c]amix=inputs=3:normalize=0,afade=t=out:st=0.35:d=0.4,volume=0.4[out]",
                    "-map", "[out]"],
        # surprise: quick rising sting
        "surprise": ["-f", "lavfi", "-i", "sine=frequency=440:duration=0.35",
                     "-af", "afade=t=out:st=0.15:d=0.2,"
                            "aeval=val(0)*1.0,volume=0.5,"
                            "asetrate=48000*1.4,aresample=48000"],
        # subscribe: bright two-tone ding
        "subscribe": ["-f", "lavfi", "-i", "sine=frequency=988:duration=0.6",
                      "-f", "lavfi", "-i", "sine=frequency=1319:duration=0.6",
                      "-filter_complex",
                      "[0:a]adelay=0|0[a];[1:a]adelay=140|140[b];"
                      "[a][b]amix=inputs=2:normalize=0,afade=t=out:st=0.3:d=0.5,volume=0.45[out]",
                      "-map", "[out]"],
    }
    made = []
    for name, args in recipes.items():
        if sfx_file(name):
            continue
        out = os.path.join(SFX_DIR, name + ".wav")
        try:
            _run(["ffmpeg", "-y"] + args + ["-ar", str(SR), "-ac", "1", out, "-loglevel", "error"])
            made.append(name)
        except Exception:
            pass
    return made


def sfx_for_line(action, emotion):
    """Ek line ka sfx naam (action pehle, warna emotion). "" = koi nahi."""
    return ACTION_SFX.get(action or "", "") or EMO_SFX.get((emotion or "").lower(), "")


# ---------------- master mix ----------------
def master_mix(video_in, video_out, music_path, sfx_events, total_dur, mono=False):
    """
    Final audio master: dialogue + ducked music (sidechain) + sfx, fades, crossfade-loop
    music, limiter (-1 dBTP), loudnorm (~-14.5 LUFS), 48k AAC 384k stereo.
    sfx_events: [(t_seconds, name, gain_db), ...]. video_in mein dialogue audio hai.
    """
    dur = max(0.5, total_dur)
    inputs = ["-i", video_in]
    idx = 1
    mus_idx = None
    if music_path and os.path.exists(music_path):
        inputs += ["-stream_loop", "-1", "-i", music_path]
        mus_idx = idx
        idx += 1
    sfx_in = []
    for (t, name, g) in (sfx_events or []):
        f = sfx_file(name)
        if f and t < dur:
            inputs += ["-i", f]
            sfx_in.append((idx, max(0.0, t), g))
            idx += 1

    fc = []
    # dialogue: 48k, split (ek mix ke liye, ek ducking key ke liye)
    fc.append("[0:a]aresample=%d,asplit=2[voc][key]" % SR)
    mixlabels = ["[voc]"]
    if mus_idx is not None:
        fo = max(0.1, dur - 1.6)
        # music bed: length-match, fade in/out, low volume; phir dialogue se DUCK
        fc.append(
            f"[{mus_idx}:a]aresample={SR},atrim=0:{dur:.2f},asetpts=N/SR/TB,"
            f"afade=t=in:st=0:d=1.2,afade=t=out:st={fo:.2f}:d=1.6,"
            f"volume={config.MUSIC_VOLUME}[mus0]")
        fc.append(
            "[mus0][key]sidechaincompress=threshold=0.03:ratio=12:attack=5:"
            "release=320:makeup=1[mduck]")
        mixlabels.append("[mduck]")
    for j, (i_idx, t, g) in enumerate(sfx_in):
        ms = int(t * 1000)
        fc.append(f"[{i_idx}:a]aresample={SR},adelay={ms}|{ms},volume={g}dB[sfx{j}]")
        mixlabels.append(f"[sfx{j}]")
    n = len(mixlabels)
    fc.append("".join(mixlabels) +
              f"amix=inputs={n}:normalize=0:dropout_transition=0[mx]")
    # master chain: loudnorm (I/TP) -> alimiter safety (-1 dBTP ~0.891) -> 48k
    tp_lin = round(10 ** (TARGET_TP / 20.0), 4)
    fc.append(
        f"[mx]loudnorm=I={TARGET_I}:TP={TARGET_TP}:LRA=11,"
        f"alimiter=limit={tp_lin}:level=disabled,aresample={SR}[aout]")

    ac = "1" if mono else "2"
    args = (["ffmpeg", "-y"] + inputs +
            ["-filter_complex", ";".join(fc), "-map", "0:v", "-map", "[aout]",
             "-c:v", "copy", "-c:a", "aac", "-b:a", BITRATE, "-ar", str(SR),
             "-ac", ac, "-movflags", "+faststart", video_out, "-loglevel", "error"])
    _run(args)
    return video_out
