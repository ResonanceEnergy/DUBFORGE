# Phase 2: ARRANGEMENT — Mission Mandate

> v6.0.0 — Input corrected: 4 deliverable categories from Phase 1, not raw SongMandate.
> ALL phases AbletonOSC. No numpy DSP.

> **Brain:** ARCHITECT — structure, energy arc, section contrast
> **Dojo Phase:** ARRANGE (Sprint 3) + DESIGN (Sprint 3)
> **Entry:** `phase_two.py` → `run_phase_two(deliverables)`
> **Input:** 4 deliverable categories (see Input Contract below)
> **Output:** StemPack (individual track WAVs bounced from Ableton) + kick positions + section map

## SOT Architecture

- Canonical runtime entrypoint: `forge.py`
- Canonical orchestrator: `tools/forge_runner.py`
- Stage 2 execution path: `forge.py` → `tools/forge_runner.py` → `engine/phase_two.py::run_phase_two()`

---

## Mission Statement

Transform Phase 1's deliverables — a pre-loaded Ableton template, audio files,
arrangement mapping, and modulation/automation data — into a **7-section arrangement**
and then **bounce individual track stems** via AbletonOSC.

Phase 2 does NOT receive a raw SongMandate dataclass. It receives **processed,
ready-to-use deliverables** from Phase 1:

1. **Pre-loaded Ableton template** — `.als` file with audio tracks created,
   Serum 2 instruments loaded, FX chains (saturation, reverb/delay, sidechain
   compressors, stereo imaging, wave folding) already configured on each track,
   128 Drum Rack loaded and populated
2. **Audio files** — Serum 2 bounced stems (Stage 4J: 10 wet WAVs) + drum/pattern
   renders (Stage 5G: per-section WAVs)
3. **Arrangement data and mapping** — section map (intro/build/drop/breakdown/outro),
   energy curve, subtractive map (what to mute per section), total_bars, BPM
4. **Modulation and automation data for FX chains** — per-stem LFO routes,
   filter sweep curves, FX send levels per section, volume rides, sidechain
   depth per section

Phase 2 places audio, writes automation, and bounces through Ableton Live.
**No DSP. No synthesis. No FX processing in Python.**

**AbletonOSC is the engine.**

---

## Architecture: AbletonOSC Arrangement → Stem Bounce

| Step | Operation | Module |
|------|-----------|--------|
| 1 | Connect to Ableton Live via OSC | `ableton_bridge.py` |
| 2 | Load/create ALS project from mandate | `als_generator.py` → `ableton_bridge.py` |
| 3 | Place WAV stems in arrangement view per section map | `ableton_bridge.py` |
| 4 | Write section-level automation (volume, filter, sends) | `automation_recorder.py` → `ableton_bridge.py` |
| 5 | Configure per-track FX chains from mandate | `ableton_bridge.py` |
| 6 | Set sidechain routing (ghost kick → compressors) | `ableton_bridge.py` |
| 7 | Compute subtractive map (what to mute per section) | `stage_integrations.py` |
| 8 | Apply mutes/attenuations per section | `ableton_bridge.py` |
| 9 | Bounce each track to individual stem WAV | `ableton_bridge.py::bounce_track()` |
| 10 | Collect stems + kick positions + section map → StemPack | `phase_two.py` |

---

## 7 Sections

| Section | Bars | Energy | Active Elements |
|---------|------|--------|----------------|
| **Intro** | 8 | Low | Pads, drones, noise bed, light drums, filtered bass |
| **Build 1** | 4 | Rising | Full drums (build pattern), riser, gate chop, vocal FX |
| **Drop 1** | 16 | Maximum | All drums, full bass rotation, leads, chords, sub (sidechained), crashes |
| **Breakdown** | 8 | Low | Pads (wide), plucks, light drums, reverse FX |
| **Build 2** | 4 | Rising | Drums, riser, supersaw swell, vocal FX |
| **Drop 2** | 16 | Max+ | All Drop 1 elements hotter, more vocals, stutter FX |
| **Outro** | 8 | Fade | Pads (fading), noise bed, light drums |

**Total:** 64 bars default (from DNA arrangement template)

---

## Subtractive Architecture

Same principle as before — the Fat Loop concept — but now executed via Ableton:
- **Drop sections:** Everything unmuted, full FX, full automation
- **Intro/Outro:** Most tracks muted or low-passed, minimal drums, pads only
- **Breakdowns:** Bass muted, drums stripped, pads + melodic elements only
- **Builds:** Risers unmuted, drums building, filter automation opening

The subtractive map drives Ableton track mute/volume automation per section.

---

## Input Contract: Phase 1 Deliverables

Phase 2 receives **4 deliverable categories**, not a raw SongMandate:

### 1. Pre-loaded Ableton Template

| Deliverable | Source |
|-------------|--------|
| `.als` project file | Stage 4I + Stage 5G (build_render_als, build_stage5_als) |
| Audio tracks (10 Serum 2 + drum groups) | Pre-created in ALS |
| Serum 2 instruments loaded per synth track | Stage 4F (state map) |
| FX chains on each track | Stage 4D (saturation, reverb, delay, sidechain, stereo, wavefold) |
| 128 Drum Rack populated | Stage 5D |
| Return tracks (reverb, delay buses) | ALS template config |

### 2. Audio Files

| Deliverable | Source | Count |
|-------------|--------|-------|
| Serum 2 stem bounces (wet WAV) | Stage 4J | 10 stems |
| Drum/pattern renders per section | Stage 5G | N × section-groups |
| FX samples (Galactia, risers, impacts) | pre-S4 collection | varies |

### 3. Arrangement Data and Mapping

| Deliverable | Source |
|-------------|--------|
| Section map (intro, build1, drop1, ...) | Stage 2A (ArrangementTemplate) |
| Energy curve per section | Stage 2B (RCOProfile) |
| Subtractive map (what to mute per section) | Computed from energy + arrangement |
| Total bars, BPM | DNA + arrangement |
| MIDI sequences per stem per section | Stage 3C |

### 4. Modulation and Automation Data for FX Chains

| Deliverable | Source |
|-------------|--------|
| LFO routes (param → LFO shape/rate/depth) | Stage 4C |
| Filter sweep automation curves | Derived from section energy |
| FX send levels per section (reverb/delay amount) | Section-dependent mapping |
| Volume rides per section | Subtractive map + energy curve |
| Sidechain depth per section | Section intensity mapping |

**Phase 2 does NOT need:** raw wavetable data, Serum 2 preset blobs, drum collection
metadata, chord theory data, palette intent, production recipe, DNA sub-fields used
only for synthesis decisions. Those are Phase 1's internal concerns — already baked
into the ALS template and audio files.

---

## Module Dependencies

### Phase 2 Modules — Confirmed needed

| Module | Purpose |
|--------|---------|
| `ableton_bridge.py` | AbletonOSC command-and-control. Connect, create tracks, place clips, write automation, set FX params, bounce stems |
| `als_generator.py` | ALSProject data model. Build/modify .als project structure |
| `arrangement_sequencer.py` | ArrangementTemplate, SectionDef — section structure |
| `stage_integrations.py` | `compute_subtractive_map()`, `compute_arrangement_energy_curve()`, energy/contrast analysis |
| `automation_recorder.py` | AutomationLane → ALSAutomation conversion, LFO/ramp generation |
| `lfo_matrix.py` | LFOPreset generation for modulation routes |
| `sidechain.py` | SidechainPreset — ghost kick routing config |

### NOT called in Phase 2

| Module | Status |
|--------|--------|
| `dsp_core.py` | No DSP in Phase 2 — Ableton does all processing |
| `supersaw.py` | Pre-rendered in Phase 1 Stage 4G |
| `karplus_strong.py` | Pre-rendered in Phase 1 Stage 4G |
| `noise_generator.py` | Pre-rendered in Phase 1 Stage 4G |
| `rhythm_engine.py` | MIDI patterns generated in Phase 1 Stage 3C |
| `saturation.py` | FX chain applied in Ableton, not numpy |
| `reverb_delay.py` | FX chain applied in Ableton, not numpy |
| `stereo_imager.py` | FX chain applied in Ableton, not numpy |

---

## Output Contract: StemPack

```python
@dataclass
class StemPack:
    """Output of Phase 2 — individual track stems ready for Phase 3 mixing."""
    stems: dict[str, np.ndarray]        # "kick" → full-arrangement-length audio
    section_map: dict[str, int]         # "intro" → sample offset
    kick_positions: list[int]           # sample indices for Phase 3 sidechain
    total_bars: int
    total_samples: int
    dna: SongDNA
    stem_metadata: dict[str, dict]      # per-stem: gain, pan, bus assignment, source
    elapsed_s: float = 0.0
```

### Expected Stems

| Stem Name | Source | Frequency Range |
|-----------|--------|----------------|
| `kick` | Drum Rack bounce | Sub-impact |
| `snare` | Drum Rack bounce | Transient mid |
| `hats` | Drum Rack bounce | Metallic high |
| `perc` | Drum Rack bounce | Various |
| `sub_bass` | Serum 2 stem bounce | 20–80 Hz |
| `mid_bass` | Serum 2 stem bounce | 80–300 Hz |
| `neuro` | Serum 2 stem bounce | Growl mid |
| `wobble` | Serum 2 stem bounce | LFO-modulated |
| `riddim` | Serum 2 stem bounce | Rhythmic bass |
| `lead` | Serum 2 stem bounce | 800 Hz–4 kHz |
| `chords` | Serum 2 stem bounce | Harmonic stabs |
| `pad` | Serum 2 stem bounce | Evolving texture |
| `arps` | Serum 2 stem bounce | Rhythmic melody |
| `supersaw` | Serum 2 stem bounce | Build swell |
| `fx_risers` | FX track bounce | Transitions |
| `fx_impacts` | FX track bounce | Boom/hit |
| `vocals` | Audio track bounce | Chop layers |

---

## Quality Gate: ARRANGE → MIX

| Metric | Min | Max |
|--------|-----|-----|
| Stem Count | 10 | 20 |
| Section Count | 5 | 10 |
| Total Duration (s) | 120 | 360 |
| All stems non-silent | True | — |
| Kick positions detected | > 0 | — |

---

## Audit Output

| Artifact | Location |
|----------|----------|
| Individual stem WAVs | `output/{track_name}/stems/` |
| Section map JSON | `audit/02_ARRANGE/section_map.json` |
| Subtractive map JSON | `audit/02_ARRANGE/subtractive_map.json` |
| Energy curve JSON | `audit/02_ARRANGE/energy_curve.json` |
| Bounce log | `audit/02_ARRANGE/bounce_log.json` |