"""Graphic-novel carousel slides: one illustrated panel per slide on cream paper, a black panel
frame, a yellow caption box (time / narration), speech bubbles with tails, an optional big
title, and the brand logo. 1080x1350.

from comic_panel import comic_slide
comic_slide("p1.png", "out.jpg", caption="10:00 PM",
            bubbles=[("just a little warmer...", (420, 330), (640, 600))],
            title=("THE THERMOSTAT WAR", "a winter story"), brand="factyeap")
Bubble = (text, centre_xy, tail_tip_xy[, max_width]) in slide pixels; tail_tip None = no tail.
"""
import math
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

ROOT = Path(__file__).resolve().parents[2]
W, H = 1080, 1350
M = 36  # paper margin around the panel
PAPER = (244, 236, 220)
INK = (22, 18, 16)


def _font(name, size):
    return ImageFont.truetype(str(ROOT / "brand/fonts" / name), size)


def _paper():
    rng = np.random.default_rng(5)
    a = np.ones((H, W, 3)) * np.array(PAPER, float)
    a += rng.normal(0, 3.5, (H, W, 1))
    return Image.fromarray(np.clip(a, 0, 255).astype("uint8")).filter(ImageFilter.GaussianBlur(0.5))


def _wrap(d, text, font, maxw):
    words, lines, cur = text.split(), [], ""
    for w in words:
        t = (cur + " " + w).strip()
        if d.textlength(t, font=font) <= maxw or not cur:
            cur = t
        else:
            lines.append(cur)
            cur = w
    if cur:
        lines.append(cur)
    return lines


def _bubble(img, text, centre, tip, maxw=430, size=46):
    d = ImageDraw.Draw(img)
    f = _font("ComicNeue-Bold.ttf", size)
    lines = _wrap(d, text, f, maxw)
    lh = int(size * 1.15)
    tw = max(d.textlength(ln, font=f) for ln in lines)
    th = lh * len(lines)
    cx, cy = centre
    rx, ry = tw / 2 + 46, th / 2 + 34
    box = (cx - rx, cy - ry, cx + rx, cy + ry)
    if tip:
        # tail: a curved wedge from the bubble edge toward the speaker
        ang = math.atan2(tip[1] - cy, tip[0] - cx)
        bx, by = cx + math.cos(ang) * rx * 0.8, cy + math.sin(ang) * ry * 0.8
        nx, ny = -math.sin(ang), math.cos(ang)
        base = [(bx + nx * 26, by + ny * 26), (bx - nx * 26, by - ny * 26)]
        d.polygon([base[0], tip, base[1]], fill=INK)
        d.ellipse((box[0] - 5, box[1] - 5, box[2] + 5, box[3] + 5), fill=INK)
        inner = [(bx + nx * 19, by + ny * 19), (tip[0] - math.cos(ang) * 9, tip[1] - math.sin(ang) * 9), (bx - nx * 19, by - ny * 19)]
        d.ellipse(box, fill="white")
        d.polygon(inner, fill="white")
    else:
        d.ellipse((box[0] - 5, box[1] - 5, box[2] + 5, box[3] + 5), fill=INK)
        d.ellipse(box, fill="white")
    y = cy - th / 2 - size * 0.08
    for ln in lines:
        d.text((cx - d.textlength(ln, font=f) / 2, y), ln, font=f, fill=INK)
        y += lh


def _caption(img, text, xy=(M + 22, M + 22), size=40):
    d = ImageDraw.Draw(img)
    f = _font("Bangers-Regular.ttf", size)
    tw = d.textlength(text, font=f)
    x, y = xy
    d.rectangle((x - 4, y - 4, x + tw + 36, y + size + 22), fill=INK)
    d.rectangle((x, y, x + tw + 32, y + size + 18), fill=(255, 214, 72))
    d.text((x + 16, y + 6), text, font=f, fill=INK)


def _title(img, title, sub=None, y=M + 40):
    d = ImageDraw.Draw(img)
    f = _font("Bangers-Regular.ttf", 120)
    tw = d.textlength(title, font=f)
    if tw > W - 2 * M - 60:
        f = _font("Bangers-Regular.ttf", int(120 * (W - 2 * M - 60) / tw))
        tw = d.textlength(title, font=f)
    x = (W - tw) / 2
    d.text((x, y), title, font=f, fill=(255, 214, 72), stroke_width=7, stroke_fill=INK)
    if sub:
        fs = _font("ComicNeue-Bold.ttf", 44)
        sw = d.textlength(sub, font=fs)
        d.text(((W - sw) / 2, y + f.size + 10), sub, font=fs, fill="white", stroke_width=4, stroke_fill=INK)


def _logo(img, brand):
    lg = Image.open(ROOT / f"brand/{brand}_wm_white.png").convert("RGBA")
    lw = 140
    lg = lg.resize((lw, int(lg.height * lw / lg.width)), Image.LANCZOS)
    lg.putalpha(lg.split()[3].point(lambda v: int(v * 0.9)))
    img.alpha_composite(lg, (W - M - lw - 24, H - M - lg.height - 22))


def comic_slide(src, out, caption=None, bubbles=(), title=None, brand="factyeap"):
    img = _paper().convert("RGBA")
    pw, ph = W - 2 * M, H - 2 * M
    im = Image.open(src).convert("RGB")
    s = max(pw / im.width, ph / im.height)
    im = im.resize((round(im.width * s), round(im.height * s)), Image.LANCZOS)
    x0, y0 = (im.width - pw) // 2, (im.height - ph) // 2
    img.paste(im.crop((x0, y0, x0 + pw, y0 + ph)), (M, M))
    d = ImageDraw.Draw(img)
    d.rectangle((M - 3, M - 3, W - M + 2, H - M + 2), outline=INK, width=7)
    if title:
        _title(img, *title)
    if caption:
        _caption(img, caption)
    for b in bubbles:
        _bubble(img, b[0], b[1], b[2], *(b[3:] if len(b) > 3 else ()))
    _logo(img, brand)
    img.convert("RGB").save(out, quality=93)
    return out
