# Phase 3: MIXING — Mission Mandate

> v6.0.0 — AbletonOSC mixing. Per-stem processing via Ableton devices.
> No numpy DSP. The DAW IS the mixing engine.

> **Brain:** CRITIC — technical precision, metering, frequency balance
> **Dojo Phase:** MIX (Sprint 4)
> **Entry:** `phase_three.py` → `run_phase_three(stem_pack)`
> **Input:** `StemPack` — individual track stems + kick positions + section map (from Phase 2)
> **Output:** Mixed stereo WAV — frequency-balanced, gain-staged, dynamics-controlled

## SOT Architecture

- Canonical runtime entrypoint: `forge.py`
- Canonical orchestrator: `tools/forge_runner.py`
- Stage 3 execution path: `forge.py` → `tools/forge_runner.py` → `engine/phase_three.py::run_phase_three()`

---

## Mission Statement

Load Phase 2's individual track stems into a **mixing session in Ableton Live**
and control the entire mix through AbletonOSC. Per-track EQ, compression, and
sidechain are applied via Ableton's built-in devices. Bus grouping, master chain,
and stereo imaging are all configured through AbletonOSC commands. The final mix
is bounced from Ableton — no numpy DSP, no offline processing.

**Ableton Live IS the mixing engine. DUBFORGE controls it, not replaces it.**

> "The mix is surgery, not seasoning. Cut problems, don't add flavor."

---

## Input Contract: StemPack

```python
@dataclass
class StemPack:
    stems: dict[str, np.ndarray]       # "kick" → full-arrangement-length mono/stereo
    section_map: dict[str, int]        # "intro" → sample offset
    kick_positions: list[int]          # sample offsets for sidechain
    total_bars: int
    total_samples: int
    dna: SongDNA
    stem_metadata: dict[str, dict]     # per-stem: gain, pan, bus assignment
    elapsed_s: float = 0.0
```

Expected stems (≥10): `kick`, `snare`, `hihat`, `sub_bass`, `mid_bass`,
`neuro`, `lead`, `pad`, `vocal`, `fx`, `riser`, `ambient`, ...

---

## 3-Tier Mixing Architecture (All AbletonOSC)

### Tier 1: Per-Track Processing (Ableton Devices)

Load each stem as an audio track in Ableton, then insert and configure devices:

| Step | Operation | Ableton Device | Purpose |
|------|-----------|----------------|---------|
| 1.1 | Load stems as audio tracks | `bridge.create_audio_track()` + import WAV | One track per stem |
| 1.2 | Per-track EQ | EQ Eight | Stem-specific surgical cuts (role-appropriate) |
| 1.3 | Per-track compression | Compressor | Dynamics control per stem |
| 1.4 | Sidechain compression | Compressor (sidechain input = kick) | Duck bass/pad/lead against kick |
| 1.5 | Gain staging | Track volume fader | Pink noise reference, priority table |
| 1.6 | Pan | Track pan knob | Stereo placement from stem_metadata |

### Tier 2: Bus Grouping (Ableton Groups)

Create group tracks and route processed stems:

| Bus | Stems | Ableton Device | Processing |
|-----|-------|----------------|-----------|
| DRUMS | kick, snare, hihat, percussion | Glue Compressor | Bus glue, transient preservation |
| BASS | sub_bass, mid_bass, neuro | Utility (mono < 120Hz) + EQ Eight | Mono sub, frequency separation |
| MELODIC | lead, pad, vocal, chord | EQ Eight + Utility | Stereo imaging, harmonic separation |
| FX | fx, riser, ambient, noise | Utility | Width enhancement, level automation |

Bus processing via AbletonOSC:
1. Create group tracks → route stems
2. Insert Glue Compressor on each bus
3. Insert EQ Eight for inter-bus frequency carving
4. Sidechain BASS bus against DRUMS bus

### Tier 3: Master Chain (Ableton Master Track)

Devices on Ableton's master track, controlled via AbletonOSC:

| Step | Ableton Device | Purpose |
|------|----------------|---------|
| 3.1 | EQ Eight | 12-band pre-master surgical cuts (all cuts, no boosts) |
| 3.2 | Utility | Stereo imaging — mono below 200Hz, width above |
| 3.3 | Compressor | Master bus glue, gentle envelope |

**Bounce:** `bridge.export_audio()` → mixed stereo WAV

---

## AbletonOSC Commands Used

| Command | Purpose | Tier |
|---------|---------|------|
| `bridge.create_audio_track(name)` | Create track for stem | 1 |
| `bridge.import_audio(track, wav_path)` | Load stem WAV | 1 |
| `bridge.load_device(track, "EQ Eight")` | Insert EQ per track | 1, 2, 3 |
| `bridge.load_device(track, "Compressor")` | Insert compressor | 1 |
| `bridge.load_device(track, "Glue Compressor")` | Insert bus glue | 2 |
| `bridge.load_device(track, "Utility")` | Insert utility (mono/width) | 2, 3 |
| `bridge.set_device_param(...)` | Set any device parameter | 1, 2, 3 |
| `bridge.set_volume(track, db)` | Set track fader | 1 |
| `bridge.set_pan(track, pan)` | Set track pan | 1 |
| `bridge.create_group_track(name)` | Create bus group | 2 |
| `bridge.set_routing(track, group)` | Route track to bus | 2 |
| `bridge.set_sidechain(track, source)` | Configure sidechain input | 1, 2 |
| `bridge.export_audio(path)` | Bounce mixed stereo | 3 |

---

## Module Dependencies

### Phase 3 Modules

| Module | Purpose |
|--------|---------|
| `ableton_bridge.py` | ALL device control, fader/pan, routing, group creation, sidechain config, export |

### NOT called in Phase 3 (handled by Ableton)

| Module | Status |
|--------|--------|
| `dc_remover.py` | Not needed — Ableton's EQ Eight HPF handles DC |
| `spectral_gate.py` | Not needed — Ableton's Gate device |
| `dynamics_processor.py` | Not needed — Ableton's Compressor |
| `intelligent_eq.py` | Not needed — Ableton's EQ Eight |
| `dsp_core.py` | Not needed — Ableton handles all DSP |
| `stereo_imager.py` | Not needed — Ableton's Utility device |
| `sidechain.py` | Not needed — Ableton's Compressor sidechain input |
| `auto_mixer.py` | Not needed — gain staging via track faders |
| `mix_bus.py` | Not needed — Ableton group tracks + devices |
| `stage_integrations.py` | Not needed for mixing — all in Ableton |

---

## Gain Staging Priority

| Element | Priority | Target Level |
|---------|----------|-------------|
| kick | 1.00 | Loudest |
| sub_bass | 0.95 | Near-loudest |
| snare | 0.90 | Strong |
| bass | 0.85 | Present |
| vocal | 0.80 | Audible |
| lead | 0.75 | Clear |
| hihat | 0.60 | Background |
| pad | 0.50 | Ambient |
| riser | 0.50 | Ambient |
| fx | 0.40 | Subtle |
| ambient | 0.30 | Quietest |

---

## Sidechain Routing (Per-Track via Ableton Compressor)

Sidechain is configured via Ableton's Compressor sidechain input:

| Track | Sidechain Source | Depth | Notes |
|-------|-----------------|-------|-------|
| sub_bass | kick track | Aggressive | Fast attack, medium release |
| mid_bass | kick track | Medium | Fast attack, medium release |
| neuro | kick track | Medium | Medium attack/release |
| pad | kick track | Light | Slow attack, slow release |
| lead | kick track | Light | Gentle pumping |

---

## Quality Gate: MIX → MASTER

| Metric | Target |
|--------|--------|
| Peak | < 0 dBFS (no clipping) |
| RMS | ~ -14 dBFS |
| Dynamic Range | ≈ 18 dB |
| Mono compatibility | > -3 dB correlation |

---

## Output Contract

| Artifact | Type |
|----------|------|
| Mixed stereo WAV | Bounced from Ableton → Phase 4 |
| Kick positions | Passed through for mastering reference |
| Section map | Passed through for mastering section-aware processing |
| Mix session .als | Ableton project file (saved for recall) |
