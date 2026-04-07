"""
DUBFORGE Engine — Production Recipe Book

Comprehensive production methodology incorporating:
  - Producer Dojo / ill.Gates: The Approach, 128 Rack, Mudpies, VIP System
  - Subtronics: Festival-weight bass design, VIP evolution, spectral layering
  - Dan Winter: Phase coherence, phi-ratio harmonics, golden mean nesting
  - DUBFORGE Doctrine: Fibonacci structure, phi math, fractal self-similarity

Each recipe is a concrete, measurable production procedure with:
  - Steps to execute
  - Quality targets (numeric thresholds)
  - Failure indicators (what to check if it sounds wrong)
  - Fibonacci checkpoint: when in the 144-step plan to apply it

Usage:
    from engine.recipe_book import RecipeBook
    book = RecipeBook()
    recipe = book.get_recipe("sub_bass_design")
    targets = book.get_quality_targets()
    checklist = book.get_checklist_for_step(34)  # Fibonacci checkpoint
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any

# ═══════════════════════════════════════════════════════════════════════════
# RECIPE DATA STRUCTURES
# ═══════════════════════════════════════════════════════════════════════════


@dataclass
class QualityTarget:
    """A measurable quality metric with pass/fail thresholds."""
    name: str
    metric: str           # what to measure
    target_min: float
    target_max: float
    unit: str
    measurement_tool: str  # which analysis function to use
    priority: str          # CRITICAL / HIGH / MEDIUM / LOW
    failure_symptom: str   # what it sounds like when this fails


@dataclass
class RecipeStep:
    """A single step in a production recipe."""
    order: int
    action: str
    details: str
    parameters: dict[str, Any] = field(default_factory=dict)
    quality_check: str = ""
    common_mistake: str = ""


@dataclass
class Recipe:
    """A complete production recipe — a repeatable procedure."""
    name: str
    category: str          # SOUND_DESIGN / DRUMS / ARRANGEMENT / MIXING / MASTERING / FX
    description: str
    source: str            # who/what this technique comes from
    steps: list[RecipeStep] = field(default_factory=list)
    quality_targets: list[QualityTarget] = field(default_factory=list)
    failure_indicators: list[str] = field(default_factory=list)
    fibonacci_steps: list[int] = field(default_factory=list)  # which Fib steps this applies at
    tags: list[str] = field(default_factory=list)

    def as_dict(self) -> dict:
        return asdict(self)


# ═══════════════════════════════════════════════════════════════════════════
# QUALITY TARGETS — Global thresholds for production quality
# ═══════════════════════════════════════════════════════════════════════════

GLOBAL_QUALITY_TARGETS: list[QualityTarget] = [
    # ── Loudness ──
    QualityTarget("LUFS", "integrated_lufs", -12.0, -6.0, "LUFS",
                  "quick_analyze.py", "CRITICAL",
                  "Too quiet = no impact on festival system. Too loud = distorted mush."),
    QualityTarget("True Peak", "true_peak_dbtp", -1.5, -0.1, "dBTP",
                  "quick_analyze.py", "CRITICAL",
                  "Clipping causes digital distortion on playback systems."),
    QualityTarget("Dynamic Range", "dynamic_range_lu", 4.0, 10.0, "LU",
                  "quick_analyze.py", "HIGH",
                  "Too compressed = fatiguing, no punch. Too dynamic = no energy."),

    # ── Spectrum Balance ──
    QualityTarget("Sub Bass %", "sub_pct_raw", 15.0, 45.0, "%",
                  "quick_analyze.py", "CRITICAL",
                  "Too little sub = no chest hit. Too much = mud, speaker damage."),
    QualityTarget("Low Bass %", "low_pct_raw", 10.0, 40.0, "%",
                  "quick_analyze.py", "HIGH",
                  "Low region carries power. Too little = thin. Too much = woofy."),
    QualityTarget("Mid %", "mid_pct_raw", 8.0, 40.0, "%",
                  "quick_analyze.py", "CRITICAL",
                  "Mids are where growls/leads live. Too quiet = no aggression."),
    QualityTarget("High %", "high_pct_raw", 3.0, 22.0, "%",
                  "quick_analyze.py", "HIGH",
                  "Highs add air and energy. Too little = dull. Too much = harsh."),
    QualityTarget("Air %", "air_pct_raw", 2.0, 12.0, "%",
                  "quick_analyze.py", "MEDIUM",
                  "Air band adds sparkle. Too much = sibilant/fatiguing."),

    # ── Stereo ──
    QualityTarget("Stereo Width", "stereo_width", 0.30, 0.85, "ratio",
                  "quick_analyze.py", "HIGH",
                  "Too narrow = mono, boring. Too wide = phase cancellation on PA."),

    # ── Arrangement ──
    QualityTarget("Intro→Drop Contrast", "intro_drop_contrast_db", 5.0, 14.0, "dB",
                  "quick_analyze.py", "CRITICAL",
                  "No contrast = boring drop. Too much = intro inaudible."),
    QualityTarget("Drop→Break Contrast", "drop_break_contrast_db", 3.0, 10.0, "dB",
                  "quick_analyze.py", "HIGH",
                  "No contrast = no breath. Too much = breakdown disappears."),

    # ── Duration ──
    QualityTarget("Track Duration", "duration_s", 180.0, 300.0, "seconds",
                  "quick_analyze.py", "MEDIUM",
                  "Too short = can't build energy. Too long = loses attention."),

    # ── Phase Coherence (Dan Winter) ──
    QualityTarget("Sub Phase Coherence", "sub_phase_coherence", 0.85, 1.0, "ratio",
                  "phase_analyzer", "HIGH",
                  "Phase-incoherent sub = cancellation on mono PA systems."),
]


# ═══════════════════════════════════════════════════════════════════════════
# RECIPES — Complete production procedures
# ═══════════════════════════════════════════════════════════════════════════

def _build_recipes() -> list[Recipe]:
    """Build the complete recipe book."""
    recipes = []

    # ─────────────────────────────────────────────────
    # 1. SUB BASS DESIGN
    # ─────────────────────────────────────────────────
    recipes.append(Recipe(
        name="sub_bass_design",
        category="SOUND_DESIGN",
        description="Design a festival-weight sub bass that translates on PA systems. "
                    "Subtronics approach: clean sine sub with controlled harmonics. "
                    "Dan Winter: phase-coherent fundamental at phi-ratio frequency.",
        source="Subtronics + Dan Winter Phase Coherence",
        steps=[
            RecipeStep(1, "Choose root frequency",
                       "Sub fundamental must be in 30-60 Hz range. Tune to track key. "
                       "Use DNA root_freq × 0.5 or × 0.25 for sub octave.",
                       {"freq_range": "30-60 Hz", "tuning": "track_key"}),
            RecipeStep(2, "Generate clean sine",
                       "Start with pure sine wave. normalize to 0.55 (not higher). "
                       "This is the foundation — clarity over loudness.",
                       {"waveform": "sine", "normalize": 0.55}),
            RecipeStep(3, "Add controlled saturation",
                       "Light saturation (tanh, factor 1.5-2.5) adds harmonics visible on small speakers. "
                       "Too much = distortion. Check: harmonics should be 20-30dB below fundamental.",
                       {"saturation": "tanh", "drive": "1.5-2.5"}),
            RecipeStep(4, "Apply phi envelope",
                       "Attack: 5-15ms (prevents click). Release: attack × phi ≈ 8-24ms. "
                       "Sustain: 1/phi ≈ 0.618 of peak level.",
                       {"attack_ms": "5-15", "release_ratio": "phi", "sustain": 0.618}),
            RecipeStep(5, "Lowpass filter",
                       "Cut everything above 80-120 Hz. This is SUB only — "
                       "mid-bass content goes in a separate layer. SVF filter, no resonance.",
                       {"filter": "svf_lowpass", "cutoff": "80-120 Hz", "Q": 0.707}),
            RecipeStep(6, "Mono enforcement",
                       "Sub MUST be mono below 100 Hz. Phase cancellation kills PA translation.",
                       {"mono_below": "100 Hz"}),
            RecipeStep(7, "Sidechain to kick",
                       "Sidechain depth 0.5-0.7, use BPM-synced envelope. "
                       "Kick and sub must never compete — sidechain creates the pump.",
                       {"depth": "0.5-0.7", "sync": "bpm"}),
            RecipeStep(8, "Level check",
                       "Sub should be 15-30% of drop spectrum energy. "
                       "Run quick_analyze.py. If sub_pct < 15%, increase normalize. "
                       "If sub_pct > 35%, reduce normalize or tighten filter.",
                       {"target_pct": "15-30%"}),
        ],
        quality_targets=[
            QualityTarget("Sub Level", "sub_pct_raw", 15.0, 35.0, "%",
                          "quick_analyze.py", "CRITICAL",
                          "Sub invisible = no chest hit on PA"),
        ],
        failure_indicators=[
            "Sub disappears in car stereo → needs saturation harmonics",
            "Sub sounds muddy → lower the saturation drive",
            "Sub clicks at start of notes → increase attack to 10-15ms",
            "Sub cancels on mono → check phase coherence, enforce mono",
            "Sub fights with kick → increase sidechain depth",
        ],
        fibonacci_steps=[1, 2, 3, 8, 34, 89],
        tags=["bass", "sub", "foundation", "pa_translation"],
    ))

    # ─────────────────────────────────────────────────
    # 2. MID-BASS GROWL DESIGN
    # ─────────────────────────────────────────────────
    recipes.append(Recipe(
        name="mid_bass_growl",
        category="SOUND_DESIGN",
        description="Festival-weight mid-bass growl. Subtronics-style: "
                    "FM synthesis → wavefold → resample chains. "
                    "ill.Gates: start with Mudpie chaos, extract golden textures.",
        source="Subtronics + ill.Gates Mudpie + Growl Resampler",
        steps=[
            RecipeStep(1, "Choose bass type from DNA",
                       "DNA.bass.types defines rotation: neuro, acid, dist_fm, reese, wobble. "
                       "Each type uses different synthesis approach.",
                       {"types": "DNA.bass.types"}),
            RecipeStep(2, "FM synthesis core",
                       "Carrier at root, modulator at phi-ratio. FM depth 3.0-10.0 per DNA. "
                       "Higher depth = more aggressive harmonics.",
                       {"fm_ratio": "phi (1.618)", "depth": "DNA.bass.fm_depth"}),
            RecipeStep(3, "Waveshaping / distortion",
                       "Apply tanh or wavefold distortion. DNA.bass.distortion controls amount. "
                       "0.3-0.6 = warm growl. 0.6-0.9 = aggressive tear. 0.9+ = chaos.",
                       {"distortion": "DNA.bass.distortion", "type": "tanh/wavefold"}),
            RecipeStep(4, "Bandpass to mid range",
                       "Keep 100-600 Hz for growl body. Highpass below 100 Hz (sub lives there). "
                       "Lowpass above 600 Hz (leads/hats live there).",
                       {"highpass": "100 Hz", "lowpass": "600 Hz"}),
            RecipeStep(5, "Modulation (LFO/envelope)",
                       "Apply filter sweep or FM modulation for movement. "
                       "Rate synced to BPM. Depth from DNA energy level.",
                       {"mod_rate": "bpm_synced", "depth": "DNA.energy"}),
            RecipeStep(6, "Resample chain (ill.Gates)",
                       "Bounce → pitch shift → distort → bounce again. 2-3 passes. "
                       "Each pass adds unique harmonic content.",
                       {"passes": "2-3", "per_pass": "pitch_shift + distort"}),
            RecipeStep(7, "Level and mix",
                       "Normalize 0.45-0.60. Mix at 0.25-0.35 in drop. "
                       "Should be audible but not dominate sub.",
                       {"normalize": "0.45-0.60", "mix": "0.25-0.35"}),
        ],
        quality_targets=[
            QualityTarget("Mid Presence", "mid_pct_raw", 20.0, 40.0, "%",
                          "quick_analyze.py", "CRITICAL",
                          "No mids = no aggression, sounds empty"),
        ],
        failure_indicators=[
            "Growl sounds thin → increase FM depth or add layer",
            "Growl is muddy → tighten bandpass, especially lowpass",
            "Growl fights with sub → ensure clean separation at 80-100 Hz",
            "Growl is harsh → reduce distortion or add gentle lowpass at 4kHz",
            "Growl lacks movement → add LFO modulation on filter cutoff",
        ],
        fibonacci_steps=[2, 3, 5, 13, 34, 55],
        tags=["bass", "growl", "mid", "sound_design", "fm"],
    ))

    # ─────────────────────────────────────────────────
    # 3. DRUM SOUND DESIGN
    # ─────────────────────────────────────────────────
    recipes.append(Recipe(
        name="drum_sound_design",
        category="DRUMS",
        description="Festival-weight drum design. Kick: punchy transient + controlled sub tail. "
                    "Snare: layered noise + body. Hats: filtered noise with DNA density.",
        source="Producer Dojo + Subtronics",
        steps=[
            RecipeStep(1, "Kick design",
                       "Sine pitch sweep (200Hz→50Hz in 20-50ms) for click/punch. "
                       "Body: sine at fundamental (50-60Hz, 100-200ms). "
                       "Normalize 0.90. This is the foundation of the rhythm.",
                       {"pitch_start": 200, "pitch_end": 50, "body_freq": "50-60 Hz",
                        "normalize": 0.90}),
            RecipeStep(2, "Snare design",
                       "Noise burst (80-200ms) highpassed at 200Hz, shaped envelope. "
                       "Optional tonal body: triangle wave at 180-220Hz. "
                       "Normalize 0.85. Snare cuts through the mix.",
                       {"noise_dur": "80-200ms", "highpass": 200, "normalize": 0.85}),
            RecipeStep(3, "Hi-hat design",
                       "Short noise burst (5-50ms) bandpassed 3kHz-12kHz. "
                       "Closed: 5-15ms. Open: 30-80ms. "
                       "Density from DNA: hat_density controls how many per bar.",
                       {"closed_ms": "5-15", "open_ms": "30-80",
                        "freq_range": "3k-12k Hz"}),
            RecipeStep(4, "Drum pattern",
                       "Kick: on 1, some on &3 or variations per DNA. "
                       "Snare: on 2, 4 (backbeat). "
                       "Hats: density from DNA (8-16 per bar). "
                       "Fills: accelerating 16th-note rolls at section transitions.",
                       {"kick_pattern": "DNA.drums", "snare_pattern": "2,4",
                        "hat_density": "DNA.hat_density"}),
            RecipeStep(5, "Bus processing",
                       "Drum bus: parallel compression (threshold 1e-4, ratio 4:1). "
                       "Sidechain bus: all non-kick elements duck to kick. "
                       "Glue: gentle bus limiter for cohesion.",
                       {"parallel_comp": True, "sidechain_depth": 0.55}),
            RecipeStep(6, "Crash cymbals",
                       "Crash at drop entries and transition points. "
                       "Normalize 0.55, mix 0.48-0.50. "
                       "Reverse crash before drops for tension.",
                       {"normalize": 0.55, "mix": "0.48-0.50"}),
        ],
        quality_targets=[
            QualityTarget("Kick Punch", "kick_transient_db", -6.0, -1.0, "dB",
                          "transient_analyzer", "CRITICAL",
                          "Weak kick = no foundation, rhythm collapses"),
            QualityTarget("Sidechain Pump", "pump_dips", 5.0, 50.0, "count",
                          "quick_analyze.py", "HIGH",
                          "No pump = static, no groove"),
        ],
        failure_indicators=[
            "Kick has no punch → increase pitch sweep range or transient level",
            "Snare buried → raise normalize or highpass more aggressively",
            "Hats too loud → reduce hat normalize (0.25-0.35)",
            "No groove → check sidechain, adjust depth and release",
            "Drums sound separate from bass → tighten sidechain timing to BPM",
            "Fills don't build energy → use accelerating note density (8ths→16ths→32nds)",
        ],
        fibonacci_steps=[1, 2, 5, 8, 21, 55],
        tags=["drums", "kick", "snare", "hats", "rhythm"],
    ))

    # ─────────────────────────────────────────────────
    # 4. LEAD MELODY DESIGN
    # ─────────────────────────────────────────────────
    recipes.append(Recipe(
        name="lead_melody_design",
        category="SOUND_DESIGN",
        description="Cutting lead melody that sits above the bass. "
                    "DNA-driven: melody_patterns define note sequences, "
                    "phrase_length controls repetition, chord_progression provides harmony.",
        source="Producer Dojo + DUBFORGE DNA System",
        steps=[
            RecipeStep(1, "Choose lead sound",
                       "Supersaw (7 voices, phi-detuned) for trance/dubstep leads. "
                       "Square wave for aggressive, FM for metallic. "
                       "DNA.lead.waveform selects approach.",
                       {"waveform": "DNA.lead.waveform", "voices": 7}),
            RecipeStep(2, "Melody from DNA",
                       "DNA.lead.melody_patterns provides note degree sequences. "
                       "DNA.lead.phrase_length controls how long before pattern repeats. "
                       "Map degrees to scale frequencies.",
                       {"patterns": "DNA.lead.melody_patterns",
                        "phrase_length": "DNA.lead.phrase_length"}),
            RecipeStep(3, "Chord progression",
                       "DNA.lead.chord_progression provides Roman numeral changes. "
                       "Lead melody should follow chord tones or passing tones.",
                       {"progression": "DNA.lead.chord_progression"}),
            RecipeStep(4, "Frequency placement",
                       "Lead lives at 300-2000 Hz. Below 300 = fights with bass. "
                       "Above 2000 = too bright, fatiguing.",
                       {"freq_range": "300-2000 Hz"}),
            RecipeStep(5, "Envelope shaping",
                       "Attack: 2-10ms (percussive stabs) or 50-200ms (swells). "
                       "Release: phi × attack. Sustain: 0.618 of peak.",
                       {"attack": "2-200ms", "release": "phi × attack"}),
            RecipeStep(6, "Spatial processing",
                       "Reverb send for depth. Delay for rhythmic interest. "
                       "Keep lead centered or slightly wide (not extreme stereo).",
                       {"reverb": "medium send", "delay": "bpm synced"}),
        ],
        quality_targets=[
            QualityTarget("Mid Presence", "mid_pct_raw", 20.0, 40.0, "%",
                          "quick_analyze.py", "HIGH",
                          "Lead buried = no melody, track sounds empty"),
        ],
        failure_indicators=[
            "Lead inaudible → raise level or highpass bass more aggressively",
            "Lead sounds thin → add detuned voices or layer with octave",
            "Lead fights with growl → EQ carve at growl fundamental",
            "Melody repetitive → increase phrase_length or add variation patterns",
            "Lead too bright → gentle lowpass at 3-4kHz",
        ],
        fibonacci_steps=[3, 5, 8, 21, 55],
        tags=["lead", "melody", "harmony", "sound_design"],
    ))

    # ─────────────────────────────────────────────────
    # 5. PAD / ATMOSPHERE DESIGN
    # ─────────────────────────────────────────────────
    recipes.append(Recipe(
        name="pad_atmosphere",
        category="SOUND_DESIGN",
        description="Pads fill harmonic space and create atmosphere. "
                    "Essential in breakdowns and intros. Subtronics uses pads "
                    "even in drops for harmonic content behind the bass.",
        source="Producer Dojo + Subtronics + Dan Winter",
        steps=[
            RecipeStep(1, "Chord voicing",
                       "Stack 3-5 notes from DNA chord progression. "
                       "Phi-spread voicing: spread notes by phi-ratio intervals. "
                       "Dan Winter: phase-coherent stacking creates bioactive harmonics.",
                       {"notes": "3-5", "voicing": "phi-spread"}),
            RecipeStep(2, "Waveform selection",
                       "Sine cluster for warm pads. Saw cluster for bright/trance. "
                       "Triangle for mellow. Add subtle detuning (2-5 cents per voice).",
                       {"waveform": "DNA.atmosphere.waveform", "detune": "2-5 cents"}),
            RecipeStep(3, "Envelope — slow attack",
                       "Attack: 100-500ms (pads breathe in). Release: 200-800ms. "
                       "Pads should never be percussive.",
                       {"attack": "100-500ms", "release": "200-800ms"}),
            RecipeStep(4, "Filter — warm lowpass",
                       "Lowpass at 2-5kHz removes harshness. "
                       "Optional filter LFO for subtle movement (slow: 0.1-0.5 Hz).",
                       {"filter": "lowpass", "cutoff": "2-5 kHz", "lfo": "0.1-0.5 Hz"}),
            RecipeStep(5, "Stereo width",
                       "Pads can be wide — they fill the stereo field. "
                       "Apply Haas delay (5-25ms) or M/S widening. "
                       "Keep below 100Hz mono to avoid phase issues.",
                       {"width": "wide", "mono_below": "100 Hz"}),
            RecipeStep(6, "Level in context",
                       "Breakdown: pad is primary element (mix 0.25-0.35). "
                       "Drop: pad is background fill (mix 0.10-0.18). "
                       "Intro: pad is atmosphere (mix 0.12-0.20, lowpassed).",
                       {"breakdown_mix": "0.25-0.35", "drop_mix": "0.10-0.18"}),
        ],
        quality_targets=[
            QualityTarget("Stereo Width", "stereo_width", 0.30, 0.75, "ratio",
                          "quick_analyze.py", "MEDIUM",
                          "Narrow pads = boring stereo image"),
        ],
        failure_indicators=[
            "Pads sound harsh → lower the lowpass cutoff",
            "Pads mud the bass → highpass pads at 150-200 Hz",
            "Pads disappear in drop → they should be subtle, check level",
            "Breakdown feels empty → pads are missing or too quiet",
            "Phase issues on PA → check mono compatibility below 100Hz",
        ],
        fibonacci_steps=[3, 5, 13, 34],
        tags=["pads", "atmosphere", "harmony", "ambient"],
    ))

    # ─────────────────────────────────────────────────
    # 6. DRUM LOOP ENGINE
    # ─────────────────────────────────────────────────
    recipes.append(Recipe(
        name="drum_loop_engine",
        category="DRUMS",
        description="Building complete drum loops from individual hits. "
                    "Varies across sections: sparse intro → full drop → half-time break.",
        source="Producer Dojo Infinite Drum Rack + DUBFORGE DNA",
        steps=[
            RecipeStep(1, "Define section patterns",
                       "Intro: kick only or kick + sparse hats. "
                       "Build: adding elements gradually (hats, snare rolls). "
                       "Drop: full pattern with fills. "
                       "Breakdown: half-time or stripped back.",
                       {}),
            RecipeStep(2, "Program kick pattern",
                       "Dubstep: kick every beat or half-time (every 2 beats). "
                       "DNA.drums.kick_pattern provides exact positions. "
                       "Double-time sections: kick on every 8th note.",
                       {"pattern": "DNA.drums.kick_pattern"}),
            RecipeStep(3, "Program snare",
                       "Backbeat (2, 4) is standard. Offbeat snares for variation. "
                       "Ghost snares at low velocity for groove.",
                       {"backbeat": [2, 4], "ghost_velocity": "50%"}),
            RecipeStep(4, "Program hi-hats",
                       "8th notes for standard. 16ths for energy. "
                       "Velocity variation: accent on beats, softer offbeats. "
                       "Open hats on offbeats for air.",
                       {"density": "DNA.hat_density", "open_hat_positions": "offbeats"}),
            RecipeStep(5, "Add percussion layers",
                       "Clap layered with snare. Ride for high-energy sections. "
                       "Toms for fills. Shaker for groove.",
                       {}),
            RecipeStep(6, "Drum fills at transitions",
                       "Accelerating rolls: 8th→16th→32nd notes over 1-2 bars. "
                       "Snare rolls into drops. Tom fills for energy builds. "
                       "Silence before drop for impact.",
                       {"fill_style": "accelerating", "positions": "transitions"}),
        ],
        failure_indicators=[
            "Drums sound robotic → add velocity variation and micro-timing",
            "Rhythm doesn't groove → check swing amount, try 55-65% shuffle",
            "Fills don't build → accelerate note density exponentially",
            "Hats dominate mix → reduce hat level, they should be felt not heard",
        ],
        fibonacci_steps=[1, 2, 5, 8, 13],
        tags=["drums", "loops", "patterns", "rhythm", "fills"],
    ))

    # ─────────────────────────────────────────────────
    # 7. DROP DESIGN
    # ─────────────────────────────────────────────────
    recipes.append(Recipe(
        name="drop_design",
        category="ARRANGEMENT",
        description="The drop is the climax — maximum energy, all elements firing. "
                    "Subtronics: the drop should physically hit you. "
                    "Must contrast sharply with build and breakdown.",
        source="Subtronics + RCO Energy Curve",
        steps=[
            RecipeStep(1, "Energy contrast",
                       "Drop must be 6-12 dB louder than intro. "
                       "3-8 dB louder than breakdown. "
                       "This contrast creates perceived impact.",
                       {"intro_contrast": "6-12 dB", "break_contrast": "3-8 dB"}),
            RecipeStep(2, "All layers active",
                       "Sub + mid bass + lead + full drums + pads + FX. "
                       "Everything should be present. Drops should feel full.",
                       {"layers": "all"}),
            RecipeStep(3, "Bass rotation",
                       "Rotate through bass types across bars: neuro→acid→dist_fm. "
                       "DNA.bass.types defines the rotation order. "
                       "Each bass type gets 1-2 bars before switching.",
                       {"rotation": "DNA.bass.types", "bars_per": "1-2"}),
            RecipeStep(4, "Impact at entry",
                       "Crash cymbal + impact hit + silence gap (1/16 note) before. "
                       "The silence before the drop makes it hit harder.",
                       {"silence_gap": "1/16 note", "crash": True, "impact": True}),
            RecipeStep(5, "Drop 2 variation",
                       "Drop 2 must differ: different bass types, higher energy, "
                       "double-time option, added elements. "
                       "Subtronics VIP principle: evolve, don't repeat.",
                       {"variation": "different bass, higher energy, new elements"}),
            RecipeStep(6, "Sidechain pumping",
                       "Sidechain all non-kick elements to kick. "
                       "Depth 0.5-0.7 in drops. Creates the rhythmic pump. "
                       "quick_analyze.py should detect pumping in drop section.",
                       {"depth": "0.5-0.7", "target": "all non-kick"}),
        ],
        quality_targets=[
            QualityTarget("Intro→Drop", "intro_drop_contrast_db", 5.0, 14.0, "dB",
                          "quick_analyze.py", "CRITICAL", "No contrast = no impact"),
            QualityTarget("Drop→Break", "drop_break_contrast_db", 3.0, 10.0, "dB",
                          "quick_analyze.py", "HIGH", "No contrast = no breath"),
        ],
        failure_indicators=[
            "Drop doesn't hit → check energy contrast with intro/build",
            "Drop sounds empty → check that pads, leads are playing in drops",
            "Drop repetitive → enable bass type rotation",
            "Drop 2 identical to Drop 1 → change bass types, add elements",
            "No pump → check sidechain depth and BPM sync",
        ],
        fibonacci_steps=[5, 8, 13, 21, 34, 55, 89],
        tags=["drop", "arrangement", "energy", "impact", "climax"],
    ))

    # ─────────────────────────────────────────────────
    # 8. BUILD-UP DESIGN
    # ─────────────────────────────────────────────────
    recipes.append(Recipe(
        name="buildup_design",
        category="ARRANGEMENT",
        description="The build creates tension before the drop. Rising energy, "
                    "adding elements, filter sweeps, drum rolls.",
        source="Producer Dojo + RCO Curve",
        steps=[
            RecipeStep(1, "Rising riser",
                       "Noise sweep rising over build duration. "
                       "Duration = BAR × max(build_bars, 8). "
                       "Volume: starts quiet, peaks at drop entry.",
                       {"type": "noise_sweep", "direction": "up"}),
            RecipeStep(2, "Drum roll acceleration",
                       "Snare fill: 8th notes → 16th notes → 32nd notes. "
                       "Volume increases through the roll. "
                       "Last bar: maximum density.",
                       {"acceleration": "8th→16th→32nd"}),
            RecipeStep(3, "Filter sweep",
                       "Lowpass filter opening from 200Hz → 10kHz over build. "
                       "Creates sense of 'opening up'.",
                       {"filter_type": "lowpass", "start": 200, "end": 10000}),
            RecipeStep(4, "Sub drop / riser",
                       "Low sine sweep from 20Hz→100Hz for sub tension. "
                       "Or reverse: high→low for downlifter effect.",
                       {"sub_sweep": "20Hz→100Hz"}),
            RecipeStep(5, "Silence before drop",
                       "0.5-1.0 beat of silence immediately before drop. "
                       "This is the most critical moment — silence makes the drop hit.",
                       {"silence_beats": "0.5-1.0"}),
        ],
        failure_indicators=[
            "Build doesn't create tension → riser too quiet or too short",
            "Drop doesn't feel impactful → no silence gap before drop",
            "Build too long → Fibonacci lengths (8, 13 bars) work best",
            "Build too static → add drum roll acceleration",
        ],
        fibonacci_steps=[5, 8, 13, 21],
        tags=["buildup", "riser", "tension", "transition", "arrangement"],
    ))

    # ─────────────────────────────────────────────────
    # 9. BREAKDOWN / BRIDGE DESIGN
    # ─────────────────────────────────────────────────
    recipes.append(Recipe(
        name="breakdown_design",
        category="ARRANGEMENT",
        description="The breakdown provides contrast and emotional depth. "
                    "Strip back energy, feature melody/chords, give ears a rest. "
                    "ill.Gates: every track needs a moment to breathe.",
        source="ill.Gates The Approach + Subtronics",
        steps=[
            RecipeStep(1, "Strip elements",
                       "Remove kick, heavy bass, full drums. "
                       "Keep: pad, lead melody, maybe sparse hats/perc. "
                       "Energy should be 3-8 dB below drops.",
                       {"remove": ["kick", "heavy_bass", "full_drums"]}),
            RecipeStep(2, "Feature melody",
                       "Lead plays its most memorable phrase. "
                       "This is the 'singable' moment of the track.",
                       {"focus": "lead_melody"}),
            RecipeStep(3, "Pad presence",
                       "Pad dominates the breakdown harmonically. "
                       "Mix: 0.25-0.35 (louder than in drop). "
                       "Filter open (higher cutoff than in drop).",
                       {"pad_mix": "0.25-0.35", "filter": "open"}),
            RecipeStep(4, "Sub presence",
                       "Light sub for warmth (mix 0.15-0.20). "
                       "Creates foundation without energy of full drop sub.",
                       {"sub_mix": "0.15-0.20"}),
            RecipeStep(5, "Transition elements",
                       "Plucks, arps, or textural elements for interest. "
                       "Not energetic — contemplative.",
                       {"elements": "plucks, arps, textures"}),
        ],
        failure_indicators=[
            "Breakdown too energetic → remove more elements, lower levels",
            "Breakdown boring → add melodic interest or textural variation",
            "No contrast with drops → need more dB difference",
            "Breakdown too quiet → sub and pads should still provide warmth",
        ],
        fibonacci_steps=[8, 13, 21, 34],
        tags=["breakdown", "bridge", "contrast", "melodic", "arrangement"],
    ))

    # ─────────────────────────────────────────────────
    # 10. SWEEP / TRANSITION FX
    # ─────────────────────────────────────────────────
    recipes.append(Recipe(
        name="sweep_transition_fx",
        category="FX",
        description="Sweeps, risers, downlifters, impacts — the glue between sections.",
        source="ill.Gates + Producer Dojo",
        steps=[
            RecipeStep(1, "Upward riser",
                       "Noise sweep from low to high before drops. "
                       "8-16 bars duration. Normalize 0.35-0.45.",
                       {"direction": "up", "duration_bars": "8-16"}),
            RecipeStep(2, "Downlifter",
                       "Noise sweep from high to low after drops or into breakdowns. "
                       "4-8 bars. Creates sense of falling energy.",
                       {"direction": "down", "duration_bars": "4-8"}),
            RecipeStep(3, "Impact hit",
                       "Short (50-200ms) layered transient at drop entry. "
                       "Layer: sub boom + noise burst + reverse crash tail. "
                       "Normalize 0.60-0.70.",
                       {"duration_ms": "50-200", "normalize": "0.60-0.70"}),
            RecipeStep(4, "Reverse crash",
                       "Reversed cymbal crash leading into major transitions. "
                       "2-4 beat duration. Classic tension builder.",
                       {"duration_beats": "2-4"}),
            RecipeStep(5, "Vocal chops",
                       "Short vocal fragments at key moments. "
                       "Formant-shifted or pitched. DNA-driven vowels. "
                       "Normalize 0.75. Use sparingly — accent, not element.",
                       {"normalize": 0.75, "usage": "accent"}),
        ],
        failure_indicators=[
            "Transitions feel abrupt → add risers/sweeps between sections",
            "FX overpower the mix → reduce FX levels, they support not lead",
            "No sense of motion → add filter sweeps to transitions",
        ],
        fibonacci_steps=[5, 8, 13, 21, 34],
        tags=["fx", "riser", "sweep", "transition", "impact"],
    ))

    # ─────────────────────────────────────────────────
    # 11. MIXING RECIPE
    # ─────────────────────────────────────────────────
    recipes.append(Recipe(
        name="mixing",
        category="MIXING",
        description="Mix as a SEPARATE pass (ill.Gates The Approach). "
                    "Focus: balance, clarity, impact. Reference against Subtronics.",
        source="ill.Gates The Approach + Subtronics Reference",
        steps=[
            RecipeStep(1, "Gain staging",
                       "Set all element levels relative to kick. "
                       "Kick = loudest transient. Sub = loudest sustained. "
                       "Lead/pads/hats fill around these anchors.",
                       {}),
            RecipeStep(2, "EQ carving",
                       "Each element occupies its frequency band: "
                       "Sub 20-80Hz, Bass 80-300Hz, Mids 300-3kHz, Highs 3k-10kHz, Air 10k+. "
                       "Don't boost pre-master EQ by more than +3dB total.",
                       {"max_boost": "+3 dB"}),
            RecipeStep(3, "Sidechain setup",
                       "Sidechain bus for all non-kick content. "
                       "Depth: 0.55 for drops. Curve synced to BPM. "
                       "ONE sidechain pass — not per-element (causes double-ducking).",
                       {"depth": 0.55, "passes": 1}),
            RecipeStep(4, "Bus compression",
                       "Drum bus: parallel compression, threshold 1e-4, 1ms gain smoothing. "
                       "Mix bus: gentle glue compression. "
                       "Avoid near-zero thresholds (causes spike artifacts).",
                       {"threshold": "1e-4", "smoothing": "1ms"}),
            RecipeStep(5, "Stereo width",
                       "Mono below 100Hz (sub + kick). "
                       "Wide: pads, ambient, hats. "
                       "Center: lead, kick, sub, snare. "
                       "Target overall: 0.30-0.75 width ratio.",
                       {"target_width": "0.30-0.75"}),
            RecipeStep(6, "Automation",
                       "Volume rides for emphasis. Filter sweeps for builds. "
                       "FX sends for depth variation. "
                       "Every section should have different levels.",
                       {}),
            RecipeStep(7, "Reference check",
                       "Run quick_analyze.py. Compare spectrum to targets. "
                       "If Sub < 15% → raise sub. If Mid < 20% → raise growl/lead.",
                       {"tool": "quick_analyze.py"}),
        ],
        quality_targets=GLOBAL_QUALITY_TARGETS[:],
        failure_indicators=[
            "Mix sounds thin → sub and low bass too quiet",
            "Mix sounds muddy → too much low-mid (200-400 Hz buildup)",
            "Mix sounds harsh → too much 3-5kHz",
            "Mix sounds dull → not enough high/air content",
            "Mix too wide → phase issues, check mono compatibility",
            "Mix too narrow → add stereo processing to pads/hats",
        ],
        fibonacci_steps=[13, 21, 34, 55, 89, 144],
        tags=["mixing", "eq", "compression", "stereo", "balance"],
    ))

    # ─────────────────────────────────────────────────
    # 12. MASTERING RECIPE
    # ─────────────────────────────────────────────────
    recipes.append(Recipe(
        name="mastering",
        category="MASTERING",
        description="Final polish. Subtle processing for loudness and translation. "
                    "ill.Gates: mastering is the LAST step. Don't master while mixing.",
        source="ill.Gates The Approach + DUBFORGE Mastering Chain",
        steps=[
            RecipeStep(1, "Pre-master EQ",
                       "Gentle broad EQ only. No narrow surgical cuts. "
                       "eq_low_boost: +1.0 to +2.5 dB at shelf below 100Hz. "
                       "eq_high_boost: +1.5 to +3.0 dB at shelf above 8kHz. "
                       "NEVER cut more than -2dB at any point.",
                       {"low_shelf_boost": "+1.0 to +2.5", "high_shelf_boost": "+1.5 to +3.0"}),
            RecipeStep(2, "Multiband compression",
                       "3-4 bands. Light compression (2:1-4:1). "
                       "Purpose: tonal balance, not loudness. "
                       "Phi crossover frequencies: 89Hz, 233Hz, 610Hz.",
                       {"bands": "3-4", "ratio": "2:1-4:1",
                        "crossovers": "89, 233, 610 Hz"}),
            RecipeStep(3, "Stereo enhancement",
                       "Subtle M/S processing. Widen high frequencies (>2kHz). "
                       "Keep low frequencies mono (<100Hz). "
                       "Don't overdo — 10-15% width increase max.",
                       {"mono_below": "100 Hz", "widen_above": "2 kHz"}),
            RecipeStep(4, "Limiting",
                       "Target: -8 to -6 LUFS for dubstep. "
                       "Ceiling: -0.5 to -0.1 dBTP. "
                       "Don't push past -6 LUFS — leaves no dynamics.",
                       {"target_lufs": "-8 to -6", "ceiling": "-0.5 to -0.1 dBTP"}),
            RecipeStep(5, "Final check",
                       "Run quick_analyze.py on mastered output. "
                       "All metrics should be in target ranges. "
                       "A/B against reference tracks (Subtronics, Samplifire).",
                       {"tool": "quick_analyze.py"}),
        ],
        quality_targets=[
            QualityTarget("LUFS", "integrated_lufs", -10.0, -6.0, "LUFS",
                          "quick_analyze.py", "CRITICAL", "Outside range = too quiet or too crushed"),
            QualityTarget("True Peak", "true_peak_dbtp", -1.5, -0.1, "dBTP",
                          "quick_analyze.py", "CRITICAL", "Clipping or too much headroom"),
        ],
        failure_indicators=[
            "Mastered track sounds worse → mastering too aggressive, reduce limiter",
            "Lost dynamics → LUFS too high, back off the limiter",
            "Clipping → true peak exceeding 0dB, lower ceiling",
            "Sounds dull → high shelf too low, add +1dB at 8kHz",
            "Too much sub → reduce low shelf or highpass at 25Hz",
        ],
        fibonacci_steps=[34, 55, 89, 144],
        tags=["mastering", "limiting", "lufs", "loudness", "final"],
    ))

    # ─────────────────────────────────────────────────
    # 13. ACID BASS DESIGN
    # ─────────────────────────────────────────────────
    recipes.append(Recipe(
        name="acid_bass",
        category="SOUND_DESIGN",
        description="303-style acid bass with resonant filter sweeps. "
                    "Subtronics uses acid elements frequently in drops.",
        source="Subtronics + Roland TB-303 heritage",
        steps=[
            RecipeStep(1, "Sawtooth oscillator",
                       "Start with raw sawtooth at bass frequency. "
                       "Single voice, no detuning — acid is mono.",
                       {"waveform": "sawtooth", "voices": 1}),
            RecipeStep(2, "Resonant lowpass filter",
                       "SVF lowpass with resonance 0.5-0.9. "
                       "Cutoff automated by envelope or LFO.",
                       {"filter": "svf_lowpass", "resonance": "0.5-0.9"}),
            RecipeStep(3, "Filter envelope",
                       "Short decay (50-200ms), high amount. "
                       "Creates the classic 'bwow' acid sound. "
                       "Accent on certain notes for variation.",
                       {"decay_ms": "50-200", "amount": "high"}),
            RecipeStep(4, "Slide / portamento",
                       "Glide between notes (20-50ms). "
                       "Classic 303 slide technique.",
                       {"glide_ms": "20-50"}),
            RecipeStep(5, "Distortion",
                       "Overdrive or tape saturation after filter. "
                       "Adds harmonics and aggression. "
                       "0.3-0.6 drive for authentic, 0.6-0.9 for modern.",
                       {"drive": "0.3-0.9", "type": "tanh"}),
        ],
        failure_indicators=[
            "Doesn't sound acid → resonance too low, increase to 0.7+",
            "Too harsh → reduce resonance or add gentle lowpass after",
            "No movement → filter envelope not connected or too fast",
        ],
        fibonacci_steps=[3, 5, 13, 34],
        tags=["bass", "acid", "303", "filter", "sound_design"],
    ))

    # ─────────────────────────────────────────────────
    # 14. DOUBLE-TIME SECTIONS
    # ─────────────────────────────────────────────────
    recipes.append(Recipe(
        name="double_time",
        category="ARRANGEMENT",
        description="Double-time sections inject maximum energy. "
                    "Subtronics frequently switches between half-time and double-time "
                    "within drops for dynamic contrast.",
        source="Subtronics",
        steps=[
            RecipeStep(1, "Identify placement",
                       "Double-time works best in Drop 2 or final drops. "
                       "4-8 bars of double-time before returning to normal.",
                       {"placement": "drop_2", "duration": "4-8 bars"}),
            RecipeStep(2, "Drum pattern change",
                       "Kick on every 8th note instead of quarter. "
                       "Hats at 32nd note density. "
                       "Snare can stay on 2,4 or double to 8th notes.",
                       {"kick_density": "2x", "hat_density": "2x"}),
            RecipeStep(3, "Bass tempo doubling",
                       "Bass notes at twice the speed. Shorter notes, faster rotation. "
                       "Creates frantic, high-energy feel.",
                       {"bass_speed": "2x"}),
            RecipeStep(4, "Transition in/out",
                       "Fill or silence to mark the switch. "
                       "Don't just jump — signal the change to the listener.",
                       {"transition": "fill + silence"}),
        ],
        failure_indicators=[
            "Double-time sounds messy → simplify other elements when drums double",
            "No contrast → switch back too quickly, need at least 4 bars",
            "Transition jarring → add fill or filter sweep at switch point",
        ],
        fibonacci_steps=[21, 34, 55, 89],
        tags=["double_time", "tempo", "energy", "arrangement"],
    ))

    # ─────────────────────────────────────────────────
    # 15. SILENCE / SPACE DESIGN
    # ─────────────────────────────────────────────────
    recipes.append(Recipe(
        name="silence_space",
        category="ARRANGEMENT",
        description="Strategic silence is the most powerful production tool. "
                    "Subtronics' drops hit because of what comes BEFORE — silence.",
        source="Subtronics + ill.Gates",
        steps=[
            RecipeStep(1, "Pre-drop gap",
                       "0.5-1.0 beats of complete silence before every drop. "
                       "No reverb tails, no sub rumble — TRUE silence.",
                       {"duration": "0.5-1.0 beats"}),
            RecipeStep(2, "Rhythmic space",
                       "Not every beat needs an element. Leave gaps in patterns. "
                       "Empty space in drum patterns creates groove.",
                       {}),
            RecipeStep(3, "Section breathing",
                       "Brief silences (1/8 - 1/4 beat) at phrase boundaries. "
                       "Creates micro-contrast that keeps energy dynamic.",
                       {"duration": "1/8 - 1/4 beat"}),
            RecipeStep(4, "Breakdown stripping",
                       "Breakdowns should remove elements. Silence = reset. "
                       "The emptier the breakdown, the harder the drop hits.",
                       {}),
        ],
        failure_indicators=[
            "Drop doesn't hit → there's no silence before it",
            "Track feels dense/fatiguing → not enough space between elements",
            "No groove → patterns are too full, remove hits",
        ],
        fibonacci_steps=[5, 8, 13, 21, 34],
        tags=["silence", "space", "dynamics", "arrangement"],
    ))

    # ─────────────────────────────────────────────────
    # 16. VOCAL CHOP DESIGN
    # ─────────────────────────────────────────────────
    recipes.append(Recipe(
        name="vocal_chops",
        category="FX",
        description="Short vocal fragments as rhythmic and textural accents.",
        source="ill.Gates 128 Rack + Producer Dojo",
        steps=[
            RecipeStep(1, "Source material",
                       "Vocal one-shots, sampled phrases, formant synthesis. "
                       "DNA provides vowel selections.",
                       {}),
            RecipeStep(2, "Chop and pitch",
                       "Short fragments: 50-200ms. Pitch to track key. "
                       "Formant-shift for character.",
                       {"duration_ms": "50-200", "pitch": "track_key"}),
            RecipeStep(3, "Rhythmic placement",
                       "Off-beat accents in drops. Sustained in breakdowns. "
                       "Use sparingly — vocal chops are seasoning, not the meal.",
                       {"usage": "accent"}),
            RecipeStep(4, "Processing",
                       "Reverb throw for space. Delay for rhythmic echoes. "
                       "Distortion for grit. Normalize 0.75.",
                       {"normalize": 0.75}),
        ],
        failure_indicators=[
            "Vocals dominate → too loud or too frequent, reduce",
            "Vocals sound cheap → better source material or more processing",
        ],
        fibonacci_steps=[8, 13, 21],
        tags=["vocal", "chops", "fx", "accent"],
    ))

    # ─────────────────────────────────────────────────
    # 17. STABS / ONE-SHOTS
    # ─────────────────────────────────────────────────
    recipes.append(Recipe(
        name="stabs_oneshots",
        category="SOUND_DESIGN",
        description="Short, punchy harmonic stabs for rhythmic accents. "
                    "Chord stabs, bass stabs, synth hits.",
        source="Producer Dojo + ill.Gates 128 Rack",
        steps=[
            RecipeStep(1, "Design the sound",
                       "Chord stab: 3-4 notes, short attack (2-5ms), short release (50-100ms). "
                       "Bass stab: single note, heavy processing. "
                       "Synth hit: metallic FM or granular texture.",
                       {}),
            RecipeStep(2, "Tight envelope",
                       "Attack: 1-5ms. Decay: 50-200ms. Sustain: 0. Release: 50-150ms. "
                       "Stabs should be percussive — hit and gone.",
                       {}),
            RecipeStep(3, "Processing",
                       "Compression for punch. Reverb tail for space. "
                       "EQ to carve slot in mix. Normalize 0.60-0.70.",
                       {"normalize": "0.60-0.70"}),
            RecipeStep(4, "Placement",
                       "On-beat or syncopated in drops. "
                       "Can replace snare or layer with it.",
                       {}),
        ],
        failure_indicators=[
            "Stabs lack punch → shorter attack, more compression",
            "Stabs clash with bass → EQ carve at bass frequencies",
        ],
        fibonacci_steps=[5, 8, 13],
        tags=["stabs", "oneshots", "accent", "rhythm"],
    ))

    # ─────────────────────────────────────────────────
    # 18. TRANCE ARP DESIGN
    # ─────────────────────────────────────────────────
    recipes.append(Recipe(
        name="trance_arp",
        category="SOUND_DESIGN",
        description="Fibonacci-timed arpeggiator for trance-influenced dubstep. "
                    "Subtronics uses arp elements in builds and breakdowns.",
        source="DUBFORGE Fibonacci Arp + Trance heritage",
        steps=[
            RecipeStep(1, "Pattern design",
                       "Arp pattern from chord progression notes. "
                       "Fibonacci note timing: 1/8, 1/8, 1/4, 3/8, 1/2, etc. "
                       "Creates non-uniform, organic rhythm.",
                       {}),
            RecipeStep(2, "Sound selection",
                       "Bright pluck or supersaw for classic trance arp. "
                       "Filtered square for darker feel.",
                       {"waveform": "pluck or supersaw"}),
            RecipeStep(3, "Filter automation",
                       "Slowly open lowpass filter over build sections. "
                       "Start muffled → bright at drop.",
                       {}),
            RecipeStep(4, "Stereo delay",
                       "Ping-pong delay for width. Phi-ratio delay times. "
                       "Creates lush stereo field.",
                       {"delay": "ping-pong", "timing": "phi-ratio"}),
        ],
        failure_indicators=[
            "Arp sounds mechanical → add velocity variation and timing humanization",
            "Arp clashes with lead → different octave or rhythmic offset",
        ],
        fibonacci_steps=[5, 8, 13, 21],
        tags=["arp", "trance", "fibonacci", "pattern"],
    ))

    # ─────────────────────────────────────────────────
    # 19. PHASE COHERENCE (Dan Winter)
    # ─────────────────────────────────────────────────
    recipes.append(Recipe(
        name="phase_coherence",
        category="MIXING",
        description="Dan Winter's phase coherence principle: harmonic components "
                    "that nest in phi-ratio produce constructive interference. "
                    "Applied to DUBFORGE: ensure layers are phase-aligned.",
        source="Dan Winter + DUBFORGE Doctrine",
        steps=[
            RecipeStep(1, "Sub phase alignment",
                       "Sub bass must be phase-coherent with kick. "
                       "Check: mono sum should NOT cancel. "
                       "If cancellation detected, invert sub phase.",
                       {"check": "mono_sum_test"}),
            RecipeStep(2, "Phi-ratio harmonics",
                       "Harmonic series at phi ratios (f, f×φ, f×φ², f×φ³) "
                       "creates constructive nesting — Dan Winter's bioactive "
                       "frequency principle. Use in wavetable design.",
                       {"ratios": "1, 1.618, 2.618, 4.236"}),
            RecipeStep(3, "Bass layer phase",
                       "PSBS layers at phi-ratio crossovers: 55, 89, 144, 233 Hz. "
                       "When layers cross at these frequencies, phase coherence is maximized. "
                       "Avoid arbitrary crossover points.",
                       {"crossovers": "55, 89, 144, 233 Hz"}),
            RecipeStep(4, "Stereo phase check",
                       "Mid/Side analysis: if side content > mid content, "
                       "phase issues likely. Target: side/mid ratio 0.30-0.75.",
                       {"target_ratio": "0.30-0.75"}),
            RecipeStep(5, "Golden mean nesting",
                       "Dan Winter: at the golden mean interval, all waves can "
                       "constructively interfere — this is the only ratio where "
                       "phase velocity allows compression without destruction. "
                       "In practice: align modulation rates to phi ratios.",
                       {}),
        ],
        failure_indicators=[
            "Sub cancels in mono → phase inversion needed",
            "Bass layers fight → crossover frequencies not at phi ratios",
            "Stereo sounds phasey → too much stereo processing, reduce",
        ],
        fibonacci_steps=[8, 13, 21, 34, 55, 89],
        tags=["phase", "coherence", "dan_winter", "phi", "alignment"],
    ))

    # ─────────────────────────────────────────────────
    # 20. DRUM ROLL / FILL DESIGN
    # ─────────────────────────────────────────────────
    recipes.append(Recipe(
        name="drum_rolls_fills",
        category="DRUMS",
        description="Drum fills and rolls that build energy into transitions. "
                    "Fibonacci acceleration: note density follows Fibonacci intervals.",
        source="Producer Dojo + DUBFORGE Fibonacci",
        steps=[
            RecipeStep(1, "Choose fill position",
                       "Last 1-2 bars before section changes. "
                       "After the final phrase of a section.",
                       {}),
            RecipeStep(2, "Acceleration pattern",
                       "Start with 8th notes → 16th notes → 32nd notes. "
                       "Fibonacci acceleration: notes at positions following "
                       "Fibonacci intervals (0, 1, 1, 2, 3, 5, 8, 13...).",
                       {"pattern": "fibonacci_acceleration"}),
            RecipeStep(3, "Velocity curve",
                       "Start quiet → build to forte. "
                       "Volume follows the same Fibonacci acceleration.",
                       {"velocity": "ascending"}),
            RecipeStep(4, "Sound selection",
                       "Snare rolls are most common. "
                       "Tom descents for melodic fills. "
                       "Cymbal rolls for washes.",
                       {}),
            RecipeStep(5, "End point",
                       "Fill ends at the exact moment the next section starts. "
                       "Optionally: fill ends with silence gap (see silence recipe).",
                       {}),
        ],
        failure_indicators=[
            "Fill doesn't build energy → velocity too flat, needs crescendo",
            "Fill sounds mechanical → add timing variation (humanize)",
            "Fill too busy → reduce to snare-only roll",
        ],
        fibonacci_steps=[8, 13, 21, 34],
        tags=["drums", "fills", "rolls", "transition", "fibonacci"],
    ))

    # ═══════════════════════════════════════════════════════════════════════
    # DOJO RECIPES — ill.Gates / Producer Dojo methodology
    # ═══════════════════════════════════════════════════════════════════════

    # 21. DOJO 128 RACK — Rapid sample audition system
    # ─────────────────────────────────────────────────
    recipes.append(Recipe(
        name="dojo_128_rack",
        category="SOUND_DESIGN",
        description="ill.Gates 128 Rack — categorize 128 samples into 8 macro pads × 16 zones "
                    "for rapid A/B auditioning. Organized by: Perc, Tonal, Texture, FX, Vocal, "
                    "Atmo, Bass, Wild. Key-mapped for instant access during production.",
        source="ill.Gates / Producer Dojo — 128 Rack technique",
        steps=[
            RecipeStep(1, "Collect 128 samples",
                       "Gather from session recordings, sample packs, Mudpie outputs, "
                       "field recordings. Aim for variety — at least 8 categories.",
                       {"sample_count": 128}),
            RecipeStep(2, "Categorize into 8 macro groups",
                       "Perc (kicks/snares/hats), Tonal (melodic hits), Texture (noise/grain), "
                       "FX (risers/impacts), Vocal (chops/phrases), Atmo (pads/ambience), "
                       "Bass (sub/mid/growl), Wild (unclassified chaos).",
                       {"groups": 8, "zones_per_group": 16}),
            RecipeStep(3, "Key-map across MIDI range",
                       "Map 16 samples per octave across 8 octaves. "
                       "C1-D#2 = Perc, E2-G#3 = Tonal, etc. Each pad instant-trigger.",
                       {"mapping": "chromatic_128"}),
            RecipeStep(4, "Rapid audition workflow",
                       "Play through all 128 pads in under 3 minutes. "
                       "Mark favorites with velocity > 100. Discard weak samples.",
                       {"audition_time_s": 180}),
            RecipeStep(5, "Integrate winners into session",
                       "Top 8-13 sounds become the session palette. "
                       "Route each to its own channel with phi-ratio gain staging.",
                       {"winners": "8-13", "gain_staging": "phi_ratio"}),
        ],
        quality_targets=[
            QualityTarget("Sample Variety", "category_coverage", 6.0, 8.0, "categories",
                          "rack_analyzer", "HIGH",
                          "Too few categories = limited palette, repetitive productions."),
        ],
        failure_indicators=[
            "All samples sound similar → need more variety across categories",
            "Can't find sounds quickly → re-organize key mapping",
            "Too many samples unused → trim to 64 and rebuild",
        ],
        fibonacci_steps=[1, 2, 3, 5],
        tags=["dojo", "128_rack", "sampling", "workflow", "ill_gates"],
    ))

    # 22. DOJO MUDPIES — Chaotic sound generation
    # ─────────────────────────────────────────────────
    recipes.append(Recipe(
        name="dojo_mudpies",
        category="SOUND_DESIGN",
        description="ill.Gates Mudpie technique — record a chaotic 5-minute session of knob-twisting, "
                    "random processing, and sound mangling. Chop the result into regions and extract "
                    "golden sounds. Chaos → Order through resampling.",
        source="ill.Gates / Producer Dojo — Mudpies technique",
        steps=[
            RecipeStep(1, "Set up chaos chain",
                       "Load any sound source (synth, sample, noise). "
                       "Chain 3-5 random effects: distortion → granular → reverb → pitch → filter. "
                       "No rules — maximum experimentation.",
                       {"effects_chain": "random_3_to_5"}),
            RecipeStep(2, "Record 5-minute jam",
                       "Hit record. Twist every knob. Automate randomly. "
                       "No judgment — capture everything. Timer enforced.",
                       {"duration_s": 300, "mode": "chaos_jam"}),
            RecipeStep(3, "Chop into 16 regions",
                       "Slice the recording into 16 equal regions. "
                       "Listen to each for 3 seconds max.",
                       {"regions": 16, "audition_s": 3}),
            RecipeStep(4, "Extract 3-5 golden sounds",
                       "Pick the 3-5 best moments — unique timbres, interesting textures, "
                       "accidental magic. These are your Mudpie gems.",
                       {"extract_count": "3-5"}),
            RecipeStep(5, "Resample and refine",
                       "Process each gem through growl_resampler pipeline. "
                       "Pitch-correct to track key. Normalize. Add to 128 Rack.",
                       {"pipeline": "growl_resampler", "normalize": True}),
        ],
        quality_targets=[
            QualityTarget("Unique Timbres", "spectral_uniqueness", 0.6, 1.0, "ratio",
                          "spectral_analyzer", "HIGH",
                          "Mudpie sounds too similar to source → more chaos needed."),
        ],
        failure_indicators=[
            "All sounds are noise → reduce distortion, add tonal source",
            "Nothing interesting → try different source material or effects order",
            "Sounds too clean → increase chaos, add more random modulation",
        ],
        fibonacci_steps=[1, 2, 3, 5, 8],
        tags=["dojo", "mudpies", "chaos", "resampling", "ill_gates", "creative"],
    ))

    # 23. DOJO NINJA SOUNDS — Singer + Band concept
    # ─────────────────────────────────────────────────
    recipes.append(Recipe(
        name="dojo_ninja_sounds",
        category="SOUND_DESIGN",
        description="ill.Gates Ninja Sounds — every track needs a 'singer' (identity sound) and a "
                    "'band' (supporting layers). The singer is the memorable hook that defines the track. "
                    "The band provides context, weight, and depth without competing.",
        source="ill.Gates / Producer Dojo — Ninja Sounds (Singer/Band)",
        steps=[
            RecipeStep(1, "Design the Singer",
                       "Create ONE identity sound — the face of the track. "
                       "Must be instantly recognizable. Maps to PSBS MID layer. "
                       "This is the sound people hum after the show.",
                       {"layer": "MID", "role": "singer"}),
            RecipeStep(2, "Test Singer in isolation",
                       "Solo the singer. Does it carry the track alone? "
                       "If not, redesign. A great singer needs no band to be compelling.",
                       {"test": "solo_identity"}),
            RecipeStep(3, "Design the Band",
                       "Build supporting layers: SUB (weight), LOW (power), HIGH (presence), "
                       "CLICK (attack). Each serves the singer — never competes. "
                       "Maps to PSBS SUB/LOW/HIGH/CLICK layers.",
                       {"layers": ["SUB", "LOW", "HIGH", "CLICK"], "role": "band"}),
            RecipeStep(4, "Balance Singer vs Band",
                       "Singer should be 3-6 dB louder than any single band member. "
                       "Singer occupies center stage (narrow stereo). "
                       "Band spreads wide for context.",
                       {"singer_gain": "+3 to +6 dB", "singer_stereo": "narrow",
                        "band_stereo": "wide"}),
            RecipeStep(5, "Verify identity test",
                       "Play for someone unfamiliar. Can they identify the 'singer' "
                       "within 5 seconds? If not, singer needs more character.",
                       {"test": "identity_recognition", "time_limit_s": 5}),
        ],
        quality_targets=[
            QualityTarget("Singer Prominence", "mid_prominence_db", 3.0, 8.0, "dB",
                          "spectral_analyzer", "CRITICAL",
                          "Singer buried = no identity. Track is forgettable."),
            QualityTarget("Band Support", "band_coherence", 0.7, 1.0, "ratio",
                          "phase_analyzer", "HIGH",
                          "Band layers fighting singer = mud, no clarity."),
        ],
        failure_indicators=[
            "Can't identify the singer → MID layer too generic, needs character",
            "Band overpowers singer → reduce band levels, especially LOW",
            "Track sounds empty → band needs more layers or wider stereo",
            "Singer sounds thin alone → add subtle harmonics or formant character",
        ],
        fibonacci_steps=[3, 5, 8, 13],
        tags=["dojo", "ninja_sounds", "singer", "band", "identity", "ill_gates"],
    ))

    # 24. DOJO 14-MINUTE HIT — Timer-enforced workflow
    # ─────────────────────────────────────────────────
    recipes.append(Recipe(
        name="dojo_14_minute_hit",
        category="ARRANGEMENT",
        description="ill.Gates 14-Minute Hit — complete a track skeleton in 14 minutes. "
                    "Timer enforced. Decisions must be instant. First instinct wins. "
                    "Prevents decision fatigue and perfectionism paralysis.",
        source="ill.Gates / Producer Dojo — 14-Minute Hit technique",
        steps=[
            RecipeStep(1, "Start timer (T+0:00)",
                       "Set 14-minute countdown. No pausing. No going back. "
                       "Open blank template or 128 Rack session.",
                       {"timer_s": 840, "mode": "countdown"}),
            RecipeStep(2, "4-bar loop (T+0:00 → T+2:00)",
                       "Build a 4-bar loop with kick, bass, and one melodic element. "
                       "First sound you reach for = the right sound. No A/B.",
                       {"bars": 4, "deadline_s": 120}),
            RecipeStep(3, "8-bar expansion (T+2:00 → T+5:00)",
                       "Double to 8 bars. Add hi-hats, snare, FX. "
                       "Start building energy curve. No mixing yet.",
                       {"bars": 8, "deadline_s": 300}),
            RecipeStep(4, "Arrangement skeleton (T+5:00 → T+11:00)",
                       "Copy/paste into full arrangement: Intro → Build → Drop → Break → Drop2 → Outro. "
                       "Use mute/unmute for section variation. Speed over perfection.",
                       {"sections": 6, "deadline_s": 660}),
            RecipeStep(5, "Polish pass (T+11:00 → T+14:00)",
                       "Quick levels pass. One reverb send. One delay send. "
                       "Export. DONE. Do not second-guess.",
                       {"deadline_s": 840, "mode": "finish_or_die"}),
        ],
        quality_targets=[
            QualityTarget("Completion Time", "session_duration_s", 0.0, 840.0, "seconds",
                          "session_timer", "CRITICAL",
                          "Over 14 minutes = decision fatigue has won. Save and move on."),
            QualityTarget("Section Count", "arrangement_sections", 4.0, 8.0, "sections",
                          "arrangement_analyzer", "HIGH",
                          "Fewer than 4 sections = not a complete arrangement sketch."),
        ],
        failure_indicators=[
            "Over 14 minutes → STOP. Save current state. Move on.",
            "Still on sound design at T+5:00 → skip to arrangement immediately",
            "Mixing during arrangement → STOP mixing, just place sections",
            "Going back to change sounds → first instinct was right, move forward",
        ],
        fibonacci_steps=[1, 2, 3, 5, 8, 13],
        tags=["dojo", "14_minute_hit", "timer", "workflow", "decision_fatigue", "ill_gates"],
    ))

    # 25. DOJO LOW PASS NARRATIVE — Frequency-based storytelling
    # ─────────────────────────────────────────────────
    recipes.append(Recipe(
        name="dojo_low_pass_narrative",
        category="MIXING",
        description="ill.Gates Low Pass Narrative Filtering — use low-pass filter automation "
                    "as a storytelling device. Filter position tells the listener where they are "
                    "in the track's emotional journey. Maps directly to RCO energy curves.",
        source="ill.Gates / Producer Dojo — Low Pass Techniques",
        steps=[
            RecipeStep(1, "Intro — Mystery (400-800 Hz)",
                       "Start with LP filter at 400 Hz. Everything is muffled, underwater. "
                       "Gradually open to 800 Hz. Builds curiosity.",
                       {"cutoff_start": 400, "cutoff_end": 800, "section": "INTRO"}),
            RecipeStep(2, "Build — Revelation (800-4000 Hz)",
                       "LP opens from 800 Hz to 4 kHz over 8-16 bars. "
                       "Each element gets brighter as energy builds. "
                       "Use Fibonacci-timed filter keyframes.",
                       {"cutoff_start": 800, "cutoff_end": 4000, "section": "BUILD"}),
            RecipeStep(3, "Drop — Full Open (20 kHz)",
                       "Filter fully open. Maximum brightness and energy. "
                       "The payoff after the build. Instant gratification.",
                       {"cutoff_start": 20000, "cutoff_end": 20000, "section": "DROP"}),
            RecipeStep(4, "Breakdown — Reflection (10000-1000 Hz)",
                       "Filter closes from 10 kHz down to 1 kHz. "
                       "Emotional cooldown. Space for the listener to breathe.",
                       {"cutoff_start": 10000, "cutoff_end": 1000, "section": "BREAK"}),
            RecipeStep(5, "Drop 2 — Reopened (20 kHz)",
                       "Second drop: filter fully open again. "
                       "The return of full energy. Maps to RCO second peak.",
                       {"cutoff_start": 20000, "cutoff_end": 20000, "section": "DROP2"}),
        ],
        quality_targets=[
            QualityTarget("Filter Range", "filter_automation_range_hz", 3000.0, 19600.0, "Hz",
                          "automation_analyzer", "HIGH",
                          "Too narrow filter range = no narrative contrast."),
            QualityTarget("Intro Darkness", "intro_high_content_pct", 0.0, 15.0, "%",
                          "spectral_analyzer", "MEDIUM",
                          "Intro too bright = reveals too much too early."),
        ],
        failure_indicators=[
            "No perceptible difference between sections → widen filter range",
            "Drop doesn't feel open → check intro was actually filtered enough",
            "Breakdown too abrupt → slow the filter close over 4+ bars",
            "Filter movement audible as sweep → use smoother automation curve",
        ],
        fibonacci_steps=[5, 8, 13, 21, 34],
        tags=["dojo", "low_pass", "narrative", "filtering", "automation", "ill_gates"],
    ))

    # 26. DOJO STOCK DEVICE MASTERY — Constraints breed creativity
    # ─────────────────────────────────────────────────
    recipes.append(Recipe(
        name="dojo_stock_device_mastery",
        category="MIXING",
        description="ill.Gates Stock Device Mastery — use ONLY Ableton stock devices "
                    "(Saturator, Glue Compressor, Auto Filter, Corpus, Erosion, etc.). "
                    "Constraints breed creativity. Master the tools you have before buying more.",
        source="ill.Gates / Producer Dojo — Stock Device Mastery",
        steps=[
            RecipeStep(1, "Saturator for harmonics",
                       "Ableton Saturator: Analog Clip mode, Drive 3-8 dB. "
                       "Adds warmth and harmonic content without harshness. "
                       "Use on bass, drums, and master bus.",
                       {"device": "saturator", "drive_db": "3-8"}),
            RecipeStep(2, "Glue Compressor for cohesion",
                       "Glue Comp on drum bus: Ratio 4:1, Attack 10ms, Release Auto. "
                       "On master: Ratio 2:1, gentle 1-2 dB reduction. "
                       "Makes elements feel like they belong together.",
                       {"device": "glue_compressor", "ratio": "2-4"}),
            RecipeStep(3, "Auto Filter for movement",
                       "LP/BP filter with LFO at phi-ratio rate. "
                       "Creates organic movement without automation lanes. "
                       "Resonance at golden ratio (0.618) for musical peaks.",
                       {"device": "auto_filter", "resonance": 0.618}),
            RecipeStep(4, "Corpus for resonance",
                       "Add Corpus after any percussion for pitched resonance. "
                       "Tune to track key. Creates metallic, physical textures.",
                       {"device": "corpus", "tuning": "track_key"}),
            RecipeStep(5, "Erosion for texture",
                       "Erosion: Noise mode, Amount 20-40%. "
                       "Adds organic texture and lo-fi character. "
                       "Use sparingly — a little goes a long way.",
                       {"device": "erosion", "amount_pct": "20-40"}),
        ],
        quality_targets=[
            QualityTarget("Third-Party Plugin Count", "external_plugin_count", 0.0, 0.0, "count",
                          "session_analyzer", "MEDIUM",
                          "Using third-party plugins = not mastering stock devices first."),
        ],
        failure_indicators=[
            "Reaching for third-party plugins → challenge yourself to solve it stock",
            "Stock devices sounding thin → explore hidden parameters and chains",
            "Missing a specific effect → chain 2-3 stock devices to replicate it",
        ],
        fibonacci_steps=[3, 5, 8, 13, 21],
        tags=["dojo", "stock_devices", "constraints", "ableton", "mastery", "ill_gates"],
    ))

    # 27. DOJO RESAMPLING CHAIN — Iterative sound evolution
    # ─────────────────────────────────────────────────
    recipes.append(Recipe(
        name="dojo_resampling_chain",
        category="SOUND_DESIGN",
        description="ill.Gates Resampling Chains — render, process, render again. "
                    "Each pass adds complexity and character. Maximum 3 passes to avoid mud. "
                    "Links directly to growl_resampler.py pipeline.",
        source="ill.Gates / Producer Dojo — Resampling Chains technique",
        steps=[
            RecipeStep(1, "Render source (Pass 0)",
                       "Start with any sound: synth patch, sample, Mudpie output. "
                       "Render to audio. This is your raw material.",
                       {"pass": 0, "action": "render_source"}),
            RecipeStep(2, "Pitch shift + distort (Pass 1)",
                       "Pitch shift ±7 semitones (phi-adjacent interval). "
                       "Apply aggressive distortion: waveshaper or bitcrusher. "
                       "Render result.",
                       {"pass": 1, "pitch_shift": "±7 semi", "distortion": "heavy"}),
            RecipeStep(3, "Granularize + filter (Pass 2)",
                       "Run through granular processor: grain size 21ms (Fibonacci). "
                       "Apply resonant filter sweep. Add subtle reverb. Render.",
                       {"pass": 2, "grain_size_ms": 21, "filter": "resonant_sweep"}),
            RecipeStep(4, "Final render + evaluate (Pass 3)",
                       "Last processing pass: gentle saturation + EQ shaping. "
                       "Render final. Compare to Pass 0 — should be unrecognizable "
                       "but musical. If over-processed, revert to Pass 2.",
                       {"pass": 3, "action": "final_render", "max_passes": 3}),
            RecipeStep(5, "Score and integrate",
                       "Rate the resampled sound on uniqueness (1-10) and musicality (1-10). "
                       "Score > 7 on both = integrate into session. "
                       "Score < 5 on either = start over with new source.",
                       {"scoring": {"uniqueness": "1-10", "musicality": "1-10"}}),
        ],
        quality_targets=[
            QualityTarget("Spectral Evolution", "spectral_distance_from_source", 0.4, 0.9, "ratio",
                          "spectral_analyzer", "HIGH",
                          "Too similar to source = wasted processing. Too different = noise."),
        ],
        failure_indicators=[
            "Sound identical to source after 3 passes → more aggressive processing",
            "Pure noise after 3 passes → reduce distortion, increase tonal elements",
            "Losing musicality → revert to Pass 2 and use gentler final pass",
            "More than 3 passes → STOP. Diminishing returns after 3.",
        ],
        fibonacci_steps=[2, 3, 5, 8],
        tags=["dojo", "resampling", "chain", "growl", "evolution", "ill_gates"],
    ))

    # 28. DOJO VIP SYSTEM — Track evolution through revisitation
    # ─────────────────────────────────────────────────
    recipes.append(Recipe(
        name="dojo_vip_system",
        category="ARRANGEMENT",
        description="ill.Gates VIP System — revisit finished tracks to create evolved versions. "
                    "Identify the weakest section, replace it with new design, add layers, re-master. "
                    "Every VIP should be noticeably better than the original.",
        source="ill.Gates / Producer Dojo — VIP System",
        steps=[
            RecipeStep(1, "Select track for VIP",
                       "Choose your BEST finished track — VIP your winners, not your losers. "
                       "Must be a track you're proud of but know can be better.",
                       {"selection": "best_track"}),
            RecipeStep(2, "Identify weakest element",
                       "Listen critically. What's the weakest moment? "
                       "Usually: bass design, drop impact, or arrangement flow. "
                       "Pick ONE element to upgrade.",
                       {"analysis": "critical_listen", "pick_count": 1}),
            RecipeStep(3, "Replace with new design",
                       "Redesign the weak element using current skills. "
                       "Your skills improve — apply new knowledge to old tracks. "
                       "The VIP should showcase your growth.",
                       {"action": "redesign_weak_element"}),
            RecipeStep(4, "Add one new layer",
                       "Add ONE new element that didn't exist in the original: "
                       "new FX layer, new vocal chop, new percussion pattern. "
                       "This makes the VIP feel fresh, not just patched.",
                       {"action": "add_new_layer", "count": 1}),
            RecipeStep(5, "Re-master and compare",
                       "Full re-master of the VIP. A/B with original at matched levels. "
                       "VIP must be clearly superior. If not, the VIP stays unreleased.",
                       {"action": "remaster_and_compare"}),
        ],
        quality_targets=[
            QualityTarget("VIP Improvement", "vip_vs_original_score", 1.0, 10.0, "delta",
                          "comparison_analyzer", "CRITICAL",
                          "VIP not better than original = wasted effort. Don't release."),
        ],
        failure_indicators=[
            "VIP sounds like a remix, not an upgrade → focus on the SAME elements",
            "Changed too many things → only change ONE weak element + ONE new layer",
            "Original was better → your new design isn't good enough yet, keep practicing",
            "VIP lost the vibe → preserve the singer/identity, only change the band",
        ],
        fibonacci_steps=[21, 34, 55, 89],
        tags=["dojo", "vip", "evolution", "revisit", "growth", "ill_gates"],
    ))

    # 29. DOJO DECISION FATIGUE PREVENTION — Session hygiene
    # ─────────────────────────────────────────────────
    recipes.append(Recipe(
        name="dojo_decision_fatigue",
        category="MIXING",
        description="ill.Gates Decision Fatigue Prevention — limit decisions per session pass "
                    "to maintain quality judgment. Maximum 3 decisions per pass. "
                    "Pomodoro timer blocks. Single-focus sessions only.",
        source="ill.Gates / Producer Dojo — Decision Fatigue Philosophy",
        steps=[
            RecipeStep(1, "Define session focus",
                       "Before starting: declare ONE focus. "
                       "EQ only. OR compression only. OR levels only. "
                       "NEVER mix focus areas in a single pass.",
                       {"focus": "single_task", "examples": ["EQ", "compression", "levels"]}),
            RecipeStep(2, "Set 25-minute Pomodoro",
                       "Timer: 25 minutes of focused work. "
                       "When timer ends: STOP. Take 5-minute break. "
                       "Evaluate: are ears still fresh?",
                       {"timer_s": 1500, "break_s": 300}),
            RecipeStep(3, "Limit to 3 decisions",
                       "In each pass, make maximum 3 changes. "
                       "If more than 3 things need fixing, do another pass after break. "
                       "Each decision must be intentional, not reactive.",
                       {"max_decisions": 3, "mode": "intentional"}),
            RecipeStep(4, "Trust first instinct",
                       "First EQ move is usually the right one. "
                       "If you undo and redo more than once → revert to first choice. "
                       "Second-guessing = decision fatigue has begun.",
                       {"rule": "first_instinct_wins"}),
            RecipeStep(5, "Save and walk away",
                       "After 2 Pomodoro blocks (50 min): STOP for the day. "
                       "Save project. Walk away. Fresh ears tomorrow will reveal truth.",
                       {"max_blocks": 2, "action": "save_and_exit"}),
        ],
        quality_targets=[
            QualityTarget("Decisions Per Pass", "decisions_count", 1.0, 3.0, "count",
                          "session_tracker", "HIGH",
                          "More than 3 decisions per pass = fatigue, bad judgment."),
            QualityTarget("Session Duration", "session_duration_min", 0.0, 50.0, "minutes",
                          "session_timer", "MEDIUM",
                          "Over 50 minutes = ears fatigued, judgment compromised."),
        ],
        failure_indicators=[
            "Undoing changes repeatedly → decision fatigue, take a break NOW",
            "Session over 50 minutes → STOP, save, continue tomorrow",
            "Mixing focus areas (EQ + compression in one pass) → separate into passes",
            "More than 3 changes in one pass → revert extras, do another pass later",
        ],
        fibonacci_steps=[8, 13, 21, 34, 55, 89],
        tags=["dojo", "decision_fatigue", "pomodoro", "workflow", "session", "ill_gates"],
    ))

    return recipes


# ═══════════════════════════════════════════════════════════════════════════
# RECIPE BOOK CLASS — API for accessing recipes
# ═══════════════════════════════════════════════════════════════════════════

class RecipeBook:
    """Production recipe book — complete methodology reference.

    Usage:
        book = RecipeBook()
        recipe = book.get_recipe("sub_bass_design")
        targets = book.get_quality_targets()
        checklist = book.get_checklist_for_step(34)
    """

    def __init__(self):
        self.recipes: list[Recipe] = _build_recipes()
        self.quality_targets: list[QualityTarget] = GLOBAL_QUALITY_TARGETS[:]
        self._by_name: dict[str, Recipe] = {r.name: r for r in self.recipes}
        self._by_category: dict[str, list[Recipe]] = {}
        for r in self.recipes:
            self._by_category.setdefault(r.category, []).append(r)

    # ── Lookups ──────────────────────────────────────
    def get_recipe(self, name: str) -> Recipe | None:
        return self._by_name.get(name)

    def get_recipes_by_category(self, category: str) -> list[Recipe]:
        return self._by_category.get(category, [])

    def get_recipes_by_tag(self, tag: str) -> list[Recipe]:
        return [r for r in self.recipes if tag in r.tags]

    def get_all_recipes(self) -> list[Recipe]:
        return self.recipes[:]

    def get_quality_targets(self) -> list[QualityTarget]:
        return self.quality_targets[:]

    # ── Fibonacci Step Lookups ───────────────────────
    def get_recipes_for_step(self, fib_step: int) -> list[Recipe]:
        """Get all recipes relevant at a given Fibonacci step number."""
        return [r for r in self.recipes if fib_step in r.fibonacci_steps]

    def get_checklist_for_step(self, fib_step: int) -> list[dict]:
        """Get a prioritized checklist for a Fibonacci checkpoint step."""
        relevant = self.get_recipes_for_step(fib_step)
        checklist = []
        for r in relevant:
            for target in r.quality_targets:
                checklist.append({
                    "recipe": r.name,
                    "category": r.category,
                    "metric": target.name,
                    "target": f"{target.target_min}-{target.target_max} {target.unit}",
                    "priority": target.priority,
                    "tool": target.measurement_tool,
                })
        return sorted(checklist, key=lambda x: {"CRITICAL": 0, "HIGH": 1,
                                                  "MEDIUM": 2, "LOW": 3}.get(x["priority"], 4))

    # ── Export ───────────────────────────────────────
    def as_dict(self) -> dict:
        return {
            "recipe_count": len(self.recipes),
            "categories": list(self._by_category.keys()),
            "recipes": [r.as_dict() for r in self.recipes],
            "global_quality_targets": [asdict(t) for t in self.quality_targets],
        }

    def summary(self) -> str:
        lines = [
            "╔══════════════════════════════════════════════╗",
            "║  DUBFORGE RECIPE BOOK                       ║",
            "╠══════════════════════════════════════════════╣",
        ]
        for cat, recipes in sorted(self._by_category.items()):
            lines.append(f"║  {cat:<15} ({len(recipes)} recipes)             ║"[:48] + "║")
            for r in recipes:
                lines.append(f"║    • {r.name:<40}║"[:48] + "║")
        lines.append(f"║                                              ║")
        lines.append(f"║  Total: {len(self.recipes)} recipes, "
                     f"{len(self.quality_targets)} quality targets     ║"[:48] + "║")
        lines.append("╚══════════════════════════════════════════════╝")
        return "\n".join(lines)


# ═══════════════════════════════════════════════════════════════════════════
# QUALITY GATE FUNCTIONS — Sprint 1: GOVERNOR
# ═══════════════════════════════════════════════════════════════════════════

# Style overrides for recipe selection
STYLE_OVERRIDES: dict[str, dict[str, tuple[float, float]]] = {
    "riddim": {"Mid %": (5.0, 30.0), "Stereo Width": (0.20, 0.70)},
    "dubstep": {"Stereo Width": (0.30, 0.85)},
    "hybrid": {"Low %": (12.0, 38.0), "Mid %": (10.0, 38.0)},
}


def select_recipe(style: str = "dubstep", mood: str = "",
                   reference_dna: Any = None) -> dict:
    """
    Select a production recipe with quality targets and per-phase timeboxes.

    Returns a dict with:
        targets: list of quality target dicts (name, target_min, target_max, unit)
        timeboxes: dict of phase → seconds
        style: resolved style
        mood: resolved mood
        recipe_names: list of selected recipe names
    """
    book = RecipeBook()

    # Start with global quality targets
    targets = []
    for qt in book.get_quality_targets():
        t = {
            "name": qt.name,
            "metric": qt.metric,
            "target_min": qt.target_min,
            "target_max": qt.target_max,
            "unit": qt.unit,
            "priority": qt.priority,
        }
        targets.append(t)

    # Apply style-specific overrides
    overrides = STYLE_OVERRIDES.get(style.lower(), {})
    for t in targets:
        if t["name"] in overrides:
            t["target_min"], t["target_max"] = overrides[t["name"]]

    # Select relevant recipes by style tags
    selected = book.get_recipes_by_tag(style.lower())
    if not selected:
        selected = book.get_all_recipes()[:10]  # Fallback: top 10

    # Default phi-ratio timeboxes (840s = 14 minutes total)
    timeboxes = {
        "oracle": 60.0, "collect": 120.0, "recipes": 30.0,
        "sketch": 200.0, "arrange": 150.0, "design": 100.0,
        "mix": 100.0, "master": 30.0, "release": 30.0, "reflect": 20.0,
    }

    return {
        "targets": targets,
        "timeboxes": timeboxes,
        "style": style,
        "mood": mood,
        "recipe_names": [r.name for r in selected],
    }


def check_quality_gate(audio_data: dict, targets: list[dict],
                        phase_name: str = "") -> dict:
    """
    Check measured audio metrics against quality targets.

    Args:
        audio_data: dict with metric names as keys, measured values as values
            e.g. {"LUFS": -8.5, "Dynamic Range": 12.0, "Sub %": 22.0}
        targets: list of target dicts from select_recipe()
        phase_name: name of the phase being gated

    Returns:
        dict with:
            passed: bool — all checks passed
            checks: list of individual check results
            warnings: list of warning strings
    """
    checks = []
    warnings = []

    for t in targets:
        name = t["name"]
        if name not in audio_data:
            continue
        value = audio_data[name]
        t_min = t.get("target_min")
        t_max = t.get("target_max")
        passed = True
        if t_min is not None and value < t_min:
            passed = False
            warnings.append(
                f"{name}: {value:.2f} below min {t_min} {t.get('unit', '')}")
        if t_max is not None and value > t_max:
            passed = False
            warnings.append(
                f"{name}: {value:.2f} above max {t_max} {t.get('unit', '')}")
        checks.append({
            "name": name,
            "value": value,
            "target_min": t_min,
            "target_max": t_max,
            "unit": t.get("unit", ""),
            "passed": passed,
            "priority": t.get("priority", "MEDIUM"),
        })

    all_passed = all(c["passed"] for c in checks) if checks else True
    return {
        "phase": phase_name,
        "passed": all_passed,
        "checks": checks,
        "warnings": warnings,
        "checks_passed": sum(1 for c in checks if c["passed"]),
        "checks_total": len(checks),
    }
