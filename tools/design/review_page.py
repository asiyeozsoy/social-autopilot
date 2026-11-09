"""Dark, phone-friendly review page of upcoming queue items, served by GitHub Pages.

python tools/design/review_page.py [pattern ...]   -> content/_share/review.html
Patterns match folder slugs (default: the character videos).
"""
import datetime as dt
import html
import re
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[2]
CONTENT = ROOT / "content"
PATTERNS = sys.argv[1:] or ["_hf-", "_tiny0", "_bear-", "_sign"]
DAYS = ["Pazartesi", "Salı", "Çarşamba", "Perşembe", "Cuma", "Cumartesi", "Pazar"]
MONTHS = ["", "Ocak", "Şubat", "Mart", "Nisan", "Mayıs", "Haziran", "Temmuz", "Ağustos", "Eylül", "Ekim", "Kasım", "Aralık"]
LABEL = {"tinynotes": "TinyNotes", "factyeap": "Factyeap"}

now = dt.datetime.now(dt.timezone(dt.timedelta(hours=1)))
items = []
for post in CONTENT.glob("*/*/post.yaml"):
    folder = post.parent
    if not any(p in folder.name for p in PATTERNS) or not ((folder / "video.mp4").exists() or (folder / "post.jpg").exists()):
        continue
    data = yaml.safe_load(post.read_text())
    when = dt.datetime.fromisoformat(str(data["publish_at"]))
    if when < now:
        continue
    ig = (data.get("platforms") or {}).get("instagram") or {}
    items.append((when, folder.parent.name, folder, ig.get("caption", "")))
items.sort()

cards, last_day = [], None
for when, brand, folder, caption in items:
    day = when.date()
    if day != last_day:
        cards.append(f'<h2>{day.day} {MONTHS[day.month]} · {DAYS[day.weekday()]}</h2>')
        last_day = day
    rel = f"../{brand}/{folder.name}"
    poster = f' poster="{rel}/cover.jpg"' if (folder / "cover.jpg").exists() else ""
    slug = re.sub(r"^\d{4}-\d\d-\d\d_\d{4}_", "", folder.name)
    first = html.escape(caption.split("\n\n")[0])
    rest = html.escape("\n\n".join(caption.split("\n\n")[1:]))
    media = (f'<video src="{rel}/video.mp4"{poster} controls playsinline preload="none"></video>' if (folder / "video.mp4").exists()
             else f'<img src="{rel}/post.jpg" alt="" loading="lazy" style="width:100%;border-radius:12px;display:block">')
    cards.append(f"""<article class="{brand}">
  <div class="meta"><span class="time">{when:%H:%M}</span><span class="brand">{LABEL.get(brand, brand)}</span><span class="slug">{slug}</span></div>
  {media}
  <p class="hook">{first}</p>
  <details><summary>Açıklamanın tamamı</summary><pre>{rest}</pre></details>
</article>""")

page = f"""<!doctype html>
<html lang="tr"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta name="robots" content="noindex">
<title>Sıradaki videolar</title>
<style>
:root {{ --bg:#121010; --card:#1c1817; --ink:#efe7dc; --muted:#a3968d; --tiny:#f08f8a; --fact:#f0b04a; }}
* {{ box-sizing:border-box; }}
body {{ margin:0; background:var(--bg); color:var(--ink); font:16px/1.45 -apple-system,system-ui,"Segoe UI",Roboto,sans-serif; }}
main {{ max-width:520px; margin:0 auto; padding:20px 16px 60px; }}
h1 {{ font-size:22px; margin:4px 0 2px; }}
.sub {{ color:var(--muted); margin:0 0 8px; font-size:14px; }}
h2 {{ position:sticky; top:0; z-index:2; background:var(--bg); margin:26px 0 10px; padding:10px 0 8px; font-size:17px; border-bottom:1px solid #2c2623; }}
article {{ background:var(--card); border-radius:16px; padding:12px; margin:0 0 16px; border-left:4px solid var(--fact); }}
article.tinynotes {{ border-left-color:var(--tiny); }}
.meta {{ display:flex; gap:8px; align-items:baseline; flex-wrap:wrap; margin-bottom:8px; }}
.time {{ font-weight:700; font-size:18px; }}
.brand {{ font-size:13px; font-weight:600; padding:2px 8px; border-radius:99px; background:#2c2623; color:var(--fact); }}
.tinynotes .brand {{ color:var(--tiny); }}
.slug {{ color:var(--muted); font-size:13px; }}
video {{ width:100%; aspect-ratio:9/16; border-radius:12px; background:#000; display:block; }}
.hook {{ margin:10px 2px 4px; font-weight:600; }}
details {{ color:var(--muted); font-size:14px; }}
summary {{ cursor:pointer; padding:4px 2px; }}
pre {{ white-space:pre-wrap; font:inherit; margin:6px 2px; }}
</style></head>
<body><main>
<h1>Sıradaki videolar</h1>
<p class="sub">{len(items)} video · {now:%d.%m %H:%M} itibarıyla · videoya dokununca oynar</p>
{chr(10).join(cards)}
</main></body></html>
"""
out = CONTENT / "_share" / "review.html"
out.write_text(page)
print(out, len(items))
