"""
DUBFORGE — Randomizer Engine  (Session 205)

Controlled randomization for sound design:
parameter randomization, seed-based determinism,
weighted ranges, PHI-distributed randomness.
"""

import hashlib
import math
from dataclasses import dataclass, field

PHI = 1.6180339887


@dataclass
class RandomRange:
    """A parameter randomization range."""
    param_name: str
    min_value: float = 0.0
    max_value: float = 1.0
    distribution: str = "uniform"  # uniform, gaussian, phi, weighted
    weight: float = 0.5  # center of gravity for weighted
    lock: bool = False  # if locked, don't randomize

    def to_dict(self) -> dict:
        return {
            "param": self.param_name,
            "min": self.min_value,
            "max": self.max_value,
            "distribution": self.distribution,
            "weight": self.weight,
            "locked": self.lock,
        }


@dataclass
class RandomPreset:
    """A randomization preset — defines what gets randomized."""
    name: str
    ranges: list[RandomRange] = field(default_factory=list)
    seed: int = 0
    description: str = ""

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "ranges": [r.to_dict() for r in self.ranges],
            "seed": self.seed,
            "description": self.description,
        }


class PRNG:
    """Simple deterministic PRNG (for reproducibility)."""

    def __init__(self, seed: int = 42):
        self.state = seed & 0xFFFFFFFF

    def next(self) -> float:
        """Generate next random float [0, 1)."""
        self.state = (self.state * 1103515245 + 12345) & 0x7FFFFFFF
        return self.state / 0x7FFFFFFF

    def next_range(self, lo: float, hi: float) -> float:
        """Random float in range."""
        return lo + self.next() * (hi - lo)

    def next_int(self, lo: int, hi: int) -> int:
        """Random int in range [lo, hi]."""
        return int(self.next_range(lo, hi + 0.999))

    def next_gaussian(self, mean: float = 0.0,
                      std: float = 1.0) -> float:
        """Box-Muller Gaussian."""
        u1 = max(1e-10, self.next())
        u2 = self.next()
        z = math.sqrt(-2 * math.log(u1)) * math.cos(2 * math.pi * u2)
        return mean + z * std

    def next_phi(self) -> float:
        """PHI-distributed: biased toward golden ratio."""
        base = self.next()
        return base ** (1 / PHI)

    def choice(self, items: list) -> any:
        """Random choice from list."""
        if not items:
            return None
        idx = self.next_int(0, len(items) - 1)
        return items[idx]

    def shuffle(self, items: list) -> list:
        """Fisher-Yates shuffle (returns new list)."""
        result = list(items)
        for i in range(len(result) - 1, 0, -1):
            j = self.next_int(0, i)
            result[i], result[j] = result[j], result[i]
        return result


class RandomizerEngine:
    """Controlled randomization for sound design."""

    def __init__(self, seed: int = 42):
        self.rng = PRNG(seed)
        self.presets: dict[str, RandomPreset] = {}
        self.history: list[dict] = []
        self._init_presets()

    def _init_presets(self) -> None:
        """Initialize built-in presets."""
        # Bass randomizer
        bass = RandomPreset("bass", description="Randomize bass parameters")
        bass.ranges = [
            RandomRange("frequency", 30, 120, "weighted", 0.4),
            RandomRange("drive", 0.0, 1.0, "phi"),
            RandomRange("filter_cutoff", 200, 5000, "gaussian", 0.5),
            RandomRange("resonance", 0.0, 0.9, "uniform"),
            RandomRange("wobble_rate", 1, 16, "phi"),
            RandomRange("sub_level", 0.5, 1.0, "weighted", 0.8),
        ]
        self.presets["bass"] = bass

        # Lead randomizer
        lead = RandomPreset("lead", description="Randomize lead parameters")
        lead.ranges = [
            RandomRange("octave", 3, 6, "weighted", 0.5),
            RandomRange("detune", 0, 30, "phi"),
            RandomRange("attack", 0.001, 0.5, "gaussian", 0.3),
            RandomRange("decay", 0.05, 1.0, "uniform"),
            RandomRange("sustain", 0.3, 1.0, "weighted", 0.7),
            RandomRange("release", 0.05, 2.0, "gaussian", 0.4),
            RandomRange("brightness", 0.0, 1.0, "phi"),
        ]
        self.presets["lead"] = lead

        # FX randomizer
        fx = RandomPreset("fx", description="Randomize FX parameters")
        fx.ranges = [
            RandomRange("reverb_mix", 0.0, 1.0, "uniform"),
            RandomRange("delay_time", 50, 500, "phi"),
            RandomRange("delay_feedback", 0.0, 0.8, "gaussian", 0.3),
            RandomRange("distortion", 0.0, 1.0, "phi"),
            RandomRange("chorus_depth", 0.0, 1.0, "uniform"),
        ]
        self.presets["fx"] = fx

        # PHI randomizer
        phi = RandomPreset("phi", description="PHI-centered randomization")
        phi.ranges = [
            RandomRange("ratio", 0.5, 3.0, "phi"),
            RandomRange("harmonic", 1, 8, "phi"),
            RandomRange("blend", 0.0, 1.0, "phi"),
            RandomRange("decay", 0.1, 5.0, "phi"),
        ]
        self.presets["phi"] = phi

    def _sample_range(self, rng: RandomRange) -> float:
        """Sample a random value according to range distribution."""
        if rng.lock:
            return rng.weight  # return center value if locked

        r = rng.max_value - rng.min_value

        if rng.distribution == "uniform":
            return self.rng.next_range(rng.min_value, rng.max_value)

        elif rng.distribution == "gaussian":
            center = rng.min_value + r * rng.weight
            std = r * 0.2
            val = self.rng.next_gaussian(center, std)
            return max(rng.min_value, min(rng.max_value, val))

        elif rng.distribution == "phi":
            val = self.rng.next_phi()
            return rng.min_value + val * r

        elif rng.distribution == "weighted":
            # Bias toward weight position
            base = self.rng.next()
            biased = base ** (1 / (rng.weight + 0.1))
            return rng.min_value + biased * r

        return self.rng.next_range(rng.min_value, rng.max_value)

    def randomize(self, preset_name: str) -> dict[str, float]:
        """Randomize parameters using a preset."""
        preset = self.presets.get(preset_name)
        if not preset:
            return {}

        result: dict[str, float] = {}
        for rng in preset.ranges:
            result[rng.param_name] = round(self._sample_range(rng), 4)

        self.history.append({
            "preset": preset_name,
            "values": result,
        })

        return result

    def randomize_custom(self, ranges: list[tuple]) -> dict[str, float]:
        """Randomize custom ranges: [(name, min, max, dist), ...]"""
        result: dict[str, float] = {}
        for item in ranges:
            name = item[0]
            lo = item[1] if len(item) > 1 else 0.0
            hi = item[2] if len(item) > 2 else 1.0
            dist = item[3] if len(item) > 3 else "uniform"
            rng = RandomRange(name, lo, hi, dist)
            result[name] = round(self._sample_range(rng), 4)
        return result

    def set_seed(self, seed: int) -> None:
        """Set PRNG seed for reproducibility."""
        self.rng = PRNG(seed)

    def seed_from_text(self, text: str) -> int:
        """Generate deterministic seed from text."""
        h = hashlib.sha1(text.encode()).hexdigest()
        seed = int(h[:8], 16)
        self.set_seed(seed)
        return seed

    def lock_param(self, preset_name: str, param: str) -> bool:
        """Lock a parameter from randomization."""
        preset = self.presets.get(preset_name)
        if not preset:
            return False
        for rng in preset.ranges:
            if rng.param_name == param:
                rng.lock = True
                return True
        return False

    def unlock_param(self, preset_name: str, param: str) -> bool:
        """Unlock a parameter."""
        preset = self.presets.get(preset_name)
        if not preset:
            return False
        for rng in preset.ranges:
            if rng.param_name == param:
                rng.lock = False
                return True
        return False

    def mutate(self, values: dict[str, float],
               amount: float = 0.2) -> dict[str, float]:
        """Mutate existing values by a small amount."""
        result: dict[str, float] = {}
        for name, val in values.items():
            offset = (self.rng.next() - 0.5) * 2 * amount
            result[name] = round(max(0.0, min(1.0, val + offset)), 4)
        return result

    def interpolate(self, values_a: dict[str, float],
                    values_b: dict[str, float],
                    blend: float = 0.5) -> dict[str, float]:
        """Interpolate between two parameter sets."""
        result: dict[str, float] = {}
        all_keys = set(values_a.keys()) | set(values_b.keys())
        for key in all_keys:
            a = values_a.get(key, 0.0)
            b = values_b.get(key, 0.0)
            result[key] = round(a * (1 - blend) + b * blend, 4)
        return result

    def get_history(self, limit: int = 10) -> list[dict]:
        """Get randomization history."""
        return self.history[-limit:]

    def get_presets(self) -> list[str]:
        """List available presets."""
        return list(self.presets.keys())

    def get_summary(self) -> dict:
        return {
            "presets": len(self.presets),
            "history": len(self.history),
            "available": self.get_presets(),
        }


def main() -> None:
    print("Randomizer Engine")

    rnd = RandomizerEngine(seed=42)

    # Randomize bass
    bass = rnd.randomize("bass")
    print(f"  Bass: {bass}")

    # Randomize lead
    lead = rnd.randomize("lead")
    print(f"  Lead: {lead}")

    # PHI randomization
    phi = rnd.randomize("phi")
    print(f"  PHI: {phi}")

    # Mutate
    mutated = rnd.mutate(bass, 0.1)
    print(f"  Mutated bass: {mutated}")

    # Interpolate
    blend = rnd.interpolate(bass, lead, 1.0 / PHI)
    print(f"  Blend (PHI): {blend}")

    # Seed from text
    seed = rnd.seed_from_text("DUBFORGE ASCENSION")
    print(f"\n  Seed from text: {seed}")

    print(f"  Summary: {rnd.get_summary()}")
    print("Done.")


if __name__ == "__main__":
    main()
