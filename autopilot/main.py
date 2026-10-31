"""Publish every post whose time has come, on every platform not yet done.

  python -m autopilot.main             publish what is due now
  python -m autopilot.main --dry-run   show what would be published, change nothing
  python -m autopilot.main --check     validate the whole queue and list upcoming posts
  python -m autopilot.main --only tinynotes --platform instagram
"""
from __future__ import annotations

import argparse
import datetime as dt
import os
import sys
from pathlib import Path

from .platforms import PUBLISHERS
from .queue import QueueError, load_queue
from .state import MAX_ATTEMPTS, State

ROOT = Path(__file__).resolve().parent.parent


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--check", action="store_true")
    ap.add_argument("--only", help="brand to limit to")
    ap.add_argument("--platform", choices=sorted(PUBLISHERS))
    ap.add_argument("--content", default=str(ROOT / "content"))
    ap.add_argument("--state", default=str(ROOT / "state" / "published.json"))
    ap.add_argument("--now", help="pretend the current time is this ISO timestamp (testing)")
    args = ap.parse_args(argv)

    content = Path(args.content)
    try:
        queue = load_queue(content)
    except QueueError as e:
        print(f"QUEUE ERROR: {e}")
        return 2
    state = State(Path(args.state))
    now = dt.datetime.fromisoformat(args.now) if args.now else dt.datetime.now(dt.timezone.utc)
    enabled = {p.strip() for p in (os.environ.get("ENABLED_PLATFORMS") or ",".join(PUBLISHERS)).split(",") if p.strip()}

    if args.check:
        print(f"{len(queue)} posts OK")
        for post in queue:
            when = "DUE " if post.publish_at <= now else "    "
            done = [p for p in post.platforms if state.is_done(post.id, p)]
            print(f"{when}{post.publish_at.isoformat()}  {post.id}  -> {', '.join(post.platforms)}"
                  + (f"  (done: {', '.join(done)})" if done else ""))
        return 0

    # Posts more than MAX_LATE_HOURS past their slot are skipped, so a late setup or a
    # long outage doesn't dump a week of posts at once.
    max_late = dt.timedelta(hours=float(os.environ.get("MAX_LATE_HOURS") or 6))
    failures = 0
    for post in queue:
        if post.publish_at > now or (args.only and post.brand != args.only):
            continue
        too_late = now - post.publish_at > max_late
        for name, pp in post.platforms.items():
            if (args.platform and name != args.platform) or name not in enabled:
                continue
            if state.is_done(post.id, name):
                continue
            label = f"{post.id} -> {name} ({pp.kind}, {len(pp.media)} file)"
            if too_late:
                print(f"SKIP {label}: more than {max_late} late")
                if not args.dry_run:
                    state.mark_skipped(post.id, name)
                    state.save()
                continue
            if args.dry_run:
                print(f"[dry-run] would publish {label}")
                continue
            try:
                remote_id, url = PUBLISHERS[name](post, pp, content)
                state.mark_published(post.id, name, remote_id, url)
                print(f"OK   {label} {url}")
            except Exception as e:  # keep going with the other posts
                state.mark_failed(post.id, name, f"{type(e).__name__}: {e}")
                attempts = state.entry(post.id, name)["attempts"]
                print(f"FAIL {label} attempt {attempts}/{MAX_ATTEMPTS}: {e}")
                failures += 1
            state.save()
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
