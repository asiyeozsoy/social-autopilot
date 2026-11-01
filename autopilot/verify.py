"""Check that a brand's platform credentials work, without publishing anything.

python -m autopilot.verify <brand> instagram
"""
from __future__ import annotations

import re
import sys

import requests

from .platforms.base import NotConfigured, creds
from .platforms.instagram import api_base


def instagram(brand: str) -> str:
    ig_id = creds(brand, "IG_USER_ID")
    token = creds(brand, "IG_TOKEN")
    base = api_base(token)
    r = requests.get(f"{base}/{ig_id}", params={"fields": "username", "access_token": token}, timeout=30)
    body = r.json()
    if "error" in body:
        me = requests.get(f"{base}/me", params={"fields": "id,name", "access_token": token}, timeout=30).json()
        who = me.get("name") or me.get("error", {}).get("message", "?")
        other = {"17841453440786843": "tinynotesforu_", "17841474070047497": "factyeap"}
        for oid, oname in other.items():
            if oid != ig_id:
                t = requests.get(f"{base}/{oid}", params={"fields": "username", "access_token": token}, timeout=30).json()
                if "username" in t:
                    who += f"; it CAN open @{t['username']} instead"
        raise RuntimeError(f"this key belongs to '{who}' (type {token[:3]}), which cannot open account {ig_id}")
    r = requests.get(f"{base}/{ig_id}/content_publishing_limit", params={"fields": "quota_usage,config", "access_token": token}, timeout=30)
    lim = r.json()
    if "error" in lim:
        raise RuntimeError(f"publishing permission check failed: {lim['error'].get('message', lim['error'])}")
    data = (lim.get("data") or [{}])[0]
    total = (data.get("config") or {}).get("quota_total", "?")
    return f"@{body.get('username')} OK - can publish (used {data.get('quota_usage', 0)}/{total} posts in the last 24h)"


def instagram_upload(brand: str) -> str:
    """Create (but never publish) a media container from the brand's next queued image.
    Proves Instagram can download our hosted JPEG and accepts it. Unused containers expire in 24h."""
    import datetime as dt
    from pathlib import Path

    from .media import public_url
    from .platforms.instagram import _container, _wait
    from .queue import load_queue

    root = Path(__file__).resolve().parent.parent / "content"
    now = dt.datetime.now(dt.timezone.utc)
    post = next(p for p in load_queue(root) if p.brand == brand and p.publish_at > now
                and "instagram" in p.platforms and p.platforms["instagram"].kind in ("image", "carousel"))
    img = post.platforms["instagram"].media[0]
    ig_id, token = creds(brand, "IG_USER_ID"), creds(brand, "IG_TOKEN")
    cid = _container(ig_id, token, image_url=public_url(img, root), is_carousel_item="true")
    _wait(cid, token)
    return f"image from {post.id} accepted by Instagram (container {cid}, NOT published)"


def instagram_reel(brand: str) -> str:
    """Create (never publish) a Reels container from the brand's next queued video."""
    import datetime as dt
    from pathlib import Path

    from .media import public_url
    from .platforms.instagram import _container, _wait
    from .queue import load_queue

    root = Path(__file__).resolve().parent.parent / "content"
    now = dt.datetime.now(dt.timezone.utc)
    post = next(p for p in load_queue(root) if p.brand == brand and p.publish_at > now
                and p.platforms.get("instagram") and p.platforms["instagram"].kind == "reel")
    vid = post.platforms["instagram"].media[0]
    ig_id, token = creds(brand, "IG_USER_ID"), creds(brand, "IG_TOKEN")
    cid = _container(ig_id, token, media_type="REELS", video_url=public_url(vid, root), share_to_feed="true")
    _wait(cid, token)
    return f"video from {post.id} accepted by Instagram Reels (container {cid}, NOT published)"


def facebook(brand: str) -> str:
    from .platforms.facebook import API, page_token
    page_id = creds(brand, "FB_PAGE_ID")
    tok = page_token(page_id)
    me = requests.get(f"{API}/{page_id}", params={"fields": "name", "access_token": tok}, timeout=30).json()
    perms = requests.get(f"{API}/me/permissions", params={"access_token": __import__("os").environ["META_SYSTEM_TOKEN"]}, timeout=30).json()
    granted = sorted(p["permission"] for p in perms.get("data", []) if p.get("status") == "granted")
    need = {"pages_manage_posts", "pages_read_engagement", "pages_show_list"}
    missing = need - set(granted)
    if missing:
        raise RuntimeError(f"page '{me.get('name')}' reachable but token lacks {sorted(missing)}")
    return f"page '{me.get('name')}' OK - can publish"


CHECKS = {"instagram": instagram, "facebook": facebook, "instagram-upload": instagram_upload, "instagram-reel": instagram_reel}


def main(argv=None) -> int:
    brand, platform = (argv or sys.argv[1:])[:2]
    try:
        print(f"::notice::{brand} {platform}: {CHECKS[platform](brand)}")
        return 0
    except NotConfigured as e:
        msg = f"{brand} {platform}: NOT SET UP - {e}"
    except Exception as e:
        msg = f"{brand} {platform}: FAILED - {e}"
    msg = re.sub(r"[A-Za-z0-9_\-]{60,}", "[hidden]", msg)  # never echo a token
    print(f"::error::{msg}")  # shows as a run annotation
    return 1


if __name__ == "__main__":
    sys.exit(main())
