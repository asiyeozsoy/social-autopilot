"""Look up public Instagram business/creator accounts (followers, posts, bio) via the
Graph API business_discovery field. Reads usernames from research/candidates.txt
and writes research/candidates.md, sorted by followers.
"""
from __future__ import annotations

import time
from pathlib import Path

import requests

from .platforms.base import creds

ROOT = Path(__file__).resolve().parents[1]


def lookup(brand, username):
    tok, uid = creds(brand, "IG_TOKEN"), creds(brand, "IG_USER_ID")
    fields = f"business_discovery.username({username}){{username,name,followers_count,media_count,biography}}"
    r = requests.get(f"https://graph.facebook.com/v22.0/{uid}", params={"fields": fields, "access_token": tok}, timeout=30)
    body = r.json()
    if "business_discovery" not in body:
        return {"username": username, "error": body.get("error", {}).get("message", "?")[:80]}
    return body["business_discovery"]


if __name__ == "__main__":
    names = [n.strip() for n in (ROOT / "research/candidates.txt").read_text().split() if n.strip()]
    rows = []
    for n in names:
        rows.append(lookup("factyeap", n))
        time.sleep(1)
    rows.sort(key=lambda r: r.get("followers_count", -1), reverse=True)
    out = ["| account | followers | posts | bio |", "|---|---|---|---|"]
    for r in rows:
        if "error" in r:
            out.append(f"| @{r['username']} | – | – | ({r['error']}) |")
        else:
            bio = (r.get("biography") or "").replace("\n", " ").replace("|", "/")[:90]
            out.append(f"| @{r['username']} | {r['followers_count']} | {r['media_count']} | {bio} |")
    (ROOT / "research/candidates.md").write_text("\n".join(out) + "\n", encoding="utf-8")
    print("\n".join(out))
