"""Bring a single AI still to life without spending video credits: slow push-in, drifting
dust motes in the light, a gentle breathing glow, and handwritten lines that fade in.

python tools/design/still_anim.py still.jpg out.mp4 --brand factyeap \
    --line "0.4:he fed me first." --line "4.4:now it's my turn." [--dur 10] [--seed 3]
"""
import argparse
import math
import subprocess
import sys
import tempfile
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(Path(__file__).resolve().parent))
W, H, FPS = 1080, 1920, 30


def caveat(size, wght=700):
    f = ImageFont.truetype(str(ROOT / "brand/fonts/Caveat[wght].ttf"), size)
    try:
        f.set_variation_by_axes([wght])
    except Exception:
        pass
    return f


def text_layer(lines, y0, size=118):
    """One RGBA layer per line: white handwriting with a soft dark halo for readability."""
    f = caveat(size)
    tmp = ImageDraw.Draw(Image.new("L", (8, 8)))
    out = []
    y = y0
    for txt in lines:
        tw = tmp.textlength(txt, font=f)
        m = Image.new("L", (W, H), 0)
        ImageDraw.Draw(m).text(((W - tw) / 2, y), txt, font=f, fill=255)
        halo = m.filter(ImageFilter.MaxFilter(9)).filter(ImageFilter.GaussianBlur(14)).point(lambda v: int(v * 0.75))
        lay = Image.new("RGBA", (W, H), (20, 12, 6, 0))
        lay.putalpha(halo)
        white = Image.new("RGBA", (W, H), (255, 248, 236, 0))
        white.putalpha(m)
        lay.alpha_composite(white)
        out.append(lay)
        y += int(size * 1.08)
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("still")
    ap.add_argument("out")
    ap.add_argument("--brand", default="factyeap")
    ap.add_argument("--line", action="append", default=[], help="start_seconds:text")
    ap.add_argument("--dur", type=float, default=10.0)
    ap.add_argument("--seed", type=int, default=3)
    ap.add_argument("--text-y", type=int, default=150)
    ap.add_argument("--focus", type=float, default=0.62, help="vertical point the camera drifts toward (0-1)")
    a = ap.parse_args()

    src = Image.open(a.still).convert("RGB")
    big = src.resize((int(W * 1.12), int(src.height * W * 1.12 / src.width)), Image.LANCZOS)
    arr = np.asarray(big).astype(np.float32)
    lum = arr.mean(2)
    glow_mask = np.clip((lum - 150) / 90, 0, 1)  # the sunlit patches breathe a little
    glow_mask = np.asarray(Image.fromarray((glow_mask * 255).astype(np.uint8)).filter(ImageFilter.GaussianBlur(25))).astype(np.float32) / 255

    rng = np.random.default_rng(a.seed)
    n = 70
    motes = np.c_[rng.uniform(0, W, n), rng.uniform(0, H * 0.75, n), rng.uniform(1.5, 4.5, n),
                  rng.uniform(-6, 6, n), rng.uniform(-14, -4, n), rng.uniform(0, 6.28, n)]

    starts, texts = [], []
    for ln in a.line:
        t, txt = ln.split(":", 1)
        starts.append(float(t))
        texts.append(txt)
    layers = text_layer(texts, a.text_y)

    tmp = Path(tempfile.mkdtemp())
    enc = subprocess.Popen(["ffmpeg", "-nostdin", "-loglevel", "error", "-y", "-f", "rawvideo", "-pix_fmt", "rgb24",
                            "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-", "-c:v", "libx264", "-preset", "veryfast",
                            "-crf", "17", "-pix_fmt", "yuv420p", str(tmp / "v.mp4")], stdin=subprocess.PIPE)
    frames = int(a.dur * FPS)
    for i in range(frames):
        t = i / FPS
        p = t / a.dur
        ease = p * p * (3 - 2 * p)
        breathe = 1 + 0.045 * math.sin(t * 1.3) + 0.02 * math.sin(t * 3.1)
        lit = arr * (1 + (breathe - 1) * glow_mask[..., None])
        z = 1.0 + 0.09 * ease
        cw, ch = big.width / z / 1.12 * 1.0, None
        # crop window: W x H at scale z inside `big`
        sw, sh = W * 1.12 / (1.12 * z) * 1.12, H * 1.12 / (1.12 * z) * 1.12
        sw, sh = big.width / z, big.width / z * H / W
        cx = big.width / 2
        cy = big.height / 2 + (a.focus - 0.5) * (big.height - sh) * ease * 2
        cy = min(max(cy, sh / 2), big.height - sh / 2)
        box = (cx - sw / 2, cy - sh / 2, cx + sw / 2, cy + sh / 2)
        fr = Image.fromarray(np.clip(lit, 0, 255).astype(np.uint8)).crop(tuple(int(round(v)) for v in box)).resize((W, H), Image.BICUBIC)
        fr = fr.convert("RGBA")
        # dust motes drifting up through the light
        dl = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        dd = ImageDraw.Draw(dl)
        for x, y, r, vx, vy, ph in motes:
            xx = (x + vx * t + 8 * math.sin(t * 0.7 + ph)) % W
            yy = (y + vy * t) % (H * 0.8)
            al = int(110 + 80 * math.sin(t * 1.7 + ph))
            dd.ellipse((xx - r, yy - r, xx + r, yy + r), fill=(255, 236, 200, max(0, al)))
        fr.alpha_composite(dl.filter(ImageFilter.GaussianBlur(1.2)))
        for s, lay in zip(starts, layers):
            k = (t - s) / 0.8
            if k <= 0:
                continue
            k = min(1.0, k)
            l2 = lay.copy()
            l2.putalpha(l2.split()[3].point(lambda v, k=k: int(v * k)))
            fr.alpha_composite(l2)
        enc.stdin.write(fr.convert("RGB").tobytes())
    enc.stdin.close()
    enc.wait()
    subprocess.run(["cp", str(tmp / "v.mp4"), a.out], check=True)


if __name__ == "__main__":
    main()
