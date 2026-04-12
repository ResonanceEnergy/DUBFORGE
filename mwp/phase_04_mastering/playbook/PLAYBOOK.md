# Phase 4: MASTERING — Playbook

> v6.0.0 — AbletonOSC mastering. Mastering chain via Ableton devices.

Step-by-step recipes for the AbletonOSC mastering phase.

---

## Recipe 1: Create Mastering Session

```
Input:  Mixed stereo WAV (from Phase 3)
Output: Ableton mastering session with mix loaded
```

1. `bridge.connect()` — establish AbletonOSC connection
2. Create new Ableton session
3. `bridge.create_audio_track("master_input")` — create audio track
4. `bridge.import_audio(track_idx, mixed_wav_path)` — load Phase 3 mix
5. `bridge.set_tempo(dna.bpm)` — match original BPM

---

## Recipe 2: Insert Mastering EQ (EQ Eight)

```
Input:  Ableton master track
Output: Master track with EQ Eight configured
```

1. `bridge.load_device("master", "EQ Eight")`
2. Set HPF at 45Hz (remove sub-rumble below production range)
3. Low shelf: gentle body shaping (V4b: 0.0 dB — Phase 3 handled it)
4. High shelf: air/brightness (V4b: 0.0 dB)
5. Parametric mid corrections (V4b: all 0.0 — no mastering EQ fights pre-master)

---

## Recipe 3: Insert Multiband Dynamics

```
Input:  Ableton master track
Output: Master track with 3-band multiband dynamics
```

1. `bridge.load_device("master", "Multiband Dynamics")`
2. Set crossover frequencies: 120Hz and 4kHz
3. Per-band settings:
   - Low (< 120Hz): threshold -20dB, ratio ~3.5, slow attack
   - Mid (120Hz–4kHz): threshold -18dB, ratio ~3.0, medium attack
   - High (> 4kHz): threshold -16dB, ratio ~2.5, fast attack
4. All via `bridge.set_device_param()`

---

## Recipe 4: Insert Glue Compressor

```
Input:  Ableton master track
Output: Master track with bus glue compression
```

1. `bridge.load_device("master", "Glue Compressor")`
2. Gentle settings: low ratio, medium attack, medium release
3. Goal: subtle bus glue, not pumping

---

## Recipe 5: Insert Utility (Stereo Width)

```
Input:  Ableton master track
Output: Master track with stereo width control
```

1. `bridge.load_device("master", "Utility")`
2. Set width to 0.5 (narrowed from 1.0, per reference analysis)
3. Mono compatibility: verify via correlation meter

---

## Recipe 6: Insert Limiter

```
Input:  Ableton master track
Output: Master track with brickwall limiter
```

1. `bridge.load_device("master", "Limiter")`
2. Set ceiling to -0.3 dBTP (codec headroom)
3. Target output LUFS: -10 (competitive dubstep)
4. Adjust input gain to hit LUFS target

---

## Recipe 7: Bounce Master

```
Input:  Fully configured mastering session
Output: Mastered stereo WAV (24-bit, 48kHz)
```

1. `bridge.export_audio(output_path, format="wav", bit_depth=24, sr=48000)`
2. `bridge.save_project(master_session_path)` — save for recall
3. Load bounced WAV for post-master analysis

---

## Recipe 8: QA Validation

```
Input:  Mastered WAV
Output: PASS/FAIL + QA report
```

1. Peak level < 1.0 (0 dBFS) — no clipping
2. DC offset < 0.01 — clean signal
3. Silence ratio < 50% — actual content
4. Stereo correlation > -0.5 — not phase-inverted
5. Crest factor > 3 dB — not over-compressed
6. Noise floor < -40 dB — clean background
7. Dojo gate: LUFS [-12, -6], True Peak [-1.5, -0.1] dBTP

---

## Recipe 9: Phi Normalization + Analysis

```
Input:  Mastered audio
Output: Phi-normalized audio + coherence score
```

1. `normalize_phi_master()` — phi-weighted normalization
2. `analyze_phi_coherence()` — golden ratio alignment score

---

## Recipe 10: Final Export

```
Input:  Validated mastered audio
Output: 24-bit WAV + reports + watermark
```

1. `apply_final_dither()` — noise-shaped dither for 24-bit
2. `embed_audio_watermark()` — imperceptible identification watermark
3. Write final 24-bit stereo WAV at 48kHz
4. Write `master_report.json` with all settings and measurements
