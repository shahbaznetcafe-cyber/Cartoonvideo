"""
Story action detection — dialogue line ke text se character ka action (madad/kheench/
ishaara/celebrate/walk...) nikaalo taake 3D renderer usay actual animate kare (sirf
camera pan nahi). Roman-Urdu + Urdu + English keywords. render_scene.html __poseFrame
in action strings ko samajhta hai.
"""
import re

# action -> keywords (Roman-Urdu, Urdu, English). Priority upar se neeche (pehla match jeeta).
# NOTE: jin actions ko partner chahiye (help/pull/reach/give/point/hug) unke liye target
# blender3d.py resolve karta hai.
_RULES = [
    ("wash",      ["handwash", "wash", "soap", "rub hands", "scrub", "foam",
                    "clean hands", "demonstrates handwashing", "rubs hands"]),
    ("slip",      ["slip", "slips", "slipped", "stumble", "loses balance", "phisal"]),
    ("splash",    ["splash", "puddle", "mud splashes", "jumps in mud"]),
    ("pickup",    ["pick up", "picks up", "uthata", "uthaata", "utha lo", "zameen se uth"]),
    ("punch",     ["punch", "mukka", "ghoosa", "ghunsa"]),
    ("kick",      ["kick", "laat", "thokar"]),
    ("hit",       ["hit", "struck", "lagti hai", "takra", "dhakka"]),
    ("fall",      ["falls", "fell", "gir gaya", "gir gayi", "girta", "girti"]),
    ("help",      ["madad", "bachao", "bacha lo", "bacha", "rescue", "save", "help",
                   "nikaal", "nikal", "chhura", "chhuda", "chura", "sahara", "sambhaal",
                   "sambhal", "guide", "raasta dikha"]),
    ("pull",      ["kheench", "khinch", "pull", "ghaseet", "ghasit", "tension"]),
    ("give",      ["thama", "de do", "de di", "diya", "pesh", "offer", "give", "le lo",
                   "haazir", "tohfa", "gift"]),
    ("point",     ["ishaara", "ishara", "point", "wahan dekho", "udhar", "us taraf",
                   "dekho wahan", "look there"]),
    ("hug",       ["gale", "jhappi", "hug", "seenay se"]),
    ("wave",      ["salaam", "hello", "assalam", "alvida", "bye", "hi ", "wave",
                   "haath hila", "khuda hafiz"]),
    ("celebrate", ["jeet", "jeeta", "jeet gaye", "mubarak", "celebrate", "cheer", "hurray",
                   "hooray", "shaandaar", "kamaal", "yay", "wah wah", "khushi se jhoom",
                   "party", "dhamaal", "win"]),
    ("jump",      ["uchhal", "kood", "jump", "chhalaang", "chhalang"]),
    ("dance",     ["dance", "naach", "nachne", "dances"]),
    ("run",       ["bhaag", "bhago", "daud", "daudo", "run", "tez chal", "raftaar"]),
    ("walk",      ["chalo", "chal ", "aao", "aaja", "jao", "chalte", "come", "go ",
                   "walk", "aage barho", "idhar aa"]),
    ("nod",       ["haan", "theek hai", "bilkul", "sahi kaha", "agree", "yes", "zaroor",
                   "manzoor"]),
    ("shake",     ["nahi", "bilkul nahi", "mat karo", "inkaar", "deny", " no ", "na na"]),
    ("reach",     ["pakdo", "pakad", "haath badha", "reach", "thaam", "pahunch"]),
    ("sit",       ["sits", "sit down", "baith", "beth"]),
    ("stand",     ["stands up", "stand up", "khara hota", "khari hoti", "uth khara"]),
    ("look",      ["looks at", "ghaur se dek", "dekhta", "dekhti", "nazar"]),
    ("listen",    ["listens", "sunta", "sunti", "kaan laga"]),
    ("exit",      ["exits", "leaves quickly", "nikal jata", "nikal jati", "chala jata", "chali jati"]),
]

# jin actions ko doosra character (target) chahiye
NEEDS_TARGET = {"help", "pull", "give", "point", "hug", "reach", "pickup", "punch", "kick", "hit"}

SUPPORTED_ACTIONS = (
    "idle", "talk", "look", "listen", "walk", "run", "approach", "exit", "wave",
    "point", "reach", "pickup", "give", "celebrate", "jump", "dance",
    "nod", "shake", "hug", "help", "pull", "punch", "kick", "hit",
    "fall", "sit", "stand", "wash", "slip", "splash",
)


def keyword_present(text, keyword):
    """Match a complete word/phrase, never an accidental substring.

    Roman Urdu words such as ``karunga`` previously triggered ``run`` and
    ``achai`` could trigger ``chai`` in downstream prop detection.  Whitespace
    inside a phrase is flexible, while its outer edges must be real token
    boundaries.  The Unicode-aware boundaries also keep Urdu matching intact.
    """
    phrase = str(keyword or "").strip()
    if not phrase:
        return False
    pattern = r"(?<!\w)" + r"\s+".join(
        re.escape(part) for part in phrase.split()
    ) + r"(?!\w)"
    return re.search(pattern, str(text or ""), flags=re.IGNORECASE) is not None


def prompt_policy():
    return (
        "ANIMATION DIRECTION: write every spoken line as "
        "'Name: (emotion; action) spoken line'. Choose exactly one concrete action from: "
        + ", ".join(SUPPORTED_ACTIONS) + ". Use idle only when no visible action is justified. "
        "Actions must follow story cause-and-effect; do not assign random gestures."
    )


def detect(text, emotion="neutral"):
    """Line text (+ emotion) se ek action string. Koi match nahi to emotion-based
    reaction (happy->celebrate light, warna 'none' = sirf idle+talk)."""
    t = str(text or "")
    for action, kws in _RULES:
        for kw in kws:
            if keyword_present(t, kw):
                return action
    # koi explicit action nahi — strong emotion se halka reaction
    e = (emotion or "").lower()
    if e in ("excited", "joy", "cheerful") and ("!" in (text or "")):
        return "celebrate"
    return "none"


def needs_target(action):
    return action in NEEDS_TARGET
