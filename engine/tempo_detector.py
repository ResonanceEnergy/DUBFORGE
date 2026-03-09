"""
DUBFORGE — Tempo Detector  (Session 216)

BPM detection from audio using onset analysis,
auto-correlation, and PHI tempo relationships.
"""

import math
from dataclasses import dataclass

PHI = 1.6180339887
SAMPLE_RATE = 48000

DUBSTEP_BPM_RANGE = (130, 155)
COMMON_TEMPOS = [70, 75, 80, 85, 90, 100, 110, 120, 125, 128, 130,
                 135, 140, 145, 150, 155, 160, 170, 174, 175, 180]


@dataclass
class TempoResult:
    """Tempo detection result."""
    bpm: float
    confidence: float
    beat_positions: list[float]  # in seconds
    half_time: float
    double_time: float
    phi_tempo: float

    def to_dict(self) -> dict:
        return {
            "bpm": round(self.bpm, 1),
            "confidence": round(self.confidence, 3),
            "beat_count": len(self.beat_positions),
            "half_time": round(self.half_time, 1),
            "double_time": round(self.double_time, 1),
            "phi_tempo": round(self.phi_tempo, 1),
        }


class TempoDetector:
    """Detect tempo and beats from audio."""

    def __init__(self, sample_rate: int = SAMPLE_RATE):
        self.sample_rate = sample_rate

    def _onset_function(self, samples: list[float],
                        hop_size: int = 512) -> list[float]:
        """Compute onset strength function."""
        onsets: list[float] = []
        prev_energy = 0.0

        for i in range(0, len(samples) - hop_size, hop_size):
            chunk = samples[i:i + hop_size]
            energy = sum(s * s for s in chunk) / hop_size
            # Onset = positive energy derivative
            onset = max(0, energy - prev_energy)
            onsets.append(onset)
            prev_energy = energy

        return onsets

    def _autocorrelate(self, signal: list[float],
                       min_lag: int, max_lag: int) -> list[tuple[int, float]]:
        """Compute autocorrelation for lag range."""
        n = len(signal)
        results: list[tuple[int, float]] = []

        for lag in range(min_lag, min(max_lag, n)):
            corr = sum(
                signal[i] * signal[i + lag]
                for i in range(n - lag)
            )
            norm = math.sqrt(
                sum(signal[i] ** 2 for i in range(n - lag)) *
                sum(signal[i + lag] ** 2 for i in range(n - lag))
            )
            results.append((lag, corr / norm if norm > 0 else 0))

        return results

    def detect(self, samples: list[float],
               bpm_range: tuple[float, float] = (60, 200)) -> TempoResult:
        """Detect BPM from audio."""
        if len(samples) < self.sample_rate:
            return TempoResult(
                bpm=140.0, confidence=0, beat_positions=[],
                half_time=70, double_time=280, phi_tempo=140 * PHI,
            )

        hop = 512
        onsets = self._onset_function(samples, hop)

        if not onsets:
            return TempoResult(
                bpm=140.0, confidence=0, beat_positions=[],
                half_time=70, double_time=280, phi_tempo=140 * PHI,
            )

        # BPM to lag conversion
        onset_sr = self.sample_rate / hop
        min_lag = max(1, int(onset_sr * 60 / bpm_range[1]))
        max_lag = int(onset_sr * 60 / bpm_range[0])

        correlations = self._autocorrelate(onsets, min_lag, max_lag)

        if not correlations:
            return TempoResult(
                bpm=140.0, confidence=0, beat_positions=[],
                half_time=70, double_time=280, phi_tempo=140 * PHI,
            )

        # Find peak
        best_lag, best_corr = max(correlations, key=lambda x: x[1])
        bpm = 60 * onset_sr / best_lag

        # Snap to nearest common tempo if close
        for common in COMMON_TEMPOS:
            if abs(bpm - common) < 1.5:
                bpm = float(common)
                break

        # Confidence: strength of autocorrelation peak
        confidence = min(1.0, max(0.0, best_corr))

        # Find beat positions
        beats = self._find_beats(onsets, best_lag, hop)

        return TempoResult(
            bpm=bpm,
            confidence=confidence,
            beat_positions=beats,
            half_time=bpm / 2,
            double_time=bpm * 2,
            phi_tempo=bpm * PHI,
        )

    def _find_beats(self, onsets: list[float],
                    period_frames: int,
                    hop_size: int) -> list[float]:
        """Find beat positions from onset function."""
        if not onsets or period_frames <= 0:
            return []

        beats: list[float] = []
        threshold = max(onsets) * 0.3 if onsets else 0

        # Look for peaks near expected beat positions
        for start_offset in range(min(period_frames, len(onsets))):
            pos = start_offset
            beat_count = 0
            while pos < len(onsets):
                # Search window around expected position
                window = max(1, period_frames // 4)
                search_start = max(0, pos - window)
                search_end = min(len(onsets), pos + window + 1)

                # Find strongest onset in window
                best_idx = search_start
                best_val = 0.0
                for i in range(search_start, search_end):
                    if onsets[i] > best_val:
                        best_val = onsets[i]
                        best_idx = i

                if best_val > threshold:
                    time_s = best_idx * hop_size / self.sample_rate
                    if not beats or time_s - beats[-1] > 0.1:
                        beats.append(time_s)
                        beat_count += 1

                pos += period_frames

            if beat_count >= 4:
                break

        return beats

    def phi_related_tempos(self, bpm: float, count: int = 5) -> list[float]:
        """Generate PHI-related tempo suggestions."""
        tempos: list[float] = [bpm]
        t = bpm
        for _ in range(count):
            t = t * PHI
            if t <= 300:
                tempos.append(round(t, 1))
        t = bpm
        for _ in range(count):
            t = t / PHI
            if t >= 40:
                tempos.append(round(t, 1))
        return sorted(tempos)

    def is_dubstep_tempo(self, bpm: float) -> bool:
        """Check if BPM is in dubstep range."""
        return DUBSTEP_BPM_RANGE[0] <= bpm <= DUBSTEP_BPM_RANGE[1]

    def suggest_tempo(self, bpm: float) -> dict:
        """Suggest related tempos and metadata."""
        return {
            "detected_bpm": round(bpm, 1),
            "half_time": round(bpm / 2, 1),
            "double_time": round(bpm * 2, 1),
            "triplet_feel": round(bpm * 2 / 3, 1),
            "phi_tempo": round(bpm * PHI, 1),
            "is_dubstep": self.is_dubstep_tempo(bpm),
            "nearest_common": min(COMMON_TEMPOS,
                                  key=lambda t: abs(t - bpm)),
            "phi_related": self.phi_related_tempos(bpm, 3),
        }


def main() -> None:
    print("Tempo Detector")
    detector = TempoDetector()

    # Generate 140 BPM click track
    bpm = 140.0
    beat_interval = int(60 / bpm * SAMPLE_RATE)
    duration = 8  # seconds
    n = SAMPLE_RATE * duration
    samples: list[float] = [0.0] * n

    for beat in range(int(duration * bpm / 60)):
        pos = beat * beat_interval
        # Short click
        for i in range(min(200, n - pos)):
            t = i / SAMPLE_RATE
            samples[pos + i] = 0.9 * math.sin(2 * math.pi * 1000 * t) * \
                max(0, 1 - t * 50)

    result = detector.detect(samples)
    d = result.to_dict()
    print(f"  Detected BPM: {d['bpm']}")
    print(f"  Confidence: {d['confidence']}")
    print(f"  Beats found: {d['beat_count']}")

    info = detector.suggest_tempo(result.bpm)
    print(f"  Is dubstep: {info['is_dubstep']}")
    print(f"  PHI related: {info['phi_related']}")

    print("Done.")


if __name__ == "__main__":
    main()
