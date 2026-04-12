# Phase 1: GENERATION — Playbook

> v7.0.0 — 4-stage pipeline: RCO removed (energy from `section.intensity`), Stage 2 STRUCTURE eliminated, audio manifest at 3I+ (4E only, 5E at 4F).

Step-by-step recipes for each stage. Follow in order.

---

## Stage 1: IDENTITY (S1A–S1H)

> Brain: ARCHITECT — establish who this song is.

### Recipe S1A: Workflow Constants (LOCKED)

```
Output: 26 immutable DubForge standard constants
```

1. **Loaded at import time** — no per-song computation
2. PHI, FIBONACCI, A4_440, SR, BEATS_PER_BAR, NOTES, SCALE_INTERVALS
3. _ZONE_RANGES (128 Drum Rack layout), ALL_SYNTH_STEMS (10 stems)
4. _ELEMENT_STEMS, _STEM_PRESET_MAP, _STEM_GROUP_MAP, _STEM_FUNCTIONS
5. Platform detection: IS_APPLE_SILICON, CPU_CORES, HAS_MLX, HAS_VDSP
6. **Time signature is always 4/4** — `BEATS_PER_BAR = 4`. No odd meters.

### Recipe S1B: Variable Definitions (DNA + Config Tables)

```
Input:  blueprint | yaml_path | dna (at least one)
Output: SongDNA + beat_s + bar_s + config lookup tables resolved
```

**S1B-α: Config Tables** (currently hardcoded, flagged for YAML migration):
1. BPM_RANGES — per-style BPM windows
2. STYLE_PROFILES — 9 style→param defaults
3. WORD_ATOMS — 60+ word→param semantic maps
4. ARRANGEMENT_ARCHETYPES — 5 arrangement templates
5. Morph maps (_MOOD_MORPH_MAP, _STYLE_MORPH_OVERRIDE)
6. Modulation profiles (_MOOD_MODULATION_PROFILES, _STYLE_MODULATION_OVERRIDES)
7. Stem configs (_SC_TIERS, _STEM_WT_PREFS)

**S1B-β: Song DNA (LYNCHPIN) — 153 fields across 7 sub-DNAs:**
1. Parse inputs → SongBlueprint
   - `yaml_path` → `load_yaml_config()` → `yaml_to_blueprint()`
   - `blueprint` → pass through
2. `_oracle(blueprint, dna, yaml_config)` → SongDNA
   - `VariationEngine().forge_dna(blueprint)` internally:
     - `_extract_atoms()` — name → WORD_ATOMS semantic params (min 4-char key guard)
     - `_aggregate_params()` — weighted merge, **clamped 0.0–1.0**
     - `_resolve_mood()` — energy/darkness → mood label
     - `_pick_key/scale/bpm()` — from mood + params (warns unknown styles)
     - `_build_*_dna()` → 7 sub-DNAs:
       - **DrumDNA** (21 fields)
       - **BassDNA** (27 fields)
       - **LeadDNA** (27 fields)
       - **AtmosphereDNA** (16 fields)
       - **FxDNA** (16 fields)
       - **MixDNA** (21 fields)
       - **SongDNA** (25 fields)
3. Compute derived timing: `beat_s = 60/bpm`, `bar_s = beat_s * BEATS_PER_BAR`

### Recipe S1C: Harmony

```
Input:  SongDNA
Output: chord_progression (ChordProgression | None)
```

1. `_build_chord_progression(dna)` → mood/style → preset selection
2. Returns `None` if chord_progression module unavailable (graceful fallback)

### Recipe S1D: Freq Table

```
Input:  SongDNA (root_freq, scale) + S1A (PHI, FIBONACCI, SCALE_INTERVALS)
Output: freq_table (~60 entries)
```

1. `_build_freq_table(dna)` → 5-octave grid + phi/Planck/Fibonacci series

### Recipe S1E: Palette Intent

```
Input:  SongDNA
Output: design_intent (dict — timbral character goals)
```

1. `_design_palette_intent(dna)` → extract timbral goals from sub-DNAs

### Recipe S1F: Template Config

```
Input:  SongDNA (arrangement)
Output: sections_raw (local dict — consumed by S1G only)
```

1. `_extract_sections(dna)` → classify + sum bars by section type

### Recipe S1G: Production Recipe

```
Input:  SongDNA + intent (S1E) + sections_raw (S1F) + S1A constants
Output: production_recipe, groove_template, quality_targets, arrange_tasks
```

1. `rb_select_recipe(style, mood)` → Recipe (quality targets + Fibonacci checkpoints)
2. `_build_recipes(dna, intent, sections_raw)` → groove_template + quality_targets + arrange_tasks

### Recipe S1H: Arrangement + Sections + Totals

```
Input:  SongDNA + S1A (SR, BEATS_PER_BAR)
Output: arrangement_template, sections, total_bars, total_samples
```

1. `_build_arrangement_from_dna(dna)` → ArrangementTemplate
2. `_sections_from_arrangement(template)` → sections + totals
3. Energy derived from `section.intensity` on each `SectionDef` (0–1, no RCO)

---

## Stage 2: MIDI SEQUENCES (2A–2B)

> Brain: ARCHITECT — generate all MIDI data and collect FX samples.

### Recipe 2A: MIDI Sequences

```
Input:  SongMandate (dna, chords, arrangement)
Output: midi_sequences (dict[str, list[ALSMidiNote]]) — 10 stems + ghost_kick
```

1. `_configure_stem_specs(mandate)` → `_midi_stem_configs` (lightweight, for MIDI generation only)
2. `_generate_midi_sequences(mandate, configs)` → 11 sets of MIDI notes:

**Note:** At 3H, stem configs are REBUILT fresh after 3A-3E populate WT/mod/FX data.

| Stem | MIDI driving logic |
|------|-------------------|
| SUB BASS | Root note sustained per bar, velocity from `section.intensity` |
| MID BASS | Bass rotation — 6 types cycling per section |
| NEURO | Rhythmic 1/16 hits at root, velocity accent patterns |
| WOBBLE | Sustained root + CC1 envelope, LFO rate from mod routes |
| RIDDIM | Gap patterns — notes with silence ratios from `dna.bass.distortion` |
| LEAD | Scale-locked random walks from chord progression |
| PAD | Chord tones sustained per section boundary |
| CHORDS | Chord voicings as stabs at section changes |
| ARPS | Step-sequenced scale degrees, BPM-driven speed |
| SUPERSAW | Rising swell in builds + sustained drop notes |
| GHOST KICK | Quarter-note C1 triggers, velocity from `section.intensity` |

3. CC automation embedded: CC1 (mod wheel) for filter/WT position, values from `section.intensity` × mod depth

### Recipe 2B: Collect FX Samples

```
Input:  design_intent
Output: galactia_fx (GalactiaFxSamples)
```

1. `_collect_fx_samples(intent)` → risers, impacts, reverses, falling, rising, shepard, buildups
2. Uses `sample_library.SampleLibrary().list_category()` — NOT `galatcia.py` directly
3. Collected HERE (before Stage 3) for early availability

---

## Stage 3: SYNTH FACTORY (3A–3K)

> Brain: CHILD — design + render all synth audio.

### Recipe 3A: Intake Wavetables

1. Try Galactia ERB neuro WT collection
2. Fallback: `phi_core.generate_phi_core_v1(n_frames=16)`

### Recipe 3B: Generate DNA-driven WT Packs

1. `_generate_dna_wavetables(dna, intent, wt_kit)` → packs
2. FM ratio sweep: `4 + bass.fm_depth * 1.2` tables (range 4–16)
3. Harmonic sweep: `6 + lead.brightness * 10` tables (range 6–16)
4. Growl vowel pack: if `distortion > 0.1` or style is riddim/tearout/dubstep
5. Morph pack: if mood is mystic/sacred/dreamy/ethereal or style is melodic
6. Phi-core root WT: `phi_harmonic_series(root_freq, 24)` → morphed frames
7. Growl resampler: if `distortion > 0.25`, pipeline first available frame

### Recipe 3C: Design Modulation Routes

1. `_design_modulation_routes(dna, intent)` → per-stem-group mod matrix
2. Per group (bass, lead, pad, fx): 3–5 ModulationRoute + 1–3 LFOPreset
3. 8 mood profiles × 4 style overrides

### Recipe 3D: Design FX Chains

1. `_design_fx_chains(dna, intent)` → per-stem-group FX
2. Per stem: saturation, sidechain, stereo, reverb/delay, wave folder (bass), pitch auto (bass+fx)

### Recipe 3E: Morph Wavetables

1. `_select_morph_type(dna)` → algorithm:
   - dark=fractal, aggressive=granular, dreamy=spectral, mystic=phi_spline, euphoric=formant
   - Style overrides: riddim=granular, tearout=fractal, melodic=spectral
2. Morph params from mod routes (LFO rate → n_frames, mood → curve shape)
3. Apply morph to every WT with ≥2 frames

### Recipe 3F: Build Serum 2 Presets

1. `s2_build_all_presets()` → dict of SerumPreset (if cbor2 installed)
2. `s2_get_preset_state_map()` → VST3 binary state for ALS embedding
3. Graceful skip if cbor2 not available

### ~~Recipe 3G: Synthesis~~ — REMOVED v6.0.0

Path B (9 Python sketch functions) has been deleted. All synth audio now renders
exclusively through the Serum 2 → ALS → Ableton bounce pipeline (3I → 3J).

### Recipe 3H: Configure Stem Specs — REBUILT v6.0.0

1. `_configure_stem_specs(mandate)` called FRESH after 3A-3E (not cached from 2A)
2. Now pulls: mod_matrix from 3C, wavetable_frames from 3A/3B, morph_frames from 3E, FX from 3D
3. Diagnostic print shows mod_routes and wt_frames counts to verify data flow

### Recipe 3H+: Mutate Serum 2 Presets (DNA-unique)

1. For each stem: start from base preset → inject wavetable frames → bake mod matrix → set LFOs → apply DNA mutations → serialize to VST3 bytes
2. Output: `serum2_state_map: dict[str, tuple[bytes, bytes]]` — 10 unique presets

### Recipe 3I: Build Render ALS — EXPANDED v6.0.0

1. `_build_render_als(mandate, configs, states, midi)` → `.als` file
2. Track 0: GHOST_KICK (volume=-inf, Drum Rack, sidechain source)
3. Tracks 1–10: Serum 2 stems with expanded FX chain + sidechain + automation
4. **Device chain by group:**
   - **Bass:** Serum 2 → OTT → Saturator → Wave Folder Rack → Auto Filter (formant) → Phaser (comb) → Compressor (SC)
   - **Lead:** Serum 2 → Saturator → Phaser → Compressor (SC) → Reverb → Utility
   - **Pad:** Serum 2 → Compressor (SC) → Reverb → Utility
5. **Macro automation (5 macros + pitch bend)**
6. Output: `output/ableton/_render_session.als`

### Recipe 3I+: Audio Manifest

```
Output: audio_manifest (4E stem entries only — no args needed)
```

1. `_build_audio_manifest()` → AudioManifest with 4E stem entries
2. 5E pattern entries are added later at Stage 4F when actual zone groups are known

### Recipe 3J: Bounce Serum 2 Tracks

**Bounce readiness check:** BPM ±1, track count=11, 15s plugin grace period.
**Workflow:** AbletonOSC + osascript → solo → export → unsolo → collect (with retry)

### Recipe 3J+: Resample Passes — NEW v6.0.0 (Subtronics technique)

After initial Serum 2 bounce, bass stems go through 3 resampling passes:

1. **Stems:** `neuro`, `wobble`, `riddim`, `mid_bass` (sub_bass stays clean)
2. **Pass processing chains:**
   - Pass 1 (grit): Saturator → Multiband Dynamics (OTT) → Utility
   - Pass 2 (texture): Auto Filter → Phaser → Saturator → Utility
   - Pass 3 (character): Frequency Shifter → Multiband Dynamics → Saturator → Utility

### Recipe 3K: Collect Bounced Audio

1. `_collect_bounced_audio()` → validate 10 WAVs (exist, non-zero, 48kHz)
2. `_build_production_skeleton()` → production `.als` with 10 audio + MIDI editing tracks
3. Register in audio manifest: `mandate.audio_clips: dict[str, Path]`

---

## Stage 4: DRUM FACTORY (4A–4G)

> Brain: CHILD — collect samples, build rack, generate patterns, bounce.

### Recipe 4A: Collect Drums

1. `_collect_drums(dna, intent)` → DrumKit
2. Uses `sample_library.SampleLibrary().list_category()` for kick, snare, hat, clap, crash, ride, perc
3. DNA-guided keyword matching (kick→heavy/clean, snare→metallic/organic)

> **Note:** `drum_generator.py` is NOT called. Drums come from `sample_library.py`.

### Recipe 4B–4B+: FX + Zone Mapping

1. `galactia_fx` already collected at 2B — logged only
2. `map_galactia_to_zones()` → galactia_zone_map for remaining empty rack slots

### Recipe 4C: Process Drums

1. `_sketch_drums(drums, dna)` → processed DrumKit
2. Trim silence, normalize to -1dBFS
3. `dynamics.compress()` + `saturation.SaturationEngine().saturate()` + `intelligent_eq.apply_eq_band()`

> **Note:** `drum_pipeline.py` is NOT called. Processing uses `dynamics.py`, `saturation.py`, `intelligent_eq.py` directly.

### Recipe 4D: Build 128 Rack

```
Input:  drums (DrumKit), galactia_fx (GalactiaFxSamples)
Output: Rack128 + RackMidiMap
```

1. `_build_128_rack(drums, galactia_fx)` → Rack128 (2-argument signature, **all inline**)
2. 14 Fibonacci zones: kicks(37–49), snares(50–62), hats(63–70), perc(71–83), fx(84–96), transitions(118–122)
3. Drums + Galactia FX only — NO synth content in rack
4. `_rack_add(galactia_zone_map)` → fill remaining empty slots
5. `_build_rack_midi_map(rack)` → zone→MIDI note mapping

### Recipe 4E: Drum Loops

1. `_build_drum_loops(drums, dna, sections)` → DrumLoopKit
2. 5 patterns: drop (full kit), build (snare roll), intro (sparse), bridge, outro
3. `_build_loop_midi_maps(loops, rack, dna)` → MIDI trigger patterns

### Recipe 4F: Pattern Factory

1. Generate MIDI patterns for each section × zone_group combination (**all inline**)
2. `_ROLE_ZONES` mapping: intro→kicks/hats/fx, drop→full kit, break→hats/perc, etc.
3. Hardcoded FX chains per zone group
4. Update audio manifest with 5E bounce targets (added here, not guessed earlier)

### Recipe 4G: Stage 4 ALS + Bounce

1. `_build_stage5_als(mandate)` → ALS with:
   - Track 0: GHOST_KICK (volume=-70dB, quarter-note C1 triggers)
   - Track 1: 128 RACK (all pads + FX chains, MIDI clips sequential per section×group)
2. `_bounce_stage5_patterns()` → same 3-tier automation as 3J
3. `_collect_stage5_renders()` → validate + catalog WAVs
4. Rebuild loop MIDI maps against full rack (after Galactia zones added)
