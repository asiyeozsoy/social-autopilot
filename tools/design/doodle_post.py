"""Turn an AI doodle (empty paper on top) into a 4:5 Instagram post with a handwritten quote.

python tools/design/doodle_post.py doodle.jpg out.png "growing slowly\\nis still growing."
"""
import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[2]
W, H = 1080, 1350
INK = (44, 40, 52)


def font(size):
    f = ImageFont.truetype(str(ROOT / "brand/fonts/Caveat[wght].ttf"), size)
    try:
        f.set_variation_by_axes([600])
    except Exception:
        pass
    return f


def make(src, out, text):
    im = Image.open(src).convert("RGB")
    im = im.resize((W, int(im.height * W / im.width)), Image.LANCZOS)
    top = max(0, im.height - H - 20)  # keep the drawing near the bottom, trim empty paper from the top
    im = im.crop((0, top, W, top + H))
    d = ImageDraw.Draw(im)
    lines = text.split("\n")
    size = 112
    while size > 50 and max(d.textlength(ln, font=font(size)) for ln in lines) > W * 0.8:
        size -= 4
    f = font(size)
    lh = int(size * 1.12)
    y = int(H * 0.30) - lh * len(lines) // 2
    for ln in lines:
        d.text(((W - d.textlength(ln, font=f)) / 2, y), ln, font=f, fill=INK)
        y += lh
    logo = Image.open(ROOT / "brand/tinynotes_wm_maroon.png").convert("RGBA")
    lw = 120
    logo = logo.resize((lw, int(logo.height * lw / logo.width)), Image.LANCZOS)
    logo.putalpha(logo.split()[3].point(lambda v: int(v * 0.8)))
    im = im.convert("RGBA")
    im.alpha_composite(logo, (W - lw - 48, H - logo.height - 44))
    im.convert("RGB").save(out, quality=95)


if __name__ == "__main__":
    make(sys.argv[1], sys.argv[2], sys.argv[3].replace("\\n", "\n"))
