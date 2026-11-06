"""Per-post numbers for both brands on Instagram, Facebook and YouTube -> plans/stats_<date>.json.
Errors are recorded next to the numbers instead of stopping the run.

python tools/stats_dump.py
"""
import datetime as dt
import json
import sys
from pathlib import Path

import requests

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from autopilot.platforms.base import creds  # noqa: E402
from autopilot.platforms.facebook import API as FB, page_token  # noqa: E402
from autopilot.platforms.instagram import api_base  # noqa: E402

YT = "https://www.googleapis.com/youtube/v3"


def get(url, **p):
    try:
        return requests.get(url, params=p, timeout=60).json()
    except Exception as e:  # noqa: BLE001
        return {"error": {"message": str(e)}}


def instagram(brand):
    tok, uid = creds(brand, "IG_TOKEN"), creds(brand, "IG_USER_ID")
    base = api_base(tok)
    out = {"profile": get(f"{base}/{uid}", fields="username,followers_count,media_count", access_token=tok), "media": []}
    url, params = f"{base}/{uid}/media", dict(fields="id,caption,media_type,media_product_type,timestamp,permalink,like_count,comments_count", limit=50, access_token=tok)
    while url:
        body = get(url, **(params or {})) if params else requests.get(url, timeout=60).json()
        for m in body.get("data", []):
            metric = "views,reach,saved,shares,total_interactions" if m.get("media_type") == "VIDEO" else "views,reach,saved,shares,total_interactions"
            ins = get(f"{base}/{m['id']}/insights", metric=metric, access_token=tok)
            m["insights"] = {d["name"]: (d.get("values") or [{}])[0].get("value", d.get("total_value", {}).get("value")) for d in ins.get("data", [])}
            if "error" in ins:
                m["insights_error"] = ins["error"].get("message", "")[:160]
            m["caption"] = (m.get("caption") or "")[:120]
            out["media"].append(m)
        url, params = (body.get("paging") or {}).get("next"), None
    return out


def facebook(brand):
    pid = creds(brand, "FB_PAGE_ID")
    tok = page_token(pid)
    out = {"page": get(f"{FB}/{pid}", fields="name,followers_count,fan_count", access_token=tok), "reels": [], "posts": []}
    r = get(f"{FB}/{pid}/video_reels", fields="id,description,created_time,post_id,length", limit=100, access_token=tok)
    out["reels_error"] = r.get("error", {}).get("message")
    for v in r.get("data", []):
        ins = get(f"{FB}/{v['id']}/video_insights", access_token=tok)
        v["insights"] = {d["name"]: (d.get("values") or [{}])[0].get("value") for d in ins.get("data", [])
                         if d["name"] in ("blue_reels_play_count", "post_impressions_unique", "post_video_likes_by_reaction_type",
                                          "post_video_social_actions", "fb_reels_total_plays", "fb_reels_replay_count")}
        if "error" in ins:
            v["insights_error"] = ins["error"].get("message", "")[:160]
        v["description"] = (v.get("description") or "")[:120]
        out["reels"].append(v)
    p = get(f"{FB}/{pid}/posts", fields="message,created_time,permalink_url,reactions.summary(true).limit(0),comments.summary(true).limit(0),shares",
            limit=100, access_token=tok)
    out["posts_error"] = p.get("error", {}).get("message")
    for x in p.get("data", []):
        out["posts"].append({"message": (x.get("message") or "")[:120], "created": x.get("created_time"),
                             "reactions": x.get("reactions", {}).get("summary", {}).get("total_count"),
                             "comments": x.get("comments", {}).get("summary", {}).get("total_count"),
                             "shares": (x.get("shares") or {}).get("count", 0), "url": x.get("permalink_url")})
    return out


def youtube():
    from autopilot.platforms.youtube import _access_token
    h = {"Authorization": f"Bearer {_access_token('factyeap')}"}
    res = {}
    for brand, handle in (("factyeap", "@factyeap"), ("tinynotes", "@TinyNotesForU")):
        ch = requests.get(f"{YT}/channels", params={"part": "contentDetails,statistics,snippet", "forHandle": handle}, headers=h, timeout=30).json()
        if not ch.get("items"):
            res[brand] = {"error": ch}
            continue
        c = ch["items"][0]
        up = c["contentDetails"]["relatedPlaylists"]["uploads"]
        ids, tokn = [], None
        while True:
            r = requests.get(f"{YT}/playlistItems", params={"part": "contentDetails", "playlistId": up, "maxResults": 50,
                                                            **({"pageToken": tokn} if tokn else {})}, headers=h, timeout=30).json()
            ids += [i["contentDetails"]["videoId"] for i in r.get("items", [])]
            tokn = r.get("nextPageToken")
            if not tokn or len(ids) > 400:
                break
        vids = []
        for i in range(0, len(ids), 50):
            r = requests.get(f"{YT}/videos", params={"part": "snippet,statistics,contentDetails", "id": ",".join(ids[i:i + 50])}, headers=h, timeout=30).json()
            for v in r.get("items", []):
                s = v.get("statistics", {})
                vids.append({"id": v["id"], "published": v["snippet"]["publishedAt"], "title": v["snippet"]["title"][:100],
                             "duration": v["contentDetails"]["duration"], "views": int(s.get("viewCount", 0)),
                             "likes": int(s.get("likeCount", 0)), "comments": int(s.get("commentCount", 0))})
        res[brand] = {"channel": c["snippet"]["title"], "stats": c["statistics"], "videos": sorted(vids, key=lambda v: v["published"])}
    return res


def main():
    out = {"generated": dt.datetime.now(dt.timezone.utc).isoformat(), "instagram": {}, "facebook": {}}
    for brand in ("factyeap", "tinynotes"):
        for name, fn in (("instagram", instagram), ("facebook", facebook)):
            try:
                out[name][brand] = fn(brand)
            except Exception as e:  # noqa: BLE001
                out[name][brand] = {"error": str(e)[:300]}
    try:
        out["youtube"] = youtube()
    except Exception as e:  # noqa: BLE001
        out["youtube"] = {"error": str(e)[:300]}
    p = ROOT / "plans" / f"stats_{dt.date.today().isoformat()}.json"
    p.write_text(json.dumps(out, indent=1, ensure_ascii=False) + "\n")
    print("wrote", p.name)


if __name__ == "__main__":
    main()
