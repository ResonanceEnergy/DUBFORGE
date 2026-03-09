"""
DUBFORGE — Groove Engine  (Session 227)

Groove quantization, swing, shuffle, feel templates.
Apply groove to MIDI-like and audio patterns.
"""

from dataclasses import dataclass, field

PHI = 1.6180339887
SAMPLE_RATE = 44100


@dataclass
class GrooveTemplate:
    """A groove timing template."""
    name: str
    # Timing offsets per 16th note (0-15), in % of 16th note duration
    timing: list[float] = field(default_factory=lambda: [0.0] * 16)
    # Velocity scaling per 16th note
    velocity: list[float] = field(default_factory=lambda: [1.0] * 16)
    swing: float = 0.0  # 0-100% swing

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "swing": self.swing,
            "steps": len(self.timing),
        }


# Built-in groove templates
GROOVE_TEMPLATES = {
    "straight": GrooveTemplate(
        name="straight",
        timing=[0.0] * 16,
        velocity=[1.0, 0.7, 0.8, 0.6, 0.9, 0.7, 0.8, 0.6,
                  1.0, 0.7, 0.8, 0.6, 0.9, 0.7, 0.8, 0.6],
    ),
    "swing_light": GrooveTemplate(
        name="swing_light",
        timing=[0, 0, 15, 0, 0, 0, 15, 0,
                0, 0, 15, 0, 0, 0, 15, 0],
        swing=25.0,
    ),
    "swing_heavy": GrooveTemplate(
        name="swing_heavy",
        timing=[0, 0, 30, 0, 0, 0, 30, 0,
                0, 0, 30, 0, 0, 0, 30, 0],
        swing=60.0,
    ),
    "dubstep_halftime": GrooveTemplate(
        name="dubstep_halftime",
        timing=[0, 5, -3, 8, 0, 3, -5, 10,
                0, 5, -3, 8, 0, 3, -5, 10],
        velocity=[1.0, 0.5, 0.6, 0.4, 0.9, 0.5, 0.7, 0.3,
                  1.0, 0.5, 0.6, 0.4, 0.9, 0.5, 0.7, 0.3],
    ),
    "riddim_bounce": GrooveTemplate(
        name="riddim_bounce",
        timing=[0, -5, 10, -5, 0, -5, 10, -5,
                0, -5, 10, -5, 0, -5, 10, -5],
        velocity=[1.0, 0.6, 0.9, 0.5, 1.0, 0.6, 0.9, 0.5,
                  1.0, 0.6, 0.9, 0.5, 1.0, 0.6, 0.9, 0.5],
    ),
    "phi_groove": GrooveTemplate(
        name="phi_groove",
        timing=[0, 0, int(100 / PHI / PHI), 0,
                0, 0, int(100 / PHI), 0,
                0, 0, int(100 / PHI / PHI), 0,
                0, 0, int(100 / PHI), 0],
        velocity=[1.0, 1 / PHI, 1 / PHI ** 2, 1 / PHI,
                  1.0, 1 / PHI, 1 / PHI ** 2, 1 / PHI,
                  1.0, 1 / PHI, 1 / PHI ** 2, 1 / PHI,
                  1.0, 1 / PHI, 1 / PHI ** 2, 1 / PHI],
    ),
}


@dataclass
class NoteEvent:
    """A MIDI-like note event."""
    time: float  # seconds
    duration: float  # seconds
    pitch: int = 60  # MIDI note
    velocity: float = 1.0


class GrooveEngine:
    """Apply groove to patterns."""

    def __init__(self, bpm: float = 140, sample_rate: int = SAMPLE_RATE):
        self.bpm = bpm
        self.sample_rate = sample_rate

    @property
    def beat_duration(self) -> float:
        """Duration of one beat in seconds."""
        return 60.0 / self.bpm

    @property
    def sixteenth_duration(self) -> float:
        """Duration of one 16th note in seconds."""
        return self.beat_duration / 4

    def apply_swing(self, events: list[NoteEvent],
                    swing_amount: float = 50.0) -> list[NoteEvent]:
        """Apply swing to events."""
        sixteenth = self.sixteenth_duration
        shifted: list[NoteEvent] = []

        for e in events:
            # Find which 16th note this falls on
            step = e.time / sixteenth
            step_idx = int(round(step)) % 16

            # Swing offsets on even-numbered off-beats
            offset = 0.0
            if step_idx % 2 == 1:  # off-beat
                offset = sixteenth * swing_amount / 100 * 0.5

            shifted.append(NoteEvent(
                time=e.time + offset,
                duration=e.duration,
                pitch=e.pitch,
                velocity=e.velocity,
            ))

        return shifted

    def apply_groove(self, events: list[NoteEvent],
                     template: GrooveTemplate | None = None) -> list[NoteEvent]:
        """Apply groove template to events."""
        tmpl = template or GROOVE_TEMPLATES["straight"]
        sixteenth = self.sixteenth_duration
        grooved: list[NoteEvent] = []

        for e in events:
            step = e.time / sixteenth
            step_idx = int(round(step)) % len(tmpl.timing)

            # Timing offset
            offset = tmpl.timing[step_idx] / 100 * sixteenth
            # Velocity scaling
            vel_scale = tmpl.velocity[step_idx] if step_idx < len(tmpl.velocity) else 1.0

            grooved.append(NoteEvent(
                time=max(0, e.time + offset),
                duration=e.duration,
                pitch=e.pitch,
                velocity=e.velocity * vel_scale,
            ))

        return grooved

    def humanize(self, events: list[NoteEvent],
                 timing_ms: float = 10,
                 velocity_pct: float = 5) -> list[NoteEvent]:
        """Add human-like timing and velocity variation."""
        import random
        rng = random.Random(42)

        humanized: list[NoteEvent] = []
        for e in events:
            t_offset = rng.gauss(0, timing_ms / 1000)
            v_offset = rng.gauss(0, velocity_pct / 100)

            humanized.append(NoteEvent(
                time=max(0, e.time + t_offset),
                duration=e.duration,
                pitch=e.pitch,
                velocity=max(0.01, min(1.0, e.velocity + v_offset)),
            ))

        return humanized

    def quantize(self, events: list[NoteEvent],
                 grid: float = 0.25,  # quarter note
                 strength: float = 1.0) -> list[NoteEvent]:
        """Quantize events to grid."""
        grid_seconds = grid * self.beat_duration

        quantized: list[NoteEvent] = []
        for e in events:
            nearest = round(e.time / grid_seconds) * grid_seconds
            new_time = e.time + (nearest - e.time) * strength

            quantized.append(NoteEvent(
                time=max(0, new_time),
                duration=e.duration,
                pitch=e.pitch,
                velocity=e.velocity,
            ))

        return quantized

    def generate_pattern(self, steps: int = 16,
                         density: float = 0.5) -> list[NoteEvent]:
        """Generate a rhythmic pattern."""
        import random
        rng = random.Random(42)

        events: list[NoteEvent] = []
        sixteenth = self.sixteenth_duration

        for i in range(steps):
            if rng.random() < density:
                events.append(NoteEvent(
                    time=i * sixteenth,
                    duration=sixteenth * 0.8,
                    pitch=60,
                    velocity=rng.uniform(0.5, 1.0),
                ))

        return events

    def list_templates(self) -> list[str]:
        """List available groove templates."""
        return list(GROOVE_TEMPLATES.keys())

    def get_template(self, name: str) -> GrooveTemplate | None:
        """Get a groove template by name."""
        return GROOVE_TEMPLATES.get(name)


def main() -> None:
    print("Groove Engine")
    engine = GrooveEngine(bpm=140)

    # Generate pattern
    pattern = engine.generate_pattern(16, density=0.6)
    print(f"  Generated: {len(pattern)} events")

    # Apply grooves
    for name in engine.list_templates():
        tmpl = engine.get_template(name)
        grooved = engine.apply_groove(pattern, tmpl)
        shifts = [
            abs(g.time - o.time) * 1000
            for g, o in zip(grooved, pattern)
        ]
        avg_shift = sum(shifts) / len(shifts) if shifts else 0
        print(f"  {name:20s}: avg shift={avg_shift:.1f}ms")

    # Humanize
    human = engine.humanize(pattern, timing_ms=15, velocity_pct=8)
    print(f"\n  Humanized: {len(human)} events")

    print("Done.")


if __name__ == "__main__":
    main()
