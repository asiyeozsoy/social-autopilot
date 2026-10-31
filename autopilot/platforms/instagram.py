"""Instagram content publishing via the Instagram Graph API.

Needs a Professional (Creator/Business) Instagram account linked to a Facebook
Page, and per brand:
  <BRAND>_IG_USER_ID  Instagram business account id
  <BRAND>_IG_TOKEN    long-lived Page access token (does not expire)
Media is pulled by Instagram from public URLs (see media.py).
"""
from __future__ import annotations

import os

import requests

from ..media import public_url
from .base import check, creds, poll

API = "https://graph.facebook.com/" + (os.environ.get("GRAPH_API_VERSION") or "v22.0")


def _container(ig_id, token, **params):
    r = requests.post(f"{API}/{ig_id}/media", data={**params, "access_token": token}, timeout=60)
    return check(r, "instagram create container")["id"]


def _wait(container_id, token):
    def status():
        r = requests.get(f"{API}/{container_id}", params={"fields": "status_code,status", "access_token": token}, timeout=30)
        return check(r, "instagram container status")

    poll(status, done=lambda s: s.get("status_code") == "FINISHED",
         fail=lambda s: s.get("status_code") in ("ERROR", "EXPIRED"), what="instagram media processing")


def publish(post, pp, content_root):
    ig_id = creds(post.brand, "IG_USER_ID")
    token = creds(post.brand, "IG_TOKEN")
    urls = [public_url(m, content_root) for m in pp.media]

    if pp.kind == "image":
        cid = _container(ig_id, token, image_url=urls[0], caption=pp.caption)
    elif pp.kind == "carousel":
        children = []
        for u in urls:
            child = _container(ig_id, token, image_url=u, is_carousel_item="true")
            _wait(child, token)
            children.append(child)
        cid = _container(ig_id, token, media_type="CAROUSEL", children=",".join(children), caption=pp.caption)
    else:  # reel
        cid = _container(ig_id, token, media_type="REELS", video_url=urls[0], caption=pp.caption, share_to_feed="true")
    _wait(cid, token)

    r = requests.post(f"{API}/{ig_id}/media_publish", data={"creation_id": cid, "access_token": token}, timeout=60)
    media_id = check(r, "instagram publish")["id"]
    r = requests.get(f"{API}/{media_id}", params={"fields": "permalink", "access_token": token}, timeout=30)
    link = r.json().get("permalink", "") if r.ok else ""
    return media_id, link
