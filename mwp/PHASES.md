# DUBFORGE — MWP Phase Architecture

> v6.0.0 — ALL phases AbletonOSC. No numpy DSP fallback anywhere.
> Phase 2 input = deliverables (ALS template + audio + arrangement + automation), not raw SongMandate.

**Minimum Workable Pipeline** — ill.Gates / Producer Dojo methodology applied to
automated dubstep production. Each phase has a **Mandate** (why), **Workflow** (how),
and **Playbook** (step-by-step recipes).

Cardinal rule: **Separate creation from revision** — never mix while creating,
never create while mixing. Each phase produces a deliverable before the next begins.

Cardinal rule 2: **Ableton Live IS the engine. ALL phases operate through AbletonOSC.**
No internal numpy DSP fallback. No offline render. The DAW handles arrangement,
mixing, mastering, and export. DUBFORGE controls Ableton — it does not replace it.

---

## Phase Map

```
┌─────────────────────────────────────────────────────────────────────────┐
│                                                                         │
│   SONG IDEA (name, mood, key, BPM, style, YAML config)                 │
│              or REFERENCE URL (SoundCloud/YouTube)                       │
│                          │                                              │
│   ┌──────────────────────▼───────────────────────────────────────┐      │
│   │  PHASE 1: GENERATION  (Dojo steps 1–4)                      │      │
│   │  Stage 1: IDENTITY — DNA, palette intent, production recipe  │      │
│   │  Stage 2: STRUCTURE — arrangement, sections, energy curve    │      │
│   │  Stage 3: HARMONIC BLUEPRINT — chords, freq table, MIDI      │      │
│   │  Stage 4: SYNTH FACTORY — wavetables, presets, FX chains,    │      │
│   │           modulation routes → Serum 2 ALS → bounce WAV stems │      │
│   │  Stage 5: DRUM FACTORY — drums, 128 Rack, loops, patterns    │      │
│   │           → drum ALS → bounce WAV stems                      │      │
│   │  OUTPUT: Pre-loaded ALS template + WAV audio files           │      │
│   │          + arrangement data + modulation/automation data      │      │
│   └──────────────────────┬───────────────────────────────────────┘      │
│                          │                                              │
│   ┌──────────────────────▼───────────────────────────────────────┐      │
│   │  PHASE 2: ARRANGEMENT  (Dojo steps 5–6) — AbletonOSC        │      │
│   │  INPUT: ALS template (tracks + FX populated) + audio files   │      │
│   │         + arrangement mapping + modulation/automation data    │      │
│   │  Place stems → write automation → bounce individual stems    │      │
│   │  OUTPUT: StemPack (track stem WAVs) + kick positions         │      │
│   └──────────────────────┬───────────────────────────────────────┘      │
│                          │                                              │
│   ┌──────────────────────▼───────────────────────────────────────┐      │
│   │  PHASE 3: MIXING  (Dojo step 7) — AbletonOSC                │      │
│   │  Load stems → per-track EQ/comp/sidechain via Ableton        │      │
│   │  Bus grouping → master chain → bounce mixed stereo           │      │
│   │  OUTPUT: Mixed stereo WAV (frequency-balanced, gain-staged)  │      │
│   └──────────────────────┬───────────────────────────────────────┘      │
│                          │                                              │
│   ┌──────────────────────▼───────────────────────────────────────┐      │
│   │  PHASE 4: MASTERING  (Dojo steps 8–10) — AbletonOSC         │      │
│   │  MASTER → RELEASE → REFLECT                                  │      │
│   │  EQ → multiband → limiter → LUFS target via Ableton devices  │      │
│   │  OUTPUT: Final WAV (24-bit) + assets + session report        │      │
│   └──────────────────────────────────────────────────────────────┘      │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## Phase 1: GENERATION — 5 Stages

The core idea: **collect first, design second, render third**. IDENTITY establishes
the song's DNA. STRUCTURE builds the time-domain scaffold. HARMONIC BLUEPRINT
generates chords, MIDI sequences, and collects FX samples via `sample_library.py`.
SYNTH FACTORY designs wavetables, builds Serum 2 presets, and bounces 10 wet stems.
DRUM FACTORY collects drums from `sample_library.py`, builds the 128 Rack (inline),
generates patterns (inline), and bounces drum stems. **36 unique engine modules wired.**

```
STAGE 1: IDENTITY (1A–1D)
  1A  Constants — PHI, FIBONACCI, A4_432
  1B  DNA — _oracle() → SongDNA, beat_s, bar_s
  1C  Palette intent — _design_palette_intent(dna) → timbral goals
  1D  Production recipe — rb_select_recipe() + sections + recipes

STAGE 2: STRUCTURE (2A–2D)
  2A  Arrangement — _build_arrangement_from_dna(dna) → ArrangementTemplate
  2B  RCO energy — subtronics_*_preset(bpm) → RCOProfile
  2C  Sections — _sections_from_arrangement() → sections, total_bars, total_samples
  2D  Audio manifest — _build_audio_manifest(sections) → AudioManifest
  2E  Template backflow — session_template.get_template_requirements()
      → inject required_stems, bus_names, return_names, sidechain_pairs
        into design_intent for all downstream stages

STAGE 3: HARMONIC BLUEPRINT (3A–3C + pre-S4)
  3A  Harmony — _build_chord_progression(dna) → ChordProgression
  3B  Freq table — _build_freq_table(dna) → 5-octave lookup
  3C  MIDI sequences — _configure_stem_specs() → _generate_midi_sequences()
  pre-S4  FX samples — _collect_fx_samples(intent) → sample_library + galactia_fx

STAGE 4: SYNTH FACTORY (4A–4K)
  4A  Intake wavetables — _collect_wavetables() → WavetableKit
  4B  Generate WT packs — _generate_dna_wavetables() → packs
  4C  Modulation routes — _design_modulation_routes() → per-stem mod matrix
  4D  FX chains — _design_fx_chains() → per-stem FX
  4E  Morph wavetables — _morph_all_wavetables() → morphed WTs
  4F  Serum 2 presets — s2_build_all_presets() + state map
  4G  Synthesis — 9 sketch functions → bass/leads/atmos/fx/vocals/melody/wobble/riddim/growl
  4G+ Gap Modules (Session 13):
      • resample_feedback  — Live resampling feedback loop (bass_mangle, whirlpool, stutter_stack, spectral_freeze, master_resample)
      • wavetable_export   — Custom wavetable export to Serum 2 (harmonic_sweep, fm_morph, fractal, formant_cycle, resample_chain)
      • granular_depth     — Deep granular processing on existing audio (time_stretch, pitch_grain, cloud, freeze, morph)
      • guitar_synth       — Guitar-synth hybrid layer (pluck_pad, strum_supersaw, harmonic_bell, power_chord, ambient_string)
      • vocal_mangle       — Creative vocal mangling (glitch_slice, granular_vocal, formant_morph, reverse_build, stutter_gate)
      • serum_lfo_shapes   — Serum 2 LFO shape generation (phi_step, fibonacci_wave, fractal_lfo, euclidean_gate, harmonic_stack)
      • ab_workflow         — A/B sound design comparison (bracket, round_robin, elimination, golden_split, blind_vote)
      • vip_generator      — VIP generation: Fractals → Antifractals (pitch/spectral/rhythm/harmonic/full) with A/B selection
  4H  Stem configs — reuses _midi_stem_configs cached from 3C
  4H+ Mutate presets — _mutate_presets_dna() → unique Serum 2 per stem
  4I  Build render ALS — _build_render_als() → 11-track .als (ghost kick + 10 Serum 2)
  4J  Bounce — _bounce_render_tracks() → 10 WAV stems (wet, sidechained)
  4K  Collect — _collect_bounced_audio() + _build_production_skeleton()

STAGE 5: DRUM FACTORY (5A–5G)
  5A  Collect drums — _collect_drums(dna, intent) → sample_library → DrumKit
  5B  FX samples — galactia_fx (already collected pre-S4)
  5B+ Zone mapping — map_galactia_to_zones()
  5C  Process drums — _sketch_drums() → dynamics + saturation + intelligent_eq
  5D  128 Rack — _build_128_rack(drums, galactia_fx) → 14 Fibonacci zones (inline)
  5E  Drum loops — _build_drum_loops() + _build_loop_midi_maps() (inline)
  5F  Pattern Factory — section × zone_group patterns + FX chains (inline)
  5G  Stage 5 ALS — _build_stage5_als() → bounce → collect
```

---

## Phase 2: ARRANGEMENT — Template-Routed + AbletonOSC Stem Render

Dojo ARRANGE + DESIGN steps. Phase 1 delivers **4 categories of deliverables**
(not a raw SongMandate dataclass):

1. **Pre-loaded Ableton template** (.als) — audio tracks + instruments (Serum 2) +
   FX chains (saturation, reverb, delay, sidechaining) already configured on every track
2. **Audio files** — Serum 2 stem bounces (Stage 4J) + drum/pattern renders (Stage 5G)
3. **Arrangement data** — section map, energy curve, subtractive map, total_bars
4. **Modulation + automation data** — per-stem LFO routes, filter sweeps, FX send
   levels, volume rides, sidechain depth per section

### Phase 2 Setup (NEW — engine/phase_two_setup.py)

Before section placement, Phase 2 Setup builds the canonical session structure
from the session template (engine/session_template.py):

```
PHASE 2 SETUP — Template → Session
  S1  Build canonical layout — build_dubstep_session(bpm) → SessionLayout
      19 audio tracks + 5 buses (DRUMS/BASS/MELODICS/FX) + 3 returns
  S2  Scene map — mandate.arrangement_template → section bar offsets
  S3  Stem resolution — resolve_mandate_stems(mandate, layout)
      Maps SongMandate fields → track slots using MANDATE_TO_TRACK
  S4  Per-track processing — HPF/LPF, mono collapse, gain staging
  S5  Bus structure — BusArrangement per bus group
  S6  Sidechain — apply_sidechain on tracks with sidechain_from set
  S7  Return tracks — initialize Reverb, Delay, Parallel Comp
  S8  Energy curve — build_energy_curve from section intensities
  OUTPUT: SessionArrangement (attached to ArrangedTrack._session_arrangement)
```

### Session Template Track Layout (engine/session_template.py)

```
DRUMS Bus (gain: 1.00)
├── Kick       — layered Sub+Body+Click, mono, HPF 30Hz
├── Snare      — layered Head+Tail+Ghost, HPF 100Hz
├── Hi-Hats    — velocity-varied, swing, HPF 200Hz
├── Percussion — rides, crashes, fills, HPF 150Hz
└── SC Trigger — muted MIDI (sidechain source)

BASS Bus (gain: 0.90)
├── Sub        — sine/triangle, mono, <120Hz, sidechained
├── Mid Bass   — Serum 2 growl/wobble/riddim, sidechained
├── Growl      — resampled audio texture, sidechained
├── Riddim     — minimal wub, halftime, sidechained
└── Formant    — vowel bass "talking" layer, sidechained

MELODICS Bus (gain: 0.75)
├── Lead       — Serum 2 clean/processed
├── Pad        — atmospheric, reverb-heavy
├── Arp        — rhythmic melodic content
├── Chords     — supersaws or plucks
└── Vocal      — processed vocals/chops

FX Bus (gain: 0.55)
├── Risers     — white noise + pitch sweep
├── Impacts    — sub boom + reverse crash
├── Transitions — tape stops, glitches
└── Atmos      — ambient textures, foley

RETURN Tracks
├── Reverb (0.35)      — hall/plate + EQ Eight
├── Delay (0.30)       — tempo-synced 1/4 or dotted 1/8 + EQ Eight
└── Parallel Comp (0.25) — Glue Compressor + Utility
```

Phase 2 loads the pre-built ALS template via AbletonOSC, places the audio files
in arrangement view per the section map, writes all modulation and automation data
as Ableton automation lanes, then bounces each track as an individual stem WAV.

**AbletonOSC is the engine.** No numpy DSP, no offline render.

**Key modules:** `ableton_bridge.py` (AbletonOSC command-and-control),
`als_generator.py` (ALS project structure), `arrangement_sequencer.py` (section templates),
`automation_recorder.py` (automation envelope generation), `lfo_matrix.py` (per-stem modulation).

**Output:** `StemPack` — individual track stem WAVs (kick, snare, hats, sub, bass×N,
lead, chords, pad, fx, vocals) + kick positions + section map — ready for Phase 3.

---

## Phase 3: MIXING — AbletonOSC Per-Stem Mixdown

**Entry:** `phase_three.py` → `run_phase_three(stem_pack)`

Phase 3 loads the individual track stems from Phase 2 into a **mixing session in
Ableton Live** and controls the entire mix through AbletonOSC:

**Per-track processing (via Ableton devices):**
1. Load stems as audio tracks
2. Insert EQ Eight per track → surgical cuts (stem-role-appropriate)
3. Insert Compressor per track → dynamics control
4. Insert Compressor (sidechain) on bass/pad tracks → duck against kick
5. Set track volume (gain staging from priority table)
6. Set track pan

**Bus processing (via Ableton groups):**
7. Create group tracks: DRUMS, BASS, MELODIC, FX
8. Route tracks to bus groups
9. Insert Glue Compressor on each bus → glue
10. Frequency collision avoidance via EQ carving between buses

**Master chain (via Ableton master track):**
11. EQ Eight → 12-band pre-master surgical cuts
12. Utility → stereo imaging (mono below 200Hz, width above)
13. Compressor → master bus glue

**Bounce:** Export mixed stereo WAV via AbletonOSC.

**Key modules:** `ableton_bridge.py` (all device control + fader/pan + routing + export).

---

## Phase 4: MASTERING — AbletonOSC Master Chain + Release + Reflect

**Entry:** `phase_four.py` → `run_phase_four(mixed_audio)`

Phase 4 loads the mixed stereo from Phase 3 into a **mastering session in
Ableton Live** and applies the mastering chain through AbletonOSC:

**Mastering chain (Ableton master track devices):**
1. **EQ Eight** — HPF@45Hz, low shelf, high shelf, parametric mid corrections
2. **Multiband Dynamics** — 3-band (120Hz / 4kHz crossovers), per-band threshold/ratio
3. **Glue Compressor** — bus glue, gentle envelope
4. **Utility** — stereo width (mid/side), mono compatibility check
5. **Limiter** — brickwall ceiling at -0.3 dBTP, LUFS targeting (-10 dubstep)

**Post-master (Python analysis + Ableton export):**
6. QA validation (6 gates: peak, DC, silence, correlation, crest, noise)
7. LUFS/true peak verification
8. Phi normalization + coherence scoring
9. Dither + watermark
10. 24-bit 48kHz WAV export via AbletonOSC

**Key modules:** `ableton_bridge.py` (device insertion + parameter control + export),
`qa_validator.py` (6 gates), `normalizer.py`, `phi_analyzer.py`, `dither.py`,
`watermark.py`.

---

## Dojo 10 Steps → 4 Phases Mapping

| Dojo Step | Name | Brain | DUBFORGE Phase |
|-----------|------|-------|----------------|
| 1 | **ORACLE** | Architect | Phase 1 — Stage 1 (IDENTITY) |
| 2 | **COLLECT** | Child | Phase 1 — Stage 5 (DRUM FACTORY) |
| 3 | **RECIPES** | Architect | Phase 1 — Stage 1 (production recipe) |
| 4 | **SKETCH** | Child | Phase 1 — Stage 3+4 (HARMONIC BLUEPRINT + SYNTH FACTORY) |
| 5 | **ARRANGE** | Architect | Phase 2 — AbletonOSC (Fat Loop → Subtractive) |
| 6 | **DESIGN** | Child | Phase 2 — AbletonOSC (Spatial + Bus Routing) |
| 7 | **MIX** | Critic | Phase 3 — AbletonOSC (per-stem mix in Ableton) |
| 8 | **MASTER** | Critic | Phase 4 — AbletonOSC (mastering chain in Ableton) |
| 9 | **RELEASE** | Architect | Phase 4 (Export Assets) |
| 10 | **REFLECT** | Architect | Phase 4 (Report + Belt Assessment) |

---

## Brain System (ill.Gates)

- **CHILD** — Pure creativity. No judgment. First instincts. Used in DRUM FACTORY, SYNTH FACTORY.
- **ARCHITECT** — Structure and planning. Blueprint before building. Used in IDENTITY, STRUCTURE, ARRANGE.
- **CRITIC** — Technical precision. Metering, A/B, specs. Used in MIX, MASTER.

---

## Quality Gates

| Gate | Phase | Criteria |
|------|-------|----------|
| **PALETTE GATE** | 1→2 | 128 Rack populated, chord progression exists, melody exists, all zones have content, MIDI mapped, 10 Serum 2 stems bounced |
| **STRUCTURE GATE** | 2→3 | Full arrangement placed, all 7 sections filled, energy curve verified, contrast > 12dB |
| **MIX GATE** | 3→4 | Frequency balance OK, gain staging correct, no clipping, no phase issues, DR ≈ 18dB |
| **MASTER GATE** | 4→done | LUFS -12 to -6, true peak < −0.3 dBTP, QA 6 gates pass, stereo width OK |