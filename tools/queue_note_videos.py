"""Render TinyNotes note videos from a spec file and queue them on all three platforms.

python tools/queue_note_videos.py tools/design/tinynotes_videos_batch1.json [HHMM]

Each entry: {date, [time HHMM], slug, hook, note, sign, ig:[text,cta,tags], tt:[...], yt:[title, description]}
"""
import json
import sys
from pathlib import Path

import yaml

sys.path.insert(0, str(Path(__file__).resolve().parent / "design"))
from tinynotes_video import render  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
TZ = "+01:00"


def main(spec_file, hhmm="1800"):
    default = hhmm
    for item in json.loads(Path(spec_file).read_text(encoding="utf-8")):
        hhmm = item.get("time", default)
        dst = ROOT / "content" / "tinynotes" / f"{item['date']}_{hhmm}_{item['slug']}-video"
        dst.mkdir(parents=True, exist_ok=True)
        video = dst / "video.mp4"
        if not video.exists():
            render(video, item["hook"], item["note"], item["sign"], item["slug"])
        spec = {
            "brand": "tinynotes",
            "publish_at": f"{item['date']}T{hhmm[:2]}:{hhmm[2:]}:00{TZ}",
            "platforms": {
                "instagram": {"kind": "reel", "media": ["video.mp4"], "caption": "\n\n".join(item["ig"])},
                "tiktok": {"kind": "video", "media": ["video.mp4"], "caption": "\n\n".join(item["tt"])},
                "youtube": {"kind": "short", "media": ["video.mp4"], "title": item["yt"][0],
                            "description": item["yt"][1] + "\n\n#tinynotes #sendthistosomeone #shorts"},
            },
        }
        (dst / "post.yaml").write_text(yaml.safe_dump(spec, allow_unicode=True, sort_keys=False), encoding="utf-8")
        print("queued", dst.relative_to(ROOT))


if __name__ == "__main__":
    main(sys.argv[1], *(sys.argv[2:3]))
