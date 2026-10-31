"""YouTube Shorts upload via the YouTube Data API v3 (resumable upload).

Per brand (one Google OAuth client can serve both channels):
  YOUTUBE_CLIENT_ID, YOUTUBE_CLIENT_SECRET    shared
  <BRAND>_YT_REFRESH_TOKEN                    authorised for that brand's channel
The OAuth consent screen must be set to "In production"; in "Testing" Google
expires refresh tokens after 7 days. Each upload costs 1,600 of the default
10,000 daily quota units, so about 6 uploads per day per Google project.
Community (image) posts are not available through the API.
"""
from __future__ import annotations

import os

import requests

from .base import PublishError, check, creds

TOKEN_URL = "https://oauth2.googleapis.com/token"
UPLOAD_URL = "https://www.googleapis.com/upload/youtube/v3/videos"


def _access_token(brand):
    r = requests.post(TOKEN_URL, data={
        "client_id": os.environ.get("YOUTUBE_CLIENT_ID", ""),
        "client_secret": os.environ.get("YOUTUBE_CLIENT_SECRET", ""),
        "refresh_token": creds(brand, "YT_REFRESH_TOKEN"),
        "grant_type": "refresh_token",
    }, timeout=30)
    return check(r, "youtube token refresh")["access_token"]


def publish(post, pp, content_root):
    token = _access_token(post.brand)
    video = pp.media[0]
    title = pp.title or pp.caption.split("\n")[0]
    if "#shorts" not in title.lower():
        title = f"{title} #shorts"
    meta = {
        "snippet": {"title": title[:100], "description": pp.description or pp.caption, "categoryId": "23"},
        "status": {
            "privacyStatus": "public",
            "selfDeclaredMadeForKids": False,
            "containsSyntheticMedia": True,  # AI disclosure
        },
    }
    size = video.stat().st_size
    r = requests.post(
        UPLOAD_URL,
        params={"uploadType": "resumable", "part": "snippet,status"},
        headers={"Authorization": f"Bearer {token}", "X-Upload-Content-Type": "video/*",
                 "X-Upload-Content-Length": str(size)},
        json=meta, timeout=60,
    )
    if r.status_code != 200 or "Location" not in r.headers:
        raise PublishError(f"youtube upload init failed ({r.status_code}): {r.text[:300]}")
    with video.open("rb") as fh:
        up = requests.put(r.headers["Location"], data=fh,
                          headers={"Authorization": f"Bearer {token}", "Content-Length": str(size)}, timeout=900)
    body = check(up, "youtube upload")
    vid = body["id"]
    return vid, f"https://youtube.com/shorts/{vid}"
