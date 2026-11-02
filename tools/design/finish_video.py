"""Finish an AI-generated vertical clip for posting.

- hook text at the top for the first seconds (white, soft shadow)
- optional "note reveal" ending: the last frame freezes, softly blurs and dims,
  and a TinyNotes-style paper note with the message slides up (Tiny / The Note)
- brand watermark bottom centre
- output: 1080x1920, H.264 30fps, AAC stereo 48k (the clip's own sound is kept)

python tools/design/finish_video.py in.mp4 out.mp4 --brand tinynotes --hook "..." [--note "..." --sign "me"]
"""
import argparse
import json
import subprocess
import tempfile
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter, ImageFont

ROOT = Path(__file__).resolve().parents[2]
G = "/usr/share/fonts/truetype/google-fonts/"
W, H, FPS = 1080, 1920, 30
PAPER, INK, MAROON = (255, 253, 247), (92, 40, 38), (132, 36, 38)


def font(name, size, wght=None):
    f = ImageFont.truetype(G + name, size)
    if wght:
        try:
            f.set_variation_by_axes([wght])
        except Exception:
            pass
    return f


def wrap(d, text, f, maxw):
    lines, line = [], []
    for w in text.split():
        if line and d.textlength(" ".join(line + [w]), font=f) > maxw:
            lines.append(" ".join(line))
            line = [w]
        else:
            line.append(w)
    lines.append(" ".join(line))
    return lines


def hook_layer(text):
    im = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    f = font("Poppins-Bold.ttf", 64)
    lines = wrap(d, text, f, W - 160)
    y = 250
    sh = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    sd = ImageDraw.Draw(sh)
    for ln in lines:
        x = (W - d.textlength(ln, font=f)) / 2
        sd.text((x, y + 4), ln, font=f, fill=(0, 0, 0, 170))
        d.text((x, y), ln, font=f, fill=(255, 255, 255, 255))
        y += 84
    sh = sh.filter(ImageFilter.GaussianBlur(8))
    sh.alpha_composite(im)
    return sh


def watermark(brand):
    im = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    name = "tinynotes_wm_white.png" if brand == "tinynotes" else "factyeap_wm_white.png"
    logo = Image.open(ROOT / "brand" / name).convert("RGBA")
    lw = 170 if brand == "tinynotes" else 210
    logo = logo.resize((lw, int(logo.height * lw / logo.width)), Image.LANCZOS)
    logo.putalpha(logo.split()[3].point(lambda v: int(v * 0.6)))
    im.alpha_composite(logo, ((W - lw) // 2, H - logo.height - 330))
    return im


def note_card(text, sign):
    cw = 860
    nf = font("Lora-Italic-Variable.ttf", 78 if len(text) < 40 else 66, 500)
    sf = font("Lora-Italic-Variable.ttf", 50, 400)
    tmp = ImageDraw.Draw(Image.new("RGB", (10, 10)))
    lines = [ln for part in text.split("\n") for ln in wrap(tmp, part, nf, cw - 180)]
    lh = int(nf.size * 1.4)
    ch = 150 + len(lines) * lh + (130 if sign else 60)
    c = Image.new("RGBA", (cw + 80, ch + 80), (0, 0, 0, 0))
    d = ImageDraw.Draw(c)
    d.rounded_rectangle((40, 40, 40 + cw, 40 + ch), 24, fill=PAPER + (255,))
    d.rectangle((40 + cw / 2 - 100, 16, 40 + cw / 2 + 100, 78), fill=(232, 214, 196, 225))
    y = 40 + 110
    for ln in lines:
        d.text((40 + (cw - d.textlength(ln, font=nf)) / 2, y), ln, font=nf, fill=INK)
        y += lh
    heart = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 44)
    if sign:
        hx = 40 + cw - 100 - d.textlength("♥", font=heart)
        d.text((hx, y + 40), "♥", font=heart, fill=MAROON)
        d.text((hx - 20 - d.textlength(sign, font=sf), y + 30), sign, font=sf, fill=MAROON)
    else:
        hx = 40 + (cw - d.textlength("♥", font=heart)) / 2
        d.text((hx, y + 10), "♥", font=heart, fill=MAROON)
    c = c.rotate(-1.4, resample=Image.BICUBIC, expand=True)
    shadow = Image.new("RGBA", c.size, (0, 0, 0, 0))
    shadow.putalpha(c.split()[3].point(lambda v: int(v * 0.35)).filter(ImageFilter.GaussianBlur(22)))
    return c, shadow


def probe(path):
    out = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration:stream=codec_type",
                          "-of", "json", str(path)], capture_output=True, text=True).stdout
    j = json.loads(out)
    return float(j["format"]["duration"]), any(s["codec_type"] == "audio" for s in j["streams"])


def run(cmd):
    subprocess.run(["ffmpeg", "-nostdin", "-loglevel", "error", "-y", *cmd], check=True)


def finish(src, out, brand, hook, note=None, sign=None, hook_secs=3.0, hold=3.0):
    tmp = Path(tempfile.mkdtemp())
    dur, has_audio = probe(src)
    base = tmp / "base.mp4"
    run(["-i", str(src), *([] if has_audio else ["-f", "lavfi", "-i", "anullsrc=r=48000:cl=stereo"]),
         "-vf", f"scale={W}:{H}:force_original_aspect_ratio=increase,crop={W}:{H},fps={FPS}",
         "-c:v", "libx264", "-preset", "veryfast", "-crf", "18", "-pix_fmt", "yuv420p",
         "-c:a", "aac", "-ac", "2", "-ar", "48000", *([] if has_audio else ["-shortest"]), str(base)])
    hook_layer(hook).save(tmp / "hook.png")
    watermark(brand).save(tmp / "wm.png")
    parts = [base]
    if note:
        run(["-sseof", "-0.1", "-i", str(base), "-frames:v", "1", "-update", "1", str(tmp / "last.png")])
        last = Image.open(tmp / "last.png").convert("RGB").resize((W, H))
        bg = Image.blend(last.filter(ImageFilter.GaussianBlur(18)), Image.new("RGB", (W, H), (20, 14, 12)), 0.35)
        card, shadow = note_card(note, sign)
        n = int(hold * FPS)
        for i in range(n):
            t = min(1.0, i / (0.6 * FPS))
            ease = 1 - (1 - t) ** 3
            frame = Image.blend(last, bg, ease).convert("RGBA")
            y = int((H - card.height) / 2 - 60 + (1 - ease) * 220)
            x = (W - card.width) // 2
            sh = shadow.copy()
            sh.putalpha(sh.split()[3].point(lambda v: int(v * ease)))
            cc = card.copy()
            cc.putalpha(cc.split()[3].point(lambda v: int(v * ease)))
            frame.alpha_composite(sh, (x + 10, y + 24))
            frame.alpha_composite(cc, (x, y))
            frame.convert("RGB").save(tmp / f"n{i:03d}.jpg", quality=93)
        endv = tmp / "end.mp4"
        run(["-framerate", str(FPS), "-i", str(tmp / "n%03d.jpg"), "-f", "lavfi", "-t", str(hold),
             "-i", "anullsrc=r=48000:cl=stereo", "-c:v", "libx264", "-preset", "veryfast", "-crf", "18",
             "-pix_fmt", "yuv420p", "-c:a", "aac", "-ac", "2", "-ar", "48000", "-shortest", str(endv)])
        parts.append(endv)
    joined = tmp / "joined.mp4"
    if len(parts) > 1:
        (tmp / "list.txt").write_text("".join(f"file '{p}'\n" for p in parts))
        run(["-f", "concat", "-safe", "0", "-i", str(tmp / "list.txt"), "-c", "copy", str(joined)])
    else:
        joined = base
    run(["-i", str(joined), "-i", str(tmp / "hook.png"), "-i", str(tmp / "wm.png"), "-filter_complex",
         f"[0:v][1:v]overlay=0:0:enable='lt(t,{hook_secs})'[a];[a][2:v]overlay=0:0[v]",
         "-map", "[v]", "-map", "0:a", "-c:v", "libx264", "-preset", "veryfast", "-crf", "20", "-pix_fmt", "yuv420p",
         "-r", str(FPS), "-g", "60", "-keyint_min", "60", "-sc_threshold", "0",
         "-c:a", "aac", "-ac", "2", "-ar", "48000", "-b:a", "128k", "-movflags", "+faststart", str(out)])


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("src")
    p.add_argument("out")
    p.add_argument("--brand", required=True)
    p.add_argument("--hook", required=True)
    p.add_argument("--note")
    p.add_argument("--sign")
    a = p.parse_args()
    finish(a.src, a.out, a.brand, a.hook, a.note, a.sign)
