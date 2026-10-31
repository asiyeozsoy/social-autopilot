"""Render Factyeap FACT posts/videos from a spec file and queue them.

python tools/queue_factyeap.py tools/design/factyeap_batch1.json [HHMM]

Posts go to Instagram (image) and TikTok (photo); videos go to Instagram (reel),
TikTok and YouTube Shorts.
"""
import json
import sys
from pathlib import Path

import yaml

sys.path.insert(0, str(Path(__file__).resolve().parent / "design"))
import factyeap_render as fr  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
TZ = "+01:00"


def main(spec_file, hhmm="1900"):
    for item in json.loads(Path(spec_file).read_text(encoding="utf-8")):
        dst = ROOT / "content" / "factyeap" / f"{item['date']}_{hhmm}_fact{item['n']:03d}-{item['slug']}"
        dst.mkdir(parents=True, exist_ok=True)
        ig_caption = f"{item['ig']}\n\n{item['cta']}\n\n{item['tags']}"
        tt_caption = f"{item['tt']}\n\n{item['cta']}\n\n{item['tt_tags']}"
        if item["kind"] == "post":
            if not (dst / "instagram.png").exists():
                fr.post(dst, item["n"], item["fact"])
            platforms = {
                "instagram": {"kind": "image", "media": ["instagram.png"], "caption": ig_caption},
                "tiktok": {"kind": "photo", "media": ["tiktok.png"], "caption": tt_caption},
            }
        else:
            if not (dst / "video.mp4").exists():
                fr.video(dst / "video.mp4", item["n"], item["fact"])
            platforms = {
                "instagram": {"kind": "reel", "media": ["video.mp4"], "caption": ig_caption},
                "tiktok": {"kind": "video", "media": ["video.mp4"], "caption": tt_caption},
                "youtube": {"kind": "short", "media": ["video.mp4"], "title": item["yt"],
                            "description": f"{item['fact']}\n\n{item['cta']}\n\n#factyeap #relatable #yeap #shorts"},
            }
        spec = {"brand": "factyeap", "publish_at": f"{item['date']}T{hhmm[:2]}:{hhmm[2:]}:00{TZ}", "platforms": platforms}
        (dst / "post.yaml").write_text(yaml.safe_dump(spec, allow_unicode=True, sort_keys=False), encoding="utf-8")
        print("queued", dst.relative_to(ROOT))


if __name__ == "__main__":
    main(sys.argv[1], *(sys.argv[2:3]))
