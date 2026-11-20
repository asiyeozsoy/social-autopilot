"""List Instagram library music for some searches (Meta Instagram Audio API, Facebook-login token).
Prints only results, never a token.

python tools/ig_audio_probe.py "slow piano|sad piano|emotional piano"
"""
import json
import os
import sys

import requests

V = os.environ.get("GRAPH_API_VERSION") or "v22.0"
G = f"https://graph.facebook.com/{V}"
queries = (sys.argv[1] if len(sys.argv) > 1 else "slow piano").split("|")
tok = os.environ["TINYNOTES_IG_TOKEN"]
ig = os.environ["TINYNOTES_IG_USER_ID"]
out = {}
for q in queries:
    for kind in ("music", "original_sound"):
        r = requests.get(f"{G}/ig_audio", params={"audio_type": kind, "user_id": ig, "access_token": tok, "search_query": q}, timeout=30)
        items = r.json().get("audio", []) if r.ok else []
        if not r.ok:
            print(q, kind, "HTTP", r.status_code, r.text[:200])
        for it in items:
            it.pop("download_url", None)
            it.pop("cover_artwork_thumbnail_uri", None)
            out.setdefault(it["audio_id"], {**it, "query": q})
            print(f"{kind[:5]} | {q:16} | {it['audio_id']} | {it.get('duration_in_ms', 0) // 1000:4}s | {it.get('title')} | {it.get('display_artist') or it.get('ig_username', '')}")
os.makedirs("plans", exist_ok=True)
json.dump(out, open("plans/ig_audio_results.json", "w"), indent=1, ensure_ascii=False)
