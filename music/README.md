# Beyond the End - ambient music

Nine procedurally composed, fully synthesised ambient tracks for the End
dimension of the Beyond the End mod, plus the `sounds.json` for the resource
pack.  No samples, no downloads: everything is generated with numpy and
encoded with ffmpeg.

## Regenerate

    python3 compose.py                 # all nine tracks, in parallel (~1 min)
    python3 compose.py violet gilded   # only some tracks
    python3 compose.py --keep-wav      # also keep the 16-bit WAV masters

Requires python3 + numpy and `/usr/bin/ffmpeg` (libvorbis).  Rendering is
deterministic (each track is seeded).

## Outputs

* `<name>.ogg`  - 44.1 kHz stereo Ogg Vorbis, `-q:a 4`, peak -3 dBFS
* `<name>.png`  - log-frequency spectrogram (30 s grid lines) for a glance at
  the structure
* `stats.json`  - peak, RMS, band energy split, click count, 10 s loudness
  profile per track
* `sounds.json` - resource-pack sound events `music.beyond.<name>`; the ogg
  files belong at `assets/beyond/sounds/music/<name>.ogg`

## Files

* `synth.py`   - the synth library: band-limited wavetable oscillators with
  detune/drift, additive bells/plucks, FM bells, ADSR envelopes, STFT
  low-pass/formant filters with time-varying cutoff, Freeverb-style
  algorithmic reverb (parallel combs + serial all-passes) and a convolution
  "cavern" tail, mid/side widening, tanh saturation, limiter + master
  normalisation, WAV/OGG output, stats and a numpy-only PNG spectrogram.
* `compose.py` - the tracks: key/mode, chord progressions, sections that
  change every 20-40 s, pad / choir / sub / melody / arp layers and the
  per-track extras (crackle, wind, sonar, shimmer, boss pulse + riff).
