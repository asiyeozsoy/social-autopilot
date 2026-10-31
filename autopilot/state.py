"""Publish log kept in state/published.json and committed back to the repo.

Each entry is keyed "<post id>::<platform>" so a post that failed on one
platform is retried there without being posted twice elsewhere.
"""
from __future__ import annotations

import datetime as dt
import json
from pathlib import Path

MAX_ATTEMPTS = 3


class State:
    def __init__(self, path: Path):
        self.path = path
        self.data: dict = json.loads(path.read_text()) if path.exists() else {}

    @staticmethod
    def key(post_id: str, platform: str) -> str:
        return f"{post_id}::{platform}"

    def entry(self, post_id: str, platform: str) -> dict:
        return self.data.get(self.key(post_id, platform), {})

    def is_done(self, post_id: str, platform: str) -> bool:
        e = self.entry(post_id, platform)
        return e.get("status") in ("published", "skipped") or e.get("attempts", 0) >= MAX_ATTEMPTS

    def mark_skipped(self, post_id: str, platform: str):
        self.data[self.key(post_id, platform)] = {
            "status": "skipped",
            "reason": "too late",
            "at": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"),
        }

    def mark_published(self, post_id: str, platform: str, remote_id: str, url: str = ""):
        e = self.entry(post_id, platform)
        self.data[self.key(post_id, platform)] = {
            "status": "published",
            "remote_id": remote_id,
            "url": url,
            "attempts": e.get("attempts", 0) + 1,
            "at": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"),
        }

    def mark_failed(self, post_id: str, platform: str, error: str):
        e = self.entry(post_id, platform)
        self.data[self.key(post_id, platform)] = {
            "status": "failed",
            "error": error[:500],
            "attempts": e.get("attempts", 0) + 1,
            "at": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"),
        }

    def save(self):
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(json.dumps(self.data, indent=2, ensure_ascii=False, sort_keys=True) + "\n")
