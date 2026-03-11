"""
DUBFORGE — Rhythm Engine

Centralised drum-pattern generation for every section of a track.
Replaces the hardcoded per-bar kick/snare/hat placement in forge.py
with parameterised, groove-aware pattern objects.

Usage in forge.py
-----------------
    from engine.rhythm_engine import RhythmEngine, RhythmDNA

    rdna = RhythmEngine.from_drum_dna(dna.drums, bpm=bpm)
    # or build RhythmDNA manually

    for bar in range(DROP1):
        events = rdna.drop_bar(bar, total_bars=DROP1, intensity=1)
        for ev in events:
            # ev.instrument  — "kick" | "snare" | "clap" | "hat_c" | "hat_o"
            # ev.beat        — beat position within bar  (0-indexed float)
            # ev.gain        — 0.0–1.0
            # ev.pan         — -1.0 (L) … +1.0 (R)
            mix_sound(ev, bar_offset, sounds)
"""

from __future__ import annotations

import random
from dataclasses import dataclass, field
from typing import Literal

from engine.groove import (
    GrooveEngine,
    GrooveTemplate,
    GROOVE_TEMPLATES,
    NoteEvent,
)

# ─── Constants ────────────────────────────────────────────────────────
from engine.config_loader import PHI
SR = 48_000

InstrumentName = Literal["kick", "snare", "clap", "hat_c", "hat_o", "ride"]


# ─── Data Structures ─────────────────────────────────────────────────

@dataclass
class DrumEvent:
    """One drum hit in a bar.  ``beat`` is 0-indexed (0 = bar start)."""
    instrument: InstrumentName
    beat: float
    gain: float = 0.70
    pan: float = 0.0

    def samples_offset(self, beat_dur_s: float, sr: int = SR) -> int:
        """Convert beat position to sample offset."""
        return int(self.beat * beat_dur_s * sr)


@dataclass
class KickPattern:
    """Positions within a 4-beat bar where the kick hits."""
    name: str
    beats: list[float] = field(default_factory=lambda: [0.0])
    velocities: list[float] | None = None  # per-hit, else uniform

    def events(self, gain: float = 0.75) -> list[DrumEvent]:
        out: list[DrumEvent] = []
        vels = self.velocities or [1.0] * len(self.beats)
        for b, v in zip(self.beats, vels):
            out.append(DrumEvent("kick", b, gain * v))
        return out


@dataclass
class SnarePattern:
    """Positions within a 4-beat bar where the snare hits."""
    name: str
    beats: list[float] = field(default_factory=lambda: [2.0])
    velocities: list[float] | None = None

    def events(self, gain: float = 0.65) -> list[DrumEvent]:
        out: list[DrumEvent] = []
        vels = self.velocities or [1.0] * len(self.beats)
        for b, v in zip(self.beats, vels):
            out.append(DrumEvent("snare", b, gain * v))
        return out


@dataclass
class FillPattern:
    """A drum fill (replaces last beat or two of a phrase-end bar)."""
    name: str
    snare_beats: list[float] = field(default_factory=list)
    hat_beats: list[float] = field(default_factory=list)
    base_gain: float = 0.40
    crescendo: float = 0.04  # gain increase per hit

    def events(self) -> list[DrumEvent]:
        out: list[DrumEvent] = []
        for i, b in enumerate(self.snare_beats):
            g = min(self.base_gain + self.crescendo * i, 0.85)
            out.append(DrumEvent("snare", b, g))
        for i, b in enumerate(self.hat_beats):
            pan = -0.35 + 0.70 * (i / max(len(self.hat_beats) - 1, 1))
            out.append(DrumEvent("hat_c", b, 0.30, pan))
        return out


# ─── Pattern Library ─────────────────────────────────────────────────

KICK_PATTERNS: dict[str, KickPattern] = {
    # Standard dubstep half-time: kick on beat 1 only
    "halftime": KickPattern("halftime", [0.0]),
    # Kick on 1 + ghost on "and of 2" (syncopation)
    "halftime_synco": KickPattern(
        "halftime_synco", [0.0, 1.5], [1.0, 0.55]),
    # Double kick: 1 and 3
    "double": KickPattern("double", [0.0, 2.0]),
    # Four-on-the-floor (house / DnB crossover)
    "four_floor": KickPattern(
        "four_floor", [0.0, 1.0, 2.0, 3.0], [1.0, 0.8, 0.9, 0.75]),
    # Sparse: kick on 1 only, lower velocity
    "sparse": KickPattern("sparse", [0.0], [0.85]),
    # Offbeat syncopation
    "offbeat": KickPattern(
        "offbeat", [0.0, 0.75, 2.5], [1.0, 0.5, 0.6]),
}

SNARE_PATTERNS: dict[str, SnarePattern] = {
    # Standard: snare on beat 3 (half-time feel)
    "halftime": SnarePattern("halftime", [2.0]),
    # Backbeat: snare on 2 and 4
    "backbeat": SnarePattern("backbeat", [1.0, 3.0], [0.9, 1.0]),
    # Ghost notes around the main hit
    "ghosted": SnarePattern(
        "ghosted", [1.75, 2.0, 2.75], [0.3, 1.0, 0.25]),
    # Sparse / breakdown
    "sparse": SnarePattern("sparse", [2.0], [0.7]),
}

FILL_PATTERNS: dict[str, FillPattern] = {
    # Classic dubstep: accelerating snares into beat 4
    "classic": FillPattern(
        "classic",
        snare_beats=[2.0, 2.5, 2.75, 3.0, 3.25, 3.5, 3.75],
        hat_beats=[2.0, 2.5, 3.0, 3.5],
        base_gain=0.38,
        crescendo=0.05,
    ),
    # Short fill: just the last beat
    "short": FillPattern(
        "short",
        snare_beats=[3.0, 3.25, 3.5, 3.75],
        hat_beats=[3.0, 3.5],
        base_gain=0.40,
        crescendo=0.06,
    ),
    # Rapid 16th triplet fill
    "triplet": FillPattern(
        "triplet",
        snare_beats=[2.0, 2.333, 2.667, 3.0, 3.167, 3.333, 3.5, 3.667, 3.833],
        hat_beats=[],
        base_gain=0.35,
        crescendo=0.04,
    ),
    # Dramatic: empty space then burst
    "dramatic": FillPattern(
        "dramatic",
        snare_beats=[3.0, 3.125, 3.25, 3.375, 3.5, 3.625, 3.75, 3.875],
        hat_beats=[3.0, 3.25, 3.5, 3.75],
        base_gain=0.35,
        crescendo=0.06,
    ),
}


# ─── Rhythm DNA (extends DrumDNA with pattern choices) ───────────────

@dataclass
class RhythmDNA:
    """All rhythmic decisions for a song — pattern selection + groove.

    Timbre is still in DrumDNA; this controls *placement & feel*.
    """
    # Pattern selections (keys into the library dicts)
    kick_pattern: str = "halftime"
    snare_pattern: str = "halftime"
    fill_pattern: str = "classic"

    # Groove
    groove_template: str = "dubstep_halftime"
    swing_amount: float = 0.0      # 0–100
    humanize_timing_ms: float = 5.0
    humanize_velocity_pct: float = 8.0

    # Hat config
    hat_density: int = 16          # 8, 12, 16 steps per bar
    hat_open_beats: list[float] = field(
        default_factory=lambda: [1.5, 3.5])
    hat_open_gain: float = 0.30
    hat_closed_gain: float = 0.40

    # Section gain profiles (base values, caller may scale)
    gain_kick: float = 0.75
    gain_snare: float = 0.65
    gain_clap: float = 0.28
    gain_hat_c: float = 0.40
    gain_hat_o: float = 0.30

    # Hat panning
    hat_pan_width: float = 0.40    # ±width across bar
    hat_open_pan: float = 0.30     # pan magnitude for open hats

    # Fill frequency: fill on every Nth bar (4 = phrase boundary)
    fill_every: int = 4

    # Variation: how much to vary between bars (0 = robotic, 1 = loose)
    variation: float = 0.3

    # Kick ghost probability on non-pattern beats
    kick_ghost_prob: float = 0.0

    # Drop 2 intensity boost (multiplied on gains)
    drop2_boost: float = 1.05


# ─── Rhythm Engine ───────────────────────────────────────────────────

class RhythmEngine:
    """Generate per-bar drum event lists for any song section."""

    def __init__(self, rdna: RhythmDNA, bpm: float = 140,
                 seed: int = 42):
        self.rdna = rdna
        self.bpm = bpm
        self.beat_dur = 60.0 / bpm           # seconds per beat
        self.bar_dur = self.beat_dur * 4      # seconds per bar (4/4)
        self.groove = GrooveEngine(bpm=bpm, sample_rate=SR)
        self.rng = random.Random(seed)

        # Resolve patterns from library
        self._kick = KICK_PATTERNS.get(rdna.kick_pattern,
                                       KICK_PATTERNS["halftime"])
        self._snare = SNARE_PATTERNS.get(rdna.snare_pattern,
                                         SNARE_PATTERNS["halftime"])
        self._fill = FILL_PATTERNS.get(rdna.fill_pattern,
                                       FILL_PATTERNS["classic"])
        self._groove_tmpl = GROOVE_TEMPLATES.get(
            rdna.groove_template,
            GROOVE_TEMPLATES["dubstep_halftime"])

    # ── Class helpers ─────────────────────────────────────────────

    @classmethod
    def from_drum_dna(cls, drum_dna, bpm: float = 140,
                      energy: float = 0.7,
                      seed: int = 42) -> "RhythmEngine":
        """Build RhythmDNA from an existing DrumDNA + energy level."""
        rng = random.Random(seed)

        # Pick kick pattern based on energy
        if energy > 0.85:
            kick_pat = rng.choice(["halftime_synco", "double"])
        elif energy > 0.6:
            kick_pat = rng.choice(["halftime", "halftime_synco"])
        else:
            kick_pat = "halftime"

        # Pick snare pattern
        if energy > 0.8:
            snare_pat = rng.choice(["halftime", "ghosted"])
        else:
            snare_pat = "halftime"

        # Pick fill
        if energy > 0.85:
            fill_pat = rng.choice(["classic", "dramatic"])
        elif energy > 0.5:
            fill_pat = "classic"
        else:
            fill_pat = "short"

        # Groove template
        groove = rng.choice(["dubstep_halftime", "riddim_bounce"])

        hat_dens = getattr(drum_dna, "hat_density", 16)

        rdna = RhythmDNA(
            kick_pattern=kick_pat,
            snare_pattern=snare_pat,
            fill_pattern=fill_pat,
            groove_template=groove,
            swing_amount=rng.uniform(0, 15),
            humanize_timing_ms=3.0 + energy * 5.0,
            humanize_velocity_pct=5.0 + energy * 5.0,
            hat_density=hat_dens,
            hat_open_beats=[1.5, 3.5],
            hat_open_gain=0.28 + energy * 0.08,
            hat_closed_gain=0.35 + energy * 0.10,
            gain_kick=0.70 + energy * 0.08,
            gain_snare=0.58 + energy * 0.10,
            gain_clap=0.22 + energy * 0.08,
            gain_hat_c=0.35 + energy * 0.10,
            gain_hat_o=0.25 + energy * 0.10,
            hat_pan_width=0.30 + energy * 0.15,
            hat_open_pan=0.25 + energy * 0.10,
            fill_every=4,
            variation=0.2 + energy * 0.2,
            kick_ghost_prob=max(0.0, (energy - 0.7) * 0.3),
            drop2_boost=1.03 + energy * 0.04,
        )
        return cls(rdna, bpm=bpm, seed=seed)

    # ── Hat pattern (groove-aware) ────────────────────────────────

    def _make_hat_bar(self) -> list[DrumEvent]:
        """Build one bar of closed hats with groove + humanization."""
        rd = self.rdna
        events: list[NoteEvent] = []

        for i in range(rd.hat_density):
            beat_pos = i * (4.0 / rd.hat_density)
            # Accent every 4th step, ghost on offbeats
            vel = 0.65 + 0.25 * ((i % 4) == 0)
            if i % 4 == 2:
                vel *= 0.65  # ghost offbeat
            events.append(NoteEvent(
                time=beat_pos * self.beat_dur,
                duration=0.025,
                pitch=42,
                velocity=vel,
            ))

        # Apply groove template + humanize
        events = self.groove.apply_groove(events, self._groove_tmpl)
        events = self.groove.humanize(
            events,
            timing_ms=rd.humanize_timing_ms,
            velocity_pct=rd.humanize_velocity_pct,
        )

        # Convert to DrumEvents
        out: list[DrumEvent] = []
        for ev in events:
            beat = ev.time / self.beat_dur
            pan = -rd.hat_pan_width + 2 * rd.hat_pan_width * (beat / 4.0)
            out.append(DrumEvent(
                "hat_c", beat,
                rd.gain_hat_c * ev.velocity,
                pan,
            ))
        return out

    def _make_open_hats(self) -> list[DrumEvent]:
        """Open hat events for a bar."""
        rd = self.rdna
        out: list[DrumEvent] = []
        for i, b in enumerate(rd.hat_open_beats):
            sign = 1.0 if i % 2 == 0 else -1.0
            out.append(DrumEvent(
                "hat_o", b,
                rd.gain_hat_o,
                sign * rd.hat_open_pan,
            ))
        return out

    # ── Core bar generators ───────────────────────────────────────

    def _kick_events(self, gain_mult: float = 1.0) -> list[DrumEvent]:
        evs = self._kick.events(self.rdna.gain_kick * gain_mult)
        # Optional ghost kick
        if self.rdna.kick_ghost_prob > 0 and self.rng.random() < self.rdna.kick_ghost_prob:
            ghost_beat = self.rng.choice([0.75, 1.5, 2.5, 3.5])
            # Avoid doubling a main hit
            main_beats = set(round(e.beat, 2) for e in evs)
            if round(ghost_beat, 2) not in main_beats:
                evs.append(DrumEvent("kick", ghost_beat,
                                     self.rdna.gain_kick * 0.35 * gain_mult))
        return evs

    def _snare_events(self, gain_mult: float = 1.0) -> list[DrumEvent]:
        return self._snare.events(self.rdna.gain_snare * gain_mult)

    def _clap_events(self, gain_mult: float = 1.0) -> list[DrumEvent]:
        """Clap layered on the main snare hit(s)."""
        snare_beats = self._snare.beats
        return [DrumEvent("clap", b, self.rdna.gain_clap * gain_mult)
                for b in snare_beats[:1]]  # only on first snare hit

    def _fill_events(self) -> list[DrumEvent]:
        return self._fill.events()

    # ── Section generators ────────────────────────────────────────

    def intro_bar(self, bar: int, total_bars: int = 8) -> list[DrumEvent]:
        """Intro: gradual element introduction."""
        events: list[DrumEvent] = []
        progress = bar / max(total_bars - 1, 1)

        # Kick enters at ~50% through intro
        if bar >= total_bars // 2:
            kick_prog = (bar - total_bars // 2) / max(total_bars // 2, 1)
            gain = 0.15 + 0.35 * kick_prog
            events.extend(self._kick_events(gain / self.rdna.gain_kick))

        # Hats enter at ~75% through intro
        if bar >= int(total_bars * 0.75):
            hat_prog = (bar - int(total_bars * 0.75)) / max(
                total_bars - int(total_bars * 0.75), 1)
            hat_events = self._make_hat_bar()
            for ev in hat_events:
                ev.gain *= 0.3 + 0.5 * hat_prog
            events.extend(hat_events)

            # Open hats on even bars
            if bar % 2 == 0:
                oh = self._make_open_hats()
                for ev in oh:
                    ev.gain *= 0.3 + 0.3 * hat_prog
                events.extend(oh)

        return events

    def build_bar(self, bar: int, total_bars: int = 4,
                  is_build2: bool = False) -> list[DrumEvent]:
        """Build section: kick + accelerating snare roll."""
        events: list[DrumEvent] = []
        progress = bar / max(total_bars - 1, 1)

        # Kick on 1 and 3, ramping
        k_gain = (0.40 if is_build2 else 0.35) + 0.15 * progress
        events.append(DrumEvent("kick", 0.0, k_gain))
        events.append(DrumEvent("kick", 2.0, k_gain))

        # Progressive snare roll: divisions increase each bar
        if is_build2:
            divs_seq = [2, 4, 8, 8, 16, 16, 16, 16]
        else:
            divs_seq = [2, 4, 4, 8, 8, 16, 16, 16]

        divs = divs_seq[min(bar, len(divs_seq) - 1)]
        step = 4.0 / divs

        for h in range(divs):
            vel = 0.15 + 0.45 * progress * (h / max(divs - 1, 1))
            pan = -0.25 + 0.50 * ((h % 6) / 5)
            events.append(DrumEvent("snare", h * step, vel, pan))

        return events

    def drop_bar(self, bar: int, total_bars: int = 16,
                 intensity: int = 1) -> list[DrumEvent]:
        """Drop section bar.

        Args:
            bar: Current bar index (0-based).
            total_bars: Total bars in this drop.
            intensity: 1 = Drop 1, 2 = Drop 2 (slightly boosted).
        """
        events: list[DrumEvent] = []
        rd = self.rdna
        boost = rd.drop2_boost if intensity >= 2 else 1.0

        # Is this a fill bar?  (every Nth bar, on the last bar of each phrase)
        is_fill_bar = (rd.fill_every > 0
                       and bar % rd.fill_every == rd.fill_every - 1
                       and bar > 0)

        # -- Kick --
        events.extend(self._kick_events(boost))

        # -- Snare + Clap --
        events.extend(self._snare_events(boost))
        events.extend(self._clap_events(boost))

        # -- Closed hats --
        hat_events = self._make_hat_bar()
        for ev in hat_events:
            ev.gain *= boost
        events.extend(hat_events)

        # -- Open hats --
        oh = self._make_open_hats()
        for ev in oh:
            ev.gain *= boost
        events.extend(oh)

        # -- Fill (replaces last part of bar) --
        if is_fill_bar:
            fill_evs = self._fill_events()
            for ev in fill_evs:
                ev.gain *= boost
            events.extend(fill_evs)

        # -- Per-bar micro-variation --
        if rd.variation > 0 and self.rng.random() < rd.variation:
            self._apply_micro_variation(events, bar)

        return events

    def breakdown_bar(self, bar: int, total_bars: int = 8) -> list[DrumEvent]:
        """Breakdown: very sparse, atmospheric."""
        events: list[DrumEvent] = []
        # Quiet quarter-note closed hats
        for q in range(4):
            pan = -0.20 + 0.40 * (q / 3)
            events.append(DrumEvent("hat_c", float(q), 0.05, pan))
        return events

    def outro_bar(self, bar: int, total_bars: int = 8) -> list[DrumEvent]:
        """Outro: decaying drums."""
        events: list[DrumEvent] = []
        decay = max(0.05, 1.0 - bar / max(total_bars - 1, 1))

        # Kick decays
        k_gain = self.rdna.gain_kick * 0.85 * decay
        events.append(DrumEvent("kick", 0.0, k_gain))

        # Hats decay
        hat_events = self._make_hat_bar()
        for ev in hat_events:
            ev.gain *= 0.35 * decay
        events.extend(hat_events)

        return events

    # ── Micro-variation ──────────────────────────────────────────

    def _apply_micro_variation(self, events: list[DrumEvent],
                               bar: int) -> None:
        """Subtle per-bar variation to avoid robotic repetition.

        Modifies events in-place.  Never removes the kick on beat 1
        or the main snare hit.
        """
        for ev in events:
            # Skip fundamental hits
            if ev.instrument == "kick" and ev.beat < 0.1:
                continue
            if ev.instrument == "snare" and 1.9 < ev.beat < 2.1:
                continue

            # Velocity wiggle ±8 %
            wiggle = self.rng.gauss(0, 0.04)
            ev.gain = max(0.02, min(0.95, ev.gain + wiggle))

            # Occasional hat skip (empty space = groove)
            if ev.instrument == "hat_c" and self.rng.random() < 0.08:
                ev.gain *= 0.15  # near-silent = perceived gap

    # ── Utility ──────────────────────────────────────────────────

    def section_events(self, section: str, bar: int,
                       total_bars: int,
                       **kwargs) -> list[DrumEvent]:
        """Dispatch to the right generator by section name."""
        dispatch = {
            "intro": self.intro_bar,
            "verse": self.intro_bar,
            "build": lambda b, t, **kw: self.build_bar(b, t, is_build2=False),
            "build2": lambda b, t, **kw: self.build_bar(b, t, is_build2=True),
            "drop1": lambda b, t, **kw: self.drop_bar(b, t, intensity=1),
            "drop2": lambda b, t, **kw: self.drop_bar(b, t, intensity=2),
            "break": self.breakdown_bar,
            "breakdown": self.breakdown_bar,
            "outro": self.outro_bar,
        }
        gen = dispatch.get(section, self.drop_bar)
        return gen(bar, total_bars, **kwargs)

    def describe(self) -> str:
        """Human-readable summary for logs."""
        rd = self.rdna
        return (
            f"Rhythm: kick={rd.kick_pattern} snare={rd.snare_pattern} "
            f"fill={rd.fill_pattern} | groove={rd.groove_template} "
            f"swing={rd.swing_amount:.0f}% humanize={rd.humanize_timing_ms:.0f}ms "
            f"| hats={rd.hat_density}/bar variation={rd.variation:.0%}"
        )


# ─── Standalone test ──────────────────────────────────────────────────

def main() -> None:
    print("=== DUBFORGE Rhythm Engine ===\n")

    rdna = RhythmDNA()
    eng = RhythmEngine(rdna, bpm=150)
    print(eng.describe())
    print()

    for section, bars in [("intro", 8), ("build", 4),
                          ("drop1", 8), ("break", 8),
                          ("build2", 4), ("drop2", 8),
                          ("outro", 8)]:
        total_events = 0
        for b in range(bars):
            evs = eng.section_events(section, b, bars)
            total_events += len(evs)
        print(f"  {section:10s}: {bars} bars → {total_events} events")

    # Detail: show one drop bar
    print("\n  Drop 1 bar 0:")
    for ev in eng.drop_bar(0, 16, intensity=1):
        print(f"    {ev.instrument:6s} beat={ev.beat:5.2f}  "
              f"gain={ev.gain:.3f}  pan={ev.pan:+.2f}")

    print("\n  Drop 1 bar 3 (fill):")
    for ev in eng.drop_bar(3, 16, intensity=1):
        print(f"    {ev.instrument:6s} beat={ev.beat:5.2f}  "
              f"gain={ev.gain:.3f}  pan={ev.pan:+.2f}")


if __name__ == "__main__":
    main()
