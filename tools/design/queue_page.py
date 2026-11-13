"""Everything still to be posted, as one dark phone-friendly page: a grid of covers per day,
tap a video to play it, carousels scroll sideways, captions fold open.

python tools/design/queue_page.py [--abs out.html]
  -> content/_share/queue.html (relative links, served by Pages)
  --abs also writes a copy with absolute Pages links (for opening outside Pages).
"""
import argparse
import datetime as dt
import html
import re
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[2]
CONTENT = ROOT / "content"
BASE = "https://asiyeozsoy.github.io/social-autopilot"
DAYS = ["Pazartesi", "Salı", "Çarşamba", "Perşembe", "Cuma", "Cumartesi", "Pazar"]
MONTHS = ["", "Ocak", "Şubat", "Mart", "Nisan", "Mayıs", "Haziran", "Temmuz", "Ağustos", "Eylül", "Ekim", "Kasım", "Aralık"]
LABEL = {"tinynotes": "TinyNotes", "factyeap": "Factyeap"}
TZ = dt.timezone(dt.timedelta(hours=1))


def build(prefix):
    now = dt.datetime.now(TZ)
    items = []
    for post in CONTENT.glob("*/*/post.yaml"):
        folder = post.parent
        if folder.parent.name.startswith("_"):
            continue
        data = yaml.safe_load(post.read_text())
        when = dt.datetime.fromisoformat(str(data["publish_at"])).astimezone(TZ)
        if when < now:
            continue
        ig = (data.get("platforms") or {}).get("instagram") or {}
        yt = (data.get("platforms") or {}).get("youtube") or {}
        items.append((when, folder.parent.name, folder, ig, yt))
    items.sort(key=lambda x: x[0])
    out, last, counts = [], None, {"video": 0, "post": 0}
    for when, brand, folder, ig, yt in items:
        if when.date() != last:
            if last is not None:
                out.append("</div>")
            last = when.date()
            out.append(f'<h2>{last.day} {MONTHS[last.month]} · {DAYS[last.weekday()]}</h2><div class="grid">')
        rel = f"{prefix}{brand}/{folder.name}"
        cap = ig.get("caption") or yt.get("description") or ""
        hook = html.escape(cap.split("\n")[0][:90])
        rest = html.escape(cap)
        if (folder / "video.mp4").exists():
            counts["video"] += 1
            poster = f' poster="{rel}/cover.jpg"' if (folder / "cover.jpg").exists() else ""
            media = f'<video src="{rel}/video.mp4"{poster} controls playsinline preload="none"></video>'
            kind = "video"
        else:
            counts["post"] += 1
            imgs = [m for m in (ig.get("media") or []) if (folder / m).exists()] or \
                   [p.name for p in sorted(folder.glob("*.jpg")) if p.name != "cover.jpg"][:1]
            media = '<div class="car">' + "".join(f'<img src="{rel}/{m}" loading="lazy" alt="">' for m in imgs) + "</div>"
            kind = f"{len(imgs)} slayt" if len(imgs) > 1 else "post"
        out.append(f'<article class="{brand}"><div class="meta"><b>{when:%H:%M}</b><span class="b">{LABEL.get(brand, brand)}</span>'
                   f'<span class="k">{kind}</span></div>{media}<details><summary>{hook}</summary><pre>{rest}</pre></details></article>')
    if last is not None:
        out.append("</div>")
    return f"""<!doctype html><html lang="tr"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<meta name="robots" content="noindex"><title>Paylaşım sırası</title><style>
:root{{--bg:#121010;--card:#1c1817;--ink:#efe7dc;--mut:#a3968d;--tiny:#f08f8a;--fact:#f0b04a}}
*{{box-sizing:border-box}}body{{margin:0;background:var(--bg);color:var(--ink);font:14px/1.4 -apple-system,system-ui,sans-serif}}
main{{max-width:1100px;margin:0 auto;padding:16px 12px 60px}}h1{{font-size:20px;margin:4px 0}}.sub{{color:var(--mut);margin:0 0 6px}}
h2{{position:sticky;top:0;z-index:2;background:var(--bg);margin:20px 0 8px;padding:8px 0;font-size:16px;border-bottom:1px solid #2c2623}}
.grid{{display:grid;grid-template-columns:repeat(auto-fill,minmax(160px,1fr));gap:10px}}
article{{background:var(--card);border-radius:12px;padding:8px;border-top:3px solid var(--fact);min-width:0}}article.tinynotes{{border-top-color:var(--tiny)}}
.meta{{display:flex;gap:6px;align-items:baseline;margin-bottom:6px;font-size:12px}}.b{{color:var(--fact)}}.tinynotes .b{{color:var(--tiny)}}.k{{color:var(--mut);margin-left:auto}}
video,.car img{{width:100%;aspect-ratio:9/16;object-fit:cover;border-radius:8px;background:#000;display:block}}
.car{{display:flex;overflow-x:auto;scroll-snap-type:x mandatory;gap:4px}}.car img{{flex:0 0 100%;scroll-snap-align:start;aspect-ratio:4/5}}
details{{margin-top:6px;color:var(--mut);font-size:12px}}summary{{cursor:pointer;color:var(--ink)}}pre{{white-space:pre-wrap;font:inherit;margin:4px 0 0}}
</style></head><body><main><h1>Paylaşım sırası</h1>
<p class="sub">{counts['video']} video · {counts['post']} post · {dt.datetime.now(TZ):%d.%m %H:%M} itibarıyla · videoya dokununca oynar, karuseller yana kayar</p>
{chr(10).join(out)}</main></body></html>"""


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--abs")
    a = ap.parse_args()
    (CONTENT / "_share" / "queue.html").write_text(build("../"))
    if a.abs:
        Path(a.abs).write_text(build(BASE + "/"))
    print("ok")
