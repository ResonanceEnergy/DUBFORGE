"""
DUBFORGE — OpenClaw Agent: Subtronics Producer Emulation

An AI producer agent that encodes Subtronics' (Jesse Kardon) production DNA
as parameter presets, arrangement templates, and sound design recipes.

Subtronics Production Profile (researched):
────────────────────────────────────────────
- Jesse Kardon, born 1992, Philadelphia PA
- Cyclops Recordings founder
- Albums: Fractals, Antifractals, Tesseract, Fibonacci
- Beatport's top-selling artist 2024, DJ Mag NA DJ of the Year 2023
- 3x Dubstep Artist of the Year (EDMA)

Sound Design Philosophy:
- Master of Serum — sound design is why he produces
- "Hundreds of different techniques" via educated trial and error
- Prefers "crisp, interesting textures" — the signature crunch
- Clips channels +50dB during sound design → bandpass → resample
- OTT + distortion layering is core workflow
- Clips master by 5-10dB ("I just make shit slam")
- No formal music theory — intuition-driven

Bass Design:
- FM synthesis: wavetable FM'd with basic shapes (sine, triangle)
- Bandpassed noise layering on bass
- Distortion + soft clipping chains
- Mono legato with 50-200ms portamento/glide
- Resample loop: slam +50dB → bandpass → resample → more OTT + distortion
- "Heavy, texturized robot bass music"
- Sub bass: pure sine, note selection creates physical resonances

Style:
- Riddim-influenced dubstep, not pure riddim
- "Savage riddim & intricate soundscapes"
- "Stellar syncopation and sound design"
- Mathematical/fractal themes (Fractals, Fibonacci albums)
- Collaborates with: Excision, Zeds Dead, GRiZ, Rezz, Marshmello
- 140-150 BPM, half-time drum patterns
- Extreme sound design contrast: quiet breakdowns → obliterating drops

Usage:
    from engine.openclaw_agent import OpenClawAgent

    agent = OpenClawAgent()
    dna = agent.produce("Track Name", style="dubstep", mood="dark")

    # Or override an existing SongDNA:
    agent.apply_style(existing_dna)
"""

from __future__ import annotations

import random
from dataclasses import dataclass, field
from typing import Optional

# We import types from variation_engine — the agent produces SongDNA objects
from engine.variation_engine import (
    ArrangementSection,
    AtmosphereDNA,
    BassDNA,
    DrumDNA,
    FxDNA,
    LeadDNA,
    MixDNA,
    SongBlueprint,
    SongDNA,
    VariationEngine,
)


# ═══════════════════════════════════════════════════════════════
#  Subtronics Production Profiles
# ═══════════════════════════════════════════════════════════════

@dataclass
class ProductionProfile:
    """A named set of parameter biases encoding a producer's style."""
    name: str
    alias: str  # display name
    description: str

    # ── Bass character ──
    bass_fm_depth: tuple[float, float] = (3.0, 5.0)  # min, max
    bass_distortion: tuple[float, float] = (0.30, 0.55)
    bass_ott: tuple[float, float] = (0.10, 0.25)
    bass_filter_cutoff: tuple[float, float] = (0.50, 0.80)
    bass_fm_feedback: tuple[float, float] = (0.10, 0.35)
    bass_sub_weight: tuple[float, float] = (0.80, 0.95)
    bass_mid_drive: tuple[float, float] = (0.55, 0.85)
    bass_lfo_rate: tuple[float, float] = (1.5, 4.0)
    bass_lfo_depth: tuple[float, float] = (0.3, 0.7)
    preferred_bass_types: list[str] = field(
        default_factory=lambda: ["dist_fm", "sync", "neuro"])
    portamento_ms: tuple[float, float] = (50.0, 200.0)

    # ── Drum character ──
    kick_pitch: tuple[float, float] = (40.0, 52.0)
    kick_fm_depth: tuple[float, float] = (2.5, 5.0)
    kick_drive: tuple[float, float] = (0.50, 0.70)
    kick_sub_weight: tuple[float, float] = (0.60, 0.80)
    snare_metallic: tuple[float, float] = (0.15, 0.45)
    snare_compression: tuple[float, float] = (6.0, 12.0)
    hat_density: tuple[int, int] = (8, 16)
    hat_metallic: tuple[float, float] = (0.10, 0.30)
    preferred_kick_pattern: str = "halftime"
    preferred_snare_pattern: str = "ghosted"

    # ── Lead character ──
    lead_fm_depth: tuple[float, float] = (2.0, 5.0)
    lead_brightness: tuple[float, float] = (0.55, 0.85)
    lead_supersaw_voices: tuple[int, int] = (5, 9)
    lead_supersaw_detune: tuple[float, float] = (25.0, 50.0)
    lead_ott: tuple[float, float] = (0.15, 0.40)
    lead_reverb: tuple[float, float] = (0.3, 0.7)

    # ── Mix character ──
    target_lufs: tuple[float, float] = (-10.0, -8.0)
    stereo_width: tuple[float, float] = (0.8, 1.3)
    master_drive: tuple[float, float] = (0.30, 0.55)
    compression_ratio: tuple[float, float] = (2.5, 5.0)
    sidechain_depth: tuple[float, float] = (0.70, 0.90)

    # ── Atmosphere character ──
    pad_brightness: tuple[float, float] = (0.2, 0.5)
    reverb_decay: tuple[float, float] = (2.0, 4.5)
    noise_bed_level: tuple[float, float] = (0.08, 0.20)
    drone_movement: tuple[float, float] = (0.3, 0.6)

    # ── FX character ──
    riser_intensity: tuple[float, float] = (0.75, 0.95)
    impact_intensity: tuple[float, float] = (0.85, 1.0)
    glitch_amount: tuple[float, float] = (0.0, 0.15)
    vocal_chop_dist: tuple[float, float] = (0.25, 0.50)

    # ── Arrangement preferences ──
    bpm_range: tuple[int, int] = (140, 150)
    preferred_scales: list[str] = field(
        default_factory=lambda: ["minor", "phrygian", "harmonic_minor"])
    preferred_arrangement: str = "standard"
    drop_bars: int = 32
    intro_bars: int = 16
    breakdown_bars: int = 16

    # ── Identity ──
    cyclops_mode: bool = False  # special one-eye themed variations


# ── Subtronics Profile ──────────────────────────────────────────────

SUBTRONICS_PROFILE = ProductionProfile(
    name="subtronics",
    alias="SUBPHONICS OPENCLAW",
    description=(
        "Riddim-influenced dubstep with extreme FM bass, metallic/robotic "
        "textures, crunchy resampled sound design, half-time drums, "
        "mathematical themes. 'I just make shit slam.'"
    ),

    # Bass: signature crunchy FM with controlled aggression
    bass_fm_depth=(3.5, 5.0),
    bass_distortion=(0.35, 0.55),
    bass_ott=(0.12, 0.25),
    bass_filter_cutoff=(0.55, 0.80),
    bass_fm_feedback=(0.15, 0.35),
    bass_sub_weight=(0.85, 0.95),
    bass_mid_drive=(0.60, 0.85),
    bass_lfo_rate=(1.5, 4.5),
    bass_lfo_depth=(0.35, 0.75),
    preferred_bass_types=["dist_fm", "sync", "neuro"],
    portamento_ms=(60.0, 180.0),

    # Drums: punchy half-time with metallic character
    kick_pitch=(42.0, 50.0),
    kick_fm_depth=(3.0, 5.0),
    kick_drive=(0.55, 0.70),
    kick_sub_weight=(0.65, 0.80),
    snare_metallic=(0.20, 0.45),
    snare_compression=(8.0, 14.0),
    hat_density=(8, 16),
    hat_metallic=(0.15, 0.35),
    preferred_kick_pattern="halftime_synco",
    preferred_snare_pattern="ghosted",

    # Leads: FM-heavy, bright, aggressive
    lead_fm_depth=(3.0, 5.5),
    lead_brightness=(0.60, 0.90),
    lead_supersaw_voices=(5, 9),
    lead_supersaw_detune=(30.0, 55.0),
    lead_ott=(0.20, 0.40),
    lead_reverb=(0.3, 0.6),

    # Mix: loud, punchy, slightly wider
    target_lufs=(-9.5, -8.0),
    stereo_width=(0.9, 1.3),
    master_drive=(0.35, 0.55),
    compression_ratio=(3.0, 5.5),
    sidechain_depth=(0.75, 0.90),

    # Atmosphere: dark, robotic
    pad_brightness=(0.15, 0.40),
    reverb_decay=(2.5, 5.0),
    noise_bed_level=(0.10, 0.20),
    drone_movement=(0.35, 0.60),

    # FX: high energy, impactful
    riser_intensity=(0.80, 0.95),
    impact_intensity=(0.90, 1.0),
    glitch_amount=(0.02, 0.15),
    vocal_chop_dist=(0.30, 0.55),

    # Arrangement: standard dubstep structure
    bpm_range=(140, 150),
    preferred_scales=["minor", "phrygian", "harmonic_minor"],
    preferred_arrangement="standard",
    drop_bars=32,
    intro_bars=16,
    breakdown_bars=16,

    cyclops_mode=True,
)


# ── Arrangement templates specific to Subtronics style ──────────────

SUBTRONICS_ARRANGEMENT = [
    ArrangementSection(
        "intro", 16, 0.12,
        ["drone", "pad", "hats_sparse", "texture"],
    ),
    ArrangementSection(
        "build", 8, 0.50,
        ["kick", "snare_roll", "riser", "pad", "sub_swell"],
    ),
    ArrangementSection(
        "drop1", 32, 1.0,
        ["kick", "snare", "hats", "sub", "bass", "lead",
         "chops", "noise_bed"],
    ),
    ArrangementSection(
        "break", 16, 0.20,
        ["pad", "plucks", "sub_long", "reverb_fx", "texture"],
    ),
    ArrangementSection(
        "build2", 8, 0.55,
        ["kick", "snare_roll", "riser", "swell"],
    ),
    ArrangementSection(
        "drop2", 32, 1.0,
        ["kick", "snare", "hats", "sub", "bass", "lead",
         "chops", "noise_bed", "extra_bass"],
    ),
    ArrangementSection(
        "outro", 16, 0.08,
        ["kick_fade", "pad_fade", "sub_fade"],
    ),
]


# ── Bass riff patterns in the Subtronics style ──────────────────────
# (scale_degree, beat_pos, duration_beats)

SUBTRONICS_BASS_RIFFS: list[list[list[tuple]]] = [
    # Riff 1: Classic riddim-influenced grind
    [
        [(0, 0.0, 0.75), (0, 1.0, 0.5), (6, 1.75, 0.25), (0, 2.0, 1.0), (4, 3.5, 0.5)],
        [(0, 0.0, 1.5), (2, 2.0, 0.5), (4, 2.75, 0.25), (0, 3.0, 1.0)],
    ],
    # Riff 2: Syncopated metallic chug
    [
        [(0, 0.0, 1.0), (0, 1.5, 0.5), (6, 2.0, 0.5), (5, 2.75, 0.25), (0, 3.0, 1.0)],
        [(0, 0.0, 0.5), (3, 0.75, 0.25), (0, 1.0, 1.0), (4, 2.5, 0.5), (0, 3.0, 1.0)],
    ],
    # Riff 3: Heavy half-time stomp
    [
        [(0, 0.0, 2.0), (4, 2.0, 1.0), (2, 3.0, 1.0)],
        [(0, 0.0, 1.5), (6, 2.0, 0.5), (0, 2.5, 1.5)],
    ],
    # Riff 4: Glitchy rapid-fire
    [
        [(0, 0.0, 0.5), (0, 0.5, 0.25), (4, 1.0, 0.5), (0, 1.5, 0.5),
         (6, 2.0, 0.5), (3, 2.5, 0.5), (0, 3.0, 0.5), (2, 3.5, 0.5)],
    ],
    # Riff 5: Fibonacci-inspired (intervals based on sequence)
    [
        [(0, 0.0, 1.0), (1, 1.0, 0.5), (2, 1.5, 0.5),
         (3, 2.0, 0.5), (5, 2.5, 0.5), (0, 3.0, 1.0)],
        [(0, 0.0, 0.5), (5, 0.5, 0.5), (3, 1.0, 1.0),
         (2, 2.0, 0.5), (1, 2.5, 0.5), (0, 3.0, 1.0)],
    ],
]


# ── Lead melody patterns in the Subtronics style ────────────────────
# (scale_degree, beat_position, duration_beats, velocity)

SUBTRONICS_MELODIES: list[list[list[tuple]]] = [
    # Melody 1: Aggressive staccato
    [
        [(4, 0.0, 0.25, 1.0), (6, 0.5, 0.25, 0.9), (4, 1.0, 0.5, 0.85),
         (2, 2.0, 0.5, 0.9), (0, 3.0, 0.5, 1.0)],
    ],
    # Melody 2: Descending power
    [
        [(6, 0.0, 0.5, 1.0), (5, 0.5, 0.5, 0.95), (4, 1.0, 0.5, 0.9),
         (2, 2.0, 1.0, 0.85), (0, 3.0, 1.0, 0.8)],
    ],
    # Melody 3: Minimal — let the bass do the talking
    [
        [(0, 0.0, 1.0, 0.7), (-1, 1.0, 1.0, 0.0),
         (4, 2.0, 0.5, 0.8), (-1, 2.5, 1.5, 0.0)],
    ],
]


# ═══════════════════════════════════════════════════════════════
#  OpenClaw Agent
# ═══════════════════════════════════════════════════════════════

class OpenClawAgent:
    """AI producer agent that applies a Subtronics-style production profile.

    The agent can:
    1. Produce a new track from scratch (name → SongDNA)
    2. Apply its style to an existing SongDNA (style transfer)
    3. Suggest parameter adjustments based on its profile

    Named "OpenClaw" after Subtronics' Cyclops branding —
    one eye open, one claw ready to rip.
    """

    def __init__(self, profile: ProductionProfile | None = None):
        self.profile = profile or SUBTRONICS_PROFILE
        self._rng = random.Random()

    def _roll(self, lo: float, hi: float) -> float:
        """Random float in [lo, hi]."""
        return self._rng.uniform(lo, hi)

    def _roll_int(self, lo: int, hi: int) -> int:
        """Random int in [lo, hi]."""
        return self._rng.randint(lo, hi)

    def _pick(self, items: list):
        """Random choice from a list."""
        return self._rng.choice(items)

    # ──────────────────────────────────────────────────────────
    #  PRODUCE: Name → SongDNA (full pipeline)
    # ──────────────────────────────────────────────────────────

    def produce(
        self,
        name: str,
        style: str = "dubstep",
        mood: str = "",
        sound_style: str = "",
        key: str = "",
        scale: str = "",
        bpm: int = 0,
        seed: int = 0,
    ) -> SongDNA:
        """Generate a complete SongDNA with Subtronics' production DNA.

        First generates a base DNA via VariationEngine, then applies
        the OpenClaw production profile to shape everything.
        """
        # Seed RNG for reproducibility
        if seed:
            self._rng = random.Random(seed)
        else:
            # Seed from name hash
            import hashlib
            h = int(hashlib.sha256(name.encode()).hexdigest()[:8], 16)
            self._rng = random.Random(h)

        # Let VariationEngine do the heavy lifting first
        bp = SongBlueprint(
            name=name,
            style=style,
            mood=mood or "aggressive",
            sound_style=sound_style or "crunchy metallic",
            key=key,
            scale=scale or self._pick(self.profile.preferred_scales),
            bpm=bpm or self._roll_int(*self.profile.bpm_range),
            seed=seed,
        )
        ve = VariationEngine(artistic_variance=0.12)
        dna = ve.forge_dna(bp)

        # Now apply OpenClaw style override
        self.apply_style(dna)

        # Tag it
        if "openclaw" not in dna.tags:
            dna.tags.append("openclaw")
        if self.profile.name not in dna.tags:
            dna.tags.append(self.profile.name)

        dna.notes = (
            f"Produced by {self.profile.alias} "
            f"(profile: {self.profile.name}) — {self.profile.description}"
        )

        return dna

    # ──────────────────────────────────────────────────────────
    #  APPLY STYLE: Override an existing SongDNA in-place
    # ──────────────────────────────────────────────────────────

    def apply_style(self, dna: SongDNA) -> SongDNA:
        """Apply production profile to an existing SongDNA.

        Overwrites bass, drum, lead, mix, fx, atmosphere parameters
        with values sampled from the profile's ranges.
        Returns the same dna object (mutated in place).
        """
        p = self.profile

        # ── Bass ──
        dna.bass.fm_depth = self._roll(*p.bass_fm_depth)
        dna.bass.distortion = self._roll(*p.bass_distortion)
        dna.bass.ott_amount = self._roll(*p.bass_ott)
        dna.bass.filter_cutoff = self._roll(*p.bass_filter_cutoff)
        dna.bass.fm_feedback = self._roll(*p.bass_fm_feedback)
        dna.bass.sub_weight = self._roll(*p.bass_sub_weight)
        dna.bass.mid_drive = self._roll(*p.bass_mid_drive)
        dna.bass.lfo_rate = self._roll(*p.bass_lfo_rate)
        dna.bass.lfo_depth = self._roll(*p.bass_lfo_depth)

        # Bass types: use profile preference
        types = list(p.preferred_bass_types)
        self._rng.shuffle(types)
        dna.bass.primary_type = types[0]
        dna.bass.secondary_type = types[1] if len(types) > 1 else types[0]
        dna.bass.tertiary_type = types[2] if len(types) > 2 else types[0]

        # Bass rotation limited to our 3 types
        dna.bass_rotation = types[:3]

        # Pick a Subtronics bass riff
        riff = self._pick(SUBTRONICS_BASS_RIFFS)
        dna.bass.bass_riff = riff

        # ── Drums ──
        dna.drums.kick_pitch = self._roll(*p.kick_pitch)
        dna.drums.kick_fm_depth = self._roll(*p.kick_fm_depth)
        dna.drums.kick_drive = self._roll(*p.kick_drive)
        dna.drums.kick_sub_weight = self._roll(*p.kick_sub_weight)
        dna.drums.snare_metallic = self._roll(*p.snare_metallic)
        dna.drums.snare_compression = self._roll(*p.snare_compression)
        dna.drums.hat_density = self._roll_int(*p.hat_density)
        dna.drums.hat_metallic = self._roll(*p.hat_metallic)

        # ── Lead ──
        dna.lead.fm_depth = self._roll(*p.lead_fm_depth)
        dna.lead.brightness = self._roll(*p.lead_brightness)
        dna.lead.supersaw_voices = self._roll_int(*p.lead_supersaw_voices)
        dna.lead.supersaw_detune = self._roll(*p.lead_supersaw_detune)
        dna.lead.ott_amount = self._roll(*p.lead_ott)
        dna.lead.reverb_decay = self._roll(*p.lead_reverb)
        dna.lead.use_fm = True  # always FM for Subtronics style

        # Pick a Subtronics melody pattern
        melody = self._pick(SUBTRONICS_MELODIES)
        dna.lead.melody_patterns = melody

        # ── Mix ──
        dna.mix.target_lufs = self._roll(*p.target_lufs)
        dna.mix.stereo_width = self._roll(*p.stereo_width)
        dna.mix.master_drive = self._roll(*p.master_drive)
        dna.mix.compression_ratio = self._roll(*p.compression_ratio)
        dna.mix.sidechain_depth = self._roll(*p.sidechain_depth)

        # ── Atmosphere ──
        dna.atmosphere.pad_brightness = self._roll(*p.pad_brightness)
        dna.atmosphere.reverb_decay = self._roll(*p.reverb_decay)
        dna.atmosphere.noise_bed_level = self._roll(*p.noise_bed_level)
        dna.atmosphere.drone_movement = self._roll(*p.drone_movement)
        dna.atmosphere.pad_type = "dark"

        # ── FX ──
        dna.fx.riser_intensity = self._roll(*p.riser_intensity)
        dna.fx.impact_intensity = self._roll(*p.impact_intensity)
        dna.fx.glitch_amount = self._roll(*p.glitch_amount)
        dna.fx.vocal_chop_distortion = self._roll(*p.vocal_chop_dist)

        # ── Arrangement ──
        # Use Subtronics-specific arrangement
        dna.arrangement = list(SUBTRONICS_ARRANGEMENT)
        dna.total_bars = sum(s.bars for s in dna.arrangement)

        # ── BPM: ensure within profile range ──
        lo, hi = p.bpm_range
        if dna.bpm < lo or dna.bpm > hi:
            dna.bpm = self._roll_int(lo, hi)

        # ── Scale: prefer profile scales ──
        if dna.scale not in p.preferred_scales:
            dna.scale = self._pick(p.preferred_scales)

        return dna

    # ──────────────────────────────────────────────────────────
    #  SUGGEST: return parameter suggestions without applying
    # ──────────────────────────────────────────────────────────

    def suggest(self, dna: SongDNA) -> dict:
        """Analyze a SongDNA and suggest Subtronics-style tweaks.

        Returns a dict of parameter paths → suggested values.
        Does NOT modify the DNA.
        """
        p = self.profile
        suggestions: dict[str, dict] = {}

        # Check bass parameters
        if dna.bass.fm_depth < p.bass_fm_depth[0]:
            suggestions["bass.fm_depth"] = {
                "current": dna.bass.fm_depth,
                "suggested": self._roll(*p.bass_fm_depth),
                "reason": "FM depth too low for Subtronics crunch",
            }
        if dna.bass.distortion < p.bass_distortion[0]:
            suggestions["bass.distortion"] = {
                "current": dna.bass.distortion,
                "suggested": self._roll(*p.bass_distortion),
                "reason": "Distortion below Subtronics floor",
            }
        if dna.bass.ott_amount > p.bass_ott[1]:
            suggestions["bass.ott_amount"] = {
                "current": dna.bass.ott_amount,
                "suggested": self._roll(*p.bass_ott),
                "reason": "OTT too high — gets harsh, not crunchy",
            }

        # Check mix
        if dna.mix.target_lufs < p.target_lufs[0]:
            suggestions["mix.target_lufs"] = {
                "current": dna.mix.target_lufs,
                "suggested": self._roll(*p.target_lufs),
                "reason": "LUFS target too quiet for Subtronics slam",
            }
        if dna.mix.target_lufs > p.target_lufs[1]:
            suggestions["mix.target_lufs"] = {
                "current": dna.mix.target_lufs,
                "suggested": self._roll(*p.target_lufs),
                "reason": "LUFS target too loud — will clip badly",
            }

        # Check BPM
        lo, hi = p.bpm_range
        if dna.bpm < lo or dna.bpm > hi:
            suggestions["bpm"] = {
                "current": dna.bpm,
                "suggested": self._roll_int(lo, hi),
                "reason": f"BPM outside Subtronics range ({lo}-{hi})",
            }

        # Check drums
        if dna.drums.snare_metallic < p.snare_metallic[0]:
            suggestions["drums.snare_metallic"] = {
                "current": dna.drums.snare_metallic,
                "suggested": self._roll(*p.snare_metallic),
                "reason": "Snare needs more metallic character",
            }

        return suggestions

    # ──────────────────────────────────────────────────────────
    #  INFO / DEBUG
    # ──────────────────────────────────────────────────────────

    def banner(self) -> str:
        """Print the agent's identity banner."""
        p = self.profile
        lines = [
            "╔══════════════════════════════════════════════════╗",
            f"║  {p.alias:<47}║",
            f"║  Profile: {p.name:<38}║",
            "║──────────────────────────────────────────────────║",
            f"║  Bass FM: {p.bass_fm_depth[0]:.1f}–{p.bass_fm_depth[1]:.1f}"
            f"  | Dist: {p.bass_distortion[0]:.2f}–{p.bass_distortion[1]:.2f}"
            f"          ║",
            f"║  LUFS: {p.target_lufs[0]:.1f} to {p.target_lufs[1]:.1f}"
            f"  | BPM: {p.bpm_range[0]}–{p.bpm_range[1]}"
            f"              ║",
            f"║  Bass: {' → '.join(p.preferred_bass_types):<41}║",
            f"║  Scales: {', '.join(p.preferred_scales):<39}║",
            "╚══════════════════════════════════════════════════╝",
        ]
        return "\n".join(lines)

    def profile_summary(self) -> str:
        """Detailed text summary of the production profile."""
        p = self.profile
        return (
            f"Production Profile: {p.alias}\n"
            f"  {p.description}\n\n"
            f"  Bass Character:\n"
            f"    FM Depth:    {p.bass_fm_depth[0]:.1f} – {p.bass_fm_depth[1]:.1f}\n"
            f"    Distortion:  {p.bass_distortion[0]:.2f} – {p.bass_distortion[1]:.2f}\n"
            f"    OTT:         {p.bass_ott[0]:.2f} – {p.bass_ott[1]:.2f}\n"
            f"    Sub Weight:  {p.bass_sub_weight[0]:.2f} – {p.bass_sub_weight[1]:.2f}\n"
            f"    Mid Drive:   {p.bass_mid_drive[0]:.2f} – {p.bass_mid_drive[1]:.2f}\n"
            f"    Types:       {' → '.join(p.preferred_bass_types)}\n"
            f"    Portamento:  {p.portamento_ms[0]:.0f} – {p.portamento_ms[1]:.0f} ms\n\n"
            f"  Drums:\n"
            f"    Kick Pitch:  {p.kick_pitch[0]:.0f} – {p.kick_pitch[1]:.0f} Hz\n"
            f"    Kick Drive:  {p.kick_drive[0]:.2f} – {p.kick_drive[1]:.2f}\n"
            f"    Snare Metal: {p.snare_metallic[0]:.2f} – {p.snare_metallic[1]:.2f}\n"
            f"    Hat Density: {p.hat_density[0]} – {p.hat_density[1]}\n"
            f"    Kick Pat:    {p.preferred_kick_pattern}\n"
            f"    Snare Pat:   {p.preferred_snare_pattern}\n\n"
            f"  Mix:\n"
            f"    LUFS Target: {p.target_lufs[0]:.1f} – {p.target_lufs[1]:.1f}\n"
            f"    Width:       {p.stereo_width[0]:.1f} – {p.stereo_width[1]:.1f}\n"
            f"    Drive:       {p.master_drive[0]:.2f} – {p.master_drive[1]:.2f}\n"
            f"    Compression: {p.compression_ratio[0]:.1f} – {p.compression_ratio[1]:.1f}:1\n"
            f"    Sidechain:   {p.sidechain_depth[0]:.2f} – {p.sidechain_depth[1]:.2f}\n\n"
            f"  Structure:\n"
            f"    BPM Range:   {p.bpm_range[0]} – {p.bpm_range[1]}\n"
            f"    Scales:      {', '.join(p.preferred_scales)}\n"
            f"    Drop Length: {p.drop_bars} bars\n"
        )


# ═══════════════════════════════════════════════════════════════
#  Registry of available producer profiles
# ═══════════════════════════════════════════════════════════════

PRODUCER_PROFILES: dict[str, ProductionProfile] = {
    "subtronics": SUBTRONICS_PROFILE,
}


def get_agent(producer: str = "subtronics") -> OpenClawAgent:
    """Factory: get an OpenClawAgent with the named producer profile."""
    profile = PRODUCER_PROFILES.get(producer.lower())
    if profile is None:
        available = ", ".join(PRODUCER_PROFILES.keys())
        raise ValueError(
            f"Unknown producer '{producer}'. Available: {available}"
        )
    return OpenClawAgent(profile)


# ═══════════════════════════════════════════════════════════════
#  CLI / Standalone Test
# ═══════════════════════════════════════════════════════════════

if __name__ == "__main__":
    agent = OpenClawAgent()
    print(agent.banner())
    print()
    print(agent.profile_summary())

    # Generate a test track
    print("\n── Test Production ──\n")
    dna = agent.produce("Cyclops Fury", style="dubstep", mood="aggressive")
    print(dna.summary())

    # Suggest tweaks on a vanilla DNA
    print("\n── Suggestions on vanilla DNA ──\n")
    from engine.variation_engine import forge_song_dna
    vanilla = forge_song_dna("Vanilla Test")
    suggestions = agent.suggest(vanilla)
    for path, info in suggestions.items():
        print(f"  {path}: {info['current']} → {info['suggested']}")
        print(f"    Reason: {info['reason']}")
