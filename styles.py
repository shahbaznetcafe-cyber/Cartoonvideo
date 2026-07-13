"""
P4 — Style System. 163+ art styles (prompt templates) + custom + AI-suggest.
Har style ek "modifier" hai jo image prompt ke aage lagta hai.
"""
import json
import os

import config

# saare 163 style names (ShaziVideoGen parity)
_ALL = [
    "2d cartoon horror", "2d old cavetime cartoons", "35mm film photography", "3d cartoon",
    "aboriginal dot art", "abstract geometric", "acrylic painting", "african art",
    "ai generated", "ambient workspace", "anamorphic widescreen", "anime",
    "architecture photography", "art deco", "art nouveau", "backrooms", "baroque",
    "black and white photography", "blender 3d", "blue hour photography", "cartoon",
    "charcoal drawing", "chibi kawaii", "chinese ink painting", "christopher nolan",
    "cinematic", "city skyline", "cluttercore", "coffee shop", "comic book",
    "concept art", "corporate presentation", "cottagecore", "cozy reading",
    "cyberpunk 2077", "dark academia", "dark aesthetic", "dark fantasy",
    "data visualization", "david fincher dark", "denis villeneuve", "dieselpunk",
    "digital art", "disney classic", "documentary photography", "dreamcore",
    "drone aerial photography", "dslr photography", "editorial magazine",
    "educational diagram", "ethereal dreamy", "fantasy vibrant", "fashion editorial",
    "film noir", "flat design", "food photography", "game art", "gen z core", "ghibli",
    "glitch art", "goblincore", "god anime vine", "golden hour photography",
    "gouache painting", "gradient background", "hdr photography", "holographic",
    "horror gothic", "horror realistic", "horror vintage", "hyperrealistic",
    "imax documentary", "impressionist", "indian miniature", "ink wash painting",
    "islamic art", "isometric design", "itachi path", "japanese ukiyo e",
    "library study", "liminal space", "lofi aesthetic", "long exposure photography",
    "low poly 3d", "macro photography", "manga panel", "marcus aurelius",
    "matrix digital rain", "matte painting", "medieval cartoon satire",
    "meditation space", "medium format film", "mexican muralism",
    "minimalist infographic", "minimalist", "minimalist room", "monochrome",
    "monosoul aesthetic", "moody atmospheric", "mountain landscape",
    "national geographic", "nature documentary", "neomind vision", "neon cyberpunk",
    "neon gaming", "noir romance realism", "nostalgic filter", "ocean deep",
    "octane render", "oil painting", "old history painting", "pastel art",
    "pastel dreamscape", "pencil drawing", "persian miniature", "photorealistic",
    "pixar art", "pixel art", "pop art", "portrait photography", "post apocalyptic",
    "product photography", "productivity aesthetic", "rain aesthetic", "renaissance",
    "retro 80s", "rick and morty style", "ridley scott sci fi", "simple 2d cartoon",
    "simpsons style", "sketch", "solarpunk", "south park style", "space exploration",
    "sports action photography", "steampunk", "stick animation", "stick animation style",
    "street photography", "study motivation", "sunset vibes", "surrealism", "synthwave",
    "tarantino grindhouse", "tech tutorial", "terrence malick nature",
    "tilt shift photography", "tim burton gothic", "tron legacy", "unreal engine render",
    "vaporwave", "vector illustration", "vhs aesthetic", "watercolor", "weirdcore",
    "wes anderson", "whiteboard drawing", "wildlife photography", "wireframe",
]

# popular styles ke behtareen templates
_CURATED = {
    "3d cartoon": "3D cartoon style, Pixar-like, soft lighting, vibrant colors, rounded shapes, polished render",
    "pixar art": "Pixar 3D animation style, expressive, cinematic lighting, polished high detail",
    "anime": "anime style, cel shaded, vibrant colors, detailed, Japanese animation",
    "ghibli": "Studio Ghibli style, soft painterly backgrounds, warm colors, hand-painted",
    "cinematic": "cinematic film still, dramatic lighting, depth of field, color graded, photorealistic",
    "comic book": "comic book style, bold ink outlines, halftone shading, dynamic, vibrant",
    "photorealistic": "photorealistic, ultra detailed, sharp focus, natural lighting, 8k",
    "hyperrealistic": "hyperrealistic, extreme detail, lifelike, sharp, professional photography",
    "watercolor": "watercolor painting, soft washes, bleeding colors, paper texture, artistic",
    "flat design": "flat vector design, minimal, bold solid colors, clean shapes, no gradients",
    "vector illustration": "clean vector illustration, flat, bold modern shapes, scalable art",
    "pixel art": "pixel art, 8-bit retro game style, crisp pixels",
    "oil painting": "oil painting, visible brush strokes, rich textures, classical fine art",
    "cyberpunk 2077": "cyberpunk style, neon lights, futuristic city, dark, high tech, rain",
    "vaporwave": "vaporwave aesthetic, pastel neon, retro 80s, surreal, glitch",
    "synthwave": "synthwave, neon grid, retro futuristic, purple pink sunset",
    "minimalist": "minimalist, clean, simple, lots of negative space, few elements",
    "sketch": "pencil sketch, hand drawn, cross hatching, monochrome lines",
    "pencil drawing": "detailed pencil drawing, graphite shading, hand drawn",
    "charcoal drawing": "charcoal drawing, bold strokes, dramatic black and white, smudged",
    "low poly 3d": "low poly 3D, geometric faceted, stylized render",
    "isometric design": "isometric 3D illustration, clean, vibrant, technical",
    "pop art": "pop art style, bold colors, Ben-Day dots, Warhol-like, high contrast",
    "disney classic": "classic Disney 2D animation, hand-drawn, expressive, colorful",
    "simpsons style": "The Simpsons cartoon style, bold outlines, flat yellow-toned colors",
    "rick and morty style": "Rick and Morty cartoon style, wobbly lines, sci-fi, adult animation",
    "south park style": "South Park style, simple paper cutout look, flat colors",
    "digital art": "digital art, detailed, vibrant, concept art quality",
    "fantasy vibrant": "vibrant fantasy art, magical, epic scale, glowing, detailed",
    "steampunk": "steampunk, brass gears, Victorian, mechanical, sepia tones",
    "film noir": "film noir, black and white, high contrast shadows, dramatic 1940s",
    "whiteboard drawing": "whiteboard drawing style, clean black marker doodles on white, explainer sketch",
    "stick animation": "simple stick figure style, minimal black lines on white background",
    "simple 2d cartoon": "simple 2D cartoon, clean bold outlines, flat colors, friendly",
    "cartoon": "cartoon style, bold outlines, bright flat colors, fun and expressive",
    "islamic art": "Islamic art style, geometric patterns, arabesque, intricate, elegant",
    "watercolor": "watercolor painting, soft washes, artistic, paper texture",
}


def _generic(name):
    return f"in {name} art style, highly detailed, consistent visual style"


CUSTOM_FILE = os.path.join(config.BASE_DIR, "styles_custom.json")


def _load_custom():
    if os.path.exists(CUSTOM_FILE):
        try:
            return json.load(open(CUSTOM_FILE, encoding="utf-8"))
        except Exception:
            return {}
    return {}


def all_styles():
    s = {n: _CURATED.get(n, _generic(n)) for n in _ALL}
    s.update({k.lower(): v for k, v in _load_custom().items()})
    return s


def list_styles():
    return sorted(all_styles().keys())


def get_modifier(name):
    return all_styles().get((name or "").lower().strip(), _generic(name or "3d cartoon"))


def apply_style(prompt, name):
    """Image prompt ke aage style modifier lagao."""
    return f"{get_modifier(name)}. {prompt}"


def add_custom(name, description):
    c = _load_custom()
    c[name.strip()] = description
    json.dump(c, open(CUSTOM_FILE, "w", encoding="utf-8"),
              ensure_ascii=False, indent=2)
    return name


def suggest_style(script_text):
    """LLM se script ke liye behtareen style tajweez (P4 ⭐)."""
    import providers
    popular = ["3d cartoon", "pixar art", "anime", "ghibli", "cinematic", "comic book",
               "watercolor", "flat design", "whiteboard drawing", "cyberpunk 2077",
               "photorealistic", "fantasy vibrant", "minimalist", "pop art", "vaporwave"]
    sysp = ("You choose the single best visual style for a short video from a list. "
            "Reply with ONLY the exact style name from the list, nothing else.")
    user = f"Styles: {', '.join(popular)}\n\nScript:\n{script_text[:500]}\n\nBest style:"
    try:
        r = providers.llm_generate(sysp, user, max_tokens=20, temperature=0.2).strip().lower()
        for n in list_styles():
            if n == r or n in r or r in n:
                return n
    except Exception as e:
        print(f"  [style suggest fail] {e}")
    return config.STYLE
