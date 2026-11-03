"""Facebook Page publishing via the Graph API.

Uses the Meta system user token (META_SYSTEM_TOKEN) to fetch each brand's Page
access token, then posts:
  image     -> POST /{page}/photos
  carousel  -> unpublished /{page}/photos per image, then /{page}/feed with attached_media
  reel      -> /{page}/video_reels start -> rupload with file_url -> finish (PUBLISHED)
Per brand: <BRAND>_FB_PAGE_ID. Token needs pages_show_list, pages_read_engagement,
pages_manage_posts, and the system user must be assigned to the Page.
Posts without an explicit `facebook:` block reuse their Instagram media and caption.
"""
from __future__ import annotations

import json
import os

import requests

from ..media import public_url
from .base import NotConfigured, PublishError, check, creds, poll

VERSION = os.environ.get("GRAPH_API_VERSION") or "v22.0"
API = f"https://graph.facebook.com/{VERSION}"


def system_token() -> str:
    tok = os.environ.get("META_SYSTEM_TOKEN", "")
    if not tok:
        raise NotConfigured("secret META_SYSTEM_TOKEN is not set")
    return tok


def page_token(page_id: str) -> str:
    r = requests.get(f"{API}/{page_id}", params={"fields": "access_token,name", "access_token": system_token()}, timeout=30)
    body = r.json()
    if "access_token" not in body:
        msg = str(body.get("error", {}).get("message", body))
        raise NotConfigured(f"no page access for {page_id}: {msg}")
    return body["access_token"]


def publish(post, pp, content_root):
    page_id = creds(post.brand, "FB_PAGE_ID")
    tok = page_token(page_id)
    urls = [public_url(m, content_root) for m in pp.media]

    if pp.kind in ("image", "photo"):
        r = requests.post(f"{API}/{page_id}/photos", data={"url": urls[0], "caption": pp.caption, "published": "true",
                                                           "access_token": tok}, timeout=120)
        body = check(r, "facebook photo")
        pid = body.get("post_id") or body["id"]
        return pid, f"https://www.facebook.com/{pid}"

    if pp.kind == "carousel":
        ids = []
        for u in urls:
            r = requests.post(f"{API}/{page_id}/photos", data={"url": u, "published": "false", "access_token": tok}, timeout=120)
            ids.append(check(r, "facebook carousel photo")["id"])
        r = requests.post(f"{API}/{page_id}/feed", data={
            "message": pp.caption, "access_token": tok,
            "attached_media": json.dumps([{"media_fbid": i} for i in ids])}, timeout=120)
        pid = check(r, "facebook multi-photo post")["id"]
        return pid, f"https://www.facebook.com/{pid}"

    if pp.kind == "video":  # regular (e.g. landscape) feed video
        r = requests.post(f"{API}/{page_id}/videos", data={"file_url": urls[0], "description": pp.caption,
                                                           "title": pp.title or "", "access_token": tok}, timeout=600)
        vid = check(r, "facebook video")["id"]
        return vid, f"https://www.facebook.com/{page_id}/videos/{vid}"

    # reel
    r = requests.post(f"{API}/{page_id}/video_reels", data={"upload_phase": "start", "access_token": tok}, timeout=60)
    start = check(r, "facebook reel start")
    vid = start["video_id"]
    up = requests.post(start.get("upload_url") or f"https://rupload.facebook.com/video-upload/{VERSION}/{vid}",
                       headers={"Authorization": f"OAuth {tok}", "file_url": urls[0]}, timeout=300)
    if not up.ok or not up.json().get("success"):
        raise PublishError(f"facebook reel upload failed ({up.status_code}): {up.text[:300]}")

    def status():
        s = requests.get(f"{API}/{vid}", params={"fields": "status", "access_token": tok}, timeout=30).json()
        return s.get("status", {})

    poll(status, done=lambda s: (s.get("uploading_phase") or {}).get("status") == "complete",
         fail=lambda s: (s.get("uploading_phase") or {}).get("status") == "error", every=5, timeout=600, what="facebook reel upload")
    r = requests.post(f"{API}/{page_id}/video_reels", data={
        "upload_phase": "finish", "video_id": vid, "video_state": "PUBLISHED",
        "description": pp.caption, "is_ai_generated": "true", "access_token": tok}, timeout=120)
    check(r, "facebook reel publish")
    return vid, f"https://www.facebook.com/reel/{vid}"
