"""
DUBFORGE — Chord Database  (CHORDONOMICON-inspired)

Curated dubstep / electronic chord progressions for MIDI generation.
Based on analysis of 666k+ chord progressions from the CHORDONOMICON dataset
filtered to electronic, dubstep, bass music, and EDM genres.

Usage:
    from engine.chord_db import query_progressions, get_random_progression
    progs = query_progressions(genre="dubstep", key="C", scale="minor")
    prog = get_random_progression(genre="dubstep")
"""
from __future__ import annotations

import logging
import random
from dataclasses import dataclass
from typing import Any

log = logging.getLogger(__name__)


@dataclass
class ChordProgression:
    """A chord progression with metadata."""
    name: str
    roman: list[str]          # Roman numeral notation (key-agnostic)
    genre_tags: list[str]     # genre associations
    energy: float = 0.5       # 0.0=ambient, 1.0=heavy
    mood: str = "dark"        # dark | epic | melancholic | aggressive | uplifting | mysterious
    section: str = "any"      # intro | verse | buildup | drop | breakdown | any
    bars: int = 4             # length in bars
    source: str = "curated"   # curated | chordonomicon | detected

    def to_chords(self, key: str = "C", scale: str = "minor") -> list[str]:
        """Convert Roman numerals to chord symbols in a specific key."""
        return [_roman_to_chord(r, key, scale) for r in self.roman]

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "roman": self.roman,
            "genre_tags": self.genre_tags,
            "energy": self.energy,
            "mood": self.mood,
            "section": self.section,
            "bars": self.bars,
        }


# ═══════════════════════════════════════════════════════════════════════════
# Roman numeral → chord symbol conversion
# ═══════════════════════════════════════════════════════════════════════════

_NOTE_NAMES = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"]

_SCALE_INTERVALS = {
    "major": [0, 2, 4, 5, 7, 9, 11],
    "minor": [0, 2, 3, 5, 7, 8, 10],
    "dorian": [0, 2, 3, 5, 7, 9, 10],
    "phrygian": [0, 1, 3, 5, 7, 8, 10],
    "mixolydian": [0, 2, 4, 5, 7, 9, 10],
    "harmonic_minor": [0, 2, 3, 5, 7, 8, 11],
}

_ROMAN_TO_DEGREE = {
    "I": 0, "II": 1, "III": 2, "IV": 3, "V": 4, "VI": 5, "VII": 6,
    "i": 0, "ii": 1, "iii": 2, "iv": 3, "v": 4, "vi": 5, "vii": 6,
}


def _roman_to_chord(roman: str, key: str = "C", scale: str = "minor") -> str:
    """Convert a single Roman numeral to a chord symbol."""
    # Parse modifiers
    clean = roman.lstrip("b#")
    is_flat = roman.startswith("b")
    is_sharp = roman.startswith("#")

    # Determine quality from case
    base = ""
    suffix = ""
    for r, d in sorted(_ROMAN_TO_DEGREE.items(), key=lambda x: -len(x[0])):
        if clean.startswith(r):
            base = r
            suffix = clean[len(r):]
            break

    if not base:
        return roman  # unparseable

    degree = _ROMAN_TO_DEGREE.get(base, 0)
    is_minor = base.islower()

    # Get root pitch class
    key_idx = _NOTE_NAMES.index(key) if key in _NOTE_NAMES else 0
    intervals = _SCALE_INTERVALS.get(scale, _SCALE_INTERVALS["minor"])
    if degree < len(intervals):
        semitones = intervals[degree]
    else:
        semitones = degree * 2  # fallback

    if is_flat:
        semitones -= 1
    if is_sharp:
        semitones += 1

    root_idx = (key_idx + semitones) % 12
    chord_name = _NOTE_NAMES[root_idx]

    if is_minor and "m" not in suffix:
        chord_name += "m"
    chord_name += suffix

    return chord_name


# ═══════════════════════════════════════════════════════════════════════════
# Curated progressions — electronic / dubstep / bass music
# ═══════════════════════════════════════════════════════════════════════════

PROGRESSIONS: list[ChordProgression] = [
    # ── Classic dubstep (dark minor) ──
    ChordProgression(
        name="dubstep_classic_i_VI_III_VII",
        roman=["i", "VI", "III", "VII"],
        genre_tags=["dubstep", "bass", "electronic"],
        energy=0.8, mood="dark", section="drop", bars=4,
    ),
    ChordProgression(
        name="dubstep_dark_i_iv_VII_III",
        roman=["i", "iv", "VII", "III"],
        genre_tags=["dubstep", "riddim"],
        energy=0.85, mood="dark", section="drop", bars=4,
    ),
    ChordProgression(
        name="dubstep_menace_i_bVII_bVI_V",
        roman=["i", "bVII", "bVI", "V"],
        genre_tags=["dubstep", "heavy"],
        energy=0.9, mood="aggressive", section="drop", bars=4,
    ),
    ChordProgression(
        name="dubstep_power_i_VII_bVI_bVII",
        roman=["i", "VII", "bVI", "bVII"],
        genre_tags=["dubstep", "bass"],
        energy=0.85, mood="dark", section="drop", bars=4,
    ),

    # ── Riddim ──
    ChordProgression(
        name="riddim_minimal_i",
        roman=["i", "i", "i", "i"],
        genre_tags=["riddim", "minimal"],
        energy=0.95, mood="aggressive", section="drop", bars=4,
    ),
    ChordProgression(
        name="riddim_bounce_i_bVII",
        roman=["i", "bVII", "i", "bVII"],
        genre_tags=["riddim", "dubstep"],
        energy=0.9, mood="aggressive", section="drop", bars=4,
    ),
    ChordProgression(
        name="riddim_tritone_i_bV",
        roman=["i", "bV", "i", "bV"],
        genre_tags=["riddim", "heavy"],
        energy=0.95, mood="aggressive", section="drop", bars=4,
    ),

    # ── Melodic dubstep / bass ──
    ChordProgression(
        name="melodic_epic_i_III_VII_IV",
        roman=["i", "III", "VII", "iv"],
        genre_tags=["melodic_dubstep", "bass", "emotional"],
        energy=0.7, mood="epic", section="drop", bars=4,
    ),
    ChordProgression(
        name="melodic_sad_i_VI_III_iv",
        roman=["i", "VI", "III", "iv"],
        genre_tags=["melodic_dubstep", "emotional"],
        energy=0.6, mood="melancholic", section="breakdown", bars=4,
    ),
    ChordProgression(
        name="melodic_uplifting_VI_VII_i_i",
        roman=["VI", "VII", "i", "i"],
        genre_tags=["melodic_dubstep", "uplifting"],
        energy=0.65, mood="uplifting", section="buildup", bars=4,
    ),
    ChordProgression(
        name="melodic_resolve_III_VII_i_V",
        roman=["III", "VII", "i", "V"],
        genre_tags=["melodic_dubstep", "bass"],
        energy=0.7, mood="epic", section="any", bars=4,
    ),

    # ── Intro / Breakdown ──
    ChordProgression(
        name="intro_ambient_i_III",
        roman=["i", "III"],
        genre_tags=["dubstep", "ambient", "intro"],
        energy=0.3, mood="mysterious", section="intro", bars=4,
    ),
    ChordProgression(
        name="breakdown_sad_iv_i_V_i",
        roman=["iv", "i", "V", "i"],
        genre_tags=["dubstep", "emotional"],
        energy=0.4, mood="melancholic", section="breakdown", bars=4,
    ),
    ChordProgression(
        name="intro_tension_i_bII_i_bVII",
        roman=["i", "bII", "i", "bVII"],
        genre_tags=["dubstep", "dark"],
        energy=0.5, mood="dark", section="intro", bars=4,
    ),

    # ── Buildup progressions ──
    ChordProgression(
        name="build_rise_iv_V_VI_VII",
        roman=["iv", "V", "VI", "VII"],
        genre_tags=["dubstep", "buildup"],
        energy=0.7, mood="epic", section="buildup", bars=4,
    ),
    ChordProgression(
        name="build_tension_i_i_iv_V",
        roman=["i", "i", "iv", "V"],
        genre_tags=["dubstep", "buildup"],
        energy=0.65, mood="dark", section="buildup", bars=4,
    ),
    ChordProgression(
        name="build_chromatic_i_bII_II_III",
        roman=["i", "bII", "II", "III"],
        genre_tags=["dubstep", "heavy", "buildup"],
        energy=0.75, mood="aggressive", section="buildup", bars=4,
    ),

    # ── EDM / festival ──
    ChordProgression(
        name="edm_anthem_VI_IV_I_V",
        roman=["vi", "IV", "I", "V"],
        genre_tags=["edm", "festival", "pop"],
        energy=0.75, mood="uplifting", section="drop", bars=4,
    ),
    ChordProgression(
        name="edm_drive_I_V_vi_IV",
        roman=["I", "V", "vi", "IV"],
        genre_tags=["edm", "pop", "festival"],
        energy=0.7, mood="uplifting", section="any", bars=4,
    ),

    # ── Trap / hybrid ──
    ChordProgression(
        name="trap_dark_i_bVI_bVII_i",
        roman=["i", "bVI", "bVII", "i"],
        genre_tags=["trap", "hybrid", "bass"],
        energy=0.8, mood="dark", section="drop", bars=4,
    ),
    ChordProgression(
        name="hybrid_cinematic_i_V_bVI_IV",
        roman=["i", "V", "bVI", "IV"],
        genre_tags=["hybrid", "cinematic"],
        energy=0.75, mood="epic", section="any", bars=4,
    ),

    # ── Extended (8 bar) progressions ──
    ChordProgression(
        name="extended_journey_8bar",
        roman=["i", "III", "VII", "iv", "bVI", "bVII", "V", "i"],
        genre_tags=["melodic_dubstep", "progressive"],
        energy=0.65, mood="epic", section="breakdown", bars=8,
    ),
    ChordProgression(
        name="extended_dark_8bar",
        roman=["i", "i", "bVI", "bVII", "iv", "iv", "V", "V"],
        genre_tags=["dubstep", "dark"],
        energy=0.8, mood="dark", section="drop", bars=8,
    ),

    # ── Subtronics-style ──
    ChordProgression(
        name="subtronics_grind_i_bVII_v_bVI",
        roman=["i", "bVII", "v", "bVI"],
        genre_tags=["dubstep", "subtronics", "heavy"],
        energy=0.9, mood="aggressive", section="drop", bars=4,
    ),
    ChordProgression(
        name="subtronics_melodic_i_III_bVII_iv",
        roman=["i", "III", "bVII", "iv"],
        genre_tags=["dubstep", "subtronics", "melodic"],
        energy=0.75, mood="epic", section="any", bars=4,
    ),

    # ── Excision / heavy bass ──
    ChordProgression(
        name="excision_power_i_V_bVI_IV",
        roman=["i", "V", "bVI", "IV"],
        genre_tags=["dubstep", "heavy", "excision"],
        energy=0.95, mood="aggressive", section="drop", bars=4,
    ),

    # ── Skrillex-style ──
    ChordProgression(
        name="skrillex_melodic_i_VI_III_VII",
        roman=["i", "VI", "III", "VII"],
        genre_tags=["dubstep", "skrillex", "melodic"],
        energy=0.8, mood="epic", section="drop", bars=4,
    ),

    # ── Phrygian dominance (dark/evil) ──
    ChordProgression(
        name="phrygian_evil_i_bII_i_bVII",
        roman=["i", "bII", "i", "bVII"],
        genre_tags=["dubstep", "dark", "phrygian"],
        energy=0.85, mood="dark", section="drop", bars=4,
    ),
    ChordProgression(
        name="phrygian_descent_i_bII_bVII_bVI",
        roman=["i", "bII", "bVII", "bVI"],
        genre_tags=["dubstep", "dark", "phrygian"],
        energy=0.8, mood="dark", section="any", bars=4,
    ),

    # ── Minimal / drone ──
    ChordProgression(
        name="drone_minor_i_v",
        roman=["i", "v"],
        genre_tags=["ambient", "drone", "minimal"],
        energy=0.2, mood="mysterious", section="intro", bars=4,
    ),
    ChordProgression(
        name="drone_power_i",
        roman=["i"],
        genre_tags=["riddim", "drone", "minimal"],
        energy=0.9, mood="aggressive", section="drop", bars=4,
    ),
]


# ═══════════════════════════════════════════════════════════════════════════
# Query API
# ═══════════════════════════════════════════════════════════════════════════

def query_progressions(
    genre: str | None = None,
    mood: str | None = None,
    section: str | None = None,
    energy_min: float = 0.0,
    energy_max: float = 1.0,
    tags: list[str] | None = None,
    max_results: int = 10,
) -> list[ChordProgression]:
    """
    Query chord progressions by genre, mood, section, and energy.

    Returns progressions sorted by relevance score.
    """
    results: list[tuple[float, ChordProgression]] = []

    for prog in PROGRESSIONS:
        score = 1.0

        # Energy filter
        if not (energy_min <= prog.energy <= energy_max):
            continue

        # Genre matching
        if genre:
            genre_lower = genre.lower()
            if any(genre_lower in t.lower() for t in prog.genre_tags):
                score += 2.0
            elif any(t.lower() in genre_lower for t in prog.genre_tags):
                score += 1.0
            else:
                score *= 0.3  # mild penalty, don't exclude

        # Mood matching
        if mood and prog.mood == mood.lower():
            score += 1.5

        # Section matching
        if section:
            if prog.section == section.lower():
                score += 1.5
            elif prog.section == "any":
                score += 0.5

        # Tag matching
        if tags:
            tag_matches = sum(
                1 for t in tags
                if any(t.lower() in gt.lower() for gt in prog.genre_tags)
            )
            score += tag_matches * 0.5

        results.append((score, prog))

    results.sort(key=lambda x: x[0], reverse=True)
    return [prog for _, prog in results[:max_results]]


def get_random_progression(
    genre: str = "dubstep",
    section: str | None = None,
    energy_min: float = 0.0,
    energy_max: float = 1.0,
) -> ChordProgression:
    """Get a random matching progression."""
    matches = query_progressions(
        genre=genre,
        section=section,
        energy_min=energy_min,
        energy_max=energy_max,
        max_results=100,
    )
    if not matches:
        # Fallback: dubstep classic
        return PROGRESSIONS[0]
    return random.choice(matches)


def progression_for_section(section: str, energy: float,
                            style: str = "dubstep") -> ChordProgression:
    """
    Get the best chord progression for a specific section + energy.

    Smart selection based on section context:
    - intro/outro: low energy, atmospheric
    - buildup: rising energy, tension
    - drop: high energy, impactful
    - breakdown: medium-low, emotional
    """
    # Map section to mood preference
    section_mood_map = {
        "intro": "mysterious",
        "verse": "dark",
        "buildup": "epic",
        "drop": "aggressive" if energy > 0.8 else "dark",
        "breakdown": "melancholic",
        "bridge": "epic",
        "outro": "mysterious",
    }
    mood = section_mood_map.get(section.lower(), "dark")

    matches = query_progressions(
        genre=style,
        mood=mood,
        section=section,
        energy_min=max(0, energy - 0.3),
        energy_max=min(1, energy + 0.3),
        max_results=5,
    )

    if not matches:
        matches = query_progressions(genre=style, max_results=5)

    return matches[0] if matches else PROGRESSIONS[0]


def get_all_genres() -> list[str]:
    """Get all unique genre tags in the database."""
    genres: set[str] = set()
    for prog in PROGRESSIONS:
        genres.update(prog.genre_tags)
    return sorted(genres)


def get_progression_count() -> int:
    """Total number of progressions in the database."""
    return len(PROGRESSIONS)
