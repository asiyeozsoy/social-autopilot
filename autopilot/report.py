"""Weekly performance report: followers per account and the best and weakest posts
of the last 7 days, ranked by shares + saves + comments (what grows an account).

python -m autopilot.report [days]   -> writes reports/<date>.md and prints it
Metrics a token can't read are shown as "–" instead of failing the report.
"""
from __future__ import annotations

import datetime as dt
import os
import sys
from pathlib import Path

import requests

from .platforms.base import creds
from .platforms.instagram import api_base

ROOT = Path(__file__).resolve().parents[1]
FB = "https://graph.facebook.com/v22.0"
BRANDS = ("tinynotes", "factyeap")


def _get(url, **params):
    try:
        r = requests.get(url, params=params, timeout=30)
        return r.json()
    except Exception as e:  # network hiccup: keep the report going
        return {"error": {"message": str(e)}}


def instagram(brand, since):
    tok, uid = creds(brand, "IG_TOKEN"), creds(brand, "IG_USER_ID")
    base = api_base(tok)
    me = _get(f"{base}/{uid}", fields="username,followers_count,media_count", access_token=tok)
    media = _get(f"{base}/{uid}/media", fields="id,caption,media_type,media_product_type,timestamp,permalink,like_count,comments_count",
                 limit=50, access_token=tok).get("data", [])
    posts = []
    for m in media:
        t = dt.datetime.fromisoformat(m["timestamp"].replace("+0000", "+00:00"))
        if t < since:
            continue
        metric = "reach,saved,shares,views" if m.get("media_product_type") != "REELS" else "reach,saved,shares,views"
        ins = _get(f"{base}/{m['id']}/insights", metric=metric, access_token=tok)
        vals = {d["name"]: (d.get("values") or [{}])[0].get("value", d.get("total_value", {}).get("value"))
                for d in ins.get("data", [])}
        posts.append({"platform": "IG", "when": t, "text": (m.get("caption") or "").split("\n")[0][:60],
                      "link": m.get("permalink", ""), "likes": m.get("like_count"), "comments": m.get("comments_count"),
                      "saves": vals.get("saved"), "shares": vals.get("shares"), "reach": vals.get("reach"),
                      "views": vals.get("views"), "insights_error": ins.get("error", {}).get("message")})
    return me, posts


def facebook(brand, since):
    from .platforms.facebook import page_token
    pid = creds(brand, "FB_PAGE_ID")
    tok = page_token(pid)
    me = _get(f"{FB}/{pid}", fields="name,followers_count,fan_count", access_token=tok)
    feed = _get(f"{FB}/{pid}/published_posts", limit=50, access_token=tok,
                fields="message,created_time,permalink_url,shares,reactions.summary(true).limit(0),comments.summary(true).limit(0)")
    posts = []
    for p in feed.get("data", []):
        t = dt.datetime.fromisoformat(p["created_time"].replace("+0000", "+00:00"))
        if t < since:
            continue
        posts.append({"platform": "FB", "when": t, "text": (p.get("message") or "").split("\n")[0][:60],
                      "link": p.get("permalink_url", ""), "likes": p.get("reactions", {}).get("summary", {}).get("total_count"),
                      "comments": p.get("comments", {}).get("summary", {}).get("total_count"),
                      "shares": p.get("shares", {}).get("count", 0), "saves": None, "reach": None, "views": None})
    return me, posts


def score(p):
    return 3 * (p.get("shares") or 0) + 3 * (p.get("saves") or 0) + 2 * (p.get("comments") or 0) + (p.get("likes") or 0)


def fmt(v):
    return "–" if v is None else str(v)


def build(days=7):
    now = dt.datetime.now(dt.timezone.utc)
    since = now - dt.timedelta(days=days)
    out = [f"# Weekly report · {now:%Y-%m-%d}", f"Last {days} days. Score = 3×shares + 3×saves + 2×comments + likes.", ""]
    notes = []
    for brand in BRANDS:
        out.append(f"## {brand}")
        rows = []
        for name, fn in (("Instagram", instagram), ("Facebook", facebook)):
            try:
                me, posts = fn(brand, since)
            except Exception as e:
                out.append(f"- {name}: not readable ({str(e)[:120]})")
                continue
            if "error" in me:
                out.append(f"- {name}: not readable ({me['error'].get('message', '')[:120]})")
                continue
            followers = me.get("followers_count", me.get("fan_count"))
            out.append(f"- {name}: **{fmt(followers)} followers**, {len(posts)} posts this week")
            rows += posts
            errs = {p.get("insights_error") for p in posts if p.get("insights_error")}
            if errs:
                notes.append(f"{brand} {name}: reach/saves/shares not readable ({next(iter(errs))[:100]})")
        rows.sort(key=score, reverse=True)
        if rows:
            out += ["", "| | post | likes | comments | shares | saves | reach | score |", "|---|---|---|---|---|---|---|---|"]
            for p in rows:
                out.append(f"| {p['platform']} {p['when']:%a %d} | [{p['text'] or '(no caption)'}]({p['link']}) | "
                           f"{fmt(p['likes'])} | {fmt(p['comments'])} | {fmt(p['shares'])} | {fmt(p['saves'])} | "
                           f"{fmt(p['reach'])} | {score(p)} |")
        out.append("")
    if notes:
        out += ["### Notes", *[f"- {n}" for n in notes], ""]
    return "\n".join(out)


if __name__ == "__main__":
    days = int(sys.argv[1]) if len(sys.argv) > 1 else 7
    text = build(days)
    path = ROOT / "reports" / f"{dt.date.today():%Y-%m-%d}.md"
    path.parent.mkdir(exist_ok=True)
    path.write_text(text, encoding="utf-8")
    print(text)
    summary = os.environ.get("GITHUB_STEP_SUMMARY")
    if summary:
        Path(summary).write_text(text, encoding="utf-8")
