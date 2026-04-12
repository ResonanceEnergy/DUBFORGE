# Phase 3: MIXING — Workflow

> v6.0.0 — AbletonOSC mixing. All processing via Ableton devices.
> **Time signature: 4/4 always** — `BEATS_PER_BAR = 4`. No odd meters.

Execution order for every render pass through the mixing phase.

**Entry:** `phase_three.py` → `run_phase_three(stem_pack)` → Mixed stereo WAV

## SOT Architecture

- Canonical runtime entrypoint: `forge.py`
- Canonical orchestrator: `tools/forge_runner.py`
- Stage workflow path: `forge.py` → `tools/forge_runner.py` → `engine/phase_three.py::run_phase_three()`

---

## Execution Order

```
Phase 3: MIXING (AbletonOSC — Per-Track → Bus → Master)
│
├── Setup (Brain: CRITIC)
│   │
│   ├── 1. Connect to Ableton Live (OSC ports 11000/11001)
│   │       └── bridge.connect()
│   │       └── HALT if Ableton not running
│   │
│   ├── 2. Create mixing session
│   │       ├── bridge.set_tempo(stem_pack.dna.bpm)
│   │       └── For each stem → create audio track + import WAV
│   │
│   └── 3. Validate stem import
│           ├── Track count matches stem count
│           └── No silent tracks
│
├── Tier 1 — Per-Track Processing (Brain: CRITIC)
│   │   For each audio track:
│   │
│   ├── 4. Insert EQ Eight → role-specific surgical cuts
│   │       └── bridge.load_device() + bridge.set_device_param()
│   │
│   ├── 5. Insert Compressor → dynamics control
│   │       └── Role-specific attack/release/ratio
│   │
│   ├── 6. Configure sidechain (bass/pad/lead tracks only)
│   │       └── bridge.set_sidechain(track, kick_track)
│   │
│   └── 7. Set volume + pan
│           ├── Gain staging from priority table
│           └── Pan from stem_metadata
│
├── Tier 2 — Bus Grouping (Brain: CRITIC)
│   │
│   ├── 8. Create group tracks
│   │       ├── DRUMS: kick + snare + hihat + perc
│   │       ├── BASS: sub_bass + mid_bass + neuro
│   │       ├── MELODIC: lead + pad + vocal + chord
│   │       └── FX: fx + riser + ambient
│   │
│   ├── 9. Route tracks to buses
│   │       └── bridge.set_routing(track, group)
│   │
│   └── 10. Bus processing
│           ├── Glue Compressor on each bus
│           ├── Utility (mono < 120Hz) on BASS bus
│           └── EQ Eight for inter-bus carving
│
├── Tier 3 — Master Chain (Brain: CRITIC)
│   │
│   ├── 11. Master EQ Eight → 12-band surgical cuts
│   │
│   ├── 12. Master Utility → stereo width
│   │       └── Mono below 200Hz, width above
│   │
│   └── 13. Master Compressor → bus glue
│
├── Bounce
│   │
│   ├── 14. Export mixed stereo WAV
│   │       └── bridge.export_audio()
│   │
│   └── 15. Save mixing session .als
│           └── bridge.save_project()
│
└── Quality Gate: MIX → MASTER
    ├── Peak < 0 dBFS
    ├── RMS ≈ -14 dBFS
    ├── DR ≈ 18 dB
    └── Mono compatibility > -3 dB
```

---

## Dependency Graph

```
Phase 2 Output (StemPack)
    ├── stems: dict[str, np.ndarray] ──────────→ [2] Import as audio tracks
    ├── kick_positions: list[int] ─────────────→ [6] Sidechain source
    ├── section_map: dict[str, int] ───────────→ (passed through)
    ├── stem_metadata: dict[str, dict] ────────→ [7] Gain/pan, [8] Bus assignment
    └── dna: SongDNA ──────────────────────────→ [2] BPM, [4] EQ decisions
                                                │
                ┌───────────────────────────────┘
                ▼
    [2-3] Create session + import stems
                │
                ▼
    [4-7] Per-track: EQ → Comp → Sidechain → Volume/Pan
                │
                ▼
    [8-10] Bus grouping → routing → bus processing
                │
                ▼
    [11-13] Master chain: EQ → Utility → Compressor
                │
                ▼
    [14-15] Bounce mixed stereo + save session
                │
                ▼
            → Phase 4: MASTER (AbletonOSC)
```
