"""
DUBFORGE Engine — Trance Arp Engine

Fibonacci-timed arpeggiator with phi-ratio gate times.
Generates MIDI-like note sequences and can render audio previews.

Based on TRANCE_ARP_ENGINE specs from Serum 2 Module Pack v1.
"""

import json
import numpy as np
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Optional
from engine.config_loader import PHI, FIBONACCI, get_config_value


@dataclass
class ArpNote:
    """Single arp step."""
    step: int
    semitone_offset: int
    velocity: int = 100
    gate_percent: float = 61.8  # phi percentage
    duration_beats: float = 0.25  # 1/16th


@dataclass
class ArpPattern:
    """Complete arp pattern."""
    name: str
    steps: int = 13  # Fibonacci
    direction: str = "up_down"
    octave_range: int = 3
    rate: str = "1/16"
    notes: list = field(default_factory=list)


# --- Config-driven defaults -----------------------------------------------

def _arp_config_defaults() -> dict:
    """Load arp defaults from serum2_module_pack_v1.yaml if available."""
    try:
        return {
            "gate_percent": get_config_value(
                "serum2_module_pack_v1", "TRANCE_ARP_ENGINE", "gate_percent",
                default=61.8),
            "steps": get_config_value(
                "serum2_module_pack_v1", "TRANCE_ARP_ENGINE", "pattern", "steps",
                default=13),
            "rate": get_config_value(
                "serum2_module_pack_v1", "TRANCE_ARP_ENGINE", "rate",
                default="1/16"),
            "direction": get_config_value(
                "serum2_module_pack_v1", "TRANCE_ARP_ENGINE", "direction",
                default="up_down"),
            "octave_range": get_config_value(
                "serum2_module_pack_v1", "TRANCE_ARP_ENGINE", "octave_range",
                default=3),
        }
    except FileNotFoundError:
        return {
            "gate_percent": 61.8,
            "steps": 13,
            "rate": "1/16",
            "direction": "up_down",
            "octave_range": 3,
        }


# --- Pattern Generators ---------------------------------------------------

def fibonacci_rise_pattern(root_semitone: int = 0) -> ArpPattern:
    """
    FIBONACCI_RISE: notes at Fibonacci semitone offsets.
    Pattern length = 13 steps (Fibonacci).
    """
    # Fibonacci semitone sequence
    fib_semitones = [0, 0, 2, 3, 5, 8, 0, 5, 3, 2, 0, 0, -5]
    accent_indices = {0, 1, 2, 4, 7, 12}  # Fibonacci-1 indices

    notes = []
    for i, st in enumerate(fib_semitones):
        vel = 127 if i in accent_indices else 80
        notes.append(ArpNote(
            step=i,
            semitone_offset=root_semitone + st,
            velocity=vel,
            gate_percent=61.8,
            duration_beats=0.25,
        ))

    return ArpPattern(
        name="FIBONACCI_RISE",
        steps=13,
        direction="up_down",
        octave_range=3,
        rate="1/16",
        notes=notes,
    )


def phi_spiral_pattern(root_semitone: int = 0) -> ArpPattern:
    """
    PHI_SPIRAL: notes spiral outward by phi-derived intervals.
    """
    steps = 21  # Fibonacci
    notes = []
    for i in range(steps):
        # Interval derived from phi
        interval = round(PHI * (i % 8)) % 12
        direction = 1 if i % 2 == 0 else -1
        st = root_semitone + (interval * direction)
        vel = 127 if i in {0, 1, 2, 4, 7, 12, 20} else 90
        notes.append(ArpNote(
            step=i,
            semitone_offset=st,
            velocity=vel,
            gate_percent=61.8,
            duration_beats=0.25,
        ))

    return ArpPattern(
        name="PHI_SPIRAL",
        steps=steps,
        direction="up_down",
        octave_range=3,
        rate="1/16",
        notes=notes,
    )


def golden_gate_pattern(root_semitone: int = 0) -> ArpPattern:
    """
    GOLDEN_GATE: all notes on root but gate lengths follow Fibonacci.
    Creates rhythmic interest through timing, not pitch.
    """
    fib_gates = [1, 1, 2, 3, 5, 8, 5, 3, 2, 1, 1, 2, 3]
    max_gate = max(fib_gates)
    notes = []
    for i, g in enumerate(fib_gates):
        gate_pct = (g / max_gate) * 100
        notes.append(ArpNote(
            step=i,
            semitone_offset=root_semitone,
            velocity=80 + int(gate_pct * 0.47),
            gate_percent=gate_pct,
            duration_beats=0.25 * (g / max_gate + 0.5),
        ))

    return ArpPattern(
        name="GOLDEN_GATE",
        steps=13,
        direction="forward",
        octave_range=1,
        rate="1/16",
        notes=notes,
    )


# --- MIDI-like Export -----------------------------------------------------

def pattern_to_midi_data(pattern: ArpPattern, bpm: float = 150.0,
                          root_note: int = 60) -> list[dict]:
    """
    Convert pattern to MIDI-like event list.
    Returns list of {note, velocity, start_beat, duration_beat} dicts.
    """
    events = []
    beat_pos = 0.0
    for note in pattern.notes:
        midi_note = root_note + note.semitone_offset
        # Clamp to valid MIDI range
        midi_note = max(0, min(127, midi_note))
        duration = note.duration_beats * (note.gate_percent / 100.0)
        events.append({
            "note": midi_note,
            "velocity": note.velocity,
            "start_beat": round(beat_pos, 4),
            "duration_beat": round(duration, 4),
        })
        beat_pos += note.duration_beats
    return events


# --- Export ----------------------------------------------------------------

def export_pattern(pattern: ArpPattern, out_dir: str = "output/analysis"):
    """Export an arp pattern to JSON."""
    path = Path(out_dir)
    path.mkdir(parents=True, exist_ok=True)
    data = asdict(pattern)
    data["midi_events"] = pattern_to_midi_data(pattern)

    json_path = path / f"arp_{pattern.name.lower()}.json"
    with open(json_path, 'w') as f:
        json.dump(data, f, indent=2)
    print(f"Arp pattern: {json_path}")


# --- Main -----------------------------------------------------------------

def main() -> None:
    patterns = [
        fibonacci_rise_pattern(),
        phi_spiral_pattern(),
        golden_gate_pattern(),
    ]

    for p in patterns:
        export_pattern(p)

    print("Trance Arp Engine complete.")


if __name__ == '__main__':
    main()
