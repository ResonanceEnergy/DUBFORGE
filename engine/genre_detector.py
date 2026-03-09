"""
DUBFORGE — Genre Detector Engine  (Session 154)

Audio genre classification using spectral feature analysis.
Pure Python — analyses frequency content, tempo, and dynamics
to classify dubstep sub-genres and related styles.
"""

import math
from dataclasses import dataclass, field

PHI = 1.6180339887
SAMPLE_RATE = 44100


@dataclass
class GenreProfile:
    """Spectral profile for a genre."""
    name: str
    bpm_range: tuple[float, float]
    sub_energy: float  # 0-1: relative energy in sub range
    bass_energy: float
    mid_energy: float
    high_energy: float
    dynamics_range_db: float  # typical dynamic range
    halftime: bool = False
    tags: list[str] = field(default_factory=list)


# Genre profiles database
GENRE_PROFILES: list[GenreProfile] = [
    GenreProfile("Dubstep", (138, 152), 0.8, 0.9, 0.5, 0.3, 12.0,
                 halftime=True, tags=["dubstep", "bass", "drop"]),
    GenreProfile("Riddim", (140, 150), 0.7, 0.95, 0.4, 0.2, 8.0,
                 halftime=True, tags=["riddim", "minimal", "heavy"]),
    GenreProfile("Brostep", (140, 150), 0.6, 0.85, 0.7, 0.4, 10.0,
                 halftime=True, tags=["brostep", "aggressive", "mid-range"]),
    GenreProfile("Melodic Dubstep", (140, 150), 0.5, 0.6, 0.7, 0.5, 15.0,
                 tags=["melodic", "emotional", "atmospheric"]),
    GenreProfile("Drum & Bass", (170, 180), 0.5, 0.7, 0.6, 0.5, 14.0,
                 tags=["dnb", "jungle", "fast"]),
    GenreProfile("Trap", (130, 170), 0.8, 0.7, 0.5, 0.4, 10.0,
                 halftime=True, tags=["trap", "808", "hiphop"]),
    GenreProfile("Future Bass", (130, 160), 0.4, 0.5, 0.8, 0.7, 16.0,
                 tags=["future", "bright", "chords"]),
    GenreProfile("Neurofunk", (170, 180), 0.4, 0.8, 0.8, 0.5, 10.0,
                 tags=["neuro", "techy", "reese"]),
    GenreProfile("Tearout", (140, 150), 0.6, 0.9, 0.6, 0.3, 6.0,
                 halftime=True, tags=["tearout", "aggressive", "raw"]),
    GenreProfile("Colour Bass", (140, 150), 0.5, 0.7, 0.8, 0.6, 14.0,
                 halftime=True, tags=["colour", "harmonic", "textured"]),
    GenreProfile("Deep Dubstep", (138, 142), 0.9, 0.6, 0.3, 0.2, 18.0,
                 tags=["deep", "minimal", "uk"]),
    GenreProfile("Hybrid Trap", (140, 160), 0.7, 0.8, 0.6, 0.4, 10.0,
                 halftime=True, tags=["hybrid", "trap", "dubstep"]),
]


@dataclass
class SpectralFeatures:
    """Extracted spectral features from audio."""
    bpm: float = 140.0
    sub_energy: float = 0.0  # 20-60Hz
    bass_energy: float = 0.0  # 60-250Hz
    mid_energy: float = 0.0  # 250-4000Hz
    high_energy: float = 0.0  # 4000-20000Hz
    dynamics_range_db: float = 12.0
    rms_db: float = -12.0
    peak_db: float = -3.0
    halftime_detected: bool = False
    zero_crossing_rate: float = 0.0


@dataclass
class GenreMatch:
    """A genre classification match."""
    genre: str
    confidence: float  # 0-1
    tags: list[str] = field(default_factory=list)


@dataclass
class GenreResult:
    """Full genre detection result."""
    features: SpectralFeatures
    matches: list[GenreMatch] = field(default_factory=list)
    primary_genre: str = ""
    confidence: float = 0.0

    def to_dict(self) -> dict:
        return {
            "primary_genre": self.primary_genre,
            "confidence": round(self.confidence, 3),
            "matches": [
                {"genre": m.genre, "confidence": round(m.confidence, 3),
                 "tags": m.tags}
                for m in self.matches
            ],
            "features": {
                "bpm": self.features.bpm,
                "sub_energy": round(self.features.sub_energy, 3),
                "bass_energy": round(self.features.bass_energy, 3),
                "mid_energy": round(self.features.mid_energy, 3),
                "high_energy": round(self.features.high_energy, 3),
                "dynamics_range_db": round(self.features.dynamics_range_db, 1),
            },
        }


def extract_features_from_signal(signal: list[float],
                                  sample_rate: int = SAMPLE_RATE,
                                  bpm: float = 140.0) -> SpectralFeatures:
    """Extract spectral features from a raw signal."""
    n = len(signal)
    if n == 0:
        return SpectralFeatures()

    # RMS and peak
    rms = math.sqrt(sum(s * s for s in signal) / n)
    peak = max(abs(s) for s in signal)
    rms_db = 20 * math.log10(max(rms, 1e-10))
    peak_db = 20 * math.log10(max(peak, 1e-10))

    # Zero crossing rate
    zc = sum(1 for i in range(1, n) if signal[i] * signal[i - 1] < 0)
    zcr = zc / n

    # Simple frequency band energy estimation via zero-crossings
    # and signal characteristics
    avg_freq = zcr * sample_rate / 2

    # Estimate band energies based on average frequency
    sub_e = max(0.0, 1.0 - avg_freq / 60) if avg_freq < 120 else 0.0
    bass_e = max(0.0, min(1.0, 1.0 - abs(avg_freq - 150) / 200))
    mid_e = max(0.0, min(1.0, 1.0 - abs(avg_freq - 1000) / 2000))
    high_e = max(0.0, min(1.0, (avg_freq - 3000) / 5000)) \
        if avg_freq > 3000 else 0.0

    # Dynamic range
    chunk_size = max(1, n // 20)
    chunk_rms = []
    for i in range(0, n - chunk_size, chunk_size):
        chunk = signal[i:i + chunk_size]
        cr = math.sqrt(sum(s * s for s in chunk) / len(chunk))
        if cr > 1e-10:
            chunk_rms.append(20 * math.log10(cr))
    dynamics = 0.0
    if chunk_rms:
        dynamics = max(chunk_rms) - min(chunk_rms)

    return SpectralFeatures(
        bpm=bpm,
        sub_energy=sub_e,
        bass_energy=bass_e,
        mid_energy=mid_e,
        high_energy=high_e,
        dynamics_range_db=dynamics,
        rms_db=rms_db,
        peak_db=peak_db,
        zero_crossing_rate=zcr,
    )


def classify_genre(features: SpectralFeatures) -> GenreResult:
    """Classify genre based on spectral features."""
    matches: list[GenreMatch] = []

    for profile in GENRE_PROFILES:
        score = 0.0
        max_score = 0.0

        # BPM match (weighted heavily)
        max_score += 30
        bpm_lo, bpm_hi = profile.bpm_range
        if bpm_lo <= features.bpm <= bpm_hi:
            score += 30
        elif abs(features.bpm - (bpm_lo + bpm_hi) / 2) < 20:
            score += 15
        elif abs(features.bpm - (bpm_lo + bpm_hi) / 2) < 40:
            score += 5

        # Sub energy
        max_score += 15
        sub_diff = abs(features.sub_energy - profile.sub_energy)
        score += max(0, 15 * (1 - sub_diff * 2))

        # Bass energy
        max_score += 20
        bass_diff = abs(features.bass_energy - profile.bass_energy)
        score += max(0, 20 * (1 - bass_diff * 2))

        # Mid energy
        max_score += 15
        mid_diff = abs(features.mid_energy - profile.mid_energy)
        score += max(0, 15 * (1 - mid_diff * 2))

        # High energy
        max_score += 10
        high_diff = abs(features.high_energy - profile.high_energy)
        score += max(0, 10 * (1 - high_diff * 2))

        # Dynamics
        max_score += 10
        dyn_diff = abs(features.dynamics_range_db -
                       profile.dynamics_range_db)
        score += max(0, 10 * (1 - dyn_diff / 10))

        confidence = score / max_score if max_score > 0 else 0
        matches.append(GenreMatch(
            genre=profile.name,
            confidence=confidence,
            tags=profile.tags,
        ))

    # Sort by confidence
    matches.sort(key=lambda m: m.confidence, reverse=True)

    primary = matches[0] if matches else GenreMatch("Unknown", 0.0)
    return GenreResult(
        features=features,
        matches=matches[:5],  # Top 5
        primary_genre=primary.genre,
        confidence=primary.confidence,
    )


def detect_genre_from_params(bpm: float = 140.0,
                              sub_energy: float = 0.7,
                              bass_energy: float = 0.8,
                              mid_energy: float = 0.5,
                              high_energy: float = 0.3) -> GenreResult:
    """Quick genre detection from manual parameters."""
    features = SpectralFeatures(
        bpm=bpm,
        sub_energy=sub_energy,
        bass_energy=bass_energy,
        mid_energy=mid_energy,
        high_energy=high_energy,
    )
    return classify_genre(features)


def genre_result_text(result: GenreResult) -> str:
    """Format genre result as readable text."""
    lines = [
        f"**Genre Detection** — Primary: **{result.primary_genre}** "
        f"({result.confidence:.0%} confidence)",
        "",
        "**Top Matches:**",
    ]
    for m in result.matches[:5]:
        bar = "█" * int(m.confidence * 20) + "░" * (20 - int(m.confidence * 20))
        lines.append(f"  {bar} {m.confidence:.0%} {m.genre}")
        if m.tags:
            lines.append(f"    Tags: {', '.join(m.tags)}")

    lines.append("")
    lines.append("**Features:**")
    f = result.features
    lines.append(f"  BPM: {f.bpm} | Sub: {f.sub_energy:.2f} | "
                  f"Bass: {f.bass_energy:.2f} | Mid: {f.mid_energy:.2f} | "
                  f"High: {f.high_energy:.2f}")
    return "\n".join(lines)


def main() -> None:
    print("Genre Detector Engine")
    # Test with dubstep profile
    result = detect_genre_from_params(
        bpm=140, sub_energy=0.8, bass_energy=0.9,
        mid_energy=0.5, high_energy=0.3,
    )
    print(genre_result_text(result))
    print()

    # Test with DnB profile
    result = detect_genre_from_params(
        bpm=174, sub_energy=0.5, bass_energy=0.7,
        mid_energy=0.6, high_energy=0.5,
    )
    print(genre_result_text(result))
    print("Done.")


if __name__ == "__main__":
    main()
