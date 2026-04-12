# Phase 1: GENERATION — Mandate

> v7.0.0 — 4-stage pipeline: RCO removed (energy from `section.intensity`), Stage 2 STRUCTURE eliminated (redundant with S1H), audio manifest at 3I+ (4E only, 5E at 4F).

**Entry Module:** `engine/phase_one.py → run_phase_one()`
**Output:** `SongMandate` (42 fields) — everything Phase 2 needs to arrange a track

## SOT Architecture

- Canonical runtime entrypoint: `forge.py`
- Canonical orchestrator: `tools/forge_runner.py`
- Stage 1 execution path: `forge.py` → `tools/forge_runner.py` → `engine/phase_one.py::run_phase_one()`

---

## Mission Statement

Phase 1 takes a **song idea** (name, mood, key, BPM, YAML config) and produces
a **complete sound palette** organized in a 128 Drum Rack with MIDI mapping,
DNA-driven wavetables, modulation routes, FX chains, and all rendered audio.
No arrangement. No mixing. No mastering. Just sounds, samples, designs, and a plan.

> "Collect first. Design second. Render third. Never arrange with incomplete ingredients."
> — ill.Gates, The Approach

---

## Goal

Transform a song idea into a fully-loaded SongMandate containing:
- Complete DNA specification (key, scale, BPM, mood, style, sub-DNAs)
- **4/4 time signature enforced** — `BEATS_PER_BAR = 4`, no odd meters
- Arrangement template with per-section energy (from `section.intensity`)
- Production recipe with quality targets
- Chord progression and frequency table
- Drum samples selected + looped + racked + MIDI-mapped
- DNA-driven wavetables (generated, morphed, applied)
- Modulation routes and FX chains per stem
- 10 Serum 2 stem bounces (wet WAV) + section pattern renders
- 128 Rack with drums + FX + Galactia samples + MIDI map
- Audio manifest tracking all expected/delivered files

---

## The 4-Stage Pipeline

```
Stage 1: IDENTITY ──→ Stage 2: MIDI SEQUENCES ──→ Stage 3: SYNTH FACTORY
     ↓                     ↓                            ↓
  SongDNA              MIDI for all stems           Wavetables, presets,
  Palette intent       Galactia FX samples          Serum 2 bounce, ALS
  Production recipe                                 Audio manifest (4E)
  Arrangement + energy                                   ↓
                                                   Stage 4: DRUM FACTORY
                                                        ↓
                                                   Drums, rack, loops,
                                                   patterns, Stage 4 ALS
                                                   Audio manifest (5E)
                                                        ↓
                                                   SongMandate (return)
```

### Stage 1: IDENTITY (S1A–S1H) — "Who is this song?"

**Steps:** 8 | Every downstream stage traces back to constants + DNA forged here.

| Step | Print label | Module/Function | Output → `mandate.` field |
|------|------------|-----------------|---------------------------|
| S1A | *(implicit)* | Workflow constants (LOCKED) | PHI, FIBONACCI, SR, BEATS_PER_BAR, NOTES, SCALE_INTERVALS, _ZONE_RANGES, ALL_SYNTH_STEMS, platform detection — 26 constants, never change per song |
| S1B-α | *(implicit)* | Config-driven lookup tables | BPM_RANGES, STYLE_PROFILES, WORD_ATOMS, ARRANGEMENT_ARCHETYPES, morph/modulation maps — 10 tables (~635 LOC, flagged for YAML migration) |
| S1B-β | `→ S1B DNA...` | `_oracle(blueprint, dna, yaml_config)` | `dna` (153 fields: DrumDNA×21 + BassDNA×27 + LeadDNA×27 + AtmosphereDNA×16 + FxDNA×16 + MixDNA×21 + SongDNA×25), `beat_s`, `bar_s` |
| S1C | `→ S1C harmony...` | `_build_chord_progression(dna)` | `chord_progression` |
| S1D | `→ S1D freq table...` | `_build_freq_table(dna)` | `freq_table` |
| S1E | `→ S1E palette intent...` | `_design_palette_intent(dna)` | `design_intent` |
| S1F | `→ S1F template config...` | `_extract_sections(dna)` | `sections_raw` (local, consumed by S1G) |
| S1G | `→ S1G production recipe...` | `rb_select_recipe()` + `_build_recipes()` | `production_recipe`, `groove_template`, `quality_targets`, `arrange_tasks` |
| S1H | `→ S1H arrangement...` | `_build_arrangement_from_dna(dna)` + `_sections_from_arrangement()` | `arrangement_template`, `sections`, `total_bars`, `total_samples` |

**Energy derivation:** Each `SectionDef` in the arrangement has an `intensity` field (0–1).
Energy is read directly from `section.intensity` — no RCO abstraction. The energy map
(`section_name → (energy, energy)`) is built by `_build_energy_map(dna)` in `stage_integrations.py`.

### Stage 2: MIDI SEQUENCES (2A–2B) — "What notes play?"

**Steps:** 2 | Section-aware MIDI for all stems + pre-load FX samples.

| Step | Print label | Module/Function | Output → `mandate.` field |
|------|------------|-----------------|---------------------------|
| 2A | `→ 2A generate MIDI sequences...` | `_configure_stem_specs(mandate)` → `_generate_midi_sequences(mandate, configs)` | `midi_sequences` (10 stems + ghost_kick) |
| 2B | `→ 2B collect FX samples...` | `_collect_fx_samples(intent)` | `galactia_fx` (GalactiaFxSamples) |

**MIDI sequences generated:**
- 10 synth stems: sub_bass, mid_bass, neuro, wobble, riddim, lead, chords, arps, supersaw, pad
- 1 ghost kick: quarter-note C1 triggers for sidechain, velocity from `section.intensity`
- Section-aware: each clip matches `arrangement_template` section boundaries
- `_midi_stem_configs` built at 2A for MIDI generation only (lightweight, no WT/mod data)
- At 3H, stem configs are REBUILT fresh via `_configure_stem_specs(mandate)` after 3A-3E populate WT/mod/FX data

### Stage 3: SYNTH FACTORY (3A–3K) — "Design + render all synth audio"

**Steps:** 11 | Wavetable pipeline → Serum 2 presets → Ableton bounce → production skeleton.

> Stage 2 provided MIDI sequences and Galactia FX.
> Stage 3 DESIGNS the sound (wavetables, modulation, FX, presets) and RENDERS it.
> Each song's DNA drives completely different wavetables, modulation, FX processing,
> and Serum 2 presets. No two songs ever produce the same output.

| Step | Print label | Module/Function | Output → `mandate.` field |
|------|------------|-----------------|---------------------------|
| 3A | `3A Intake:` | `_collect_wavetables()` | `wavetables` |
| 3B | `3B Generate:` | `_generate_dna_wavetables(dna, intent, wt)` | `wavetable_packs` |
| 3C | `3C Modulation:` | `_design_modulation_routes(dna, intent)` | `modulation_routes` |
| 3D | `3D FX chains:` | `_design_fx_chains(dna, intent)` | `fx_chains` |
| 3E | `3E Morph:` | `_select_morph_type(dna)` → `_morph_all_wavetables(...)` | `morph_wavetables` |
| 3F | `3F Presets:` | `s2_build_all_presets()` + `s2_get_preset_state_map()` | `serum2_presets`, `serum2_state_map` |
| ~~3G~~ | ~~`3G Synthesis...`~~ | **REMOVED v6.0.0** — Path B (Python sketch renders) deleted. All audio via Serum 2 → ALS → bounce exclusively. | — |
| 3H | `3H Configure...` | `_configure_stem_specs(mandate)` — **REBUILT** fresh after 3A-3E | `stem_configs` (with full WT/mod/FX data) |
| 3H+ | `3H+ Mutate...` | `_mutate_presets_dna(mandate, stem_configs)` | Updates `serum2_state_map` |
| 3I | `3I Build .als...` | `_build_render_als(mandate, configs, states, midi)` | `render_als_path` |
| 3I+ | `3I+ Audio manifest` | `_build_audio_manifest()` | `audio_manifest` (4E stem entries only) |
| 3J | `3J Bounce` | `_bounce_render_tracks(als_path, mandate=mandate)` | *(local bounces)* |
| **3J+** | **`3J+ Resample`** | **`_resample_passes(bounces, mandate, num_passes=3)`** | **Resampled bass WAVs (3 passes)** |
| 3K | `3K Collect` | `_collect_bounced_audio()` + `_build_production_skeleton()` | `audio_clips`, `production_als_path` |

**Why every song sounds different:**
```
DNA (S1) → mood, style, energy, key, scale, bpm, tuning_hz
         → different wavetable morphs (3E)
         → different LFO rates, mod depths, filter curves (3C)
         → different saturation types/drives, reverb decays, stereo widths (3D)
         → different chord voicings, melody contours, rhythmic patterns (2A)
         → per-element gain staging (MixDNA: sub/bass/lead/pad_gain_db)
         → sidechain character (MixDNA: attack/release/mode — pump vs hard_cut)
         → drum groove (DrumDNA: pattern_swing, hi_hat_separation_ms, sample categories)
         → bass texture (BassDNA: wavefold_mix, saturation_type/drive, wobble_lfo_shape, riddim_style)
         → lead expression (LeadDNA: ADSR envelope, glide_ms, arp_subdivision/style/octave)
         → spatial depth (AtmosphereDNA: reverb_type/predelay/width, pad_attack_ms)
         → FX character (FxDNA: riser/impact types, overdrive_type/amount)
         → humanized timing (MixDNA: humanize_strength + phi_sine/jitter method)
         → 10 completely unique Serum 2 stems per song
```

**The 10 Serum 2 stems:**
| Stem | Group | Base Preset |
|------|-------|-------------|
| `sub_bass` | bass | `DUBFORGE_Fractal_Sub` or `DUBFORGE_Deep_Sub` |
| `mid_bass` | bass | `DUBFORGE_Golden_Reese` |
| `neuro` | bass | `DUBFORGE_Phi_Growl` |
| `wobble` | bass | `DUBFORGE_Spectral_Tear` |
| `riddim` | bass | `DUBFORGE_Riddim_Minimal` |
| `lead` | lead | `DUBFORGE_Fibonacci_FM_Screech` |
| `chords` | lead | `DUBFORGE_Counter_Pluck` |
| `arps` | lead | `DUBFORGE_Phi_Arp` |
| `supersaw` | lead | *(init patch — dense detuned osc)* |
| `pad` | pad | `DUBFORGE_Granular_Atmosphere` |

**~~3G Synthesis~~ — REMOVED v6.0.0:**
Path B (9 Python sketch functions) has been deleted. All synth audio is now rendered
exclusively through the Serum 2 → Ableton ALS → AbletonOSC bounce pipeline.
The sketch functions (`_sketch_bass`, `_sketch_leads`, etc.) were standalone Python
synth engines that ignored the wavetable/modulation/FX design from 4A-4E.
Removing them ensures ALL audio benefits from DNA-driven WT morphing, mod matrix,
and FX chains designed earlier in the pipeline.

**3J+ Resampling — NEW v6.0.0 (Subtronics technique):**
After initial Serum 2 bounce (3J), bass stems go through 3 resample passes:

| Pass | Label | Devices | Purpose |
|------|-------|---------|---------|
| 1 | Grit | Saturator → Multiband Dynamics (OTT) → Utility | Body + harmonic saturation |
| 2 | Texture | Auto Filter → Phaser → Saturator → Utility | Formant resonance + comb filtering |
| 3 | Character | Frequency Shifter → Multiband Dynamics → Saturator → Utility | Metallic detuning + final OTT |

Only `_RESAMPLE_STEMS` are resampled: `neuro`, `wobble`, `riddim`, `mid_bass`.
`sub_bass` stays clean for club playback.

---

#### 3A–3F: Wavetable + Sound Design Pipeline

**3A Intake:** Collect existing wavetables from Galactia + phi_core fallback.

**3B Generate:** DNA-driven WT packs:
- FM tables scaled by `bass.fm_depth` (0–10 → 4–16 tables)
- Harmonic count from `lead.brightness` (0–1 → 6–16 tables)
- Growl pack gated by `distortion > 0.1`
- Phi-core root WT tuned to song key + root_freq
- Growl resampler gated by `distortion > 0.25`

**3C Modulation:** Per-stem-group mod matrix for Serum 2 (bass, lead, pad, fx).

**3D FX chains:** Per-stem-group Ableton FX rack design (saturation, sidechain, reverb, stereo).

**3E Morph:** DNA-informed wavetable morphing:
- Mood → morph type: dark=fractal, aggressive=granular, dreamy=spectral, mystic=phi_spline, euphoric=formant
- Style overrides: riddim=granular, tearout=fractal, melodic=spectral

**3F Presets:** Build Serum 2 presets + serialize to VST3 state bytes.

---

#### 3I: ALS Device Chain (v6.0.0 Expanded)

The render ALS per-stem device chain now includes OTT, formant filtering,
and comb/phaser effects. Chain varies by stem group:

**Bass stems** (sub_bass, mid_bass, neuro, wobble, riddim):
```
Serum 2 → Multiband Dynamics (OTT) → Saturator → Audio Effect Rack (wave folder)
        → Auto Filter (formant sweep) → Phaser (comb textures)
        → Compressor (sidechain) → Utility
```

**Lead stems** (lead, chords, arps, supersaw):
```
Serum 2 → Saturator → Phaser → Compressor (sidechain) → Reverb → Utility
```

**Pad stems** (pad):
```
Serum 2 → Compressor (sidechain) → Reverb → Utility
```

#### 3I+: Macro Automation (v6.0.0 — 5 Macros + Pitch Bend)

Per-stem automation written into the render ALS:

| Macro | Parameter | Behavior | Scale Source |
|-------|-----------|----------|-------------|
| Macro 1 | Filter cutoff | Section energy → open in drops, closed in intros, ramp in builds | `filter_mod_depth` from mod_matrix |
| Macro 2 | WT position | Sweep across drops for movement, static in breaks | `wt_mod_depth` from mod_matrix |
| Macro 3 | FM depth / growl | Aggressive in drops (×1.4 for bass), subdued in breaks | `fm_mod_depth` from mod_matrix |
| Macro 4 | Formant shift | Cyclic "yoi" sweep in drops (bass only) — low→high→low | `formant_depth` from mod_matrix |
| Macro 5 | LFO rate | Faster in builds (0.8), medium in drops (0.5), slow in intros (0.3) | `lfos` config |
| Pitch Bend | Octave dive | -12 semitones → center on drop transitions (bass only) | Threshold: prev_energy < 0.6 |

---

#### 4A: StemSynthConfig — Per-stem synthesis spec

For each of the 10 Serum 2 stems, pull together ALL relevant data into
a single `StemSynthConfig`. This is the "recipe card" for that stem — everything
needed to build its Serum 2 preset, write its MIDI, and configure its FX chain.

**Stem → S3 stem group mapping:**
| Stem | Group | Why |
|------|-------|-----|
| `sub_bass` | `bass` | Sub-frequency layer |
| `mid_bass` | `bass` | Mid-bass body |
| `neuro` | `bass` | Aggressive textured bass |
| `wobble` | `bass` | LFO-modulated bass |
| `riddim` | `bass` | Gap-pattern bass |
| `lead` | `lead` | Melodic lead |
| `pad` | `pad` | Sustained atmospheric |
| `chords` | `lead` | Harmonic voicings |
| `arps` | `lead` | Rhythmic melodic patterns |
| `supersaw` | `lead` | Dense detuned layer |

**What `StemSynthConfig` contains:**

```python
@dataclass
class StemSynthConfig:
    stem_name: str                          # e.g. "sub_bass"
    stem_group: str                         # "bass" | "lead" | "pad"

    # --- From S3C: modulation_routes[group] ---
    mod_matrix: list[ModulationRoute]       # Serum 2 mod slots for this group
    lfos: list[LFOPreset]                   # BPM-synced LFO configs

    # --- From S3D: fx_chains[group] ---
    saturation: SatConfig                   # Tube/tape/hard etc, DNA-driven drive
    sidechain: SidechainPreset | None       # Pump/hard_cut, BPM-timed
    stereo: StereoPreset | None             # Haas/mid_side/freq_split
    reverb: ReverbDelayPreset | None        # Room/hall/plate/shimmer
    wave_folder: WaveFolderPatch | None     # For bass stems only
    pitch_auto: PitchAutoPreset | None      # For bass/fx stems

    # --- From S3B/S3E: wavetable_packs + morph_wavetables ---
    wavetable_frames: list[np.ndarray]      # Selected WT frames for this stem's oscillator
    morph_frames: list[np.ndarray] | None   # Morphed WT variants (mood-driven morph algo)

    # --- From S3F: serum2_presets ---
    base_preset_name: str                   # Which S3F recipe to start from
    base_preset: SerumPreset                # The preset object to mutate

    # --- From S1: identity ---
    root_midi: int                          # MIDI note for root
    bpm: float                              # Tempo
    key: str                                # Musical key
    scale: str                              # Scale type
    mood: str                               # Drives morph type, saturation character
    style: str                              # Drives pattern selection, aggression level
    energy: float                           # 0-1, drives intensity of all processing
```

**Stem → base preset mapping** (from S3F's 14 recipes):
| Stem | Base Preset | Reason |
|------|-------------|--------|
| `sub_bass` | `DUBFORGE_Fractal_Sub` or `DUBFORGE_Deep_Sub` | DNA energy selects sub type |
| `mid_bass` | `DUBFORGE_Golden_Reese` | Reese-chord bass body |
| `neuro` | `DUBFORGE_Phi_Growl` | Aggressive growl texture |
| `wobble` | `DUBFORGE_Spectral_Tear` | Modulated wobble |
| `riddim` | `DUBFORGE_Riddim_Minimal` | Minimal gap bass |
| `lead` | `DUBFORGE_Fibonacci_FM_Screech` | FM lead |
| `pad` | `DUBFORGE_Granular_Atmosphere` | Atmospheric pad |
| `chords` | `DUBFORGE_Counter_Pluck` | Pluck chord stabs |
| `arps` | `DUBFORGE_Phi_Arp` | Rhythmic arp |
| `supersaw` | — (built from init patch) | Dense detuned osc (no factory recipe) |

**Wavetable selection per stem** (from S3B packs + S3E morphs):
| Stem | Primary wavetable source | Morph source |
|------|-------------------------|-------------|
| `sub_bass` | `phi_root_{key}_{scale}` (if available) else default sine | — |
| `mid_bass` | FM ratio sweep pack | `*_spectral_crush` or `*_phi_spline` (mood-driven) |
| `neuro` | Growl vowel pack OR growl_resample | `*_fractal` or `*_spectral_crush` |
| `wobble` | FM ratio sweep pack | Mood-driven morph |
| `riddim` | Growl vowel pack (if available) else FM sweep | `*_spectral_crush` |
| `lead` | Harmonic sweep pack | `*_spectral_blend` or `*_formant` |
| `pad` | Harmonic sweep pack or morph pack | `*_phi_spline` or `*_spectral_blend` |
| `chords` | Harmonic sweep pack | — |
| `arps` | Harmonic sweep pack | — |
| `supersaw` | Default saw (detuned multi-voice — Serum 2 native) | — |

---

#### 3H+: PRESETS — DNA-mutate Serum 2 presets for each stem

This is where Stage 3 data becomes UNIQUE sound. For each stem:

1. **Start from base preset** (`stem_config.base_preset` — SerumPreset object from S3F)
2. **Inject wavetable frames** into oscillator state:
   - `stem_config.wavetable_frames` → Osc A wavetable position 0–N
   - `stem_config.morph_frames` → Osc B wavetable position (or Osc A sweep range)
   - If morph frames exist, set WT position modulation (LFO sweeps through morph)
3. **Bake modulation matrix** from `stem_config.mod_matrix`:
   - Each `ModulationRoute` → `preset.set_mod_slot(idx, source, dest, amount, curve, ...)`
   - Supports up to 64 slots — S3C typically fills 2–5 per stem group
   - Routes are DNA-driven: LFO rates from BPM, depths from energy/distortion
4. **Set LFO parameters** from `stem_config.lfos`:
   - LFO type (sine/saw/square/S&H — mood-driven)
   - Rate Hz (BPM-synced via `sync_division`)
   - Depth (energy-driven)
5. **Apply per-stem parameter mutations** based on DNA:
   - `sub_bass`: Filter cutoff low (< 120 Hz), mono, minimal modulation
   - `neuro`: High distortion → more aggressive WT position, higher mod depth
   - `wobble`: LFO rate directly from `modulation_routes["bass"]["lfos"]`
   - `lead`: Brightness → filter cutoff, FM depth → operator ratio
   - `pad`: Stereo width → Serum 2 unison detune, reverb_decay → release time
6. **Serialize to VST3 state bytes:**
   - `preset.get_processor_state()` → processor bytes (sound params)
   - `preset.get_controller_state()` → controller bytes (UI state)
   - Store in `serum2_state_map[stem_name] = (proc_bytes, ctrl_bytes)`

**What makes each song's presets unique:**
| DNA field | Effect on preset |
|-----------|-----------------|
| `mood` → morph type | Different wavetable character in Osc A/B |
| `style` → aggression | neuro/riddim get more distortion, lead/pad get cleaner |
| `bpm` → LFO rates | Faster songs = faster modulation = different filter movement |
| `energy` → mod depths | High energy = deeper filter sweeps, more WT position movement |
| `bass.distortion` → fold/sat | Higher distortion = more wave folding in bass presets |
| `bass.filter_cutoff` → cutoff | Drives Serum 2 filter starting position |
| `lead.brightness` → harmonics | Brighter leads = higher harmonic sweep range |
| `atmosphere.reverb_decay` → release | Longer pads for ambient moods |
| `chord_progression` → voicing | Different inversions = different WT position bias |

**Output:** `mandate.serum2_state_map: dict[str, tuple[bytes, bytes]]`
— 10 unique VST3 binary states, one per Serum 2 track.
These bytes go directly into `ALSTrack.preset_states["Serum 2"]` in step 4D.

**Without `cbor2`:** Falls back to init-patch state (Serum 2 loads but with default sound).

---

#### 2A/3C: MIDI — Generate DNA-driven MIDI for all 10 stems

MIDI generation is where S1 data (chords, arrangement, energy) meets S3 data
(modulation rates, rhythmic parameters). Generated at Step 2A. Every note, velocity,
and timing decision is DNA-derived — never hardcoded.

**S1–S3 inputs per stem:**

| Input | Source | Drives |
|-------|--------|--------|
| `dna.bpm` | S1B | Note durations, step timing, LFO sync |
| `dna.key` + `dna.scale` | S1B | Root MIDI note, scale degrees |
| `chord_progression` | S1C | Voicings for chords/pads, melody guide tones |
| `freq_table` | S1D | Pitch-to-MIDI conversion |
| `arrangement_template` | S1H | Section boundaries (intro/build/drop), which stems play where |
| `section.intensity` | S1H | Velocity/intensity scaling per section |
| `modulation_routes[group].lfos` | S3C | LFO rates → wobble speed, arp rate, CC automation |
| `design_intent` | S1E | Palette character → pattern style selection |

**Per-stem MIDI generation:**

| # | Stem | MIDI driving logic | What makes it unique |
|---|------|-------------------|---------------------|
| 1 | **SUB BASS** | Root note sustained per bar. Velocity from `section.intensity` | Energy shapes dynamics — drops hit harder |
| 2 | **MID BASS** | Bass rotation — 6 types cycling per section. Notes from `design_intent.bass_character` | Style (riddim vs melodic) changes rotation order |
| 3 | **NEURO** | Rhythmic 1/16 hits at root. Velocity accent patterns from `drum_loops` grid swing | BPM + swing amount = different rhythm feel |
| 4 | **WOBBLE** | Sustained root note + CC1 envelope. LFO rate from `modulation_routes["bass"]["lfos"][0].rate_hz` | Different BPM = different wobble speed |
| 5 | **RIDDIM** | Gap patterns — notes with calculated silence ratios. Gap width from `dna.bass.distortion` | More distortion = tighter gaps = more aggressive |
| 6 | **LEAD** | Inline scale-locked random walks from `chord_progression` via `_generate_stem_midi()` + `_get_scale_midi_notes()`. Uses `NOTES`/`SCALE_INTERVALS` from `variation_engine` — NOT `markov_melody.py` (that's 4G `_sketch_melody()` audio only) | Different chord progression = entirely different melody |
| 7 | **PAD** | Chord tones sustained per section boundary. Voicings from `chord_progression.chords[section]` | Different chords + section lengths = different pad movement |
| 8 | **CHORDS** | Chord voicings as stabs at section changes. Inversions from `chord_progression` | Rhythmic placement follows `arrangement_template` energy |
| 9 | **ARPS** | Step-sequenced scale degrees. Step count from BPM, pattern from `design_intent` | BPM drives arp speed, mood drives pattern shape |
| 10 | **SUPERSAW** | Rising swell in build sections + sustained drop notes. Filter CC ramp from `section.intensity` | Build energy = different swell shape |

**CC automation (embedded in MIDI clips):**
- CC1 (Mod Wheel) → Serum 2 macro for filter cutoff or WT position
- CC values derived from `section.intensity` × `modulation_routes` depth
- Drop sections: CC peaks at 127 (full mod depth)
- Intro/outro: CC at 20–60 (gentle modulation)

**Section-aware generation:**
MIDI clips are section-length, not full-song. Each section from `arrangement_template`
(intro, build_1, drop_1, breakdown, build_2, drop_2, outro) gets its own clip with
appropriate intensity from `section.intensity`.

Output: `mandate.midi_sequences: dict[str, list[ALSMidiNote]]`

**Ghost kick MIDI generation:**
In addition to the 10 synth stems, 2A generates a GHOST KICK pattern — a silent
sidechain trigger track. This is the Subtronics/Producer Dojo "silent kick" technique:
a MIDI track that plays a kick pattern at the song BPM but is **never heard** in
the mix. Its sole purpose is to feed the sidechain input of Compressor devices
on bass and synth tracks, creating the signature dubstep pump.

```python
# Ghost kick: quarter-note hits on every beat, velocity from energy curve
ghost_kick_notes = []
for section in arrangement_template.sections:
    beats_in_section = section.bars * 4
    for beat in range(beats_in_section):
        velocity = int(80 + 47 * section.intensity)
        ghost_kick_notes.append(ALSMidiNote(
            pitch=36,  # C1 — standard kick MIDI note
            start_beat=section_offset + beat,
            duration_beats=0.25,  # Short trigger
            velocity=velocity,
        ))
midi_sequences["ghost_kick"] = ghost_kick_notes
```

The ghost kick velocity tracks `section.intensity` — drops pump harder,
intros/outros pump lighter. Section-aware: only generates notes for sections where
`"sidechain"` appears in the arrangement template's `elements` list.

---

#### Sidechain Architecture — Dual-Layer Pumping

DUBFORGE implements sidechain at **two levels**, combining the best of both approaches
from professional dubstep production (Subtronics, Virtual Riot, EDMProd workflows):

**Layer 1: Internal Serum 2 LFO Sidechain (baked into preset)**
- During 4B PRESETS, bass stems get an LFO with a sidechain-shaped curve
- Serum 2's LFO section has built-in "Sidechain" shape presets (pump, hard cut, etc.)
- LFO is BPM-synced and assigned to master volume or filter cutoff
- Creates internal tonal pumping that lives inside the synth
- Controlled via Serum 2 Macro → DAW automation for section-aware depth
- `SidechainPreset.shape` drives the LFO curve selection
- `SidechainPreset.depth` drives the LFO mod amount (0–1)

**Layer 2: External Ableton Compressor Sidechain (ghost kick routing)**
- Ghost kick MIDI track (Track 0) feeds Compressor sidechain input on all ducked tracks
- Ableton Compressor with `SideChain.OnOff=true`, routed from ghost kick track
- Attack/release/ratio derived from `SidechainPreset` parameters
- Ghost kick track output is **muted** (volume -inf dB) — trigger only, never heard
- This is the classic "mix sidechain" that respects the actual kick rhythm

**Which stems get which layer:**
| Stem | Layer 1 (Serum LFO) | Layer 2 (Ghost Kick SC) | Why |
|------|---------------------|------------------------|-----|
| `sub_bass` | Subtle volume LFO | Full compressor duck | Sub MUST clear for kick |
| `mid_bass` | Filter cutoff LFO | Full compressor duck | Mid-bass body ducks hard |
| `neuro` | Filter cutoff LFO | Medium compressor duck | Aggressive but needs space |
| `wobble` | — (already has wobble LFO) | Medium compressor duck | Wobble LFO is the primary motion |
| `riddim` | — (gap pattern provides space) | Light compressor duck | Gaps already provide rhythmic space |
| `lead` | — | Light compressor duck | Leads duck gently for kick clarity |
| `pad` | — | Medium compressor duck | Pads are sustained, need ducking |
| `chords` | — | Light compressor duck | Chord stabs have natural gaps |
| `arps` | — | Light compressor duck | Arps are fast, gentle duck keeps rhythm |
| `supersaw` | — | Medium compressor duck | Dense layers need space for kick |

**Compressor depth tiers** (from `SidechainPreset` → Ableton Compressor params):
| Tier | Threshold | Ratio | Attack | Release | Use |
|------|-----------|-------|--------|---------|-----|
| Full | -30 dB | 8:1 | 0.5 ms | 100–200 ms | Sub/mid bass — maximum clarity |
| Medium | -24 dB | 4:1 | 1 ms | 80–150 ms | Pads, neuro, supersaw |
| Light | -18 dB | 2:1 | 2 ms | 60–120 ms | Leads, chords, arps |

**Section-awareness:** Sidechain compressor is only active in sections where
`"sidechain"` appears in the arrangement template's `elements` list (drops, expands).
In intros, breakdowns, and outros, the sidechain is bypassed — no pumping.

**Sidechain EQ filter** (Ableton Compressor sidechain EQ section):
- High-pass at 80 Hz on the sidechain input — the ghost kick's low rumble
  shouldn't trigger the compressor, only the transient click above 80 Hz
- This gives a tighter, more controlled pump (EDMProd best practice)

---

#### 3I: ALS — Build the render session `.als`

Build a temporary Ableton Live 12 set specifically for bouncing Serum 2 synth stems.
This is NOT the final arrangement — it's a **ghost kick + 10 Serum 2 track** render session.
**Every track includes its full FX chain + sidechain routing + modulation automation so bounces are WET.**

**Track layout:**

| # | Track | Type | Purpose |
|---|-------|------|---------|
| 0 | GHOST_KICK | midi | Silent sidechain trigger — volume=-inf, Drum Rack with short kick sample |
| 1–10 | Serum 2 stems | midi | Synth tracks with Compressor sidechain routed from Track 0 |

**Serum 2 MIDI tracks (1–10):**

| # | Track | Devices (in chain order) | State | FX from `stem_config` | MIDI | Automation |
|---|-------|--------------------------|-------|----------------------|------|------------|
| 1 | SUB BASS | Serum 2 → Saturator → **Compressor (SC←GhostKick)** → EQ Eight | `serum2_state_map["sub_bass"]` | `fx_chains["bass"]` (sub-filtered) | `midi_sequences["sub_bass"]` | `modulation_routes["bass"]` |
| 2 | MID BASS | Serum 2 → Saturator → **Compressor (SC←GhostKick)** → EQ Eight | `serum2_state_map["mid_bass"]` | `fx_chains["bass"]` | `midi_sequences["mid_bass"]` | `modulation_routes["bass"]` |
| 3 | NEURO | Serum 2 → Saturator → Wave Folder → **Compressor (SC←GhostKick)** | `serum2_state_map["neuro"]` | `fx_chains["bass"]` (heavy sat) | `midi_sequences["neuro"]` | `modulation_routes["bass"]` |
| 4 | WOBBLE | Serum 2 → Saturator → **Compressor (SC←GhostKick)** → EQ Eight | `serum2_state_map["wobble"]` | `fx_chains["bass"]` | `midi_sequences["wobble"]` | `modulation_routes["bass"]` |
| 5 | RIDDIM | Serum 2 → Saturator → Wave Folder → **Compressor (SC←GhostKick)** | `serum2_state_map["riddim"]` | `fx_chains["bass"]` | `midi_sequences["riddim"]` | `modulation_routes["bass"]` |
| 6 | LEAD | Serum 2 → Reverb → Delay → Stereo Width → **Compressor (SC←GhostKick)** | `serum2_state_map["lead"]` | `fx_chains["lead"]` | `midi_sequences["lead"]` | `modulation_routes["lead"]` |
| 7 | PAD | Serum 2 → Reverb → Delay → Stereo Width → **Compressor (SC←GhostKick)** → EQ Eight | `serum2_state_map["pad"]` | `fx_chains["pad"]` | `midi_sequences["pad"]` | `modulation_routes["pad"]` |
| 8 | CHORDS | Serum 2 → Reverb → Stereo Width → **Compressor (SC←GhostKick)** | `serum2_state_map["chords"]` | `fx_chains["lead"]` | `midi_sequences["chords"]` | `modulation_routes["lead"]` |
| 9 | ARPS | Serum 2 → Delay → Reverb → Stereo Width → **Compressor (SC←GhostKick)** | `serum2_state_map["arps"]` | `fx_chains["lead"]` | `midi_sequences["arps"]` | `modulation_routes["lead"]` |
| 10 | SUPERSAW | Serum 2 → Reverb → Stereo Width → **Compressor (SC←GhostKick)** | `serum2_state_map["supersaw"]` | `fx_chains["lead"]` | `midi_sequences["supersaw"]` | `modulation_routes["lead"]` |

**Ghost Kick Track (Track 0) configuration:**
```
Name:           GHOST_KICK
Type:           MIDI track
Volume:         -inf dB (muted output — trigger only, never heard)
Color:          COLOR_GREY
Device:         Drum Rack with single pad → short kick oneshot sample (~50ms)
MIDI:           midi_sequences["ghost_kick"] — quarter notes on every beat
Output routing: Master (but volume is -inf, so no audio reaches master)
Purpose:        Sidechain source for Compressor devices on tracks 1–10
```

**Compressor sidechain routing in ALS XML:**
```xml
<Compressor2>
  ...
  <SideChain>
    <OnOff><Manual>true</Manual></OnOff>
    <RoutedFrom>
      <Target>AudioIn/TrackIn/S0</Target>          <!-- Ghost Kick track index -->
      <UpperDisplayString>GHOST_KICK</UpperDisplayString>
      <LowerDisplayString>Post FX</LowerDisplayString>
    </RoutedFrom>
    <DryWet><Manual>1</Manual></DryWet>
  </SideChain>
</Compressor2>
```

**FX chain → Ableton device translation:**
| S3D config type | Ableton device | Parameters mapped |
|-----------------|---------------|-------------------|
| `SatConfig` | Saturator | type → mode, drive → drive, tone → color, mix → dry/wet |
| `SidechainPreset` | Compressor (sidechain ON, routed from GHOST_KICK) | shape → ratio/attack/release, depth → threshold, SC EQ HP 80Hz |
| `StereoPreset` | Utility + Stereo Width rack | image_type → mode, width → width, delay_ms → haas delay |
| `ReverbDelayPreset` | Reverb + Delay | effect_type → algorithm, decay → decay, mix → dry/wet |
| `WaveFolderPatch` | Audio Effect Rack | fold_amount → drive, symmetry → shape, mix → dry/wet |
| `PitchAutoPreset` | Pitch rack (automation) | auto_type → curve shape, semitones → range |

**Automation envelopes** from `modulation_routes[group]`:
- Each `ModulationRoute` targeting an FX parameter → Ableton automation lane
- LFO rate → mapped to Serum 2 macro or filter cutoff automation
- Mod depth → filter envelope amount over time
- FX sweeps → reverb mix, delay feedback ramps synced to section boundaries

**All 10 tracks bounce WET.** Every track has its full signal chain baked in at export time.

Device name: `"Serum 2"` (with space — matches `_VST3_REGISTRY` key).
`ALSTrack.preset_states["Serum 2"]` + `ALSTrack.controller_states["Serum 2"]`.
`ALSTrack.fx_devices = [...]` — translated from `fx_chains[stem_group]`.
`ALSTrack.automations = [...]` — envelopes from `modulation_routes[stem_group]`.
MIDI clips placed in arrangement view at beat 0.

Output: `output/ableton/_render_session.als`

---

#### 3J: BOUNCE — Open in Live 12 and bounce Serum 2 tracks

**The critical step.** This is where DNA-designed sounds become real audio.

**Bounce readiness check (v4.2.0):**
Before starting exports, `_bounce_auto` verifies that Ableton has fully loaded the
new ALS project by checking:
1. **Expected BPM** — waits until tempo matches `dna.bpm` (±1 BPM tolerance)
2. **Expected track count** — verifies track count = 11 (ghost kick + 10 stems)
3. **Plugin grace period** — 15s wait after ALS load for Serum 2 instances to initialize

This prevents the race condition where Ableton is still loading while export begins.

**Workflow via `AbletonBridge` (OSC → AbletonOSC remote script):**

```
1. bridge.connect()  — verify AbletonOSC is running
2. Open _render_session.als:
     subprocess.Popen(["open", "-a", "Ableton Live 12 Standard", als_path])
3. Wait for Ableton to load + restore all Serum 2 instances
4. For each track (1–10):
   a. Solo the track:       bridge.set_track_solo(track_idx, True)
   b. Set loop region:      bridge.set_loop(True, 0, clip_length_beats)
   c. Trigger Cmd+Shift+R via osascript (Export Audio/Video)
   d. Or: use arrangement record with resampling track
   e. Unsolo:               bridge.set_track_solo(track_idx, False)
5. Collect exported WAVs from Ableton's export path
```

**Export automation (macOS):**
```bash
osascript -e 'tell application "System Events" to keystroke "r" using {command down, shift down}'
```
This triggers Ableton's Export Audio/Video dialog. The export settings (WAV, 48kHz, 24-bit)
must be pre-configured in Ableton preferences.

**Alternative: Freeze + Flatten workflow:**
- AbletonOSC can't directly trigger freeze/flatten (requires right-click menu)
- But we can detect when tracks are frozen by monitoring CPU load
- Flattened tracks become audio — we read those WAVs from the Ableton project folder

**Fallback: Manual bounce prompt:**
If AbletonOSC is not connected or osascript fails, Stage 4E prints instructions:
```
ACTION REQUIRED: Open output/ableton/_render_session.als in Ableton Live 12
Solo each track → Cmd+Shift+R → Export to output/bounces/{stem_name}.wav
```

**Output:** `output/bounces/` directory with one WAV per Serum 2 track:
`sub_bK: COLLECT — Gather + validate all Serum 2 bounced WAVs + production skeletoniddim.wav`,
`lead.wav`, `pad.wav`, `chords.wav`, `arps.wav`, `supersaw.wav`

**These are DNA-unique audio files.** The Serum 2 presets were mutated with song-specific
wavetables, modulation, and FX. The MIDI was generated from the song's chords and energy.
No two songs will ever produce the same bounce output.

---

#### 3K: COLLECT — Gather + validate all Serum 2 bounced WAVs

Collect all 10 Serum 2 bounces from 3J into a single registry.

```python
audio_clips: dict[str, Path] = {
    "sub_bass": Path("output/bounces/sub_bass.wav"),
    "mid_bass": Path("output/bounces/mid_bass.wav"),
    "neuro": Path("output/bounces/neuro.wav"),
    "wobble": Path("output/bounces/wobble.wav"),
    "riddim": Path("output/bounces/riddim.wav"),
    "lead": Path("output/bounces/lead.wav"),
    "pad": Path("output/bounces/pad.wav"),
    "chords": Path("output/bounces/chords.wav"),
    "arps": Path("output/bounces/arps.wav"),
    "supersaw": Path("output/bounces/supersaw.wav"),
}
```

**Validation:** Check each WAV exists, has non-zero length, and is at the correct sample rate (48 kHz).

Output: `mandate.audio_clips: dict[str, Path]` + `mandate.production_als_path`

`_collect_bounced_audio()` registers WAVs into the audio manifest.
`_build_production_skeleton()` builds the production `.als` with 10 audio tracks + MIDI editing tracks.

---

#### Requirements for 3J BOUNCE workflow

| Requirement | Status | Notes |
|-------------|--------|-------|
| AbletonOSC remote script installed | Required | [github.com/ideoforms/AbletonOSC](https://github.com/ideoforms/AbletonOSC) |
| `python-osc` package | Required | `pip install python-osc` |
| Ableton Live 12 running | Required | macOS: `/Applications/Ableton Live 12 Standard.app` |
| Serum 2 VST3 installed | Required | `/Library/Audio/Plug-Ins/VST3/Serum2.vst3` |
| macOS Accessibility permissions | Required for osascript | System Settings → Privacy → Accessibility |
| Export settings pre-configured | Required | WAV, 48kHz, 24-bit, no dither |

**Fallback modes:**
1. **Full auto:** AbletonOSC connected + osascript → fully automated bounce
2. **Semi-auto:** AbletonOSC connected, no osascript → bridge solos tracks, user hits Cmd+Shift+R
3. **Manual:** No AbletonOSC → prints step-by-step instructions, user bounces manually

### Stage 4: DRUM FACTORY (4A–4G) — "Samples, rack, loops, patterns"

**Steps:** 7+ | Drums and samples collected, racked, looped, patterned, bounced.

> Stage 4 handles ALL physical audio (drums, FX, Galactia samples).
> Synth audio (Serum 2 stems) was handled in Stage 3.
> No synth content goes into the 128 Rack — drums + FX only.

| Step | Print label | Module/Function | Output → `mandate.` field |
|------|------------|-----------------|---------------------------|
| 4A | `4A Drums:` | `_collect_drums(dna, intent)` | `drums` (DrumKit) |
| 4B | `4B FX samples:` | *(already collected at 2B)* | `galactia_fx` (logged only) |
| 4B+ | `4B+ Mapping Galactia...` | `map_galactia_to_zones()` | `galactia_zone_map` |
| 4C | `4C Processing drums...` | `_sketch_drums(drums, dna)` | `drums` (processed) |
| 4D | `4D Building 128 Rack...` | `_build_128_rack(drums, galactia_fx)` + `_rack_add(galactia_zone_map)` + `_build_rack_midi_map()` | `rack_128`, `rack_midi_map` |
| 4E | `4E Building drum loops...` | `_build_drum_loops(drums, dna, sections)` + `_build_loop_midi_maps(...)` | `drum_loops`, `loop_midi_maps` |
| 4F | `4F Pattern Factory` | Inline pattern generation + audio manifest update (5E entries) + FX chains | `render_patterns`, `audio_manifest` (5E entries added here), `fx_chains["stage4"]` |
| 4G | `→ 4G Build Stage 4 render .als...` | `_build_stage5_als(mandate)` → `_bounce_stage5_patterns()` → `_collect_stage5_renders()` + rebuild loop MIDI maps | `stage5_als_path`, `stage5_renders`, `loop_midi_maps` (rebuilt) |

---

#### 4D: `_build_128_rack(drums, galactia_fx)` — 2-argument signature

Takes ONLY drums and FX. No synth content. Populates 14 Fibonacci-sized zones:

**Drums:**
| Source | Target Zone |
|--------|-------------|
| `drums.kick` | kicks (37–49) |
| `drums.snare` | snares (50–62) |
| `drums.clap` | snares (50–62) |
| `drums.hat_closed` | hats (63–70) |
| `drums.hat_open` | hats (63–70) |
| `drums.crash` | perc (71–83) |
| `drums.ride` | perc (71–83) |
| `drums.perc` | perc (71–83) |

**Galactia FX (inline zone filling):**
| Source | Target Zone |
|--------|-------------|
| `galactia_fx.risers[:5]` | fx (84–96) |
| `galactia_fx.impacts[:5]` | fx (84–96) |
| `galactia_fx.falling[:3]` | fx (84–96) |
| `galactia_fx.rising[:3]` | fx (84–96) |
| `galactia_fx.shepard[:2]` | fx (84–96) |
| `galactia_fx.buildups[:3]` | transitions (118–122) |

After `_build_128_rack`, `_rack_add` loads additional Galactia zone map samples into remaining empty slots.

---

#### 4F: Pattern Factory — `_ROLE_ZONES` mapping

| Role | Active zones |
|------|-------------|
| intro | kicks, hats, fx |
| build | kicks, snares, hats, perc, fx, transitions |
| drop | kicks, snares, hats, perc, fx |
| break | hats, perc |
| bridge | kicks, hats, fx |
| verse | kicks, snares, hats, perc |
| outro | kicks, hats |
| vip | kicks, snares, hats, perc, fx, transitions |

**Pattern generation rules:**
- **kicks**: Beat 0.0 and 2.0 per bar, vel=100
- **snares**: Drop/VIP → beat 3.0 vel=110; else → beat 2.0 vel=90
- **hats**: 8 eighths per bar, alternating vel 80/60, cycling through zone_slots
- **fx/transitions**: One hit at time 0.0 dur=4.0 vel=80; if >4 bars + >1 slot, second hit at `(n_bars-2)*4.0` dur=8.0 vel=75
- **perc**: Odd sixteenths (1,3,5,7,9,11,13,15) per bar, vel=65

**5F+ FX chains:** Hardcoded per zone group:
- kicks → Compressor
- snares → Compressor + Reverb
- hats → EQ + Compressor
- perc → Saturator + Delay
- fx → Reverb + Delay
- transitions → AutoFilter + Reverb

---

#### 4G: Stage 4 Render ALS

`_build_stage5_als(mandate)` creates:
- **Track 0:** GHOST_KICK — MIDI, volume=-70dB, quarter-note C1 triggers
- **Track 1:** 128 RACK — Drum Rack with all pads + FX chains, MIDI clips laid out
  sequentially (one per section × zone_group) separated by silence gaps

Writes to `output/ableton/{name}_stage5_render.als`.
Bounce via `_bounce_stage5_patterns()` (same 3-tier automation as 4J).
Collect via `_collect_stage5_renders()`.
Loop MIDI maps rebuilt against the FULL rack (after Galactia zones added).

---

## Input Contract

| Input | Type | Required | Notes |
|-------|------|----------|-------|
| `blueprint` | `SongBlueprint` | No | Name, style, mood, key, BPM, tags |
| `dna` | `SongDNA` | No | Pre-computed DNA (bypasses IDENTITY) |
| `yaml_path` | `str` | No | Path to YAML config |

At least one must be provided. Priority: `dna` > `yaml_path` > `blueprint` > default.

---

## Output Contract — SongMandate (42 fields)

### Identity
| Field | Type | Stage | Status |
|-------|------|-------|--------|
| `dna` | `SongDNA` | 1B | ✅ LIVE — consumed by ALL stages |

### Timing
| Field | Type | Stage | Status |
|-------|------|-------|--------|
| `beat_s` | `float` | 1B | ✅ LIVE — `60/bpm` |
| `bar_s` | `float` | 1B | ✅ LIVE — `beat_s * 4` |
| `freq_table` | `dict[str, float]` | 3B | ⚠️ ORPHAN — assigned but never read downstream |

### Section map
| Field | Type | Stage | Status |
|-------|------|-------|--------|
| `sections` | `dict[str, int]` | 2C | ✅ LIVE |
| `total_bars` | `int` | 2C | ✅ LIVE |
| `total_samples` | `int` | 2C | ✅ LIVE |

### Arrangement + energy
| Field | Type | Stage | Status |
|-------|------|-------|--------|
| `arrangement_template` | `ArrangementTemplate` | S1H | ✅ LIVE — 2A MIDI, 3I ALS, 4F patterns |

### Production
| Field | Type | Stage | Status |
|-------|------|-------|--------|
| `production_recipe` | `Recipe` | S1G | ✅ LIVE — enriches quality_targets |
| `groove_template` | `str` | S1G | ✅ LIVE |
| `quality_targets` | `dict` | S1G | ✅ LIVE |
| `arrange_tasks` | `list[str]` | S1G | ✅ LIVE — Phase 2 instructions |
| `design_intent` | `dict` | S1E | ✅ LIVE — 4A drums, FX, 3A–3G |

### Harmonic + melodic
| Field | Type | Stage | Status |
|-------|------|-------|--------|
| `chord_progression` | `ChordProgression` | S1C | ✅ LIVE — 2A melody MIDI |

### Sound palette
| Field | Type | Stage | Status |
|-------|------|-------|--------|
| `drums` | `DrumKit` | 4A/4C | ✅ LIVE |
| `drum_loops` | `DrumLoopKit` | 4E | ✅ LIVE |
| `bass` | `BassArsenal` | 3G | ✅ LIVE |
| `leads` | `LeadPalette` | 3G | ✅ LIVE |
| `atmosphere` | `AtmosphereKit` | 3G | ✅ LIVE |
| `fx` | `FxKit` | 3G | ✅ LIVE |
| `vocals` | `VocalKit` | 3G | ✅ LIVE |
| `wavetables` | `WavetableKit` | 3A | ✅ LIVE |
| `galactia_fx` | `GalactiaFxSamples` | 2B | ✅ LIVE — 3G fx, 4D rack |
| `melody` | `MelodyKit` | 3G | ✅ LIVE |
| `wobble_bass` | `WobbleBassKit` | 3G | ✅ LIVE |
| `riddim_bass` | `RiddimBassKit` | 3G | ✅ LIVE |
| `growl_textures` | `GrowlKit` | 3G | ✅ LIVE |

### Infrastructure
| Field | Type | Stage | Status |
|-------|------|-------|--------|
| `rack_128` | `Rack128` | 4D | ✅ LIVE |
| `rack_midi_map` | `RackMidiMap` | 4D | ✅ LIVE |
| `loop_midi_maps` | `list[LoopMidiMap]` | 4G | ✅ LIVE (rebuilt twice) |
| `galactia_zone_map` | `Any` | 4B+ | ✅ LIVE |

### Sound design (Stage 4)
| Field | Type | Stage | Status |
|-------|------|-------|--------|
| `modulation_routes` | `dict` | 3C | ✅ LIVE |
| `fx_chains` | `dict` | 3D/4F+ | ✅ LIVE |
| `wavetable_packs` | `list[tuple]` | 3B | ✅ LIVE |
| `morph_wavetables` | `dict` | 3E | ✅ LIVE |
| `serum2_presets` | `dict` | 3F | ✅ LIVE |
| `serum2_state_map` | `dict[str, tuple[bytes, bytes]]` | 3F/3H+ | ✅ LIVE |

### Serum 2 + ALS
| Field | Type | Stage | Status |
|-------|------|-------|--------|
| `stem_configs` | `dict[str, StemSynthConfig]` | 3H | ✅ LIVE |
| `midi_sequences` | `dict[str, list]` | 2A | ✅ LIVE |
| `render_als_path` | `Path` | 3I | ✅ LIVE |
| `audio_clips` | `dict[str, Path]` | 3K | ✅ LIVE |
| `production_als_path` | `Path` | 3K | ✅ LIVE |

### Stage 5 outputs
| Field | Type | Stage | Status |
|-------|------|-------|--------|
| `render_patterns` | `dict` | 4F | ✅ LIVE |
| `stage5_als_path` | `Path` | 4G | ✅ LIVE |
| `stage5_renders` | `dict` | 4G | ✅ LIVE |

### Meta
| Field | Type | Stage | Status |
|-------|------|-------|--------|
| `audio_manifest` | `AudioManifest` | 3I+ | ✅ LIVE — tracks all expected/delivered files |
| `phase_log` | `list[dict]` | all | ✅ LIVE — audit trail |
| `yaml_config` | `dict \| None` | pre-S1 | ✅ LIVE |

---

## Roadmap

### Done ✅
- Stage 1: IDENTITY (S1A–S1H) — DNA, palette intent, production recipe, arrangement + energy
- Stage 2: MIDI SEQUENCES (2A–2B) — MIDI sequences + ghost kick, Galactia FX
- Stage 3: SYNTH FACTORY (3A–3K) — wavetables, presets, bounce, production skeleton
- Stage 4: DRUM FACTORY (4A–4G) — drums, rack, loops, patterns, Stage 4 ALS
- Dead code cleanup: removed `song_template`, `energy_curve`, `template_config` fields
- Dead code cleanup: removed `_augment_128_rack()` function
- `_build_128_rack` cleaned to 2-arg signature (drums, galactia_fx) — no synth content
- `_configure_stem_specs` cached from 2A, reused in 3H (no redundant computation)
- Galactia FX collected at Stage 2B (so 3G `_sketch_fx()` can use them)
- 3J bounce readiness: waits for expected BPM + track count + plugin grace period
- RCO eliminated — energy derived directly from `section.intensity` on `SectionDef`
- Audio manifest restructured — 4E entries at 3I+, 5E entries at 4F only (no rebuild)

### Next 🔜
- 3I sidechain routing: wire ghost kick → Compressor sidechain on each stem track
- Phase 2 arrangement: consume `stage5_renders` catalog for clip placement
- Multi-bounce validation: cross-check WAV durations against expected beat lengths
- `freq_table` field: evaluate removal (assigned in S1D but never read)

### Future 🔮
- Live Serum 2 control via OSC (serum2_controller.py)
- A/B testing automated against reference tracks
- Multi-track parallel rendering with GPU acceleration
- Batch bounce mode — render multiple tracks in parallel sessions
