"""Bold closing slides for the engagement carousels.

tinynotes_end(platform, title, sub) -> PIL image: maroon card, big logo, number chips
factyeap_end(platform, title, sub)  -> PIL image: honey card, owl mascot, number chips
"""
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter, ImageFont

ROOT = Path(__file__).resolve().parents[2]
G = "/usr/share/fonts/truetype/google-fonts/"
SIZES = {"instagram": (1080, 1350), "tiktok": (1080, 1920)}
SAFE = {"instagram": (90, 90), "tiktok": (250, 430)}


def font(name, size, wght=None):
    f = ImageFont.truetype(G + name, size)
    if wght:
        try:
            f.set_variation_by_axes([wght])
        except Exception:
            pass
    return f


def centered(d, y, text, f, fill, w):
    d.text(((w - d.textlength(text, font=f)) / 2, y), text, font=f, fill=fill)


def chips(d, y, w, n, fill, text_fill, outline=None, r=58):
    gap = 30
    total = n * 2 * r + (n - 1) * gap
    x = (w - total) / 2
    f = font("Poppins-Bold.ttf", int(r * 0.95))
    for i in range(1, n + 1):
        d.ellipse((x, y, x + 2 * r, y + 2 * r), fill=fill, outline=outline, width=5 if outline else 0)
        t = str(i)
        tw = d.textlength(t, font=f)
        d.text((x + r - tw / 2, y + r - f.size * 0.62), t, font=f, fill=text_fill)
        x += 2 * r + gap
    return y + 2 * r


def comment_bubble(d, cx, cy, s, fill):
    d.rounded_rectangle((cx - s, cy - s * 0.7, cx + s, cy + s * 0.55), radius=s * 0.45, fill=fill)
    d.polygon([(cx - s * 0.45, cy + s * 0.45), (cx - s * 0.75, cy + s * 0.95), (cx - s * 0.05, cy + s * 0.5)], fill=fill)


def tinynotes_end(platform, title="comment your number", sub="then send this to someone who needs theirs", n=5):
    W, H = SIZES[platform]
    top, bottom = SAFE[platform]
    maroon, cream, light = (132, 36, 38), (253, 246, 232), (196, 120, 110)
    im = Image.new("RGB", (W, H), maroon).convert("RGBA")
    glow = Image.new("L", (W, H), 0)
    ImageDraw.Draw(glow).ellipse((W * 0.1, H * 0.05, W * 0.9, H * 0.55), fill=70)
    im = Image.composite(Image.new("RGBA", (W, H), (160, 52, 52, 255)), im, glow.filter(ImageFilter.GaussianBlur(180)))
    d = ImageDraw.Draw(im)
    logo = Image.open(ROOT / "brand/tinynotes_wm_white.png").convert("RGBA")
    lw = 330 if platform == "instagram" else 380
    logo = logo.resize((lw, int(logo.height * lw / logo.width)), Image.LANCZOS)
    block = logo.height + 60 + 40 + 60 + 2 * 96 + 70 + 120 + 60 + 50
    y = top + (H - top - bottom - block) // 2
    im.alpha_composite(logo, ((W - lw) // 2, y))
    y += logo.height + 60
    centered(d, y, "YOUR TURN", font("Poppins-Medium.ttf", 34), light, W)
    y += 60
    tf = font("Lora-Variable.ttf", 92, 650)
    for line in (title.split(" ", 1) if len(title) > 14 else [title]):
        centered(d, y, line, tf, cream, W)
        y += 110
    y += 40
    y = chips(d, y, W, n, None, cream, outline=cream)
    y += 60
    centered(d, y, sub, font("Lora-Italic-Variable.ttf", 40, 400), (240, 210, 200), W)
    return im.convert("RGB")


def owl(im, cx, cy, s, body=(28, 24, 22), belly=(58, 48, 40), eye=(253, 246, 232), beak=(244, 183, 64)):
    """Simple geometric night-owl mascot, centred at (cx, cy), size s."""
    d = ImageDraw.Draw(im)
    sh = Image.new("L", im.size, 0)
    ImageDraw.Draw(sh).ellipse((cx - s * 0.9, cy + s * 1.05, cx + s * 0.9, cy + s * 1.3), fill=90)
    im.paste((0, 0, 0), mask=sh.filter(ImageFilter.GaussianBlur(14)))
    d.polygon([(cx - s * 0.78, cy - s * 0.55), (cx - s * 0.55, cy - s * 1.15), (cx - s * 0.2, cy - s * 0.75)], fill=body)
    d.polygon([(cx + s * 0.78, cy - s * 0.55), (cx + s * 0.55, cy - s * 1.15), (cx + s * 0.2, cy - s * 0.75)], fill=body)
    d.ellipse((cx - s * 0.85, cy - s * 0.9, cx + s * 0.85, cy + s * 1.2), fill=body)
    d.ellipse((cx - s * 0.5, cy + s * 0.05, cx + s * 0.5, cy + s * 1.05), fill=belly)
    for k in range(3):
        yy = cy + s * (0.3 + 0.22 * k)
        for xx in (-0.18, 0.18) if k % 2 == 0 else (0.0,):
            d.arc((cx + s * xx - s * 0.1, yy - s * 0.06, cx + s * xx + s * 0.1, yy + s * 0.08), 200, 340, fill=body, width=max(3, int(s * 0.04)))
    for side in (-1, 1):
        ex = cx + side * s * 0.36
        d.ellipse((ex - s * 0.3, cy - s * 0.55, ex + s * 0.3, cy + s * 0.05), fill=eye)
        d.ellipse((ex - s * 0.13 + side * s * 0.03, cy - s * 0.38, ex + s * 0.13 + side * s * 0.03, cy - s * 0.12), fill=body)
        d.ellipse((ex - s * 0.06 + side * s * 0.06, cy - s * 0.34, ex + s * 0.0 + side * s * 0.06, cy - s * 0.28), fill=eye)
        # sleepy lid: it is 2am
        d.chord((ex - s * 0.3, cy - s * 0.55, ex + s * 0.3, cy + s * 0.05), 180, 360, fill=body)
        d.line((ex - s * 0.28, cy - s * 0.25, ex + s * 0.28, cy - s * 0.25), fill=beak, width=max(3, int(s * 0.035)))
    d.polygon([(cx - s * 0.11, cy - s * 0.02), (cx + s * 0.11, cy - s * 0.02), (cx, cy + s * 0.2)], fill=beak)
    for side in (-1, 1):
        fx = cx + side * s * 0.3
        for t in (-1, 0, 1):
            d.ellipse((fx + t * s * 0.09 - s * 0.05, cy + s * 1.12, fx + t * s * 0.09 + s * 0.05, cy + s * 1.22), fill=beak)


def factyeap_end(platform, title="Comment your number.", sub="Tag your 2am twin.", n=5):
    W, H = SIZES[platform]
    top, bottom = SAFE[platform]
    honey, dark = (244, 183, 64), (24, 21, 19)
    im = Image.new("RGB", (W, H), honey)
    glow = Image.new("L", (W, H), 0)
    ImageDraw.Draw(glow).ellipse((W * 0.15, H * 0.02, W * 0.85, H * 0.5), fill=80)
    im = Image.composite(Image.new("RGB", (W, H), (252, 205, 104)), im, glow.filter(ImageFilter.GaussianBlur(160)))
    s = 170 if platform == "instagram" else 200
    block = int(s * 2.5) + 60 + 50 + 2 * 105 + 50 + 2 * 54 + 60 + 70
    y = top + (H - top - bottom - block) // 2
    owl(im, W // 2, y + int(s * 1.15), s)
    d = ImageDraw.Draw(im)
    comment_bubble(d, W // 2 + s * 1.05, y + s * 0.35, s * 0.32, dark)
    f = font("Poppins-Bold.ttf", int(s * 0.28))
    d.text((W // 2 + s * 1.05 - s * 0.17, y + s * 0.35 - s * 0.24), "#?", font=f, fill=honey)
    y += int(s * 2.5) + 60
    centered(d, y, "YOUR TURN", font("Poppins-Medium.ttf", 34), (110, 72, 20), W)
    y += 50
    tf = font("Poppins-Bold.ttf", 84)
    for line in title.split(" ", 1) if len(title) > 16 else [title]:
        centered(d, y, line, tf, dark, W)
        y += 105
    y += 50
    y = chips(d, y, W, n, dark, honey, r=54)
    y += 60
    centered(d, y, sub, font("Lora-Italic-Variable.ttf", 50, 600), dark, W)
    logo = Image.open(ROOT / "brand/factyeap_wm_white.png").convert("RGBA")
    a = logo.split()[3]
    logo = Image.new("RGBA", logo.size, dark + (255,))
    logo.putalpha(a.point(lambda v: int(v * 0.8)))
    lw = 230
    logo = logo.resize((lw, int(logo.height * lw / logo.width)), Image.LANCZOS)
    im = im.convert("RGBA")
    im.alpha_composite(logo, ((W - lw) // 2, H - bottom - logo.height + 20))
    return im.convert("RGB")


if __name__ == "__main__":
    import sys
    out = Path(sys.argv[1])
    out.mkdir(parents=True, exist_ok=True)
    for p in SIZES:
        tinynotes_end(p).save(out / f"tinynotes_end_{p}.png")
        factyeap_end(p).save(out / f"factyeap_end_{p}.png")
