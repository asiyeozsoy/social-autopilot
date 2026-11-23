"""Very soft, slow solo piano (real sampled grand, no drums): gentle broken chords in the left
hand, a few quiet melody notes on top, long warm reverb, felt-piano tone. Every seed is a
slightly different piece (key, progression, tempo, pattern).

python tools/design/soft_piano.py out.wav 12 [seed]
from soft_piano import soft_piano; soft_piano("out.wav", 12, "seed")

Samples: FluidR3_GM acoustic grand (MIT licence), brand/piano/*.mp3.
"""
import hashlib
import subprocess
import sys
import wave
from pathlib import Path

import numpy as np
from scipy import signal

SR = 44100
ROOT = Path(__file__).resolve().parents[2]
NAMES = ["C", "Db", "D", "Eb", "E", "F", "Gb", "G", "Ab", "A", "Bb", "B"]
_CACHE = {}

# calm, emotional progressions (root offset, chord intervals), one per bar
PROGS = [
    [(0, [0, 4, 7, 11]), (9, [0, 3, 7, 10]), (5, [0, 4, 7, 11]), (7, [0, 2, 7])],     # Imaj7 vi7 IVmaj7 Vsus2
    [(5, [0, 4, 7, 11]), (0, [0, 4, 7]), (9, [0, 3, 7]), (7, [0, 5, 7])],            # IVmaj7 I vi Vsus4
    [(9, [0, 3, 7, 10]), (5, [0, 4, 7, 11]), (0, [0, 4, 7, 14]), (7, [0, 4, 7])],    # vi7 IVmaj7 Iadd9 V
    [(0, [0, 7, 14]), (4, [0, 3, 7, 10]), (5, [0, 4, 7, 11]), (5, [0, 3, 7])],       # Iadd9 iii7 IVmaj7 iv (tender)
    [(5, [0, 7, 11, 16]), (7, [0, 7, 14]), (9, [0, 3, 7, 10]), (0, [0, 7, 16])],     # open voicings
]


def _rng(seed):
    return np.random.default_rng(int(hashlib.md5(str(seed).encode()).hexdigest()[:8], 16))


def _sample(midi):
    midi = int(min(max(midi, 21), 108))
    if midi not in _CACHE:
        name = NAMES[midi % 12] + str(midi // 12 - 1)
        raw = subprocess.run(["ffmpeg", "-nostdin", "-loglevel", "error", "-i", str(ROOT / f"brand/piano/{name}.mp3"),
                              "-f", "f32le", "-ac", "1", "-ar", str(SR), "-"], capture_output=True, check=True).stdout
        x = np.frombuffer(raw, np.float32).astype(np.float64)
        lead = np.argmax(np.abs(x) > 0.01 * np.abs(x).max())  # drop silence before the attack
        _CACHE[midi] = x[lead:]
    return _CACHE[midi]


def _note(midi, vel, hold):
    """vel 0..1 (kept low = soft). Softer notes also get a darker tone."""
    x = _sample(midi).copy()
    n = min(len(x), int((hold + 1.8) * SR))
    x = x[:n]
    rel = int(min(n, hold * SR))
    env = np.ones(n)
    if rel < n:  # damper: fade after the hold time
        env[rel:] = np.exp(-np.arange(n - rel) / (0.45 * SR))
    b, a = signal.butter(1, (1500 + 3500 * vel) / (SR / 2))  # felt: low velocity = darker
    return signal.lfilter(b, a, x * env) * vel


def _add(buf, x, at):
    i = int(at * SR)
    if i >= len(buf):
        return
    j = min(len(buf), i + len(x))
    buf[i:j] += x[: j - i]


def _reverb(x, seconds=3.2, mix=0.32, rng=None):
    n = int(seconds * SR)
    t = np.arange(n) / SR
    ir = (rng.standard_normal(n) if rng is not None else np.random.standard_normal(n)) * np.exp(-t * 6.9 / seconds)
    b, a = signal.butter(1, 4200 / (SR / 2))
    ir = signal.lfilter(b, a, ir)
    ir[: int(0.02 * SR)] = 0
    wet = signal.fftconvolve(x, ir)[: len(x)]
    wet *= np.abs(x).max() / (np.abs(wet).max() + 1e-9)
    return x * (1 - mix) + wet * mix


def render(dur, seed=0):
    rng = _rng(seed)
    bpm = rng.uniform(56, 66)
    beat = 60 / bpm
    bar = 4 * beat
    key = 55 + int(rng.integers(-5, 5))  # around G3
    prog = PROGS[int(rng.integers(len(PROGS)))]
    pattern = rng.choice(["arp_up", "arp_wave", "block_soft"], p=[0.4, 0.4, 0.2])
    total = int((dur + 4) * SR)
    left, right = np.zeros(total), np.zeros(total)
    nbars = int(np.ceil(dur / bar)) + 1
    last_mel = key + 12
    for b in range(nbars):
        root, ivs = prog[b % len(prog)]
        t0 = b * bar
        bass = key - 12 + root
        while bass > key - 5:
            bass -= 12
        _add(left, _note(bass, 0.20, bar * 0.95), t0)
        chord = [key + root + iv for iv in ivs]
        chord = [m - 12 if m > key + 14 else m for m in chord]
        if pattern == "block_soft":
            for k, m in enumerate(sorted(chord)):
                _add(left, _note(m, 0.12, bar * 0.9), t0 + k * 0.035)
            _add(left, _note(chord[1], 0.09, beat * 1.8), t0 + 2 * beat)
        else:
            seq = sorted(chord)
            if pattern == "arp_wave":
                seq = seq + seq[-2:0:-1]
            for k in range(8):
                m = seq[k % len(seq)]
                _add(left, _note(m, 0.11 * rng.uniform(0.8, 1.0), beat * 1.6), t0 + k * beat / 2 + rng.uniform(0, 0.012))
        # melody: 1-3 quiet notes per bar from the chord, an octave up, moving by small steps
        tones = sorted({m + 12 for m in chord} | {m + 24 for m in chord if m + 24 <= key + 26})
        for k in range(int(rng.choice([1, 2, 2, 3]))):
            if b == 0 and k == 0:
                continue
            cand = sorted(tones, key=lambda m: abs(m - last_mel) + rng.uniform(0, 3))
            m = cand[0] if rng.random() < 0.7 else cand[min(1, len(cand) - 1)]
            last_mel = m
            at = t0 + rng.choice([0, 1.5, 2, 3]) * beat + k * beat * 0.5
            _add(right, _note(m, 0.16 * rng.uniform(0.85, 1.0), beat * 2.5), at)
    mix = left * 0.9 + right
    mix = _reverb(mix, rng=rng)
    # gentle compression + final low-pass so nothing is bright
    env = signal.lfilter([0.002], [1, -0.998], np.abs(mix))
    gain = 1 / np.maximum(1, env / (env.max() * 0.55 + 1e-9)) ** 0.5
    mix = mix * gain
    b, a = signal.butter(2, 5200 / (SR / 2))
    mix = signal.lfilter(b, a, mix)
    mix = mix[: int(dur * SR)]
    fade = int(min(1.5, dur / 4) * SR)
    mix[:int(0.25 * SR)] *= np.linspace(0, 1, int(0.25 * SR))
    mix[-fade:] *= np.linspace(1, 0, fade)
    mix = mix / (np.abs(mix).max() + 1e-9) * 0.6  # leave headroom, quiet master
    st = np.stack([mix, np.roll(mix, int(0.012 * SR)) * 0.96], 1)  # a touch of width
    return st


def soft_piano(out, dur, seed=0):
    st = render(float(dur), seed)
    pcm = (np.clip(st, -1, 1) * 32767).astype(np.int16)
    with wave.open(str(out), "wb") as w:
        w.setnchannels(2)
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes(pcm.tobytes())
    return out


if __name__ == "__main__":
    soft_piano(sys.argv[1], float(sys.argv[2]), sys.argv[3] if len(sys.argv) > 3 else 0)
