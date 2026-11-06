"""Write cover.jpg for queued reels whose first frame is blank (notes that write themselves):
the cover is a frame near the end, when the whole note is on screen. Instagram uses it as the
Reels cover / profile grid thumbnail.

python tools/make_covers.py [brand ...]      (default: tinynotes)
"""
import datetime as dt
import json
import subprocess
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]


def duration(p):
    out = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "json", str(p)],
                         capture_output=True, text=True).stdout
    return float(json.loads(out)["format"]["duration"])


def main(brands):
    now = dt.datetime.now(dt.timezone.utc)
    made = 0
    for brand in brands:
        for spec in sorted((ROOT / "content" / brand).glob("*/post.yaml")):
            folder = spec.parent
            y = yaml.safe_load(spec.read_text(encoding="utf-8"))
            ig = (y.get("platforms") or {}).get("instagram") or {}
            if ig.get("kind") != "reel" or (folder / "cover.jpg").exists():
                continue
            when = dt.datetime.fromisoformat(str(y["publish_at"]))
            if when < now:
                continue
            video = folder / ig["media"][0]
            # catalogue shorts end on a "follow for more" card, so use an early frame there
            t = 1.2 if "_cat" in video.parent.name else max(0.0, duration(video) - 0.9)
            subprocess.run(["ffmpeg", "-nostdin", "-loglevel", "error", "-y", "-ss", f"{t:.2f}", "-i", str(video),
                            "-frames:v", "1", "-q:v", "3", str(folder / "cover.jpg")], check=True)
            made += 1
    print(f"{made} covers written")


if __name__ == "__main__":
    main(sys.argv[1:] or ["tinynotes"])
