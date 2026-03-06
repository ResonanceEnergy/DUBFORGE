"""
DUBFORGE Engine — Serum 2 Synthesizer Engine

Comprehensive Serum 2 architecture model: oscillator types, wavetable warps,
filters, modulation matrix, effects rack, macros, unison, arpeggiator,
clip sequencer, and preset generation — all governed by phi/Fibonacci doctrine.

Xfer Records Serum 2 — "Advanced Hybrid Synthesizer"
Version modelled: 2.0.x (2024-2025 release)

Reference:
    https://xferrecords.com/products/serum-2
    Serum 2 What's New PDF
    Official support docs

Outputs:
    output/serum2/serum2_architecture.json
    output/serum2/serum2_presets.json
    output/serum2/serum2_wavetable_map.json
    output/serum2/serum2_init_template.json
    output/serum2/serum2_dubstep_patches.json
"""

from __future__ import annotations
import json
import math
import os
from dataclasses import dataclass, field, asdict
from enum import Enum
from pathlib import Path
from typing import Optional

# ═══════════════════════════════════════════════════════════════════════════
# CONSTANTS — DUBFORGE DOCTRINE
# ═══════════════════════════════════════════════════════════════════════════

PHI = 1.6180339887498948482
FIBONACCI = [1, 1, 2, 3, 5, 8, 13, 21, 34, 55, 89, 144, 233]
A4_432 = 432.0
A4_440 = 440.0

# Serum wavetable specs
SERUM_FRAME_SIZE = 2048          # samples per frame
SERUM_MAX_FRAMES = 256           # max wavetable frames
SERUM_SAMPLE_RATE = 44100        # default sample rate
SERUM_BIT_DEPTH = 16             # 16-bit PCM for .wav wavetables
SERUM_CLM_MARKER = b'clm '      # Serum wavetable identification marker

# Serum 2 preset format
SERUM2_PRESET_EXT = '.fxp'       # VST preset format
SERUM2_BANK_EXT = '.fxb'         # VST bank format

# ═══════════════════════════════════════════════════════════════════════════
# OSCILLATOR TYPES — Serum 2 has 5 oscillator types per slot (A/B)
# ═══════════════════════════════════════════════════════════════════════════


class OscillatorType(Enum):
    """Serum 2 oscillator types — each slot A/B can be any of these."""
    WAVETABLE = "wavetable"
    MULTISAMPLE = "multisample"
    SAMPLE = "sample"
    GRANULAR = "granular"
    SPECTRAL = "spectral"


class WarpMode(Enum):
    """
    Serum 2 wavetable warp modes — dual warp slots per oscillator.
    Each oscillator can apply TWO warps simultaneously.
    """
    NONE = "None"
    # Classic Serum warps
    SYNC = "Sync"
    SYNC_WINDOW = "Sync (Window)"
    BEND_PLUS = "Bend +"
    BEND_MINUS = "Bend -"
    BEND_PLUS_MINUS = "Bend +/-"
    PWM = "PWM"
    ASYM_PLUS = "Asym +"
    ASYM_MINUS = "Asym -"
    ASYM_PLUS_MINUS = "Asym +/-"
    FLIP = "Flip"
    MIRROR = "Mirror"
    REMAP_1 = "Remap 1"
    REMAP_2 = "Remap 2"
    REMAP_3 = "Remap 3"
    REMAP_4 = "Remap 4"
    QUANTIZE = "Quantize"
    # FM / Ring Mod modes
    FM_FROM_B = "FM (from B)"
    FM_FROM_A = "FM (from A)"
    RM_FROM_B = "RM (from B)"
    RM_FROM_A = "RM (from A)"
    AM_FROM_B = "AM (from B)"
    AM_FROM_A = "AM (from A)"
    # Phase Distortion
    PD = "Phase Distortion"
    # Serum 2 additions
    FOLD = "Fold"
    WRAP = "Wrap"
    DRIVE = "Drive"
    FILTER = "Filter"


class FilterType(Enum):
    """
    Serum 2 filter types — significantly expanded from Serum 1.
    Organized by filter family.
    """
    # Normal (multi-mode)
    MG_LOW_12 = "MG Low 12"
    MG_LOW_24 = "MG Low 24"
    MG_HIGH_12 = "MG High 12"
    MG_HIGH_24 = "MG High 24"
    MG_BAND_12 = "MG Band 12"
    MG_BAND_24 = "MG Band 24"
    MG_NOTCH_12 = "MG Notch 12"
    MG_NOTCH_24 = "MG Notch 24"
    # Low-pass variants
    LP_12 = "Low 12"
    LP_24 = "Low 24"
    LP_48 = "Low 48"
    LP_GERMAN = "German LP"
    LP_ACID = "Acid"
    # High-pass
    HP_12 = "High 12"
    HP_24 = "High 24"
    HP_48 = "High 48"
    # Band-pass / Notch
    BP_12 = "Band 12"
    BP_24 = "Band 24"
    NOTCH_12 = "Notch 12"
    NOTCH_24 = "Notch 24"
    # Comb / Phaser / Formant
    COMB_PLUS = "Comb +"
    COMB_MINUS = "Comb -"
    COMB_PM = "Comb +/-"
    PHASER = "Phaser"
    FLANGER = "Flanger"
    FORMANT_VOWEL = "Formant (Vowel)"
    FORMANT_I = "Formant I"
    FORMANT_II = "Formant II"
    # Special
    SAMPLE_HOLD = "Sample & Hold"
    RING_MOD = "Ring Mod"
    LOW_EQ = "Low EQ Shelf"
    HIGH_EQ = "High EQ Shelf"
    # Serum 2 additions
    REVERB = "Reverb"
    LADDER = "Ladder"
    SVF_LP = "SVF LP"
    SVF_HP = "SVF HP"
    SVF_BP = "SVF BP"


class FilterRouting(Enum):
    """Filter routing options for dual-filter configuration."""
    SERIAL = "Serial"              # Osc → Filter1 → Filter2
    PARALLEL = "Parallel"          # Osc → Filter1 + Filter2 → Mix
    SPLIT_AB = "Split A/B"         # OscA → Filter1, OscB → Filter2


class EffectType(Enum):
    """
    Serum 2 built-in effects — 10 FX slots available.
    Can be reordered via drag and drop in the FX rack.
    """
    DISTORTION = "Distortion"
    DELAY = "Delay"
    COMPRESSOR = "Compressor"
    CHORUS = "Chorus"
    FLANGER = "Flanger"
    PHASER = "Phaser"
    EQ = "EQ"
    FILTER = "Filter"
    REVERB = "Reverb"
    HYPER_DIMENSION = "Hyper/Dimension"
    # Serum 2 additions
    MULTIBAND_COMPRESSOR = "Multiband Compressor"
    OTT = "OTT"
    PITCH_SHIFT = "Pitch Shift"
    FREQUENCY_SHIFT = "Frequency Shift"
    BITCRUSHER = "Bitcrusher"
    WAVEFOLDER = "Wavefolder"
    TAPE_SATURATOR = "Tape Saturator"


class DistortionMode(Enum):
    """Distortion sub-modes within the Distortion FX."""
    TUBE = "Tube"
    SOFT_CLIP = "Soft Clip"
    HARD_CLIP = "Hard Clip"
    DIODE_1 = "Diode 1"
    DIODE_2 = "Diode 2"
    LIN_FOLD = "Lin Fold"
    SIN_FOLD = "Sin Fold"
    ZERO_SQZ = "Zero Sqz"
    SQR = "Sqr"
    DOWNSAMPLE = "Downsample"
    ASYM = "Asym"
    RECTIFY = "Rectify"
    XOR = "Xor"


class UnisonMode(Enum):
    """Serum 2 unison voice distribution modes."""
    NONE = "None"
    CLASSIC = "Classic"
    SUPER = "Super"
    LINEAR = "Linear"
    CHORD = "Chord"
    MAJOR = "Major"
    MINOR = "Minor"
    # Serum 2 additions
    STACK = "Stack"
    SPREAD = "Spread"
    INV_SAW = "Inv Saw"
    RANDOM = "Random"


class LFOShape(Enum):
    """LFO built-in shapes — Serum also allows custom-drawn shapes."""
    SINE = "Sine"
    TRIANGLE = "Triangle"
    SAW_UP = "Saw Up"
    SAW_DOWN = "Saw Down"
    SQUARE = "Square"
    S_AND_H = "Sample & Hold"
    SMOOTH_RANDOM = "Smooth Random"
    CUSTOM = "Custom"

class LFOMode(Enum):
    """LFO trigger / playback modes."""
    FREE = "Free"              # Free-running (no retrigger)
    SYNC = "Sync"              # BPM-synced
    TRIGGER = "Trigger"        # Retrigger on note
    ENVELOPE = "Envelope"      # One-shot (LFO as envelope)


class VoicingMode(Enum):
    """Oscillator voicing modes."""
    POLY = "Poly"
    MONO = "Mono"
    LEGATO = "Legato"
    MONO_RETRIG = "Mono Retrigger"


class ArpDirection(Enum):
    """Built-in arpeggiator direction modes."""
    UP = "Up"
    DOWN = "Down"
    UP_DOWN = "Up/Down"
    DOWN_UP = "Down/Up"
    RANDOM = "Random"
    ORDER = "Order"


# ═══════════════════════════════════════════════════════════════════════════
# DATA STRUCTURES — Full Serum 2 architecture model
# ═══════════════════════════════════════════════════════════════════════════


@dataclass
class WavetableSlot:
    """A single wavetable loaded into an oscillator."""
    name: str = "Default"
    frames: int = 256
    frame_size: int = SERUM_FRAME_SIZE
    morph_mode: str = "Crossfade"       # Crossfade, Spectral, Spectral (HD)
    smooth_interpolation: bool = True   # Serum 2: near-infinite frame positions


@dataclass
class OscillatorConfig:
    """Configuration for one Serum 2 oscillator slot (A or B)."""
    enabled: bool = True
    osc_type: str = OscillatorType.WAVETABLE.value
    wavetable: Optional[WavetableSlot] = None
    # Position/morph
    wt_position: float = 0.0           # 0.0–1.0 wavetable position
    # Level & pan
    level: float = 0.80                # 0.0–1.0
    pan: float = 0.5                   # 0.0=L, 0.5=C, 1.0=R
    # Tuning
    octave: int = 0                    # -4 to +4
    semi: int = 0                      # -24 to +24
    fine: float = 0.0                  # -100 to +100 cents
    coarse: float = 0.0               # Hz offset
    # Unison
    unison_voices: int = 1             # 1-16
    unison_detune: float = 0.0         # 0.0–1.0
    unison_blend: float = 0.0          # 0.0–1.0
    unison_mode: str = UnisonMode.CLASSIC.value
    # Warp modes (Serum 2: dual warp)
    warp_1: str = WarpMode.NONE.value
    warp_1_amount: float = 0.0
    warp_2: str = WarpMode.NONE.value
    warp_2_amount: float = 0.0
    # Phase
    phase: float = 0.0                 # 0.0–1.0
    random_phase: bool = True
    # Sub-oscillator (basic waveform)
    sub_enabled: bool = False
    sub_shape: str = "Sine"            # Sine, Triangle, Saw, Square, Pulse
    sub_level: float = 0.5
    sub_octave: int = -1               # relative to main osc
    sub_direct_out: bool = False       # bypass filters

    def __post_init__(self):
        if self.wavetable is None:
            self.wavetable = WavetableSlot()


@dataclass
class NoiseOscillator:
    """Serum 2 noise oscillator — one-shot samples or noise textures."""
    enabled: bool = False
    sample: str = "White Noise"
    level: float = 0.25
    pan: float = 0.5
    pitch_tracking: bool = False
    phase: float = 0.0
    random_phase: bool = True
    one_shot: bool = False
    direct_out: bool = False           # bypass filters
    filter_routing: str = "Filter 1"   # Filter 1, Filter 2, Both, None


@dataclass
class FilterConfig:
    """Configuration for one Serum 2 filter."""
    enabled: bool = True
    filter_type: str = FilterType.MG_LOW_24.value
    cutoff: float = 1000.0             # Hz (20–20000)
    resonance: float = 0.0             # 0.0–1.0
    drive: float = 0.0                 # 0.0–1.0
    fat: bool = False                  # analog-style filter fattening
    key_tracking: float = 0.0          # 0.0–1.0
    # Serum 2: filter can blend between types
    morph: float = 0.0                 # 0.0–1.0 blend to second type
    morph_target: str = FilterType.MG_HIGH_24.value


@dataclass
class EnvelopeConfig:
    """ADSR envelope — Serum 2 has 3 assignable envelopes."""
    attack_ms: float = 1.0             # milliseconds
    decay_ms: float = 200.0
    sustain: float = 0.75              # 0.0–1.0
    release_ms: float = 100.0
    # Curvature
    attack_curve: float = 0.0          # -1.0 (log) to +1.0 (exp)
    decay_curve: float = 0.0
    release_curve: float = 0.0


@dataclass
class LFOConfig:
    """LFO configuration — Serum 2 has 4 LFOs with custom shape drawing."""
    enabled: bool = True
    shape: str = LFOShape.SINE.value
    mode: str = LFOMode.SYNC.value
    rate_hz: float = 1.0               # free-running rate
    rate_sync: str = "1/4"             # BPM-synced rate
    phase: float = 0.0                 # start phase 0–360°
    # Custom shape data (list of (x, y) if shape == CUSTOM)
    custom_points: list = field(default_factory=list)
    # LFO envelope (rise/delay)
    rise_ms: float = 0.0
    delay_ms: float = 0.0
    smooth: float = 0.0                # smoothing amount
    # One-shot mode (acts as complex envelope)
    one_shot: bool = False
    loop: bool = True


@dataclass
class ModulationRoute:
    """
    A single modulation assignment in the mod matrix.
    Serum's drag-and-drop system + matrix view.
    """
    source: str = "LFO 1"             # Env 1-3, LFO 1-4, Velocity, Note, etc.
    destination: str = "Osc A WT Pos"  # any modulatable parameter
    amount: float = 0.0                # -1.0 to +1.0
    # Aux source for modulating the modulation depth
    aux_source: Optional[str] = None   # e.g., "Mod Wheel" to control depth
    aux_amount: float = 1.0
    bipolar: bool = True


@dataclass
class EffectSlot:
    """A single effect in the Serum 2 FX rack (up to 10 slots)."""
    enabled: bool = True
    fx_type: str = EffectType.DISTORTION.value
    mix: float = 0.5                   # dry/wet 0.0–1.0
    # Common parameters (specifics depend on fx_type)
    param_a: float = 0.5              # Primary parameter
    param_b: float = 0.5              # Secondary parameter
    param_c: float = 0.5              # Tertiary parameter
    # Distortion sub-mode
    distortion_mode: Optional[str] = None
    # Pre/post filter position
    pre_filter: bool = False


@dataclass
class MacroConfig:
    """
    Serum 2 macro knob — 4 macros available (Serum 2 adds up to 8).
    Each macro can control multiple destinations.
    """
    label: str = "Macro 1"
    value: float = 0.0                 # 0.0–1.0
    targets: list = field(default_factory=list)  # list of (destination, min, max)


@dataclass
class ArpeggiatorConfig:
    """
    Serum 2 arpeggiator + clip sequencer.
    Serum 2 adds a clip-based step sequencer alongside the classic arp.
    """
    enabled: bool = False
    direction: str = ArpDirection.UP.value
    octave_range: int = 2              # 1–8
    tempo_sync: bool = True
    rate: str = "1/8"                  # note rate
    gate: float = 0.5                  # 0.0–1.0
    # Swing
    swing: float = 0.0                 # 0.0–1.0
    # Sequence
    steps: int = 16                    # number of steps
    step_pattern: list = field(default_factory=list)  # vel per step
    # Clip sequencer (Serum 2 new)
    clip_sequencer_enabled: bool = False
    clips: list = field(default_factory=list)  # list of clip patterns


@dataclass
class VoicingConfig:
    """Global voicing settings."""
    mode: str = VoicingMode.POLY.value
    max_voices: int = 8
    portamento_ms: float = 0.0
    portamento_mode: str = "Always"    # Always, Legato
    pitch_bend_range: int = 2          # semitones
    mpe_enabled: bool = False          # Serum 2: MPE support


@dataclass
class Serum2Patch:
    """
    Complete Serum 2 patch — the full state of the synthesizer.
    This mirrors the internal data structure of a .fxp preset.
    """
    name: str = "DUBFORGE Init"
    author: str = "DUBFORGE"
    category: str = "Bass"
    tags: list = field(default_factory=lambda: ["dubstep", "phi", "fractal"])

    # Oscillators
    osc_a: OscillatorConfig = field(default_factory=OscillatorConfig)
    osc_b: OscillatorConfig = field(default_factory=lambda: OscillatorConfig(enabled=False))
    noise: NoiseOscillator = field(default_factory=NoiseOscillator)

    # Filters
    filter_1: FilterConfig = field(default_factory=FilterConfig)
    filter_2: FilterConfig = field(default_factory=lambda: FilterConfig(enabled=False))
    filter_routing: str = FilterRouting.SERIAL.value

    # Envelopes (Env 1 = amp by default)
    env_1: EnvelopeConfig = field(default_factory=EnvelopeConfig)           # Amp
    env_2: EnvelopeConfig = field(default_factory=lambda: EnvelopeConfig(   # Filter
        attack_ms=5.0, decay_ms=300.0, sustain=0.3, release_ms=200.0
    ))
    env_3: EnvelopeConfig = field(default_factory=lambda: EnvelopeConfig(   # Aux
        attack_ms=0.0, decay_ms=100.0, sustain=0.0, release_ms=50.0
    ))

    # LFOs
    lfo_1: LFOConfig = field(default_factory=LFOConfig)
    lfo_2: LFOConfig = field(default_factory=lambda: LFOConfig(enabled=False))
    lfo_3: LFOConfig = field(default_factory=lambda: LFOConfig(enabled=False))
    lfo_4: LFOConfig = field(default_factory=lambda: LFOConfig(enabled=False))

    # Modulation matrix
    mod_matrix: list = field(default_factory=list)  # list of ModulationRoute

    # Effects rack (up to 10)
    effects: list = field(default_factory=list)  # list of EffectSlot

    # Macros (4 standard, up to 8 in Serum 2)
    macro_1: MacroConfig = field(default_factory=lambda: MacroConfig(label="PHI MORPH"))
    macro_2: MacroConfig = field(default_factory=lambda: MacroConfig(label="FM DEPTH"))
    macro_3: MacroConfig = field(default_factory=lambda: MacroConfig(label="SUB WEIGHT"))
    macro_4: MacroConfig = field(default_factory=lambda: MacroConfig(label="GRIT"))

    # Arpeggiator
    arp: ArpeggiatorConfig = field(default_factory=ArpeggiatorConfig)

    # Voicing
    voicing: VoicingConfig = field(default_factory=VoicingConfig)

    # Global
    master_volume: float = 0.80
    master_tune: float = A4_432        # DUBFORGE default: 432 Hz
    quality: str = "2x"                # oversampling: 1x, 2x, 4x, Draft


# ═══════════════════════════════════════════════════════════════════════════
# SERUM 2 ARCHITECTURE DATABASE
# ═══════════════════════════════════════════════════════════════════════════

SERUM2_ARCHITECTURE = {
    "product": "Serum 2",
    "developer": "Xfer Records (Steve Duda)",
    "type": "Advanced Hybrid Synthesizer",
    "version": "2.0.x",
    "price_usd": 249.00,
    "lifetime_free_updates": True,
    "free_upgrade_from_serum_1": True,
    "formats": ["VST3", "AU", "AAX"],
    "bit_depth": "64-bit only",
    "system_requirements": {
        "windows": "Windows 10+",
        "macos": "High Sierra+ (Intel) / Big Sur+ (Apple Silicon)",
        "host": "64-bit VST3, AU, or AAX compatible"
    },
    "factory_content": {
        "presets": 626,
        "wavetables": 288,
    },
    "oscillator_types": {
        "wavetable": {
            "description": "Legendary wavetable engine with smooth interpolation",
            "frame_size": SERUM_FRAME_SIZE,
            "max_frames": SERUM_MAX_FRAMES,
            "features": [
                "Smooth Interpolation (near-infinite frame positions)",
                "Dual warp modes",
                "FM, PD, Ring Mod, Distortion within oscillator",
                "Built-in wavetable editor",
                "Import audio / draw / FFT / morph",
                "Serum clm marker for identification",
            ],
            "warp_modes": [w.value for w in WarpMode],
            "morph_modes": ["Crossfade", "Spectral", "Spectral (HD)"],
        },
        "multisample": {
            "description": "Real instrument replication via SFZ format",
            "features": [
                "Massive exclusive library (orchestra, choir, piano, guitar, etc.)",
                "Open standard SFZ file format (human-readable)",
                "Create/import your own multisamples",
                "Round-robin and velocity layering",
                "Key-split and crossfade zones",
            ],
        },
        "sample": {
            "description": "Advanced sample playback with loop modulation",
            "features": [
                "FM/PD/Distortion processing",
                "Snap loop detection with flexible loop modulation",
                "Rate control for tape-stop effects",
                "Sample slicing with score extraction",
                "Tails mode for natural decay",
                "Realtime score playback",
            ],
        },
        "granular": {
            "description": "Granular synthesis for new textures from samples",
            "features": [
                "Position, size, rate controls",
                "Random spray/scatter",
                "Grain density modulation",
                "Pitch-independent time stretching",
                "Reverse and freeze modes",
            ],
        },
        "spectral": {
            "description": "Realtime harmonic resynthesis with transient detection",
            "features": [
                "FFT-based harmonic resynthesis",
                "Transient detection for timestretching",
                "Shape time and frequencies independently",
                "Spectral filtering and morphing",
                "Harmonic shifting and stretching",
            ],
        },
    },
    "filters": {
        "total_types": len(FilterType),
        "families": [
            "MG (Moog-style ladder)",
            "Standard LP/HP/BP/Notch (6/12/24/48 dB)",
            "German LP (MS-20 style)",
            "Acid (303-style resonance)",
            "Comb (+/-/±)",
            "Phaser / Flanger",
            "Formant (Vowel / I / II)",
            "Sample & Hold",
            "Ring Mod",
            "EQ Shelf (Low/High)",
            "Reverb (filter slot)",
            "Ladder",
            "SVF (LP/HP/BP)",
        ],
        "routing_options": [r.value for r in FilterRouting],
        "features": [
            "Drive per filter",
            "Fat mode (analog warmth)",
            "Key tracking",
            "Morph between filter types",
            "Serial / Parallel / Split routing",
        ],
    },
    "modulation": {
        "envelopes": {
            "count": 3,
            "default_assignment": "Env 1 → Amp",
            "type": "ADSR with curvature control per segment",
            "features": ["Drag-and-drop assignment", "Visual feedback"],
        },
        "lfos": {
            "count": 4,
            "shapes": [s.value for s in LFOShape],
            "modes": [m.value for m in LFOMode],
            "features": [
                "Custom shape drawing",
                "BPM sync with note divisions",
                "One-shot (envelope) mode",
                "Smooth/slew control",
                "Phase offset",
                "Rise time / delay",
            ],
        },
        "matrix": {
            "description": "Drag source → destination with depth control",
            "features": [
                "Drag-and-drop from any source to any parameter",
                "Aux source for modulating modulation depth",
                "Visual routing indicators",
                "Per-route bipolar/unipolar",
                "Matrix view for overview",
            ],
            "sources": [
                "Env 1", "Env 2", "Env 3",
                "LFO 1", "LFO 2", "LFO 3", "LFO 4",
                "Velocity", "Note (Pitch)", "Aftertouch",
                "Mod Wheel", "Pitch Bend",
                "Macro 1-4 (up to 8)",
                "Random", "Alternate",
                "MPE Slide", "MPE Pressure",
            ],
        },
    },
    "effects_rack": {
        "max_slots": 10,
        "drag_reorder": True,
        "available_effects": [e.value for e in EffectType],
        "distortion_modes": [d.value for d in DistortionMode],
    },
    "macros": {
        "standard_count": 4,
        "extended_count": 8,
        "description": "Assignable knobs controlling multiple destinations",
    },
    "unison": {
        "max_voices": 16,
        "modes": [u.value for u in UnisonMode],
        "params": ["Detune", "Blend", "Width (stereo spread)"],
    },
    "voicing": {
        "modes": [v.value for v in VoicingMode],
        "features": ["Portamento with legato mode", "Adjustable voice count", "MPE support"],
    },
    "arpeggiator": {
        "directions": [a.value for a in ArpDirection],
        "features": [
            "BPM sync with rate divisions",
            "Swing control",
            "Gate length",
            "Octave range 1-8",
            "Step sequencer (velocity per step)",
            "Clip sequencer (Serum 2 new)",
        ],
    },
    "wavetable_editor": {
        "features": [
            "Draw waveforms by hand",
            "Import audio files",
            "FFT additive editor",
            "Morph between frames",
            "Process: Normalize, Fade, Crossfade, Invert, etc.",
            "Generate from formula",
            "Export as .wav with clm marker",
        ],
    },
    "preset_format": {
        "extension": ".fxp",
        "bank_extension": ".fxb",
        "serum1_compatibility": "Serum 1 presets load in Serum 2, not vice versa",
        "organization": "Category / Tags / Ratings / Favorites",
    },
}


# ═══════════════════════════════════════════════════════════════════════════
# PHI / FIBONACCI INTEGRATION — DUBFORGE x SERUM 2
# ═══════════════════════════════════════════════════════════════════════════

def phi_unison_detune(voices: int) -> list[float]:
    """
    Calculate unison detune values using phi subdivisions.
    Each voice is offset by cents derived from phi ratios.
    Symmetric around center (0 cents).

    Returns cents offsets for each voice.
    """
    if voices <= 1:
        return [0.0]

    half = voices // 2
    offsets = []
    for i in range(half):
        cents = (PHI ** (i + 1)) * 3.0  # ~4.85, ~7.85, ~12.7, ...
        offsets.append(-cents)
        offsets.append(cents)
    if voices % 2 == 1:
        offsets.insert(len(offsets) // 2, 0.0)
    offsets.sort()
    return offsets


def phi_envelope(base_attack_ms: float = 5.0, base_decay_ms: float = 200.0,
                 base_release_ms: float = 100.0) -> EnvelopeConfig:
    """
    Generate an ADSR envelope with phi-ratio timing.
    Attack : Decay : Release = 1 : phi : phi²

    Sustain set to 1/phi ≈ 0.618.
    """
    return EnvelopeConfig(
        attack_ms=base_attack_ms,
        decay_ms=base_attack_ms * PHI,
        sustain=1.0 / PHI,  # ≈ 0.618
        release_ms=base_attack_ms * (PHI ** 2),
        attack_curve=-0.382,   # -1/phi² — gentle log curve
        decay_curve=0.618,     # 1/phi — exponential decay
        release_curve=0.618,
    )


def phi_filter_cutoff(root_hz: float = 55.0, n_steps: int = 8) -> list[float]:
    """
    Generate a phi-spaced filter cutoff ladder.
    Each step: previous * phi.

    From 55 Hz root: 55, 89, 144, 233, 377, 610, 987, 1597 Hz
    (These approximate Fibonacci numbers!)
    """
    return [root_hz * (PHI ** i) for i in range(n_steps)]


def fibonacci_lfo_rates() -> list[str]:
    """
    Generate LFO sync rates at Fibonacci divisions.
    Maps to Serum's BPM sync notation.
    """
    # Fibonacci bar/beat fractions
    return [
        "1/1",     # 1 bar
        "1/2",     # half note (1)
        "1/3",     # triplet (2)
        "1/5",     # quintuplet (5)
        "1/8",     # eighth (8)
        "1/13",    # Fib-13 division
        "3/1",     # 3 bars (Fib 3)
        "5/1",     # 5 bars (Fib 5)
        "8/1",     # 8 bars (Fib 8)
    ]


def phi_macro_scaling(macro_value: float) -> float:
    """
    Apply phi-curve scaling to a macro value (0–1).
    Creates a golden-ratio response curve instead of linear.
    Result: value^(1/phi) — emphasizes the 0.618 sweet spot.
    """
    return macro_value ** (1.0 / PHI)


def phi_fm_ratio(fundamental: float) -> float:
    """
    Calculate FM modulator frequency as phi ratio of carrier.
    Carrier:Modulator = 1:phi ≈ 1:1.618

    This creates non-integer-ratio FM → inharmonic/metallic overtones
    characteristic of dubstep growl timbres.
    """
    return fundamental * PHI


def fibonacci_wavetable_frames() -> list[int]:
    """
    Valid frame counts for DUBFORGE wavetables.
    Fibonacci numbers up to Serum's 256parcela max.
    """
    return [f for f in FIBONACCI if f <= SERUM_MAX_FRAMES] + [SERUM_MAX_FRAMES]


def phi_effect_mix(depth: float = 0.618) -> float:
    """
    Golden ratio wet/dry mix.
    Default: 1/phi ≈ 0.618 wet = 0.382 dry.
    """
    return min(1.0, depth)


# ═══════════════════════════════════════════════════════════════════════════
# SERUM 2 WAVETABLE MAP — Common wavetable categories and tables
# ═══════════════════════════════════════════════════════════════════════════

WAVETABLE_MAP = {
    "categories": [
        "Analog", "Digital", "Spectral", "Vowel/Formant",
        "Distortion/Noise", "Complex", "User", "DUBFORGE"
    ],
    "dubforge_tables": [
        {
            "name": "DUBFORGE_PHI_CORE",
            "file": "DUBFORGE_PHI_CORE.wav",
            "frames": 256,
            "description": "Phi-spaced additive partials — fractal harmonic series",
            "generation": "phi_harmonic_series + phi_amplitude_curve",
        },
        {
            "name": "DUBFORGE_PHI_CORE_v2_WOOK",
            "file": "DUBFORGE_PHI_CORE_v2_WOOK.wav",
            "frames": 256,
            "description": "Dense phi partials with Fibonacci morph — aggressive",
            "generation": "fibonacci_harmonic_series + morph_frames",
        },
        {
            "name": "DUBFORGE_GROWL_SAW",
            "file": "DUBFORGE_GROWL_SAW.wav",
            "frames": 256,
            "description": "Resampled growl saw — mid-bass character",
            "generation": "growl_resampler saw pipeline",
        },
        {
            "name": "DUBFORGE_GROWL_FM",
            "file": "DUBFORGE_GROWL_FM.wav",
            "frames": 256,
            "description": "FM growl wavetable — metallic mid-range",
            "generation": "growl_resampler FM pipeline",
        },
    ],
    "recommended_factory_tables": [
        "Analog_BD_Sin", "Analog_Saw_Unison", "Basic_Shapes",
        "Digital_Carbon", "Spectral_Harm", "Vowel_Formant_A",
    ],
}


# ═══════════════════════════════════════════════════════════════════════════
# DUBSTEP PATCH PRESETS — Phi-doctrine bass patches for Serum 2
# ═══════════════════════════════════════════════════════════════════════════

def _build_phi_modulation_matrix() -> list[dict]:
    """Standard DUBFORGE modulation matrix — phi-governed assignments."""
    return [
        asdict(ModulationRoute(
            source="Macro 1",
            destination="Osc A WT Pos",
            amount=1.0,
            aux_source="Velocity",
            aux_amount=0.618,
        )),
        asdict(ModulationRoute(
            source="Macro 2",
            destination="Osc B WT Pos",
            amount=PHI - 1,  # 0.618
        )),
        asdict(ModulationRoute(
            source="Env 2",
            destination="Filter 1 Cutoff",
            amount=0.75,
        )),
        asdict(ModulationRoute(
            source="LFO 1",
            destination="Osc A WT Pos",
            amount=0.382,  # 1 - 1/phi
            aux_source="Macro 1",
            aux_amount=1.0,
        )),
        asdict(ModulationRoute(
            source="LFO 2",
            destination="Filter 1 Cutoff",
            amount=0.25,
            aux_source="Mod Wheel",
            aux_amount=1.0,
        )),
        asdict(ModulationRoute(
            source="Velocity",
            destination="Filter 1 Cutoff",
            amount=0.3,
        )),
        asdict(ModulationRoute(
            source="Note (Pitch)",
            destination="Filter 1 Cutoff",
            amount=0.2,
        )),
    ]


def _build_dubstep_fx_rack() -> list[dict]:
    """Standard DUBFORGE dubstep FX rack — phi-mixed effects chain."""
    return [
        asdict(EffectSlot(
            fx_type=EffectType.DISTORTION.value,
            mix=phi_effect_mix(0.382),
            param_a=0.618,            # drive
            distortion_mode=DistortionMode.LIN_FOLD.value,
        )),
        asdict(EffectSlot(
            fx_type=EffectType.OTT.value,
            mix=phi_effect_mix(0.5),
            param_a=0.618,            # depth
            param_b=0.5,              # upward
            param_c=0.382,            # downward
        )),
        asdict(EffectSlot(
            fx_type=EffectType.EQ.value,
            mix=1.0,
            param_a=0.3,              # low shelf boost
            param_b=0.5,              # mid scoop
            param_c=0.7,              # high presence
        )),
        asdict(EffectSlot(
            fx_type=EffectType.COMPRESSOR.value,
            mix=phi_effect_mix(0.618),
            param_a=0.6,              # threshold
            param_b=0.4,              # ratio
        )),
        asdict(EffectSlot(
            fx_type=EffectType.REVERB.value,
            mix=phi_effect_mix(0.15),
            param_a=0.3,              # size
            param_b=0.618,            # decay
            param_c=0.5,              # damping
        )),
    ]


def build_dubstep_patches() -> list[dict]:
    """
    Generate the full DUBFORGE dubstep patch collection for Serum 2.
    Each patch follows phi/Fibonacci doctrine throughout.
    """
    patches = []

    # ─── 1. FRACTAL SUB ─────────────────────────────────────────────
    sub_patch = Serum2Patch(
        name="DUBFORGE Fractal Sub",
        category="Bass",
        tags=["sub", "dubstep", "phi", "fractal", "clean"],
    )
    sub_patch.osc_a.osc_type = OscillatorType.WAVETABLE.value
    sub_patch.osc_a.wavetable = WavetableSlot(name="DUBFORGE_PHI_CORE", frames=256)
    sub_patch.osc_a.wt_position = 0.0
    sub_patch.osc_a.octave = -1
    sub_patch.osc_a.level = 0.9
    sub_patch.osc_a.unison_voices = 1
    sub_patch.osc_a.sub_enabled = True
    sub_patch.osc_a.sub_shape = "Sine"
    sub_patch.osc_a.sub_level = 0.8
    sub_patch.osc_a.sub_octave = -1
    sub_patch.osc_b.enabled = False
    sub_patch.filter_1.filter_type = FilterType.LP_24.value
    sub_patch.filter_1.cutoff = phi_filter_cutoff(55.0)[2]  # ~144 Hz
    sub_patch.filter_1.resonance = 0.1
    sub_patch.env_1 = phi_envelope(1.0)
    sub_patch.env_2 = phi_envelope(3.0)
    sub_patch.voicing.mode = VoicingMode.MONO.value
    sub_patch.voicing.portamento_ms = 30.0
    sub_patch.voicing.portamento_mode = "Legato"
    sub_patch.master_tune = A4_432
    patches.append(asdict(sub_patch))

    # ─── 2. PHI GROWL ───────────────────────────────────────────────
    growl_patch = Serum2Patch(
        name="DUBFORGE Phi Growl",
        category="Bass",
        tags=["growl", "dubstep", "mid-bass", "aggressive", "phi"],
    )
    growl_patch.osc_a.wavetable = WavetableSlot(name="DUBFORGE_GROWL_SAW", frames=256)
    growl_patch.osc_a.wt_position = 0.382
    growl_patch.osc_a.unison_voices = 5  # Fibonacci
    growl_patch.osc_a.unison_detune = 0.35
    growl_patch.osc_a.unison_mode = UnisonMode.SUPER.value
    growl_patch.osc_a.warp_1 = WarpMode.FM_FROM_B.value
    growl_patch.osc_a.warp_1_amount = 0.618
    growl_patch.osc_a.warp_2 = WarpMode.FOLD.value
    growl_patch.osc_a.warp_2_amount = 0.382

    growl_patch.osc_b.enabled = True
    growl_patch.osc_b.wavetable = WavetableSlot(name="DUBFORGE_PHI_CORE_v2_WOOK", frames=256)
    growl_patch.osc_b.wt_position = 0.618
    growl_patch.osc_b.semi = 0
    growl_patch.osc_b.fine = 0.0  # exact phi ratio achieved via FM warp

    growl_patch.filter_1.filter_type = FilterType.LP_ACID.value
    growl_patch.filter_1.cutoff = phi_filter_cutoff(55.0)[4]  # ~377 Hz
    growl_patch.filter_1.resonance = 0.618
    growl_patch.filter_1.drive = 0.5

    growl_patch.filter_2.enabled = True
    growl_patch.filter_2.filter_type = FilterType.FORMANT_VOWEL.value
    growl_patch.filter_2.cutoff = phi_filter_cutoff(55.0)[5]  # ~610 Hz
    growl_patch.filter_routing = FilterRouting.SERIAL.value

    growl_patch.env_2 = phi_envelope(2.0)
    growl_patch.lfo_1.shape = LFOShape.CUSTOM.value
    growl_patch.lfo_1.rate_sync = "1/8"
    growl_patch.lfo_1.mode = LFOMode.SYNC.value

    growl_patch.mod_matrix = _build_phi_modulation_matrix()
    growl_patch.effects = _build_dubstep_fx_rack()

    growl_patch.macro_1.label = "PHI MORPH"
    growl_patch.macro_2.label = "FM DEPTH"
    growl_patch.macro_3.label = "SUB WEIGHT"
    growl_patch.macro_4.label = "GRIT"

    growl_patch.voicing.mode = VoicingMode.MONO.value
    growl_patch.voicing.portamento_ms = 15.0
    growl_patch.master_tune = A4_432
    patches.append(asdict(growl_patch))

    # ─── 3. FIBONACCI FM SCREECH ────────────────────────────────────
    screech_patch = Serum2Patch(
        name="DUBFORGE Fibonacci FM Screech",
        category="Bass",
        tags=["screech", "FM", "fibonacci", "aggressive", "lead"],
    )
    screech_patch.osc_a.wavetable = WavetableSlot(name="DUBFORGE_GROWL_FM", frames=256)
    screech_patch.osc_a.wt_position = 0.75
    screech_patch.osc_a.unison_voices = 3  # Fibonacci
    screech_patch.osc_a.unison_detune = 0.25
    screech_patch.osc_a.unison_mode = UnisonMode.SUPER.value
    screech_patch.osc_a.warp_1 = WarpMode.FM_FROM_B.value
    screech_patch.osc_a.warp_1_amount = 0.85
    screech_patch.osc_a.warp_2 = WarpMode.SYNC.value
    screech_patch.osc_a.warp_2_amount = 0.5

    screech_patch.osc_b.enabled = True
    screech_patch.osc_b.osc_type = OscillatorType.WAVETABLE.value
    screech_patch.osc_b.wavetable = WavetableSlot(name="Basic_Shapes", frames=5)
    screech_patch.osc_b.wt_position = 0.0  # Saw
    screech_patch.osc_b.semi = 7           # Perfect 5th up
    screech_patch.osc_b.level = 0.0        # FM carrier only — not heard directly

    screech_patch.filter_1.filter_type = FilterType.BP_24.value
    screech_patch.filter_1.cutoff = phi_filter_cutoff(55.0)[5]  # ~610 Hz
    screech_patch.filter_1.resonance = 0.5
    screech_patch.filter_1.drive = 0.7

    screech_patch.env_2 = EnvelopeConfig(
        attack_ms=0.5,
        decay_ms=0.5 * PHI,  # ~0.81 ms
        sustain=0.382,
        release_ms=0.5 * (PHI ** 2),  # ~1.31 ms
    )

    screech_patch.lfo_1.shape = LFOShape.SAW_DOWN.value
    screech_patch.lfo_1.rate_sync = "1/8"

    screech_patch.mod_matrix = [
        asdict(ModulationRoute(source="LFO 1", destination="Osc A WT Pos", amount=1.0)),
        asdict(ModulationRoute(source="Env 2", destination="Filter 1 Cutoff", amount=0.8)),
        asdict(ModulationRoute(source="LFO 2", destination="Osc A Warp 1", amount=0.618)),
        asdict(ModulationRoute(source="Macro 4", destination="FX Distortion Drive", amount=1.0)),
    ]

    screech_patch.effects = [
        asdict(EffectSlot(
            fx_type=EffectType.DISTORTION.value, mix=0.7,
            param_a=0.8, distortion_mode=DistortionMode.SIN_FOLD.value
        )),
        asdict(EffectSlot(
            fx_type=EffectType.WAVEFOLDER.value, mix=0.5, param_a=0.618
        )),
        asdict(EffectSlot(fx_type=EffectType.OTT.value, mix=0.6, param_a=0.7)),
        asdict(EffectSlot(fx_type=EffectType.EQ.value, mix=1.0)),
    ]

    screech_patch.voicing.mode = VoicingMode.MONO.value
    screech_patch.master_tune = A4_432
    patches.append(asdict(screech_patch))

    # ─── 4. GOLDEN REESE ────────────────────────────────────────────
    reese_patch = Serum2Patch(
        name="DUBFORGE Golden Reese",
        category="Bass",
        tags=["reese", "dubstep", "unison", "detuned", "phi"],
    )
    reese_patch.osc_a.wavetable = WavetableSlot(name="DUBFORGE_PHI_CORE", frames=256)
    reese_patch.osc_a.wt_position = 0.5
    reese_patch.osc_a.unison_voices = 8  # Fibonacci 8
    phi_detune = phi_unison_detune(8)
    reese_patch.osc_a.unison_detune = 0.40
    reese_patch.osc_a.unison_blend = 0.618
    reese_patch.osc_a.unison_mode = UnisonMode.SUPER.value
    reese_patch.osc_a.warp_1 = WarpMode.BEND_PLUS_MINUS.value
    reese_patch.osc_a.warp_1_amount = 0.2

    reese_patch.osc_b.enabled = True
    reese_patch.osc_b.wavetable = WavetableSlot(name="DUBFORGE_PHI_CORE_v2_WOOK", frames=256)
    reese_patch.osc_b.wt_position = 0.382
    reese_patch.osc_b.unison_voices = 8
    reese_patch.osc_b.unison_detune = 0.42
    reese_patch.osc_b.unison_mode = UnisonMode.SUPER.value
    reese_patch.osc_b.fine = 5.0  # slight beating

    reese_patch.filter_1.filter_type = FilterType.MG_LOW_24.value
    reese_patch.filter_1.cutoff = phi_filter_cutoff(55.0)[3]  # ~233 Hz
    reese_patch.filter_1.resonance = 0.2
    reese_patch.filter_1.fat = True

    reese_patch.noise.enabled = True
    reese_patch.noise.sample = "White Noise"
    reese_patch.noise.level = 0.05

    reese_patch.env_2 = phi_envelope(10.0)  # slower filter envelope

    reese_patch.mod_matrix = [
        asdict(ModulationRoute(source="LFO 1", destination="Osc A Fine", amount=0.1)),
        asdict(ModulationRoute(source="LFO 1", destination="Osc B Fine", amount=-0.1)),
        asdict(ModulationRoute(source="Env 2", destination="Filter 1 Cutoff", amount=0.5)),
        asdict(ModulationRoute(source="Macro 1", destination="Osc A WT Pos", amount=1.0)),
        asdict(ModulationRoute(source="Macro 1", destination="Osc B WT Pos", amount=1.0)),
    ]

    reese_patch.lfo_1.rate_sync = "1/2"
    reese_patch.lfo_1.shape = LFOShape.TRIANGLE.value

    reese_patch.effects = [
        asdict(EffectSlot(fx_type=EffectType.CHORUS.value, mix=0.2, param_a=0.618)),
        asdict(EffectSlot(fx_type=EffectType.DISTORTION.value, mix=0.3,
                          distortion_mode=DistortionMode.TUBE.value)),
        asdict(EffectSlot(fx_type=EffectType.EQ.value, mix=1.0)),
        asdict(EffectSlot(fx_type=EffectType.COMPRESSOR.value, mix=0.5)),
    ]

    reese_patch.voicing.mode = VoicingMode.MONO.value
    reese_patch.voicing.portamento_ms = 50.0
    reese_patch.voicing.portamento_mode = "Legato"
    reese_patch.master_tune = A4_432
    patches.append(asdict(reese_patch))

    # ─── 5. SPECTRAL TEAR ───────────────────────────────────────────
    spectral_patch = Serum2Patch(
        name="DUBFORGE Spectral Tear",
        category="Bass",
        tags=["spectral", "experimental", "tear", "dubstep", "serum2"],
    )
    spectral_patch.osc_a.osc_type = OscillatorType.SPECTRAL.value
    spectral_patch.osc_a.level = 0.85
    spectral_patch.osc_a.unison_voices = 3
    spectral_patch.osc_a.unison_detune = 0.15
    spectral_patch.osc_a.warp_1 = WarpMode.FOLD.value
    spectral_patch.osc_a.warp_1_amount = 0.618
    spectral_patch.osc_a.warp_2 = WarpMode.DRIVE.value
    spectral_patch.osc_a.warp_2_amount = 0.382

    spectral_patch.osc_b.enabled = True
    spectral_patch.osc_b.osc_type = OscillatorType.GRANULAR.value
    spectral_patch.osc_b.level = 0.5

    spectral_patch.filter_1.filter_type = FilterType.COMB_PLUS.value
    spectral_patch.filter_1.cutoff = phi_filter_cutoff(55.0)[4]
    spectral_patch.filter_1.resonance = 0.75

    spectral_patch.filter_2.enabled = True
    spectral_patch.filter_2.filter_type = FilterType.HP_24.value
    spectral_patch.filter_2.cutoff = 80.0
    spectral_patch.filter_routing = FilterRouting.SERIAL.value

    spectral_patch.env_2 = phi_envelope(1.0)
    spectral_patch.lfo_1.shape = LFOShape.S_AND_H.value
    spectral_patch.lfo_1.rate_sync = "1/13"

    spectral_patch.mod_matrix = [
        asdict(ModulationRoute(source="LFO 1", destination="Osc A WT Pos", amount=0.618)),
        asdict(ModulationRoute(source="Env 2", destination="Filter 1 Cutoff", amount=0.9)),
        asdict(ModulationRoute(source="LFO 2", destination="Osc A Warp 1", amount=0.5)),
        asdict(ModulationRoute(source="Macro 4", destination="FX Distortion Drive", amount=0.8)),
        asdict(ModulationRoute(source="Velocity", destination="Osc A Level", amount=0.3)),
    ]

    spectral_patch.effects = [
        asdict(EffectSlot(
            fx_type=EffectType.DISTORTION.value, mix=0.618,
            distortion_mode=DistortionMode.XOR.value, param_a=0.7
        )),
        asdict(EffectSlot(fx_type=EffectType.BITCRUSHER.value, mix=0.3, param_a=0.4)),
        asdict(EffectSlot(fx_type=EffectType.OTT.value, mix=0.5)),
        asdict(EffectSlot(fx_type=EffectType.HYPER_DIMENSION.value, mix=0.2)),
        asdict(EffectSlot(fx_type=EffectType.EQ.value, mix=1.0)),
    ]

    spectral_patch.voicing.mode = VoicingMode.MONO.value
    spectral_patch.master_tune = A4_432
    patches.append(asdict(spectral_patch))

    # ─── 6. GRANULAR ATMOSPHERE ─────────────────────────────────────
    gran_patch = Serum2Patch(
        name="DUBFORGE Granular Atmosphere",
        category="Pad",
        tags=["granular", "atmosphere", "pad", "ambient", "phi"],
    )
    gran_patch.osc_a.osc_type = OscillatorType.GRANULAR.value
    gran_patch.osc_a.level = 0.7
    gran_patch.osc_a.unison_voices = 5
    gran_patch.osc_a.unison_detune = 0.3
    gran_patch.osc_a.unison_mode = UnisonMode.SPREAD.value

    gran_patch.osc_b.enabled = True
    gran_patch.osc_b.osc_type = OscillatorType.WAVETABLE.value
    gran_patch.osc_b.wavetable = WavetableSlot(name="DUBFORGE_PHI_CORE", frames=256)
    gran_patch.osc_b.wt_position = 0.618
    gran_patch.osc_b.octave = 1
    gran_patch.osc_b.level = 0.3
    gran_patch.osc_b.unison_voices = 3

    gran_patch.filter_1.filter_type = FilterType.LP_24.value
    gran_patch.filter_1.cutoff = phi_filter_cutoff(55.0)[6]  # ~987 Hz
    gran_patch.filter_1.resonance = 0.15

    gran_patch.env_1 = EnvelopeConfig(
        attack_ms=500.0,                        # slow pad attack
        decay_ms=500.0 * PHI,                   # 809 ms
        sustain=0.8,
        release_ms=500.0 * (PHI ** 2),          # 1309 ms
    )

    gran_patch.lfo_1.shape = LFOShape.SINE.value
    gran_patch.lfo_1.rate_sync = "3/1"  # 3-bar Fibonacci cycle

    gran_patch.mod_matrix = [
        asdict(ModulationRoute(source="LFO 1", destination="Osc A WT Pos", amount=0.5)),
        asdict(ModulationRoute(source="LFO 2", destination="Filter 1 Cutoff", amount=0.3)),
        asdict(ModulationRoute(source="Macro 1", destination="Osc A WT Pos", amount=1.0)),
    ]

    gran_patch.effects = [
        asdict(EffectSlot(fx_type=EffectType.REVERB.value, mix=0.618, param_a=0.7, param_b=0.8)),
        asdict(EffectSlot(fx_type=EffectType.DELAY.value, mix=0.3, param_a=0.382)),
        asdict(EffectSlot(fx_type=EffectType.CHORUS.value, mix=0.25)),
        asdict(EffectSlot(fx_type=EffectType.EQ.value, mix=1.0)),
    ]

    gran_patch.voicing.mode = VoicingMode.POLY.value
    gran_patch.voicing.max_voices = 8
    gran_patch.master_tune = A4_432
    patches.append(asdict(gran_patch))

    # ─── 7. WEAPON (Drop Lead) ──────────────────────────────────────
    weapon_patch = Serum2Patch(
        name="DUBFORGE Weapon",
        category="Lead",
        tags=["weapon", "lead", "dubstep", "heavy", "drop"],
    )
    weapon_patch.osc_a.wavetable = WavetableSlot(name="DUBFORGE_GROWL_FM", frames=256)
    weapon_patch.osc_a.wt_position = 0.0
    weapon_patch.osc_a.unison_voices = 5
    weapon_patch.osc_a.unison_detune = 0.3
    weapon_patch.osc_a.unison_mode = UnisonMode.SUPER.value
    weapon_patch.osc_a.warp_1 = WarpMode.SYNC.value
    weapon_patch.osc_a.warp_1_amount = 0.5
    weapon_patch.osc_a.warp_2 = WarpMode.FM_FROM_B.value
    weapon_patch.osc_a.warp_2_amount = 0.618

    weapon_patch.osc_b.enabled = True
    weapon_patch.osc_b.wavetable = WavetableSlot(name="DUBFORGE_PHI_CORE_v2_WOOK", frames=256)
    weapon_patch.osc_b.wt_position = 0.0
    weapon_patch.osc_b.octave = -1
    weapon_patch.osc_b.level = 0.6

    weapon_patch.osc_a.sub_enabled = True
    weapon_patch.osc_a.sub_shape = "Sine"
    weapon_patch.osc_a.sub_level = 0.7
    weapon_patch.osc_a.sub_octave = -2
    weapon_patch.osc_a.sub_direct_out = True

    weapon_patch.filter_1.filter_type = FilterType.LP_ACID.value
    weapon_patch.filter_1.cutoff = phi_filter_cutoff(55.0)[3]  # ~233 Hz
    weapon_patch.filter_1.resonance = 0.55
    weapon_patch.filter_1.drive = 0.618

    weapon_patch.env_2 = EnvelopeConfig(
        attack_ms=0.1,
        decay_ms=0.1 * PHI * 1000,   # 161.8 ms
        sustain=0.382,
        release_ms=0.1 * (PHI ** 2) * 1000,
    )

    weapon_patch.lfo_1.shape = LFOShape.SAW_DOWN.value
    weapon_patch.lfo_1.rate_sync = "1/8"
    weapon_patch.lfo_2.enabled = True
    weapon_patch.lfo_2.shape = LFOShape.SQUARE.value
    weapon_patch.lfo_2.rate_sync = "1/2"

    weapon_patch.mod_matrix = [
        asdict(ModulationRoute(source="LFO 1", destination="Osc A WT Pos", amount=1.0)),
        asdict(ModulationRoute(source="LFO 1", destination="Osc B WT Pos", amount=0.618)),
        asdict(ModulationRoute(source="Env 2", destination="Filter 1 Cutoff", amount=0.85)),
        asdict(ModulationRoute(source="LFO 2", destination="Osc A Warp 2", amount=0.5)),
        asdict(ModulationRoute(source="Macro 4", destination="FX Distortion Drive", amount=1.0)),
        asdict(ModulationRoute(source="Macro 1", destination="Osc A WT Pos", amount=1.0)),
        asdict(ModulationRoute(source="Macro 2", destination="Osc A Warp 2", amount=0.8)),
    ]

    weapon_patch.effects = _build_dubstep_fx_rack()
    weapon_patch.voicing.mode = VoicingMode.MONO.value
    weapon_patch.voicing.portamento_ms = 8.0
    weapon_patch.master_tune = A4_432
    patches.append(asdict(weapon_patch))

    # ─── 8. PHI PAD ─────────────────────────────────────────────────
    pad_patch = Serum2Patch(
        name="DUBFORGE Phi Pad",
        category="Pad",
        tags=["pad", "ambient", "phi", "lush", "soft"],
    )
    pad_patch.osc_a.wavetable = WavetableSlot(name="DUBFORGE_PHI_CORE", frames=256)
    pad_patch.osc_a.wt_position = 0.618
    pad_patch.osc_a.unison_voices = 8
    pad_patch.osc_a.unison_detune = 0.2
    pad_patch.osc_a.unison_mode = UnisonMode.SPREAD.value
    pad_patch.osc_a.octave = 0
    pad_patch.osc_a.level = 0.6

    pad_patch.osc_b.enabled = True
    pad_patch.osc_b.osc_type = OscillatorType.MULTISAMPLE.value
    pad_patch.osc_b.level = 0.4
    pad_patch.osc_b.octave = 1

    pad_patch.filter_1.filter_type = FilterType.LP_24.value
    pad_patch.filter_1.cutoff = phi_filter_cutoff(55.0)[7]  # ~1597 Hz
    pad_patch.filter_1.resonance = 0.1

    pad_patch.env_1 = EnvelopeConfig(
        attack_ms=800.0,
        decay_ms=800.0 * PHI,
        sustain=0.85,
        release_ms=800.0 * (PHI ** 2),
    )

    pad_patch.lfo_1.shape = LFOShape.SINE.value
    pad_patch.lfo_1.rate_sync = "5/1"  # Fibonacci 5-bar sweep

    pad_patch.mod_matrix = [
        asdict(ModulationRoute(source="LFO 1", destination="Osc A WT Pos", amount=0.382)),
        asdict(ModulationRoute(source="LFO 1", destination="Filter 1 Cutoff", amount=0.2)),
    ]

    pad_patch.effects = [
        asdict(EffectSlot(fx_type=EffectType.CHORUS.value, mix=0.382)),
        asdict(EffectSlot(fx_type=EffectType.REVERB.value, mix=0.618, param_a=0.85, param_b=0.9)),
        asdict(EffectSlot(fx_type=EffectType.DELAY.value, mix=0.2, param_a=0.618)),
        asdict(EffectSlot(fx_type=EffectType.EQ.value, mix=1.0)),
    ]

    pad_patch.voicing.mode = VoicingMode.POLY.value
    pad_patch.voicing.max_voices = 8
    pad_patch.master_tune = A4_432
    patches.append(asdict(pad_patch))

    return patches


# ═══════════════════════════════════════════════════════════════════════════
# SERUM 2 INIT TEMPLATE — DUBFORGE-doctrine starting point
# ═══════════════════════════════════════════════════════════════════════════

def build_init_template() -> dict:
    """
    Build a DUBFORGE-optimized Serum 2 init template.
    Starting point for all new patches — pre-loaded with phi doctrine.
    """
    init = Serum2Patch(name="DUBFORGE Init Template")
    init.osc_a.wavetable = WavetableSlot(name="DUBFORGE_PHI_CORE", frames=256)
    init.osc_a.wt_position = 0.0
    init.osc_a.level = 0.8
    init.osc_b.enabled = False

    init.filter_1.filter_type = FilterType.MG_LOW_24.value
    init.filter_1.cutoff = phi_filter_cutoff(55.0)[5]  # ~610 Hz
    init.filter_1.resonance = 0.0

    init.env_1 = phi_envelope(1.0)
    init.env_2 = phi_envelope(5.0)

    init.lfo_1 = LFOConfig(
        shape=LFOShape.SINE.value,
        mode=LFOMode.SYNC.value,
        rate_sync="1/4",
    )

    # Default macro assignments
    init.macro_1 = MacroConfig(
        label="PHI MORPH",
        targets=[("Osc A WT Pos", 0.0, 1.0)],
    )
    init.macro_2 = MacroConfig(
        label="FM DEPTH",
        targets=[("Osc A Warp 1", 0.0, 1.0)],
    )
    init.macro_3 = MacroConfig(
        label="SUB WEIGHT",
        targets=[("Sub Level", 0.0, 1.0)],
    )
    init.macro_4 = MacroConfig(
        label="GRIT",
        targets=[("FX Distortion Drive", 0.0, 1.0)],
    )

    init.master_tune = A4_432
    init.quality = "2x"

    return asdict(init)


# ═══════════════════════════════════════════════════════════════════════════
# SERUM 2 MODULATION DESTINATIONS REFERENCE
# ═══════════════════════════════════════════════════════════════════════════

MODULATION_DESTINATIONS = {
    "oscillators": [
        "Osc A Level", "Osc A Pan", "Osc A WT Pos", "Osc A Octave",
        "Osc A Semi", "Osc A Fine", "Osc A Phase", "Osc A Unison Detune",
        "Osc A Unison Blend", "Osc A Warp 1", "Osc A Warp 2",
        "Osc B Level", "Osc B Pan", "Osc B WT Pos", "Osc B Octave",
        "Osc B Semi", "Osc B Fine", "Osc B Phase", "Osc B Unison Detune",
        "Osc B Unison Blend", "Osc B Warp 1", "Osc B Warp 2",
        "Sub Level", "Sub Pan",
        "Noise Level", "Noise Pan",
    ],
    "filters": [
        "Filter 1 Cutoff", "Filter 1 Resonance", "Filter 1 Drive",
        "Filter 1 Morph", "Filter 1 Fat",
        "Filter 2 Cutoff", "Filter 2 Resonance", "Filter 2 Drive",
        "Filter 2 Morph",
    ],
    "envelopes": [
        "Env 1 Attack", "Env 1 Decay", "Env 1 Sustain", "Env 1 Release",
        "Env 2 Attack", "Env 2 Decay", "Env 2 Sustain", "Env 2 Release",
        "Env 3 Attack", "Env 3 Decay", "Env 3 Sustain", "Env 3 Release",
    ],
    "lfos": [
        "LFO 1 Rate", "LFO 1 Phase", "LFO 1 Smooth",
        "LFO 2 Rate", "LFO 2 Phase", "LFO 2 Smooth",
        "LFO 3 Rate", "LFO 3 Phase", "LFO 3 Smooth",
        "LFO 4 Rate", "LFO 4 Phase", "LFO 4 Smooth",
    ],
    "effects": [
        "FX Distortion Drive", "FX Distortion Mix",
        "FX Delay Time", "FX Delay Feedback", "FX Delay Mix",
        "FX Reverb Size", "FX Reverb Decay", "FX Reverb Mix",
        "FX Compressor Threshold", "FX Compressor Ratio",
        "FX Filter Cutoff", "FX Filter Resonance",
        "FX Chorus Rate", "FX Chorus Depth", "FX Chorus Mix",
        "FX Phaser Rate", "FX Phaser Depth",
        "FX EQ Low", "FX EQ Mid", "FX EQ High",
        "FX Hyper Amount", "FX Hyper Mix",
        "FX OTT Depth", "FX OTT Mix",
    ],
    "global": [
        "Master Volume", "Master Pan",
        "Voicing Porta Time",
        "Pitch Bend",
    ],
}


# ═══════════════════════════════════════════════════════════════════════════
# MAIN — Generate all Serum 2 engine outputs
# ═══════════════════════════════════════════════════════════════════════════

def main():
    """Generate all Serum 2 engine JSON outputs."""
    out = Path("output/serum2")
    out.mkdir(parents=True, exist_ok=True)

    # 1) Full architecture reference
    arch_path = out / "serum2_architecture.json"
    with open(arch_path, "w") as f:
        json.dump(SERUM2_ARCHITECTURE, f, indent=2)
    print(f"  ✓ Architecture reference → {arch_path}")

    # 2) Wavetable map
    wt_path = out / "serum2_wavetable_map.json"
    with open(wt_path, "w") as f:
        json.dump(WAVETABLE_MAP, f, indent=2)
    print(f"  ✓ Wavetable map          → {wt_path}")

    # 3) Init template
    init_path = out / "serum2_init_template.json"
    init_data = build_init_template()
    with open(init_path, "w") as f:
        json.dump(init_data, f, indent=2)
    print(f"  ✓ Init template          → {init_path}")

    # 4) Dubstep patch collection
    patches_path = out / "serum2_dubstep_patches.json"
    patches = build_dubstep_patches()
    with open(patches_path, "w") as f:
        json.dump(patches, f, indent=2)
    print(f"  ✓ Dubstep patches ({len(patches)})   → {patches_path}")

    # 5) Preset metadata summary
    presets_path = out / "serum2_presets.json"
    preset_summary = {
        "total_patches": len(patches),
        "patches": [
            {
                "name": p["name"],
                "category": p["category"],
                "tags": p["tags"],
                "osc_a_type": p["osc_a"]["osc_type"],
                "osc_b_enabled": p["osc_b"]["enabled"],
                "filter_1_type": p["filter_1"]["filter_type"],
                "fx_count": len(p["effects"]),
                "mod_routes": len(p["mod_matrix"]),
                "unison_voices": p["osc_a"]["unison_voices"],
                "tuning": p["master_tune"],
            }
            for p in patches
        ],
        "phi_integration": {
            "unison_detune": "phi^k * 3.0 cents (symmetric)",
            "envelope_timing": "A:D:R = 1 : phi : phi²",
            "filter_cutoff_ladder": [round(f, 2) for f in phi_filter_cutoff(55.0)],
            "fm_ratio": f"carrier:modulator = 1:{PHI:.4f}",
            "effect_mix": "1/phi ≈ 0.618 wet",
            "macro_curve": "value^(1/phi) golden response",
            "sustain_level": f"1/phi ≈ {1/PHI:.4f}",
            "wt_position_center": "0.618 (golden ratio point)",
            "fibonacci_lfo_rates": fibonacci_lfo_rates(),
            "fibonacci_frame_counts": fibonacci_wavetable_frames(),
        },
        "modulation_destinations": MODULATION_DESTINATIONS,
    }
    with open(presets_path, "w") as f:
        json.dump(preset_summary, f, indent=2)
    print(f"  ✓ Preset summary         → {presets_path}")

    # Summary stats
    total_osc_types = len(OscillatorType)
    total_warp_modes = len(WarpMode)
    total_filter_types = len(FilterType)
    total_fx_types = len(EffectType)
    total_dist_modes = len(DistortionMode)
    total_unison_modes = len(UnisonMode)
    print()
    print(f"  Serum 2 Engine Stats:")
    print(f"    Oscillator types:  {total_osc_types}")
    print(f"    Warp modes:        {total_warp_modes}")
    print(f"    Filter types:      {total_filter_types}")
    print(f"    Effect types:      {total_fx_types}")
    print(f"    Distortion modes:  {total_dist_modes}")
    print(f"    Unison modes:      {total_unison_modes}")
    print(f"    DUBFORGE patches:  {len(patches)}")
    print(f"    Mod destinations:  {sum(len(v) for v in MODULATION_DESTINATIONS.values())}")


if __name__ == "__main__":
    main()
