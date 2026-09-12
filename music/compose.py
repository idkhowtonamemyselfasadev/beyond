#!/usr/bin/env python3
"""
compose.py - procedurally composes the nine ambient tracks for the End
dimension of the Beyond the End mod and encodes them to Ogg Vorbis.

    python3 compose.py              # render all nine tracks (parallel)
    python3 compose.py violet bone  # render only these
    python3 compose.py --keep-wav   # also keep the intermediate WAVs

Every track is deterministic (seeded).  Outputs: <name>.ogg, <name>.png
(spectrogram), stats.json, sounds.json.
"""
import json
import math
import os
import sys
import time
from multiprocessing import Pool

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import synth as S  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))

MODES = {
    "minor": [0, 2, 3, 5, 7, 8, 10],
    "aeolian": [0, 2, 3, 5, 7, 8, 10],
    "harmonic_minor": [0, 2, 3, 5, 7, 8, 11],
    "dorian": [0, 2, 3, 5, 7, 9, 10],
    "phrygian": [0, 1, 3, 5, 7, 8, 10],
    "lydian": [0, 2, 4, 6, 7, 9, 11],
    "major": [0, 2, 4, 5, 7, 9, 11],
}


# ----------------------------------------------------------------------------
# music theory helpers
# ----------------------------------------------------------------------------
def deg_to_midi(root, mode, degree):
    octave, d = divmod(int(degree), 7)
    return root + mode[d] + 12 * octave


def chord_tones(root, mode, degree, size=4):
    """Stacked thirds on a scale degree (tertian chords inside the mode)."""
    return [deg_to_midi(root, mode, degree + 2 * i) for i in range(size)]


def voice_chord(tones, low, high):
    """Spread chord tones into [low, high] midi, avoiding muddy low thirds."""
    out = []
    for i, t in enumerate(tones):
        while t < low:
            t += 12
        while t > high:
            t -= 12
        out.append(t)
    out = sorted(set(out))
    return out


def nearest_scale_degree(root, mode, midi):
    best, bd = 0, 1e9
    for d in range(-21, 35):
        m = deg_to_midi(root, mode, d)
        if abs(m - midi) < bd:
            bd, best = abs(m - midi), d
    return best


def snap_to_chord(midi, tones):
    cands = [t + 12 * k for t in tones for k in range(-4, 5)]
    return min(cands, key=lambda c: abs(c - midi))


# ----------------------------------------------------------------------------
# note renderers (all return stereo arrays)
# ----------------------------------------------------------------------------
def pad_note(freq, dur, rng, kind="saw", voices=5, detune=8.0, cutoff=(300, 900),
             attack=3.0, release=4.0, sine_mix=0.3, lfo_depth=0.2, drift=0.002):
    n = S.seconds(dur + release)
    l, r = S.unison(kind, freq, n, rng, voices=voices, detune_cents=detune, drift=drift)
    t = S.tvec(n)
    c0, c1 = cutoff
    cut = np.geomspace(max(c0, 40), max(c1, 40), n)
    cut *= 1.0 + lfo_depth * np.sin(S.TWO_PI * rng.uniform(0.03, 0.08) * t + rng.uniform(0, 6))
    l = S.lowpass(l, cut, order=1.5)
    r = S.lowpass(r, cut, order=1.5)
    if sine_mix > 0:
        s = S.sine(freq * S.drift_lfo(n, rng, 0.07, drift), n, rng.uniform(0, 1)) * sine_mix
        l = l + s
        r = r + s
    env = S.adsr(n, attack, 0.0, 1.0, release, curve=2.0)
    return np.stack([l, r], axis=1) * env[:, None]


def choir_note(freq, dur, rng, attack=2.5, release=3.5, voices=6):
    """Saw unison through vowel formants: an 'ahh/ooh' choir pad."""
    n = S.seconds(dur + release)
    l, r = S.unison("saw", freq, n, rng, voices=voices, detune_cents=12.0, drift=0.004)
    peaks = [(500, 90, 1.0), (900, 120, 0.7), (2300, 250, 0.35), (3200, 300, 0.15)]
    l = S.formant(l, [p[0] for p in peaks], [p[1] for p in peaks], [p[2] for p in peaks])
    r = S.formant(r, [p[0] for p in peaks], [p[1] for p in peaks], [p[2] for p in peaks])
    l = S.lowpass(l, 3500, order=2.0)
    r = S.lowpass(r, 3500, order=2.0)
    env = S.adsr(n, attack, 0.0, 1.0, release)
    return np.stack([l, r], axis=1) * env[:, None] * 1.4


def bell_note(freq, dur, rng, decay=5.0, inharm=1.0, brightness=1.0, pan=0.0,
              detune_cents=0.0):
    n = S.seconds(min(dur + decay * 1.5, decay * 2.2 + 1.0))
    parts = S.bell_partials(decay=decay, inharm=inharm, brightness=brightness)
    x = S.additive(freq, n, parts, rng, detune=1.0)
    if detune_cents:
        x = 0.6 * x + 0.5 * S.additive(freq * 2 ** (detune_cents / 1200.0), n, parts, rng, detune=1.0)
    x *= S.adsr(n, 0.02, 0.0, 1.0, 0.6)
    return S.pan(x, pan)


def fm_note(freq, dur, rng, decay=4.0, ratio=3.5, index=2.0, pan=0.0):
    n = S.seconds(decay * 2.0)
    x = S.fm_bell(freq, n, ratio=ratio, index=index, decay=decay, index_decay=decay * 0.3)
    x *= S.adsr(n, 0.02, 0.0, 1.0, 0.6)
    return S.pan(x, pan)


def pluck_note(freq, dur, rng, decay=2.0, brightness=0.85, damping=0.15, pan=0.0):
    n = S.seconds(decay * 2.5)
    parts = S.pluck_partials(nharm=20, decay=decay, brightness=brightness, damping=damping)
    x = S.additive(freq, n, parts, rng, detune=0.5)
    x *= S.adsr(n, 0.02, 0.0, 1.0, 0.5)
    return S.pan(x, pan) * 0.8


def musicbox_note(freq, dur, rng, decay=2.5, pan=0.0):
    n = S.seconds(decay * 2.5)
    x = S.additive(freq, n, S.musicbox_partials(decay), rng, detune=0.5)
    x *= S.adsr(n, 0.02, 0.0, 1.0, 0.5)
    return S.pan(x, pan)


def whistle_note(freq, dur, rng, pan=0.0, breath=0.12, vib=0.004):
    n = S.seconds(dur + 1.2)
    t = S.tvec(n)
    vib_env = np.clip((t - 0.4) / 1.2, 0, 1)
    f = freq * (1.0 + vib * vib_env * np.sin(S.TWO_PI * rng.uniform(4.5, 5.5) * t))
    f *= S.drift_lfo(n, rng, 0.2, 0.002)
    x = S.sine(f, n) + 0.12 * S.sine(f * 2.0, n)
    if breath > 0:
        nz = S.bandpass(S.noise(n, rng), freq * 0.9, freq * 1.1, order=3.0)
        x += breath * nz / (np.abs(nz).max() + 1e-9) * 2.0
    env = S.adsr(n, 0.5, 0.0, 1.0, 1.0, curve=1.5)
    return S.pan(x * env, pan)


def brass_note(freq, dur, rng, pan=0.0, attack=1.8, release=2.5, cutoff=(500, 2200)):
    n = S.seconds(dur + release)
    l, r = S.unison("saw", freq, n, rng, voices=3, detune_cents=6.0, drift=0.002, spread=0.4)
    env = S.adsr(n, attack, 0.0, 1.0, release, curve=1.5)
    cut = cutoff[0] + (cutoff[1] - cutoff[0]) * env
    l = S.lowpass(l, cut, order=2.0, resonance=0.15)
    r = S.lowpass(r, cut, order=2.0, resonance=0.15)
    st = np.stack([l, r], axis=1) * env[:, None]
    return st if pan == 0 else S.pan(st.mean(axis=1), pan)


def deep_note(freq, dur, rng, pan=0.0):
    n = S.seconds(dur + 3.0)
    x = S.sine(freq * S.drift_lfo(n, rng, 0.1, 0.002), n) + 0.3 * S.sine(freq * 2.0, n, 0.3)
    x *= S.adsr(n, 1.2, 0.0, 1.0, 3.0, curve=1.5)
    return S.pan(x, pan)


def sub_note(freq, dur, rng):
    n = S.seconds(dur)
    x = S.sine(freq, n) + 0.3 * S.sine(freq * 2.0, n, 0.25)
    x *= S.adsr(n, dur * 0.4, 0.0, 1.0, dur * 0.45, curve=1.5)
    return np.stack([x, x], axis=1)


def thump(freq, rng, decay=0.35, drop=1.6):
    n = S.seconds(decay * 3)
    t = S.tvec(n)
    f = freq * (1.0 + (drop - 1.0) * np.exp(-t / 0.06))
    x = S.sine(f, n) * np.exp(-t / decay)
    x += 0.15 * S.sine(f * 2.0, n) * np.exp(-t / (decay * 0.4))
    x *= S.adsr(n, 0.02, 0.0, 1.0, 0.05)
    return np.stack([x, x], axis=1)


MELODY_TIMBRES = {
    "bell": lambda f, d, r, p: bell_note(f, d, r, decay=5.0, inharm=1.0, pan=p),
    "glass": lambda f, d, r, p: bell_note(f, d, r, decay=6.0, inharm=0.25, brightness=1.15, pan=p),
    "icebell": lambda f, d, r, p: bell_note(f, d, r, decay=7.0, inharm=0.6, brightness=1.1, pan=p, detune_cents=14.0),
    "fm": lambda f, d, r, p: fm_note(f, d, r, decay=4.5, ratio=3.5, index=1.8, pan=p),
    "chime": lambda f, d, r, p: fm_note(f, d, r, decay=4.0, ratio=2.0, index=1.2, pan=p),
    "pluck": lambda f, d, r, p: pluck_note(f, d, r, decay=2.6, brightness=0.9, damping=0.12, pan=p),
    "harp": lambda f, d, r, p: pluck_note(f, d, r, decay=3.0, brightness=0.8, damping=0.08, pan=p),
    "musicbox": lambda f, d, r, p: musicbox_note(f, d, r, decay=2.8, pan=p),
    "whistle": lambda f, d, r, p: whistle_note(f, d, r, pan=p),
    "brass": lambda f, d, r, p: brass_note(f, d, r, pan=p),
    "deep": lambda f, d, r, p: deep_note(f, d, r, pan=p),
}


# ----------------------------------------------------------------------------
# melodic material
# ----------------------------------------------------------------------------
def make_motif(rng, length=None):
    """A motif is a list of (scale-step interval from previous note, beats)."""
    length = length or int(rng.integers(3, 6))
    steps = [-3, -2, -1, -1, 0, 1, 1, 2, 2, 3, 4]
    durs = [1, 2, 2, 3, 4]
    motif = []
    for i in range(length):
        step = 0 if i == 0 else int(rng.choice(steps))
        motif.append((step, float(rng.choice(durs))))
    return motif


def transform(motif, how, rng):
    if how == "same":
        return list(motif)
    if how == "invert":
        return [(-s, d) for s, d in motif]
    if how == "retro":
        m = motif[::-1]
        return [(-s, d) for s, d in m]
    if how == "stretch":
        return [(s, d * 2) for s, d in motif]
    if how == "shrink":
        return [(s, max(1.0, d / 2)) for s, d in motif]
    if how == "tail":
        return list(motif[-2:]) + [(int(rng.choice([-1, 1, 2])), 4.0)]
    return list(motif)


# ----------------------------------------------------------------------------
# the track model
# ----------------------------------------------------------------------------
class Track:
    def __init__(self, name, seed, bpm, root, mode, sections, fade=(6.0, 10.0),
                 reverb_pad=None, reverb_wet=None, cavern=None, gains=None,
                 melody_timbre="bell", arp_timbre="glass", pad_kind="saw",
                 pad_voices=5, pad_detune=8.0, pad_attack=3.0, pad_release=4.0,
                 pad_sine=0.3, pad_range=(48, 72), sub_octave=-24, chord_size=4,
                 width=1.3, drive=1.2, rms_target=(-19.5, -15.5), extras=()):
        self.name, self.seed, self.bpm = name, seed, bpm
        self.root, self.mode = root, MODES[mode]
        self.sections = sections
        self.fade = fade
        self.reverb_pad = reverb_pad or dict(room=0.85, damp=0.45, wet=0.45, size=1.5)
        self.reverb_wet = reverb_wet or dict(room=0.92, damp=0.35, wet=1.0, size=2.0, dry=0.5)
        self.cavern = cavern
        self.gains = gains or {}
        self.melody_timbre = melody_timbre
        self.arp_timbre = arp_timbre
        self.pad_kind, self.pad_voices, self.pad_detune = pad_kind, pad_voices, pad_detune
        self.pad_attack, self.pad_release, self.pad_sine = pad_attack, pad_release, pad_sine
        self.pad_range = pad_range
        self.sub_octave = sub_octave
        self.chord_size = chord_size
        self.width, self.drive, self.rms_target = width, drive, rms_target
        self.extras = extras

    # -- timeline --------------------------------------------------------
    def timeline(self):
        beat = 60.0 / self.bpm
        bar = 4 * beat
        t = 0.0
        chords, secs = [], []
        for sec in self.sections:
            cb = sec.get("chord_bars", 2)
            prog = sec["prog"]
            nch = sec["bars"] // cb
            for i in range(nch):
                deg = prog[i % len(prog)]
                chords.append(dict(start=t + i * cb * bar, dur=cb * bar, degree=deg, sec=sec))
            secs.append(dict(start=t, end=t + sec["bars"] * bar, sec=sec))
            t += sec["bars"] * bar
        return chords, secs, t, beat

    def chord_at(self, chords, time):
        for c in chords:
            if c["start"] <= time < c["start"] + c["dur"]:
                return c
        return chords[-1]

    # -- layers ----------------------------------------------------------
    def render_pads(self, mx, chords, rng):
        for c in chords:
            p = c["sec"].get("pad")
            if not p:
                continue
            tones = chord_tones(self.root, self.mode, c["degree"], self.chord_size)
            lo, hi = p.get("range", self.pad_range)
            voiced = voice_chord(tones, lo, hi)
            if p.get("root_double", True):
                voiced = [voiced[0] - 12] + voiced
            for m in voiced:
                if m < 24:
                    continue
                clip = pad_note(S.midi_to_hz(m), c["dur"] + p.get("overlap", 1.5), rng,
                                kind=p.get("kind", self.pad_kind),
                                voices=p.get("voices", self.pad_voices),
                                detune=p.get("detune", self.pad_detune),
                                cutoff=p.get("cutoff", (300, 900)),
                                attack=p.get("attack", self.pad_attack),
                                release=p.get("release", self.pad_release),
                                sine_mix=p.get("sine", self.pad_sine))
                mx.add("pad", clip, c["start"] - rng.uniform(0, 0.4), p.get("level", 1.0) * 0.28)

    def render_choir(self, mx, chords, rng):
        for c in chords:
            p = c["sec"].get("choir")
            if not p:
                continue
            tones = chord_tones(self.root, self.mode, c["degree"], self.chord_size)
            voiced = voice_chord(tones, *p.get("range", (55, 76)))
            for m in voiced:
                clip = choir_note(S.midi_to_hz(m), c["dur"] + 1.0, rng)
                mx.add("pad", clip, c["start"] - rng.uniform(0, 0.3), p.get("level", 1.0) * 0.25)

    def render_sub(self, mx, chords, rng):
        for c in chords:
            p = c["sec"].get("sub")
            if not p or rng.uniform() > p.get("prob", 0.6):
                continue
            m = deg_to_midi(self.root, self.mode, c["degree"]) + self.sub_octave
            while m < 24:
                m += 12
            while m > 40:
                m -= 12
            dur = c["dur"] * rng.uniform(0.8, 1.15)
            mx.add("sub", sub_note(S.midi_to_hz(m), dur, rng), c["start"] + rng.uniform(0, 1.0),
                   p.get("level", 1.0) * 0.55)

    def render_melody(self, mx, chords, secs, beat, rng):
        motif_a = make_motif(rng)
        motif_b = make_motif(rng)
        timbre_fn = MELODY_TIMBRES[self.melody_timbre]
        for s in secs:
            p = s["sec"].get("melody")
            if not p:
                continue
            density = p.get("density", 0.5)
            lo, hi = p.get("register", (72, 88))
            timbre = MELODY_TIMBRES[p["timbre"]] if "timbre" in p else timbre_fn
            level = p.get("level", 1.0)
            stretch = p.get("stretch", 1.0)
            t = s["start"] + rng.uniform(0.0, 4.0) * (1.5 - density)
            cur = (lo + hi) // 2
            while t < s["end"] - 2.0:
                motif = motif_a if rng.uniform() < 0.7 else motif_b
                how = rng.choice(["same", "same", "invert", "retro", "stretch", "tail", "shrink"],
                                 p=[0.35, 0.15, 0.12, 0.1, 0.13, 0.1, 0.05])
                phrase = transform(motif, how, rng)
                c = self.chord_at(chords, t)
                tones = chord_tones(self.root, self.mode, c["degree"], self.chord_size)
                # first note of a phrase: a chord tone near the current register
                cur = snap_to_chord(cur + int(rng.integers(-4, 5)), tones)
                cur = int(np.clip(cur, lo, hi))
                deg = nearest_scale_degree(self.root, self.mode, cur)
                for i, (step, d) in enumerate(phrase):
                    if i > 0:
                        deg += step
                    m = deg_to_midi(self.root, self.mode, deg)
                    if m < lo:
                        deg += 7
                        m += 12
                    if m > hi:
                        deg -= 7
                        m -= 12
                    dur = d * beat * stretch
                    c = self.chord_at(chords, t)
                    tones = chord_tones(self.root, self.mode, c["degree"], self.chord_size)
                    if dur >= 3 * beat or i == len(phrase) - 1:
                        m = snap_to_chord(m, tones)
                    pan = rng.uniform(-0.5, 0.5)
                    vel = level * rng.uniform(0.7, 1.0)
                    mx.add("wet", timbre_fn(S.midi_to_hz(m), dur, rng, pan) if timbre is timbre_fn
                           else timbre(S.midi_to_hz(m), dur, rng, pan), t, vel * 0.62)
                    t += dur
                    cur = m
                    if rng.uniform() > density * 1.2:  # breath inside a phrase
                        t += beat * rng.choice([1, 2])
                # rest between phrases; low density means long silences
                t += beat * rng.uniform(2, 4) * (2.2 - 1.6 * density) + rng.uniform(0, beat)

    def render_arps(self, mx, chords, beat, rng):
        timbre = MELODY_TIMBRES[self.arp_timbre]
        for c in chords:
            p = c["sec"].get("arp")
            if not p:
                continue
            tones = chord_tones(self.root, self.mode, c["degree"], self.chord_size)
            lo, hi = p.get("register", (84, 100))
            notes = voice_chord(tones, lo, hi)
            notes = notes + [n + 12 for n in notes if n + 12 <= hi]
            notes = sorted(set(notes))
            rate = p.get("rate", 0.5) * beat
            pattern = p.get("pattern", "up")
            prob = p.get("prob", 0.6)
            steps = int(c["dur"] / rate)
            k = int(rng.integers(0, len(notes)))
            direction = 1
            for i in range(steps):
                t = c["start"] + i * rate + rng.uniform(-0.01, 0.01)
                if pattern == "up":
                    idx = k % len(notes)
                elif pattern == "updown":
                    idx = k % len(notes)
                    if idx == len(notes) - 1 or (idx == 0 and k > 0):
                        direction = -direction
                elif pattern == "random":
                    idx = int(rng.integers(0, len(notes)))
                else:
                    idx = (k * 2) % len(notes)
                k += direction
                # long silences inside the arp so it sparkles rather than runs
                if rng.uniform() > prob:
                    continue
                m = notes[idx]
                pan = (idx / max(len(notes) - 1, 1)) * 1.4 - 0.7
                lvl = p.get("level", 0.3) * rng.uniform(0.5, 1.0)
                mx.add("wet", timbre(S.midi_to_hz(m), rate, rng, pan), t, lvl * 0.35)

    # -- assembly --------------------------------------------------------
    def render(self, outdir, keep_wav=False):
        t0 = time.time()
        rng = np.random.default_rng(self.seed)
        chords, secs, length, beat = self.timeline()
        length_total = length + 8.0  # reverb tail room
        mx = S.Mixer(length_total)
        self.render_pads(mx, chords, rng)
        self.render_choir(mx, chords, rng)
        self.render_sub(mx, chords, rng)
        self.render_melody(mx, chords, secs, beat, rng)
        self.render_arps(mx, chords, beat, rng)
        for extra in self.extras:
            extra(self, mx, chords, secs, beat, rng)

        rp, rw = dict(self.reverb_pad), dict(self.reverb_wet)
        procs = {
            "pad": lambda x: S.reverb(x, **rp),
            "wet": lambda x: S.reverb(x, **rw),
        }
        if self.cavern:
            ir = S.cavern_ir(rng, **self.cavern)
            procs["wet"] = lambda x: S.reverb(x, **rw) + 0.5 * S.convolve_stereo(x, ir)
        mix = mx.mix(gains=self.gains, processors=procs)
        mix = S.widen(mix, self.width)
        mix = mix[:S.seconds(length)]
        mix = S.master(mix, peak_db=-3.0, rms_target=self.rms_target, drive=self.drive)
        mix = S.raised_cos_fade(mix, *self.fade)
        mix = mix / (np.abs(mix).max() + 1e-12) * S.db(-3.0)

        wav = os.path.join(outdir, self.name + ".wav")
        ogg = os.path.join(outdir, self.name + ".ogg")
        S.write_wav(wav, mix)
        S.encode_ogg(wav, ogg, quality=4)
        if not keep_wav:
            os.remove(wav)
        S.spectrogram_png(mix, os.path.join(outdir, self.name + ".png"))
        st = S.stats(mix)
        st["size_bytes"] = os.path.getsize(ogg)
        st["render_seconds"] = round(time.time() - t0, 1)
        return self.name, st


# ----------------------------------------------------------------------------
# extra layers used by some tracks
# ----------------------------------------------------------------------------
def extra_crackle(track, mx, chords, secs, beat, rng):
    """Ember: sparse fire crackles + a slow lava rumble."""
    for s in secs:
        p = s["sec"].get("crackle")
        if not p:
            continue
        dur = s["end"] - s["start"]
        n = S.seconds(dur)
        rate = p.get("rate", 6.0)
        count = int(rate * dur)
        buf = np.zeros((n, 2))
        for _ in range(count):
            pos = int(rng.uniform(0, n - S.seconds(0.05)))
            ln = S.seconds(rng.uniform(0.003, 0.02))
            burst = S.noise(ln, rng) * np.exp(-np.linspace(0, 6, ln))
            burst *= S.adsr(ln, 0.02 * 0.05, 0, 1, 0.02 * 0.05)  # tiny bursts, softened below
            amp = rng.uniform(0.1, 1.0) ** 2
            pan = rng.uniform(-0.8, 0.8)
            buf[pos:pos + ln] += S.pan(burst * amp, pan)
        for ch in range(2):
            buf[:, ch] = S.bandpass(buf[:, ch], 600, 5000, order=2.0)
        buf *= S.adsr(n, 4.0, 0, 1, 4.0)[:, None]
        mx.add("wet", buf, s["start"], p.get("level", 0.35) * 0.5)
        # rumble: brown noise below 120 Hz, slowly breathing
        br = np.cumsum(S.noise(n, rng))
        br = S.highpass(br, 25, order=2.0)
        br = S.lowpass(br, 110, order=2.0)
        br /= np.abs(br).max() + 1e-9
        t = S.tvec(n)
        breath = 0.6 + 0.4 * np.sin(S.TWO_PI * 0.05 * t + rng.uniform(0, 6))
        br *= breath * S.adsr(n, 5.0, 0, 1, 5.0)
        mx.add("sub", np.stack([br, br], axis=1), s["start"], p.get("rumble", 0.5) * 0.5)


def extra_wind(track, mx, chords, secs, beat, rng):
    """Bone: a dry, thin wind of band-passed noise with a wandering centre."""
    for s in secs:
        p = s["sec"].get("wind")
        if not p:
            continue
        dur = s["end"] - s["start"]
        n = S.seconds(dur)
        t = S.tvec(n)
        out = np.zeros((n, 2))
        for ch in range(2):
            w = S.noise(n, rng)
            centre = 900 * 2 ** (0.8 * np.sin(S.TWO_PI * 0.02 * t + rng.uniform(0, 6)))
            w = S.lowpass(w, centre * 1.3, order=3.0)
            w = S.highpass(w, 300, order=3.0)
            w /= np.abs(w).max() + 1e-9
            gust = 0.5 + 0.5 * np.sin(S.TWO_PI * 0.035 * t + rng.uniform(0, 6))
            out[:, ch] = w * gust ** 2
        out *= S.adsr(n, 6.0, 0, 1, 6.0)[:, None]
        mx.add("dry", out, s["start"], p.get("level", 0.3) * 0.25)


def extra_sonar(track, mx, chords, secs, beat, rng):
    """Abyssal: rare high pings lost in the deep."""
    for s in secs:
        p = s["sec"].get("sonar")
        if not p:
            continue
        t = s["start"] + rng.uniform(2, 8)
        while t < s["end"] - 2:
            m = deg_to_midi(track.root, track.mode, int(rng.choice([0, 4, 7, 11])) + 28)
            clip = fm_note(S.midi_to_hz(m), 1.0, rng, decay=2.5, ratio=1.0, index=0.3,
                           pan=rng.uniform(-0.6, 0.6))
            mx.add("wet", clip, t, p.get("level", 0.3) * 0.5)
            t += rng.uniform(9, 18)


def extra_shimmer(track, mx, chords, secs, beat, rng):
    """Glacial/violet: a very high, slow detuned sine halo two octaves up."""
    for c in chords:
        p = c["sec"].get("shimmer")
        if not p:
            continue
        tones = chord_tones(track.root, track.mode, c["degree"], 3)
        for m in voice_chord(tones, 84, 96):
            n = S.seconds(c["dur"] + 4.0)
            l, r = S.unison("sine", S.midi_to_hz(m), n, rng, voices=3, detune_cents=10.0, drift=0.004)
            env = S.adsr(n, 4.0, 0, 1, 4.0)
            mx.add("wet", np.stack([l, r], axis=1) * env[:, None], c["start"], p.get("level", 0.2) * 0.2)


def extra_boss(track, mx, chords, secs, beat, rng):
    """Hollow King: deep pulse, heavy riff, rising tension line, final hit."""
    bar = 4 * beat
    for s in secs:
        sec = s["sec"]
        pl = sec.get("pulse")
        if pl:
            t = s["start"]
            i = 0
            while t < s["end"] - 0.1:
                accent = 1.0 if i % 2 == 0 else pl.get("offbeat", 0.55)
                if rng.uniform() < pl.get("prob", 1.0):
                    mx.add("sub", thump(pl.get("freq", 48.0), rng, decay=pl.get("decay", 0.35)), t,
                           pl.get("level", 1.0) * 0.9 * accent)
                t += beat * pl.get("div", 0.5)
                i += 1
        rf = sec.get("riff")
        if rf:
            riff = rf.get("notes", [(0, 1.5), (0, 0.5), (3, 1.0), (2, 1.0), (0, 1.5), (0, 0.5), (-1, 2.0)])
            t = s["start"]
            while t < s["end"] - 0.1:
                for step, beats in riff:
                    if t >= s["end"] - 0.1:
                        break
                    m = deg_to_midi(track.root, track.mode, step) + rf.get("octave", -12)
                    dur = beats * beat
                    n = S.seconds(dur + 0.4)
                    l, r = S.unison("saw", S.midi_to_hz(m), n, rng, voices=4, detune_cents=10, spread=0.6)
                    env = S.adsr(n, 0.03, 0.2, 0.7, 0.35)
                    cut = rf.get("cutoff", 900) * (0.5 + env)
                    l = S.saturate(S.lowpass(l, cut, order=2.0, resonance=0.2), 2.5)
                    r = S.saturate(S.lowpass(r, cut, order=2.0, resonance=0.2), 2.5)
                    mx.add("dry", np.stack([l, r], axis=1) * env[:, None], t, rf.get("level", 1.0) * 0.45)
                    t += dur
        tl = sec.get("tension")
        if tl:
            # a slowly rising high string line: chromatic-ish creep through the scale
            n = S.seconds(s["end"] - s["start"] + 3.0)
            t = S.tvec(n)
            m0 = tl.get("start_midi", 69)
            semis = tl.get("rise", 5) * np.clip(t / (s["end"] - s["start"]), 0, 1)
            f = S.midi_to_hz(m0) * 2 ** (semis / 12.0)
            l, r = S.unison("saw", float(f[0]), 8, rng)  # warm the tables
            fa = f * S.drift_lfo(n, rng, 0.3, 0.003)
            tab = S.get_table("saw", float(f.max()))
            l = S.osc_table(tab, fa * 2 ** (-6 / 1200), n, 0.0)
            r = S.osc_table(tab, fa * 2 ** (6 / 1200), n, 0.5)
            trem = 1.0 - 0.35 * (0.5 + 0.5 * np.sin(S.TWO_PI * 6.5 * t))
            l = S.lowpass(l, 2600, order=2.0) * trem
            r = S.lowpass(r, 2600, order=2.0) * trem
            env = S.adsr(n, 3.0, 0, 1, 3.0)
            mx.add("wet", np.stack([l, r], axis=1) * env[:, None], s["start"], tl.get("level", 0.25) * 0.3)
        hit = sec.get("hit")
        if hit:
            t = s["start"] + hit.get("at", 0.0)
            mx.add("sub", thump(40.0, rng, decay=1.2, drop=2.5), t, 1.2)
            tones = chord_tones(track.root, track.mode, 0, 3)
            for m in voice_chord(tones, 45, 64):
                clip = pad_note(S.midi_to_hz(m), 5.0, rng, kind="saw", voices=7, detune=14,
                                cutoff=(2500, 300), attack=0.03, release=6.0, sine_mix=0.4)
                mx.add("pad", clip, t, 0.35)


# ----------------------------------------------------------------------------
# the nine tracks
# ----------------------------------------------------------------------------
def build_tracks():
    T = {}

    # violet: hollow, purple, drifting, D minor, glassy bells ---------------
    pad = dict(cutoff=(320, 800), level=1.0)
    T["violet"] = Track(
        "violet", seed=101, bpm=58, root=50, mode="minor", melody_timbre="glass", arp_timbre="glass",
        pad_kind="saw", pad_voices=5, pad_detune=9.0, pad_range=(50, 71), width=1.35,
        reverb_pad=dict(room=0.88, damp=0.45, wet=0.5, size=1.7),
        reverb_wet=dict(room=0.94, damp=0.3, wet=1.1, size=2.2, dry=0.45),
        cavern=dict(length=7.0),
        fade=(8.0, 12.0), extras=(extra_shimmer,),
        sections=[
            dict(bars=8, prog=[0, 5], pad=dict(pad, cutoff=(250, 600)), sub=dict(prob=0.5, level=0.8)),
            dict(bars=8, prog=[0, 5, 2, 6], pad=pad, melody=dict(density=0.45, register=(74, 89), level=0.9),
                 sub=dict(prob=0.6)),
            dict(bars=8, prog=[0, 3, 5, 4], pad=dict(pad, cutoff=(400, 1100)),
                 melody=dict(density=0.55, register=(74, 91)), arp=dict(level=0.3, rate=0.5, prob=0.45, pattern="up"),
                 shimmer=dict(level=0.25), sub=dict(prob=0.7)),
            dict(bars=8, prog=[5, 2, 6, 0], pad=dict(pad, cutoff=(500, 900)), melody=dict(density=0.4, register=(72, 86)),
                 arp=dict(level=0.22, rate=0.25, prob=0.35, pattern="random"), shimmer=dict(level=0.2), sub=dict(prob=0.6)),
            dict(bars=7, prog=[0, 5, 0], chord_bars=2, pad=dict(pad, cutoff=(450, 300)),
                 melody=dict(density=0.3, register=(74, 86)), shimmer=dict(level=0.15), sub=dict(prob=0.8)),
        ])

    # verdigris: mossy, warm, E dorian, plucked-string tones -----------------
    pad = dict(cutoff=(600, 1600), level=0.8, kind="soft", voices=4, detune=7.0)
    T["verdigris"] = Track(
        "verdigris", seed=202, bpm=62, root=52, mode="dorian", melody_timbre="pluck", arp_timbre="harp",
        pad_kind="soft", pad_range=(52, 74), pad_sine=0.45, width=1.25,
        reverb_pad=dict(room=0.85, damp=0.55, wet=0.4, size=1.4),
        reverb_wet=dict(room=0.9, damp=0.5, wet=0.9, size=1.6, dry=0.7),
        fade=(6.0, 10.0),
        sections=[
            dict(bars=8, prog=[0, 3], pad=dict(pad, cutoff=(400, 900)), melody=dict(density=0.35, register=(64, 79), level=1.0),
                 sub=dict(prob=0.5, level=0.7)),
            dict(bars=8, prog=[0, 3, 1, 6], pad=pad, melody=dict(density=0.55, register=(64, 81)),
                 arp=dict(level=0.3, rate=0.5, prob=0.5, register=(76, 91), pattern="updown"), sub=dict(prob=0.5)),
            dict(bars=8, prog=[5, 3, 0, 4], pad=dict(pad, cutoff=(700, 1900)), melody=dict(density=0.6, register=(67, 83), level=1.1),
                 arp=dict(level=0.45, rate=0.25, prob=0.4, register=(79, 93), pattern="up"), sub=dict(prob=0.6)),
            dict(bars=8, prog=[0, 1, 3, 6], pad=pad, melody=dict(density=0.45, register=(64, 79)),
                 arp=dict(level=0.25, rate=0.5, prob=0.5, register=(76, 91), pattern="updown"), sub=dict(prob=0.5)),
            dict(bars=6, prog=[0, 3, 0], pad=dict(pad, cutoff=(400, 300)), melody=dict(density=0.3, register=(64, 76)),
                 sub=dict(prob=0.8)),
        ])

    # ember: hot, crackling drones, C phrygian, brass swells -----------------
    pad = dict(cutoff=(260, 650), level=1.0, kind="saw", voices=6, detune=12.0, range=(36, 58))
    T["ember"] = Track(
        "ember", seed=303, bpm=54, root=48, mode="phrygian", melody_timbre="brass", arp_timbre="fm",
        pad_range=(36, 58), pad_sine=0.3, pad_attack=4.0, pad_release=5.0, chord_size=3, width=1.2, drive=1.6,
        reverb_pad=dict(room=0.8, damp=0.6, wet=0.35, size=1.3),
        reverb_wet=dict(room=0.88, damp=0.55, wet=0.8, size=1.8, dry=0.7),
        fade=(7.0, 11.0), extras=(extra_crackle,),
        sections=[
            dict(bars=7, prog=[0], pad=dict(pad, cutoff=(150, 350)), crackle=dict(rate=5, level=0.3, rumble=0.35),
                 sub=dict(prob=0.9, level=0.5)),
            dict(bars=8, prog=[0, 1], pad=pad, crackle=dict(rate=7, level=0.35, rumble=0.5),
                 melody=dict(density=0.35, register=(55, 67), level=1.2, stretch=1.6), sub=dict(prob=0.7, level=0.5)),
            dict(bars=8, prog=[0, 5, 1, 0], pad=dict(pad, cutoff=(300, 900)), crackle=dict(rate=9, level=0.4, rumble=0.5),
                 melody=dict(density=0.5, register=(57, 70), level=1.3, stretch=1.4), arp=dict(level=0.2, rate=1.0, prob=0.3, register=(72, 86)),
                 sub=dict(prob=0.8, level=0.5)),
            dict(bars=8, prog=[3, 1, 0, 6], pad=dict(pad, cutoff=(350, 700)), crackle=dict(rate=8, level=0.35, rumble=0.5),
                 melody=dict(density=0.45, register=(55, 69), level=1.3, stretch=1.5), sub=dict(prob=0.8, level=0.5)),
            dict(bars=6, prog=[0, 1, 0], pad=dict(pad, cutoff=(300, 150)), crackle=dict(rate=4, level=0.25, rumble=0.35),
                 sub=dict(prob=1.0, level=0.5)),
        ])

    # bone: dry, sparse, desolate, A minor, thin whistles --------------------
    pad = dict(cutoff=(600, 1400), level=0.45, kind="sine", voices=3, detune=6.0, range=(57, 76), root_double=False)
    T["bone"] = Track(
        "bone", seed=404, bpm=52, root=57, mode="minor", melody_timbre="whistle", arp_timbre="glass",
        pad_range=(57, 76), pad_sine=0.0, pad_attack=5.0, pad_release=6.0, chord_size=3, width=1.15,
        reverb_pad=dict(room=0.7, damp=0.5, wet=0.25, size=1.0),
        reverb_wet=dict(room=0.75, damp=0.5, wet=0.4, size=1.1, dry=0.9),
        gains=dict(dry=1.0), rms_target=(-20.0, -16.5),
        fade=(7.0, 12.0), extras=(extra_wind,),
        sections=[
            dict(bars=7, prog=[0], chord_bars=7, pad=dict(pad, level=0.3), wind=dict(level=0.35),
                 melody=dict(density=0.2, register=(81, 93), level=0.7)),
            dict(bars=8, prog=[0, 5], chord_bars=4, pad=pad, wind=dict(level=0.3),
                 melody=dict(density=0.3, register=(81, 95), level=0.8), sub=dict(prob=0.5, level=0.8)),
            dict(bars=8, prog=[3, 0], chord_bars=4, pad=dict(pad, level=0.5), wind=dict(level=0.25),
                 melody=dict(density=0.35, register=(79, 93)), arp=dict(level=0.15, rate=1.0, prob=0.2, register=(88, 100), pattern="random"),
                 sub=dict(prob=0.5, level=0.8)),
            dict(bars=8, prog=[5, 6, 0, 0], chord_bars=2, pad=dict(pad, level=0.4), wind=dict(level=0.3),
                 melody=dict(density=0.25, register=(81, 95))),
            dict(bars=7, prog=[0], chord_bars=7, pad=dict(pad, level=0.3, cutoff=(800, 400)), wind=dict(level=0.35),
                 melody=dict(density=0.15, register=(81, 93), level=0.6)),
        ])

    # abyssal: deep, underwater, sub heavy, G lydian, very slow -------------
    pad = dict(cutoff=(160, 420), level=1.0, kind="saw", voices=6, detune=10.0, range=(43, 64))
    T["abyssal"] = Track(
        "abyssal", seed=505, bpm=48, root=43, mode="lydian", melody_timbre="deep", arp_timbre="chime",
        pad_range=(43, 64), pad_sine=0.6, pad_attack=5.0, pad_release=6.0, sub_octave=-12, width=1.2,
        reverb_pad=dict(room=0.9, damp=0.7, wet=0.5, size=2.2),
        reverb_wet=dict(room=0.95, damp=0.6, wet=1.2, size=2.6, dry=0.4),
        cavern=dict(length=8.0, tilt=1.2),
        fade=(9.0, 12.0), extras=(extra_sonar,),
        sections=[
            dict(bars=6, prog=[0], chord_bars=3, pad=dict(pad, cutoff=(140, 340)), sub=dict(prob=1.0, level=0.7), sonar=dict(level=0.25)),
            dict(bars=8, prog=[0, 1], chord_bars=4, pad=pad, sub=dict(prob=0.9, level=0.7), melody=dict(density=0.35, register=(52, 66), level=1.2, stretch=1.8),
                 sonar=dict(level=0.3)),
            dict(bars=8, prog=[4, 0, 1, 0], chord_bars=2, pad=dict(pad, cutoff=(240, 700)), sub=dict(prob=0.9, level=0.7),
                 melody=dict(density=0.45, register=(55, 69), level=1.3, stretch=1.6), arp=dict(level=0.12, rate=1.0, prob=0.25, register=(79, 93), pattern="random"),
                 sonar=dict(level=0.3)),
            dict(bars=8, prog=[5, 1, 0, 0], chord_bars=2, pad=dict(pad, cutoff=(200, 500)), sub=dict(prob=1.0, level=0.7),
                 melody=dict(density=0.35, register=(52, 66), level=1.2, stretch=1.8), sonar=dict(level=0.25)),
            dict(bars=6, prog=[0], chord_bars=3, pad=dict(pad, cutoff=(220, 110)), sub=dict(prob=1.0, level=0.7)),
        ])

    # gilded: bright, golden, C lydian, chimes and harp arps -----------------
    pad = dict(cutoff=(700, 2000), level=0.85, kind="saw", voices=5, detune=7.0, range=(55, 79))
    T["gilded"] = Track(
        "gilded", seed=606, bpm=64, root=60, mode="lydian", melody_timbre="chime", arp_timbre="harp",
        pad_range=(55, 79), pad_sine=0.25, width=1.35,
        reverb_pad=dict(room=0.85, damp=0.35, wet=0.45, size=1.5),
        reverb_wet=dict(room=0.92, damp=0.25, wet=1.0, size=2.0, dry=0.6),
        fade=(6.0, 10.0),
        sections=[
            dict(bars=8, prog=[0, 1], pad=dict(pad, cutoff=(500, 1200)), melody=dict(density=0.4, register=(76, 91), level=0.8), sub=dict(prob=0.4, level=0.6)),
            dict(bars=8, prog=[0, 1, 4, 0], pad=pad, melody=dict(density=0.5, register=(76, 93)),
                 arp=dict(level=0.4, rate=0.5, prob=0.6, register=(79, 96), pattern="up"), sub=dict(prob=0.5, level=0.6)),
            dict(bars=8, prog=[2, 1, 0, 5], pad=dict(pad, cutoff=(900, 2400)), melody=dict(density=0.55, register=(79, 95)),
                 arp=dict(level=0.45, rate=0.25, prob=0.5, register=(81, 98), pattern="updown"), sub=dict(prob=0.5, level=0.6)),
            dict(bars=8, prog=[0, 4, 1, 0], pad=pad, melody=dict(density=0.45, register=(76, 91)),
                 arp=dict(level=0.35, rate=0.5, prob=0.55, register=(79, 96), pattern="up"), sub=dict(prob=0.5, level=0.6)),
            dict(bars=6, prog=[1, 0, 0], pad=dict(pad, cutoff=(900, 500)), melody=dict(density=0.3, register=(76, 91)),
                 arp=dict(level=0.2, rate=0.5, prob=0.35, register=(79, 96), pattern="random"), sub=dict(prob=0.7, level=0.6)),
        ])

    # roseate: soft, pink, music box over pads, G major ----------------------
    pad = dict(cutoff=(550, 1400), level=0.8, kind="soft", voices=4, detune=6.0, range=(55, 76))
    T["roseate"] = Track(
        "roseate", seed=707, bpm=60, root=55, mode="major", melody_timbre="musicbox", arp_timbre="musicbox",
        pad_kind="soft", pad_range=(55, 76), pad_sine=0.5, width=1.25,
        reverb_pad=dict(room=0.85, damp=0.5, wet=0.45, size=1.5),
        reverb_wet=dict(room=0.9, damp=0.4, wet=0.9, size=1.7, dry=0.7),
        fade=(6.0, 10.0),
        sections=[
            dict(bars=8, prog=[0, 5, 3, 4], pad=dict(pad, cutoff=(400, 900)), melody=dict(density=0.45, register=(79, 93), level=1.0), sub=dict(prob=0.4, level=0.6)),
            dict(bars=8, prog=[0, 4, 5, 3], pad=pad, melody=dict(density=0.6, register=(79, 95), level=1.1),
                 arp=dict(level=0.35, rate=0.5, prob=0.45, register=(84, 98), pattern="up"), sub=dict(prob=0.5, level=0.6)),
            dict(bars=8, prog=[3, 4, 0, 5], pad=dict(pad, cutoff=(700, 1800)), melody=dict(density=0.65, register=(81, 96), level=1.2),
                 arp=dict(level=0.4, rate=0.5, prob=0.5, register=(84, 98), pattern="updown"), sub=dict(prob=0.5, level=0.6)),
            dict(bars=8, prog=[0, 5, 3, 4], pad=pad, melody=dict(density=0.5, register=(79, 93), level=1.1),
                 arp=dict(level=0.3, rate=0.5, prob=0.4, register=(84, 98), pattern="random"), sub=dict(prob=0.5, level=0.6)),
            dict(bars=6, prog=[3, 4, 0], pad=dict(pad, cutoff=(500, 300)), melody=dict(density=0.35, register=(79, 93)), sub=dict(prob=0.7, level=0.6)),
        ])

    # glacial: icy, crystalline, E aeolian, high sines + detuned bells -------
    pad = dict(cutoff=(900, 2500), level=0.55, kind="sine", voices=4, detune=9.0, range=(64, 84), root_double=True)
    T["glacial"] = Track(
        "glacial", seed=808, bpm=54, root=52, mode="aeolian", melody_timbre="icebell", arp_timbre="glass",
        pad_range=(64, 84), pad_sine=0.0, pad_attack=5.0, pad_release=6.0, chord_size=3, width=1.4,
        reverb_pad=dict(room=0.9, damp=0.2, wet=0.55, size=2.0),
        reverb_wet=dict(room=0.95, damp=0.15, wet=1.2, size=2.4, dry=0.5),
        cavern=dict(length=8.0, tilt=1.6),
        fade=(8.0, 12.0), extras=(extra_shimmer,),
        sections=[
            dict(bars=7, prog=[0], chord_bars=7, pad=dict(pad, level=0.4), shimmer=dict(level=0.2), melody=dict(density=0.25, register=(76, 91), level=0.8), sub=dict(prob=0.6, level=0.8)),
            dict(bars=8, prog=[0, 5], chord_bars=4, pad=pad, shimmer=dict(level=0.25), melody=dict(density=0.35, register=(76, 93)), sub=dict(prob=0.7, level=0.9)),
            dict(bars=8, prog=[2, 6, 0, 5], chord_bars=2, pad=dict(pad, level=0.6), shimmer=dict(level=0.3), melody=dict(density=0.4, register=(79, 95)),
                 arp=dict(level=0.2, rate=0.5, prob=0.3, register=(88, 103), pattern="random"), sub=dict(prob=0.7, level=0.9)),
            dict(bars=8, prog=[3, 0], chord_bars=4, pad=pad, shimmer=dict(level=0.25), melody=dict(density=0.3, register=(76, 93)),
                 arp=dict(level=0.15, rate=1.0, prob=0.3, register=(88, 103), pattern="random"), sub=dict(prob=0.7, level=0.9)),
            dict(bars=7, prog=[0], chord_bars=7, pad=dict(pad, level=0.4, cutoff=(2000, 800)), shimmer=dict(level=0.2), melody=dict(density=0.2, register=(76, 91)), sub=dict(prob=0.8, level=0.8)),
        ])

    # hollow king: boss theme, A harmonic minor, 90 BPM pulse ----------------
    choir = dict(level=1.0, range=(57, 76))
    T["hollow_king"] = Track(
        "hollow_king", seed=909, bpm=90, root=45, mode="harmonic_minor", melody_timbre="fm", arp_timbre="fm",
        pad_kind="saw", pad_range=(45, 64), pad_sine=0.4, pad_attack=1.5, pad_release=2.0, width=1.25, drive=1.8,
        reverb_pad=dict(room=0.85, damp=0.5, wet=0.4, size=1.6),
        reverb_wet=dict(room=0.9, damp=0.4, wet=0.9, size=1.8, dry=0.6),
        gains=dict(dry=1.0), rms_target=(-17.5, -14.5),
        fade=(2.5, 9.0), extras=(extra_boss,),
        sections=[
            dict(bars=6, prog=[0], chord_bars=2, pad=dict(cutoff=(200, 500), level=0.9, voices=6, detune=12),
                 pulse=dict(level=0.7, div=1.0, decay=0.4, prob=0.85), sub=dict(prob=1.0, level=0.5),
                 tension=dict(start_midi=64, rise=3, level=0.12)),
            dict(bars=8, prog=[0, 5, 3, 4], chord_bars=2, pad=dict(cutoff=(300, 700), level=0.8, voices=6, detune=12),
                 choir=dict(choir, level=0.9), pulse=dict(level=0.6, div=0.5, offbeat=0.5), riff=dict(level=1.2, cutoff=900),
                 melody=dict(density=0.4, register=(69, 84), level=0.9)),
            dict(bars=8, prog=[0, 5, 1, 4], chord_bars=2, pad=dict(cutoff=(400, 1000), level=0.8, voices=6, detune=12),
                 choir=dict(choir, level=1.1), pulse=dict(level=0.6, div=0.5, offbeat=0.6), riff=dict(level=1.3, cutoff=1300),
                 melody=dict(density=0.5, register=(69, 86), level=1.0), tension=dict(start_midi=69, rise=7, level=0.25)),
            dict(bars=8, prog=[3, 4, 0, 4], chord_bars=2, pad=dict(cutoff=(500, 1400), level=0.9, voices=7, detune=14),
                 choir=dict(choir, level=1.3), pulse=dict(level=0.65, div=0.5, offbeat=0.7), riff=dict(level=1.4, cutoff=1900),
                 melody=dict(density=0.55, register=(72, 88), level=1.1), tension=dict(start_midi=72, rise=8, level=0.35),
                 arp=dict(level=0.3, rate=0.25, prob=0.5, register=(81, 96), pattern="up")),
            dict(bars=8, prog=[0, 5, 4, 0], chord_bars=2, pad=dict(cutoff=(600, 400), level=1.0, voices=7, detune=14),
                 choir=dict(choir, level=1.3), pulse=dict(level=0.65, div=0.5, offbeat=0.7), riff=dict(level=1.4, cutoff=1600),
                 tension=dict(start_midi=76, rise=5, level=0.3), hit=dict(at=0.0)),
            dict(bars=8, prog=[0, 0], chord_bars=4, pad=dict(cutoff=(500, 150), level=1.0, voices=7, detune=14),
                 choir=dict(choir, level=0.8), pulse=dict(level=0.6, div=1.0, decay=0.5, prob=0.5), hit=dict(at=0.0)),
        ])
    return T


DESCRIPTIONS = {
    "violet": "D minor, 58 BPM: hollow detuned-saw pads under glassy inharmonic bells, a high sine halo and sparse upward arps; i-VI / i-VI-III-VII.",
    "verdigris": "E dorian, 62 BPM: warm rolled-off pads, plucked-string motifs and harp-like arps over i-IV-ii-VII; mossy and gently moving.",
    "ember": "C phrygian, 54 BPM: low crackling drones with a lava rumble, filtered saw pads and slow brass swells over i-bII-VI.",
    "bone": "A minor, 52 BPM: near-silent sine pads, a thin dry wind and lonely high whistles; long rests, tiny room.",
    "abyssal": "G lydian, 48 BPM: sub-bass swells and dark low-passed pads with deep sine melodies and rare sonar pings in a cavern reverb.",
    "gilded": "C lydian, 64 BPM: bright open pads, FM chimes and quick harp arps over I-II-V-I; golden but slightly wrong.",
    "roseate": "G major, 60 BPM: soft pads with a music-box melody and gentle tine arps over I-vi-IV-V.",
    "glacial": "E aeolian, 54 BPM: high sine pads, detuned ice bells and a sine halo in a bright cavern; very sparse.",
    "hollow_king": "A harmonic minor, 90 BPM: deep pulse, saturated low riff, formant choir pads, rising tremolo tension and a final hit.",
}


def render_one(args):
    name, keep = args
    tr = build_tracks()[name]
    return tr.render(HERE, keep_wav=keep)


def main():
    argv = sys.argv[1:]
    keep = "--keep-wav" in argv
    names = [a for a in argv if not a.startswith("--")]
    tracks = build_tracks()
    names = names or list(tracks)
    with Pool(min(len(names), os.cpu_count() or 1)) as pool:
        results = pool.map(render_one, [(n, keep) for n in names])
    stats_path = os.path.join(HERE, "stats.json")
    allstats = {}
    if os.path.exists(stats_path):
        allstats = json.load(open(stats_path))
    for name, st in results:
        allstats[name] = st
        b = " ".join("%3.0f%%" % (100 * v) for v in st["bands"])
        print("%-12s %5.1fs %6.1f KB  peak %5.1f dB  rms %6.1f dB  slew %.3f  bands[%s]  clip %d  (%ss)" % (
            name, st["seconds"], st["size_bytes"] / 1024, st["peak_db"], st["rms_db"], st["max_slew"], b,
            st["clipped_samples"], st["render_seconds"]))
    json.dump(allstats, open(stats_path, "w"), indent=1)
    sounds = {}
    for name in tracks:
        sounds["music.beyond." + name] = {"sounds": [{"name": "beyond:music/" + name, "stream": True}]}
    json.dump(sounds, open(os.path.join(HERE, "sounds.json"), "w"), indent=2)
    total = sum(os.path.getsize(os.path.join(HERE, n + ".ogg")) for n in tracks
                if os.path.exists(os.path.join(HERE, n + ".ogg")))
    print("total ogg size: %.1f MB" % (total / 1e6))


if __name__ == "__main__":
    main()
