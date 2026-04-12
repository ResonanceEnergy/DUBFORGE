# Phase 1: GENERATION — Workflow

> v7.0.0 — 4-stage pipeline: RCO removed (energy from `section.intensity`), Stage 2 STRUCTURE eliminated, audio manifest at 3I+ (4E only, 5E at 4F).
> **Time signature: 4/4 always** — `BEATS_PER_BAR = 4`. No odd meters.

**Entry point:** `engine/phase_one.py → run_phase_one()`
**Orchestrator:** `forge.py` (via `tools/forge_runner.py`)

## SOT Architecture

- Canonical runtime entrypoint: `forge.py`
- Canonical orchestrator: `tools/forge_runner.py`
- Stage workflow path: `forge.py` → `tools/forge_runner.py` → `engine/phase_one.py::run_phase_one()`

---

## Execution Order

```
run_phase_one(blueprint?, dna?, yaml_path?)
│
╔══════════════════════════════════════════════════════════════════════════
║ STAGE 1: IDENTITY (S1A–S1H)
║ Brain: ARCHITECT
║ Input:  blueprint | yaml_path | dna
║ Output: SongDNA, beat_s, bar_s, chord_progression, freq_table,
║         design_intent, production_recipe, groove_template,
║         quality_targets, arrange_tasks, arrangement_template,
║         sections, total_bars, total_samples
╠══════════════════════════════════════════════════════════════════════════
│
├── S1A. Workflow Constants (LOCKED — 26 constants)
│   ├── Math: PHI, FIBONACCI, A4_440
│   ├── Audio: SR=48000, BEATS_PER_BAR=4, _SR, _BOUNCE_MAX_RETRIES
│   ├── Music Theory: NOTES, SCALE_INTERVALS
│   ├── Rack: _ZONE_RANGES, _ZONE_IDX, _ZONE_MAX
│   ├── Stems: ALL_SYNTH_STEMS, _STEM_PRESET_MAP, _STEM_GROUP_MAP,
│   │          _ELEMENT_STEMS, _STEM_FUNCTIONS
│   └── Platform: IS_APPLE_SILICON, CPU_CORES, HAS_MLX, HAS_VDSP, etc.
│
├── S1B. Variable Definitions (DNA + Config Tables) — 153 fields across 7 sub-DNAs
│   ├── S1B-α: Config Tables (10 lookup tables, ~635 LOC)
│   │   ├── BPM_RANGES, STYLE_PROFILES, WORD_ATOMS
│   │   ├── ARRANGEMENT_ARCHETYPES
│   │   ├── _MOOD_MORPH_MAP, _STYLE_MORPH_OVERRIDE
│   │   ├── _MOOD_MODULATION_PROFILES, _STYLE_MODULATION_OVERRIDES
│   │   └── _SC_TIERS, _STEM_WT_PREFS
│   └── S1B-β: _oracle(blueprint, dna, yaml_config) → SongDNA + beat_s + bar_s
│       └── VariationEngine().forge_dna(blueprint):
│           ├── _extract_atoms() — name → WORD_ATOMS semantic params (min 4-char guard)
│           ├── _aggregate_params() — weighted merge (clamped 0.0–1.0)
│           ├── _resolve_mood() — energy/darkness → mood label
│           ├── _pick_key/scale/bpm() — from mood + params + BPM_RANGES (warns unknown styles)
│           └── _build_*_dna() → 7 sub-DNAs (153 total fields):
│               ├── DrumDNA (21) — pattern_swing, hi_hat_separation_ms, sample categories
│               ├── BassDNA (27) — wavefold_mix, filter_resonance, saturation, wobble_lfo_shape, riddim
│               ├── LeadDNA (27) — filter, envelope (ADSR), glide_ms, arp (subdivision/style/octave), chords
│               ├── AtmosphereDNA (16) — reverb (type/predelay/width), pad_attack_ms
│               ├── FxDNA (16) — riser_type, impact_type, reversal_bars, overdrive
│               ├── MixDNA (21) — per-element gain_db, sidechain (attack/release/mode), humanize
│               └── SongDNA (25) — tuning_hz (432/440), escalation_enabled, arrangement_template_type
│
├── S1C. _build_chord_progression(dna) → chord_progression
│   └── Mood/style → preset → ChordProgression | None
│
├── S1D. _build_freq_table(dna) → freq_table
│   └── 5-octave grid + phi/Planck/Fibonacci series (~60 entries)
│
├── S1E. _design_palette_intent(dna) → design_intent
│   └── Timbral character goals from sub-DNAs
│
├── S1F. _extract_sections(dna) → sections_raw (local)
│   └── Classify + sum bars by section type (consumed by S1G only)
│
├── S1G. rb_select_recipe() + _build_recipes(dna, intent, sections_raw)
│   └── production_recipe, groove_template, quality_targets, arrange_tasks
│
└── S1H. _build_arrangement_from_dna(dna) + _sections_from_arrangement()
    └── arrangement_template, sections, total_bars, total_samples
        Energy derived from section.intensity on each SectionDef (no RCO)
│
╔══════════════════════════════════════════════════════════════════════════
║ STAGE 2: MIDI SEQUENCES (2A–2B)
║ Brain: ARCHITECT
║ Input:  SongDNA + ArrangementTemplate + ChordProgression
║ Output: midi_sequences (11 sets), galactia_fx
╠══════════════════════════════════════════════════════════════════════════
│
├── 2A. _configure_stem_specs(mandate) → _midi_stem_configs (CACHED)
│   └── _generate_midi_sequences(mandate, configs) → midi_sequences
│       ├── 10 synth stems: sub_bass through supersaw
│       ├── 1 ghost kick: quarter-note C1, velocity from section.intensity
│       ├── CC automation: CC1 from section.intensity × mod depth
│       └── _freq_to_midi(freq, tuning_hz) — tuning-aware pitch conversion
│
└── 2B. _collect_fx_samples(intent) → mandate.galactia_fx
    └── sample_library.SampleLibrary().list_category() → risers, impacts, etc.
│
╔══════════════════════════════════════════════════════════════════════════
║ STAGE 3: SYNTH FACTORY (3A–3K)
║ Brain: CHILD
║ Input:  SongDNA + ChordProgression + midi_sequences + galactia_fx
║ Output: wavetables, modulation_routes, fx_chains, serum2_state_map,
║         audio_clips (10 bounced WAVs, bass stems resampled ×3),
║         audio_manifest (4E entries), render_als_path, production_als_path
╠══════════════════════════════════════════════════════════════════════════
│
├── 3A. _collect_wavetables() → WavetableKit
│   └── Galactia ERB WTs / phi_core fallback
│
├── 3B. _generate_dna_wavetables(dna, intent, wt_kit) → packs
│   └── FM + harmonic + growl + morph + phi-core + growl resample
│
├── 3C. _design_modulation_routes(dna, intent) → modulation_routes
│   └── Per-group: bass, lead, pad, fx → mod_matrix + lfos
│
├── 3D. _design_fx_chains(dna, intent) → fx_chains
│   └── Per-group: saturation, sidechain, stereo, reverb, wave_folder, pitch_auto
│
├── 3E. _morph_all_wavetables(dna, wt_kit, mod_routes) → morphed
│   └── Mood → fractal/granular/spectral/phi_spline/formant
│
├── 3F. s2_build_all_presets() + s2_get_preset_state_map()
│   └── SerumPreset objects + VST3 binary states (needs cbor2)
│
├── ~~3G. REMOVED~~ — Path B (9 Python sketch renders) deleted v6.0.0
│   └── All audio via Serum 2 → ALS → Ableton bounce exclusively
│
├── 3H. _configure_stem_specs(mandate) → stem_configs  ← REBUILT (not cached)
│   └── Fresh build after 3A-3E: mod_matrix, lfos, wavetable_frames, morph_frames populated
│
├── 3H+. _mutate_presets_dna(mandate, stem_configs) → serum2_state_map
│   └── Base preset → inject WTs → bake mods → set LFOs → DNA mutations → VST3 bytes
│
├── 3I. _build_render_als(mandate, configs, states, midi) → .als
│   ├── Track 0: GHOST_KICK (volume=-inf, sidechain source)
│   ├── Tracks 1–10: Serum 2 + device chain + sidechain + automation
│   ├── Device chain (bass): Serum 2 → OTT → Saturator → Wave Folder Rack
│   │                        → Auto Filter (formant) → Phaser (comb) → Compressor (SC)
│   ├── Device chain (lead): Serum 2 → Saturator → Phaser → Compressor → Reverb → Utility
│   └── Automation: Macros 1-5 + Pitch Bend (section-aware, mod_matrix-scaled)
│
├── 3I+. _build_audio_manifest() → audio_manifest (4E stem entries only)
│   └── 5E pattern entries added later at Stage 4F
│
├── 3J. _bounce_render_tracks(als_path, mandate=mandate)
│   ├── Readiness check: BPM ±1, track count=11, 15s plugin grace
│   └── Solo → Export → Wait for WAV → Unsolo (with retry)
│
├── 3J+. _resample_passes(bounces, mandate, num_passes=3)  ← NEW v6.0.0
│   ├── Only bass stems: neuro, wobble, riddim, mid_bass (sub_bass stays clean)
│   ├── Pass 1 (grit): Saturator → OTT → Utility
│   ├── Pass 2 (texture): Auto Filter → Phaser → Saturator → Utility
│   ├── Pass 3 (character): Freq Shifter → OTT → Saturator → Utility
│   └── Each pass: build ALS → open in Ableton → bounce → feed into next pass
│
└── 3K. _collect_bounced_audio() + _build_production_skeleton()
    └── audio_clips (10 WAVs) + production_als_path
│
╔══════════════════════════════════════════════════════════════════════════
║ STAGE 4: DRUM FACTORY (4A–4G)
║ Brain: CHILD
║ Input:  SongDNA + design_intent + galactia_fx
║ Output: drums, drum_loops, rack_128, rack_midi_map,
║         loop_midi_maps, render_patterns, stage5_als_path,
║         stage5_renders
╠══════════════════════════════════════════════════════════════════════════
│
├── 4A. _collect_drums(dna, intent) → DrumKit
│   └── sample_library.SampleLibrary().list_category() → kick, snare, hat, etc.
│
├── 4B. galactia_fx — already collected (2B), logged
│
├── 4B+. map_galactia_to_zones() → galactia_zone_map
│
├── 4C. _sketch_drums(drums, dna) → DrumKit (processed)
│   └── Trim, normalize, dynamics.compress() + saturation + intelligent_eq per sample type
│
├── 4D. _build_128_rack(drums, galactia_fx) → Rack128
│   ├── 14 Fibonacci zones — all logic inline (_rack_add, _ZONE_RANGES)
│   ├── _rack_add(galactia_zone_map) → fill remaining empty slots
│   └── _build_rack_midi_map(rack) → zone→MIDI note mapping
│
├── 4E. _build_drum_loops(drums, dna, sections) → DrumLoopKit
│   └── _build_loop_midi_maps(loops, rack, dna) → MIDI triggers
│
├── 4F. Pattern Factory (inline in run_phase_one)
│   ├── Per section × zone_group → MIDI pattern
│   ├── _ROLE_ZONES mapping: intro→kicks/hats/fx, drop→full, etc.
│   ├── Hardcoded FX chains per zone group
│   └── Update audio manifest with 5E bounce targets (added here, not guessed earlier)
│
└── 4G. _build_stage5_als(mandate)
    ├── Track 0: GHOST_KICK (-70dB, C1 quarter notes)
    ├── Track 1: 128 RACK (all pads + FX, sequential MIDI clips)
    ├── Silence gap from dna.drums.silence_gap_beats (default: 4)
    ├── _bounce_stage5_patterns() → 3-tier automation
    ├── _collect_stage5_renders() → validate + catalog WAVs
    └── Rebuild loop MIDI maps (full rack)

→ SongMandate (42 fields) complete → Phase 2
```

---

## Dependency Graph

```
                    ┌──────────────────┐
                    │    STAGE 1       │
                    │    IDENTITY      │
                    │    S1A–S1H       │
                    │                  │
                    │ SongDNA          │
                    │ design_intent    │
                    │ production_recipe│
                    │ arrangement +    │
                    │ energy (from     │
                    │ section.intensity│
                    └────────┬─────────┘
                             │
                    ┌────────▼──────────┐
                    │    STAGE 2        │
                    │ MIDI SEQUENCES    │
                    │    2A–2B          │
                    │                   │
                    │ midi_sequences    │
                    │ galactia_fx       │
                    └────────┬──────────┘
                             │
                    ┌────────▼──────────┐
                    │    STAGE 3        │
                    │  SYNTH FACTORY    │
                    │    3A–3K          │
                    │                   │
                    │ wavetables, mods  │
                    │ FX chains, presets│
                    │ 10 Serum 2 WAVs   │
                    │ audio manifest    │
                    │ production .als   │
                    └────────┬──────────┘
                             │
                    ┌────────▼──────────┐
                    │    STAGE 4        │
                    │  DRUM FACTORY     │
                    │    4A–4G          │
                    │                   │
                    │ DrumKit, loops    │
                    │ Rack128 (128 pad) │
                    │ patterns, FX      │
                    │ Stage 4 ALS + WAVs│
                    └────────┬──────────┘
                             │
                    ┌────────▼──────────┐
                    │   SongMandate     │
                    │   (42 fields)     │
                    │   + audio_clips   │
                    │   + stage5_renders│
                    │                   │
                    │     → Phase 2     │
                    └───────────────────┘
```
