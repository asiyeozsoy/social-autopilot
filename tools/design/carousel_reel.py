"""Turn a queued carousel post into a 9:16 reel with chill piano lo-fi, so it carries music
(the Instagram API can't add music to carousels).

python tools/design/carousel_reel.py content/tinynotes/2026-11-19_1930_me-and-my-dad [--first 3.0] [--hold 2.4]

Each slide sits centred on a blurred, dimmed copy of itself, drifts in slightly, and swipes
left into the next one like a carousel. Writes video.mp4 + cover.jpg and switches post.yaml
to a reel (instagram reel, tiktok video, youtube short, facebook keeps whatever it had).
"""
import argparse
import subprocess
import sys
from pathlib import Path

import numpy as np
import yaml
from PIL import Image, ImageFilter

sys.path.insert(0, str(Path(__file__).resolve().parent))
from lofi import lofi  # noqa: E402

W, H, FPS = 1080, 1920, 30
SW = 1000  # slide width inside the frame


def ease(t):
    t = min(1.0, max(0.0, t))
    return t * t * (3 - 2 * t)


def frame_for(slide):
    """Background (blurred, dimmed fill) and the slide itself with rounded corners + shadow."""
    bg = slide.copy()
    s = max(W / bg.width, H / bg.height)
    bg = bg.resize((int(bg.width * s) + 2, int(bg.height * s) + 2), Image.LANCZOS)
    bg = bg.crop(((bg.width - W) // 2, (bg.height - H) // 2, (bg.width - W) // 2 + W, (bg.height - H) // 2 + H))
    bg = bg.filter(ImageFilter.GaussianBlur(38))
    bg = Image.blend(bg, Image.new("RGB", (W, H), (24, 18, 14)), 0.35)
    sh = int(slide.height * SW / slide.width)
    fg = slide.resize((SW, sh), Image.LANCZOS)
    mask = Image.new("L", fg.size, 0)
    from PIL import ImageDraw
    ImageDraw.Draw(mask).rounded_rectangle((0, 0, SW - 1, sh - 1), 28, fill=255)
    fg = fg.convert("RGBA")
    fg.putalpha(mask)
    return bg, fg


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("post")
    ap.add_argument("--first", type=float, default=3.0, help="seconds on the hook slide")
    ap.add_argument("--hold", type=float, default=2.5, help="seconds on every other slide")
    ap.add_argument("--last", type=float, default=3.0)
    ap.add_argument("--swipe", type=float, default=0.45)
    a = ap.parse_args()
    post = Path(a.post)
    meta = yaml.safe_load((post / "post.yaml").read_text())
    ig = meta["platforms"]["instagram"]
    slides = [Image.open(post / m).convert("RGB") for m in ig["media"]]
    n = len(slides)
    holds = [a.first] + [a.hold] * (n - 2) + [a.last] if n > 1 else [a.first + a.last + 1.5]
    starts = np.cumsum([0] + holds[:-1])
    dur = float(sum(holds))
    pre = [frame_for(s) for s in slides]
    shadow_cache = {}

    def compose(idx, local_t, xoff=0.0, base=None):
        bg, fg = pre[idx]
        z = 1.0 + 0.025 * ease(local_t / max(holds[idx], 0.1))
        fw, fh = int(fg.width * z), int(fg.height * z)
        f2 = fg.resize((fw, fh), Image.BILINEAR)
        x, y = int((W - fw) / 2 + xoff), int((H - fh) / 2)
        out = base if base is not None else bg.copy().convert("RGBA")
        key = (fw, fh)
        if key not in shadow_cache:
            s = Image.new("RGBA", (fw + 120, fh + 120), (0, 0, 0, 0))
            s.paste((0, 0, 0, 110), (60, 72, 60 + fw, 72 + fh), f2.split()[3])
            shadow_cache[key] = s.filter(ImageFilter.GaussianBlur(26))
        if -fw - 60 < x < W + 60:
            sh = shadow_cache[key]
            out.paste(sh, (x - 60, y - 60), sh)
            out.paste(f2, (x, y), f2)
        return out

    tmp = str(post / "video.silent.mp4")
    enc = subprocess.Popen(["ffmpeg", "-nostdin", "-loglevel", "error", "-y", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}",
                            "-r", str(FPS), "-i", "-", "-c:v", "libx264", "-preset", "veryfast", "-crf", "19", "-pix_fmt", "yuv420p", tmp],
                           stdin=subprocess.PIPE)
    for i in range(int(dur * FPS)):
        t = i / FPS
        k = int(np.searchsorted(starts, t, side="right") - 1)
        lt = t - starts[k]
        sw_start = holds[k] - a.swipe
        if k < n - 1 and lt > sw_start:
            p = ease((lt - sw_start) / a.swipe)
            bg = Image.blend(pre[k][0], pre[k + 1][0], p).convert("RGBA")
            img = compose(k, lt, -p * W, bg)
            img = compose(k + 1, 0, (1 - p) * W, img)
        else:
            img = compose(k, lt)
        enc.stdin.write(img.convert("RGB").tobytes())
        if i == int(0.9 * FPS):
            img.convert("RGB").save(post / "cover.jpg", quality=92)
    enc.stdin.close()
    enc.wait()
    wav = str(post / "music.wav")
    lofi(wav, dur + 0.1, post.name)
    subprocess.run(["ffmpeg", "-nostdin", "-loglevel", "error", "-y", "-i", tmp, "-i", wav, "-map", "0:v", "-map", "1:a", "-c:v", "copy",
                    "-c:a", "aac", "-b:a", "160k", "-af", f"afade=t=in:d=0.6,afade=t=out:st={dur - 1.5}:d=1.5", "-shortest",
                    "-movflags", "+faststart", str(post / "video.mp4")], check=True)
    Path(tmp).unlink()
    Path(wav).unlink()

    cap = ig.get("caption", "")
    first = cap.split("\n")[0].strip()
    plats = meta["platforms"]
    plats["instagram"] = {"kind": "reel", "media": ["video.mp4"], "caption": cap}
    plats["tiktok"] = {"kind": "video", "media": ["video.mp4"], "caption": cap}
    if "youtube" not in plats:
        title = first[:90] or post.name
        plats["youtube"] = {"kind": "short", "media": ["video.mp4"], "title": title, "description": cap + "\n\n#shorts"}
    if "facebook" in plats:
        plats["facebook"] = {**plats["facebook"], "kind": "reel", "media": ["video.mp4"], "caption": plats["facebook"].get("caption", cap)}
    (post / "post.yaml").write_text(yaml.safe_dump(meta, allow_unicode=True, sort_keys=False))
    print("ok", post, f"{dur:.1f}s")


if __name__ == "__main__":
    main()
