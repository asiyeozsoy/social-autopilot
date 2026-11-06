"""Render crumpled-paper note videos from a spec file and queue them for TinyNotes.

python tools/queue_handnotes.py tools/design/handnotes_batch1.json [HHMM] [index ...]
"""
import json
import sys
from pathlib import Path

import yaml

sys.path.insert(0, str(Path(__file__).resolve().parent / "design"))
from handnote2 import render  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent


def main(spec, hhmm="1300", only=None):
    items = json.loads(Path(spec).read_text(encoding="utf-8"))
    for i, it in enumerate(items):
        if only and i not in only:
            continue
        dst = ROOT / "content" / "tinynotes" / f"{it['date']}_{hhmm}_{it['slug']}-note"
        dst.mkdir(parents=True, exist_ok=True)
        if not (dst / "video.mp4").exists():
            render(dst / "video.mp4", "crumple", it["text"], it["doodle"], seed=i + 10)
        title = it["text"].replace("\n", " ")
        cap = f"{it['ig']}\n\n{it['cta']}\n\n{it['tags']}"
        post = {"brand": "tinynotes", "publish_at": f"{it['date']}T{hhmm[:2]}:{hhmm[2:]}:00+01:00", "platforms": {
            "instagram": {"kind": "reel", "media": ["video.mp4"], "caption": cap},
            "tiktok": {"kind": "video", "media": ["video.mp4"], "caption": f"{it['ig']}\n\n{it['cta'].lower()}\n\n#sendthistosomeone #love #fyp"},
            "youtube": {"kind": "short", "media": ["video.mp4"], "title": f"{title} 🤍", "description": cap + "\n\n#shorts"}}}
        (dst / "post.yaml").write_text(yaml.safe_dump(post, allow_unicode=True, sort_keys=False, width=1000), encoding="utf-8")
        print("queued", dst.name, flush=True)


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2] if len(sys.argv) > 2 else "1300", {int(x) for x in sys.argv[3:]} or None)


# every queued note gets its finished-note frame as the Reels cover
import subprocess as _sp  # noqa: E402
_sp.run([sys.executable, str(Path(__file__).resolve().parent / "make_covers.py"), "tinynotes"], check=False)
