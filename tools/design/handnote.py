"""Minimal handwritten note video (TinyNotes): a short line appears word by word on paper,
a little doodle draws itself, the camera keeps drifting (no frozen ending).

python tools/design/handnote.py out.mp4 "hey.\\nI love you." [heart|sun|smile] [seed]
"""
import math
import subprocess
import sys
import tempfile
from pathlib import Path

import numpy as np
from PIL import Image, ImageChops, ImageDraw, ImageFilter, ImageFont

sys.path.insert(0, str(Path(__file__).resolve().parent))
import paper as P  # noqa: E402
from tinynotes_video import music  # noqa: E402

ROOT = Path(__file__).resolve().parents[2]
W, H, FPS, DUR = 1080, 1920, 30, 7.5
INK = (38, 36, 52)
RED = (196, 52, 58)
SS = 2  # draw text supersampled for smooth handwriting edges


def caveat(size, wght=650):
    f = ImageFont.truetype(str(ROOT / "brand/fonts/Caveat[wght].ttf"), size)
    try:
        f.set_variation_by_axes([wght])
    except Exception:
        pass
    return f


def background(seed):
    g = P.grain((W, H), seed, strength=10)
    base = np.array((250, 245, 234), float)
    arr = np.clip(base[None, None, :] * g[..., None] / 255, 0, 255)
    # soft vignette like a sheet under a lamp
    yy, xx = np.mgrid[0:H, 0:W]
    v = 1 - 0.10 * (((xx - W / 2) / (W / 2)) ** 2 + ((yy - H / 2) / (H / 2)) ** 2)
    return Image.fromarray(np.clip(arr * v[..., None], 0, 255).astype(np.uint8), "RGB")


def layout(text):
    lines = text.split("\n")
    size = 190 if max(len(ln) for ln in lines) <= 11 else 150 if max(len(ln) for ln in lines) <= 16 else 120
    f = caveat(size * SS)
    tmp = ImageDraw.Draw(Image.new("L", (10, 10)))
    lh = int(size * 1.15 * SS)
    total_h = lh * len(lines)
    y0 = (H * SS - total_h) // 2 - 120 * SS
    words = []  # (x, y, word)
    space = tmp.textlength(" ", font=f)
    for i, ln in enumerate(lines):
        w = tmp.textlength(ln, font=f)
        x = (W * SS - w) / 2 + (i % 2) * 24 * SS - 12 * SS
        y = y0 + i * lh
        for wd in ln.split():
            words.append((x, y, wd))
            x += tmp.textlength(wd, font=f) + space
    return f, words, y0 + total_h


def doodle_points(kind, cx, cy, s):
    pts = []
    if kind == "heart":
        for i in range(121):
            t = math.pi * 2 * i / 120 + math.pi
            x = 16 * math.sin(t) ** 3
            y = 13 * math.cos(t) - 5 * math.cos(2 * t) - 2 * math.cos(3 * t) - math.cos(4 * t)
            pts.append((cx + x * s, cy - y * s))
        return [pts]
    if kind == "sun":
        circ = [(cx + 9 * s * math.cos(a), cy + 9 * s * math.sin(a)) for a in np.linspace(0, 2 * math.pi, 80)]
        rays = [[(cx + 13 * s * math.cos(a), cy + 13 * s * math.sin(a)), (cx + 19 * s * math.cos(a), cy + 19 * s * math.sin(a))]
                for a in np.linspace(0, 2 * math.pi, 9)[:-1]]
        return [circ] + rays
    if kind == "smile":
        circ = [(cx + 14 * s * math.cos(a), cy + 14 * s * math.sin(a)) for a in np.linspace(0, 2 * math.pi, 80)]
        mouth = [(cx + 8 * s * math.cos(a), cy + 2 * s + 8 * s * math.sin(a)) for a in np.linspace(0.2, math.pi - 0.2, 30)]
        return [circ, [(cx - 5 * s, cy - 5 * s), (cx - 5 * s, cy - 3 * s)], [(cx + 5 * s, cy - 5 * s), (cx + 5 * s, cy - 3 * s)], mouth]
    return []


def render(out, text, doodle="heart", seed=1):
    bg = background(seed)
    f, words, text_bottom = layout(text)
    n = len(words)
    t_write0, per, fade = 0.3, 0.42, 0.18
    t_doodle0 = t_write0 + per * n + 0.15
    strokes = doodle_points(doodle, W / 2 + 40, text_bottom / SS + 150, 7.5)
    total_pts = sum(len(s) for s in strokes)
    wm = Image.open(ROOT / "brand/tinynotes_wm_maroon.png").convert("RGBA")
    wm = wm.resize((150, int(wm.height * 150 / wm.width)), Image.LANCZOS)
    wm.putalpha(wm.split()[3].point(lambda v: int(v * 0.55)))
    tmp = Path(tempfile.mkdtemp())
    proc = subprocess.Popen(["ffmpeg", "-nostdin", "-loglevel", "error", "-y", "-f", "rawvideo", "-pix_fmt", "rgb24",
                             "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-", "-c:v", "libx264", "-preset", "veryfast",
                             "-crf", "18", "-pix_fmt", "yuv420p", str(tmp / "v.mp4")], stdin=subprocess.PIPE)
    word_masks = []
    for x, y, wd in words:
        m = Image.new("L", (W * SS, H * SS), 0)
        ImageDraw.Draw(m).text((x, y), wd, font=f, fill=255)
        word_masks.append(m.resize((W, H), Image.LANCZOS))
    for i in range(int(DUR * FPS)):
        t = i / FPS
        # words appear one by one: a quick ink fade with a small settle into place
        layer = Image.new("L", (W, H), 0)
        for j, m in enumerate(word_masks):
            a = (t - (t_write0 + j * per)) / fade
            if a <= 0:
                continue
            a = min(1.0, a)
            dy = int((1 - a) * 14)
            mm = m.point(lambda v, a=a: int(v * a))
            if dy:
                mm = mm.transform(mm.size, Image.AFFINE, (1, 0, 0, 0, 1, -dy))
            layer = ImageChops.lighter(layer, mm)
        small = layer
        fr = bg.copy()
        fr.paste(Image.new("RGB", (W, H), INK), (0, 0), small)
        # doodle
        if t > t_doodle0 and strokes:
            m = int(min(1, (t - t_doodle0) / 0.9) * total_pts)
            d = ImageDraw.Draw(fr)
            left = m
            for s in strokes:
                seg = s[:max(0, min(len(s), left))]
                left -= len(s)
                if len(seg) > 1:
                    d.line(seg, fill=RED, width=11, joint="curve")
        fr = fr.convert("RGBA")
        fr.alpha_composite(wm, ((W - wm.width) // 2, H - wm.height - 300))
        # gentle drift so the ending never freezes
        z = 1.0 + 0.035 * (t / DUR)
        ox = 6 * math.sin(t * 0.7)
        cw_, ch_ = W / z, H / z
        fr = fr.crop((W / 2 - cw_ / 2 + ox, H / 2 - ch_ / 2, W / 2 + cw_ / 2 + ox, H / 2 + ch_ / 2)).resize((W, H), Image.BICUBIC)
        proc.stdin.write(fr.convert("RGB").tobytes())
    proc.stdin.close()
    proc.wait()
    music(tmp / "m.wav", DUR, f"hn{seed}")
    subprocess.run(["ffmpeg", "-nostdin", "-loglevel", "error", "-y", "-i", str(tmp / "v.mp4"), "-i", str(tmp / "m.wav"),
                    "-map", "0:v", "-map", "1:a", "-c:v", "copy", "-c:a", "aac", "-ac", "2", "-ar", "48000", "-shortest",
                    "-movflags", "+faststart", str(out)], check=True)


if __name__ == "__main__":
    render(sys.argv[1], sys.argv[2].replace("\\n", "\n"), *(sys.argv[3:4] or ["heart"]), *(int(x) for x in sys.argv[4:5]))
