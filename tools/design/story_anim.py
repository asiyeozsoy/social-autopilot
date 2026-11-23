"""Credit-free motion for a single illustrated still: slow push-in, a scene effect
(rain, twinkling stars, a light that grows in the dark, fairy lights switching on,
drifting petals or sparkles) and handwritten lines that write on and fade.

python tools/design/story_anim.py spec.json
spec = {"still": "...", "out": "video.mp4", "cover": "cover.jpg", "brand": "tinynotes",
        "dur": 12, "effect": "rain|stars|lightup|fairy|petals|sparkle|none",
        "focus": [0.5, 0.7], "zoom": 1.08, "ink": "dark|light", "seed": 3, "cover_t": 9.5,
        "fx": {...effect options...},
        "lines": [{"t0": 0.4, "t1": 12, "y": 220, "text": "...", "size": 92, "x": 0.5, "ink": "dark"}]}
"""
import json
import math
import subprocess
import sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFilter

sys.path.insert(0, str(Path(__file__).resolve().parent))
from still_anim import caveat  # noqa: E402

ROOT = Path(__file__).resolve().parents[2]
W, H, FPS = 1080, 1920, 30
INK = {"dark": ((44, 32, 26), (255, 250, 242), 0.55), "light": ((255, 248, 236), (18, 12, 8), 0.75)}


def ease(t):
    t = min(1.0, max(0.0, t))
    return t * t * (3 - 2 * t)


def line_layer(text, y, size, x, ink):
    """Returns (rgb float array, alpha float array, x0, x1) for one handwritten line."""
    f = caveat(size)
    col, halo_col, strength = INK[ink]
    tw = ImageDraw.Draw(Image.new("L", (8, 8))).textlength(text, font=f)
    cx = x * W
    x0 = max(30, min(W - 30 - tw, cx - tw / 2))
    m = Image.new("L", (W, H), 0)
    ImageDraw.Draw(m).text((x0, y), text, font=f, fill=255)
    halo = m.filter(ImageFilter.MaxFilter(9)).filter(ImageFilter.GaussianBlur(12)).point(lambda v: int(v * strength))
    a_t = np.asarray(m).astype(np.float32) / 255
    a_h = np.asarray(halo).astype(np.float32) / 255
    alpha = np.maximum(a_t, a_h)
    rgb = (np.array(halo_col, np.float32) * (a_h * (1 - a_t))[..., None] + np.array(col, np.float32) * a_t[..., None])
    rgb = rgb / np.maximum(alpha, 1e-4)[..., None]
    return rgb, alpha, x0, x0 + tw


class Lines:
    def __init__(self, specs, ink):
        self.items = []
        for s in specs:
            rgb, al, x0, x1 = line_layer(s["text"], s["y"], s.get("size", 92), s.get("x", 0.5), s.get("ink", ink))
            ys = np.nonzero(al.max(1) > 0)[0]
            self.items.append((s["t0"], s.get("t1", 999), s.get("write", 0.7), rgb[ys[0]:ys[-1] + 1], al[ys[0]:ys[-1] + 1], ys[0], x0, x1))

    def apply(self, arr, t):
        for t0, t1, wr, rgb, al, y0, x0, x1 in self.items:
            if t < t0 or t > t1 + 0.6:
                continue
            k = ease((t - t0) / wr)  # write-on: reveal left to right with a soft edge
            edge = x0 - 40 + (x1 - x0 + 80) * k
            xs = np.arange(W, dtype=np.float32)
            wipe = np.clip((edge - xs) / 40, 0, 1)[None, :]
            fade = min(1.0, max(0.0, (t1 + 0.6 - t) / 0.6)) if t > t1 else 1.0
            a = (al * wipe * fade)[..., None]
            sl = arr[y0:y0 + al.shape[0]]
            sl[:] = sl * (1 - a) + rgb * a
        return arr


def logo(brand, tone="white"):
    lg = Image.open(ROOT / f"brand/{brand}_wm_{tone}.png").convert("RGBA")
    lw = 150
    lg = lg.resize((lw, int(lg.height * lw / lg.width)), Image.LANCZOS)
    a = np.asarray(lg).astype(np.float32) / 255
    return a[..., :3] * 255, a[..., 3:4] * 0.85, (W - lw - 48, H - lg.height - 70)


def main():
    spec = json.loads(Path(sys.argv[1]).read_text())
    dur, seed = spec.get("dur", 12), spec.get("seed", 3)
    rng = np.random.default_rng(seed)
    src = Image.open(spec["still"]).convert("RGB")
    s = max(W / src.width, H / src.height) * 1.6
    big = src.resize((int(src.width * s), int(src.height * s)), Image.LANCZOS)
    bw, bh = big.size
    base = np.asarray(big).astype(np.float32)
    fx, eff = spec.get("fx", {}), spec.get("effect", "none")
    fxpt = fx.get("point", [0.5, 0.5])

    # effect pre-computation in source (big) pixel space
    if eff == "fairy":
        # bright warm pixels inside the tree box are the bulbs; "off" = dim and desaturate them
        x0, y0, x1, y1 = (int(v * d) for v, d in zip(fx["box"], (bw, bh, bw, bh)))
        r, g, b = base[..., 0], base[..., 1], base[..., 2]
        lum = base.mean(2)
        warm = ((r > 200) & (g > 170) & (b < 170) & (lum > 175)).astype(np.float32)
        box = np.zeros_like(warm)
        box[y0:y1, x0:x1] = 1
        bulbs = np.asarray(Image.fromarray((warm * box * 255).astype(np.uint8)).filter(ImageFilter.MaxFilter(5)).filter(ImageFilter.GaussianBlur(3))).astype(np.float32) / 255
        glow = np.asarray(Image.fromarray((bulbs * 255).astype(np.uint8)).filter(ImageFilter.GaussianBlur(28))).astype(np.float32) / 255
        halo = np.asarray(Image.fromarray((bulbs * 255).astype(np.uint8)).filter(ImageFilter.GaussianBlur(70))).astype(np.float32) / 255
        halo = np.clip(halo * 2.5, 0, 1) * box
        paper = np.median(base[: bh // 4].reshape(-1, 3), 0)
        # "unlit" bulbs: fill them from their surroundings (normalized blur), so they vanish into the branches
        keep = 1 - bulbs
        den = np.asarray(Image.fromarray((keep * 255).astype(np.uint8)).filter(ImageFilter.GaussianBlur(9))).astype(np.float32) / 255
        num = np.stack([np.asarray(Image.fromarray(np.clip(base[..., c] * keep, 0, 255).astype(np.uint8)).filter(ImageFilter.GaussianBlur(9))).astype(np.float32) for c in range(3)], -1)
        dull = num / np.maximum(den, 0.05)[..., None] * 0.93
        off = base * (1 - halo[..., None] * 0.55) + paper * halo[..., None] * 0.55
        off = off * (1 - bulbs[..., None]) + dull * bulbs[..., None]
        # twinkle phases: low-frequency random field so neighbouring bulbs differ
        ph = np.asarray(Image.fromarray((rng.random((bh // 40, bw // 40)) * 255).astype(np.uint8)).resize((bw, bh), Image.NEAREST)).astype(np.float32) / 255 * 6.28
    if eff == "switch":
        offimg = Image.open(fx["off"]).convert("RGB").resize((bw, bh), Image.LANCZOS)
        off = np.asarray(offimg).astype(np.float32)
        diff = np.clip((base - off).mean(2), 0, 255) / 255
        bulbs = np.asarray(Image.fromarray((np.clip(diff * 3, 0, 1) * 255).astype(np.uint8)).filter(ImageFilter.GaussianBlur(4))).astype(np.float32) / 255
        ph = np.asarray(Image.fromarray((rng.random((bh // 40, bw // 40)) * 255).astype(np.uint8)).resize((bw, bh), Image.NEAREST)).astype(np.float32) / 255 * 6.28
    if eff == "lightup":
        px, py = fxpt[0] * bw, fxpt[1] * bh
        yy, xx = np.mgrid[0:bh, 0:bw].astype(np.float32)
        dist = np.sqrt((xx - px) ** 2 + (yy - py) ** 2) / bw
    if eff == "stars":
        lum = base.mean(2)
        ns = 140
        sx = rng.uniform(0, bw, ns)
        sy = rng.uniform(0, bh * fx.get("sky", 0.3), ns)
        sp = rng.uniform(0, 6.28, ns)
        sr = rng.uniform(1.5, 4.0, ns)
        moon = np.clip((lum - 200) / 55, 0, 1)
        moon = np.asarray(Image.fromarray((moon * 255).astype(np.uint8)).filter(ImageFilter.GaussianBlur(60))).astype(np.float32) / 255
    n_p = {"rain": 260, "petals": 26, "sparkle": 40, "lightup": 45}.get(eff, 0)
    P = np.c_[rng.uniform(0, W, n_p), rng.uniform(0, H, n_p), rng.uniform(0.6, 1.4, n_p), rng.uniform(0, 6.28, n_p)] if n_p else None

    lines = Lines(spec.get("lines", []), spec.get("ink", "dark"))
    brand = spec.get("brand", "tinynotes")
    tone = spec.get("logo") or ("maroon" if spec.get("ink", "dark") == "dark" and brand == "tinynotes" else ("ink" if spec.get("ink", "dark") == "dark" else "white"))
    lrgb, la, (lx, ly) = logo(brand, tone)
    out = spec["out"]
    tmp = out + ".silent.mp4"
    enc = subprocess.Popen(["ffmpeg", "-nostdin", "-loglevel", "error", "-y", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}",
                            "-r", str(FPS), "-i", "-", "-c:v", "libx264", "-preset", "veryfast", "-crf", "18", "-pix_fmt", "yuv420p", tmp],
                           stdin=subprocess.PIPE)
    fxf, fyf = spec.get("focus", [0.5, 0.6])
    zoom = spec.get("zoom", 1.08)
    cover_t = spec.get("cover_t", dur - 1.5)
    cover = None
    n = int(dur * FPS)
    for i in range(n):
        t = i / FPS
        k = ease(t / dur)
        z = 1.0 + (zoom - 1.0) * k
        cw, ch = W * 1.6 / z, H * 1.6 / z
        cx = bw / 2 + (fxf * bw - bw / 2) * (1 - 1 / z)
        cy = bh / 2 + (fyf * bh - bh / 2) * (1 - 1 / z)
        cx = min(max(cx, cw / 2), bw - cw / 2)
        cy = min(max(cy, ch / 2), bh - ch / 2)
        ys0, xs0 = int(cy - ch / 2), int(cx - cw / 2)
        if eff == "fairy":
            on = ease((t - fx.get("on", 3.0)) / 0.5)
            tw = 0.75 + 0.25 * np.sin(ph[ys0:ys0 + int(ch), xs0:xs0 + int(cw)] + t * 3.1)
            lit = base[ys0:ys0 + int(ch), xs0:xs0 + int(cw)]
            dk = off[ys0:ys0 + int(ch), xs0:xs0 + int(cw)]
            b_ = (bulbs[ys0:ys0 + int(ch), xs0:xs0 + int(cw)] * tw)[..., None]
            gl = glow[ys0:ys0 + int(ch), xs0:xs0 + int(cw)][..., None]
            crop = dk * (1 - on) + (lit * (1 - b_ * 0.0) + gl * np.array([60, 40, 6], np.float32) * (0.6 + 0.4 * tw[..., None])) * on
        elif eff == "switch":
            sl_ = (slice(ys0, ys0 + int(ch)), slice(xs0, xs0 + int(cw)))
            on = ease((t - fx.get("on", 3.0)) / 0.35)
            # a quick flicker as they come on
            if 0 < t - fx.get("on", 3.0) < 0.5:
                on *= 0.6 + 0.4 * (math.sin((t - fx.get("on", 3.0)) * 60) > 0)
            tw = 0.82 + 0.18 * np.sin(ph[sl_] + t * 3.3)
            lit, dk = base[sl_], off[sl_]
            crop = dk + (lit - dk) * (on * (1 - bulbs[sl_] * (1 - tw)))[..., None]
        elif eff == "lightup":
            g = ease((t - fx.get("on", 2.5)) / fx.get("grow", 4.0))
            flick = 1 + 0.04 * math.sin(t * 7.3) + 0.03 * math.sin(t * 13.1)
            rad = 0.03 + g * fx.get("radius", 0.6) * flick
            lightm = np.clip(1 - dist[ys0:ys0 + int(ch), xs0:xs0 + int(cw)] / rad, 0, 1) ** 1.5
            mult = 0.10 + 0.9 * np.clip(lightm + g ** 2, 0, 1)
            crop = base[ys0:ys0 + int(ch), xs0:xs0 + int(cw)] * mult[..., None]
        elif eff == "stars":
            crop = base[ys0:ys0 + int(ch), xs0:xs0 + int(cw)] * (1 + 0.05 * math.sin(t * 1.3) * moon[ys0:ys0 + int(ch), xs0:xs0 + int(cw)][..., None])
        else:
            crop = base[ys0:ys0 + int(ch), xs0:xs0 + int(cw)]
        fr = np.asarray(Image.fromarray(np.clip(crop, 0, 255).astype(np.uint8)).resize((W, H), Image.BILINEAR)).astype(np.float32)
        img = Image.fromarray(fr.astype(np.uint8))
        if eff == "stars":
            d = ImageDraw.Draw(img, "RGBA")
            for x, y, p, r in zip(sx, sy, sp, sr):
                X, Y = (x - xs0) / cw * W, (y - ys0) / ch * H
                a = max(0.0, math.sin(t * 2.2 + p)) ** 3
                if a > 0.05:
                    rr = r * (0.6 + a)
                    d.ellipse((X - rr, Y - rr, X + rr, Y + rr), fill=(255, 246, 220, int(230 * a)))
                    d.line((X - rr * 3, Y, X + rr * 3, Y), fill=(255, 246, 220, int(120 * a)), width=1)
                    d.line((X, Y - rr * 3, X, Y + rr * 3), fill=(255, 246, 220, int(120 * a)), width=1)
        elif eff == "rain" and P is not None:
            d = ImageDraw.Draw(img, "RGBA")
            for x, y, sp_, p in P:
                Y = (y + t * 1500 * sp_) % (H + 80) - 40
                X = (x - (Y + 40) * 0.12) % W
                d.line((X, Y, X + 6 * sp_, Y + 46 * sp_), fill=(240, 244, 250, int(90 + 70 * sp_)), width=2)
        elif eff == "petals" and P is not None:
            d = ImageDraw.Draw(img, "RGBA")
            for x, y, sp_, p in P:
                Y = (y + t * 70 * sp_) % (H + 60) - 30
                X = (x + 40 * math.sin(t * 0.9 * sp_ + p)) % W
                ang = t * 1.5 * sp_ + p
                rx, ry = 13 * sp_, 6 * sp_ * (0.4 + 0.6 * abs(math.cos(ang)))
                d.ellipse((X - rx, Y - ry, X + rx, Y + ry), fill=tuple(fx.get("color", [244, 196, 48])) + (215,))
        elif eff in ("sparkle", "lightup") and P is not None:
            d = ImageDraw.Draw(img, "RGBA")
            vis = 1.0 if eff == "sparkle" else ease((t - fx.get("on", 2.5) - 1.0) / 2.0)
            cx0, cy0 = fxpt[0] * W, fxpt[1] * H
            for x, y, sp_, p in P:
                if eff == "lightup":  # fireflies orbit the light
                    X = cx0 + (x - W / 2) * 0.55 + 30 * math.sin(t * 0.7 * sp_ + p)
                    Y = cy0 + (y - H / 2) * 0.35 - (t * 18 * sp_ % 300) + 30 * math.cos(t * 0.5 + p)
                else:
                    X = (x + 20 * math.sin(t * 0.6 + p)) % W
                    Y = (y - t * 25 * sp_) % H
                a = vis * max(0.0, math.sin(t * 2.0 * sp_ + p)) ** 2
                if a > 0.03:
                    rr = 3.5 * sp_ + 2
                    d.ellipse((X - rr * 3, Y - rr * 3, X + rr * 3, Y + rr * 3), fill=(255, 214, 120, int(50 * a)))
                    d.ellipse((X - rr, Y - rr, X + rr, Y + rr), fill=(255, 240, 190, int(240 * a)))
        arr = np.asarray(img).astype(np.float32)
        arr = lines.apply(arr, t)
        sl = arr[ly:ly + la.shape[0], lx:lx + la.shape[1]]
        sl[:] = sl * (1 - la) + lrgb * la
        if abs(t - cover_t) < 0.5 / FPS:
            cover = np.clip(arr, 0, 255).astype(np.uint8)
        arr += rng.normal(0, 2.0, arr.shape[:2])[..., None]
        if t > dur - 0.6:  # gentle fade out
            arr *= max(0.0, (dur - t) / 0.6) * 0.4 + 0.6
        enc.stdin.write(np.clip(arr, 0, 255).astype(np.uint8).tobytes())
    enc.stdin.close()
    enc.wait()
    if cover is not None and spec.get("cover"):
        Image.fromarray(cover).save(spec["cover"], quality=92)
    # no music: Asiye picks trending audio herself in the app
    subprocess.run(["ffmpeg", "-nostdin", "-loglevel", "error", "-y", "-i", tmp, "-map", "0:v", "-c:v", "copy", "-an",
                    "-movflags", "+faststart", out], check=True)
    Path(tmp).unlink()
    print("ok", out)


if __name__ == "__main__":
    main()
