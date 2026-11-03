"""Mirror older Instagram reels to the brand's Facebook Page with the same caption.

Only reels posted before the autopilot (or by hand) are considered; anything the
autopilot published itself is already on Facebook. A few per run, oldest first,
so the Page isn't flooded. Progress is kept in state/backfill.json.

python -m autopilot.backfill [per_brand]
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import requests

from .platforms.base import check, creds, poll, PublishError
from .platforms.facebook import API, VERSION, page_token
from .platforms.instagram import api_base

ROOT = Path(__file__).resolve().parents[1]
STATE = ROOT / "state" / "backfill.json"
BRANDS = ("factyeap", "tinynotes")


def load():
    return json.loads(STATE.read_text()) if STATE.exists() else {}


def save(d):
    STATE.parent.mkdir(exist_ok=True)
    STATE.write_text(json.dumps(d, indent=2, sort_keys=True) + "\n")


def ig_reels(brand):
    tok, uid = creds(brand, "IG_TOKEN"), creds(brand, "IG_USER_ID")
    out, url = [], f"{api_base(tok)}/{uid}/media"
    params = {"fields": "id,caption,media_type,media_product_type,media_url,permalink,timestamp", "limit": 50, "access_token": tok}
    while url:
        body = requests.get(url, params=params, timeout=60).json()
        out += [m for m in body.get("data", []) if m.get("media_type") == "VIDEO"]
        url, params = (body.get("paging") or {}).get("next"), None
    return sorted(out, key=lambda m: m["timestamp"])


def autopilot_ig_ids():
    pub = json.loads((ROOT / "state" / "published.json").read_text())
    return {v.get("remote_id") for k, v in pub.items() if k.endswith("::instagram")}


def fb_reel(page_id, tok, video_url, caption):
    r = requests.post(f"{API}/{page_id}/video_reels", data={"upload_phase": "start", "access_token": tok}, timeout=60)
    vid = check(r, "facebook reel start")["video_id"]
    up = requests.post(f"https://rupload.facebook.com/video-upload/{VERSION}/{vid}",
                       headers={"Authorization": f"OAuth {tok}", "file_url": video_url}, timeout=300)
    if not up.ok or not up.json().get("success"):
        raise PublishError(f"facebook reel upload failed ({up.status_code}): {up.text[:200]}")
    poll(lambda: requests.get(f"{API}/{vid}", params={"fields": "status", "access_token": tok}, timeout=30).json().get("status", {}),
         done=lambda s: (s.get("uploading_phase") or {}).get("status") == "complete",
         fail=lambda s: (s.get("uploading_phase") or {}).get("status") == "error", every=5, timeout=600, what="reel upload")
    r = requests.post(f"{API}/{page_id}/video_reels", data={"upload_phase": "finish", "video_id": vid, "video_state": "PUBLISHED",
                                                            "description": caption, "is_ai_generated": "true", "access_token": tok}, timeout=120)
    check(r, "facebook reel publish")
    return vid


def main(per_brand=2):
    state, skip = load(), autopilot_ig_ids()
    for brand in BRANDS:
        done = state.setdefault(brand, {})
        try:
            reels = [m for m in ig_reels(brand) if m["id"] not in skip and m["id"] not in done and m.get("media_url")]
            page_id = creds(brand, "FB_PAGE_ID")
            tok = page_token(page_id)
        except Exception as e:
            print(f"::warning::{brand}: backfill skipped ({str(e)[:150]})")
            continue
        print(f"{brand}: {len(reels)} older reels not on Facebook yet")
        for m in reels[:per_brand]:
            try:
                vid = fb_reel(page_id, tok, m["media_url"], m.get("caption") or "")
                done[m["id"]] = {"facebook": vid, "from": m.get("permalink")}
                print(f"OK   {brand} {m.get('permalink')} -> facebook reel {vid}")
            except Exception as e:
                print(f"FAIL {brand} {m.get('permalink')}: {str(e)[:200]}")
            save(state)
    save(state)


if __name__ == "__main__":
    main(int(sys.argv[1]) if len(sys.argv) > 1 else 2)
