"""
DUBFORGE — Live FX Processor Engine  (Session 177)

Real-time signal processing effects for live performance:
filters, delays, distortion, all with PHI-tuned parameters.
"""

import math
from dataclasses import dataclass

PHI = 1.6180339887
SAMPLE_RATE = 48000


@dataclass
class FXState:
    """Mutable state for an effect processor."""
    buffer: list[float]
    write_pos: int = 0
    feedback: float = 0.0
    prev_sample: float = 0.0
    prev_sample2: float = 0.0

    @staticmethod
    def create(buffer_size: int = 44100) -> 'FXState':
        return FXState(buffer=[0.0] * buffer_size)


class LiveFilter:
    """Real-time biquad filter."""

    def __init__(self, cutoff: float = 1000.0,
                 resonance: float = 0.5,
                 filter_type: str = "lowpass",
                 sample_rate: int = SAMPLE_RATE):
        self.cutoff = cutoff
        self.resonance = resonance
        self.filter_type = filter_type
        self.sample_rate = sample_rate
        self._x1 = self._x2 = 0.0
        self._y1 = self._y2 = 0.0
        self._update_coeffs()

    def _update_coeffs(self) -> None:
        """Calculate biquad coefficients."""
        w0 = 2 * math.pi * min(self.cutoff, self.sample_rate * 0.49) / self.sample_rate
        alpha = math.sin(w0) / (2.0 * max(self.resonance, 0.01) * 10)
        cos_w0 = math.cos(w0)

        if self.filter_type == "highpass":
            self.b0 = (1 + cos_w0) / 2
            self.b1 = -(1 + cos_w0)
            self.b2 = (1 + cos_w0) / 2
        elif self.filter_type == "bandpass":
            self.b0 = alpha
            self.b1 = 0.0
            self.b2 = -alpha
        else:  # lowpass
            self.b0 = (1 - cos_w0) / 2
            self.b1 = 1 - cos_w0
            self.b2 = (1 - cos_w0) / 2

        a0 = 1 + alpha
        self.a1 = -2 * cos_w0
        self.a2 = 1 - alpha

        # Normalize
        self.b0 /= a0
        self.b1 /= a0
        self.b2 /= a0
        self.a1 /= a0
        self.a2 /= a0

    def set_cutoff(self, cutoff: float) -> None:
        self.cutoff = cutoff
        self._update_coeffs()

    def set_resonance(self, resonance: float) -> None:
        self.resonance = resonance
        self._update_coeffs()

    def process_sample(self, x: float) -> float:
        y = (self.b0 * x + self.b1 * self._x1 + self.b2 * self._x2
             - self.a1 * self._y1 - self.a2 * self._y2)
        self._x2 = self._x1
        self._x1 = x
        self._y2 = self._y1
        self._y1 = y
        return y

    def process(self, signal: list[float]) -> list[float]:
        return [self.process_sample(x) for x in signal]


class LiveDelay:
    """Tempo-synced delay with feedback."""

    def __init__(self, delay_ms: float = 300.0,
                 feedback: float = 0.5,
                 mix: float = 0.3,
                 sample_rate: int = SAMPLE_RATE):
        self.delay_ms = delay_ms
        self.feedback = min(feedback, 0.95)
        self.mix = mix
        self.sample_rate = sample_rate
        max_samples = int(sample_rate * 2)  # 2s max
        self._buffer = [0.0] * max_samples
        self._write_pos = 0

    @property
    def delay_samples(self) -> int:
        return int(self.delay_ms / 1000.0 * self.sample_rate)

    def set_delay_ms(self, ms: float) -> None:
        self.delay_ms = ms

    def set_delay_beats(self, bpm: float, beats: float = 0.5) -> None:
        self.delay_ms = beats * 60000.0 / bpm

    def phi_delay(self, bpm: float) -> None:
        """Set delay to PHI ratio of beat."""
        self.set_delay_beats(bpm, 1.0 / PHI)

    def process_sample(self, x: float) -> float:
        buf_size = len(self._buffer)
        delay = min(self.delay_samples, buf_size - 1)
        read_pos = (self._write_pos - delay) % buf_size
        delayed = self._buffer[read_pos]
        self._buffer[self._write_pos] = x + delayed * self.feedback
        self._write_pos = (self._write_pos + 1) % buf_size
        return x * (1.0 - self.mix) + delayed * self.mix

    def process(self, signal: list[float]) -> list[float]:
        return [self.process_sample(x) for x in signal]


class LiveDistortion:
    """Real-time distortion with multiple algorithms."""

    def __init__(self, drive: float = 0.5,
                 mode: str = "tanh",
                 mix: float = 1.0):
        self.drive = drive
        self.mode = mode
        self.mix = mix

    def process_sample(self, x: float) -> float:
        gained = x * (1.0 + self.drive * 20.0)

        if self.mode == "hard_clip":
            distorted = max(-1.0, min(1.0, gained))
        elif self.mode == "soft_clip":
            if abs(gained) > 2 / 3:
                distorted = math.copysign(1.0, gained)
            elif abs(gained) > 1 / 3:
                distorted = (3 - (2 - 3 * abs(gained)) ** 2) / 3
                distorted = math.copysign(distorted, gained)
            else:
                distorted = 2 * gained
        elif self.mode == "fold":
            while abs(gained) > 1.0:
                if gained > 1.0:
                    gained = 2.0 - gained
                elif gained < -1.0:
                    gained = -2.0 - gained
            distorted = gained
        elif self.mode == "bitcrush":
            bits = max(1, int(16 - self.drive * 14))
            levels = 2 ** bits
            distorted = round(gained * levels) / levels
        else:  # tanh
            distorted = math.tanh(gained)

        return x * (1.0 - self.mix) + distorted * self.mix

    def process(self, signal: list[float]) -> list[float]:
        return [self.process_sample(x) for x in signal]


class LiveChorus:
    """Stereo chorus effect."""

    def __init__(self, rate: float = 1.0,
                 depth: float = 0.5,
                 mix: float = 0.3,
                 sample_rate: int = SAMPLE_RATE):
        self.rate = rate
        self.depth = depth
        self.mix = mix
        self.sample_rate = sample_rate
        self._buffer = [0.0] * (sample_rate // 2)
        self._write_pos = 0
        self._phase = 0.0

    def process_sample(self, x: float) -> float:
        buf_size = len(self._buffer)
        self._buffer[self._write_pos] = x

        # LFO modulated delay
        lfo = math.sin(2 * math.pi * self._phase) * self.depth
        delay_samples = int((5.0 + lfo * 5.0) * self.sample_rate / 1000.0)
        delay_samples = max(1, min(delay_samples, buf_size - 1))

        read_pos = (self._write_pos - delay_samples) % buf_size
        delayed = self._buffer[read_pos]

        self._write_pos = (self._write_pos + 1) % buf_size
        self._phase += self.rate / self.sample_rate

        return x * (1.0 - self.mix) + delayed * self.mix

    def process(self, signal: list[float]) -> list[float]:
        return [self.process_sample(x) for x in signal]


class LivePhaser:
    """All-pass based phaser."""

    def __init__(self, rate: float = 0.5,
                 depth: float = 0.7,
                 stages: int = 4,
                 feedback: float = 0.3,
                 sample_rate: int = SAMPLE_RATE):
        self.rate = rate
        self.depth = depth
        self.stages = stages
        self.feedback = min(feedback, 0.95)
        self.sample_rate = sample_rate
        self._phase = 0.0
        self._prev = [0.0] * stages
        self._fb_sample = 0.0

    def process_sample(self, x: float) -> float:
        # LFO
        lfo = (math.sin(2 * math.pi * self._phase) + 1) * 0.5
        self._phase += self.rate / self.sample_rate

        # All-pass chain
        freq = 200 + lfo * self.depth * 4000
        w = 2 * math.pi * freq / self.sample_rate
        coeff = (1.0 - math.tan(w / 2)) / (1.0 + math.tan(w / 2))

        sample = x + self._fb_sample * self.feedback
        for i in range(self.stages):
            ap_out = coeff * (sample - self._prev[i]) + sample
            self._prev[i] = sample
            sample = ap_out

        self._fb_sample = sample
        return x * 0.5 + sample * 0.5

    def process(self, signal: list[float]) -> list[float]:
        return [self.process_sample(x) for x in signal]


@dataclass
class FXChain:
    """A chain of effects."""
    effects: list[object] = None  # type: ignore[assignment]
    name: str = "FX Chain"

    def __post_init__(self):
        if self.effects is None:
            self.effects = []

    def add(self, fx: object) -> None:
        self.effects.append(fx)

    def process(self, signal: list[float]) -> list[float]:
        result = signal
        for fx in self.effects:
            if hasattr(fx, 'process'):
                result = fx.process(result)  # type: ignore[union-attr]
        return result


def create_dubstep_fx_chain(bpm: float = 140.0) -> FXChain:
    """Create a standard dubstep FX chain."""
    chain = FXChain(name="Dubstep FX")

    # Lowpass filter
    chain.add(LiveFilter(cutoff=2000.0, resonance=0.4))

    # Distortion
    chain.add(LiveDistortion(drive=0.4, mode="tanh", mix=0.6))

    # Tempo-synced delay
    delay = LiveDelay(feedback=0.4, mix=0.25)
    delay.set_delay_beats(bpm, 0.375)  # Dotted 8th
    chain.add(delay)

    # Chorus
    chain.add(LiveChorus(rate=PHI, depth=0.3, mix=0.15))

    return chain


def main() -> None:
    print("Live FX Processor Engine")

    # Generate test signal
    signal = [
        math.sin(2 * math.pi * 80 * i / SAMPLE_RATE) * 0.5
        for i in range(SAMPLE_RATE)
    ]

    # Individual effects
    filt = LiveFilter(800.0, 0.6)
    filtered = filt.process(signal)
    print(f"  Filter: {len(filtered)} samples")

    delay = LiveDelay(300, 0.5, 0.3)
    delayed = delay.process(signal)
    print(f"  Delay: {len(delayed)} samples")

    dist = LiveDistortion(0.5, "tanh")
    distorted = dist.process(signal)
    print(f"  Distortion: {len(distorted)} samples")

    chorus = LiveChorus(1.0, 0.5, 0.3)
    chorused = chorus.process(signal)
    print(f"  Chorus: {len(chorused)} samples")

    phaser = LivePhaser(0.5, 0.7, 4, 0.3)
    phased = phaser.process(signal)
    print(f"  Phaser: {len(phased)} samples")

    # Full chain
    chain = create_dubstep_fx_chain(140.0)
    processed = chain.process(signal)
    print(f"  FX Chain: {len(processed)} samples")

    print("Done.")


if __name__ == "__main__":
    main()
