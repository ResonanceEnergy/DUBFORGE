"""
DUBFORGE — Envelope Generator  (Session 202)

Advanced envelope generation: ADSR, AHDSR, multi-stage,
looping envelopes, PHI-curved envelopes, tempo-sync.
"""

import math
from dataclasses import dataclass

from engine.config_loader import PHI
SAMPLE_RATE = 48000


@dataclass
class EnvelopeStage:
    """A single envelope stage."""
    name: str
    duration: float  # seconds
    start_level: float
    end_level: float
    curve: str = "linear"  # linear, exponential, phi, log, sine

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "duration": self.duration,
            "start": self.start_level,
            "end": self.end_level,
            "curve": self.curve,
        }


class EnvelopeGenerator:
    """Generate various envelope shapes."""

    def __init__(self, sample_rate: int = SAMPLE_RATE):
        self.sample_rate = sample_rate

    def _apply_curve(self, t: float, curve: str) -> float:
        """Apply curve shaping to normalized time [0-1]."""
        t = max(0.0, min(1.0, t))

        if curve == "linear":
            return t
        elif curve == "exponential":
            return t * t
        elif curve == "log":
            return math.sqrt(t)
        elif curve == "phi":
            return t ** (1 / PHI)
        elif curve == "sine":
            return 0.5 * (1 - math.cos(math.pi * t))
        elif curve == "s_curve":
            return t * t * (3 - 2 * t)
        elif curve == "inverse_exp":
            return 1 - (1 - t) ** 2
        else:
            return t

    def _render_stage(self, stage: EnvelopeStage) -> list[float]:
        """Render a single stage."""
        n = max(1, int(stage.duration * self.sample_rate))
        samples: list[float] = []

        for i in range(n):
            t = i / n if n > 1 else 1.0
            curved = self._apply_curve(t, stage.curve)
            val = stage.start_level + (
                stage.end_level - stage.start_level
            ) * curved
            samples.append(val)

        return samples

    # --- Standard Envelopes ---

    def adsr(self, attack: float = 0.01, decay: float = 0.1,
             sustain: float = 0.7, release: float = 0.3,
             hold_time: float = 0.5,
             curve: str = "exponential") -> list[float]:
        """Generate ADSR envelope."""
        stages = [
            EnvelopeStage("attack", attack, 0.0, 1.0, curve),
            EnvelopeStage("decay", decay, 1.0, sustain, curve),
            EnvelopeStage("sustain", hold_time, sustain, sustain, "linear"),
            EnvelopeStage("release", release, sustain, 0.0, curve),
        ]
        return self.render_stages(stages)

    def ahdsr(self, attack: float = 0.01, hold: float = 0.05,
              decay: float = 0.1, sustain: float = 0.7,
              release: float = 0.3, hold_time: float = 0.5,
              curve: str = "exponential") -> list[float]:
        """Generate AHDSR envelope."""
        stages = [
            EnvelopeStage("attack", attack, 0.0, 1.0, curve),
            EnvelopeStage("hold", hold, 1.0, 1.0, "linear"),
            EnvelopeStage("decay", decay, 1.0, sustain, curve),
            EnvelopeStage("sustain", hold_time, sustain, sustain, "linear"),
            EnvelopeStage("release", release, sustain, 0.0, curve),
        ]
        return self.render_stages(stages)

    def ar(self, attack: float = 0.01, release: float = 0.5,
           curve: str = "exponential") -> list[float]:
        """Simple attack-release envelope."""
        stages = [
            EnvelopeStage("attack", attack, 0.0, 1.0, curve),
            EnvelopeStage("release", release, 1.0, 0.0, curve),
        ]
        return self.render_stages(stages)

    def pluck(self, attack: float = 0.001,
              decay: float = 0.5) -> list[float]:
        """Pluck envelope (instant attack, exponential decay)."""
        stages = [
            EnvelopeStage("attack", attack, 0.0, 1.0, "linear"),
            EnvelopeStage("decay", decay, 1.0, 0.0, "exponential"),
        ]
        return self.render_stages(stages)

    def pad(self, attack: float = 0.5, sustain: float = 0.8,
            hold: float = 2.0, release: float = 1.0) -> list[float]:
        """Slow pad envelope."""
        stages = [
            EnvelopeStage("attack", attack, 0.0, 1.0, "sine"),
            EnvelopeStage("sustain", hold, sustain, sustain, "linear"),
            EnvelopeStage("release", release, sustain, 0.0, "sine"),
        ]
        return self.render_stages(stages)

    # --- PHI Envelopes ---

    def phi_envelope(self, total_duration: float = 1.0) -> list[float]:
        """Envelope with PHI-ratio stage durations."""
        t = total_duration
        attack = t / (PHI ** 4)
        decay = t / (PHI ** 3)
        sustain_time = t / (PHI ** 2)
        release = t / PHI

        # Scale to fit
        total = attack + decay + sustain_time + release
        scale = t / total

        return self.adsr(
            attack=attack * scale,
            decay=decay * scale,
            sustain=1.0 / PHI,
            release=release * scale,
            hold_time=sustain_time * scale,
            curve="phi",
        )

    def phi_decay(self, duration: float = 1.0) -> list[float]:
        """Decay curve shaped by PHI."""
        n = int(self.sample_rate * duration)
        samples: list[float] = []
        for i in range(n):
            t = i / n
            val = (1 - t) ** (1 / PHI)
            samples.append(val)
        return samples

    # --- Special Envelopes ---

    def multi_stage(self, stages: list[tuple]) -> list[float]:
        """Custom multi-stage envelope.

        stages: [(duration, start, end, curve), ...]
        """
        envelope_stages = [
            EnvelopeStage(f"stage_{i}", dur, start, end, crv)
            for i, (dur, start, end, crv) in enumerate(stages)
        ]
        return self.render_stages(envelope_stages)

    def looping(self, loop_stages: list[tuple],
                loops: int = 4,
                release: float = 0.5) -> list[float]:
        """Looping envelope."""
        loop_env = self.multi_stage(loop_stages)

        result = loop_env * loops

        # Release
        release_n = int(self.sample_rate * release)
        final_val = result[-1] if result else 0.0
        for i in range(release_n):
            t = i / release_n
            result.append(final_val * (1 - t))

        return result

    def tempo_synced(self, bpm: float = 140.0,
                     beats: float = 1.0,
                     shape: str = "adsr") -> list[float]:
        """Tempo-synced envelope."""
        beat_duration = 60.0 / bpm
        total = beat_duration * beats

        if shape == "adsr":
            return self.adsr(
                attack=total * 0.05,
                decay=total * 0.2,
                sustain=0.7,
                release=total * 0.25,
                hold_time=total * 0.5,
            )
        elif shape == "pluck":
            return self.pluck(total * 0.01, total * 0.99)
        elif shape == "pad":
            return self.pad(total * 0.3, 0.8, total * 0.4, total * 0.3)
        else:
            return self.ar(total * 0.1, total * 0.9)

    def sidechain(self, bpm: float = 140.0,
                  beats: float = 1.0,
                  depth: float = 0.8,
                  curve: str = "exponential") -> list[float]:
        """Sidechain ducking envelope."""
        beat_duration = 60.0 / bpm * beats
        n = int(self.sample_rate * beat_duration)

        samples: list[float] = []
        for i in range(n):
            t = i / n
            val = (1 - depth) + depth * self._apply_curve(t, curve)
            samples.append(val)

        return samples

    # --- Rendering ---

    def render_stages(self, stages: list[EnvelopeStage]) -> list[float]:
        """Render multi-stage envelope."""
        result: list[float] = []
        for stage in stages:
            rendered = self._render_stage(stage)
            result.extend(rendered)
        return result

    def apply(self, samples: list[float],
              envelope: list[float]) -> list[float]:
        """Apply envelope to audio samples."""
        result: list[float] = []
        for i, s in enumerate(samples):
            if i < len(envelope):
                result.append(s * envelope[i])
            else:
                result.append(0.0)
        return result

    def get_presets(self) -> dict[str, dict]:
        """Get envelope presets."""
        return {
            "pluck": {"attack": 0.001, "decay": 0.3, "sustain": 0.0,
                       "release": 0.1},
            "pad": {"attack": 0.5, "decay": 0.3, "sustain": 0.8,
                     "release": 1.0},
            "bass": {"attack": 0.005, "decay": 0.1, "sustain": 0.9,
                      "release": 0.05},
            "keys": {"attack": 0.01, "decay": 0.2, "sustain": 0.6,
                      "release": 0.3},
            "swell": {"attack": 1.0, "decay": 0.0, "sustain": 1.0,
                       "release": 0.5},
            "stab": {"attack": 0.001, "decay": 0.05, "sustain": 0.0,
                      "release": 0.01},
            "phi": {"attack": 0.01, "decay": 0.1 * PHI,
                     "sustain": 1 / PHI, "release": 0.3 * PHI},
        }


def main() -> None:
    print("Envelope Generator")

    gen = EnvelopeGenerator()

    # ADSR
    env = gen.adsr(0.01, 0.1, 0.7, 0.3, 0.5)
    print(f"  ADSR: {len(env)} samples, "
          f"peak={max(env):.3f}")

    # PHI envelope
    phi_env = gen.phi_envelope(1.0)
    print(f"  PHI: {len(phi_env)} samples, "
          f"peak={max(phi_env):.3f}")

    # Sidechain
    sc = gen.sidechain(140, 1.0, 0.8)
    print(f"  Sidechain: {len(sc)} samples, "
          f"min={min(sc):.3f}")

    # Tempo-synced
    ts = gen.tempo_synced(140, 2.0, "pluck")
    print(f"  Synced pluck: {len(ts)} samples")

    # Presets
    presets = gen.get_presets()
    print(f"\n  Presets: {list(presets.keys())}")
    print("Done.")


if __name__ == "__main__":
    main()
