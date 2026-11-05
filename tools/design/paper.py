"""Torn-paper / paper-cut look: textured layers with ragged edges, white torn fringe,
soft drop shadows, sticker-style character cutouts and torn caption strips."""
from pathlib import Path

import numpy as np
from PIL import Image, ImageChops, ImageDraw, ImageFilter, ImageFont
from scipy import ndimage

ROOT = Path(__file__).resolve().parents[2]
FONTS = ROOT / "brand" / "fonts"
PAPER_WHITE = (250, 246, 236)


def hand_font(size):
    return ImageFont.truetype(str(FONTS / "PatrickHand-Regular.ttf"), size)


def _noise(size, scale, seed):
    rng = np.random.default_rng(seed)
    w, h = size
    small = rng.standard_normal((max(2, h // scale + 2), max(2, w // scale + 2)))
    big = Image.fromarray(((small - small.min()) / (np.ptp(small) + 1e-9) * 255).astype(np.uint8)).resize((w, h), Image.BICUBIC)
    return np.asarray(big).astype(float) / 255 - 0.5


def grain(size, seed=0, strength=14):
    """Paper fibre texture as a multiplicative L image around 255."""
    rng = np.random.default_rng(seed)
    fine = rng.standard_normal((size[1], size[0])) * strength * 0.35
    coarse = _noise(size, 40, seed + 1) * strength
    return np.clip(255 + fine + coarse, 200, 255)


def torn(mask, jag=6, seed=0):
    """Roughen the edge of an L mask so it looks torn by hand."""
    m = np.asarray(mask).astype(float) / 255
    dist_in = ndimage.distance_transform_edt(m > 0.5)
    dist_out = ndimage.distance_transform_edt(m <= 0.5)
    sd = dist_in - dist_out
    n = _noise(mask.size, 18, seed) * 2 * jag + _noise(mask.size, 5, seed + 7) * jag * 0.8
    out = np.clip((sd + n) * 0.9 + 0.5, 0, 1)
    return Image.fromarray((out * 255).astype(np.uint8), "L")


def textured(color, size, seed=0):
    g = grain(size, seed)
    arr = np.stack([np.clip(c * g / 255, 0, 255) for c in color], -1)
    return Image.fromarray(arr.astype(np.uint8), "RGB")


def paper_layer(canvas, mask, color, seed=0, jag=6, fringe=5, shadow=0.28, offset=(5, 9)):
    """Paste a coloured torn-paper piece shaped like `mask` onto `canvas` (RGBA, same size)."""
    size = canvas.size
    body = torn(mask, jag, seed)
    if fringe:
        edge = torn(mask.filter(ImageFilter.MaxFilter(fringe * 2 + 1)), jag, seed + 3)
    else:
        edge = body
    if shadow:
        sh = Image.new("RGBA", size, (40, 26, 14, 0))
        sh.putalpha(ImageChops.offset(edge, *offset).filter(ImageFilter.GaussianBlur(7)).point(lambda v: int(v * shadow)))
        canvas.alpha_composite(sh)
    if fringe:
        w = textured(PAPER_WHITE, size, seed + 5).convert("RGBA")
        w.putalpha(edge)
        canvas.alpha_composite(w)
    c = textured(color, size, seed + 9).convert("RGBA")
    c.putalpha(body)
    canvas.alpha_composite(c)


def sticker(img, border=16, seed=0, shadow=0.35):
    """Character cut out with scissors: ragged white paper border and a drop shadow.
    The border also hides any fringe left from keying the original background."""
    pad = border * 3
    a = img.split()[3]
    a = a.point(lambda v: 255 if v > 150 else 0).filter(ImageFilter.MinFilter(5))  # trim the soft fringe
    W, H = img.width + pad * 2, img.height + pad * 2
    am = Image.new("L", (W, H), 0)
    am.paste(a, (pad, pad))
    outer = torn(am.filter(ImageFilter.MaxFilter(border * 2 + 1)).filter(ImageFilter.GaussianBlur(4)).point(lambda v: 255 if v > 100 else 0), 4, seed)
    out = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    sh = Image.new("RGBA", (W, H), (30, 20, 10, 0))
    sh.putalpha(ImageChops.offset(outer, 6, 10).filter(ImageFilter.GaussianBlur(8)).point(lambda v: int(v * shadow)))
    out.alpha_composite(sh)
    paper = textured(PAPER_WHITE, (W, H), seed + 2).convert("RGBA")
    paper.putalpha(outer)
    out.alpha_composite(paper)
    body = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    src = img.copy()
    src.putalpha(a)
    body.paste(src, (pad, pad))
    out.alpha_composite(body)
    return out


def strip(text, width_max=900, size=72, seed=0, angle=-1.5, color=PAPER_WHITE, ink=(34, 30, 28)):
    """A torn paper strip with handwritten text, as an RGBA image."""
    f = hand_font(size)
    tmp = ImageDraw.Draw(Image.new("RGB", (10, 10)))
    lines = []
    for part in text.split("\n"):
        line = []
        for wd in part.split():
            if line and tmp.textlength(" ".join(line + [wd]), font=f) > width_max - 80:
                lines.append(" ".join(line))
                line = [wd]
            else:
                line.append(wd)
        lines.append(" ".join(line))
    lh = int(size * 1.15)
    tw = max(tmp.textlength(ln, font=f) for ln in lines)
    w, h = int(tw + 90), int(lh * len(lines) + 50)
    W, H = w + 60, h + 60
    m = Image.new("L", (W, H), 0)
    ImageDraw.Draw(m).rectangle((30, 30, 30 + w, 30 + h), fill=255)
    im = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    paper_layer(im, m, color, seed=seed, jag=5, fringe=0, shadow=0.35, offset=(4, 7))
    d = ImageDraw.Draw(im)
    y = 30 + 22
    for ln in lines:
        d.text((30 + (w - tmp.textlength(ln, font=f)) / 2, y), ln, font=f, fill=ink)
        y += lh
    return im.rotate(angle, resample=Image.BICUBIC, expand=True)
