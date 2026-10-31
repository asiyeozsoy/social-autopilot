"""TikTok Content Posting API (Direct Post).

Per brand:
  TIKTOK_CLIENT_KEY, TIKTOK_CLIENT_SECRET   shared app credentials
  <BRAND>_TT_REFRESH_TOKEN                  user refresh token (valid ~365 days)
Until TikTok audits the app, every post is forced to private ("SELF_ONLY");
set TIKTOK_PRIVACY=PUBLIC_TO_EVERYONE after the audit passes.
Videos are uploaded directly; photo posts are pulled from public URLs, and
TikTok requires the URL prefix (MEDIA_BASE_URL) to be verified in the app.
"""
from __future__ import annotations

import math
import os

import requests

from ..media import public_url
from .base import PublishError, check, creds, poll

API = "https://open.tiktokapis.com/v2"
CHUNK = 10 * 1024 * 1024


def _access_token(brand):
    r = requests.post(f"{API}/oauth/token/", data={
        "client_key": os.environ.get("TIKTOK_CLIENT_KEY", ""),
        "client_secret": os.environ.get("TIKTOK_CLIENT_SECRET", ""),
        "grant_type": "refresh_token",
        "refresh_token": creds(brand, "TT_REFRESH_TOKEN"),
    }, headers={"Content-Type": "application/x-www-form-urlencoded"}, timeout=30)
    body = r.json()
    if "access_token" not in body:
        raise PublishError(f"tiktok token refresh failed: {body}")
    return body["access_token"]


def _headers(token):
    return {"Authorization": f"Bearer {token}", "Content-Type": "application/json; charset=UTF-8"}


def _privacy(token):
    r = requests.post(f"{API}/post/publish/creator_info/query/", headers=_headers(token), timeout=30)
    options = check(r, "tiktok creator info")["data"].get("privacy_level_options", [])
    wanted = os.environ.get("TIKTOK_PRIVACY") or "SELF_ONLY"
    if wanted not in options:
        raise PublishError(f"tiktok privacy {wanted} not allowed for this account: {options}")
    return wanted


def publish(post, pp, content_root):
    token = _access_token(post.brand)
    privacy = _privacy(token)
    caption = pp.caption[:2200]

    if pp.kind == "video":
        video = pp.media[0]
        size = video.stat().st_size
        # TikTok: chunks of 5-64 MB, count = floor(size / chunk); the last chunk takes the remainder
        if size < CHUNK:
            chunk, count = size, 1
        else:
            chunk, count = CHUNK, size // CHUNK
        body = {
            "post_info": {"title": caption, "privacy_level": privacy, "is_aigc": True,
                          "disable_comment": False, "disable_duet": False, "disable_stitch": False},
            "source_info": {"source": "FILE_UPLOAD", "video_size": size,
                            "chunk_size": chunk, "total_chunk_count": count},
        }
        r = requests.post(f"{API}/post/publish/video/init/", headers=_headers(token), json=body, timeout=60)
        data = check(r, "tiktok video init")["data"]
        with video.open("rb") as fh:
            for i in range(count):
                start = i * chunk
                end = size - 1 if i == count - 1 else start + chunk - 1
                fh.seek(start)
                part = fh.read(end - start + 1)
                up = requests.put(data["upload_url"], data=part, timeout=600, headers={
                    "Content-Type": "video/mp4", "Content-Length": str(len(part)),
                    "Content-Range": f"bytes {start}-{end}/{size}"})
                if up.status_code not in (200, 201, 206):
                    raise PublishError(f"tiktok chunk {i + 1}/{count} failed ({up.status_code}): {up.text[:200]}")
        publish_id = data["publish_id"]
    else:  # photo
        urls = [public_url(m, content_root) for m in pp.media]
        title, _, rest = caption.partition("\n")
        body = {
            "post_info": {"title": title[:90], "description": (rest or title)[:4000],
                          "privacy_level": privacy, "disable_comment": False, "auto_add_music": True},
            "source_info": {"source": "PULL_FROM_URL", "photo_cover_index": 0, "photo_images": urls},
            "post_mode": "DIRECT_POST",
            "media_type": "PHOTO",
        }
        r = requests.post(f"{API}/post/publish/content/init/", headers=_headers(token), json=body, timeout=60)
        publish_id = check(r, "tiktok photo init")["data"]["publish_id"]

    def status():
        r = requests.post(f"{API}/post/publish/status/fetch/", headers=_headers(token),
                          json={"publish_id": publish_id}, timeout=30)
        return check(r, "tiktok status")["data"]

    final = poll(status, done=lambda s: s.get("status") == "PUBLISH_COMPLETE",
                 fail=lambda s: s.get("status") == "FAILED", every=8, what="tiktok publish")
    ids = final.get("publicaly_available_post_id") or final.get("publicly_available_post_id") or []
    return publish_id, (f"https://www.tiktok.com/video/{ids[0]}" if ids else "")
