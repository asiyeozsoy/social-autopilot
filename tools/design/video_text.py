"""Put the same handwritten fade-in lines used by still_anim.py on top of a real video clip.

python tools/design/video_text.py in.mp4 out.mp4 --line "-1:she tied my shoes" --line "4.3:now I tie hers." [--text-y 190]
"""
import argparse
import subprocess
import sys
from pathlib import Path

import numpy as np
from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parent))
from still_anim import W, H, text_layer  # noqa: E402


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("src")
    ap.add_argument("out")
    ap.add_argument("--line", action="append", default=[])
    ap.add_argument("--text-y", type=int, default=190)
    a = ap.parse_args()
    starts, ends, layers = [], [], []
    plain = []
    for ln in a.line:
        t, txt = ln.split(":", 1)
        if "@" in t or "-" in t.lstrip("-"):  # "start-end@y:text" = its own window and height
            span, _, y = t.partition("@")
            t0, _, t1 = span.lstrip("-").partition("-")
            t0 = -float(t0) if span.startswith("-") else float(t0)
            starts.append(t0)
            ends.append(float(t1) if t1 else 1e9)
            layers.append(np.asarray(text_layer([txt], int(y) if y else a.text_y)[0]).astype(np.float32) / 255)
        else:
            plain.append((float(t), txt))
    for (t0, _), lay in zip(plain, text_layer([p[1] for p in plain], a.text_y)):
        starts.append(t0)
        ends.append(1e9)
        layers.append(np.asarray(lay).astype(np.float32) / 255)
    fps_s = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries", "stream=r_frame_rate",
                            "-of", "csv=p=0", a.src], capture_output=True, text=True).stdout.strip()
    num, den = fps_s.split("/")
    fps = float(num) / float(den)
    dec = subprocess.Popen(["ffmpeg", "-nostdin", "-loglevel", "error", "-i", a.src, "-vf",
                            f"scale={W}:-2:flags=lanczos,crop={W}:{H}", "-f", "rawvideo", "-pix_fmt", "rgb24", "-"],
                           stdout=subprocess.PIPE)
    enc = subprocess.Popen(["ffmpeg", "-nostdin", "-loglevel", "error", "-y", "-f", "rawvideo", "-pix_fmt", "rgb24",
                            "-s", f"{W}x{H}", "-r", f"{fps}", "-i", "-", "-c:v", "libx264", "-preset", "veryfast",
                            "-crf", "17", "-pix_fmt", "yuv420p", a.out], stdin=subprocess.PIPE)
    i = 0
    while True:
        buf = dec.stdout.read(W * H * 3)
        if len(buf) < W * H * 3:
            break
        fr = np.frombuffer(buf, np.uint8).reshape(H, W, 3).astype(np.float32)
        t = i / fps
        for s, e, lay in zip(starts, ends, layers):
            k = min(1.0, (t - s) / 0.8, (e - t) / 0.5)
            if k <= 0:
                continue
            al = lay[..., 3:4] * k
            fr = fr * (1 - al) + lay[..., :3] * 255 * al
        enc.stdin.write(np.clip(fr, 0, 255).astype(np.uint8).tobytes())
        i += 1
    enc.stdin.close()
    enc.wait()


if __name__ == "__main__":
    main()
