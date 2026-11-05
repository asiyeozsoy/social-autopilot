"""Bear Family paper-cut skits (credit-free): couple and family micro-moments.

Each episode is a function frame(t, A) -> RGB frame plus a list of sound cues.
Assets (sticker cutouts, paper rooms, props) come from bear_skit / paper.

python tools/design/paper_skits.py <episode> out_raw.mp4
python tools/design/paper_skits.py <episode> --frames prefix t1 t2 ...
"""
import math
import random
import subprocess
import sys
import tempfile
import wave
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFilter

sys.path.insert(0, str(Path(__file__).resolve().parent))
import bear_skit as B  # noqa: E402
import paper as P  # noqa: E402

W, H, FPS, DUR, SR = 1080, 1920, 30, 13.0, 44100
ease = B.ease


def L(fn):
    return B.L(fn)


# ---------- assets ----------
def head(img, frac):
    bb = img.getbbox()
    return img.crop((bb[0], bb[1], bb[2], bb[1] + int((bb[3] - bb[1]) * frac)))


def bedroom(single=False):
    im = Image.new("RGBA", (W, H), (0, 0, 0, 255))
    lay = [
        (lambda d: d.rectangle((0, 0, W, 1300)), (62, 72, 108), 0),
        (lambda d: d.rectangle((700, 180, 1000, 560)), (120, 86, 60), 4),
        (lambda d: d.rectangle((720, 200, 980, 540)), (28, 36, 70), 0),
        (lambda d: d.ellipse((830, 250, 920, 340)), (246, 232, 180), 2),
        (lambda d: d.rectangle((60, 300, 300, 520)), (120, 86, 60), 3),
        (lambda d: d.rectangle((78, 318, 282, 502)), (200, 170, 120), 0),
        (lambda d: d.rectangle((-20, 1300, W + 20, H + 20)), (120, 92, 70), 4),
    ]
    if single:
        lay += [
            (lambda d: d.rounded_rectangle((200, 860, 980, 1200), 60), (110, 150, 170), 5),
            (lambda d: d.rounded_rectangle((180, 1150, 1000, 1720), 40), (236, 230, 216), 5),
            (lambda d: d.ellipse((280, 1030, 640, 1240)), (250, 246, 236), 4),
        ]
    else:
        lay += [
            (lambda d: d.rounded_rectangle((70, 820, 1010, 1180), 70), (132, 92, 64), 5),
            (lambda d: d.rounded_rectangle((50, 1150, 1030, 1740), 40), (236, 230, 216), 5),
            (lambda d: d.ellipse((120, 1030, 500, 1240)), (250, 246, 236), 4),
            (lambda d: d.ellipse((580, 1030, 960, 1240)), (250, 246, 236), 4),
        ]
    for i, (fn, col, fr) in enumerate(lay):
        P.paper_layer(im, L(fn), col, seed=300 + i * 17, jag=5, fringe=fr, shadow=0.25 if fr else 0)
    return im


def piece(size, draw_fn, col, seed, jag=4, fringe=4, shadow=0.3):
    im = Image.new("RGBA", size, (0, 0, 0, 0))
    m = Image.new("L", size, 0)
    d = ImageDraw.Draw(m)
    d.fill = True
    d.ink = 255
    draw_fn(d)
    P.paper_layer(im, m, col, seed=seed, jag=jag, fringe=fringe, shadow=shadow)
    return im


def big_blanket(w, h, col, seed):
    return B.paper_blanket(w, h, col, seed)


def honey_jar(level):
    im = piece((240, 300), lambda d: d.rounded_rectangle((40, 70, 200, 270), 40), (238, 226, 196), 1)
    if level > 0:
        top = int(260 - 180 * level)
        im.alpha_composite(piece((240, 300), lambda d: d.rounded_rectangle((52, top, 188, 258), 30), (232, 160, 40), 2, fringe=0, shadow=0))
    im.alpha_composite(piece((240, 300), lambda d: d.rectangle((60, 40, 180, 90)), (170, 100, 50), 3))
    d = ImageDraw.Draw(im)
    f = P.hand_font(48)
    d.text((120 - d.textlength("honey", font=f) / 2, 160), "honey", font=f, fill=(90, 50, 20))
    return im


def tea_cup():
    im = piece((260, 220), lambda d: [d.rounded_rectangle((40, 60, 190, 190), 40), d.ellipse((170, 90, 235, 160))], (240, 238, 230), 4)
    im.alpha_composite(piece((260, 220), lambda d: d.ellipse((190, 108, 220, 142)), (62, 72, 108), 5, fringe=0, shadow=0))
    im.alpha_composite(piece((260, 220), lambda d: d.rectangle((40, 110, 190, 135)), (196, 84, 70), 6, fringe=0, shadow=0))
    return im


def heart(size=110, col=(214, 64, 70), seed=0):
    def fn(d):
        r = size // 4
        d.ellipse((10, 10, 10 + 2 * r, 10 + 2 * r))
        d.ellipse((10 + 2 * r - 6, 10, 10 + 4 * r - 6, 10 + 2 * r))
        d.polygon([(12, 10 + r + 6), (10 + 4 * r - 8, 10 + r + 6), (10 + 2 * r - 3, size - 6)])
    return piece((size + 20, size + 20), fn, col, seed, jag=2, fringe=4)


def cloud(seed=0):
    def fn(d):
        for x, y, r in [(90, 110, 70), (170, 80, 90), (260, 110, 70), (175, 140, 70)]:
            d.ellipse((x - r, y - r, x + r, y + r))
    return piece((360, 230), fn, (110, 116, 128), seed, jag=4, fringe=5)


def zzz(s, seed=0):
    im = Image.new("RGBA", (200, 120), (0, 0, 0, 0))
    f = P.hand_font(int(90 * s) + 1)
    d = ImageDraw.Draw(im)
    d.text((10, 0), "z", font=f, fill=(250, 246, 236), stroke_width=4, stroke_fill=(62, 72, 108))
    return im


def speech(text, seed=0):
    return P.strip(text, width_max=420, size=60, seed=seed, angle=2)


def assets():
    A = B.assets()
    cut = B.cutouts()
    A["mom_back"] = B.to_sticker(B.scaled(cut[8], 700), 11)
    A["kid_turn"] = B.to_sticker(B.scaled(cut[11], 430), 12)
    A["dad_head"] = B.to_sticker(head(B.scaled(cut[0], 980), 0.36), 21)
    A["mom_head"] = B.to_sticker(head(B.scaled(cut[5], 900), 0.38), 22)
    A["kid_head"] = B.to_sticker(head(B.scaled(cut[10], 700), 0.5), 23)
    A["bedroom"] = bedroom()
    A["kidroom"] = bedroom(single=True)
    A["duvet"] = big_blanket(860, 520, (96, 120, 170), 31)
    A["burrito"] = big_blanket(330, 520, (96, 120, 170), 32)
    A["kid_duvet"] = big_blanket(720, 480, (226, 170, 64), 33)
    A["shawl"] = big_blanket(380, 300, (176, 62, 58), 34)
    A["cup"] = tea_cup()
    A["heart"] = heart()
    A["cloud"] = cloud()
    A["jars"] = {k: honey_jar(k / 10) for k in range(11)}
    return A


def put(fr, img, cx, cy, s=1.0, rot=0.0, flip=False):
    """Paste centred at (cx, cy) with stop-motion wobble."""
    im = img
    if flip:
        im = im.transpose(Image.FLIP_LEFT_RIGHT)
    if s != 1.0:
        im = im.resize((max(1, int(im.width * s)), max(1, int(im.height * s))), Image.BILINEAR)
    r = random.Random(B.STEP * 7919 + img.width)
    im = im.rotate(rot + r.uniform(-1.0, 1.0), resample=Image.BICUBIC, expand=True)
    fr.alpha_composite(im, (int(cx - im.width / 2 + r.uniform(-2, 2)), int(cy - im.height / 2 + r.uniform(-2, 2))))


def stand(fr, img, cx, feet, s=1.0, flip=False):
    im = img.transpose(Image.FLIP_LEFT_RIGHT) if flip else img
    B.place(fr, im, cx, feet, s, s)


def glow(fr, cx, cy, r, a):
    if a <= 0:
        return
    g = Image.new("L", (W, H), 0)
    ImageDraw.Draw(g).ellipse((cx - r, cy - r, cx + r, cy + r), fill=int(255 * a))
    g = g.filter(ImageFilter.GaussianBlur(r / 3))
    ov = Image.new("RGBA", (W, H), (255, 170, 80, 0))
    ov.putalpha(g.point(lambda v: int(v * 0.55)))
    fr.alpha_composite(ov)


def step(t):
    B.STEP = int(t * 12)
    return B.STEP / 12


# ---------- episodes ----------
def ep_blanket(t, A):
    """Blanket war: him too hot, too cold, too hot... she wins."""
    t = step(t)
    fr = A["bedroom"].copy()
    moves = [(0, 540), (1.0, 300), (3.6, 790), (6.7, 280)]
    cx = 540
    for i, (t0, x) in enumerate(moves):
        if t >= t0:
            prev = moves[i - 1][1] if i else x
            cx = prev + (x - prev) * ease((t - t0) / 0.35)
    burrito = t >= 9.3
    dad_cov = abs(cx - 700) < 260 and not burrito
    mom_cov = abs(cx - 380) < 260 or burrito
    sh_d = 0 if dad_cov else 4 * math.sin(t * 50)
    sh_m = 0 if mom_cov else 4 * math.sin(t * 50 + 1)
    # bodies under the duvet
    fr.alpha_composite(A["_bodies"])
    put(fr, A["mom_head"], 310 + sh_m, 1080, 0.82)
    put(fr, A["dad_head"], 770 + sh_d, 1070, 0.82)
    if burrito:
        k = ease((t - 9.3) / 0.4)
        b = A["burrito"]
        put(fr, b, 310, 1450 + (1 - k) * 60, 1.0)
        fr.alpha_composite(A["_bodies_dad"])
    else:
        d = A["duvet"]
        fr.alpha_composite(d, (int(cx - d.width / 2), 1160))
    return fr.convert("RGB")


def ep_heater(t, A):
    """Personal heater: cold house, she hugs him, everyone gets warm, he stays grumpy."""
    t = step(t)
    fr = A["room"].copy()
    B.snow(fr, t, (130, 350, 520, 830))
    th = A["therm"][18]
    fr.alpha_composite(th, (960 - th.width // 2, 830 - th.height // 2))
    warm = ease((t - 5.6) / 1.2)
    cold = 1 - warm
    dad_x = 1300 - 620 * ease((t - 2.8) / 0.9)
    glow(fr, dad_x, 1350, 420 + 30 * math.sin(t * 4), warm)
    shiver = 5 * cold * math.sin(t * 55)
    B.shadow(fr, dad_x, 1720, 380)
    stand(fr, A["dad_front"], dad_x, 1730, 0.96)
    if t < 4.3:
        mom_x = 330
        stand(fr, A["mom_front"], mom_x + shiver, 1690)
    else:
        mom_x = 330 + 160 * ease((t - 4.3) / 0.5)
        stand(fr, A["mom_turn"], mom_x + shiver, 1700)
    if t >= 8.6:
        kx = -200 + (dad_x + 170 + 200) * ease((t - 8.6) / 0.7)
        stand(fr, A["kid_front"], kx, 1760)
    for i in range(4):
        k = (t - 6.2 - i * 0.6) % 2.4
        if t > 6.2 + i * 0.6 and k < 1.8:
            put(fr, A["heart"], dad_x - 220 + i * 150, 1000 - k * 260, 0.5 + 0.2 * (i % 2))
    B.tint(fr, (150, 190, 255), 0.17 * cold)
    B.tint(fr, (255, 168, 90), 0.10 * warm)
    return fr.convert("RGB")


def ep_honey(t, A):
    """Still mad. But hungry."""
    t = step(t)
    fr = A["kit"].copy()
    B.shadow(fr, 690, 1770, 420)
    stand(fr, A["dad_front"], 690, 1780, 0.98)
    cs = 1.0 if t < 9.6 else max(0.35, 1 - 0.65 * ease((t - 9.6) / 2.0))
    put(fr, A["cloud"], 700, 620 + 8 * math.sin(t * 3), cs)
    if cs > 0.6:
        d = ImageDraw.Draw(fr)
        r = random.Random(B.STEP)
        for _ in range(9):
            x = 700 + r.uniform(-130, 130) * cs
            y = 700 + r.uniform(0, 140)
            d.line((x, y, x - 10, y + 40), fill=(120, 150, 210, 230), width=6)
    if t >= 3.4:
        mx = -300 + 560 * ease((t - 3.4) / 0.8)
        B.shadow(fr, mx, 1740, 300)
        stand(fr, A["mom_turn"], mx, 1750)
    level = 10 if t < 9.6 else max(0, int(10 - (t - 9.6) * 4))
    if 3.4 <= t < 6.6:
        put(fr, A["jars"][10], -300 + 560 * ease((t - 3.4) / 0.8) + 150, 1330, 0.8)
    elif t >= 6.6:
        k = ease((t - 6.6) / 0.5)
        jx = 410 + (640 - 410) * k
        jy = 1330 - 140 * math.sin(math.pi * k)
        put(fr, A["jars"][level], jx, jy, 0.8)
    return fr.convert("RGB")


def ep_tea(t, A):
    """She's not talking to him. He still brings a blanket and tea."""
    t = step(t)
    fr = A["room"].copy()
    B.snow(fr, t, (130, 350, 520, 830))
    th = A["therm"][21]
    fr.alpha_composite(th, (960 - th.width // 2, 830 - th.height // 2))
    turned = t >= 10.0
    B.shadow(fr, 380, 1700, 300)
    stand(fr, A["mom_turn"] if turned else A["mom_back"], 380, 1710, flip=False)
    if t >= 4.4:
        k = ease((t - 4.4) / 0.4)
        sh = A["shawl"]
        fr.alpha_composite(sh, (int(380 - sh.width / 2), int(1180 - (1 - k) * 500)))
    fr.alpha_composite(A["_table"], (0, 0))
    if t >= 7.0:
        k = ease((t - 7.0) / 0.3)
        put(fr, A["cup"], 780, 1330 - (1 - k) * 80, 0.9 * k + 0.01)
        if k >= 1:
            d = ImageDraw.Draw(fr)
            for i in range(3):
                x = 760 + i * 25
                y0 = 1240 - ((t * 60 + i * 30) % 90)
                d.arc((x - 18, y0 - 60, x + 18, y0), 90, 270, fill=(250, 246, 236, 200), width=6)
    if 3.0 <= t < 4.4:
        dx = -300 + 900 * ease((t - 3.0) / 0.8)
    elif 4.4 <= t < 8.6:
        dx = 600
    elif 8.6 <= t < 9.8:
        dx = 600 - 1100 * ease((t - 8.6) / 0.9)
    else:
        dx = None
    if dx is not None:
        B.shadow(fr, dx, 1740, 360)
        stand(fr, A["dad_side"], dx, 1750, 0.98, flip=(t >= 8.6))
    if turned:
        k = ease((t - 10.4) / 0.4) if t > 10.4 else 0
        if k > 0:
            put(fr, A["heart"], 470, 900 - 40 * k, 0.4 + 0.5 * k)
    return fr.convert("RGB")


def ep_tuck(t, A):
    """Dad tucks him in. Again. And again. Who tucked in who?"""
    t = step(t)
    fr = A["kidroom"].copy()
    final = t >= 9.0
    kid_up = (3.2 <= t < 5.2) or (6.4 <= t < 8.0)
    ky = 1050 if not kid_up else 940
    put(fr, A["kid_head"], 420 if final else 450, ky, 0.9)
    if final:
        put(fr, A["dad_head"], 790, 1010, 0.8, rot=-8)
    if not kid_up:
        d = A["kid_duvet"]
        fr.alpha_composite(d, (590 - d.width // 2, 1150))
    else:
        d = A["kid_duvet"]
        fr.alpha_composite(d, (590 - d.width // 2, 1260))
    if 3.5 <= t < 5.2 or 6.7 <= t < 8.0:
        sp = A["_dad_q"]
        fr.alpha_composite(sp, (130, 640))
    if not final:
        if t < 2.2 or 5.2 <= t < 6.4 or t >= 8.0:
            dx = 900
        elif 2.2 <= t < 3.0:
            dx = 900 + 500 * ease((t - 2.2) / 0.6)
        elif 4.4 <= t < 5.2:
            dx = 1400 - 500 * ease((t - 4.4) / 0.6)
        elif 6.4 <= t < 7.2:
            dx = 900 + 500 * ease((t - 6.4) / 0.6)
        elif 7.4 <= t < 8.0:
            dx = 1400 - 500 * ease((t - 7.4) / 0.5)
        else:
            dx = 1400
        if dx < 1300:
            B.shadow(fr, dx, 1840, 380)
            stand(fr, A["dad_front"], dx, 1850, 0.95)
    else:
        for i in range(3):
            k = (t - 9.0 + i * 0.6) % 1.8
            put(fr, A["_z"], 880 + k * 60 + i * 30, 820 - k * 240, 1.0 + k * 0.8)
    return fr.convert("RGB")


EPISODES = {"blanket": ep_blanket, "heater": ep_heater, "honey": ep_honey, "tea": ep_tea, "tuck": ep_tuck}

SFX = {  # (time, kind)
    "blanket": [(1.0, "whoosh"), (3.6, "whoosh"), (6.7, "whoosh"), (9.3, "pop")],
    "heater": [(2.8, "step"), (4.3, "pop"), (5.6, "ding"), (8.6, "pop")],
    "honey": [(3.4, "step"), (6.6, "pop"), (9.6, "slurp"), (10.4, "slurp"), (11.2, "slurp")],
    "tea": [(3.0, "step"), (4.4, "whoosh"), (7.0, "pop"), (8.6, "step"), (10.4, "ding")],
    "tuck": [(3.2, "pop"), (4.4, "step"), (6.4, "pop"), (7.4, "step"), (9.0, "ding")],
}
SONG = {"blanket": (0.24, 1), "heater": (0.26, 2), "honey": (0.25, 3), "tea": (0.28, 4), "tuck": (0.3, 5)}


def extras(name, A):
    if name == "blanket":
        bodies = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        bodies.alpha_composite(piece((W, H), lambda d: d.rounded_rectangle((150, 1180, 470, 1690), 90), (170, 90, 72), 41, fringe=0))
        dad = piece((W, H), lambda d: d.rounded_rectangle((590, 1170, 960, 1700), 100), (70, 92, 72), 42, fringe=0)
        bodies.alpha_composite(dad)
        A["_bodies"], A["_bodies_dad"] = bodies, dad
    if name == "tea":
        A["_table"] = piece((W, H), lambda d: [d.ellipse((650, 1380, 910, 1440)), d.rectangle((768, 1410, 792, 1700)),
                                              d.ellipse((700, 1680, 860, 1720))], (150, 108, 74), 51)
    if name == "tuck":
        A["_dad_q"] = speech('"dad?"', 3)
        A["_z"] = zzz(1.0)


# ---------- sound ----------
def synth(path, name):
    n = int(SR * DUR)
    out = np.zeros(n)
    beat, seed = SONG[name]
    rng = np.random.default_rng(seed)

    def add(start, sig, gain=1.0):
        i = int(start * SR)
        sig = sig[: max(0, n - i)]
        out[i:i + len(sig)] += sig * gain

    def pluck(freq, dur=0.32, decay=11):
        tt = np.arange(int(SR * dur)) / SR
        env = np.exp(-tt * decay) * np.minimum(1, tt * 400)
        return env * (np.sin(2 * np.pi * freq * tt) + 0.35 * np.sin(4 * np.pi * freq * tt) + 0.12 * np.sin(6 * np.pi * freq * tt))

    scale = [261.6, 293.7, 329.6, 392.0, 440.0, 523.3, 587.3, 659.3]
    bass = [130.8, 196.0, 174.6, 196.0]
    r = random.Random(seed)
    phrase = [r.choice([0, 2, 4, 5, 4, 2, 3, 1, -1]) for _ in range(16)]
    t, k = 0.0, 0
    while t < DUR - 0.5:
        nidx = phrase[k % 16]
        if nidx >= 0:
            add(t, pluck(scale[nidx]), 0.2)
        if k % 4 == 0:
            add(t, pluck(bass[(k // 4) % 4], 0.5, 6), 0.28)
        t += beat
        k += 1
    for t0, kind in SFX[name]:
        if kind == "whoosh":
            wl = int(SR * 0.5)
            sm = np.convolve(rng.standard_normal(wl), np.ones(30) / 30, mode="same")
            add(t0, sm * np.sin(np.linspace(0, np.pi, wl)) ** 2, 0.9)
        elif kind == "pop":
            tt = np.arange(int(SR * 0.15)) / SR
            add(t0, np.sin(2 * np.pi * (500 + 900 * tt / 0.15) * tt) * np.exp(-tt * 30), 0.5)
        elif kind == "ding":
            tt = np.arange(int(SR * 1.0)) / SR
            add(t0, np.exp(-tt * 4) * (np.sin(2 * np.pi * 1568 * tt) + 0.5 * np.sin(2 * np.pi * 2349 * tt)), 0.3)
        elif kind == "step":
            for j in range(3):
                tt = np.arange(int(SR * 0.08)) / SR
                add(t0 + j * 0.2, np.sin(2 * np.pi * 110 * tt) * np.exp(-tt * 40), 0.6)
        elif kind == "slurp":
            tt = np.arange(int(SR * 0.3)) / SR
            add(t0, np.sin(2 * np.pi * (300 - 200 * tt / 0.3) * tt) * np.exp(-tt * 8) * (rng.standard_normal(len(tt)) * 0.3 + 1), 0.35)
    out[: int(SR * 0.05)] *= np.linspace(0, 1, int(SR * 0.05))
    out[-int(SR * 0.6):] *= np.linspace(1, 0, int(SR * 0.6))
    out = out / (np.abs(out).max() + 1e-9) * 0.8
    pcm = (out * 32767).astype(np.int16)
    with wave.open(str(path), "wb") as w:
        w.setnchannels(2)
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes(np.stack([pcm, pcm], 1).tobytes())


def render(name, out, A=None):
    A = A or assets()
    extras(name, A)
    fn = EPISODES[name]
    tmp = Path(tempfile.mkdtemp())
    proc = subprocess.Popen(["ffmpeg", "-nostdin", "-loglevel", "error", "-y", "-f", "rawvideo", "-pix_fmt", "rgb24",
                             "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-", "-c:v", "libx264", "-preset", "veryfast",
                             "-crf", "17", "-pix_fmt", "yuv420p", str(tmp / "v.mp4")], stdin=subprocess.PIPE)
    cache = {}
    for i in range(int(DUR * FPS)):
        s = int(i / FPS * 12)  # stop-motion: only 12 distinct drawings per second
        if s not in cache:
            cache = {s: fn(i / FPS, A).tobytes()}
        proc.stdin.write(cache[s])
    proc.stdin.close()
    proc.wait()
    synth(tmp / "a.wav", name)
    subprocess.run(["ffmpeg", "-nostdin", "-loglevel", "error", "-y", "-i", str(tmp / "v.mp4"), "-i", str(tmp / "a.wav"),
                    "-map", "0:v", "-map", "1:a", "-c:v", "copy", "-c:a", "aac", "-ac", "2", "-ar", "48000", "-shortest",
                    str(out)], check=True)


if __name__ == "__main__":
    name = sys.argv[1]
    if sys.argv[2] == "--frames":
        A = assets()
        extras(name, A)
        for t in sys.argv[4:]:
            EPISODES[name](float(t), A).save(f"{sys.argv[3]}_{name}_{t}.png")
    else:
        render(name, sys.argv[2])
