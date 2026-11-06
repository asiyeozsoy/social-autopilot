"""Content queue: every post is a folder with a post.yaml and its media files.

content/<brand>/<YYYY-MM-DD_HHMM>_<slug>/post.yaml

    brand: tinynotes
    publish_at: 2026-11-02T15:00:00+01:00   # ISO time with offset
    platforms:
      instagram:
        kind: image | carousel | reel
        media: [instagram.png]               # files in this folder, in order
        caption: "..."
      tiktok:
        kind: photo | video
        media: [tiktok.png]
        caption: "..."
      youtube:
        kind: short                          # YouTube API only uploads videos
        media: [video.mp4]
        title: "..."
        description: "..."
"""
from __future__ import annotations

import datetime as dt
from dataclasses import dataclass, field
from pathlib import Path

import yaml

KINDS = {
    "instagram": {"image", "carousel", "reel"},
    "tiktok": {"photo", "video"},
    "youtube": {"short", "video"},
    "facebook": {"image", "carousel", "reel", "video"},
}


class QueueError(ValueError):
    pass


@dataclass
class PlatformPost:
    platform: str
    kind: str
    media: list[Path]
    caption: str = ""
    title: str = ""
    description: str = ""
    cover: Path | None = None  # cover.jpg next to post.yaml: the Reels cover / grid thumbnail


@dataclass
class Post:
    id: str
    brand: str
    folder: Path
    publish_at: dt.datetime
    platforms: dict[str, PlatformPost] = field(default_factory=dict)


def _parse_time(value) -> dt.datetime:
    if isinstance(value, dt.datetime):
        t = value
    else:
        t = dt.datetime.fromisoformat(str(value))
    if t.tzinfo is None:
        raise QueueError(f"publish_at needs a timezone offset (e.g. +01:00): {value}")
    return t


def load_post(folder: Path, root: Path) -> Post:
    spec_file = folder / "post.yaml"
    spec = yaml.safe_load(spec_file.read_text(encoding="utf-8")) or {}
    post_id = folder.relative_to(root).as_posix()
    for key in ("brand", "publish_at", "platforms"):
        if key not in spec:
            raise QueueError(f"{post_id}: missing '{key}'")
    post = Post(post_id, spec["brand"], folder, _parse_time(spec["publish_at"]))
    for name, p in (spec["platforms"] or {}).items():
        if name not in KINDS:
            raise QueueError(f"{post_id}: unknown platform '{name}'")
        kind = p.get("kind")
        if kind not in KINDS[name]:
            raise QueueError(f"{post_id}/{name}: kind must be one of {sorted(KINDS[name])}")
        media = [folder / m for m in p.get("media", [])]
        if not media:
            raise QueueError(f"{post_id}/{name}: no media listed")
        missing = [m.name for m in media if not m.exists()]
        if missing:
            raise QueueError(f"{post_id}/{name}: missing files {missing}")
        if name == "instagram" and kind == "carousel" and not 2 <= len(media) <= 10:
            raise QueueError(f"{post_id}/instagram: carousel needs 2-10 images")
        if name == "tiktok" and kind == "photo" and len(media) > 35:
            raise QueueError(f"{post_id}/tiktok: photo post allows at most 35 images")
        if kind in {"image", "reel", "video", "short"} and len(media) != 1:
            raise QueueError(f"{post_id}/{name}: '{kind}' takes exactly one file")
        post.platforms[name] = PlatformPost(
            platform=name,
            kind=kind,
            media=media,
            caption=str(p.get("caption", "")).strip(),
            title=str(p.get("title", "")).strip(),
            description=str(p.get("description", "")).strip(),
            cover=(folder / "cover.jpg") if (folder / "cover.jpg").exists() else None,
        )
    # Facebook mirrors Instagram unless a post says otherwise
    if "facebook" not in post.platforms and "instagram" in post.platforms:
        ig = post.platforms["instagram"]
        post.platforms["facebook"] = PlatformPost("facebook", ig.kind, ig.media, ig.caption, cover=ig.cover)
    return post


def load_queue(root: Path) -> list[Post]:
    posts = [load_post(f.parent, root) for f in sorted(root.glob("*/*/post.yaml"))]
    return sorted(posts, key=lambda p: p.publish_at)
