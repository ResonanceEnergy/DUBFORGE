"""
DUBFORGE Engine — Serum 2 Synthesizer Engine

Comprehensive Serum 2 architecture model: oscillator types, wavetable warps,
filters, modulation matrix, effects rack, macros, unison, arpeggiator,
clip sequencer, and preset generation — all governed by phi/Fibonacci doctrine.

Xfer Records Serum 2 — "Advanced Hybrid Synthesizer"
Version modelled: 2.0.18 (Manual Version 1.0.3, April 27, 2025)

Reference:
    Serum 2 User Guide (Official PDF, v1.0.3)
    Serum 2 What's New (Official PDF, v1.0.0, March 17, 2025)
    https://xferrecords.com/products/serum-2

Outputs:
    output/serum2/serum2_architecture.json
    output/serum2/serum2_presets.json
    output/serum2/serum2_wavetable_map.json
    output/serum2/serum2_init_template.json
    output/serum2/serum2_dubstep_patches.json
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from enum import Enum
from pathlib import Path
from typing import Optional

# ═══════════════════════════════════════════════════════════════════════════
# CONSTANTS — DUBFORGE DOCTRINE
# ═══════════════════════════════════════════════════════════════════════════
from engine.config_loader import A4_432, FIBONACCI, PHI, get_config_value

# Serum wavetable specs
SERUM_FRAME_SIZE = 2048          # samples per frame (internal resolution)
SERUM_MAX_FRAMES = 256           # max wavetable frames
SERUM_SAMPLE_RATE = 48000        # default sample rate
SERUM_BIT_DEPTH = 16             # 16-bit PCM for .wav wavetables
SERUM_CLM_MARKER = b'clm '      # Serum wavetable identification marker

# Serum 2 preset format
SERUM2_PRESET_EXT = '.fxp'       # VST preset format
SERUM2_BANK_EXT = '.fxb'         # VST bank format

# ═══════════════════════════════════════════════════════════════════════════
# OSCILLATOR TYPES — Serum 2: 5 modes per slot (A / B / C)
# ═══════════════════════════════════════════════════════════════════════════


class OscillatorType(Enum):
    """Serum 2 oscillator types — each slot A/B/C can be any of these."""
    WAVETABLE = "wavetable"
    MULTISAMPLE = "multisample"
    SAMPLE = "sample"
    GRANULAR = "granular"
    SPECTRAL = "spectral"


# ═══════════════════════════════════════════════════════════════════════════
# WARP MODES — Complete Serum 2 warp catalogue (dual warp per osc)
# Organised by menu category as shown in the Serum 2 UI.
# ═══════════════════════════════════════════════════════════════════════════


class WarpMode(Enum):
    """
    Serum 2 wavetable warp modes — dual warp slots per oscillator.
    Each oscillator can apply TWO warps simultaneously (Warp 1 + Warp 2).
    Categories: Off, Sync, Alt Warp, Filter, Distortion, FM, PD, AM, RM.
    """
    # ── Off ──────────────────────────────────────────────────────────
    OFF = "Off"

    # ── Sync ─────────────────────────────────────────────────────────
    SYNC = "Sync"                        # WARP Var fader: hard-to-soft sync

    # ── Alt Warp ─────────────────────────────────────────────────────
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
    ODD_EVEN = "Odd/Even"

    # ── Filter (warp-slot filter) ────────────────────────────────────
    WARP_LPF = "LPF"
    WARP_HPF = "HPF"

    # ── Distortion (oscillator-level) ────────────────────────────────
    DIST_TUBE = "Tube"
    DIST_SOFT_CLIP = "Soft Clip"
    DIST_HARD_CLIP = "Hard Clip"
    DIST_DIODE_1 = "Diode 1"
    DIST_DIODE_2 = "Diode 2"
    DIST_LINEAR_FOLD = "Linear Fold"
    DIST_SINE_FOLD = "Sine Fold"
    DIST_ZERO_SQUARE = "Zero-Square"
    DIST_ASYM = "Asym"
    DIST_RECTIFY = "Rectify"
    DIST_SINE_SHAPER = "Sine Shaper"
    DIST_STOMP_BOX = "Stomp Box"
    DIST_TAPE_SAT = "Tape Sat."
    DIST_SOFT_SAT = "Soft Sat."

    # ── FM (Frequency Modulation) ────────────────────────────────────
    # Source variants — each can use sub-modes: Thru-Zero, Exp, Linear
    FM_B = "FM (B)"
    FM_C = "FM (C)"
    FM_NOISE = "FM (Noise)"
    FM_SUB = "FM (Sub)"
    FM_FILTER_1 = "FM (Filter 1)"
    FM_FILTER_2 = "FM (Filter 2)"

    # ── PD (Phase Distortion) ────────────────────────────────────────
    PD_B = "PD (B)"
    PD_C = "PD (C)"
    PD_NOISE = "PD (Noise)"
    PD_SUB = "PD (Sub)"
    PD_FILTER_1 = "PD (Filter 1)"
    PD_FILTER_2 = "PD (Filter 2)"
    PD_SELF = "PD (Self)"

    # ── AM (Amplitude Modulation) ────────────────────────────────────
    AM_B = "AM (B)"
    AM_C = "AM (C)"
    AM_NOISE = "AM (Noise)"
    AM_SUB = "AM (Sub)"
    AM_FILTER_1 = "AM (Filter 1)"
    AM_FILTER_2 = "AM (Filter 2)"

    # ── RM (Ring Modulation) ─────────────────────────────────────────
    RM_B = "RM (B)"
    RM_C = "RM (C)"
    RM_NOISE = "RM (Noise)"
    RM_SUB = "RM (Sub)"
    RM_FILTER_1 = "RM (Filter 1)"
    RM_FILTER_2 = "RM (Filter 2)"


class FMSubMode(Enum):
    """FM warp sub-modes (selectable when an FM warp is active)."""
    THRU_ZERO = "Thru-Zero"
    EXP = "Exp"
    LINEAR = "Linear"


# ═══════════════════════════════════════════════════════════════════════════
# FILTER TYPES — Complete Serum 2 filter catalogue
# 5 categories: Normal, Multi, Flanges, Misc, New (Serum 2)
# ═══════════════════════════════════════════════════════════════════════════


class FilterType(Enum):
    """
    Serum 2 filter types — massively expanded from Serum 1.
    Each filter has: CUTOFF, RES, DRIVE, VAR, PAN, MIX.
    Organised by UI menu category.
    """
    # ── Normal (with slope variants 6/12/18/24 dB) ──────────────────
    MG_LOW_6 = "MG Low 6"
    MG_LOW_12 = "MG Low 12"
    MG_LOW_18 = "MG Low 18"
    MG_LOW_24 = "MG Low 24"
    LOW_6 = "Low 6"
    LOW_12 = "Low 12"
    LOW_18 = "Low 18"
    LOW_24 = "Low 24"
    HIGH_6 = "High 6"
    HIGH_12 = "High 12"
    HIGH_18 = "High 18"
    HIGH_24 = "High 24"
    BAND_12 = "Band 12"
    BAND_24 = "Band 24"
    PEAK_12 = "Peak 12"
    PEAK_24 = "Peak 24"
    NOTCH_12 = "Notch 12"
    NOTCH_24 = "Notch 24"

    # ── Multi (dual SVF combinations) ───────────────────────────────
    MULTI_LH = "LH"
    MULTI_LB = "LB"
    MULTI_LP = "LP"
    MULTI_LN = "LN"
    MULTI_HB = "HB"
    MULTI_HP = "HP"
    MULTI_HN = "HN"
    MULTI_BP = "BP"
    MULTI_BN = "BN"
    MULTI_PP = "PP"
    MULTI_PN = "PN"
    MULTI_NN = "NN"
    MULTI_LBH = "LBH"
    MULTI_LPH = "LPH"
    MULTI_LNH = "LNH"
    MULTI_BPN = "BPN"

    # ── Flanges (Comb / Flanger / Phaser with LP/HP/HL variants) ────
    CMB_L = "Cmb L"
    CMB_H = "Cmb H"
    CMB_HL = "Cmb HL"
    FLG_L = "Flg L"
    FLG_H = "Flg H"
    FLG_HL = "Flg HL"
    PHS_L = "Phs L"
    PHS_H = "Phs H"
    PHS_HL = "Phs HL"

    # ── Misc ─────────────────────────────────────────────────────────
    LOW_EQ_6 = "Low EQ 6"
    LOW_EQ_12 = "Low EQ 12"
    BAND_EQ_6 = "Band EQ 6"
    BAND_EQ_12 = "Band EQ 12"
    HIGH_EQ_6 = "High EQ 6"
    HIGH_EQ_12 = "High EQ 12"
    RING_MOD = "Ring Mod"
    RING_MOD_X2 = "Ring Mod x2"
    SAMPLE_HOLD = "SampHold"
    SAMPLE_HOLD_NEG = "SampHold-"
    COMBS = "Combs"
    ALLPASSES = "Allpasses"
    REVERB = "Reverb"
    FRENCH_LP = "French LP"
    GERMAN_LP = "German LP"
    ADD_BASS = "Add Bass"
    FORMANT_I = "Formant-I"
    FORMANT_II = "Formant-II"
    FORMANT_III = "Formant-III"
    BANDREJECT = "Bandreject"
    DIST_COMB_1_LP = "Dist.Comb 1 LP"
    DIST_COMB_1_BP = "Dist.Comb 1 BP"
    DIST_COMB_2_LP = "Dist.Comb 2 LP"
    DIST_COMB_2_BP = "Dist.Comb 2 BP"
    SCREAM_LP = "Scream LP"
    SCREAM_BP = "Scream BP"

    # ── New (Serum 2) ────────────────────────────────────────────────
    WSP = "Wsp"
    DJ_MIXER = "DJ Mixer"
    DIFFUSOR = "Diffusor"
    MG_LADDER = "MG Ladder"
    ACID_LADDER = "Acid Ladder"
    EMS_LADDER = "EMS Ladder"
    MG_DIRTY = "MG Dirty"
    PZ_SVF = "PZ SVF"
    COMB_2 = "Comb 2"
    EXP_MM = "Exp MM"
    EXP_BPF = "Exp BPF"


class FilterRouting(Enum):
    """Filter routing options for dual-filter configuration."""
    SERIAL = "Serial"              # Filter 1 → Filter 2
    PARALLEL = "Parallel"          # Filter 1 + Filter 2 → Mix

    # Per-oscillator routing targets (set per osc in the mixer)
    FILTER_1 = "Filter 1"
    FILTER_2 = "Filter 2"
    BOTH = "Filter 1 + Filter 2"
    MAIN = "Main"                  # bypass filters (ENV 1 toggle)
    DIRECT = "Direct"              # bypass filters + FX
    NONE = "None"                  # disabled


# ═══════════════════════════════════════════════════════════════════════════
# EFFECTS — 13 FX modules + 3 splitters + Utility
# 3 independent FX racks: MAIN, BUS 1, BUS 2
# ═══════════════════════════════════════════════════════════════════════════


class EffectType(Enum):
    """
    Serum 2 built-in effects — 13 FX modules + 3 splitters + Utility.
    Unlimited instances per rack. 3 racks: MAIN, BUS 1, BUS 2.
    """
    BODE = "Bode"                      # frequency shifter (new in S2)
    CHORUS = "Chorus"
    COMPRESSOR = "Compressor"          # single + multiband modes
    CONVOLVE = "Convolve"              # convolution reverb (new in S2)
    DELAY = "Delay"                    # HQ mode default (new in S2)
    DISTORTION = "Distortion"          # Overdrive mode + DC bias (new in S2)
    EQUALIZER = "Equalizer"            # 2-band parametric
    FILTER = "Filter"                  # same types as synth filters
    FLANGER = "Flanger"
    HYPER_DIMENSION = "Hyper/Dimension"
    PHASER = "Phaser"
    REVERB = "Reverb"                  # 5 types: Plate/Hall/Vintage/Nitrous/Basin
    UTILITY = "Utility"                # polarity, mono bass, width (new in S2)
    # Splitters
    SPLITTER_LH = "Splitter L/H"      # Lows/Highs
    SPLITTER_LMH = "Splitter L/M/H"   # Lows/Mids/Highs
    SPLITTER_MS = "Splitter M/S"       # Mid/Side


class FXRack(Enum):
    """Serum 2 FX rack targets."""
    MAIN = "Main"
    BUS_1 = "Bus 1"
    BUS_2 = "Bus 2"


class DistortionMode(Enum):
    """Distortion FX sub-modes (15 types)."""
    TUBE = "Tube"
    SOFT_CLIP = "Soft Clip"
    HARD_CLIP = "Hard Clip"
    DIODE_1 = "Diode 1"
    DIODE_2 = "Diode 2"
    LINEAR_FOLD = "Linear Fold"
    SINE_FOLD = "Sine Fold"
    ZERO_SQUARE = "Zero-Square"
    ASYM = "Asym"
    RECTIFY = "Rectify"
    SINE_SHAPER = "Sine Shaper"
    DOWNSAMPLE = "Downsample"
    X_SHAPER = "X-Shaper"
    X_SHAPER_ASYM = "X-Shaper (Asym)"
    OVERDRIVE = "Overdrive"            # new in Serum 2


class ReverbType(Enum):
    """Reverb FX sub-types (5 algorithms)."""
    PLATE = "Plate"
    HALL = "Hall"
    VINTAGE = "Vintage"                # new in Serum 2
    NITROUS = "Nitrous"                # new in S2 — 5 sub-modes
    BASIN = "Basin"                    # new in Serum 2


class NitrousMode(Enum):
    """Nitrous reverb sub-modes."""
    SPACE = "Space"
    MARBLE = "Marble"
    RECTANGLE = "Rectangle"
    HEXAGON = "Hexagon"
    BOX = "Box"


class CompressorMode(Enum):
    """Compressor FX modes."""
    SINGLE = "Single"
    MULTIBAND = "Multiband"


class DelayMode(Enum):
    """Delay FX modes."""
    NORMAL = "Normal"
    PING_PONG = "Ping-Pong"
    TAP_DELAY = "Tap->Delay"


# ═══════════════════════════════════════════════════════════════════════════
# UNISON — 5 distribution modes + stack options
# ═══════════════════════════════════════════════════════════════════════════


class UnisonMode(Enum):
    """Serum 2 unison voice distribution modes (1–16 voices per osc)."""
    LINEAR = "Linear"                  # even pitch spacing
    SUPER = "Super"                    # dense/powerful detuning emphasis
    EXP = "Exp"                        # exponential detuning spread
    INV = "Inv"                        # inverted (lower voices more detuned)
    RANDOM = "Random"                  # random detuning per voice


class UnisonStack(Enum):
    """Unison stack transposition options."""
    OFF = "Off"
    OCT_1X = "12 (1x)"
    OCT_2X = "12 (2x)"
    OCT_3X = "12 (3x)"
    FIFTH_1X = "12+7 (1x)"
    FIFTH_2X = "12+7 (2x)"
    FIFTH_3X = "12+7 (3x)"
    CENTER_12 = "Center-12"
    CENTER_24 = "Center-24"


# ═══════════════════════════════════════════════════════════════════════════
# LFO — 10 LFOs, 5 types, 3 modes, 3 directions
# ═══════════════════════════════════════════════════════════════════════════


class LFOType(Enum):
    """LFO oscillator types."""
    NORMAL = "Normal"                  # standard drawable LFO
    PATH = "Path"                      # path-based movement
    CHAOS_LORENZ = "Chaos: Lorenz"     # chaotic attractor (new in S2)
    CHAOS_ROSSLER = "Chaos: Rossler"   # chaotic attractor (new in S2)
    SAMPLE_AND_HOLD = "S&H"            # sample & hold


class LFOShape(Enum):
    """LFO preset shapes (for Normal type)."""
    SINE = "Sine"
    TRIANGLE = "Triangle"
    SAW_UP = "Saw Up"
    SAW_DOWN = "Saw Down"
    SQUARE = "Square"
    CUSTOM = "Custom"                  # user-drawn


class LFOMode(Enum):
    """LFO retrigger modes."""
    FREE = "Free"                      # follows host clock, ignores note timing
    RETRIG = "Retrig"                  # restarts on new note
    ENVELOPE = "Envelope"              # single cycle then stops (loopback optional)


class LFODirection(Enum):
    """LFO playback direction."""
    FORWARD = "Forward"
    REVERSE = "Reverse"
    PING_PONG = "Ping Pong"


# ═══════════════════════════════════════════════════════════════════════════
# VOICING — Mono / Legato / Poly
# ═══════════════════════════════════════════════════════════════════════════


class VoicingMode(Enum):
    """Oscillator voicing modes."""
    POLY = "Poly"
    MONO = "Mono"
    LEGATO = "Legato"


class VoiceStealPriority(Enum):
    """Voice steal priority when polyphony is exhausted."""
    NEWEST = "Newest"
    OLDEST = "Oldest"
    HIGHEST = "Highest"
    LOWEST = "Lowest"
    VELOCITY = "Velocity"


# ═══════════════════════════════════════════════════════════════════════════
# ARPEGGIATOR — 12 slots per bank, 20+ shapes, pattern editor
# ═══════════════════════════════════════════════════════════════════════════


class ArpShape(Enum):
    """Arpeggiator transpose range shapes."""
    UP = "Up"
    DOWN = "Down"
    UP_DOWN = "Up/Down"
    DOWN_UP = "Down/Up"
    UP_PLUS_DOWN = "Up+Down"
    DOWN_PLUS_UP = "Down+Up"
    THUMB_UP = "Thumb Up"
    THUMB_UD = "Thumb UD"
    PINKY_UP = "Pinky Up"
    PINKY_UD = "Pinky UD"
    CONVERGE = "Converge"
    DIVERGE = "Diverge"
    CON_DIVERGE = "Con+Diverge"
    CHORD = "Chord"
    RANDOM = "Random"
    RND_NO_DUP = "Rnd.NoDup"
    RND_DRIFT = "Rnd.Drift"
    RND_ONCE = "Rnd.Once"
    PATTERN = "Pattern"                # custom pattern editor


class ArpPatternMode(Enum):
    """ARP pattern editor playback modes."""
    NORMAL = "Normal"
    REVERSE = "Reverse"
    PENDULUM = "Pendulum"
    RANDOM = "Random"
    RAND_START = "Rand Start"
    RAND_END = "Rand End"
    ONE_SHOT = "One Shot"
    STATIC = "Static"


# ═══════════════════════════════════════════════════════════════════════════
# SUB OSCILLATOR — 6 waveforms
# ═══════════════════════════════════════════════════════════════════════════


class SubOscWaveform(Enum):
    """Sub oscillator waveform types."""
    SINE = "Sine"
    ROUNDED_RECT = "Rounded Rect"
    TRIANGLE = "Triangle"
    SAW = "Saw"
    SQUARE = "Square"
    PULSE = "Pulse"


# ═══════════════════════════════════════════════════════════════════════════
# NOISE OSCILLATOR — colour modes
# ═══════════════════════════════════════════════════════════════════════════


class NoiseColor(Enum):
    """Noise oscillator colour noise modes."""
    WHITE = "White"
    PINK = "Pink"
    BROWN = "Brown"
    GEIGER = "Geiger"


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
    """Configuration for one Serum 2 oscillator slot (A, B, or C)."""
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
    coarse: float = 0.0               # CRS — continuous semitone offset
    # Unison (1–16 voices)
    unison_voices: int = 1
    unison_detune: float = 0.0         # 0.0–1.0
    unison_blend: float = 0.75         # 0.0–1.0 (Serum 2 default 75%)
    unison_mode: str = UnisonMode.SUPER.value
    unison_width: float = 1.0          # stereo spread
    unison_wt_pos: float = 0.0         # WT POS spread per voice
    unison_warp1: float = 0.0          # WARP 1 spread per voice
    unison_warp2: float = 0.0          # WARP 2 spread per voice
    unison_stack: str = UnisonStack.OFF.value
    # Warp modes (Serum 2: dual warp)
    warp_1: str = WarpMode.OFF.value
    warp_1_amount: float = 0.0
    warp_2: str = WarpMode.OFF.value
    warp_2_amount: float = 0.0
    # FM sub-mode (only relevant when warp is FM)
    fm_sub_mode: str = FMSubMode.THRU_ZERO.value
    # Phase
    phase: float = 0.0                 # 0.0–1.0
    random_phase: bool = True
    phase_memory: bool = False         # Serum 2: remember phase across notes
    contiguous_phase: bool = False     # Serum 2: contiguous phase mode
    # Pitch tracking
    pitch_tracking: bool = True
    # Routing target (per-osc)
    routing: str = FilterRouting.FILTER_1.value
    # Bus sends
    bus_1_send: float = 0.0
    bus_2_send: float = 0.0

    def __post_init__(self):
        if self.wavetable is None:
            self.wavetable = WavetableSlot()


@dataclass
class SubOscillator:
    """Serum 2 dedicated sub oscillator."""
    enabled: bool = False
    waveform: str = SubOscWaveform.SINE.value
    level: float = 0.5
    pan: float = 0.5
    octave: int = -1                   # relative to root
    coarse: float = 0.0                # CRS — continuous semitone offset
    phase: float = 0.0
    contiguous_phase: bool = False
    routing: str = FilterRouting.FILTER_1.value
    direct_out: bool = False           # bypass filters


@dataclass
class NoiseOscillator:
    """Serum 2 noise oscillator — samples or colour noise."""
    enabled: bool = False
    sample: str = "White Noise"
    level: float = 0.25
    pan: float = 0.5
    # Colour noise mode (alternative to sample)
    color_mode: Optional[str] = None   # None = use sample; or NoiseColor value
    # Sample controls
    start: float = 0.0                 # START position
    start_rand: float = 0.0            # RAND start randomisation
    pitch: float = 0.0
    fine: float = 0.0
    key_tracking: bool = False
    one_shot: bool = False
    # Routing
    routing: str = FilterRouting.FILTER_1.value
    direct_out: bool = False
    bus_1_send: float = 0.0
    bus_2_send: float = 0.0


@dataclass
class FilterConfig:
    """Configuration for one Serum 2 filter (Filter 1 or Filter 2)."""
    enabled: bool = True
    filter_type: str = FilterType.MG_LOW_24.value
    cutoff: float = 1000.0             # Hz (20–20000)
    resonance: float = 0.0             # 0.0–1.0
    drive: float = 0.0                 # 0.0–1.0
    drive_clean: bool = False          # Serum 2: clean mode for drive
    var: float = 0.0                   # VAR parameter (function depends on type)
    pan: float = 0.5                   # PAN 0.0=L, 0.5=C, 1.0=R
    mix: float = 1.0                   # MIX dry/wet
    fat: bool = False                  # FAT — saturation on resonance (Normal types)
    key_tracking: float = 0.0          # 0.0–1.0
    # Filter output routing
    output_routing: str = "Main"       # Main, Direct, None
    bus_1_send: float = 0.0
    bus_2_send: float = 0.0


@dataclass
class EnvelopeConfig:
    """AHDSR envelope — Serum 2 has 4 envelopes with HOLD segment."""
    attack_ms: float = 1.0             # milliseconds
    hold_ms: float = 0.0               # HOLD — Serum 2: between attack & decay
    decay_ms: float = 200.0
    sustain: float = 0.75              # 0.0–1.0
    release_ms: float = 100.0
    # Curvature
    attack_curve: float = 0.0          # -1.0 (log) to +1.0 (exp)
    decay_curve: float = 0.0
    release_curve: float = 0.0
    # Time mode
    bpm_sync: bool = False             # Serum 2: BPM tempo-sync option
    # Legato
    legato_inverted: bool = False      # Serum 2: force trigger even in legato


@dataclass
class LFOConfig:
    """LFO configuration — Serum 2 has 10 LFOs."""
    enabled: bool = True
    lfo_type: str = LFOType.NORMAL.value
    shape: str = LFOShape.SINE.value   # preset shape (Normal type)
    mode: str = LFOMode.RETRIG.value
    direction: str = LFODirection.FORWARD.value
    rate_hz: float = 1.0               # free-running rate (up to 1000 Hz w/ 10x)
    rate_sync: str = "1/4"             # BPM-synced rate
    bpm_sync: bool = True              # BPM or Hz mode
    phase: float = 0.0                 # start phase 0–360°
    # Mono/Poly
    mono: bool = False                 # default polyphonic
    # HOST sync
    host_sync: bool = False            # sync to global song position
    # Timing options
    triplet: bool = False              # TRIP
    dotted: bool = False               # DOT
    rate_10x: bool = False             # 10x rate multiplier (up to 1000 Hz)
    swing: float = 0.0                 # Serum 2: LFO swing
    # Custom shape data (list of (x, y) if shape == CUSTOM)
    custom_points: list = field(default_factory=list)
    # LFO envelope (rise/delay)
    rise_ms: float = 0.0
    delay_ms: float = 0.0
    smooth: float = 0.0                # output smoothing


@dataclass
class ModulationRoute:
    """
    A single modulation assignment in the 64-slot mod matrix.
    Serum's drag-and-drop system + matrix view.
    """
    source: str = "LFO 1"             # from 49 sources
    destination: str = "Osc A WT Pos"  # any modulatable parameter
    amount: float = 0.0                # -1.0 to +1.0 (bidirectional)
    curve: float = 0.0                 # CRV — source response curve
    polarity_bipolar: bool = True      # POL — bipolar or unipolar
    # Aux source for modulating the modulation depth
    aux_source: Optional[str] = None   # e.g., "Mod Wheel"
    aux_inverted: bool = False         # INV
    aux_curve: float = 0.0             # aux CRV
    # Output
    output_scale: float = 1.0          # OUTPUT — final scaling


@dataclass
class EffectSlot:
    """A single effect in a Serum 2 FX rack."""
    enabled: bool = True
    fx_type: str = EffectType.DISTORTION.value
    rack: str = FXRack.MAIN.value      # which rack (Main, Bus 1, Bus 2)
    mix: float = 0.5                   # dry/wet 0.0–1.0
    level: float = 1.0                 # output level
    # Common parameters (specifics depend on fx_type)
    param_a: float = 0.5              # Primary parameter
    param_b: float = 0.5              # Secondary parameter
    param_c: float = 0.5              # Tertiary parameter
    # Distortion sub-mode
    distortion_mode: Optional[str] = None
    # Reverb sub-type
    reverb_type: Optional[str] = None
    nitrous_mode: Optional[str] = None
    # Compressor mode
    compressor_mode: Optional[str] = None
    # Delay mode
    delay_mode: Optional[str] = None
    delay_hq: bool = True              # Serum 2: HQ mode default


@dataclass
class MacroConfig:
    """
    Serum 2 macro knob — 8 macros available.
    Each macro can control multiple destinations AND be a mod destination.
    """
    label: str = "Macro 1"
    value: float = 0.0                 # 0.0–1.0
    targets: list = field(default_factory=list)  # list of (destination, min, max)


@dataclass
class ArpeggiatorConfig:
    """
    Serum 2 arpeggiator — 12 slots per bank, advanced shapes, pattern editor.
    """
    enabled: bool = False
    shape: str = ArpShape.UP.value
    octave_range: int = 2              # 1–8
    tempo_sync: bool = True
    rate: str = "1/8"                  # note rate
    triplet: bool = False
    dotted: bool = False
    gate: float = 0.5                  # 0.0–1.0
    swing: float = 0.0
    # Transpose
    shift: int = 0                     # semitones
    transpose_range: int = 12          # range in semitones
    # Playback
    offset: int = 0
    repeats: int = 1
    chance: float = 1.0                # note probability
    latch: bool = False
    thru: bool = False
    # Velocity
    velocity_retrig: bool = False
    velocity_decay: float = 0.0
    velocity_target: float = 1.0
    # Retrigger
    retrig_launch: bool = False
    retrig_rate: str = "1/4"
    retrig_note: bool = False
    retrig_first: bool = False
    # Sequencer pattern (when shape == Pattern)
    pattern_mode: str = ArpPatternMode.NORMAL.value
    pattern_steps: list = field(default_factory=list)
    # Slots (12 per bank)
    active_slot: int = 1               # 1–12


@dataclass
class ClipSequencerConfig:
    """Serum 2 CLIP module — 12 clip slots per bank with piano roll editor."""
    enabled: bool = False
    active_slot: int = 1               # 1–12
    key: str = "C"
    scale: str = "Chromatic"
    transpose: int = 0
    record_mode: str = "Overdub"       # Overdub, Extend
    midi_out: bool = False
    clips: list = field(default_factory=list)


@dataclass
class VoicingConfig:
    """Global voicing settings."""
    mode: str = VoicingMode.POLY.value
    max_voices: int = 8
    # Portamento
    portamento_ms: float = 0.0
    portamento_curve: float = 0.0      # convex/concave contour
    portamento_always: bool = False    # even without held note
    portamento_scaled: bool = False    # rate scales with interval distance
    # Voice stealing
    steal_priority: str = VoiceStealPriority.NEWEST.value
    limit_same_note: bool = False      # limit same note poly to 1
    # Pitch bend
    pitch_bend_range: int = 2          # semitones
    # MPE
    mpe_enabled: bool = False
    mpe_pitch_maps_to_x: bool = False
    mpe_y_bidirectional: bool = False
    # Voice control (per-voice randomisation)
    voice_pan_rand: float = 0.0
    voice_detune_rand: float = 0.0     # cents
    voice_cutoff_rand: float = 0.0     # %
    voice_env_rand: float = 0.0        # %


@dataclass
class Serum2Patch:
    """
    Complete Serum 2 patch — the full state of the synthesizer.
    Mirrors the Serum 2 preset structure.
    3 oscillators (A/B/C), sub, noise, 2 filters, 4 envs, 10 LFOs,
    64-slot mod matrix, 3 FX racks, 8 macros, arp, clip sequencer.
    """
    name: str = "DUBFORGE Init"
    author: str = "DUBFORGE"
    category: str = "Bass"
    description: str = ""              # DESC field
    tags: list = field(default_factory=lambda: ["dubstep", "phi", "fractal"])

    # Oscillators — A, B, C (Serum 2: three primary oscillators)
    osc_a: OscillatorConfig = field(default_factory=OscillatorConfig)
    osc_b: OscillatorConfig = field(default_factory=lambda: OscillatorConfig(enabled=False))
    osc_c: OscillatorConfig = field(default_factory=lambda: OscillatorConfig(enabled=False))

    # Sub oscillator (dedicated)
    sub: SubOscillator = field(default_factory=SubOscillator)

    # Noise oscillator
    noise: NoiseOscillator = field(default_factory=NoiseOscillator)

    # Filters
    filter_1: FilterConfig = field(default_factory=FilterConfig)
    filter_2: FilterConfig = field(default_factory=lambda: FilterConfig(enabled=False))
    filter_routing: str = FilterRouting.SERIAL.value

    # Envelopes (4 — ENV 1 = amp, always active)
    env_1: EnvelopeConfig = field(default_factory=EnvelopeConfig)
    env_2: EnvelopeConfig = field(default_factory=lambda: EnvelopeConfig(
        attack_ms=5.0, decay_ms=300.0, sustain=0.3, release_ms=200.0
    ))
    env_3: EnvelopeConfig = field(default_factory=lambda: EnvelopeConfig(
        attack_ms=0.0, decay_ms=100.0, sustain=0.0, release_ms=50.0
    ))
    env_4: EnvelopeConfig = field(default_factory=lambda: EnvelopeConfig(
        attack_ms=0.0, decay_ms=100.0, sustain=0.0, release_ms=50.0
    ))

    # LFOs (10 — LFO 7–10 appear after LFO 6 is assigned)
    lfo_1: LFOConfig = field(default_factory=LFOConfig)
    lfo_2: LFOConfig = field(default_factory=lambda: LFOConfig(enabled=False))
    lfo_3: LFOConfig = field(default_factory=lambda: LFOConfig(enabled=False))
    lfo_4: LFOConfig = field(default_factory=lambda: LFOConfig(enabled=False))
    lfo_5: LFOConfig = field(default_factory=lambda: LFOConfig(enabled=False))
    lfo_6: LFOConfig = field(default_factory=lambda: LFOConfig(enabled=False))
    lfo_7: LFOConfig = field(default_factory=lambda: LFOConfig(enabled=False))
    lfo_8: LFOConfig = field(default_factory=lambda: LFOConfig(enabled=False))
    lfo_9: LFOConfig = field(default_factory=lambda: LFOConfig(enabled=False))
    lfo_10: LFOConfig = field(default_factory=lambda: LFOConfig(enabled=False))

    # Modulation matrix (64 slots max)
    mod_matrix: list = field(default_factory=list)  # list of ModulationRoute

    # Effects — 3 racks (Main, Bus 1, Bus 2)
    effects: list = field(default_factory=list)  # list of EffectSlot

    # Macros (8)
    macro_1: MacroConfig = field(default_factory=lambda: MacroConfig(label="PHI MORPH"))
    macro_2: MacroConfig = field(default_factory=lambda: MacroConfig(label="FM DEPTH"))
    macro_3: MacroConfig = field(default_factory=lambda: MacroConfig(label="SUB WEIGHT"))
    macro_4: MacroConfig = field(default_factory=lambda: MacroConfig(label="GRIT"))
    macro_5: MacroConfig = field(default_factory=lambda: MacroConfig(label="Macro 5"))
    macro_6: MacroConfig = field(default_factory=lambda: MacroConfig(label="Macro 6"))
    macro_7: MacroConfig = field(default_factory=lambda: MacroConfig(label="Macro 7"))
    macro_8: MacroConfig = field(default_factory=lambda: MacroConfig(label="Macro 8"))

    # Arpeggiator
    arp: ArpeggiatorConfig = field(default_factory=ArpeggiatorConfig)

    # Clip sequencer (Serum 2 new)
    clip: ClipSequencerConfig = field(default_factory=ClipSequencerConfig)

    # Voicing
    voicing: VoicingConfig = field(default_factory=VoicingConfig)

    # Global
    master_volume: float = 0.80
    master_tune: float = A4_432        # DUBFORGE default: 432 Hz
    quality: str = "2x"                # Draft (1x), High (2x), Ultra (4x)
    s1_compatibility: bool = False     # Serum 1 compat mode


# ═══════════════════════════════════════════════════════════════════════════
# SERUM 2 ARCHITECTURE DATABASE
# ═══════════════════════════════════════════════════════════════════════════

SERUM2_ARCHITECTURE = {
    "product": "Serum 2",
    "developer": "Xfer Records (Steve Duda)",
    "type": "Advanced Hybrid Synthesizer",
    "version": "2.0.18",
    "manual_version": "1.0.3 (April 27, 2025)",
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
    "oscillators": {
        "primary_count": 3,
        "slots": ["OSC A", "OSC B", "OSC C"],
        "types": [t.value for t in OscillatorType],
        "features": [
            "Smooth Interpolation (near-infinite frame positions)",
            "Dual warp modes (WARP 1 + WARP 2)",
            "FM, PD, AM, RM from any oscillator/filter/sub/noise",
            "Phase Memory and Contiguous phase modes",
            "Copy/paste oscillators with or without modulations",
            "Hover preset navigation with mouse wheel",
        ],
        "warp_categories": {
            "Off": 1,
            "Sync": 1,
            "Alt Warp": 16,
            "Filter": 2,
            "Distortion": 14,
            "FM": 6,
            "PD": 7,
            "AM": 6,
            "RM": 6,
        },
        "total_warp_modes": len(WarpMode),
        "morph_modes": ["Crossfade", "Spectral", "Spectral (HD)"],
        "granular": {
            "max_grains": 256,
            "params": ["SCAN", "DENSITY", "LENGTH", "OFFSET", "DIR",
                        "PITCH", "RAND", "Window Amount"],
        },
        "spectral": {
            "params": ["SCAN", "CUT", "FILTER", "MIX",
                        "High/Low freq markers", "Smooth", "Post Warp"],
        },
        "multisample": {
            "format": "SFZ",
            "features": ["Round-robin", "Velocity layering",
                          "Key-split and crossfade zones"],
        },
        "sample": {
            "features": ["Start/end/loop points", "Crossfade loops",
                          "Auto/manual slicing", "Forward-reverse looping",
                          "Rate control (tape-stop)"],
        },
    },
    "sub_oscillator": {
        "waveforms": [w.value for w in SubOscWaveform],
        "controls": ["OCT", "CRS", "PHASE", "PAN", "LEVEL"],
        "features": ["Contiguous phase", "Routable to Filter 1/2/Direct",
                      "FM/PD/AM/RM source for main oscillators"],
    },
    "noise_oscillator": {
        "color_modes": [c.value for c in NoiseColor],
        "controls": ["START", "RAND", "PITCH", "FINE", "PAN", "LEVEL"],
        "features": ["Stereo sample player", "Color noise modes",
                      "One Shot/Looping", "Key Track", "Embed in preset",
                      "FM/PD/AM/RM source"],
    },
    "filters": {
        "count": 2,
        "total_types": len(FilterType),
        "categories": {
            "Normal": "MG Low/High 6-24, Low/High 6-24, Band/Peak/Notch 12-24",
            "Multi": "LH, LB, LP, LN, HB, HP, HN, BP, BN, PP, PN, NN, LBH, LPH, LNH, BPN",
            "Flanges": "Cmb L/H/HL, Flg L/H/HL, Phs L/H/HL",
            "Misc": "EQ, Ring Mod, SampHold, Combs, Allpasses, Reverb, "
                    "French LP, German LP, Add Bass, Formant I/II/III, "
                    "Bandreject, Dist.Comb, Scream",
            "New (Serum 2)": "Wsp, DJ Mixer, Diffusor, MG Ladder, Acid Ladder, "
                             "EMS Ladder, MG Dirty, PZ SVF, Comb 2, Exp MM, Exp BPF",
        },
        "per_filter_controls": ["CUTOFF", "RES", "DRIVE", "VAR", "PAN", "MIX"],
        "routing_options": [r.value for r in FilterRouting],
        "features": [
            "Drive with Clean mode (new in Serum 2)",
            "FAT mode (analog saturation on resonance)",
            "Key tracking",
            "Per-filter PAN and MIX",
            "Serial / Parallel routing",
            "Per-oscillator routing to Filter 1/2/Both/Main/Direct",
            "Bus 1/Bus 2 send knobs",
        ],
    },
    "modulation": {
        "envelopes": {
            "count": 4,
            "segments": "AHDSR (Attack, Hold, Decay, Sustain, Release)",
            "default_assignment": "ENV 1 → Amp (always active)",
            "features": ["Graphical curve editing", "BPM tempo sync",
                          "Legato Inverted per envelope",
                          "MS or BPM time mode"],
        },
        "lfos": {
            "count": 10,
            "note": "LFO 7–10 appear after LFO 6 is assigned",
            "types": [t.value for t in LFOType],
            "shapes": [s.value for s in LFOShape],
            "modes": [m.value for m in LFOMode],
            "directions": [d.value for d in LFODirection],
            "features": [
                "Custom shape drawing with dedicated editor",
                "BPM sync with note divisions (Trip/Dot)",
                "Envelope mode (single cycle, optional loopback)",
                "Smooth/slew control",
                "Phase offset with snap-to-grid",
                "Rise time + delay",
                "10x rate (up to 1000 Hz)",
                "Swing (new in Serum 2)",
                "Mono/Poly toggle",
                "HOST sync to global song position",
                "Directional playback (Forward/Reverse/Ping Pong)",
                "Chaos modes: Lorenz, Rossler (new in Serum 2)",
                "LFO point modulation via LFO Busses",
            ],
        },
        "matrix": {
            "max_slots": 64,
            "per_slot": ["SOURCE", "CRV", "AMOUNT", "POL", "DESTINATION",
                          "AUX SOURCE", "INV", "CRV (aux)", "OUTPUT"],
            "features": [
                "Drag-and-drop assignment",
                "Custom editable curves on any source",
                "Bypass individual modulations (new in Serum 2)",
                "Reorder modulations via drag-and-drop",
                "Dynamic matrix visualisations",
                "Expanded matrix view",
            ],
            "sources": [
                "ENV 1", "ENV 2", "ENV 3", "ENV 4",
                "LFO 1", "LFO 2", "LFO 3", "LFO 4",
                "LFO 5", "LFO 6", "LFO 7", "LFO 8", "LFO 9", "LFO 10",
                "Velocity", "Note",
                "Macro 1", "Macro 2", "Macro 3", "Macro 4",
                "Macro 5", "Macro 6", "Macro 7", "Macro 8",
                "Mod Wheel", "Aftertouch", "Poly Aftertouch",
                "Pitch Bend",
                "Note-On Alt. 1", "Note-On Alt. 2",
                "Note-On Rand 1", "Note-On Rand 2",
                "Note-On Rand (Discrete)",
                "Active Voices", "Release Velocity",
                "Voice Index", "Voice Mod 1", "Voice Mod 2",
                "Expression", "MPE X", "MPE Y", "MPE Z",
                "OSC A", "OSC B", "OSC C", "SUB", "NOISE",
                "Filter 1", "Filter 2",
                "Fixed",
            ],
            "total_sources": 49,
        },
    },
    "effects_rack": {
        "rack_count": 3,
        "racks": ["Main", "Bus 1", "Bus 2"],
        "instances_per_rack": "unlimited",
        "drag_reorder": True,
        "modules": [e.value for e in EffectType if "Splitter" not in e.value],
        "splitters": [e.value for e in EffectType if "Splitter" in e.value],
        "distortion_modes": [d.value for d in DistortionMode],
        "reverb_types": [r.value for r in ReverbType],
        "nitrous_modes": [n.value for n in NitrousMode],
        "compressor_modes": [c.value for c in CompressorMode],
        "delay_modes": [d.value for d in DelayMode],
        "new_in_serum2": [
            "Bode (frequency shifter)",
            "Convolve (convolution reverb)",
            "Utility (polarity, mono bass, width)",
            "Splitter L/H, L/M/H, M/S",
            "Reverb: Vintage, Nitrous (5 modes), Basin",
            "Delay: HQ mode (now default)",
            "Distortion: Overdrive mode + DC bias control",
        ],
    },
    "macros": {
        "count": 8,
        "description": "Assignable knobs — each can be both source AND destination",
        "features": ["Apply and Delete macro (bake offsets into preset)",
                      "Swappable (drag one onto another)"],
    },
    "unison": {
        "max_voices": 16,
        "modes": [u.value for u in UnisonMode],
        "stack_options": [s.value for s in UnisonStack],
        "params": ["DETUNE", "BLEND", "WIDTH", "RANGE",
                    "WT POS", "WARP 1", "WARP 2"],
    },
    "voicing": {
        "modes": [v.value for v in VoicingMode],
        "steal_priorities": [p.value for p in VoiceStealPriority],
        "features": [
            "Portamento with CURVE, ALWAYS, SCALED options",
            "Voice Control panel (per-voice step sequencer)",
            "Voice Mod 1/2 (usable as mod sources)",
            "Per-voice randomisation: PAN, DETUNE, CUTOFF, ENVS",
            "MPE support (Expression, MPE X/Y/Z)",
        ],
    },
    "arpeggiator": {
        "slots_per_bank": 12,
        "shapes": [a.value for a in ArpShape],
        "pattern_modes": [p.value for p in ArpPatternMode],
        "features": [
            "BPM sync with Trip/Dot",
            "Transpose: SHIFT, RANGE, range shape",
            "Playback: OFFSET, REPEATS, GATE, CHANCE, LATCH, THRU",
            "Retrigger: LAUNCH, RATE, NOTE, FIRST",
            "Velocity: RETRIG, DECAY, TARGET",
            "Pattern editor (advanced, when shape = Pattern)",
            "MIDI Out",
        ],
    },
    "clip_sequencer": {
        "slots_per_bank": 12,
        "features": [
            "Full piano roll MIDI clip editor",
            "Record: Overdub or Extend mode",
            "Automation lanes",
            "Key/Scale quantisation",
            "MIDI Out",
        ],
    },
    "wavetable_editor": {
        "features": [
            "Up to 256 frames, 2048 samples per frame",
            "12 drawing tools",
            "FFT additive editor",
            "Morph: Crossfade, Spectral, Spectral (Zero All Phases)",
            "Formula Parser for math-generated waveforms",
            "Import audio (.wav) with multiple detection modes",
            "Drag-and-drop from Finder/Explorer/DAW",
        ],
    },
    "preset_format": {
        "extension": ".fxp",
        "bank_extension": ".fxb",
        "serum1_compatibility": "S1 presets load in S2 (S1 Compat Mode auto-enabled)",
        "metadata": ["ARTIST", "DESC"],
        "wavetable_embedded": True,
        "samples_embeddable": True,
        "organisation": "Category / Tags / Ratings / Favorites / Folders / Packs",
    },
    "global": {
        "quality_modes": ["Draft (1x)", "High (2x)", "Ultra (4x)"],
        "tuning": {
            "default": "A4=440 Hz",
            "dubforge_default": "A4=432 Hz",
            "tun_file": True,
            "mts_esp": True,
        },
        "features": [
            "Comprehensive undo/redo",
            "S1 Compatibility Mode",
            "Disable Smoothing (sample-accurate automation)",
            "Use Ultra quality when rendering",
        ],
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
    Generate an AHDSR envelope with phi-ratio timing.
    Attack : Decay : Release = 1 : phi : phi²
    Hold = 0 (instant transition).
    Sustain set to 1/phi ≈ 0.618.
    """
    return EnvelopeConfig(
        attack_ms=base_attack_ms,
        hold_ms=0.0,
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
    Result: value^(1/phi) — emphasises the 0.618 sweet spot.
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
    Fibonacci numbers up to Serum's 256 max.
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
        )),
        asdict(ModulationRoute(
            source="Macro 2",
            destination="Osc B WT Pos",
            amount=PHI - 1,  # 0.618
        )),
        asdict(ModulationRoute(
            source="ENV 2",
            destination="Filter 1 Cutoff",
            amount=0.75,
        )),
        asdict(ModulationRoute(
            source="LFO 1",
            destination="Osc A WT Pos",
            amount=0.382,  # 1 - 1/phi
            aux_source="Macro 1",
        )),
        asdict(ModulationRoute(
            source="LFO 2",
            destination="Filter 1 Cutoff",
            amount=0.25,
            aux_source="Mod Wheel",
        )),
        asdict(ModulationRoute(
            source="Velocity",
            destination="Filter 1 Cutoff",
            amount=0.3,
        )),
        asdict(ModulationRoute(
            source="Note",
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
            distortion_mode=DistortionMode.LINEAR_FOLD.value,
        )),
        asdict(EffectSlot(
            fx_type=EffectType.COMPRESSOR.value,
            mix=phi_effect_mix(0.5),
            param_a=0.618,            # threshold
            param_b=0.5,              # ratio
            compressor_mode=CompressorMode.MULTIBAND.value,
        )),
        asdict(EffectSlot(
            fx_type=EffectType.EQUALIZER.value,
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
            compressor_mode=CompressorMode.SINGLE.value,
        )),
        asdict(EffectSlot(
            fx_type=EffectType.REVERB.value,
            mix=phi_effect_mix(0.15),
            param_a=0.3,              # size
            param_b=0.618,            # decay
            param_c=0.5,              # damping
            reverb_type=ReverbType.PLATE.value,
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
    sub_patch.sub.enabled = True
    sub_patch.sub.waveform = SubOscWaveform.SINE.value
    sub_patch.sub.level = 0.8
    sub_patch.sub.octave = -1
    sub_patch.osc_b.enabled = False
    sub_patch.osc_c.enabled = False
    sub_patch.filter_1.filter_type = FilterType.LOW_24.value
    sub_patch.filter_1.cutoff = phi_filter_cutoff(55.0)[2]  # ~144 Hz
    sub_patch.filter_1.resonance = 0.1
    sub_patch.env_1 = phi_envelope(1.0)
    sub_patch.env_2 = phi_envelope(3.0)
    sub_patch.voicing.mode = VoicingMode.MONO.value
    sub_patch.voicing.portamento_ms = 30.0
    sub_patch.voicing.portamento_always = False
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
    growl_patch.osc_a.warp_1 = WarpMode.FM_B.value
    growl_patch.osc_a.warp_1_amount = 0.618
    growl_patch.osc_a.warp_2 = WarpMode.DIST_LINEAR_FOLD.value
    growl_patch.osc_a.warp_2_amount = 0.382

    growl_patch.osc_b.enabled = True
    growl_patch.osc_b.wavetable = WavetableSlot(name="DUBFORGE_PHI_CORE_v2_WOOK", frames=256)
    growl_patch.osc_b.wt_position = 0.618
    growl_patch.osc_b.semi = 0
    growl_patch.osc_b.fine = 0.0

    growl_patch.filter_1.filter_type = FilterType.ACID_LADDER.value
    growl_patch.filter_1.cutoff = phi_filter_cutoff(55.0)[4]  # ~377 Hz
    growl_patch.filter_1.resonance = 0.618
    growl_patch.filter_1.drive = 0.5

    growl_patch.filter_2.enabled = True
    growl_patch.filter_2.filter_type = FilterType.FORMANT_I.value
    growl_patch.filter_2.cutoff = phi_filter_cutoff(55.0)[5]  # ~610 Hz
    growl_patch.filter_routing = FilterRouting.SERIAL.value

    growl_patch.env_2 = phi_envelope(2.0)
    growl_patch.lfo_1.shape = LFOShape.CUSTOM.value
    growl_patch.lfo_1.rate_sync = "1/8"
    growl_patch.lfo_1.mode = LFOMode.RETRIG.value

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
    screech_patch.osc_a.warp_1 = WarpMode.FM_B.value
    screech_patch.osc_a.warp_1_amount = 0.85
    screech_patch.osc_a.warp_2 = WarpMode.SYNC.value
    screech_patch.osc_a.warp_2_amount = 0.5

    screech_patch.osc_b.enabled = True
    screech_patch.osc_b.osc_type = OscillatorType.WAVETABLE.value
    screech_patch.osc_b.wavetable = WavetableSlot(name="Basic_Shapes", frames=5)
    screech_patch.osc_b.wt_position = 0.0  # Saw
    screech_patch.osc_b.semi = 7           # Perfect 5th up
    screech_patch.osc_b.level = 0.0        # FM carrier only — not heard directly

    screech_patch.filter_1.filter_type = FilterType.BAND_24.value
    screech_patch.filter_1.cutoff = phi_filter_cutoff(55.0)[5]  # ~610 Hz
    screech_patch.filter_1.resonance = 0.5
    screech_patch.filter_1.drive = 0.7

    screech_patch.env_2 = EnvelopeConfig(
        attack_ms=0.5,
        decay_ms=0.5 * PHI,
        sustain=0.382,
        release_ms=0.5 * (PHI ** 2),
    )

    screech_patch.lfo_1.shape = LFOShape.SAW_DOWN.value
    screech_patch.lfo_1.rate_sync = "1/8"

    screech_patch.mod_matrix = [
        asdict(ModulationRoute(source="LFO 1", destination="Osc A WT Pos", amount=1.0)),
        asdict(ModulationRoute(source="ENV 2", destination="Filter 1 Cutoff", amount=0.8)),
        asdict(ModulationRoute(source="LFO 2", destination="Osc A Warp 1", amount=0.618)),
        asdict(ModulationRoute(source="Macro 4", destination="FX Distortion Drive", amount=1.0)),
    ]

    screech_patch.effects = [
        asdict(EffectSlot(
            fx_type=EffectType.DISTORTION.value, mix=0.7,
            param_a=0.8, distortion_mode=DistortionMode.SINE_FOLD.value
        )),
        asdict(EffectSlot(
            fx_type=EffectType.DISTORTION.value, mix=0.5,
            param_a=0.618, distortion_mode=DistortionMode.X_SHAPER.value
        )),
        asdict(EffectSlot(
            fx_type=EffectType.COMPRESSOR.value, mix=0.6,
            param_a=0.7, compressor_mode=CompressorMode.MULTIBAND.value
        )),
        asdict(EffectSlot(fx_type=EffectType.EQUALIZER.value, mix=1.0)),
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
    reese_patch.osc_a.unison_detune = phi_detune
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
        asdict(ModulationRoute(source="ENV 2", destination="Filter 1 Cutoff", amount=0.5)),
        asdict(ModulationRoute(source="Macro 1", destination="Osc A WT Pos", amount=1.0)),
        asdict(ModulationRoute(source="Macro 1", destination="Osc B WT Pos", amount=1.0)),
    ]

    reese_patch.lfo_1.rate_sync = "1/2"
    reese_patch.lfo_1.shape = LFOShape.TRIANGLE.value

    reese_patch.effects = [
        asdict(EffectSlot(fx_type=EffectType.CHORUS.value, mix=0.2, param_a=0.618)),
        asdict(EffectSlot(fx_type=EffectType.DISTORTION.value, mix=0.3,
                          distortion_mode=DistortionMode.TUBE.value)),
        asdict(EffectSlot(fx_type=EffectType.EQUALIZER.value, mix=1.0)),
        asdict(EffectSlot(fx_type=EffectType.COMPRESSOR.value, mix=0.5,
                          compressor_mode=CompressorMode.SINGLE.value)),
    ]

    reese_patch.voicing.mode = VoicingMode.MONO.value
    reese_patch.voicing.portamento_ms = 50.0
    reese_patch.voicing.portamento_always = False
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
    spectral_patch.osc_a.warp_1 = WarpMode.DIST_LINEAR_FOLD.value
    spectral_patch.osc_a.warp_1_amount = 0.618
    spectral_patch.osc_a.warp_2 = WarpMode.DIST_TUBE.value
    spectral_patch.osc_a.warp_2_amount = 0.382

    spectral_patch.osc_b.enabled = True
    spectral_patch.osc_b.osc_type = OscillatorType.GRANULAR.value
    spectral_patch.osc_b.level = 0.5

    spectral_patch.filter_1.filter_type = FilterType.CMB_L.value
    spectral_patch.filter_1.cutoff = phi_filter_cutoff(55.0)[4]
    spectral_patch.filter_1.resonance = 0.75

    spectral_patch.filter_2.enabled = True
    spectral_patch.filter_2.filter_type = FilterType.HIGH_24.value
    spectral_patch.filter_2.cutoff = 80.0
    spectral_patch.filter_routing = FilterRouting.SERIAL.value

    spectral_patch.env_2 = phi_envelope(1.0)
    spectral_patch.lfo_1.lfo_type = LFOType.SAMPLE_AND_HOLD.value
    spectral_patch.lfo_1.rate_sync = "1/13"

    spectral_patch.mod_matrix = [
        asdict(ModulationRoute(source="LFO 1", destination="Osc A WT Pos", amount=0.618)),
        asdict(ModulationRoute(source="ENV 2", destination="Filter 1 Cutoff", amount=0.9)),
        asdict(ModulationRoute(source="LFO 2", destination="Osc A Warp 1", amount=0.5)),
        asdict(ModulationRoute(source="Macro 4", destination="FX Distortion Drive", amount=0.8)),
        asdict(ModulationRoute(source="Velocity", destination="Osc A Level", amount=0.3)),
    ]

    spectral_patch.effects = [
        asdict(EffectSlot(
            fx_type=EffectType.DISTORTION.value, mix=0.618,
            distortion_mode=DistortionMode.X_SHAPER.value, param_a=0.7
        )),
        asdict(EffectSlot(
            fx_type=EffectType.DISTORTION.value, mix=0.3,
            distortion_mode=DistortionMode.DOWNSAMPLE.value, param_a=0.4
        )),
        asdict(EffectSlot(
            fx_type=EffectType.COMPRESSOR.value, mix=0.5,
            compressor_mode=CompressorMode.MULTIBAND.value
        )),
        asdict(EffectSlot(fx_type=EffectType.HYPER_DIMENSION.value, mix=0.2)),
        asdict(EffectSlot(fx_type=EffectType.EQUALIZER.value, mix=1.0)),
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
    gran_patch.osc_a.unison_mode = UnisonMode.RANDOM.value

    gran_patch.osc_b.enabled = True
    gran_patch.osc_b.osc_type = OscillatorType.WAVETABLE.value
    gran_patch.osc_b.wavetable = WavetableSlot(name="DUBFORGE_PHI_CORE", frames=256)
    gran_patch.osc_b.wt_position = 0.618
    gran_patch.osc_b.octave = 1
    gran_patch.osc_b.level = 0.3
    gran_patch.osc_b.unison_voices = 3

    gran_patch.filter_1.filter_type = FilterType.LOW_24.value
    gran_patch.filter_1.cutoff = phi_filter_cutoff(55.0)[6]  # ~987 Hz
    gran_patch.filter_1.resonance = 0.15

    gran_patch.env_1 = EnvelopeConfig(
        attack_ms=500.0,
        decay_ms=500.0 * PHI,
        sustain=0.8,
        release_ms=500.0 * (PHI ** 2),
    )

    gran_patch.lfo_1.shape = LFOShape.SINE.value
    gran_patch.lfo_1.rate_sync = "3/1"  # 3-bar Fibonacci cycle

    gran_patch.mod_matrix = [
        asdict(ModulationRoute(source="LFO 1", destination="Osc A WT Pos", amount=0.5)),
        asdict(ModulationRoute(source="LFO 2", destination="Filter 1 Cutoff", amount=0.3)),
        asdict(ModulationRoute(source="Macro 1", destination="Osc A WT Pos", amount=1.0)),
    ]

    gran_patch.effects = [
        asdict(EffectSlot(
            fx_type=EffectType.REVERB.value, mix=0.618,
            param_a=0.7, param_b=0.8,
            reverb_type=ReverbType.HALL.value
        )),
        asdict(EffectSlot(fx_type=EffectType.DELAY.value, mix=0.3, param_a=0.382,
                          delay_mode=DelayMode.PING_PONG.value)),
        asdict(EffectSlot(fx_type=EffectType.CHORUS.value, mix=0.25)),
        asdict(EffectSlot(fx_type=EffectType.EQUALIZER.value, mix=1.0)),
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
    weapon_patch.osc_a.warp_2 = WarpMode.FM_B.value
    weapon_patch.osc_a.warp_2_amount = 0.618

    weapon_patch.osc_b.enabled = True
    weapon_patch.osc_b.wavetable = WavetableSlot(name="DUBFORGE_PHI_CORE_v2_WOOK", frames=256)
    weapon_patch.osc_b.wt_position = 0.0
    weapon_patch.osc_b.octave = -1
    weapon_patch.osc_b.level = 0.6

    # Use OSC C as a sub-bass layer (Serum 2 three-osc power)
    weapon_patch.osc_c.enabled = True
    weapon_patch.osc_c.wavetable = WavetableSlot(name="Basic_Shapes", frames=5)
    weapon_patch.osc_c.wt_position = 0.0  # Sine
    weapon_patch.osc_c.octave = -2
    weapon_patch.osc_c.level = 0.5
    weapon_patch.osc_c.unison_voices = 1

    weapon_patch.sub.enabled = True
    weapon_patch.sub.waveform = SubOscWaveform.SINE.value
    weapon_patch.sub.level = 0.7
    weapon_patch.sub.octave = -2
    weapon_patch.sub.direct_out = True

    weapon_patch.filter_1.filter_type = FilterType.ACID_LADDER.value
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
        asdict(ModulationRoute(source="ENV 2", destination="Filter 1 Cutoff", amount=0.85)),
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
    pad_patch.osc_a.unison_mode = UnisonMode.LINEAR.value
    pad_patch.osc_a.octave = 0
    pad_patch.osc_a.level = 0.6

    pad_patch.osc_b.enabled = True
    pad_patch.osc_b.osc_type = OscillatorType.MULTISAMPLE.value
    pad_patch.osc_b.level = 0.4
    pad_patch.osc_b.octave = 1

    pad_patch.filter_1.filter_type = FilterType.LOW_24.value
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
        asdict(EffectSlot(
            fx_type=EffectType.REVERB.value, mix=0.618,
            param_a=0.85, param_b=0.9,
            reverb_type=ReverbType.VINTAGE.value
        )),
        asdict(EffectSlot(fx_type=EffectType.DELAY.value, mix=0.2, param_a=0.618,
                          delay_mode=DelayMode.PING_PONG.value)),
        asdict(EffectSlot(fx_type=EffectType.EQUALIZER.value, mix=1.0)),
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
    Build a DUBFORGE-optimised Serum 2 init template.
    Starting point for all new patches — pre-loaded with phi doctrine.
    """
    init = Serum2Patch(name="DUBFORGE Init Template")
    init.osc_a.wavetable = WavetableSlot(name="DUBFORGE_PHI_CORE", frames=256)
    init.osc_a.wt_position = 0.0
    init.osc_a.level = 0.8
    init.osc_b.enabled = False
    init.osc_c.enabled = False

    init.filter_1.filter_type = FilterType.MG_LOW_24.value
    init.filter_1.cutoff = phi_filter_cutoff(55.0)[5]  # ~610 Hz
    init.filter_1.resonance = 0.0

    init.env_1 = phi_envelope(1.0)
    init.env_2 = phi_envelope(5.0)

    init.lfo_1 = LFOConfig(
        shape=LFOShape.SINE.value,
        mode=LFOMode.RETRIG.value,
        rate_sync="1/4",
    )

    # Default macro assignments (8 macros)
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
    init.macro_5 = MacroConfig(label="FILTER ENV")
    init.macro_6 = MacroConfig(label="SPACE")
    init.macro_7 = MacroConfig(label="MOVEMENT")
    init.macro_8 = MacroConfig(label="CHAOS")

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
        "Osc C Level", "Osc C Pan", "Osc C WT Pos", "Osc C Octave",
        "Osc C Semi", "Osc C Fine", "Osc C Phase", "Osc C Unison Detune",
        "Osc C Unison Blend", "Osc C Warp 1", "Osc C Warp 2",
        "Sub Level", "Sub Pan",
        "Noise Level", "Noise Pan", "Noise Pitch",
    ],
    "filters": [
        "Filter 1 Cutoff", "Filter 1 Resonance", "Filter 1 Drive",
        "Filter 1 Var", "Filter 1 Pan", "Filter 1 Mix",
        "Filter 2 Cutoff", "Filter 2 Resonance", "Filter 2 Drive",
        "Filter 2 Var", "Filter 2 Pan", "Filter 2 Mix",
    ],
    "envelopes": [
        "ENV 1 Attack", "ENV 1 Hold", "ENV 1 Decay",
        "ENV 1 Sustain", "ENV 1 Release",
        "ENV 2 Attack", "ENV 2 Hold", "ENV 2 Decay",
        "ENV 2 Sustain", "ENV 2 Release",
        "ENV 3 Attack", "ENV 3 Hold", "ENV 3 Decay",
        "ENV 3 Sustain", "ENV 3 Release",
        "ENV 4 Attack", "ENV 4 Hold", "ENV 4 Decay",
        "ENV 4 Sustain", "ENV 4 Release",
    ],
    "lfos": [
        "LFO 1 Rate", "LFO 1 Phase", "LFO 1 Smooth",
        "LFO 2 Rate", "LFO 2 Phase", "LFO 2 Smooth",
        "LFO 3 Rate", "LFO 3 Phase", "LFO 3 Smooth",
        "LFO 4 Rate", "LFO 4 Phase", "LFO 4 Smooth",
        "LFO 5 Rate", "LFO 5 Phase", "LFO 5 Smooth",
        "LFO 6 Rate", "LFO 6 Phase", "LFO 6 Smooth",
        "LFO 7 Rate", "LFO 7 Phase", "LFO 7 Smooth",
        "LFO 8 Rate", "LFO 8 Phase", "LFO 8 Smooth",
        "LFO 9 Rate", "LFO 9 Phase", "LFO 9 Smooth",
        "LFO 10 Rate", "LFO 10 Phase", "LFO 10 Smooth",
    ],
    "effects": [
        "FX Distortion Drive", "FX Distortion Mix",
        "FX Delay Time", "FX Delay Feedback", "FX Delay Mix",
        "FX Reverb Size", "FX Reverb Decay", "FX Reverb Mix",
        "FX Compressor Threshold", "FX Compressor Ratio",
        "FX Filter Cutoff", "FX Filter Resonance",
        "FX Chorus Rate", "FX Chorus Depth", "FX Chorus Mix",
        "FX Flanger Rate", "FX Flanger Depth", "FX Flanger Mix",
        "FX Phaser Rate", "FX Phaser Depth", "FX Phaser Mix",
        "FX EQ Low", "FX EQ High",
        "FX Hyper Amount", "FX Hyper Mix",
        "FX Bode Shift", "FX Bode Mix",
        "FX Convolve Size", "FX Convolve Mix",
        "FX Utility Width", "FX Utility Pan",
    ],
    "macros": [
        "Macro 1", "Macro 2", "Macro 3", "Macro 4",
        "Macro 5", "Macro 6", "Macro 7", "Macro 8",
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

def main() -> None:
    """Generate all Serum 2 engine JSON outputs."""
    out = Path("output/serum2")
    out.mkdir(parents=True, exist_ok=True)

    # Load module-pack config for reference tuning
    tuning_ref = float(get_config_value(
        "serum2_module_pack_v1", "tuning_ref", default=432))

    # 1) Full architecture reference
    arch_path = out / "serum2_architecture.json"
    arch_out = dict(SERUM2_ARCHITECTURE)
    arch_out["tuning_ref_hz"] = tuning_ref
    with open(arch_path, "w") as f:
        json.dump(arch_out, f, indent=2)
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
                "osc_c_enabled": p["osc_c"]["enabled"],
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
    total_reverb_types = len(ReverbType)
    total_lfo_types = len(LFOType)
    print()
    print("  Serum 2 Engine Stats:")
    print(f"    Oscillator types:  {total_osc_types}")
    print(f"    Warp modes:        {total_warp_modes}")
    print(f"    Filter types:      {total_filter_types}")
    print(f"    Effect types:      {total_fx_types}")
    print(f"    Distortion modes:  {total_dist_modes}")
    print(f"    Reverb types:      {total_reverb_types}")
    print(f"    LFO types:         {total_lfo_types}")
    print(f"    Unison modes:      {total_unison_modes}")
    print(f"    DUBFORGE patches:  {len(patches)}")
    print(f"    Mod destinations:  {sum(len(v) for v in MODULATION_DESTINATIONS.values())}")


if __name__ == "__main__":
    main()
