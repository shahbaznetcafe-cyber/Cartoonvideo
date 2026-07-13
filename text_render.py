"""
PIL se text ko image (RGBA numpy array) mein render karta hai.
Urdu/Arabic ke liye reshaping + RTL handle karta hai. ImageMagick ki zaroorat nahi.
Captions aur name-labels dono ke liye.
"""
import os
import re

import numpy as np
from PIL import Image, ImageDraw, ImageFont

import arabic_reshaper
from bidi.algorithm import get_display

# Windows fonts (Urdu-capable pehle)
_FONT_CANDIDATES = [
    r"C:\Windows\Fonts\Aldhabi.ttf",        # Urdu Nastaliq
    r"C:\Windows\Fonts\segoeui.ttf",        # Arabic-capable
    r"C:\Windows\Fonts\arial.ttf",
]

_ARABIC = re.compile(r"[؀-ۿ]")


def _font(size):
    for path in _FONT_CANDIDATES:
        if os.path.exists(path):
            return ImageFont.truetype(path, size)
    return ImageFont.load_default()


def _shape(text):
    """Urdu ho to reshape + RTL."""
    if _ARABIC.search(text):
        return get_display(arabic_reshaper.reshape(text))
    return text


def _wrap(text, font, max_w, draw):
    words = text.split()
    lines, cur = [], ""
    for w in words:
        test = (cur + " " + w).strip()
        if draw.textlength(test, font=font) <= max_w or not cur:
            cur = test
        else:
            lines.append(cur)
            cur = w
    if cur:
        lines.append(cur)
    return lines


def render_caption(text, video_w=1920, font_size=54, max_ratio=0.85):
    """
    Caption ko ek RGBA image (numpy) banao — semi-transparent bar ke saath.
    Niche-center par overlay karne ke liye.
    """
    font = _font(font_size)
    max_w = int(video_w * max_ratio)

    tmp = Image.new("RGBA", (10, 10))
    d = ImageDraw.Draw(tmp)

    shaped = _shape(text)
    lines = _wrap(shaped, font, max_w, d)

    pad_x, pad_y, line_gap = 40, 26, 12
    line_h = font_size + line_gap
    box_w = max_w + pad_x * 2
    box_h = line_h * len(lines) + pad_y * 2

    img = Image.new("RGBA", (box_w, box_h), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    # rounded translucent background
    draw.rounded_rectangle([0, 0, box_w, box_h], radius=24, fill=(0, 0, 0, 150))

    y = pad_y
    for ln in lines:
        w = draw.textlength(ln, font=font)
        x = (box_w - w) / 2
        # outline
        for dx, dy in [(-2, 0), (2, 0), (0, -2), (0, 2)]:
            draw.text((x + dx, y + dy), ln, font=font, fill=(0, 0, 0, 220))
        draw.text((x, y), ln, font=font, fill=(255, 255, 255, 255))
        y += line_h

    return np.array(img)


def render_label(text, font_size=34):
    """Character ka naam — chhota pill label (RGBA numpy)."""
    font = _font(font_size)
    shaped = _shape(text)

    tmp = Image.new("RGBA", (10, 10))
    d = ImageDraw.Draw(tmp)
    tw = d.textlength(shaped, font=font)

    pad_x, pad_y = 24, 12
    w, h = int(tw) + pad_x * 2, font_size + pad_y * 2
    img = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    draw.rounded_rectangle([0, 0, w, h], radius=h // 2, fill=(34, 197, 94, 235))
    draw.text((pad_x, pad_y - 2), shaped, font=font, fill=(6, 42, 19, 255))
    return np.array(img)


# ---------------- P2: Karaoke captions ----------------

def _hex(h):
    h = h.lstrip("#")
    return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))


def _outline(d, x, y, text, font, color, size):
    for dx in (-size, 0, size):
        for dy in (-size, 0, size):
            if dx or dy:
                d.text((x + dx, y + dy), text, font=font, fill=color + (255,))


def _active_chunk(chunks, t):
    for ch in chunks:
        if ch[0]["start"] <= t <= ch[-1]["end"]:
            return ch
        if t < ch[0]["start"]:
            return ch
    return chunks[-1]


def render_karaoke_frame(words, t, video_w, settings, highlight_color=None):
    """
    Ek window of words (group) render karo, current bola jane wala word highlight.
    Latin (English/Roman Urdu) = per-word karaoke. Urdu script = chunk-level.
    Full-width RGBA (video_w) — center aligned.
    """
    fs = settings["font_size"]
    font = _font(fs)
    H = int(fs * 2.4)
    img = Image.new("RGBA", (video_w, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    if not words:
        return np.array(img)

    N = max(1, settings.get("words_per_group", 3))
    chunks = [words[i:i + N] for i in range(0, len(words), N)]
    ch = _active_chunk(chunks, t)

    col = _hex(settings["color"])
    out = _hex(settings["outline"])
    osz = settings.get("outline_size", 3)
    hl = _hex(highlight_color or settings["highlight_color"])
    style = settings.get("highlight_style", "color")
    hbg = _hex(settings.get("highlight_bg", "#3700B3"))

    is_ar = any(_ARABIC.search(w["word"]) for w in ch)

    if is_ar:
        # Urdu: poora chunk reshaped (per-word color mushkil) — chunk-level karaoke (white)
        text = _shape(" ".join(w["word"] for w in ch))
        tw = d.textlength(text, font=font)
        x = (video_w - tw) / 2; y = (H - fs) / 2
        _outline(d, x, y, text, font, out, osz)
        d.text((x, y), text, font=font, fill=col + (255,))
        return np.array(img)

    # Latin: per-word highlight
    ai = 0
    for i, w in enumerate(ch):
        if w["start"] <= t <= w["end"]:
            ai = i; break
        if t > w["end"]:
            ai = i
    txts = [w["word"] for w in ch]
    space = d.textlength(" ", font=font)
    widths = [d.textlength(w, font=font) for w in txts]
    total = sum(widths) + space * (len(txts) - 1)
    x = (video_w - total) / 2; y = (H - fs) / 2

    big = _font(int(fs * 1.22))
    for i, w in enumerate(txts):
        ww = widths[i]
        active = (i == ai)
        if active and style == "box":
            d.rounded_rectangle([x - 8, y - 6, x + ww + 8, y + fs + 12],
                                radius=10, fill=hbg + (235,))
        if active and style == "scale":
            # pop: bara font, same center par
            bw = d.textlength(w, font=big)
            bx = x + (ww - bw) / 2; by = y - (fs * 0.11)
            _outline(d, bx, by, w, big, out, osz)
            d.text((bx, by), w, font=big, fill=hl + (255,))
        else:
            _outline(d, x, y, w, font, out, osz)
            d.text((x, y), w, font=font, fill=(hl if active else col) + (255,))
        x += ww + space

    return np.array(img)

