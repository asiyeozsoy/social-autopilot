"""Dump a brand's YouTube uploads (title, description, duration, views) and its
Instagram reel captions to plans/catalog_<brand>.json, so older YouTube videos
can be queued for Instagram/Facebook/TikTok without duplicates.

python tools/yt_catalog.py factyeap
"""
import json
import sys
from pathlib import Path

import requests

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from autopilot.platforms.youtube import _access_token  # noqa: E402
from autopilot.backfill import ig_reels  # noqa: E402

API = "https://www.googleapis.com/youtube/v3"
brand = sys.argv[1]
h = {"Authorization": f"Bearer {_access_token(brand)}"}
ch = requests.get(f"{API}/channels", params={"part": "contentDetails,snippet", "mine": "true"}, headers=h, timeout=30).json()
uploads = ch["items"][0]["contentDetails"]["relatedPlaylists"]["uploads"]
ids, tok = [], None
while True:
    r = requests.get(f"{API}/playlistItems", params={"part": "contentDetails", "playlistId": uploads, "maxResults": 50,
                                                     **({"pageToken": tok} if tok else {})}, headers=h, timeout=30).json()
    ids += [i["contentDetails"]["videoId"] for i in r.get("items", [])]
    tok = r.get("nextPageToken")
    if not tok:
        break
videos = []
for i in range(0, len(ids), 50):
    r = requests.get(f"{API}/videos", params={"part": "snippet,contentDetails,statistics", "id": ",".join(ids[i:i + 50])},
                     headers=h, timeout=30).json()
    for v in r.get("items", []):
        s = v["snippet"]
        videos.append({"id": v["id"], "published": s["publishedAt"], "title": s["title"], "description": s.get("description", ""),
                       "tags": s.get("tags", []), "duration": v["contentDetails"]["duration"],
                       "views": int(v.get("statistics", {}).get("viewCount", 0))})
videos.sort(key=lambda v: v["published"])
try:
    ig = [{"id": m["id"], "timestamp": m["timestamp"], "caption": (m.get("caption") or "")[:300], "permalink": m.get("permalink")}
          for m in ig_reels(brand)]
except Exception as e:  # noqa: BLE001
    ig = [{"error": str(e)[:200]}]
out = Path(__file__).resolve().parents[1] / "plans" / f"catalog_{brand}.json"
out.write_text(json.dumps({"channel": ch["items"][0]["snippet"]["title"], "youtube": videos, "instagram_reels": ig},
                          indent=1, ensure_ascii=False) + "\n")
print(f"{len(videos)} youtube videos, {len(ig)} instagram reels -> {out.name}")
