"""Factyeap credit-free format: dark card, "FACT #N", a relatable statement, then "yeap."

post:  python tools/design/factyeap_render.py post  <out_dir> <number> "<statement>"
video: python tools/design/factyeap_render.py video <out.mp4> <number> "<statement>"
"""
import random
import subprocess
import sys
import tempfile
import wave
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

ROOT = Path(__file__).resolve().parents[2]
G = "/usr/share/fonts/truetype/google-fonts/"
BG, WHITE, AMBER, DIM = (17, 16, 15), (244, 240, 233), (244, 183, 64), (120, 112, 104)
SIZES = {"instagram": (1080, 1350), "tiktok": (1080, 1920)}
SAFE = {"instagram": (130, 120), "tiktok": (300, 470)}  # top, bottom margins kept clear of app UI


def font(name, size, wght=None):
    f = ImageFont.truetype(G + name, size)
    if wght:
        try:
            f.set_variation_by_axes([wght])
        except Exception:
            pass
    return f


def wrap(draw, words, f, maxw):
    lines, line = [], []
    for w in words:
        if line and draw.textlength(" ".join(line + [w]), font=f) > maxw:
            lines.append(line)
            line = [w]
        else:
            line.append(w)
    lines.append(line)
    return lines


def background(w, h, seed):
    random.seed(seed)
    im = Image.new("RGB", (w, h), BG)
    glow = Image.new("L", (w, h), 0)
    ImageDraw.Draw(glow).ellipse((-w * 0.3, -h * 0.25, w * 1.0, h * 0.55), fill=40)
    glow = glow.filter(ImageFilter.GaussianBlur(160))
    im = Image.composite(Image.new("RGB", (w, h), (52, 44, 32)), im, glow)
    noise = Image.effect_noise((w, h), 18).convert("RGB")
    im = Image.blend(im, noise, 0.04)
    return im.convert("RGBA")


def layout(platform, statement):
    w, h = SIZES[platform]
    top, bottom = SAFE[platform]
    tmp = ImageDraw.Draw(Image.new("RGB", (10, 10)))
    size = 92 if len(statement) < 60 else 80 if len(statement) < 95 else 68
    while True:
        f = font("Poppins-Bold.ttf", size)
        lines = wrap(tmp, statement.split(), f, w - 200)
        block = 90 + len(lines) * int(size * 1.22) + 60 + 150
        if block < h - top - bottom - 160 or size <= 52:
            break
        size -= 4
    y0 = top + (h - top - bottom - 160 - block) // 2 + 20
    return dict(w=w, h=h, f=f, size=size, lines=lines, y0=y0, bottom=bottom)


def draw_frame(platform, number, statement, seed, n_words=None, yeap_scale=1.0, logo_alpha=1.0, label=None, sign="yeap."):
    L = layout(platform, statement)
    im = background(L["w"], L["h"], seed)
    d = ImageDraw.Draw(im)
    x, y = 100, L["y0"]
    d.text((x, y), label or f"FACT #{number:03d}", font=font("Poppins-Medium.ttf", 36), fill=AMBER)
    y += 90
    shown, total = 0, sum(len(l) for l in L["lines"])
    limit = total if n_words is None else n_words
    for line in L["lines"]:
        cx = x
        for wd in line:
            if shown >= limit:
                break
            d.text((cx, y), wd, font=L["f"], fill=WHITE)
            cx += d.textlength(wd + " ", font=L["f"])
            shown += 1
        y += int(L["size"] * 1.22)
    if yeap_scale > 0 and sign:
        yf = font("Lora-Italic-Variable.ttf", max(8, int(120 * yeap_scale)), 600)
        d.text((x - 4, y + 40 + int(60 * (1 - yeap_scale))), sign, font=yf, fill=AMBER)
    logo = Image.open(ROOT / "brand/factyeap_wm_white.png").convert("RGBA")
    lw = 230
    logo = logo.resize((lw, int(logo.height * lw / logo.width)), Image.LANCZOS)
    logo.putalpha(logo.split()[3].point(lambda v: int(v * 0.55 * logo_alpha)))
    im.alpha_composite(logo, ((L["w"] - lw) // 2, L["h"] - L["bottom"] - logo.height))
    return im.convert("RGB"), total


def post(out_dir, number, statement):
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    for p in SIZES:
        draw_frame(p, number, statement, f"fy{number}")[0].save(out / f"{p}.png")


def beat(path, seconds, yeap_at):
    sr = 44100
    n_total = int(sr * seconds)
    out = np.zeros(n_total)
    spb = 60 / 92
    t = 0.0
    i = 0
    while t < seconds:
        s = int(t * sr)
        if i % 4 in (0, 2):  # soft kick
            n = np.arange(int(sr * 0.25))
            f = 110 * np.exp(-n / (sr * 0.04)) + 45
            kick = np.sin(2 * np.pi * np.cumsum(f) / sr) * np.exp(-n / (sr * 0.09)) * 0.35
            e = min(n_total, s + len(kick))
            out[s:e] += kick[: e - s]
        hs = int((t + spb / 2) * sr)  # off-beat hat
        n = np.arange(int(sr * 0.05))
        hat = np.random.default_rng(i).standard_normal(len(n)) * np.exp(-n / (sr * 0.012)) * 0.05
        e = min(n_total, hs + len(hat))
        if hs < n_total:
            out[hs:e] += hat[: e - hs]
        t += spb
        i += 1
    n = np.arange(n_total)
    chords = [(220.0, 261.63, 329.63), (174.61, 220.0, 261.63)]
    bar = int(sr * spb * 4)
    for k, start in enumerate(range(0, n_total, bar)):
        seg = n[start:start + bar]
        out[start:start + bar] += sum(np.sin(2 * np.pi * f * seg / sr) for f in chords[k % 2]) * 0.03
    s = int(yeap_at * sr)  # "yeap" chime
    n = np.arange(int(sr * 1.2))
    chime = (np.sin(2 * np.pi * 1318.5 * n / sr) + 0.5 * np.sin(2 * np.pi * 1975.5 * n / sr)) * np.exp(-n / (sr * 0.25)) * 0.2
    e = min(n_total, s + len(chime))
    out[s:e] += chime[: e - s]
    k = int(sr * 0.8)
    out[-k:] *= np.linspace(1, 0, k)
    with wave.open(str(path), "w") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(sr)
        w.writeframes((np.clip(out, -1, 1) * 32000).astype(np.int16).tobytes())


def video(out, number, statement, fps=30, dur=9.0):
    tmp = Path(tempfile.mkdtemp())
    words = len(statement.split())
    start, per = 0.5, 0.2
    yeap_at = start + words * per + 0.9
    cache = {}
    for i in range(int(dur * fps)):
        t = i / fps
        k = 0 if t < start else min(words, int((t - start) / per) + 1)
        ys = 0.0 if t < yeap_at else min(1.0, (t - yeap_at) / 0.18)
        ys = ys * (1.0 + 0.12 * max(0.0, 1 - (t - yeap_at) / 0.35)) if ys > 0 else 0  # small pop
        key = (k, round(ys, 2))
        if key not in cache:
            cache.clear()
            cache[key] = draw_frame("tiktok", number, statement, f"fy{number}", k, ys)[0]
        cache[key].save(tmp / f"f{i:04d}.jpg", quality=92)
    beat(tmp / "a.wav", dur, yeap_at)
    subprocess.run(["ffmpeg", "-nostdin", "-loglevel", "error", "-y", "-framerate", str(fps), "-i", str(tmp / "f%04d.jpg"),
                    "-i", str(tmp / "a.wav"), "-c:v", "libx264", "-preset", "veryfast", "-crf", "20", "-pix_fmt", "yuv420p",
                    "-c:a", "aac", "-b:a", "128k", "-shortest", "-movflags", "+faststart", str(out)], check=True)


if __name__ == "__main__":
    mode, target, number, statement = sys.argv[1], sys.argv[2], int(sys.argv[3]), sys.argv[4]
    (post if mode == "post" else video)(target, number, statement)


def carousel(out_dir, slides, seed="types"):
    """slides: list of (label, statement, sign) -> instagram_01.png ... and tiktok_01.png ..."""
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    for i, (label, statement, sign) in enumerate(slides, 1):
        for p in SIZES:
            draw_frame(p, 0, statement, f"{seed}{i}", label=label, sign=sign)[0].save(out / f"{p}_{i:02d}.png")
