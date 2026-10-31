"""Instagram content publishing via the Instagram Graph API.

Works with either login method, picked from the token itself:
  - Instagram Login (token starts with "IG"): no Facebook Page needed,
    calls graph.instagram.com. Long-lived tokens last 60 days and must be
    refreshed before they expire.
  - Facebook Login (Page token): calls graph.facebook.com.
Per brand:
  <BRAND>_IG_USER_ID  Instagram professional account id
  <BRAND>_IG_TOKEN    access token
Media is pulled by Instagram from public URLs (see media.py).
"""
from __future__ import annotations

import os

import requests

from ..media import public_url
from .base import NotConfigured, check, creds, poll

VERSION = os.environ.get("GRAPH_API_VERSION") or "v22.0"


def api_base(token: str) -> str:
    host = "graph.instagram.com" if token.startswith("IG") else "graph.facebook.com"
    return f"https://{host}/{VERSION}"


ACCESS_ERRORS = ("does not exist, cannot be loaded due to missing permissions", "Invalid OAuth access token",
                 "Error validating access token", "has not authorized application")


def _container(ig_id, token, **params):
    r = requests.post(f"{api_base(token)}/{ig_id}/media", data={**params, "access_token": token}, timeout=60)
    err = (r.json().get("error") or {}) if r.headers.get("content-type", "").startswith(("application/json", "text/javascript")) else {}
    if any(m in str(err.get("message", "")) for m in ACCESS_ERRORS):
        # the key can't reach this account yet: wait without using up an attempt
        raise NotConfigured(f"instagram key has no access to account {ig_id}: {err.get('message')}")
    return check(r, "instagram create container")["id"]


def _wait(container_id, token):
    def status():
        r = requests.get(f"{api_base(token)}/{container_id}", params={"fields": "status_code,status", "access_token": token}, timeout=30)
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

    API = api_base(token)
    r = requests.post(f"{API}/{ig_id}/media_publish", data={"creation_id": cid, "access_token": token}, timeout=60)
    media_id = check(r, "instagram publish")["id"]
    r = requests.get(f"{API}/{media_id}", params={"fields": "permalink", "access_token": token}, timeout=30)
    link = r.json().get("permalink", "") if r.ok else ""
    return media_id, link
