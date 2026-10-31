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


CHECKS = {"instagram": instagram}


def main(argv=None) -> int:
    brand, platform = (argv or sys.argv[1:])[:2]
    try:
        print(f"{brand} {platform}: {CHECKS[platform](brand)}")
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
