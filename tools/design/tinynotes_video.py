"""Render a TinyNotes note video (1080x1920, ~10 s): the note writes itself word
by word on the paper card, the signature appears, then it holds. Music is a
short original music-box melody synthesised here, so there are no licence issues.

python tools/design/tinynotes_video.py out.mp4 "hook" "note text" "signature" [seed]
"""
import math
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
CREAM, PAPER, MAROON, INK = (253, 250, 241), (255, 253, 247), (132, 36, 38), (92, 40, 38)
W, H, FPS, DUR = 1080, 1920, 30, 10.0


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


def background(seed):
    random.seed(seed)
    im = Image.new("RGB", (W, H), CREAM)
    g = Image.effect_noise((W, H), 12).convert("RGB")
    return Image.blend(im, Image.composite(im, g, Image.new("L", (W, H), 235)), 0.35).convert("RGBA")


def music(path, seconds, seed):
    sr = 44100
    t_total = int(sr * seconds)
    out = np.zeros(t_total)
    rng = random.Random(seed)
    scale = [523.25, 587.33, 659.25, 783.99, 880.0, 1046.5]  # C major pentatonic
    t = 0.35
    while t < seconds - 1.2:
        f = rng.choice(scale)
        n = np.arange(int(sr * 1.8))
        env = np.exp(-n / (sr * 0.45))
        tone = (np.sin(2 * np.pi * f * n / sr) + 0.3 * np.sin(2 * np.pi * 2 * f * n / sr)) * env * 0.18
        s = int(t * sr)
        e = min(t_total, s + len(tone))
        out[s:e] += tone[: e - s]
        t += rng.choice([0.45, 0.45, 0.6, 0.9])
    n = np.arange(t_total)
    pad = sum(np.sin(2 * np.pi * f * n / sr) for f in (130.81, 196.0, 261.63)) * 0.025
    out += pad * np.minimum(1, n / (sr * 1.5))
    fade = np.ones(t_total)
    k = int(sr * 1.2)
    fade[-k:] = np.linspace(1, 0, k)
    out = np.clip(out * fade, -1, 1)
    with wave.open(str(path), "w") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(sr)
        w.writeframes((out * 32000).astype(np.int16).tobytes())


def render(out, hook, note, sign, seed="tn"):
    tmp = Path(tempfile.mkdtemp())
    base = background(seed)
    d = ImageDraw.Draw(base)
    hf = font("Poppins-Medium.ttf", 40)
    y = 260
    for line in wrap(d, hook.upper().split(), hf, W - 200):
        txt = " ".join(line)
        d.text(((W - d.textlength(txt, font=hf)) / 2, y), txt, font=hf, fill=MAROON)
        y += 57
    logo = Image.open(ROOT / "brand/tinynotes_wm_maroon.png").convert("RGBA")
    lw = 160
    logo = logo.resize((lw, int(logo.height * lw / logo.width)), Image.LANCZOS)
    base.alpha_composite(logo, ((W - lw) // 2, H - logo.height - 430))

    cw = 860
    fs = 72 if len(note) < 70 else 62 if len(note) < 120 else 54
    nf = font("Lora-Italic-Variable.ttf", fs, 500)
    sf = font("Lora-Italic-Variable.ttf", int(fs * 0.72), 400)
    heart = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 40)
    words = note.split()
    lines = wrap(d, words, nf, cw - 170)
    lh = int(fs * 1.45)
    ch = len(lines) * lh + 280
    rng = random.Random(seed)
    angle = rng.choice([-1.8, -1.2, 1.3, 1.9])
    top, bottom = y + 40, H - 430 - logo.height - 40
    cy = top + max(0, (bottom - top - ch) // 2)

    def card(n_words, sign_alpha):
        c = Image.new("RGBA", (cw + 80, ch + 80), (0, 0, 0, 0))
        cd = ImageDraw.Draw(c)
        cd.rounded_rectangle((40, 40, 40 + cw, 40 + ch), 20, fill=PAPER + (255,))
        cd.rectangle((40 + cw / 2 - 90, 20, 40 + cw / 2 + 90, 76), fill=(232, 214, 196, 210))
        ty, shown = 40 + 95, 0
        for line in lines:
            x = 110
            for w in line:
                if shown >= n_words:
                    break
                cd.text((x, ty), w, font=nf, fill=INK)
                x += cd.textlength(w + " ", font=nf)
                shown += 1
            ty += lh
        if sign_alpha > 0:
            a = int(255 * sign_alpha)
            sw = cd.textlength(sign, font=sf)
            hx = 40 + cw - 110
            cd.text((hx - 16 - sw, ty + 30), sign, font=sf, fill=MAROON + (a,))
            cd.text((hx, ty + 36), "♥", font=heart, fill=MAROON + (a,))
        c = c.rotate(angle, resample=Image.BICUBIC, expand=True)
        sh = Image.new("RGBA", c.size, (0, 0, 0, 0))
        sh.putalpha(c.split()[3].point(lambda v: int(v * 0.22)).filter(ImageFilter.GaussianBlur(18)))
        return c, sh

    frames = int(DUR * FPS)
    write_start, write_end = 0.6, 0.6 + min(6.0, 0.28 * len(words) + 1.2)
    cache = {}
    for i in range(frames):
        t = i / FPS
        k = 0 if t < write_start else min(len(words), int((t - write_start) / (write_end - write_start) * len(words)) + 1)
        sa = max(0.0, min(1.0, (t - write_end - 0.2) / 0.6))
        key = (k, round(sa, 2))
        if key not in cache:
            cache.clear()
            cache[key] = card(k, sa)
        c, sh = cache[key]
        intro = min(1.0, t / 0.6)  # card slides up and fades in
        dy = int((1 - intro) ** 2 * 60)
        frame = base.copy()
        cx = (W - c.width) // 2
        cc, ss = c.copy(), sh.copy()
        if intro < 1:
            cc.putalpha(cc.split()[3].point(lambda v: int(v * intro)))
            ss.putalpha(ss.split()[3].point(lambda v: int(v * intro * intro)))
        frame.alpha_composite(ss, (cx + 10, cy + 18 + dy))
        frame.alpha_composite(cc, (cx, cy + dy))
        frame.convert("RGB").save(tmp / f"f{i:04d}.jpg", quality=92)
    music(tmp / "m.wav", DUR, seed)
    subprocess.run(["ffmpeg", "-nostdin", "-loglevel", "error", "-y", "-framerate", str(FPS), "-i", str(tmp / "f%04d.jpg"),
                    "-i", str(tmp / "m.wav"), "-c:v", "libx264", "-preset", "veryfast", "-crf", "20", "-pix_fmt", "yuv420p",
                    "-c:a", "aac", "-b:a", "128k", "-shortest", "-movflags", "+faststart", str(out)], check=True)


if __name__ == "__main__":
    render(sys.argv[1], sys.argv[2], sys.argv[3], sys.argv[4], sys.argv[5] if len(sys.argv) > 5 else "tn")
