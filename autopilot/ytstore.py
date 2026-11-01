"""YouTube channel connection without copy-pasting refresh tokens.

Flow: Claude opens the Google consent URL, the channel owner approves, and the
one-time code is committed to .github/yt-code/<brand>. The yt-connect workflow
exchanges it (using the YOUTUBE_CLIENT_* secrets), encrypts the refresh token
with a key derived from the client secret and commits state/yt_<brand>.enc.
The code alone is useless without the client secret, and the stored token can
only be decrypted with it.
"""
from __future__ import annotations

import base64
import hashlib
import os
import sys
from pathlib import Path

import requests
from cryptography.fernet import Fernet

ROOT = Path(__file__).resolve().parents[1]
REDIRECT = "https://developers.google.com/oauthplayground"
SCOPES = "https://www.googleapis.com/auth/youtube.upload https://www.googleapis.com/auth/youtube.readonly"


def _fernet() -> Fernet:
    secret = os.environ["YOUTUBE_CLIENT_SECRET"].encode()
    return Fernet(base64.urlsafe_b64encode(hashlib.sha256(b"yt-store:" + secret).digest()))


def path(brand: str) -> Path:
    return ROOT / "state" / f"yt_{brand}.enc"


def load(brand: str) -> str:
    p = path(brand)
    if not p.exists() or not os.environ.get("YOUTUBE_CLIENT_SECRET"):
        return ""
    return _fernet().decrypt(p.read_bytes()).decode()


def connect(brand: str, code: str) -> str:
    r = requests.post("https://oauth2.googleapis.com/token", data={
        "code": code.strip(), "client_id": os.environ["YOUTUBE_CLIENT_ID"],
        "client_secret": os.environ["YOUTUBE_CLIENT_SECRET"], "redirect_uri": REDIRECT,
        "grant_type": "authorization_code"}, timeout=30)
    body = r.json()
    if "refresh_token" not in body:
        raise RuntimeError(f"code exchange failed: {body.get('error')} {body.get('error_description', '')}")
    ch = requests.get("https://www.googleapis.com/youtube/v3/channels", params={"part": "snippet", "mine": "true"},
                      headers={"Authorization": f"Bearer {body['access_token']}"}, timeout=30).json()
    title = (ch.get("items") or [{}])[0].get("snippet", {}).get("title", "?")
    path(brand).parent.mkdir(exist_ok=True)
    path(brand).write_bytes(_fernet().encrypt(body["refresh_token"].encode()))
    return title


if __name__ == "__main__":
    brand = sys.argv[1]
    code_file = ROOT / ".github" / "yt-code" / brand
    try:
        print(f"::notice::{brand} youtube: connected to channel '{connect(brand, code_file.read_text())}'")
    except Exception as e:
        print(f"::error::{brand} youtube: {e}")
        sys.exit(1)
    finally:
        code_file.unlink(missing_ok=True)
