"""
DUBFORGE — Reference Analyzer Engine  (Session 166)

Compare a mix against reference track characteristics —
frequency balance, loudness, dynamics, stereo width.
"""

import math
from dataclasses import dataclass, field

from engine.config_loader import PHI
SAMPLE_RATE = 48000


@dataclass
class TrackProfile:
    """Spectral/dynamic profile of a track."""
    name: str = ""
    rms_db: float = -14.0
    peak_db: float = -1.0
    crest_factor_db: float = 13.0
    sub_energy: float = 0.0  # 20-60Hz (0-1)
    bass_energy: float = 0.0  # 60-250Hz
    mid_energy: float = 0.0  # 250-4kHz
    high_energy: float = 0.0  # 4k-20kHz
    stereo_width: float = 0.5
    dynamic_range_db: float = 12.0

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "rms_db": round(self.rms_db, 1),
            "peak_db": round(self.peak_db, 1),
            "crest_factor_db": round(self.crest_factor_db, 1),
            "sub_energy": round(self.sub_energy, 3),
            "bass_energy": round(self.bass_energy, 3),
            "mid_energy": round(self.mid_energy, 3),
            "high_energy": round(self.high_energy, 3),
            "stereo_width": round(self.stereo_width, 2),
            "dynamic_range_db": round(self.dynamic_range_db, 1),
        }


# Reference profiles for common styles
REFERENCE_PROFILES: dict[str, TrackProfile] = {
    "subtronics": TrackProfile(
        "Subtronics Reference", -8.0, -0.5, 7.5,
        0.75, 0.85, 0.6, 0.35, 0.4, 8.0,
    ),
    "excision": TrackProfile(
        "Excision Reference", -7.0, -0.3, 6.7,
        0.8, 0.9, 0.55, 0.3, 0.35, 6.0,
    ),
    "skrillex": TrackProfile(
        "Skrillex Reference", -8.5, -0.5, 8.0,
        0.6, 0.8, 0.75, 0.5, 0.5, 10.0,
    ),
    "virtual_riot": TrackProfile(
        "Virtual Riot Reference", -8.0, -0.5, 7.5,
        0.7, 0.85, 0.7, 0.45, 0.5, 9.0,
    ),
    "noisia": TrackProfile(
        "Noisia Reference", -9.0, -0.8, 8.2,
        0.65, 0.75, 0.8, 0.5, 0.6, 11.0,
    ),
    "dubforge_phi": TrackProfile(
        "DUBFORGE PHI Reference", -8.0, -0.5, 7.5,
        0.7, 0.8, 0.65, 0.4, 0.5, 1.618 * 6,
    ),
}


@dataclass
class ComparisonPoint:
    """A single comparison metric."""
    metric: str
    your_value: float
    ref_value: float
    diff: float
    severity: str  # ok, caution, problem
    suggestion: str


@dataclass
class ReferenceComparison:
    """Full comparison result."""
    reference_name: str
    your_profile: TrackProfile
    ref_profile: TrackProfile
    points: list[ComparisonPoint] = field(default_factory=list)
    overall_match: float = 0.0  # 0-100%

    def to_dict(self) -> dict:
        return {
            "reference": self.reference_name,
            "overall_match": round(self.overall_match, 1),
            "your_profile": self.your_profile.to_dict(),
            "ref_profile": self.ref_profile.to_dict(),
            "points": [
                {
                    "metric": p.metric,
                    "your_value": round(p.your_value, 2),
                    "ref_value": round(p.ref_value, 2),
                    "diff": round(p.diff, 2),
                    "severity": p.severity,
                    "suggestion": p.suggestion,
                }
                for p in self.points
            ],
        }


def profile_from_signal(signal: list[float],
                          name: str = "Your Mix") -> TrackProfile:
    """Create a profile from a raw signal."""
    if not signal:
        return TrackProfile(name=name)

    n = len(signal)
    rms = math.sqrt(sum(s * s for s in signal) / n)
    peak = max(abs(s) for s in signal)
    rms_db = 20 * math.log10(max(rms, 1e-10))
    peak_db = 20 * math.log10(max(peak, 1e-10))
    crest = peak_db - rms_db

    # Estimate frequency content via zero crossings
    zc = sum(1 for i in range(1, n) if signal[i] * signal[i - 1] < 0)
    zcr = zc / n
    avg_freq = zcr * SAMPLE_RATE / 2

    sub = max(0.0, 1.0 - avg_freq / 60) if avg_freq < 120 else 0.0
    bass = max(0.0, min(1.0, 1.0 - abs(avg_freq - 150) / 200))
    mid = max(0.0, min(1.0, 1.0 - abs(avg_freq - 1000) / 2000))
    high = max(0.0, (avg_freq - 3000) / 5000) if avg_freq > 3000 else 0.0

    # Dynamic range from chunks
    chunk_size = max(1, n // 20)
    chunk_rms = []
    for i in range(0, n - chunk_size, chunk_size):
        chunk = signal[i:i + chunk_size]
        cr = math.sqrt(sum(s * s for s in chunk) / len(chunk))
        if cr > 1e-10:
            chunk_rms.append(20 * math.log10(cr))
    dr = max(chunk_rms) - min(chunk_rms) if chunk_rms else 0.0

    return TrackProfile(
        name=name,
        rms_db=rms_db,
        peak_db=peak_db,
        crest_factor_db=crest,
        sub_energy=sub,
        bass_energy=bass,
        mid_energy=mid,
        high_energy=high,
        dynamic_range_db=dr,
    )


def compare_to_reference(your_profile: TrackProfile,
                          ref_name: str = "subtronics"
                          ) -> ReferenceComparison:
    """Compare your profile to a reference."""
    ref = REFERENCE_PROFILES.get(ref_name)
    if not ref:
        ref = REFERENCE_PROFILES["subtronics"]
        ref_name = "subtronics"

    points: list[ComparisonPoint] = []
    total_score = 0.0
    n_metrics = 0

    # Compare each metric
    metrics = [
        ("RMS Level", your_profile.rms_db, ref.rms_db, 3.0, "dB",
         "Adjust overall level"),
        ("Peak Level", your_profile.peak_db, ref.peak_db, 1.0, "dB",
         "Adjust limiter threshold"),
        ("Crest Factor", your_profile.crest_factor_db,
         ref.crest_factor_db, 3.0, "dB",
         "Adjust compression ratio"),
        ("Sub Energy", your_profile.sub_energy, ref.sub_energy, 0.2,
         "", "Adjust sub bass level"),
        ("Bass Energy", your_profile.bass_energy, ref.bass_energy, 0.2,
         "", "Adjust bass EQ 60-250Hz"),
        ("Mid Energy", your_profile.mid_energy, ref.mid_energy, 0.2,
         "", "Adjust mid EQ 250-4kHz"),
        ("High Energy", your_profile.high_energy, ref.high_energy, 0.2,
         "", "Adjust high EQ 4k+"),
        ("Dynamic Range", your_profile.dynamic_range_db,
         ref.dynamic_range_db, 4.0, "dB",
         "Adjust compressor settings"),
    ]

    for name, yours, theirs, tolerance, unit, suggestion in metrics:
        diff = yours - theirs
        abs_diff = abs(diff)

        if abs_diff <= tolerance * 0.5:
            severity = "ok"
            score = 1.0
        elif abs_diff <= tolerance:
            severity = "caution"
            score = 0.5
        else:
            severity = "problem"
            score = max(0.0, 1.0 - abs_diff / (tolerance * 2))

        direction = "higher" if diff > 0 else "lower"
        sug = f"{suggestion} ({abs_diff:.1f}{unit} {direction} than ref)"

        points.append(ComparisonPoint(
            metric=name,
            your_value=yours,
            ref_value=theirs,
            diff=round(diff, 2),
            severity=severity,
            suggestion=sug if severity != "ok" else "On target",
        ))

        total_score += score
        n_metrics += 1

    overall = (total_score / n_metrics * 100) if n_metrics > 0 else 0

    return ReferenceComparison(
        reference_name=ref_name,
        your_profile=your_profile,
        ref_profile=ref,
        points=points,
        overall_match=overall,
    )


def comparison_text(comp: ReferenceComparison) -> str:
    """Format comparison as readable text."""
    lines = [
        f"**Reference Comparison: {comp.reference_name.upper()}**",
        f"Overall Match: {comp.overall_match:.0f}%",
        "",
    ]

    for p in comp.points:
        icon = {"ok": "✅", "caution": "⚠️", "problem": "❌"}[p.severity]
        lines.append(
            f"  {icon} **{p.metric}**: {p.your_value:.2f} vs "
            f"{p.ref_value:.2f} (diff: {p.diff:+.2f})"
        )
        if p.severity != "ok":
            lines.append(f"     → {p.suggestion}")

    return "\n".join(lines)


def list_references() -> list[str]:
    """List available reference profiles."""
    return sorted(REFERENCE_PROFILES.keys())


def main() -> None:
    print("Reference Analyzer Engine")
    print(f"  Available refs: {list_references()}")

    # Simulate a mix profile
    your_mix = TrackProfile(
        name="My Mix",
        rms_db=-10.0,
        peak_db=-0.8,
        crest_factor_db=9.2,
        sub_energy=0.6,
        bass_energy=0.7,
        mid_energy=0.8,
        high_energy=0.5,
        dynamic_range_db=10.0,
    )

    for ref_name in list_references():
        comp = compare_to_reference(your_mix, ref_name)
        print(f"\n{comparison_text(comp)}")
    print("\nDone.")


if __name__ == "__main__":
    main()
