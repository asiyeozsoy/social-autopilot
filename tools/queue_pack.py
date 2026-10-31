"""Queue a rendered TinyNotes week from a spec file.

python tools/queue_pack.py <spec.json> <pack folder>

spec.json: list of {"id", "date", "time" (HHMM), "slug", "ig": [text, cta, tags], "tt": [text, cta, tags]}
The pack folder holds one subfolder per id with instagram*.png and tiktok*.png.
"""
import json
import shutil
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
TZ = "+01:00"  # Skopje winter time; use +02:00 from the last Sunday of March


def caption(parts):
    return "\n\n".join(parts)


def main(spec_file: Path, pack: Path, brand="tinynotes"):
    for item in json.loads(spec_file.read_text(encoding="utf-8")):
        if "date" not in item:
            continue
        src = pack / item["id"]
        dst = ROOT / "content" / brand / f"{item['date']}_{item['time']}_{item['slug']}"
        dst.mkdir(parents=True, exist_ok=True)
        ig = sorted(p.name for p in src.glob("instagram*.png"))
        tt = sorted(p.name for p in src.glob("tiktok*.png"))
        for f in ig + tt:
            shutil.copy2(src / f, dst / f)
        spec = {
            "brand": brand,
            "publish_at": f"{item['date']}T{item['time'][:2]}:{item['time'][2:]}:00{TZ}",
            "platforms": {
                "instagram": {"kind": "carousel" if len(ig) > 1 else "image", "media": ig, "caption": caption(item["ig"])},
                "tiktok": {"kind": "photo", "media": tt, "caption": caption(item["tt"])},
            },
        }
        (dst / "post.yaml").write_text(yaml.safe_dump(spec, allow_unicode=True, sort_keys=False), encoding="utf-8")
        print("queued", dst.relative_to(ROOT))


if __name__ == "__main__":
    main(Path(sys.argv[1]), Path(sys.argv[2]))
