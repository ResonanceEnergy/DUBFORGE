"""DUBFORGE — Curated Dubstep MIDI Pattern Database.

Provides genre-authentic MIDI patterns for bass, lead, arp, and rhythm
stems.  Patterns are stored as scale-degree tuples so they transpose
to any key.  The database is indexed by style / energy / section type
so phase_one can pick the right pattern for the current arrangement
context.

Pattern format (per note):
    (scale_degree, beat_position, duration_beats, velocity_norm)

    scale_degree : int   0–6 within the scale, -1 = rest
    beat_position: float 0.0–3.75 within a single bar (4/4)
    duration_beats: float note length
    velocity_norm : float 0.0–1.0 (scaled by stem base velocity)

All patterns are 1-bar long (to be looped/sequenced).
"""
from __future__ import annotations

import random
from dataclasses import dataclass, field


# ═══════════════════════════════════════════════════════════════════════════
#  DATA TYPES
# ═══════════════════════════════════════════════════════════════════════════

# One note: (scale_degree, beat_pos, duration_beats, velocity_norm)
NotePattern = tuple[int, float, float, float]

# One bar of notes
BarPattern = list[NotePattern]


@dataclass
class MidiPattern:
    """A named MIDI pattern with metadata for query-matching."""
    name: str
    stem: str               # "mid_bass" | "sub_bass" | "lead" | "arp" | ...
    style: str = "dubstep"  # dubstep | riddim | melodic | heavy
    section: str = "drop"   # intro | build | drop | breakdown | outro
    energy: float = 0.8     # 0.0–1.0
    bars: list[BarPattern] = field(default_factory=list)
    tags: list[str] = field(default_factory=list)


# ═══════════════════════════════════════════════════════════════════════════
#  MID BASS PATTERNS — rhythmic 8th/16th patterns on root+octave
# ═══════════════════════════════════════════════════════════════════════════

_BASS_PATTERNS: list[MidiPattern] = [
    # ── Classic dubstep: heavy offbeat 8ths ──
    MidiPattern(
        name="offbeat_pump",
        stem="mid_bass", style="dubstep", section="drop", energy=0.9,
        bars=[
            [(0, 0.0, 0.25, 1.0), (0, 0.5, 0.25, 0.8), (0, 1.0, 0.25, 1.0),
             (0, 1.5, 0.25, 0.8), (0, 2.0, 0.25, 1.0), (0, 2.5, 0.25, 0.8),
             (0, 3.0, 0.25, 1.0), (0, 3.5, 0.25, 0.8)],
        ],
        tags=["8th", "driving"],
    ),
    # ── Syncopated Subtronics-style ──
    MidiPattern(
        name="subtronics_bounce",
        stem="mid_bass", style="dubstep", section="drop", energy=1.0,
        bars=[
            [(0, 0.0, 0.25, 1.0), (6, 0.75, 0.25, 0.9), (0, 1.0, 0.25, 1.0),
             (0, 1.5, 0.125, 0.7), (0, 2.0, 0.25, 1.0), (6, 2.75, 0.25, 0.9),
             (0, 3.0, 0.25, 1.0), (4, 3.5, 0.25, 0.8)],
        ],
        tags=["syncopated", "aggressive"],
    ),
    # ── Half-time feel ──
    MidiPattern(
        name="halftime_grind",
        stem="mid_bass", style="dubstep", section="drop", energy=0.7,
        bars=[
            [(0, 0.0, 0.5, 1.0), (-1, 0.5, 0.5, 0.0), (0, 1.0, 0.25, 0.9),
             (6, 1.5, 0.25, 0.7), (0, 2.0, 1.0, 0.85), (0, 3.0, 0.5, 0.9),
             (4, 3.5, 0.25, 0.7)],
        ],
        tags=["halftime", "heavy"],
    ),
    # ── Skrillex triplet bounce ──
    MidiPattern(
        name="triplet_bounce",
        stem="mid_bass", style="dubstep", section="drop", energy=0.95,
        bars=[
            [(0, 0.0, 0.33, 1.0), (0, 0.33, 0.33, 0.8), (0, 0.67, 0.33, 0.6),
             (0, 1.0, 0.33, 1.0), (0, 1.33, 0.33, 0.8), (0, 1.67, 0.33, 0.6),
             (0, 2.0, 0.33, 1.0), (0, 2.33, 0.33, 0.8), (0, 2.67, 0.33, 0.6),
             (0, 3.0, 0.33, 1.0), (0, 3.33, 0.33, 0.8), (0, 3.67, 0.33, 0.6)],
        ],
        tags=["triplet", "aggressive"],
    ),
    # ── Excision-style 16th stutter ──
    MidiPattern(
        name="stutter_16th",
        stem="mid_bass", style="dubstep", section="drop", energy=1.0,
        bars=[
            [(0, 0.0, 0.125, 1.0), (0, 0.25, 0.125, 0.9), (0, 0.5, 0.125, 0.8),
             (0, 0.75, 0.125, 0.7), (0, 1.0, 0.5, 1.0),
             (0, 2.0, 0.125, 1.0), (0, 2.25, 0.125, 0.9), (0, 2.5, 0.125, 0.8),
             (0, 2.75, 0.125, 0.7), (0, 3.0, 0.5, 1.0), (0, 3.5, 0.25, 0.9)],
        ],
        tags=["16th", "stutter", "heavy"],
    ),
    # ── Melodic bass: chord tone movement ──
    MidiPattern(
        name="melodic_walk",
        stem="mid_bass", style="melodic", section="drop", energy=0.6,
        bars=[
            [(0, 0.0, 1.0, 1.0), (2, 1.0, 0.5, 0.85), (4, 1.5, 0.5, 0.8),
             (2, 2.0, 1.0, 0.9), (0, 3.0, 0.5, 0.85), (6, 3.5, 0.5, 0.7)],
        ],
        tags=["melodic", "walking"],
    ),
    # ── Intro / breakdown: simple sustained ──
    MidiPattern(
        name="intro_sustain",
        stem="mid_bass", style="dubstep", section="intro", energy=0.3,
        bars=[
            [(0, 0.0, 4.0, 0.7)],
        ],
        tags=["sustained", "simple"],
    ),
    # ── Build: rising tension ──
    MidiPattern(
        name="build_tension",
        stem="mid_bass", style="dubstep", section="build", energy=0.6,
        bars=[
            [(0, 0.0, 0.5, 0.7), (0, 1.0, 0.5, 0.8), (0, 2.0, 0.5, 0.9),
             (0, 3.0, 0.25, 1.0), (0, 3.5, 0.25, 1.0)],
        ],
        tags=["building", "accelerating"],
    ),
]

# ═══════════════════════════════════════════════════════════════════════════
#  RIDDIM BASS PATTERNS — gap-based with 808-style
# ═══════════════════════════════════════════════════════════════════════════

_RIDDIM_PATTERNS: list[MidiPattern] = [
    MidiPattern(
        name="riddim_classic",
        stem="riddim", style="riddim", section="drop", energy=0.9,
        bars=[
            [(0, 0.0, 0.25, 1.0), (-1, 0.25, 0.25, 0.0), (0, 0.5, 0.25, 0.9),
             (-1, 0.75, 0.75, 0.0), (0, 1.5, 0.25, 0.9), (-1, 1.75, 0.25, 0.0),
             (0, 2.0, 0.25, 1.0), (-1, 2.25, 0.25, 0.0), (0, 2.5, 0.25, 0.9),
             (-1, 2.75, 0.75, 0.0), (0, 3.5, 0.25, 0.8)],
        ],
        tags=["riddim", "gap", "classic"],
    ),
    MidiPattern(
        name="riddim_minimal",
        stem="riddim", style="riddim", section="drop", energy=0.7,
        bars=[
            [(0, 0.0, 0.25, 1.0), (-1, 0.25, 1.25, 0.0),
             (0, 1.5, 0.25, 0.9), (-1, 1.75, 0.75, 0.0),
             (0, 2.5, 0.25, 1.0), (-1, 2.75, 1.25, 0.0)],
        ],
        tags=["riddim", "minimal", "space"],
    ),
    MidiPattern(
        name="riddim_bounce",
        stem="riddim", style="riddim", section="drop", energy=1.0,
        bars=[
            [(0, 0.0, 0.125, 1.0), (0, 0.25, 0.125, 0.9),
             (-1, 0.5, 0.5, 0.0),
             (0, 1.0, 0.125, 1.0), (0, 1.25, 0.125, 0.9),
             (-1, 1.5, 0.5, 0.0),
             (0, 2.0, 0.125, 1.0), (0, 2.25, 0.125, 0.9),
             (0, 2.5, 0.125, 0.8), (-1, 2.75, 0.25, 0.0),
             (0, 3.0, 0.125, 1.0), (0, 3.25, 0.125, 0.9),
             (-1, 3.5, 0.5, 0.0)],
        ],
        tags=["riddim", "bounce", "16th"],
    ),
]

# ═══════════════════════════════════════════════════════════════════════════
#  LEAD PATTERNS — melodic phrases using scale degrees
# ═══════════════════════════════════════════════════════════════════════════

_LEAD_PATTERNS: list[MidiPattern] = [
    # ── Scream lead: repeating motif ──
    MidiPattern(
        name="scream_motif",
        stem="lead", style="dubstep", section="drop", energy=0.9,
        bars=[
            [(4, 0.0, 0.5, 1.0), (6, 0.5, 0.5, 0.9), (4, 1.0, 0.25, 0.85),
             (2, 1.5, 0.5, 0.8), (0, 2.0, 1.0, 1.0), (2, 3.0, 0.5, 0.85),
             (4, 3.5, 0.5, 0.9)],
        ],
        tags=["scream", "melodic", "motif"],
    ),
    MidiPattern(
        name="siren_call",
        stem="lead", style="dubstep", section="drop", energy=0.85,
        bars=[
            [(0, 0.0, 0.25, 1.0), (4, 0.5, 0.25, 0.9), (0, 1.0, 0.25, 1.0),
             (4, 1.5, 0.25, 0.9), (0, 2.0, 0.5, 1.0), (6, 2.5, 0.5, 0.85),
             (4, 3.0, 0.5, 0.9), (2, 3.5, 0.5, 0.8)],
        ],
        tags=["siren", "call_response"],
    ),
    # ── Melodic dubstep: singable melody ──
    MidiPattern(
        name="melodic_hook",
        stem="lead", style="melodic", section="drop", energy=0.7,
        bars=[
            [(0, 0.0, 1.0, 0.9), (2, 1.0, 0.5, 0.85), (4, 1.5, 1.0, 0.9),
             (6, 2.5, 0.5, 0.8), (4, 3.0, 1.0, 0.85)],
        ],
        tags=["melodic", "singable", "hook"],
    ),
    MidiPattern(
        name="descending_phrase",
        stem="lead", style="dubstep", section="drop", energy=0.8,
        bars=[
            [(6, 0.0, 0.5, 1.0), (4, 0.5, 0.5, 0.9), (2, 1.0, 0.5, 0.85),
             (0, 1.5, 0.5, 0.8), (-1, 2.0, 0.5, 0.0), (4, 2.5, 0.5, 0.9),
             (2, 3.0, 0.5, 0.85), (0, 3.5, 0.5, 0.8)],
        ],
        tags=["descending", "phrase"],
    ),
    MidiPattern(
        name="ascending_build",
        stem="lead", style="dubstep", section="build", energy=0.6,
        bars=[
            [(0, 0.0, 0.5, 0.7), (2, 0.5, 0.5, 0.75), (4, 1.0, 0.5, 0.8),
             (6, 1.5, 0.5, 0.85), (0, 2.0, 0.5, 0.9), (2, 2.5, 0.5, 0.9),
             (4, 3.0, 0.5, 0.95), (6, 3.5, 0.5, 1.0)],
        ],
        tags=["ascending", "build", "tension"],
    ),
    # ── Staccato stab lead ──
    MidiPattern(
        name="stab_rhythm",
        stem="lead", style="dubstep", section="drop", energy=0.95,
        bars=[
            [(0, 0.0, 0.125, 1.0), (0, 0.5, 0.125, 0.9), (4, 1.0, 0.125, 1.0),
             (4, 1.5, 0.125, 0.85), (6, 2.0, 0.25, 1.0),
             (4, 2.5, 0.125, 0.9), (2, 3.0, 0.25, 0.9), (0, 3.5, 0.125, 0.85)],
        ],
        tags=["staccato", "stab", "rhythmic"],
    ),
    # ── Intro / breakdown: sparse, atmospheric ──
    MidiPattern(
        name="intro_melody",
        stem="lead", style="melodic", section="intro", energy=0.3,
        bars=[
            [(0, 0.0, 2.0, 0.6), (4, 2.0, 1.0, 0.5), (2, 3.0, 1.0, 0.45)],
        ],
        tags=["intro", "sparse", "atmospheric"],
    ),
]

# ═══════════════════════════════════════════════════════════════════════════
#  NEURO PATTERNS — timed hits for growl/neuro bass
# ═══════════════════════════════════════════════════════════════════════════

_NEURO_PATTERNS: list[MidiPattern] = [
    MidiPattern(
        name="neuro_chop",
        stem="neuro", style="dubstep", section="drop", energy=0.9,
        bars=[
            [(0, 0.0, 0.25, 1.0), (0, 0.5, 0.125, 0.8), (0, 0.75, 0.125, 0.7),
             (0, 1.0, 0.25, 1.0), (-1, 1.5, 0.5, 0.0),
             (0, 2.0, 0.125, 1.0), (0, 2.25, 0.125, 0.9), (0, 2.5, 0.25, 0.85),
             (0, 3.0, 0.5, 1.0), (0, 3.5, 0.125, 0.7)],
        ],
        tags=["chop", "rhythmic"],
    ),
    MidiPattern(
        name="neuro_stutter",
        stem="neuro", style="dubstep", section="drop", energy=1.0,
        bars=[
            [(0, i * 0.125, 0.0625, 1.0 - i * 0.05) for i in range(8)] +
            [(-1, 1.0, 1.0, 0.0)] +
            [(0, 2.0 + i * 0.125, 0.0625, 1.0 - i * 0.05) for i in range(8)] +
            [(-1, 3.0, 0.5, 0.0), (0, 3.5, 0.25, 1.0)],
        ],
        tags=["stutter", "rapid", "aggressive"],
    ),
    MidiPattern(
        name="neuro_swing",
        stem="neuro", style="dubstep", section="drop", energy=0.75,
        bars=[
            [(0, 0.0, 0.25, 1.0), (-1, 0.25, 0.25, 0.0),
             (0, 0.5, 0.25, 0.8), (0, 1.0, 0.5, 1.0),
             (-1, 1.5, 0.5, 0.0), (0, 2.0, 0.25, 0.9),
             (0, 2.5, 0.5, 0.85), (0, 3.0, 0.25, 1.0),
             (-1, 3.25, 0.25, 0.0), (0, 3.5, 0.25, 0.8)],
        ],
        tags=["swing", "groove"],
    ),
]

# ═══════════════════════════════════════════════════════════════════════════
#  ARP PATTERNS — sequenced scale-degree runs
# ═══════════════════════════════════════════════════════════════════════════

_ARP_PATTERNS: list[MidiPattern] = [
    MidiPattern(
        name="arp_classic_up",
        stem="arps", style="melodic", section="build", energy=0.6,
        bars=[
            [(d % 7, i * 0.25, 0.2, 0.8 + 0.02 * i) for i, d in
             enumerate([0, 2, 4, 6, 0, 2, 4, 6, 0, 2, 4, 6, 0, 2, 4, 6])],
        ],
        tags=["up", "classic", "16th"],
    ),
    MidiPattern(
        name="arp_updown",
        stem="arps", style="melodic", section="build", energy=0.7,
        bars=[
            [(d % 7, i * 0.25, 0.2, 0.85) for i, d in
             enumerate([0, 2, 4, 6, 4, 2, 0, 2, 4, 6, 4, 2, 0, 2, 4, 6])],
        ],
        tags=["updown", "flowing"],
    ),
    MidiPattern(
        name="arp_broken",
        stem="arps", style="dubstep", section="drop", energy=0.8,
        bars=[
            [(0, 0.0, 0.125, 1.0), (4, 0.25, 0.125, 0.9),
             (2, 0.5, 0.125, 0.85), (6, 0.75, 0.125, 0.8),
             (-1, 1.0, 0.5, 0.0),
             (4, 1.5, 0.125, 0.9), (0, 1.75, 0.125, 1.0),
             (6, 2.0, 0.25, 0.85), (2, 2.5, 0.125, 0.9),
             (-1, 2.75, 0.25, 0.0),
             (0, 3.0, 0.125, 1.0), (4, 3.25, 0.125, 0.9),
             (6, 3.5, 0.25, 0.85)],
        ],
        tags=["broken", "glitchy"],
    ),
]

# ═══════════════════════════════════════════════════════════════════════════
#  SUB BASS — follows chord roots (not always just sitting on root)
# ═══════════════════════════════════════════════════════════════════════════

_SUB_PATTERNS: list[MidiPattern] = [
    MidiPattern(
        name="sub_root_hold",
        stem="sub_bass", style="dubstep", section="drop", energy=0.8,
        bars=[[(0, 0.0, 4.0, 0.9)]],
        tags=["sustained", "simple"],
    ),
    MidiPattern(
        name="sub_octave_bounce",
        stem="sub_bass", style="dubstep", section="drop", energy=0.9,
        bars=[
            [(0, 0.0, 2.0, 1.0), (0, 2.0, 0.5, 0.9), (0, 3.0, 0.5, 0.85),
             (0, 3.5, 0.25, 0.8)],
        ],
        tags=["bounce", "octave"],
    ),
    MidiPattern(
        name="sub_chord_follow",
        stem="sub_bass", style="melodic", section="drop", energy=0.7,
        bars=[
            [(0, 0.0, 2.0, 0.9), (4, 2.0, 2.0, 0.85)],
        ],
        tags=["chord_follow", "melodic"],
    ),
]

# ═══════════════════════════════════════════════════════════════════════════
#  SUPERSAW — power chord / swell patterns
# ═══════════════════════════════════════════════════════════════════════════

_SUPERSAW_PATTERNS: list[MidiPattern] = [
    MidiPattern(
        name="supersaw_power",
        stem="supersaw", style="dubstep", section="drop", energy=0.9,
        bars=[
            [(0, 0.0, 4.0, 1.0), (4, 0.0, 4.0, 0.9), (2, 0.0, 4.0, 0.85)],
        ],
        tags=["power", "sustained"],
    ),
    MidiPattern(
        name="supersaw_stab",
        stem="supersaw", style="dubstep", section="drop", energy=0.95,
        bars=[
            [(0, 0.0, 0.5, 1.0), (4, 0.0, 0.5, 0.9), (2, 0.0, 0.5, 0.85),
             (-1, 0.5, 1.5, 0.0),
             (0, 2.0, 0.5, 1.0), (4, 2.0, 0.5, 0.9), (2, 2.0, 0.5, 0.85),
             (-1, 2.5, 0.5, 0.0),
             (0, 3.0, 0.5, 1.0), (4, 3.0, 0.5, 0.9), (2, 3.0, 0.5, 0.85)],
        ],
        tags=["stab", "rhythmic"],
    ),
    MidiPattern(
        name="supersaw_swell",
        stem="supersaw", style="dubstep", section="build", energy=0.5,
        bars=[
            [(0, 0.0, 4.0, 0.5), (4, 0.0, 4.0, 0.45)],
        ],
        tags=["swell", "build"],
    ),
]


# ═══════════════════════════════════════════════════════════════════════════
#  COMBINED INDEX
# ═══════════════════════════════════════════════════════════════════════════

ALL_PATTERNS: list[MidiPattern] = (
    _BASS_PATTERNS + _RIDDIM_PATTERNS + _LEAD_PATTERNS +
    _NEURO_PATTERNS + _ARP_PATTERNS + _SUB_PATTERNS + _SUPERSAW_PATTERNS
)

# Quick lookup by stem name
_BY_STEM: dict[str, list[MidiPattern]] = {}
for _p in ALL_PATTERNS:
    _BY_STEM.setdefault(_p.stem, []).append(_p)


def query_patterns(
    stem: str,
    *,
    style: str = "",
    section: str = "",
    energy_min: float = 0.0,
    energy_max: float = 1.0,
    tags: list[str] | None = None,
) -> list[MidiPattern]:
    """Return patterns matching the given criteria, scored by relevance.

    Parameters
    ----------
    stem : str
        Stem name (mid_bass, lead, neuro, riddim, arps, sub_bass, supersaw).
    style : str
        Style filter (dubstep, riddim, melodic, heavy).  Empty = any.
    section : str
        Section filter (intro, build, drop, breakdown, outro).  Empty = any.
    energy_min, energy_max : float
        Energy range filter.
    tags : list[str] | None
        If specified, prefer patterns that have any of these tags.

    Returns patterns sorted by relevance (best first).
    """
    candidates = _BY_STEM.get(stem, [])
    if not candidates:
        # Fall back to any stem if exact match fails
        candidates = ALL_PATTERNS

    scored: list[tuple[float, MidiPattern]] = []
    for p in candidates:
        score = 0.0
        # Stem exact match is mandatory (already filtered above)
        if p.stem != stem:
            score -= 10.0

        # Style match
        if style and p.style == style:
            score += 3.0
        elif style and p.style != style:
            score -= 1.0

        # Section match
        if section:
            if p.section == section:
                score += 2.0
            elif p.section == "drop" and section in ("expand", "drop_2"):
                score += 1.5
            elif p.section == "build" and section in ("intro", "breakdown"):
                score += 0.5

        # Energy range
        if energy_min <= p.energy <= energy_max:
            score += 1.0
        else:
            score -= abs(p.energy - (energy_min + energy_max) / 2) * 2

        # Tag overlap
        if tags:
            overlap = len(set(tags) & set(p.tags))
            score += overlap * 0.5

        scored.append((score, p))

    scored.sort(key=lambda x: x[0], reverse=True)
    return [p for _, p in scored]


def pick_pattern(
    stem: str,
    *,
    style: str = "",
    section: str = "",
    energy: float = 0.8,
    tags: list[str] | None = None,
    seed: int | None = None,
) -> MidiPattern | None:
    """Pick the best matching pattern, with seeded randomness for variety.

    Returns the top-scored pattern, with a small chance of picking the
    2nd or 3rd best for variation.
    """
    results = query_patterns(
        stem,
        style=style,
        section=section,
        energy_min=max(0.0, energy - 0.3),
        energy_max=min(1.0, energy + 0.3),
        tags=tags,
    )
    if not results:
        return None
    if len(results) == 1:
        return results[0]
    # Seeded variety — 60% best, 30% second, 10% third
    rng = random.Random(seed)
    roll = rng.random()
    if roll < 0.6:
        return results[0]
    elif roll < 0.9 and len(results) > 1:
        return results[1]
    elif len(results) > 2:
        return results[2]
    return results[0]


def pattern_to_notes(
    pattern: MidiPattern,
    scale_notes: list[int],
    offset: float,
    bars: int,
    root_midi: int,
    vel_base: int = 100,
) -> list[tuple[int, float, float, int]]:
    """Convert a MidiPattern to absolute (pitch, time, duration, velocity) tuples.

    Parameters
    ----------
    pattern : MidiPattern
        The pattern to expand.
    scale_notes : list[int]
        MIDI notes in the scale (from _get_scale_midi_notes).
    offset : float
        Beat offset for this section.
    bars : int
        How many bars to fill.
    root_midi : int
        Root MIDI note for degree-0.
    vel_base : int
        Base velocity (0–127).

    Returns list of (pitch, time, duration, velocity) tuples.
    """
    notes: list[tuple[int, float, float, int]] = []
    n_bar_patterns = len(pattern.bars) if pattern.bars else 1

    for bar in range(bars):
        bar_pattern = pattern.bars[bar % n_bar_patterns] if pattern.bars else []
        for degree, beat_pos, dur, vel_norm in bar_pattern:
            if degree < 0:  # rest
                continue
            # Map scale degree to MIDI pitch
            if scale_notes:
                pitch = scale_notes[int(degree) % len(scale_notes)]
            else:
                pitch = root_midi + degree * 2  # rough fallback
            abs_time = offset + bar * 4.0 + float(beat_pos)
            velocity = min(127, max(1, int(vel_norm * vel_base)))
            notes.append((pitch, abs_time, float(dur), velocity))

    return notes
