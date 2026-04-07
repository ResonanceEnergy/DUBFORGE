# DUBFORGE × ill.GATES PRODUCER DOJO — Full System Reorganization Plan

**Date**: 2026-04-06
**Status**: PROPOSED — Full workflow restructuring around ill.GATES methodology
**Scope**: Every module in engine/ re-mapped, every workflow chain rebuilt

---

## THE PROBLEM

DubForge has **world-class Dojo encoding** (2,885 lines of methodology in dojo.py — 34 rules, 22 techniques, 3 mental models, all phi-enhanced) but **zero enforcement**. The Dojo is an encyclopedia sitting on a shelf. The actual render pipeline (`forge.py render_full_track()`) ignores it completely:

- **No Brain Separation** — Child/Architect/Critic all execute in one 1,441-line function
- **No Phase Gating** — Collect/Sketch/Arrange/Mix/Master/Release blend together
- **No Quality Gates** — recipe_book has 14 pass/fail thresholds that nothing checks
- **No Belt Progression** — All 202 modules accessible regardless of skill level
- **No 128s Integration** — `build_128_rack()` output goes nowhere
- **No Subtractive Arrangement** — Builds left-to-right, never "Fat Loop → Subtract"
- **No Contrast Measurement** — Dojo's "Contrast is King" framework is dead code
- **No Singer/Band Routing** — Mix doesn't differentiate focus vs. support elements
- **No Decision Fatigue Prevention** — Hundreds of synthesis decisions in one pass

**The fix**: Make `dojo.py` the **governor** of the pipeline, not a passenger.

---

## THE DOJO PIPELINE — NEW ARCHITECTURE

```
╔══════════════════════════════════════════════════════════════════════════════════════╗
║                   DUBFORGE DOJO PRODUCTION PIPELINE                                ║
║                                                                                    ║
║   ┌─ NIGHTTIME (Prep — Low Energy) ─────────────────────────────────────────────┐  ║
║   │  PHASE 0: ORACLE  — Choose reference, set intent, pick belt target          │  ║
║   │  PHASE 1: COLLECT — 128 Racks, sample curation, preset audition             │  ║
║   │  PHASE 2: RECIPES — Load recipe, set timeboxes, configure quality gates     │  ║
║   └──────────────────────────────────────────────────────────────────────────────┘  ║
║                                                                                    ║
║   ┌─ DAYTIME (Creation — High Energy) ──────────────────────────────────────────┐  ║
║   │  PHASE 3: SKETCH  [CHILD BRAIN]  — Jam, generate DNA, raw sounds, 8-bar    │  ║
║   │  PHASE 4: ARRANGE [ARCHITECT BRAIN] — Fat Loop → Subtractive → Structure   │  ║
║   │  PHASE 5: DESIGN  [CHILD BRAIN]  — Finalize timbres, commit to audio       │  ║
║   └──────────────────────────────────────────────────────────────────────────────┘  ║
║                                                                                    ║
║   ┌─ FINISHING (Technical — Low Energy) ────────────────────────────────────────┐  ║
║   │  PHASE 6: MIX     [CRITIC BRAIN] — EQ, compress, spatial, Singer/Band      │  ║
║   │  PHASE 7: MASTER   [CRITIC BRAIN] — Final loudness, limiting, stereo       │  ║
║   │  PHASE 8: RELEASE  [ARCHITECT]    — Export, metadata, artwork, distribute   │  ║
║   └──────────────────────────────────────────────────────────────────────────────┘  ║
║                                                                                    ║
║   ┌─ LEARNING (Always) ────────────────────────────────────────────────────────┐   ║
║   │  PHASE 9: REFLECT — Belt check, lessons, memory, evolution, feedback loop  │   ║
║   └──────────────────────────────────────────────────────────────────────────────┘  ║
╚══════════════════════════════════════════════════════════════════════════════════════╝
```

---

## PHASE-BY-PHASE MODULE MAPPING

### PHASE 0: ORACLE — "Choose Your Battle" (Pre-Session)

**Brain**: Architect
**Dojo Concept**: Ghost Track, Song Mapping, reference-driven intent
**Timebox**: 10 minutes
**Quality Gate**: Must have a reference track selected and intent statement

| Module | Role | Current Status | Action |
|--------|------|----------------|--------|
| `reference_library` | Scan/browse 92-track reference library | ⚡ Wired (compare only) | **UPGRADE**: Add `select_reference()` → returns target spectral/dynamics profile |
| `reference_analyzer` | Deep DNA of chosen reference | ⚡ Wired | **UPGRADE**: Extract arrangement markers (Ghost Track sections) |
| `sb_analyzer` | Subtronics corpus context | ⬜ Unwired | **WIRE**: Feed Subtronics VIP delta targets into MixDNA |
| `dubstep_taste_analyzer` | Personal taste profile | ⚡ Wired | Keep — feeds genre affinity |
| `recipe_book` | Recipe selection + quality targets | ⬜ Unwired | **CRITICAL**: `select_recipe()` → returns QualityTargets that GATE all downstream phases |
| `dojo` | Belt assessment + approach timer setup | ⚡ Partial | **UPGRADE**: `begin_dojo_session()` → enforces belt-appropriate module set |

**New Functions Needed**:
- `dojo.begin_dojo_session(belt_level, reference_track) → DojoSession`
- `recipe_book.select_recipe(style, mood, reference) → Recipe(quality_targets, timeboxes)`
- `reference_analyzer.extract_ghost_markers(wav_path) → [SectionMarker]`

---

### PHASE 1: COLLECT — "Build Your Arsenal" (Nighttime/Prep)

**Brain**: Child (playful curation, no pressure)
**Dojo Concept**: 128 Racks, Infinite Drum Rack, sample library as instrument
**Timebox**: 20 minutes
**Quality Gate**: 128 Rack populated for each category needed by recipe

| Module | Role | Current Status | Action |
|--------|------|----------------|--------|
| `sample_library` | Scan/index all available samples | ⬜ Unwired | **WIRE**: `curate_palette(recipe) → SoundPalette` |
| `galatcia` | GALATCIA pack: 336 assets (91 drums, 71 FX, 57 loops, 12 WT, 95 FXP) | ⬜ Unwired | **WIRE**: Feed into sample_library index |
| `sample_slicer` | Beat-aligned Fibonacci slicing | ⬜ Unwired | **WIRE**: Slice loops into one-shots for 128 Rack loading |
| `wav_pool` | WAV file pool manager | ⬜ Unwired | **WIRE**: Cache curated samples in memory |
| `sound_palette` | Sound palette builder | ⬜ Unwired | **WIRE**: `SoundPalette` dataclass holding all curated sounds |
| `preset_browser` | Preset browsing/audition | ⬜ Unwired | **WIRE**: Browse Serum FXP presets from GALATCIA |
| `dojo` | `build_128_rack()` — 14-category Fibonacci zone distribution | ⬜ Unwired | **CRITICAL**: Output must feed into drum_generator + arrangement |
| `ableton_rack_builder` | Drum Rack .adg XML generation | ⚡ Wired (export only) | **UPGRADE**: Generate 128-pad racks from curated palette |
| `audio_preview` | Audio preview/audition | ⬜ Unwired | **WIRE**: In-context audition during collection |
| `sample_pack_exporter` | Export curated packs | ⬜ Unwired | Keep for Release phase |
| `tempo_detector` | BPM detection for imported samples | ⬜ Unwired | **WIRE**: Auto-detect BPM of loops for slicing |
| `key_detector` | Key detection for tonal samples | ⚡ Wired | **UPGRADE**: Tag all tonal samples with detected key |

**New Functions Needed**:
- `sample_library.curate_palette(recipe, reference_dna) → SoundPalette`
- `dojo.build_128_rack_from_palette(palette) → Rack128`
- `sample_slicer.slice_loops_for_rack(loops, bpm) → [OneShot]`

**The 128s Workflow**:
```
1. Recipe says: need kick, snare, hat, clap, bass, lead, pad, FX
2. sample_library scans GALATCIA + output/taste/downloads/ + output/wavetables/
3. For each category: load 128 candidates into a Sampler
4. dojo.build_128_rack_from_palette() generates the Fibonacci-zone mapping
5. SoundPalette frozen — these are the ONLY sounds available to Sketch phase
```

---

### PHASE 2: RECIPES — "Set the Timer" (Nighttime/Prep)

**Brain**: Architect
**Dojo Concept**: Timeboxing, 14-Minute Hit, Custom Templates, Recipe cards
**Timebox**: 5 minutes
**Quality Gate**: Recipe loaded, all timeboxes set, template selected

| Module | Role | Current Status | Action |
|--------|------|----------------|--------|
| `recipe_book` | 14 quality targets + pass/fail thresholds | ⬜ Unwired | **CRITICAL**: `load_recipe() → Recipe` with timebox durations per phase |
| `song_templates` | 20 structure templates (4 categories × 5) | ⚡ Wired | Keep — feeds arrangement skeleton |
| `fibonacci_feedback` | Dojo timer + quality feedback loop | ⚡ Wired | **UPGRADE**: `start_timer(phase, duration)` enforced per-phase |
| `config_loader` | YAML config + PHI/FIBONACCI constants | ✅ Wired | Keep — provides constants |
| `dojo` | `phi_approach_timing()` — golden-ratio phase durations | ⬜ Unwired | **WIRE**: Feed approach timing into fibonacci_feedback timer |

**New Functions Needed**:
- `recipe_book.load_recipe(style, reference_dna) → Recipe(targets, timeboxes, template_id)`
- `fibonacci_feedback.start_phase_timer(phase_name, duration_s) → Timer`
- `dojo.get_approach_timing(total_minutes) → {phase: duration_s}`

**The Recipe Workflow**:
```
1. User picks style (dubstep/riddim/hybrid) + reference track
2. recipe_book.load_recipe() combines:
   - GLOBAL_QUALITY_TARGETS (LUFS, DR, spectral balance, stereo width)
   - Reference track's DNA (target frequencies, dynamics, arrangement)
   - Style-specific overrides (riddim = lower mid, dubstep = wider stereo)
3. dojo.get_approach_timing(session_minutes) calculates phi-ratio phase durations
4. Recipe frozen — quality gates WILL enforce these targets at phase boundaries
```

---

### PHASE 3: SKETCH — "Say YES" (Daytime/Creation)

**Brain**: CHILD ONLY — No EQ tweaking, no arrangement, no mixing decisions
**Dojo Concept**: Jamming, 14-Minute Hit, Mudpies, "Never hit delete"
**Timebox**: 15-20 minutes (phi-proportion of total)
**Quality Gate**: At least N sound elements exist (recipe minimum). NO quality judgment.

| Module | Role | Current Status | Action |
|--------|------|----------------|--------|
| `variation_engine` | `forge_dna()` — SongDNA from name seed | ✅ Wired | Keep — DNA generation is the sketch seed |
| `mood_engine` | Mood → parameter mapping | ⚡ Wired | Keep — drives emotional direction |
| `bass_oneshot` | 7 bass types | ✅ Wired | Keep |
| `lead_synth` | Screech/pluck leads | ✅ Wired | Keep |
| `pad_synth` | Dark/lush pads | ✅ Wired | Keep |
| `perc_synth` | Kick/snare/hat/clap | ✅ Wired | Keep |
| `noise_generator` | White/pink/brown noise | ✅ Wired | Keep |
| `impact_hit` | Sub boom/cinematic | ✅ Wired | Keep |
| `fm_synth` | FM patches | ✅ Wired | Keep |
| `drone_synth` | Drones | ✅ Wired | Keep |
| `granular_synth` | Cloud textures | ✅ Wired | Keep |
| `additive_synth` | Phi partials | ✅ Wired | Keep |
| `formant_synth` | Vowel morphing | ✅ Wired | Keep |
| `supersaw` | Supersaw stacks | ✅ Wired | Keep |
| `karplus_strong` | Physical modeling | ✅ Wired | Keep |
| `vocal_chop` | Formant chops | ✅ Wired | Keep |
| `riser_synth` | Noise sweeps | ✅ Wired | Keep |
| `growl_resampler` | Growl pipeline | ✅ Wired | Keep |
| `sub_bass` | Sub enhancement | ⚡ Wired | Keep |
| `wobble_bass` | Wobble variants | ⚡ Wired | Keep |
| `riddim_engine` | Riddim variants | ⚡ Wired | Keep |
| `chord_progression` | Chord sequences | ⚡ Wired | Keep |
| `chord_pad` | Chord voicings | ⚡ Wired | Keep |
| `ambient_texture` | Ambient layers | ⚡ Wired | Keep |
| `trance_arp` | Fibonacci arp | ⚡ Wired | Keep |
| `markov_melody` | Markov melodies | ⚡ Wired | Keep |
| `harmonic_gen` | Harmonic enrichment | ⚡ Wired | Keep |
| `glitch_engine` | Stutter FX | ✅ Wired | Keep |
| `beat_repeat` | Beat repeat | ✅ Wired | Keep |
| `transition_fx` | Transitions | ✅ Wired | Keep |
| `groove` | Groove templates | ✅ Wired | Keep |
| `rhythm_engine` | Rhythm DNA | ✅ Wired | Keep |
| `openclaw_agent` | Producer agent | ✅ Wired | Keep |
| `tuning_system` | 432Hz validation | ⚡ Wired | Keep |

**CHILD BRAIN RULES (ENFORCED)**:
- NO calls to `mastering_chain`, `intelligent_eq`, `auto_mixer`, `mix_bus`
- NO spectral analysis or frequency measurement
- NO gain staging or level adjustment beyond simple normalize
- NO deletion of generated sounds — keep everything
- Timer running from `fibonacci_feedback`

**Output**: `SketchPalette` — all raw sounds as `list[float]` mono signals, unprocessed.

---

### PHASE 4: ARRANGE — "Say NO" (Daytime)

**Brain**: ARCHITECT ONLY — Structure, not sound. No new synthesis.
**Dojo Concept**: Fat Loop → Subtractive Arrangement, Ghost Track, Song Mapping
**Timebox**: 15 minutes
**Quality Gate**: Full arrangement with all 7 sections, energy curve matches reference

| Module | Role | Current Status | Action |
|--------|------|----------------|--------|
| `arrangement_sequencer` | 4 templates (weapon/emotive/hybrid/fib) | ⚡ Wired | **UPGRADE**: Implement Fat Loop mode |
| `song_templates` | 20 structure templates | ⚡ Wired | Keep — skeleton provider |
| `auto_arranger` | Auto-arrangement | ⚡ Wired | Keep |
| `rco` | Energy curves | ⚡ Wired | **UPGRADE**: Compare energy curve to Ghost Track reference |
| `crossfade` | Section crossfades | ⚡ Wired | Keep |
| `cue_points` | Section markers | ⚡ Wired | Keep |
| `clip_manager` | Clip management | ⚡ Wired | Keep |
| `audio_splitter` | Split segments | ⚡ Wired | Keep |
| `audio_stitcher` | Stitch segments | ⚡ Wired | Keep |
| `pitch_automation` | Pitch curves | ✅ Wired | Keep |

**NEW: FAT LOOP → SUBTRACTIVE ARRANGEMENT ENGINE**:
```python
# The Dojo Way:
# 1. Build the DROP (climax) with ALL elements playing — the "Fat Loop"
# 2. Duplicate across entire timeline
# 3. SUBTRACT: mute/delete elements per section
# 4. Add transitions between sections

def arrange_subtractive(sketch_palette, ghost_markers, rco_curve):
    """
    Phase 4: Subtractive arrangement (ill.GATES Fat Loop technique).
    
    1. Build 8-bar "Fat Loop" — every element from SketchPalette at full intensity
    2. Spread across timeline using ghost_markers section lengths
    3. For each section, apply RCO energy curve to determine which elements play
    4. Intro = minimal (10-20% of elements), Build = rising, Drop = 100%, etc.
    5. Add transitions at section boundaries
    """
```

**ARCHITECT BRAIN RULES (ENFORCED)**:
- NO new sound synthesis — only use what's in SketchPalette
- NO EQ, compression, or mixing — only placement and muting
- NO timbre changes — only volume/mute/position
- Structure decisions ONLY: Section lengths, element presence, transition placement

---

### PHASE 5: DESIGN — "Polish the Gems" (Daytime)

**Brain**: CHILD returning — Now finalize each sound's character
**Dojo Concept**: Freeze & Flatten, Commit to Audio, 128s Macro Performance
**Timebox**: 10 minutes
**Quality Gate**: All sounds committed to audio (list[float]), no MIDI/synth params left open

| Module | Role | Current Status | Action |
|--------|------|----------------|--------|
| `psbs` | Phase-Separated Bass System | ⚡ Partial | **UPGRADE**: Apply PSBS crossovers to all bass elements |
| `wave_folder` | Wave folding distortion | ⚡ Wired | Keep |
| `ring_mod` | Ring modulation | ⚡ Wired | Keep |
| `lfo_matrix` | LFO modulation | ✅ Wired | Keep |
| `multiband_distortion` | 5 algos × 4 presets | ✅ Wired | Keep |
| `saturation` | Tape/tube/digital | ✅ Wired | Keep |
| `reverb_delay` | Space effects | ✅ Wired | Keep |
| `convolution` | IR reverbs | ⚡ Wired | Keep |
| `resonance` | Resonance filters | ⚡ Wired | Keep |
| `serum2` | Serum 2 architecture | ⚡ Wired | Keep |
| `serum2_preset` | FXP export | ⚡ Wired | Keep |
| `serum_blueprint` | Serum blueprint gen | ⚡ Wired | Keep |

**NEW: FREEZE & FLATTEN**:
```python
# After Sound Design phase:
# Every sound is rendered to final audio — no more parameter changes allowed
# This is the "Commit to Audio" step

def freeze_and_flatten(arranged_track):
    """Convert all synthesis parameters to frozen audio.
    After this, only mixing operations (EQ, compression, spatial) are allowed.
    The Child brain is dismissed. The Critic takes over."""
    for element in arranged_track.elements:
        element.audio = element.render_final()  # list[float]
        element.synth_params = None  # Locked — no more tweaking
    return FrozenTrack(arranged_track)
```

**CHILD BRAIN RULES (ENFORCED)**:
- CAN change synth parameters, effects, distortion, modulation
- CANNOT change arrangement/structure (that was Phase 4)
- CANNOT start mixing (no EQ curves, no gain staging)
- MUST commit to audio at end — Freeze & Flatten

---

### PHASE 6: MIX — "The Critic Arrives" (Finishing)

**Brain**: CRITIC ONLY — Technical precision, no creative decisions
**Dojo Concept**: Tetris Board, Singer/Band, Pink Noise Mix, Frequency Slotting, Pain Zone
**Timebox**: 15 minutes
**Quality Gate**: recipe_book quality targets for spectral balance, stereo width, dynamics

| Module | Role | Current Status | Action |
|--------|------|----------------|--------|
| `dsp_core` | Core DSP (multiband, compress, EQ) | ✅ Used internally | Keep |
| `mix_bus` | Mix bus processing | ⚡ Wired | **UPGRADE**: Implement Singer/Band gain routing |
| `auto_mixer` | Gain staging (phi priority) | ⚡ Wired | **UPGRADE**: Pink Noise reference calibration |
| `intelligent_eq` | Auto EQ | ✅ Wired | **UPGRADE**: Pain Zone (2-4.5kHz) clearance enforcement |
| `stem_mixer` | Stem mixing | ⚡ Wired | Keep |
| `bus_router` | Bus routing | ⚡ Wired | Keep |
| `signal_chain` | Signal chain | ⚡ Wired | Keep |
| `dynamics_processor` | Dynamics gate | ⚡ Wired | Keep |
| `dynamics` | Compression + transients | ✅ Wired | Keep |
| `spectral_gate` | Spectral gating | ⚡ Wired | Keep |
| `frequency_analyzer` | FFT analysis | ⚡ Wired | Keep |
| `sidechain` | Kick-triggered ducking | ⚡ Wired | Keep |
| `panning` | Spatial panning | ✅ Wired | Keep |
| `stereo_imager` | Stereo width | ✅ Wired | Keep |
| `dc_remover` | DC offset removal | ⚡ Wired | Keep |
| `vocal_processor` | Vocal processing | ✅ Wired | Keep |
| `audio_analyzer` | Audio analysis | ⚡ Wired | Keep |
| `mix_assistant` | Mix guidance | ⬜ Unwired | **WIRE**: Provide Singer/Band suggestions |
| `harmonic_analysis` | FFT harmonic analysis | ⬜ Unwired | **WIRE**: Detect masking conflicts |

**NEW: SINGER/BAND ROUTING**:
```python
# ill.GATES "Ninja Sounds" — most elements should be INVISIBLE
# Only the "Singer" (lead melody, vocal, hook) demands listener attention
# Everything else is "Band" — essential but should not compete

SINGER_ELEMENTS = ["lead", "vocal", "hook"]  # Gets the Pain Zone (2-4.5kHz)
BAND_ELEMENTS = ["kick", "snare", "bass", "pad", "hat", "fx", "drone"]  # HPF at Pain Zone

def apply_singer_band_routing(frozen_track, recipe):
    """Route Singer elements to focus frequencies, Band to support."""
    for element in frozen_track.elements:
        if element.role in SINGER_ELEMENTS:
            # Singer: boost presence, own the Pain Zone
            element.eq = recipe.singer_eq  # Gentle boost at 3236Hz (phi × 2kHz)
        else:
            # Band: cut Pain Zone, be invisible
            element.eq = recipe.band_eq  # Notch at 2-4.5kHz, serve the track
```

**NEW: PINK NOISE REFERENCE MIXING**:
```python
def pink_noise_gain_stage(frozen_track):
    """ill.Gates pink noise mixing technique.
    Play pink noise at reference level, bring each stem up until just audible.
    Creates mathematically balanced frequency distribution."""
    pink = noise_generator.render("pink", duration=10.0)
    pink_rms = compute_rms(pink)
    for element in frozen_track.elements:
        # Binary search for "just audible over pink noise"
        element.gain = find_threshold_gain(element.audio, pink, pink_rms)
```

**NEW: FREQUENCY SLOTTING (TETRIS BOARD)**:
```python
def check_frequency_collisions(frozen_track):
    """ill.Gates Tetris Board — detect overlapping frequency homes.
    Flag any two elements that share >30% spectral energy in same band."""
    for a, b in combinations(frozen_track.elements, 2):
        overlap = compute_spectral_overlap(a.audio, b.audio)
        if overlap > 0.30:
            log.warning(f"TETRIS COLLISION: {a.name} vs {b.name} — {overlap:.0%} overlap")
            # Suggest: HPF one, or sidechain, or pan opposite
```

**CRITIC BRAIN RULES (ENFORCED)**:
- NO new sounds — work with frozen audio only
- NO arrangement changes — structure is locked
- NO creative decisions — only technical (EQ, compress, spatial)
- CAN adjust gains, EQ curves, compression, stereo, panning
- MUST pass recipe_book quality targets before proceeding to Master

---

### PHASE 7: MASTER — "Final Authority" (Finishing)

**Brain**: CRITIC
**Dojo Concept**: Master chain stock devices, Reference matching, Loudness target
**Timebox**: 5 minutes
**Quality Gate**: LUFS target, DR target, stereo width target, true peak < ceiling

| Module | Role | Current Status | Action |
|--------|------|----------------|--------|
| `mastering_chain` | 7-stage master | ✅ Wired | **UPGRADE**: Settings driven by recipe_book targets |
| `auto_master` | Auto-mastering | ⚡ Wired | Keep |
| `normalizer` | Phi normalization | ⚡ Wired | Keep |
| `dither` | Final dither | ⚡ Wired | Keep |
| `phi_analyzer` | Phi coherence | ⚡ Wired | Keep |
| `qa_validator` | Output QA | ⚡ Wired | **UPGRADE**: Hard-fail on recipe target misses |

**NEW: RECIPE-DRIVEN MASTER SETTINGS**:
```python
def master_from_recipe(mixed_audio, recipe):
    """Master settings derived from recipe quality targets, not hardcoded."""
    settings = MasterSettings(
        target_lufs=recipe.targets.lufs,         # From recipe, not -10 default
        ceiling_db=recipe.targets.ceiling_db,     # From recipe
        stereo_width=recipe.targets.stereo_width, # From recipe
        # Compare to reference track's mastering DNA
        eq_low_shelf_db=recipe.reference.mastering_dna.eq_adjustments.low,
        eq_high_shelf_db=recipe.reference.mastering_dna.eq_adjustments.high,
    )
    mastered, report = master(mixed_audio, settings)
    # QUALITY GATE — hard fail if targets missed
    assert report.lufs >= recipe.targets.lufs - 1.0, f"LUFS target missed: {report.lufs}"
    return mastered, report
```

---

### PHASE 8: RELEASE — "Ship It" (Finishing)

**Brain**: Architect
**Dojo Concept**: Non-musical assets, brand consistency, multiple touchpoints
**Timebox**: 5 minutes
**Quality Gate**: All export formats generated

| Module | Role | Current Status | Action |
|--------|------|----------------|--------|
| `bounce` | Stem export | ⚡ Wired | Keep |
| `format_converter` | Format conversion | ⚡ Wired | Keep |
| `metadata` | Audio metadata | ⚡ Wired | Keep |
| `midi_export` | MIDI file export | ⚡ Wired | Keep |
| `watermark` | Audio watermark | ⚡ Wired | Keep |
| `artwork_generator` | Artwork generation | ⚡ Wired | Keep |
| `waveform_display` | Waveform visual | ⚡ Wired | Keep |
| `vip_pack` | VIP pack export | ⚡ Wired | Keep |
| `ep_builder` | EP metadata | ⚡ Wired | Keep |
| `fxp_writer` | FXP presets | ✅ Wired | Keep |
| `als_generator` | Ableton .als export | ✅ Wired | Keep |
| `ableton_rack_builder` | .adg rack export | ⚡ Wired | Keep |
| `tag_system` | Tag management | ⚡ Wired | Keep |
| `cue_points` | Cue point export | ⚡ Wired | Keep |
| `sample_pack_builder` | Sample pack | ⬜ Unwired | **WIRE**: Export stems as sample pack |
| `preset_pack_builder` | Preset pack | ⬜ Unwired | **WIRE**: Export presets as pack |
| `marketplace_metadata` | Marketplace meta | ⬜ Unwired | **WIRE**: Generate marketplace listing |
| `soundcloud_pipeline` | SoundCloud upload | ⬜ Unwired | **WIRE**: Auto-upload to SC |

**Non-Musical Assets (ill.Gates "Value Add")**:
- Final WAV (24-bit/48kHz)
- Stems (24-bit/48kHz per track group)
- MIDI file
- Artwork (auto-generated)
- Serum 2 presets (.fxp)
- Ableton Live Set (.als)
- Drum Rack (.adg)
- Cue points + markers
- Metadata (ID3 tags, BPM, key)
- Sample pack (stems for remix)

---

### PHASE 9: REFLECT — "The Learning Loop" (Always)

**Brain**: All
**Dojo Concept**: Belt progression, accountability, finish more music, lessons learned
**Timebox**: 5 minutes
**Quality Gate**: Lessons recorded, belt updated, memory persisted

| Module | Role | Current Status | Action |
|--------|------|----------------|--------|
| `fibonacci_feedback` | Quality feedback loop | ⚡ Wired | **UPGRADE**: Compare final output vs recipe targets |
| `lessons_learned` | Lessons persistence | ⚡ Wired | Keep |
| `memory` | Long-term memory | ⚡ Wired | Keep |
| `evolution_engine` | Parameter evolution | ⚡ Wired | Keep |
| `session_logger` | Session logging | ⚡ Wired | Keep |
| `ab_tester` | A/B testing | ⚡ Wired | Keep |
| `pattern_recognizer` | Pattern recognition | ⚡ Wired | Keep |
| `genetic_evolver` | Genetic evolution | ⚡ Wired | Keep |
| `preset_mutator` | Preset mutation | ⚡ Wired | Keep |
| `dojo` | Belt check + progression | ⚡ Partial | **UPGRADE**: `assess_belt_promotion()` with hard criteria |
| `recipe_book` | Quality report card | ⬜ Unwired | **WIRE**: `generate_report_card(output, targets) → ReportCard` |

**Belt Assessment**:
```python
def assess_belt_promotion(session_history, current_belt):
    """Check if producer earns a belt promotion.
    Belt thresholds are Fibonacci session/track counts:
    - White → Yellow: 3 finished tracks
    - Yellow → Orange: 5 tracks + meets 50% of recipe targets
    - Orange → Green: 8 tracks + meets 75% of recipe targets
    - Green → Blue: 13 tracks + meets 90% of recipe targets
    - Blue → Purple: 21 tracks + reference-quality on 3+
    - Purple → Brown: 34 tracks + consistent reference-quality
    - Brown → Black: 55 tracks + original sonic identity
    """
```

---

## ORPHAN MODULE DISPOSITION

These 23 modules don't fit the Dojo flow. Recommended actions:

| Module | Lines | Disposition |
|--------|-------|-------------|
| `arp_synth` | 406 | **MERGE** into `trance_arp` (duplicate functionality) |
| `pluck_synth` | 342 | **MERGE** into `lead_synth` (already has pluck mode) |
| `vector_synth` | 191 | **ARCHIVE** — no integration point, research-only |
| `drum_generator` | 2971 | **RE-PURPOSE** — make it the 128 Rack engine for Phase 1 COLLECT |
| `vocal_tts` | 330 | **ARCHIVE** — TTS not in production workflow |
| `vocoder` | 228 | **WIRE** into Sound Design (Phase 5) as optional effect |
| `spectral_morph` | 181 | **WIRE** into Sound Design (Phase 5) |
| `spectral_resynthesis` | 299 | **WIRE** into Sound Design (Phase 5) |
| `wavetable_morph` | 329 | **WIRE** into Phase 1 COLLECT (WT creation) |
| `wavetable_pack` | 205 | **WIRE** into Phase 8 RELEASE |
| `emulator` | 774 | **KEEP** as standalone tool (not in Dojo pipeline) |
| `envelope_generator` | 255 | **KEEP** as internal utility (used by synths) |
| `phase_distortion` | 140 | **WIRE** into Sound Design (Phase 5) |
| `style_transfer` | 175 | **ARCHIVE** — research-only |
| `fx_generator` | 730 | **MERGE** into `fx_rack` (consolidate FX) |
| `fx_rack` | 235 | **WIRE** into Sound Design (Phase 5) |
| `harmonic_analysis` | 540 | **WIRE** into Mix (Phase 6) for masking detection |
| `mix_assistant` | 285 | **WIRE** into Mix (Phase 6) for Singer/Band guidance |
| `stem_separator` | 227 | **KEEP** as standalone tool (requires ML model) |
| `sub_pipeline` | 80 | **MERGE** into `sub_bass` |
| `atmos_pipeline` | 167 | **MERGE** into `ambient_texture` |
| `preset_vcs` | 255 | **WIRE** into Phase 9 REFLECT (preset versioning) |
| `session_persistence` | 101 | **MERGE** into `memory` |

---

## IMPLEMENTATION ROADMAP

### Sprint 1: GOVERNOR (Dojo enforces phase boundaries)

**Goal**: `dojo.py` becomes the pipeline controller, not a data-only module.

1. Add `DojoSession` class to `dojo.py`:
   - Tracks current phase, brain, timer, quality gates
   - Enforces which modules can be called per phase
   - Logs phase transitions

2. Add `Recipe` class to `recipe_book.py`:
   - `select_recipe(style, reference_dna) → Recipe`
   - Quality targets with pass/fail thresholds
   - Per-phase timeboxes

3. Refactor `forge.py render_full_track()` into 7 phase functions:
   - `phase_sketch(dna, palette) → SketchPalette`
   - `phase_arrange(sketch, ghost_markers) → ArrangedTrack`
   - `phase_design(arranged) → FrozenTrack`
   - `phase_mix(frozen, recipe) → MixedTrack`
   - `phase_master(mixed, recipe) → MasteredTrack`
   - `phase_release(mastered, dna) → ReleasePackage`
   - `phase_reflect(release, recipe) → SessionReport`

4. Quality gates between phases (fail-safe: warn, don't block):
   - Sketch → Arrange: minimum N elements exist
   - Arrange → Design: all 7 sections present, energy curve validated
   - Design → Mix: all sounds frozen to audio
   - Mix → Master: spectral balance within recipe tolerance
   - Master → Release: LUFS/DR/Peak within recipe tolerance

**Estimated scope**: ~400 lines new code + ~200 lines refactor

### Sprint 2: COLLECT (128 Racks become real)

**Goal**: The weakest phase (31% wired) becomes functional.

1. Wire `sample_library.curate_palette(recipe)` to filter samples by recipe needs
2. Wire `dojo.build_128_rack_from_palette()` to produce Fibonacci-zone mapped racks
3. Wire `galatcia` into `sample_library` index
4. Wire `sample_slicer` for loop → one-shot conversion
5. Wire `drum_generator` as 128 Rack population engine (re-purpose its 2,971 lines)

**Estimated scope**: ~300 lines new wiring + ~100 lines new functions

### Sprint 3: FAT LOOP (Subtractive arrangement)

**Goal**: Replace left-to-right additive arrangement with Dojo subtractive technique.

1. Add `build_fat_loop()` to `arrangement_sequencer`:
   - Takes all elements, renders 8-bar "climax" with everything playing
2. Add `subtract_for_section()`:
   - Energy curve → element muting decisions per section
3. Wire Ghost Track markers from `reference_analyzer`
4. Wire contrast measurement (drop energy vs breakdown energy)

**Estimated scope**: ~250 lines new code

### Sprint 4: MIXING INTELLIGENCE (Singer/Band, Pink Noise, Tetris)

**Goal**: Mix phase implements Dojo's three mixing mental models.

1. Add `singer_band_routing()` to `mix_bus`
2. Add `pink_noise_gain_stage()` to `auto_mixer`
3. Add `check_frequency_collisions()` to `frequency_analyzer`
4. Wire `mix_assistant` for guidance output
5. Wire `harmonic_analysis` for masking detection
6. Add Pain Zone enforcement to `intelligent_eq`

**Estimated scope**: ~350 lines new code

### Sprint 5: BELT ENFORCEMENT (Progression becomes real)

**Goal**: Belt system gates module access and tracks real progression.

1. Add `assess_belt_promotion()` to `dojo`
2. Wire `recipe_book.generate_report_card()` for per-track scoring
3. Add belt-gated module imports (warn if using advanced module at low belt)
4. Wire `session_persistence` into `memory` for cross-session belt tracking

**Estimated scope**: ~200 lines new code

---

## SUMMARY SCORECARD (CURRENT → TARGET)

| Dimension | Current | Target | Sprint |
|-----------|---------|--------|--------|
| Methodology Encoding | ★★★★★ | ★★★★★ | — (already excellent) |
| Dojo Enforcement | ★★☆☆☆ | ★★★★☆ | Sprint 1 |
| COLLECT Phase | ★★☆☆☆ | ★★★★☆ | Sprint 2 |
| Fat Loop Arrangement | ☆☆☆☆☆ | ★★★★☆ | Sprint 3 |
| Mixing Intelligence | ★★☆☆☆ | ★★★★☆ | Sprint 4 |
| Belt Progression | ★☆☆☆☆ | ★★★★☆ | Sprint 5 |
| Phase Brain Separation | ☆☆☆☆☆ | ★★★★☆ | Sprint 1 |
| Quality Gate Enforcement | ★☆☆☆☆ | ★★★★☆ | Sprint 1 |
| 128s Integration | ★☆☆☆☆ | ★★★★☆ | Sprint 2 |
| Contrast Measurement | ★☆☆☆☆ | ★★★☆☆ | Sprint 3 |
| Singer/Band Routing | ☆☆☆☆☆ | ★★★★☆ | Sprint 4 |
| Pink Noise Mixing | ☆☆☆☆☆ | ★★★☆☆ | Sprint 4 |
| Subtractive Arrangement | ☆☆☆☆☆ | ★★★★☆ | Sprint 3 |

---

## THE GOLDEN RULE

> **"The thing you need is not next if you scroll down."**
> — ill.GATES

The Dojo methodology isn't about adding MORE modules. DubForge already has 202 modules.
It's about making them **obey the discipline**.

The governor pattern: `dojo.py` becomes the **orchestrator** that enforces which modules can fire, when, under what brain, with what quality gates, on what timer. The modules themselves are fine. The *workflow* between them needs to become the Dojo.
