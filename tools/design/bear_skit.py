"""Credit-free Bear Family skit, made entirely in code (no Higgsfield).

The bears are cut out of our own character sheet (brand/characters/ayilar_referans.jpg)
and animated as puppets (breathing, shivering, dashing, squash and stretch) over
rooms drawn here, with an original synthesised tune and sound effects.

Episode: "The Thermostat" (Mom & kid turn the heat up, Dad senses it from 3 rooms away).

python tools/design/bear_skit.py raw.mp4
then: finish_video.py raw.mp4 final.mp4 --brand factyeap --hook x --beat ...
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
from scipy import ndimage

ROOT = Path(__file__).resolve().parents[2]
G = "/usr/share/fonts/truetype/google-fonts/"
W, H, FPS, DUR = 1080, 1920, 30, 13.0
SR = 44100


# ---------- characters ----------
def cutouts():
    im = Image.open(ROOT / "brand/characters/ayilar_referans.jpg").convert("RGB")
    a = np.asarray(im).astype(float)
    bg = np.median(a[:, :30, :], axis=1)[:, None, :]
    d = np.sqrt(((a - bg) ** 2).sum(-1))
    fg = ndimage.binary_fill_holes(ndimage.binary_closing(d > 22, iterations=3))
    lab, n = ndimage.label(fg)
    sizes = ndimage.sum(fg, lab, range(1, n + 1))
    objs = ndimage.find_objects(lab)
    keep = sorted([(i + 1, objs[i]) for i in range(n) if sizes[i] > 20000], key=lambda t: (t[1][0].start // 400, t[1][1].start))
    alpha = np.clip((d - 14) / 16, 0, 1)
    out = []
    for lid, (ys, xs) in keep:
        m = ndimage.binary_dilation(lab[ys, xs] == lid, iterations=2)
        al = np.maximum(alpha[ys, xs] * m, ndimage.binary_erosion(m, iterations=4))
        # drop the soft floor shadow under the feet (low-contrast pixels in the bottom rows)
        rows = al.shape[0]
        cut = int(rows * 0.88)
        al[cut:] *= np.clip((d[ys, xs][cut:] - 46) / 14, 0, 1)
        out.append(Image.fromarray(np.dstack([a[ys, xs], al * 255]).astype(np.uint8), "RGBA"))
    return out


def scaled(img, h):
    return img.resize((int(img.width * h / img.height), int(h)), Image.LANCZOS)


# ---------- rooms ----------
def vgrad(w, h, c0, c1):
    t = np.linspace(0, 1, h)[:, None, None]
    arr = (np.array(c0) * (1 - t) + np.array(c1) * t).repeat(w, axis=1)
    return Image.fromarray(arr.astype(np.uint8), "RGB")


def living_room():
    im = vgrad(W, H, (236, 224, 204), (214, 197, 172)).convert("RGBA")
    d = ImageDraw.Draw(im)
    d.rectangle((0, 1120, W, 1390), fill=(203, 184, 158))
    d.rectangle((0, 1112, W, 1124), fill=(240, 230, 214))
    for x in range(40, W, 210):
        d.rounded_rectangle((x, 1160, x + 170, 1350), 10, outline=(190, 170, 144), width=4)
    # window with a snowy night
    d.rounded_rectangle((110, 330, 540, 900), 16, fill=(126, 92, 66))
    glass = vgrad(390, 530, (34, 52, 92), (92, 112, 160))
    im.paste(glass, (130, 350))
    d.ellipse((90, 800, 620, 960), fill=(232, 238, 248))
    d.rectangle((110, 880, 540, 900), fill=(126, 92, 66))
    d.rectangle((318, 350, 332, 880), fill=(126, 92, 66))
    d.rectangle((130, 600, 520, 612), fill=(126, 92, 66))
    d.rectangle((90, 896, 560, 920), fill=(150, 112, 82))
    # framed picture and floor lamp
    d.rectangle((650, 420, 900, 640), fill=(150, 112, 82))
    d.rectangle((666, 436, 884, 624), fill=(222, 196, 150))
    d.polygon([(680, 610), (750, 500), (800, 560), (840, 520), (874, 610)], fill=(140, 160, 130))
    d.ellipse((800, 455, 840, 495), fill=(250, 220, 140))
    d.rectangle((995, 600, 1007, 1420), fill=(90, 74, 60))
    d.polygon([(930, 600), (1072, 600), (1040, 470), (962, 470)], fill=(246, 222, 170))
    # sofa
    d.rounded_rectangle((40, 1060, 760, 1300), 60, fill=(92, 126, 124))
    d.rounded_rectangle((70, 1150, 730, 1420), 40, fill=(104, 140, 138))
    d.rounded_rectangle((20, 1120, 140, 1430), 40, fill=(86, 118, 116))
    d.rounded_rectangle((660, 1120, 780, 1430), 40, fill=(86, 118, 116))
    # floor
    floor = vgrad(W, H - 1400, (176, 128, 92), (140, 98, 68))
    im.paste(floor, (0, 1400))
    for y in range(1440, H, 90):
        d.line((0, y, W, y), fill=(150, 106, 74), width=3)
    d.ellipse((60, 1530, 1020, 1840), fill=(176, 86, 72))
    d.ellipse((110, 1560, 970, 1810), outline=(206, 150, 110), width=8)
    return im.filter(ImageFilter.GaussianBlur(3))


def kitchen():
    im = vgrad(W, H, (214, 222, 204), (190, 200, 180)).convert("RGBA")
    d = ImageDraw.Draw(im)
    for x in range(30, W, 260):
        d.rounded_rectangle((x, 220, x + 230, 620), 14, fill=(236, 232, 220))
        d.rectangle((x + 100, 560, x + 130, 572), fill=(150, 140, 120))
    d.rectangle((0, 1160, W, 1240), fill=(230, 226, 214))
    d.rectangle((0, 1240, W, 1500), fill=(120, 140, 124))
    d.rounded_rectangle((760, 420, 1060, 1500), 24, fill=(232, 236, 238))
    d.rectangle((790, 760, 1030, 770), fill=(200, 206, 210))
    d.rounded_rectangle((150, 1050, 290, 1162), 18, fill=(226, 120, 70))  # flower pot
    for dx in (-40, 0, 40):
        d.ellipse((205 + dx, 930, 245 + dx, 1050), fill=(110, 150, 100))
    d.rectangle((0, 1500, W, H), fill=(196, 176, 150))
    for x in range(0, W, 135):
        d.line((x, 1500, x, H), fill=(180, 160, 134), width=3)
    return im.filter(ImageFilter.GaussianBlur(4))


def thermostat(temp):
    s = Image.new("RGBA", (190, 190), (0, 0, 0, 0))
    d = ImageDraw.Draw(s)
    d.rounded_rectangle((10, 14, 184, 188), 34, fill=(0, 0, 0, 60))
    d.rounded_rectangle((4, 4, 178, 178), 34, fill=(248, 247, 242), outline=(200, 196, 188), width=3)
    hot = temp > 21
    col = (232, 104, 44) if hot else (60, 126, 220)
    d.ellipse((24, 24, 158, 158), outline=col, width=10)
    f = ImageFont.truetype(G + "Poppins-Bold.ttf", 54)
    txt = f"{int(round(temp))}°"
    d.text((91 - d.textlength(txt, font=f) / 2, 52), txt, font=f, fill=(40, 40, 46))
    return s


# ---------- sound ----------
def synth(path):
    n = int(SR * DUR)
    out = np.zeros(n)

    def add(start, sig, gain=1.0):
        i = int(start * SR)
        sig = sig[: max(0, n - i)]
        out[i:i + len(sig)] += sig * gain

    def pluck(freq, dur=0.32):
        t = np.arange(int(SR * dur)) / SR
        env = np.exp(-t * 11) * np.minimum(1, t * 400)
        return env * (np.sin(2 * np.pi * freq * t) + 0.35 * np.sin(4 * np.pi * freq * t) + 0.12 * np.sin(6 * np.pi * freq * t))

    notes = {"C4": 261.6, "D4": 293.7, "E4": 329.6, "F4": 349.2, "G4": 392.0, "A4": 440.0, "B4": 493.9,
             "C5": 523.3, "D5": 587.3, "E5": 659.3, "G3": 196.0, "C3": 130.8, "F3": 174.6, "A3": 220.0}
    melody = "E4 G4 C5 G4 A4 G4 E4 - D4 F4 A4 F4 G4 F4 D4 - E4 G4 C5 E5 D5 C5 A4 - G4 E4 D4 E4 C4 - - -".split()
    bass = ["C3", "G3", "F3", "G3"]
    beat = 0.25
    t = 0.0
    k = 0
    while t < DUR - 0.4:
        if 4.3 < t < 6.3:  # the music holds its breath while Dad senses it
            t += beat
            k += 1
            continue
        nm = melody[k % len(melody)]
        if nm != "-":
            add(t, pluck(notes[nm]), 0.22)
        if k % 4 == 0:
            add(t, pluck(notes[bass[(k // 4) % 4]], 0.5), 0.3)
        t += beat
        k += 1
    rng = np.random.default_rng(3)
    # ding when Dad senses it
    tt = np.arange(int(SR * 1.2)) / SR
    add(4.85, np.exp(-tt * 4) * (np.sin(2 * np.pi * 1568 * tt) + 0.5 * np.sin(2 * np.pi * 2349 * tt)), 0.35)
    # whoosh for the dash
    wl = int(SR * 0.6)
    noise = rng.standard_normal(wl)
    env = np.sin(np.linspace(0, np.pi, wl)) ** 2
    sm = np.convolve(noise, np.ones(30) / 30, mode="same")
    add(6.35, sm * env, 0.9)
    # dial clicks
    for c in list(np.arange(2.4, 3.6, 0.17)) + list(np.arange(7.35, 8.4, 0.15)):
        cl = rng.standard_normal(int(SR * 0.02)) * np.exp(-np.arange(int(SR * 0.02)) / 80)
        add(c, cl, 0.25)
    # fade in/out
    out[: int(SR * 0.05)] *= np.linspace(0, 1, int(SR * 0.05))
    out[-int(SR * 0.6):] *= np.linspace(1, 0, int(SR * 0.6))
    out = out / (np.abs(out).max() + 1e-9) * 0.8
    pcm = (out * 32767).astype(np.int16)
    st = np.stack([pcm, pcm], axis=1)
    with wave.open(str(path), "wb") as w:
        w.setnchannels(2)
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes(st.tobytes())


# ---------- animation helpers ----------
def ease(x):
    x = min(1, max(0, x))
    return 1 - (1 - x) ** 3


def clamp01(x):
    return min(1, max(0, x))


def place(frame, img, cx, feet, sx=1.0, sy=1.0):
    w, h = int(img.width * sx), int(img.height * sy)
    im = img.resize((w, h), Image.BILINEAR) if (sx, sy) != (1.0, 1.0) else img
    frame.alpha_composite(im, (int(cx - w / 2), int(feet - h)))


def shadow(frame, cx, feet, w):
    sh = Image.new("RGBA", (int(w), 60), (0, 0, 0, 0))
    ImageDraw.Draw(sh).ellipse((0, 0, int(w), 60), fill=(40, 20, 10, 90))
    frame.alpha_composite(sh.filter(ImageFilter.GaussianBlur(10)), (int(cx - w / 2), int(feet - 34)))


def tint(frame, col, a):
    if a <= 0:
        return frame
    ov = Image.new("RGBA", frame.size, col + (int(255 * a),))
    frame.alpha_composite(ov)
    return frame


def blanket(frame, cx, top, w, h, col):
    """A plaid blanket wrapped round a bear: rounded drape, fold shading, soft shadow."""
    b = Image.new("RGBA", (w + 40, h + 40), (0, 0, 0, 0))
    d = ImageDraw.Draw(b)
    d.rounded_rectangle((20, 20, w + 20, h + 20), 110, fill=col + (255,))
    light = tuple(min(255, c + 40) for c in col)
    dark = tuple(max(0, c - 45) for c in col)
    for x in range(50, w + 20, 120):
        d.rectangle((x, 20, x + 34, h + 20), fill=light + (55,))
        d.rectangle((x + 46, 20, x + 52, h + 20), fill=dark + (70,))
    for y in range(80, h + 20, 120):
        d.rectangle((20, y, w + 20, y + 34), fill=light + (55,))
        d.rectangle((20, y + 46, w + 20, y + 52), fill=dark + (70,))
    d.line((20 + w * 0.55, 60, 20 + w * 0.45, h + 10), fill=dark + (200,), width=10)
    mask = Image.new("L", b.size, 0)
    ImageDraw.Draw(mask).rounded_rectangle((20, 20, w + 20, h + 20), 110, fill=255)
    b.putalpha(mask)
    sh = Image.new("RGBA", b.size, (0, 0, 0, 0))
    sh.putalpha(mask.point(lambda v: v // 3))
    frame.alpha_composite(sh.filter(ImageFilter.GaussianBlur(12)), (int(cx - w / 2 - 20 + 8), int(top - 20 + 14)))
    frame.alpha_composite(b, (int(cx - w / 2 - 20), int(top - 20)))


def snow(frame, t, region, seed=1):
    x0, y0, x1, y1 = region
    d = ImageDraw.Draw(frame)
    rng = random.Random(seed)
    for _ in range(40):
        bx, by, sp, r = rng.uniform(x0, x1), rng.uniform(0, 1), rng.uniform(60, 140), rng.uniform(3, 7)
        y = y0 + ((by * (y1 - y0) + t * sp) % (y1 - y0))
        x = bx + 10 * math.sin(t * 2 + by * 9)
        d.ellipse((x - r, y - r, x + r, y + r), fill=(255, 255, 255, 220))


def puffs(frame, t, x, y, phase):
    d = ImageDraw.Draw(frame)
    k = (t + phase) % 1.4
    if k < 0.9:
        r = 14 + 40 * k
        a = int(150 * (1 - k / 0.9))
        d.ellipse((x - r + 30 * k, y - r - 60 * k, x + r + 30 * k, y + r - 60 * k), fill=(255, 255, 255, a))


def speed_lines(frame, x0, x1, y0, y1, a):
    d = ImageDraw.Draw(frame)
    rng = random.Random(7)
    for _ in range(14):
        y = rng.uniform(y0, y1)
        L = rng.uniform(150, 420)
        x = rng.uniform(x0, x1)
        d.line((x - L, y, x, y), fill=(255, 255, 255, int(180 * a)), width=rng.choice([4, 6, 8]))


def bang(frame, cx, cy, s):
    if s <= 0:
        return
    f = ImageFont.truetype(G + "Poppins-Bold.ttf", int(220 * s))
    d = ImageDraw.Draw(frame)
    d.text((cx - d.textlength("!", font=f) / 2 + 6, cy + 6), "!", font=f, fill=(60, 20, 20, 160))
    d.text((cx - d.textlength("!", font=f) / 2, cy), "!", font=f, fill=(228, 54, 44, 255))


# ---------- the episode ----------
def assets():
    cut = cutouts()
    return dict(dad_front=scaled(cut[0], 860), dad_side=scaled(cut[2], 860), mom_front=scaled(cut[5], 700),
                mom_turn=scaled(cut[6], 700), kid_front=scaled(cut[10], 430), room=living_room(), kit=kitchen())


def frame_at(t, A):
    dad_front, dad_side, mom_front, mom_turn, kid_front = A["dad_front"], A["dad_side"], A["mom_front"], A["mom_turn"], A["kid_front"]
    room, kit = A["room"], A["kit"]
    T_X, T_Y = 960, 830
    breathe = 1 + 0.012 * math.sin(t * 3.2)
    if 4.2 <= t < 6.35:  # ---- Dad, three rooms away
        k = (t - 4.2) / 2.15
        fr = kit.copy()
        shadow(fr, 540, 1760, 520)
        sq = 1.0
        if t > 4.85:
            sq = 1 + 0.06 * math.exp(-(t - 4.85) * 8) * math.cos((t - 4.85) * 40)
        place(fr, dad_front, 540, 1770, breathe * 1.05, sq * 1.05)
        bang(fr, 790, 760, ease((t - 4.85) / 0.18) * (1 + 0.15 * math.exp(-(t - 4.85) * 6)) if t > 4.85 else 0)
        zoom = 1 + 0.22 * ease(k)
        cx, cy = 540, 1000
        if 4.85 < t < 5.3:
            cx += 14 * math.sin(t * 90)
        fr = fr.crop((cx - W / 2 / zoom, cy - H / 2 / zoom * 1.0, cx + W / 2 / zoom, cy + H / 2 / zoom)).resize((W, H), Image.BILINEAR)
        fr = fr.convert("RGBA")
    else:  # ---- living room
        fr = room.copy()
        snow(fr, t, (130, 350, 520, 830))
        if t < 2.4:
            temp = 18
        elif t < 3.6:
            temp = 18 + 7 * ease((t - 2.4) / 1.2)
        elif t < 7.3:
            temp = 25
        elif t < 8.4:
            temp = 25 - 7 * ease((t - 7.3) / 1.1)
        else:
            temp = 18
        cold = 1.0 if t < 2.6 else (1 - ease((t - 2.6) / 1.0) if t < 7.6 else ease((t - 7.6) / 1.0))
        fr.alpha_composite(thermostat(temp), (T_X - 95, T_Y - 95))
        shiver = 5 * cold * math.sin(t * 55)
        # Mom walks to the thermostat and back (scene 1)
        if t < 4.2:
            go = ease((t - 1.0) / 0.9) - ease((t - 3.4) / 0.7)
            mom_x = 300 + 400 * go
            mom_img = mom_turn if 0.9 < t < 4.0 else mom_front
        else:
            mom_x, mom_img = 300, mom_front
        wrapped = t >= 9.2
        kid_x = 560 if t < 6.35 else 470
        if wrapped:
            mom_x = 200
            kid_x = 430
        shadow(fr, mom_x, 1650, 300)
        shadow(fr, kid_x, 1690, 200)
        hop = abs(math.sin(t * 9)) * 10 if (1.0 < t < 1.9 or 3.4 < t < 4.1) else 0
        place(fr, mom_img, mom_x + (shiver if not (1.0 < t < 4.1) else 0), 1660 - hop, breathe, breathe)
        if wrapped:
            blanket(fr, mom_x + shiver, 1200, 400, 470, (176, 62, 58))
        place(fr, kid_front, kid_x - shiver, 1700, breathe, breathe)
        if wrapped:
            blanket(fr, kid_x - shiver, 1440, 270, 270, (226, 170, 64))
        # Dad dashes in (scene 3) and stays for the punchline (scene 4)
        if 6.35 <= t < 9.2:
            k = (t - 6.35) / 0.55
            x = -350 + (700 + 350) * ease(k) + (18 * math.sin((t - 6.9) * 25) * math.exp(-(t - 6.9) * 6) if t > 6.9 else 0)
            sx, sy = (1.12, 0.92) if 6.85 < t < 7.0 else (1.0, 1.0)
            if k < 1:
                speed_lines(fr, 0, x - 150, 900, 1650, 1 - ease(k))
            shadow(fr, x, 1700, 360)
            place(fr, dad_side, x, 1712, sx, sy)
        elif wrapped:
            k = t - 9.2
            pop = 1 + 0.03 * math.sin(k * 6)
            shadow(fr, 840, 1800, 360)
            place(fr, dad_front, 840, 1810, 0.9 * pop, 0.9 * (2 - pop))
        tint(fr, (150, 190, 255), 0.16 * cold)
        tint(fr, (255, 168, 90), 0.10 * (1 - cold))
    return fr.convert("RGB")


def render(out):
    A = assets()
    tmp = Path(tempfile.mkdtemp())
    proc = subprocess.Popen(["ffmpeg", "-nostdin", "-loglevel", "error", "-y", "-f", "rawvideo", "-pix_fmt", "rgb24",
                             "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-", "-c:v", "libx264", "-preset", "veryfast",
                             "-crf", "17", "-pix_fmt", "yuv420p", str(tmp / "v.mp4")], stdin=subprocess.PIPE)
    for i in range(int(DUR * FPS)):
        proc.stdin.write(frame_at(i / FPS, A).tobytes())
    proc.stdin.close()
    proc.wait()
    synth(tmp / "a.wav")
    subprocess.run(["ffmpeg", "-nostdin", "-loglevel", "error", "-y", "-i", str(tmp / "v.mp4"), "-i", str(tmp / "a.wav"),
                    "-map", "0:v", "-map", "1:a", "-c:v", "copy", "-c:a", "aac", "-ac", "2", "-ar", "48000", "-shortest",
                    str(out)], check=True)


if __name__ == "__main__":
    if sys.argv[1] == "--frames":
        A = assets()
        for t in sys.argv[3:]:
            frame_at(float(t), A).save(f"{sys.argv[2]}_{t}.png")
    else:
        render(sys.argv[1])
