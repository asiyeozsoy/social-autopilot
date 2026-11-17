"""Me / my mom" style label slides: handwritten labels with hand-drawn curved arrows on an illustration.

from label_slide import label_slide, title_slide, text_slide
label_slide("in.jpg", "out.jpg", [("ME", (700, 1000), (600, 880)), ("MY MOM", (190, 420), (400, 560))], brand="tinynotes")
Each label = (text, text_centre_xy, arrow_tip_xy) in the 1080x1350 frame.
"""
import math
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter, ImageFont

ROOT = Path(__file__).resolve().parents[2]
W, H = 1080, 1350


def font(size, wght=700):
    f = ImageFont.truetype(str(ROOT / "brand/fonts/Caveat[wght].ttf"), size)
    try:
        f.set_variation_by_axes([wght])
    except Exception:
        pass
    return f


def _trim(im):
    """Cut away a plain paper border some generations come with."""
    import numpy as np
    a = np.asarray(im.convert("L")).astype(int)
    h, w = a.shape
    def edge(line):
        return line.mean() > 225 and line.std() < 18
    t = 0
    while t < h // 8 and edge(a[t]):
        t += 1
    b = h - 1
    while b > h * 7 // 8 and edge(a[b]):
        b -= 1
    l = 0
    while l < w // 8 and edge(a[:, l]):
        l += 1
    r = w - 1
    while r > w * 7 // 8 and edge(a[:, r]):
        r -= 1
    pad = 12 if (t or l or b < h - 1 or r < w - 1) else 0
    return im.crop((l + pad, t + pad, r - pad, b - pad)) if pad else im


def fit(src):
    im = _trim(Image.open(src).convert("RGB"))
    s = max(W / im.width, H / im.height)
    im = im.resize((round(im.width * s), round(im.height * s)), Image.LANCZOS)
    x, y = (im.width - W) // 2, (im.height - H) // 2
    return im.crop((x, y, x + W, y + H))


INK_DARK = (34, 26, 20)
INK_LIGHT = (255, 255, 255)
LEAF = (236, 178, 62)  # autumn-leaf yellow for the closing slide


def _ink_for(im, box):
    """Black text on light art, white text on dark art (decided from the area the label covers)."""
    import numpy as np
    x0, y0, x1, y1 = (max(0, int(v)) for v in box)
    a = np.asarray(im.convert("L").crop((x0, y0, min(W, x1), min(H, y1)))).astype(float)
    return (INK_DARK, (255, 250, 240)) if a.mean() > 150 else (INK_LIGHT, (20, 14, 10))


def _shadowed(base, draw_fn, halo_color=(20, 14, 10), strength=0.75):
    """Draw once into a mask, add a soft contrasting halo under it, then the stroke on top."""
    layer = Image.new("RGBA", base.size, (0, 0, 0, 0))
    draw_fn(ImageDraw.Draw(layer))
    alpha = layer.split()[3]
    halo = Image.new("RGBA", base.size, halo_color + (0,))
    halo.putalpha(alpha.filter(ImageFilter.MaxFilter(9)).filter(ImageFilter.GaussianBlur(4)).point(lambda v: int(v * strength)))
    base.alpha_composite(halo)
    base.alpha_composite(layer)


def _arrow(d, start, tip, bend=0.25, color=INK_LIGHT):
    (x0, y0), (x1, y1) = start, tip
    mx, my = (x0 + x1) / 2, (y0 + y1) / 2
    nx, ny = -(y1 - y0), (x1 - x0)
    cx, cy = mx + nx * bend, my + ny * bend
    pts = []
    for i in range(41):
        t = i / 40
        pts.append(((1 - t) ** 2 * x0 + 2 * (1 - t) * t * cx + t * t * x1, (1 - t) ** 2 * y0 + 2 * (1 - t) * t * cy + t * t * y1))
    d.line(pts, fill=color + (255,), width=6, joint="curve")
    ax, ay = pts[-1]
    bx, by = pts[-6]
    ang = math.atan2(ay - by, ax - bx)
    for da in (2.6, -2.6):
        d.line([(ax, ay), (ax + 28 * math.cos(ang + da), ay + 28 * math.sin(ang + da))], fill=color + (255,), width=6)


def _logo(im, brand):
    logo = Image.open(ROOT / f"brand/{brand}_wm_white.png").convert("RGBA")
    lw = 130
    logo = logo.resize((lw, int(logo.height * lw / logo.width)), Image.LANCZOS)
    logo.putalpha(logo.split()[3].point(lambda v: int(v * 0.85)))
    im.alpha_composite(logo, (W - lw - 36, H - logo.height - 34))


def label_slide(src, out, labels, brand="tinynotes", size=78):
    im = fit(src).convert("RGBA")
    f = font(size)
    for text, (tx, ty), tip in labels:
        tw = ImageDraw.Draw(im).textlength(text, font=f)
        # arrow leaves from the label edge nearest the tip
        sx = tx + (tw / 2 + 14 if tip[0] > tx + tw / 2 else (-tw / 2 - 14 if tip[0] < tx - tw / 2 else 0))
        sy = ty + (size * 0.55 if tip[1] > ty + size * 0.4 else (-size * 0.5 if tip[1] < ty - size * 0.4 else 0))
        bend = 0.25 if (tip[0] - sx) * (tip[1] - sy) >= 0 else -0.25
        ink, halo = _ink_for(im, (tx - tw / 2 - 20, ty - size * 0.6, tx + tw / 2 + 20, ty + size * 0.6))

        def draw(d, text=text, tx=tx, ty=ty, tw=tw, sx=sx, sy=sy, tip=tip, bend=bend, ink=ink):
            d.text((tx - tw / 2, ty - size * 0.55), text, font=f, fill=ink + (255,))
            _arrow(d, (sx, sy), tip, bend, ink)
        _shadowed(im, draw, halo, 0.6 if ink == INK_DARK else 0.75)
    _logo(im, brand)
    im.convert("RGB").save(out, quality=94)


def title_slide(src, out, lines, y=150, brand="tinynotes", size=104):
    im = fit(src).convert("RGBA")
    f = font(size)
    probe = ImageDraw.Draw(im)
    wmax = max(probe.textlength(ln, font=f) for ln in lines)
    ink, halo = _ink_for(im, ((W - wmax) / 2, y, (W + wmax) / 2, y + size * 1.05 * len(lines)))

    def draw(d):
        yy = y
        for ln in lines:
            tw = d.textlength(ln, font=f)
            d.text(((W - tw) / 2, yy), ln, font=f, fill=ink + (255,))
            yy += int(size * 1.05)
    _shadowed(im, draw, halo, 0.6 if ink == INK_DARK else 0.75)
    _logo(im, brand)
    im.convert("RGB").save(out, quality=94)


def _brown_paper(seed=3):
    """Dark coffee-brown background with a painted-paper texture so it sits with the gouache art."""
    import numpy as np
    rng = np.random.default_rng(seed)
    base = np.array([62, 42, 30], float)
    small = rng.normal(0, 1, (H // 24, W // 24))
    blot = np.asarray(Image.fromarray(((small - small.min()) / np.ptp(small) * 255).astype("uint8")).resize((W, H), Image.BICUBIC)).astype(float) / 255
    grain = rng.normal(0, 1, (H, W))
    fibres = np.asarray(Image.fromarray((rng.random((H // 2, W // 12)) * 255).astype("uint8")).resize((W, H), Image.BILINEAR)).astype(float) / 255
    yy, xx = np.mgrid[0:H, 0:W]
    vign = 1 - 0.35 * (((xx - W / 2) / W) ** 2 + ((yy - H / 2) / H) ** 2) * 2.2
    img = base[None, None, :] * (0.82 + 0.3 * blot[..., None]) * (0.95 + 0.08 * fibres[..., None]) * vign[..., None]
    img += grain[..., None] * 5
    return Image.fromarray(np.clip(img, 0, 255).astype("uint8"), "RGB").filter(ImageFilter.GaussianBlur(0.6))


def text_slide(out, lines, brand="tinynotes", size=88, heart=True):
    im = _brown_paper().convert("RGBA")
    d = ImageDraw.Draw(im)
    f = font(size, 650)
    total = len(lines) * size * 1.25
    yy = (H - total) / 2 - 40
    for ln in lines:
        tw = d.textlength(ln, font=f)
        d.text(((W - tw) / 2, yy), ln, font=f, fill=LEAF)
        yy += size * 1.25
    if heart:
        cx, cy, r = W / 2, yy + 70, 26
        col = (214, 112, 70)
        d.ellipse((cx - r * 1.9, cy - r, cx - r * 0.1, cy + r * 0.8), fill=col)
        d.ellipse((cx + r * 0.1, cy - r, cx + r * 1.9, cy + r * 0.8), fill=col)
        d.polygon([(cx - r * 1.85, cy - r * 0.05), (cx + r * 1.85, cy - r * 0.05), (cx, cy + r * 2.0)], fill=col)
    _logo(im, brand)
    im.convert("RGB").save(out, quality=94)
