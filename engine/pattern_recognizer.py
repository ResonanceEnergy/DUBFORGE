"""
DUBFORGE — Pattern Recognizer Engine  (Session 173)

Analyzes audio signals for rhythmic and spectral patterns,
detecting repetitions and motifs with PHI-ratio awareness.
"""

import math
from dataclasses import dataclass, field

PHI = 1.6180339887
A4_432 = 432.0
SAMPLE_RATE = 48000


@dataclass
class PatternMatch:
    """A detected pattern match."""
    start_sample: int
    length_samples: int
    repeat_count: int
    confidence: float
    pattern_type: str  # "rhythmic", "melodic", "spectral"

    @property
    def start_s(self) -> float:
        return self.start_sample / SAMPLE_RATE

    @property
    def length_s(self) -> float:
        return self.length_samples / SAMPLE_RATE

    def to_dict(self) -> dict:
        return {
            "start_s": round(self.start_s, 3),
            "length_s": round(self.length_s, 3),
            "repeats": self.repeat_count,
            "confidence": round(self.confidence, 3),
            "type": self.pattern_type,
        }


@dataclass
class PatternProfile:
    """Overall pattern analysis of a signal."""
    patterns: list[PatternMatch] = field(default_factory=list)
    rhythm_score: float = 0.0
    complexity: float = 0.0
    phi_alignment: float = 0.0
    dominant_period_s: float = 0.0

    def to_dict(self) -> dict:
        return {
            "pattern_count": len(self.patterns),
            "rhythm_score": round(self.rhythm_score, 3),
            "complexity": round(self.complexity, 3),
            "phi_alignment": round(self.phi_alignment, 3),
            "dominant_period_s": round(self.dominant_period_s, 4),
            "patterns": [p.to_dict() for p in self.patterns[:10]],
        }


def _rms_block(signal: list[float], start: int, length: int) -> float:
    """Compute RMS of a block."""
    end = min(start + length, len(signal))
    if end <= start:
        return 0.0
    s = sum(x * x for x in signal[start:end])
    return math.sqrt(s / (end - start))


def _autocorrelation(signal: list[float], max_lag: int) -> list[float]:
    """Compute normalized autocorrelation."""
    n = len(signal)
    if n == 0:
        return []

    mean = sum(signal) / n
    var = sum((x - mean) ** 2 for x in signal) / n
    if var < 1e-10:
        return [0.0] * max_lag

    result = []
    for lag in range(max_lag):
        if lag >= n:
            result.append(0.0)
            continue
        s = sum(
            (signal[i] - mean) * (signal[i + lag] - mean)
            for i in range(n - lag)
        )
        result.append(s / (n * var))

    return result


def detect_rhythmic_patterns(signal: list[float],
                              bpm: float = 140.0,
                              sample_rate: int = SAMPLE_RATE) -> list[PatternMatch]:
    """Detect repeating rhythmic patterns using onset-based envelope."""
    if len(signal) < sample_rate:
        return []

    # Create onset envelope
    block_size = int(sample_rate * 0.01)  # 10ms blocks
    n_blocks = len(signal) // block_size
    envelope = []
    for i in range(n_blocks):
        rms = _rms_block(signal, i * block_size, block_size)
        envelope.append(rms)

    if not envelope:
        return []

    # Detect onsets (rising envelope)
    threshold = max(envelope) * 0.2
    onsets = []
    for i in range(1, len(envelope)):
        if envelope[i] > threshold and envelope[i] > envelope[i - 1] * 1.5:
            onsets.append(i)

    if len(onsets) < 3:
        return []

    # Find repeating intervals
    intervals = [onsets[i + 1] - onsets[i] for i in range(len(onsets) - 1)]

    # Group similar intervals
    patterns: list[PatternMatch] = []
    interval_counts: dict[int, int] = {}
    tolerance = 2  # blocks

    for iv in intervals:
        found = False
        for key in interval_counts:
            if abs(iv - key) <= tolerance:
                interval_counts[key] += 1
                found = True
                break
        if not found:
            interval_counts[iv] = 1

    for interval_blocks, count in interval_counts.items():
        if count >= 2:
            confidence = min(1.0, count / len(intervals) * 2)
            patterns.append(PatternMatch(
                start_sample=0,
                length_samples=interval_blocks * block_size,
                repeat_count=count,
                confidence=confidence,
                pattern_type="rhythmic",
            ))

    patterns.sort(key=lambda p: p.confidence, reverse=True)
    return patterns[:8]


def detect_spectral_patterns(signal: list[float],
                              window_size: int = 2048,
                              sample_rate: int = SAMPLE_RATE) -> list[PatternMatch]:
    """Detect repeating spectral moments using DFT snapshots."""
    if len(signal) < window_size * 4:
        return []

    hop = window_size // 2
    spectra: list[list[float]] = []

    for pos in range(0, len(signal) - window_size, hop):
        # Simple magnitude spectrum
        chunk = signal[pos:pos + window_size]
        # Band energy in 4 bands
        bands = [0.0, 0.0, 0.0, 0.0]
        quarter = window_size // 4
        for b in range(4):
            start = b * quarter
            end = start + quarter
            bands[b] = sum(x * x for x in chunk[start:end])
        spectra.append(bands)

    if len(spectra) < 4:
        return []

    # Find repeating spectral fingerprints
    patterns: list[PatternMatch] = []
    n_spectra = len(spectra)

    for period in range(2, min(n_spectra // 2, 32)):
        match_count = 0
        total_sim = 0.0

        for i in range(n_spectra - period):
            # Cosine similarity between spectral snapshots
            a = spectra[i]
            b = spectra[i + period]
            dot = sum(x * y for x, y in zip(a, b))
            mag_a = math.sqrt(sum(x * x for x in a) + 1e-10)
            mag_b = math.sqrt(sum(x * x for x in b) + 1e-10)
            sim = dot / (mag_a * mag_b)

            if sim > 0.9:
                match_count += 1
            total_sim += sim

        avg_sim = total_sim / max(n_spectra - period, 1)
        if match_count >= 3 and avg_sim > 0.7:
            patterns.append(PatternMatch(
                start_sample=0,
                length_samples=period * hop,
                repeat_count=match_count,
                confidence=avg_sim,
                pattern_type="spectral",
            ))

    patterns.sort(key=lambda p: p.confidence, reverse=True)
    return patterns[:5]


def measure_phi_alignment(patterns: list[PatternMatch],
                           bpm: float = 140.0) -> float:
    """Measure how closely patterns align with PHI ratios."""
    if not patterns:
        return 0.0

    beat_s = 60.0 / bpm
    phi_periods = [beat_s * (PHI ** i) for i in range(-3, 4)]

    alignment_scores = []
    for p in patterns:
        best_match = 1.0
        for phi_p in phi_periods:
            if phi_p > 0:
                ratio = p.length_s / phi_p
                # How close to a PHI power?
                log_ratio = abs(math.log(max(ratio, 1e-10)) / math.log(PHI))
                nearest = round(log_ratio)
                diff = abs(log_ratio - nearest)
                best_match = min(best_match, diff)
        alignment_scores.append(max(0, 1.0 - best_match))

    return sum(alignment_scores) / len(alignment_scores) if alignment_scores else 0.0


def analyze_patterns(signal: list[float],
                      bpm: float = 140.0,
                      sample_rate: int = SAMPLE_RATE) -> PatternProfile:
    """Full pattern analysis."""
    rhythmic = detect_rhythmic_patterns(signal, bpm, sample_rate)
    spectral = detect_spectral_patterns(signal, 2048, sample_rate)
    all_patterns = rhythmic + spectral

    # Dominant period
    if all_patterns:
        best = max(all_patterns, key=lambda p: p.confidence)
        dominant_period = best.length_s
    else:
        dominant_period = 0.0

    # Rhythm score
    if rhythmic:
        rhythm_score = sum(p.confidence for p in rhythmic) / len(rhythmic)
    else:
        rhythm_score = 0.0

    # Complexity
    unique_periods = len({p.length_samples for p in all_patterns})
    complexity = min(1.0, unique_periods / 8.0)

    # PHI alignment
    phi_align = measure_phi_alignment(all_patterns, bpm)

    return PatternProfile(
        patterns=all_patterns,
        rhythm_score=rhythm_score,
        complexity=complexity,
        phi_alignment=phi_align,
        dominant_period_s=dominant_period,
    )


def main() -> None:
    print("Pattern Recognizer Engine")

    # Generate test signal with repeating pattern
    import random
    rng = random.Random(42)
    signal: list[float] = []
    pattern_len = int(SAMPLE_RATE * 0.5)  # 0.5s pattern

    # Create a base pattern
    base = [math.sin(2 * math.pi * 80 * i / SAMPLE_RATE)
            * (1.0 if (i % 4410) < 2205 else 0.1)
            for i in range(pattern_len)]

    # Repeat it
    for _ in range(8):
        signal.extend(base)
        signal.extend([rng.gauss(0, 0.01) for _ in range(100)])

    profile = analyze_patterns(signal, 140.0)
    print(f"  Patterns found: {len(profile.patterns)}")
    print(f"  Rhythm score: {profile.rhythm_score:.3f}")
    print(f"  Complexity: {profile.complexity:.3f}")
    print(f"  PHI alignment: {profile.phi_alignment:.3f}")
    print(f"  Dominant period: {profile.dominant_period_s:.4f}s")
    print("Done.")


if __name__ == "__main__":
    main()
