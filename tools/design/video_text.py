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
    starts, texts = [], []
    for ln in a.line:
        t, txt = ln.split(":", 1)
        starts.append(float(t))
        texts.append(txt)
    layers = [np.asarray(l).astype(np.float32) / 255 for l in text_layer(texts, a.text_y)]
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
        for s, lay in zip(starts, layers):
            k = min(1.0, (t - s) / 0.8)
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
