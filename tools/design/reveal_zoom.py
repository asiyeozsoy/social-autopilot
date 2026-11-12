"""Credit-free "find the one" reveal: a still held wide, then a slow eased push onto one spot,
with handwritten lines that fade in and out. Built for "this is how I see you" style videos.

python tools/design/reveal_zoom.py still.jpg out.mp4 --focus 0.48,0.50 --zoom 2.6 --brand tinynotes \
    --line "0.3-4.4@300:everyone looks the same..." --line "4.8-10@300:...except you." \
    --line "7.0-10@1560:this is how I see you."
"""
import argparse
import subprocess
import sys
from pathlib import Path

import numpy as np
from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parent))
from still_anim import H, W, text_layer  # noqa: E402

ROOT = Path(__file__).resolve().parents[2]
FPS = 30


def ease(t):
    t = min(1.0, max(0.0, t))
    return t * t * (3 - 2 * t)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("still")
    ap.add_argument("out")
    ap.add_argument("--focus", default="0.5,0.5")
    ap.add_argument("--zoom", type=float, default=2.6)
    ap.add_argument("--hold", type=float, default=1.4, help="seconds held wide before the push")
    ap.add_argument("--push", type=float, default=5.0, help="seconds the push takes")
    ap.add_argument("--dur", type=float, default=10.0)
    ap.add_argument("--brand", default="tinynotes")
    ap.add_argument("--line", action="append", default=[], help="start-end@y:text")
    a = ap.parse_args()
    fx, fy = (float(v) for v in a.focus.split(","))
    src = Image.open(a.still).convert("RGB")
    scale = max(W / src.width, H / src.height) * 2.0  # work at 2x so the push stays sharp
    big = src.resize((int(src.width * scale), int(src.height * scale)), Image.LANCZOS)
    bw, bh = big.size
    lines = []
    for spec in a.line:
        when, txt = spec.split(":", 1)
        span, y = when.split("@")
        t0, t1 = (float(v) for v in span.split("-"))
        lay = np.asarray(text_layer([txt], int(y))[0]).astype(np.float32) / 255
        lines.append((t0, t1, lay))
    logo = Image.open(ROOT / f"brand/{a.brand}_wm_white.png").convert("RGBA")
    lw = 150
    logo = logo.resize((lw, int(logo.height * lw / logo.width)), Image.LANCZOS)
    logo.putalpha(logo.split()[3].point(lambda v: int(v * 0.8)))
    enc = subprocess.Popen(["ffmpeg", "-nostdin", "-loglevel", "error", "-y", "-f", "rawvideo", "-pix_fmt", "rgb24",
                            "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-", "-c:v", "libx264", "-preset", "veryfast",
                            "-crf", "17", "-pix_fmt", "yuv420p", a.out], stdin=subprocess.PIPE)
    n = int(a.dur * FPS)
    rng = np.random.default_rng(7)
    for i in range(n):
        t = i / FPS
        k = ease((t - a.hold) / a.push)
        z = 1 + (a.zoom - 1) * k + 0.04 * max(0.0, t - a.hold - a.push)  # keep drifting a touch after the push
        cw, ch = W * 2 / z, H * 2 / z
        cx = bw / 2 + (fx * bw - bw / 2) * k
        cy = bh / 2 + (fy * bh - bh / 2) * k
        cx = min(max(cx, cw / 2), bw - cw / 2)
        cy = min(max(cy, ch / 2), bh - ch / 2)
        fr = big.crop((int(cx - cw / 2), int(cy - ch / 2), int(cx + cw / 2), int(cy + ch / 2))).resize((W, H), Image.BILINEAR)
        fr = fr.convert("RGBA")
        fr.alpha_composite(logo, (W - lw - 48, H - logo.height - 70))
        arr = np.asarray(fr.convert("RGB")).astype(np.float32)
        for t0, t1, lay in lines:
            al = min(1.0, (t - t0) / 0.7, (t1 - t) / 0.5)
            if al <= 0:
                continue
            al = lay[..., 3:4] * al
            arr = arr * (1 - al) + lay[..., :3] * 255 * al
        arr += rng.normal(0, 2.2, arr.shape[:2])[..., None]  # light film grain
        enc.stdin.write(np.clip(arr, 0, 255).astype(np.uint8).tobytes())
    enc.stdin.close()
    enc.wait()


if __name__ == "__main__":
    main()
