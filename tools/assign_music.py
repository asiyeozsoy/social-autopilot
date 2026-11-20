"""Give every upcoming reel a slow-piano track from Instagram's music library (audio_id in
post.yaml -> instagram). Rotates the pool so neighbouring posts never share a track, and
matches a few themes (rain, winter/christmas). Facebook/YouTube/TikTok keep the video's own lo-fi.

python tools/assign_music.py [--brand tinynotes] [--force]
"""
import argparse
import datetime as dt
import glob
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
# Instagram library tracks found with the Audio API (searches: slow / sad / emotional / calm / soft piano)
POOL = [
    ("2477944699150252", "Peaceful Piano - Dr. Pheel"),
    ("350265329652625", "Memories Are Forever - Brent Bourgeois"),
    ("954265876232572", "Nostalgic Piano Reverie - Daria Novo"),
    ("296861997666070", "The Nature Of Memories - Dhruv Goel"),
    ("1367487581578605", "Breathe Again - Magnetic Sirens"),
    ("819173022431906", "Summer's Autumn - Brian Withycombe"),
    ("134367083941949", "Moments Emotional - Scott Dugdale"),
    ("1011178941789966", "Riverbank - Goldenrod"),
    ("534836465627737", "Midnight Dreamer - Giulio Cercato"),
    ("976299230340697", "Someday (Instrumental) - Cy Curnin"),
    ("2263439694405407", "Golden Ascent - Afterlight"),
    ("1214608611732450", "Little Things - Giulio Cercato"),
    ("1866485437031985", "Understory - Ross Lara"),
    ("1140588937751449", "New Horizons - Giulio Cercato"),
]
THEMES = [
    (("rain", "storm", "umbrella", "two-ways"), ("3015012582136708", "Piano On A Rainy Day - Cy Curnin")),
    (("christmas", "its-time", "winter", "snow", "december", "xmas", "cozy"), ("1183861130553498", "Winter - Giulio Cercato")),
]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--brand", default="tinynotes")
    ap.add_argument("--force", action="store_true")
    a = ap.parse_args()
    now = dt.datetime.now(dt.timezone.utc)
    posts = []
    for f in glob.glob(str(ROOT / f"content/{a.brand}/*/post.yaml")):
        d = yaml.safe_load(open(f))
        t = dt.datetime.fromisoformat(str(d["publish_at"]))
        ig = (d.get("platforms") or {}).get("instagram") or {}
        if t > now and ig.get("kind") == "reel":
            posts.append((t, Path(f), d))
    posts.sort(key=lambda x: x[0])
    i = 0
    for t, f, d in posts:
        ig = d["platforms"]["instagram"]
        if ig.get("audio_id") and not a.force:
            continue
        slug = f.parent.name
        pick = next((trk for keys, trk in THEMES if any(k in slug for k in keys)), None)
        if pick is None:
            pick = POOL[i % len(POOL)]
            i += 1
        ig["audio_id"], ig["audio_title"] = pick
        f.write_text(yaml.safe_dump(d, allow_unicode=True, sort_keys=False))
        print(f"{t:%m-%d %H:%M} {slug:45} {pick[1]}")


if __name__ == "__main__":
    main()
