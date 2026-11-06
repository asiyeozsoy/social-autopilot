"""Write text onto a blank sign a character holds in an AI clip (one clip -> many videos).

The white card is found in every frame, its corners are smoothed over time, and handwritten
marker text is warped onto it so it moves with the card and picks up the card's lighting.
Each slide is (start, end, text); the first slide is visible from frame 0 (it is the hook),
later slides replace the previous one with a quick fade and a word-by-word reveal.

python tools/design/card_text.py raw.mp4 out.mp4 "0-4:this is your sign" "4-10:to rest today." [--flip] [--zoom 1.06]
"""
import argparse
import math
import subprocess
import sys
from pathlib import Path

import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[2]
W, H = 1080, 1920
INK = np.array([34, 34, 48], float)
RED = (190, 46, 54)


def marker(size):
    f = ImageFont.truetype(str(ROOT / "brand/fonts/Caveat[wght].ttf"), size)
    try:
        f.set_variation_by_axes([700])
    except Exception:
        pass
    return f


def probe(src):
    out = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries", "stream=r_frame_rate",
                          "-of", "csv=p=0", src], capture_output=True, text=True).stdout.strip()
    a, b = out.split("/")
    return float(a) / float(b)


def frames(src, flip, zoom):
    vf = f"scale={int(W * zoom)}:{int(H * zoom)}:flags=lanczos,crop={W}:{H}" + (",hflip" if flip else "")
    p = subprocess.Popen(["ffmpeg", "-nostdin", "-loglevel", "error", "-i", src, "-vf", vf, "-f", "rawvideo",
                          "-pix_fmt", "rgb24", "-"], stdout=subprocess.PIPE)
    while True:
        buf = p.stdout.read(W * H * 3)
        if len(buf) < W * H * 3:
            break
        yield np.frombuffer(buf, np.uint8).reshape(H, W, 3)


def _ransac_line(pts, tol=1.5, iters=300, seed=0):
    """Fit a line a*x + b*y = c to pts robustly; returns (point, direction)."""
    rng = np.random.default_rng(seed)
    pts = np.asarray(pts, float)
    best = None
    for _ in range(iters):
        i, j = rng.choice(len(pts), 2, replace=False)
        d = pts[j] - pts[i]
        n = np.linalg.norm(d)
        if n < 1e-6:
            continue
        nrm = np.array([-d[1], d[0]]) / n
        inl = np.abs((pts - pts[i]) @ nrm) < tol
        if best is None or inl.sum() > best.sum():
            best = inl
    q = pts[best]
    c = q.mean(0)
    _, _, vt = np.linalg.svd(q - c)
    return c, vt[0]


def _intersect(l1, l2):
    (p1, d1), (p2, d2) = l1, l2
    A = np.array([d1, -d2]).T
    t = np.linalg.solve(A, p2 - p1)
    return p1 + t[0] * d1


def find_card(fr):
    """Corners (tl, tr, br, bl) of the white card. Each side is fitted as a straight line with
    RANSAC, so paws, body and floor touching the card cannot pull the corners around."""
    s = 2
    small = cv2.resize(fr, (W // s, H // s), interpolation=cv2.INTER_AREA)
    hsv = cv2.cvtColor(small, cv2.COLOR_RGB2HSV)
    m = ((hsv[..., 2] > 175) & (hsv[..., 1] < 40)).astype(np.uint8)
    m = cv2.morphologyEx(m, cv2.MORPH_OPEN, np.ones((5, 5), np.uint8))
    n, lab, stats, cent = cv2.connectedComponentsWithStats(m)
    best, score = None, 0
    for i in range(1, n):
        area = stats[i, cv2.CC_STAT_AREA]
        cx = cent[i][0]
        if area < 0.04 * m.size:
            continue
        sc = area / (1 + abs(cx - m.shape[1] / 2) / m.shape[1] * 4)
        if sc > score:
            best, score = i, sc
    if best is None:
        return None
    comp = lab == best
    x0, y0, bw, bh = stats[best, :4]
    cols = np.arange(x0 + int(bw * 0.12), x0 + int(bw * 0.88))
    rows = np.arange(y0 + int(bh * 0.08), y0 + int(bh * 0.92))
    colany = comp[:, cols].any(0)
    top = [(c, np.argmax(comp[:, c])) for c, ok in zip(cols, colany) if ok]
    bot = [(c, comp.shape[0] - 1 - np.argmax(comp[::-1, c])) for c, ok in zip(cols, colany) if ok]
    rowany = comp[rows].any(1)
    left = [(np.argmax(comp[r]), r) for r, ok in zip(rows, rowany) if ok]
    right = [(comp.shape[1] - 1 - np.argmax(comp[r, ::-1]), r) for r, ok in zip(rows, rowany) if ok]
    if min(len(top), len(bot), len(left), len(right)) < 20:
        return None
    L = [_ransac_line(v) for v in (top, right, bot, left)]
    q = np.array([_intersect(L[3], L[0]), _intersect(L[0], L[1]), _intersect(L[1], L[2]), _intersect(L[2], L[3])])
    return (q + 0.5) * s


def smooth(quads, sigma=2.0, jump=10.0):
    q = np.array(quads, float)
    n = len(q)
    # replace single-frame outliers by the local median
    for i in range(n):
        a, b = max(0, i - 3), min(n, i + 4)
        med = np.median(q[a:b], axis=0)
        bad = np.linalg.norm(q[i] - med, axis=1) > jump
        q[i][bad] = med[bad]
    k = np.arange(-int(3 * sigma), int(3 * sigma) + 1)
    g = np.exp(-k ** 2 / (2 * sigma ** 2))
    out = np.empty_like(q)
    for i in range(n):
        idx = np.clip(i + k, 0, n - 1)
        out[i] = (q[idx] * g[:, None, None]).sum(0) / g.sum()
    return out


def text_canvas(text, cw, ch):
    """RGBA canvas with the handwritten text; returns canvas and per-word alpha masks."""
    heart = text.rstrip().endswith("<3")
    text = text.rstrip()[:-2].rstrip() if heart else text
    lines = text.split("\n")
    tmp = ImageDraw.Draw(Image.new("L", (8, 8)))
    size = int(ch * 0.74 / max(1, len(lines)) / 1.12)
    while size > 20:
        f = marker(size)
        if max(tmp.textlength(ln, font=f) for ln in lines) <= cw * (0.72 if heart else 0.84):
            break
        size -= 4
    f = marker(size)
    lh = size * 1.12
    y = (ch - lh * len(lines)) / 2 - size * 0.08
    words = []
    for i, ln in enumerate(lines):
        x = (cw - tmp.textlength(ln, font=f)) / 2 - (size * 0.3 if heart and i == len(lines) - 1 else 0)
        for wd in ln.split():
            m = Image.new("L", (cw, ch), 0)
            ImageDraw.Draw(m).text((x, y + i * lh), wd, font=f, fill=255)
            words.append((np.asarray(m).astype(float) / 255, INK))
            x += tmp.textlength(wd + " ", font=f)
    if heart:  # small red marker heart after the last word
        m = Image.new("L", (cw, ch), 0)
        hs = size * 0.022
        cx, cy = x + size * 0.3, y + (len(lines) - 1) * lh + size * 0.56
        pts = []
        for i in range(101):
            a = math.pi * 2 * i / 100
            pts.append((cx + 16 * math.sin(a) ** 3 * hs,
                        cy - (13 * math.cos(a) - 5 * math.cos(2 * a) - 2 * math.cos(3 * a) - math.cos(4 * a)) * hs))
        ImageDraw.Draw(m).polygon(pts, fill=255)
        words.append((np.asarray(m).astype(float) / 255, np.array(RED, float)))
    return words


def main():
    p = argparse.ArgumentParser()
    p.add_argument("src")
    p.add_argument("out")
    p.add_argument("slides", nargs="+")
    p.add_argument("--flip", action="store_true")
    p.add_argument("--zoom", type=float, default=1.0)
    p.add_argument("--fps", type=float)
    a = p.parse_args()
    fps = a.fps or probe(a.src)
    slides = []
    for s in a.slides:
        rng, txt = s.split(":", 1)
        t0, t1 = map(float, rng.split("-"))
        slides.append((t0, t1, txt.replace("\\n", "\n")))

    fr_list = list(frames(a.src, a.flip, a.zoom))
    quads, last = [], None
    for fr in fr_list:
        q = find_card(fr)
        if q is None:
            q = last
        quads.append(q)
        last = q
    first = next(q for q in quads if q is not None)
    quads = [q if q is not None else first for q in quads]
    quads = smooth(quads)
    med = np.median(quads, axis=0)
    cw = int(np.linalg.norm(med[1] - med[0]) * 1.5)
    ch = int(np.linalg.norm(med[3] - med[0]) * 1.5)
    inset = 0.09
    src_rect = np.float32([[0, 0], [cw, 0], [cw, ch], [0, ch]])
    word_sets = [text_canvas(t, cw, ch) for _, _, t in slides]

    enc = subprocess.Popen(["ffmpeg", "-nostdin", "-loglevel", "error", "-y", "-f", "rawvideo", "-pix_fmt", "rgb24",
                            "-s", f"{W}x{H}", "-r", f"{fps}", "-i", "-", "-c:v", "libx264", "-preset", "veryfast",
                            "-crf", "17", "-pix_fmt", "yuv420p", a.out], stdin=subprocess.PIPE)
    per, fade_in, fade_out = 0.16, 0.14, 0.22
    for i, fr in enumerate(fr_list):
        t = i / fps
        alpha = np.zeros((ch, cw))
        red = np.zeros((ch, cw))
        for k, ((t0, t1, _), words) in enumerate(zip(slides, word_sets)):
            if not (t0 - 0.01 <= t < t1 + fade_out):
                continue
            out_f = 1.0 if t < t1 else max(0.0, 1 - (t - t1) / fade_out)
            for j, (wm, col) in enumerate(words):
                if k == 0:
                    w_a = 1.0
                else:
                    w_a = min(1.0, max(0.0, (t - (t0 + fade_out + j * per)) / fade_in))
                if w_a > 0:
                    if col is INK:
                        alpha = np.maximum(alpha, wm * w_a * out_f)
                    else:
                        red = np.maximum(red, wm * w_a * out_f)
        frame = fr.astype(float)
        if alpha.max() > 0 or red.max() > 0:
            q = quads[i]
            c = q.mean(0)
            qi = (c + (q - c) * (1 - inset)).astype(np.float32)
            Hm = cv2.getPerspectiveTransform(src_rect, qi)
            shade = np.clip(cv2.GaussianBlur(frame.mean(2), (0, 0), 6) / 240.0, 0.55, 1.05)[..., None]
            for amap, col in ((alpha, INK), (red, np.array(RED, float))):
                if amap.max() <= 0:
                    continue
                al = cv2.warpPerspective(amap.astype(np.float32), Hm, (W, H), flags=cv2.INTER_LINEAR)
                al = cv2.GaussianBlur(al, (0, 0), 0.7)[..., None] * 0.93
                frame = frame * (1 - al) + col[None, None, :] * shade * al
        enc.stdin.write(np.clip(frame, 0, 255).astype(np.uint8).tobytes())
    enc.stdin.close()
    enc.wait()


if __name__ == "__main__":
    main()
