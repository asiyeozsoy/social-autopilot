"""Queue Factyeap's older YouTube videos for Instagram (+Facebook mirror) and TikTok.

Captions come from the YouTube title/description (plans/catalog_factyeap.json);
the handful of videos with no YouTube match get captions from EXTRA below.

python tools/queue_catalog.py <dir with NN_slug.mp4> [--from N --to M]
"""
import argparse
import csv
import datetime as dt
import json
import re
import shutil
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
TZ = "+01:00"
START = dt.date(2026, 11, 3)
DROP = {"#shorts", "#youtubeshorts", "#tiktokshorts", "#fyp", "#fypシ゚viral", "#viralshorts", "#alizasehar", "#new",
        "#viralvideo", "#viralvideos", "#viral", "#fypviral"}
SKIP = {"spiders"}  # has a Spider-Man shot, never went up on YouTube
CTA = "Follow @factyeap for a new fact every day 🦉"

EXTRA = {
    "polar-bears": ("Polar bears aren't actually white 🐻‍❄️",
                    "Their fur is see-through and their skin is black. They just look white because the hollow hairs scatter light, like snow.",
                    "#polarbear #animalfacts #arctic #wildlife"),
    "spiders": ("Spiders are tiny engineers 🕷️",
                "Gram for gram, spider silk is stronger than steel, and some spiders can even fly on it. Creepy or genius?",
                "#spiders #animalfacts #nature #science"),
    "great-wall": ("Can you really see the Great Wall from space? 🧱🚀",
                   "It's one of the most repeated 'facts' ever, and astronauts say it's a myth. The wall is long, but way too narrow to spot with the naked eye.",
                   "#greatwallofchina #space #mythbusting #history"),
    "liver": ("Your liver can grow back 🫀✨",
              "It's the only organ that can regenerate. Lose a big part of it and it can grow back to full size in a few weeks.",
              "#humanbody #biology #sciencefacts #liver"),
}
KEYS = {  # slug -> words that identify its YouTube upload
    "orangutans": "Orangutans: More Human", "phoenix": "Phoenix", "snails": "Inside That Shell", "yeti": "Yeti",
    "comic-sans": "Comic Sans", "octopus": "How Weird Can They Get", "butterflies": "Caterpillars",
    "sharks": "Sharks don’t just swim", "ottoman": "A Hub of Innovation", "ai-future": "future is AI-powered",
    "squirrels": "Squirrels aren", "internet-name": "Information Superhighway", "aztec-chocolate": "Aztecs",
    "be-the-change": "be the change", "bee-math": "Bees don", "first-jobs": "First Jobs",
    "happiness": "Happiness starts", "game-brain": "in the loop", "time-flies": "time fly",
    "lol-addictive": "League of Legends so addictive", "bluetooth": "Bluetooth", "fidget-spinner": "fidget spinners",
    "small-joys": "tiniest moments", "clowns": "Clowns", "yoyo": "Yoyos", "tiger-woods": "Tiger Woods",
    "space-signals": "Signals coming from space", "bike-history": "pedal-less", "pencil-history": "History of the Pencil",
    "fanny-pack": "Fanny Pack", "area-54": "Area 54", "neuralink": "Neuralink", "humanity-restarted": "already peaked",
    "english": "English isn’t one language", "loneliest-planet": "Loneliest Planet", "everest-ocean": "Everest Fits",
    "quietest-room": "Quietest Room", "chewing-gum": "Chewing Gum", "jellyfish": "Jellyfish",
    "stomach-acid": "Stomach Acid", "first-mouse": "First Mouse", "trex-game": "T-Rex", "dna-drive": "DNA: The Ultimate",
    "deepest-point": "Deepest Point", "shark-cables": "Attacking The Internet", "ameca-robot": "Humanoid Robot",
    "black-hole": "Black Hole", "forbidden-experiment": "FORBIDDEN", "first-computer": "Ancestor of Your Computer",
    "big-bacterium": "Bacterium", "first-bug": "Computer BUG", "men-nipples": "NIPPLES", "firefox": "Firefox",
    "qwerty": "Your Keyboard", "captcha": "CAPTCHA", "atoms": "Atoms", "phantom-vibration": "phone vibrate",
    "red-notifications": "notifications are RED", "endless-scroll": "stop scrolling", "ai-pompeii": "2,000 year old secret",
}


def split_tags(text):
    tags = re.findall(r"#[^\s#]+", text)
    body = re.sub(r"#[^\s#]+", "", text)
    body = re.sub(r"(?m)^\s*[_\-–—=≈]+\s*$", "", body)
    body = re.sub(r"[ \t]+", " ", body)
    body = re.sub(r"\n{3,}", "\n\n", body).strip()
    body = re.sub(r"(?<!\n)\n(?!\n)", " ", body)  # undo hard line wraps
    body = re.sub(r" {2,}", " ", body).replace("“", "").replace("”", "").strip()
    return body, tags


def clean_tags(tags, limit):
    out, seen = ["#factyeap"], {"#factyeap"}
    for t in tags:
        t = t.rstrip(".,!")
        k = t.lower()
        if k in seen or k in DROP or "fyp" in k or "short" in k or len(t) < 3:
            continue
        seen.add(k)
        out.append(t if any(c.isupper() for c in t[1:]) else k)
        if len(out) >= limit:
            break
    for t in ("#didyouknow", "#facts"):
        if t not in seen and len(out) < limit + 2:
            out.append(t)
            seen.add(t)
    return out


def caption_for(slug, yt):
    if slug in EXTRA:
        title, body, tags = EXTRA[slug]
        tags = tags.split()
    else:
        cands = [v for v in yt if KEYS[slug].lower() in v["title"].lower()] or \
                [v for v in yt if KEYS[slug].lower() in v["description"].lower()]
        v = max(cands, key=lambda v: v["views"])
        title, ttags = split_tags(v["title"])
        body, dtags = split_tags(v["description"])
        tags = ttags + dtags
    hook = title.strip()
    parts = [hook] + ([body] if body else [])
    ig = "\n\n".join(parts + [CTA, " ".join(clean_tags(tags, 8))])
    tt = "\n\n".join(parts + [" ".join(clean_tags(tags, 5) + ["#fyp"])])
    return ig, tt


def slots(n):
    """Back-catalogue slots so Factyeap posts ~3 times a day together with the queued originals."""
    taken = {p.name[:10] for p in (ROOT / "content" / "factyeap").iterdir() if p.is_dir() and "_cat" not in p.name}
    day, out = START, []
    while len(out) < n:
        times = ["10:30", "15:30"] + ([] if day.isoformat() in taken else ["21:30"])
        if day == START:
            times = ["15:30", "21:30"]
        out += [(day, t) for t in times]
        day += dt.timedelta(days=1)
    return out[:n]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("videos")
    ap.add_argument("--from", dest="lo", type=int, default=1)
    ap.add_argument("--to", dest="hi", type=int, default=999)
    a = ap.parse_args()
    yt = json.loads((ROOT / "plans" / "catalog_factyeap.json").read_text())["youtube"]
    picks = [(int(r[0]), r[1]) for r in csv.reader((ROOT / "tools" / "catalog_picks.tsv").open(), delimiter="\t")
             if r[1] not in SKIP]
    sched = slots(len(picks))
    for n, (i, slug) in enumerate(picks):
        if not a.lo <= i <= a.hi:
            continue
        src = Path(a.videos) / f"{i:02d}_{slug}.mp4"
        day, t = sched[n]
        folder = ROOT / "content" / "factyeap" / f"{day.isoformat()}_{t.replace(':', '')}_cat{i:02d}-{slug}"
        folder.mkdir(parents=True, exist_ok=True)
        shutil.copy(src, folder / "video.mp4")
        ig, tt = caption_for(slug, yt)
        post = {"brand": "factyeap", "publish_at": f"{day.isoformat()}T{t}:00{TZ}",
                "platforms": {"instagram": {"kind": "reel", "media": ["video.mp4"], "caption": ig},
                              "tiktok": {"kind": "video", "media": ["video.mp4"], "caption": tt}}}
        (folder / "post.yaml").write_text(yaml.safe_dump(post, allow_unicode=True, sort_keys=False, width=1000))
        print(folder.name)


if __name__ == "__main__":
    main()
