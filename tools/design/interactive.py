"""Interactive templates: Factyeap 'which owl are you today?' grid and the
TinyNotes 'I'm a ___ person' slider card. Everything is drawn here (no stock art).

python tools/design/interactive.py <out_dir>
"""
import math
import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter

sys.path.insert(0, str(Path(__file__).resolve().parent))
from end_cards import ROOT, SAFE, SIZES, centered, font  # noqa: E402

BODY, BELLY, EYE, HONEY, DARK, CREAM = (28, 24, 22), (58, 48, 40), (253, 246, 232), (244, 183, 64), (17, 16, 15), (253, 246, 232)
PINK, BLUE = (240, 110, 120), (120, 190, 240)


def owl_body(d, cx, cy, s):
    d.polygon([(cx - s * .78, cy - s * .55), (cx - s * .55, cy - s * 1.15), (cx - s * .2, cy - s * .75)], fill=BODY)
    d.polygon([(cx + s * .78, cy - s * .55), (cx + s * .55, cy - s * 1.15), (cx + s * .2, cy - s * .75)], fill=BODY)
    d.ellipse((cx - s * .85, cy - s * .9, cx + s * .85, cy + s * 1.2), fill=BODY)
    d.ellipse((cx - s * .5, cy + s * .05, cx + s * .5, cy + s * 1.05), fill=BELLY)
    w = max(2, int(s * .04))
    for k, xs in enumerate(((-.18, .18), (0,), (-.18, .18))):
        yy = cy + s * (.3 + .22 * k)
        for xx in xs:
            d.arc((cx + s * xx - s * .1, yy - s * .06, cx + s * xx + s * .1, yy + s * .08), 200, 340, fill=BODY, width=w)
    d.polygon([(cx - s * .11, cy - s * .02), (cx + s * .11, cy - s * .02), (cx, cy + s * .2)], fill=HONEY)
    for side in (-1, 1):
        fx = cx + side * s * .3
        for t in (-1, 0, 1):
            d.ellipse((fx + t * s * .09 - s * .05, cy + s * 1.12, fx + t * s * .09 + s * .05, cy + s * 1.22), fill=HONEY)


def heart(d, x, y, r, fill):
    d.ellipse((x - r, y - r * .6, x, y + r * .4), fill=fill)
    d.ellipse((x, y - r * .6, x + r, y + r * .4), fill=fill)
    d.polygon([(x - r * .97, y), (x + r * .97, y), (x, y + r * 1.1)], fill=fill)


def owl(d, cx, cy, s, mood):
    owl_body(d, cx, cy, s)
    w = max(3, int(s * .05))
    for side in (-1, 1):
        ex, ey = cx + side * s * .36, cy - s * .25
        box = (ex - s * .3, ey - s * .3, ex + s * .3, ey + s * .3)
        if mood == "sleepy":
            d.ellipse(box, fill=EYE)
            d.ellipse((ex - s * .12, ey - s * .1, ex + s * .12, ey + s * .14), fill=BODY)
            d.chord(box, 180, 360, fill=BODY)
            d.line((ex - s * .28, ey, ex + s * .28, ey), fill=HONEY, width=w)
        elif mood == "shocked":
            d.ellipse((ex - s * .34, ey - s * .34, ex + s * .34, ey + s * .34), fill=EYE)
            d.ellipse((ex - s * .06, ey - s * .06, ex + s * .06, ey + s * .06), fill=BODY)
        elif mood == "love":
            d.ellipse(box, fill=EYE)
            heart(d, ex, ey - s * .05, s * .17, PINK)
        elif mood == "crying":
            d.ellipse(box, fill=EYE)
            d.arc((ex - s * .2, ey - s * .1, ex + s * .2, ey + s * .2), 200, 340, fill=BODY, width=w)
            d.ellipse((ex - s * .07, ey + s * .3, ex + s * .07, ey + s * .52), fill=BLUE)
            d.polygon([(ex - s * .065, ey + s * .37), (ex + s * .065, ey + s * .37), (ex, ey + s * .24)], fill=BLUE)
        elif mood == "angry":
            d.ellipse(box, fill=EYE)
            d.ellipse((ex - s * .12, ey - s * .02, ex + s * .12, ey + s * .22), fill=BODY)
            d.polygon([(ex - s * .34, ey - s * .32 + side * s * .0), (ex + s * .34, ey - s * .32), (ex + side * s * .34, ey - s * .08)], fill=BODY)
        elif mood == "nerd":
            d.ellipse(box, fill=EYE)
            d.ellipse((ex - s * .1, ey - s * .1, ex + s * .1, ey + s * .1), fill=BODY)
            d.ellipse((ex - s * .34, ey - s * .34, ex + s * .34, ey + s * .34), outline=HONEY, width=w)
        elif mood == "party":
            d.arc((ex - s * .2, ey - s * .05, ex + s * .2, ey + s * .3), 200, 340, fill=EYE, width=w + 2)
        elif mood == "caffeine":
            d.ellipse((ex - s * .34, ey - s * .34, ex + s * .34, ey + s * .34), fill=EYE)
            for r in (.24, .14, .05):
                d.ellipse((ex - s * r, ey - s * r, ex + s * r, ey + s * r), outline=BODY, width=max(2, w - 1))
        elif mood == "dead":
            d.ellipse(box, fill=EYE)
            for a, b in ((-1, 1), (1, -1)):
                d.line((ex - s * .14, ey + a * s * .14, ex + s * .14, ey + b * s * .14), fill=BODY, width=w + 1)
    if mood == "nerd":
        d.line((cx - s * .02, cy - s * .25, cx + s * .02, cy - s * .25), fill=HONEY, width=w)
    if mood == "party":
        d.polygon([(cx - s * .3, cy - s * .78), (cx + s * .3, cy - s * .78), (cx + s * .05, cy - s * 1.5)], fill=PINK)
        d.ellipse((cx - s * .03, cy - s * 1.6, cx + s * .13, cy - s * 1.44), fill=HONEY)
        for k in range(10):
            a = k * 0.63
            x, y = cx + math.cos(a) * s * 1.15, cy - s * .4 + math.sin(a) * s * .9
            d.rectangle((x, y, x + s * .07, y + s * .07), fill=(PINK, BLUE, HONEY)[k % 3])
    if mood == "caffeine":
        x, y = cx + s * .95, cy + s * .55
        d.rounded_rectangle((x - s * .22, y - s * .25, x + s * .22, y + s * .3), s * .06, fill=EYE)
        d.arc((x + s * .12, y - s * .12, x + s * .38, y + s * .14), 270, 90, fill=EYE, width=w)
        for k in (-1, 0, 1):
            d.arc((x + k * s * .1 - s * .05, y - s * .55, x + k * s * .1 + s * .05, y - s * .3), 90, 270, fill=EYE, width=max(2, w - 2))
    if mood == "sleepy":
        f = font("Poppins-Bold.ttf", int(s * .32))
        d.text((cx + s * .75, cy - s * 1.25), "z", font=f, fill=BODY)
        d.text((cx + s * 1.0, cy - s * 1.55), "Z", font=font("Poppins-Bold.ttf", int(s * .42)), fill=BODY)
    if mood == "shocked":
        d.text((cx + s * .85, cy - s * 1.3), "!", font=font("Poppins-Bold.ttf", int(s * .7)), fill=BODY)


MOODS = ["sleepy", "shocked", "love", "crying", "angry", "nerd", "party", "caffeine", "dead"]


def owl_grid(platform, title="which owl are you today?"):
    W, H = SIZES[platform]
    top, bottom = SAFE[platform]
    im = Image.new("RGB", (W, H), DARK)
    d = ImageDraw.Draw(im)
    tf = font("Poppins-Bold.ttf", 64)
    gap, margin = 18, 60
    cell = (W - 2 * margin - 2 * gap) // 3
    grid_h = 3 * cell + 2 * gap
    block = 80 + 40 + grid_h + 40 + 60
    y = top + (H - top - bottom - block) // 2
    centered(d, y, title, tf, CREAM, W)
    y += 120
    nf = font("Poppins-Bold.ttf", 40)
    for i, mood in enumerate(MOODS):
        r, c = divmod(i, 3)
        x0, y0 = margin + c * (cell + gap), y + r * (cell + gap)
        d.rounded_rectangle((x0, y0, x0 + cell, y0 + cell), 26, fill=HONEY)
        owl(d, x0 + cell / 2, y0 + cell * .5, cell * .22, mood)
        d.ellipse((x0 + 14, y0 + 14, x0 + 74, y0 + 74), fill=DARK)
        t = str(i + 1)
        d.text((x0 + 44 - d.textlength(t, font=nf) / 2, y0 + 17), t, font=nf, fill=HONEY)
    y += grid_h + 40
    logo = Image.open(ROOT / "brand/factyeap_wm_white.png").convert("RGBA")
    lw = 210
    logo = logo.resize((lw, int(logo.height * lw / logo.width)), Image.LANCZOS)
    im = im.convert("RGBA")
    im.alpha_composite(logo, ((W - lw) // 2, int(y)))
    return im.convert("RGB")


SLIDERS = [("Call", "Text", .25), ("Hugs", "Words", .7), ("Morning person", "Night owl", .8),
           ("Flowers", "Handwritten notes", .85), ("Plans", "Spontaneous", .4), ("Say it first", "Wait for it", .3)]


def person_card(platform, rows=SLIDERS):
    W, H = SIZES[platform]
    top, bottom = SAFE[platform]
    maroon, ink = (132, 36, 38), (92, 40, 38)
    im = Image.new("RGB", (W, H), CREAM)
    noise = Image.effect_noise((W, H), 12).convert("RGB")
    im = Image.blend(im, Image.composite(im, noise, Image.new("L", (W, H), 235)), .35)
    d = ImageDraw.Draw(im)
    row_h = 138 if platform == "instagram" else 175
    logo = Image.open(ROOT / "brand/tinynotes_wm_maroon.png").convert("RGBA")
    lw = 120
    logo = logo.resize((lw, int(logo.height * lw / logo.width)), Image.LANCZOS)
    block = 130 + 70 + len(rows) * row_h + 20 + 40 + 50 + logo.height
    y = top + (H - top - bottom - block) // 2
    tf = font("Lora-Italic-Variable.ttf", 86, 600)
    centered(d, y, "I'm a ___ person", tf, maroon, W)
    y += 130
    centered(d, y, "the love edition", font("Poppins-Medium.ttf", 32), (176, 110, 100), W)
    y += 70
    lf = font("Lora-Italic-Variable.ttf", 40, 500)
    x0, x1 = 120, W - 120
    for left, right, pos in rows:
        d.text((x0, y), left, font=lf, fill=ink)
        d.text((x1 - d.textlength(right, font=lf), y), right, font=lf, fill=ink)
        ly = y + 82
        d.rounded_rectangle((x0, ly - 5, x1, ly + 5), 5, fill=(226, 205, 190))
        kx = x0 + (x1 - x0) * pos
        d.rounded_rectangle((x0, ly - 5, kx, ly + 5), 5, fill=(196, 120, 110))
        sh = Image.new("L", (W, H), 0)
        ImageDraw.Draw(sh).ellipse((kx - 30, ly - 24, kx + 30, ly + 36), fill=60)
        im.paste((150, 120, 110), mask=sh.filter(ImageFilter.GaussianBlur(8)))
        d = ImageDraw.Draw(im)
        d.ellipse((kx - 30, ly - 30, kx + 30, ly + 30), fill=(255, 253, 247), outline=maroon, width=4)
        heart(d, kx, ly - 3, 11, maroon)
        y += row_h
    y += 20
    centered(d, y, "screenshot it, move the hearts, tag your person", font("Poppins-Medium.ttf", 30), maroon, W)
    im = im.convert("RGBA")
    im.alpha_composite(logo, ((W - lw) // 2, int(y + 90)))
    return im.convert("RGB")


if __name__ == "__main__":
    out = Path(sys.argv[1])
    out.mkdir(parents=True, exist_ok=True)
    for p in SIZES:
        owl_grid(p).save(out / f"factyeap_owl_grid_{p}.png")
        person_card(p).save(out / f"tinynotes_person_{p}.png")
