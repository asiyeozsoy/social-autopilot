"""TikTok hand-off feed: one phone-friendly page (and JSON) listing what to post on TikTok.

TikTok is posted outside the autopilot (by hand or by another assistant). This page gives that
poster everything in one place: when, which brand account, the direct file link and the caption.
Landscape videos get a vertical 1080x1920 copy (blurred fill) as video_tiktok.mp4, so TikTok
shows them full screen.

python tools/tiktok_feed.py            -> content/_share/tiktok.html + tiktok.json
"""
import datetime as dt
import html
import json
import re
import subprocess
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
CONTENT = ROOT / "content"
BASE = "https://asiyeozsoy.github.io/social-autopilot"
ACCOUNTS = {"factyeap": "@factyeap", "tinynotes": "@tinynotesforu"}
TZ = dt.timezone(dt.timedelta(hours=1))
DAYS_BACK, DAYS_AHEAD = 1, 10


def size(video):
    out = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries", "stream=width,height",
                          "-of", "csv=p=0", str(video)], capture_output=True, text=True).stdout.strip()
    w, h = (int(x) for x in out.split(",")[:2])
    return w, h


def vertical_copy(video):
    out = video.with_name("video_tiktok.mp4")
    if out.exists() and out.stat().st_mtime >= video.stat().st_mtime:
        return out
    vf = ("[0:v]split[a][b];[a]scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920,boxblur=30:3,"
          "eq=brightness=-0.08[bg];[b]scale=1080:-2[fg];[bg][fg]overlay=(W-w)/2:(H-h)/2,format=yuv420p")
    subprocess.run(["ffmpeg", "-nostdin", "-loglevel", "error", "-y", "-i", str(video), "-filter_complex", vf,
                    "-c:v", "libx264", "-preset", "veryfast", "-crf", "20", "-c:a", "copy", str(out)], check=True)
    return out


def tiktok_caption(caption):
    cap = re.sub(r"#factyeap\b|#tinynotes\b", "", caption or "").strip()
    if "#fyp" not in cap:
        cap += " #fyp"
    return cap[:2150]


def main():
    now = dt.datetime.now(TZ)
    items = []
    for post in sorted(CONTENT.glob("*/*/post.yaml")):
        folder = post.parent
        if folder.parent.name.startswith("_"):
            continue
        data = yaml.safe_load(post.read_text())
        when = dt.datetime.fromisoformat(str(data["publish_at"])).astimezone(TZ)
        if not (now - dt.timedelta(days=DAYS_BACK) <= when <= now + dt.timedelta(days=DAYS_AHEAD)):
            continue
        ig = (data.get("platforms") or {}).get("instagram") or {}
        rel = f"{folder.parent.name}/{folder.name}"
        video = folder / "video.mp4"
        if video.exists():
            w, h = size(video)
            src = vertical_copy(video) if w > h else video
            files = [f"{BASE}/{rel}/{src.name}"]
            kind = "video"
        else:
            imgs = [m for m in (ig.get("media") or []) if (folder / m).exists()]
            if not imgs:
                continue
            files = [f"{BASE}/{rel}/{m}" for m in imgs]
            kind = "photo"
        items.append({"when": when.isoformat(timespec="minutes"), "account": ACCOUNTS.get(folder.parent.name, folder.parent.name),
                      "kind": kind, "files": files, "cover": f"{BASE}/{rel}/cover.jpg" if (folder / "cover.jpg").exists() else None,
                      "caption": tiktok_caption(ig.get("caption")), "id": rel})
    items.sort(key=lambda x: x["when"])
    share = CONTENT / "_share"
    share.mkdir(exist_ok=True)
    (share / "tiktok.json").write_text(json.dumps({"generated": now.isoformat(timespec="minutes"), "timezone": "UTC+01:00",
                                                    "posts": items}, ensure_ascii=False, indent=1))
    rows = []
    for it in items:
        when = dt.datetime.fromisoformat(it["when"])
        links = " ".join(f'<a href="{f}">{"video" if it["kind"] == "video" else f"foto {i + 1}"}</a>' for i, f in enumerate(it["files"]))
        past = " past" if when < now else ""
        rows.append(f'<article class="{past}"><div class="meta"><b>{when:%d.%m %H:%M}</b> <span>{it["account"]}</span> '
                    f'<span class="k">{it["kind"]}</span></div><div class="links">{links}</div>'
                    f'<pre>{html.escape(it["caption"])}</pre></article>')
    page = f"""<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<meta name="robots" content="noindex"><title>TikTok queue</title><style>
body{{margin:0;background:#121010;color:#efe7dc;font:15px/1.45 system-ui,sans-serif}}main{{max-width:560px;margin:0 auto;padding:18px 16px 60px}}
article{{background:#1c1817;border-radius:14px;padding:12px;margin:0 0 12px}}article.past{{opacity:.55}}.meta span{{color:#f0b04a;margin-left:6px}}
.k{{color:#a3968d!important}}a{{color:#f08f8a}}.links{{margin:6px 0}}pre{{white-space:pre-wrap;font:inherit;color:#cfc4b8;margin:0}}</style></head>
<body><main><h1>TikTok queue</h1><p>Post each item at its time (UTC+1) on the named TikTok account, using the file link and caption as given.
Vertical copies are already made for landscape videos. Machine-readable: <a href="tiktok.json">tiktok.json</a>.</p>
{chr(10).join(rows)}</main></body></html>"""
    (share / "tiktok.html").write_text(page)
    print(len(items), "items")


if __name__ == "__main__":
    main()
