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
    ("run",       ["bhaag", "bhago", "daud", "daudo", "run", "tez chal", "raftaar"]),
    ("walk",      ["chalo", "chal ", "aao", "aaja", "jao", "chalte", "come", "go ",
                   "walk", "aage barho", "idhar aa"]),
    ("nod",       ["haan", "theek hai", "bilkul", "sahi kaha", "agree", "yes", "zaroor",
                   "manzoor"]),
    ("shake",     ["nahi", "bilkul nahi", "mat karo", "inkaar", "deny", " no ", "na na"]),
    ("reach",     ["pakdo", "pakad", "haath badha", "reach", "thaam", "pahunch"]),
]

# jin actions ko doosra character (target) chahiye
NEEDS_TARGET = {"help", "pull", "give", "point", "hug", "reach"}


def detect(text, emotion="neutral"):
    """Line text (+ emotion) se ek action string. Koi match nahi to emotion-based
    reaction (happy->celebrate light, warna 'none' = sirf idle+talk)."""
    t = " " + (text or "").lower().strip() + " "
    for action, kws in _RULES:
        for kw in kws:
            if kw in t:
                return action
    # koi explicit action nahi — strong emotion se halka reaction
    e = (emotion or "").lower()
    if e in ("excited", "joy", "cheerful") and ("!" in (text or "")):
        return "celebrate"
    return "none"


def needs_target(action):
    return action in NEEDS_TARGET
