"""TinyNotes Facebook-only daily cards (1080x1350): good morning in many languages,
gentle wishes, short positive quotes and short scripture verses.

card(kind, main, sub, label, seed) -> PIL image
  kind "morning": main = greeting in some language, sub = "good morning in <language>"
  kind "note":    main = the note,                  sub = signature ("me", "a friend")
  kind "verse":   main = verse text,                 sub = reference ("Psalm 30:5 (KJV)")
"""
import random
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter, ImageFont

ROOT = Path(__file__).resolve().parents[2]
G = "/usr/share/fonts/truetype/google-fonts/"
CREAM, PAPER, MAROON, INK = (253, 250, 241), (255, 253, 247), (132, 36, 38), (92, 40, 38)
W, H = 1080, 1350


def font(name, size, wght=None):
    f = ImageFont.truetype(G + name, size)
    if wght:
        try:
            f.set_variation_by_axes([wght])
        except Exception:
            pass
    return f


def wrap(d, text, f, maxw):
    lines, line = [], []
    for wd in text.split():
        if line and d.textlength(" ".join(line + [wd]), font=f) > maxw:
            lines.append(" ".join(line))
            line = [wd]
        else:
            line.append(wd)
    lines.append(" ".join(line))
    return lines


def background(seed):
    im = Image.new("RGB", (W, H), CREAM)
    noise = Image.effect_noise((W, H), 12).convert("RGB")
    im = Image.blend(im, Image.composite(im, noise, Image.new("L", (W, H), 235)), 0.35)
    return im.convert("RGBA")


def sun(d, cx, cy, r):
    d.ellipse((cx - r, cy - r, cx + r, cy + r), outline=MAROON, width=6)
    for k in range(8):
        import math
        a = k * math.pi / 4
        d.line((cx + math.cos(a) * r * 1.4, cy + math.sin(a) * r * 1.4, cx + math.cos(a) * r * 1.8,
                cy + math.sin(a) * r * 1.8), fill=MAROON, width=6)


def card(kind, main, sub, label, seed="d"):
    rng = random.Random(seed)
    im = background(seed)
    d = ImageDraw.Draw(im)
    lf = font("Poppins-Medium.ttf", 36)
    d.text(((W - d.textlength(label.upper(), font=lf)) / 2, 150), label.upper(), font=lf, fill=MAROON)

    cw = 880
    if kind == "morning":
        fs = 132 if len(main) < 10 else 110 if len(main) < 14 else 92
        mf = font("Lora-Italic-Variable.ttf", fs, 600)
    else:
        fs = 66 if len(main) < 70 else 58 if len(main) < 110 else 50
        mf = font("Lora-Italic-Variable.ttf", fs, 500)
    sf = font("Lora-Italic-Variable.ttf", 40 if kind != "morning" else 44, 400)
    tmp = ImageDraw.Draw(Image.new("RGB", (10, 10)))
    lines = wrap(tmp, main, mf, cw - 180)
    lh = int(fs * 1.35)
    extra = 170 if kind == "morning" else 0
    ch = 120 + extra + len(lines) * lh + 150
    c = Image.new("RGBA", (cw + 80, ch + 80), (0, 0, 0, 0))
    cd = ImageDraw.Draw(c)
    cd.rounded_rectangle((40, 40, 40 + cw, 40 + ch), 22, fill=PAPER + (255,))
    cd.rectangle((40 + cw / 2 - 95, 18, 40 + cw / 2 + 95, 76), fill=(232, 214, 196, 210))
    y = 40 + 110
    if kind == "morning":
        sun(cd, 40 + cw / 2, y + 60, 34)
        y += extra
    for ln in lines:
        x = 40 + (cw - cd.textlength(ln, font=mf)) / 2 if kind != "note" else 40 + 90
        cd.text((x, y), ln, font=mf, fill=INK)
        y += lh
    heart = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 34)
    if kind == "note":
        hx = 40 + cw - 90 - cd.textlength("♥", font=heart)
        cd.text((hx, y + 46), "♥", font=heart, fill=MAROON)
        cd.text((hx - 18 - cd.textlength(sub, font=sf), y + 38), sub, font=sf, fill=MAROON)
    else:
        t = f"— {sub}" if kind == "verse" else sub
        cd.text((40 + (cw - cd.textlength(t, font=sf)) / 2, y + 38), t, font=sf, fill=MAROON)
    angle = rng.choice([-1.6, -1.0, 1.1, 1.7])
    c = c.rotate(angle, resample=Image.BICUBIC, expand=True)
    sh = Image.new("RGBA", c.size, (0, 0, 0, 0))
    sh.putalpha(c.split()[3].point(lambda v: int(v * 0.22)).filter(ImageFilter.GaussianBlur(18)))
    top, bottom = 230, H - 230
    cy = top + max(0, (bottom - top - c.height) // 2)
    cx = (W - c.width) // 2
    im.alpha_composite(sh, (cx + 10, cy + 18))
    im.alpha_composite(c, (cx, cy))
    logo = Image.open(ROOT / "brand/tinynotes_wm_maroon.png").convert("RGBA")
    lw = 150
    logo = logo.resize((lw, int(logo.height * lw / logo.width)), Image.LANCZOS)
    im.alpha_composite(logo, ((W - lw) // 2, H - logo.height - 70))
    return im.convert("RGB")
