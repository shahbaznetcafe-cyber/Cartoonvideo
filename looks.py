"""
3D VISUAL LOOK — Style dropdown ko 3D mode mein 'mood' bana deta hai (rang/roshni),
kyunki 3D characters/env AI-image nahi (art-style unpar asar nahi karta). Har look ek
ffmpeg color-grade (line-clip encode par) + exposure hint. Maujooda 163 art-styles ko
keyword se in moods par map karte hain -> dropdown 3D mein bhi kaam karta.
"""

# look -> {grade (ffmpeg filter chain), exposure (Blender view exposure)}
LOOKS = {
    "vibrant":   {"label": "🌈 Vibrant (bright cartoon)",
                  "grade": "eq=saturation=1.5:contrast=1.12:brightness=0.03:gamma=0.98",
                  "exposure": -0.2},
    "warm":      {"label": "🌅 Warm / Golden",
                  "grade": "eq=saturation=1.35:contrast=1.1:gamma=0.97,colorbalance=rm=0.07:gm=0.02:bm=-0.06",
                  "exposure": -0.1},
    "cool":      {"label": "🌙 Cool / Night",
                  "grade": "eq=saturation=1.05:contrast=1.16:brightness=-0.04:gamma=1.05,colorbalance=rm=-0.05:bm=0.09",
                  "exposure": -0.45},
    "pastel":    {"label": "🎨 Pastel / Soft",
                  "grade": "eq=saturation=0.72:contrast=0.96:brightness=0.06:gamma=1.02",
                  "exposure": 0.0},
    "cinematic": {"label": "🎬 Cinematic (contrast+vignette)",
                  "grade": "eq=saturation=1.2:contrast=1.28:gamma=0.95,vignette=PI/5",
                  "exposure": -0.3},
    "vivid":     {"label": "💡 Vivid / Neon",
                  "grade": "eq=saturation=1.85:contrast=1.22:gamma=0.96",
                  "exposure": -0.2},
    "vintage":   {"label": "📽️ Vintage / Retro",
                  "grade": "eq=saturation=0.55:contrast=1.05:gamma=1.0,colorbalance=rm=0.09:gm=0.03:bm=-0.09",
                  "exposure": -0.15},
}

# art-style keyword -> look (163 styles ko in moods par bind karta)
_KEYWORDS = [
    (("cinematic", "noir", "nolan", "fincher", "villeneuve", "imax", "documentary",
      "35mm", "film"), "cinematic"),
    (("neon", "cyber", "vapor", "gaming", "glitch", "holograph", "matrix", "digital"), "vivid"),
    (("pastel", "kawaii", "chibi", "soft", "dreamy", "dreamscape", "ethereal", "lofi",
      "cottagecore", "gen z"), "pastel"),
    (("ghibli", "watercolor", "gouache", "oil", "warm", "golden", "impressionist",
      "disney", "pixar"), "warm"),
    (("night", "dark", "horror", "gothic", "moody", "cyberpunk", "dieselpunk",
      "liminal", "backrooms", "aesthetic"), "cool"),
    (("vintage", "nostalg", "sepia", "old", "retro", "history", "monochrome",
      "black and white", "charcoal", "pencil", "ink"), "vintage"),
]


def look_for_style(style):
    s = (style or "").lower()
    for kws, look in _KEYWORDS:
        if any(k in s for k in kws):
            return look
    return "vibrant"     # default (3d cartoon, flat design, etc.)


def grade_for(style):
    """ffmpeg color-grade filter chain for the chosen style/look."""
    return LOOKS[look_for_style(style)]["grade"]


def exposure_for(style):
    return LOOKS[look_for_style(style)].get("exposure", -0.2)


def looks_list():
    return [{"id": k, "label": v["label"]} for k, v in LOOKS.items()]
