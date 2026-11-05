"""Two more TinyNotes note designs (credit-free), words appear one by one:

  scrap   - a torn notebook scrap drops onto a wooden desk, then the words appear
  crumple - a crumpled ball of paper unfolds into a creased sheet, then the words appear

python tools/design/handnote2.py out.mp4 scrap|crumple "hey.\\nI love you." [heart|sun|smile] [seed]
"""
import math
import subprocess
import sys
import tempfile
from pathlib import Path

import numpy as np
from PIL import Image, ImageChops, ImageDraw, ImageFilter
from scipy.spatial import cKDTree

sys.path.insert(0, str(Path(__file__).resolve().parent))
import paper as P  # noqa: E402
from handnote import INK, RED, caveat, doodle_points  # noqa: E402
from tinynotes_video import music  # noqa: E402

ROOT = Path(__file__).resolve().parents[2]
W, H, FPS, DUR, SR = 1080, 1920, 30, 8.0, 44100
ease = lambda x: 1 - (1 - min(1, max(0, x))) ** 3  # noqa: E731


# ---------- backgrounds ----------
def wood(seed=3):
    rng = np.random.default_rng(seed)
    yy, xx = np.mgrid[0:H, 0:W].astype(float)
    grain = np.sin(xx / 7 + 6 * P._noise((W, H), 120, seed)) * 0.5 + P._noise((W, H), 30, seed + 1) * 0.8
    plank = (xx // 270) % 2
    base = np.array([140, 96, 64], float) + plank[..., None] * np.array([10, 6, 2])
    arr = base * (1 + 0.10 * grain[..., None]) + rng.normal(0, 3, (H, W, 1))
    for x in range(270, W, 270):
        arr[:, x - 2:x + 2] *= 0.7
    yy2 = (yy - H / 2) / (H / 2)
    xx2 = (xx - W / 2) / (W / 2)
    arr *= (1 - 0.25 * (xx2 ** 2 + yy2 ** 2))[..., None]
    return Image.fromarray(np.clip(arr, 0, 255).astype(np.uint8)).convert("RGBA")


def linen(seed=4):
    g = P.grain((W, H), seed, 16)
    arr = np.array((222, 214, 204), float)[None, None] * g[..., None] / 255
    yy, xx = np.mgrid[0:H, 0:W]
    arr *= (1 - 0.18 * (((xx - W / 2) / (W / 2)) ** 2 + ((yy - H / 2) / (H / 2)) ** 2))[..., None]
    return Image.fromarray(np.clip(arr, 0, 255).astype(np.uint8)).convert("RGBA")


# ---------- paper pieces ----------
def scrap_sheet(w=860, h=760, seed=5):
    """Torn notebook page: ruled lines, red margin, ragged torn top edge."""
    im = Image.new("RGBA", (w + 80, h + 80), (0, 0, 0, 0))
    m = Image.new("L", im.size, 0)
    ImageDraw.Draw(m).rectangle((40, 40, w + 40, h + 40), fill=255)
    P.paper_layer(im, m, (252, 250, 244), seed=seed, jag=7, fringe=0, shadow=0.0)
    d = ImageDraw.Draw(im)
    for y in range(150, h + 20, 88):
        d.line((44, y, w + 36, y), fill=(150, 180, 220, 150), width=3)
    d.line((150, 44, 150, h + 36), fill=(220, 120, 120, 150), width=3)
    for y in (180, 400, 620):  # binder holes
        d.ellipse((70, y, 104, y + 34), fill=(0, 0, 0, 0))
    alpha = im.split()[3]
    hole = Image.new("L", im.size, 255)
    hd = ImageDraw.Draw(hole)
    for y in (180, 400, 620):
        hd.ellipse((70, y, 104, y + 34), fill=0)
    im.putalpha(ImageChops.multiply(alpha, hole))
    return im


def crease_field(w, h, seed=6, n=60):
    """Crumpled-paper look: many short folds. Each fold is a sharp step in brightness
    (one side catches the light, the other is in shadow) that fades out along its length."""
    rng = np.random.default_rng(seed)
    yy, xx = np.mgrid[0:h, 0:w].astype(float)
    shade = P._noise((w, h), 120, seed) * 0.8
    crease = np.zeros((h, w))
    for _ in range(n):
        px, py = rng.uniform(0, w), rng.uniform(0, h)
        ang = rng.uniform(0, math.pi)
        ux, uy = math.cos(ang), math.sin(ang)
        nx, ny = -uy, ux
        along = (xx - px) * ux + (yy - py) * uy
        dd = (xx - px) * nx + (yy - py) * ny + 0.0006 * along ** 2 * rng.uniform(-1, 1)
        L = rng.uniform(180, 520)
        win = np.exp(-(along / L) ** 2)
        shade += rng.uniform(0.25, 0.6) * np.tanh(dd / 5) * win * rng.choice([-1, 1])
        crease += 0.35 * np.exp(-np.abs(dd) / 1.6) * win
    shade = (shade - shade.mean()) / (shade.std() + 1e-9) * 0.4
    return shade, np.clip(crease, 0, 1)


def crumple_frame(base_sheet, shade, crease, k):
    """k=1 fully crumpled look, k=0 flattened (a few creases remain)."""
    s = 0.09 + 0.30 * k
    c = 0.08 + 0.20 * k
    arr = np.asarray(base_sheet.convert("RGB")).astype(float)
    mult = 1 + s * shade - c * crease
    out = np.clip(arr * mult[..., None], 0, 255).astype(np.uint8)
    im = Image.fromarray(out).convert("RGBA")
    im.putalpha(base_sheet.split()[3])
    return im


def blob_to_rect(e, cx, cy, w, h, seed=7, n=96):
    rng = np.random.default_rng(seed)
    rad = 170 * (1 + 0.25 * rng.standard_normal(n).cumsum() / np.sqrt(np.arange(1, n + 1)))
    rad = np.convolve(np.r_[rad[-4:], rad, rad[:4]], np.ones(5) / 5, "same")[4:-4]
    pts = []
    for i in range(n):
        a = 2 * math.pi * i / n - math.pi / 4
        bx, by = cx + rad[i] * math.cos(a), cy + rad[i] * math.sin(a)
        # matching point on the rectangle perimeter
        tx, ty = math.cos(a), math.sin(a)
        sc = min((w / 2) / abs(tx) if tx else 1e9, (h / 2) / abs(ty) if ty else 1e9)
        rx, ry = cx + tx * sc, cy + ty * sc
        pts.append((bx + (rx - bx) * e, by + (ry - by) * e))
    return pts


# ---------- words ----------
def word_layer(text, box, size=None):
    x0, y0, x1, y1 = box
    lines = text.split("\n")
    longest = max(len(ln) for ln in lines)
    size = size or (150 if longest <= 11 else 120 if longest <= 16 else 96)
    f = caveat(size * 2)
    tmp = ImageDraw.Draw(Image.new("L", (10, 10)))
    lh = int(size * 1.2 * 2)
    cy = (y0 + y1) // 2 * 2 - lh * len(lines) // 2 - 40
    masks = []
    space = tmp.textlength(" ", font=f)
    for i, ln in enumerate(lines):
        x = ((x0 + x1) * 2 - tmp.textlength(ln, font=f)) / 2
        for wd in ln.split():
            m = Image.new("L", (W * 2, H * 2), 0)
            ImageDraw.Draw(m).text((x, cy + i * lh), wd, font=f, fill=255)
            masks.append(m.resize((W, H), Image.LANCZOS))
            x += tmp.textlength(wd, font=f) + space
    return masks, (cy + lh * len(lines)) / 2


def ink_words(fr, masks, t, t0, per=0.42, fade=0.18):
    layer = Image.new("L", (W, H), 0)
    for j, m in enumerate(masks):
        a = (t - (t0 + j * per)) / fade
        if a <= 0:
            continue
        a = min(1.0, a)
        mm = m.point(lambda v, a=a: int(v * a * 0.92))
        dy = int((1 - a) * 12)
        if dy:
            mm = mm.transform(mm.size, Image.AFFINE, (1, 0, 0, 0, 1, -dy))
        layer = ImageChops.lighter(layer, mm)
    fr.paste(Image.new("RGB", (W, H), INK), (0, 0), layer)
    return t0 + per * len(masks)


def draw_doodle(fr, kind, cx, cy, t, t0):
    strokes = doodle_points(kind, cx, cy, 6.5)
    total = sum(len(s) for s in strokes)
    if t <= t0:
        return
    m = int(min(1, (t - t0) / 0.9) * total)
    d = ImageDraw.Draw(fr)
    for s in strokes:
        seg = s[:max(0, min(len(s), m))]
        m -= len(s)
        if len(seg) > 1:
            d.line(seg, fill=RED, width=10, joint="curve")


# ---------- sound ----------
def crinkle(seconds, starts, seed=1):
    rng = np.random.default_rng(seed)
    out = np.zeros(int(SR * seconds))
    for st, dur in starts:
        n = int(SR * dur)
        sig = rng.standard_normal(n) * (rng.random(n) < 0.08)  # sparse clicks = paper crackle
        sig = np.convolve(sig, np.ones(6) / 6, "same") * np.sin(np.linspace(0, np.pi, n))
        i = int(SR * st)
        out[i:i + n] += sig[: len(out) - i]
    return out


def mix_audio(path, extra):
    import wave
    music(path, DUR, "hn2")
    with wave.open(str(path)) as w:
        sr, ch = w.getframerate(), w.getnchannels()
        a = np.frombuffer(w.readframes(w.getnframes()), np.int16).reshape(-1, ch).astype(float)
    n = min(len(a), len(extra))
    a[:n] += (extra[:n] * 9000)[:, None]
    a = np.clip(a, -32767, 32767).astype(np.int16)
    with wave.open(str(path), "wb") as w:
        w.setnchannels(ch)
        w.setsampwidth(2)
        w.setframerate(sr)
        w.writeframes(a.tobytes())


# ---------- render ----------
def frame_scrap(t, A):
    fr = A["bg"].copy()
    k = ease(t / 0.55)
    sheet = A["sheet"]
    rot = -3 + (1 - k) * 14
    sc = 1 + (1 - k) * 0.25
    im = sheet.resize((int(sheet.width * sc), int(sheet.height * sc)), Image.BILINEAR).rotate(rot, resample=Image.BICUBIC, expand=True)
    cx, cy = W // 2, int(H * 0.47 - (1 - k) * 420)
    sh = Image.new("RGBA", im.size, (20, 10, 0, 0))
    sh.putalpha(im.split()[3].point(lambda v: int(v * 0.45)).filter(ImageFilter.GaussianBlur(14 + 30 * (1 - k))))
    fr.alpha_composite(sh, (cx - im.width // 2 + int(10 + 40 * (1 - k)), cy - im.height // 2 + int(18 + 60 * (1 - k))))
    fr.alpha_composite(im, (cx - im.width // 2, cy - im.height // 2))
    fr = fr.convert("RGB")
    if k >= 1:
        txt = Image.new("RGB", (W, H))
        txt.paste(fr)
        layer = fr.copy()
        t_end = ink_words(layer, A["masks"], t, 0.75)
        # words follow the sheet's slight tilt
        fr = layer
        draw_doodle(fr, A["doodle"], W / 2 + 60, A["text_bottom"] + (165 if A["doodle"] == "sun" else 105), t, t_end + 0.15)
    return fr


def frame_crumple(t, A):
    fr = A["bg"].copy()
    e = ease((t - 0.25) / 1.1)
    k = 1 - ease((t - 0.25) / 1.4)
    cx, cy = W // 2, int(H * 0.47)
    sw, sh_ = A["sheet_size"]
    pts = blob_to_rect(e, cx, cy, sw * (0.35 + 0.65 * e), sh_ * (0.35 + 0.65 * e))
    mask = Image.new("L", (W, H), 0)
    if e > 0.995:
        pts = [(cx - sw / 2, cy - sh_ / 2), (cx + sw / 2, cy - sh_ / 2), (cx + sw / 2, cy + sh_ / 2), (cx - sw / 2, cy + sh_ / 2)]
    ImageDraw.Draw(mask).polygon(pts, fill=255)
    mask = mask.filter(ImageFilter.GaussianBlur(1.2))
    tex = crumple_frame(A["sheet_full"], A["shade"], A["crease"], k)
    rot = (1 - e) * 40 - 2
    tex = tex.rotate(rot, resample=Image.BILINEAR, center=(cx, cy))
    mask = mask.rotate(rot, resample=Image.BILINEAR, center=(cx, cy))
    shadow = Image.new("RGBA", (W, H), (30, 20, 10, 0))
    shadow.putalpha(ImageChops.offset(mask, 12, 22).filter(ImageFilter.GaussianBlur(18)).point(lambda v: int(v * 0.45)))
    fr.alpha_composite(shadow)
    piece = tex.copy()
    piece.putalpha(mask)
    fr.alpha_composite(piece)
    fr = fr.convert("RGB")
    if t > 1.6:
        layer = fr.copy()
        t_end = ink_words(layer, A["masks"], t, 1.7)
        # creases show through the ink a little
        fr = layer
        draw_doodle(fr, A["doodle"], W / 2 + 60, A["text_bottom"] + (165 if A["doodle"] == "sun" else 105), t, t_end + 0.15)
    return fr


def render(out, style, text, doodle="heart", seed=1):
    A = {"doodle": doodle}
    if style == "scrap":
        A["bg"] = wood(seed)
        A["sheet"] = scrap_sheet(seed=seed + 4)
        A["masks"], A["text_bottom"] = word_layer(text, (170, 520, 960, 1220))
        fn = frame_scrap
        sfx = crinkle(DUR, [(0.35, 0.3)], seed)
    else:
        A["bg"] = linen(seed)
        sw, sh_ = 860, 1160
        A["sheet_size"] = (sw, sh_)
        sheet = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        x0, y0 = (W - sw) // 2, int(H * 0.47) - sh_ // 2
        sheet.paste(P.textured((252, 249, 240), (sw, sh_), seed).convert("RGBA"), (x0, y0))
        A["sheet_full"] = sheet
        shade = np.zeros((H, W))
        crease = np.zeros((H, W))
        s_, c_ = crease_field(sw, sh_, seed + 9)
        shade[y0:y0 + sh_, x0:x0 + sw] = s_
        crease[y0:y0 + sh_, x0:x0 + sw] = c_
        A["shade"], A["crease"] = shade, crease
        A["masks"], A["text_bottom"] = word_layer(text, (x0, y0, x0 + sw, y0 + sh_))
        fn = frame_crumple
        sfx = crinkle(DUR, [(0.2, 1.3)], seed)
    wm = Image.open(ROOT / "brand/tinynotes_wm_white.png").convert("RGBA")
    wm = wm.resize((150, int(wm.height * 150 / wm.width)), Image.LANCZOS)
    wm.putalpha(wm.split()[3].point(lambda v: int(v * 0.7)))
    tmp = Path(tempfile.mkdtemp())
    proc = subprocess.Popen(["ffmpeg", "-nostdin", "-loglevel", "error", "-y", "-f", "rawvideo", "-pix_fmt", "rgb24",
                             "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-", "-c:v", "libx264", "-preset", "veryfast",
                             "-crf", "18", "-pix_fmt", "yuv420p", str(tmp / "v.mp4")], stdin=subprocess.PIPE)
    for i in range(int(DUR * FPS)):
        t = i / FPS
        fr = fn(t, A).convert("RGBA")
        fr.alpha_composite(wm, ((W - wm.width) // 2, H - wm.height - 260))
        z = 1.0 + 0.03 * (t / DUR)
        cw_, ch_ = W / z, H / z
        fr = fr.crop((W / 2 - cw_ / 2, H / 2 - ch_ / 2, W / 2 + cw_ / 2, H / 2 + ch_ / 2)).resize((W, H), Image.BICUBIC)
        proc.stdin.write(fr.convert("RGB").tobytes())
    proc.stdin.close()
    proc.wait()
    mix_audio(tmp / "m.wav", sfx)
    subprocess.run(["ffmpeg", "-nostdin", "-loglevel", "error", "-y", "-i", str(tmp / "v.mp4"), "-i", str(tmp / "m.wav"),
                    "-map", "0:v", "-map", "1:a", "-c:v", "copy", "-c:a", "aac", "-ac", "2", "-ar", "48000", "-shortest",
                    "-movflags", "+faststart", str(out)], check=True)


if __name__ == "__main__":
    render(sys.argv[1], sys.argv[2], sys.argv[3].replace("\\n", "\n"), *(sys.argv[4:5] or ["heart"]),
           *(int(x) for x in sys.argv[5:6]))
