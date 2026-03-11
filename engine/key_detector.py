"""
DUBFORGE — Key/Scale Detector  (Session 209)

Detect musical key and scale from audio using
chromagram analysis (DFT-based pitch class profiling).
"""

import math
from dataclasses import dataclass

from engine.config_loader import PHI, A4_432
SAMPLE_RATE = 48000
NOTE_NAMES = ["C", "C#", "D", "D#", "E", "F",
              "F#", "G", "G#", "A", "A#", "B"]

# Scale profiles (Krumhansl-Kessler key profiles simplified)
MAJOR_PROFILE = [6.35, 2.23, 3.48, 2.33, 4.38, 4.09,
                 2.52, 5.19, 2.39, 3.66, 2.29, 2.88]
MINOR_PROFILE = [6.33, 2.68, 3.52, 5.38, 2.60, 3.53,
                 2.54, 4.75, 3.98, 2.69, 3.34, 3.17]

SCALE_INTERVALS = {
    "major": [0, 2, 4, 5, 7, 9, 11],
    "natural_minor": [0, 2, 3, 5, 7, 8, 10],
    "harmonic_minor": [0, 2, 3, 5, 7, 8, 11],
    "melodic_minor": [0, 2, 3, 5, 7, 9, 11],
    "dorian": [0, 2, 3, 5, 7, 9, 10],
    "phrygian": [0, 1, 3, 5, 7, 8, 10],
    "lydian": [0, 2, 4, 6, 7, 9, 11],
    "mixolydian": [0, 2, 4, 5, 7, 9, 10],
    "locrian": [0, 1, 3, 5, 6, 8, 10],
    "pentatonic_major": [0, 2, 4, 7, 9],
    "pentatonic_minor": [0, 3, 5, 7, 10],
    "blues": [0, 3, 5, 6, 7, 10],
    "whole_tone": [0, 2, 4, 6, 8, 10],
    "chromatic": list(range(12)),
}


@dataclass
class KeyResult:
    """Key detection result."""
    key: str
    mode: str  # major, minor
    confidence: float
    correlation: float
    chromagram: list[float]

    @property
    def key_name(self) -> str:
        return f"{self.key} {self.mode}"

    def to_dict(self) -> dict:
        return {
            "key": self.key,
            "mode": self.mode,
            "key_name": self.key_name,
            "confidence": round(self.confidence, 3),
            "correlation": round(self.correlation, 3),
            "chromagram": [round(c, 4) for c in self.chromagram],
        }


@dataclass
class ScaleMatch:
    """Scale matching result."""
    scale_name: str
    root: str
    score: float
    notes: list[str]

    def to_dict(self) -> dict:
        return {
            "scale": self.scale_name,
            "root": self.root,
            "score": round(self.score, 3),
            "notes": self.notes,
        }


class KeyDetector:
    """Detect key and scale from audio."""

    def __init__(self, sample_rate: int = SAMPLE_RATE,
                 reference_freq: float = A4_432):
        self.sample_rate = sample_rate
        self.reference_freq = reference_freq

    def _compute_chromagram(self, samples: list[float],
                            fft_size: int = 4096) -> list[float]:
        """Compute chromagram (pitch class energy distribution)."""
        # Use DFT to find energy at each pitch class
        chroma = [0.0] * 12

        # Analyze multiple octaves
        for octave in range(1, 8):
            for pc in range(12):
                # Note frequency
                midi = 12 + octave * 12 + pc  # C1 = midi 24
                freq = self.reference_freq * (
                    2 ** ((midi - 69) / 12)
                )

                if freq >= self.sample_rate / 2:
                    continue

                # Goertzel-like: compute DFT at specific frequency
                k = freq * fft_size / self.sample_rate
                n = min(len(samples), fft_size)

                real = 0.0
                imag = 0.0
                for i in range(n):
                    angle = 2 * math.pi * k * i / fft_size
                    real += samples[i] * math.cos(angle)
                    imag -= samples[i] * math.sin(angle)

                magnitude = math.sqrt(real * real + imag * imag) / n
                chroma[pc] += magnitude * magnitude

        # Normalize
        total = sum(chroma)
        if total > 0:
            chroma = [c / total for c in chroma]

        return chroma

    def _correlate_profile(self, chroma: list[float],
                           profile: list[float],
                           rotation: int) -> float:
        """Correlate chromagram with rotated profile."""
        n = len(profile)
        rotated = [profile[(i - rotation) % n] for i in range(n)]

        # Pearson correlation
        mean_c = sum(chroma) / n
        mean_p = sum(rotated) / n

        num = sum((chroma[i] - mean_c) * (rotated[i] - mean_p)
                  for i in range(n))
        den_c = math.sqrt(sum((c - mean_c) ** 2 for c in chroma))
        den_p = math.sqrt(sum((p - mean_p) ** 2 for p in rotated))

        if den_c * den_p == 0:
            return 0.0
        return num / (den_c * den_p)

    def detect_key(self, samples: list[float],
                   fft_size: int = 4096) -> KeyResult:
        """Detect key from audio samples."""
        if not samples:
            return KeyResult("C", "major", 0, 0, [0] * 12)

        chroma = self._compute_chromagram(samples, fft_size)

        best_corr = -1.0
        best_key = 0
        best_mode = "major"

        # Test all keys and modes
        for rotation in range(12):
            # Major
            corr_maj = self._correlate_profile(
                chroma, MAJOR_PROFILE, rotation
            )
            if corr_maj > best_corr:
                best_corr = corr_maj
                best_key = rotation
                best_mode = "major"

            # Minor
            corr_min = self._correlate_profile(
                chroma, MINOR_PROFILE, rotation
            )
            if corr_min > best_corr:
                best_corr = corr_min
                best_key = rotation
                best_mode = "minor"

        # Confidence: gap between best and second best
        second_best = -1.0
        for rotation in range(12):
            for profile, mode in [(MAJOR_PROFILE, "major"),
                                   (MINOR_PROFILE, "minor")]:
                if rotation == best_key and mode == best_mode:
                    continue
                corr = self._correlate_profile(chroma, profile, rotation)
                if corr > second_best:
                    second_best = corr

        confidence = best_corr - second_best if second_best >= 0 else best_corr

        return KeyResult(
            key=NOTE_NAMES[best_key],
            mode=best_mode,
            confidence=min(1.0, max(0.0, confidence * 5)),
            correlation=best_corr,
            chromagram=chroma,
        )

    def detect_scale(self, samples: list[float],
                     top_n: int = 5) -> list[ScaleMatch]:
        """Detect best matching scales."""
        if not samples:
            return []

        chroma = self._compute_chromagram(samples)
        results: list[ScaleMatch] = []

        for root_idx in range(12):
            for scale_name, intervals in SCALE_INTERVALS.items():
                # Score: sum of chroma energy on scale degrees
                score = sum(
                    chroma[(root_idx + i) % 12] for i in intervals
                )
                # Penalize energy not on scale
                off_scale = sum(
                    chroma[(root_idx + i) % 12]
                    for i in range(12) if i not in intervals
                )
                score -= off_scale * 0.5

                notes = [NOTE_NAMES[(root_idx + i) % 12]
                          for i in intervals]

                results.append(ScaleMatch(
                    scale_name=scale_name,
                    root=NOTE_NAMES[root_idx],
                    score=score,
                    notes=notes,
                ))

        results.sort(key=lambda r: r.score, reverse=True)
        return results[:top_n]

    def get_scale_notes(self, root: str,
                        scale: str = "major") -> list[str]:
        """Get notes in a scale."""
        intervals = SCALE_INTERVALS.get(scale, SCALE_INTERVALS["major"])
        root_idx = NOTE_NAMES.index(root) if root in NOTE_NAMES else 0
        return [NOTE_NAMES[(root_idx + i) % 12] for i in intervals]

    def get_relative_key(self, key: str, mode: str) -> tuple[str, str]:
        """Get relative major/minor key."""
        idx = NOTE_NAMES.index(key) if key in NOTE_NAMES else 0
        if mode == "major":
            # Relative minor is 3 semitones down
            return NOTE_NAMES[(idx - 3) % 12], "minor"
        else:
            return NOTE_NAMES[(idx + 3) % 12], "major"

    def get_parallel_key(self, key: str, mode: str) -> tuple[str, str]:
        """Get parallel key (same root, different mode)."""
        return key, "minor" if mode == "major" else "major"


def main() -> None:
    print("Key/Scale Detector")

    detector = KeyDetector()

    # Generate A minor chord (A=432, C=~257, E=~324)
    n = SAMPLE_RATE * 2
    samples: list[float] = []
    a_freq = 432.0
    c_freq = a_freq * 2 ** (-9 / 12)  # C
    e_freq = a_freq * 2 ** (-5 / 12)  # E

    for i in range(n):
        t = i / SAMPLE_RATE
        s = (0.4 * math.sin(2 * math.pi * a_freq * t) +
             0.3 * math.sin(2 * math.pi * c_freq * t) +
             0.3 * math.sin(2 * math.pi * e_freq * t))
        samples.append(s)

    # Detect
    result = detector.detect_key(samples)
    print(f"  Key: {result.key_name}")
    print(f"  Confidence: {result.confidence:.3f}")
    print(f"  Correlation: {result.correlation:.3f}")

    # Scale matching
    scales = detector.detect_scale(samples, 3)
    print("\n  Top scales:")
    for s in scales:
        print(f"    {s.root} {s.scale_name}: {s.score:.3f}")

    # Relative key
    rel = detector.get_relative_key(result.key, result.mode)
    print(f"\n  Relative: {rel[0]} {rel[1]}")

    print("Done.")


if __name__ == "__main__":
    main()
