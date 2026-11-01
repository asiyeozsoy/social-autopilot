"""Write a .jpg next to every .png under a folder (Instagram and TikTok photo posts only accept JPEG).

python tools/make_jpegs.py content
"""
import sys
from pathlib import Path

from PIL import Image

for png in Path(sys.argv[1]).rglob("*.png"):
    jpg = png.with_suffix(".jpg")
    if jpg.exists() and jpg.stat().st_mtime >= png.stat().st_mtime:
        continue
    Image.open(png).convert("RGB").save(jpg, "JPEG", quality=92, optimize=True, progressive=False)
    print("jpeg", jpg)
