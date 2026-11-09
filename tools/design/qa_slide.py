"""Young-asks / old-answers carousel slide: question in soft handwriting over the young couple
(left), answer in handwritten capitals over the old couple (right). 4:5, 1080x1350.

python tools/design/qa_slide.py art.jpg out.jpg "what if I get\\nslow one day?" "THEN I'LL\\nWALK SLOWER."
"""
import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[2]
W, H = 1080, 1350
INK = (34, 30, 40)


def caveat(size, wght=600):
    f = ImageFont.truetype(str(ROOT / "brand/fonts/Caveat[wght].ttf"), size)
    try:
        f.set_variation_by_axes([wght])
    except Exception:
        pass
    return f


def block(d, text, font, cx, y, max_w):
    lines = text.split("\n")
    size = font.size
    f = font
    while max(d.textlength(ln, font=f) for ln in lines) > max_w and size > 40:
        size -= 3
        f = font.font_variant(size=size)
    lh = int(size * 1.1)
    for ln in lines:
        d.text((cx - d.textlength(ln, font=f) / 2, y), ln, font=f, fill=INK)
        y += lh
    return y


def make(src, out, question, answer):
    im = Image.open(src).convert("RGB")
    im = im.resize((W, int(im.height * W / im.width)), Image.LANCZOS)
    top = max(0, im.height - H - 10)
    im = im.crop((0, top, W, top + H))
    d = ImageDraw.Draw(im)
    block(d, question, caveat(84, 550), W * 0.27, 170, W * 0.44)
    hand_caps = ImageFont.truetype(str(ROOT / "brand/fonts/PatrickHand-Regular.ttf"), 78)
    block(d, answer, hand_caps, W * 0.73, 250, W * 0.44)
    logo = Image.open(ROOT / "brand/tinynotes_wm_maroon.png").convert("RGBA")
    lw = 110
    logo = logo.resize((lw, int(logo.height * lw / logo.width)), Image.LANCZOS)
    logo.putalpha(logo.split()[3].point(lambda v: int(v * 0.75)))
    im = im.convert("RGBA")
    im.alpha_composite(logo, (W - lw - 40, H - logo.height - 36))
    im.convert("RGB").save(out, quality=95)


if __name__ == "__main__":
    make(sys.argv[1], sys.argv[2], sys.argv[3].replace("\\n", "\n"), sys.argv[4].replace("\\n", "\n"))
