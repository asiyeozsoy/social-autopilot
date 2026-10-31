"""One-off: turn the week-1 TinyNotes pack into queue folders under content/tinynotes/.

python tools/build_tinynotes_week1.py <pack folder with 01_..06_ subfolders>
"""
import shutil
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
TZ = "+01:00"  # Skopje, winter time

POSTS = [
    ("01_pazartesi_2kasim", "2026-11-02", "1500", "monday",
     ("you don't have to fix the whole week before breakfast ☕",
      "Know someone running on empty today? This one's for their inbox.",
      "#sendthistosomeone #mondaymotivation #gentlereminder #mondaymood #smallsteps"),
     ("monday, but make it gentle 🤍",
      "forward to the friend who already said \"i'm so tired\" today",
      "#sendthistosomeone #mondayblues #softlife #motivation #fyp")),
    ("02_sali_3kasim_anne", "2026-11-03", "1500", "mom",
     ("for the woman who still checks if you got home safe 🏡",
      "Send it to her. She'll screenshot it, trust me.",
      "#sendthistosomeone #momlove #thankyoumom #motherdaughter #familyfirst"),
     ("she'll pretend she's not crying",
      "send this to mom and report back 🥹",
      "#sendthistosomeone #mom #momtok #grateful #fyp")),
    ("03_carsamba_4kasim_kanka", "2026-11-04", "1500", "bestie",
     ("every chaotic friend group has a calm one. who's yours? 🫶",
      "Drop their @ in the comments or slide it into their DMs.",
      "#sendthistosomeone #bestfriends #friendshipquotes #bff #soulfriend"),
     ("for my person, no explanation needed",
      "tag the one who's been there since day one 👇",
      "#sendthistosomeone #bestie #friendship #besties #fyp")),
    ("04_persembe_5kasim_buyukgun", "2026-11-05", "1500", "bigday",
     ("exam, interview, first day… whatever tomorrow holds 🍀",
      "Someone you love needs this before bed tonight. Share it.",
      "#sendthistosomeone #goodluck #examseason #youvegotthis #believeinyourself"),
     ("the night-before text they actually need",
      "send it to the one who's overthinking tomorrow",
      "#sendthistosomeone #examday #goodluck #studytok #fyp")),
    ("05_cuma_6kasim_sevgili", "2026-11-06", "1500", "weekend",
     ("the only weekend plan that matters 💌",
      "Send it to them. Let them guess what you're hinting at.",
      "#sendthistosomeone #couplegoals #weekendvibes #lovenotes #slowweekend"),
     ("no alarms, no plans, just us",
      "send this to your person and see what they reply 👀",
      "#sendthistosomeone #couples #relationship #friyay #fyp")),
    ("06_pazar_8kasim_kaydirmali", "2026-11-08", "1500", "reminders",
     ("read them slowly, keep the one you needed most 📌",
      "Save this for Wednesday. Share it with whoever's had a long week.",
      "#sendthistosomeone #selfcarereminder #weeklyreset #mentalhealthmatters #sundayreset"),
     ("swipe → which one hit hardest?",
      "comment the number, then pass it to a friend",
      "#sendthistosomeone #sundayreset #selfcare #reminder #fyp")),
]


def caption(parts):
    text, cta, tags = parts
    return f"{text}\n\n{cta}\n\n{tags}"


def main(pack: Path):
    out_root = ROOT / "content" / "tinynotes"
    for src_name, day, hhmm, slug, ig, tt in POSTS:
        src = pack / src_name
        dst = out_root / f"{day}_{hhmm}_{slug}"
        dst.mkdir(parents=True, exist_ok=True)
        ig_files = sorted(p.name for p in src.glob("instagram*.png"))
        tt_files = sorted(p.name for p in src.glob("tiktok*.png"))
        for f in ig_files + tt_files:
            shutil.copy2(src / f, dst / f)
        spec = {
            "brand": "tinynotes",
            "publish_at": f"{day}T{hhmm[:2]}:{hhmm[2:]}:00{TZ}",
            "platforms": {
                "instagram": {"kind": "carousel" if len(ig_files) > 1 else "image",
                              "media": ig_files, "caption": caption(ig)},
                "tiktok": {"kind": "photo", "media": tt_files, "caption": caption(tt)},
            },
        }
        (dst / "post.yaml").write_text(yaml.safe_dump(spec, allow_unicode=True, sort_keys=False), encoding="utf-8")
        print("queued", dst.relative_to(ROOT))


if __name__ == "__main__":
    main(Path(sys.argv[1]))
