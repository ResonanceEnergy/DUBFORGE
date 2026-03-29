"""
DUBFORGE Engine — Serum 2 Blueprint Generator

Generates Serum 2 preset blueprints from analyzed stem features:
  - Oscillator warp mode selection (Asymmetric, FM, Sync, Bend, PWM)
  - WT Pos modulation routing (1/8 stepped + Chaos)
  - Path Mode LFO (X = WT Pos, Y = Filter + Distortion)
  - Lorenz vs Rössler chaos attractor recommendation
  - Meta-modulation (Envelope → LFO Rate/Depth)
  - FX chain suggestions (per stem)
  - Wavetable export (multi-frame, golden zone pitch shift)
  - Modulation matrix (JSON routing spec)

Uses the existing engine.serum2 architecture for enums and data models.

Outputs:
    output/serum_blueprints/<track>_<stem>_blueprint.json
    output/serum_blueprints/wavetables/<stem>_wt.wav
    output/serum_blueprints/fx_suggestions.json
"""

from __future__ import annotations

import json
import math
import struct
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Optional

from engine.config_loader import FIBONACCI, PHI, get_config_value
from engine.log import get_logger
from engine.turboquant import SpectralVectorIndex, TurboQuantConfig

_log = get_logger("dubforge.serum_blueprint")

# Import Serum 2 enums from existing module
from engine.serum2 import (
    SERUM_FRAME_SIZE,
    SERUM_MAX_FRAMES,
    SERUM_SAMPLE_RATE,
    EffectType,
    LFOMode,
    LFOType,
    WarpMode,
)

# ═══════════════════════════════════════════════════════════════════════════
# OPTIONAL IMPORTS
# ═══════════════════════════════════════════════════════════════════════════

try:
    import numpy as np
    HAS_NUMPY = True
except ImportError:
    np = None  # type: ignore[assignment]
    HAS_NUMPY = False

try:
    import soundfile as sf
    HAS_SOUNDFILE = True
except ImportError:
    sf = None  # type: ignore[assignment]
    HAS_SOUNDFILE = False


# ═══════════════════════════════════════════════════════════════════════════
# CONSTANTS
# ═══════════════════════════════════════════════════════════════════════════

GOLDEN_BASS_LOW_HZ = 40.0
GOLDEN_BASS_HIGH_HZ = 110.0
GOLDEN_ZONE_ROOT_NOTE = "F1"  # F1 ≈ 43.65 Hz — center of golden zone

# Lorenz attractor params (σ=10, ρ=28, β=8/3 — canonical)
LORENZ_SIGMA = 10.0
LORENZ_RHO = 28.0
LORENZ_BETA = 8.0 / 3.0

# Rössler attractor params (a=0.2, b=0.2, c=5.7 — canonical)
ROSSLER_A = 0.2
ROSSLER_B = 0.2
ROSSLER_C = 5.7


# ═══════════════════════════════════════════════════════════════════════════
# DATA MODELS
# ═══════════════════════════════════════════════════════════════════════════

@dataclass
class ModRoute:
    """A single modulation matrix entry."""
    source: str          # e.g. "LFO 1", "Env 2", "Macro 1", "Chaos: Lorenz"
    target: str          # e.g. "Osc A WT Pos", "Filter 1 Cutoff"
    amount: float = 0.5  # -1.0 to 1.0
    bipolar: bool = True
    aux_source: Optional[str] = None   # meta-modulation source
    aux_amount: float = 0.0
    notes: str = ""      # human-readable explanation


@dataclass
class WarpConfig:
    """Oscillator warp configuration."""
    warp_1: str = WarpMode.OFF.value
    warp_1_amount: float = 0.5
    warp_2: str = WarpMode.OFF.value
    warp_2_amount: float = 0.5
    notes: str = ""


@dataclass
class OscConfig:
    """Oscillator slot configuration."""
    slot: str = "A"                    # A, B, or C
    enabled: bool = True
    wt_pos: float = 0.0               # 0.0-1.0
    octave: int = 0
    semi: int = 0
    fine: float = 0.0
    unison_voices: int = 1
    unison_detune: float = 0.0
    warp: WarpConfig = field(default_factory=WarpConfig)
    notes: str = ""


@dataclass
class LFOBlueprint:
    """LFO configuration blueprint."""
    slot: int = 1                       # LFO 1-10
    lfo_type: str = LFOType.NORMAL.value
    shape: str = "Sine"
    rate_sync: str = "1/4"
    bpm_sync: bool = True
    mode: str = LFOMode.RETRIG.value
    notes: str = ""


@dataclass
class FXSlot:
    """Effect chain slot."""
    fx_type: str = ""
    mix: float = 0.5
    params: dict = field(default_factory=dict)
    notes: str = ""


@dataclass
class ChaosRecommendation:
    """Lorenz vs Rössler recommendation with reasoning."""
    attractor: str = "Lorenz"           # "Lorenz" or "Rossler"
    confidence: float = 0.5             # 0-1
    reasoning: str = ""
    lfo_slot: int = 3                   # which LFO slot to assign
    targets: list[str] = field(default_factory=list)
    rate_sync: str = "1/2"
    sonic_character: str = ""


@dataclass
class SerumBlueprint:
    """Complete Serum 2 preset blueprint for a stem."""
    stem_type: str = ""
    track_name: str = ""
    patch_name: str = ""

    # Oscillators
    osc_a: OscConfig = field(default_factory=lambda: OscConfig(slot="A"))
    osc_b: OscConfig = field(default_factory=lambda: OscConfig(slot="B"))

    # LFOs
    lfos: list[LFOBlueprint] = field(default_factory=list)

    # Chaos
    chaos: ChaosRecommendation = field(default_factory=ChaosRecommendation)

    # Modulation matrix
    mod_matrix: list[ModRoute] = field(default_factory=list)

    # FX chain
    fx_chain: list[FXSlot] = field(default_factory=list)

    # Macros
    macros: dict[str, str] = field(default_factory=dict)  # {macro_label: target}

    # Wavetable export path (if generated)
    wavetable_path: Optional[str] = None

    # Notes
    notes: str = ""
    dojo_tips: list[str] = field(default_factory=list)

    def to_feature_vector(self) -> list[float]:
        """Flatten blueprint parameters into a feature vector for TQ indexing."""
        vec: list[float] = []
        for osc in (self.osc_a, self.osc_b):
            vec.extend([
                osc.wt_pos, float(osc.octave), float(osc.semi),
                osc.fine, float(osc.unison_voices), osc.unison_detune,
                osc.warp.warp_1_amount, osc.warp.warp_2_amount,
            ])
        if self.chaos:
            vec.extend([self.chaos.confidence, float(self.chaos.lfo_slot)])
        for lfo in self.lfos:
            vec.append(float(lfo.slot))
        for fx in self.fx_chain:
            vec.append(fx.mix)
        return vec

    def to_dict(self) -> dict:
        return {
            "stem_type": self.stem_type,
            "track_name": self.track_name,
            "patch_name": self.patch_name,
            "osc_a": asdict(self.osc_a),
            "osc_b": asdict(self.osc_b),
            "lfos": [asdict(l) for l in self.lfos],
            "chaos": asdict(self.chaos),
            "mod_matrix": [asdict(m) for m in self.mod_matrix],
            "fx_chain": [asdict(f) for f in self.fx_chain],
            "macros": self.macros,
            "wavetable_path": self.wavetable_path,
            "notes": self.notes,
            "dojo_tips": self.dojo_tips,
        }


# ═══════════════════════════════════════════════════════════════════════════
# CHAOS ATTRACTOR RECOMMENDATION ENGINE
# ═══════════════════════════════════════════════════════════════════════════

def recommend_chaos_attractor(resample_chaos_score: float,
                               transient_sharpness: float,
                               wobble_rate_hz: float,
                               mod_depth: float,
                               stem_type: str) -> ChaosRecommendation:
    """
    Recommend Lorenz vs Rössler chaos attractor based on stem features.

    LORENZ — "The Aggressive One"
        - Three-variable system: x(t), y(t), z(t)
        - Famous butterfly attractor — wide, erratic trajectories
        - Sonic character: Wild, aggressive, unpredictable modulation
        - Best for: Heavy basses, chaotic drops, Mudpies-style resampling
        - Triggers: High chaos score, high transient sharpness

    RÖSSLER — "The Musical One"
        - Three-variable system with gentler orbits
        - Near-periodic with occasional burst departures
        - Sonic character: Musical, breathing, organic modulation
        - Best for: Atmospheric pads, evolving textures, subtle movement
        - Triggers: Lower chaos, smoother mod depth, atmospheric stems
    """

    # Decision scoring
    lorenz_points = 0.0
    rossler_points = 0.0
    reasons = []

    # --- Chaos score ---
    if resample_chaos_score > 0.5:
        lorenz_points += 2.0
        reasons.append(f"High chaos ({resample_chaos_score:.2f}) → Lorenz's erratic "
                       f"trajectories match the complex spectrum")
    else:
        rossler_points += 1.5
        reasons.append(f"Moderate chaos ({resample_chaos_score:.2f}) → Rössler's "
                       f"near-periodic orbits feel more musical")

    # --- Transient sharpness ---
    if transient_sharpness > 0.6:
        lorenz_points += 1.5
        reasons.append(f"Sharp transients ({transient_sharpness:.2f}) → Lorenz "
                       f"creates complementary unpredictable accents")
    else:
        rossler_points += 1.0
        reasons.append(f"Soft transients ({transient_sharpness:.2f}) → Rössler's "
                       f"smooth orbits preserve dynamics")

    # --- Wobble rate ---
    if wobble_rate_hz > 4.0:
        lorenz_points += 1.0
        reasons.append(f"Fast wobble ({wobble_rate_hz:.1f} Hz) → Lorenz at audio "
                       f"rate creates FM-like timbres")
    elif wobble_rate_hz > 1.0:
        rossler_points += 1.0
        reasons.append(f"Medium wobble ({wobble_rate_hz:.1f} Hz) → Rössler adds "
                       f"organic breathing to the wobble")

    # --- Mod depth ---
    if mod_depth > 0.5:
        lorenz_points += 0.5
        reasons.append(f"Deep modulation ({mod_depth:.2f}) → Lorenz for maximum chaos")
    else:
        rossler_points += 0.5
        reasons.append(f"Subtle modulation ({mod_depth:.2f}) → Rössler for gentle movement")

    # --- Stem type bias ---
    stem_bias = {
        "sub": ("rossler", 1.0, "Sub bass needs controlled movement"),
        "bass": ("lorenz", 0.5, "Mid-bass benefits from Lorenz aggression"),
        "drums": ("lorenz", 0.5, "Drums + Lorenz = chaotic fills and ghost notes"),
        "mids_growls": ("lorenz", 1.5, "Growls ARE chaos — Lorenz is home"),
        "atmos_fx": ("rossler", 1.5, "Atmosphere needs Rössler's breathing quality"),
    }

    if stem_type in stem_bias:
        attractor, points, reason = stem_bias[stem_type]
        if attractor == "lorenz":
            lorenz_points += points
        else:
            rossler_points += points
        reasons.append(f"Stem type '{stem_type}': {reason}")

    # --- Decision ---
    total = lorenz_points + rossler_points
    if total < 0.01:
        total = 1.0

    if lorenz_points >= rossler_points:
        chosen = "Lorenz"
        confidence = lorenz_points / total
        sonic = ("Wild, erratic modulation — butterfly attractor creates "
                 "unpredictable spectral movement, FM-like timbral shifts, "
                 "and aggressive motion. Routes well to WT Pos + Filter + Distortion.")
    else:
        chosen = "Rossler"
        confidence = rossler_points / total
        sonic = ("Musical, breathing modulation — near-periodic orbits create "
                 "organic evolution with occasional surprise departures. "
                 "Routes well to WT Pos + Pitch Fine + Reverb Send.")

    # Targets based on choice
    if chosen == "Lorenz":
        targets = ["Osc A WT Pos", "Filter 1 Cutoff", "Distortion Drive"]
        rate_sync = "1/4" if wobble_rate_hz > 2 else "1/2"
    else:
        targets = ["Osc A WT Pos", "Osc B Pitch Fine", "Reverb Mix"]
        rate_sync = "1/2" if wobble_rate_hz > 2 else "1 bar"

    return ChaosRecommendation(
        attractor=chosen,
        confidence=confidence,
        reasoning=" | ".join(reasons),
        lfo_slot=3,  # Default to LFO 3 for chaos
        targets=targets,
        rate_sync=rate_sync,
        sonic_character=sonic,
    )


# ═══════════════════════════════════════════════════════════════════════════
# WARP MODE SELECTION — based on stem characteristics
# ═══════════════════════════════════════════════════════════════════════════

def _select_warp_mode(stem_type: str,
                      resample_chaos: float,
                      wobble_rate: float,
                      mod_depth: float) -> WarpConfig:
    """
    Select optimal Serum 2 warp modes based on stem characteristics.

    Prioritizes modes that match the analysis findings.
    """
    warp = WarpConfig()

    if stem_type == "sub":
        # Sub: minimal warp — keep it clean
        warp.warp_1 = WarpMode.ASYM_PLUS.value
        warp.warp_1_amount = 0.15
        warp.warp_2 = WarpMode.OFF.value
        warp.notes = "Sub: Light Asym+ for harmonic warmth, keep clean"

    elif stem_type == "bass":
        # Bass: Asymmetric + FM for dubstep growl
        if resample_chaos > 0.4:
            warp.warp_1 = WarpMode.FM_B.value if hasattr(WarpMode, 'FM_B') else "FM (B)"
            warp.warp_1_amount = 0.5 + resample_chaos * 0.3
            warp.warp_2 = WarpMode.ASYM_PLUS_MINUS.value
            warp.warp_2_amount = mod_depth * 0.6
            warp.notes = "Bass: FM for metallic harmonics + Asym for character"
        else:
            warp.warp_1 = WarpMode.SYNC.value
            warp.warp_1_amount = 0.4
            warp.warp_2 = WarpMode.ASYM_PLUS.value
            warp.warp_2_amount = 0.3
            warp.notes = "Bass: Sync for classic dubstep buzz + Asym warmth"

    elif stem_type == "drums":
        warp.warp_1 = WarpMode.PWM.value
        warp.warp_1_amount = 0.3
        warp.warp_2 = WarpMode.DIST_HARD_CLIP.value
        warp.warp_2_amount = 0.4
        warp.notes = "Drums: PWM for punch + Hard Clip for transient saturation"

    elif stem_type == "mids_growls":
        # Growls: Maximum chaos
        warp.warp_1 = WarpMode.FM_B.value if hasattr(WarpMode, 'FM_B') else "FM (B)"
        warp.warp_1_amount = 0.6 + resample_chaos * 0.3
        warp.warp_2 = WarpMode.BEND_PLUS_MINUS.value
        warp.warp_2_amount = wobble_rate / 8.0  # scale with wobble rate
        warp.notes = "Growls: FM for metallic screech + Bend for movement"

    elif stem_type == "atmos_fx":
        warp.warp_1 = WarpMode.MIRROR.value
        warp.warp_1_amount = 0.4
        warp.warp_2 = WarpMode.WARP_LPF.value
        warp.warp_2_amount = 0.6
        warp.notes = "Atmos: Mirror for ethereal quality + LPF for warmth"

    else:
        warp.warp_1 = WarpMode.SYNC.value
        warp.warp_1_amount = 0.4
        warp.notes = "Default: Sync warp"

    return warp


# ═══════════════════════════════════════════════════════════════════════════
# FX CHAIN GENERATION — per-stem
# ═══════════════════════════════════════════════════════════════════════════

def generate_serum_fx_chain(stem_type: str,
                            resample_chaos: float = 0.0,
                            transient_sharpness: float = 0.0,
                            mod_depth: float = 0.0) -> list[FXSlot]:
    """
    Generate a Serum 2 FX chain recommendation based on stem analysis.
    """
    chain: list[FXSlot] = []

    if stem_type == "sub":
        chain.append(FXSlot(
            fx_type="Distortion",
            mix=0.2,
            params={"mode": "Tube", "drive": 0.3},
            notes="Gentle tube saturation for sub harmonics",
        ))
        chain.append(FXSlot(
            fx_type="EQ",
            mix=1.0,
            params={"hp_freq": 20, "lp_freq": 120, "bell_freq": 60, "bell_gain": 2.0},
            notes="Tight sub EQ — kill everything above 120 Hz",
        ))

    elif stem_type == "bass":
        chain.append(FXSlot(
            fx_type="Distortion",
            mix=0.4 + resample_chaos * 0.3,
            params={"mode": "Hard Clip" if resample_chaos > 0.5 else "Soft Clip",
                    "drive": 0.5 + resample_chaos * 0.3},
            notes="Distortion scaled to chaos level",
        ))
        chain.append(FXSlot(
            fx_type="Compressor",
            mix=0.8,
            params={"threshold": -12, "ratio": 4, "attack_ms": 5, "release_ms": 50},
            notes="Compress after distortion for consistency",
        ))
        chain.append(FXSlot(
            fx_type="EQ",
            mix=1.0,
            params={"hp_freq": 30, "notch_freq": 250, "notch_q": 2},
            notes="Clean low end, notch mud frequencies",
        ))

    elif stem_type == "drums":
        chain.append(FXSlot(
            fx_type="Compressor",
            mix=0.9,
            params={"threshold": -8, "ratio": 6, "attack_ms": 1, "release_ms": 30},
            notes="Fast attack compressor for transient control",
        ))
        chain.append(FXSlot(
            fx_type="Distortion",
            mix=0.15,
            params={"mode": "Tape Sat.", "drive": 0.25},
            notes="Tape saturation for analog warmth",
        ))

    elif stem_type == "mids_growls":
        chain.append(FXSlot(
            fx_type="Distortion",
            mix=0.6,
            params={"mode": "Sine Fold" if resample_chaos > 0.4 else "Diode 1",
                    "drive": min(0.8, 0.4 + resample_chaos * 0.5)},
            notes="Heavy distortion for growl character",
        ))
        chain.append(FXSlot(
            fx_type="Filter",
            mix=1.0,
            params={"type": "BP", "cutoff": 800, "resonance": 0.4},
            notes="Bandpass to focus growl energy",
        ))
        chain.append(FXSlot(
            fx_type="Delay",
            mix=0.15,
            params={"time_sync": "1/16", "feedback": 0.2, "filter_hp": 200},
            notes="Short slapback for width",
        ))

    elif stem_type == "atmos_fx":
        chain.append(FXSlot(
            fx_type="Reverb",
            mix=0.5,
            params={"size": 0.8, "decay": 3.0, "damping": 0.4, "pre_delay_ms": 20},
            notes="Large reverb for spatial depth",
        ))
        chain.append(FXSlot(
            fx_type="Delay",
            mix=0.3,
            params={"time_sync": "1/4 dot", "feedback": 0.35, "filter_lp": 5000},
            notes="Dotted-quarter ping-pong for stereo width",
        ))
        chain.append(FXSlot(
            fx_type="Chorus",
            mix=0.25,
            params={"rate": 0.3, "depth": 0.5},
            notes="Chorus for thickness",
        ))

    return chain


# ═══════════════════════════════════════════════════════════════════════════
# BLUEPRINT GENERATION — complete Serum 2 preset blueprint from features
# ═══════════════════════════════════════════════════════════════════════════

def generate_serum_blueprint(stem_type: str,
                             track_name: str = "",
                             resample_chaos_score: float = 0.0,
                             transient_sharpness: float = 0.0,
                             wobble_rate_hz: float = 0.0,
                             mod_depth: float = 0.0,
                             golden_zone_match: float = 0.0,
                             volume_mod_fidelity: float = 0.0,
                             bpm: float = 140.0) -> SerumBlueprint:
    """
    Generate a complete Serum 2 preset blueprint from analyzed stem features.

    This is the main entry point — takes feature values from
    dubstep_taste_analyzer.StemFeatures and produces a full patch design.
    """
    safe_stem = stem_type.replace("/", "_")
    patch_name = f"DF_{safe_stem}_{track_name[:16]}".replace(" ", "_")

    bp = SerumBlueprint(
        stem_type=stem_type,
        track_name=track_name,
        patch_name=patch_name,
    )

    # --- Oscillator A: Main sound ---
    bp.osc_a = OscConfig(
        slot="A",
        enabled=True,
        wt_pos=golden_zone_match * 0.5,  # start position from analysis
        octave=0 if stem_type != "sub" else -1,
        unison_voices=1 if stem_type == "sub" else min(7, int(3 + mod_depth * 4)),
        unison_detune=0.0 if stem_type == "sub" else mod_depth * 30,
        warp=_select_warp_mode(stem_type, resample_chaos_score,
                               wobble_rate_hz, mod_depth),
        notes=f"Main oscillator for {stem_type}",
    )

    # --- Oscillator B: Layer / FM carrier ---
    bp.osc_b = OscConfig(
        slot="B",
        enabled=stem_type in ("bass", "mids_growls"),
        wt_pos=0.25,
        octave=1 if stem_type == "mids_growls" else 0,
        semi=7 if stem_type == "mids_growls" else 0,  # fifth interval for growls
        unison_voices=1,
        warp=WarpConfig(
            warp_1=WarpMode.SYNC.value if stem_type == "bass" else WarpMode.OFF.value,
            warp_1_amount=0.3,
        ),
        notes="Layer oscillator" if stem_type == "bass" else "FM carrier for growl",
    )

    # --- LFO 1: Main modulation (WT Pos) ---
    bp.lfos.append(LFOBlueprint(
        slot=1,
        lfo_type=LFOType.NORMAL.value,
        shape="Custom" if mod_depth > 0.3 else "Sine",
        rate_sync="1/8" if wobble_rate_hz > 2 else "1/4",
        bpm_sync=True,
        mode=LFOMode.RETRIG.value,
        notes="Main WT Pos modulation — ill.Gates: start with volume, add filter later",
    ))

    # --- LFO 2: Volume modulation (80/20 rule) ---
    bp.lfos.append(LFOBlueprint(
        slot=2,
        lfo_type=LFOType.NORMAL.value,
        shape="Saw Down",
        rate_sync="1/4",
        bpm_sync=True,
        mode=LFOMode.RETRIG.value,
        notes="Volume pump — Dojo 80/20: volume mod > filter sweep",
    ))

    # --- LFO 3: Chaos attractor ---
    chaos = recommend_chaos_attractor(
        resample_chaos_score, transient_sharpness,
        wobble_rate_hz, mod_depth, stem_type,
    )
    bp.chaos = chaos

    chaos_type = (LFOType.CHAOS_LORENZ.value if chaos.attractor == "Lorenz"
                  else LFOType.CHAOS_ROSSLER.value)
    bp.lfos.append(LFOBlueprint(
        slot=3,
        lfo_type=chaos_type,
        shape="",  # N/A for chaos
        rate_sync=chaos.rate_sync,
        bpm_sync=True,
        mode=LFOMode.FREE.value,
        notes=f"Chaos: {chaos.attractor} — {chaos.sonic_character[:80]}",
    ))

    # --- LFO 4: Path Mode (if applicable) ---
    if stem_type in ("bass", "mids_growls"):
        bp.lfos.append(LFOBlueprint(
            slot=4,
            lfo_type=LFOType.PATH.value,
            shape="",
            rate_sync="1/2",
            bpm_sync=True,
            mode=LFOMode.RETRIG.value,
            notes="Path Mode: X = WT Pos, Y = Filter Cutoff + Distortion Drive",
        ))

    # --- Modulation Matrix ---
    # Route 1: LFO 1 → WT Pos (main movement)
    bp.mod_matrix.append(ModRoute(
        source="LFO 1", target="Osc A WT Pos",
        amount=0.5 + mod_depth * 0.3,
        notes="Wavetable position sweep — the core of the sound",
    ))

    # Route 2: LFO 2 → Volume (80/20)
    vol_amount = volume_mod_fidelity * 0.6
    bp.mod_matrix.append(ModRoute(
        source="LFO 2", target="Master Volume",
        amount=max(0.2, vol_amount),
        bipolar=False,
        notes="Volume modulation — Dojo 80/20 rule",
    ))

    # Route 3: Chaos → targets
    for target in chaos.targets:
        bp.mod_matrix.append(ModRoute(
            source=f"LFO 3 ({chaos.attractor})", target=target,
            amount=0.3 + resample_chaos_score * 0.3,
            notes=f"Chaos modulation → {target}",
        ))

    # Route 4: Meta-modulation — Env 2 → LFO 1 Rate
    if mod_depth > 0.3:
        bp.mod_matrix.append(ModRoute(
            source="Env 2", target="LFO 1 Rate",
            amount=0.3,
            notes="Meta-mod: Envelope speeds up LFO over note duration — accelerating wobble",
        ))

    # Route 5: Macro 1 → Warp 1 amount (performance control)
    bp.mod_matrix.append(ModRoute(
        source="Macro 1", target="Osc A Warp 1",
        amount=0.8,
        bipolar=False,
        notes="Macro 1: Performer controls warp intensity",
    ))

    # Path Mode routing (if enabled)
    if stem_type in ("bass", "mids_growls"):
        bp.mod_matrix.append(ModRoute(
            source="LFO 4 (Path X)", target="Osc A WT Pos",
            amount=0.4,
            notes="Path X axis → WT Pos for 2D movement",
        ))
        bp.mod_matrix.append(ModRoute(
            source="LFO 4 (Path Y)", target="Filter 1 Cutoff",
            amount=0.5,
            notes="Path Y axis → Filter for timbral sweep",
        ))

    # --- FX Chain ---
    bp.fx_chain = generate_serum_fx_chain(
        stem_type, resample_chaos_score, transient_sharpness, mod_depth,
    )

    # --- Macros ---
    bp.macros = {
        "Macro 1": "WARP — Controls Osc A Warp 1 amount",
        "Macro 2": "WOBBLE — Controls LFO 1 depth",
        "Macro 3": "FILTER — Controls Filter 1 Cutoff",
        "Macro 4": "DIRT — Controls Distortion Drive",
        "Macro 5": "SPACE — Controls Reverb Mix",
        "Macro 6": "WIDTH — Controls Unison Detune",
        "Macro 7": "ATTACK — Controls Env 1 Attack",
        "Macro 8": "CHAOS — Controls LFO 3 (Chaos) Rate",
    }

    # --- Dojo Tips ---
    bp.dojo_tips = _generate_dojo_tips(stem_type, resample_chaos_score,
                                        volume_mod_fidelity)

    _log.info(f"Blueprint generated: {patch_name} ({chaos.attractor} chaos)")

    return bp


def _generate_dojo_tips(stem_type: str,
                        chaos_score: float,
                        vol_mod_fidelity: float) -> list[str]:
    """Generate Producer Dojo / ill.Gates workflow tips."""
    tips = [
        "ill.Gates 80/20: Start with VOLUME modulation, add filter later",
        f"Chaos score: {chaos_score:.2f} — {'resample this into a Mudpies chain' if chaos_score > 0.5 else 'use as-is or light processing'}",
    ]

    if vol_mod_fidelity < 0.5:
        tips.append("⚠ Volume mod fidelity is low — try routing LFO to volume "
                     "instead of filter cutoff for more impact")

    if stem_type in ("bass", "mids_growls"):
        tips.append("128s Technique: Bounce this to audio → chop into 128 slices → "
                     "map to Simpler rack → play chromatically")
        tips.append("Mudpies: Resample → process → resample → process → repeat 3x "
                     "for maximum texture")

    if stem_type == "sub":
        tips.append("Golden Zone: Keep fundamental in 40-110 Hz — mono below 80 Hz")
        tips.append("Hard clip ceiling: -3 dBFS — ill.Gates' headroom standard")

    if stem_type == "atmos_fx":
        tips.append("Checkerboarding: Alternate atmos fills with silences "
                     "for rhythmic negative space")

    return tips


# ═══════════════════════════════════════════════════════════════════════════
# WAVETABLE EXPORT — multi-frame for Serum import
# ═══════════════════════════════════════════════════════════════════════════

def export_stem_as_wavetable(audio_path: str,
                              output_path: str,
                              n_frames: int = 64,
                              golden_zone_shift: bool = True) -> str:
    """
    Export an audio stem as a Serum-ready wavetable .wav.

    - Splits audio into n_frames equal segments of 2048 samples each.
    - Optionally pitch-shifts to golden zone root note for harmonic wavetables.
    - Writes with Serum's CLM marker for auto-detection.

    Args:
        audio_path: Input audio file path
        output_path: Output .wav file path
        n_frames: Number of wavetable frames (1-256)
        golden_zone_shift: Shift pitch to golden zone root

    Returns:
        Path to the exported wavetable.
    """
    if not HAS_NUMPY or not HAS_SOUNDFILE:
        raise ImportError("Wavetable export requires numpy and soundfile")

    import soundfile as sf

    # Load audio
    y, sr = sf.read(audio_path, dtype='float32')
    if y.ndim > 1:
        y = y.mean(axis=1)  # mono

    n_frames = min(n_frames, SERUM_MAX_FRAMES)
    total_samples = n_frames * SERUM_FRAME_SIZE

    # Resample / pad to exact size
    if len(y) >= total_samples:
        y = y[:total_samples]
    else:
        # Loop / pad
        repeats = (total_samples // len(y)) + 1
        y = np.tile(y, repeats)[:total_samples]

    # Optional: pitch shift to golden zone
    if golden_zone_shift and HAS_NUMPY:
        try:
            import librosa
            # Detect fundamental frequency
            f0_frames = librosa.yin(
                y, fmin=20, fmax=2000,
                sr=sr if sr else SERUM_SAMPLE_RATE,
            )
            f0_median = float(np.median(f0_frames[f0_frames > 0])) if np.any(f0_frames > 0) else 0
            target_f0 = 43.65  # F1 — center of golden zone

            if 20 < f0_median < 2000 and abs(f0_median - target_f0) > 5:
                shift_semitones = 12 * np.log2(target_f0 / f0_median)
                y = librosa.effects.pitch_shift(
                    y, sr=sr or SERUM_SAMPLE_RATE,
                    n_steps=float(shift_semitones),
                )
                _log.info(f"Pitch shifted from {f0_median:.1f} Hz → "
                          f"{target_f0:.1f} Hz ({shift_semitones:+.1f} st)")
        except Exception as e:
            _log.warning(f"Golden zone pitch shift failed: {e}")

    # Normalize
    peak = np.max(np.abs(y))
    if peak > 0:
        y = y / peak * 0.95  # Leave slight headroom

    # Reshape into frames
    y = y[:n_frames * SERUM_FRAME_SIZE]

    # Write WAV with Serum CLM marker
    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    sf.write(output_path, y, sr or SERUM_SAMPLE_RATE, subtype='PCM_16')

    # Append CLM marker (Serum auto-detects wavetable format)
    _append_clm_marker(output_path, SERUM_FRAME_SIZE)

    _log.info(f"Exported wavetable: {output_path} ({n_frames} frames)")
    return output_path


def _append_clm_marker(wav_path: str, frame_size: int) -> None:
    """
    Append Serum's CLM wavetable marker to a WAV file.

    Serum looks for 'clm ' chunk with frame size info to auto-detect
    wavetable format on import.
    """
    marker = b'clm \x00\x00\x00\x00'  # basic marker
    # Encode frame size as text hint (Serum parses this)
    marker_text = f"<!>{frame_size} Serum Wavetable\x00"
    marker_data = marker_text.encode('ascii')

    with open(wav_path, 'ab') as f:
        f.write(marker_data)


# ═══════════════════════════════════════════════════════════════════════════
# BATCH PROCESSING — generate blueprints from full analysis
# ═══════════════════════════════════════════════════════════════════════════

def generate_blueprints_from_analysis(
    stems: dict,  # dict[str, StemFeatures] from taste analyzer
    track_name: str = "",
    bpm: float = 140.0,
) -> dict[str, SerumBlueprint]:
    """
    Generate Serum 2 blueprints for all analyzed stems.

    Args:
        stems: Dict of stem_type → StemFeatures from dubstep_taste_analyzer
        track_name: Track name for patch naming
        bpm: Track BPM

    Returns:
        Dict of stem_type → SerumBlueprint
    """
    blueprints = {}
    for stem_type, feats in stems.items():
        bp = generate_serum_blueprint(
            stem_type=stem_type,
            track_name=track_name,
            resample_chaos_score=feats.resample_chaos_score,
            transient_sharpness=feats.transient_sharpness,
            wobble_rate_hz=feats.wobble_rate_hz,
            mod_depth=feats.mod_depth,
            golden_zone_match=feats.golden_zone_match,
            volume_mod_fidelity=feats.volume_mod_fidelity,
            bpm=feats.bpm if feats.bpm > 0 else bpm,
        )
        blueprints[stem_type] = bp
    return blueprints


# ═══════════════════════════════════════════════════════════════════════════
# EXPORT
# ═══════════════════════════════════════════════════════════════════════════

OUTPUT_DIR = Path(__file__).parent.parent / "output" / "serum_blueprints"


def export_blueprint(blueprint: SerumBlueprint,
                     output_dir: Optional[Path] = None) -> Path:
    """Export a single blueprint to JSON."""
    out = output_dir or OUTPUT_DIR
    out.mkdir(parents=True, exist_ok=True)

    filename = f"{blueprint.patch_name}_blueprint.json"
    filepath = out / filename
    filepath.write_text(json.dumps(blueprint.to_dict(), indent=2), encoding="utf-8")
    _log.info(f"Exported blueprint: {filepath}")
    return filepath


def export_all_blueprints(blueprints: dict[str, SerumBlueprint],
                          output_dir: Optional[Path] = None) -> list[Path]:
    """Export all blueprints to JSON files."""
    paths = []
    for bp in blueprints.values():
        paths.append(export_blueprint(bp, output_dir))
    return paths


def write_serum_blueprint_manifest(output_dir: Optional[Path] = None) -> Path:
    """Write module manifest for discovery."""
    out = output_dir or OUTPUT_DIR
    out.mkdir(parents=True, exist_ok=True)
    manifest = {
        "module": "serum_blueprint",
        "version": "1.0.0",
        "chaos_attractors": ["Lorenz", "Rossler"],
        "warp_modes_used": [
            "Asym +", "Asym +/-", "FM (B)", "Sync",
            "PWM", "Bend +/-", "Mirror", "LPF", "Hard Clip",
        ],
        "requires": ["numpy"],
        "optional": ["soundfile", "librosa"],
    }
    filepath = out / "serum_blueprint_manifest.json"
    filepath.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    return filepath
