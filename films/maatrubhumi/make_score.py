"""Compose the film's score in code: military drums, deep bass and strings, timed to the narration.

  python make_score.py --project films/maatrubhumi        # writes audio/score.wav

Nothing is sampled or licensed: every sound is synthesised here with numpy (and scipy filters), so the
score is original and safe to publish. It follows the film's seven sections (takes in script.json):
  open      low drone, distant taiko hits like heartbeats
  title     a riser into one big hit, strings enter (D minor)
  world     a steady march: snare pattern, taiko on the downbeat
  cast      march continues, brass-like swell
  sacrifice drums drop out; strings alone, softer
  climax    full drums, faster snare rolls, everything builds
  end       one final hit, a long low tail into silence
"""
import argparse
import json
import pathlib
import wave

import numpy as np

try:
    from scipy.signal import butter, lfilter
except ImportError:                                       # scipy is optional: a plain one-pole filter instead
    butter = None

SR = 48000
BPM = 84
BEAT = 60 / BPM


def lowpass(x, hz):
    if butter is not None:
        b, a = butter(2, hz / (SR / 2))
        return lfilter(b, a, x)
    k = np.exp(-2 * np.pi * hz / SR); y = np.empty_like(x); acc = 0.0
    for i, v in enumerate(x):
        acc = (1 - k) * v + k * acc; y[i] = acc
    return y


def highpass(x, hz):
    if butter is not None:
        b, a = butter(2, hz / (SR / 2), btype="high")
        return lfilter(b, a, x)
    return x - lowpass(x, hz)


def env(n, attack, release, total):
    """Attack-sustain-release envelope of n samples (seconds)."""
    t = np.arange(n) / SR
    e = np.minimum(1, t / max(attack, 1e-3))
    e *= np.clip((total - t) / max(release, 1e-3), 0, 1)
    return e


def add(buf, start, sig, gain=1.0):
    i = int(start * SR)
    if i >= len(buf) or i + len(sig) <= 0:
        return
    j0 = max(0, -i); i = max(0, i)
    n = min(len(sig) - j0, len(buf) - i)
    buf[i:i + n] += gain * sig[j0:j0 + n]


rng = np.random.default_rng(1903)


def taiko(size=1.0):
    n = int(SR * 1.6); t = np.arange(n) / SR
    f = 48 * size + 70 * size * np.exp(-t * 18)
    body = np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t * 3.2)
    slap = lowpass(rng.standard_normal(n), 900) * np.exp(-t * 40) * 0.6
    return np.tanh(1.6 * (body + slap))


def snare(accent=1.0):
    n = int(SR * 0.35); t = np.arange(n) / SR
    noise = highpass(rng.standard_normal(n), 1800) * np.exp(-t * 22)
    tone = np.sin(2 * np.pi * 190 * t) * np.exp(-t * 30)
    return accent * (0.7 * noise + 0.5 * tone)


def roll(dur, start_gain=0.2, end_gain=1.0):
    n = int(SR * (dur + 0.3)); out = np.zeros(n)
    k = int(dur / 0.055)
    for i in range(k):
        g = start_gain + (end_gain - start_gain) * i / max(1, k - 1)
        add(out, i * 0.055, snare(0.5), g)
    return out


def boom(size=1.0):
    n = int(SR * 4.0); t = np.arange(n) / SR
    f = 30 + 60 * np.exp(-t * 6)
    sub = np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t * 0.9)
    crash = lowpass(rng.standard_normal(n), 3000) * np.exp(-t * 2.2) * 0.35
    return np.tanh(size * 1.4 * (sub + crash))


def pad(freqs, dur, attack=1.5, release=2.0, bright=1400, detune=0.004):
    """Strings: detuned saws per note, low-passed, slow swell."""
    n = int(SR * (dur + release)); t = np.arange(n) / SR
    out = np.zeros(n)
    for f in freqs:
        for d in (-detune, 0, detune):
            ph = (t * f * (1 + d)) % 1.0
            out += (2 * ph - 1) * (0.5 if d else 0.7)
    out = lowpass(out / (len(freqs) * 2), bright)
    vib = 1 + 0.08 * np.sin(2 * np.pi * 5.2 * t)
    return out * env(n, attack, release, dur + release) * vib


def drone(dur, f=36.71):
    n = int(SR * dur); t = np.arange(n) / SR
    sig = np.sin(2 * np.pi * f * t) + 0.5 * np.sin(2 * np.pi * f * 2 * t) + 0.25 * np.sin(2 * np.pi * f * 1.5 * t)
    swell = 0.75 + 0.25 * np.sin(2 * np.pi * t / 7.0)
    return lowpass(sig, 180) * swell * env(n, 3.0, 3.0, dur)


NOTE = {"D2": 73.42, "F2": 87.31, "A2": 110.0, "Bb2": 116.54, "C3": 130.81, "D3": 146.83, "E3": 164.81, "F3": 174.61,
        "G3": 196.0, "A3": 220.0, "Bb3": 233.08, "C4": 261.63, "D4": 293.66, "F4": 349.23, "A4": 440.0}
CHORDS = {"Dm": ("D3", "F3", "A3", "D4"), "Bb": ("Bb2", "D3", "F3", "Bb3"), "F": ("F2", "C3", "F3", "A3"),
          "C": ("C3", "E3", "G3", "C4"), "Gm": ("G3", "Bb3", "D4", "D3"), "A": ("A2", "E3", "A3", "C4")}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--project", required=True)
    ap.add_argument("--out", default="audio/score.wav")
    a = ap.parse_args()
    proj = pathlib.Path(a.project)
    timing = json.loads((proj / "audio" / "timing.json").read_text())
    script = json.loads((proj / "script.json").read_text())
    seg = {s["id"]: s for s in timing["segments"]}
    total = timing["total_duration"] + 1.0
    takes = [(tk["take"], seg[tk["lines"][0]["id"]]["start"], seg[tk["lines"][-1]["id"]]["end"]) for tk in script["takes"]]
    T = {name.split("_", 1)[1]: (s, e) for name, s, e in takes}
    L = lambda i: seg[i]["start"]

    mus = np.zeros(int(SR * (total + 5)))
    drums = np.zeros_like(mus)

    # drone under everything, with a lift into the climax
    add(mus, 0.0, drone(total), 0.3)
    add(mus, T["climax"][0] - 2, drone(T["climax"][1] - T["climax"][0] + 6, 55.0), 0.35)

    # open: distant taiko heartbeats
    s, e = T["open"]
    tt = s + 0.6
    while tt < e:
        add(drums, tt, taiko(0.9), 0.45); add(drums, tt + 0.38, taiko(0.8), 0.25); tt += 2.6

    # title: roll into a big hit, strings come in
    s, e = T["title"]
    add(drums, s - 2.2, roll(2.2, 0.05, 0.8), 0.5)
    add(drums, s, boom(1.0), 0.9)
    progression = [("Dm", "Bb"), ("F", "C"), ("Dm", "Gm"), ("Bb", "A")]

    def strings(s, e, chords, gain, bright=1400):
        step = (e - s) / len(chords)
        for i, ch in enumerate(chords):
            add(mus, s + i * step, pad([NOTE[n] for n in CHORDS[ch]], step + 0.4, attack=1.2, release=1.8, bright=bright), gain)

    strings(s, e + 0.6, progression[0], 0.32, 1100)

    # world + cast: the march
    for name, chords in (("world", progression[1] + progression[2]), ("cast", progression[3])):
        s, e = T[name]
        strings(s, e + 0.6, chords, 0.34, 1500)
        b = 0; tt = s
        while tt < e + 0.4:
            add(drums, tt, taiko(1.0), 0.55 if b % 4 == 0 else 0.0)
            add(drums, tt, snare(0.6 if b % 2 else 0.35), 0.35)
            add(drums, tt + BEAT / 2, snare(0.25), 0.2)
            if b % 4 == 3:
                add(drums, tt + BEAT * 0.75, snare(0.3), 0.22)
            tt += BEAT; b += 1

    # sacrifice: strings alone, soft and high
    s, e = T["sacrifice"]
    strings(s, e + 1.0, ("Dm", "Bb", "Gm", "A"), 0.3, 900)
    add(mus, s + 0.5, pad([NOTE["A4"], NOTE["D4"]], e - s, attack=3.0, release=2.0, bright=2400, detune=0.002), 0.12)

    # climax: everything, a roll every bar, taiko on every beat
    s, e = T["climax"]
    add(drums, s - 1.8, roll(1.8, 0.1, 1.0), 0.6)
    add(drums, s, boom(1.1), 0.8)
    strings(s, e + 0.8, ("Dm", "Bb", "F", "A"), 0.42, 2600)
    tt = s; b = 0
    while tt < e:
        add(drums, tt, taiko(1.1), 0.7)
        add(drums, tt + BEAT / 2, taiko(0.85), 0.35)
        add(drums, tt, snare(0.8), 0.45)
        if b % 4 == 3:
            add(drums, tt, roll(BEAT, 0.3, 1.0), 0.45)
        tt += BEAT * 0.75; b += 1

    # end: hold, one final hit on the last line, long tail
    s, e = T["end"]
    strings(s, e + 2.5, ("Dm", "Bb", "Dm"), 0.36, 1800)
    add(drums, L(16) - 0.05, boom(1.0), 0.7)
    add(drums, L(18) + 1.2, boom(1.25), 1.0)

    mix = mus + drums
    # section dynamics: quiet open, lift for the title and march, drop for the sacrifice, peak at the climax
    level = {"open": 0.45, "title": 0.75, "world": 0.7, "cast": 0.72, "sacrifice": 0.42, "climax": 1.0, "end": 0.85}
    keys = sorted((s, level[n]) for n, (s, e) in T.items())
    tg = np.arange(len(mix)) / SR
    xs = [0.0] + [k[0] for k in keys]; ys = [keys[0][1]] + [k[1] for k in keys]
    curve = np.interp(tg, xs, ys)
    # smooth the steps over about a second
    kern = np.ones(SR) / SR
    curve = np.convolve(curve[::48], kern[::48] * 48, mode="same")
    curve = np.interp(np.arange(len(mix)), np.arange(0, len(mix), 48)[: len(curve)], curve)
    mix = mix * curve
    mix = mix[: int(SR * total)]
    fade = int(SR * 2.5)
    mix[-fade:] *= np.linspace(1, 0, fade)
    mix = np.tanh(mix / (np.max(np.abs(mix)) + 1e-9) * 1.3) * 0.89
    # gentle stereo: slightly different filters left and right
    left, right = mix, np.roll(lowpass(mix, 9000), 12)
    st = np.stack([left, right], axis=1)
    out = proj / a.out
    out.parent.mkdir(parents=True, exist_ok=True)
    with wave.open(str(out), "wb") as w:
        w.setnchannels(2); w.setsampwidth(2); w.setframerate(SR)
        w.writeframes((np.clip(st, -1, 1) * 32767).astype(np.int16).tobytes())
    print(f"score: {out} ({total:.1f} s)")


if __name__ == "__main__":
    main()
