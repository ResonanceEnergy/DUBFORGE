"""
DUBFORGE — Tempo Sync Engine  (Session 174)

BPM detection, tempo synchronization, and beat-locked
timing utilities for the DUBFORGE pipeline.
"""

import math
from dataclasses import dataclass

PHI = 1.6180339887
SAMPLE_RATE = 44100

# Standard dubstep BPM ranges
BPM_RANGES: dict[str, tuple[float, float]] = {
    "dubstep": (138.0, 150.0),
    "riddim": (140.0, 150.0),
    "dnb": (170.0, 180.0),
    "trap": (130.0, 145.0),
    "house": (120.0, 130.0),
    "halftime": (70.0, 75.0),
}


@dataclass
class BeatGrid:
    """A quantized beat grid."""
    bpm: float
    offset_samples: int = 0
    time_signature_num: int = 4
    time_signature_den: int = 4

    @property
    def beat_duration_s(self) -> float:
        return 60.0 / self.bpm

    @property
    def beat_duration_samples(self) -> int:
        return int(self.beat_duration_s * SAMPLE_RATE)

    @property
    def bar_duration_s(self) -> float:
        return self.beat_duration_s * self.time_signature_num

    @property
    def bar_duration_samples(self) -> int:
        return int(self.bar_duration_s * SAMPLE_RATE)

    def beat_at(self, beat_number: int) -> int:
        """Sample position of beat N."""
        return self.offset_samples + beat_number * self.beat_duration_samples

    def bar_at(self, bar_number: int) -> int:
        """Sample position of bar N."""
        return self.offset_samples + bar_number * self.bar_duration_samples

    def nearest_beat(self, sample_pos: int) -> int:
        """Snap to nearest beat."""
        relative = sample_pos - self.offset_samples
        beat_len = self.beat_duration_samples
        if beat_len <= 0:
            return sample_pos
        beat_idx = round(relative / beat_len)
        return self.beat_at(beat_idx)

    def nearest_subdivision(self, sample_pos: int,
                             subdivision: int = 4) -> int:
        """Snap to nearest subdivision (e.g., 16th = 4)."""
        sub_len = self.beat_duration_samples // max(subdivision, 1)
        if sub_len <= 0:
            return sample_pos
        relative = sample_pos - self.offset_samples
        sub_idx = round(relative / sub_len)
        return self.offset_samples + sub_idx * sub_len


@dataclass
class TempoEvent:
    """A tempo change event."""
    sample_pos: int
    bpm: float

    @property
    def time_s(self) -> float:
        return self.sample_pos / SAMPLE_RATE


@dataclass
class TempoMap:
    """Multi-tempo map."""
    events: list[TempoEvent]

    def bpm_at(self, sample_pos: int) -> float:
        """Get BPM at a sample position."""
        if not self.events:
            return 140.0
        result = self.events[0].bpm
        for ev in self.events:
            if ev.sample_pos <= sample_pos:
                result = ev.bpm
            else:
                break
        return result

    def beat_position(self, sample_pos: int) -> float:
        """Get beat number at a sample position (float)."""
        if not self.events:
            return sample_pos / SAMPLE_RATE * 140.0 / 60.0

        beats = 0.0
        prev_pos = 0
        prev_bpm = self.events[0].bpm

        for ev in self.events:
            if ev.sample_pos >= sample_pos:
                break
            dt = (ev.sample_pos - prev_pos) / SAMPLE_RATE
            beats += dt * prev_bpm / 60.0
            prev_pos = ev.sample_pos
            prev_bpm = ev.bpm

        dt = (sample_pos - prev_pos) / SAMPLE_RATE
        beats += dt * prev_bpm / 60.0
        return beats


def detect_bpm(signal: list[float],
               sample_rate: int = SAMPLE_RATE,
               min_bpm: float = 60.0,
               max_bpm: float = 200.0) -> float:
    """Detect BPM using onset autocorrelation."""
    if len(signal) < sample_rate:
        return 140.0

    # Create onset envelope
    block_size = int(sample_rate * 0.01)  # 10ms
    n_blocks = len(signal) // block_size
    envelope: list[float] = []

    for i in range(n_blocks):
        start = i * block_size
        end = start + block_size
        rms = math.sqrt(
            sum(x * x for x in signal[start:end]) / block_size
        )
        envelope.append(rms)

    if len(envelope) < 10:
        return 140.0

    # Onset detection function (spectral flux approximation)
    onset = [0.0]
    for i in range(1, len(envelope)):
        diff = max(0, envelope[i] - envelope[i - 1])
        onset.append(diff)

    # Autocorrelation on onset signal
    min_lag = int(60.0 / max_bpm * 100)  # 100 blocks/s
    max_lag = int(60.0 / min_bpm * 100)
    max_lag = min(max_lag, len(onset) // 2)

    if min_lag >= max_lag:
        return 140.0

    best_lag = min_lag
    best_corr = -1.0
    n = len(onset)
    mean = sum(onset) / n

    for lag in range(min_lag, max_lag):
        corr = sum(
            (onset[i] - mean) * (onset[i + lag] - mean)
            for i in range(n - lag)
        )
        if corr > best_corr:
            best_corr = corr
            best_lag = lag

    # Convert lag to BPM
    block_rate = 1.0 / 0.01  # 100 blocks/s
    period_s = best_lag / block_rate
    if period_s > 0:
        bpm = 60.0 / period_s
    else:
        bpm = 140.0

    # Octave correction (prefer dubstep range)
    while bpm < 100:
        bpm *= 2
    while bpm > 200:
        bpm /= 2

    return round(bpm, 1)


def time_stretch_factor(original_bpm: float, target_bpm: float) -> float:
    """Calculate time-stretch factor to match target BPM."""
    if original_bpm <= 0:
        return 1.0
    return target_bpm / original_bpm


def beat_delay_ms(bpm: float, subdivision: float = 1.0) -> float:
    """Calculate delay time for a rhythmic subdivision."""
    if bpm <= 0:
        return 0.0
    beat_ms = 60000.0 / bpm
    return beat_ms * subdivision


def phi_delay_ms(bpm: float) -> float:
    """PHI-ratio delay time (golden ratio of beat)."""
    return beat_delay_ms(bpm, 1.0 / PHI)


def sync_to_grid(signal: list[float], grid: BeatGrid,
                  target_length_beats: int = 4) -> list[float]:
    """Trim/pad signal to align with beat grid."""
    target_samples = target_length_beats * grid.beat_duration_samples
    if len(signal) >= target_samples:
        return signal[:target_samples]
    else:
        return signal + [0.0] * (target_samples - len(signal))


def create_click_track(bpm: float, duration_s: float,
                        sample_rate: int = SAMPLE_RATE) -> list[float]:
    """Generate a click track at given BPM."""
    n = int(duration_s * sample_rate)
    signal = [0.0] * n
    beat_samples = int(60.0 / bpm * sample_rate)

    if beat_samples <= 0:
        return signal

    click_len = min(int(sample_rate * 0.01), beat_samples)

    pos = 0
    beat_num = 0
    while pos < n:
        freq = 1000.0 if beat_num % 4 == 0 else 800.0
        amp = 0.8 if beat_num % 4 == 0 else 0.5
        for i in range(min(click_len, n - pos)):
            t = i / sample_rate
            env = 1.0 - i / click_len
            signal[pos + i] = amp * env * math.sin(2 * math.pi * freq * t)
        pos += beat_samples
        beat_num += 1

    return signal


def main() -> None:
    print("Tempo Sync Engine")

    # BPM detection test with known tempo signal
    grid = BeatGrid(bpm=140.0)
    click = create_click_track(140.0, 4.0)
    detected = detect_bpm(click)
    print(f"  Generated: 140 BPM, Detected: {detected} BPM")

    # Beat grid
    print(f"  Beat duration: {grid.beat_duration_s:.4f}s "
          f"({grid.beat_duration_samples} samples)")
    print(f"  Bar duration: {grid.bar_duration_s:.4f}s")
    print(f"  Beat 4 at sample: {grid.beat_at(4)}")

    # PHI delay
    print(f"  PHI delay at 140 BPM: {phi_delay_ms(140.0):.1f}ms")
    print(f"  1/4 note: {beat_delay_ms(140.0, 1.0):.1f}ms")
    print(f"  1/8 note: {beat_delay_ms(140.0, 0.5):.1f}ms")

    # Tempo map
    tmap = TempoMap([
        TempoEvent(0, 140.0),
        TempoEvent(SAMPLE_RATE * 8, 150.0),
    ])
    print(f"  BPM at 0s: {tmap.bpm_at(0)}")
    print(f"  BPM at 10s: {tmap.bpm_at(SAMPLE_RATE * 10)}")
    print("Done.")


if __name__ == "__main__":
    main()
