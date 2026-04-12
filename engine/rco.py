"""RCO — Resonance Curve Oscillator.

Energy-curve presets modelled on Subtronics-style arrangements.
Each preset defines section energies that map to the canonical
9-scene session template (112 bars @ 150 BPM default).
"""

from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np


@dataclass
class RCOProfile:
    """A named energy profile describing per-section dynamics."""

    name: str
    bpm: float
    sections: list[dict] = field(default_factory=list)


# ── preset builders ─────────────────────────────────────────────

_WEAPON_SECTIONS = [
    {"name": "INTRO", "bars": 8, "energy": 0.20},
    {"name": "BUILD 1", "bars": 16, "energy": 0.55},
    {"name": "DROP 1", "bars": 16, "energy": 1.00},
    {"name": "BREAKDOWN", "bars": 8, "energy": 0.30},
    {"name": "BUILD 2", "bars": 16, "energy": 0.65},
    {"name": "DROP 2", "bars": 16, "energy": 1.00},
    {"name": "BRIDGE", "bars": 8, "energy": 0.40},
    {"name": "FINAL DROP", "bars": 16, "energy": 0.95},
    {"name": "OUTRO", "bars": 8, "energy": 0.15},
]

_EMOTIVE_SECTIONS = [
    {"name": "INTRO", "bars": 8, "energy": 0.15},
    {"name": "BUILD 1", "bars": 16, "energy": 0.40},
    {"name": "DROP 1", "bars": 16, "energy": 0.80},
    {"name": "BREAKDOWN", "bars": 8, "energy": 0.25},
    {"name": "BUILD 2", "bars": 16, "energy": 0.50},
    {"name": "DROP 2", "bars": 16, "energy": 0.85},
    {"name": "BRIDGE", "bars": 8, "energy": 0.35},
    {"name": "FINAL DROP", "bars": 16, "energy": 0.75},
    {"name": "OUTRO", "bars": 8, "energy": 0.10},
]

_HYBRID_SECTIONS = [
    {"name": "INTRO", "bars": 8, "energy": 0.25},
    {"name": "BUILD 1", "bars": 16, "energy": 0.50},
    {"name": "DROP 1", "bars": 16, "energy": 0.95},
    {"name": "BREAKDOWN", "bars": 8, "energy": 0.20},
    {"name": "BUILD 2", "bars": 16, "energy": 0.60},
    {"name": "DROP 2", "bars": 16, "energy": 0.90},
    {"name": "BRIDGE", "bars": 8, "energy": 0.45},
    {"name": "FINAL DROP", "bars": 16, "energy": 1.00},
    {"name": "OUTRO", "bars": 8, "energy": 0.12},
]


def subtronics_weapon_preset(bpm: float = 150) -> RCOProfile:
    return RCOProfile(name="Weapon", bpm=bpm, sections=list(_WEAPON_SECTIONS))


def subtronics_emotive_preset(bpm: float = 150) -> RCOProfile:
    return RCOProfile(name="Emotive", bpm=bpm, sections=list(_EMOTIVE_SECTIONS))


def subtronics_hybrid_preset(bpm: float = 150) -> RCOProfile:
    return RCOProfile(name="Hybrid", bpm=bpm, sections=list(_HYBRID_SECTIONS))


# ── energy-curve generator ──────────────────────────────────────

def generate_energy_curve(
    profile: RCOProfile,
    resolution_per_bar: int = 4,
) -> dict:
    """Expand an RCO profile into a time-domain energy curve.

    Returns dict with keys:
        total_bars, total_duration_s, time_s, energy
    """
    bpm = profile.bpm or 150
    seconds_per_bar = (4 * 60) / bpm  # 4 beats per bar
    total_bars = sum(s["bars"] for s in profile.sections)
    total_duration = total_bars * seconds_per_bar

    time_s: list[float] = []
    energy: list[float] = []
    current_bar = 0

    for sec in profile.sections:
        bars = sec["bars"]
        e = sec["energy"]
        samples = bars * resolution_per_bar
        for i in range(samples):
            bar_offset = current_bar + i / resolution_per_bar
            t = bar_offset * seconds_per_bar
            time_s.append(t)
            energy.append(e)
        current_bar += bars

    return {
        "total_bars": total_bars,
        "total_duration_s": total_duration,
        "time_s": time_s,
        "energy": energy,
    }
