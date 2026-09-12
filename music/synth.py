"""
synth.py - a small numpy-only synthesis library for the Beyond the End music.

Everything here is pure numpy (no scipy):
  * band-limited wavetable oscillators (saw/triangle/square built by additive
    sums, mip-mapped by harmonic count) with detune + drift
  * additive partial synthesis (bells, plucks) with per-partial decay
  * ADSR / exponential envelopes (all attacks/releases >= 20 ms)
  * STFT-based soft low-pass with time-varying cutoff (no IIR loops)
  * Freeverb-style algorithmic reverb (parallel feedback combs + serial
    all-passes, computed block-wise), plus a convolution "cavern" tail
  * mid/side stereo widening, tanh tape-like saturation
  * a master stage: soft limiter + peak normalisation to -3 dBFS
  * wav writer, ffmpeg ogg encoder, stats, and a numpy-only spectrogram PNG
"""
import math
import os
import struct
import subprocess
import zlib

import numpy as np

SR = 44100
TWO_PI = 2.0 * math.pi


# ----------------------------------------------------------------------------
# helpers
# ----------------------------------------------------------------------------
def midi_to_hz(m):
    return 440.0 * 2.0 ** ((np.asarray(m, dtype=float) - 69.0) / 12.0)


def db(x):
    return 10.0 ** (x / 20.0)


def seconds(n):
    return int(round(n * SR))


def tvec(n):
    return np.arange(n, dtype=np.float64) / SR


# ----------------------------------------------------------------------------
# wavetables (band-limited by construction: additive sums of harmonics)
# ----------------------------------------------------------------------------
TABLE_SIZE = 4096
_TABLES = {}


def _build_table(kind, nharm):
    k = np.arange(1, nharm + 1, dtype=np.float64)
    ph = np.arange(TABLE_SIZE) / TABLE_SIZE
    arg = TWO_PI * np.outer(ph, k)
    if kind == "saw":
        amp = 1.0 / k
        tab = (np.sin(arg) * amp).sum(axis=1) * (2.0 / math.pi)
    elif kind == "square":
        amp = np.where(k % 2 == 1, 1.0 / k, 0.0)
        tab = (np.sin(arg) * amp).sum(axis=1) * (4.0 / math.pi)
    elif kind == "triangle":
        amp = np.where(k % 2 == 1, 1.0 / k ** 2, 0.0)
        sign = np.where(((k - 1) // 2) % 2 == 0, 1.0, -1.0)
        tab = (np.sin(arg) * amp * sign).sum(axis=1) * (8.0 / math.pi ** 2)
    elif kind == "soft":  # rolled-off saw: 1/k^1.5, warm and dark
        amp = 1.0 / k ** 1.5
        tab = (np.sin(arg) * amp).sum(axis=1)
        tab /= np.abs(tab).max()
    else:
        raise ValueError(kind)
    return tab.astype(np.float64)


def get_table(kind, freq):
    """Pick the mip level whose highest harmonic stays under ~0.45*SR."""
    max_h = int(0.45 * SR / max(freq, 1.0))
    level = 1
    while level * 2 <= max_h and level < 256:
        level *= 2
    key = (kind, level)
    if key not in _TABLES:
        _TABLES[key] = _build_table(kind, level)
    return _TABLES[key]


def osc_table(table, freq, n, phase0=0.0):
    """Read a wavetable at `freq` (scalar or per-sample array) for n samples."""
    if np.isscalar(freq):
        ph = phase0 + np.arange(n) * (freq / SR)
    else:
        ph = phase0 + np.cumsum(np.asarray(freq, dtype=np.float64)) / SR
    ph = np.mod(ph, 1.0) * TABLE_SIZE
    i0 = ph.astype(np.int64)
    frac = ph - i0
    i1 = (i0 + 1) % TABLE_SIZE
    return table[i0] * (1.0 - frac) + table[i1] * frac


def sine(freq, n, phase0=0.0):
    if np.isscalar(freq):
        ph = phase0 + np.arange(n) * (freq / SR)
    else:
        ph = phase0 + np.cumsum(np.asarray(freq, dtype=np.float64)) / SR
    return np.sin(TWO_PI * ph)


def drift_lfo(n, rng, rate=0.15, depth=0.003):
    """Slow random-ish pitch drift: sum of two slow sines with random phase."""
    t = tvec(n)
    a = np.sin(TWO_PI * rate * t + rng.uniform(0, TWO_PI))
    b = np.sin(TWO_PI * rate * 0.37 * t + rng.uniform(0, TWO_PI))
    return 1.0 + depth * (0.6 * a + 0.4 * b)


def unison(kind, freq, n, rng, voices=5, detune_cents=8.0, drift=0.002,
           spread=1.0, phase_random=True):
    """Detuned multi-voice oscillator, returns (left, right)."""
    left = np.zeros(n)
    right = np.zeros(n)
    if voices == 1:
        offsets = [0.0]
    else:
        offsets = np.linspace(-1.0, 1.0, voices)
    for i, off in enumerate(offsets):
        cents = off * detune_cents + rng.uniform(-0.5, 0.5)
        f = freq * 2.0 ** (cents / 1200.0)
        fa = f * drift_lfo(n, rng, rate=rng.uniform(0.05, 0.2), depth=drift)
        ph0 = rng.uniform(0, 1) if phase_random else 0.0
        if kind == "sine":
            v = sine(fa, n, ph0)
        else:
            v = osc_table(get_table(kind, f), fa, n, ph0)
        pan = 0.5 + 0.5 * off * spread  # 0..1
        left += v * math.cos(pan * math.pi / 2)
        right += v * math.sin(pan * math.pi / 2)
    g = 1.0 / math.sqrt(max(voices, 1))
    return left * g, right * g


# ----------------------------------------------------------------------------
# additive partial synthesis (bells, plucks, glass)
# ----------------------------------------------------------------------------
def additive(freq, n, partials, rng=None, detune=0.0):
    """partials: list of (ratio, amp, decay_seconds). Returns mono."""
    t = tvec(n)
    out = np.zeros(n)
    for ratio, amp, dec in partials:
        f = freq * ratio
        if f >= 0.45 * SR:
            continue
        if rng is not None and detune > 0:
            f *= 2.0 ** (rng.uniform(-detune, detune) / 1200.0)
        ph0 = rng.uniform(0, 1) if rng is not None else 0.0
        out += amp * np.exp(-t / dec) * np.sin(TWO_PI * (f * t + ph0))
    return out


def bell_partials(decay=5.0, inharm=1.0, brightness=1.0):
    """Glassy bell: a few inharmonic partials, the higher ones dying sooner."""
    base = [
        (1.0, 1.0, 1.0),
        (2.0, 0.55, 0.6),
        (2.0 + 0.76 * inharm, 0.35, 0.45),
        (3.0 + 0.5 * inharm, 0.25, 0.35),
        (4.0 + 0.2 * inharm, 0.16, 0.28),
        (5.0 + 0.4 * inharm, 0.10, 0.2),
        (6.0 + 0.8 * inharm, 0.06, 0.16),
    ]
    return [(r, a * (brightness ** (i * 0.5)), decay * d)
            for i, (r, a, d) in enumerate(base)]


def pluck_partials(nharm=24, decay=1.8, brightness=1.0, damping=0.12):
    """Harmonic string-like spectrum; harmonic k decays k*damping faster."""
    out = []
    for k in range(1, nharm + 1):
        amp = brightness ** (k - 1) / k
        out.append((float(k), amp, decay / (1.0 + damping * (k - 1))))
    return out


def musicbox_partials(decay=2.5):
    """Music box tine: strong fundamental, a bright ~4x partial, a faint 9x."""
    base = [(1.0, 1.0, 1.0), (3.9, 0.35, 0.5), (8.8, 0.12, 0.3), (2.0, 0.15, 0.7)]
    return [(r, a, decay * d) for r, a, d in base]


def fm_bell(freq, n, ratio=3.5, index=2.0, decay=4.0, index_decay=1.2):
    """Classic FM bell: modulator index decays faster than the carrier."""
    t = tvec(n)
    mod = np.sin(TWO_PI * freq * ratio * t) * index * np.exp(-t / index_decay)
    return np.sin(TWO_PI * freq * t + mod) * np.exp(-t / decay)


# ----------------------------------------------------------------------------
# envelopes
# ----------------------------------------------------------------------------
def adsr(n, a=0.02, d=0.0, s=1.0, r=0.05, curve=2.0):
    """ADSR over n samples; release occupies the last r seconds. Always >= 20 ms
    attack and release to avoid clicks."""
    a = max(a, 0.02)
    r = max(r, 0.02)
    na, nd, nr = seconds(a), seconds(d), seconds(r)
    if na + nd + nr > n:
        scale = n / float(na + nd + nr + 1)
        na, nd, nr = int(na * scale), int(nd * scale), int(nr * scale)
    ns = max(n - na - nd - nr, 0)
    env = np.empty(n)
    x = np.linspace(0, 1, na, endpoint=False)
    env[:na] = 1 - (1 - x) ** curve
    x = np.linspace(0, 1, nd, endpoint=False)
    env[na:na + nd] = 1 - (1 - s) * x
    env[na + nd:na + nd + ns] = s
    x = np.linspace(0, 1, nr, endpoint=True)
    env[na + nd + ns:] = s * (1 - x) ** curve
    return env


def swell(n, a, r, curve=2.0, hold=None):
    """Smooth attack/hold/release; hold fills what is left."""
    return adsr(n, a=a, d=0.0, s=1.0, r=r, curve=curve)


def raised_cos_fade(x, fade_in_s, fade_out_s):
    x = x.copy()
    n = x.shape[0]
    ni, no = min(seconds(fade_in_s), n), min(seconds(fade_out_s), n)
    if ni > 0:
        w = 0.5 - 0.5 * np.cos(np.linspace(0, math.pi, ni))
        x[:ni] *= w[:, None] if x.ndim == 2 else w
    if no > 0:
        w = 0.5 + 0.5 * np.cos(np.linspace(0, math.pi, no))
        x[n - no:] *= w[:, None] if x.ndim == 2 else w
    return x


# ----------------------------------------------------------------------------
# STFT filter (soft low-pass / band-pass with time-varying cutoff)
# ----------------------------------------------------------------------------
_FRAME = 4096
_HOP = 1024
_WIN = np.hanning(_FRAME + 1)[:-1]
_FREQS = np.fft.rfftfreq(_FRAME, 1.0 / SR)


def _stft_frames(x):
    n = len(x)
    pad = _FRAME
    xp = np.concatenate([np.zeros(pad), x, np.zeros(pad + _HOP)])
    nfr = 1 + (len(xp) - _FRAME) // _HOP
    idx = np.arange(_FRAME)[None, :] + _HOP * np.arange(nfr)[:, None]
    frames = xp[idx] * _WIN
    return np.fft.rfft(frames, axis=1), nfr, n, pad


def _istft(spec, nfr, n, pad):
    frames = np.fft.irfft(spec, axis=1) * _WIN
    out = np.zeros(pad + n + pad + _HOP + _FRAME)
    for i in range(nfr):
        s = i * _HOP
        out[s:s + _FRAME] += frames[i]
    # hann^2 overlap-add at hop=frame/4 sums to 1.5
    return out[pad:pad + n] / 1.5


def lowpass(x, cutoff, order=2.0, resonance=0.0):
    """Soft low-pass. cutoff may be a scalar or per-sample array (Hz).
    Magnitude response is butterworth-like: 1/sqrt(1+(f/fc)^(2*order)),
    with an optional gentle resonant bump at the cutoff."""
    spec, nfr, n, pad = _stft_frames(x)
    if np.isscalar(cutoff):
        fc = np.full(nfr, float(cutoff))
    else:
        centers = np.clip(np.arange(nfr) * _HOP - pad + _FRAME // 2, 0, n - 1)
        fc = np.asarray(cutoff)[centers]
    fc = np.maximum(fc, 20.0)
    ratio = _FREQS[None, :] / fc[:, None]
    mag = 1.0 / np.sqrt(1.0 + ratio ** (2.0 * order))
    if resonance > 0:
        mag += resonance * np.exp(-((np.log2(np.maximum(ratio, 1e-6))) ** 2) * 8.0)
    return _istft(spec * mag, nfr, n, pad)


def highpass(x, cutoff, order=2.0):
    spec, nfr, n, pad = _stft_frames(x)
    ratio = np.maximum(_FREQS, 1e-3) / float(cutoff)
    mag = 1.0 / np.sqrt(1.0 + ratio ** (-2.0 * order))
    return _istft(spec * mag[None, :], nfr, n, pad)


def bandpass(x, lo, hi, order=2.0):
    return highpass(lowpass(x, hi, order), lo, order)


def formant(x, peaks, widths, gains):
    """Fixed multi-peak (vocal formant) filter for choir-like pads."""
    spec, nfr, n, pad = _stft_frames(x)
    mag = np.zeros_like(_FREQS)
    for p, w, g in zip(peaks, widths, gains):
        mag += g * np.exp(-0.5 * ((_FREQS - p) / w) ** 2)
    mag += 0.05
    return _istft(spec * mag[None, :], nfr, n, pad)


def noise(n, rng):
    return rng.standard_normal(n)


# ----------------------------------------------------------------------------
# reverb: Freeverb-style network, block-wise (delay length = block length)
# ----------------------------------------------------------------------------
_COMBS = [1116, 1188, 1277, 1356, 1422, 1491, 1557, 1617]
_ALLPASS = [556, 441, 341, 225]
_STEREO_SPREAD = 23


def _damp_kernel(damp):
    L = 1 + 2 * int(round(damp * 5))
    if L <= 1:
        return np.array([1.0])
    k = np.hanning(L + 2)[1:-1]
    return k / k.sum()


def _comb(x, D, g, kernel):
    n = len(x)
    h = len(kernel) // 2
    off = D + h + 1
    out = np.zeros(n + off)
    for s in range(0, n, D):
        e = min(s + D, n)
        seg = out[s + off - D - h: e + off - D + h]
        fb = np.convolve(seg, kernel, mode="valid") if h else seg
        out[s + off:e + off] = x[s:e] + g * fb
    return out[off:]


def _allpass(x, D, g=0.5):
    n = len(x)
    out = np.zeros(n + D)
    xp = np.concatenate([np.zeros(D), x])
    for s in range(0, n, D):
        e = min(s + D, n)
        out[s + D:e + D] = -g * x[s:e] + xp[s:e] + g * out[s:e]
    return out[D:]


def _reverb_channel(x, delays_c, delays_a, g, kernel):
    acc = np.zeros(len(x))
    for D in delays_c:
        acc += _comb(x, D, g, kernel)
    acc /= len(delays_c)
    for D in delays_a:
        acc = _allpass(acc, D, 0.5)
    return acc


def reverb(stereo, room=0.85, damp=0.4, wet=0.35, dry=1.0, size=1.0,
           predelay=0.02, width=1.0):
    """Freeverb-like. `size` scales the delay lines (2-3 = cavern),
    `room` is the comb feedback (0.7..0.97)."""
    x = np.asarray(stereo)
    if x.ndim == 1:
        x = np.stack([x, x], axis=1)
    n = x.shape[0]
    kernel = _damp_kernel(damp)
    g = float(np.clip(room, 0.0, 0.985))
    pre = seconds(predelay)
    src = np.concatenate([np.zeros((pre, 2)), x])[:n]
    mono_in = 0.5 * (src[:, 0] + src[:, 1])
    cl = [int(d * size) for d in _COMBS]
    cr = [int(d * size) + _STEREO_SPREAD for d in _COMBS]
    al = [int(d * size) for d in _ALLPASS]
    ar = [int(d * size) + _STEREO_SPREAD for d in _ALLPASS]
    # feed each side a mostly-own-channel mix so stereo placement survives
    in_l = 0.7 * src[:, 0] + 0.3 * mono_in
    in_r = 0.7 * src[:, 1] + 0.3 * mono_in
    wl = _reverb_channel(in_l, cl, al, g, kernel)
    wr = _reverb_channel(in_r, cr, ar, g, kernel)
    wetsig = np.stack([wl, wr], axis=1)
    if width != 1.0:
        wetsig = widen(wetsig, width)
    return dry * x + wet * wetsig


def cavern_ir(rng, length=6.0, lowcut=80.0, tilt=1.5, stereo=True):
    """Exponentially decaying noise IR whose high end dies faster (tilt)."""
    n = seconds(length)
    t = tvec(n)
    outs = []
    for ch in range(2 if stereo else 1):
        w = rng.standard_normal(n)
        # frequency-dependent decay: split into 4 bands with FFT masks
        spec = np.fft.rfft(w)
        f = np.fft.rfftfreq(n, 1.0 / SR)
        ir = np.zeros(n)
        bands = [(20, 300, 1.0), (300, 1200, 0.7), (1200, 4000, 0.45), (4000, 20000, 0.25)]
        for lo, hi, tau_scale in bands:
            m = np.exp(-0.5 * ((np.log2(np.maximum(f, 1)) - np.log2(math.sqrt(lo * hi))) / 0.6) ** 2)
            band = np.fft.irfft(spec * m, n)
            ir += band * np.exp(-t / (length / 4.0 * tau_scale * tilt))
        outs.append(ir)
    ir = np.stack(outs, axis=1) if stereo else np.stack([outs[0], outs[0]], axis=1)
    ir[:seconds(0.01)] *= np.linspace(0, 1, seconds(0.01))[:, None]
    ir /= np.sqrt((ir ** 2).sum(axis=0)).max()
    return ir


def convolve_stereo(stereo, ir):
    n = stereo.shape[0]
    m = ir.shape[0]
    N = 1 << int(math.ceil(math.log2(n + m)))
    out = np.zeros((n, 2))
    for ch in range(2):
        X = np.fft.rfft(stereo[:, ch], N)
        H = np.fft.rfft(ir[:, ch], N)
        out[:, ch] = np.fft.irfft(X * H, N)[:n]
    return out


# ----------------------------------------------------------------------------
# stereo tools, saturation, master
# ----------------------------------------------------------------------------
def pan(mono, p):
    """p in [-1, 1]."""
    a = (p + 1.0) * 0.25 * math.pi
    return np.stack([mono * math.cos(a), mono * math.sin(a)], axis=1)


def widen(stereo, width=1.3):
    mid = 0.5 * (stereo[:, 0] + stereo[:, 1])
    side = 0.5 * (stereo[:, 0] - stereo[:, 1]) * width
    return np.stack([mid + side, mid - side], axis=1)


def saturate(x, drive=1.5, mix=1.0):
    """Gentle tape-like saturation: tanh with unity small-signal gain."""
    y = np.tanh(drive * x) / drive
    return mix * y + (1.0 - mix) * x


def _smooth(x, win_s):
    k = np.hanning(seconds(win_s))
    k /= k.sum()
    n = len(x)
    N = 1 << int(math.ceil(math.log2(n + len(k))))
    y = np.fft.irfft(np.fft.rfft(x, N) * np.fft.rfft(k, N), N)
    return y[len(k) // 2: len(k) // 2 + n]


def limiter(stereo, threshold_db=-3.0, attack_s=0.01, release_s=0.25):
    """Look-ahead style soft limiter built from a block-max envelope."""
    thr = db(threshold_db)
    absx = np.abs(stereo).max(axis=1)
    blk = seconds(attack_s)
    n = len(absx)
    npad = (-n) % blk
    padded = np.concatenate([absx, np.zeros(npad)]).reshape(-1, blk).max(axis=1)
    padded = np.maximum(padded, np.maximum(np.roll(padded, 1), np.roll(padded, -1)))
    env = np.repeat(padded, blk)[:n]
    env = np.maximum(env, _smooth(env, release_s))
    gain = np.minimum(1.0, thr / np.maximum(env, 1e-9))
    gain = np.minimum(gain, _smooth(gain, attack_s) + 1e-3)
    y = stereo * gain[:, None]
    return np.tanh(y / thr) * thr  # safety, only touches overs


def rms_db(x):
    return 20.0 * math.log10(math.sqrt(float(np.mean(x ** 2))) + 1e-12)


def master(stereo, peak_db=-3.0, rms_target=(-19.5, -15.5), drive=1.2):
    """Normalise the mix: gentle saturation, then raise gain into a limiter
    until the whole-file RMS falls in the target window, then peak-normalise."""
    x = np.asarray(stereo, dtype=np.float64)
    x = x - x.mean(axis=0)
    x = x / (np.abs(x).max() + 1e-12) * db(peak_db)
    x = saturate(x, drive=drive, mix=0.6)
    x = x / (np.abs(x).max() + 1e-12) * db(peak_db)
    lo, hi = rms_target
    for _ in range(12):
        r = rms_db(x)
        if r >= lo:
            break
        boost = min(hi - r, 2.0)
        x = limiter(x * db(boost), peak_db)
    x = x / (np.abs(x).max() + 1e-12) * db(peak_db)
    return x


# ----------------------------------------------------------------------------
# IO
# ----------------------------------------------------------------------------
def write_wav(path, stereo):
    x = np.clip(stereo, -1.0, 1.0)
    pcm = (x * 32767.0).astype("<i2")
    data = pcm.tobytes()
    with open(path, "wb") as fh:
        fh.write(b"RIFF" + struct.pack("<I", 36 + len(data)) + b"WAVE")
        fh.write(b"fmt " + struct.pack("<IHHIIHH", 16, 1, 2, SR, SR * 4, 4, 16))
        fh.write(b"data" + struct.pack("<I", len(data)) + data)


def encode_ogg(wav_path, ogg_path, quality=4):
    subprocess.run(["/usr/bin/ffmpeg", "-y", "-loglevel", "error", "-i", wav_path,
                    "-c:a", "libvorbis", "-q:a", str(quality), ogg_path], check=True)


def stats(stereo):
    x = np.asarray(stereo)
    peak = float(np.abs(x).max())
    rms = rms_db(x)  # mean power over both channels
    # spectral band energy split (both channels)
    N = 1 << 16
    nblk = x.shape[0] // N
    spec = np.zeros(N // 2 + 1)
    win = np.hanning(N)
    for ch in range(2):
        for i in range(nblk):
            spec += np.abs(np.fft.rfft(x[i * N:(i + 1) * N, ch] * win)) ** 2
    # loudness profile per 10 s (shows the piece evolving)
    blk = seconds(10.0)
    profile = [round(rms_db(x[i:i + blk]), 1) for i in range(0, x.shape[0] - blk // 2, blk)]
    # click detector: a 2 ms block whose max slew dwarfs its mean slew
    d = np.abs(np.diff(x, axis=0)).max(axis=1)
    bl = seconds(0.002)
    m = len(d) // bl * bl
    blocks = d[:m].reshape(-1, bl)
    ratio = blocks.max(axis=1) / (blocks.mean(axis=1) + 1e-9)
    clicks = int(((ratio > 12.0) & (blocks.max(axis=1) > 0.02)).sum())
    f = np.fft.rfftfreq(N, 1.0 / SR)
    edges = [0, 150, 600, 2500, 8000, 22050]
    tot = spec.sum() + 1e-12
    bands = []
    for lo, hi in zip(edges[:-1], edges[1:]):
        m = (f >= lo) & (f < hi)
        bands.append(float(spec[m].sum() / tot))
    slew = float(np.abs(np.diff(x, axis=0)).max())
    clipped = int((np.abs(x) >= 0.999).sum())
    return dict(peak_db=20 * math.log10(peak + 1e-12), rms_db=rms,
                bands=bands, max_slew=slew, clicks=clicks, clipped_samples=clipped,
                rms_profile_10s=profile, seconds=len(x) / SR)


# --- numpy-only PNG spectrogram ---------------------------------------------
_CMAP = np.array([
    [0, 0, 4], [28, 12, 68], [80, 18, 123], [130, 37, 129], [181, 54, 122],
    [230, 81, 98], [251, 135, 97], [254, 194, 135], [252, 253, 191]], dtype=float)


def _png_write(path, rgb):
    h, w, _ = rgb.shape
    raw = b"".join(b"\x00" + rgb[y].astype(np.uint8).tobytes() for y in range(h))

    def chunk(tag, data):
        c = struct.pack(">I", len(data)) + tag + data
        return c + struct.pack(">I", zlib.crc32(tag + data) & 0xffffffff)
    png = b"\x89PNG\r\n\x1a\n"
    png += chunk(b"IHDR", struct.pack(">IIBBBBB", w, h, 8, 2, 0, 0, 0))
    png += chunk(b"IDAT", zlib.compress(raw, 6))
    png += chunk(b"IEND", b"")
    with open(path, "wb") as fh:
        fh.write(png)


def spectrogram_png(stereo, path, width=1400, height=420, fmin=30.0, fmax=16000.0,
                    dyn_db=80.0):
    mono = np.asarray(stereo).mean(axis=1)
    n = len(mono)
    N = 4096
    hop = max(1, n // width)
    starts = np.arange(0, n - N, hop)[:width]
    win = np.hanning(N)
    idx = starts[:, None] + np.arange(N)[None, :]
    S = np.abs(np.fft.rfft(mono[idx] * win, axis=1)) ** 2
    f = np.fft.rfftfreq(N, 1.0 / SR)
    # log-frequency rows
    rows = np.geomspace(fmin, fmax, height)
    ridx = np.searchsorted(f, rows)
    ridx = np.clip(ridx, 1, len(f) - 1)
    img = 10 * np.log10(S[:, ridx] + 1e-14)  # time x freq
    img = img - img.max()
    img = np.clip((img + dyn_db) / dyn_db, 0, 1)
    img = img.T[::-1]  # freq rows top = high
    # colormap
    pos = img * (len(_CMAP) - 1)
    i0 = np.clip(pos.astype(int), 0, len(_CMAP) - 2)
    fr = (pos - i0)[..., None]
    rgb = _CMAP[i0] * (1 - fr) + _CMAP[i0 + 1] * fr
    # 30 s grid lines
    for s in range(30, int(n / SR), 30):
        col = int(s * SR / hop)
        if col < rgb.shape[1]:
            rgb[:, col] = rgb[:, col] * 0.5 + np.array([120, 120, 120]) * 0.5
    _png_write(path, rgb)


# ----------------------------------------------------------------------------
# mixer
# ----------------------------------------------------------------------------
class Mixer:
    """Holds named stereo buses of equal length; `add` places clips at times."""

    def __init__(self, length_s):
        self.n = seconds(length_s)
        self.buses = {}

    def bus(self, name):
        if name not in self.buses:
            self.buses[name] = np.zeros((self.n, 2))
        return self.buses[name]

    def add(self, name, clip, at_s, gain=1.0):
        b = self.bus(name)
        if clip.ndim == 1:
            clip = np.stack([clip, clip], axis=1)
        s = seconds(at_s)
        if s >= self.n or s < 0:
            return
        e = min(s + clip.shape[0], self.n)
        seg = clip[:e - s]
        if e - s > seconds(0.03):
            # protect against clips cut off by the end of the buffer
            tail = min(seconds(0.03), e - s)
            seg = seg.copy()
            seg[-tail:] *= np.linspace(1, 0, tail)[:, None]
        b[s:e] += seg * gain

    def mix(self, gains=None, processors=None):
        gains = gains or {}
        processors = processors or {}
        out = np.zeros((self.n, 2))
        for name, b in self.buses.items():
            sig = b
            if name in processors:
                sig = processors[name](sig)
            out += sig * gains.get(name, 1.0)
        return out
