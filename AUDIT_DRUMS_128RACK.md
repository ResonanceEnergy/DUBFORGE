# DUBFORGE Drum Engine Audit — ill.Gates 128 Rack Cross-Reference

> **Date:** 2026-07-05
> **Scope:** Full drum pipeline audit vs. ill.Gates 128 Rack protocol, Producer Dojo methodology, and Ableton Drum Rack optimization best practices
> **Files audited:** `forge.py`, `engine/als_generator.py`, `engine/drum_generator.py`, `engine/drum_pipeline.py`, `engine/perc_synth.py`, `engine/groove.py`, `engine/rhythm_engine.py`, `engine/variation_engine.py`, `make_wild_ones_v12.py`, `make_template.py`

---

## Executive Summary

DUBFORGE's drum synthesis engine is **sonically advanced** — 4-layer kick synthesis, parallel-compressed snare, Fibonacci percussion, phi-groove templates, and a 6-stage rendering pipeline place it above most generative engines. However, when measured against the **ill.Gates 128 Rack protocol** and Ableton Drum Rack optimization standards, the **ALS export layer** has critical gaps that prevent the generated `.als` files from delivering the same workflow in Ableton Live.

| Category | DUBFORGE Status | 128 Rack Standard | Gap Severity |
|----------|----------------|-------------------|--------------|
| Pad Count | 8-11 pads | 128 pads (8 banks × 16) | **CRITICAL** |
| Macro Controls | 16 generated, **all hidden** | 16 mapped + named + visible | **CRITICAL** |
| Return Chains | Empty element | 6 internal FX returns | **HIGH** |
| Per-Pad FX | Empty `<Devices>` | EQ8 + Compressor + Saturator + AutoFilter | **HIGH** |
| Choke Groups | ✅ Implemented (hat open/closed) | ✅ Same | OK |
| Velocity Zones | None | Multi-layer velocity mapping | **MEDIUM** |
| Chain Select / Kit Banks | None | Chain Select for palette switching | **MEDIUM** |
| Round-Robin | None | Multiple samples per pad | **LOW** |
| Color Coding | ✅ Per-pad colors | ✅ Per-bank colors | OK |
| Push Integration | N/A (code-generated) | Full 128-pad Push mapping | N/A |

**Bottom line:** DUBFORGE builds drums that *sound* professional but exports Drum Racks that are *workflow-empty*. A producer opening the ALS gets a bare-bones rack with no macros, no FX, no returns — just silent pads waiting for manual setup.

---

## 1. DUBFORGE Drum Synthesis Engine — Current State

### 1.1 Drum Elements (forge.py Stage [1/9])

| Element | Layers | Synthesis Method | Processing Chain |
|---------|--------|-----------------|-----------------|
| **Kick** | 4 | Sub body (sine @ `kick_pitch` Hz) + FM modulator (`kick_fm_depth`) + Karplus-Strong click (2500 Hz) + Brown noise rumble | Transient → Compress (10:1, -4dB thresh, +4dB makeup) → Saturate (tape, `kick_drive`) → 3-band EQ (+4dB sub, +4dB@3.5kHz click, -3dB@300Hz mud) → Normalize (0.98) |
| **Snare** | 4 | Tonal body (sine @ `snare_pitch`) + Pink noise tail + Karplus metallic ring (`snare_pitch`×3.5) + White noise transient | 50/50 dry/compressed blend (8:1, -12dB, +6dB) → Transient (1.5) → OTT (`snare_ott`=0.35) → Saturate (transistor) → EQ (+2.5dB body, +3dB@5kHz crack) → Plate reverb (0.6s, mix=0.2) → Normalize (0.93) |
| **Closed Hat** | 2 | Karplus-Strong @ `hat_frequency` + 6-partial Fibonacci percussion | EQ (+3dB@10kHz) → Tape saturation (0.3) → Normalize (0.85) |
| **Open Hat** | 2 | Extended Karplus-Strong + longer Fibonacci percussion | Same as closed hat with longer decay |
| **Clap** | 1 | 4 phi-spaced noise bursts (φ timing between each burst) | Bandpass filter → Reverb tail → Normalize |

### 1.2 DrumDNA Parameters (20 total)

```
Kick:   pitch=45Hz, fm_depth=3.0, drive=0.55, sub_weight=0.65, attack=3.0ms
Snare:  pitch=230Hz, noise_mix=0.5, metallic=0.2, compression=8.0:1, ott=0.35
Hats:   frequency=8000Hz, metallic=0.15, brightness=0.95, density=16
Clap:   brightness=0.95, reverb=0.15
Global: swing=0.0, humanize=5.0ms
```

### 1.3 Post-Synthesis Bus Processing

```
All drums summed → Compressor (threshold=-20dB, ratio=4:1, attack=10ms, release=40ms) → DC-block @ 10Hz
Stereo: Kick=center, Snare=5% width, Hats=20% width
```

### 1.4 Engine Modules

| Module | Capability |
|--------|-----------|
| `drum_generator.py` | 80+ pattern generators (12 core dubstep, 10 fills/builds, 50+ genre variants), 8 synth functions |
| `drum_pipeline.py` | 6-stage rendering pipeline, sample library fallback |
| `perc_synth.py` | 13 synthesizer types, 50+ presets across 9 banks |
| `groove.py` | 5 groove templates: straight, swing_light, swing_heavy, dubstep_halftime, riddim_bounce, phi_groove |
| `rhythm_engine.py` | Energy-based pattern selection + humanization (5ms timing, 8% velocity) |
| `variation_engine.py` | DrumDNA (20 params) + RhythmDNA (15 params) dataclasses |

---

## 2. ill.Gates 128 Rack Protocol

### 2.1 Core Philosophy

The 128 Rack is a **single Ableton Drum Rack** that maps all 128 MIDI notes, organized into 8 banks of 16 pads — a "one rack rules all" template. It's designed for:

- **Instant recall**: Every sound in your palette lives in one rack
- **Push workflow**: 8 banks × 16 pads = direct Push 1/2/3 pad mapping
- **Macro performance**: 16 macros mapped to universal parameters = tweak any sound instantly
- **FX consistency**: Shared return chains = cohesive space across all elements
- **CPU efficiency**: Return chains share FX processing instead of duplicating per-pad

### 2.2 128-Pad Bank Organization

| Bank | Notes | Purpose | Typical Contents |
|------|-------|---------|-----------------|
| 1 | C-1 → D#0 | **Kicks** | Sub kicks, punchy kicks, layered kicks, processed kicks, one-shots |
| 2 | E0 → G#1 | **Snares & Claps** | Acoustic snares, electronic snares, claps, rimshots, layered hits |
| 3 | A1 → C#2 | **Hi-Hats & Cymbals** | Closed hats, open hats, pedal hats, rides, crashes, splashes |
| 4 | D2 → F#3 | **Percussion** | Toms, congas, bongos, shakers, tambourines, woodblocks |
| 5 | G3 → B3 | **Bass Shots** | Sub hits, reese stabs, bass one-shots, 808 tails |
| 6 | C4 → D#5 | **Synth Stabs** | Chord stabs, lead hits, pluck one-shots, pad swells |
| 7 | E5 → G#5 | **FX & Risers** | Impacts, risers, sweeps, noise bursts, reverse cymbals |
| 8 | A5 → C#6 | **Vocals & Misc** | Vocal chops, ad-libs, foley, resampled material |

### 2.3 Macro Control Mapping

The 128 Rack's power comes from **universally mapped macros** that control the same parameter across all pads:

| Macro | Name | Target | Range |
|-------|------|--------|-------|
| 1 | **Attack** | Amp envelope attack | 0-127 |
| 2 | **Decay** | Amp envelope decay/release | 0-127 |
| 3 | **Tone** | Filter cutoff / EQ tilt | 0-127 |
| 4 | **Drive** | Saturator amount | 0-127 |
| 5 | **Pitch** | Transpose / pitch envelope | 0-127 |
| 6 | **Space** | Reverb send level | 0-127 |
| 7 | **Time** | Delay send level | 0-127 |
| 8 | **Crush** | Bitcrusher / Redux amount | 0-127 |
| 9-12 | **Mod 1-4** | LFO destinations, filter mod | 0-127 |
| 13 | **Width** | Utility stereo width | 0-127 |
| 14 | **Volume** | Chain volume | 0-127 |
| 15-16 | **Custom** | Song-specific mapping | 0-127 |

### 2.4 Internal Return Chains (6 Available)

| Return | FX | Purpose |
|--------|----|---------|
| A | **Reverb** (long) | Room/hall for cohesive space |
| B | **Delay** (sync'd) | Rhythmic echoes, dub effects |
| C | **Distortion** | Parallel saturation/overdrive |
| D | **Chorus/Flanger** | Movement and width |
| E | **Filter** | Auto Filter for sweeps |
| F | **Special** | Song-specific (granular, spectral, etc.) |

### 2.5 Per-Pad FX Chain (Inside Each Branch)

```
[Simpler/Sampler] → [EQ Eight] → [Compressor] → [Saturator] → [Auto Filter] → [Utility]
```

Each pad has its own processing so that shared return FX receive already-shaped signals.

### 2.6 Choke Groups

| Group | Members | Behavior |
|-------|---------|----------|
| 1 | Closed HH, Open HH, Pedal HH | Closed cuts open (natural hi-hat behavior) |
| 2 | Muted conga, Open conga | Muted cuts open |
| 3+ | Custom per-song | User-defined exclusive groups |

### 2.7 Velocity Zones

- **2-4 velocity layers per pad**: Soft (1-40), Medium (41-90), Hard (91-127)
- Different samples or synthesis parameters per layer
- Creates natural dynamic response without volume automation

---

## 3. Gap Analysis — DUBFORGE vs 128 Rack

### 3.1 🔴 CRITICAL: Pad Count & Bank Organization

**Current:** 8-11 pads (kick, snare, clap, hat_closed, hat_open, side_stick, tom_low, tom_high, crash, ride, cowbell)

**128 Rack:** 128 pads in 8 organized banks

**Impact:** A DUBFORGE-generated ALS opens with a mostly-empty Drum Rack. No bank structure for Push. No room for bass shots, synth stabs, FX, or vocal chops — limiting the rack to pure drums when the 128 Rack philosophy treats it as a full production instrument.

**Recommendation — Phase 1 (Quick Win):**
Expand the `_GM_DRUM_PADS` list to populate at minimum 32 pads (Banks 1-2) with properly named/colored entries:
- Bank 1 (notes 36-51): Kick variations, sub kick, click kick, processed kicks
- Bank 2 (notes 52-67): Snares, claps, rimshots, snare variations

**Recommendation — Phase 2 (Full 128):**
Create a `DUBFORGE_128_TEMPLATE` pad map that populates all 128 pads with:
- Banks 1-4: Drum elements (matches current engine output)
- Banks 5-8: Empty but named/colored placeholder pads for manual loading

### 3.2 🔴 CRITICAL: Macro Controls Hidden & Unmapped

**Current (`als_generator.py` lines 970-990):**
```python
_v(dg, "NumVisibleMacroControls", "0")
_v(dg, "AreMacroControlsVisible", "false")
# All 16 macros = generic "Macro 1-16", value=0, no mapping
```

**128 Rack:** 16 named macros mapped to universal parameters (Attack, Decay, Tone, Drive, Pitch, Space, Time, Crush, etc.)

**Impact:** When a producer opens the ALS, the Drum Rack shows zero macro knobs. This is the single biggest workflow gap — macros are the primary performance interface for sound shaping in Ableton.

**Recommendation:**
1. Set `NumVisibleMacroControls` = `"8"` (or `"16"` for full control)
2. Set `AreMacroControlsVisible` = `"true"`
3. Map macro names to DUBFORGE DrumDNA parameters:

```python
DRUM_MACRO_NAMES = [
    "Kick Pitch",     # Macro 1 → DrumDNA.kick_pitch
    "Kick Drive",     # Macro 2 → DrumDNA.kick_drive
    "Snare Pitch",    # Macro 3 → DrumDNA.snare_pitch
    "Snare OTT",      # Macro 4 → DrumDNA.snare_ott
    "Hat Frequency",   # Macro 5 → DrumDNA.hat_frequency
    "Hat Brightness",  # Macro 6 → DrumDNA.hat_brightness
    "Reverb Send",     # Macro 7 → Return A send
    "Delay Send",      # Macro 8 → Return B send
    "Swing",           # Macro 9 → Groove amount
    "Humanize",        # Macro 10 → Velocity variation
    "Sub Weight",      # Macro 11 → DrumDNA.kick_sub_weight
    "Snare Noise",     # Macro 12 → DrumDNA.snare_noise_mix
    "Clap Reverb",     # Macro 13 → DrumDNA.clap_reverb
    "Density",         # Macro 14 → DrumDNA.hat_density
    "Master Drive",    # Macro 15 → Bus saturation
    "Width",           # Macro 16 → Stereo width
]
```

Note: Actual macro → parameter *mapping* in XML requires `ModulationTarget` connections inside each branch's device chain. This is non-trivial but achievable in the ALS generator.

### 3.3 🟡 HIGH: Empty Return Chains

**Current (`als_generator.py` line 1000):**
```python
ET.SubElement(dg, "ReturnBranches")  # empty
```

**128 Rack:** 6 return chains (Reverb, Delay, Distortion, Chorus, Filter, Special)

**Impact:** Every pad's send knobs route to nothing. Return chains are the CPU-efficient way to add shared space and character — without them, the Drum Rack has no internal FX processing.

**Recommendation:**
Build 4-6 return chains in `_build_drum_group_device()`:

```
Return A: Reverb (Ableton Reverb or Hybrid Reverb, dubstep room preset)
Return B: Delay (Simple Delay, 1/4 sync'd, feedback 30%)
Return C: Saturator (warm tube, drive 6dB)
Return D: Auto Filter (LP, cutoff mapped to macro)
Return E: Chorus-Ensemble (subtle width)
Return F: Redux (lo-fi character)
```

Each return is an AudioEffectReturnBranch with a Devices element containing the inline effect. The `_build_eq8()` and similar builders already exist in `als_generator.py` — extend this pattern for Reverb/Delay/Saturator/AutoFilter.

### 3.4 🟡 HIGH: Per-Pad Device Chains Empty

**Current (`als_generator.py` line 893):**
```python
a2a = ET.SubElement(dc_slot, "AudioToAudioDeviceChain", Id=str(ids.next()))
ET.SubElement(a2a, "Devices")  # EMPTY
```

**128 Rack:** Each pad chain contains `EQ Eight → Compressor → Saturator → Auto Filter → Utility`

**Impact:** In Ableton, each pad has no processing. The carefully crafted per-element DSP from forge.py (transient shaping, OTT, tape saturation) exists only in the bounced WAV — not in the ALS project. A producer can't tweak individual pad tones without adding effects manually.

**Recommendation — Minimal:**
Add per-pad EQ Eight (using existing `_build_eq8()`) with role-specific presets:
- Kick pad: High-pass nothing, low-shelf +3dB @ 60Hz, notch -3dB @ 300Hz
- Snare pad: Bell +2dB @ 200Hz body, shelf +3dB @ 5kHz crack
- Hat pads: High-shelf +3dB @ 10kHz

**Recommendation — Full:**
Build per-pad chains mirroring forge.py processing:
- Kick: `EQ Eight → Compressor (10:1) → Saturator (tape) → Utility`
- Snare: `EQ Eight → Compressor (8:1) → Saturator (transistor) → Utility`
- Hats: `EQ Eight → Saturator (tape, light) → Utility`

This requires new builder functions: `_build_compressor()`, `_build_saturator()`, `_build_auto_filter()`, `_build_utility()` — following the same XML schema pattern as `_build_eq8()`.

### 3.5 ✅ OK: Choke Groups

**Current (`make_wild_ones_v12.py` lines 266-267):**
```python
ALSDrumPad(note=CLOSED_HH, name="CLOSED HH", color=3, choke_group=1),
ALSDrumPad(note=OPEN_HH,   name="OPEN HH",   color=3, choke_group=1),
```

**128 Rack:** Choke group 1 for hi-hat family.

**Status:** ✅ Correctly implemented. Closed and open hi-hats share choke group 1. The `_build_drum_branch()` function writes `ChokeGroup` into `BranchInfo`.

**Minor Enhancement:** Add choke group 2 for muted/open percussion pairs (congas, toms) when those elements are present.

### 3.6 🟠 MEDIUM: No Velocity Zones

**Current:** Each pad has a single `BranchSelectorRange` with `Min=Max=note` (single key, no velocity differentiation). Synthesis uses the same parameters regardless of MIDI velocity.

**128 Rack:** 2-4 velocity layers per pad (Soft/Medium/Hard) with different samples or synthesis parameters per layer.

**Impact:** MIDI velocity only affects volume — it doesn't change the tonal character of hits. A soft ghost note snare sounds identical to a hard accent snare, just quieter.

**Recommendation:**
This is a synthesis-level change. Two approaches:
1. **ALS approach:** Add velocity-zone child chains within each pad (Soft: vel 1-60, Hard: vel 61-127) with different Simpler settings
2. **Engine approach:** Make forge.py per-hit synthesis velocity-aware — change `snare_noise_mix`, `kick_fm_depth`, `hat_brightness` based on velocity

### 3.7 🟠 MEDIUM: No Chain Select / Kit Banks

**Current:** `ChainSelector` exists in the XML but is set to 0 with no zone mappings to switch between kits.

**128 Rack:** Chain Select zones allow switching between entire sound palettes — e.g., ChainSelector 0-31 = acoustic kit, 32-63 = electronic kit, 64-95 = hybrid kit.

**Impact:** Each DUBFORGE track gets one fixed DrumDNA. No ability to switch drum character between verse/drop/breakdown without manual intervention.

**Recommendation — Future:**
Map DrumDNA presets to chain selector zones:
- Zone 0-31: Default (current)
- Zone 32-63: Aggressive (higher drive, brighter, more FM)
- Zone 64-95: Minimal (lower drive, darker, less saturation)
- Zone 96-127: Experimental (extreme FM, granular, glitch)

### 3.8 🟢 LOW: No Round-Robin

**Current:** Each hit is a unique synthesis pass (not sample-based), so round-robin doesn't apply in the traditional sense. However, the same DrumDNA produces identical waveforms for repeated notes.

**128 Rack:** 2-4 samples per pad with round-robin for natural variation.

**Impact:** Reduced for DUBFORGE because the humanization engine adds timing/velocity variation. However, tonal character is identical between repetitions.

**Recommendation:** Add optional micro-variation to synthesis parameters per hit (±2% pitch, ±5% FM depth) in forge.py to simulate round-robin without actual sample management.

---

## 4. Producer Dojo Methodology Alignment

### 4.1 Workflow Speed

| Principle | DUBFORGE Status | Notes |
|-----------|----------------|-------|
| Template-based rapid prototyping | ✅ YAML config → full track | Core strength |
| Sound design first, mixing second | ✅ 4-layer synthesis with DSP chains | Excellent |
| Resampling workflow | ❌ Not implemented | No resample-in-place or bounce-to-pad |
| One-rack-rules-all | ❌ Drum rack is minimal | Needs 128-pad expansion |
| Macro performance | ❌ Macros hidden | Critical gap |
| Freeze and flatten for CPU | ❌ No freeze markers in ALS | Could add freeze suggestion metadata |

### 4.2 Belt System Mapping

If DUBFORGE were graded on the Producer Dojo belt system for drum rack sophistication:

- **White Belt** (basic): ✅ Can create drum patterns and render audio
- **Yellow Belt** (organization): ⚠️ Pad naming and colors exist but no bank structure
- **Green Belt** (processing): ❌ Per-pad FX chains empty, no returns
- **Blue Belt** (macro control): ❌ Macros hidden and unmapped
- **Brown Belt** (velocity/dynamics): ❌ No velocity layers
- **Black Belt** (full 128 mastery): ❌ Only 8-11 of 128 pads used

**Current grade: Yellow Belt** — Good synthesis, mediocre ALS output.

---

## 5. Ableton Drum Rack Optimization Checklist

| Best Practice | DUBFORGE | Action Required |
|--------------|----------|-----------------|
| Per-pad EQ for tone shaping | ❌ Empty device chains | Build `_build_eq8()` per pad |
| Per-pad compression | ❌ | Build `_build_compressor()` per pad |
| Choke groups for exclusive sounds | ✅ | None |
| Internal returns over track sends | ❌ Empty ReturnBranches | Build 4-6 return chains |
| Macro mapping for quick access | ❌ Macros hidden | Enable + name + map |
| Simpler over Sampler (CPU) | N/A (synthesis) | N/A |
| Nested audio effect racks | ❌ Not used | Consider for parallel processing |
| -6dB headroom per chain | ⚠️ Not enforced | Set mixer Volume in `_build_audio_branch_mixer()` |
| Color code by function | ✅ | Per-pad colors assigned |
| Pad naming convention | ✅ | Clear names (KICK, SNARE, etc.) |
| CPU optimization notes | ❌ | Add Info Text with freeze recommendations |

---

## 6. Implementation Roadmap

### Phase 1 — Quick Wins (ALS Generator Only)

**Effort:** ~200 lines of Python in `als_generator.py`

1. **Enable macros**: Set `NumVisibleMacroControls` = `"8"`, `AreMacroControlsVisible` = `"true"`
2. **Name macros**: Use DrumDNA-derived names instead of generic "Macro 1-16"
3. **Set macro defaults**: Map DrumDNA default values (normalized to 0-127)
4. **Build per-pad EQ Eight**: Reuse `_build_eq8()` with role-specific band settings inside each `_build_drum_branch()` Devices element
5. **Add Utility device per pad**: Set gain to -6dB headroom

### Phase 2 — Return Chains & Per-Pad FX

**Effort:** ~400 lines

1. **Build return chain XML structure**: `AudioEffectReturnBranch` with devices
2. **Add 4 return chains**: Reverb (A), Delay (B), Saturator (C), Auto Filter (D)
3. **Build `_build_compressor()`**: Per the Ableton 12 schema, matching forge.py ratios
4. **Build `_build_saturator()`**: Tape mode for kicks, transistor for snares
5. **Build `_build_auto_filter()`**: LP/HP/BP with cutoff parameter
6. **Wire per-pad send levels**: Add send knobs in `_build_audio_branch_mixer()` pointing to return chains

### Phase 3 — 128-Pad Template

**Effort:** ~300 lines + YAML config

1. **Define 128-pad map**: 8 banks × 16, with names/colors/choke groups
2. **Populate Banks 1-4**: Map to existing engine output (kick variants, snare variants, hat family, percussion)
3. **Populate Banks 5-8**: Placeholder pads (named but empty chains) for manual loading
4. **Add macro variations**: Save 3-4 MacroSnapshots (Default, Aggressive, Minimal, Experimental)

### Phase 4 — Velocity Layers & Chain Select

**Effort:** ~500 lines (engine + ALS)

1. **Velocity-aware synthesis**: Modify forge.py `_gen_drums()` to vary DrumDNA parameters by velocity range
2. **Multi-chain per pad**: Build 2-3 velocity-zone child chains per pad in ALS
3. **Chain Select zones**: Map DrumDNA presets to chain selector ranges for kit switching
4. **Per-section kit switching**: Allow YAML configs to specify different DrumDNA per song section

---

## 7. Code Locations for Implementation

| Change | File | Line(s) | Function |
|--------|------|---------|----------|
| Enable macros | `engine/als_generator.py` | 970-990 | `_build_drum_group_device()` |
| Name macros | `engine/als_generator.py` | 975-980 | `_build_drum_group_device()` |
| Per-pad EQ | `engine/als_generator.py` | 890-893 | `_build_drum_branch()` |
| Return chains | `engine/als_generator.py` | 998-1000 | `_build_drum_group_device()` |
| Compressor builder | `engine/als_generator.py` | after 1040 | New `_build_compressor()` |
| Saturator builder | `engine/als_generator.py` | after 1040 | New `_build_saturator()` |
| AutoFilter builder | `engine/als_generator.py` | after 1040 | New `_build_auto_filter()` |
| Utility builder | `engine/als_generator.py` | after 1040 | New `_build_utility()` |
| 128-pad template | `engine/als_generator.py` | 78-85 | `ALSDrumPad` + new constant |
| Pad map config | `make_template.py` | 705-710 | Drum pad assembly |
| Velocity-aware synth | `forge.py` | Stage [1/9] | `_gen_drums()` |
| DrumDNA macro mapping | `engine/variation_engine.py` | DrumDNA class | Add `to_macro_values()` |

---

## 8. Reference: Ableton Drum Rack XML Schema (12.0_12117)

Key XML elements that DUBFORGE already generates correctly:
- `DrumGroupDevice` with `Id` attribute
- `DrumBranch` per pad with `BranchSelectorRange`, `BranchInfo`
- `AudioToAudioDeviceChain` inside each branch
- `AudioBranchMixerDevice` with Volume/Pan/Speaker
- `MacroControls.{0-15}` as TimeableFloat
- `ChainSelector` as TimeableFloat
- `ChokeGroup` in BranchInfo

Key XML elements that need to be populated:
- `ReturnBranches` → needs `AudioEffectReturnBranch` children
- `Devices` inside each `AudioToAudioDeviceChain` → needs effect devices
- `MacroVariations/MacroSnapshots` → needs snapshot entries
- `ModulationTarget` connections for macro → parameter mapping
- Velocity zone `KeyRange` elements for multi-layer per pad

---

## 9. Conclusion

DUBFORGE's drum *engine* is **black-belt level** — the 4-layer synthesis, phi-groove templates, Fibonacci percussion, and 20-parameter DrumDNA system rival commercial sound design tools. But the *ALS export* is **white/yellow belt** — generating structurally valid but functionally empty Drum Racks that waste Ableton's most powerful workflow features.

The fix is concentrated in `engine/als_generator.py`. No synthesis engine changes are required for Phases 1-3. The existing `_build_eq8()` pattern provides the template for all new device builders.

**Priority order:** Macros (visibility + naming) → Return chains → Per-pad EQ → Per-pad Compressor/Saturator → 128-pad template → Velocity layers.

---

*This audit was produced by analyzing DUBFORGE source code against the ill.Gates 128 Rack methodology, Producer Dojo workflow principles, and Ableton's official Drum Rack documentation (Chapter 24: Instrument, Drum and Effect Racks).*
