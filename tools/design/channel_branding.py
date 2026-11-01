"""Profile pictures and cover/banner art for the Facebook pages and YouTube channels.

python tools/design/channel_branding.py <out_dir>
"""
import random
import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter, ImageFont

sys.path.insert(0, str(Path(__file__).parent))
from end_cards import owl  # noqa: E402

ROOT = Path(__file__).resolve().parents[2]
G = "/usr/share/fonts/truetype/google-fonts/"
CREAM, PAPER, MAROON, INK = (253, 250, 241), (255, 253, 247), (132, 36, 38), (92, 40, 38)
BG, WHITE, AMBER = (17, 16, 15), (244, 240, 233), (244, 183, 64)
TN_LOGO = Path("/mnt/user-data/uploads/tiny-notes-for-u-logo.png")


def font(name, size, wght=None):
    f = ImageFont.truetype(G + name, size)
    if wght:
        try:
            f.set_variation_by_axes([wght])
        except Exception:
            pass
    return f


def paper_bg(w, h):
    im = Image.new("RGB", (w, h), CREAM)
    noise = Image.effect_noise((w, h), 12).convert("RGB")
    return Image.blend(im, Image.composite(im, noise, Image.new("L", (w, h), 235)), 0.35)


def dark_bg(w, h, glow_box):
    im = Image.new("RGB", (w, h), BG)
    glow = Image.new("L", (w, h), 0)
    ImageDraw.Draw(glow).ellipse(glow_box, fill=55)
    im = Image.composite(Image.new("RGB", (w, h), (60, 48, 30)), im, glow.filter(ImageFilter.GaussianBlur(min(w, h) // 5)))
    return Image.blend(im, Image.effect_noise((w, h), 18).convert("RGB"), 0.035)


def tn_logo(width):
    logo = Image.open(TN_LOGO).convert("RGB")
    bb = Image.eval(logo.convert("L"), lambda v: 255 if v < 200 else 0).getbbox()
    logo = logo.crop(bb)
    mask = Image.eval(logo.convert("L"), lambda v: max(0, min(255, (235 - v) * 3)))
    solid = Image.new("RGBA", logo.size, MAROON + (255,))
    solid.putalpha(mask)
    return solid.resize((width, int(solid.height * width / solid.width)), Image.LANCZOS)


def note_card(text, sign, w, fs, angle, seed):
    nf = font("Lora-Italic-Variable.ttf", fs, 500)
    sf = font("Lora-Italic-Variable.ttf", int(fs * 0.7), 400)
    tmp = ImageDraw.Draw(Image.new("RGB", (10, 10)))
    words, lines, line = text.split(), [], []
    for wd in words:
        if line and tmp.textlength(" ".join(line + [wd]), font=nf) > w - 2 * int(fs * 1.1):
            lines.append(" ".join(line))
            line = [wd]
        else:
            line.append(wd)
    lines.append(" ".join(line))
    lh = int(fs * 1.4)
    h = int(fs * 1.6) + len(lines) * lh + int(fs * 1.8)
    c = Image.new("RGBA", (w + 60, h + 60), (0, 0, 0, 0))
    d = ImageDraw.Draw(c)
    d.rounded_rectangle((30, 30, 30 + w, 30 + h), int(fs * 0.3), fill=PAPER + (255,))
    d.rectangle((30 + w / 2 - fs * 1.3, 14, 30 + w / 2 + fs * 1.3, 14 + fs * 0.8), fill=(232, 214, 196, 210))
    y = 30 + int(fs * 1.4)
    for ln in lines:
        d.text((30 + int(fs * 1.1), y), ln, font=nf, fill=INK)
        y += lh
    hf = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", int(fs * 0.6))
    hx = 30 + w - int(fs * 1.1) - d.textlength("♥", font=hf)
    d.text((hx, y + int(fs * 0.42)), "♥", font=hf, fill=MAROON)
    d.text((hx - fs * 0.3 - d.textlength(sign, font=sf), y + int(fs * 0.3)), sign, font=sf, fill=MAROON)
    c = c.rotate(angle, resample=Image.BICUBIC, expand=True)
    sh = Image.new("RGBA", c.size, (0, 0, 0, 0))
    sh.putalpha(c.split()[3].point(lambda v: int(v * 0.2)).filter(ImageFilter.GaussianBlur(14)))
    return c, sh


def place(im, card, x, y):
    c, sh = card
    im.alpha_composite(sh, (x + 8, y + 14))
    im.alpha_composite(c, (x, y))


def tinynotes_avatar(size=1080):
    im = paper_bg(size, size).convert("RGBA")
    logo = tn_logo(int(size * 0.62))
    im.alpha_composite(logo, ((size - logo.width) // 2, (size - logo.height) // 2 + int(size * 0.01)))
    return im.convert("RGB")


NOTES = [("you're doing better than you think.", "me"), ("drink some water. text them back.", "a friend"),
         ("rest is productive too.", "me"), ("someone smiled because of you today.", "u know who")]


def tinynotes_cover(w, h, safe_w, safe_h):
    im = paper_bg(w, h).convert("RGBA")
    cx, cy = w // 2, h // 2
    logo = tn_logo(int(safe_h * 0.58))
    im.alpha_composite(logo, (cx - logo.width // 2, cy - logo.height // 2 - int(safe_h * 0.07)))
    tf = font("Poppins-Medium.ttf", int(safe_h * 0.05))
    d = ImageDraw.Draw(im)
    tag = "A TINY NOTE FOR WHOEVER NEEDS IT TODAY"
    d.text((cx - d.textlength(tag, font=tf) / 2, cy + logo.height // 2 - int(safe_h * 0.01)), tag, font=tf, fill=MAROON)
    cw, fs = int(safe_w * 0.2), int(safe_h * 0.045)
    spots = [(-0.52, -0.4, -5), (-0.54, 0.06, 4), (0.3, -0.42, 4), (0.32, 0.05, -3)]
    for (text, sign), (fx, fy, a) in zip(NOTES, spots):
        card = note_card(text, sign, cw, fs, a, text)
        place(im, card, int(cx + fx * safe_w), int(cy + fy * safe_h))
    return im.convert("RGB")


def factyeap_avatar(size=1080):
    im = dark_bg(size, size, (size * 0.1, size * 0.05, size * 0.9, size * 0.85))
    owl(im, size // 2, int(size * 0.42), int(size * 0.22), body=(40, 35, 31), belly=(72, 60, 48))
    d = ImageDraw.Draw(im)
    f = font("Lora-Italic-Variable.ttf", int(size * 0.13), 600)
    t = "yeap."
    d.text(((size - d.textlength(t, font=f)) / 2, int(size * 0.72)), t, font=f, fill=AMBER)
    return im


def factyeap_cover(w, h, safe_w, safe_h):
    cx, cy = w // 2, h // 2
    im = dark_bg(w, h, (cx - safe_w * 0.6, cy - safe_h * 0.9, cx + safe_w * 0.2, cy + safe_h * 0.7))
    s = int(safe_h * 0.24)
    owl(im, int(cx + safe_w * 0.33), int(cy - safe_h * 0.12), s, body=(40, 35, 31), belly=(72, 60, 48))
    d = ImageDraw.Draw(im)
    x = int(cx - safe_w * 0.44)
    d.text((x, int(cy - safe_h * 0.36)), "FACT #∞", font=font("Poppins-Medium.ttf", int(safe_h * 0.085)), fill=AMBER)
    bf = font("Poppins-Bold.ttf", int(safe_h * 0.15))
    y = int(cy - safe_h * 0.2)
    for line in ("Small facts about", "being a person."):
        d.text((x, y), line, font=bf, fill=WHITE)
        y += int(safe_h * 0.18)
    d.text((x - 4, y + int(safe_h * 0.02)), "yeap.", font=font("Lora-Italic-Variable.ttf", int(safe_h * 0.17), 600), fill=AMBER)
    logo = Image.open(ROOT / "brand/factyeap_wm_white.png").convert("RGBA")
    lw = int(safe_w * 0.13)
    logo = logo.resize((lw, int(logo.height * lw / logo.width)), Image.LANCZOS)
    logo.putalpha(logo.split()[3].point(lambda v: int(v * 0.6)))
    im = im.convert("RGBA")
    im.alpha_composite(logo, (int(cx + safe_w * 0.33) - lw // 2, int(cy + safe_h * 0.3)))
    return im.convert("RGB")


if __name__ == "__main__":
    out = Path(sys.argv[1])
    out.mkdir(parents=True, exist_ok=True)
    tinynotes_avatar().save(out / "tinynotes_profile.png")
    factyeap_avatar().save(out / "factyeap_profile.png")
    # Facebook cover 1640x624: mobile shows the centre ~1100x624
    tinynotes_cover(1640, 624, 1180, 560).save(out / "tinynotes_fb_cover.png")
    factyeap_cover(1640, 624, 1180, 560).save(out / "factyeap_fb_cover.png")
    # YouTube banner 2560x1440: always-visible safe area 1546x423
    tinynotes_cover(2560, 1440, 1546, 423).save(out / "tinynotes_yt_banner.png")
    factyeap_cover(2560, 1440, 1546, 423).save(out / "factyeap_yt_banner.png")
