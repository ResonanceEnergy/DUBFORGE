# Phase 3: MIXING — Playbook

> v6.0.0 — AbletonOSC mixing. All processing via Ableton devices.

Step-by-step recipes for the AbletonOSC mixing phase.

---

## Recipe 1: Create Mixing Session

```
Input:  StemPack (from Phase 2)
Output: Ableton session with all stems loaded as audio tracks
```

1. `bridge.connect()` — establish AbletonOSC connection
2. Create new Ableton session (or continue from Phase 2's session)
3. `bridge.set_tempo(stem_pack.dna.bpm)`
4. For each stem in `stem_pack.stems`:
   - `bridge.create_audio_track(stem_name)`
   - Export stem np.ndarray to temp WAV
   - `bridge.import_audio(track_idx, wav_path)`
5. Validate: track count matches stem count

---

## Recipe 2: Per-Track EQ (EQ Eight)

```
Input:  Audio track in Ableton
Output: Track with EQ Eight inserted, role-appropriate cuts applied
```

1. `bridge.load_device(track_idx, "EQ Eight")`
2. Look up stem role (kick=sub, snare=mid, pad=low-mid, lead=high-mid)
3. Apply HPF on everything except kick/sub_bass (cut below 30Hz)
4. Apply role-specific surgical cuts via `bridge.set_device_param()`:
   - Bass stems: cut 200Hz mud, cut 400Hz box
   - Pad stems: cut 3kHz harshness, cut 200Hz mud
   - Lead stems: cut 600Hz honk, shelf brightness
   - Drum stems: minimal — just HPF

---

## Recipe 3: Per-Track Compression (Compressor)

```
Input:  Audio track in Ableton
Output: Track with Compressor, dynamics controlled
```

1. `bridge.load_device(track_idx, "Compressor")`
2. Role-specific settings via `bridge.set_device_param()`:
   - Kick/snare: fast attack (1ms), fast release (50ms), ratio 4:1
   - Bass stems: medium attack (10ms), medium release (100ms), ratio 3:1
   - Pads: slow attack (30ms), slow release (200ms), ratio 2:1
   - Leads: medium attack, medium release, ratio 3:1

---

## Recipe 4: Sidechain Compression

```
Input:  Audio track + kick track reference
Output: Track with sidechain compressor ducking against kick
```

1. Skip kick and snare (they ARE the transients)
2. `bridge.load_device(track_idx, "Compressor")`
3. `bridge.set_sidechain(track_idx, kick_track_idx)`
4. Set depth by stem role:
   - sub_bass: aggressive (threshold low, ratio high)
   - mid_bass: medium
   - pad/lead: light pumping
5. Fast attack, medium release for all

---

## Recipe 5: Gain Staging + Pan

```
Input:  All audio tracks loaded
Output: Correct volume levels and pan positions
```

1. For each track, set volume from gain priority table:
   - `bridge.set_volume(track_idx, priority_to_db(priority))`
2. Set pan from `stem_pack.stem_metadata[stem_name]["pan"]`:
   - `bridge.set_pan(track_idx, pan_value)`
3. Reference: target overall RMS ≈ -14 dBFS

---

## Recipe 6: Create Bus Groups

```
Input:  All processed audio tracks
Output: 4 group tracks (DRUMS, BASS, MELODIC, FX) with routing
```

1. `bridge.create_group_track("DRUMS")` → route kick, snare, hihat, perc
2. `bridge.create_group_track("BASS")` → route sub_bass, mid_bass, neuro
3. `bridge.create_group_track("MELODIC")` → route lead, pad, vocal, chord
4. `bridge.create_group_track("FX")` → route fx, riser, ambient
5. Route each track: `bridge.set_routing(track_idx, group_idx)`

---

## Recipe 7: Bus Processing

```
Input:  4 group tracks
Output: Processed buses with glue compression and EQ carving
```

1. Insert Glue Compressor on each bus:
   - `bridge.load_device(bus_idx, "Glue Compressor")`
   - DRUMS bus: gentle glue, preserve transients
   - BASS bus: tighter control, mono below 120Hz via Utility
   - MELODIC bus: gentle, preserve dynamics
   - FX bus: light compression
2. Insert EQ Eight on BASS bus:
   - `bridge.load_device(bass_bus, "Utility")` → set to mono below 120Hz
   - EQ carving to separate from DRUMS

---

## Recipe 8: Master Chain

```
Input:  All buses summing to master
Output: Master track with pre-master EQ, imaging, glue
```

1. On master track:
   - `bridge.load_device("master", "EQ Eight")` → 12-band surgical cuts (all cuts)
   - `bridge.load_device("master", "Utility")` → stereo width control
   - `bridge.load_device("master", "Compressor")` → gentle bus glue
2. Set EQ bands (80Hz–12kHz, all cuts -1 to -4 dB)
3. Set Utility width (mono below 200Hz, slight widen above)

---

## Recipe 9: Bounce Mixed Stereo

```
Input:  Fully mixed Ableton session
Output: Mixed stereo WAV file
```

1. `bridge.export_audio(output_path, format="wav", bit_depth=24, sr=48000)`
2. Save Ableton session: `bridge.save_project(mix_session_path)`
3. Load bounced WAV for quality validation

---

## Recipe 10: Quality Gate

```
Input:  Mixed stereo WAV
Output: PASS/FAIL
```

1. Peak < 0 dBFS (no clipping)
2. RMS ≈ -14 dBFS
3. Dynamic range ≈ 18 dB
4. Mono compatibility > -3 dB correlation
