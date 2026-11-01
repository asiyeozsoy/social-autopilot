"""Queue TinyNotes Facebook-only morning cards (08:30 Skopje time), one per day.

python tools/queue_fb_daily.py tools/design/fb_daily_batch1.json
"""
import json
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools/design"))
from fb_daily import card  # noqa: E402

batch = json.loads(Path(sys.argv[1]).read_text())
for item in batch:
    folder = ROOT / "content/tinynotes" / f"{item['date']}_0830_fb-{item['slug']}"
    folder.mkdir(parents=True, exist_ok=True)
    card(item["kind"], item["main"], item["sub"], item["label"], item["slug"]).save(folder / "facebook.png")
    spec = {"brand": "tinynotes", "publish_at": f"{item['date']}T08:30:00+01:00",
            "platforms": {"facebook": {"kind": "image", "media": ["facebook.png"], "caption": item["caption"]}}}
    (folder / "post.yaml").write_text(yaml.safe_dump(spec, allow_unicode=True, sort_keys=False), encoding="utf-8")
    print(folder.name)
