"""
DUBFORGE — Dynamics Processor  (Session 221)

Gate, ducker, de-esser, transient designer.
Complementary to dynamics.py (compressor/limiter).
"""

import math
from dataclasses import dataclass

PHI = 1.6180339887
SAMPLE_RATE = 44100


@dataclass
class GateConfig:
    """Noise gate configuration."""
    threshold_db: float = -40.0
    attack_ms: float = 1.0
    hold_ms: float = 50.0
    release_ms: float = 100.0
    range_db: float = -80.0  # max attenuation


@dataclass
class DeEsserConfig:
    """De-esser configuration."""
    frequency: float = 6000.0
    threshold_db: float = -20.0
    reduction_db: float = -6.0
    bandwidth: float = 2000.0


class DynamicsProcessor:
    """Advanced dynamics processing."""

    def __init__(self, sample_rate: int = SAMPLE_RATE):
        self.sample_rate = sample_rate

    @staticmethod
    def _db(linear: float) -> float:
        return 20 * math.log10(linear) if linear > 0 else -120.0

    @staticmethod
    def _from_db(db: float) -> float:
        return 10 ** (db / 20)

    def gate(self, samples: list[float],
             config: GateConfig | None = None) -> list[float]:
        """Apply noise gate."""
        cfg = config or GateConfig()
        threshold = self._from_db(cfg.threshold_db)
        range_gain = self._from_db(cfg.range_db)

        attack = max(1, int(cfg.attack_ms * self.sample_rate / 1000))
        hold = max(1, int(cfg.hold_ms * self.sample_rate / 1000))
        release = max(1, int(cfg.release_ms * self.sample_rate / 1000))

        result: list[float] = []
        env = 0.0
        hold_counter = 0
        _gate_open = False

        for s in samples:
            level = abs(s)

            if level > threshold:
                _gate_open = True
                hold_counter = hold
                # Attack
                env += (1.0 - env) / attack
            else:
                if hold_counter > 0:
                    hold_counter -= 1
                else:
                    _gate_open = False
                    # Release
                    env += (range_gain - env) / release

            env = max(range_gain, min(1.0, env))
            result.append(s * env)

        return result

    def duck(self, audio: list[float], sidechain: list[float],
             threshold_db: float = -20.0,
             amount_db: float = -12.0,
             attack_ms: float = 5.0,
             release_ms: float = 100.0) -> list[float]:
        """Duck audio based on sidechain signal."""
        threshold = self._from_db(threshold_db)
        duck_gain = self._from_db(amount_db)
        attack = max(1, int(attack_ms * self.sample_rate / 1000))
        release = max(1, int(release_ms * self.sample_rate / 1000))

        n = min(len(audio), len(sidechain))
        result: list[float] = []
        env = 1.0

        for i in range(n):
            sc_level = abs(sidechain[i])

            if sc_level > threshold:
                target = duck_gain
                env += (target - env) / attack
            else:
                target = 1.0
                env += (target - env) / release

            result.append(audio[i] * env)

        return result

    def de_ess(self, samples: list[float],
               config: DeEsserConfig | None = None) -> list[float]:
        """Simple de-esser using band detection + gain reduction."""
        cfg = config or DeEsserConfig()
        threshold = self._from_db(cfg.threshold_db)
        reduction = self._from_db(cfg.reduction_db)

        # Simple high-frequency detector (difference filter)
        result: list[float] = []
        prev = 0.0
        env = 1.0
        attack = 0.01  # fast attack
        release_coeff = 0.001  # slow release

        for s in samples:
            # High-frequency content estimate
            hf = abs(s - prev)
            prev = s

            if hf > threshold:
                env = max(reduction, env - attack)
            else:
                env = min(1.0, env + release_coeff)

            result.append(s * env)

        return result

    def transient_shaper(self, samples: list[float],
                         attack_gain: float = 1.5,
                         sustain_gain: float = 0.8) -> list[float]:
        """Shape transients — boost attack, control sustain."""
        if not samples:
            return []

        result: list[float] = []
        fast_env = 0.0
        slow_env = 0.0
        fast_coeff = 0.01
        slow_coeff = 0.0001

        for s in samples:
            level = abs(s)

            # Fast envelope (tracks transients)
            fast_env += (level - fast_env) * fast_coeff
            # Slow envelope (tracks sustain)
            slow_env += (level - slow_env) * slow_coeff

            # Transient detection
            if fast_env > slow_env * 1.5:
                # Transient — boost
                gain = attack_gain
            else:
                # Sustain — attenuate
                gain = sustain_gain

            result.append(s * gain)

        # Limit
        pk = max(abs(s) for s in result) if result else 1.0
        if pk > 1.0:
            result = [s / pk for s in result]

        return result

    def phi_dynamics(self, samples: list[float],
                     amount: float = 0.5) -> list[float]:
        """PHI-ratio dynamic processing — golden ratio compression."""
        if not samples:
            return []

        # PHI threshold: 1/PHI of peak
        pk = max(abs(s) for s in samples) if samples else 1.0
        threshold = pk / PHI

        result: list[float] = []
        for s in samples:
            level = abs(s)
            if level > threshold:
                # Compress with PHI ratio
                over = level - threshold
                compressed = threshold + over / PHI * amount
                result.append(math.copysign(compressed, s))
            else:
                result.append(s)

        return result


def main() -> None:
    print("Dynamics Processor")
    proc = DynamicsProcessor()

    n = SAMPLE_RATE * 2
    # Signal with noise floor
    samples: list[float] = []
    import random
    rng = random.Random(42)
    for i in range(n):
        t = i / SAMPLE_RATE
        # Drum-like burst
        if i % (SAMPLE_RATE // 2) < 2000:
            s = 0.9 * math.sin(2 * math.pi * 80 * t) * max(0, 1 - t * 10)
        else:
            s = rng.gauss(0, 0.01)  # noise floor
        samples.append(s)

    # Gate
    gated = proc.gate(samples, GateConfig(threshold_db=-30))
    print(f"  Gate: removed noise, peak={max(abs(s) for s in gated):.3f}")

    # Transient shaper
    shaped = proc.transient_shaper(samples, attack_gain=2.0, sustain_gain=0.5)
    print(f"  Transient shaped: peak={max(abs(s) for s in shaped):.3f}")

    # PHI dynamics
    phi = proc.phi_dynamics(samples, amount=0.7)
    print(f"  PHI dynamics: peak={max(abs(s) for s in phi):.3f}")

    # De-esser
    deessed = proc.de_ess(samples)
    print(f"  De-essed: {len(deessed)} samples")

    print("Done.")


if __name__ == "__main__":
    main()
