"""Public URLs for media files.

Instagram and TikTok photo posts download media from a public URL instead of
taking an upload. MEDIA_BASE_URL points at where the content/ folder is served,
e.g. the repo's GitHub Pages site: https://<user>.github.io/<repo>/content
"""
from __future__ import annotations

import os
from pathlib import Path
from urllib.parse import quote


def public_url(file: Path, content_root: Path) -> str:
    base = os.environ.get("MEDIA_BASE_URL", "").rstrip("/")
    if not base:
        raise RuntimeError("MEDIA_BASE_URL is not set; Instagram/TikTok photos need public media URLs")
    rel = file.relative_to(content_root).as_posix()
    return f"{base}/{quote(rel)}"
