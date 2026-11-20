"""Can our keys use Meta's Instagram Audio API (licensed/trending music on reels)?
Prints only token kinds and results, never a token.

python tools/ig_audio_probe.py "slow piano"
"""
import os
import sys

import requests

V = os.environ.get("GRAPH_API_VERSION") or "v22.0"
G = f"https://graph.facebook.com/{V}"
q = sys.argv[1] if len(sys.argv) > 1 else "slow piano"


def search(token, ig_id, label):
    for params in ({"search_query": q}, {}):
        r = requests.get(f"{G}/ig_audio", params={"audio_type": "music", "user_id": ig_id, "access_token": token, **params}, timeout=30)
        what = f"'{q}'" if params else "trending"
        try:
            j = r.json()
        except Exception:
            j = {"raw": r.text[:200]}
        if r.ok:
            items = j.get("data", [])
            print(f"  {label} {what}: OK {len(items)} tracks")
            for it in items[:12]:
                print("     ", {k: it.get(k) for k in ("id", "title", "artist_name", "display_artist", "duration_in_ms", "is_trending") if k in it} or it)
        else:
            print(f"  {label} {what}: HTTP {r.status_code} {str(j.get('error', j))[:300]}")


sys_tok = os.environ.get("META_SYSTEM_TOKEN", "")
for brand in ("TINYNOTES", "FACTYEAP"):
    ig_id = os.environ.get(f"{brand}_IG_USER_ID")
    page = os.environ.get(f"{brand}_FB_PAGE_ID")
    ig_tok = os.environ.get(f"{brand}_IG_TOKEN", "")
    print(f"== {brand} ig={ig_id} page={page} ig_token_kind={'instagram-login' if ig_tok.startswith('IG') else ('facebook' if ig_tok else 'none')}")
    if ig_tok and not ig_tok.startswith("IG"):
        search(ig_tok, ig_id, "ig-token")
    if sys_tok:
        r = requests.get(f"{G}/{page}", params={"fields": "access_token,instagram_business_account", "access_token": sys_tok}, timeout=30)
        j = r.json()
        print("  page link:", j.get("instagram_business_account"), "page token:", bool(j.get("access_token")), str(j.get("error", ""))[:200])
        search(sys_tok, ig_id, "system-token")
        if j.get("access_token"):
            search(j["access_token"], ig_id, "page-token")
        linked = (j.get("instagram_business_account") or {}).get("id")
        if linked and linked != ig_id:
            search(sys_tok, linked, "system-token(linked id)")
