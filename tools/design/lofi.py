"""Chill, emotional piano lo-fi bed (lofi-girl feel); every seed gives a slightly different track.

Warm Rhodes-style 7th/9th chords, soft swung dusty drums, round sine bass, a few sparse
melody notes, vinyl crackle, tape wobble and a low-pass "old tape" master.

python tools/design/lofi.py out.wav 10.1 [seed]
from lofi import lofi; lofi("out.wav", 10.1, "seed")
"""
import hashlib
import sys
import wave

import numpy as np
from scipy import signal

SR = 48000

# emotional progressions as (root semitone from key, chord intervals); each lasts one bar
PROGRESSIONS = [
    [(5, [0, 4, 7, 11, 14]), (4, [0, 3, 7, 10, 14]), (2, [0, 3, 7, 10, 14]), (0, [0, 4, 7, 11, 14])],   # IVmaj9 iii7 ii9 Imaj9
    [(9, [0, 3, 7, 10, 14]), (5, [0, 4, 7, 11, 14]), (0, [0, 4, 7, 11]), (7, [0, 4, 7, 9])],             # vi9 IVmaj9 Imaj7 V6
    [(2, [0, 3, 7, 10, 14]), (7, [0, 4, 10, 14, 21]), (0, [0, 4, 7, 11, 14]), (9, [0, 4, 7, 10, 13])],   # ii9 V13 Imaj9 VI7b9
    [(0, [0, 4, 7, 11, 14]), (9, [0, 3, 7, 10]), (5, [0, 4, 7, 11, 14]), (5, [0, 3, 7, 10, 14])],        # Imaj9 vi7 IVmaj9 iv9 (sad turn)
    [(9, [0, 3, 7, 10, 14]), (2, [0, 3, 7, 10]), (7, [0, 4, 7, 10, 14]), (0, [0, 4, 7, 11, 14])],        # vi9 ii7 V9 Imaj9
]
PENTA = [0, 2, 4, 7, 9]


def _rng(seed):
    return np.random.default_rng(int(hashlib.md5(str(seed).encode()).hexdigest()[:8], 16))


def _hz(midi):
    return 440.0 * 2 ** ((midi - 69) / 12)


def _rhodes(f, dur, vel, rng):
    t = np.arange(int(dur * SR)) / SR
    det = 1 + rng.uniform(-0.0015, 0.0015)
    env = np.exp(-t * 1.1) * (1 - np.exp(-t * 180))
    bell = np.exp(-t * 7)
    x = (np.sin(2 * np.pi * f * det * t) + 0.35 * np.sin(2 * np.pi * 2 * f * t) * bell
         + 0.12 * np.sin(2 * np.pi * 3.01 * f * t) * bell + 0.05 * np.sin(2 * np.pi * 7 * f * t) * np.exp(-t * 20))
    trem = 1 + 0.12 * np.sin(2 * np.pi * 4.6 * t)
    return x * env * trem * vel


def _piano(f, dur, vel, rng):
    """Soft felt-piano tone: inharmonic partials that die faster the higher they are, plus a little hammer thump."""
    t = np.arange(int(dur * SR)) / SR
    x = np.zeros_like(t)
    B = 0.0004
    for k, amp in enumerate((1.0, 0.55, 0.28, 0.16, 0.09, 0.05), start=1):
        fk = f * k * np.sqrt(1 + B * k * k)
        if fk > 9000:
            break
        x += amp * np.sin(2 * np.pi * fk * t + rng.uniform(0, 6.28)) * np.exp(-t * (0.9 + 0.9 * k))
    x *= (1 - np.exp(-t * 400))
    thump = np.sin(2 * np.pi * 90 * t) * np.exp(-t * 60) * 0.15
    return (x + thump) * vel


def _kick(vel):
    t = np.arange(int(0.45 * SR)) / SR
    f = 48 + 70 * np.exp(-t * 28)
    return np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t * 8) * vel


def _snare(vel, rng):
    t = np.arange(int(0.3 * SR)) / SR
    n = rng.standard_normal(len(t))
    b, a = signal.butter(2, [900 / (SR / 2), 5000 / (SR / 2)], "band")
    n = signal.lfilter(b, a, n) * np.exp(-t * 18)
    tone = np.sin(2 * np.pi * 190 * t) * np.exp(-t * 30) * 0.4
    return (n * 0.8 + tone) * vel


def _hat(vel, rng):
    t = np.arange(int(0.08 * SR)) / SR
    n = rng.standard_normal(len(t))
    b, a = signal.butter(2, 6500 / (SR / 2), "high")
    return signal.lfilter(b, a, n) * np.exp(-t * 60) * vel


def _add(buf, x, at):
    i = int(at * SR)
    if i >= len(buf):
        return
    j = min(len(buf), i + len(x))
    buf[i:j] += x[: j - i]


def render(dur, seed=0):  # noqa: C901
    rng = _rng(seed)
    bpm = rng.uniform(64, 78)
    beat = 60 / bpm
    bar = 4 * beat
    key = 48 + int(rng.integers(0, 12)) if rng.random() < 0.5 else 53 + int(rng.integers(-3, 4))
    prog = PROGRESSIONS[int(rng.integers(len(PROGRESSIONS)))]
    swing = rng.uniform(0.56, 0.62)
    total = int((dur + 1.5) * SR)
    keys, drums, bass, mel = (np.zeros(total) for _ in range(4))
    nbars = int(np.ceil(dur / bar)) + 1
    style = rng.choice(["piano", "piano_drums", "arp", "arp_drums", "piano_rhodes"], p=[0.25, 0.25, 0.2, 0.15, 0.15])
    voice = _piano
    for b in range(nbars):
        root, ivs = prog[b % len(prog)]
        t0 = b * bar
        notes = []
        for iv in ivs:
            m = key + root + iv
            while m > 76:
                m -= 12
            notes.append(m)
        if style.startswith("arp"):
            # gentle broken chord, up then down, eighth notes
            seq = notes + notes[-2:0:-1]
            for k in range(8):
                _add(keys, voice(_hz(seq[k % len(seq)]), beat * 2.2, 0.13 * rng.uniform(0.75, 1.0), rng), t0 + k * beat / 2 + rng.uniform(0, 0.01))
        else:
            for k, m in enumerate(notes):  # soft rolled chord
                _add(keys, voice(_hz(m), bar * 1.2, 0.13 * rng.uniform(0.8, 1.0), rng), t0 + k * 0.022)
            if rng.random() < 0.5:
                for k, m in enumerate(notes[1:4]):
                    _add(keys, voice(_hz(m), beat * 1.6, 0.06, rng), t0 + 2.5 * beat + k * 0.015)
        if style == "piano_rhodes":
            for m in notes[:3]:
                _add(keys, _rhodes(_hz(m - 12), bar * 1.1, 0.07, rng), t0)
        # bass: low piano root, soft
        bm = key + root - 12
        while bm > 45:
            bm -= 12
        _add(bass, voice(_hz(bm), bar * 1.1, 0.16, rng), t0)
        # sparse melody on top: 1-3 notes, high and quiet
        for _ in range(int(rng.integers(1, 4))):
            at = t0 + rng.choice([0.5, 1, 1.5, 2, 3, 3.5]) * beat
            m = key + 24 + PENTA[int(rng.integers(len(PENTA)))]
            _add(mel, voice(_hz(m), beat * 2.0, 0.07, rng), at)
        if not style.endswith("drums") or b == 0:
            continue
        for s_ in range(8):
            off = (s_ // 2) * beat + (swing * beat if s_ % 2 else 0)
            _add(drums, _hat(0.07 * rng.uniform(0.6, 1.0) * (0.7 if s_ % 2 else 1), rng), t0 + off)
        _add(drums, _kick(0.35), t0)
        _add(drums, _kick(0.25), t0 + 2.5 * beat)
        _add(drums, _snare(0.12, rng), t0 + beat + 0.015)
        _add(drums, _snare(0.12, rng), t0 + 3 * beat + 0.015)
    # dusty drums
    b, a = signal.butter(2, 3800 / (SR / 2), "low")
    drums = signal.lfilter(b, a, drums)
    mix = keys + 0.9 * mel + bass + drums * 0.8
    # tape wobble (slow pitch drift) via a modulated delay line
    t = np.arange(total) / SR
    d = (0.0018 + 0.0012 * np.sin(2 * np.pi * 0.45 * t + rng.uniform(0, 6)) + 0.0004 * np.sin(2 * np.pi * 5.3 * t)) * SR
    idx = np.clip(np.arange(total) - d, 0, total - 1)
    i0 = np.floor(idx).astype(int)
    fr = idx - i0
    i1 = np.minimum(i0 + 1, total - 1)
    mix = mix[i0] * (1 - fr) + mix[i1] * fr
    # warm low-pass master + vinyl
    b, a = signal.butter(2, 5200 / (SR / 2), "low")
    mix = signal.lfilter(b, a, mix)
    hiss = signal.lfilter(*signal.butter(1, 3000 / (SR / 2), "low"), rng.standard_normal(total)) * 0.006
    crackle = np.zeros(total)
    pops = rng.integers(0, total, int(dur * 5))
    crackle[pops] = rng.uniform(-0.25, 0.25, len(pops))
    crackle = signal.lfilter(*signal.butter(1, 2500 / (SR / 2), "high"), crackle)
    mix = mix + hiss + crackle * 0.5
    mix = np.tanh(mix * 1.4) / 1.4
    n = int(dur * SR)
    mix = mix[:n]
    fade_in, fade_out = int(0.15 * SR), int(0.9 * SR)
    mix[:fade_in] *= np.linspace(0, 1, fade_in)
    mix[-fade_out:] *= np.linspace(1, 0, fade_out) ** 1.5
    mix = mix / (np.abs(mix).max() + 1e-9) * 0.7
    # gentle stereo: keys slightly wider via a short Haas delay
    right = np.concatenate([np.zeros(int(0.012 * SR)), mix])[:n]
    return np.stack([mix * 0.92 + right * 0.08, mix * 0.6 + right * 0.4], 1)


def lofi(path, dur, seed=0):
    x = render(float(dur), seed)
    pcm = (np.clip(x, -1, 1) * 32767).astype(np.int16)
    with wave.open(str(path), "wb") as w:
        w.setnchannels(2)
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes(pcm.tobytes())


if __name__ == "__main__":
    lofi(sys.argv[1], float(sys.argv[2]), sys.argv[3] if len(sys.argv) > 3 else 0)
