# Phase 2: ARRANGEMENT — Workflow

> v6.0.0 — Input = 4 deliverable categories from Phase 1, not raw SongMandate.
> ALL phases AbletonOSC. No numpy DSP.
> **Time signature: 4/4 always** — `BEATS_PER_BAR = 4`. No odd meters.

Execution order for every render pass through the arrangement phase.

**Entry:** `phase_two.py` → `run_phase_two(deliverables)` → `StemPack`

**Input:** (1) pre-loaded ALS template, (2) audio files, (3) arrangement data,
(4) modulation/automation data for FX chains.

## SOT Architecture

- Canonical runtime entrypoint: `forge.py`
- Canonical orchestrator: `tools/forge_runner.py`
- Stage workflow path: `forge.py` → `tools/forge_runner.py` → `engine/phase_two.py::run_phase_two()`

---

## Execution Order

```
Phase 2: ARRANGEMENT (AbletonOSC)
├── Dojo Sprint 3 — ARRANGE (Brain: ARCHITECT)
│   │
│   ├── 1. Connect to Ableton Live (OSC ports 11000/11001)
│   │       └── ableton_bridge.AbletonBridge.connect()
│   │       └── HALT if Ableton not running
│   │
│   ├── 2. Load ALS project from mandate
│   │       ├── Option A: mandate.production_als_path → bridge.open_project()
│   │       └── Option B: Build live from mandate.stem_configs
│   │           ├── Create MIDI tracks per stem
│   │           ├── Load Serum 2 + state from serum2_state_map
│   │           ├── Load FX chains from mandate.fx_chains
│   │           └── Load 128 Rack from mandate.rack_128
│   │
│   ├── 3. Set project globals
│   │       ├── bridge.set_tempo(mandate.dna.bpm)
│   │       └── bridge.set_loop(0, mandate.total_bars * 4)
│   │
│   ├── 4. Place WAV stems in arrangement view
│   │       ├── audio_clips (10 Serum 2 bounces) → per-section placement
│   │       ├── stage5_renders (drum/pattern WAVs) → per-section placement
│   │       └── midi_sequences → MIDI clips per track per section
│   │
│   ├── 5. Compute subtractive architecture
│   │       ├── compute_subtractive_map(audio_clips, dna, energy_curve)
│   │       ├── compute_arrangement_energy_curve(dna)
│   │       └── Per-section: what to mute, attenuate, filter
│   │
│   ├── 6. Write section automation
│   │       ├── Volume rides (subtractive mutes/fades)
│   │       ├── Filter sweeps (builds: LP closed→open)
│   │       ├── Send levels (reverb/delay per section)
│   │       ├── Sidechain depth variation per section
│   │       └── Modulation routes from mandate.modulation_routes
│   │
│   ├── 7. Configure sidechain routing
│   │       ├── Ghost kick → Compressor sidechain on bass/pad tracks
│   │       └── Per-section sidechain depth automation
│   │
│   └── 8. Quality checkpoint
│           ├── All tracks populated
│           ├── Section count [5..10]
│           └── Total beats = mandate.total_bars * 4
│
├── Dojo Sprint 3 — BOUNCE (Brain: ARCHITECT)
│   │
│   ├── 9. Bounce individual track stems via AbletonOSC
│   │       ├── For each track (skip GHOST_KICK):
│   │       │   ├── bridge.bounce_track(track_idx, wav_path, solo=True)
│   │       │   └── Load WAV → stems dict
│   │       └── Parallel bounce if Ableton supports it
│   │
│   ├── 10. Detect kick positions from bounced kick stem
│   │       └── Onset detection (transient peak finding)
│   │
│   ├── 11. Build section_map (section_name → sample offset)
│   │
│   └── 12. Assemble StemPack
│           ├── stems: dict[str, np.ndarray]
│           ├── kick_positions: list[int]
│           ├── section_map: dict[str, int]
│           ├── stem_metadata: dict[str, dict]
│           └── dna: SongDNA (passed through)
│
└── Quality Gate: ARRANGE → MIX
    ├── Stem count >= 10
    ├── No silent stems (RMS > -96 dB)
    ├── Kick positions > 0
    ├── Duration [120s..360s]
    └── All sections have audio
```

---

## Dependency Graph

```
Phase 1 Deliverables (4 categories)
    │
    ├── [1] PRE-LOADED ALS TEMPLATE
    │       ├── .als project file ────────→ [2] Load ALS project
    │       ├── Serum 2 instruments ──────→ [2] Already on tracks
    │       ├── FX chains ───────────────→ [2] Already configured
    │       ├── 128 Drum Rack ───────────→ [2] Already loaded
    │       └── Return tracks ───────────→ [2] Reverb/delay buses
    │
    ├── [2] AUDIO FILES
    │       ├── Serum 2 bounces (10) ────→ [4] Place in arrangement
    │       ├── Drum/pattern WAVs ───────→ [4] Place per section
    │       └── FX samples ─────────────→ [4] Place in arrangement
    │
    ├── [3] ARRANGEMENT DATA
    │       ├── Section map ─────────────→ [4] Per-section placement
    │       ├── Energy curve ────────────→ [5] Subtractive map
    │       ├── BPM ─────────────────────→ [3] Set tempo
    │       ├── Total bars ──────────────→ [3] Set loop range
    │       └── MIDI sequences ──────────→ [4] Insert MIDI clips
    │
    └── [4] MODULATION + AUTOMATION DATA
            ├── LFO routes ──────────────→ [6] Write LFO automation
            ├── Filter sweeps ───────────→ [6] Section automation
            ├── FX send levels ──────────→ [6] Per-section sends
            ├── Volume rides ────────────→ [6] Subtractive mutes
            └── Sidechain depth ─────────→ [7] Ghost kick routing
                                     │
                                     ▼
                              [9] Bounce stems
                                     │
                              ┌──────┴──────┐
                              ▼              ▼
                     [10] Kick detect  [11] Section map
                              │              │
                              └──────┬───────┘
                                     ▼
                              [12] StemPack
                                     │
                                     ▼
                              → Phase 3: MIX (per-stem)
```

---

## AbletonOSC Commands Used

| Command | Purpose | Step |
|---------|---------|------|
| `bridge.connect()` | Test roundtrip | 1 |
| `bridge.open_project(path)` | Load ALS | 2 |
| `bridge.create_midi_track(name)` | Create track | 2 |
| `bridge.load_device(track, name)` | Load VST/device | 2 |
| `bridge.set_device_param(...)` | Set FX params | 2, 6 |
| `bridge.set_tempo(bpm)` | Set project BPM | 3 |
| `bridge.set_loop(start, end)` | Set render range | 3 |
| `bridge.insert_audio_clip(...)` | Place WAV in arrangement | 4 |
| `bridge.create_clip(...)` | Create MIDI clip | 4 |
| `bridge.add_notes(...)` | Insert MIDI notes | 4 |
| `bridge.write_automation(...)` | Write param automation | 6 |
| `bridge.bounce_track(...)` | Solo→export WAV | 9 |
| `bridge.list_tracks()` | Enumerate tracks | 9 |
| `bridge.get_volume(track)` | Read fader position | 9 |
| `bridge.get_pan(track)` | Read pan knob | 9 |