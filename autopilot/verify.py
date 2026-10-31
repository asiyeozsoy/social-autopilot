"""Check that a brand's platform credentials work, without publishing anything.

python -m autopilot.verify <brand> instagram
"""
from __future__ import annotations

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
        raise RuntimeError(f"account lookup failed: {body['error'].get('message', body['error'])}")
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
        print(f"{brand} {platform}: NOT SET UP - {e}")
        return 1
    except Exception as e:
        print(f"{brand} {platform}: FAILED - {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
